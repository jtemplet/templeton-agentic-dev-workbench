---
description: "Review all new/modified code with fresh eyes, find and fix obvious bugs and errors"
argument-hint: "[--base <ref>] [bead-id]"
---

Dispatch the `fresh-eyes-reviewer` agent (`agents/fresh-eyes-reviewer.md`) with `$ARGUMENTS` as
its input, and relay its report whole. Use the Agent tool with `subagent_type` set to
`tadw:fresh-eyes-reviewer`. Do not run the review in this window.

The agent runs the `review-fresh-eyes` skill on `sonnet` in its own context window. It reads the
diff and the code each hunk touches there, so the file text never enters this window; only the
report comes back. The `reviewed` label lands from this command's own name, before the dispatch.

Pass `--base <ref>` on a stacked branch, meaning a branch built on another branch that is not
merged yet. The agent then reviews only the files this branch changed. Pass a bead id to have
the report name it.

The agent will:

1. Resolve the changed set from git state (committed, staged, unstaged, and untracked work)
2. Read the diff, then the enclosing unit of each hunk and every in-file use of a symbol the hunk
   adds, renames, or removes; a whole file only when it is short or the hunk changes module-level
   state
3. Look for bugs, logic errors, missing error handling at a boundary, copy-paste errors, and
   security issues
4. **Fix a finding only after naming the input that makes the current code wrong**, then run the
   narrowest test that covers the edited file; a fix that fails its test is reverted and reported
5. Return one report table: issues fixed with the test that proved each, issues that need your
   input with the `file:line` it read and the line quoted, claims it could not check, and the
   files it read clean

When the report lists an issue under "Needs Your Input", answer it here; the agent has already
ended, so re-run the command after you decide. A claim under "Not checked" is not a finding yet:
read the code the report names before you act on it.
