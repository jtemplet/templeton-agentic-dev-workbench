# Feature Plan: Deterministic Ship Command

**Date:** 2026-09-23
**Status:** Draft

## Summary

Move the ship workflow into a Python executable for repository maintainers and unattended callers.
Keep a short ship skill and direct terminal use as the two interfaces to the same executable.
The executable will enforce the workflow, record progress, and generate reports without model calls.

## Motivation

The current ship skill makes the model coordinate commands, retries, gate selection, and reports.
Its Python helpers already enforce several rules, but the model still connects their results.
Moving those remaining rules into code should reduce tokens, model turns, and inconsistent outcomes.

The review measured 494 lines, 4,546 words, and 27,600 bytes in the skill.
Reproduce that baseline with `wc -l -w -c skills/ship/SKILL.md`.
These are document measurements, not measured token costs or execution times.

The review found these concrete opportunities in the current files:

| Evidence | Consequence | Proposed improvement |
|---|---|---|
| The skill describes six steps and leaves their execution to the model | Each command result can require another model turn | Execute the workflow in Python |
| Step 3 interprets Markdown and framework conventions to choose checks | Gate selection can differ between runs | Read explicit gate configuration |
| `.githooks/pre-push` repeats checks used by ship | Some checks run twice | Share execution and selectively reuse results |
| The gate precedes the squash and tracker export | The checked tree can differ from the final commit | Check the candidate tree and verify the committed tree |
| Step 4 permits local default-branch commits beyond the remote base | The final merge can include code absent from the earlier gate | Include those commits in the candidate tree |
| Step 5 treats a rejected push as a moved remote | Some failures cause needless reconstruction | Classify failures before retrying |
| The branch resolver proposes up to 25 bead candidates | Resolving a bead can require many tracker calls | Prefer an explicit bead ID or stored mapping |
| Step 1 permits untracked files; Step 3 rejects any porcelain status output | The same file can pass one guard and fail another | Share one status policy |
| Step 1 says both to take the first matching bead and reject multiple matches | Selection depends on which instruction the model follows | Resolve and deduplicate candidates in code |
| Helper commands repeatedly search installed directories with `find` | Searches cost time and can select another installed copy | Resolve the executable location once |

The evidence comes from [the ship skill](../../skills/ship/SKILL.md),
[the ground resolver](../../skills/ship/scripts/resolve_ground.py), and
[the pre-push hook](../../.githooks/pre-push).

## Scope

### In Scope

- A Python executable that performs ship without model calls.
- A smaller ship skill that invokes the executable and passes through its result.
- Exact `cd` guidance when ship removes the worktree its caller started in.
- Explicit gate configuration, shared check execution, and bounded concurrency.
- Migration of this repository's gate list before `/tadw:ship` switches to the new command.
- Final-tree verification, recorded progress, and recovery after interruption.
- Explicit bead selection, canonical ID matching, and a compatibility fallback for branch names.
- Shared guards, generated reports, deterministic subjects, and bounded failure output.
- One stable executable location with helper imports relative to that installation.
- Workflow tests and measurements of instruction size, model calls, and elapsed time.
- Conditional reuse of check results after eligibility rules are established.

### Out of Scope

- A shell function or wrapper in any shell, fish or bash included.
- Pull requests, hosted CI as the ship gate, or changes to release numbering.
- Resolving source conflicts or fixing failing application checks during ship.
- Disabling hooks, skipping required checks, or force-pushing the default branch.
- Changing tracker schemas or making the export a source of truth.
- Replacing the quality-gates orchestrator or changing its agent delegation policy.
- Filing implementation beads or implementing this plan during the planning task.

## Technical Approach

### Architecture

Use one Python executable for both direct terminal use and `/tadw:ship`.
Retain Python because the existing ship helpers already use it and have regression suites.

The executable owns named workflow states and the rules for moving between them.
It resolves the repository, branch, default branch, bead, and gate before starting mutations.
Every command receives an explicit repository path and argument list.
Only the documented shell-command override requires shell interpretation.

Resolve helper locations relative to the installed executable.
The skill uses its loaded plugin root when available.
Any fallback must select one installation explicitly and reject ambiguous installations.
A filesystem traversal must not choose a version through first-match ordering.

Keep the current machine lines and stop categories for existing callers. In particular,
Callers must still consume `SHIP_DONE <sha>` or `SHIP_BLOCKED <reason>`. The reported
commit must exist on the verified destination before remote shipping counts as complete.
Repositories without a remote retain the current local completion behavior and report that
limitation.

### Gate Selection and Execution

Keep `TADW_SHIP_CHECK` as the highest-priority command override. Keep `TADW_SHIP_CHECK_TIMEOUT` and
its current default unless a later decision changes that contract. Below the override, read a
versioned repository configuration that declares the complete gate. Missing configuration stops ship
with instructions for configuring the gate. Configuration discovery may suggest commands during
setup, but must not reinterpret Markdown on every run.

Ship the Python executable before changing `/tadw:ship` to call it. During that first stage, the
existing skill remains the active path for repositories without gate configuration. Before the skill
switches, add and validate configuration for this repository. Its ship list must match the commands
in `AGENTS.md`, excluding `python3 evals/run.py`. Publish one-time setup instructions for other
repositories before the switch. Their maintainers can create a configuration or set the existing
`TADW_SHIP_CHECK` override. After the switch, the Python command stops with an actionable gate error
when both are absent. An unknown repository cannot be migrated from this plugin repository, so the
stop is deliberate and must name the setup action. Do not describe that stop as a successful ship.

Share a check runner between ship and this repository's pre-push hook. Keep their policies separate:
ship requires its complete gate; pre-push retains its documented forgiveness. Preserve the distinct
ship and pre-push check lists, including their eval exclusions. Preserve the pre-push rule that
reports all check failures together.

Declare dependencies and shared resources for checks.
Run independent checks concurrently within a fixed worker limit.
Run checks that share the tracker database in sequence.
Timeout and interruption must stop child processes and record incomplete checks as incomplete.

Introduce result reuse only after defining eligible checks and their complete inputs. A matching
commit hash alone does not prove that commands, tools, environment, or external services match. The
default is to rerun a check whose inputs cannot be identified reliably. Missing, invalid, failed, or
incomplete saved results never satisfy ship's gate. Do not use `TADW_PREPUSH=off` to avoid repeated
work.

### Candidate Tree and Recovery

Build the candidate from the actual local default-branch state and the feature branch.
Include pre-existing local default-branch commits that the current skill permits shipping.
Protect unrelated work in either checkout before changing branches or staging files.

Use a temporary worktree based on the current local default-branch commit. Squash the feature branch
there while the default branch stays unchanged. Close the bead through bd, export the tracker, and
create the candidate commit in that worktree. The pre-commit hook may refresh the export during this
commit. Run the complete gate against the clean candidate commit after the hook returns. This order
checks the exact committed tree, including tracker metadata. If a check changes a tracked file,
invalidate the result and stop before updating the default branch or pushing. The gate may create
untracked output only when that output does not obstruct cleanup. Export the tracker to a temporary
file after the gate. If its bytes differ from the candidate commit's export, invalidate the gate
result and stop before updating the default branch.

After a passing gate, verify that the local default branch still names the candidate's parent.
Fast-forward that branch to the checked candidate commit. If its base moved, build and check a new
candidate before moving the branch. Verify the remote contains the candidate commit after push.
If pre-push creates a later local commit, report it as unpushed; do not claim it was checked or
published by this run. No candidate commit reaches the default branch before its gate passes.

When a gate fails or times out, keep the default branch unchanged and the feature branch at its
rebased tip. Reopen the bead only when its current tracker state still matches this run's close.
Regenerate its export through bd after reopening. If that comparison or reopening fails, retain the
candidate and progress record, report the bead's actual status, and stop with `tracker`. Never report
a closed bead as an ordinary `gate` stop that the caller can restart from the branch. A bead-free ship
needs no tracker reversal. Remove the temporary worktree only after recording the final state.

If the process stops after closure but before the gate, resume from the recorded candidate state.
Verify the bead and the recorded staged tree or commit. Complete the commit or safely reverse this
run's close before continuing. If the process stops after a passing gate but before the
fast-forward, keep the bead closed and resume from the verified candidate when its base is still
current. After the fast-forward, keep the bead closed while push or cleanup retries. An unknown or
changed tracker state stops recovery for a human decision.

Record progress before and after each mutation in local state outside the tracked working tree.
Store that state where removing the feature worktree cannot delete it.
Allow only one active ship mutation sequence per repository common directory.
On restart, verify stored commits, refs, paths, and tracker status against current state.
An inconsistent record stops recovery rather than authorizing a reset.

Classify push failures before selecting a recovery action.
A confirmed moved destination may require rebuilding the candidate and rerunning the gate.
An authentication or hook refusal requires a report, not reconstruction of the landing commit.
After an uncertain network result, inspect the destination before retrying or cleaning up.

Tracker closure and Git publication are separate operations with no shared transaction. Record
whether this run closed the bead and whether its commit exists locally or remotely. Recovery must
distinguish an interrupted run from an unrelated invocation naming an already closed bead. Never
reopen a bead automatically when concurrent tracker changes make ownership uncertain.

### Bead Selection, Guards, and Output

Resolve beads in this order: explicit argument, stored branch mapping, then branch-name fallback.
Validate the selected ID against the tracker.
For fallback matching, deduplicate responses by canonical bead ID before checking ambiguity.
Keep the current bead-free behavior when no candidate resolves or no tracker exists.
An invalid explicit argument continues to stop the run.

Use the same guard functions at every workflow boundary.
Untracked files remain reportable unless they obstruct a required operation.
Changed tracked files block mutations, and failed status inspection is a distinct error.
Compute default-branch commands from resolved names, including repositories that use `master`.

Generate the report and machine line from one structured result.
Keep full command output in local logs and return bounded failure excerpts to model callers.
Report counts only when a known parser can extract them; otherwise mark counts unavailable.
Shorten bead titles through a fixed algorithm that preserves the bead ID.
For bead-free shipping, accept an explicit subject and define a deterministic branch-slug fallback.

No shell function ships. A child process cannot change its parent shell's directory, and a shell
function would tie the interface to one shell: fish must be installed, and a bash function does not
load in fish. Python records its starting directory, which is the caller's directory. Before it
removes a worktree, Python resolves a stable checkout path outside every worktree it may remove, and
moves its own process there. If it cannot find one, it stops before the first mutation. When the
starting directory sat inside a removed worktree, the result prints the exact `cd <stable-path>`
line before the final machine line. Agent and terminal callers get the same accurate guidance, and
no output claims that their shell moved.

### Key Components

Existing paths below were checked during planning. Names of new commands and files remain proposed.

| Component | Purpose | Change |
|---|---|---|
| `skills/ship/SKILL.md` | Invoke ship and describe its result contract | Modify |
| `skills/ship/scripts/` | Hold the Python workflow and existing helper interfaces | Extend |
| `resolve_ground.py` and its regression suite | Resolve repository state and consistent guards | Reuse and extend |
| `landed_check.py` and its regression suite | Check branch content before cleanup | Reuse |
| `resolve_rebase_conflict.py` and its regression suite | Resolve the existing mechanical conflicts | Reuse |
| `check_worktree_occupants.py` and its regression suite | Report occupants before cleanup | Reuse |
| Proposed `tadw-ship` executable | Provide direct terminal access | New |
| Proposed gate configuration and shared check runner | Declare and execute checks | New |
| Repository gate configuration | Preserve this repository's complete ship gate during migration | New |
| `.githooks/pre-push` and `.githooks/test_prepush.py` | Consume the shared runner without changing hook policy | Modify |
| `.githooks/pre-commit` | Existing source of tracker export changes during commit | Verify integration |
| `AGENTS.md`, `README.md`, and `docs/ROUTING.md` | Document invocation, configuration, and migration | Modify |

### Test Seams

A test seam is the public boundary through which a test proves behavior.
The user confirmed Python command tests in temporary repositories and retention of existing helper tests.
The user later removed the fish function, so no shell-function seam remains.
Existing pre-push tests continue to protect hook behavior during runner extraction.

| Seam | Existing or new | What it proves |
|---|---|---|
| Python executable in temporary repositories | New | Workflow outcomes, recovery, refs, files, and tracker calls |
| Existing helper command interfaces | Existing | Repository inspection, landed checks, conflict resolution, and occupant reporting |
| Existing pre-push test interface | Existing | Check selection, interruption, and hook policy after runner extraction |

Use the executable as the primary seam because its observable behavior should survive internal
refactoring. Keep helper tests that already prove independent behavior without duplicating every
workflow assertion.

### Data Model

No tracker schema changes are required.
Use versioned local records for gate configuration, progress, and results.
Exact filenames and serialization formats remain implementation choices.

| Record | Required contents |
|---|---|
| Gate configuration | Commands, working directories, dependencies, resource groups, timeouts, and reuse eligibility |
| Branch mapping | Repository identity, branch name, and canonical bead ID |
| Progress | Run ID, workflow state, original branch tip, destination, candidate parent and commit, bead snapshots, and tracker mutations |
| Check result | Command, checked inputs, tool identity, relevant environment, exit status, duration, and log location |
| Ship result | Outcome, stop reason, landed commit, destination status, cleanup status, warnings, and next-bead evidence |

### API / Interface

Proposed terminal commands are `tadw-ship [bead-id]` and `tadw-ship --resume <run-id>`.
A result-file option provides JSON without changing the existing final machine line.
Exact flag names must be settled before implementation beads expose them as contracts.
When the caller's starting directory is removed, the output names the `cd` target before the
machine line.

Retain `/tadw:ship`, its bead argument, the documented environment overrides, and existing stop
categories. Do not create `commands/ship.md`, which would compete with the skill's invocation name.
Direct terminal execution uses no model; the skill invokes the executable once and reports its
result.

## Decisions That Bind This Plan

| ADR | Rule | Application |
|---|---|---|
| [0001](../adr/0001-native-tracker-fields-are-canonical.md) | Native tracker fields are canonical | Read bead fields through bd without changing their storage |
| [0003](../adr/0003-a-push-to-main-is-already-published.md) | Pushing the default branch distributes the plugin | Complete verification before publication; leave numbering to a manual release |
| [0004](../adr/0004-the-pre-push-hook-forgives-by-design.md) | The hook names missing evidence and forgives it | Preserve hook policy while ship remains strict |
| [0005](../adr/0005-the-evals-are-a-measurement-not-a-gate.md) | Model evals are deliberate measurements | Keep model measurements outside hooks and the ship gate |
| [0007](../adr/0007-a-tadw-skill-wins-over-an-overlapping-external-skill.md) | tadw owns this workflow | Retain tadw invocation and source-conflict boundaries |
| [0009](../adr/0009-the-large-skill-documents-are-not-split.md) | Required rules do not belong in optional reference files | Replace prose rules with executable checks before removing them |
| [0010](../adr/0010-the-tracker-export-rides-the-commit-and-the-audit-log-is-untracked.md) | The export joins the commit; the interactions log stays untracked | Preserve export hooks and verify their effect on the checked tree |

No ADR replacement is proposed. Use the definitions in [CONTEXT.md](../../CONTEXT.md) for ship,
gate, bead, export, and machine line.

## Implementation Milestones

Effort bands describe relative scope, not elapsed-time promises.
These milestones describe the design sequence; bd remains the implementation tracker.

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Contracts and baseline | Set the configuration format, draft migration instructions, and set the speed target from current runs | M | Fixtures identify commands, outputs, and rules; a measured speed target exists before implementation |
| 2 | Executable and gate migration | Add the Python workflow, shared guards, and this repository's gate configuration | L | The command validates the configuration and its checks match `AGENTS.md` except the model eval |
| 3 | Checked candidate and recovery | Commit and check a temporary candidate, then record and recover each mutation | L | A failed gate leaves main unchanged; interruption and moved-base tests preserve work |
| 4 | Shared check execution | Extract concurrency and command execution for ship and pre-push | M | Both callers retain their required checks and failure policies |
| 5 | Eligible result reuse | Reuse only results with complete, matching inputs | M | Invalidation tests rerun every changed or unverifiable check |
| 6 | Terminal, documentation, and skill switch | Add terminal use with `cd` guidance, generated output, and a smaller skill; publish setup instructions | M | The skill switches only after configuration and documentation; both interfaces preserve the machine line |
| 7 | Final verification | Measure savings and check all acceptance criteria | M | Evidence covers behavior, instruction size, check counts, and execution time |

## Acceptance Criteria

1. Direct execution completes a fixture ship without model calls and produces the expected
   destination commit.
2. Skill execution invokes the runner once, excluding tool polling, and ends with exactly one
   existing machine line.
3. The ship skill contains at most 500 words, measured with `wc -w`, without requiring another
   workflow document.
4. The override selects the declared gate; missing or invalid configuration stops before shipping
   mutations.
5. Before `/tadw:ship` switches to Python, this repository has validated configuration whose ship
   checks match the `AGENTS.md` list except `python3 evals/run.py`. Setup instructions for other
   repositories are published before that switch.
6. Every required check runs or yields an explicit failure. Timeout and interruption never produce
   success.
7. Independent check fixtures overlap in execution; fixtures sharing a tracker resource execute in
   order.
8. The complete gate checks a clean candidate commit after pre-commit hooks. The published commit
   has that checked tree. Tracked changes or a changed tracker export invalidate the gate result.
9. When the gate fails after this run closes a bead, the default branch stays unchanged. The bead
   reopens if its state still matches this run's close; otherwise `SHIP_BLOCKED tracker` names its
   actual status and retains the candidate for recovery.
10. An interruption between bead closure and gate completion resumes from verified progress. It
    never mistakes that bead for work previously shipped by another run.
11. Local default-branch commits beyond the remote base appear in both the candidate tree and the
    report.
12. A changed destination requires renewed verification; other push failures preserve the
    candidate and report their cause.
13. An uncertain push result triggers destination inspection before retry or cleanup.
14. Resuming after each recorded mutation verifies current state and neither duplicates a landing
    nor deletes unrelated work.
15. Concurrent ship invocations cannot mutate the same repository simultaneously.
16. Explicit bead selection requires one lookup. Fallback aliases resolving to one canonical ID
    are not ambiguous.
17. Two distinct fallback bead matches stop the run; an invalid explicit ID never becomes
    bead-free shipping.
18. Untracked files follow one policy throughout. Failed status inspection cannot count as a clean
    working tree.
19. A missing or ineligible saved check result reruns the check. Changed declared inputs invalidate
    saved success.
20. Reports derive from recorded results, keep full logs outside model output, and never invent
    test counts or bead IDs.
21. Multiple installations cannot silently select a helper from a different version.
22. Python runs from any shell with no wrapper. When it removes the worktree its caller started
    in, it prints the exact `cd` line to a stable checkout before the final machine line.
23. Source conflicts stop and abort rebase. Dirty worktrees and the default-branch worktree survive
    cleanup.
24. Tracker exports remain generated by bd, and the interactions log stays untracked.
25. A caller consumes the unchanged machine line successfully, including every existing
    blocked category.
26. With the same checks and fixture inputs, a warm ship-and-push run starts fewer check processes
    and has a lower median elapsed time than the current workflow. Measure each version three times
    and report cold-run results separately.

**Coverage:** Criteria 1-3 measure model overhead and instruction size. Criteria 7, 19, and 26
prove speed. Criteria 4-6 protect gate coverage and migration. The remaining criteria cover checked
content, recovery, compatibility, and protection of existing work.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Git publication and tracker closure cannot be atomic | High | Medium | Commit in a temporary worktree; record the closure and verify both systems before recovery |
| A gate fails after bead closure | High | Medium | Reopen only when this run still owns the close; otherwise report the closed bead and retain the candidate |
| A hook changes the checked tree | High | Medium | Run the gate after pre-commit hooks; reject tracked changes made by the gate |
| Saved success omits an input that matters | High | Medium | Require explicit eligibility; rerun when inputs are uncertain |
| Concurrent callers change refs or tracker state | High | Medium | Serialize ship mutations and recheck external state |
| Runner extraction changes pre-push forgiveness | High | Medium | Keep caller policy separate and retain hook regression tests |
| Existing repositories lack gate configuration | Medium | High | Migrate this repository before the skill switches; document configuration and the override for others |
| Installation expands into general shell tooling | Medium | Medium | Ship no shell function; print `cd` guidance from Python |
| A smaller skill omits a rule before code enforces it | High | Medium | Map each removed rule to executable behavior and acceptance evidence |

## Dependencies

- Python 3 and Git, already required by the existing helper workflow.
- bd for ships with a bead; direct bead-free execution remains supported.
- Repository-specific tools declared by the configured gate.
- Current helper regression suites and `.githooks/test_prepush.py`.
- Resolution of configuration, installation, and result-reuse contracts before their implementation
  milestones.

## Testing Strategy

Drive the executable against temporary repositories and local bare remotes.
Use a controlled bd executable to force tracker failures and verify call ordering.
Add isolated real-bd checks where its database-location and export behavior affect correctness.
No test may mutate the maintainer's tracker or push to the project's real remote.

Cover clean shipping, bead-free shipping, no remote, alternate default branches, and linked
worktrees. Cover duplicate bead aliases, multiple beads, dirty tracked files, harmless untracked
files, and failed status inspection. Cover already-landed content, source conflicts, mechanical
conflicts, failing gates, and unavailable tools. Interrupt the process around tracker closure,
commit, push, and cleanup, then exercise resume. Cover remote movement, hook refusal, authentication
failure, uncertain transport results, and hook-created changes.

Exercise the actual configured gate from this repository and compare its command set to `AGENTS.md`.
Test a repository with no configuration or override and one migrated through the override. Run the
gate on a temporary candidate whose export reflects `bd close`. On a failing gate, verify whether
the bead reopens or the report names the closed bead and retained candidate. Test interruption
between close and candidate commit, and between candidate commit and gate. Test a pre-push hook
that creates a later local commit; the report must name it as unpushed. Test a gate that changes the
tracker database without touching a tracked file; the post-gate export comparison must stop ship.

Keep existing helper suites and run pre-push fixtures after extracting shared execution. Test result
reuse with changed content, command definitions, tool identities, and declared environment inputs.
Prove Git, tracker, and `cd` guidance behavior through Python execution.

Measure instruction size before and after with the same command. Measure each cold and warm case
three times with identical fixture inputs and gate commands. Record median elapsed time and actual
check-process counts. The warm case must improve both values to satisfy criterion 26. Report cold
results even if they regress. Measure skill token usage only where the calling runtime exposes it;
do not substitute word counts for tokens. Keep model measurements outside deterministic gates, as
ADR 0005 requires.

## Open Questions

- **Milestone 1 implementer:** Choose the configuration filename and versioned format. Draft the
  migration procedure for publication before the milestone 6 skill switch.
- **Implementer and plan reviewer:** Choose the installation mechanism without assuming a
  particular plugin cache layout.
- **Implementer and plan reviewer:** Specify the progress-record format and retention. Preserve the
  closure, candidate, and gate states defined in this plan.
- **Implementer and plan reviewer:** Select the first checks eligible for reuse and enumerate their
  complete inputs. Keep reuse disabled until this is proven.
- **Implementer and plan reviewer:** Define branch-mapping storage and who writes it without
  expanding this plan into every branch-creation workflow.

The terms in this plan use the existing glossary. Local result and progress records describe
proposed implementation data, not new plugin components or replacements for beads.

## Revision Notes

**2026-09-23 plan review:** Added gate configuration migration before the skill switch. Defined a
temporary candidate commit checked after pre-commit hooks, the bead state after a failed gate, and
resume points after interruption. Placed the fish directory change before Python invocation and
added a measured warm-run speed criterion.

**2026-09-24 interface change:** Removed the fish function, and chose no shell function in its
place. A bash script cannot change its caller's directory, and a bash function does not load in
fish. Python now detects when it removes its caller's starting worktree and prints the exact `cd`
line. This keeps the interface independent of the shell.
