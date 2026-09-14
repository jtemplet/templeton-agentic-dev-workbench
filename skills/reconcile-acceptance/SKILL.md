---
name: reconcile-acceptance
description: "Fix the FAIL criteria and FAIL gates a /tadw:verify-acceptance run recorded in acceptance-report.json, then stop without re-grading the fix. Reads findings only from that report file, never from the diff or a transcript, and refuses to start when the report is missing, stale, foreign, or unreadable. Runs each finding's command, criterion or gate alike, before committing when it names one, edits nothing outside the report's changed_files, refuses a file with uncommitted changes, and ends with one machine line: RECONCILE_ACCEPTANCE_DONE <n> or RECONCILE_ACCEPTANCE_BLOCKED <reason>. Use after a NOT ACCEPTED verdict, never to grade work or to fix a review finding."
---

# Reconcile Acceptance

Fixes what `/tadw:verify-acceptance` already found wrong, then stops. It never runs the QA gates
again and never decides whether the fix worked, because a fixer that grades its own fix is the
failure [ADR 0011](../../docs/adr/0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md)
exists to prevent. The caller runs `/tadw:verify-acceptance` again to check.

## When to Use / When NOT to Use

Use when:

- `/tadw:verify-acceptance` just reported NOT ACCEPTED, and its report names this skill in a
  `**Next:**` line.
- An unattended loop, such as outrigger, needs a fixer it can call after a failed acceptance
  check, up to a small attempt cap.

Do NOT use when:

- The report's verdict is ACCEPTED or INCONCLUSIVE. Nothing here is a finding this skill fixes.
- You want to fix a code-review comment. That is a different job, and outrigger's own reconcile
  phase owns it.
- No `acceptance-report.json` exists yet. Run `/tadw:verify-acceptance` first.

## Invocation

```text
/tadw:reconcile-acceptance [bead-id]
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
REPORT="$(git rev-parse --path-format=absolute --git-dir)/acceptance-report.json"
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/reconcile-acceptance/scripts/load_findings.py' -print -quit 2>/dev/null)" \
  --report "$REPORT" \
  --head "$(git rev-parse HEAD)" \
  --dirty-files <(git status --porcelain=v1 -z) \
  --bead "$BEAD_ID"
```

Drop `--bead "$BEAD_ID"` when the caller named none.

| Exit | What it means | What to do |
|---|---|---|
| 0 | Findings on stdout, as one JSON object | Continue to Step 2 |
| 1 | Nothing was fixed. The last stdout line is `RECONCILE_ACCEPTANCE_BLOCKED <reason>` | Print that line and stop. See the reasons table below |
| 2 | A usage error: a blank `--head`, a blank `--bead`, or an unreadable `--dirty-files` | Fix the argument and run it again. This is the caller's own mistake, not a report problem |
| 3 | The report's counts already make it ACCEPTED | Print `RECONCILE_ACCEPTANCE_DONE 0` and stop. Nothing to fix |

The JSON object on exit 0 holds five keys. `in_scope` lists the findings to fix, each with its
own `criterion` or `gate` key. `out_of_scope` lists findings this skill never touches, without
`evidence` or `command`. `base`, `bead`, and `scope_known` name the report's own scope.

**Every finding names no file.** The loader never emits `failures-outside-change`, because an
acceptance criterion or gate is graded against behavior, not a line in a diff. Step 4 decides
which file each finding needs.

### Step 2: Check for a Repeated Finding

Read `git log --oneline` on this branch for an earlier commit whose subject starts
`fix(acceptance): reconcile`, naming this bead when one was given. A finding that already has such
a commit and is still in scope came back after a fix, so the same approach failed once. Try a
different fix, or, if none is apparent, treat it as not fixed in Step 5 rather than repeating the
same edit.

### Step 3: Load the Style Skills

For each in-scope finding, decide which file it touches (Step 4 names how), then load the style
skill [docs/style-routing.md](../../docs/style-routing.md) maps to that file's extension, plus
`style-testing` for any test file.

### Step 4: Find Each Finding's File

Every finding lacks a `file` key, so find one before editing:

- **A criterion with a `command`.** Run it. Read its output and the criterion's `text` and
  `evidence` to find the file the criterion is about.
- **A criterion with no `command`, or a gate.** Read `text`/`evidence`, or the gate's `detail`
  and `command`, the same way. A gate's `command` is the one `/tadw:quality-gates` reported for
  that gate, such as `pytest -q`.

**Refuse a fix outside `changed_files`.** When `scope_known` is `true` and the file a finding
needs is not in the report's `changed_files`, leave that finding unfixed and say so in Step 7; do
not edit a file the graded diff never touched. When `scope_known` is `false` (the report's `base`
was `null`), there is no changed set to check against, so use your own judgment.

**The dirty-file refusal already happened in Step 1, only when `scope_known` is `true`.** The
loader checks every in-scope finding's file against `changed_files` before printing anything, and
stops with `uncommitted-changes` when one already has uncommitted changes. That check needs
`changed_files`, so it never runs when `scope_known` is `false`; the loader has no changed set to
check a dirty file against.

**When `scope_known` is `false`, check each file yourself before you edit it.** Run
`git status --porcelain=v1 -z` again, or reuse `--dirty-files`, and compare it against the file
Step 4 found. A dirty file stops the whole run: make no edit, and print
`RECONCILE_ACCEPTANCE_BLOCKED uncommitted-changes` in Step 7, naming the file.

### Step 5: Fix Each In-Scope Finding

For each finding, in the order the JSON listed it:

1. Edit the file Step 4 found. Never weaken, skip, or delete a test or an assertion to make a
   finding pass, and never edit the bead or its criteria.
2. Build nothing the finding does not ask for. A missing test the finding names is in scope; a
   new feature is not.
3. **Run the finding's `command` before moving on, whenever it is not `null`.** A criterion whose
   `command` now exits 0, or a gate whose `command` now reports no failure, is fixed. One that
   still fails is not; mark it not fixed and keep going.
4. A finding with no `command` is fixed once its file matches what `text` or `evidence`
   describes, read by hand.

**A finding you could not fix does not stop the run.** Move to the next one, and let Step 7's
BLOCKED line report the gap once, at the end.

### Step 6: Commit the Fixes

When at least one finding was fixed:

```bash
git add <path> <path> ...
git commit -m "fix(acceptance): reconcile <n> findings (<bead-id>)" -m "<body>"
```

Stage the fixed files by path, one at a time. **Never run `git add -A` or `git add .`**; either
one can stage a file no finding named. Drop the `(<bead-id>)` parenthetical when no bead was
given. The body has one line per fixed finding, naming the criterion number or gate, the
`file:line`, and the problem it had.

**Never amend, push, or rewrite history.** This is the one commit the run makes, and the caller
decides what happens to it next.

When nothing was fixed, make no commit and go straight to Step 7.

### Step 7: Report

Print a table with one row per finding: its number or gate name, and whether it was fixed, left
out of scope, or not fixed. Then print exactly one line, as the last line of the output:

- **`RECONCILE_ACCEPTANCE_DONE <n>`**, where `<n>` is the count of findings fixed, when every
  in-scope finding was fixed.
- **`RECONCILE_ACCEPTANCE_BLOCKED <reason>`** otherwise, using the first reason from the table
  below that applies. A partial run, where some findings were fixed and at least one was not,
  still commits the working fixes first, then prints this line with `finding-not-fixed`.

## The Ten BLOCKED Reasons

The first of these that applies wins. Reasons 1 to 4 and 7 to 8 come from `load_findings.py`, on
stdout, in Step 1. Reason 5 comes from the loader when `scope_known` is `true`; this skill decides
it itself, in Step 4, when `scope_known` is `false`. Reasons 6, 9, and 10 are this skill's own too,
decided in Step 4 onward.

| # | Reason | Decided by | Condition |
|---|---|---|---|
| 1 | `report-missing` | the loader | No file exists at `--report` |
| 2 | `report-unreadable` | the loader | The file will not parse, lacks a version 2 field, or names a version other than 2 |
| 3 | `report-stale` | the loader | The report's `head` differs from the current `HEAD` |
| 4 | `bead-mismatch` | the loader | `--bead` was given and differs from the report's `bead`, `null` included |
| 5 | `uncommitted-changes` | the loader when `scope_known` is `true`, this skill otherwise | A file in `changed_files` already has uncommitted changes, or, when `scope_known` is `false`, the file Step 4 found does |
| 6 | `failures-outside-change` | this skill | Never printed. Acceptance findings name no file, so nothing can sit outside the change before Step 4 picks one |
| 7 | `needs-environment` | the loader | Nothing is in scope, and a gate is BLOCKED |
| 8 | `needs-human-check` | the loader | Nothing is in scope, and the report is not ACCEPTED: only UNVERIFIABLE criteria remain, or the report grades no criteria |
| 9 | `finding-not-fixed` | this skill | At least one in-scope finding stayed unfixed after Step 5 |
| 10 | `commit-failed` | this skill | `git commit` refused, for example because a hook failed |

## Guardrails

- Never weaken, skip, or delete a test or an assertion.
- Never edit the bead or its criteria.
- Build nothing beyond what the finding asks for.
- Never write `acceptance-report.json` or `quality-gates-report.json`.

## Output Format

```markdown
## Reconcile Acceptance

**Bead:** tadw-abc, or "none given"
**Report:** <n> in scope, <n> out of scope, base <scope_known>

| # | Finding | Result |
|---|---|---|
| 2 | Criterion 2, an expired token returns 401 | Fixed: `auth.py:88`, ran `pytest -k expired`, now passes |
| Tests | Gate: Tests | Not fixed: `test_export.py:12` still fails after the edit |

RECONCILE_ACCEPTANCE_BLOCKED finding-not-fixed
```

## Critical Rules

**Always:**

- Read findings only from `load_findings.py`'s output, never from the diff or a transcript.
- Run a finding's `command` before counting it fixed, when it has one.
- Stage fixed files by path, never with `git add -A`.
- End with exactly one machine line, as the last line of the output.

**Never:**

- Run `/tadw:quality-gates` or `/tadw:verify-acceptance` from inside this skill. That is the
  caller's job, after this run ends.
- Write a verdict, or grade whether the fix worked.
- Edit a file outside the report's `changed_files` when `scope_known` is `true`.
- Amend, push, or rewrite the commit this skill made.

## Quality Checklist

- [ ] Every finding came from `load_findings.py`'s JSON, none from the diff or a transcript.
- [ ] A dirty file was checked before every edit, by the loader when `scope_known` is `true`, by
      this skill when it is `false`.
- [ ] Every fixed finding's `command` ran and passed, when it had one.
- [ ] No test or assertion was weakened, skipped, or deleted.
- [ ] No file outside `changed_files` was edited, when `scope_known` is `true`.
- [ ] The commit, if one was made, stages fixed files by path, never with `git add -A`.
- [ ] The output ends with exactly one machine line.
