---
name: triage-beads
description: "Triage the open beads in a br (beads_rust) tracker into a concise \"what to work on next\" readout: one Start-here pick plus Quick wins / User impact / Keep momentum buckets, then a priority-ordered tail. Use this whenever someone asks what to work on next, what to pick up, what is on their plate, or wants the backlog prioritized, even if they do not say beads or triage by name. Reads the tracker through the br and bv command-line tools only, never an MCP server. Takes readiness from br ready and br blocked, the measured graph facts (PageRank, betweenness, unblock counts) from bv --robot-triage, and adds its own read of each bead body for effort, user impact, and momentum, which bv does not score. Report-only: it never claims, closes, or edits a bead."
---

# Triage Beads

Answer one question fast: *what should I pick up next?* "Best" is one of three moods: a fast win,
something that moves the needle for users, or the next link in a thread already being pulled. Those
moods genuinely compete, and which one wins depends on the day. So surface all three and recommend
one, rather than averaging them into a single score that hides the choice being made.

The output is a tight terminal readout: one **Start here** pick, then **Quick wins / User impact /
Keep momentum** buckets, then a priority-ordered tail.

## When to Use

- Someone asks what to work on next, what to pick up, or what is on their plate
- At the start of a session, to choose the next bead before claiming it
- After closing a bead, to find the next link in the same thread
- When a backlog has grown past the point where `br ready` output is scannable

## When NOT to Use

- To judge whether a bead is *well written* (use `bead-audit`)
- To decide whether finished work met its criteria (use `verify-acceptance`)
- To create or decompose beads (use `plan-to-beads`)
- When the user names a specific bead already; just `br show <id> --json` and start

## Division of labor: bv scores the graph, this skill reads the prose

`bv` computes what can be measured: PageRank, betweenness, how many beads each one unblocks,
staleness, and a composite score. Those are numbers, not guesses, so never invent a substitute for
one. Readiness is the exception: `br` owns it, and `bv` only reflects it, sometimes by a different
definition (see the `blocked_count` warning in Step 2).

`bv` does not read a bead body for effort, user-visible impact, or thread continuity. That is this
skill's job, and it is the part that produces the three buckets.

| Signal | Source | Kind |
|---|---|---|
| Ready or blocked | `br ready`, `br blocked` | Computed by `br`; never re-derive it |
| Graph importance, unblock count | `bv --robot-triage` | Measured |
| Priority, type, labels, due date | `br list --json` fields | Stored |
| Effort | `estimated_minutes` if set, else the body | Stored if present, else inferred |
| User impact | The body plus `dependents` | Inferred |
| Momentum | Dependency edges, labels, recent closes | Inferred |

## Inputs

All optional, from `$ARGUMENTS`:

- **free text**: a scope filter, matched case-insensitively against title, description, and labels.
- `--label <label>`: scope to one label's subgraph. This is the closest thing beads has to a
  Linear team or project. Repeatable in `br`; `bv` takes one.
- `--repo <prefix>`: in a multi-repo workspace, scope to one repository's beads. `bv` takes
  `--repo` directly; `br` has no such flag, so filter its output on the `source_repo` field
  client-side, or the two halves of the readout will cover different sets.
- `--all`: include beads assigned to someone else. Default is unassigned plus your own.
- `--include-deferred`: include beads someone deliberately pushed out. Default excludes them.

## Step 0: Pre-flight

1. **`br` must exist.** Run `which br`. If it is missing, say
   `br not found on PATH: install beads_rust, or paste the beads you want triaged.` and stop.
2. **`bv` is optional.** Run `which bv`. If it is missing, run the whole triage from `br` alone and
   say so in one line at the top of the readout. Do not silently drop the graph facts and present
   the result as if they were included. Substitute the unblock count with the number of
   `dependents[]` entries whose `dependency_type` is `blocks`, read from `br show`. Do not use
   `dependent_count` from `br list` for this: it sums every edge type (see the `dependency_type`
   warning in Step 2), and the `br ready` row does not carry it at all.
3. **Never run bare `bv`.** It launches an interactive TUI and blocks the session. Every `bv` call
   here carries a `--robot-*` flag.
4. **A stale database gives a wrong readout.** If `br` warns that the database is stale, run
   `br sync --import-only` before fetching, then continue.
5. **Parse the arguments** listed above.

## Step 1: Fetch candidates

**Three traps, all of which silently shrink or pad the candidate set.**

1. **Every listing command has a default limit and truncates without complaining.** `br list` and
   `br blocked` default to 50, `br ready` defaults to 20. Pass `--limit 0` for unlimited on every
   call that feeds a ranking or a count.
2. **"Open" and "ready" are different sets.** `br list --status=open` includes beads that are
   blocked by an open dependency. `br ready` is open, unblocked, and not deferred. The actionable
   buckets come from `br ready`; the tail and the blocked bucket need the open set too.
3. **`draft` is a status, not a label.** A draft bead is not pickup-ready. `br ready` already
   excludes it, so do not add it back from the open set.

```bash
br ready --json --limit 0                # actionable: open, unblocked, not deferred, not draft
br blocked --json --limit 0              # blocked, each with blocked_by ids
br list --status=open --limit 0 --json   # full open set, for the tail and the counts
```

Add `--include-deferred` to `br ready` when the user passed that argument. Without the flag, a
deferred bead never appears, which is the default this skill wants.

Add `--label <label>` to any of the three to scope. `br list` also has `--title-contains` and
`--desc-contains`, but they are separate AND-ed flags, so a single free-text scope that should match
*either* is cleaner client-side over the fetched JSON. For a wide or fuzzy scope, use
`br search "<text>" --json` instead.

Note the shapes, which differ between commands:

- `br list` returns an envelope: `{"issues": [...], "total": N, "has_more": bool}`. Check
  `has_more`; if it is true you truncated.
- `br ready` and `br blocked` return a bare array.
- Null fields are **omitted** from the JSON. A bead with no assignee has no `assignee` key, so
  test for absence, not for null.

Apply the scope filter, then drop anything claimed by someone else unless `--all` was passed.

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
`docs/beads-workflow.md` still documents the flat shape. Read through `(.triage // .)` so both
work.

What to take from it:

| Field | Use |
|---|---|
| `quick_ref.top_picks[]` | `bv`'s own top 3, with `score`, `reasons`, `unblocks` |
| `recommendations[].breakdown` | `pagerank_norm`, `betweenness_norm`, `time_to_impact_explanation` |
| `recommendations[].blocked_by` | Blocker ids, when the recommendation is not actionable |
| `quick_wins[]` | Low-complexity candidates, with a short `reason` such as `Low complexity` |
| `blockers_to_clear[]` | `unblocks_count` and `unblocks_ids` per bead, plus `actionable` |
| `status` | Which metrics were computed and which were skipped |

**`recommendations` is not a claimable list.** It includes graph-important work that is blocked or
already assigned. Only `quick_ref.top_picks` and beads present in `br ready` are claimable.

**Check `status` before quoting a metric.** On a small graph `bv` skips Eigenvector, HITS, critical
path, cycles, and k-core, and marks betweenness `approximate`. A metric marked `skipped` is absent,
not zero.

**Do not take the blocked count from `quick_ref.blocked_count`.** It counts beads whose *status* is
`blocked`, which almost nothing sets, so it reads `0` on a backlog with plenty of dependency-blocked
work. The count that matches reality is the length of `br blocked`, and `bv` reports the same number
as `project_health.counts.dependency_blocked`. On this repository at the time of writing:
`blocked_count` 0, `dependency_blocked` 6, `br blocked` 6 rows.

Three cheap `br` reads complete the momentum picture:

```bash
br list --status=in_progress --limit 0 --json                  # threads that are hot right now
br list --status=closed -a --limit 50 --json --sort updated_at # most recent first; --reverse flips it
br show <id> --json                                            # per-candidate edges, for the shortlist
```

Filter the closed list client-side to the last 14 days on `updated_at`. The cap of 50 is the one
place this skill does not pass `--limit 0`, because the closed list supplies momentum evidence
rather than a ranking or a count. It is only safe while the oldest row it returns is already older
than 14 days. When the 50th row is still inside the window, raise the limit and fetch again, or the
momentum axis is reading a truncated history.

**`br show` returns a one-element array.** Index `.[0]`. It is the only call that carries edge
*identity*: `dependencies[]` and `dependents[]`, each with the other bead's `id`, `title`,
`status`, `priority`, and `dependency_type`. `br list` carries only `dependency_count` and
`dependent_count`. Rank first, then `br show` the top ~12 in parallel.

**Only a `blocks` edge blocks or releases anything.** `dependency_type` is also `parent-child` (an
epic and its members) or `related`, and the two counts on `br list` add up every type without
distinguishing them. A bead whose single `dependencies[]` entry is its open parent epic is *ready*,
and a bead whose single `dependents[]` entry is a `related` bead releases *nothing* by closing. So
filter on `dependency_type == "blocks"` before you call an edge a blocker or count it as an unblock.
Verified: a child created with `br create --parent <epic>` shows `dependency_count` 1 and appears in
`br ready` at the same time.

Unlike a Linear fetch, `br list --json` already carries the **full** `description`, `design`,
`acceptance_criteria`, and `notes`. There is no truncation to work around, so do not re-fetch a
body you already have.

## Step 3: Score on three axes, and do not average them

Judge each candidate from its body, its fields, and its edges. Quote the evidence in the "why"
line: a phrase from the body, a count, or a bead id.

### Effort: S / M / L

Prefer stored evidence over a read of the prose.

1. `estimated_minutes`, when set, decides it outright.
2. An `## Estimated size` section, which `plan-to-beads` writes as
   `2 files, about 70 LOC, band: Target`. Trust the band.
3. Membership in `bv`'s `quick_wins`, whose `reason` is `Low complexity`. Its sibling
   `time_to_impact_explanation` looks like an estimate and usually is not: on this repository all
   ten recommendations carry the identical `Leaf node, median estimate 60m`. Compare it across
   candidates before quoting it, and when they all match, it separates nothing and is not evidence.
4. Failing all three, infer: **S** is one file or one concern, one to three acceptance criteria, no
   new interface. **L** is `epic`, "Phase N", several deliverables, a new endpoint or migration, or
   a cross-surface change. **M** is the rest.

Say which of the four you used. "estimated_minutes 45" and "no size signal, inferred from one
acceptance criterion" are different claims.

### User impact: High / Med / Low

- **High**: `issue_type` is `bug` on a path a user touches; or the bead fixes broken, stale, or
  wedged behavior; or it has a `blocks` dependent, so finishing it releases other work. A
  `parent-child` or `related` dependent releases nothing and earns no credit here.
- **Low**: internal refactor, test determinism, tooling, or a schema tidy with no visible change.
- `chore` and `docs` skew Low; `feature` and `bug` skew High. The body overrides the type.

**PageRank is not user impact.** It measures position in the dependency graph. A high-PageRank
chore is important to the *plan*, and invisible to a user. Report them as separate reasons and never
let one stand in for the other.

### Momentum: Hot / Warm / Cold

Strongest signal first:

1. **A dependency edge whose other end just moved.** A bead whose blocker closed in the last 14
   days, or whose `dependencies[]` contain something `in_progress`, is the next link. This is the
   beads equivalent of "Phase 1 shipped yesterday".
2. **Shared label with an `in_progress` or recently closed bead**, especially a feature label such
   as `qg-hardening`.
3. **Same epic.** Read membership from the child, not from the epic: the `dependencies[]` entry
   whose `dependency_type` is `parent-child`, or the id itself, since `br create --parent <epic>`
   names the child `<epic-id>.1`, `<epic-id>.2`, and so on. `br epic status --json` reports only
   `total_children`, `closed_children`, and `eligible_for_close`; it lists no member ids, and
   `br dep tree <epic>` returned the epic alone. Use it for epic progress, not for membership.
4. **The same plan.** `plan-to-beads` writes `Plan: docs/plans/<name>.md (M4)` into the body. Two
   beads naming one plan file are one thread, and the milestone marker orders them.
5. **Cold**: standalone, no shared label, no recent activity on either end of an edge.

### Priority and the two override fields

`priority` is `0` critical through `4` backlog. Render it `P0` to `P4`. Use it as the tiebreaker,
and let it override the axes: a P0 bug beats a cold refactor whatever the buckets say.

Two stored fields outrank the moods when they are set:

- `due_at` in the past or within days: lead with it, whatever bucket it lands in.
- `defer_until` in the future: it is deferred on purpose. Keep it out unless `--include-deferred`.

**Neither field is in the `br ready` row.** Only `br list` and `br show` carry them, so read them
from the open set or from the shortlist fetch. Looking for `due_at` in `br ready` output finds
nothing and proves nothing.

### What stays out of the actionable buckets

| Excluded | How to tell | Where it goes |
|---|---|---|
| Blocked | present in `br blocked` | Blocked bucket, naming the blocker |
| Deferred | `status` is `deferred`, or `defer_until` is future | One count line |
| Draft | `status` is `draft` | One count line |
| Claimed by someone else | `assignee` set and not you | Omit, unless `--all` |
| Marked not-ready by label | `BV_ROBOT_NOT_READY_LABELS`, or a repo convention such as a bead lacking `auto-ok` | Name it once, with the label |

## Step 4: Render

Terse and scannable. One entry per bead, in the order `id  title  Pn - why`, wrapping onto an
indented continuation line when a long id and title leave no room for the why. Cap each bucket at
three. A bead may appear in two buckets when it genuinely qualifies. Omit an empty bucket entirely.

Bead ids vary in length, from `tadw-op0` to `tadw-qg-prepush-verdict-gate-tug`, so do not expect a
`FAC-388`-sized column. Never abbreviate an id: it gets copied into a command. A long title may be
truncated to about 60 characters with a trailing ellipsis, but never reworded, because the user
searches on the words the tracker holds.

```text
🎯 Start here: tadw-qg-eval-fixture-harness-e4i
   Teach the eval harness to run in a fixture repository
   P2 · unblocks tadw-qg-eval-verdict-rules-xub; PageRank 91%, top of bv's picks; bv calls it low
   effort and the bead lists 4 acceptance criteria. Quick win + hot thread (all 13 open
   qg-hardening beads name the same plan file).
   claim: br update tadw-qg-eval-fixture-harness-e4i --claim

⚡ Quick wins (ship today)
  tadw-qg-script-secrets-gate-jbg   Script the secrets gate           P2 · one script, 5 criteria
  tadw-em-dash-cleanup-mtl          Remove the 104 remaining em-…     P2 · bv: low complexity

👥 User impact (moves the needle)
  tadw-self-report-sentence-length-zxu  Diagnose why the sentence limit fails in self-reports
                                        P2 · type bug, every session's self-report hits it

🔗 Keep momentum (next in an active thread)
  tadw-qg-script-changed-set-jhb    Script the changed-set resolution  P2 · unblocks 2 in
                                                                            qg-hardening

⛔ Blocked (6)
  tadw-qg-prepush-hook-suites-w8r   Add a pre-push hook that runs the repository's checks
                                    · blocked by 3, first is tadw-qg-script-changed-set-jhb

Rest of the ready backlog, priority order (7 of 12 ready; the 6 blocked are above):
  P2  tadw-qg-json-verdict-artifact-21l   Write the verdict as a JSON artifact
  P2  tadw-qg-script-hygiene-count-rkd    Script the hygiene marker count
  … and 5 more

0 deferred, 0 draft, 0 in progress. Graph metrics: PageRank and betweenness computed
(betweenness approximate); eigenvector, HITS, critical path skipped on a 21-bead graph.
```

Rules for the readout:

- **Start here is one bead**, the one that best combines the three axes weighted by priority and by
  how much energy the moment calls for. Two sentences at most, naming which axes it wins. Always
  print its claim command, which is `br update <id> --claim` (atomic: assigns to you and sets
  `in_progress`). `bv` prints its own under `.triage.commands.claim_top`, in the longer
  `--status in_progress` form.
- **"Why" is one clause of evidence**, never a restatement of the title.
- **Numbers, not adjectives.** "unblocks 3", "PageRank 91%", "4 acceptance criteria", "P1".
- **Mark what is inferred.** A stored number and a read of the prose are different claims.
- **One screen total.** Cap the tail at 10 and close it with `… and N more`. A full dump of the
  backlog is what `br list` already prints, and it buries the recommendation this skill exists to
  make.

## Step 5: Handoff

Close with the next action and nothing more:

```text
Pick one and tell me which, and I'll claim it and start.
```

Starting means `br update <id> --claim`, reading the bead's `acceptance_criteria`, and
implementing. The handoff carries the **bead id** only; everything else is re-read from `br`.

`--claim` refuses two cases with `VALIDATION_FAILED` and exit code 4: `cannot claim blocked issue`
and `already assigned to <name>`. Treat either as evidence that this readout was built on stale
data, re-fetch, and say so. It is also the reason blocked beads stay out of the actionable buckets:
the command this skill prints would not work on them.

## Command reference

Every call this skill makes, and why.

| Call | Purpose |
|---|---|
| `br ready --json --limit 0` | The actionable candidate set |
| `br blocked --json --limit 0` | The blocked bucket, with `blocked_by` ids |
| `br list --status=open --limit 0 --json` | Open set for the tail and the counts |
| `br list --status=in_progress --limit 0 --json` | Hot threads |
| `br list --status=closed -a --limit 10 --json --sort updated_at` | Recent closes, newest first |
| `br show <id> --json` | Edge identity for the shortlist; returns a one-element array |
| `br search "<text>" --json` | Wide or fuzzy scope filter |
| `br epic status --json` | Epic progress only (`total_children`, `closed_children`); it carries no member ids |
| `bv --robot-triage` | All graph facts in one call |
| `bv --robot-triage --format toon` | Same, in fewer tokens, but only when the `tru` helper is on PATH. Without it `bv` prints `warning: tru not available; falling back to JSON` on **stderr** and emits ordinary JSON, so a piped call saves nothing and says so where you cannot see it |
| `bv --robot-next` | The single top pick, when the user wants only that |
| `bv --robot-triage --label <label>` | Graph facts scoped to one label's subgraph |

## Notes

- **Read-only.** This skill never claims, closes, defers, edits, or re-prioritizes a bead. Moving a
  bead to `in_progress` happens when the work actually starts, and it is the user's call.
- **Default scope is actionable, unassigned or yours.** That is the daily-driver case. `--all`
  widens to work others hold; a free-text argument or `--label` narrows to a thread.
- **Readiness belongs to `br`.** It already walks the dependency graph and excludes deferred and
  draft beads. Recomputing it from raw JSONL invites a wrong answer, and a closed blocker is
  already gone from `br ready`.
- **Edges beat labels for "same thread".** A label is a coarse grouping and most of one person's
  work carries the same one, so it rarely separates candidates. A dependency edge whose other end
  just closed is the actual next link. Weight edges first, labels second.
- **Thin body, thin claim.** When a bead has no `estimated_minutes`, no size band, and a two-line
  description, say the evidence is thin in the "why" rather than inventing a size. That bead may
  belong in `bead-audit` before it belongs in a bucket.
- **Priority is inverted from what a reader expects.** `0` is the most urgent and `4` the least, so
  sort ascending and never treat a higher number as more important.
