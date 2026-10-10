---
name: review-fresh-eyes
description: "Review recently changed code as if seeing it for the first time. Resolves the changed set from git, reads the diff and the code each hunk touches, finds real bugs, proves each one with a failure scenario before fixing it, and runs the narrowest test that covers each fix. Conservative scope: bugs only, never style, naming, or design. Normally runs inside the fresh-eyes-reviewer agent on sonnet, so the file reads stay out of the caller's window."
---

# Fresh Eyes Review

A bug pass over recently changed code that fixes what it can prove and reports what it cannot.
It reads the diff first, then the code each hunk touches, and it never edits on a hunch.

`/fresh-eyes-cr` runs this skill inside the `fresh-eyes-reviewer` agent, on `sonnet`, so the
reading happens in that agent's window. Running the skill in a parent window works, and it costs
that window every file read.

## When to Use / When NOT to Use

Use when:

- After implementing a feature, before committing
- After refactoring, to catch errors the change introduced
- When asked to "review my changes" or "check what I just did"
- Before opening a pull request, as a self-review pass

Do NOT use when:

- For style or formatting feedback (this is not a style review)
- For architectural review (this is not a design review)
- For a full read-only review (use `/code-review`)
- On code with no recent changes (nothing to review)

## Universal Core (injected)

The universal style core (`hooks/style-core.md`) defines how code should be written. This skill
does NOT enforce it. It fixes bugs only, never style, formatting, naming, or design. Treat the
core as the boundary marker here, not the checklist. A style or design deviation that is not a
defect stays as it is.

## Bug Categories

Look for these, in priority order:

| Category | Examples |
|---|---|
| **Bugs** | Off-by-one, null or nil dereference, wrong variable name, missing return |
| **Logic Errors** | Inverted condition, unreachable code, a loop that cannot end |
| **Missing Error Handling** | An unhandled exception at a system boundary, a missing nil check on external data |
| **Copy-Paste Errors** | A duplicated block with one copy not updated, the wrong variable in a repeated pattern |
| **Security Issues** | SQL injection, XSS, a hardcoded secret, path traversal |
| **Stale Call Sites** | A symbol the hunk renamed, removed, or re-typed that another line in the file still uses the old way |

Shadowing, misleading names, and dead code are not on this list. They are style findings, and
`/code-review` owns them.

## Required Workflow

### Step 1: Resolve the Changed Set

Run the changed-set script `quality-gates` uses. It diffs the default base against the working
tree and adds untracked files, so committed, staged, and unstaged work land in one list.

<!-- plugin-root-fallback -->
**The command below finds its plugin script when `CLAUDE_PLUGIN_ROOT` is unset.** The `find`
fallback searches the installed plugin cache. Claude Code uses the loaded plugin root first.

```bash
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/quality-gates/scripts/changed_set.py' -print -quit 2>/dev/null)" --repo-root .
```

Pass `--base <ref>` through when the caller gave one. An empty list means nothing to review: say
so and stop. On exit 3 (no resolvable base), use `git diff --name-only HEAD` plus
`git ls-files --others --exclude-standard`.

The caller's input takes one of three forms. `--base <ref>` narrows the changed set. A bead id
names the bead in the report and changes nothing else. Nothing means the default base.

### Step 2: Read the Diff, Then the Code It Touches

Read the diff once, with `git diff <base>...HEAD` plus `git diff HEAD` for uncommitted work. Then,
for each hunk, read these parts of its file:

1. The enclosing unit: the function, method, class, or top-level block the hunk sits in, start to
   end.
2. Every in-file use of a symbol the hunk adds, renames, removes, or re-types. Find the uses with
   `Grep`, then read each one in place. This is where the bugs a diff view hides live: the call
   site that still passes the old argument, the branch that still reads the old field.
3. The imports at the top of the file, when the hunk adds a call to anything not already in use.

Read a file whole in three cases only: it is under 300 lines, a hunk changes module-level state
(an import, a constant, a class field, a global), or it is untracked, since `git diff` shows no
hunk for a new file. A long file with a hunk inside one function does not need its other functions
read.

A file with no code units, such as Markdown, JSON, or YAML, has no enclosing unit. Read the
changed sections of it, then `Grep` the repository for every name the hunk renames, removes, or
re-counts, and read each use in place.

A test file in the changed set is read the same way. A test the hunk changed is a test to check
for an assertion that now proves nothing.

### Step 3: Find and Prove

Scan what you read against the Bug Categories, in priority order. For each candidate, write the
failure scenario before you decide anything: one concrete input or state, and the wrong output or
crash it produces on the current code. "Looks off" is not a scenario.

A candidate with a scenario is a finding. Give it a severity from the Severity Scale. A candidate
without one is not reported at all.

Stop at 10 findings. When there are more, keep the 10 highest by severity and say that the list
was capped.

### Step 4: Fix and Prove the Fix

For each finding, in severity order:

1. When the fix is unambiguous, apply it with the Edit tool. When two reasonable fixes exist, or
   the right behavior depends on intent you cannot see, leave the code alone and list the finding
   under "Needs Your Input".
2. Run the narrowest test command that covers the edited file. Take the command from the
   repository's `AGENTS.md` or `CLAUDE.md` check list, scoped to that file or its test file
   (`pytest path/to/test_x.py`, `npx vitest run path/to/x.test.ts`, `go test ./pkg/x/`). When the
   project lists no such command, use the language's standard runner on the matching test file.
   When no test covers the file, say so in the report and keep the fix only when its scenario is
   plain.
3. A fix whose test fails is reverted with `git checkout -- <file>` for a tracked file, or by
   re-applying the original text for an untracked one. Report it under "Needs Your Input" with the
   test's output.

**Be conservative:**

- Fix only what you proved in Step 3.
- Do NOT fix style, formatting, or naming.
- Do NOT refactor working code.
- Do NOT change behavior beyond the bug.

### Step 5: Report

Output the summary report below and nothing after it.

## Output Format

```markdown
## Fresh Eyes Review

**Changed set:** N files against <base> (bead <id>, when one was given)

### Issues Fixed

| File:Line | Severity | Category | Failure Scenario | Fix Applied | Proved By |
|---|---|---|---|---|---|
| src/auth.py:42 | HIGH | Bug | `user_id` is unbound when `session` is None, so sign-in raises NameError | Changed to `user.id` | `pytest tests/test_auth.py`: 12 passed, 0 failed |

### Needs Your Input

- [File:Line] [Severity] [Failure scenario, and why the fix is not yours to pick, or the test
  output that failed]

### Clean Files

- [Files reviewed with no finding]

### Summary

- Files reviewed: X (Y read whole, Z read by hunk; "whole" means every line of the file)
- Issues fixed: A, each proved by a passing test
- Needs input: B
- Findings capped: yes or no
```

## Severity Scale

- **CRITICAL** - Security vulnerability, data loss, or crash on normal input.
- **HIGH** - Wrong result on a real code path, or an unhandled boundary error.
- **MEDIUM** - Bug that only triggers on an edge case.

There is no LOW. A correctness nit with no failure scenario is not a finding here.

This skill fixes CRITICAL, HIGH, and MEDIUM findings directly when the fix is unambiguous.
Anything ambiguous is flagged for the user instead of guessed at.

## Critical Rules

**Always:**

- Read the diff before any file, and read each hunk's enclosing unit and symbol uses in place
- Write the failure scenario before you count a candidate as a finding
- Run the scoped test after every fix, and report its real counts
- Revert a fix whose test fails
- Include file:line references for every finding

**Never:**

- Fix style or formatting (that is a different review)
- Refactor working code (you are looking for bugs, not improvements)
- Edit a finding without a failure scenario, or guess at an ambiguous fix
- Read every changed file whole by default; the 300-line rule and module-level state decide
- Report LOW, or more than 10 findings
- Commit, push, or write to the tracker

## Quality Checklist

Before reporting completion, verify:

- [ ] Every hunk's enclosing unit and symbol uses were read in place
- [ ] Every finding carries a failure scenario and a severity
- [ ] Every fix names the scoped test that passed after it, with counts
- [ ] Every fix whose test failed was reverted and listed under Needs Your Input
- [ ] No finding is a style preference
- [ ] The summary counts match the tables
