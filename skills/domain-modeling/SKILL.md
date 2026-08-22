---
name: domain-modeling
description: "Build and sharpen a project's domain model as you design: challenge a term that conflicts with the glossary, sharpen fuzzy or overloaded words into one canonical term, stress-test relationships with concrete edge-case scenarios, cross-check what the user says against what the code does, and write resolved terms into CONTEXT.md the moment they crystallize. Use when discussing a codebase's terminology, writing or editing a CONTEXT.md or CONTEXT-MAP.md, naming a new concept, or when two words are being used for one thing"
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design. A shared language costs the
agent fewer tokens to think in, names variables and files consistently, and makes the codebase
easier to navigate on the next session.

This is the *active* discipline: challenging terms, inventing edge-case scenarios, and writing the
glossary down as decisions crystallize. Merely *reading* `CONTEXT.md` for vocabulary is not this
skill; that is a habit any skill can have. Reach for this skill when you are changing the model,
not just consuming it.

## File structure

Most repositories have a single context:

```text
/
├── CONTEXT.md
├── docs/
│   └── decisions/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repository has several contexts, and the map points
to where each one lives.

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/domain-modeling/CONTEXT-FORMAT.md` for both layouts and the
glossary format. If that path does not resolve, locate it with
`Glob: **/skills/domain-modeling/CONTEXT-FORMAT.md`.

Create files lazily: only when you have something to write. If no `CONTEXT.md` exists, create one
when the first term is resolved.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the language already in `CONTEXT.md`, call it out
immediately. "Your glossary defines cancellation as X, but you seem to mean Y. Which is it?"

### Sharpen fuzzy language

When the user uses a vague or overloaded word, propose one precise canonical term. "You said
account. Do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are on the table, stress-test them with specific scenarios. Invent cases
that probe the edges and force the user to be precise about where one concept stops and the next
starts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. Surface any
contradiction: "Your code cancels a whole Order, but you just said a partial cancellation is
possible. Which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Do not batch these up; capture them as
they happen.

`CONTEXT.md` is a glossary and nothing else. Keep every implementation detail out of it. It is not
a spec, not a scratch pad, and not a home for implementation decisions.

## Offer an ADR sparingly

Only offer to record a decision when all three are true:

1. **Hard to reverse.** The cost of changing your mind later is meaningful.
2. **Surprising without context.** A future reader will wonder why it was done this way.
3. **The result of a real trade-off.** There were genuine alternatives and one was picked for
   specific reasons.

If any of the three is missing, skip it. An easy-to-reverse decision just gets reversed; an
unsurprising one raises no question; a decision with no alternative records nothing beyond "we did
the obvious thing."

When all three hold, hand the writing to the `architecture-decision-record` skill, which owns the
ADR format and writes to `docs/decisions/`. Do not invent a second ADR layout here.

## Where this fits

| Situation | Skill or command |
|---|---|
| Interviewing the user, and the terms are still fuzzy | `grilling`, run alongside this skill |
| A decision the discussion settled needs recording | `architecture-decision-record` |
| The vocabulary is settled and the plan is next | `/plan-feature` |

---

Adapted from Matt Pocock's `domain-modeling` skill, MIT licensed:
<https://github.com/mattpocock/skills>. The ADR half of the original was dropped, because
`architecture-decision-record` already owns that format in this plugin.
