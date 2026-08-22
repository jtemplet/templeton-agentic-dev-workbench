---
description: "Get relentlessly interviewed about a plan, design, or decision until every branch of the design tree is resolved"
argument-hint: "[what to grill me about]"
---

Use the `grilling` skill to interview me about the topic in the arguments. If no argument is
given, grill me about whatever this conversation has been about.

Invoking the skill by name is safe here: `grill-me` and `grilling` are different names, so
`Skill(grilling)` reaches `skills/grilling/SKILL.md` and not this file.

The skill will:

1. Model the open questions as a design tree and compute the **frontier**: the questions whose
   prerequisites are already settled
2. Ask the whole frontier in one numbered round, with a recommended answer per question, then wait
3. Find every fact itself (dispatching subagents for the slow ones) and ask me only for decisions
4. Recompute the frontier from my answers and ask the next round
5. Stop when the frontier is empty, and wait for me to confirm we are aligned before acting

Ask questions. Do not write code, plans, or beads during the interview.
