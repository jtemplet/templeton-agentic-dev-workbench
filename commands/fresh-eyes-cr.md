---
description: "Review all new/modified code with fresh eyes, find and fix obvious bugs and errors"
---

Use the `fresh-eyes-reviewer` agent to review all recently changed code.

The agent will:

1. Auto-detect changed files from git state (unstaged, staged, or branch diff vs main)
2. Read full files (not just diffs) for complete context
3. Look for bugs, logic errors, missing error handling, copy-paste errors, and security issues
4. **Fix issues directly** using the Edit tool, explaining each fix
5. Report a summary table of issues found, fixes applied, and files needing your input

No arguments needed — scope is auto-detected from git.
