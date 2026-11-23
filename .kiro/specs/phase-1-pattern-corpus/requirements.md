# Phase 1 — Pattern Corpus & Hybrid Vector Indexer: Requirements

## Status: IN PROGRESS 🔄

---

## Context

The 20-pattern cross-domain corpus in `data/patterns_20.json` is the product's core moat.
Phase 1 has two goals:
1. Validate and harden the existing `patterns_20.json` against the full schema.
2. Implement `data/seed_opensearch.py` so the corpus can be indexed into Amazon OpenSearch
   Serverless (live demo) or pre-computed as a local numpy fallback (post-demo, $0/mo).

The analogy engine (Phase 2, Lane 4) depends entirely on what this phase produces.

---

## Functional Requirements

### FR-1: Pattern Schema Compliance
WHEN `data/patterns_20.json` is loaded, THE SYSTEM SHALL validate every record against
the `AnalogPattern` Pydantic schema defined in `data/seed_opensearch.py`. Each record MUST
contain all of the following fields with no empty strings:

| Field | Type | Constraint |
|---|---|---|
| `pattern_id` | str | Format `PAT-001` through `PAT-020`, unique |
| `source_domain` | str | Non-empty; must span 5 required domains (see FR-2) |
| `canonical_mechanism` | str | Named real algorithm/protocol/standard — no vague metaphors |
| `problem_signature.state_space` | str | Non-empty |
| `problem_signature.bottleneck_type` | str | Non-empty |
| `problem_signature.failure_mode` | str | Non-empty |
| `problem_signature.consistency_model` | str | Non-empty |
| `trigger_condition.detected_when` | str | Non-empty |
| `transferable_design.mechanism` | str | Non-empty |
| `transferable_design.mapping_table` | list | ≥ 1 entry; each entry has `source_primitive`, `target_repo_module`, `expected_effect` |
| `transferable_design.expected_lift` | str | Non-empty |
| `transferable_design.anti_pattern_warning` | str | ≥ 10 characters |
| `evidence.standard` | str | Non-empty |
| `evidence.reference_url` | str | Must start with `https://` |
| `evidence.measurement_status` | Literal | Must be `"ESTIMATED"` |

### FR-2: Domain Coverage
WHEN all 20 patterns are loaded, THE SYSTEM SHALL confirm at least one pattern exists
for each of these 5 source domain keywords:
- `"Telecom"` (Signaling and Fault Management patterns)
- `"Distributed"` (Distributed Systems patterns)
- `"OS"` (OS Kernels patterns)
- `"Control"` (Control Theory patterns)
- `"Operations"` (Operations Research patterns)

### FR-3: No Vague Metaphors
WHEN validating `canonical_mechanism` fields, THE SYSTEM SHALL reject any value
containing the phrases: `"like a"`, `"similar to"`, `"acts as"`, `"functions as"`.
Every mechanism must name a real algorithm, protocol, or engineering standard.

### FR-4: Embedding Generation — AOSS Mode
WHEN `seed_opensearch.py` is run with `--mode aoss`, THE SYSTEM SHALL:
1. Validate all 20 patterns against `AnalogPattern` schema (fail fast on any error).
2. For each pattern, build an embedding text string:
   `"{source_domain}. {canonical_mechanism}. State space: {state_space}. Bottleneck: {bottleneck_type}. Failure mode: {failure_mode}. Mechanism: {mechanism}"`
3. Call `amazon.titan-embed-text-v2:0` via Bedrock to generate a 1024-dimensional
   normalised float vector for each pattern.
4. Create (or update) the OpenSearch Serverless index `systems-patterns-v1` with:
   - `knn_vector` field (`dimension: 1024`, `method: hnsw`, `space_type: cosinesimil`)
   - `keyword` field for `pattern_id`
   - `text` fields for `source_domain`, `canonical_mechanism`, `text`
   - `object` field (disabled indexing) for the full `record`
5. Index all 20 documents with `pattern_id` as the document ID.
6. Print a confirmation line per indexed pattern: `✓ PAT-NNN: <mechanism>`

### FR-5: Embedding Generation — Local Mode
WHEN `seed_opensearch.py` is run with `--mode local`, THE SYSTEM SHALL:
1. Validate all 20 patterns (same as FR-4 step 1).
2. Generate Titan v2 embeddings for each pattern (same as FR-4 step 3).
3. Write `data/patterns_20_embedded.json` — a JSON array where each element contains:
   `{"pattern_id": str, "embedding": list[float], "text": str, "record": dict}`
4. This file is the zero-cost fallback used by `lambdas/analogy_engine/handler.py`
   when `AOSS_ENDPOINT` is unset (after `cdk destroy`).

### FR-6: CLI Flags
THE SYSTEM SHALL support these `seed_opensearch.py` CLI flags:

| Flag | Behaviour |
|---|---|
| `--mode aoss` | Index into Amazon OpenSearch Serverless |
| `--mode local` | Write local numpy fallback file |
| `--dry-run` | Validate schema only; skip Bedrock and OpenSearch calls |
| `--force-refresh` | Delete and recreate the AOSS index before indexing (aoss mode only) |

### FR-7: Force-Refresh Safety
WHEN `--force-refresh` is passed WITHOUT `--mode aoss`, THE SYSTEM SHALL print a warning
and ignore the flag (force-refresh only applies to AOSS).

### FR-8: Missing AOSS Endpoint Guard
WHEN `--mode aoss` is run and `AOSS_ENDPOINT` environment variable is not set,
THE SYSTEM SHALL print a clear error message:
`"ERROR: AOSS_ENDPOINT not set. Run 'cdk deploy' first and set AOSS_ENDPOINT from stack outputs."`
and exit with code 1 without calling Bedrock.

### FR-9: Disclaimer on PatternEvidence
WHEN any pattern is rendered in the Enhancement Dossier, THE SYSTEM SHALL include
the disclaimer: `"Architectural lift projections are domain-derived estimates, not empirical repo benchmarks."`
This is enforced via `PatternEvidence.measurement_status == "ESTIMATED"` and displayed
in the Analogy Card UI component (Phase 4).

---

## Non-Functional Requirements

### NFR-1: Validation Speed
WHEN `--dry-run` is passed, THE SYSTEM SHALL complete schema validation of all 20
patterns in under 1 second without any network calls.

### NFR-2: Idempotency
WHEN `seed_opensearch.py --mode local` is run twice with the same `patterns_20.json`,
THE SYSTEM SHALL produce identical `patterns_20_embedded.json` output (deterministic).

### NFR-3: Local Fallback File Not Committed
`data/patterns_20_embedded.json` SHALL be listed in `.gitignore` and never committed
to the repository (it is generated output, up to ~80 MB).

---

## Acceptance Criteria

- [ ] `python data/seed_opensearch.py --mode local --dry-run` runs in < 1s with zero errors
- [ ] All 20 patterns validate against `AnalogPattern` schema with no failures
- [ ] All 20 `evidence.reference_url` values start with `https://`
- [ ] All 20 `evidence.measurement_status` values equal `"ESTIMATED"`
- [ ] Domain coverage confirmed: Telecom, Distributed, OS, Control, Operations all present
- [ ] No `canonical_mechanism` contains a vague metaphor phrase
- [ ] `tests/unit/test_pattern_corpus.py` — all tests green (`make test`)
- [ ] `tests/unit/test_seed_opensearch.py` — all tests green with mocked Bedrock
- [ ] `make lint` — zero ruff errors on `data/seed_opensearch.py`
