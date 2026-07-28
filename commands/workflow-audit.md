---
description: "Scan recent sessions for repeated friction and output ranked fixes with issue tickets"
argument-hint: "[session-count-or-path]"
---

Use the `workflow-auditor` agent to scan recent sessions for workflow friction.

The agent will:

1. Read the last 10 sessions (or specify a count/path as argument)
2. Extract repeated friction: corrections, retries, re-explanations
3. Classify root causes and rank by impact
4. Output a short report to `docs/retro-<YYYY-MM-DD>.md` with fixes and `br create` tickets

Lightweight enough for weekly use. Stops early if findings are thin.
