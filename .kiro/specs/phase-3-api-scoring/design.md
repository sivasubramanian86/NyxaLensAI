# Phase 3 — REST API, Caching, Re-Scan Delta & SVG Badge: Design

## Status: PENDING

Key decisions (locked):
- Cache key: `sha256(normalized_input + commit_sha)` stored in DynamoDB `cache_key` attribute
- DynamoDB TTL: 24 hours for COMPLETED scans; 1 hour for FAILED/INITIALIZED
- Badge Lambda: returns `image/svg+xml` directly — no HTML wrapper
- Score delta: `score_delta = new_scan.composite - parent_scan.composite`
- Scoring Engine is pure Python inside Enhancement Lambda — no extra Lambda hop
