# Phase 6 — Demo Hardening & Polish: Tasks

## Status: PARTIAL; fixtures and local hardening checks pass

- [x] Create `tests/fixtures/fixture-a-python-agent/` — Python fixture + precomputed dossier
- [x] Create `tests/fixtures/fixture-b-typescript-app/` — TypeScript fixture + precomputed dossier
- [x] Create `tests/fixtures/fixture-c-markdown-rfc/` — RFC fixture + precomputed dossier
- [x] Add invalid-URL guard to `lambdas/api_router/handler.py` → 422 without Step Functions
- [x] Add monorepo file cap test (600-file repo; scanner inspects 40 code files)
- [ ] Document collision thresholds in `lambdas/name_collision/handler.py` comments
- [x] Verify `docs/SCORING_RUBRIC.md` documents RED/YELLOW/GREEN thresholds consistent with code
- [ ] Write `tests/integration/test_e2e_pipeline.py` (5 integration tests)
- [ ] Verify live cache hit returns < 2s for all 3 fixtures (requires deployed AWS)
- [ ] `make lint` and `make test` pass at 100%

## Resume checkpoint

The three precomputed demos run without backend access. Python end-to-end simulation and API behavior tests pass locally. Live cache latency and full cloud integration remain unverified.
