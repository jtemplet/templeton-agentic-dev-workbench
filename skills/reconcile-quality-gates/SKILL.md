---
name: reconcile-quality-gates
description: "Fix the FAIL gate findings a /tadw:quality-gates run recorded in quality-gates-report.json, then stop without re-grading the fix. Reads findings only from that report file, never from the diff or a transcript, and refuses to start when the report is missing, stale, foreign, or unreadable. Runs each finding's gate command before committing, edits nothing outside the report's changed_files, refuses a file with uncommitted changes, and ends with one machine line: RECONCILE_QUALITY_GATES_DONE <n> or RECONCILE_QUALITY_GATES_BLOCKED <reason>. Use after a FAIL verdict, never to grade work or to fix a review finding."
---

# Reconcile Quality Gates

Fixes what `/tadw:quality-gates` already found wrong, then stops. It never runs the gates again
and never decides whether the fix worked, because a fixer that grades its own fix is the failure
[ADR 0011](../../docs/adr/0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md)
exists to prevent. The caller runs `/tadw:quality-gates` again to check.

## When to Use / When NOT to Use

Use when:

- `/tadw:quality-gates` just reported FAIL, and its report names this skill in a `**Next:**` line.
- An unattended loop, such as outrigger, needs a fixer it can call after a failed gate run, up to
  a small attempt cap.

Do NOT use when:

- The verdict is PASS, INCOMPLETE, or NO GATES RAN. Nothing here is a finding this skill fixes.
- You want to fix a code-review comment. That is a different job, and outrigger's own reconcile
  phase owns it.
- No `quality-gates-report.json` exists yet. Run `/tadw:quality-gates` first.

## Invocation

```text
/tadw:reconcile-quality-gates [bead-id]
```

The only argument is the bead id, and it is optional. `head` and `base` always come from the
report, never from the caller.

## Required Workflow

### Step 1: Load the Findings

Resolve the report path and the current state, then run the bundled loader. Do not hand-roll any
of these checks; the loader decides them.

<!-- plugin-root-fallback -->
**The command below finds its plugin script when `CLAUDE_PLUGIN_ROOT` is unset.** The `find`
fallback searches the installed plugin cache. Claude Code uses the loaded plugin root first.

```bash
REPORT="$(git rev-parse --path-format=absolute --git-dir)/quality-gates-report.json"
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/reconcile-quality-gates/scripts/load_findings.py' -print -quit 2>/dev/null)" \
  --report "$REPORT" \
  --head "$(git rev-parse HEAD)" \
  --dirty-files <(git status --porcelain=v1 -z) \
  --bead "$BEAD_ID"
```

Drop `--bead "$BEAD_ID"` when the caller named none.

| Exit | What it means | What to do |
|---|---|---|
| 0 | Findings on stdout, as one JSON object | Continue to Step 2 |
| 1 | Nothing was fixed. The last stdout line is `RECONCILE_QUALITY_GATES_BLOCKED <reason>` | Print that line and stop. See the reasons table below |
| 2 | A usage error: a blank `--head`, a blank `--bead`, a `--report` naming no file, or an unreadable `--dirty-files` | Fix the argument and run it again. This is the caller's own mistake, not a report problem |
| 3 | The verdict is already PASS or NO GATES RAN | Print `RECONCILE_QUALITY_GATES_DONE 0` and stop. Nothing to fix |

The JSON object on exit 0 holds five keys. `in_scope` lists the findings to fix, each carrying its
gate's `command`. `out_of_scope` lists findings this skill never touches, holding only `gate`,
`file`, and `problem`. `base`, `bead`, and `scope_known` name the report's own scope.

**Only a FAIL gate's findings are ever in scope.** A finding on a BLOCKED, HANDOFF, WARN, or SKIP
row always prints in `out_of_scope`; this skill leaves those rows alone.

### Step 2: Check for a Repeated Finding

Read `git log --oneline` on this branch for an earlier commit whose subject starts
`fix(quality-gates): reconcile`, naming this bead when one was given. A finding that already has
such a commit and is still in scope came back after a fix, so the same approach failed once. Try a
different fix, or, if none is apparent, treat it as not fixed in Step 5 rather than repeating the
same edit.

### Step 3: Load the Style Skills

For each in-scope finding that already names a file, load the style skill
[docs/style-routing.md](../../docs/style-routing.md) maps to that file's extension, plus
`style-testing` for any test file. A finding whose `file` is `null` waits until Step 4 finds one.

### Step 4: Find a File for a `null`-File Finding

An in-scope finding whose `file` is `null` names no place, most often a Tests gate whose failure
spans several files. Re-run its `command` and read the output to find the file, or files, it
names.

**Apply the outside-the-change rule to what the command names.** When `scope_known` is `true` and
every file the output names is outside the report's `changed_files`, leave the finding unfixed and
report it with `failures-outside-change` in Step 7; do not edit a file the graded diff never
touched. When `scope_known` is `false` (the report's `base` was `null`), there is no changed set to
check against, so use your own judgment.

**Then check each file the command named against `--dirty-files`,** the same way Step 1 already
checked every in-scope finding that had its own `file`. A dirty file stops the whole run: make no
edit, and print `RECONCILE_QUALITY_GATES_BLOCKED uncommitted-changes` in Step 7, naming the file.

Load the style skill for whichever file you settle on, per Step 3.

### Step 5: Fix Each In-Scope Finding

For each finding, in the order the JSON listed it:

1. Edit the file. Never weaken, skip, or delete a test or an assertion to make a finding pass, and
   never edit the bead or its criteria.
2. Build nothing the finding does not ask for. A missing test the finding names is in scope; a new
   feature is not.
3. **Run the finding's `command` before moving on.** A finding whose gate now reports no failure
   is fixed. One that still fails is not; mark it not fixed and keep going.

**A finding you could not fix does not stop the run.** Move to the next one, and let Step 7's
BLOCKED line report the gap once, at the end.

### Step 6: Commit the Fixes

When at least one finding was fixed:

```bash
git add <path> <path> ...
git commit -m "fix(quality-gates): reconcile <n> findings (<bead-id>)" -m "<body>"
```

Stage the fixed files by path, one at a time. **Never run `git add -A` or `git add .`**; either one
can stage a file no finding named. Drop the `(<bead-id>)` parenthetical when no bead was given. The
body has one line per fixed finding, naming the gate, the `file:line`, and the problem it had.

**Never amend, push, or rewrite history.** This is the one commit the run makes, and the caller
decides what happens to it next.

When nothing was fixed, make no commit and go straight to Step 7.

### Step 7: Report

Print a table with one row per finding: its gate name, and whether it was fixed, left out of
scope, or not fixed. Then print exactly one line, as the last line of the output:

- **`RECONCILE_QUALITY_GATES_DONE <n>`**, where `<n>` is the count of findings fixed, when every
  in-scope finding was fixed.
- **`RECONCILE_QUALITY_GATES_BLOCKED <reason>`** otherwise, using the first reason from the table
  below that applies. A partial run, where some findings were fixed and at least one was not,
  still commits the working fixes first, then prints this line with `finding-not-fixed`.

## The Ten BLOCKED Reasons

The first of these that applies wins. Reasons 1 to 4, 7, and 8 come from `load_findings.py`, on
stdout, in Step 1. Reasons 5 and 6 come from the loader for a finding that already named a file;
this skill decides them itself, in Step 4, for a finding whose `file` was `null`. Reasons 9 and 10
are this skill's own.

| # | Reason | Decided by | Condition |
|---|---|---|---|
| 1 | `report-missing` | the loader | No file exists at `--report` |
| 2 | `report-unreadable` | the loader | The file will not parse, lacks a version 2 field, names a version other than 2, or its shape is otherwise invalid |
| 3 | `report-stale` | the loader | The report's `head` differs from the current `HEAD` |
| 4 | `bead-mismatch` | the loader | `--bead` was given and differs from the report's `bead`, `null` included |
| 5 | `uncommitted-changes` | the loader for a finding with its own `file`, this skill for a `null`-file finding | The file already has uncommitted changes |
| 6 | `failures-outside-change` | the loader for a finding with its own `file`, this skill for a `null`-file finding | Every FAIL finding is in a file outside `changed_files` |
| 7 | `needs-environment` | the loader | Nothing is in scope, and a gate is BLOCKED |
| 8 | `needs-human-check` | the loader | Nothing is in scope, and the verdict is not PASS or NO GATES RAN: a HANDOFF gate remains, or a FAIL gate has no finding |
| 9 | `finding-not-fixed` | this skill | At least one in-scope finding stayed unfixed after Step 5 |
| 10 | `commit-failed` | this skill | `git commit` refused, for example because a hook failed |

## Guardrails

- Never weaken, skip, or delete a test or an assertion.
- Never edit the bead or its criteria.
- Build nothing beyond what the finding asks for.
- Never write `quality-gates-report.json` or `acceptance-report.json`.

## Output Format

```markdown
## Reconcile Quality Gates

**Bead:** tadw-abc, or "none given"
**Report:** <n> in scope, <n> out of scope, base <scope_known>

| Gate | Finding | Result |
|---|---|---|
| Lint | `src/exports.py:88` F841 unused variable | Fixed: ran `ruff check src/exports.py`, now clean |
| Tests | `test_export.py:12` still fails after the edit | Not fixed |

RECONCILE_QUALITY_GATES_BLOCKED finding-not-fixed
```

## Critical Rules

**Always:**

- Read findings only from `load_findings.py`'s output, never from the diff or a transcript.
- Run a finding's gate `command` before counting it fixed.
- Stage fixed files by path, never with `git add -A`.
- End with exactly one machine line, as the last line of the output.

**Never:**

- Run `/tadw:quality-gates` from inside this skill. That is the caller's job, after this run ends.
- Write a verdict, or grade whether the fix worked.
- Edit a file outside the report's `changed_files` when `scope_known` is `true`.
- Amend, push, or rewrite the commit this skill made.
- Fix a BLOCKED, HANDOFF, WARN, or SKIP row's finding. Only a FAIL gate's findings are in scope.

## Quality Checklist

- [ ] Every finding came from `load_findings.py`'s JSON, none from the diff or a transcript.
- [ ] A dirty file was checked before every edit, by the loader for a finding with its own `file`,
      by this skill for a `null`-file finding.
- [ ] Every fixed finding's gate `command` ran and reported no failure.
- [ ] No test or assertion was weakened, skipped, or deleted.
- [ ] No file outside `changed_files` was edited, when `scope_known` is `true`.
- [ ] The commit, if one was made, stages fixed files by path, never with `git add -A`.
- [ ] The output ends with exactly one machine line.
