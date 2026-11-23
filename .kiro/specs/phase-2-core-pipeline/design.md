# Phase 2 — Core Pipeline: Design

## Status: PENDING

See `requirements.md` for full FR list. Design to be authored when Phase 1 passes.

## Key design notes (locked from architecture)

- Enhancement Lambda runs AFTER fan-in — it needs all 4 discovery payloads as input
- Scoring Engine lives inside the Enhancement Lambda (same process, same in-memory JSON)
- Local numpy fallback in Analogy Engine when `AOSS_ENDPOINT` unset
- Mermaid sanitisation regex: strip `()` and `"` inside `[...]` before DynamoDB write
- Citation Verifier: programmatic URL cross-check against raw tool payloads — no LLM
