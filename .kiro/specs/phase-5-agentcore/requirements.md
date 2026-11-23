# Phase 5 — AgentCore Memory & Observability: Requirements

## Status: PENDING (start after Phase 4 acceptance gate passes)

---

## Functional Requirements

### FR-1: AgentCore Memory (`lambdas/shared/memory_client.py`)
- `SessionMemoryProvider` abstraction with native AgentCore + DynamoDB fallback
- Inspect `botocore.session.get_service_model('bedrock-agentcore')` before binding
- Store per-session: `scan_id`, `project_name`, `tech_stack`, `matched_pattern_ids`, `nyxa_score`, `timestamp`
- Retrieve up to 3 prior relevant scans for Enhancement Lambda context
- DynamoDB fallback table: `NyxaSessionMemory` (auto-created if AgentCore unavailable)

### FR-2: Pipeline Telemetry (`lambdas/shared/telemetry.py`)
- Record per-subagent: duration_ms, model_id, input_tokens, output_tokens, estimated_usd, citations_verified, citations_stripped
- Emit as CloudWatch EMF structured logs + X-Ray subsegments
- Attach `pipeline_trace: list[PipelineTrace]` to `EnhancementDossier`

### FR-3: Pipeline Trace UI Tab
- Add "Pipeline Trace" tab to `dossier/[scanId]/page.tsx`
- Show latency waterfall, model routing, token usage, stripped hallucination count

---

## Acceptance Criteria

- [ ] AgentCore Memory stores and retrieves scan history (native or DynamoDB fallback)
- [ ] DynamoDB fallback works when AgentCore service model unavailable
- [ ] EMF telemetry produces valid CloudWatch embedded metrics format
- [ ] Pipeline Trace tab renders in frontend
- [ ] Unit tests cover memory read/write and both code paths (AgentCore + fallback)
- [ ] `make lint` and `make test` pass
