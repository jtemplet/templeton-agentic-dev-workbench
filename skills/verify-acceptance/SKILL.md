---
name: verify-acceptance
description: "Check a finished unit of work against its bead's acceptance criteria and the QA gates. Resolves the bead from bd, grades each criterion against evidence rather than against the diff, runs the QA gates, and reports one verdict table. It edits no file in the working tree and closes no bead. It writes one artifact, `<git-dir>/acceptance-report.json`, carrying the per-criterion and per-gate counts; a Stop hook reads that file and applies the `accepted` label, so this skill runs no bd command of its own."
---

# Verify Acceptance

Answers two questions about a unit of work that looks finished: **has it met its acceptance criteria**, and **has it passed QA**. Grades each criterion against evidence you can point at, then stops. It does not fix, refactor, or close anything.

## When to Use / When NOT to Use

Use when:

- A fresh-eyes review just finished and you are deciding whether the work is done
- Before opening a pull request, to see which criteria are still unmet
- Before running `bd close`, as the check that the bead earned its close
- When asked "is this done?", "did this meet the criteria?", or "did this pass QA?"

Do NOT use when:

- Looking for bugs in changed code (use `review-fresh-eyes`)
- Judging whether the criteria themselves are well written (use `bead-audit`)
- Judging a plan before implementation starts (use `plan-review`)
- No bead and no QA command exist, so there is nothing to grade against

## The Rule That Makes This Worth Running

**Grade every criterion against an artifact, never against the diff.** Reading a diff and concluding that it should satisfy a criterion is a prediction, not a check. The evidence for a criterion is a named test that ran, a command with its output, or a `file:line` a reader can open. A criterion with no such evidence is UNVERIFIABLE, not PASS.

This is the same rule as the house response style's: report the evidence, not the label. "Criterion 2 passes" is worth nothing to a reader who cannot audit it. "Criterion 2: `test_rejects_expired_token` passed, `pytest -k expired` 3 passed" is.

## Required Workflow

### Step 1: Resolve the Unit of Work

If the caller named a bead id, grade that bead and skip the search. Confirm it exists with `bd show <id> --json` first; if it does not, say so and stop rather than falling back to auto-resolution.

Otherwise find the bead this work belongs to. Try in order, stopping at the first hit:

```bash
bd list --status in_progress --json      # the claimed bead, if one is claimed
git rev-parse --abbrev-ref HEAD          # a branch often carries the bead id
git log --oneline main..HEAD             # commit messages often cite it
```

If a branch or commit names an id, confirm it:

```bash
bd show <id> --json
```

**If exactly one bead resolves,** use it and say which and how you found it.

**If several resolve,** list them and ask the user which one to grade. Do not merge their criteria.

**If none resolves,** report `Unit of work: UNRESOLVED`, skip the acceptance table entirely, run the QA gates anyway, and ask the user for the bead id. Do not invent criteria, do not infer them from the diff, and do not fall back to grading the work against what it appears to be trying to do. A made-up criterion always passes, which is worse than no criterion.

### Step 2: Read the Criteria

From `bd show <id> --json`, read:

- `acceptance_criteria` - the authoritative list, usually numbered Given/When/Then
- `notes` - often carries a `## Done when (Acceptance)` block that adds to it

Number every criterion. Keep the bead's own numbering where it has one, so the report and the bead can be read side by side.

If the field is empty, report `Criteria: NONE RECORDED` and stop the acceptance half there. An empty criteria field is a finding about the bead, and `bead-audit` is the skill that acts on it.

### Step 3: Gather Evidence, One Criterion at a Time

For each criterion, find what would prove it. Prefer, in this order:

1. **A test that exercises it.** Run it by name and keep the output. Name the test in the report.
2. **A command that demonstrates it.** Run it and keep the output.
3. **A `file:line` that implements it,** when the criterion is about structure ("the ceiling is still 35") rather than behavior.

Then assign a verdict:

| Verdict | Means |
|---|---|
| **PASS** | Evidence exists, you ran or read it, and it shows the criterion met. |
| **FAIL** | Evidence exists and shows the criterion unmet, or the implementing code is absent. |
| **UNVERIFIABLE** | No artifact can settle it here: it needs a human, a production observation, a design sign-off, or a device you do not have. |

UNVERIFIABLE is a real answer and is not a soft FAIL. Say what would settle it and who has to do that.

### Step 4: Run the QA Gates

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/SKILL.md` and run three of its gates against the current tree: **Tests**, **Lint and Format**, and **Type Checking**. If that path does not resolve, locate it with `Glob: **/skills/quality-gates/SKILL.md` and read it from there.

Those three are the subset that can invalidate an acceptance claim. Skip its doc freshness and hygiene gates here; they produce warnings, and a warning never changes a verdict. Run `/quality-gates` instead when the user wants the complete sweep.

Read the file rather than restating the gates from memory. It owns how each gate is discovered, how it is scoped, and what its statuses mean, and a second copy of that here would drift from it.

**Do not write its `quality-gates-report.json` artifact.** That file records a full-sweep verdict, and this skill runs three gates of seven. A partial run recorded there would gate a push on a conclusion nobody drew.

Two of its rules carry into this report unchanged:

- A configured gate that could not run is **BLOCKED**, never SKIP. A missing binary proves nothing about the code.
- Record real numbers. "Tests: 218 passed, 0 failed" is a gate result. "Tests: green" is not, and neither is "QA passed."

### Step 5: Write the Verdict Artifact

**Write the counts you just graded, and run no `bd` command.** A `Stop` hook reads this file and
applies the `accepted` label itself. Apply the Verdict Rules below first, then write what they
produced:

```bash
python3 - <<'PY'
import json, subprocess
git_dir = subprocess.run(
    ["git", "rev-parse", "--path-format=absolute", "--git-dir"],
    capture_output=True, text=True, check=True).stdout.strip()
report = {
    "bead": "<bead-id>",
    "criteria_total": 0,
    "criteria_passed": 0,
    "criteria_failed": 0,
    "criteria_unverifiable": 0,
    "gates_total": 0,
    "gates_failed": 0,
    "gates_blocked": 0,
}
with open(f"{git_dir}/acceptance-report.json", "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
    handle.write("\n")
PY
```

The path comes from `git rev-parse --path-format=absolute --git-dir`, which resolves per worktree,
so a linked worktree writes its own verdict rather than the main checkout's. That is the same
resolution the reader uses.

Every field is required, and every count is a plain integer. The reader rejects an absent field, a
non-numeric one, and a count written with a leading zero.

| Field | What it counts |
|---|---|
| `bead` | The bead this run graded, for the log |
| `criteria_total` | Every criterion in the bead's table, including the ones that failed |
| `criteria_passed` | Rows marked PASS |
| `criteria_failed` | Rows marked FAIL |
| `criteria_unverifiable` | Rows marked UNVERIFIABLE |
| `gates_total` | Gates you considered, which is three: tests, lint, type checking |
| `gates_failed` | Gates marked FAIL |
| `gates_blocked` | Gates marked BLOCKED |

**Report the counts. Do not report the conclusion.** There is deliberately no `verdict` field, and
the reader ignores one if you add it. You are the authority on each row; what the rows add up to is
the hook's to decide. A run that wrote `"verdict": "ACCEPTED"` beside a failing criterion would be
labeling work it had just graded as failed. That is the self-grading failure this skill exists to
prevent.

**Skipped gates have no field, because a SKIP does not change the verdict.** A BLOCKED gate does,
and `gates_blocked` carries it.

**Write nothing when Step 1 resolved no bead.** There is nothing to label, so an artifact would
name a run that graded no unit of work.

**This file is a completion token as much as a verdict.** A run that stops mid-grading writes
nothing, and its absence is the only reliable signal that the grading did not finish. `Stop` fires
whenever the model yields rather than when the work ends, so it cannot tell an interrupted run from
a finished one any other way. The marker stays in place while the file is absent, and the run is
abandoned after six hours rather than labeled early.

**Do not run `bd update --add-label accepted` yourself.** The hook applies it from this file. A run
that both writes the artifact and applies the label is doing the same job twice, and the second way
is the one that was landing 5 verdicts in 15.

**This skill still closes no bead and changes no bead status.** Closing is a separate decision,
taken after this report.

### Step 6: Report

Output the report below, then stop.

## Output Format

```markdown
## Acceptance Verification

**Unit of work:** <bead-id> - <title>
**Resolved by:** <bd list --status in_progress | branch name | commit message>

### Acceptance Criteria

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | <criterion, shortened> | PASS | `test_name` passed (`<command>`, 3 passed) |
| 2 | <criterion, shortened> | FAIL | No handler for the expired case; `auth.py:88` returns early |
| 3 | <criterion, shortened> | UNVERIFIABLE | Needs a manual check on a physical device |

### QA Gates

| Gate | Status | Command | Result |
|---|---|---|---|
| Tests | PASS | `pytest -q` | 218 passed, 0 failed |
| Lint | PASS | `ruff check .` | 0 errors, 2 warnings |
| Type checking | SKIP | - | No type checker configured |

### Verdict: ACCEPTED / NOT ACCEPTED / INCONCLUSIVE

<One sentence naming what decided it.>

**Label:** left to the `Stop` hook, which reads `acceptance-report.json`. Wrote 9 of 9 criteria PASS
and 3 gates with 0 failing and 0 blocked, so the hook applies `accepted`. / Wrote 7 of 9 criteria
PASS, so the hook withholds it; the verdict is <verdict>.

### What Is Left

- [Criterion 2] <what is missing, and where>
- [Criterion 3] <what would settle it, and who has to do it>
```

## Verdict Rules

Apply these mechanically. Do not soften a verdict because the work is nearly there.

- **ACCEPTED** - at least one criterion was graded, every criterion is PASS, and no gate FAIL or BLOCKED.
- **NOT ACCEPTED** - any criterion FAIL, or any gate FAIL or BLOCKED. One is enough.
- **INCONCLUSIVE** - no criterion FAIL, but at least one UNVERIFIABLE. The work may well be done; you cannot say so from here.

A skipped gate does not change the verdict. A BLOCKED gate does, because a check that could not run leaves the claim unproven. An unresolved unit of work, or a bead with an empty criteria field, makes the acceptance half INCONCLUSIVE, not ACCEPTED. Zero criteria satisfy "every criterion PASS" vacuously, and that is the reading this skill exists to refuse.

## Critical Rules

**Always:**

- Name the bead you graded and how you resolved it
- Grade each criterion separately, in the bead's own numbering
- Put the evidence in the table, not a summary of the evidence
- Run the QA gates and report their real counts
- Report NOT ACCEPTED plainly when that is the answer
- Write the Step 5 artifact with counts that match the report's own table, and say on the `Label:` line which verdict the counts carry

**Never:**

- Edit code in the working tree, write the `quality-gates` JSON artifact, run `bd close`, or change a bead's status. This skill writes exactly one file, `<git-dir>/acceptance-report.json` from Step 5, and `<git-dir>` is not the working tree, so the run still leaves the tree as clean as it found it
- Run `bd update --add-label accepted`, or any other `bd` write. The `Stop` hook applies the label from the Step 5 artifact
- Infer acceptance criteria when the bead has none
- Grade a criterion from the diff alone
- Call a criterion PASS because the code looks like it should satisfy it
- Report a gate as "green" or "passing" without its numbers
- Re-run the fresh-eyes review (a different skill already did that)

## Quality Checklist

Before reporting completion, verify:

- [ ] The bead is named, with how it was resolved
- [ ] Every criterion in the bead appears in the table, with none merged or dropped
- [ ] Every PASS cites a test name, a command with output, or a `file:line`
- [ ] Every UNVERIFIABLE says what would settle it and who does it
- [ ] Every gate reports a real count, an explicit SKIP with a reason, or BLOCKED with what stopped it
- [ ] The verdict follows the Verdict Rules mechanically
- [ ] Step 5 wrote `<git-dir>/acceptance-report.json` with all seven counts, and no `bd` command ran
- [ ] The counts in that file match the report's own table, row for row
- [ ] No file in the working tree was edited, `quality-gates-report.json` was not written, and no bead was closed
