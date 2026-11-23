# NyxaLensAI — Scoring Rubric & Collision Thresholds

This document exists so judges, reviewers, and users can audit every scoring decision
without reading implementation code.

---

## Nyxa Score Formula

```
Nyxa Score (0–100) = 0.40 × S_deterministic + 0.60 × S_rubric
```

### S_deterministic — 40 points maximum (pure Python, no LLM)

| Signal | Points | How Computed |
|---|---|---|
| `has_tests` | +8 | Repository scanner found a test path or `test_*.py` file |
| unique dependencies | +6 | At least one dependency and dependency list contains no duplicates |
| verified citations | 0–8 | `round(8 × min(count, 3) / 3)` citations retained from raw lane evidence |
| README/module overlap | +8 | At least one core module string appears in the README claims text |
| Mermaid diagram | +4 | Diagram contains `graph` and an edge marker (`--`) |
| collision status GREEN | +6 | Name Collision lane returned GREEN |

### S_rubric — 60 points maximum (Bedrock Claude Sonnet, rubric-anchored)

| Dimension | Weight | What It Measures |
|---|---|---|
| Clarity | 15% | README claims match actual implemented code paths |
| Landscape Coverage | 15% | Known direct competitors acknowledged in README/docs |
| Originality | 25% | Ratio of novel control-flow logic vs. commodity wrapper code |
| Gap Opportunity | 15% | Unaddressed failure modes in existing ecosystem tools |
| Enhancement Potential | 20% | Concrete architectural lift available from cross-domain patterns |
| Evidence Quality | 10% | Presence of benchmarks, deterministic evals, latency metrics |

> **Disclaimer:** All lift estimates in Analogy Cards are architectural projections derived
> from domain knowledge, not empirical benchmarks run against this specific repository.
> Every `PatternEvidence` record carries `measurement_status: "ESTIMATED"`.

### Realistic Score Delta

Applying the top 2 Enhancement recommendations yields a realistic **+12 to +18 point
lift** (e.g. 64 → 79). A jump larger than +18 on a single re-scan is a signal the rubric
is soft — investigate before publishing.

---

## Name Collision Traffic Light Thresholds

The name collision subagent uses fixed similarity bands. It does not retain prior state,
so these thresholds are not stateful Schmitt-trigger hysteresis.

### Thresholds

| Colour | Condition | Action |
|---|---|---|
| **RED** | Any exact normalized package/repository name match, or best Jaro-Winkler score ≥ **0.88** | Strong collision signal; returns 3 alternatives |
| **YELLOW** | Best score ≥ **0.78**, a phonetic match, or any upstream partial failure | Review name differentiation; partial checks are marked `PARTIAL_TIMEOUT` |
| **GREEN** | Best score < **0.78**, no phonetic match, and all lookups completed | No collision found in checked registries |

### Why hysteresis?

YELLOW forms an advisory band between GREEN and RED; each scan is evaluated independently.

### Registry Coverage

| Registry | Method |
|---|---|
| GitHub | Search API — exact + Jaro-Winkler + Double Metaphone |
| PyPI | JSON API (`https://pypi.org/pypi/{name}/json`) — exact and fuzzy name comparison |
| npm | Registry API (`https://registry.npmjs.org/{name}`) — exact and fuzzy name comparison |

> If any registry is rate-limited, the subagent returns YELLOW with
> `status: "PARTIAL_TIMEOUT"` and an explicit partial-check badge in the UI.

---

## Citation Verification Rules

Every URL, GitHub repo path, and arXiv paper ID in the generated Dossier must pass a
deterministic existence check against the raw tool payloads from the 4 discovery lanes
before being rendered to the user.

- **Pass**: URL is present in a raw subagent payload → rendered with a ✓ verified badge.
- **Fail**: URL not found in any raw payload → stripped programmatically;
  `stripped_hallucinations_count` incremented.

Target: **100% citation grounding** (zero unsourced hallucinations rendered to user).

---

## Per-Input-Type Calibration

| Rubric Dimension | Repo Mode Weight | RFC/Idea Mode Weight |
|---|---|---|
| Clarity | 15% | 20% |
| Landscape Coverage | 15% | 25% |
| Originality | 25% | 15% |
| Gap Opportunity | 15% | 25% |
| Enhancement Potential | 20% | 15% |
| Evidence Quality | 10% | 0% (not applicable pre-code) |

In RFC/Idea Mode, the deterministic AST signals (`has_automated_tests`,
`dependency_dedup_ratio`) default to 0 since no code exists yet; the full 40 deterministic
points shift to the rubric sub-scores.
