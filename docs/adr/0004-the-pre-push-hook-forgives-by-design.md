# 0004. The pre-push hook forgives by design

**Date:** 2026-09-01
**Status:** Accepted

## Context

[ADR 0003](0003-a-push-to-main-is-already-published.md) establishes that a push to `main` reaches
every consumer immediately. That makes `.githooks/pre-push` the only automated check standing
between a change and its users.

A gate in that position invites a natural instinct: make it strict. Refuse anything unproven.

The hook does the opposite in four situations, and each looks like a hole until you ask what the
strict version would do instead.

**A tool is missing from PATH.** Neither `rumdl` nor `node` is universally installed. A fresh
clone on a new machine has neither.

**No quality-gates verdict has been recorded.** The second stage reads
`quality-gates-report.json` from the directory `git rev-parse --git-dir` resolves. A clone that
has never run `/quality-gates` has no such file.

**A verdict exists but was recorded for a different commit.** It describes some other tree.

**Every tool is missing.** The run checks nothing at all.

The hook also carries a documented off-switch, `TADW_PREPUSH=off`, which is exact: any other
value, empty included, leaves the hook on.

## Options Considered

### Option A: Forgive, and say so out loud

A missing tool warns by name and allows. A missing or unreadable verdict warns and allows. A
stale verdict warns and allows. Only a recorded `FAIL` refuses. A run that verified nothing says
so rather than reporting success.

- **Pros:** A clone is always pushable. Every forgiven case is named on stderr, so the gap is
  visible rather than silent. The one state that is real evidence of a problem, a recorded
  `FAIL`, still stops the push.
- **Cons:** A push can reach consumers having verified less than it appears to. Somebody who does
  not read stderr learns nothing.

### Option B: Fail closed

Any missing tool, any missing verdict, or any stale verdict refuses the push.

- **Pros:** No push is ever unverified. The gate means exactly one thing.
- **Cons:** A fresh clone cannot push until every tool is installed, which turns a documentation
  typo fix into an afternoon. The predictable response is `TADW_PREPUSH=off` in a shell profile,
  which disables the hook permanently and invisibly. A gate people routinely bypass is worse than
  a gate that forgives loudly, because the bypass is not logged anywhere.

### Option C: Fail closed on tools, forgive on the verdict

Require the tools, since they are installable, but tolerate a missing verdict.

- **Pros:** Splits the difference. The checks that can run always run.
- **Cons:** Keeps the worst property of Option B. The unpushable-fresh-clone case is a tool
  problem, not a verdict problem, so this option does not fix it.

## Decision

**Option A. The hook forgives, and names every forgiveness on stderr.**

The rule it follows: **refuse only on evidence of a problem, never on absence of evidence.** A
recorded `FAIL` is evidence. A missing report is not. A verdict recorded for another commit is
evidence about another tree, so it warns as stale and allows, while a `FAIL` in that state still
refuses, because one command refreshes it.

Three supporting behaviors follow from the same rule:

- **Every check runs, even after one fails**, and all failures report together. A hook that
  stopped at the first would make you push, fail, fix, and fail again on the next one.
- **A run where every tool was missing reports that it verified nothing.** It does not print
  "passed". A run that checked nothing has not earned the word. This matches the
  `quality-gates` skill, whose third principle states that "a gate that could not run is not a
  gate that passed" and maps BLOCKED to an overall FAIL
  (`skills/quality-gates/SKILL.md:43` and `:72`).
- **`TADW_PREPUSH=off` is documented here and in AGENTS.md**, so that nobody invents an
  undocumented workaround under deadline. An escape hatch people know about is one you can ask
  about later.

Option B lost on a prediction about people rather than about code: the strict version produces a
permanently disabled hook, and a disabled hook checks nothing at all. Option C lost because it
keeps that same failure mode.

## Consequences

**Easier:**

- A fresh clone can push immediately. Fixing a typo does not require installing a toolchain.
- The hook is worth leaving on, which is the property that actually determines how much it
  catches over a year.
- Every gap is on stderr with the tool named, so a person can see what was skipped and decide.

**Harder:**

- A green push does not prove the checks ran. Reading the summary line matters, because it
  carries how many of the total actually ran.
- Somebody who ignores stderr can push repeatedly with an incomplete gate and never notice.
- The forgiveness is easy to mistake for a bug. That is why the hook file carries the reasoning
  in comments at the point of each decision, and why this record exists.
- Recorded verdicts are per worktree, because `git rev-parse --git-dir` resolves differently
  there. A linked worktree reads its own verdict, not the main checkout's, which is correct but
  is not obvious.
