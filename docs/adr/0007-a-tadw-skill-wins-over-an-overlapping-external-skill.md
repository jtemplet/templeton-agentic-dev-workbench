# 0007. A tadw skill wins over an overlapping external skill

**Date:** 2026-09-01
**Status:** Accepted

## Context

The `mattpocock-skills` plugin is installed alongside this one, and its engineering skills
overlap this plugin's substantially. Ten pairs answer the same question:

| `mattpocock-skills` | tadw |
|---|---|
| `to-tickets`, `to-spec` | `/plan-to-beads`, `/write-plan`, `/bead-create` |
| `triage` | `/triage-beads` |
| `code-review` | `/code-review` |
| `diagnosing-bugs` | `/diagnose` |
| `implement` | `/build` |
| `tdd` | `style-testing` |
| `research` | `/research-ingest`, `/research-synthesize` |
| `grilling` | `/grill-me` |

Two of them share a bare name: `code-review` and `grilling` exist in both plugins. Namespaced
invocation is unambiguous, but a model choosing a skill from its description alone sees two
plausible candidates and nothing that ranks them.

The overlap is not accidental. `skills/grilling/SKILL.md` records that it was adapted from Matt
Pocock's skill under MIT, and the beads that created it and the deleted `domain-modeling` skill
both cite the source.

The consequences of picking the wrong one are concrete, not stylistic. `to-tickets` files a
GitHub issue; this repository tracks work in bd, so the issue lands in a queue nothing reads.
`to-spec` writes acceptance criteria into a description body; [ADR
0001](0001-native-tracker-fields-are-canonical.md) makes the native `acceptance_criteria` field
canonical, so the result fails this repository's own audit. Neither failure is loud.

Two skills run the other way. This plugin **deleted** its own `domain-modeling` on 2026-08-28 in
favor of `mattpocock-skills:domain-modeling`, and renamed its records directory from
docs/decisions to `docs/adr/` so that skill, which cannot be told where to write, lands records
where everything here reads. Five files named it before this decision: AGENTS.md, `README.md`,
`docs/ROUTING.md`, `skills/architecture-decision-record/SKILL.md`, and `skills/grilling/SKILL.md`. Separately, `/write-plan` names
`mattpocock-skills:grill-with-docs` as a valid predecessor, in its frontmatter, its body, and
`docs/ROUTING.md`.

## Options Considered

### Option A: A standing rule that tadw wins, with named exceptions

State once that the tadw skill wins on overlap, list the swaps, and list the two skills that stay
external.

- **Pros:** One rule to remember, and the exceptions are enumerated rather than judged case by
  case. Protects the tracker contract, which is where a wrong choice does real damage.
- **Cons:** A blanket rule can be wrong in a case nobody anticipated. It also means preferring a
  tadw skill even where the external one is genuinely better.

### Option B: Decide case by case

Leave both installed and let each session pick on the merits.

- **Pros:** Always picks the better skill for the situation, in principle.
- **Cons:** In practice the chooser is a model reading two descriptions, neither of which mentions
  the other. The tracker damage above happens quietly, and nothing in the transcript reveals it.
  Re-deciding the same question every session is how vocabulary and process drift.

### Option C: Uninstall the overlapping external skills

Remove `mattpocock-skills` and keep only what this plugin ships.

- **Pros:** No ambiguity at all.
- **Cons:** Loses `domain-modeling`, which this repository deliberately adopted and four files
  cite, and `grill-with-docs`, which `/write-plan` names. Also loses five skills with no tadw
  equivalent: `codebase-design`, `improve-codebase-architecture`, `prototype`, `wizard`, and
  `ask-matt`. Throws away the good to remove the ambiguous.

## Decision

**Option A. Where a tadw skill and a `mattpocock-skills` skill answer the same question, use the
tadw one.** It is a standing rule, not a preference to weigh each time.

The reason is contract, not quality. The tadw skills write bd beads with the native fields ADR
0001 makes canonical, ground their claims against the code on `main`, and emit the machine
lines the pipelines read. A skill that files elsewhere, or writes criteria into a body, produces
work the rest of the pipeline cannot consume.

**Two skills stay external, and they are the whole exception list:** `domain-modeling`, which
this plugin deleted its own in favor of, and `grill-with-docs`, which `/write-plan` names.

**Two overlaps are partial and are recorded as such.**
`mattpocock-skills:resolving-merge-conflicts` covers the source conflicts the `ship` skill
refuses to judge by design. `mattpocock-skills:wayfinder` covers planning work too large for one
session, which `/plan-to-beads` does not do. Five external skills have no tadw equivalent at all
and are used as they are.

The full mapping lives in `docs/agents/skill-precedence.md`, and the rule is summarized in the
`## Agent skills` section of AGENTS.md.

Option B lost because the chooser is a model reading descriptions that do not mention each other,
so "decide on the merits" is not a mechanism. Option C lost because it removes seven useful
skills to resolve ambiguity in ten.

## Consequences

**Easier:**

- One rule settles ten pairs, and the two exceptions are named rather than remembered.
- Work filed by a skill always lands in bd with the native fields populated, so the audit,
  refinement, and dashboard tooling can read it.
- A new overlap has an obvious default, so adding an external plugin does not require re-arguing
  this.

**Harder:**

- The rule lives in documents that a model does not read at the moment it picks a skill. For the
  two bare-name collisions, `code-review` and `grilling`, nothing at the point of choice ranks
  them, so the descriptions themselves are the only durable fix.
- Preferring the tadw skill sometimes means preferring the weaker one. The rule accepts that
  trade for the contract it protects.
- The exception list has to be maintained. If this plugin ever ships its own `domain-modeling`
  again, this record and four other files need updating together.
