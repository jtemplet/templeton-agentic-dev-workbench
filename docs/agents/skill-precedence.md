# Skill precedence: tadw over mattpocock-skills

Both plugins are installed, and their skills overlap. **Where a tadw skill and a
`mattpocock-skills` skill answer the same question, use the tadw one.** This is a standing
instruction, not a preference to weigh case by case.

Two exceptions are listed at the bottom, and they are deliberate.

## Why tadw wins by default

The tadw skills are built around this repository's tracker, its house style, and its gates.
They write bd beads with the native `acceptance_criteria`, `design`, and `notes` fields that
[ADR 0001](../adr/0001-native-tracker-fields-are-canonical.md) makes canonical. They ground
their claims against the code on `main`. They emit the machine-readable lines the pipelines
read. A skill that files a GitHub issue, or writes acceptance criteria into a description body,
produces work the rest of the pipeline cannot consume.

## Use these instead

| Instead of | Use | Because |
|---|---|---|
| `mattpocock-skills:to-tickets` | `/plan-to-beads` | Wires blocking edges with `bd dep add`, and fills the native tracker fields per ADR 0001 |
| `mattpocock-skills:to-spec` | `/write-plan`, then `/plan-to-beads` | Writes the canonical 11-section plan template that `/plan-review` grades and `/plan-to-beads` decomposes |
| `mattpocock-skills:to-spec`, for work that fits one bead | `/bead-create` | Searches for a duplicate first, grounds every claim against `main`, self-audits the draft, and reads the bead back to prove it landed |
| `mattpocock-skills:triage` | `/triage-beads` | Ranks by value over effort with evidence cited per point, is deterministic on the same tracker state, and never edits a bead |
| `mattpocock-skills:code-review` | `/code-review` | Detects the language and dispatches to `review-python`, `review-rails`, `style-swift`, `style-frontend`, or `terraform-iac-expert` |
| `mattpocock-skills:diagnosing-bugs` | `/diagnose` | The `diagnostician` agent has no Edit or Write access, so it cannot start fixing before it has explained |
| `mattpocock-skills:implement` | `/build` | Reads the spec from `bd` rather than the transcript, implements criterion by criterion with a test each, then simplifies and lints |
| `mattpocock-skills:tdd` | `style-testing` | One behavior per test, hoisted setup, deterministic clocks, and a list of what not to test |
| `mattpocock-skills:research` | `/research-ingest`, `/research-synthesize` | Weighs each claim by the source's recorded validity, and keeps the wiki and its index current |
| `mattpocock-skills:grilling` | `/grill-me` | tadw's own `grilling` skill, adapted from his under MIT and since diverged |

## Where the overlap is partial

**`mattpocock-skills:resolving-merge-conflicts`.** The `ship` skill resolves exactly two paths
mechanically, `.beads/issues.jsonl` and `CHANGELOG.md`, and stops on any other conflicted path
by design. Use his skill for a source conflict, which is the case `ship` refuses to judge.

**`mattpocock-skills:wayfinder`.** It plans work too large for one agent session as a map of
decision tickets. `/plan-to-beads` plus `bd dep add` covers the dependency graph, but nothing in
tadw covers the "resolve one unknown at a time until the way is clear" loop. Use his when the
destination itself is unclear.

## Use his, not yours

**`mattpocock-skills:domain-modeling`.** tadw had its own and deleted it on 2026-08-28 in favor
of this one. The records directory was renamed from docs/decisions to `docs/adr/` so that this
skill, which cannot be told where to write, lands them where everything here reads. It is named in the AGENTS.md
routing table, in `docs/ROUTING.md`, in `skills/architecture-decision-record/SKILL.md`, and in
`skills/grilling/SKILL.md`.

**`mattpocock-skills:grill-with-docs`.** `/write-plan` names it, alongside `/grill-me`, as a
valid step to follow. Reach for it over `/grill-me` when the interview should also produce ADRs
and glossary entries as it goes.

## No tadw equivalent exists

Nothing here competes with `codebase-design`, `improve-codebase-architecture`, `prototype`,
`wizard`, or `ask-matt`. Use them as they are.
