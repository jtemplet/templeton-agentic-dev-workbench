---
description: "Synthesize the codebase and beads tracker into a self-contained interactive HTML project dashboard at docs/roadmap.html"
argument-hint: "[optional: path to a beads issues.jsonl]"
---

Use the `roadmap-dashboard` skill to produce a single self-contained, interactive HTML
project dashboard at `docs/roadmap.html`.

Operate as a dual-role Senior Software Architect and Technical Project Manager: perform the
engineering assessment first, then render the visuals. The skill will:

1. Collect the beads tracker data with `scripts/collect_beads.py` (refreshes the JSONL, parses
   it, and annotates each issue with ready/blocked/blocked_by). If `$ARGUMENTS` names a JSONL
   path, pass it via `--jsonl`.
2. Assess the codebase (architecture, DB schema, API surface, CI/CD, tests) and cross-reference
   it against the beads to classify each subsystem as Built / Partial / Stubbed / Planned.
3. Compute a defensible overall completion percentage (blended, with rationale and a confidence
   score), enumerate evidence-based risks, and sequence the outstanding beads into a roadmap.
4. Render one HTML file with zero external dependencies: an executive KPI dashboard, five pure
   HTML/CSS diagrams (architecture current-vs-target, data/request flow, DB relationships, task
   dependency graph, milestone timeline + risk matrix), collapsible subsystem deep-dives, a
   Todo / In Progress / Done Kanban board fed from beads, a prioritized roadmap table, a sticky
   auto-generated table of contents, and print-friendly CSS.

Write to `docs/roadmap.html`; if a versioned report already exists (`docs/roadmap-vX.Y.html`),
bump to the next minor version instead of overwriting. Mark every inferred claim with an
`[Inference]` tag and a confidence score, and use a plain hyphen for genuinely unknown values.
Report the resolved file path back when done.
