# Feature Plan: Domain Docs Wiring

**Date:** 2026-09-02
**Status:** Draft, revised 2026-09-02. Decomposed 2026-09-02, see bd tadw-iva, tadw-dyz, tadw-rx0, tadw-ej2.

**Revision 2026-09-02.** Applied the eight recommended changes from `/plan-review`. The review
found three wrong counts or claims in Motivation and Architecture, one contradiction about the
gate count, and two acceptance criteria that could not prove their work.

## Summary

Three tadw skills that write beads and plans will read `CONTEXT.md`, the repository's glossary, so
the words they choose match the words the project already uses. Two documentation files that still
say `CONTEXT.md` has not been written will be corrected. A new check script will fail the gate
whenever those files drift from what is on disk again.

## Motivation

`CONTEXT.md` was written on 2026-09-02 in commit `02f4925` and holds 229 lines. Two files still say
it does not exist:

- `docs/agents/domain.md:15` reads "`CONTEXT.md` does not exist here today."
- `docs/agents/domain.md:21` labels the file `(not yet written)` in its file-structure block.
- `AGENTS.md:570` reads "one `CONTEXT.md` at the root, not yet written".

`docs/agents/domain.md` is the file `/setup-matt-pocock-skills` wrote to record this repository's
documentation layout. One file in the `mattpocock-skills` plugin references it,
`skills/engineering/setup-matt-pocock-skills/SKILL.md`. The six reader skills read `CONTEXT.md`
directly instead, so no skill is currently acting on the false line. Two of them, `diagnosing-bugs`
and `tdd`, read it only "when it exists". It is still the document a person or an agent opens to
ask where the domain docs live, and it currently answers wrongly.

The same file lists two records in `docs/adr/`. Seven are on disk. Run `ls docs/adr/ | wc -l` to
derive the current count.

Separately, tadw's own skills read the records in `docs/adr/` but almost never read the glossary.
Run these two commands to derive each figure:

```bash
grep -rl "docs/adr" skills/ agents/ commands/ | wc -l
grep -rl "CONTEXT.md" skills/ agents/ commands/ | wc -l
```

Today the first count is 13 and the second is 3. A bead title that invents a synonym for a term the
glossary already fixed costs every later reader a translation. `bead-create` and `plan-to-beads`
write text that outlives the session that produced it, so they benefit most.

## Scope

### In Scope

- Correct the three stale statements listed under Motivation.
- Refresh the file-structure block in `docs/agents/domain.md` so it lists every record in
  `docs/adr/`.
- Add one instruction to `docs/agents/domain.md` telling `mattpocock-skills:domain-modeling` to
  search bd before it reports a naming collision. This is an addition beyond the three-part
  request, kept because it edits a file milestone 1 already opens. Delete this line and milestone
  2 to cut it.
- Add a glossary read to `skills/write-plan/SKILL.md`, `skills/bead-create/SKILL.md`, and
  `skills/plan-to-beads/SKILL.md`.
- Write `skills/quality-gates/scripts/check_domain_docs.py` and its regression suite
  `skills/quality-gates/scripts/test_check_domain_docs.py`.
- Register both new commands in the `AGENTS.md` check-list block and in `.githooks/pre-push`.

### Out of Scope

- The other tadw skills that could read the glossary: `feature-development`, `style-testing`,
  `bead-audit`, `review-fresh-eyes`, and the `diagnostician` agent. The author picked three skills.
  Widening the edit now would make the change hard to review.
- `.github/workflows/lint.yml`. Continuous integration runs four of the checks, and the pre-push
  hook plus the ship gate already run all of them.
- Writing to `CONTEXT.md`. ADR 0007 keeps `mattpocock-skills:domain-modeling` as the skill that
  writes the glossary. This plan adds reading only.
- Whether `mattpocock-skills:grill-with-docs` is reachable in this session. That is a question about
  the plugin host, not about this repository.

## Technical Approach

### Architecture

Two documentation files carry the claims, three skill files carry the new instruction, and one new
script checks that the claims stay true.

`docs/agents/domain.md` is the shared contract. The external skills read it to find the glossary.
The new script reads it to confirm the file says what disk shows. Nothing else changes shape.

The new script follows the seven checkers already in this repository. Run
`ls skills/*/scripts/check_*.py | wc -l` to derive that count. Each is a Python file under a
skill's `scripts/` directory, each exits 1 on a finding, and each ships with a `test_` suite beside
it. `.githooks/test_prepush.py` derives the hook's expected command list from the `AGENTS.md` block,
so adding both commands to that block and to the hook keeps that test passing. The check count in
the `AGENTS.md` prose is separate: no test asserts it, so milestone 5 edits it by hand.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `docs/agents/domain.md` | The layout contract the external skills read | Modified |
| `AGENTS.md` | Its "Domain docs" section and its check-list block. `CLAUDE.md` is a symlink to it, so one edit covers both. | Modified |
| `skills/write-plan/SKILL.md` | Step 4 already names `CONTEXT.md`; make the read explicit | Modified |
| `skills/bead-create/SKILL.md` | Step 3 grounds claims; add the glossary read there | Modified |
| `skills/plan-to-beads/SKILL.md` | Step 2 drafts bead text; add the glossary read there | Modified |
| `skills/quality-gates/scripts/check_domain_docs.py` | Fails when the claims contradict disk | New |
| `skills/quality-gates/scripts/test_check_domain_docs.py` | Regression suite for that checker | New |
| `.githooks/pre-push` | Runs both new commands | Modified |

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| `python3 skills/quality-gates/scripts/test_check_domain_docs.py` | New | The checker reports a stale claim, a wrong record list, and a skill that dropped its glossary read, and stays quiet when all four are correct |
| `.githooks/test_prepush.py`, case `case_command_list_matches_agents_md` | Existing | The hook's command list equals the `AGENTS.md` block, minus the documented exclusions |

The checker is a function over file text, so its command line is the highest seam that proves the
behavior. The seven sibling checkers are tested the same way. The second seam already exists and needs
no new test, only the two new command lines in both places.

### Data Model

N/A because this change stores nothing.

### API / Interface

One new command line, matching the sibling checkers:

```bash
python3 skills/quality-gates/scripts/check_domain_docs.py
```

It takes no required argument and prints one line per finding. It exits 0 when it finds nothing and
1 when it finds anything. Exit 1 is a gate failure, not a warning, because every finding is a
statement that contradicts a file on disk.

The checker makes four assertions:

1. `docs/agents/domain.md` states whether `CONTEXT.md` exists, and that statement matches disk.
2. The fenced file-structure block in `docs/agents/domain.md` lists exactly the files in
   `docs/adr/`.
3. The "Domain docs" section of `AGENTS.md` carries no existence claim that contradicts disk.
4. `skills/write-plan/SKILL.md`, `skills/bead-create/SKILL.md`, and `skills/plan-to-beads/SKILL.md`
   each name `CONTEXT.md`.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| 0001 | A bead's sections live in bd's native `design`, `notes`, and `acceptance_criteria` fields, not in the description body | The edits to `bead-create` and `plan-to-beads` change which words those skills choose. They add no section and move no content. |
| 0004 | The pre-push hook forgives: it runs every check even after one fails, and a missing tool warns by name and allows the push | The two new commands run under the hook's existing `check` wrapper, so they inherit both behaviors without new code. |
| 0007 | Where a tadw skill and a `mattpocock-skills` skill overlap, the tadw one wins, and `domain-modeling` is a deliberate exception that stays his | This plan adds glossary reading to tadw skills and no glossary writing. `mattpocock-skills:domain-modeling` stays the only writer. |

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Correct the stale claims | Fix `docs/agents/domain.md:15`, its file-structure block, and `AGENTS.md:570`. List every record in `docs/adr/`. | S | `grep -rn "not yet written\|does not exist here today" docs/agents/domain.md AGENTS.md` prints nothing, and the fenced block names every file `ls docs/adr/` prints |
| 2 | Add the bd search instruction | One paragraph in `docs/agents/domain.md` telling `mattpocock-skills:domain-modeling` to run `bd search <term>` before it reports a naming collision | S | `docs/agents/domain.md` names `bd search`, and says a settled collision in a closed bead is not a finding |
| 3 | Add the glossary read to three skills | Add the read to `bead-create` step 3 and `plan-to-beads` step 2, which name `CONTEXT.md` nowhere today. Turn `write-plan` step 4's passing mention into an explicit read step. | M | `grep -l CONTEXT.md` matches all three files, and `write-plan` step 4 names reading it as a step |
| 4 | Write the checker and its suite | `check_domain_docs.py` with the four assertions, and `test_check_domain_docs.py` covering each one passing and each one failing | M | `python3 skills/quality-gates/scripts/test_check_domain_docs.py` exits 0, and `python3 skills/quality-gates/scripts/check_domain_docs.py` exits 0 against the corrected tree |
| 5 | Register the checker in the gate | Add both commands to the `AGENTS.md` check-list block and to `.githooks/pre-push`, and update the check count in the `AGENTS.md` prose | S | `python3 .githooks/test_prepush.py` exits 0, and the count in the `AGENTS.md` prose equals the output of `grep -c '^check ' .githooks/pre-push` |

## Acceptance Criteria

1. Given `CONTEXT.md` exists on disk, when a reader opens `docs/agents/domain.md`, then no sentence
   in it says the file is missing or not yet written.
2. Given `CONTEXT.md` exists on disk, when a reader opens the "Domain docs" section of `AGENTS.md`,
   then no sentence in it says the file is missing or not yet written.
3. Given the `docs/adr/` portion of the file-structure block in `docs/agents/domain.md`, when it is
   compared with the output of `ls docs/adr/`, then it names every file that command prints and no
   other file under `docs/adr/`.
4. Given `docs/agents/domain.md`, when a reader looks for the collision rule, then the file tells
   `mattpocock-skills:domain-modeling` to run `bd search` before reporting a naming collision.
5. Given `skills/bead-create/SKILL.md` and `skills/plan-to-beads/SKILL.md`, when each is read, then
   each names `CONTEXT.md` and instructs the author to use the glossary's term rather than a
   synonym. `grep -l CONTEXT.md` matches neither file today.
6. Given `skills/write-plan/SKILL.md`, when step 4 is read, then it instructs the author to read
   `CONTEXT.md` as a step, rather than naming it only as a source of vocabulary.
7. Given a tree where `CONTEXT.md` exists and `docs/agents/domain.md` says it does not, when
   `python3 skills/quality-gates/scripts/check_domain_docs.py` runs, then it prints that finding and
   exits 1.
8. Given a tree where `docs/agents/domain.md` lists a set of records that differs from `docs/adr/`,
   when the checker runs, then it prints that finding and exits 1.
9. Given a tree where any of the three skill files no longer names `CONTEXT.md`, when the checker
   runs, then it prints that finding and exits 1.
10. Given the corrected repository, when the checker runs, then it prints no finding and exits 0.
11. Given the corrected repository, when `python3 .githooks/test_prepush.py` runs, then it exits 0,
    which proves the hook's command list still equals the `AGENTS.md` block minus the documented
    exclusions.
12. Given `.githooks/pre-push`, when `grep -c '^check ' .githooks/pre-push` runs, then the count
    stated in the `AGENTS.md` prose equals its output.

**Coverage:** criteria 1 to 3 prove the stale-claim fix. Criterion 4 proves the bd search
instruction. Criteria 5 and 6 prove the skill edits. Criteria 7 to 10 prove the checker. Criteria
11 and 12 prove the gate registration.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| The checker matches today's exact wording, so a harmless rewrite of `docs/agents/domain.md` fails the gate | Med | High | Assert on the claim, not the sentence. Search for a small set of phrases that mean "missing", and report which phrase matched, so the fix is obvious. |
| The three-skill edit invites widening to all thirteen files that name `docs/adr/` | Med | Med | Out of Scope names the five deferred skills. File them as separate beads rather than growing this change. |
| Adding two commands to the gate slows every push | Low | Low | Both are pure text reads with no process to start. Measure them against the 16 checks already there, and report the number. |
| The record list in `docs/agents/domain.md` goes stale again the next time an ADR is written | Med | High | This is what the checker exists to catch. Criterion 8 covers it. |
| A future reader treats the checker's exit 1 as a warning, as `check_doc_paths.py` is treated | Low | Med | Say in the script's docstring that exit 1 is a gate failure, and give the reason. |

## Dependencies

- None. Every file this plan touches is in this repository, and the checker uses the Python standard
  library alone, as the seven sibling checkers do.

## Testing Strategy

- **The new regression suite** drives `check_domain_docs.py` through its command line. It builds a
  throwaway tree for each case, the way `test_check_doc_paths.py` does, and covers each of the four
  assertions failing and all four passing.
- **The existing pre-push suite** covers the gate registration. `case_command_list_matches_agents_md`
  reads the `AGENTS.md` block and compares it with the hook, so it fails if either list gains a
  command the other does not.
- **The full check list** runs once at the end, from the `AGENTS.md` block, to prove nothing else
  broke.

## Open Questions

- Should the five deferred skills named in Out of Scope read the glossary too? The author picked
  three. The other five are a separate decision, and each is one bead.
- Is `mattpocock-skills:grill-with-docs` reachable in this session? `AGENTS.md` names it as a valid
  predecessor to `/write-plan`, and this session's skill list does not show it. The author owns
  checking `/plugin`.
