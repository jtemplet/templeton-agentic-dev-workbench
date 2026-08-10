---
description: "QA the change: tests, change coverage and span, lint, type checks, doc freshness, secrets, hygiene. Scoped to what changed by default"
argument-hint: "[--changed | --all]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/SKILL.md` and follow it to run the gates against the current tree.

Read the file rather than invoking the skill by name. `commands/quality-gates.md` and
`skills/quality-gates/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(quality-gates)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/quality-gates/SKILL.md` and read it from there.

The skill will:

1. Discover the gate set from `AGENTS.md`, CI config, or a task runner, and fall back to language auto-detect only when none of those names a check
2. Run tests, change coverage, lint, type checking, doc freshness, secrets, and hygiene, each with a bounded timeout
3. Check that every case the change introduces is exercised at the unit level, and that every CLI command or HTTP route it touches is exercised end to end through the real entry point
4. Check the span of each case, meaning the classes of input, state, and outcome, and name the classes nothing covers
5. Hand a browser or mobile UI change to `/qa` rather than passing it, which makes the run INCOMPLETE
6. Record a configured gate it could not run as BLOCKED, which fails the run, rather than as a skip
7. Report one table carrying the exact command and real counts for every gate

Report-only. It never fixes, formats, or edits anything, and it never rewrites the working tree to establish a baseline.

**The default scope is the change, not the repository.** `--changed` runs the tests that cover the changed code and narrows lint, doc freshness, and hygiene to changed files. The report says the full suite did not run. Two gates stay wide on purpose: type checking analyzes the whole project and reports only the changed files, because a type error surfaces in the consumer; the secret scan always covers the whole tree. Pass `--all` for the repository-wide sweep. With no argument it uses `--changed`, falling back to `--all` when the base will not resolve.

The gate is proportionate by design. It asks for one test per span class, never their cross-product, and never for defensive code around a failure that cannot happen.

`/verify-acceptance` runs the four gates that can invalidate an acceptance claim, and points here for the rest.
