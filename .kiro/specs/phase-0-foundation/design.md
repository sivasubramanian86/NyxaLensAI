# Phase 0 — Foundation: Design

## Status: COMPLETE ✅

---

## Component Map

```
lambdas/shared/schemas.py
  └── 10 Pydantic v2 models (ScanRequest → EnhancementDossier)
      Validated at every Lambda boundary.

lambdas/shared/bedrock_client.py
  ├── invoke_lite(prompt)           → str          (Nova Lite)
  ├── invoke_sonnet_json(prompt, tool_schema) → dict (Claude Sonnet + tool-use)
  └── embed(text)                   → list[float]  (Titan v2, 1024-dim)
      lru_cache(1) on boto3 client. Exponential backoff on ThrottlingException.

lambdas/shared/github_client.py
  ├── _get_token()       → str   (Secrets Manager, lru_cache(1))
  ├── get_repo_tree()    → dict
  ├── get_file_content() → str
  ├── search_repos()     → list[dict]
  └── search_repos_by_name() → list[dict]

cdk/stacks/nyxalens_stack.py
  ├── DynamoDB Table (scan_id PK, TTL, PAY_PER_REQUEST)
  ├── S3 Bucket (evidence snapshots, BLOCK_ALL public access)
  ├── Secrets Manager reference (nyxalens/github-token)
  ├── OpenSearch Serverless collection (VECTORSEARCH)
  ├── IAM Role (bedrock:InvokeModel, aoss:APIAccessAll, DDB r/w, S3 r/w)
  ├── 6 Lambda functions (orchestrator, repo_scanner, name_collision,
  │   landscape_scout, analogy_engine, enhancement_citation)
  ├── Step Functions Standard Workflow
  │   Orchestrator → Parallel(4 lanes) → EnhancementCitation
  ├── API Gateway LambdaRestApi (POST /scans, GET /scans/{id}, GET /badge/{id})
  └── CfnOutputs: ApiEndpointUrl, OpenSearchEndpoint, StateMachineArn
```

## Key design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Pydantic version | v2 | Strict mode, `model_validate`, faster validation |
| Bedrock API | Converse | Unified across models; tool-use enforces JSON output |
| Token storage | Secrets Manager | Never in env vars or CloudFormation |
| CDK workflow type | Standard (not Express) | Live execution graph visible in AWS Console during judging |
| Scoring location | Inside Enhancement Lambda | Same in-memory JSON — no extra cold start |
