# Feature Plan: Readable Beads and a Route Column for Refine

**Date:** 2026-09-07
**Status:** Draft

**Decomposed:** 2026-09-07, into 10 beads labeled `plan:readable-beads`.

**Revised 2026-09-07** after `/plan-review`. Seven changes: consumer
repositories covered, the eval fixture named and re-estimated, two counts corrected, `bead-refine`
added to milestone 2, criterion 11 split, the model-call cost added, and the 20-word cap marked
provisional.

## Summary

A bead is one unit of trackable work in bd. Today a person cannot read a bead and tell what it
asks for, and `/bead-refine` prints its questions in a shape nobody can follow. This plan adds one
plain sentence to the top of every bead, moves the writing rules into one file that four skills
read, and gives `/bead-refine` a route column that says whether a bead serves a milestone or is a
detour.

## Motivation

Three problems were reported by the plugin's owner. Each one was traced to a cause in the files.

| Problem | Cause found |
|---|---|
| A bead does not say what it asks for | No bead states its ask in one sentence. The description of `tadw-w87` is one paragraph of 160 words that names three git commands |
| `/bead-refine` does not talk to the reader | Step 6 of `skills/bead-refine/SKILL.md` prints a table of 13 columns. A terminal wraps it into text nobody can read |
| Same | Step 5 asks through `AskUserQuestion`. That widget caps its header at 12 characters, so the reasoning never reaches the reader |
| The writing rule did not bind | `skills/bead-refine/SKILL.md` carries 4 rules, `skills/house-response-style/SKILL.md` carries 8, and `skills/style-markdown/SKILL.md` carries 10. All three name the same standard |
| A detour cannot be told from the direct route | Nothing in this repository states a schedule. No bead carries a due date, and no roadmap file exists |

Who benefits: the person who reads the backlog and decides what to build. The backlog is the set
of beads that are not closed. It holds 57 beads today, counted with
`bd list --status open,blocked --limit 0 --json`.

## Scope

### In Scope

- `docs/bead-body-contract.md`, one file that owns the bead body shape and the writing rules.
- An `**Ask:**` first line in every bead description, added once and repaired on every later touch.
- A reading level of fourteen years old, set in the 6 files that state a reading level
  today, across 9 lines.
- `skills/bead-audit/scripts/check_bead_body.py` and its test, both run by `.githooks/pre-push`.
- A one-off pass that prepends the `**Ask:**` line to all 57 beads in the backlog.
- An `Ask` dimension in `skills/bead-audit/SKILL.md`, weighted 10, with a grace rule that
  scores a bead N/A on that dimension when its description has no `**Ask:**` line at all.
- `docs/milestones.md`, drafted from the 12 plan documents and the 13 beads that carry a
  `plan:<name>` label, with every date left as a plain hyphen.
- A route column in `skills/bead-refine/SKILL.md`, a fifth suspicion signal, a table of 6 columns,
  a worked example, `**Ask:**` repair, two route lines in the closing summary, and an `overbuilt`
  label.
- `commands/bead-refine.md` updated to match the skill.
- `evals/cases/bead-refine-round/case.json`, one eval case with a fixture tracker.

### Out of Scope

- Renaming the heading `## Why (Computational)`. That heading appears in 35 files, counted with
  `grep -rln "Done when\|Why (Computational)" --include='*.md' .`, and 8 of those are audit
  fixtures. The rename buys a better heading and nothing else.
- An eighth verdict named `Overbuilt`. It would overlap `Shrink` for a bead that is partly useful,
  and `Kill` for a bead that is wholly premature. Two runs would then file the same bead
  differently.
- Any change to `skills/triage-beads/SKILL.md`. A bead kept knowing it is hardening is a bead the
  reader decided to build.
- Rewriting the prose of all 57 bead bodies in one pass. Prose is rewritten one theme at a time,
  where the reader sees it.
- Filling in the dates in `docs/milestones.md`. Those are the owner's to write.
- Running the one-off pass in any repository other than this one. This plugin publishes at
  version 4.2.0 and installs into other repositories from a marketplace. Each of those owns its
  own tracker, and its owner runs the pass when they choose to.
- Making the evals a gate. [ADR
  0005](../adr/0005-the-evals-are-a-measurement-not-a-gate.md) forbids it.

## Technical Approach

### Architecture

Four skills write or grade a bead body: `bead-create`, `bead-audit`, `plan-to-beads`, and
`bead-refine`. Each carries its own copy of the body shape today, and the copies drifted. [ADR
0001](../adr/0001-native-tracker-fields-are-canonical.md) records what that drift already cost:
every bead this repository generated failed its own auditor.

The fix is one file the four skills read. `docs/bead-body-contract.md` holds the section list, the
map from section to native field, the `**Ask:**` line, and all 10 Simplified Technical English
rules copied from `skills/style-markdown/SKILL.md`. Simplified Technical English is a controlled
form of English, specified in ASD-STE100. A native field is one of bd's first-class `design`,
`notes`, and `acceptance_criteria` columns.

`/bead-refine` gains a second yardstick. Today it measures a bead against a purpose it infers from
a file. It will also measure the bead against `docs/milestones.md`, and record the answer as a
route: `on route`, `detour`, or `hardening`.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `docs/bead-body-contract.md` | Owns the bead body shape and the writing rules | New |
| `docs/milestones.md` | Names each milestone, its date, and the label that maps beads to it | New |
| `skills/bead-audit/scripts/check_bead_body.py` | Checks the `**Ask:**` line, the reading level, and a prepend-only edit | New |
| `skills/bead-audit/scripts/test_check_bead_body.py` | Proves the check script | New |
| `evals/cases/bead-refine-round/case.json` | Measures what the Step 6 round prints | New |
| `skills/bead-refine/SKILL.md` | Route, fifth signal, 6 columns, worked example, Ask repair, route lines | Modified |
| `skills/bead-audit/SKILL.md` | Gains the `Ask` dimension at weight 10, with a grace rule for a bead that has no `**Ask:**` line | Modified |
| `skills/bead-create/SKILL.md` | Reads the contract, writes the `**Ask:**` line | Modified |
| `skills/plan-to-beads/SKILL.md` | Reads the contract, writes the `**Ask:**` line | Modified |
| `commands/bead-refine.md` | Matches the reworked skill | Modified |
| `skills/style-markdown/SKILL.md` | Reading level fourteen, 2 lines | Modified |
| `skills/house-response-style/SKILL.md` | Reading level fourteen, 3 lines | Modified |
| `skills/write-plan/SKILL.md` | Reading level fourteen, 1 line | Modified |
| `agents/feature-planner.md` | Reading level fourteen, 1 line | Modified |
| `docs/ROUTING.md` | Reading level fourteen, 1 line | Modified |
| `.githooks/pre-push` | Runs the new check and its test | Modified |

### Test Seams

A seam is the place a test drives the work through.

| Seam | Existing or new | What it proves |
|---|---|---|
| `skills/bead-audit/scripts/check_bead_body.py`, driven by `test_check_bead_body.py` | New files, existing pattern | A description starts with the `**Ask:**` line; its Flesch-Kincaid grade is 9 or below after code spans and paths are removed; a prepend-only edit changed nothing else |
| `evals/cases/bead-refine-round/case.json`, driven by `evals/run.py` | Existing harness, new case | The Step 6 round prints 6 columns, fills the route cell, keeps every `Why` cell to 15 words or fewer, and uses none of the forbidden words |

The first seam is the highest one that can check 57 real bead bodies with no model call, so it is
free and it can gate. The second is the only seam that sees what the skill prints, which is the
reported failure. It measures and never gates.

The repository already holds 12 files named `test_*.py`. `.githooks/pre-push` runs a script and
its test as a pair, at lines 144 and 145 for `check_doc_paths.py`. The new check follows that
shape.

### Data Model

Two fields change on a bead, and both are existing bd fields.

| Field | Change |
|---|---|
| `description` | Gains a first line, `**Ask:** <one sentence, under 20 words>`, then a blank line |
| `labels` | Gains `overbuilt` on every bead whose route is `hardening` |

The `**Ask:**` line goes in `description` and not in bd's `--context` field. `bd list --json`
returns 16 keys and `context` is not one of them, so the one bulk read `/bead-refine` makes would
never see it.

### API / Interface

`docs/milestones.md` holds one table with four columns: milestone, target date, what it delivers,
and the `plan:<name>` label that maps beads to it.

`/bead-refine` changes what it prints in three places.

1. The theme table in Step 5 gains a column, `Off route`, counting the beads in that theme whose
   route is `hardening` or `detour`.
2. The bead table in Step 6 falls from 13 columns to 6: `# | ID | Title | Route | Verdict | Why`.
   Age, idle, blocks, blocked by, serves, and target move into the `Detail` list below the table.
3. The closing summary in Step 8 gains two lines. One counts the route values in the theme just
   refined. One counts them across the whole backlog.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| [0001](../adr/0001-native-tracker-fields-are-canonical.md) | A section belongs in its native bd field, not in the description body | The contract file carries that map, and the `**Ask:**` line stays in `description` because no native field holds it |
| [0005](../adr/0005-the-evals-are-a-measurement-not-a-gate.md) | The evals measure and never gate | The new eval case is excluded from `.githooks/pre-push`, and the check script is the only thing that gates |
| [0009](../adr/0009-the-large-skill-documents-are-not-split.md) | A large skill document is not split into reference files | The contract file removes 3 copies of one rule set across 4 skills. It does not move one skill's own prose out of that skill |

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Write the contract | Create `docs/bead-body-contract.md` with the section list, the native-field map, the `**Ask:**` line, and all 10 Simplified Technical English rules | M | The file exists and `rumdl check docs/bead-body-contract.md` exits 0 |
| 2 | Set the reading level | Change every reading level to fourteen years old, in all 6 files, including `skills/bead-refine/SKILL.md` | S | `grep -rn "ten-year-old" --include='*.md' .` returns no line outside `CHANGELOG.md` and `docs/plans/` |
| 3 | Build the check | Add `check_bead_body.py` and `test_check_bead_body.py` under `skills/bead-audit/scripts/` | M | `python3 skills/bead-audit/scripts/test_check_bead_body.py` exits 0 |
| 4 | Run the one-off pass | Write the first 10 `**Ask:**` lines and check whether 20 words holds for a bug and for an epic, then prepend a line to the remaining 47, changing nothing else | L | Every bead in `bd list --status open,blocked --limit 0 --json` has a description starting `**Ask:**`, and the check script passes on all of them |
| 5 | Turn the gate on | Add both new commands to `.githooks/pre-push`, and add the `Ask` dimension at weight 10, and its grace rule, to `skills/bead-audit/SKILL.md` | S | `.githooks/pre-push` runs the test and the check, and a bead with no `**Ask:**` line scores below its old score |
| 6 | Draft the milestones | Write `docs/milestones.md` from the 12 plan documents and the 13 beads labeled `plan:<name>`, with every date a plain hyphen | M | The file lists every `plan:<name>` label found in the tracker, and no date cell holds a guess |
| 7 | Rework the refine skill | Point `bead-refine`, `bead-create`, and `plan-to-beads` at the contract, delete the 4-rule paraphrase, add the route, the fifth signal, the 6-column table, the worked example, the `**Ask:**` repair, the route lines, and the `overbuilt` label. Update `commands/bead-refine.md` to match | L | A `/bead-refine` run on this repository prints a 6-column table with a filled route cell, and its closing summary holds both route lines |
| 8 | Add the eval case | Create `evals/fixtures/bead-refine-round/base/`, holding a small `.beads/issues.jsonl`, and `evals/cases/bead-refine-round/case.json` that names it. The case runs `bd init` then `bd import` before the round | L | `python3 evals/run.py --case bead-refine-round` completes and reports a grade |

## Acceptance Criteria

1. Given any bead in the backlog, when its description is read, then its first line is
   `**Ask:**` followed by one sentence. The limit is 20 words, and it is provisional until
   milestone 4 measures the first 10 beads.
2. Given a bead description, when `check_bead_body.py` runs on it, then the command reports a
   failure for a missing `**Ask:**` line, and reports a failure for a Flesch-Kincaid grade above 9
   once code spans and paths are removed.
3. Given the one-off pass has run on a bead, when the new description is compared to the old one,
   then the only difference is the added `**Ask:**` line and one blank line.
4. Given a push, when `.githooks/pre-push` runs, then it runs both
   `test_check_bead_body.py` and `check_bead_body.py`, and it does not run `evals/run.py`.
5. Given the repository, when `grep -rn "ten-year-old" --include='*.md' .` runs, then every
   remaining line is in `CHANGELOG.md` or under `docs/plans/`.
6. Given the four skills that write or grade a bead body, when each is read, then each points at
   `docs/bead-body-contract.md` and none carries its own copy of the writing rules.
7. Given `docs/milestones.md` exists and is confirmed, when `/bead-refine` judges a bead, then the
   route cell holds `on route`, `detour`, or `hardening`, and `hardening` is tested before
   `detour`.
8. Given `docs/milestones.md` is missing, when `/bead-refine` runs, then it infers the milestone
   names, waits for a correction, writes the file with every date a plain hyphen, and says the
   schedule is unknown.
9. Given a theme is presented in Step 6, when the table is read, then it holds exactly 6 columns,
   and every `Why` cell holds one sentence of 15 words or fewer.
10. Given a bead whose route is `hardening`, when its verdict is applied, then the bead carries
    the label `overbuilt`, whether it was kept or closed.
11. Given a verdict that leaves a bead alive, when it is applied, then the bead's `**Ask:**`
    line is present.
12. Given a Shrink verdict, when its `bd update` command is read, then the same command that
    changed the description also wrote the `**Ask:**` line.
13. Given a refine session ends, when the closing summary is read, then it holds one route line
    for the theme and one route line for the whole backlog.
14. Given `skills/bead-refine/SKILL.md`, when it is read, then it holds one worked example of a
    Step 6 round showing three beads with filled values.
15. Given `/bead-refine` reaches Step 5, when it asks which theme to refine, then the full ranked
    theme table is printed before `AskUserQuestion` opens, and no option label carries reasoning.
16. Given a bead whose description has no `**Ask:**` line at all, when `bead-audit` scores it,
    then the `Ask` dimension is reported N/A and its weight leaves the denominator, so a bead in a
    repository that has not run the pass keeps its old score.

**Coverage:** every item in "In Scope" and every problem in "Motivation" is proven by at least one
criterion above.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| The one-off pass loses content from a description, because `bd update -d` replaces the whole field | High | Med | The pass prepends only. The check script compares the new description to the old one and fails on any other difference. Export the tracker with `bd export -o .beads/issues.jsonl` before the pass |
| Turning the `Ask` dimension on before the pass finishes marks all 57 beads down for a line no tool wrote yet | Med | High | Milestone 5 comes after milestone 4, and its "Done when" depends on the pass |
| Flesch-Kincaid passes a sentence that is still unreadable, because it counts syllables and sentence length and cannot see jargon | Med | High | The score is a floor, not the test. The contract file carries the checklist that catches jargon, and the eval case carries the forbidden-word list |
| The scope grows into renaming `## Why (Computational)` across 35 files | Med | Med | The rename is named in Out of Scope, with the file count and the reason |
| `docs/milestones.md` sits unused because nobody fills in the dates | Med | Med | The route works on milestone membership alone. Only the schedule half waits on the dates, and `/bead-refine` says so in one line |
| Milestone 8 is the first eval case to use `prepare_fixture`, so the mechanism is implemented but unproven. It may not build a working `bd` tracker | Med | Med | Milestone 8 is estimated L for this reason, and it gates nothing. When the fixture cannot hold a tracker, the case falls back to asserting the printed shape against a planted transcript |
| A consumer repository upgrades the plugin and every one of its beads loses score, because it never ran the pass | Med | High | The `Ask` dimension reports N/A when no `**Ask:**` line exists, so the weight leaves the denominator instead of scoring zero. Criterion 16 proves it |
| A half-applied change makes every bead fail its own auditor, which is what ADR 0001 records | High | Low | Milestone 7 changes `bead-refine`, `bead-create`, and `plan-to-beads` together, in one unit of work |

## Dependencies

- `bd` must run. `/bead-refine` stops when it does not.
- `rumdl` formats the two new Markdown files. `.githooks/pre-push` already runs `rumdl fmt --check .`.
- `python3` runs the check script and the eval harness. Both are already required by
  `.githooks/pre-push`.
- Milestone 8 runs `evals/run.py`, which makes real `claude -p` calls. [ADR
  0005](../adr/0005-the-evals-are-a-measurement-not-a-gate.md) records 12 calls per run, taking
  several minutes. That cost falls on milestone 8 alone, and on no gate.
- No new third-party library. Flesch-Kincaid is a short formula over word, sentence, and syllable
  counts, so the check script computes it without a dependency.

## Testing Strategy

- **Unit, gated.** `skills/bead-audit/scripts/test_check_bead_body.py` drives
  `check_bead_body.py` with fixed strings. It covers a missing `**Ask:**` line, an `**Ask:**` line
  over 20 words, a grade above 9, a grade at 9, a description whose code spans would inflate the
  grade, and a prepend-only edit compared to an edit that also changed a later line.
- **Whole backlog, gated.** `check_bead_body.py` runs over every bead in the backlog and names each
  failing bead id.
- **Behavior, measured.** `evals/cases/bead-refine-round/case.json` plants a small tracker in a
  fixture repository under `/tmp`, runs a refine round against it, and grades the printed output on
  column count, route cell, sentence length, and forbidden words. It never gates, per ADR 0005.

## Open Questions

- **Four terms in this plan are not in `CONTEXT.md`.** They are `route`, `milestone`, `Ask line`,
  and `bead body contract`. Each names something this plan creates, so this is a gap in the
  glossary rather than a renaming of an existing term. `CONTEXT.md` should gain all four once the
  work lands. This plan does not write that file; [ADR
  0007](../adr/0007-a-tadw-skill-wins-over-an-overlapping-external-skill.md) keeps
  `mattpocock-skills:domain-modeling` as the only skill that writes it.
- **The dates in `docs/milestones.md` are unwritten.** The owner supplies them. Until then the
  route reports milestone membership, and `/bead-refine` states that the schedule half of its
  judgment is unjudged.
- **The exact word count for the `Ask` sentence is 20.** No measurement supports that number yet.
  Milestone 4 writes the first 10 lines and checks whether 20 words holds for a bug and for an
  epic, before the remaining 47. Criterion 1 marks the number provisional until then.
