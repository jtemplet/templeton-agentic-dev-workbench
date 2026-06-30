---
name: fresh-eyes-review
description: Review recently changed code as if seeing it for the first time. Auto-detects changed files from git, reads full files for context, finds genuine bugs and logic errors, and fixes them directly. Conservative scope: real bugs, not style preferences.
---

# Fresh Eyes Review

A conservative bug-and-correctness pass over recently changed code. Reads full files (not just diffs) to spot issues the diff view hides, then fixes genuine bugs directly.

## When to Use / When NOT to Use

Use when:

- After implementing a feature, before committing
- After refactoring, to catch errors introduced by the changes
- When asked to "review my changes" or "check what I just did"
- Before opening a pull request, as a self-review pass

Do NOT use when:

- For style or formatting feedback (this is not a style review)
- For architectural review (this is not a design review)
- For full PR review (this is a fast bug-and-correctness pass, not comprehensive)
- On code with no recent changes (nothing to review)

## Universal Core (injected)

The universal style core (`hooks/style-core.md`) defines how code should be written, but this skill deliberately does NOT enforce it. This is a conservative bug-and-correctness pass: it flags and fixes genuine bugs only, never style, formatting, naming, or design. Treat the core as the boundary marker here, not the checklist. If something is merely a style or design deviation rather than a defect, leave it alone.

## Bug Categories

Look for these, in priority order:

| Category | Examples |
|---|---|
| **Bugs** | Off-by-one, null/nil dereference, wrong variable name, missing return |
| **Logic Errors** | Inverted condition, unreachable code, infinite loop potential |
| **Missing Error Handling** | Unhandled exceptions at system boundaries, missing nil checks on external data |
| **Copy-Paste Errors** | Duplicated blocks with one not updated, wrong variable in repeated pattern |
| **Security Issues** | SQL injection, XSS, hardcoded secrets, path traversal |
| **Confusion** | Variable shadowing, misleading names, dead code that looks active |

## Required Workflow

### Step 1: Identify Changed Files

Try these in order until you get results:

```bash
# Unstaged + staged changes
git diff --name-only
git diff --cached --name-only
```

If both are empty:

```bash
# Branch changes vs main
git diff main...HEAD --name-only
```

If still empty, inform the user there are no changes to review.

### Step 2: Read Full Files

For every changed file, read the **entire file**, not just the diff hunks. You need surrounding context to spot issues like:

- Variables used before being defined
- Functions called with wrong arguments
- Missing imports or broken references
- Logic that contradicts code elsewhere in the file

### Step 3: Review for Issues

Scan each file against the Bug Categories above, in priority order. Assign a severity label (see Severity Scale) to every issue you find.

### Step 4: Fix Issues Directly

For each issue found:

1. Use the Edit tool to apply the fix
2. Explain what was wrong and why the fix is correct

**Be conservative:**

- Only fix clear bugs and errors
- Do NOT fix style, formatting, or naming preferences
- Do NOT refactor working code
- If unsure whether something is a bug, flag it but do not fix it

### Step 5: Report

Output the summary report (see Output Format).

## Output Format

```markdown
## Fresh Eyes Review

### Issues Fixed

| File:Line | Severity | Category | What Was Wrong | Fix Applied |
|---|---|---|---|---|
| src/auth.py:42 | HIGH | Bug | Wrong variable `user_id` should be `user.id` | Changed to `user.id` |
| ... | ... | ... | ... | ... |

### Needs Your Input

- [File:Line] [Severity] [Description of ambiguous issue]

### Clean Files

- [Files reviewed with no issues found]

### Summary

- Files reviewed: X
- Issues fixed: Y
- Needs input: Z
```

## Severity Scale

Label every reported issue with one of these levels:

- **CRITICAL** - Security vulnerability, data loss, or crash on normal input.
- **HIGH** - Wrong result on a real code path, or an unhandled boundary error.
- **MEDIUM** - Bug that only triggers on an edge case.
- **LOW** - Minor or cosmetic correctness nit.

This skill fixes CRITICAL, HIGH, and MEDIUM bugs directly when the fix is unambiguous. Anything ambiguous is flagged for the user instead of guessed at.

## Critical Rules

**Always:**

- Read the full file, not just the diff
- Fix bugs directly via Edit, do not just report them
- Explain every fix clearly
- Be conservative, only fix clear problems
- Include file:line references for every issue

**Never:**

- Fix style or formatting (that is a different review)
- Refactor working code (you are looking for bugs, not improvements)
- Guess at fixes for ambiguous issues (flag those for the user)
- Skip files because they look fine from the diff (read the whole thing)
- Make changes that alter behavior beyond fixing the bug

## Quality Checklist

Before reporting completion, verify:

- [ ] All changed files were read in full (not just diffs)
- [ ] Every fix is genuinely a bug, not a style preference
- [ ] Every fix is explained with before/after reasoning
- [ ] Every reported issue carries a severity label
- [ ] Ambiguous issues are flagged, not silently fixed
- [ ] Summary table is complete and accurate
