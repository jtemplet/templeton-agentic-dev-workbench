# Bead Body Contract

This file defines nine bead body sections. It says what each section is called, which `bd` field
holds it, and how to write the sentences inside it. Write a bead against this file and nothing
else. No single bead carries all nine: the type decides which ones are required, and the table
below gives the type for each.

This file is the one owner of that shape. Four skills read it and keep no copy of it:
`skills/bead-create/SKILL.md`, `skills/bead-audit/SKILL.md`, `skills/plan-to-beads/SKILL.md`, and
`skills/bead-refine/SKILL.md`. This file wins wherever one of them disagrees with it. Confirm that
all four still point here with
`grep -l bead-body-contract skills/bead-*/SKILL.md skills/plan-to-beads/SKILL.md`.

## The Ask line

Every bead description starts with an `**Ask:**` line. It is the first line of the `description`
field, followed by one blank line. It is one sentence of 20 words or fewer, and it says what the
bead wants done.

```markdown
**Ask:** Remove the two tadw hooks copied into `.beads/hooks`, so only `.githooks` holds them.
```

The title names the work. The Ask line says what changes. Write the Ask line as an instruction, not
as a description of a problem. The problem belongs under `## Why (Computational)` below it.

The Ask line goes in `description` and in no other field. `bd` has no native field for it, and
`description` is the field a bulk read returns. `bd list --json` returns 16 keys per bead,
including `description`; derive them with
`bd list --limit 1 --json | python3 -c 'import json,sys; print(sorted(json.load(sys.stdin)[0]))'`.
Plain `bd list` prints the title alone, so the Ask line reaches a tool reading the backlog rather
than a person scrolling one.

## Where each section goes

`bd` has four fields that hold a bead body: `description`, `design`, `notes`, and
`acceptance_criteria`. A section belongs in its native field. Never put a section in the
description body when a native field exists for it.
[ADR 0001](adr/0001-native-tracker-fields-are-canonical.md) records that decision and the two
options that lost.

<!-- section-table:start -->
| Section | Goes in this `bd` field | Heading to write | Required for |
|---|---|---|---|
| Ask | `description` | none; it is the first line | all types |
| Why | `description` | `## Why (Computational)` | all types |
| Estimated size | `description` | `## Estimated size` | task, feature, bug |
| Steps to Reproduce | `description` | `## Steps to Reproduce` | bug |
| Success Criteria | `description` | `## Success Criteria` | epic, milestone |
| How | `design` | none; write the content alone | all types |
| Done when | `notes` | `## Done when (Acceptance)` | all types |
| Out of scope | `notes` | `## Out of scope` | optional, any type |
| Acceptance Criteria | `acceptance_criteria` | none; write the list alone | task, feature, bug |
<!-- section-table:end -->

`skills/bead-audit/scripts/test_container_contract.py` reads the table between the two comments
above. Keep the four columns, and write each type name in the last column exactly as `bd` spells
it.

The flags that write these four fields are `-d`, `--design`, `--notes`, and `--acceptance`. `bd`
rejects `--acceptance-criteria` as an unknown flag.

An operational bead, such as a config change or a manual production step, writes
`N/A (operational)` as its size instead of a band.

## Containers: epic and milestone

A container is a bead that holds other beads and produces no diff of its own. `bd` has two
container types, and this contract gives both the same body.

| Type | What it holds |
|---|---|
| `epic` | A large body of work, as the child beads that deliver it |
| `milestone` | A deliverable a stakeholder can see, as the beads that must close to reach it |

**A container carries five sections: Ask, Why, How, Done when, and Success Criteria.** The How
goes in `design` and the Done when goes in `notes`, the same as for every other type.

**A container carries no Estimated size and no Acceptance Criteria.** Both describe one diff, and
a container has none. Leave the `acceptance_criteria` field empty. A missing size on a container
is correct, and no audit counts it as a fault.

**Success Criteria is the section a container cannot omit.** Write each line so that a
stakeholder who has read none of the child beads can judge it. A stakeholder is a person who
wants the result and does not build it. Name a result that person can see, measure, or use.

| Do not write | Write |
|---|---|
| All 4 child beads are closed | A developer can turn a reviewed plan into beads without a manual fix |
| `test_publish.py` passes | A publish that stops halfway leaves no duplicate bead |

A line that only a builder can check belongs in the Acceptance Criteria of a child bead.

The How of a container says how the work is divided and in what order. It names no file to edit.
The Done when of a container says which child work must be verified before the container closes.

**A milestone bead is not a table row in `docs/milestones.md`.** That file maps a label to a goal
for `/bead-refine`. A milestone bead is a `bd` bead whose type is `milestone`. This contract
governs the bead alone.

## Two fields carry headings, and two do not

The `description` and `notes` fields each hold more than one section, so each section inside them
needs a heading to tell them apart. The `design` and `acceptance_criteria` fields each hold exactly
one section, so a heading inside them repeats what the field name already says.

Write `## How (Algorithmic)` nowhere. The `design` field is the How. Write `## Acceptance Criteria`
nowhere. The `acceptance_criteria` field is the Acceptance Criteria.

Every heading above is byte-exact. `## Why` and `## Why (Computational)` are not the same heading,
and a bead that uses the first one reads as a bead missing the section.

## Done when and Acceptance Criteria are different

A bead needs both, and neither restates the other.

**Done when** states the outcome in the words of the person doing the work. It describes the end
state. It goes in `notes`.

**Acceptance Criteria** is the checklist a second person walks. Each line is pass or fail with no
judgment left to make. It goes in `acceptance_criteria`.

The test is who reads the line. If you can hand the line to a reviewer, and they can mark it pass
or fail without asking you a question, it is an Acceptance Criteria line. If it describes the
finished state in your own words, it is a Done when line.

```markdown
## Done when (Acceptance)

- Repeated failed logins from one source are throttled.
- The threshold is configurable without a redeploy.
```

```markdown
1. Given 5 failed logins in 60s from one IP, when a 6th is attempted, then the response status
   is 429.
2. Given the RATE_LIMIT env var is changed, when config reloads, then the new limit applies
   without a process restart.
```

## Sentence rules

These ten rules are copied from `skills/style-markdown/SKILL.md`, with its numbering. They are
copied here, and not linked, on purpose. A summary of these rules once cut ten of them down to
four, and the four that survived stated no rule at all. Apply every rule to every sentence in a
bead body.

Simplified Technical English is a controlled-English standard, specified in ASD-STE100. Use its
writing rules, never its licensed dictionary, which you cannot open. The ten rules below are the
whole of what to apply. Do not add a rule you half-remember from the standard itself.

1. **One word for one thing.** Pick a word for something and use only that word. A second word
   reads as a second thing. If you call it a bead in one line, do not call it a ticket later.

2. **Thirty words per sentence, maximum.** Twenty when the sentence tells the reader to do
   something. Long sentences are two statements joined. Cut them at "which", "so", "but",
   "because", ", meaning", and ", making".

3. **Name the thing, not a picture of it.** A reader cannot unpack a metaphor. Every word on the
   right below names a real mechanism.

   | Do not write | Write |
   |---|---|
   | wire it up | add the hook to `settings.json` |
   | surface it | show it |
   | handle it | retry it, or write it to the log and stop |
   | leverage | use |
   | the row, the entry, the item | the table row, the bead, the line in the report |
   | it lands in `main` | it merges into `main` |

4. **No jargon.** If a word needs a gloss, write the gloss instead. One exception: an exact
   technical name stays as it is, because the reader has to type or search for it. Keep
   `TADW_STYLE_CORE`, `git rebase`, and `skills/quality-gates/SKILL.md` verbatim.

5. **Define a term in the sentence that uses it.** Do this even for terms an engineer reads
   fluently. Write "the script is idempotent, meaning running it twice does what running it once
   does".

6. **Active voice, and the imperative for steps.** Write "the deploy job clears the cache", not
   "the cache is cleared".

7. **Positive form, and the condition before the instruction.** Write "Run this only when the
   backup is less than a day old".

8. **Plain words.** Write "that is" not `i.e.`, "for example" not `e.g.`, "and so on" not `etc.`
   Never stack more than three nouns. Write "the timeout for the connection pool".

9. **American spelling.** Write color, behavior, initialize, canceled, analyze. A name you do not
   own stays as it is, so an API field called `colour` keeps its spelling.

10. **No em-dash and no en-dash.** Use a comma, semicolon, colon, parentheses, or a new sentence.
    For a missing value use a plain hyphen. Quoted text and code samples keep their punctuation.

## Every number in a bead is a claim

A stale number looks exactly like a fresh one. Write the command that produces the number beside
the number.

Write "the copy runs 10 checks and `.githooks/pre-push` runs 18; derive both with
`grep -c '^check ' <path>`". Do not write "the copy runs fewer checks".

## A complete bead

This is every field of one task, written to this contract.

```text
description:
  **Ask:** Remove the two tadw hooks copied into `.beads/hooks`, so only `.githooks` holds them.

  ## Why (Computational)

  `.beads/hooks/pre-push` is a tracked copy of the hook in `.githooks`. The copy runs 10 checks
  and `.githooks/pre-push` runs 18. Derive both with `grep -c "^check " <path>`.

  ## Estimated size

  2 files deleted, band: Small.

design:
  Delete the two copies. Keep the four beads shims. Then add one check to
  `.githooks/test_prepush.py`, so a new copy fails the suite.

notes:
  ## Done when (Acceptance)

  - Only the four beads shims remain under `.beads/hooks`.

  ## Out of scope

  - Changing `core.hooksPath` from a committed file. Git does not read local config from the tree.

acceptance_criteria:
  1. Given the repository, when `.beads/hooks` is listed, then it holds exactly the four beads
     shims and no tadw hook.
```

## A complete milestone

This is every field of one milestone, written to this contract. It has no `## Estimated size`
section and no `acceptance_criteria` field.

```text
description:
  **Ask:** Deliver safe publication, so a plan becomes beads that are ready only when valid.

  ## Why (Computational)

  A developer who publishes a plan today can see half of its beads as ready work. A publish that
  stops halfway leaves beads with no dependency on the bead that must come first.

  ## Success Criteria

  - A developer can publish a reviewed plan and start the first bead with no manual fix.
  - A publish that stops halfway shows no bead as ready, and a second run adds no duplicate.

design:
  Publish every bead on hold first. Add the dependencies next, and release the holds last. The
  three child beads follow that order, and each one ships alone.

notes:
  ## Done when (Acceptance)

  - The three child beads are closed, and each one has a recorded acceptance verdict.
  - One reviewed plan was published from start to finish with the released skill.

  ## Out of scope

  - Moving an existing backlog into the new hierarchy.
```
