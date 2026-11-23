# Phase 6 — Demo Hardening, Polish & End-to-End Verification: Requirements

## Status: PENDING (start after Phase 5 acceptance gate passes)

---

## Functional Requirements

### FR-1: 3 Curated Demo Fixtures (`tests/fixtures/`)
- Fixture A: Python multi-agent repo with known weakness (unbounded retry loop, no test coverage)
  — demonstrates real diagnostic value, not cherry-picked
- Fixture B: TypeScript/Next.js AI app
- Fixture C: Markdown architecture RFC
- Pre-cached Dossier JSON for each in `tests/fixtures/<name>/dossier.json`
- Demo Mode returns cached result in < 2s (DynamoDB cache hit)

### FR-2: Scoring Rubric Documentation
- Document RED (≥ 0.88) / YELLOW (0.78–0.87) / GREEN (< 0.78) thresholds in `docs/SCORING_RUBRIC.md`
- Document both thresholds in `lambdas/name_collision/handler.py` as inline comments

### FR-3: Edge Case Hardening
- Invalid or private GitHub URL → 400/422, no Step Functions invocation
- Monorepo (> 500 files) → cap at 40 files, no OOM, no timeout
- Mermaid syntax errors → sanitised before DynamoDB write, never shown as red error box

### FR-4: End-to-End Test Suite (`tests/integration/test_e2e_pipeline.py`)
- Repo URL → Dossier → `0 <= composite <= 100`
- RFC text → calibration mode shift → analogy grounding
- Re-scan with `parent_scan_id` → positive `score_delta`
- `GET /badge/{scan_id}` → valid `image/svg+xml`
- Cache hit → 200 in < 2s

### FR-5: Performance
- Repeat demo (cache hit) returns in < 2s
- DynamoDB cache key: `sha256(normalized_input + commit_sha)` with `force_refresh` override

---

## Acceptance Criteria

- [ ] All 3 demo fixtures return Dossier in < 2s (from cache)
- [ ] RED/YELLOW/GREEN thresholds documented in both `SCORING_RUBRIC.md` and handler comments
- [ ] Invalid URL returns 400/422 without triggering Step Functions
- [ ] Monorepo test repo (> 500 files) scans without Lambda OOM or timeout
- [ ] All integration tests in `test_e2e_pipeline.py` pass
- [ ] `make lint` and `make test` pass at 100%
