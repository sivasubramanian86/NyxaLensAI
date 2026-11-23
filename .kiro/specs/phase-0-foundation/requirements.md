# Phase 0 — Foundation: Requirements

## Status: COMPLETE ✅

All deliverables for Phase 0 exist in the repository. No further implementation needed.

---

## Functional Requirements

### FR-1: Monorepo Structure
WHEN the repository is cloned, THE SYSTEM SHALL contain the exact directory layout:
- `cdk/` — CDK app entrypoint, stacks/, requirements.txt, cdk.json
- `lambdas/shared/` — schemas.py, bedrock_client.py, github_client.py, __init__.py
- `lambdas/{api_router,orchestrator,repo_scanner,name_collision,landscape_scout,analogy_engine,enhancement_citation}/handler.py`
- `data/patterns_20.json`, `data/seed_opensearch.py`
- `docs/SCORING_RUBRIC.md`
- `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- `frontend/`
- `Makefile`, `.gitignore`, `README.md`
- `.kiro/steering/`, `.kiro/specs/`

### FR-2: Pydantic Schemas
WHEN data passes between any two Lambda functions, THE SYSTEM SHALL validate it using
strict Pydantic v2 models defined in `lambdas/shared/schemas.py`:
- `ScanRequest`, `UniversalProjectProfile`, `ProblemSignature`
- `NameCollisionResult`, `LandscapeResult`, `CompetitorEntry`, `AcademicPaper`
- `PatternEvidence`, `AnalogyMatch`, `MappingTableEntry`
- `KillKeepInjectItem`, `BacklogItem`, `NyxaScore`, `PipelineTrace`, `EnhancementDossier`

### FR-3: Bedrock Client Wrapper
WHEN a Lambda invokes a foundation model, THE SYSTEM SHALL route the call through
`lambdas/shared/bedrock_client.py` using the Bedrock Converse API with:
- `invoke_lite()` for Nova Lite (classification/extraction)
- `invoke_sonnet_json()` for Claude Sonnet with mandatory tool-use schema
- `embed()` for Titan Embeddings v2 (1024-dim)
- Exponential backoff retry on ThrottlingException (max 3 attempts)

### FR-4: GitHub Token Security
WHEN a Lambda requires GitHub API access, THE SYSTEM SHALL retrieve the token from
AWS Secrets Manager secret `nyxalens/github-token` via `lambdas/shared/github_client.py`
using `@lru_cache(maxsize=1)`. The token SHALL never appear in environment variables,
CloudFormation templates, or logs.

### FR-5: Makefile Targets
THE SYSTEM SHALL provide a Makefile with working targets:
`bootstrap`, `lint`, `test`, `seed-patterns`, `seed-local`, `deploy`, `destroy`

### FR-6: CI Pipeline
WHEN a pull request is opened against `main`, THE SYSTEM SHALL run:
- `ruff check lambdas/ data/ tests/` (lint)
- `pytest tests/unit/ -v --tb=short` (unit tests)

---

## Non-Functional Requirements

### NFR-1: Python Version
All Lambda handlers and CDK code SHALL use Python 3.12.

### NFR-2: No Real AWS Calls in Unit Tests
Unit tests SHALL mock all boto3 clients. No test SHALL make a real AWS API call.

---

## Acceptance Criteria — All Passing ✅

- [x] `lambdas/shared/schemas.py` exists with all 10 Pydantic v2 models
- [x] `lambdas/shared/bedrock_client.py` exists with `invoke_lite`, `invoke_sonnet_json`, `embed`
- [x] `lambdas/shared/github_client.py` exists with Secrets Manager token caching
- [x] `data/patterns_20.json` exists with 20 valid patterns
- [x] `cdk/stacks/nyxalens_stack.py` exists with full infrastructure wiring
- [x] `tests/unit/test_schemas.py` — 18 unit tests covering schemas and corpus integrity
- [x] `tests/unit/test_bedrock_client.py` — mocked Bedrock + retry tests
- [x] `tests/unit/test_github_client.py` — mocked Secrets Manager tests
- [x] `Makefile` exists with all required targets
- [x] `.github/workflows/ci.yml` exists
- [x] `docs/SCORING_RUBRIC.md` exists with formula and collision thresholds
- [x] `.kiro/steering/project.md` and `.kiro/steering/conventions.md` exist
