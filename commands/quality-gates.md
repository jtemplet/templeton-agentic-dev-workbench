---
description: "QA the change: tests, change coverage and span, a live curl probe of changed REST endpoints, lint, type checks, doc freshness, hygiene. Scoped to what changed by default"
argument-hint: "[--changed | --all] [--base <ref>] [bead-id]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/SKILL.md` and follow it to run the gates
against the current tree.

Read the file rather than invoking the skill by name. `commands/quality-gates.md` and
`skills/quality-gates/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(quality-gates)` returns this file and never reaches the skill. If that path does not resolve,
locate the file with `Glob: **/skills/quality-gates/SKILL.md` and read it from there.

The skill will:

1. Discover the gate set from `AGENTS.md`, CI config, or a task runner, and fall back to language
   auto-detect only when none of those names a check
2. **Read the diff and pick the QA method the change earns**: real curl requests against a local
   server for a REST surface, a handoff to `agent-browser` for browser UI (or `agent-device` for
   mobile), and a test-coverage review alone for a CLI, a library, or prompt assets. A full-stack
   diff gets several methods, not a choice between them
3. Run tests, change coverage, the live API probe, lint, type checking, doc freshness, and hygiene,
   each with a bounded timeout
4. Check that every case the change introduces is exercised at the unit level, and that every CLI
   command or HTTP route it touches is exercised end to end through the real entry point
5. Check the span of each case, meaning the classes of input, state, and outcome, and name the
   classes nothing covers
6. Hand a browser UI change to `agent-browser`, or a mobile UI change to `agent-device`, on its own
   report row rather than passing it, which makes the run INCOMPLETE
7. Record a configured gate it could not run as BLOCKED, which fails the run, rather than as a skip
8. Report one table carrying the exact command and real counts for every gate
9. Write that verdict, the routing, every gate row, and one finding per Action Item to
   `quality-gates-report.json` inside the git directory, through `write_report_json.py`, so a tool
   can read the conclusion instead of parsing prose. The script refuses a report whose verdict
   disagrees with its gate rows, and writes nothing then. The file is
   `.git/quality-gates-report.json` in an ordinary clone, and a per-worktree path in a worktree,
   resolved by `git rev-parse --git-dir` rather than hardcoded
10. End a FAIL report with a `**Next:**` line naming `/tadw:reconcile-quality-gates`, for you to
    run. It never runs that skill itself

**The live probe addresses this machine unless you name somewhere else.** With no URL given it
probes `http://127.0.0.1:3000`, and it never infers a host from a config file or a URL it read in
the repository, because it sends POST, PUT, PATCH, and DELETE. A URL you supply is used as given and
marked `(NOT this machine)` in the summary when it is not loopback, so a remote probe cannot go
unmentioned in the report. It starts a server only when the project declares a start command, always
stops it, and reports SKIP rather than guessing one. A refused connection is BLOCKED, never a
failing endpoint.

**A passing probe is not an end-to-end test.** It measures this build and leaves nothing behind, so
a REST change with a green probe and no committed request-level test is still a change-coverage
finding.

**No issue tracker is involved.** The skill's whole input is the diff; it needs no bead and no
written acceptance criteria.

Report-only. It never fixes, formats, or edits anything in the working tree, and it never rewrites
the working tree to establish a baseline. It writes three files, all inside the git directory and
never committed: the changed set `quality-gates-changed.txt`, the JSON artifact above, and the
probe spec `quality-gates-probe.json` when the live probe runs. It writes none of them when the
tree is not a git repository.

**The default scope is the change, not the repository.** `--changed` runs the tests that cover the
changed code and narrows lint, doc freshness, and hygiene to changed files. The report says the full
suite did not run. One gate stays wide on purpose: type checking analyzes the whole project and
reports only the changed files, because a type error surfaces in the consumer. Pass `--all` for the
repository-wide sweep. With no argument it uses `--changed`, falling back to `--all` when the base
will not resolve.

**Pass `--base <ref>` on a stacked branch,** meaning a branch built on another branch that is not
merged yet. The changed set then holds this branch's commits alone. A named base that does not
resolve is BLOCKED, and never widens to `--all`. Pass a bead id to record it in the report, where
`/tadw:reconcile-quality-gates` reads it.

The gate is proportionate by design. It asks for one test per span class, never their cross-product,
and never for defensive code around a failure that cannot happen.

`/verify-acceptance` runs the four gates that can invalidate an acceptance claim, and points here
for the rest.
