# Feature Plan: Token Routing

**Date:** 2026-09-06
**Status:** Draft, revised 2026-09-06. Decomposed 2026-09-06, see bd tadw-1hs, tadw-r9i, tadw-019, tadw-rai, tadw-ubc, tadw-12t.

**Revision 2026-09-06b, on the owner's instruction.** `terraform-iac-expert` left the scope,
and milestone 5, the `references/` split, was dropped with it. The measurement behind that is
under "The split that was dropped" below. Milestone 4 survives on its own merit, because the
checker gap it fixes is real in this repository today. Milestone 6 became milestone 5.

**Revision 2026-09-06, from `/plan-review`.** Applied the six recommended changes. The review found
one gap that would have failed three milestones at their own gate, and one mechanism the plan
called proven when nothing here proves it.

## Summary

Route the plugin's cheap work off the expensive model. Three changes do it: the quality-gates
lanes get a cheaper model, a new read-only `bulk-reader` agent answers questions about many files
without those files entering the caller's context, and an optional hook routes a large read to that
agent. A fourth change fixes a checker that cannot see a whole class of broken path today.

## Motivation

An agent spends most of its work on reading and on writing predictable output, not on reasoning.
Both cost the same as reasoning when they run on the largest model. Two separate costs show up in
this repository, and they need different fixes.

**Every delegation runs on the largest model.** Twelve of the thirteen files in `agents/` set
`model: inherit`, so a subagent runs on whatever the parent runs on. Only
`agents/product-analyst.md` names a cheaper model. Derive the count with
`grep -c '^model: inherit' agents/*.md | grep -v ':0'`. The clearest case is
`agents/quality-gates-orchestrator.md`, which starts three lanes. A lane runs test commands and
returns rows. That work does not need the largest model.

**Every skill invocation loads the whole skill document.** The files under `skills/*/SKILL.md`
total 16,927 lines; derive that with `wc -l skills/*/SKILL.md | tail -1`. This plan set out to cut
that and no longer does. The next section records why.

### The split that was dropped

This plan used to move reference prose out of the four largest skill documents into `references/`
files. That milestone is gone, and a measurement rather than a preference removed it.

`terraform-iac-expert` left the scope first, on the owner's instruction of 2026-09-06, who does not
use that skill. At 957 lines it was the largest, and the only one holding a large section that
lifts cleanly: a 459-line `## Examples` of pure reference.

What remained does not look like that. Derive each row with
`awk '/^## /{if(h)print len" "h; h=$0; len=0; next}{len++}END{if(h)print len" "h}' skills/<name>/SKILL.md | sort -rn`.

| Skill | Lines | Cleanly movable | What the rest is |
|---|---|---|---|
| `review-python` | 897 | about 182 | `## Review Principles` is 558 lines of rules |
| `bead-audit` | 919 | little | No section over 143 lines, and the largest are specs it executes |
| `quality-gates` | 882 | almost none | `## Required Workflow` is 611 lines of gate technique |

Moving 182 lines out of one skill is about one percent of the 16,927. The work to split, measure,
and judge costs more than that returns. A risk this plan already recorded points the same way: a
skill that always reads its own reference file pays for a pointer and then a full read, which is
more than one read cost before.

**Milestone 4 survives the drop.** `check_doc_paths.py` cannot see a `references/` pointer today,
and three skills already name such files: `skills/product-surface-docs`,
`skills/roadmap-dashboard`, and `skills/style-testing`. A pointer that goes missing in any of them
prints no error right now. That gap is real whether or not anything new is split.

**Reading a whole file to answer one question is the most common waste.** Three shipped documents
tell the model to read entire files: `skills/review-fresh-eyes/SKILL.md:64`,
`skills/review-python/SKILL.md:775`, and `skills/pr-maintenance/SKILL.md:283`. Each is correct
about needing context and wrong about who should hold it.

Whoever runs this plugin benefits, because all four changes are in the plugin rather than in any
project that loads it.

## Scope

### In Scope

- A measurement of whether an `Agent` tool call honors a `model` parameter.
- A model override for the three lanes `agents/quality-gates-orchestrator.md` starts, in whichever
  of the two forms that measurement selects.
- A new agent, `agents/bulk-reader.md`, that reads many files and returns structured bullets.
- Its registration in `AGENTS.md` and in `README.md`, which the hook suite already checks.
- An orientation-not-editing rule, added to the three documents that instruct a full-file read.
- A new rule in `skills/quality-gates/scripts/check_doc_paths.py` that resolves a `references/`
  pointer relative to the document that names it.
- An optional `PreToolUse` hook that routes a large `Read` to `bulk-reader`, off unless its
  environment variable is set.
- New checks in `hooks/test-hooks.js` for the lane model rule and the new hook entry.
- The check count in `docs/HOOKS.md`, which that suite asserts against its own real total.
- The two sentences in `CLAUDE.md` and `docs/HOOKS.md` calling the hook manifest a one-feature file.

### Out of Scope

- A `code-writer` worker that generates test files. The Decisions section records why.
- Any change to the lane count, which ADR 0002 fixes at three.
- Any change to the gate set, the report format, or the verdict rules in
  `skills/quality-gates/SKILL.md`.
- Any change to `hooks/style-core.md` or to the size of the payload a subagent receives.
- Moving reference prose out of any skill document. See "The split that was dropped" above.
- Measuring the saving. Milestone 0 measures whether a mechanism works, which is a different
  question. How many tokens the four changes actually save stays a follow-up, named under Open
  Questions.

## Technical Approach

### Architecture

The plugin already has every part this needs, so no new system is added.

Model routing has two forms here, and they are not the same mechanism. A defined agent names its
model in frontmatter, and `agents/product-analyst.md:4` sets `model: haiku` today, so that form is
proven in this plugin. A lane is not a defined agent: `agents/quality-gates-orchestrator.md` never
names a `subagent_type`, so each lane is a generic dispatch, and giving one a model means passing
`model` on the `Agent` tool call.

**Milestone 0 measured that call, and it works.** The orchestrator passes `model` on each lane
start. The fallback, three lane agents carrying the model in frontmatter, is not needed. See "The
lane model mechanism, measured" below.

A subagent runs in its own context. Files it reads never enter the caller's context. That is what
saves the tokens, and `agents/quality-gates-orchestrator.md` already relies on it: it tells every
lane to return rows and never its test-runner output.

`hooks/style-core-hooks.json` registers hooks, and `.claude-plugin/plugin.json` points at that one
file. Adding a `PreToolUse` entry is an edit to the manifest, not a new mechanism.

**The manifest keeps its name, and two documents change instead.** `CLAUDE.md` says that file
"wires one feature", and `docs/HOOKS.md` describes it the same way. Both sentences stop being true
when milestone 5 adds a read-routing entry. Renaming the file was the other option. It loses
because the name appears in `.claude-plugin/plugin.json`, in `hooks/test-hooks.js`, and in both
documents, so a rename changes five places to fix a sentence in two.

Three skills already keep reference prose in a `references/` directory:
`skills/product-surface-docs`, `skills/roadmap-dashboard`, and `skills/style-testing`. Each
SKILL.md names its reference files by a backticked relative path, such as
`references/refresh-workflow.md`. Those pointers are what milestone 4 teaches the checker to see.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `agents/bulk-reader.md` | Reads many files, answers one question, returns bullets | New |
| `agents/quality-gates-orchestrator.md` | Names the model each lane runs on | Modified |
| `skills/review-fresh-eyes/SKILL.md` | Orients through `bulk-reader`, then reads what it edits | Modified |
| `skills/review-python/SKILL.md` | Same rule, in its Review Workflow step 1 | Modified |
| `skills/pr-maintenance/SKILL.md` | Same rule, in its Always list | Modified |
| `skills/quality-gates/scripts/check_doc_paths.py` | Resolves a `references/` pointer | Modified |
| `hooks/style-core-hooks.json` | Registers the `PreToolUse` read-size entry | Modified |
| `hooks/read-size.js` | Decides whether a `Read` is large enough to route | New |
| `hooks/test-hooks.js` | Checks the lane model rule and the new hook entry | Modified |
| `docs/HOOKS.md` | States the suite's check count, which that suite asserts | Modified |
| `agents/lane-*.md` | Three lane agents, only if milestone 0 shows the parameter is not honored | New, conditional |
| `AGENTS.md` and `README.md` | Register the new agent, and the lane agents if milestone 0 requires them | Modified |

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| `node hooks/test-hooks.js` | Existing | The new agent is registered, the orchestrator names a lane model, and the new hook entry runs |
| `python3 skills/quality-gates/scripts/check_doc_paths.py` | Existing | Every `references/` pointer a SKILL.md names resolves to a file on disk |

Both seams are already in the check list in `AGENTS.md`, and both already run in
`.githooks/pre-push`, at lines 140 and 145. A test written at either seam runs on every push with
no new wiring.

**Adding a check to that suite is never a one-file change.** `hooks/test-hooks.js:832` asserts that
`docs/HOOKS.md` states how many checks the suite runs, and `docs/HOOKS.md:112` says 19 today. A
milestone that adds a check and leaves that number alone fails its own seam and the push is
refused. Milestones 0, 1, 2, and 6 each carry that update in their Done-when.

`node hooks/test-hooks.js` is the right height for three of the four changes. It already reads
every file in `agents/` to check registration, and it already runs the manifest commands end to
end. A check on the agent's model or on a new manifest entry is one more assertion in a suite that
already opens those files.

`check_doc_paths.py` is the right height for milestone 4. Rule 1 of that script counts a backticked
token only when its first segment is a directory in the repository root. `references` is not such a
directory, so a pointer at a missing `references/foo.md` prints no error today. Three skills
already name such files, so this is a live gap, not one the plan would have introduced.

No seam sits lower. Nothing here is a function worth testing on its own.

### Data Model

N/A because this plan adds no stored data.

### API / Interface

**A new agent name.** `tadw:bulk-reader`, dispatched through the `Agent` tool.

**A new environment variable.** `TADW_BULK_READ_MIN_LINES` holds a whole number of lines. The hook
does nothing unless the variable is set to a number above zero. Any other value, empty included,
leaves the hook off.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| 0002 | The orchestrator starts three lanes, and every start passes `run_in_background: false` | The plan changes the model each lane runs on. It changes neither the lane count nor the blocking rule |
| 0002 | A `PreToolUse` matcher fires in every project the plugin loads into, which is why a matcher on `Agent` was rejected for bead labeling | The new hook is off unless `TADW_BULK_READ_MIN_LINES` is set, so an unset installation behaves as it does today |
| 0004 | The pre-push hook forgives, and names every case it forgives | The read-size hook forgives the same way. It allows the read and says why whenever it cannot decide |
| 0006 | The style core ships as several hook entries, because one entry would exceed the output cap | The new entry is a separate `PreToolUse` entry. It does not join the `SessionStart` entries, so the split the suite checks is untouched |

### The lane model mechanism, measured

**An `Agent` tool call honors a `model` parameter, including one made from inside a plugin agent.**
Milestone 0 measured it on 2026-09-06, against Claude Code 2.1.263. ADR 0002's spike measured
2.1.239.

Two throwaway plugin agents ran under `claude -p --output-format stream-json`. Both dispatched the
same echo agent with the same prompt, and differed only in the parameter:

| Run | What the dispatch carried | The model that answered |
|---|---|---|
| Test | `{"subagent_type": "tadw:spike-model-echo", "model": "haiku", ...}` | `claude-haiku-4-5-20251001` |
| Control | `{"subagent_type": "tadw:spike-model-echo", ...}`, no `model` | `claude-opus-5[1m]` |

The transcript shows the `model` parameter inside the dispatch made by the calling agent, whose
`parent_tool_use_id` is that agent's own dispatch, so the call came from the plugin agent and not
from the session that invoked it. That is the same nesting test ADR 0002 Finding 1 used.

**The control is what makes the answer trustworthy.** The echo agent reports its own model, and a
model can be wrong about itself. It reported a different model in each run, and only the parameter
differed, so the change came from the parameter rather than from the agent's guess.

**Consequence:** milestone 1 edits `agents/quality-gates-orchestrator.md` alone, plus the check and
the documented count. It does not add three agent files or three registrations, so its size drops
from the Stretch band to Target.

### The decisions this conversation made

**The lanes run on `sonnet`, not on `haiku`.** A lane does more than run a command. It grades
Gate 2 change coverage, and it writes the Step 5 sentence saying whether a failure looks new. That
is judgment. `haiku` was the cheaper option and the article's own choice for a worker. It loses
here because the orchestrator trusts a lane's rows as returned, and has no way to detect a
mis-graded row. `sonnet` keeps the judgment and still costs less than the parent model.

**A `code-writer` worker is rejected for tests.** The idea was a cheap agent that writes a test
file from a specification and a reference file, straight to disk, without the parent model reading
it. It loses on one fact about this plugin. `skills/feature-development/SKILL.md` writes a test
for each acceptance criterion and then runs a simplify pass and a lint pass over what it wrote.
Writing to disk unseen removes the step that makes the output match the house style, which is this
plugin's whole purpose. A narrower version, limited to configuration stubs and type stubs, stays
available as a later decision.

**`bulk-reader` orients, and never supplies the text an edit is based on.** Its answer carries no
reliable line numbers, so an edit built on it edits the wrong line. Every skill that routes through
it reads the specific file it is about to change.

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 0 | Lane model spike | **Done, 2026-09-06.** Measured whether an `Agent` tool call made from inside a plugin agent honors a `model` parameter. It does. See "The lane model mechanism, measured" | S | Met. The transcript shows the parameter inside the nested dispatch, a control run without it answered on a different model, and the plugin cache is back to 13 agents |
| 1 | Lane model | Give the three lanes a model, and state it as a rule of the orchestrator rather than a note. The orchestrator passes `model` on each lane start | S | `agents/quality-gates-orchestrator.md` states the lane model in its Required Workflow and in its Always list, a new check in `hooks/test-hooks.js` fails when that rule is absent, and `docs/HOOKS.md` states the suite's new check count |
| 2 | The bulk-reader agent | Add `agents/bulk-reader.md` and register it | S | `/validate-plugin` reports no error, `node hooks/test-hooks.js` passes with the agent count raised from 13 to 14 in `AGENTS.md`, `README.md` carries its row, and `docs/HOOKS.md` states the suite's new check count |
| 3 | Route the three read sites | Add the orientation-not-editing rule to the three documents that instruct a full-file read | S | Each of the three documents names `bulk-reader`, states that an edit reads its own file, and `rumdl fmt --check .` exits 0 |
| 4 | The doc-path rule | Teach `check_doc_paths.py` to resolve a `references/` pointer relative to the document naming it | M | `python3 skills/quality-gates/scripts/test_check_doc_paths.py` passes with a new case that fails before the change, and `python3 skills/quality-gates/scripts/check_doc_paths.py` exits 0 on this repository |
| 5 | The read-size hook | Add `hooks/read-size.js` and its `PreToolUse` manifest entry, off unless the variable is set | M | With `TADW_BULK_READ_MIN_LINES` unset the hook changes nothing, with it set a read over the threshold is routed, `node hooks/test-hooks.js` covers both, and `CLAUDE.md`, `docs/HOOKS.md` no longer call the manifest a one-feature file and `docs/HOOKS.md` states the suite's new check count |

Milestone 1 depends on milestone 0, which selects the form it takes. Milestones 3 and 5 both
depend on milestone 2, because each names the agent that milestone adds. Milestone 4 depends on
nothing.

**Rollback.** Every milestone is additive, or a single stated rule in one document, so each reverts
by a `git revert` of its own commit. Nothing here rewrites a shipped document wholesale. The
milestone that would have, the `references/` split, is gone.

## Acceptance Criteria

1. Given a repository whose diff routes work to two or more lanes, when `/quality-gates` runs
   through `agents/quality-gates-orchestrator.md`, then the run's transcript shows every lane
   dispatched with the model that file names. ADR 0002 made milestone 2's Done-when read the
   transcript for `run_in_background: false`, and this reads the same transcript for the same
   reason: the alternative is a report that looks correct while the rule was dropped.
2. Given the orchestrator file with its lane model rule deleted, when `node hooks/test-hooks.js`
   runs, then it fails and names the missing rule.
3. Given a question about several files, when the caller dispatches `tadw:bulk-reader`, then the
   answer is structured bullets, and none of those files appears in the caller's context.
4. Given `agents/bulk-reader.md` on disk, when `node hooks/test-hooks.js` runs, then it passes only
   while `AGENTS.md` and `README.md` both list the agent.
5. Given `agents/bulk-reader.md`, when its frontmatter is read, then its `tools` list holds only
   `Read`, `Grep`, and `Glob`, so it can never write a file.
6. Given a skill that routes through `bulk-reader`, when that skill is about to edit a file, then it
   reads that file itself rather than editing from the returned bullets.
7. Given a SKILL.md that names `references/missing.md`, when
   `python3 skills/quality-gates/scripts/check_doc_paths.py` runs, then it exits 1 and names that
   pointer.
8. Given a SKILL.md that names a `references/` file which exists, when that checker runs, then it
   reports no miss for it.
9. Given this repository as it stands, when that checker runs, then it exits 0.
10. Given `TADW_BULK_READ_MIN_LINES` unset, when any `Read` runs, then the hook emits nothing and
    the read proceeds, so an installation that does not opt in behaves as it does today.
11. Given `TADW_BULK_READ_MIN_LINES` set to a number, when a `Read` targets a file with more lines
    than that number, then the hook tells the caller to use `bulk-reader` instead.
12. Given a `Read` the hook cannot measure, such as one whose file it cannot open, then the hook
    allows the read and states why, following ADR 0004.
13. Given milestone 0 finished, when this plan is read, then its Decisions section states whether
    an `Agent` tool call honors a `model` parameter, and which form milestone 1 took.
14. Given every milestone merged, when each command in the `AGENTS.md` check list runs, then each
    one passes. Derive that list with
    `sed -n '/rumdl fmt --check ./,/evals\/run.py/p' CLAUDE.md | grep -E '^[a-z]'`.

**Coverage:** criteria 1, 2, and 13 cover the lane model. Criteria 3, 4, and 5 cover the new agent.
Criterion 6 covers the three routed read sites. Criteria 7, 8, and 9 cover the doc-path checker.
Criteria 10, 11, and 12 cover the hook. Criterion 14 covers the whole set against the existing
gate.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| A lane on a cheaper model mis-grades a Gate 2 row, and the orchestrator trusts it | High | Medium | Choose `sonnet` rather than `haiku`, and treat the first weeks of reports as the measurement. Reverting is a one-line change to the orchestrator |
| The read-size hook fires in every project and blocks a read someone needed | High | Low | The hook is off unless `TADW_BULK_READ_MIN_LINES` is set. ADR 0002 rejected a broad matcher for this reason, and this plan takes the opt-in form instead |
| Scope grows into the `code-writer` worker, which this plan rejected | Medium | Medium | The Out of Scope list names it. A later plan can revisit the narrow version |
| Six milestones land as one change, and a regression cannot be traced to its cause | Medium | Medium | Each milestone is its own bead and its own branch. Milestones 1, 2, and 3 are small and independent |
| A `bulk-reader` answer is used to build an edit, and the edit lands on the wrong line | High | Medium | Criterion 6 states the rule, and all three routed documents carry it |
| A future Claude Code release stops honoring `model` on an `Agent` call, and the lanes quietly return to the parent's model | High | Low | Milestone 0 measured the behavior on 2026-09-06 against 2.1.263, and criterion 1 reads the transcript on every run rather than trusting the rule text. The fallback stays available: define three lane agents whose frontmatter carries the model, the form `agents/product-analyst.md:4` proves |

## Dependencies

- `agents/product-analyst.md` proves the `model` **frontmatter** field works in this plugin.
- **An `Agent` tool call honoring a `model` parameter.** Milestone 0 measured this on 2026-09-06
  and it holds, so milestone 1 is unblocked. It is harness behavior rather than a repository
  contract, so a future release could change it. Milestone 1's transcript check is what would catch
  that.
- ADR 0002 must stay accepted. If the lane count or the blocking rule changes, milestone 1 changes
  with it.
- Milestones 3 and 5 both depend on milestone 2, because each names the agent it adds.

## Testing Strategy

Two seams carry everything, and both already run in `.githooks/pre-push`.

**`node hooks/test-hooks.js`** carries three scenarios. It fails when
`agents/quality-gates-orchestrator.md` no longer states a lane model. It fails when `AGENTS.md` or
`README.md` stops listing `bulk-reader`, through the registration checks it already runs. It runs
the new `PreToolUse` entry end to end, with the variable unset and with it set, because that suite
already runs manifest commands as programs rather than reading them as strings.

**Every milestone that adds a check also edits `docs/HOOKS.md`.** That suite ends by asserting the
count that document publishes, at `hooks/test-hooks.js:832` against `docs/HOOKS.md:112`. A
milestone that adds a check and leaves the number at 19 fails, and `.githooks/pre-push:140` then
refuses the push. This is not a separate test; it is a condition of the one already named.

**`python3 skills/quality-gates/scripts/check_doc_paths.py`** carries milestone 4. Its own suite,
`test_check_doc_paths.py`, gains a case for a `references/` pointer that resolves and a case for
one that does not. The second case must fail before milestone 4 and pass after it.

One thing no suite can prove, and a person has to judge it: whether a lane on a cheaper model still
grades correctly is visible only in real reports over time. That is why the lane model is `sonnet`
rather than `haiku`, and why reverting it is one line.

## Open Questions

- Nobody has measured the saving. The article this plan follows reports about 90 percent on a Java
  repository, and this repository is prompt documents rather than source code, so that number does
  not transfer. Jason decides whether to run a before-and-after measurement of one `/quality-gates`
  run, in the style of the six runs ADR 0002 cites.
- Whether the read-size hook ships at all. It is the only change that acts in every project, and
  milestones 1 through 4 deliver most of the saving without it. Jason decides after milestone 4.
- Whether a narrow `code-writer` worker, limited to configuration stubs and type stubs, is worth a
  later plan. This plan rejects the test-writing version and takes no view on the narrow one.
