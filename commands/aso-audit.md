---
description: "App Store Optimization audit across 10 weighted factors with a prioritized action plan"
argument-hint: "[app-id-or-package-name]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/aso-audit/SKILL.md` and follow it to conduct a comprehensive ASO health audit.

Read the file rather than invoking the skill by name. `commands/aso-audit.md` and
`skills/aso-audit/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(aso-audit)` returns this file and never reaches the skill.

If the user passed an App ID or package name as an argument, use it as the starting point. Otherwise, follow the skill's process and ask for the App ID, target country, and platform (iOS / Android / Both).

Before scoring, check for `app-marketing-context.md` in the working directory and read it if present. If an ASO data source is connected (Appeeky MCP, App Store Connect, Sensor Tower, etc.), pull metadata, rankings, and competitor data; otherwise ask the user to paste the metadata.

Produce the ASO Score Card, Quick Wins / High-Impact / Strategic recommendations, and competitor comparison defined by the skill's Output Format.

Write the report to `docs/aso-audits/<YYYY-MM-DD>-<app-slug>.md` (matching the `docs/ux-audits/` convention used by `/ux-audit` and `/ux-audit-ios`). Create the directory if needed.
