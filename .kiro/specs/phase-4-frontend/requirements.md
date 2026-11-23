# Phase 4 — Next.js 14 Frontend & AWS Amplify Hosting: Requirements

## Status: PENDING (start after Phase 3 acceptance gate passes)

---

## Functional Requirements

### FR-1: Page 1 — Scan Input (`src/app/page.tsx`)
- `ScanInputForm`: tabs for GitHub URL and Markdown RFC, `force_refresh` toggle, 3 demo preset buttons
- `LivePollingStatus`: polls `GET /scans/{id}` every 1500ms until COMPLETED or FAILED
- Shows subagent progress badges: Repo AST → Name Collision → Ecosystem Scout → Systems Ontology → Grounded Synthesis

### FR-2: Page 2 — Enhancement Dossier (`src/app/dossier/[scanId]/page.tsx`)
- `TrafficLight`: RED/YELLOW/GREEN with matched names and 3 safe alternatives
- `NyxaScoreCard`: composite score, projected score (e.g. 64→79), 6-dimension breakdown, citation drawer
- `KillKeepInjectMatrix`: 3-column triage table with clickable verified URLs
- `AnalogyCard`: canonical standard, mapping table, disclaimer: *"Architectural lift projections are domain-derived estimates, not empirical repo benchmarks."*
- `MermaidDiagram`: renders `mermaid_before_after` with React Error Boundary fallback to plain text
- `EnhancementBacklog`: ranked list (max 5), effort/impact tags
- `ReScanButton`: submits `parent_scan_id + force_refresh=true`, shows `score_delta` badge
- `BadgeSnippet`: copy-pasteable Markdown embed

### FR-3: Styling
- Background: `#0B0F19`, accent: `#38BDF8`, collisions: amber/crimson, code: JetBrains Mono
- Shadcn UI components, Tailwind CSS, responsive (mobile + desktop)

### FR-4: Amplify Hosting
- `amplify.yml` at repo root, `appRoot: frontend`
- `NEXT_PUBLIC_API_URL` set from CDK `ApiEndpointUrl` output
- Cognito guest mode for 1-click demo (no login required)

---

## Acceptance Criteria

- [ ] `npm run build` succeeds inside `frontend/`
- [ ] Live polling renders correct subagent progress badges
- [ ] TrafficLight renders RED, YELLOW, GREEN states correctly
- [ ] MermaidDiagram Error Boundary renders fallback text on parse failure
- [ ] Re-Scan shows `score_delta` badge (e.g. +15 points)
- [ ] Amplify deploys from `main` branch successfully
- [ ] Jest + RTL unit tests pass for all 9 components
- [ ] Mobile responsive layout verified
