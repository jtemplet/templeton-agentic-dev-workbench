---
description: "Run a UX audit: drives a running app via Playwright, captures screenshots, and produces a severity-ranked report focused on clarity, clutter, and cognitive load"
argument-hint: "<app-url> [notes]"
---

Use the `ux-product-designer` agent to conduct a UX audit of the app at `$ARGUMENTS`.

The agent will:

1. Read `AGENTS.md` to ground the audit in the product's purpose, target user, and primary workflows
2. Drive the app via Playwright: navigate, capture screenshots, exercise forms and edge cases
3. Evaluate visual hierarchy, clarity of CTAs, information density, interaction feedback, and trust signals
4. Explicitly hunt for clutter and cognitive overload, the most important part of the audit
5. Write a severity-ranked report to `docs/ux-audits/<YYYY-MM-DD>-<app>.md` with screenshots under `docs/ux-audits/<slug>/screenshots/`

The report covers:

- Product Understanding (from AGENTS.md)
- Issues ranked by severity (Critical, High, Medium, Low) with screenshot evidence
- Clutter and Confusion findings
- Concrete recommendations (preferring subtraction over addition)
- Quick Wins

If `AGENTS.md` is missing or context is too thin, the agent will ask for product purpose, target user, and primary workflows before proceeding.
