# Phase 2 — Core Pipeline: Tasks

## Status: IMPLEMENTED; local checks pass; cloud latency unverified

---

- [ ] Implement `lambdas/orchestrator/handler.py` — Nova Lite classification, UniversalProjectProfile
- [ ] Implement `lambdas/repo_scanner/handler.py` — GitHub tree fetch, Python ast, TS/JS regex, 40-file cap
- [ ] Implement `lambdas/name_collision/handler.py` — Jaro-Winkler, Double Metaphone, asyncio multi-registry
- [ ] Implement `lambdas/landscape_scout/handler.py` — GitHub Search + arXiv, auto-broaden
- [ ] Implement `lambdas/analogy_engine/handler.py` — AOSS hybrid search + local numpy fallback
- [ ] Implement `lambdas/enhancement_citation/handler.py` — Sonnet synthesis + citation verifier + scoring engine
- [ ] Update `cdk/stacks/nyxalens_stack.py` — verify topology is Orchestrator → Parallel(4) → Enhancement
- [ ] Write `tests/unit/test_orchestrator.py`
- [ ] Write `tests/unit/test_repo_scanner.py`
- [ ] Write `tests/unit/test_name_collision.py`
- [ ] Write `tests/unit/test_landscape_scout.py`
- [ ] Write `tests/unit/test_analogy_engine.py`
- [ ] Write `tests/unit/test_enhancement_citation.py`
- [ ] Write `tests/integration/test_e2e_stub.py` — simulates Step Functions payload locally
- [ ] `make lint` → zero errors
- [ ] `make test` → all green
- [ ] End-to-end latency < 15s verified

## Resume checkpoint

All five analytical roles, four parallel discovery lanes, sequential grounded synthesis, deterministic scoring, persistence, and failure handling are implemented. Consolidated unit tests and one mocked Python repository end-to-end test pass. No live AWS execution or latency measurement has been run.
