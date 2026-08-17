---
description: "Check whether the current unit of work met its bead's acceptance criteria and passed the QA gates"
argument-hint: "[bead-id]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/verify-acceptance/SKILL.md` and follow it to grade the current unit of work.

Read the file rather than invoking the skill by name. `commands/verify-acceptance.md` and
`skills/verify-acceptance/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(verify-acceptance)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/verify-acceptance/SKILL.md` and read it from there.

The skill will:

1. Resolve the bead from `bd list --status in_progress`, the branch name, or the commit messages
2. Read its `acceptance_criteria` (and any `## Done when` block in `notes`)
3. Grade each criterion PASS / FAIL / UNVERIFIABLE against evidence, never against the diff
4. Run the QA gates (tests, linting, type checking, security) and record their real counts
5. Report one verdict table: ACCEPTED, NOT ACCEPTED, or INCONCLUSIVE

Report-only. It never edits code, never closes a bead, and never invents criteria when the bead records none.

Pass a bead id as an argument to grade that bead instead of the auto-resolved one. No argument needed otherwise.

Invoke it by hand with `/verify-acceptance`, usually right after a fresh-eyes review.
