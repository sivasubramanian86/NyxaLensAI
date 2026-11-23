# Phase 6 — Demo Hardening & Polish: Design

## Status: PENDING

Key decisions (locked):
- Fixture A must have a real known weakness — use a real open-source repo, not a fabricated one
- Cache hit path: `api_router` checks DynamoDB before starting Step Functions
- Monorepo cap: `repo_scanner` stops at 40 files, prioritising manifests then entry points
- Mermaid sanitisation already implemented in `enhancement_citation` — Phase 6 adds the integration test
