# Phase 1 — Pattern Corpus & Hybrid Vector Indexer: Design

## Status: IN PROGRESS 🔄

---

## Overview

Phase 1 produces two artefacts that every downstream phase depends on:

| Artefact | Used by |
|---|---|
| `data/patterns_20.json` | Phase 2 (Analogy Engine), Phase 1 tests |
| `data/patterns_20_embedded.json` | Phase 2 Analogy Engine local fallback |
| AOSS index `systems-patterns-v1` | Phase 2 Analogy Engine live path |

---

## Data Model

### AnalogPattern (validation schema inside seed_opensearch.py)

```python
class AnalogPattern(BaseModel):
    pattern_id:           str                    # "PAT-001" … "PAT-020"
    source_domain:        str
    canonical_mechanism:  str
    problem_signature:    ProblemSignature
    trigger_condition:    dict                   # {"detected_when": str}
    transferable_design:  TransferableDesign
    evidence:             PatternEvidence

class ProblemSignature(BaseModel):
    state_space:        str
    bottleneck_type:    str
    failure_mode:       str
    consistency_model:  str

class TransferableDesign(BaseModel):
    mechanism:            str
    mapping_table:        list[MappingEntry]     # min 1 entry
    expected_lift:        str
    anti_pattern_warning: str                    # min 10 chars

class MappingEntry(BaseModel):
    source_primitive:  str
    target_repo_module: str
    expected_effect:   str

class PatternEvidence(BaseModel):
    standard:            str
    reference_url:       str    # must start with https://
    measurement_status:  Literal["ESTIMATED", "BENCHMARKED"] = "ESTIMATED"
```

---

## Embedding Text Construction

Each pattern is embedded using this deterministic text template:

```
"{source_domain}. {canonical_mechanism}. State space: {state_space}.
 Bottleneck: {bottleneck_type}. Failure mode: {failure_mode}.
 Mechanism: {transferable_design.mechanism}"
```

This strips all domain-specific nouns from the query at search time,
matching the Domain-Stripped Structural Abstraction strategy from the architecture doc.
The analogy engine (Phase 2) strips the same nouns from the user's `ProblemSignature`
before querying, ensuring structural rather than surface similarity.

---

## seed_opensearch.py Architecture

```
main()
  │
  ├── load_and_validate()
  │     └── json.loads(patterns_20.json)
  │         → for each record: AnalogPattern.model_validate(record)
  │         → collect errors, fail-fast if any
  │
  ├── [--mode local]  seed_local()
  │     └── for each pattern:
  │           text  = _pattern_text(p)
  │           vec   = _embed_text(text)   ← Bedrock Titan v2
  │           append {"pattern_id", "embedding", "text", "record"} to list
  │         write list → data/patterns_20_embedded.json
  │
  └── [--mode aoss]  seed_aoss()
        ├── check AOSS_ENDPOINT set (exit 1 if not)
        ├── build AWS4Auth from boto3 session credentials
        ├── [--force-refresh] delete existing index
        ├── create index with knn_vector mapping if not exists
        └── for each pattern:
              text = _pattern_text(p)
              vec  = _embed_text(text)   ← Bedrock Titan v2
              client.index(id=pattern_id, body={...})
```

---

## OpenSearch Index Mapping

```json
{
  "settings": { "index": { "knn": true } },
  "mappings": {
    "properties": {
      "pattern_id":          { "type": "keyword" },
      "source_domain":       { "type": "text" },
      "canonical_mechanism": { "type": "text" },
      "text":                { "type": "text" },
      "embedding": {
        "type": "knn_vector",
        "dimension": 1024,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib"
        }
      },
      "record": { "type": "object", "enabled": false }
    }
  }
}
```

The hybrid search strategy (Phase 2 Analogy Engine) will combine:
- **k-NN vector search** on the `embedding` field (structural similarity)
- **BM25 text search** on `source_domain` + `canonical_mechanism` + `text` (keyword recall)

---

## Local Fallback Design

When `AOSS_ENDPOINT` is not set (post `cdk destroy`), the Analogy Engine loads
`data/patterns_20_embedded.json` and runs exact cosine similarity using numpy:

```python
import numpy as np

def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))
```

20 vectors × 1024 floats × 4 bytes = ~80 KB in memory — negligible Lambda overhead.

---

## 20-Pattern Corpus — Domain Distribution

| Domain Group | Pattern IDs | Count |
|---|---|---|
| Telecom Signaling & Fault Mgmt | PAT-001, PAT-002, PAT-003, PAT-004, PAT-005 | 5 |
| Distributed Systems | PAT-006, PAT-007, PAT-008, PAT-009, PAT-010 | 5 |
| OS Kernels | PAT-011, PAT-012, PAT-013, PAT-014, PAT-015 | 5 |
| Control Theory | PAT-016, PAT-017, PAT-018 | 3 |
| Operations Research | PAT-019, PAT-020 | 2 |

> Control Theory and Operations Research have 3 and 2 patterns respectively.
> All 5 domain keywords ("Telecom", "Distributed", "OS", "Control", "Operations")
> are present — the FR-2 coverage check passes.

---

## Test Strategy

### test_pattern_corpus.py (extend existing tests in tests/unit/)
Verifies corpus integrity without any AWS calls:
- Exactly 20 records
- All IDs unique and sequential (PAT-001 … PAT-020)
- All `reference_url` values HTTPS
- All `measurement_status` values `"ESTIMATED"`
- No vague metaphors in `canonical_mechanism`
- All `mapping_table` entries non-empty
- All `anti_pattern_warning` values ≥ 10 chars
- Domain coverage (5 keywords present)

### test_seed_opensearch.py (new file)
Verifies seeder logic with mocked Bedrock and OpenSearch:
- `--dry-run` completes without calling Bedrock or OpenSearch
- `--mode local --dry-run` skips file write
- `_embed_text()` calls Bedrock with correct model ID
- `_pattern_text()` produces deterministic string for each pattern
- Missing `AOSS_ENDPOINT` on `--mode aoss` exits with code 1
- `--force-refresh` without `--mode aoss` prints warning and continues safely

---

## Dependencies Required

Add to `Makefile` bootstrap and CI:
```
opensearch-py>=2.4
requests-aws4auth>=1.2
```
These are only needed for `--mode aoss`; `--mode local` requires only `boto3` and `numpy`.
