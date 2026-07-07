# HTML Blueprint: Zero-Dependency Roadmap Dashboard

This reference specifies how to build the single self-contained HTML file. Every requirement
here is a hard constraint, not a suggestion. The output must render correctly by opening the
file directly in a browser with no network access.

## Absolute Constraints

- **One file.** All CSS in a single `<style>` tag in `<head>`; all JS in a single `<script>`
  tag before `</body>`. No external `<link>`, `<script src>`, `@import`, or `url()` pointing off-file.
- **No dependencies.** No Tailwind, Bootstrap, FontAwesome, Google Fonts, jQuery, D3, Chart.js,
  Mermaid, or SVG icon libraries. Diagrams are built from HTML elements styled with CSS.
- **System fonts only.** Use a native stack:
  `font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;`
  and `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace` for code/IDs.
- **Icons are Unicode or CSS shapes.** Use plain Unicode glyphs (e.g. `▲ ● ◆ ✓ ⚠`) or CSS
  pseudo-elements. Never load an icon font.

## Color System (dark, professional)

Define as CSS custom properties on `:root` so the palette is edited in one place:

```css
:root {
  --bg: #0d1117;            /* page background */
  --surface: #161b22;      /* cards, panels */
  --surface-2: #21262d;    /* nested / hover */
  --border: #30363d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --accent: #58a6ff;       /* primary / links */
  --ok: #3fb950;           /* done, low risk */
  --warn: #d29922;         /* medium risk, in-progress */
  --danger: #f85149;       /* critical, high risk, blocked */
  --info: #a371f7;         /* inference tags */
}
```

Meet WCAG AA contrast (>= 4.5:1 for body text) against `--bg`/`--surface`. Never encode
state with color alone: pair every colored badge with a text label or glyph.

## Required Sections and How to Build Each

### 1. Executive dashboard (top of page)

A responsive KPI grid using CSS Grid: `grid-template-columns: repeat(auto-fit, minmax(180px, 1fr))`.
Each KPI is a card (`--surface`, rounded, 1px `--border`) with a large number and a muted label.
Required KPIs: Overall Completion %, Completed vs Remaining counts, Identified Risks,
Estimated Milestones Left, Largest Unfinished Feature, Current Focus, Confidence Level.

Overall completion is a **CSS-only progress bar**: an outer div (`--surface-2`) and an inner
div whose `width: NN%` is set inline, filled with a gradient `--accent`→`--ok`. Show the
numeric percent as text inside or beside the bar (color-alone is not enough).

### 2. Diagrams (pure HTML/CSS/JS)

All five diagrams are built from nested `<div>`s. Techniques:

- **Boxes/nodes:** styled divs with border, padding, radius, and a title + subtitle line.
- **Layers/columns:** Flexbox rows or CSS Grid; use `gap` for rhythm.
- **Connectors:** either (a) a thin flex "arrow" element (`▸`/`→` glyph between boxes), or
  (b) CSS borders / `::before` pseudo-elements drawn as lines. Keep connectors legible; do
  not attempt dense graph routing.
- **Color:** use the state palette (green built, amber partial, red stubbed/at-risk). Add a
  small legend beside each diagram mapping color → meaning.

Diagrams to produce:

1. **System Architecture: Current vs Target.** Two side-by-side columns (Flexbox), each a
   vertical stack of component boxes. Tag each box built / partial / stubbed / planned.
2. **Data & Request Flow.** A horizontal row of layer boxes (Client → API → Service →
   Database) separated by `→` connectors; annotate each hop.
3. **Database Relationships.** A grid of entity cards; each card lists key columns. Show
   relationships as labeled connector rows (e.g. `User 1..* Order`) rather than routed lines.
4. **Task & Feature Dependency Graph.** Group beads into dependency "tiers" (topological
   layers) as horizontal rows; draw each node as a card colored by ready/blocked/done and
   annotate `blocked_by` edges with the upstream IDs. Mark the critical path with a distinct
   border (e.g. `--danger` 2px). Compute tiers from the `dependencies`/`blocked_by` data.
5. **Milestone Timeline & Risk Matrix.** A horizontal timeline (Flexbox row of milestone
   markers) plus a 3×3 risk matrix built with CSS Grid (axes: Likelihood × Impact), each cell
   colored and holding the risks that fall in it.

### 3. Subsystem deep-dives (collapsible accordions)

Use the native `<details>`/`<summary>` element (no JS needed for basic collapse). Style
`summary` as a clickable header with a rotating `▸`/`▾` indicator via CSS. Each panel:
purpose, implementation maturity (with a mini progress bar), mapped beads, refactoring
opportunities, test status, localized risks.

### 4. Kanban board

Three columns (CSS Grid, `grid-template-columns: repeat(3, 1fr)`): **Todo**, **In Progress**,
**Done**. Populate cards from the beads data using the status→column routing in
`references/beads-extraction.md` (the single source for that mapping). Each card shows the
bead ID (monospace), title, a priority badge, and a blocked indicator when applicable. Cards
are read-only (no drag-and-drop required); keep them scannable.

### 5. Roadmap table

A styled `<table>` (zebra striping via `:nth-child`, sticky `thead`). Columns: Priority Tier,
Bead ID, Title, Effort, Difficulty, Upstream Dependencies, Impact, Parallelization-Safe.
Sort by priority tier then readiness.

## Navigation, Interactivity, and Print

- **Sticky nav / TOC.** A `position: sticky` (or fixed sidebar) nav auto-generated by JS:
  on `DOMContentLoaded`, query all `section[id]` (or `h2[id]`), build anchor links, and
  highlight the active section on scroll (IntersectionObserver or a scroll listener). Keep
  the JS small and dependency-free.
- **Smooth in-page scroll** via `html { scroll-behavior: smooth; }`.
- **Print CSS** in an `@media print` block: switch to a light background and dark text,
  expand all `<details>` (`details { open: ... }` cannot be forced by CSS, so also set
  `details[open]` styling and add JS that opens all panels when `window.matchMedia('print')`
  fires via `onbeforeprint`), hide the sticky nav, avoid page breaks inside cards
  (`break-inside: avoid`), and ensure diagrams fit page width.

## Uncertainty Mapping

Wherever a claim is inferred rather than observed in the code or beads data, append an inline
`[Inference]` badge (styled with `--info`) and a confidence score, e.g.
`<span class="inf">[Inference] Confidence: 75%</span>`. Anything the analysis could not
determine gets a plain hyphen (`-`) placeholder, never a fabricated value.

## Self-Verification Before Delivery

- Open the file mentally / structurally: confirm no `src=`, `href="http`, `@import`, or
  `cdn` strings remain except in-page `#anchors`.
- Confirm every colored status also carries a text label or glyph.
- Confirm the completion percentage in the hero matches the rationale text and is not a bare
  bead ratio (see `references/beads-extraction.md`).
- Confirm every beads issue appears in exactly one Kanban column.
- Confirm the file opens standalone (no console-visible network requests are required to render).
