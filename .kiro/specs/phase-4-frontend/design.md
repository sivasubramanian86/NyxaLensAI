# Phase 4 — Frontend: Design

## Status: PENDING

Key decisions (locked):
- Polling: `useEffect` loop every 1500ms against `GET /scans/{id}` — no WebSocket
- Mermaid: `mermaid.initialize({ startOnLoad: false })` + manual `mermaid.render()` in useEffect
- Error Boundary wraps MermaidDiagram only — renders raw mermaid source text on failure
- No login required for hackathon demo: Cognito guest mode via `Auth.currentCredentials()`
- `score_delta` computed client-side: `dossier.nyxa_score.composite - parentDossier.nyxa_score.composite`
