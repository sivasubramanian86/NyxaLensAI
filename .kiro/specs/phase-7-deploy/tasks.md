# Phase 7 — Production Deployment & Builder Center Article: Tasks

## Status: DOCUMENTATION COMPLETE; production gate pending

- [x] Write `DEPLOYMENT.md` — step-by-step runbook and cost drivers/controls
- [x] Write `docs/BUILDER_CENTER_ARTICLE.md` — article with scope and honest limitations
- [ ] Run `make deploy` in production (us-east-1) — verify all CDK outputs present
- [ ] Run `python data/seed_opensearch.py --mode aoss` — verify all 20 patterns indexed
- [ ] Connect Amplify to GitHub `main` branch with `NEXT_PUBLIC_API_URL`
- [ ] Run end-to-end test with 3 curated repos in production — verify latency < 15s each
- [ ] Verify `GET /badge/{scan_id}` returns valid SVG in production
- [ ] Run `make seed-local` + `make destroy` — verify local fallback still works at $0/mo
- [ ] All Acceptance Criteria in `requirements.md` checked off

## Resume checkpoint

Deployment and article docs match the current CDK stack. CDK synth/deploy, OpenSearch seeding, Amplify connection, production E2E, badge check, and teardown remain pending. CDK CLI and `aws_cdk` are absent in the current environment; no AWS resources were created. The specified Next.js 14 line is unsupported, so production also needs a supported patched frontend version before traffic.
