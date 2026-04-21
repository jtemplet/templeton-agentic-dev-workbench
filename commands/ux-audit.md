---
description: "Run a UX audit of a web app: drives it via Playwright, captures screenshots, and produces a severity-ranked report across 7 design dimensions (accessibility, design system, IA, interaction, content, emotional design, cognitive load)"
argument-hint: "<app-url> [notes]"
---

Use the `ux-product-designer` agent to conduct a UX audit of the web app at `$ARGUMENTS`.

For iOS apps, use `/ux-audit-ios` instead.

The agent will:

1. Read `AGENTS.md` to ground the audit in the product's purpose, target user, and primary workflows
2. Drive the app via Playwright: navigate, capture screenshots, exercise forms, error states, and edge cases
3. Perform a five-second test, keyboard accessibility pass, and three-viewport responsive evaluation
4. Evaluate across seven dimensions: Accessibility, Design System Coherence, Information Architecture, Interaction Design, Content & Microcopy, Emotional Design & Trust, and Cognitive Load
5. Write a severity-ranked report to `docs/ux-audits/<YYYY-MM-DD>-<app>.md` with screenshots under `docs/ux-audits/<slug>/screenshots/`

The report covers:

- Product Understanding (from AGENTS.md)
- Five-Second Test
- Issues ranked by severity with dimension tags and screenshot evidence
- Dimension Scorecards (7 dimensions, 5-point scale benchmarked against Apple/Stripe/Airbnb)
- Clutter and Cognitive Load deep-dive
- Accessibility Summary (keyboard, focus, contrast, heading hierarchy, touch targets, dark patterns)
- Concrete recommendations (preferring subtraction over addition, with effort/impact ratings)
- Quick Wins
- Strategic Observations

If `AGENTS.md` is missing or context is too thin, the agent will ask for product purpose, target user, and primary workflows before proceeding.
