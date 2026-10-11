# Feature Plan: Stronger TADW validation reports

**Date:** 2026-10-11
**Status:** Draft
**Planning bead:** tadw-28ik

## Summary

Give TADW's quality-gates and acceptance reports complete inputs, named evidence, and consistent
validation by every reader. Keep the two report formats and their current verdict policies.
Introduce version 3 through a reader-first release, coordinated with Outrigger.

This document recommends a design for review. The user requested the plan; implementation and
the version 3 release remain separate work.

## Motivation

A developer needs to know which checks ran, which criteria were graded, and which files they
describe. An autonomous caller needs the same information before advancing to the next phase.

TADW's version 2 writers already validate fields, reject inconsistent results, cap evidence,
and replace reports atomically. The remaining work concerns complete coverage, evidence, and
consistent reader decisions.

Grounding used TADW main at `baf6b1fb8d65a4819c7dbe7f574f528ae47dac34`, Outrigger at
`e7ca3e0`, and the local Gas City reference at `f9a0b0d`.

| Current behavior | Evidence | Improvement |
|---|---|---|
| Quality-gates validates its verdict against gate statuses | `skills/quality-gates/scripts/write_report_json.py`, `build_report` | Preserve this rule and use it in readers |
| Acceptance checks counts against criterion and gate results | `skills/verify-acceptance/scripts/write_acceptance_report.py`, `check_counts` | Preserve this rule and compare against the expected criteria |
| Evidence and commands can be null | Both writers' field rules | Require evidence appropriate to each claimed result |
| The quality-gates Stop reader checks the verdict string | `scripts/label_bead_on_skill_invocation.sh`, `quality_gates_report_passes` | Check the complete report and its identity before labeling |
| Acceptance Stop checks counts rather than recounting results | The same script, `acceptance_report_passes` | Use the report format's validator before deciding acceptance |
| The writers know only the results submitted by the caller | Both writers' input contracts | Compare results with a saved list of expected checks and criteria |
| A command executor already records real outcomes | `skills/ship/scripts/run_checks.py`, `CheckResult` | Reuse it for command evidence instead of building another executor |

Gas City's `internal/dispatch/ralph.go`, `persistCheckResult`, records exit status, output,
duration, and truncation. Its formula guide separates a check's result from an agent's completion
claim. Borrow those mechanisms without introducing a formula engine.

## Scope

### In Scope

- Define version 3 for the two existing report formats.
- Validate expected checks, expected criteria, report identity, and supporting evidence.
- Capture command results through the existing executor.
- Apply each report format's validation rules in its writers and readers.
- Keep incomplete browser and device checks visible through the existing reporting work.
- Coordinate portable hook installation and Outrigger compatibility before producer cutover.
- Add contract fixtures and behavior tests at the confirmed boundaries.

### Out of Scope

- A general report framework covering build, ship, UX, and every other skill.
- A new command executor, formula engine, scheduling system, or retry system.
- Automatic fixes inside quality-gates or verify-acceptance.
- A new browser or iOS verification implementation.
- Changing pre-push to refuse missing evidence.
- Rewriting Outrigger's inline acceptance report in this TADW change.
- Treating a report as protection against an agent deliberately altering local evidence.

## Technical Approach

### Architecture

Keep one completed report per skill at its existing path:

- `<git-dir>/quality-gates-report.json`
- `<git-dir>/acceptance-report.json`

The skill resolves repository and tracker context. It saves the expected checks or criteria before
grading. Command execution produces measured results. The skill supplies judgment about criterion
meaning and findings. A format-specific validator combines these inputs and refuses contradictions.

The writer publishes a report only after validation succeeds. The same format-specific rules
validate reports read by hooks, reconcile skills, and result reuse. Each consumer keeps its own
policy for what to do with a valid report.

A schema check proves structure and consistency. Command evidence proves what a process returned.
Criterion grading still requires judgment about whether that evidence proves the requested behavior.

Keep the two report formats separate. Share a format's validation rules between its producer and
consumers; do not introduce a universal loader with a report-mode argument.

### Key Components

All paths described as existing were checked in the repositories named below. New paths are proposals.

| Component | Purpose | New/Modified |
|---|---|---|
| `docs/validation-report-contract.md` | Own both formats' identity, evidence, and compatibility rules | New |
| `skills/quality-gates/scripts/report_contract.py` | Validate quality-gates reports and derive their verdict | New |
| `skills/verify-acceptance/scripts/report_contract.py` | Validate acceptance reports and derive their counts | New |
| Both existing report writers | Use their contract module and publish validated reports atomically | Modified |
| `skills/quality-gates/scripts/capture_validation.py` | Adapt existing command results into report evidence | New |
| `skills/ship/scripts/run_checks.py` | Supply execution results without adopting ship's policy | Existing |
| Both `skills/reconcile-*/scripts/load_findings.py` readers | Validate the report before selecting findings | Modified |
| `scripts/label_bead_on_skill_invocation.sh` | Validate a matching completed report before labeling | Modified |
| `scripts/install_label_bead_on_skill_invocation.sh` | Install and check the validator dependencies with the hook | Modified |
| `.githooks/pre-push` | Validate report structure while preserving its warning policy | Modified |
| Both check skills' `SKILL.md` files | Specify input capture, evidence, and failure behavior | Modified |
| `AGENTS.md` and `.tadw/ship-gates.json` | Register the implementation's deterministic checks | Modified |
| Outrigger `cmd/outrigger-phased/verifyacceptance.go` | Read the new acceptance contract | External companion change |

Portable hooks must carry their validator dependencies. They must not search several installed
plugin copies and silently select whichever appears first. The installer and its `--check`
operation must cover every dependency.
Give the installed validators distinct module names so one format cannot load the other's rules.

The two contract modules contain report rules, not git or tracker discovery. Their callers inject
the current commit, bead, and expected inputs. Reuse the current pattern of loading helpers from a
known path within the installed component.

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| Report-writer commands | Existing | Valid input publishes a complete report; invalid input preserves the previous file |
| Reconcile loaders, Stop hook, and pre-push behavior | Existing | The same report is interpreted consistently while consumer policies remain distinct |
| Reports produced by TADW and read by Outrigger | Existing reader with new fixtures | Version transition, identity, counts, and incomplete checks remain compatible |
| The existing command executor through its adapter | Existing executor with new adapter | Exit status, interruption, and output come from execution |

These boundaries test observable results rather than private helper functions.
The user confirmed these test boundaries on 2026-10-11.

### Data Model

Version 3 keeps the existing report-specific fields and adds a small common identity and evidence
contract. It keeps acceptance counts rather than adding a top-level acceptance verdict.

| Field or collection | Rule |
|---|---|
| `version` and report kind | Identify the exact format understood by the reader |
| `run_id` | Identify one invocation; a hook checks its pending invocation when one exists |
| `head`, `bead`, `base`, and `changed_files` | Identify the work and scope that were checked |
| `dirty` | Record whether the checked tree contained uncommitted work |
| Timestamp and producer version | Identify when the report was created and which writer produced it |
| Expected checks | Name every planned gate, its applicability, and its required evidence kind |
| Expected criteria | Copy every criterion's number and text from the resolved acceptance input |
| Execution evidence | Record command, working directory, completion state, exit code, duration, and output reference |
| Observation evidence | Identify code references, browser journeys, screenshots, or other inspected artifacts |
| Gate and criterion results | Reference the evidence supporting each claimed result |

Expected criteria are required only for acceptance. Expected checks are required for both formats.
The report retains the expected input list so a reader can detect omitted results.

Acceptance input comes from the bead's native acceptance criteria or the existing documented fallback.
Save the authoritative text once. Match graded numbers and text against that saved list.
If the input cannot be separated into clear criteria, report it as inconclusive.

A writer must reject duplicate, omitted, and unexpected results. A skipped check still has a result
and an applicability reason. The existing policy determines whether that skip affects the verdict.

An executed check needs captured process evidence. A criterion proved by reading code can cite that
code and its checked revision. Do not require every criterion to run a separate command.

Evidence reuse also compares the relevant inputs, command, tool identity, and declared environment.
A matching commit alone cannot establish that those inputs still match.

Normalize commit identifiers to lowercase. Preserve SHA-1 and SHA-256 support.
A report with no bead remains useful for a manual run and can never label a bead.

Automatic acceptance and phase advancement require committed work matching `head`.
A dirty report remains useful for inspection but cannot establish a pass for a later commit merely
because the same paths changed. Content-based reuse of dirty reports is deferred.

Store evidence under the worktree's git directory. Keep excerpts bounded and identify omitted output.
A referenced local artifact must exist and match its recorded content digest when consumed.
Replacing the latest report must not remove evidence that the replacement references.
Apply the existing secret-handling rules before storing output or rendering excerpts.

### API / Interface

Preserve the current report paths, writer exit codes, reconcile machine lines, and skill names.

Add an explicit version 3 writer option during migration. Existing version 2 invocations remain
available until the reader-first release is verified. The final producer cutover makes the skills
request version 3.

Each report's contract module exposes separate operations for validating shape, checking evidence,
and deriving the existing conclusion. A consumer supplies its own freshness requirements and policy.

The capture adapter uses `run_checks.py` with result reuse disabled initially. It records a
structured result beside bounded output. It does not add git or tracker discovery to the validators.
It preserves process-group cleanup and interruption behavior from the existing executor.
Compare checked inputs before and after execution. Changed or unreadable inputs cannot support reuse.

The quality-gates orchestrator still owns dispatch and merging of lane results. Each command gate
references captured execution evidence. The orchestrator remains responsible for interpreted
findings and cannot turn a missing lane into a pass.

Acceptance may cite a current quality-gates result through the existing `tadw-v6k` work.
A citation must resolve to valid evidence for the same inputs. Copying a previous PASS string is
insufficient. A mismatch runs the required check again or records it as incomplete.

### Reader Policies

| Consumer | Valid success | Missing, invalid, or outdated report | Valid failure or incomplete result |
|---|---|---|---|
| Stop labeling | Apply only the label for the matching bead and invocation | Apply no success label and log the reason | Apply no success label |
| Reconcile | Return the existing nothing-to-fix result | Preserve the existing BLOCKED reason order | Select only mechanically fixable findings |
| Pre-push | Apply the existing push policy | Warn and allow under ADR 0004 | Preserve the current recorded-FAIL refusal rule |
| Acceptance reuse | Cite matching evidence | Run the required checks or record an incomplete result | Carry the actual result into acceptance |
| Outrigger | Advance only after its independent report check | Record ERROR and use its existing retry limit | Follow its existing repair or human decision route |

Structural validity does not imply success. Required browser and device observations that have not
run remain incomplete. Malformed evidence is distinct from a valid report describing failed checks.

Do not change the existing acceptance SKIP policy as an incidental schema edit.
Keep every skipped gate explicit and test the documented all-SKIP behavior.
Required UI work cannot be classified as inapplicable to obtain a SKIP.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| [0001](../adr/0001-native-tracker-fields-are-canonical.md) | Native tracker fields own acceptance criteria | Capture the native acceptance input before grading |
| [0002](../adr/0002-the-quality-gates-orchestrator-fans-out-to-blocking-subagents.md) | The orchestrator collects blocking lanes and owns the result | Require every planned result without changing dispatch ownership |
| [0003](../adr/0003-a-push-to-main-is-already-published.md) | Main reaches plugin consumers immediately | Publish compatible readers before new reports become the default |
| [0004](../adr/0004-the-pre-push-hook-forgives-by-design.md) | Missing evidence warns rather than blocking push | Keep warning and refusal policy separate from report validation |
| [0011](../adr/0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md) | Findings travel in one report; the fixer never grades its fix | Keep one completed report, two loaders, and independent regrading |
| [0012](../adr/0012-ship-gates-the-code-tree-and-carries-the-close.md) | Ship checks the exact code tree under its own contract | Reuse execution machinery without replacing ship's evidence or tree rules |

The version 3 format and release sequence need a new ADR before implementation cutover.
It must amend ADR 0011's version-specific refusal rule while retaining its findings and repair rules.
This draft proposes that amendment; it does not authorize changing the accepted decision.

## Implementation Milestones

Each milestone must be split into normal-sized beads after plan review.

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Contract and fixtures | Define both version 3 formats, expected inputs, evidence rules, and migration policy | M | Valid and invalid fixtures cover every report rule; a new ADR records the version transition |
| 2 | Compatible readers | Add format-specific validators to loaders, portable hooks, and pre-push; prepare Outrigger's companion reader | L | All readers accept valid fixtures and reject malformed fixtures under their documented policies |
| 3 | Acceptance evidence | Validate the complete criteria list and referenced gate evidence; connect reconciled UI reporting work | L | Missing criteria, stale evidence, and unfinished required UI checks cannot earn accepted |
| 4 | Quality-gates evidence | Capture command results with the existing executor and account for every expected check | L | Missing lanes, omitted gates, interrupted commands, and contradictory results cannot produce PASS |
| 5 | Producer cutover | Enable version 3 after reader compatibility and hook installation are verified | M | A real fixture repository completes QA, acceptance, failure, and repair flows across processes |
| 6 | Documentation and release checks | Update skill instructions, hook installation guidance, and deterministic gates | M | Documented commands and registered checks match the shipped interfaces |

Release order is 1, then 2, then 3, then 4, then 5 and 6.
Acceptance and quality-gates producer changes can be prepared independently after their readers exist.
Map each milestone onto the existing beads in the assessment below before creating new implementation
beads. The milestones describe delivery order, not six additional tasks.

Version 2 reports are legacy evidence during migration. Never convert them into version 3 by
inventing missing inputs or execution facts. Keep their current interpretation during the reader
preparation release. The producer cutover activates the stronger automatic-success requirements.

If a reader cannot consume version 3, stop the cutover or rerun checks through a supported producer.
Do not silently downgrade evidence to preserve a success result.

## Acceptance Criteria

1. Both report formats have one documented contract and one owning format-specific validator.
2. Given omitted or duplicate expected criteria, acceptance refuses to publish a successful report.
3. Given omitted or duplicate expected checks, neither writer publishes a successful report.
4. Given a command that violates its gate's success predicate, times out, is interrupted, or never
   starts, its evidence cannot support PASS.
5. Given a command that completes, the report records its measured exit status and output reference.
6. Given a criterion supported by code inspection, the report identifies the checked code revision
   and evidence without requiring a new command solely to populate the report.
7. Given contradictory verdicts, counts, or result statuses, validation refuses the report.
8. Given missing or changed referenced evidence, automatic acceptance and result reuse refuse it.
9. Given a report for another bead, commit, or pending invocation, Stop applies no success label.
10. Given an uncommitted tree, the report remains inspectable but cannot certify automatic success
    for a later commit through path membership alone.
11. Given a bead-free manual run, the report is retained and no bead receives a label.
12. Given a required browser journey without current passing evidence, acceptance remains
    INCONCLUSIVE and applies no accepted label. Mobile verification remains incomplete until its
    existing provider work is available.
13. Given a valid report containing mechanical failures, reconcile selects findings using its
    existing scope and BLOCKED reason rules and never writes a new passing report itself.
14. Given a missing or unreadable report, pre-push warns and allows under ADR 0004.
    A recorded FAIL continues to refuse the push under the existing policy.
15. Given a refused write or interrupted publication, the prior completed report remains intact.
    A later reader never consumes half-written JSON.
16. Given a linked worktree, writers and consumers use its own git directory and matching evidence.
17. Given a version 2 report during reader preparation, its documented legacy behavior remains
    available. It is never upgraded by filling missing evidence with guessed values.
18. Given version 3 output from TADW, Outrigger's supported reader makes the expected success,
    failure, incomplete, and invalid-report decisions in compatibility fixtures.
19. Given an installed portable hook missing a validator dependency, installer `--check` fails
    and reports the missing dependency before producer cutover.
20. Given uppercase hexadecimal commit input, both writers normalize it before identity checks.

**Coverage:** criteria 1-8 cover report contracts, completeness, and evidence.
Criteria 9-16 cover reader decisions and durable publication.
Criteria 17-20 cover compatibility and installation.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Older Outrigger readers require version 2 | High | High | Release and test companion readers before producer cutover |
| Portable hooks miss their validator dependencies | High | Medium | Install dependencies together and extend installer checks |
| A schema-valid report contains unsupported claims | High | Medium | Require captured execution results or named observation evidence |
| Arbitrary Markdown cannot be divided reliably into criteria | Medium | Medium | Preserve authoritative text and report ambiguous input as inconclusive |
| Stricter freshness breaks the existing dirty-report repair convenience | Medium | High | Make the changed automatic-success rule explicit and retain manual inspection |
| New fields drift between separate readers | High | Medium | Give each format one validator and use common fixtures across consumers |
| UI reporting work expands this release | Medium | High | Reuse existing beads and leave unavailable device checks incomplete |
| A general reporting framework grows beyond this request | Medium | Medium | Keep two formats and reuse the existing executor |

## Dependencies

Outrigger needs a companion change for version 3 acceptance verification and QA report enforcement.
Its inline acceptance report strengthening remains separate work in Outrigger.
The existing TADW implementation records and their actual prerequisites are assessed below.

## Existing Bead Plan Assessment

### Review boundary

This assessment uses the live TADW tracker snapshot read on 2026-10-11.
The inventory command was `bd list --all --limit 0 --json`.
All non-closed records were screened by title and native fields for report, reader, and execution work.
Relevant designs, criteria, notes, and dependency edges were then read in full.
Related closed records were compared with TADW main at `baf6b1f`.

This is an overlap and sequencing assessment for validation reports.
It does not grade every backlog bead's writing or certify every closed bead's implementation.
Implementation bead fields, statuses, and dependencies remain unchanged by this planning task.

### Planned and completed work

| Existing work | Current state | Relationship | Recommended treatment |
|---|---|---|---|
| `tadw-6qd`, `tadw-gky`, `tadw-s6d`, `tadw-bhi` | Closed; version 2 writers and skill calls exist | Field validation, counts, bounded evidence, and atomic writing are already delivered | Extend these writers; create no replacement-writer tasks |
| `tadw-gni`, `tadw-1v7`, `tadw-568` | Closed; reconcile readers and skills exist | Report-file handoff and independent regrading are already delivered | Preserve both loaders and their machine results |
| `tadw-6xhi` | Closed; `skills/verify-app/scripts/journeys.py` exists | Journey coverage and content fingerprints already exist | Reuse its output rather than computing another fingerprint |
| `tadw-imgg` | Open | Owns durable per-journey verification results | Keep this owner; let acceptance cite its separate report |
| `tadw-do7x` | Open; depends on `tadw-imgg` and closed `tadw-6xhi` | Owns deterministic UI handoff grading and counts | Retain its fixed grading table; reconcile its version 2 choice before cutover |
| `tadw-440` | Open; depends on `tadw-do7x`, `tadw-imgg`, `tadw-qby`, and closed foundation beads | Owns routing and the INCONCLUSIVE verdict for unfinished UI work | Reuse this work; resolve its mobile prerequisite before promising an independent web release |
| `tadw-qby` | Open; depends on `tadw-imgg` and closed `tadw-7q8` | Owns the iOS verification provider | Keep outside this report implementation; mobile work remains incomplete until available |
| `tadw-v6k` | Open; its writer prerequisite is closed | Owns acceptance reuse of saved QA results | Amend its HEAD-only reuse criteria to require matching validated evidence |
| `tadw-2yg` | Open | Owns lowercase commit normalization in both writers | Reuse this bead; do not duplicate the normalization change |
| `tadw-ch3` | Deferred; its description records the owner's resolution | Bead-free reports are allowed | Preserve the resolution; do not reopen the policy question |
| `tadw-5697` under `tadw-2s5s` | Open; blocked by open `tadw-n4xs` | Owns moving Stop parsing into Python | Coordinate contract integration with this owner; do not build a competing Stop parser |
| `tadw-7raw`, `tadw-n8xh` | Closed; executor and declared-input reuse exist | Execution and caching machinery are already delivered | Add an evidence adapter; keep capture reuse disabled initially |
| `tadw-acf` | Open | Owns saving the changed set once for QA routing | Reuse its scope capture in expected-input preparation |
| `tadw-1suy` | Open; notes say two original findings were already addressed | Owns unresolved QA status mappings | Re-ground its remaining cases before encoding verdict fixtures |
| `tadw-8gl`, `tadw-fdq` | Open | Own live CLI probing and API server identity | Preserve their ownership; consume their evidence when delivered |
| `tadw-ac4`, `tadw-l8f`, `tadw-j80`, `tadw-dhdg` | Open | Own installer selection, Codex checks, enforcement, and documentation | Coordinate dependency installation and checks with these changes |
| `tadw-tyh` | Open; distribution choice is unresolved | Proposes replacing copied hooks or enforcing their freshness | Do not make the report contract depend on a new distribution model |
| `tadw-vpzt`, `tadw-sbaq` | Open | Own ship reuse declarations and environment policy | Keep ship policy separate; reuse the executor without changing these decisions |

The source evidence is in both report writers' validation functions, both reconcile loaders,
`skills/verify-app/scripts/journeys.py`, and `skills/ship/scripts/run_checks.py`.
The closed bead records explain ownership; these existing files establish the current foundation.

### Conflicts and required resolutions

| Conflict | Evidence | Resolution proposed for plan review |
|---|---|---|
| UI acceptance remains version 2 in the existing plan; this draft recommends version 3 | `tadw-do7x` design; [verification-loop plan](feature-plan-verification-loop.md), Data Model; Outrigger's `acceptanceReportVersion = 2` | Choose an additive version 2 UI fix first, or amend that plan and bead for the coordinated version 3 release |
| ADR 0011 currently specifies version 2 readers | [ADR 0011](../adr/0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md), Consequences; both loaders' `REPORT_VERSION = 2` | Record a narrow version amendment in the new ADR before producer cutover |
| QA reuse currently requires only matching HEAD | `tadw-v6k` design and criterion 1 | Require validated scope and evidence; rerun when inputs, tools, environment, or artifacts cannot be verified |
| An unavailable UI check must not enter mechanical repair as a failed criterion | `tadw-440` requires HANDOFF to mean INCONCLUSIVE; `tadw-do7x` supplies its count | Preserve HANDOFF and INCONCLUSIVE in version 3; never map unfinished UI work to a repairable failure |
| The existing routing bead waits for iOS, while this draft allows a web release first | `tadw-440` has a blocking edge to `tadw-qby` | Approve a web/mobile split in the existing work, or retain that prerequisite and delay routing integration |
| Stop parsing has a pending Python migration | `tadw-5697` and its `tadw-n4xs` prerequisite | Integrate the report rules through that migration, or explicitly sequence a temporary adapter without duplicating the refactor |
| Existing plans use different freshness rules | Verification-loop plan uses journey fingerprints; reconcile loaders require matching HEAD; ship compares declared inputs | Keep the report's identity check distinct from a supporting artifact's content check |
| Some old plans describe a superseded orchestration shape | `tadw-y6h` identifies the stale four-lane plan; ADR 0002 and the current orchestrator define three lanes | Ground expected-check generation in the current skill and ADR, and leave the old plan correction with `tadw-y6h` |

A journey result may retain an older informational `head` when its required content fingerprint
still matches. The acceptance report that cites it must describe the current committed work.
This preserves the existing journey reuse design while preventing path-only reuse of a dirty
acceptance report.

Captured process facts do not decide every gate's status. A CLI probe may expect a nonzero exit,
and interpreted lint results may distinguish warnings from errors.
Apply each gate's documented success predicate to measured facts.
Resolve the remaining `tadw-1suy` mappings before making those mappings contract fixtures.

The implementation milestone that changes Stop must account for the open `tadw-n4xs` prerequisite.
The implementation milestone that integrates routing must account for the open `tadw-qby` prerequisite.
Neither dependency may disappear merely because this draft calls that work an integration point.

### New work after reconciliation

The reviewed inventory does not contain a dedicated bead for the following report-contract gaps:

- A complete expected-criteria and expected-check contract for both report formats.
- Captured command evidence connected to report results through the existing executor.
- One validator per format used consistently by producers and consumers.
- Invocation identity, evidence existence, and evidence digest checks for automatic success.
- Coordinated version 3 compatibility fixtures and the Outrigger reader release.

These gaps are candidates for new implementation beads after plan review.
Existing beads should retain their deliverables, with approved amendments for the conflicts above.
Every eventual implementation bead must map to a plan criterion and an existing owner or a named gap.

Adjacent work remains separate: `tadw-gsg` proves real browser use; `tadw-1ze` improves pre-push
fixtures; `tadw-uck` covers typed QA invocation; `tadw-vt1x` repairs Markdown formatting.
The model-based `tadw-qg-eval-verdict-rules-xub` cases remain manual measurements, outside git hooks.
Deterministic report fixtures cannot replace those measurements.

`tadw-c99` proposes a Linear input path for acceptance.
Expected-criteria capture must accept an injected source description without requiring a bead.
Adding Linear support itself stays with that existing bead.

Before decomposing this draft, approve the contract version, reconcile the affected existing
plan and bead fields, and read their dependencies again.
This assessment creates no implementation beads and changes no implementation ordering in the tracker.

## Testing Strategy

Drive writer behavior through the existing command entry points:

- `skills/quality-gates/scripts/test_write_report_json.py`
- `skills/verify-acceptance/scripts/test_write_acceptance_report.py`

Drive reader behavior through their existing harnesses:

- Both `skills/reconcile-*/scripts/test_load_findings.py` suites.
- `hooks/test-claude-scripts.sh`, selecting the copy of record through its existing override.
- `.githooks/test_prepush.py`.
- `skills/ship/scripts/test_run_checks.py` for unchanged executor guarantees.
- Outrigger `cmd/outrigger-phased/verifyacceptance_test.go` and scoped phase-loop fixtures.

Use temporary repositories and stubbed tracker commands for hook tests. Use small local commands
that succeed, fail, time out, or receive interruption for capture tests. No test needs a real model,
remote tracker, browser account, or deployment.

Add fixture cases for empty arrays, omitted inputs, extra results, mismatched identity, null bead,
uppercase hashes, malformed versions, stale artifacts, incomplete handoffs, and failed writes.
Include a same-HEAD older report from another invocation.

Register new deterministic suites through the repository's existing gate configuration.
During implementation, run scoped suites first and the repository's required gates before landing.
Document checks validate this planning artifact. The push hook also runs the repository's required
checks. This planning task does not change report behavior.

## Open Questions

- The owner should confirm version 3 and the narrow ADR 0011 amendment during plan review.
  Choose whether the existing version 2 UI fix ships first or joins the coordinated version 3 cutover.
- The owner should approve a web/mobile split of the existing routing work if web delivery must
  precede iOS. Its current dependency graph requires the iOS provider.
- The owner should confirm whether legacy dirty-report reconciliation remains a manual repair
  convenience.
  It must not certify automatic success without a proof of identical checked content.
- The owner should confirm the retention period for execution logs before production cutover.
  Referenced evidence must survive the report's useful lifetime.
- `CONTEXT.md` defines criterion, gate, and verdict but lacks validation report and execution
  evidence. Add these terms through the domain-modeling workflow during implementation.
