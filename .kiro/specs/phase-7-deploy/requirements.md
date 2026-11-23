# Phase 7 — Production Deployment, Cost Audit & Builder Center Article: Requirements

## Status: PENDING (start after Phase 6 acceptance gate passes)

---

## Functional Requirements

### FR-1: DEPLOYMENT.md
Step-by-step runbook covering:
- Create `nyxalens/github-token` in Secrets Manager
- `make deploy` → capture `ApiEndpointUrl` and `OpenSearchEndpoint` from outputs
- `python data/seed_opensearch.py --mode aoss`
- Connect GitHub repo to Amplify with `NEXT_PUBLIC_API_URL`
- Cost estimate table (Step Functions, Lambda, Bedrock, DynamoDB, AOSS, Amplify)
- `make seed-local` + `make destroy` teardown path ($0/mo post-demo)

### FR-2: docs/BUILDER_CENTER_ARTICLE.md
Publication-ready article titled:
*"Building NyxaLensAI: Parallel Multi-Agent RAG & Cross-Domain Architectural Amplification with AWS Step Functions, Bedrock, OpenSearch Serverless, and Amplify"*

Structure (honest limitations FIRST):
1. Honest limitations (estimated lifts, public repos only, single region)
2. Problem framing
3. Mermaid system architecture diagram
4. 5-subagent parallel fan-out rationale + latency budget
5. 3 fully worked cross-domain analogy examples with mapping tables
6. Deterministic + rubric Nyxa Score formula (40/60 split)
7. Citation Verifier — how hallucination stripping works
8. FinOps strategy (Nova Lite + Sonnet + local fallback)
9. 2-minute demo walkthrough
10. Future roadmap

### FR-3: Production Validation
- `cdk deploy` succeeds in a clean account (us-east-1)
- End-to-end test with 3 real repos passes (latency < 15s each)
- `GET /badge/{scan_id}` returns valid SVG in production

---

## Acceptance Criteria

- [ ] `DEPLOYMENT.md` complete, accurate, no placeholder credentials
- [ ] `docs/BUILDER_CENTER_ARTICLE.md` complete, opens with honest limitations
- [ ] `make deploy` succeeds in production
- [ ] All 3 curated demo repos return valid Dossier in production (< 15s)
- [ ] README Nyxa Score badge renders correctly from production endpoint
