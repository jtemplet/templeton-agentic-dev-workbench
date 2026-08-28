# Feature Plan: Run the quality gates from an agent that fans out to four subagents

**Date:** 2026-08-21
**Status:** Draft, not started. Grounded against `origin/main` @ `8a94e69`. Milestone 1 can start;
milestones 2 through 4 are blocked on the Open Question 0 spike.

**Revision history.**

- **2026-08-21, from a `/plan-review` pass (verdict: Major Rework).** Ten changes. The `frontend`
  lane rested on a misreading of `route_qa.py:85`, which routes `browser-ui` to a handoff, so the
  browser-ui HANDOFF is now the third coupling and the lane's duty is restated. Gate 2 for
  `http-api` had been assigned to two lanes in two sections; the lane table is rewritten as the
  single rule, with a worst-of reduction for files that classify into two surfaces. The Task or
  Agent tool dependency became Open Question 0 with a spike and a written fallback, because no
  agent carries that tool today. The lane contract widened so it can populate the JSON artifact,
  and Step 5 attribution moved to the lane that produced the failure. Added a step-ownership table
  covering all six of the skill's steps. Added acceptance criteria 9, 10, and 11, and gave criteria
  2 and 4 a verification method. Added a rollback line. Corrected four citation defects.
- **2026-08-21, from a second `/plan-review` pass (verdict: Major Rework).** Eight changes. The
  rewritten lane table had partitioned six of the nine surfaces `route_qa.py:83-93` defines, leaving
  Gate 2 unowned for `mobile-ui` and `docs`, so a SwiftUI change would have reported PASS where
  Verdict Rule 2 requires INCOMPLETE and a docs-only diff would have dropped a required row. All
  nine surfaces now have an owner, and the orchestrator emits the SKIP rows for lanes it did not
  dispatch. The worse-of reduction had no stated ordering and would have folded a handoff into a
  graded status, which `SKILL.md:711` forbids; the order is now written down and handoff rows are
  exempt. The handoff is its own row (`Handoff: <surface>`), not a status on Gate 2, so the lane
  table, the third coupling, and criteria 1 and 11 are reworded. The lane contract gained
  `evidence_block` for Gate 2's case table and Gate 8's probe table, a nullable `command`, and a
  stated counts-to-detail mapping. Criterion 10 had contradicted the contract's own
  `raw_output_on_fail` field and is redrafted; criterion 2 had named the wrong report line; criterion
  9 gained a tolerance and a run count so the fallback path can meet it. Gate 1 is qualified per
  suite, and two Gate 1 rows stay two rows.
- **2026-08-21, from a third `/plan-review` pass (verdict: Major Rework).** Six changes. The
  partition was complete over surfaces but not over rows. Two rows had no owner: Gate 2's own
  HANDOFF status when every routed surface is a handoff (`SKILL.md:180-181`), which the previous
  draft would have emitted as SKIP in exactly criterion 11's fixture, and the **Project checks** row
  (`SKILL.md:90`), which this repository produces on every run. The orchestrator owns both. The lane
  contract's `raw_output_on_fail` could not carry a BLOCKED gate's output, which the report template
  shows at `SKILL.md:634-637`; it is now `raw_output`, non-null on FAIL or BLOCKED, and a new
  `attribution` field carries the Step 5 sentence. The orchestrator is named as the renderer of
  `### Failures`, `### Action Items`, and each `evidence_block`'s named section. Gate 1's suite split
  is defined in terms of what Step 1 actually discovers rather than assuming a repository has exactly
  one backend and one frontend suite. Criteria 1, 10, and 11 updated to match. Corrected five
  citations: `:562` to `:563`, `:528` and `:566` to `:533` and `:571`, `:684` to `:685`, `:688` to
  `:689`, and widened `:588-592` to `:588-594`.
- **2026-08-21, from a fourth `/plan-review` pass (verdict: Needs Revision).** The partition over
  rows, sections, and artifact fields verified complete, with no unowned row found. Six changes, all
  narrower than the previous rounds. The duplicate-row reduction had been defined on `status` alone,
  so on the most common diff shape here (one `http-api` file and one `library` file) the losing
  lane's `evidence_block` was discarded and its cases silently ungraded; the reduction is now defined
  per field and criterion 12 pins it. "Handoff row" had acquired two meanings once Gate 2 could
  itself be HANDOFF, and the never-merge rule fit only one of them; it now means a
  `Handoff: <surface>` row and nothing else. `raw_output` had no case for a gate that ran no command,
  which the template shows twice, so it would have forced a lane to invent output; it is now
  conditioned on a non-null `command`. Gate 8's `evidence_block` gained the failing probe's `curl`
  and its explanation (`SKILL.md:596-606`). The `docs` lane is measured against the orchestrator's
  own single-scripted-command test, which it currently fails, with the consequence written down:
  if Open Question 3 resolves to report-only, Gate 5 folds into the orchestrator and this becomes a
  three-lane fan-out. The Project checks citation moved from `AGENTS.md:22-29`, two lines of which
  are gate commands rather than project checks, to `:18` and `:32-33`.
- **2026-08-21, from a fifth `/plan-review` pass (verdict: Needs Revision, MECE now GREEN).** Three
  changes, and the partition was re-verified complete against three diff shapes. The plan had cited
  the wrong copy of the bead-labeling hook: two tracked copies exist and they have diverged.
  `.claude/scripts/label_bead_on_skill_invocation.sh` is the one `.claude/settings.json:29` wires
  here, it handles `PreToolUse` and `Stop` only, and it maps `quality-gates` to **inject** mode gated
  on a PASS verdict (`:202-204`), while the distribution copy at `scripts/...:190` uses gate mode and
  carries a canonical-name function the live copy does not have. Criterion 7, the risk row, Open
  Question 2, and milestone 4's file list now name the live copy and describe inject mode. Milestone
  2's Done-when said "the six fields of the lane contract" when the contract defines eight; it now
  says every field, so it cannot go stale again. The `SKILL.md:548` citation supported an adjacent
  claim about invented commands rather than invented output, and is restated as such.

## Summary

`/quality-gates` today is one skill that a single session executes end to end. This plan adds
`agents/quality-gates.md`, an orchestrator that resolves the scope once and then dispatches four
subagents that work concurrently: documentation, backend unit tests, frontend tests (only when a
frontend exists), and integration tests. The orchestrator aggregates their returns into the single
report the skill already specifies, with the same six statuses and the same verdict rules.

The skill stays where it is. It keeps the gate definitions, the status model, and the report format,
and it becomes the technique the agent and every lane read. Nothing under
`skills/quality-gates/scripts/` moves.

## Motivation

`/quality-gates` runs at every session close (`AGENTS.md:314`) and is a stated precondition for
running `/tadw:ship` (`skills/ship/SKILL.md:20`), so it is the most frequently executed component in
this repository. Three properties of the current shape cost something on every run.

**The independent work is serialized.** `skills/quality-gates/SKILL.md` is 741 lines and defines
eight gates, all inside Step 4 (`:196-467`). Documentation freshness (Gate 5), the test run (Gate 1),
and the coverage review (Gate 2) share no state beyond the scope SHA, yet they run one after another
in one session.

**Everything lands in one context.** The 741-line technique, every gate's raw output, and the diff
being graded all occupy the same context window as the change under review. A large diff and a
verbose test runner compete with the reasoning that grades them.

**The report is assembled by the same session that produced every input.** A lane that returns a
structured verdict is easier to hold to a contract than a lane that is simply the next paragraph of
one long transcript.

The stakeholder is the repository author, who runs this at every session close and before every
ship, and any agent following "Landing the Plane" in `AGENTS.md`.

## Scope

### In scope

- A new `agents/quality-gates.md` orchestrator with four lane contracts and an aggregation rule.
- Restructuring `skills/quality-gates/SKILL.md` Step 4 so each lane owns a contiguous, well-defined
  set of gates, preserving the three cross-gate couplings named under Technical Approach.
- Updating the referrers that must change for the new entry point to work: `commands/quality-gates.md`,
  `skills/verify-acceptance/SKILL.md`, the bead-labeling hook matcher, and registration in
  `AGENTS.md` and `README.md`.
- One ADR recording the decisions under Open Questions, including the Open Question 0 spike result.

### Out of scope

- Moving, renaming, or deleting anything under `skills/quality-gates/scripts/`. Four executable
  callers hardwire those paths: `.githooks/pre-push:129-136`, `AGENTS.md:22-29`,
  `.githooks/test_prepush.py:96-103`, and `evals/test_run.py:265`.
- Changing what any individual gate checks. Gate semantics are unchanged; only who runs them and in
  what order changes.
- Changing the JSON artifact's schema or location. `tadw-6qd` owns scripting that write, and this
  plan neither blocks nor depends on it.
- Adding an eval case for `quality-gates`. None exists today (`evals/cases/` holds six unrelated
  cases) and adding one is separate work.
- Making the gates fix anything. See Open Question 3; the default this plan implements is
  report-only, unchanged.

**Rollback.** Milestone 3 restructures the skill in place, so the restructured skill must remain a
valid standalone document that `skills/verify-acceptance/SKILL.md:89` can still read and run without
the agent. Reverting this feature is therefore deleting `agents/quality-gates.md` and restoring one
line of `commands/quality-gates.md`, with no change to the skill required.

## Technical Approach

### Why the skill stays

Two constraints force the agent-orchestrates, skill-holds-the-technique split rather than a move.

`AGENTS.md:79-91` states the architecture: "A command is a shortcut that loads an agent or a skill.
An agent is a workflow definition that references skills. A skill holds the technique itself."
Relocating 741 lines of gate definitions into `agents/` inverts that.

The four callers listed under Out of scope run `skills/quality-gates/scripts/*.py` by path. A
directory move breaks the repository's own pre-push gate, which is the highest-consequence failure
available here.

### Who owns each of the skill's six steps

The skill defines six steps and this plan partitions only Step 4, so the other five need a stated
owner or every lane re-derives them.

| Step | Owner | Note |
|---|---|---|
| Step 1, discover the gate set (`SKILL.md:79`) | Orchestrator | The discovered gate set is passed into every lane; a lane never re-discovers it |
| Step 2, set the scope (`SKILL.md:92`) | Orchestrator | Runs `changed_set.py` once; see the scope-SHA coupling |
| Step 3, route the QA method (`SKILL.md:141`) | Orchestrator | Its surface classification is what decides which lanes run at all |
| Step 4, run each gate (`SKILL.md:196`) | Lanes and orchestrator | Partitioned by the lane table below |
| Step 5, attribute every failure (`SKILL.md:468`) | The lane that produced the failure | Attribution needs the raw output, which only the lane holds |
| Step 6, report (`SKILL.md:476`) | Orchestrator | Aggregates rows, applies the Verdict Rules, writes the artifact |

### The four lanes

`route_qa.py:83-93` defines nine surfaces, and every one of them needs an owner. A partition that
covers only the surfaces this repository happens to produce drops a required row on the first diff
that produces another.

| Lane | Gates it owns | Runs when |
|---|---|---|
| `docs` | Gate 5 (documentation freshness), and Gate 2 for the `docs` surface, which is a SKIP carrying its reason (`route_qa.py:91`) | Always |
| `backend-unit` | Gate 1 for the backend suite, and Gate 2 for the `cli`, `library`, `prompt-assets`, `infra`, and `unknown` surfaces | Always |
| `frontend` | Gate 1 for the frontend suite, and the `Handoff: browser-ui` row naming `/qa` (`route_qa.py:85`) | Only when the router reports a `browser-ui` surface |
| `integration` | Gate 8 (live API probe), and Gate 2 for the `http-api` surface, both unit and end to end | Only when the router reports an `http-api` surface |

The orchestrator owns Gates 3, 4, 6, and 7 (lint, type check, secrets, hygiene), because each is a
single scripted command and dispatching a subagent to run one `python3` call costs more than it
saves. That test applies to the `docs` lane too, and today it fails: Gate 5 is one scripted command
that forbids prose judgment (`SKILL.md:295-300`, "Run the bundled script. Do not hand-roll this
check"), so the lane runs one script and one SKIP row. The lane is kept anyway because Open Question
3 decides whether it becomes a writer: a lane that reads the drift and drafts the fix is real work
that earns its own context, and a lane that only reports drift is not. **If Open Question 3 resolves
to report-only, fold Gate 5 into the orchestrator and restate this as a three-lane fan-out**,
adjusting the Summary. The ADR records that consequence alongside the decision.

The orchestrator also owns the `Handoff: mobile-ui` row naming `/ios-qa` (`route_qa.py:86`), since no
lane in this design runs iOS checks, and the **Project checks** row (`SKILL.md:90`), which carries every
command Step 1 discovered that maps to no gate, with its exact command and real counts. This
repository produces that row on every run: `AGENTS.md:18` is `node hooks/test-hooks.js`, which is the
command the skill's own example puts under Project checks (`SKILL.md:539`), and `AGENTS.md:32-33`
adds `claude plugin validate .` and `python3 evals/run.py`, neither of which maps to a gate.

**When every surface the router reported routes to a handoff, Gate 2 is itself HANDOFF, not SKIP.**
`SKILL.md:180-181` states the rule: Gate 2 grades the `curl` and `coverage` surfaces, and it is
HANDOFF only when every surface routed to a handoff, leaving it nothing to grade. The orchestrator
emits that row, because no single lane can see the union of surfaces, and `SKILL.md:709` forbids
recording it as SKIP.

Gate 1 splits per suite, not per lane: Step 1 discovers a list of commands (`SKILL.md:79-90`), and
each test suite among them gets its own row. A suite goes to `frontend` when the router reported a
`browser-ui` surface and the suite is that surface's, and to `backend-unit` otherwise. Two rows stay
two rows, because `SKILL.md:678-679` requires the exact command and real counts per row, so merging
them would discard one of each. A repository with one suite gets one row.

For every lane it did not dispatch, the orchestrator emits that lane's rows as SKIP carrying the
router's reason, so no row is ever absent (criterion 3, and `SKILL.md:685`).

When one file classifies into two surfaces, `route_qa.py:33` reports the ambiguity rather than
resolving it, and `SKILL.md:225` says "A change can touch two surfaces. Grade each, and take the
worst result". Applied across lanes, worse is ordered BLOCKED, FAIL, HANDOFF, WARN, PASS, SKIP, from
worst to best. Two **graded** rows for the same gate reduce to one row, and the reduction is defined
per field, not just on the status:

- `status` takes the worse of the two by that order. A gate whose own status is HANDOFF is a graded
  row and reduces at the HANDOFF position like any other.
- `counts` are the orchestrator's sum over the union of the numbered case list, not the surviving
  row's counts alone.
- Every `evidence_block` for the gate is spliced into that gate's section in case-number order,
  regardless of which row's status survived. Dropping the losing lane's block would silently ungrade
  the cases it covered, which is the failure the single numbered case list exists to prevent.
- `raw_output` and `attribution` come from every row that carries them, not only the survivor.

**"Handoff row" means a `Handoff: <surface>` row, and only that.** Such a row never merges with a
graded row: `SKILL.md:711` forbids folding a handoff surface and a graded surface into one status,
so it stays its own row and Verdict Rule 2 still sees it.

### The three couplings that must survive

These are the reason a naive fan-out breaks the gates rather than parallelizing them.

**The scope SHA.** `SKILL.md:102` says the base SHA from Step 2 is what Gate 7 takes as its `--base`,
and that re-deriving it is the hand-rolling the script exists to replace. The orchestrator therefore
runs `changed_set.py` exactly once, before any dispatch, and passes both the base SHA and the changed
path list into every lane. No lane resolves its own scope.

**Gate 2 cites Gate 8.** `SKILL.md:217` has Gate 2 cite Gate 8's result for `http-api` surfaces
rather than repeating it, and `SKILL.md:243` states that a green Gate 8 does not satisfy Gate 2's
end-to-end rule. Splitting those across two lanes that cannot see each other would either duplicate
the probe or lose the distinction. Both live in the `integration` lane, so the citation stays inside
one context.

**A browser-ui surface is a HANDOFF, not a gate this skill can run.**
`skills/quality-gates/scripts/route_qa.py:85` maps `browser-ui` to `("handoff", "/qa")`, and
`SKILL.md:220` says of `browser-ui` and `mobile-ui`: "This skill cannot settle it. HANDOFF". A
HANDOFF row drives the whole run to INCOMPLETE by Verdict Rule 2 (`SKILL.md:661`). It is its own
row, named `Handoff: browser-ui` with a null command (`SKILL.md:533` in the artifact, `:571` in the
report table), not a status on Gate 2; `SKILL.md:710` says to hand it to `/qa` "on its own row". The `frontend` lane therefore runs the
frontend unit suite for Gate 1 and emits that row; it never attempts to settle browser UI itself,
and the orchestrator must not reduce the row to a SKIP, per `SKILL.md:75`.

### The lane contract

Every lane receives, from the orchestrator: the base SHA, its slice of the changed paths, the
discovered gate set from Step 1, the numbered case list Gate 2 requires (`SKILL.md:229-233`), and the
path to `skills/quality-gates/SKILL.md`.

The numbered case list is enumerated once, by the orchestrator. Three lanes enumerating
independently would produce three unrelated numbered lists, and `SKILL.md:229-233` requires the cases
be numbered before any is graded precisely so a case nobody listed cannot be silently ungraded.

Every lane returns one row per gate it owns:

```json
{"gate": "Tests", "status": "PASS", "command": "pytest -q", "counts": "14 passed, 0 failed",
 "detail": "selected, not the full suite", "raw_output": null, "attribution": null,
 "evidence_block": null}
```

`raw_output` is non-null when the status is FAIL or BLOCKED **and the gate ran a command**, carrying
that command's real output. `SKILL.md:686` requires it for a FAIL, and the report template carries it
for a BLOCKED gate too: `SKILL.md:634-637` shows type checking BLOCKED with `mypy: command not found`
as its evidence. A gate whose `command` is null carries its failure evidence in `evidence_block`
instead and does not appear in `### Failures`; that is how the template treats the Change coverage
FAIL at `SKILL.md:569`, whose command column reads "case review over 6 cases" rather than a runnable
command. `SKILL.md:548` makes the adjacent point about commands, "An invented command is worse than an
absent one", and the same holds for output: a lane invents nothing.

`attribution` is non-null on every FAIL, carrying the Step 5 sentence that says whether the failure
looks new (`SKILL.md:470-472`), which the report renders as prose beside the failure.

`command` is `null` when the gate names a method rather than a runnable command, which is how
Change coverage and a handoff row are recorded (`SKILL.md:531`, `:533`).

`evidence_block` is a markdown fragment the orchestrator splices verbatim into that gate's named
report section.
Gate 2 and Gate 8 must populate it: Gate 2's numbered case table is required by the Critical Rule at
`SKILL.md:680` ("Enumerate the change's cases before grading coverage, and show the table"), and
Gate 8's per-probe table (`SKILL.md:588-594`) comes with the statement of whether the run started
the server or found it running (`SKILL.md:585`), the Critical Rule at `SKILL.md:689` naming the
probed host, and the failing probe's exact `curl` with the paragraph explaining it
(`SKILL.md:596-606`), which only the lane holds. A one-line `detail` string cannot carry either.

The orchestrator writes the artifact by folding `counts` and `detail` into the single `detail` field
the gate object uses (`SKILL.md:530`), and renders the report table from `command` and `counts`.

The shape is set by what the report needs, not by what is convenient to return. The JSON artifact's
gate object (`SKILL.md:530`) carries `name`, `status`, `command`, and `detail`; the Critical Rules
require the exact command (`SKILL.md:678`), real counts in every non-SKIP row (`:679`), and the
failing command's real output for every FAIL (`:686`). An orchestrator cannot synthesize a command
for a gate it did not run, so the lane supplies all of it, and the lane performs Step 5 attribution
for its own failures.

A lane never renders the report and never decides the overall verdict. The orchestrator renders
every prose section: `### Failures` (`SKILL.md:626-637`) from each FAIL and BLOCKED row's `command`,
`raw_output`, and `attribution`; `### Action Items` (`:639-646`) from the union of the FAIL, BLOCKED,
and HANDOFF rows; and it routes each `evidence_block` into its named section, Gate 8's at
`SKILL.md:583-606` and Gate 2's at `:608-624`, rather than beneath a table row.

Aggregation is mechanical: the orchestrator concatenates the rows in gate order, reduces duplicate
**graded** rows for one gate using the order stated under the lane table, leaves every handoff row
standing on its own, and applies the existing Verdict Rules (`SKILL.md:656-670`) to the union. `SKILL.md:75` forbids collapsing BLOCKED or HANDOFF into SKIP, so
the aggregation preserves all six statuses rather than reducing them to pass/fail.

**A lane that fails to return is BLOCKED, not PASS.** An aggregation that treats a missing return as
an absent finding would report a clean sweep from a lane that never ran, which is the
silent-degradation failure the six-status model exists to prevent.

### Data Model

N/A. This plan adds no persisted structure. The JSON artifact keeps the schema and location it has
today.

### Interface

The user-facing entry point does not change: `/quality-gates [--changed | --all]`.
`commands/quality-gates.md` currently reads `${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/SKILL.md`
by path, deliberately, to dodge the command-versus-skill namespace collision documented at
`AGENTS.md:262-266`. It will point at the agent instead, subject to Open Question 1.

## Implementation Milestones

| # | Milestone | Files | Done when |
|---|---|---|---|
| 1 | The Open Question 0 spike, then an ADR resolving questions 0 through 3 | `docs/adr/000N-*.md` | The spike has demonstrated a plugin agent dispatching a subagent and returning its result, or has proven it cannot; the ADR records a decision and rationale for each of the four questions plus the Gate 2 ownership rule; `/validate-plugin` passes |
| 2 | The orchestrator agent and its four lane contracts | `agents/quality-gates.md` | Dispatching against a REST-surface diff produces rows for all eight gates, each carrying every field of the lane contract |
| 3 | Step 4 restructured into lanes | `skills/quality-gates/SKILL.md` | Every gate resolves to exactly one lane or to the orchestrator, all three couplings are stated in the skill rather than implied, and `/verify-acceptance` can still read the skill and run its four gates standalone |
| 4 | Referrers, registration, hook wiring, changelog | `commands/quality-gates.md`, `skills/verify-acceptance/SKILL.md`, `AGENTS.md`, `README.md`, `docs/ROUTING.md`, both copies of the labeling hook (`.claude/scripts/label_bead_on_skill_invocation.sh`, which is the one that fires here, and `scripts/label_bead_on_skill_invocation.sh`, which ships to other repositories; the two have diverged), `CHANGELOG.md` | Every referrer resolves, the registration counts match disk, a `/quality-gates` run still labels its bead, and the stale "four gates of seven" count at `skills/verify-acceptance/SKILL.md:95` reads eight |

Milestone 1 blocks 2 and 3. Milestone 4 depends on both 2 and 3.

## Acceptance Criteria

1. Given a change with a REST surface, when `/quality-gates` runs, then the report contains one row
   per gate for all eight gates, using only the six statuses defined at `SKILL.md:66-73`, plus one
   `Handoff: <surface>` row for each handoff surface the router reported, plus a **Project checks**
   row whenever Step 1 discovered a command that maps to no gate (`SKILL.md:90`).
2. Given the same change, when the orchestrator dispatches, then the report's `**Scope:**` line
   names exactly one base SHA (`SKILL.md:563`), the hygiene gate's command carries that same SHA as
   its `--base`, and the orchestrator's transcript shows exactly one `changed_set.py` invocation.
3. Given a change with no frontend files, when `/quality-gates` runs, then the frontend lane reports
   SKIP with a stated reason and the report never omits the row.
4. Given a lane whose dispatch is deliberately made to fail (for example, by pointing it at a
   contract file that does not exist), when the orchestrator aggregates, then that lane's gates are
   reported BLOCKED and the overall verdict is FAIL, per Verdict Rule 1 (`SKILL.md:660`).
5. Given a change with an `http-api` surface, when the report is produced, then Gate 2's end-to-end
   finding and Gate 8's probe result are both present and distinguishable, per `SKILL.md:243`.
6. Given the repository after this change, when `.githooks/pre-push` runs, then the eight
   `skills/quality-gates/scripts/*.py` check lines at `:129-136` all resolve and run, as they do
   today.
7. Given a `/quality-gates` invocation, when it starts, then the run receives the same injected
   instruction it receives today from
   `.claude/scripts/label_bead_on_skill_invocation.sh:202-204`, which is inject mode carrying the
   gate "the overall verdict is PASS", and the bead it acted on carries the `qa-d` label after a
   PASS verdict and no label after any other verdict.
8. Given `AGENTS.md` and `README.md` after this change, when the registered component lists are
   compared against `agents/`, `commands/`, and `skills/` on disk, then the names and counts match.
9. Given the same diff run three times each way, once through `skills/quality-gates/SKILL.md` read
   directly and once through the orchestrator, when all six runs complete, then every wall-clock
   time is recorded in the changelog entry and the orchestrator's median is no more than 10 percent
   slower than the direct median. Under the Open Question 0 fallback this is the whole bar; with
   concurrency it is the floor, and the entry says which path produced the numbers.
10. Given a `/quality-gates` run through the orchestrator, when it completes, then each lane
    returned only the contract's fields, `raw_output` is non-null only on rows whose status is FAIL
    or BLOCKED, every FAIL row carries a non-null `attribution`, and the orchestrator's transcript
    contains no test-runner output from a lane whose gates all passed.
11. Given a fixture diff containing a `.tsx` file, when `/quality-gates` runs, then the frontend lane
    returns a real Gate 1 row for the frontend suite and a `Handoff: browser-ui` row naming `/qa`
    with a null command, Gate 2 is reported HANDOFF rather than SKIP because every routed surface
    was a handoff (`SKILL.md:180-181`), and the overall verdict is INCOMPLETE per Verdict Rule 2
    (`SKILL.md:661`).
12. Given a diff that touches both an `http-api` file and a `library` file, when `/quality-gates`
    runs, then the report contains exactly one Change coverage row, its counts cover every case in
    the orchestrator's numbered case list, and the `### Change Coverage` table contains a row for
    every numbered case, including the cases graded by the lane whose status did not survive the
    reduction.

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| The capability the design rests on does not exist | High | Unknown | No agent's `tools` array carries a Task or Agent tool today. Open Question 0 and the milestone 1 spike settle it before any other work, and carry a written fallback |
| The bead-labeling hook stops firing, silently | Medium | High | `.claude/settings.json:29` wires `.claude/scripts/label_bead_on_skill_invocation.sh` to `PreToolUse` with matcher `Skill`, and that copy maps `quality-gates` to inject mode at `:202-204`. An agent dispatch is not a `Skill` call, so nothing fires and nothing errors. Criterion 7 pins the behavior; Open Question 2 decides the mechanism |
| A command and an agent of the same name collide in the `tadw:` namespace | High | Unknown | Open Question 1 settles it before milestone 2, choosing between reading the agent by path and giving the agent a non-colliding name |
| Fan-out loses a cross-gate coupling and the report reads green while a gate never ran | High | Medium | All three couplings are stated explicitly in Technical Approach; criteria 2, 4, 5, and 11 each pin one |
| No precedent for a fan-out agent in this repository | Medium | Certain | No agent in `agents/` spawns subagents. Milestone 2 is therefore the riskiest estimate in this plan; the spike in milestone 1 exists to price it before the skill is touched |
| The restructure makes the skill unusable standalone | Medium | Medium | `skills/verify-acceptance/SKILL.md:89` reads the skill and runs four gates without the agent. Milestone 3's Done-when and the Rollback line both require the standalone path to keep working |
| Parallel lanes cost more tokens than the serial run saves in time | Low | Medium | Accepted. Criterion 9 requires both wall-clock numbers in the changelog entry rather than leaving it unmeasured |

## Dependencies

- **Open Question 0 (a Task or Agent tool available to a plugin agent)** blocks milestones 2, 3, and
  4. It is resolved by the milestone 1 spike, not assumed.
- **`skills/quality-gates/scripts/route_qa.py`** supplies the surface classification that decides
  which lanes run. It exists and is covered by `test_route_qa.py`.
- **`skills/quality-gates/scripts/changed_set.py`** supplies the base SHA (on stderr, per
  `changed_set.py:167`) and the changed set on stdout. It exists and is covered by
  `test_changed_set.py`.
- **The milestone 1 ADR** blocks milestones 2 and 3.
- Related but not blocking: `tadw-6qd` scripts the Step 5 JSON artifact write. Either order works;
  whichever lands second adjusts to the other.

## Testing Strategy

There is no test runner for prompt assets, so the gates on this change are the repository's own
checks plus the manual runs the acceptance criteria describe.

**Automated, and already in `.githooks/pre-push`:**

- `python3 skills/quality-gates/scripts/test_route_qa.py` and the five sibling suites, which must
  keep passing unchanged. This plan does not touch the scripts, so a failure here means the
  restructure moved something it should not have.
- `python3 skills/quality-gates/scripts/check_doc_paths.py`, which covers the new ADR under
  `docs/adr/` and the edits to `AGENTS.md`, `README.md`, and `docs/ROUTING.md`. It proves
  nothing about this plan's own citations: `.docpaths-ignore:19` is `doc:docs/plans/*`, which skips
  every document under `docs/plans/` on purpose, because a plan naming a file that does not exist
  yet is the plan working. This plan's citations were checked by hand and must be re-checked by hand
  on revision.
- `python3 .githooks/test_prepush.py`, which pins that the pre-push hook still names real paths.
- `claude plugin validate .` and `/validate-plugin`, for frontmatter and registration.

**Manual, once per milestone:**

- Run `/quality-gates` against a diff with a REST surface and confirm criteria 1, 2, 5, 9, and 10 by
  reading the report.
- Run `/quality-gates` against a docs-only diff and confirm criterion 3: the frontend and integration
  lanes report SKIP with reasons rather than vanishing.
- Run `/quality-gates` against a fixture diff carrying a `.tsx` file and confirm criterion 11.
- Induce a lane failure and confirm criterion 4.
- Run `/verify-acceptance` and confirm it can still read the skill directly and run its four gates
  without the agent.

## Open Questions

0. **Can an agent in this plugin dispatch a subagent at all?** No agent's `tools` array carries a
   Task or Agent tool today, and none of the twelve agents spawns one. This is not a design
   preference; the whole approach rests on it. Milestone 1 resolves it with a spike that dispatches
   one trivial subagent from a plugin agent and returns its result. **If it cannot be done, the
   fallback is a single agent that runs the four lanes sequentially in its own context**, which
   keeps the lane contract, the step-ownership table, and the aggregation rule, and drops only the
   concurrency. Criterion 9 then becomes a no-regression check rather than a speedup.
1. **Does `commands/quality-gates.md` collide with `agents/quality-gates.md` in the `tadw:`
   namespace?** `AGENTS.md:262-266` rules only on command-versus-skill. Two known answers, and the
   ADR picks one rather than researching a third: have the command read the agent by path, the same
   dodge it uses today for the skill, or name the agent `quality-gates-orchestrator` so no collision
   is possible.
2. **How does bead labeling survive an agent dispatch?** The copy that fires here,
   `.claude/scripts/label_bead_on_skill_invocation.sh`, is wired by `.claude/settings.json:29` to
   `PreToolUse` with matcher `Skill`. Options: add a matcher for the agent dispatch, have the orchestrator invoke the
   skill through the `Skill` tool so the existing matcher still fires, or label from the Stop event
   instead. This blocks criterion 7.
3. **Does the documentation lane report drift, or fix it?** `commands/quality-gates.md:39` and
   `SKILL.md:695` both promise report-only, and `SKILL.md:695` forbids editing the working tree at
   all. A lane that updates documentation reverses a stated guarantee. This plan implements
   report-only; reversing it is a decision for the ADR, not an implementation detail.
