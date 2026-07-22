---
description: "Re-assert the house response style (concise, answer-first, owner-split Next actions) for this session or subagent"
---

**Read** the file `${CLAUDE_PLUGIN_ROOT}/skills/house-response-style/SKILL.md`, then follow it for
the rest of this session. If that path does not resolve, locate the file with
`Glob: **/skills/house-response-style/SKILL.md` and read it from there.

Read the file directly. Do **not** invoke it through the Skill tool: the skill sets
`disable-model-invocation: true`, so the Skill tool refuses it and this command silently does
nothing. Reading the file is what makes the always-on injection and this command share one source
of truth.

The SessionStart hook already injects this style into every parent session, so you rarely
need this command there. Reach for it when:

- A compaction or long tangent has eroded the style and you want to re-anchor it.
- You are inside a subagent, which does not inherit the parent session's injected style.
- You want to read the full ruleset (why it is shaped this way, Bad/Good examples, escape
  hatches, the pre-send check) rather than the abbreviated always-on injection.

Apply it silently; do not narrate that you have loaded it.
