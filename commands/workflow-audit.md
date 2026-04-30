---
description: "Conduct a workflow optimization audit of recent sessions - identifies friction, wasted turns, and high-leverage improvements"
argument-hint: "[path-to-transcripts-or-blank-for-auto-detect]"
---

Use the `workflow-auditor` agent to conduct a systematic workflow optimization audit.

The agent will:

1. Read the last 20+ session transcripts (prioritizing recent and high-turn-count sessions)
2. Compare agent configuration (AGENTS.md, CLAUDE.md) against actual session behavior
3. Analyze recent commits for effort/output mismatches
4. Classify every friction pattern by root cause (knowledge / memory / tooling / process)
5. Produce a ranked report at `docs/retro-<YYYY-MM-DD>.md`

The output includes:

- **Top 5 high-leverage changes** ranked by (time saved x frequency) / effort
- **AGENTS.md additions** - copy-paste ready, enforceable sections
- **Skills/commands to create** - with triggers, behavior, and problem citations
- **Tooling/scripts to add** - only items that remove repeated manual work
- **Process changes** - explicit critique of prompting patterns with before/after rewrites
- **Issue tickets** - ready-to-paste `br create` commands for the top 3 items

This is an optimization report, not a narrative retrospective. Every claim must cite a specific session. Generic advice is excluded.
