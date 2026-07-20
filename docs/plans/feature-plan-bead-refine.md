# Feature Plan: Bead Refinement (scored backlog refinement loop)

**Date:** 2026-07-20
**Status:** Milestone 1 shipped (scorecard in bead-audit, commit 94b9e22). Milestones 2-4 (the driver) blocked on a state-machine respecification of "Loop state and termination" per two Major Rework reviews; see Open Questions.

## Summary

Add a scored refinement loop that brings every open bead in a repo up to a target quality band. This splits into two pieces: a **scorecard rubric** added to the existing `bead-audit` skill (which today emits only a 3-state verdict), and a new **`bead-refinement` driver** skill plus **`/bead-refine`** command that enumerates open beads, calls the audit, applies the safe fixes, and reports progress. The driver is idempotent so it can run under `/loop` until the backlog converges.

Naming follows the repo's existing convention of a noun skill with a verb command, as in `pr-maintenance` and `/pr-maintain`: the skill is `bead-refinement`, the command is `/bead-refine`.

## Motivation

`bead-audit` already encodes the quality bar (Marr Why/How/Done when, size band, type-specific Acceptance Criteria / Steps to Reproduce / Success Criteria) and already documents a loop contract at `skills/bead-audit/SKILL.md:305`. But it is deliberately tracker-agnostic and write-free: it audits the *text* of one bead and returns corrected content. Three things are therefore missing before it can refine a backlog unattended:

1. There is no score, only PASS / REFORMAT / NEEDS WORK. "Get every bead to Great or Excellent" is not expressible.
2. Nothing enumerates open beads. `skills/bead-audit/SKILL.md:10` explicitly makes fetching the caller's job.
3. Nothing writes back. `skills/bead-audit/SKILL.md:386` states the skill issues no tracker write commands.

The beneficiary is anyone inheriting or maintaining a backlog written before the current standard existed. Beads created ad hoc via `br create "title"` carry no Why, no How, and no acceptance criteria, so they cannot be picked up without asking the author, which is exactly the failure `plan-to-beads` was built to prevent at creation time. This closes the same gap retroactively.

## Scope

### In Scope

- A weighted scorecard rubric added to `bead-audit`, computed from its existing verdicts, with named bands and verdict-derived band caps
- `score` and `band` fields added to `bead-audit`'s JSON output mode
- A new `bead-refinement` skill: enumerate open beads, audit each, apply `applyable` fixes to canonical destinations, verify the score rose, report the iteration
- A new `/bead-refine` command with `--target`, `--dry-run`, and `--max-writes`
- Cross-bead duplicate detection by token similarity, report-only
- Registration in `.claude-plugin/plugin.json`, `AGENTS.md`, and `README.md`

### Out of Scope

- Auto-merging or auto-closing duplicate beads. Detection reports; a human decides. Merging is destructive and irreversible from a loop.
- Changing a bead's title, type, priority, status, or dependency edges. The loop only touches audited content fields.
- Refining beads whose status is anything other than `open`. Closed, deferred, and `in_progress` beads are never fetched. Excluding `in_progress` is deliberate: it is what lets the driver skip work another agent or human has claimed, without claiming anything itself.
- Support for trackers other than `br` in v1. The audit stays tracker-agnostic; the driver targets `br` first and isolates tracker calls so a second adapter is additive.
- Creating new beads to fill gaps. The loop improves existing beads only.

## Technical Approach

### Architecture

Two layers with a clean seam, mirroring the split the repo already uses for `pr-maintenance` (driver) and the style skills (judgment):

```text
/bead-refine  →  bead-refinement skill     →  bead-audit skill
   command        (tracker I/O, loop           (pure text judgment,
                   state, write-back)            score, corrected fields)
```

`bead-audit` stays pure: text in, verdict + score + corrected content out. It gains scoring but no tracker coupling and no write commands. `bead-refinement` owns everything side-effecting: `br list`, `br update`, `br sync`. This preserves the One Tool One Job and No Surprise Side Effects principles in `skills/agentic-clean-code/SKILL.md`, and keeps `bead-audit` usable standalone by a human pasting a body.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `skills/bead-audit/SKILL.md` | Add "Scorecard" section; add `score`/`band` to JSON schema | Modified |
| `skills/bead-audit/references/fixtures/` | Five scored fixture beads; the rubric's regression suite | New |
| `skills/bead-refinement/SKILL.md` | Driver: enumerate, audit, apply, verify, report, terminate | New |
| `commands/bead-refine.md` | Entry point; `--target`, `--dry-run`, `--max-writes` | New |
| `.claude-plugin/plugin.json`, `AGENTS.md`, `README.md` | Registration | Modified |

### Scoring model

Points are **derived from the verdicts `bead-audit` already produces**, never assigned directly. Content `pass` earns a dimension's full weight, `warn` half, `fail` zero.

| Dimension | Weight | Applies to |
|---|---|---|
| Why (Computational) | 20 | all types |
| How (Algorithmic) | 20 | all types |
| Done when (Acceptance) | 20 | all types |
| Acceptance Criteria (Success Criteria for epic) | 20 | all types |
| Steps to Reproduce | 10 | `bug` only |
| Estimated size | 10 | code-bearing beads only |
| Structure | 10 | all types |

**Structure aggregation (stated explicitly, because the score is not derivable without it):** structure earns `10 × (canonical required sections ÷ total required sections)`. A section that is absent counts as not canonical. Native tracker fields count as canonical per ADR 0001.

**Renormalization.** The denominator is the sum of applicable weights, not a fixed 100, so a bead with no applicable size dimension can still reach 100. Applicability is **never model-inferred**: size is excluded only when `issue_type == epic` or the bead carries an explicit `operational` label a human set. This closes an inflation vector, since a model could otherwise drop 10 points from any denominator by declaring a bead operational.

**Band caps, which override the score.** The raw score alone contradicts `bead-audit`'s own verdict at realistic inputs, so the reported band is the **lower** of the score band and the ceiling implied by the rollup verdict:

| Rollup verdict | Condition | Band ceiling |
|---|---|---|
| NEEDS WORK | any required-section content `fail` | Weak |
| REFORMAT | all content `pass`, any structure `variant`/`absent` | Great |
| REFORMAT (weak content) | any content `warn`, no content `fail` | Great, per `bead-audit:184` |
| PASS | all content `pass`, all structure `canonical` | Excellent (no cap) |

Bands: Excellent 90-100, Great 75-89, Adequate 60-74, Weak 40-59, Poor below 40.

Worked arithmetic, computed from the weights and aggregation rule above rather than asserted:

| Bead state | Raw | Uncapped band | Ceiling | Reported |
|---|---|---|---|---|
| task, no Acceptance Criteria | 78.0 | Great | Weak | **Weak** |
| task, no Why | 78.0 | Great | Weak | **Weak** |
| task, all content pass, every heading variant | 90.0 | Excellent | Great | **Great** |
| bug, no Steps to Reproduce | 89.4 | Great | Weak | **Weak** |
| task, all content warn, canonical | 55.0 | Weak | Great | **Weak** |
| epic, clean, size N/A | 100.0 | Excellent | Excellent | **Excellent** |

Rows 1, 2, and 4 are why the caps exist: each is a bead the audit calls NEEDS WORK that the raw score would otherwise band as Great. Row 4 is also why `Steps to Reproduce` must carry weight; without it that bead scores 100 while banding Weak, an incoherent report.

**Default target: Excellent.** ADR 0001 settled that native tracker fields are canonical and `plan-to-beads` now writes them, so newly generated beads are born canonical and the Great-to-Excellent distance is genuinely mechanical. See "First run against a legacy backlog" for the one case where this is not cheap.

### Enumeration

One call returns everything the audit needs: `br list --status open --limit 0 --json` emits `{issues, total, limit, offset, has_more}`, with `description`, `design`, `notes`, and `acceptance_criteria` all inline. No per-bead `br show` is required.

Two verified details the driver must honor:

- **`--limit` defaults to 50.** Omitting it silently truncates any backlog larger than 50 beads and would then report convergence, precisely the "no silent caps" failure. Pass `--limit 0` (unlimited) and assert `has_more == false` after reading.
- **`--status open` excludes `in_progress` and `deferred`.** Beads a human or another agent has claimed are never fetched, so the loop cannot clobber active work without needing to claim anything itself.

### Write-back

Fixes go to their canonical destinations per ADR 0001: `--design` for How, `--notes` for Done when and Out of scope, `--acceptance-criteria` for Acceptance Criteria, and `--description` for Why, Estimated size, Steps to Reproduce, and Success Criteria. Note `br update` has **no `-d` short form**; that alias exists only on `br create`.

**Content-preservation guard.** `br update --description` replaces the field wholesale, and `bead-audit`'s drafting template emits canonical sections only (`bead-audit:385` forbids adding sections not required for the type). Any author content that is not a canonical section (context links, a scratch checklist, prior discussion) would be silently destroyed. Before any description write, the driver diffs the pre-image against the draft and **refuses the write, routing the bead to a human, if any non-whitespace content in the original has no counterpart in the draft.** Across an unattended sweep this is the highest-consequence failure mode in the design.

The driver never claims a bead. Claiming sets status to `in_progress`, which this plan places out of scope, and would surface refinement as phantom work in `bv --robot-next` and `br ready`.

### Loop state and termination

Each iteration re-derives bead state from the tracker, so the loop is safe to interrupt and resume. Within a single run the driver keeps an in-memory ledger of `(bead id, prior score, new score)`.

**Three terminal categories.** A bead is finished when it is any one of:

- **at-target**: its band is at or above `--target`.
- **blocked-on-human**: `applyable: false`, so a person must supply content the audit cannot infer.
- **stalled**: audited, below target, `applyable: true` produced no score improvement, and unchanged since the prior iteration.

The stalled category is load-bearing. A bead whose content is all `warn` scores 55, bands Weak, and is *not* `blocked_on_human` (its content exists, it is merely weak), so a two-category predicate can never converge on it. Weak-but-complete is the most common state in an inherited backlog and the exact population this feature targets.

**Signals**, emitted so `/loop` has an unambiguous terminal condition:

- `REFINE: CONVERGED` when every open bead is at-target, blocked-on-human, or stalled, and the iteration wrote nothing.
- `REFINE: PROGRESS <n> updated` when the iteration improved at least one bead.
- `REFINE: HALTED <id> <reason>` on a regression (a write that did not raise the score), a refused description write, or a bead written twice in one run. `/loop` treats HALTED as terminal; it is not retried.

The oscillation guard matters because the audit is model judgment, not a pure function: a borderline bead can be judged `warn` on one iteration and `pass` on the next, producing an endless PROGRESS stream with nothing actually improving. Writing the same id twice in one run, or a score returning to a previously-seen value, halts the run.

### First run against a legacy backlog

A backlog created before ADR 0001 has every How and Done when in the description body, so `bead-audit` rates them all `structure: variant` and a default-target run will restructure every bead at once. That is correct work but a large blast radius for a first contact.

The driver therefore **refuses an unattended (non-dry-run) first run against a backlog where no bead is yet canonical**, and directs the user to `--dry-run` first. It also refuses any unattended run when `git status --porcelain .beads/issues.jsonl` is non-empty, because the rollback procedure below discards uncommitted bead state indiscriminately.

### Rollback

Every write is recoverable, and the driver prints this procedure in its iteration report so the path is never tribal knowledge:

```bash
git checkout .beads/issues.jsonl   # restore the last committed backlog state
br sync --import-only              # re-import JSONL into the local DB
```

This works because `.beads/issues.jsonl` is git-tracked and `br update` auto-flushes to it. **The restore is indiscriminate**: it discards all uncommitted bead state, including unrelated beads created in the same session. That is why the dirty-tree pre-flight above is a refusal rather than a warning.

### Duplicate detection

Report-only. Two beads are candidate duplicates when the normalized-token Jaccard similarity of their combined Why and How exceeds 0.8. Reported as a ranked list with scores, never acted on. Exact-string matching would almost never fire; unbounded semantic matching would make the result unfalsifiable. Comparison is capped at the 200 highest-priority open beads to bound the O(n²) sweep, and the report states when that cap truncated the comparison.

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Scorecard in `bead-audit` | Weighted rubric, structure aggregation rule, band caps, restricted renormalization, `score`/`band` JSON fields, and the five fixtures | M | Each fixture in `skills/bead-audit/references/fixtures/` scores its documented band, including criteria 5, 6, and 7 |
| 2 | `bead-refinement` skill + registration | Enumerate, audit, apply with content guard, verify-after, ledger, three terminal states, signals, rollback in report; registered in manifest, AGENTS.md, README.md | M | Running twice on a converged backlog emits `REFINE: CONVERGED` both times and writes nothing on the second run |
| 3 | `/bead-refine` command | Command file with `--target`, `--dry-run`, `--max-writes`; pre-flight refusals | S | `/validate-plugin` reports no orphans and no broken references |
| 4 | Duplicate detection | Jaccard similarity report over open beads | S | Two deliberately duplicated beads are reported as a pair with a score, and neither is modified |

Registration sits in milestone 2, not 3, because a skill directory that exists without a manifest entry fails `/validate-plugin`'s orphan check, and leaving that window open would mean the repo fails its own validator between milestones.

The five fixtures, authored as part of milestone 1: `excellent-task`, `reformat-only`, `needs-work-no-ac`, `epic-without-size`, `bug-without-repro`.

## Acceptance Criteria

1. Given a bead with a rich Why, How, Done when, and Acceptance Criteria in their canonical destinations, when audited, then it scores 90 or above and reports band Excellent.
2. Given a bead with only a title and a one-line description, when audited, then it scores below 40, reports band Poor, and is marked `applyable: false` with `blocked_on` naming the missing sections.
3. Given an epic with no size dimension, when audited, then size is excluded from the denominator and the epic can reach a score of 100.
4. Given a bead whose content is complete but written under non-canonical headings, when refined, then it is moved to its canonical destinations, its band rises, and no wording of its substance is altered.
5. Given a task bead missing its Acceptance Criteria but complete elsewhere, when audited, then it reports Weak (not Great), so the loop does not treat it as done.
6. Given a bug bead missing Steps to Reproduce but complete elsewhere, when audited, then it scores below 90 and reports Weak, never a passing score alongside a failing band.
7. Given a bead whose every content verdict is `warn` and no verdict is `fail`, when audited, then the WARN cap applies and it reports at most Great.
8. Given a backlog where every open bead is at-target, blocked-on-human, or stalled, when `/bead-refine` runs, then it writes nothing and emits `REFINE: CONVERGED`.
9. Given a backlog containing one weak-but-complete bead that no write can improve, when `/bead-refine` runs repeatedly, then that bead is classified stalled and `REFINE: CONVERGED` still fires.
10. Given a write that does not raise a bead's score, when the post-write re-audit runs, then the driver emits `REFINE: HALTED <id> regression` and stops.
11. Given a description whose pre-image contains author content absent from the draft, when the driver attempts the write, then it refuses, routes the bead to a human, and emits `REFINE: HALTED <id> content-loss`.
12. Given the same bead id written twice within one run, when the ledger detects it, then the driver emits `REFINE: HALTED <id> oscillation` and stops.
13. Given `--target great` on a backlog of Great-band beads, when `/bead-refine` runs, then it writes nothing and converges, proving the target is honored rather than hard-coded.
14. Given `--max-writes 5` on a backlog of 20 refinable beads, when `/bead-refine` runs, then exactly 5 beads are written and the report states how many were deferred.
15. Given `--dry-run`, when `/bead-refine` runs, then it prints the intended updates and `br sync --flush-only` afterward reports no dirty issues.
16. Given a backlog of more than 50 open beads, when `/bead-refine` enumerates, then every open bead is audited and `has_more` is false, proving the default 50-row page cap was overridden.
17. Given a bead whose status is closed, deferred, or `in_progress`, when `/bead-refine` runs, then it is never fetched or modified.
18. Given a working tree where `.beads/issues.jsonl` is uncommitted, when `/bead-refine` runs without `--dry-run`, then it refuses to start and names the dirty file.
19. Given a backlog in which no bead is yet structurally canonical, when `/bead-refine` runs without `--dry-run`, then it refuses and directs the user to dry-run first.
20. Given two open beads whose combined Why and How exceed 0.8 token similarity, when `/bead-refine` runs, then both are reported as a duplicate pair with the score, and neither is merged, closed, or edited.
21. Given any scored bead, when its report is printed, then it includes the per-section content and structure verdicts and the weight-by-weight sum, so the score is checkable rather than asserted.
22. Given any completed iteration, when the report is printed, then it includes the rollback procedure verbatim.
23. Given the shipped skill, when `grep -rl "skills/bead-refinement" .claude-plugin/plugin.json AGENTS.md README.md` runs, then all three files match.

**Coverage:** every item in "In Scope" and every goal in "Motivation" is proven by at least one criterion above.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Score inflation: the model assigns a passing score rather than deriving it | High | High | Score computed from verdicts; criterion 21 requires the verdict table and weight-by-weight sum in every report; band caps mean an inflated score cannot lift a bead past its verdict ceiling |
| Score contradicts the verdict (a bead missing a required section bands as Great) | High | High | Band caps plus a weighted dimension for every required section including Steps to Reproduce; criteria 5, 6, 7 and fixtures cover it |
| Description write destroys non-canonical author content | High | Medium | Pre-write diff refuses any write dropping unmatched content (criterion 11); the guard is a refusal, not a warning |
| Non-termination: convergence unreachable for weak-but-complete beads | High | Medium | Third terminal category (stalled); criterion 9 |
| Oscillation across iterations from non-deterministic judgment | Medium | Medium | Per-run ledger halts on a repeat write or a repeated score (criterion 12) |
| Silent truncation: only the first page groomed, then convergence reported | High | Medium | `--limit 0` plus a `has_more == false` assertion; criterion 16 |
| Renormalization abused to shrink the denominator | Medium | Medium | Applicability restricted to `issue_type == epic` or an explicit human-set `operational` label; never inferred |
| First run restructures an entire legacy backlog unattended | Medium | Medium | Refuses a non-dry-run first contact with a fully non-canonical backlog (criterion 19) |
| Rollback discards unrelated uncommitted bead state | Medium | Medium | Dirty-tree pre-flight refusal (criterion 18); rollback text states the restore is indiscriminate |
| Unattended write-back applies placeholder-bearing drafts | High | Low | `bead-audit`'s existing rule: never write `applyable: false`; driver re-checks before every write |
| `br` JSON shape changes between versions | Medium | Low | All `br` invocations isolated in one section; fail loudly with raw output rather than parsing defensively |

## Dependencies

- `br` (beads_rust) on PATH. Required flags verified present: `br update --design`, `--notes`, `--acceptance-criteria`, `--description`; `br list --status`, `--limit`, `--json`; `br sync --flush-only`, `--import-only`.
- ADR 0001 (`docs/decisions/0001-native-tracker-fields-are-canonical.md`), which settles that native fields are canonical. Already accepted, and `plan-to-beads` already updated to comply.
- `bead-audit` must gain scoring (milestone 1) before the driver can target a band. Milestones 2-4 depend on 1.

## Testing Strategy

- **Fixtures:** the five bodies in `skills/bead-audit/references/fixtures/`, each with its expected score and band recorded inline. These are the rubric's regression suite and are authored in milestone 1.
- **Idempotency:** run the driver twice against a converged backlog; the second run must write nothing.
- **Stall convergence:** run repeatedly against a backlog containing one weak-but-complete bead; `REFINE: CONVERGED` must still fire (criterion 9).
- **Dry-run safety:** run with `--dry-run` against a dirty backlog and confirm the tracker is unchanged.
- **Live smoke test:** run against this repo's backlog, which holds one bead (`tadw-wdk`). It was migrated to native fields under ADR 0001, so its How is in `design`, its Done when in `notes`, and its Acceptance Criteria in `acceptance_criteria`. It is expected to audit PASS and score Excellent. If it does not, the discrepancy is a rubric defect, not a bead defect.
- No automated test harness exists for skills in this repo, so verification is by worked example against the fixtures, consistent with `hooks/test-hooks.js` being the only executable test present.

## Resolved Decisions

- **Native fields versus description body.** Settled by ADR 0001: native tracker fields are canonical. `plan-to-beads` now writes How to `--design`, Done when to `--notes`, and Acceptance Criteria to `--acceptance-criteria`, so newly generated beads are born canonical. This removes the conflict that would otherwise have made a default-target run rewrite every bead the repo's own generator produces.
- **Default target is Excellent, not Great.** The first draft proposed Great. Computing the bands disproved it: a bead missing its Acceptance Criteria entirely scores 78, which bands as Great, so a Great-targeted loop would skip the exact defect this feature exists to fix. Band caps resolve the contradiction, and with ADR 0001 in place the residual Great-to-Excellent distance is mechanical.
- **The driver does not claim beads.** Claiming sets status to `in_progress`, already out of scope, and would surface refinement as phantom work in `bv --robot-next`. The concurrency concern is handled for free, since `br list --status open` excludes `in_progress`.

## Open Questions

- None blocking milestone 1 (shipped).
- **Before milestone 2 (the driver):** the "Loop state and termination" section must be respecified as an explicit state machine before any code is written. Two independent reviews found the prose version non-exhaustive and self-contradictory: `stalled` and `regression` claim the same state with opposite outcomes (a write that leaves the score unchanged), and a bead whose score *decreases* between iterations reaches none of the three terminal categories. Redefine `regression` as a score that fell, evaluate `stalled` first, and prove exhaustiveness over {score-up, score-down, score-unchanged, not-applyable} with a transition table. Also fold in the round-2 factual fixes: rollback uses `br sync --rebuild` (not `--import-only`), drop `.claude-plugin/plugin.json` from registration scope (skills are auto-discovered), rewrite criterion 15 as `git diff --quiet .beads/issues.jsonl`, and define the content-preservation guard's diff over the union of all four native fields.
