# Phase 3 — REST API, Caching, Re-Scan Delta & SVG Badge: Tasks

## Status: IMPLEMENTED; API unit checks pass

- [ ] Implement full `lambdas/api_router/handler.py` (POST /scans, GET /scans/{id}, GET /badge/{id})
- [ ] Implement SHA-256 cache key logic and 24h DynamoDB TTL
- [ ] Implement `score_delta` calculation using `parent_scan_id`
- [ ] Implement SVG badge generator (25 lines, color-coded by score range)
- [ ] Add Secrets Manager CDK wiring (grant read to 3 Lambdas only)
- [ ] Write `tests/unit/test_api_router.py` — cache hit/miss, badge SVG validity, score delta
- [ ] `make lint` and `make test` pass

## Resume checkpoint

POST/GET/badge routes, 24-hour SHA-256 cache lookup, parent score delta, and XML-parsable SVG are covered by mocked API tests. No live API Gateway test has been run.
