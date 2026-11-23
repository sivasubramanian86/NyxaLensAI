# Phase 5 — AgentCore Memory & Observability: Tasks

## Status: IMPLEMENTED; mocked native/fallback and telemetry checks pass

- [ ] Implement `lambdas/shared/memory_client.py` — SessionMemoryProvider with AgentCore + DynamoDB fallback
- [ ] Implement `lambdas/shared/telemetry.py` — EMF + X-Ray per-subagent traces
- [ ] Update `lambdas/enhancement_citation/handler.py` — pass prior scan context from memory
- [ ] Update `cdk/stacks/nyxalens_stack.py` — add NyxaSessionMemory DynamoDB table + X-Ray tracing
- [ ] Add Pipeline Trace tab to `frontend/src/app/dossier/[scanId]/page.tsx`
- [x] Write `tests/unit/test_memory_telemetry.py` — AgentCore native + DynamoDB fallback + EMF checks
- [ ] `make lint` and `make test` pass

## Resume checkpoint

Memory provider, DynamoDB fallback, EMF/X-Ray telemetry, prior-scan retrieval, and the frontend trace tab are implemented. Current checks ran directly with Python/ruff/npm; Makefile virtualenv targets were not run.
