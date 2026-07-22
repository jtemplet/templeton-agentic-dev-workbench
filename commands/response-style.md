---
description: "Re-assert the house response style (concise, answer-first, owner-split Next actions) for this session or subagent"
---

Use the `house-response-style` skill to re-assert the house response style, and follow it for the rest of this session.

The SessionStart hook already injects this style into every parent session, so you rarely
need this command there. Reach for it when:

- A compaction or long tangent has eroded the style and you want to re-anchor it.
- You are inside a subagent, which does not inherit the parent session's injected style.
- You want to read the full ruleset (why it is shaped this way, Bad/Good examples, escape
  hatches, the pre-send check) rather than the abbreviated always-on injection.

Apply it silently; do not narrate that you have loaded it.
