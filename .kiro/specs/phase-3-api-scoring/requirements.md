# Phase 3 — REST API, Caching, Re-Scan Delta & SVG Badge: Requirements

## Status: PENDING (start after Phase 2 acceptance gate passes)

---

## Functional Requirements

### FR-1: POST /scans
- Validate `ScanRequest` (repo_url or rfc_text required)
- Compute cache key: `sha256(normalized_input + commit_sha)`
- Cache hit (COMPLETED within 24h, `force_refresh=False`) → return 200 with cached `scan_id`
- Cache miss → write INITIALIZED to DynamoDB, start Step Functions, return 202 + `scan_id`
- Preserve `parent_scan_id` for re-scan delta

### FR-2: GET /scans/{scan_id}
- Read from DynamoDB, return `status`, `stage`, `progress`, `dossier`
- Include `score_delta` if `parent_scan_id` exists
- Return 404 if not found

### FR-3: GET /badge/{scan_id}
- Return `image/svg+xml` shields-style badge: `Nyxa Score | 79/100`
- Color: brightgreen ≥ 70, amber 50–69, red < 50
- `Cache-Control: max-age=300`
- 25-line Lambda — no Bedrock call

### FR-4: GitHub Token in Secrets Manager
- `GITHUB_SECRET_ARN` passed to 3 Lambdas only (repo_scanner, name_collision, landscape_scout)
- Never in plaintext env vars

### FR-5: Scoring Engine deterministic signals
- `has_automated_tests` +10
- `dependency_dedup_ratio` +10
- `verified_citations_count >= 3` +10
- `readme_to_ast_claim_match` +10
- `has_mermaid_diff` +5
- `name_collision_status == GREEN` +5

---

## Acceptance Criteria

- [ ] `POST /scans` returns 202 + `scan_id` (cache miss)
- [ ] `POST /scans` returns 200 + cached `scan_id` (cache hit, same input within 24h)
- [ ] `GET /scans/{scan_id}` returns status + partial/full dossier
- [ ] `GET /badge/{scan_id}` returns valid `image/svg+xml`
- [ ] `score_delta` computed correctly on re-scan with `parent_scan_id`
- [ ] `GITHUB_TOKEN` stored in Secrets Manager, never in plaintext
- [ ] `make lint` and `make test` pass
