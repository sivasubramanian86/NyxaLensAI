# Phase 2 — Core Pipeline: Requirements

## Status: PENDING (start after Phase 1 acceptance gate passes)

---

## Summary

Build the 5-subagent Step Functions pipeline:

```
Orchestrator (Nova Lite)
  → Parallel [Repo Scanner | Name Collision | Landscape Scout | Analogy Engine]
  → Sequential: Enhancement + Citation + Deterministic Scoring
  → DynamoDB write (COMPLETED) + S3 evidence snapshot
```

Total target latency: **11–14 seconds** end-to-end.

---

## Functional Requirements

### FR-1: Orchestrator Lambda (`lambdas/orchestrator/handler.py`)
WHEN invoked with a `ScanRequest`, THE SYSTEM SHALL:
- Classify `input_type` as `GITHUB_URL` or `RFC_TEXT` using Nova Lite
- Extract `project_name` and `domain_keywords` from the input
- Build a `ProblemSignature` (state_space, bottleneck_type, failure_mode, consistency_model)
- Construct and return a valid `UniversalProjectProfile`
- Write `status=DISCOVERING`, `progress=20` to DynamoDB atomically

### FR-2: Repo Scanner Lambda (`lambdas/repo_scanner/handler.py`)
WHEN invoked with a `UniversalProjectProfile`, THE SYSTEM SHALL:
- Fetch the GitHub repo tree at depth=2 via `github_client.get_repo_tree()`
- Fetch `README.md` and all manifest files (`pyproject.toml`, `package.json`, `pom.xml`, `go.mod`, `Cargo.toml`)
- Select up to 40 salient files prioritised by: manifests → entry points (`main.py`, `app.py`, `index.ts`) → `src/` files
- Parse `.py` files using stdlib `ast` to extract: imported modules, class names, function names
- Parse `.ts`/`.js`/`.tsx` files using regex to extract: `import` statements, exported class/function names
- Detect `has_tests` (True if `tests/` directory or `test_*.py` files exist)
- Populate `tech_stack`, `dependencies`, `core_modules`, `readme_claims`, `dependency_count`, `code_files_scanned`
- If `code_files_scanned == 0`, set `input_type = RFC_TEXT` and continue gracefully
- Cap total Lambda execution at 10 seconds; return shallow profile if tree fetch exceeds limit

### FR-3: Name Collision Lambda (`lambdas/name_collision/handler.py`)
WHEN invoked with a `project_name`, THE SYSTEM SHALL:
- Normalise the name: lowercase, strip suffixes (`-ai`, `-js`, `-py`, `_ai`, `labs`, `hq`)
- Compute Jaro-Winkler similarity against top 50k GitHub repo names
- Apply Double Metaphone phonetic encoding to detect homophones
- Query GitHub Search API, PyPI JSON API (`https://pypi.org/pypi/{name}/json`), and npm Registry (`https://registry.npmjs.org/{name}`) concurrently via `asyncio`/`httpx`
- Apply Schmitt-trigger hysteresis thresholds (PAT-017):
  - RED: Jaro-Winkler ≥ 0.88 OR exact match on any registry
  - YELLOW: 0.78–0.87 OR phonetic match in same technical domain
  - GREEN: < 0.78 with no phonetic collision
- Return `NameCollisionResult` with `traffic_light`, matches, and 3 `safe_alternatives`
- Return `YELLOW` with `status=PARTIAL_TIMEOUT` if any registry call times out

### FR-4: Landscape Scout Lambda (`lambdas/landscape_scout/handler.py`)
WHEN invoked with a `UniversalProjectProfile`, THE SYSTEM SHALL:
- Use Nova Lite to strip marketing adjectives from `domain_keywords`, producing 3 technical search queries
- Query GitHub Search API for top 5 repos per query (sorted by stars), deduplicating results
- Query arXiv Atom API (`https://export.arxiv.org/api/query`) for top 3 papers using formal problem terminology
- Fetch `README.md` Limitations/Known Issues sections from the top 3 GitHub competitors
- Auto-broaden query (remove version/framework constraints) if fewer than 2 results return
- Return `LandscapeResult` with `direct_competitors`, `academic_papers`, `ecosystem_gaps`

### FR-5: Analogy Engine Lambda (`lambdas/analogy_engine/handler.py`)
WHEN invoked with a `UniversalProjectProfile`, THE SYSTEM SHALL:
- Strip all domain nouns from `problem_signature` using Nova Lite, producing a domain-agnostic query string
- Call `bedrock_client.embed()` to generate a 1024-dim Titan v2 vector of the stripped query
- If `AOSS_ENDPOINT` is set: run hybrid BM25 + k-NN query against `systems-patterns-v1` index
- If `AOSS_ENDPOINT` is unset: load `data/patterns_20_embedded.json` and compute numpy cosine similarity
- Return 1–3 `AnalogyMatch` objects with `similarity_score ≥ 0.72`; return empty list if none qualify
- Each `AnalogyMatch` must include the full `mapping_table` and `PatternEvidence` with `measurement_status="ESTIMATED"`

### FR-6: Enhancement + Citation + Scoring Lambda (`lambdas/enhancement_citation/handler.py`)
WHEN invoked with the fan-in result (all 4 discovery payloads), THE SYSTEM SHALL:

**Synthesis (Claude Sonnet):**
- Build a single structured-output Bedrock Converse call with a strict tool-use schema
- Generate: `kill_keep_inject` list (max 10 items), `ranked_backlog` (max 5 items), `mermaid_before_after` string
- Sanitise Mermaid: strip `()` and `"` inside `[...]` node labels via regex before saving

**Citation Verification (deterministic Python):**
- Extract every URL, GitHub repo path, and arXiv paper ID from the draft Dossier JSON
- Cross-check each against the raw payloads from all 4 discovery lanes
- Strip any citation not present in a raw payload; increment `stripped_hallucinations_count`
- Target: `stripped_hallucinations_count == 0` (zero unsourced claims rendered)

**Scoring Engine (pure Python, no LLM):**
- Compute `S_deterministic` (0–40 pts) from: `has_tests`, `dependency_dedup_ratio`, `verified_citations_count >= 3`, `readme_to_ast_claim_match`, `has_mermaid_diff`, `name_collision_status == GREEN`
- Compute `S_rubric` (0–60 pts) from Claude Sonnet sub-scores: Clarity 15%, Landscape Coverage 15%, Originality 25%, Gap Opportunity 15%, Enhancement Potential 20%, Evidence Quality 10%
- `composite = S_deterministic + S_rubric`
- `projected_post_enhancement = min(composite + delta, 100)` where `delta` is clamped to 12–18

**Persistence:**
- Write raw evidence JSON to `s3://{EVIDENCE_BUCKET}/{scan_id}.json`
- Write completed `EnhancementDossier` to DynamoDB: `status=COMPLETED`, `progress=100`

### FR-7: Step Functions Wiring
THE SYSTEM SHALL update `cdk/stacks/nyxalens_stack.py` to wire the exact topology:
Orchestrator → Parallel(Repo Scanner, Name Collision, Landscape Scout, Analogy Engine) → Enhancement + Citation + Scoring → (DynamoDB persist is inside the Enhancement Lambda, not a separate state)

---

## Latency Budget

| Stage | Target | Notes |
|---|---|---|
| Orchestrator | < 1s | Nova Lite classification |
| Parallel fan-out (all 4) | 4–6s | Longest pole: Landscape Scout |
| Enhancement/Citation/Scoring | 6–8s | Claude Sonnet synthesis |
| DynamoDB write (inside Enhancement) | < 0.5s | Included in above |
| **Total** | **11–14s** | Well under API Gateway 29s limit |

---

## Acceptance Criteria

- [ ] Step Functions state machine deploys successfully (`cdk deploy`)
- [ ] End-to-end test with a real public Python repo returns a valid `EnhancementDossier`
- [ ] All 5 Lambda handlers have unit tests with mocked Bedrock/API calls
- [ ] `stripped_hallucinations_count == 0` for a known-clean test fixture
- [ ] Measured end-to-end latency < 15s on a typical repo
- [ ] `NyxaScore.projected_post_enhancement - NyxaScore.composite` is between 12 and 18
- [ ] `make lint` and `make test` pass
