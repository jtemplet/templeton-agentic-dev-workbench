---
description: "Run a UX audit of a web app: drives it via Playwright, captures screenshots, and produces a severity-ranked report across 7 design dimensions (accessibility, design system, IA, interaction, content, emotional design, cognitive load)"
argument-hint: "<app-url> [notes]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/ux-audit/SKILL.md` and follow it to conduct a UX audit of the web app at $ARGUMENTS.

Read the file rather than invoking the skill by name. `commands/ux-audit.md` and
`skills/ux-audit/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(ux-audit)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/ux-audit/SKILL.md` and read it from there.

The audit operates from the `ux-product-designer` role: a senior product designer working at the standard of Apple, Stripe, and Airbnb design teams. Refer to `agents/ux-product-designer.md` for the role's beliefs and judgment principles.

For iOS apps, use `/ux-audit-ios` instead.

The skill will:

1. Read `AGENTS.md` to ground the audit in the product's purpose, target user, and primary workflows
2. Drive the app via Playwright: navigate, capture screenshots, exercise forms, error states, and edge cases
3. Perform a five-second test, keyboard accessibility pass, and three-viewport responsive evaluation
4. Evaluate across seven dimensions: Accessibility, Design System Coherence, Information Architecture, Interaction Design, Content & Microcopy, Emotional Design & Trust, and Cognitive Load
5. Write a severity-ranked report to `docs/ux-audits/<YYYY-MM-DD>-<app>.md` with screenshots under `docs/ux-audits/<slug>/screenshots/`

If `AGENTS.md` is missing or context is too thin, the skill will ask for product purpose, target user, and primary workflows before proceeding.
