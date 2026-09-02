---
description: "Run a UX review of an iOS app in the Simulator: captures screenshots, tests Dynamic Type / Dark Mode / accessibility settings, and produces a severity-ranked report against Apple HIG standards"
argument-hint: "<app-bundle-id-or-name> [notes]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/ux-review-ios/SKILL.md` and follow it to conduct a UX review of the iOS app specified in $ARGUMENTS.

Read the file rather than invoking the skill by name. `commands/ux-review-ios.md` and
`skills/ux-review-ios/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(ux-review-ios)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/ux-review-ios/SKILL.md` and read it from there.

The audit operates from the `ux-product-designer-ios` role: a senior product designer working at the standard of Apple's Human Interface team. Refer to `agents/ux-product-designer-ios.md` for the role's beliefs and judgment principles.

The skill will:

1. Read `AGENTS.md` to ground the audit in the product's purpose, target user, and primary workflows
2. Verify the iOS Simulator is booted and clean the status bar for professional screenshots
3. Capture screenshots via `xcrun simctl io` and guide you through flows interactively
4. Test Dynamic Type (extra-large and XXXL), Dark Mode, and Bold Text configurations
5. Evaluate across seven dimensions: Accessibility, Design System Coherence, Information Architecture, Interaction Design, Content & Microcopy, Emotional Design & Trust, and Cognitive Load
6. Write a severity-ranked report to `docs/ux-audits/<YYYY-MM-DD>-<app>.md` with screenshots under `docs/ux-audits/<slug>/screenshots/`

**Prerequisites:**

- iOS Simulator must be booted with the target app running
- Boot a simulator: `xcrun simctl boot <device-id>` or launch from Xcode

If `AGENTS.md` is missing or context is too thin, the skill will ask for product purpose, target user, and primary workflows before proceeding.
