---
description: "App Store Optimization audit across 10 weighted factors with a prioritized action plan"
argument-hint: "[app-id-or-package-name]"
---

Use the `aso-audit` skill to conduct a comprehensive ASO health audit.

If the user passed an App ID or package name as an argument, use it as the starting point. Otherwise, follow the skill's process and ask for the App ID, target country, and platform (iOS / Android / Both).

Before scoring, check for `app-marketing-context.md` in the working directory and read it if present. If an ASO data source is connected (Appeeky MCP, App Store Connect, Sensor Tower, etc.), pull metadata, rankings, and competitor data; otherwise ask the user to paste the metadata.

Produce the ASO Score Card, Quick Wins / High-Impact / Strategic recommendations, and competitor comparison defined by the skill's Output Format.

Write the report to `docs/aso-audits/<YYYY-MM-DD>-<app-slug>.md` (matching the `docs/ux-audits/` convention used by `/ux-audit` and `/ux-audit-ios`). Create the directory if needed.
