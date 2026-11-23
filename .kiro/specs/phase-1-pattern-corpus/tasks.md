# Phase 1 — Pattern Corpus & Hybrid Vector Indexer: Tasks

## Status: IMPLEMENTED; local acceptance checks pass

Execute these tasks in order. Check each box only after the item is verified.

---

## Task 1 — Extend corpus validation tests

**File:** `tests/unit/test_pattern_corpus.py`

The existing `test_schemas.py` already covers basic corpus checks. This task creates a
dedicated file with the full FR-1 / FR-2 / FR-3 validation suite.

- [ ] Create `tests/unit/test_pattern_corpus.py`
- [ ] Test: exactly 20 patterns loaded from `data/patterns_20.json`
- [ ] Test: all pattern IDs unique
- [ ] Test: pattern IDs sequential PAT-001 through PAT-020
- [ ] Test: all `evidence.reference_url` values start with `https://`
- [ ] Test: all `evidence.measurement_status` == `"ESTIMATED"`
- [ ] Test: no `canonical_mechanism` contains `"like a"`, `"similar to"`, `"acts as"`, `"functions as"`
- [ ] Test: all `transferable_design.mapping_table` lists have ≥ 1 entry
- [ ] Test: all `transferable_design.anti_pattern_warning` values have ≥ 10 characters
- [ ] Test: domain coverage — `"Telecom"`, `"Distributed"`, `"OS"`, `"Control"`, `"Operations"` all present in `source_domain` values
- [ ] Test: all `trigger_condition` dicts have a non-empty `detected_when` key
- [ ] Test: `AnalogPattern.model_validate()` succeeds for every record (no Pydantic errors)
- [ ] Run `pytest tests/unit/test_pattern_corpus.py -v` → all green

**Acceptance check:** `make test` passes with all corpus tests green.

---

## Task 2 — Harden seed_opensearch.py

**File:** `data/seed_opensearch.py`

The seeder skeleton exists. This task implements all missing logic and adds guards.

- [ ] Add `AnalogPattern` Pydantic model to `seed_opensearch.py` (mirrors the schema above)
- [ ] Add `ProblemSignature`, `TransferableDesign`, `MappingEntry`, `PatternEvidence` models
- [ ] Implement `load_and_validate()` — fail fast with clear error messages on any schema violation
- [ ] Implement `_pattern_text(p: AnalogPattern) -> str` — deterministic embedding text builder
- [ ] Implement `_embed_text(text: str) -> list[float]` — Bedrock Titan v2 call
- [ ] Implement `seed_local(patterns, dry_run)`:
  - [ ] Skip all Bedrock calls when `dry_run=True`
  - [ ] Write `data/patterns_20_embedded.json` with correct structure
  - [ ] Print `✓ PAT-NNN: <mechanism>` per pattern
- [ ] Implement `seed_aoss(patterns, dry_run, force_refresh)`:
  - [ ] Exit code 1 with clear error if `AOSS_ENDPOINT` not set
  - [ ] Skip all calls when `dry_run=True`
  - [ ] Delete + recreate index when `force_refresh=True`
  - [ ] Create index with correct knn_vector mapping if not exists
  - [ ] Index all 20 documents with `pattern_id` as document ID
  - [ ] Print `✓ PAT-NNN: <mechanism>` per indexed pattern
- [ ] Add `--force-refresh` warning when used without `--mode aoss`
- [ ] Run `python data/seed_opensearch.py --mode local --dry-run` → exits 0, no errors

**Acceptance check:** `--dry-run` completes in < 1 second.

---

## Task 3 — Write seed_opensearch unit tests

**File:** `tests/unit/test_seed_opensearch.py`

- [ ] Create `tests/unit/test_seed_opensearch.py`
- [ ] Test: `load_and_validate()` returns 20 `AnalogPattern` objects for valid corpus
- [ ] Test: `load_and_validate()` exits / raises on a corpus with a missing required field
- [ ] Test: `_pattern_text()` produces a deterministic non-empty string for PAT-001
- [ ] Test: `_pattern_text()` output does not contain domain nouns from `source_domain`
  verbatim — it includes mechanism and structural primitives
- [ ] Test: `seed_local(patterns, dry_run=True)` makes zero boto3 calls
- [ ] Test: `seed_local(patterns, dry_run=False)` calls `bedrock-runtime.invoke_model`
  exactly 20 times with model ID `amazon.titan-embed-text-v2:0` (mocked)
- [ ] Test: `seed_local(patterns, dry_run=False)` writes a JSON file containing
  exactly 20 entries each with keys `pattern_id`, `embedding`, `text`, `record`
- [ ] Test: running `seed_local` twice produces identical output (idempotency)
- [ ] Test: `seed_aoss` with `AOSS_ENDPOINT=""` exits with code 1
- [ ] Test: `--force-refresh` with `--mode local` prints warning, does not crash
- [ ] Run `pytest tests/unit/test_seed_opensearch.py -v` → all green

**Acceptance check:** All 10+ seed tests pass with mocked boto3.

---

## Task 4 — Update Makefile dependencies

**File:** `Makefile`

- [ ] Add `opensearch-py>=2.4` and `requests-aws4auth>=1.2` to the `bootstrap` pip install list
- [ ] Verify `make bootstrap` still completes without errors
- [ ] Verify `make lint` passes on `data/seed_opensearch.py` (zero ruff errors)

---

## Task 5 — Verify .gitignore excludes generated file

**File:** `.gitignore`

- [ ] Confirm `data/patterns_20_embedded.json` is listed in `.gitignore`
- [ ] Run `git status` after `--mode local` dry-run — confirm the file would not be tracked

---

## Task 6 — Run full acceptance gate

- [ ] `make lint` → zero errors
- [ ] `make test` → all unit tests green (includes new corpus and seeder tests)
- [ ] `python data/seed_opensearch.py --mode local --dry-run` → exits 0 in < 1s
- [ ] All Acceptance Criteria in `requirements.md` checked off

---

## Completion checklist

- [ ] Task 1 complete — corpus tests all green
- [ ] Task 2 complete — seeder fully implemented
- [ ] Task 3 complete — seeder unit tests all green
- [ ] Task 4 complete — Makefile updated
- [ ] Task 5 complete — .gitignore confirmed
- [ ] Task 6 complete — full acceptance gate passed

## Resume checkpoint

Corpus, validator, seeder, Makefile dependencies, and unit tests are implemented. Verified with 20-record schema tests and `python data/seed_opensearch.py --mode local --dry-run`. Exact Makefile bootstrap gate and Git status check were not run in this environment.

## → Phase 2 (Core Pipeline) is implemented; synth/deployment gates remain.
