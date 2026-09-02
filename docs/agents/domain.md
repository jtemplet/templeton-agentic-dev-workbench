# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the
codebase. This repo is **single-context**: one `CONTEXT.md` at the root, one `docs/adr/`.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, when it exists.
- **`docs/adr/`**: read the records that touch the area you are about to work in.

If either is missing, **proceed silently**. Do not flag its absence, and do not propose creating
one up front. `mattpocock-skills:domain-modeling` creates them lazily, when a term or a decision
actually gets resolved.

Both exist here today. `CONTEXT.md` carries the glossary and the resolved collisions, and
`docs/adr/` carries seven records.

## File structure

```text
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-native-tracker-fields-are-canonical.md
│   ├── 0002-the-quality-gates-orchestrator-fans-out-to-blocking-subagents.md
│   ├── 0003-a-push-to-main-is-already-published.md
│   ├── 0004-the-pre-push-hook-forgives-by-design.md
│   ├── 0005-the-evals-are-a-measurement-not-a-gate.md
│   ├── 0006-the-style-core-ships-as-several-hook-entries.md
│   └── 0007-a-tadw-skill-wins-over-an-overlapping-external-skill.md
└── skills/ agents/ commands/ hooks/ scripts/
```

## Use the glossary's vocabulary

When your output names a domain concept, in an issue title, a refactor proposal, a hypothesis,
or a test name, use the term as `CONTEXT.md` defines it. Do not drift to a synonym the glossary
avoids.

A concept missing from the glossary is a signal. Either you are inventing language the project
does not use, so reconsider, or there is a real gap, so note it for `/domain-modeling`.

## Search the tracker before reporting a collision

`mattpocock-skills:domain-modeling` reads the code and the committed files. It does not read
the bead tracker, so a collision that was argued and settled in a closed bead looks new to it.

Before you report a naming collision, run `bd search <term>` for each spelling of the term. A
collision that a closed bead already settled is not a finding. Say which bead settled it, and
move on. Report the collision only when the search returns nothing, or when no bead it returns
settled the term.

`CONTEXT.md` records the settled ones too, under "Resolved collisions". Read that section first,
because it is faster than a search.

## Flag ADR conflicts

If your output contradicts an existing record, say so rather than overriding it in silence:

> _Contradicts ADR 0001 (native tracker fields are canonical), but worth reopening because..._

## Two rules this repo adds

**`/adr` is the preferred writer.** Two skills write into `docs/adr/` and they use different
formats. `/adr` writes the structured template: Context, Options Considered with pros and cons,
Decision, Consequences. `mattpocock-skills:domain-modeling` writes its own, which can be a
single paragraph. Both scan the directory and increment the number, so they never collide on a
filename. Prefer `/adr` when the rejected options are worth recording, which is most of the
time.

**A record earns its place when reversing the decision would cost more than a day, and somebody
would otherwise argue it again.** Anything smaller belongs in the bead's `design` field, where
it already is. A record nothing cites is a diary entry, and it makes the ones carrying real
rules harder to find.

The full rationale, including when in a session to write one, is under "Architecture Decision
Records" in [AGENTS.md](../../AGENTS.md).
