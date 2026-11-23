# NyxaLensAI — Project Steering

## What this project is

NyxaLensAI is a **Repo Architectural Amplifier** built on AWS.
It scans a GitHub repository or Markdown RFC and returns an **Enhancement Dossier**
containing a Kill/Keep/Inject matrix, a Name Collision Traffic Light, a Cross-Domain
Analogy Card, a calibrated Nyxa Score (0–100), and a ranked Enhancement Backlog.

Tagline: **"See in the dark. Build in the light."**

## Architecture in one paragraph

A Next.js frontend on AWS Amplify accepts a GitHub URL or Markdown RFC.
`POST /scans` triggers an AWS Step Functions Standard Workflow:
an Orchestrator Lambda (Nova Lite) builds a `UniversalProjectProfile`,
then 4 parallel discovery lanes run simultaneously (Repo Scanner, Name Collision,
Landscape Scout, Analogy Engine), and finally a sequential Enhancement + Citation +
Scoring Lambda (Claude Sonnet) synthesises the dossier, strips hallucinated citations,
and writes the result to DynamoDB. The frontend polls every 1.5 s.

## Critical topology constraint

**Enhancement + Citation + Scoring runs AFTER the parallel fan-in, never inside it.**
It requires the outputs of all 4 discovery lanes as input.

## Stack

| Layer | Service |
|---|---|
| Frontend | Next.js 14 App Router on AWS Amplify |
| API | Amazon API Gateway (REST) |
| Orchestration | AWS Step Functions Standard Workflow |
| Compute | AWS Lambda Python 3.12 |
| Foundation models | Amazon Bedrock — Nova Lite + Claude 3.5 Sonnet + Titan Embeddings v2 |
| Vector search | Amazon OpenSearch Serverless (k-NN + BM25) with local numpy fallback |
| State / cache | Amazon DynamoDB (on-demand) |
| Evidence store | Amazon S3 |
| Secrets | AWS Secrets Manager (`nyxalens/github-token`) |
| IaC | AWS CDK v2 (Python) |

## Coding conventions

- Python 3.12, Pydantic v2 strict models, `ruff` linting
- Every Lambda input/output validated against `lambdas/shared/schemas.py`
- No LLM call without a structured tool-use schema (Bedrock Converse API)
- GitHub token always from Secrets Manager via `github_client.get_token()` — never plaintext
- All cited URLs in the Dossier must pass the Citation Verifier before rendering
- Mermaid node labels sanitised (strip `()` and `"` inside `[...]`) before persistence

## Scoring rules

```
Nyxa Score = 0.40 × S_deterministic + 0.60 × S_rubric
Projected post-enhancement delta capped at +12 to +18 points (never inflated)
```

See `docs/SCORING_RUBRIC.md` for full formula and collision thresholds.

## Cost control

- Use Nova Lite for classification/extraction; Claude Sonnet only for final synthesis
- Local numpy fallback for AOSS (run `make seed-local` before `make destroy`)
- AOSS has ~$350/mo OCU floor — destroy after demo, run via local fallback post-demo

## Honest limitations (state in all outputs)

- Lift estimates are architectural projections, not empirical benchmarks
- Public GitHub repos only (private OAuth is v2)
- Single region (us-east-1)
- 20 patterns cover common agentic bottlenecks; exotic domains suppressed at similarity < 0.72
