---
name: roadmap-dashboard
description: This skill should be used when the user asks to "build a roadmap dashboard", "generate a project dashboard", "create docs/roadmap.html", "visualize project status and remaining beads work", or wants a self-contained interactive HTML dashboard that synthesizes the codebase and the beads tracker into architecture diagrams, a completion gauge, a Kanban board, and a prioritized roadmap. Not for markdown status reports or product docs.
---

# Roadmap Dashboard

Perform a deep-dive analysis of a repository together with its `beads` issue tracker, then
synthesize the findings into one self-contained, interactive HTML dashboard at
`docs/roadmap.html`. The audience is a senior engineer who scans visuals, diagrams, and
data-dense dashboards rather than prose. Act as a dual-role Senior Software Architect and
Technical Project Manager: assess the true state of the system, then present it.

## When to Use

- Producing an at-a-glance view of project maturity, architecture, and remaining work
- Turning the beads backlog into a visual dependency graph, Kanban board, and roadmap
- Communicating MVP proximity and production-readiness to a technical stakeholder

## When NOT to Use

- A plain-markdown status report (this skill's output is a rich HTML artifact)
- Product-surface documentation (use `product-surface-docs`)
- Decomposing a plan into new beads (use `plan-to-beads`)

## Process

Do the analysis before rendering. Rendering a pretty dashboard over a shallow assessment is
the primary failure mode. Detailed guidance lives in the reference files; load them as needed.

1. **Collect the tracker data.** Run the bundled script from the repo root, then read the
   JSON it writes (`<skill>` is this skill's own directory):

   ```bash
   python3 <skill>/scripts/collect_beads.py --out /tmp/roadmap-beads.json
   ```

   It refreshes the JSONL (`bd export -o .beads/issues.jsonl` when `bd` is present), parses it, skips
   tombstones, normalizes priorities, filters dependency edges to the blocking ones, and
   annotates each issue with `ready`/`blocked`/`blocked_by`. It always exits 0 and writes the
   `--out` file. When no `.beads/` exists (or the tracker is empty) it emits an empty shape
   (`summary.total == 0`, `source: null`); in that case say so in the dashboard and fall back
   to `TODO`s and code gaps, marked `[Inference]`. See `references/beads-extraction.md` for
   the full field map.

2. **Assess the engineering state.** Inspect entry points, service boundaries, DB schema, API
   routes, CI/CD, and the test suite. Gather implicit signals (`TODO`/`FIXME`, ADRs, issue IDs
   in recent commits). Cross-reference code against beads to classify each subsystem as Built /
   Partial / Stubbed / Planned. See `references/analysis-guide.md`.

3. **Compute a defensible completion %.** Blend task completion (effort-weighted), feature
   maturity, and production-readiness into one figure with a one-sentence rationale. Never
   publish the bare `done / total` bead ratio as the answer. Attach a confidence score.

4. **Identify risks and sequence the roadmap.** Enumerate risks from concrete evidence and
   place them on a Likelihood × Impact matrix. Order outstanding beads by value and velocity,
   respecting `blocked_by`, and label each with effort, difficulty, dependencies, impact, and
   parallelization-safety.

5. **Render the HTML.** Build the single file to the spec in `references/html-blueprint.md`:
   executive KPI dashboard, five pure-HTML/CSS diagrams, collapsible subsystem deep-dives, a
   Kanban board fed from beads status, and a prioritized roadmap table, with a sticky
   auto-generated TOC and print CSS. Route beads onto Kanban columns and lay out the
   dependency tiers per `references/beads-extraction.md`.

6. **Version and write the file.** Write to `docs/roadmap.html`. If a versioned file already
   exists (see next section), bump the version instead of overwriting. Create `docs/` if needed.

7. **Self-verify.** Run the checklist in `references/html-blueprint.md` (no external
   references, color never used alone, every bead in exactly one Kanban column, completion
   figure matches its rationale). Report the written file path back to the user.

## File Versioning

The base target is `docs/roadmap.html`. Preserve prior reports rather than clobbering them.
Resolve the output filename with these rules, in order:

- **Nothing exists yet** (no `docs/roadmap.html` and no `docs/roadmap-vX.Y.html`): write
  `docs/roadmap.html`.
- **Versioned files exist**: find the highest version and write the next minor bump
  (`v1.0` → `v1.1`). Determine the highest with:

  ```bash
  ls docs/roadmap-v*.html 2>/dev/null | sort -V | tail -1
  ```

- **Only the unversioned `docs/roadmap.html` exists** (no versioned siblings): do not
  overwrite it. Treat it as `v1.0` and write the new report as `docs/roadmap-v1.1.html`.

Never overwrite any existing report, versioned or not. Confirm the resolved filename in the
summary so the user knows which version was produced.

## Output Requirements (hard constraints)

- **Exactly one HTML file.** All CSS in one `<style>` tag; all JS in one `<script>` tag.
- **Zero external dependencies.** No external fonts, icon fonts, CSS frameworks, or JS
  libraries (no Tailwind, Bootstrap, FontAwesome, jQuery, D3, Mermaid). System font stack only.
- **Diagrams are pure HTML/CSS/vanilla JS.** No SVG libraries, no image assets, no Mermaid.
  Build nodes and connectors from styled `<div>`s (Flexbox/Grid, borders, pseudo-elements).
- **Dark, professional palette** with WCAG AA contrast; state is never encoded by color alone
  (always pair a colored badge with a text label or glyph).
- **Interactivity:** sticky auto-generated TOC nav, `<details>` accordions for deep-dives, a
  Todo / In Progress / Done Kanban board, and a print-friendly `@media print` block.
- **Uncertainty mapping:** mark every inferred claim with an inline `[Inference]` badge and a
  `Confidence: NN%` score; use a plain hyphen (`-`) for genuinely unknown values, never a guess.

## Critical Rules

**Always:**

- Collect beads via the bundled script, never by hand-parsing JSONL.
- Ground every claim in a file, endpoint, schema, test, or bead; label everything else `[Inference]`.
- Keep the output a single file that renders offline with no network requests.
- Map every beads issue into exactly one Kanban column; surface unknown statuses verbatim.
- Blend three signals for the completion figure and show the rationale.

**Never:**

- Add any external font, stylesheet, script, image, or icon library.
- Use Mermaid or an SVG/charting library for the diagrams.
- Publish the raw bead ratio as the project completion percentage.
- Fabricate values, estimates, or risks; use `-` and `[Inference]` for the unknown.
- Overwrite an existing report, versioned or not; bump the version instead.

## Bundled Resources

- **`scripts/collect_beads.py`**: refreshes and normalizes the beads tracker into a stable
  JSON blob (`summary` + per-issue `ready`/`blocked`/`blocked_by`). Run this first.
- **`references/analysis-guide.md`**: how to inspect the codebase, cross-reference against
  beads, compute the completion %, identify risks, and sequence the roadmap.
- **`references/html-blueprint.md`**: the full no-dependency HTML/CSS/JS spec (palette,
  every diagram, the Kanban board, print CSS, and the pre-delivery verification checklist).
- **`references/beads-extraction.md`**: field-by-field mapping from the script's output onto
  dashboard elements, Kanban routing, and dependency-tier layout.
