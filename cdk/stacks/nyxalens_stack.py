"""
NyxaLensAI CDK Stack
Topology: Orchestrator → 4 Parallel Discovery Lanes → Sequential Enhancement/Citation/Scoring
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import jsii
from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput, BundlingOptions, ILocalBundling,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_opensearchserverless as aoss,
)
from constructs import Construct


REPO_ROOT = Path(__file__).resolve().parents[2]

ASSET_EXCLUDES = [
    ".git", ".github", ".kiro", ".agents", ".codegraph", ".venv", "venv", "cdk", "frontend",
    "tests", "docs", "node_modules", "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache",
    "cdk.out", "*.md", "Makefile", "amplify.yml",
]


@jsii.implements(ILocalBundling)
class LocalLambdaBundler:
    """Bundle Lambda code without Docker: pip-install Linux wheels, then copy code + data."""

    def try_bundle(self, output_dir: str, *args, **kwargs) -> bool:
        try:
            out = Path(output_dir)
            reqs = [
                line.strip()
                for line in (REPO_ROOT / "lambdas" / "requirements.txt").read_text().splitlines()
                if line.strip() and not line.startswith("#")
            ]
            # Metaphone ships only as a pure-Python sdist; install it separately.
            wheel_reqs = [r for r in reqs if not r.lower().startswith("metaphone")]
            pure_reqs = [r for r in reqs if r.lower().startswith("metaphone")]
            base = [sys.executable, "-m", "pip", "install", "--no-compile", "--upgrade", "-t", str(out)]
            subprocess.run(
                base + ["--platform", "manylinux2014_x86_64", "--implementation", "cp",
                        "--python-version", "3.12", "--only-binary=:all:"] + wheel_reqs,
                check=True,
            )
            if pure_reqs:
                subprocess.run(base + ["--no-deps"] + pure_reqs, check=True)
            shutil.copytree(REPO_ROOT / "lambdas", out, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            shutil.copytree(REPO_ROOT / "data", out / "data", dirs_exist_ok=True)
            return True
        except Exception as exc:  # fall back to Docker bundling
            print(f"Local bundling failed ({exc}); falling back to Docker.")
            return False


COLLECTION_NAME = "nyxalens-patterns"
AOSS_INDEX      = "systems-patterns-v1"
LITE_MODEL_ID   = "amazon.nova-lite-v1:0"
SONNET_MODEL_ID = "us.anthropic.claude-sonnet-4-6"  # cross-region inference profile (us-east-1)
EMBED_MODEL_ID  = "amazon.titan-embed-text-v2:0"


class NyxaLensStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── 1. DynamoDB — scan state polling + score history ──────────────
        scans_table = dynamodb.Table(
            self, "NyxaScansTable",
            partition_key=dynamodb.Attribute(name="scan_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
            point_in_time_recovery=False,
        )
        scans_table.add_global_secondary_index(
            index_name="CacheIndex",
            partition_key=dynamodb.Attribute(name="cache_key", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="completed_at", type=dynamodb.AttributeType.NUMBER),
            projection_type=dynamodb.ProjectionType.ALL,
        )
        session_memory_table = dynamodb.Table(
            self, "NyxaSessionMemoryTable",
            table_name="NyxaSessionMemory",
            partition_key=dynamodb.Attribute(name="session_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.NUMBER),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── 2. S3 — raw grounding evidence snapshots ──────────────────────
        evidence_bucket = s3.Bucket(
            self, "NyxaEvidenceBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # ── 3. GitHub token in Secrets Manager ───────────────────────────
        # Create the secret once manually:
        #   aws secretsmanager create-secret --name nyxalens/github-token \
        #     --secret-string "ghp_YOUR_TOKEN"
        github_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "GitHubTokenSecret", "nyxalens/github-token"
        )

        # ── 4. Amazon OpenSearch Serverless collection (OPTIONAL) ─────────
        # AOSS bills a minimum of roughly $175-350/month while it exists.
        # It is OFF by default: the analogy lane then uses the local vector
        # fallback (data/patterns_20_embedded.json). Enable with:
        #   cdk deploy -c enable_aoss=true
        enable_aoss = str(self.node.try_get_context("enable_aoss") or "false").lower() == "true"
        pattern_collection = None
        if enable_aoss:
            enc_policy = aoss.CfnSecurityPolicy(
                self, "PatternEncryptionPolicy",
                name=f"{COLLECTION_NAME}-enc",
                type="encryption",
                policy=(
                    f'{{"Rules":[{{"ResourceType":"collection",'
                    f'"Resource":["collection/{COLLECTION_NAME}"]}}],'
                    f'"AWSOwnedKey":true}}'
                ),
            )
            net_policy = aoss.CfnSecurityPolicy(
                self, "PatternNetworkPolicy",
                name=f"{COLLECTION_NAME}-net",
                type="network",
                policy=(
                    f'[{{"Rules":[{{"ResourceType":"collection",'
                    f'"Resource":["collection/{COLLECTION_NAME}"]}},'
                    f'{{"ResourceType":"dashboard","Resource":["collection/{COLLECTION_NAME}"]}}],'
                    f'"AllowFromPublic":true}}]'
                ),
            )
            pattern_collection = aoss.CfnCollection(
                self, "PatternCollection",
                name=COLLECTION_NAME,
                type="VECTORSEARCH",
                description="NyxaLensAI 20-pattern cross-domain systems ontology",
            )
            pattern_collection.add_dependency(enc_policy)
            pattern_collection.add_dependency(net_policy)

        # ── 5. Shared Lambda execution role (least-privilege) ─────────────
        agent_role = iam.Role(
            self, "NyxaAgentExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess"),
            ],
        )
        agent_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"],
        ))
        if pattern_collection is not None:
            agent_role.add_to_policy(iam.PolicyStatement(
                actions=["aoss:APIAccessAll"],
                resources=[pattern_collection.attr_arn],
            ))
        scans_table.grant_read_write_data(agent_role)
        session_memory_table.grant_read_write_data(agent_role)
        evidence_bucket.grant_read_write(agent_role)

        # Grant GitHub secret read to the 3 Lambdas that call GitHub API
        # (done individually after Lambda creation below)

        # OpenSearch data access policy (only when AOSS is enabled)
        if pattern_collection is not None:
            aoss.CfnAccessPolicy(
                self, "PatternDataAccessPolicy",
                name=f"{COLLECTION_NAME}-data",
                type="data",
                policy=(
                    f'[{{"Rules":['
                    f'{{"ResourceType":"index","Resource":["index/{COLLECTION_NAME}/*"],'
                    f'"Permission":["aoss:*"]}},'
                    f'{{"ResourceType":"collection","Resource":["collection/{COLLECTION_NAME}"],'
                    f'"Permission":["aoss:*"]}}],'
                    f'"Principal":["{agent_role.role_arn}"]}}]'
                ),
            )

        # ── 6. Shared environment for all Lambdas ─────────────────────────
        shared_env = {
            "SCANS_TABLE":      scans_table.table_name,
            "EVIDENCE_BUCKET":  evidence_bucket.bucket_name,
            "AOSS_ENDPOINT":    pattern_collection.attr_collection_endpoint if pattern_collection else "",
            "AOSS_INDEX":       AOSS_INDEX,
            "LITE_MODEL_ID":    LITE_MODEL_ID,
            "SONNET_MODEL_ID":  SONNET_MODEL_ID,
            "EMBED_MODEL_ID":   EMBED_MODEL_ID,
            "GITHUB_SECRET_ARN": github_secret.secret_arn,
            "SESSION_MEMORY_TABLE": session_memory_table.table_name,
            "AGENTCORE_MEMORY_ID": os.environ.get("AGENTCORE_MEMORY_ID", ""),
        }
        agentcore_memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
        if agentcore_memory_id:
            agent_role.add_to_policy(iam.PolicyStatement(
                actions=["bedrock-agentcore:CreateEvent", "bedrock-agentcore:ListEvents"],
                resources=[f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:memory/{agentcore_memory_id}"],
            ))

        def build_lambda(logical_id: str, folder: str,
                         timeout_sec: int = 12, mem_mb: int = 512) -> _lambda.Function:
            return _lambda.Function(
                self, logical_id,
                runtime=_lambda.Runtime.PYTHON_3_12,
                handler=f"{folder}.handler.lambda_handler",
                code=_lambda.Code.from_asset(
                    str(REPO_ROOT),
                    exclude=ASSET_EXCLUDES,
                    bundling=BundlingOptions(
                        local=LocalLambdaBundler(),
                        image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                        command=["bash", "-c", "pip install -r /asset-input/lambdas/requirements.txt --no-compile -t /asset-output && cp -a /asset-input/lambdas/. /asset-output/ && cp -a /asset-input/data /asset-output/data"],
                    ),
                ),
                timeout=Duration.seconds(timeout_sec),
                memory_size=mem_mb,
                tracing=_lambda.Tracing.ACTIVE,
                role=agent_role,
                environment=shared_env,
            )

        orchestrator_fn   = build_lambda("OrchestratorFn",        "orchestrator",         10)
        repo_scanner_fn   = build_lambda("RepoScannerFn",          "repo_scanner",         12, 1024)
        name_collision_fn = build_lambda("NameCollisionFn",        "name_collision",       10)
        landscape_fn      = build_lambda("LandscapeScoutFn",       "landscape_scout",      12)
        analogy_fn        = build_lambda("AnalogyEngineFn",        "analogy_engine",       10)
        enhancement_fn    = build_lambda("EnhancementCitationFn",  "enhancement_citation", 20, 1024)
        failure_fn        = build_lambda("ScanFailureFn", "failure_handler", 5)

        # Grant GitHub secret read to the 3 API-calling Lambdas
        for fn in [repo_scanner_fn, name_collision_fn, landscape_fn]:
            github_secret.grant_read(fn)

        # ── 7. Step Functions: Orchestrator → 4 Parallel → Sequential ─────
        step_orchestrate = tasks.LambdaInvoke(
            self, "StepOrchestrate",
            lambda_function=orchestrator_fn,
            output_path="$.Payload",
        )

        parallel_discovery = sfn.Parallel(
            self, "ParallelDiscoveryLanes",
            result_path="$.discovery",
        )
        parallel_discovery.branch(
            tasks.LambdaInvoke(self, "Lane1RepoScanner",
                                lambda_function=repo_scanner_fn, output_path="$.Payload")
        )
        parallel_discovery.branch(
            tasks.LambdaInvoke(self, "Lane2NameCollision",
                                lambda_function=name_collision_fn, output_path="$.Payload")
        )
        parallel_discovery.branch(
            tasks.LambdaInvoke(self, "Lane3LandscapeScout",
                                lambda_function=landscape_fn, output_path="$.Payload")
        )
        parallel_discovery.branch(
            tasks.LambdaInvoke(self, "Lane4AnalogyEngine",
                                lambda_function=analogy_fn, output_path="$.Payload")
        )

        # Enhancement runs AFTER fan-in — it needs all 4 discovery payloads
        step_synthesize = tasks.LambdaInvoke(
            self, "StepEnhancementCitationScore",
            lambda_function=enhancement_fn,
            output_path="$.Payload",
        )

        failure_state = tasks.LambdaInvoke(
            self, "RecordPipelineFailure",
            lambda_function=failure_fn,
            output_path="$.Payload",
        )
        for state in (step_orchestrate, parallel_discovery, step_synthesize):
            state.add_catch(failure_state, result_path="$.failure")

        definition = step_orchestrate.next(parallel_discovery).next(step_synthesize)

        state_machine = sfn.StateMachine(
            self, "NyxaLensStateMachine",
            state_machine_name="NyxaLensOrchestrator-v1",
            # Standard (not Express) so the live execution graph is visible in Console
            state_machine_type=sfn.StateMachineType.STANDARD,
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.seconds(45),
        )

        # ── 8. API Gateway: POST /scans, GET /scans/{id}, GET /badge/{id} ─
        api_router_fn = build_lambda("ApiRouterFn", "api_router", 10)
        api_router_fn.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)
        state_machine.grant_start_execution(api_router_fn)
        scans_table.grant_read_write_data(api_router_fn)

        api = apigw.LambdaRestApi(
            self, "NyxaLensApi",
            rest_api_name="NyxaLensAPI-v1",
            handler=api_router_fn,
            proxy=False,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        scans_res   = api.root.add_resource("scans")
        scans_res.add_method("POST")
        scan_item   = scans_res.add_resource("{scan_id}")
        scan_item.add_method("GET")
        badge_res   = api.root.add_resource("badge").add_resource("{scan_id}")
        badge_res.add_method("GET")

        # ── 9. Outputs ────────────────────────────────────────────────────
        CfnOutput(self, "ApiEndpointUrl",
                   value=api.url,
                   description="Set as NEXT_PUBLIC_API_URL in Amplify")
        if pattern_collection is not None:
            CfnOutput(self, "OpenSearchEndpoint",
                       value=pattern_collection.attr_collection_endpoint,
                       description="Set as AOSS_ENDPOINT for seed_opensearch.py")
        CfnOutput(self, "StateMachineArn",
                   value=state_machine.state_machine_arn)
        CfnOutput(self, "ScansTableName",
                   value=scans_table.table_name)
        CfnOutput(self, "EvidenceBucketName",
                   value=evidence_bucket.bucket_name)
