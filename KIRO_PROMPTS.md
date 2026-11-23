# NyxaLensAI — Complete Phase-Wise Execution Playbook for Kiro IDE

## Workspace checkpoint — 23 Nov 2026

Phases 0–5 are implemented locally; Phase 6 has fixtures, offline demos, validation guards, and mocked end-to-end coverage; Phase 7 documentation is written. Local Python checks, frontend tests/build, and the pattern seeder dry run pass. CDK synthesis, AWS deployment, live cache latency, OpenSearch seeding, and Amplify hosting remain unverified. No cloud resources were created. See `.kiro/specs/phase-0-foundation/tasks.md` through `phase-7-deploy/tasks.md` for phase checkpoints.

The attached scoping and brainstorming PDFs are reference material. Their build-versus-reuse framing informed the RFC examples and article; the executable requirements below remain this playbook's instructions.

> **How to use this file in Kiro:**
> 1. This file is already saved at the root of `nyxalensai/`.
> 2. The workspace is open in Kiro IDE.
> 3. Copy the fenced `text` prompt block for the active phase and paste it into Kiro's Spec panel.
> 4. Review and approve Kiro's generated `requirements.md` (EARS) → `design.md` → `tasks.md`.
> 5. Execute tasks and verify all Acceptance Criteria before advancing to the next phase.

---

## Phase Dependencies

```
Phase 0 (Foundation)
  └──> Phase 1 (Pattern Corpus)
         └──> Phase 2 (Core Pipeline)
                └──> Phase 3 (API + Scoring)
                       └──> Phase 4 (Frontend)
                              └──> Phase 5 (AgentCore)
                                     └──> Phase 6 (Polish)
                                            └──> Phase 7 (Deploy + Article)
```

## Time Estimate

| Phase | Estimated Time |
|---|---|
| Phase 0: Foundation | 2–3 hours |
| Phase 1: Pattern Corpus | 4–6 hours (hand-curating 20 patterns) |
| Phase 2: Core Pipeline | 8–12 hours |
| Phase 3: API + Scoring | 4–6 hours |
| Phase 4: Frontend | 8–12 hours |
| Phase 5: AgentCore | 4–6 hours |
| Phase 6: Polish | 4–6 hours |
| Phase 7: Deploy + Article | 6–8 hours |
| **Total** | **40–60 hours (1–2 weeks part-time)** |

---

## Phase 0: Foundation (Monorepo, Pydantic Contracts, Bedrock & Secrets Wrappers, CDK Skeleton)

### Copy-Paste Prompt for Kiro

```text
Create a spec and implement Phase 0 (Foundation) for NyxaLensAI: a Repo & RFC Architectural
Amplifier built on AWS (Bedrock, Step Functions, Lambda, OpenSearch Serverless, DynamoDB,
Secrets Manager, Amplify, CDK).

Initialize the monorepo with this exact directory layout:

nyxalensai/
├── cdk/
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   └── stacks/
│       └── nyxalens_stack.py
├── lambdas/
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── bedrock_client.py
│   │   └── github_client.py
│   ├── api_router/handler.py
│   ├── orchestrator/handler.py
│   ├── repo_scanner/handler.py
│   ├── name_collision/handler.py
│   ├── landscape_scout/handler.py
│   ├── analogy_engine/handler.py
│   └── enhancement_citation/handler.py
├── data/
│   ├── patterns_20.json
│   └── seed_opensearch.py
├── frontend/
├── tests/
│   ├── unit/
│   └── integration/
├── Makefile
├── .gitignore
├── README.md
└── LICENSE

EARS Requirements:

1. WHEN the developer runs `make bootstrap` or `make test`, THE SYSTEM SHALL install
   Python 3.12 dependencies (aws-cdk-lib, constructs, pydantic>=2.0, boto3, requests,
   httpx, numpy, pytest, ruff) and execute unit tests cleanly.

2. WHEN data passes between any subagent in the pipeline, THE SYSTEM SHALL validate inputs
   and outputs using strict Pydantic v2 models in `lambdas/shared/schemas.py`:
   - `ScanRequest` (accepts repo_url OR rfc_text, optional parent_scan_id, optional
     force_refresh)
   - `UniversalProjectProfile` (scan_id, input_type, project_name, domain_keywords,
     problem_signature, tech_stack, dependencies, core_modules, has_tests, readme_claims)
   - `NameCollisionResult` (traffic_light: Literal["RED","YELLOW","GREEN"], exact_matches,
     fuzzy_matches, phonetic_matches, safe_alternatives, status)
   - `LandscapeResult` (direct_competitors, academic_papers, ecosystem_gaps)
   - `PatternEvidence` (standard, reference_url,
     measurement_status: Literal["ESTIMATED","BENCHMARKED"] = "ESTIMATED")
   - `AnalogyMatch` (pattern_id, source_domain, canonical_mechanism, mechanism,
     mapping_table, expected_lift, anti_pattern_warning, evidence: PatternEvidence,
     similarity_score)
   - `KillKeepInjectItem` (action: Literal["KILL","KEEP","INJECT"], target_component,
     rationale, citation_url)
   - `NyxaScore` (composite: int, clarity: int, landscape_coverage: int, originality: int,
     gap_opportunity: int, enhancement_potential: int, evidence_quality: int,
     deterministic_points: int, rubric_points: int, projected_post_enhancement: int,
     verdict: str)
   - `EnhancementDossier` (scan_id, parent_scan_id, project_profile, name_collision,
     landscape, analogies, kill_keep_inject, ranked_backlog, mermaid_before_after,
     nyxa_score, verified_citations_count, stripped_hallucinations_count, disclaimer)

3. WHEN a Lambda invokes an LLM or embedding model, THE SYSTEM SHALL route calls through
   `lambdas/shared/bedrock_client.py` using the Amazon Bedrock Converse API:
   - amazon.nova-lite-v1:0 for fast classification/extraction
   - anthropic.claude-3-5-sonnet-20241022-v2:0 for synthesis
   - amazon.titan-embed-text-v2:0 for 1024-dim embeddings
   With structured JSON tool-use enforcement and exponential backoff retries.

4. WHEN a Lambda requires GitHub API authentication, THE SYSTEM SHALL retrieve
   nyxalens/github-token from AWS Secrets Manager via
   `lambdas/shared/github_client.py` using @lru_cache(maxsize=1) rather than plaintext
   environment variables.

5. Include a Makefile with targets: bootstrap, lint, test, seed-patterns, deploy, destroy,
   plus a GitHub Actions workflow .github/workflows/ci.yml running ruff and pytest.

Acceptance Criteria:
- `make test` passes with unit tests validating all Pydantic schemas, mocked Bedrock
  Converse responses, and mocked Secrets Manager token caching.
- `cdk synth` succeeds without errors.
```

---

## Phase 1: Cross-Domain Pattern Corpus & Hybrid Vector Indexer

### Copy-Paste Prompt for Kiro

```text
Create a spec and implement Phase 1 (20-Pattern Cross-Domain Ontology & Hybrid Indexer)
for NyxaLensAI.

Requirements:

1. Populate `data/patterns_20.json` with 20 deeply structured canonical engineering
   patterns (4 per domain: Telecom Signaling & Fault Management, Distributed Systems,
   OS Kernels, Control Theory, Operations Research).
   The file already exists at data/patterns_20.json — validate, review, and extend if
   any pattern is missing required fields.

2. Each pattern in `data/patterns_20.json` MUST contain:
   - pattern_id (PAT-001 through PAT-020)
   - source_domain
   - canonical_mechanism (real named algorithm, protocol, or standard — zero vague
     metaphors)
   - problem_signature (state_space, bottleneck_type, failure_mode, consistency_model)
   - trigger_condition (detected_when)
   - transferable_design (mechanism, mapping_table with source_primitive,
     target_repo_module, expected_effect; expected_lift; anti_pattern_warning)
   - evidence (standard, verified accessible reference_url such as ITU-T Q.704, ITU-T
     X.733, IETF RFC 2475, IETF RFC 4960, IETF RFC 8506, and
     measurement_status: "ESTIMATED")

3. Implement `data/seed_opensearch.py` to:
   - Validate all 20 records against the Pydantic AnalogyPattern schema.
   - Generate 1024-dimensional embeddings via Amazon Bedrock amazon.titan-embed-text-v2:0.
   - Support --mode aoss (creates/updates OpenSearch Serverless index systems-patterns-v1
     with k-NN + BM25 hybrid mapping).
   - Support --mode local (writes pre-computed embeddings to
     data/patterns_20_embedded.json for zero-cost local/fallback vector search after
     cdk destroy).
   - Support --dry-run and --force-refresh CLI flags.

Acceptance Criteria:
- Unit tests validate all 20 records in data/patterns_20.json against the Pydantic schema,
  verify every reference_url uses HTTPS, and confirm
  measurement_status == "ESTIMATED".
- `python data/seed_opensearch.py --mode local --dry-run` executes cleanly and passes
  unit tests with mocked Bedrock embeddings.
```

---

## Phase 2: Core 5-Subagent Pipeline & AWS Step Functions Orchestration

### Copy-Paste Prompt for Kiro

```text
Create a spec and implement Phase 2 (5-Subagent Step Functions Pipeline) for NyxaLensAI.

CRITICAL Architecture Topology — do NOT run Enhancement in parallel with Discovery:
  Orchestrator
    → Step Functions Parallel (4 Discovery Lanes simultaneously)
    → Sequential: Enhancement + Citation + Deterministic Scoring
    → Persist to DynamoDB & S3

EARS Requirements:

1. `lambdas/orchestrator/handler.py`:
   - Classify input (GITHUB_URL vs RFC_TEXT), extract candidate project name and technical
     keywords using Bedrock Nova Lite, build UniversalProjectProfile, and update DynamoDB
     status to DISCOVERING (progress: 20%).

2. Parallel Discovery Lanes — all 4 run concurrently inside sfn.Parallel:

   Lane 1 — `lambdas/repo_scanner/handler.py`:
   - Fetch GitHub repository tree (depth=2), README.md, and dependency manifests
     (pyproject.toml, package.json, pom.xml, go.mod, Cargo.toml).
   - Parse Python files using stdlib ast and TypeScript/JS files using import/class regex
     extraction. Cap at 40 salient files, <=4,000 chars each.
   - Detect has_tests, dependencies, core_modules, and readme_claims.
   - Gracefully fall back to RFC_TEXT mode if code_files == 0.

   Lane 2 — `lambdas/name_collision/handler.py`:
   - Normalize project name (stripping -, _, ai, js, py, labs).
   - Compute Jaro-Winkler similarity and Double Metaphone phonetic keys.
   - Query GitHub Search API, PyPI JSON API, and npm Registry concurrently via
     asyncio/httpx.
   - Schmitt-trigger hysteresis thresholds:
       RED  : Jaro-Winkler >= 0.88 OR exact package match
       YELLOW: 0.78 – 0.87
       GREEN : < 0.78
   - Return traffic_light + 3 clear alternative names.
   - Return YELLOW with status PARTIAL_TIMEOUT if an upstream registry rate-limits.

   Lane 3 — `lambdas/landscape_scout/handler.py`:
   - Strip marketing adjectives via Nova Lite into 3 technical search queries.
   - Fetch top 5 GitHub repos (with star counts and README limitations) and top 3 arXiv
     papers via Atom API.
   - Auto-broaden query if fewer than 2 matches return.

   Lane 4 — `lambdas/analogy_engine/handler.py`:
   - Strip all domain nouns into a problem_signature.
   - Embed with Titan Embeddings v2.
   - Query OpenSearch Serverless (systems-patterns-v1).
   - Automatic local fallback: if AOSS_ENDPOINT is unreachable or unset, run exact cosine
     similarity over data/patterns_20_embedded.json (20 vectors × 1024 floats < 160 KB).
   - Drop any analogy scoring < 0.72 similarity.

3. Sequential Synthesis, Grounding & Scoring —
   `lambdas/enhancement_citation/handler.py` (runs AFTER fan-in, NOT in parallel):
   - Single structured-output Bedrock Claude Sonnet call generating:
       * Kill / Keep / Inject matrix
       * Ranked enhancement backlog (max 5 items)
       * Mermaid before/after architecture diagram
         (sanitize parentheses/quotes inside [...] node labels via regex)
       * Rubric sub-scores
   - Deterministic Citation Verifier:
       * Extract every URL/repo/paper from the draft Dossier.
       * Cross-check each against the raw URLs returned by Lanes 1–4.
       * Programmatically strip any unverified URL and increment
         stripped_hallucinations_count.
   - Deterministic Scoring Engine (pure Python, same Lambda, no extra cold start):
       * 40% deterministic signals:
           has_automated_tests      +10
           dependency_dedup_ratio   +10
           verified_citations >= 3  +10
           readme_to_ast_match      +10
           has_mermaid_diff         +5
           name_collision GREEN     +5
       * 60% rubric-anchored LLM sub-scores
       * Cap projected_post_enhancement delta at +12 to +18 points (never inflated leap).
   - Save raw evidence JSON to S3: s3://{EVIDENCE_BUCKET}/{scan_id}.json
   - Write completed EnhancementDossier to DynamoDB
     (status = "COMPLETED", progress = 100).

4. Wire the complete state machine and IAM permissions in
   `cdk/stacks/nyxalens_stack.py` with a 45-second execution timeout.
   Use Step Functions Standard Workflow (not Express) so the live execution graph is
   visible in the AWS Console during judging.

Latency budget:
  Orchestrator              < 1s   (Nova Lite classification)
  Parallel fan-out (all 4)  4–6s   (longest pole: Landscape Scout)
  Enhancement/Citation/Score 6–8s  (Claude Sonnet synthesis)
  DynamoDB write             < 0.5s
  TOTAL                      11–14s (well under API Gateway 29s limit)

Acceptance Criteria:
- Unit tests cover all 5 subagent handlers, Mermaid label sanitization, deterministic
  citation stripping, and local vector fallback.
- Integration test simulates an end-to-end Step Functions execution payload for a sample
  Python/TS repo and validates the resulting EnhancementDossier.
- Measured latency < 15s on a typical public Python or TypeScript repo.
```

---

## Phase 3: REST API, Caching, Re-Scan Delta & Dynamic README SVG Badge

### Copy-Paste Prompt for Kiro

```text
Create a spec and implement Phase 3 (API Gateway REST Router, SHA-256 Caching, Re-Scan
Delta, and SVG Badge Generator) for NyxaLensAI.

EARS Requirements:

1. Implement `lambdas/api_router/handler.py` handling three REST routes:

   POST /scans:
   - Validate ScanRequest (repo_url or rfc_text).
   - Compute deterministic cache key: sha256(normalized_input + commit_sha).
   - If a COMPLETED scan exists in DynamoDB within the last 24 hours AND force_refresh
     is false → return 200 OK immediately with cached scan_id (< 2s repeat demo latency).
   - Otherwise: write an INITIALIZED record to DynamoDB (preserving parent_scan_id if
     provided), invoke stepfunctions:StartExecution, return 202 Accepted with
     {"scan_id": scan_id, "status": "INITIALIZED"}.

   GET /scans/{scan_id}:
   - Fetch item from DynamoDB.
   - Return current status, stage, progress, completed subagent flags, and dossier.
   - Include score_delta if parent_scan_id exists.
   - Return 404 if not found.

   GET /badge/{scan_id}:
   - Fetch nyxa_score.composite and name_collision.traffic_light from DynamoDB.
   - Return a crisp shields-style image/svg+xml badge:
       "Nyxa Score | 79/100"  (green fill for >= 70, amber for 50–69, red for < 50)
   - Cache-Control: max-age=300.

2. Store GITHUB_TOKEN in AWS Secrets Manager (secret name: nyxalens/github-token).
   Pass secret ARN to relevant Lambdas via environment variable GITHUB_SECRET_ARN.
   Grant secretsmanager:GetSecretValue only to repo_scanner, name_collision, and
   landscape_scout Lambdas (least-privilege IAM).

3. Wire POST /scans, GET /scans/{scan_id}, and GET /badge/{scan_id} with CORS enabled
   in cdk/stacks/nyxalens_stack.py.

Acceptance Criteria:
- Unit tests verify: cache hits (200), cache misses (202 + Step Functions start),
  parent_scan_id score delta calculation, and valid XML structure for GET /badge/{scan_id}.
- GITHUB_TOKEN is never stored in plaintext env vars or CloudFormation templates.
```

---

## Phase 4: Next.js 14 Frontend & AWS Amplify Hosting

### Copy-Paste Prompt for Kiro

```text
Create a spec and implement Phase 4 (Next.js 14 App Router Frontend for AWS Amplify)
inside `frontend/`.

EARS Requirements:

1. Build a responsive dark-mode developer UI with:
   - Background: #0B0F19 (obsidian/midnight-indigo)
   - Accent: #38BDF8 (bioluminescent cyan) for verified signals and unique moats
   - Collision indicators: amber (#F59E0B) for YELLOW, crimson (#EF4444) for RED
   - Code/AST/diff blocks: JetBrains Mono monospace
   - Component library: Shadcn UI

2. Page 1 — `src/app/page.tsx`:

   ScanInputForm:
   - Tabs for "GitHub Repo URL" and "Markdown RFC / Idea".
   - Optional force_refresh toggle.
   - Three one-click "Try Curated Demo" preset buttons (pre-loaded repo URLs).

   LivePollingStatus:
   - Polls GET ${NEXT_PUBLIC_API_URL}/scans/{scanId} every 1500ms until COMPLETED or
     FAILED.
   - Displays real-time subagent progress badges:
       [✓] Repo AST
       [✓] Name Collision
       [✓] Ecosystem Scout
       [✓] Systems Ontology
       [⚡] Grounded Synthesis

3. Page 2 — `src/app/dossier/[scanId]/page.tsx`:

   TrafficLight:
   - RED / YELLOW / GREEN name collision banner.
   - Shows GitHub/PyPI/npm matches and 3 safe alternative names.

   NyxaScoreCard:
   - Composite 0–100 score + projected post-enhancement score (e.g. 64 → 79).
   - 6-dimension breakdown bars.
   - Deterministic vs rubric split.
   - Collapsible Citation Verification drawer.

   KillKeepInjectMatrix:
   - 3-column architectural triage table (KILL commodity bloat / KEEP unique moat /
     INJECT cross-domain pattern).
   - Clickable verified URLs.

   AnalogyCard:
   - Matched cross-domain pattern, canonical standard.
   - Component mapping table (source_primitive → target_repo_module).
   - Anti-pattern warning.
   - Explicit disclaimer: "Architectural lift projections are domain-derived estimates,
     not empirical repo benchmarks."

   MermaidDiagram:
   - Renders mermaid_before_after.
   - Wrapped in a React Error Boundary that falls back to formatted Mermaid source text
     if mermaid.js fails to parse.

   EnhancementBacklog:
   - Ranked improvement checklist (max 5 items) with effort/impact tags.

   ReScanButton:
   - Submits parent_scan_id + force_refresh: true.
   - Renders score_delta badge on completion (e.g. "+15 points").

   BadgeSnippet:
   - Copy-pasteable Markdown: ![Nyxa Score](${API_URL}/badge/${scanId})

4. Add `amplify.yml` build specification at the repository root configured for the
   `frontend` monorepo app root (appRoot: frontend).

5. Amplify frontend polls GET /scans/{scan_id} — no WebSocket needed.
   Clicking "Scan" sends POST /scans (returns 202 + scan_id in < 150ms), then triggers
   a useEffect polling loop every 1500ms until status === "COMPLETED".

Acceptance Criteria:
- npm run build succeeds inside frontend/.
- Jest + React Testing Library unit tests pass for: polling state transitions,
  TrafficLight rendering (all 3 states), Mermaid error boundary fallback, and Re-Scan
  score delta display.
- Amplify deploys successfully from the GitHub main branch.
```

---

## Phase 5: Amazon Bedrock AgentCore Memory & Pipeline Observability

### Copy-Paste Prompt for Kiro

```text
Create a spec and implement Phase 5 (Amazon Bedrock AgentCore Memory & Observability)
for NyxaLensAI.

EARS Requirements:

1. Implement `lambdas/shared/memory_client.py` with a clean SessionMemoryProvider
   abstraction:
   - Inspect the installed boto3 service models:
       botocore.session.get_service_model('bedrock-agentcore')
   - Bind native AgentCore Memory read/write calls when available in the target region.
   - Fall back automatically to a DynamoDB NyxaSessionMemory table when AgentCore is
     unavailable (cross-region, local, or pre-GA).
   - Store per-session/builder scan summaries:
       scan_id, project_name, tech_stack, matched_pattern_ids, nyxa_score, timestamp
   - Retrieve up to 3 prior relevant scans and pass them into
     enhancement_citation/handler.py as context so recommendations adapt across
     iterations.

2. Implement `lambdas/shared/telemetry.py`:
   - Record per-subagent: execution duration (ms), model ID used, input/output token
     counts, estimated USD cost, citation verification count.
   - Emit as structured CloudWatch EMF logs and AWS X-Ray subsegments.
   - Attach a pipeline_trace object to the EnhancementDossier.

3. Add a "Pipeline Trace" tab in
   `frontend/src/app/dossier/[scanId]/page.tsx`:
   - Per-subagent latency waterfall bars.
   - Model routing (Nova Lite vs Claude Sonnet).
   - Token usage and estimated cost.
   - Stripped hallucination count.

Acceptance Criteria:
- Unit tests verify both AgentCore Memory read/write AND DynamoDB fallback behavior.
- EMF telemetry formatting produces valid CloudWatch embedded metrics.
- Frontend Pipeline Trace tab renders all fields from the pipeline_trace object.
```

---

## Phase 6: Demo Hardening, README Badge Polish & End-to-End Verification

### Copy-Paste Prompt for Kiro

```text
Create a spec and implement Phase 6 (Demo Hardening & End-to-End Verification Suite)
for NyxaLensAI.

EARS Requirements:

1. Pre-warm and verify 3 curated demo fixtures in `tests/fixtures/`:
   - Fixture A: A Python multi-agent repo with a known weakness (e.g. unbounded retry
     loops, no test coverage) so the Dossier demonstrates real value — not a cherry-picked
     perfect repo.
   - Fixture B: A TypeScript/Next.js AI app.
   - Fixture C: A Markdown architecture RFC.
   Cache results in DynamoDB so Demo Mode returns in < 2s with no live API calls.

2. Document the RED/YELLOW/GREEN name collision Schmitt-trigger thresholds
   (0.88 / 0.78) explicitly in:
   - lambdas/name_collision/handler.py (code comments)
   - docs/SCORING_RUBRIC.md (so judges can audit the logic)

3. Harden edge cases across all handlers:
   - Invalid or private GitHub URLs → clear 400/422 user-facing validation errors,
     no Step Functions invocation.
   - Monorepos (> 500 files) → cap AST inspection at 40 files cleanly without exceeding
     Lambda memory or timeout limits.
   - Mermaid syntax anomalies → caught and sanitized before DynamoDB persistence.

4. Implement `tests/integration/test_e2e_pipeline.py` verifying:
   - Repo URL scan → Dossier generation → Nyxa Score rubric bounds (0 <= score <= 100).
   - RFC text scan → calibration mode shift → Analogy pattern grounding.
   - Re-scan with parent_scan_id → positive score_delta computation.
   - GET /badge/{scan_id} → valid image/svg+xml response.
   - Cache hit path → 200 response in < 2s.

Acceptance Criteria:
- `make lint` and `make test` pass at 100% across unit and integration suites.
- All 3 demo fixtures return a complete Dossier in < 2s (from cache).
```

---

## Phase 7: Production Deployment, Cost Audit & AWS Builder Center Article

### Copy-Paste Prompt for Kiro

```text
Create a spec and execute Phase 7 (Production Deployment Runbook & AWS Builder Center
Technical Article) for NyxaLensAI.

EARS Requirements:

1. Generate `DEPLOYMENT.md` with step-by-step commands for:
   a. Pre-flight: Create nyxalens/github-token in AWS Secrets Manager:
        aws secretsmanager create-secret \
          --name nyxalens/github-token \
          --secret-string "ghp_YOUR_TOKEN"
   b. Run `make deploy` (cdk deploy) and capture ApiEndpointUrl and
      OpenSearchEndpoint from CloudFormation outputs.
   c. Seed patterns:
        python data/seed_opensearch.py --mode aoss
   d. Document the $0/mo teardown path:
        python data/seed_opensearch.py --mode local   # pre-compute local embeddings
        make destroy                                   # eliminates ~$350/mo AOSS OCU cost
        # App continues to work via local numpy fallback
   e. Connect the GitHub repository to AWS Amplify Hosting with NEXT_PUBLIC_API_URL
      set to the CDK ApiEndpointUrl output.
   f. Cost estimate table:
        Step Functions Standard  ~$0.025 per 1,000 state transitions
        Lambda (6 functions)     ~$0.0000002 per request
        Bedrock Nova Lite        ~$0.00006 per 1K input tokens
        Bedrock Claude Sonnet    ~$0.003 per 1K input tokens
        DynamoDB on-demand       ~$0.00 (free tier covers demo volume)
        AOSS                     ~$350/mo minimum OCU (destroy after demo filming)
        Amplify Hosting          ~$0.01 per build minute

2. Generate `docs/BUILDER_CENTER_ARTICLE.md` — publication-ready technical deep-dive:
   Title: "Building NyxaLensAI: Parallel Multi-Agent RAG & Cross-Domain Architectural
           Amplification with AWS Step Functions, Bedrock, OpenSearch Serverless,
           and Amplify"
   Structure:
   a. HONEST LIMITATIONS FIRST (builds credibility):
      - Lift estimates are architectural projections, not empirical benchmarks.
      - Single AWS region deployment (us-east-1 by default).
      - Public GitHub repositories only (private repo OAuth is v2).
      - 20 canonical patterns cover common AI/agentic bottlenecks; exotic domains
        may return no analogy (similarity < 0.72, correctly suppressed).
   b. Problem framing: the duplicate-build cost problem.
   c. Mermaid system architecture diagram (full 5-subagent topology).
   d. 5-subagent parallel fan-out rationale and latency budget.
   e. 20-pattern cross-domain ontology — 3 fully worked examples with mapping tables.
   f. Deterministic + rubric Nyxa Score formula (the 40/60 split).
   g. Hallucination-stripping Citation Verifier — how it works in code.
   h. FinOps strategy: Nova Lite for extraction, Sonnet for synthesis, local fallback
      for AOSS after demo.
   i. Demo walkthrough with the 2-minute script.
   j. Future roadmap: private repos, multimodal input, weekly drift radar.

Acceptance Criteria:
- DEPLOYMENT.md covers all steps end-to-end with no placeholder credentials.
- docs/BUILDER_CENTER_ARTICLE.md is complete, opens with honest limitations, and
  includes all required sections.
- `make deploy` succeeds in a clean AWS account (us-east-1).
- End-to-end test with 3 real repos passes in production (latency < 15s each).
```

---

## Kiro Best Practices

1. **Write specs, not code.** Let Kiro generate `requirements.md`, `design.md`, `tasks.md`
   from your prompt — then execute tasks.
2. **Use EARS format.** Kiro understands EARS (Easy Approach to Requirements Syntax)
   natively. These prompts already use it.
3. **Review specs before executing.** Kiro generates a design and task list — review
   them before letting it write code.
4. **Run tests after each phase.** Kiro runs tests automatically; verify acceptance
   criteria before moving on.
5. **Iterate on failures.** If a phase fails acceptance, refine the prompt and re-run —
   Kiro updates the spec and re-executes.

---

## Three Final Polish Notes (non-blocking)

1. **Phase 2 Schmitt-trigger thresholds** — The RED (0.88) / YELLOW (0.78) thresholds
   are documented in the Phase 2 prompt. Phase 6 adds them to `docs/SCORING_RUBRIC.md`
   so judges can audit the name collision logic without reading code.

2. **Phase 6 demo fixtures** — Fixture A is explicitly a repo with a known weakness
   (unbounded retry loop, no test coverage) so the Dossier demonstrates real diagnostic
   value — not a cherry-picked easy case.

3. **Phase 7 article** — The article structure above leads with honest limitations
   before the "wow" features, building technical credibility with senior judges and
   AWS Builder Center readers.

---

*One-line reminder for Kiro:*

> "Build NyxaLensAI: a Repo Architectural Amplifier with 5 subagents (4 parallel
> discovery + 1 sequential Enhancement/Citation/Scoring), a 20-pattern cross-domain
> ontology, a 6-dimension citation-backed Nyxa Score, and a name collision traffic
> light — deployed on AWS Amplify, Step Functions, Bedrock, OpenSearch Serverless,
> and AgentCore Memory/Observability."
