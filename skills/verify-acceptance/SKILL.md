---
name: verify-acceptance
description: "Check a finished unit of work against its bead's acceptance criteria and the QA gates. Resolves the bead from br, grades each criterion against evidence rather than against the diff, runs the QA gates, and reports one verdict table. Report-only: it writes no file and closes no bead."
---

# Verify Acceptance

Answers two questions about a unit of work that looks finished: **has it met its acceptance criteria**, and **has it passed QA**. Grades each criterion against evidence you can point at, then stops. It does not fix, refactor, or close anything.

## When to Use / When NOT to Use

Use when:

- A fresh-eyes review just finished and you are deciding whether the work is done
- Before opening a pull request, to see which criteria are still unmet
- Before running `br close`, as the check that the bead earned its close
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

If the caller named a bead id, grade that bead and skip the search. Confirm it exists with `br show <id> --json` first; if it does not, say so and stop rather than falling back to auto-resolution.

Otherwise find the bead this work belongs to. Try in order, stopping at the first hit:

```bash
br list --status in_progress --json      # the claimed bead, if one is claimed
git rev-parse --abbrev-ref HEAD          # a branch often carries the bead id
git log --oneline main..HEAD             # commit messages often cite it
```

If a branch or commit names an id, confirm it:

```bash
br show <id> --json
```

**If exactly one bead resolves,** use it and say which and how you found it.

**If several resolve,** list them and ask the user which one to grade. Do not merge their criteria.

**If none resolves,** report `Unit of work: UNRESOLVED`, skip the acceptance table entirely, run the QA gates anyway, and ask the user for the bead id. Do not invent criteria, do not infer them from the diff, and do not fall back to grading the work against what it appears to be trying to do. A made-up criterion always passes, which is worse than no criterion.

### Step 2: Read the Criteria

From `br show <id> --json`, read:

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

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/SKILL.md` and run four of its gates against the current tree: **Tests**, **Lint and Format**, **Type Checking**, and **Secrets**. If that path does not resolve, locate it with `Glob: **/skills/quality-gates/SKILL.md` and read it from there.

Those four are the subset that can invalidate an acceptance claim. Skip its doc freshness and hygiene gates here; they produce warnings, and a warning never changes a verdict. Run `/quality-gates` instead when the user wants the complete sweep.

Read the file rather than restating the gates from memory. It owns how each gate is discovered, how it is scoped, and what its statuses mean, and a second copy of that here would drift from it.

**Do not write its `quality-gates-report.json` artifact.** That file records a full-sweep verdict, and this skill runs four gates of seven. A partial run recorded there would gate a push on a conclusion nobody drew.

Two of its rules carry into this report unchanged:

- A configured gate that could not run is **BLOCKED**, never SKIP. A missing binary proves nothing about the code.
- Record real numbers. "Tests: 218 passed, 0 failed" is a gate result. "Tests: green" is not, and neither is "QA passed."

### Step 5: Report

Output the report below, then stop.

## Output Format

```markdown
## Acceptance Verification

**Unit of work:** <bead-id> - <title>
**Resolved by:** <br list --status in_progress | branch name | commit message>

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
| Secrets | PASS | `gitleaks detect` | 0 findings |

### Verdict: ACCEPTED / NOT ACCEPTED / INCONCLUSIVE

<One sentence naming what decided it.>

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

**Never:**

- Edit code in the working tree, write the `quality-gates` JSON artifact, run `br close`, or change a bead's status (this skill is report-only and writes no file at all)
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
- [ ] No file in the working tree was edited, no artifact was written, and no bead was closed
