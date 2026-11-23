# Phase 0 — Foundation: Tasks

## Status: IMPLEMENTED; CDK synth pending

All tasks completed. Files exist in the repository.

---

- [x] Create full monorepo directory skeleton
- [x] Write `lambdas/shared/schemas.py` — 10 Pydantic v2 models
- [x] Write `lambdas/shared/bedrock_client.py` — Converse API wrapper + retry
- [x] Write `lambdas/shared/github_client.py` — Secrets Manager token cache
- [x] Write `lambdas/shared/__init__.py`
- [x] Write Lambda handler stubs (all 6 — typed contracts, no logic yet)
- [x] Write `cdk/app.py`, `cdk/cdk.json`, `cdk/requirements.txt`
- [x] Write `cdk/stacks/nyxalens_stack.py` — full infrastructure wiring
- [x] Write `data/patterns_20.json` — 20 fully populated cross-domain patterns
- [x] Write `data/seed_opensearch.py` — `--mode aoss/local`, `--dry-run`, `--force-refresh`
- [x] Write `docs/SCORING_RUBRIC.md` — formula + collision thresholds
- [x] Write `Makefile` — bootstrap, lint, test, seed-patterns, seed-local, deploy, destroy
- [x] Write `.gitignore`
- [x] Write `README.md`
- [x] Write `.github/workflows/ci.yml` — ruff + pytest on PR
- [x] Write `tests/unit/test_schemas.py` — 18 tests (schemas + corpus integrity)
- [x] Write `tests/unit/test_bedrock_client.py` — mocked Bedrock + retry
- [x] Write `tests/unit/test_github_client.py` — mocked Secrets Manager
- [x] Write `.kiro/steering/project.md`
- [x] Write `.kiro/steering/conventions.md`

## Acceptance gate result

| Check | Result |
|---|---|
| Python lint | ✅ Ruff passes |
| Unit/integration checks | ✅ 85 tests pass |
| `cdk synth` | ⏳ Not run; CDK CLI and `aws_cdk` are not installed in current environment |
| All AC checked | ⏳ Synth remains unverified |

## Proceed to Phase 1 →
