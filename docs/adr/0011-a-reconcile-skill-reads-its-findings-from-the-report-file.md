# 0011. A reconcile skill reads its findings from the report file and never grades its own fix

**Date:** 2026-09-13
**Status:** Accepted

## Context

Outrigger's autonomous loop runs `/tadw:quality-gates` and `/tadw:verify-acceptance` with no person
present. When either check fails, outrigger needs a tadw skill that fixes the failure and gives the
work back for another check, at most 3 times per check. Two skills do that job:
`reconcile-quality-gates` and `reconcile-acceptance`. The full design is in
[the reconcile skills plan](../plans/feature-plan-reconcile-skills.md).

Three facts constrain where a fixer can get its findings, meaning the failing rows it must fix.

**The report files carry verdicts, not findings.** `quality-gates-report.json` gives each gate one
`detail` line (`skills/quality-gates/SKILL.md:771-796`). `acceptance-report.json` holds a bead id
and seven counts (`skills/verify-acceptance/SKILL.md:114-123`). The failing output lives only in the
markdown report.

**A transcript does not cross outrigger's process boundary.** Outrigger runs each phase in a
separate `claude -p` process. A file in the git directory survives that boundary; a transcript and a
dispatch prompt do not.

**A grade that the fixer writes cannot be trusted.** `verify-acceptance` already refuses a
`verdict` field in its report for this reason: a model that grades its own work passes it. A fixer
that re-ran the full check and recorded the result would repeat that failure.

## Options Considered

### Option A: Findings in the existing report files

Each check skill writes its findings into the JSON file it already writes, at `version: 2`, through
a script. The fixer reads only that file.

- **Pros:** One `json.dump` call writes the verdict and the findings, so they cannot describe
  different runs. The path is already per worktree. No existing reader breaks: the pre-push hook
  reads `verdict`, `head`, and `timestamp` with `.get`, and the label hook reads each count by name.
- **Cons:** Both report schemas grow, and two scripts must now write them.

### Option B: A second findings file beside each report

- **Pros:** The report schemas stay as they are.
- **Cons:** One run writes two files that can disagree, and a fixer cannot tell which one is stale.

### Option C: A bead comment, as outrigger does with `outrigger-acceptance-report:`

- **Pros:** The findings sit on the bead, where a person reads them.
- **Cons:** It ties the check skills to `bd` for data that is not tracker state.
  `skills/quality-gates/SKILL.md:24` says that skill "needs no issue tracker, no bead".

### Option D: The transcript or the dispatch prompt

- **Pros:** Nothing new is written.
- **Cons:** It fails in outrigger, where each phase is its own process. A report copied from a
  transcript also has no `head` to check against the tree.

## Decision

**Option A. A reconcile skill reads its findings only from the report file its check skill wrote,
and it never grades its own fix.**

Option B lost because two files from one run can disagree. Option C lost on the coupling to `bd`.
Option D lost at outrigger's process boundary.

These rules follow from the decision, and other components obey them:

1. **The fixer starts only when the report's `head` equals `HEAD`.** It makes one commit per run,
   so `HEAD` moves and the same report goes stale. Nobody can attempt a second fix without running
   the check again.
2. **The fixer never writes either report file and never runs the full check.** It re-runs only the
   commands of the rows it fixed, as a local test before committing.
3. **A check skill never calls its fixer.** It prints a `**Next:**` line on `FAIL` or
   `NOT ACCEPTED`. The caller calls the fixer and counts attempts.
4. **Every new script is told its inputs.** No new script runs `git` or `bd`. The skill passes each
   value as an argument, so each script is a pure function its tests call without a git repository.
5. **The fixer ends with one machine line** from a closed list of ten BLOCKED reasons, checked in
   the order the plan's reasons table sets.

Three smaller choices were settled with the same decision, and their losing options are recorded
here so they are not argued again:

- **The base is named, never detected.** Detecting a stacked branch's parent is a guess, and a
  wrong guess narrows the scope while the report still reads as confident. `changed_set.py` gains
  `--base <ref>` instead.
- **The fixer refuses a file with uncommitted changes.** Committing the whole file was the other
  choice, and it would put work nobody asked to commit into a fix commit.
- **Two loaders, one per report shape.** A shared loader would need a mode argument or a third file,
  and house rule 1 waits for a third copy. The runtime cost is the same, because the model reads the
  loader's output and never its source.

## Consequences

**Easier:**

- Outrigger routes on one machine line and one file, with no transcript parsing.
- Every fix attempt is graded by the check skill, never by the fixer, because the stale `head`
  forces a new check.
- The loaders and writers are tested with plain values, so their suites need no git repository.

**Harder:**

- **The report files are now a contract between two repositories.** A field rename in tadw breaks
  outrigger. `version: 2` marks the shape, and a loader refuses any other version with
  `report-unreadable`.
- **A person working by hand must commit before calling a fixer.** A manual report is usually
  written before a commit, so the fixer often stops with `uncommitted-changes` or `report-stale`.
- **A flipping verdict makes the loop repeat.** `tadw-4s5` records that `/tadw:quality-gates` can
  give different verdicts on one tree. Until it is fixed, outrigger's cap of 3 attempts is the only
  bound, so `tadw-4s5` blocks `reconcile-quality-gates`.
