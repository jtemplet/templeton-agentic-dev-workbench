---
name: triage-beads
description: "Rank the open beads in a bd (beads) tracker by ROI, value delivered per unit of effort, and answer one question: which single bead to pick up next. Use this whenever someone asks what to work on next, what to pick up, what has the highest ROI, what is on their plate, or wants the backlog prioritized, even if they do not say beads or triage by name. Reads the tracker through the bd and bv command-line tools only, never an MCP server. Takes readiness from bd ready and bd blocked, the measured graph facts (unblock counts, PageRank) from bv --robot-triage, then scores every candidate on an explicit value-over-effort rubric in which every point cites evidence from a stored field or the bead body. Output: one top pick with the scoring arithmetic shown and its claim command, a scored leaderboard so the ranking can be audited, and the blocked list. Deterministic: the same tracker state always yields the same pick. Report-only: it never claims, closes, or edits a bead."
---

# Triage Beads

Answer one question fast: *what is the single highest-ROI bead to pick up next?* ROI is value
delivered divided by effort spent. Every candidate gets a score from the rubric in Step 3, the top
score wins, and the readout prints the arithmetic, so the ranking is deterministic and auditable.

A single score can hide the choice being made, so the score never travels alone. Each pick carries
its component breakdown: priority, user impact, unblock leverage, momentum, and effort. The
leaderboard shows the nearest alternatives, with the component that separates them. A reader who
disagrees with a weight can see exactly which one to argue with.

## When to Use

- Someone asks what to work on next, what to pick up, or what has the best ROI
- At the start of a session, to choose the next bead before claiming it
- After closing a bead, to re-rank with the newly released work included
- When a backlog has grown past the point where `bd ready` output is scannable

## When NOT to Use

- To judge whether a bead is *well written* (use `bead-audit`)
- To decide whether finished work met its criteria (use `verify-acceptance`)
- To create or decompose beads (use `plan-to-beads`)
- When the user names a specific bead already; just `bd show <id> --json` and start

## Division of labor: bv scores the graph, this skill scores ROI

`bv` computes what can be measured: PageRank, betweenness, how many beads each one unblocks,
staleness, and a composite score. Those are numbers, not guesses, so never invent a substitute for
one. Readiness is the exception: `bd` owns it, and `bv` only reflects it, sometimes by a different
definition (see the `blocked_count` warning in Step 2).

`bv` does not read a bead body for effort, user-visible impact, or thread momentum, and its
composite score is opaque. This skill reads the bodies, prices each candidate on the explicit rubric
in Step 3, and shows the arithmetic. `bv`'s measured facts feed the rubric; they never replace it.

| Signal | Source | Kind |
|---|---|---|
| Ready or blocked | `bd ready`, `bd blocked` | Computed by `bd`; never re-derive it |
| Unblock count, graph importance | `bv --robot-triage` | Measured |
| Priority, type, labels, due date | `bd list --json` fields | Stored |
| Effort | `estimated_minutes` if set, else the body | Stored if present, else inferred |
| User impact | The body plus `dependents` | Inferred |
| Momentum | Dependency edges, labels, recent closes | Inferred |

## Inputs

All optional, from `$ARGUMENTS`:

- **free text**: a scope filter, matched case-insensitively against title, description, and labels.
- `--label <label>`: scope to one label's subgraph. This is the closest thing beads has to a Linear
  team or project. Repeatable in `bd`; `bv` takes one.
- `--repo <prefix>`: in a multi-repo workspace, scope to one repository's beads. `bv` takes `--repo`
  directly. `bd` has no such flag, so filter its output on the `source_repo` field in your own code.
  Otherwise the two halves of the readout will cover different sets.
- `--all`: include beads assigned to someone else. Default is unassigned plus your own.
- `--include-deferred`: include beads someone deliberately pushed out. Default excludes them.

## Step 0: Pre-flight

1. **`bd` must exist.** Run `bd list --limit 1`. If it fails, say
   `bd not found on PATH: install beads, or paste the beads you want triaged.` and stop.
2. **`bv` is optional.** Run `which bv`. If it is missing, run the whole triage from `bd` alone and
   say so in one line at the top of the readout. Do not silently drop the graph facts and present
   the result as if they were included. Substitute the unblock count with the number of
   `dependents[]` entries whose `dependency_type` is `blocks`, read from `bd show`. Do not use
   `dependent_count` from `bd list` for this: it sums every edge type (see the `dependency_type`
   warning in Step 2), and the `bd ready` row does not carry it at all.
3. **Never run bare `bv`.** It launches an interactive TUI and blocks the session. Every `bv` call
   here carries a `--robot-*` flag.
4. **A stale database gives a wrong readout.** If `bd` warns that the database is stale, run
   `bd import .beads/issues.jsonl` before fetching, then continue.
5. **Parse the arguments** listed above.

## Step 1: Fetch candidates

**Three traps, all of which silently shrink or pad the candidate set.**

1. **Every listing command has a default limit and truncates without complaining.** `bd list` and
   `bd blocked` default to 50, `bd ready` defaults to 20. Pass `--limit 0` for unlimited on every
   call that feeds a ranking or a count.
2. **"Open" and "ready" are different sets.** `bd list --status=open` includes beads that are
   blocked by an open dependency. `bd ready` is open, unblocked, and not deferred. The scored
   candidates come from `bd ready`; the tail and the blocked list need the open set too.
3. **`draft` is a status, not a label.** A draft bead is not pickup-ready. `bd ready` already
   excludes it, so do not add it back from the open set.

```bash
bd ready --json --limit 0                # actionable: open, unblocked, not deferred, not draft
bd blocked --json --limit 0              # blocked, each with blocked_by ids
bd list --status=open --limit 0 --json   # full open set, for the tail and the counts
```

Add `--include-deferred` to `bd ready` when the user passed that argument. Without the flag, a
deferred bead never appears, which is the default this skill wants.

Add `--label <label>` to any of the three to scope. `bd list` also has `--title-contains` and
`--desc-contains`. They are separate flags joined by AND. So a single free-text scope that should
match *either* is cleaner to apply in your own code, over the fetched JSON. For a wide or fuzzy
scope, use `bd search "<text>" --json` instead.

Note the shapes, which differ between commands:

- `bd list`, `bd ready`, and `bd blocked` all return a bare array of issues. There is no envelope
  and no `has_more` flag, so guard against truncation with `--limit 0` (unlimited) rather than by
  reading a field. `--limit` defaults to 50.
- `--status` takes a comma-separated list in one flag (`--status open,in_progress`). Repeating the
  flag silently keeps only the last value.
- Null fields are **omitted** from the JSON. A bead with no assignee has no `assignee` key, so test
  for absence, not for null.

Apply the scope filter, then drop anything claimed by someone else unless `--all` was passed. Drop
beads whose `issue_type` is `epic`: the work lives in the children, so an epic never wins the pick.
When a ready epic has no open children, flag it once as needing decomposition (`plan-to-beads`)
rather than scoring it.

If nothing survives, name the scope, so an empty result reads as "nothing matched *this filter*"
rather than "the backlog is empty":

```text
No ready beads matching "docs". Of 18 open beads, 12 are ready and none match that scope. 🎉
```

## Step 2: Gather graph and momentum signals

**One `bv` call carries every graph fact.**

```bash
bv --robot-triage
```

The fields live under a top-level `triage` key in `bv` v0.18: `.triage.quick_ref`,
`.triage.recommendations`, `.triage.quick_wins`, `.triage.blockers_to_clear`,
`.triage.project_health`, `.triage.commands`. Older output put them at the root, and
`docs/beads-workflow.md` still documents the flat shape. Read through `(.triage // .)` so both work.

What to take from it:

| Field | Use |
|---|---|
| `blockers_to_clear[]` | `unblocks_count` and `unblocks_ids` per bead, plus `actionable`; feeds the leverage score |
| `quick_ref.top_picks[]` | `bv`'s own top 3, with `score`, `reasons`, `unblocks`; a cross-check on this skill's ranking |
| `recommendations[].breakdown` | `pagerank_norm`, `betweenness_norm`, `time_to_impact_explanation` |
| `recommendations[].blocked_by` | Blocker ids, when the recommendation is not actionable |
| `quick_wins[]` | Low-complexity candidates, with a short `reason` such as `Low complexity`; feeds the effort tier |
| `status` | Which metrics were computed and which were skipped |

**`recommendations` is not a claimable list.** It includes graph-important work that is blocked or
already assigned. Only `quick_ref.top_picks` and beads present in `bd ready` are claimable.

**Check `status` before quoting a metric.** On a small graph `bv` skips Eigenvector, HITS, critical
path, cycles, and k-core, and marks betweenness `approximate`. A metric marked `skipped` is absent,
not zero.

**Do not take the blocked count from `quick_ref.blocked_count`.** It counts beads whose *status* is
`blocked`. Almost nothing sets that status, so the count reads `0` on a backlog with plenty of
dependency-blocked work. The count that matches reality is the length of `bd blocked`, and `bv`
reports the same number as `project_health.counts.dependency_blocked`. On this repository at the
time of writing: `blocked_count` 0, `dependency_blocked` 6, `bd blocked` 6 rows.

Three cheap `bd` reads complete the momentum picture:

```bash
bd list --status=in_progress --limit 0 --json                  # threads that are hot right now
bd list --status=closed -a --limit 50 --json --sort updated_at # most recent first; --reverse flips it
bd show <id> --json                                            # per-candidate edges, for the shortlist
```

Filter the closed list client-side to the last 14 days on `updated_at`. The cap of 50 is the one
place this skill does not pass `--limit 0`, because the closed list supplies momentum evidence
rather than a ranking or a count. It is only safe while the oldest row it returns is already older
than 14 days. When the 50th row is still inside the window, raise the limit and fetch again, or the
momentum score is reading a truncated history.

**`bd show` returns a one-element array.** Index `.[0]`. It is the only call that carries edge
*identity*: `dependencies[]` and `dependents[]`, each with the other bead's `id`, `title`, `status`,
`priority`, and `dependency_type`. `bd list` carries only `dependency_count` and `dependent_count`.
Score first, then `bd show` the top ~12 in parallel to verify the edges behind their scores.

**Only a `blocks` edge blocks or releases anything.** `dependency_type` is also `parent-child`,
meaning an epic and its members, or `related`. The two counts on `bd list` add up every type without
separating them. A bead whose single `dependencies[]` entry is its open parent epic is *ready*, and
a bead whose single `dependents[]` entry is a `related` bead releases *nothing* by closing. So
filter on `dependency_type == "blocks"` before you call an edge a blocker or count it as an unblock.
Verified: a child created with `bd create --parent <epic>` shows `dependency_count` 1 and appears in
`bd ready` at the same time.

Unlike a Linear fetch, `bd list --json` already carries the **full** `description`, `design`,
`acceptance_criteria`, and `notes`. There is no truncation to work around, so do not re-fetch a body
you already have.

## Step 3: Score ROI

**ROI = value ÷ effort.** Value is a point sum over four components plus a deadline bonus; effort is
a divisor from the size tier. The rubric's weights encode judgment, and they are fixed so the same
tracker state always produces the same ranking. Every point must cite evidence: a stored field, a
count, a bead id, or a phrase from the body. A point that cannot name its evidence is not awarded.

### Hard overrides, checked before any arithmetic

1. **Overdue `due_at` on a ready bead**: it is the pick, whatever its score. Lead with the date.
2. **A ready P0**: it outranks every non-P0, whatever the arithmetic. The rubric usually agrees; the
   override guards the edge where a large P0 would lose on division to a trivial P4.
3. **`defer_until` in the future**: deferred on purpose. Keep it out unless `--include-deferred`.

**Neither `due_at` nor `defer_until` is in the `bd ready` row.** Only `bd list` and `bd show` carry
them, so read them from the open set or from the shortlist fetch. Looking for `due_at` in `bd ready`
output finds nothing and proves nothing.

### Value: 0 to 23 points

| Component | Points | Evidence source |
|---|---|---|
| Priority | P0 8 · P1 5 · P2 3 · P3 1 · P4 0 | stored `priority` |
| User impact | High 4 · Med 2 · Low 0 | body plus type, rules below |
| Unblock leverage | 2 per bead released, cap 6 | `bv` `unblocks_count`, verified as `blocks` edges |
| Momentum | Hot 2 · Warm 1 · Cold 0 | signals below |
| Due within 7 days | +3 | `due_at` from the open set |

**User impact rules.**

- **High**: `issue_type` is `bug` on a path a user touches; or the bead fixes broken, stale, or
  wedged behavior. `chore` and `docs` skew Low; `feature` and `bug` skew High. The body overrides
  the type.
- **Low**: internal refactor, test determinism, tooling, or a schema tidy with no visible change.
- Unblock leverage is scored separately, so releasing other work earns leverage points, not impact
  points. Never count one fact twice.

**Momentum rules, strongest signal first.** Momentum prices the context already loaded: the next
link in an active thread costs less to start than a cold standalone.

1. **Hot: a dependency edge whose other end just moved.** A bead whose blocker closed in the last 14
   days, or whose `dependencies[]` contain something `in_progress`, is the next link.
2. **Warm: shared label with an `in_progress` or recently closed bead**, especially a feature label
   such as `qg-hardening`. The same epic counts too, and so does the same plan file. `plan-to-beads`
   writes `Plan: docs/plans/<name>.md (M4)` into the body, and the milestone marker orders the
   thread. Read epic membership from the child, not from the epic. Use the `dependencies[]` entry
   whose `dependency_type` is `parent-child`, or the id itself, since `bd create --parent <epic>`
   names children `<epic-id>.1`, `<epic-id>.2`, and so on. `bd epic status --json` reports only
   `total_children`, `closed_children`, and `eligible_for_close`; it lists no member ids.
3. **Cold**: standalone, no shared label, no recent activity on either end of an edge.

**PageRank is not a value component.** It measures position in the dependency graph. The leverage
points already price that position, through `unblocks_count`. A high-PageRank chore is also
important to the *plan* while invisible to a user. Quote PageRank as supporting evidence in the
"why" line; never add points for it.

### Effort: the divisor

S divides by 1, M by 1.5, L by 2.5.

**Why the divisor is compressed rather than proportional to time.** The minute bands below imply a
much wider spread, roughly 1 to 4 to 10. Dividing by those numbers would let the effort tier decide
every ranking on its own. Value spans about 3 to 8 points on a typical backlog, while a 1-to-10
divisor spans a factor of 10. Effort is also the least evidenced input here: it is stored on a
minority of beads and inferred on the rest. So the divisor is deliberately narrower than real time,
sized to swing the score about as much as the four value components combined and no more. The
consequence is intended: this ranks by value tilted toward the cheaper of two comparable beads, not
by value per hour.

Prefer stored evidence over a read of the prose, in this order:

1. `estimated_minutes`, when set: 30 or less is S, 31 to 120 is M, more is L.
2. An `## Estimated size` section, which `plan-to-beads` writes as
   `2 files, about 70 LOC, band: Target`. Map the band by its file and LOC counts: one or two files
   under ~100 LOC is S, a cross-surface or several-hundred-LOC band is L, the rest M.
3. Membership in `bv`'s `quick_wins`, whose `reason` is `Low complexity`: S. Its sibling
   `time_to_impact_explanation` looks like an estimate and usually is not: on this repository all
   ten recommendations carry the identical `Leaf node, median estimate 60m`. Compare it across
   candidates before quoting it, and when they all match, it separates nothing and is not evidence.
4. Failing all three, infer: **S** is one file or one concern, one to three acceptance criteria, no
   new interface. **L** is "Phase N", several deliverables, a new endpoint or migration, or a
   cross-surface change. **M** is the rest. It is also the default when the body is too thin to
   tell. Never award S, and its ROI boost, to a bead whose size is a guess.

Say which of the four you used. "estimated_minutes 45" and "no size signal, inferred from one
acceptance criterion" are different claims.

### Ranking and ties

Compute `ROI = value / effort` for every candidate that survives the overrides. **Round to one
decimal place** before comparing. Dividing by 1.5 and 2.5 produces repeating decimals, which would
otherwise separate two beads on a digit no reader can check. Break ties in the rounded score in this
order: lower priority number, more unblocks, smaller effort, older `created_at`. The order is fixed
so the pick is reproducible.

Worked example: a P1 bug (5) with High impact (4) that unblocks two beads (4) in a hot thread (2) is
value 15. At effort M it scores `15 ÷ 1.5 = 10.0`. It takes the pick from a P2 chore (3) that
unblocks three (6) at effort S, which scores `9 ÷ 1 = 9.0`. The chore is cheaper and has more
leverage; the bug wins on priority and user impact, and the compressed divisor is what lets those
two outweigh a one-tier size difference. The arithmetic goes in the readout precisely so this
comparison is visible and arguable.

**Cross-check against `bv`.** When this skill's top pick differs from `quick_ref.top_picks[0]`, say
so in one line. Name the component that moved it, usually user impact or effort. `bv` reads neither
of those. A silent disagreement with the measured tool looks like an error even when it is a
judgment.

### What stays out of the scored set

| Excluded | How to tell | Where it goes |
|---|---|---|
| Blocked | present in `bd blocked` | Blocked list, naming the blocker |
| Deferred | `status` is `deferred`, or `defer_until` is future | One count line |
| Draft | `status` is `draft` | One count line |
| Epic | `issue_type` is `epic` | Its children are scored instead; childless, flag for `plan-to-beads` |
| Claimed by someone else | `assignee` set and not you | Omit, unless `--all` |
| Marked not-ready by label | `BV_ROBOT_NOT_READY_LABELS`, or whatever label the repository uses to mark work not ready | Name it once, with the label |

## Step 4: Render

Terse and scannable: one pick, one leaderboard, one blocked list, one footer. Cap the leaderboard at
5 and the tail at 10.

Bead ids vary in length, from `tadw-op0` to `tadw-qg-prepush-verdict-gate-tug`, so do not expect a
`FAC-388`-sized column. Never abbreviate an id: it gets copied into a command. A long title may be
truncated to about 60 characters with a trailing ellipsis, but never reworded, because the user
searches on the words the tracker holds.

```text
🎯 Next highest ROI: tadw-qg-eval-fixture-harness-e4i
   Teach the eval harness to run in a fixture repository
   ROI 9.0 = value 9 (P2 3 + impact Low 0 + unblocks 2 ×2 + hot thread 2) ÷ effort S 1
   Evidence: unblocks tadw-qg-eval-finding-cases-29f and tadw-qg-eval-verdict-rules-xub (bv,
   verified blocks edges); bv quick-win "Low complexity" and 4 acceptance criteria (S);
   13 open qg-hardening beads name the same plan file (hot). Agrees with bv's top pick.
   claim: bd update tadw-qg-eval-fixture-harness-e4i --claim

Leaderboard (value ÷ effort = ROI)
  #2  tadw-self-report-sentence-length-zxu  8.0 = 8 (P2 3 + High 4 + warm 1) ÷ S 1
      type bug, every session's self-report hits it · loses on leverage: unblocks 0
  #3  tadw-qg-script-changed-set-jhb        7.3 = 11 (P2 3 + Low 0 + unblocks 3 ×2 + hot 2) ÷ M 1.5
      most leverage on the board · loses on effort: 2 scripts + a resolver, inferred M
  #4  tadw-em-dash-cleanup-mtl              4.0 = 4 (P2 3 + Low 0 + warm 1) ÷ S 1
      bv: low complexity · loses on impact and leverage

⛔ Blocked (6)
  tadw-qg-prepush-hook-suites-w8r   Add a pre-push hook that runs the repository's checks
                                    · blocked by 3, first is tadw-qg-script-changed-set-jhb

Rest of the ready backlog, ROI order (7 of 12 ready; the 6 blocked are above):
  3.0  tadw-qg-json-verdict-artifact-21l   Write the verdict as a JSON artifact
  3.0  tadw-qg-script-hygiene-count-rkd    Script the hygiene marker count
  … and 5 more

0 deferred, 0 draft, 0 in progress. Graph metrics: PageRank and betweenness computed
(betweenness approximate); eigenvector, HITS, critical path skipped on a 21-bead graph.
```

Rules for the readout:

- **The pick is one bead** with its full arithmetic and its evidence, three to five lines. Always
  print its claim command, which is `bd update <id> --claim` (atomic: assigns to you and sets
  `in_progress`). `bv` prints its own under `.triage.commands.claim_top`, in the longer
  `--status in_progress` form.
- **Every leaderboard row shows its arithmetic** and one clause naming the component that cost it
  the top spot. That clause is how the user audits the pick without recomputing it.
- **Numbers, not adjectives.** "unblocks 3", "4 acceptance criteria", "P1", "ROI 7.5".
- **Mark what is inferred.** A stored number and a read of the prose are different claims. When the
  pick's score rests on an inferred size or a thin body, say so on the evidence line and name the
  runner-up that wins if the inference is wrong.
- **One screen total.** Cap the tail at 10 and close it with `… and N more`. A full dump of the
  backlog is what `bd list` already prints, and it buries the recommendation this skill exists to
  make.

## Step 5: Handoff

Close with the next action and nothing more:

```text
Say the word and I'll claim tadw-qg-eval-fixture-harness-e4i and start.
```

Starting means `bd update <id> --claim`, reading the bead's `acceptance_criteria`, and implementing.
The handoff carries the **bead id** only; everything else is re-read from `bd`.

`--claim` refuses two cases with `VALIDATION_FAILED` and exit code 4: `cannot claim blocked issue`
and `already assigned to <name>`. Treat either as evidence that this readout was built on stale
data, re-fetch, and say so. It is also the reason blocked beads are never scored: the command this
skill prints would not work on them.

## Command reference

Every call this skill makes, and why.

| Call | Purpose |
|---|---|
| `bd ready --json --limit 0` | The scored candidate set |
| `bd blocked --json --limit 0` | The blocked list, with `blocked_by` ids |
| `bd list --status=open --limit 0 --json` | Open set for the tail, the counts, and `due_at` |
| `bd list --status=in_progress --limit 0 --json` | Hot threads |
| `bd list --status=closed -a --limit 50 --json --sort updated_at` | Recent closes, newest first |
| `bd show <id> --json` | Edge identity for the shortlist; returns a one-element array |
| `bd search "<text>" --json` | Wide or fuzzy scope filter |
| `bd epic status --json` | Epic progress only (`total_children`, `closed_children`); it carries no member ids |
| `bv --robot-triage` | All graph facts in one call |
| `bv --robot-triage --format toon` | Same, in fewer tokens, but only when the `tru` helper is on PATH. Without it `bv` prints `warning: tru not available; falling back to JSON` on **stderr** and emits ordinary JSON, so a piped call saves nothing and says so where you cannot see it |
| `bv --robot-next` | `bv`'s single top pick; a cross-check, not a substitute for the rubric |
| `bv --robot-triage --label <label>` | Graph facts scoped to one label's subgraph |

## Notes

- **Read-only.** This skill never claims, closes, defers, edits, or re-prioritizes a bead. Moving a
  bead to `in_progress` happens when the work actually starts, and it is the user's call.
- **Default scope is actionable, unassigned or yours.** That is the daily-driver case. `--all`
  widens to work others hold; a free-text argument or `--label` narrows to a thread.
- **Readiness belongs to `bd`.** It already walks the dependency graph and excludes deferred and
  draft beads. Recomputing it from raw JSONL invites a wrong answer, and a closed blocker is already
  gone from `bd ready`.
- **The rubric's weights are policy, not measurement.** They are fixed here so the pick is
  reproducible across sessions and arguable in one place. Tuning a weight is an edit to this file,
  never an in-session judgment call, or "deterministic" stops being true.
- **Edges beat labels for "same thread".** A label is a coarse grouping and most of one person's
  work carries the same one, so it rarely separates candidates. A dependency edge whose other end
  just closed is the actual next link. Weight edges first, labels second.
- **Thin body, thin claim.** When a bead has no `estimated_minutes`, no size band, and a two-line
  description, effort defaults to M and the "why" says the evidence is thin. That bead may belong in
  `bead-audit` before it belongs on the leaderboard.
- **Priority is inverted from what a reader expects.** `0` is the most urgent and `4` the least. So
  a lower number means more points. Never treat a higher number as more important.
