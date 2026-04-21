---
description: "Run a UX audit of an iOS app in the Simulator: captures screenshots, tests Dynamic Type / Dark Mode / accessibility settings, and produces a severity-ranked report against Apple HIG standards"
argument-hint: "<app-bundle-id-or-name> [notes]"
---

Use the `ux-product-designer-ios` agent to conduct a UX audit of the iOS app specified in `$ARGUMENTS`.

The agent will:

1. Read `AGENTS.md` to ground the audit in the product's purpose, target user, and primary workflows
2. Verify the iOS Simulator is booted and clean the status bar for professional screenshots
3. Capture screenshots via `xcrun simctl io` and guide you through flows interactively
4. Test Dynamic Type (extra-large and XXXL), Dark Mode, and Bold Text configurations
5. Evaluate across seven dimensions: Accessibility, Design System Coherence, Information Architecture, Interaction Design, Content & Microcopy, Emotional Design & Trust, and Cognitive Load
6. Write a severity-ranked report to `docs/ux-audits/<YYYY-MM-DD>-<app>.md` with screenshots under `docs/ux-audits/<slug>/screenshots/`

The report covers:

- Product Understanding (from AGENTS.md)
- First Impression assessment
- Issues ranked by severity with HIG references and screenshot evidence
- Dimension Scorecards (7 dimensions, 5-point scale)
- Clutter and Cognitive Load deep-dive
- Accessibility Configuration Results (Dynamic Type, Dark Mode, Bold Text, touch targets)
- Concrete recommendations (preferring subtraction over addition, with effort/impact ratings)
- Quick Wins
- Strategic Observations
- Untested Areas (honest about limitations)

**Prerequisites:**
- iOS Simulator must be booted with the target app running
- Boot a simulator: `xcrun simctl boot <device-id>` or launch from Xcode

If `AGENTS.md` is missing or context is too thin, the agent will ask for product purpose, target user, and primary workflows before proceeding.
