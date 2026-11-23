# NyxaLensAI deployment runbook

This runbook deploys the CDK stack in `us-east-1`. It creates billable AWS resources, including an OpenSearch Serverless collection. The current task has not deployed them.

## Prerequisites

- Python 3.12, Node.js 20+, AWS CLI, and an AWS account with permission to create the resources in `cdk/stacks/nyxalens_stack.py`.
- AWS credentials configured for the target account. The CDK app pins `us-east-1`.
- AWS CDK v2 CLI: `npm install --global aws-cdk`.

## Create the GitHub secret

Use a read-only token that can access public repositories. The Lambdas read it from Secrets Manager; do not put the token in `.env` or Lambda environment variables.

```powershell
aws secretsmanager create-secret `
  --name nyxalens/github-token `
  --secret-string 'YOUR_READ_ONLY_GITHUB_TOKEN' `
  --region us-east-1
```

If the secret already exists, update it with `aws secretsmanager put-secret-value --secret-id nyxalens/github-token --secret-string 'YOUR_READ_ONLY_GITHUB_TOKEN' --region us-east-1`.

## Install and deploy

```powershell
make bootstrap
. .\.venv\Scripts\Activate.ps1
aws sts get-caller-identity
cdk bootstrap aws://ACCOUNT_ID/us-east-1
make deploy
```

Replace `ACCOUNT_ID` with the `Account` value returned by `aws sts get-caller-identity`. `make deploy` runs `cdk deploy` from `cdk/`.

Read stack outputs after deployment:

```powershell
aws cloudformation describe-stacks `
  --stack-name NyxaLensAI `
  --region us-east-1 `
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" `
  --output table
```

Record `ApiEndpointUrl` and `OpenSearchEndpoint`. The stack also prints the state machine ARN, scans table name, and evidence bucket name. API routes are `POST /scans`, `GET /scans/{scan_id}`, and `GET /badge/{scan_id}`.

## Seed the pattern index

The Lambda role has data access to the index. Run the seeder with the deployed endpoint and the same AWS account credentials:

```powershell
$env:AWS_REGION = 'us-east-1'
$env:AOSS_ENDPOINT = 'https://REPLACE_WITH_OpenSearchEndpoint_OUTPUT'
python data/seed_opensearch.py --mode aoss
```

Use `--force-refresh` only when you intend to delete and recreate `systems-patterns-v1`. Check data and mapping first; the seeder uses Titan Embeddings v2 and requires Bedrock model access in the target region.

For local fallback, `python data/seed_opensearch.py --mode local` writes `data/patterns_20_embedded.json`. This still calls Bedrock to create embeddings; `--dry-run` validates only and makes no embedding calls.

## Connect Amplify

1. Connect the repository in AWS Amplify Hosting and select the `frontend` monorepo application root. Root `amplify.yml` already sets `appRoot: frontend` and runs `npm ci` / `npm run build`.
2. Set Amplify environment variable `NEXT_PUBLIC_API_URL` to the `ApiEndpointUrl` output exactly as printed, including its stage path and trailing slash if present.
3. Deploy the branch and open the Amplify URL. Use one of the three precomputed demos to inspect the UI without calling AWS, then submit a small public repository or RFC to exercise the live pipeline.

## Tear down after demo

If retaining local vector search, create the embedded corpus before teardown:

```powershell
python data/seed_opensearch.py --mode local
make destroy
```

`make destroy` deletes the stack's DynamoDB tables, evidence bucket contents, and OpenSearch collection. Export any data you need first. Removing the backend does not automatically remove the Amplify app or the manually created GitHub secret; delete those separately if no longer needed.

## Deployment checks and limits

| Cost source | Driver | Control |
|---|---|---|
| OpenSearch Serverless | Collection capacity while provisioned | Run `make destroy` after the demo |
| Bedrock models | Input/output tokens and embeddings | Use Nova Lite for extraction; one Sonnet synthesis call; seed only 20 patterns |
| Lambda / Step Functions | Invocations and duration | 45-second workflow limit; bounded repository scan |
| DynamoDB / S3 | Requests and retained scan evidence | TTL on scan and memory records; teardown removes stack data |

- Run `make lint`, `make test`, and frontend `npm test -- --runInBand` / `npm run build` before deploy.
- Run `cdk synth` from `cdk/` after installing `cdk/requirements.txt` and the CDK CLI.
- **Do not put this frontend on production traffic yet:** the requested Next.js 14 line is now unsupported. Next.js lists 14.x as unsupported and its October 2026 security fixes are published for 15.5.28 and 16.4.1; upgrade to a currently supported patched line before production. See [Next.js support policy](https://nextjs.org/support-policy) and [October 2026 security update](https://nextjs.org/blog/nextjs-security-update-october-14-2026).
- The OpenSearch network policy currently permits public network reachability; IAM data access policy controls authorized calls. Tighten the network policy before production.
- Session Memory uses AgentCore only when `AGENTCORE_MEMORY_ID` is set and the SDK exposes the needed operations; otherwise it uses the DynamoDB fallback.
- Offline fixtures are precomputed examples, not fresh repository scans or live citation checks.
