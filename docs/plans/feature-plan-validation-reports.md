# Feature Plan: Stronger TADW validation reports

**Date:** 2026-10-11
**Status:** Revised after plan review
**Planning bead:** tadw-28ik

## Summary

Give TADW's quality-gates and acceptance reports complete inputs, named evidence, and consistent
validation by every reader. Keep the two report formats and their current verdict policies.
Introduce version 3 through a reader-first release, coordinated with Outrigger.

The owner approved applying the review corrections on 2026-10-11. This plan selects version 3
and the narrow ADR 0011 amendment. Implementation and release remain separate work.

### Revision Notes

The 2026-10-11 plan review returned Needs Revision. The owner's instruction, "apply and re-review,"
authorizes these planning corrections:

| Prior finding | Change applied |
|---|---|
| F1, Dependencies | Select version 3; assign the ADR amendment to milestone 1; retain existing integration prerequisites |
| F2, MECE | Give current UI failures precedence over incomplete journeys; add separate observable criteria |
| F3, MECE | Define consumer behavior by version and release mode; assign strict activation and rollback to milestone 5 |
| F4, Actionability | Define invocation creation, transport, retries, concurrency, and Outrigger enforcement |
| F5, Actionability | Refuse automatic success when checked inputs change during execution, including a first run |
| F6, Feasibility | Correct the QA loader's dirty-report exception; preserve it only for manual repair |

## Motivation

A developer needs to know which checks ran, which criteria were graded, and which files they
describe. An autonomous caller needs the same information before advancing to the next phase.

TADW's version 2 writers already validate fields, reject inconsistent results, cap evidence,
and replace reports atomically. The remaining work concerns complete coverage, evidence, and
consistent reader decisions.

Grounding used TADW main at `baf6b1fb8d65a4819c7dbe7f574f528ae47dac34`, Outrigger at
`e7ca3e0`, and the local Gas City reference at `f9a0b0d`.
The re-review checked the changed claims against TADW main at `9165ff5`.

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
| `scripts/validation_invocation.py` | Create and finish invocation records; enforce one active invocation per report kind and worktree | New |
| `skills/ship/scripts/run_checks.py` | Supply execution results without adopting ship's policy | Existing |
| Both `skills/reconcile-*/scripts/load_findings.py` readers | Validate the report before selecting findings | Modified |
| `scripts/label_bead_on_skill_invocation.sh` | Validate a matching completed report before labeling | Modified |
| `scripts/install_label_bead_on_skill_invocation.sh` | Install and check the validator dependencies with the hook | Modified |
| `.githooks/pre-push` | Validate report structure while preserving its warning policy | Modified |
| Both check skills' `SKILL.md` files | Specify input capture, evidence, and failure behavior | Modified |
| `AGENTS.md` and `.tadw/ship-gates.json` | Register the implementation's deterministic checks | Modified |
| Outrigger `cmd/outrigger-phased/verifyacceptance.go` | Read the new acceptance contract | External companion change |
| Outrigger `cmd/outrigger-phased/verify.go` and `cmd/outrigger-phased/main.go` | Accept independently supplied invocation identity and minimum version; add QA report verification | External companion changes |
| Outrigger `lib/phased_loop.sh`, `prompts/qa.md`, and `prompts/acceptance_tadw.md` | Create attempt identity, pass it to TADW, and verify reports before recording phase success | External companion changes |

Portable hooks must carry their validator dependencies. They must not search several installed
plugin copies and silently select whichever appears first. The installer and its `--check`
operation must cover every dependency.
Give the installed validators distinct module names so one format cannot load the other's rules.

The two contract modules contain report rules, not git or tracker discovery. Their callers inject
the current commit, bead, and expected inputs. Reuse the current pattern of loading helpers from a
known path within the installed component.
The invocation helper also receives its git directory, HEAD, bead, and expected inputs from its caller.
New helpers run neither `git` nor `bd`, preserving ADR 0011's injected-input rule.

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
| `run_id` | Identify one invocation; consumers compare it with independently retained invocation context |
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
Keep referenced evidence while either latest completed report cites it. Automatic evidence deletion
is outside this release; an explicit cleanup must preserve those references.

### Invocation Lifecycle

Use a random UUID for each invocation. Store its descriptor and evidence under
`<git-dir>/validation-runs/<run_id>/`. These are proposed runtime paths.
The descriptor records report kind, bead or null, starting HEAD, expected inputs, and consumer mode.
The expected inputs become fixed before execution or grading begins.

Outrigger creates the ID before each cold Claude attempt. It retains the expected ID outside the
transcript and passes `--run-id <id>` in the TADW skill invocation.
Its verifier receives that retained value through a new `--run-id` option and `VerifyOptions` field.
It never obtains its expected ID from the completed report.

The TADW hook adopts a supplied ID or creates one for a direct skill invocation.
The proposed invocation helper creates the descriptor and records its ID in any pending Stop marker.
The skill reads that descriptor and passes its path to the writer through a new `--invocation` option.
This file handoff works across processes; it does not depend on a child hook changing parent variables.
The installer carries the helper and checks it with the validators.

Without a hook, the skill calls the same helper before grading. A bead-free invocation records
`bead: null` and produces a report without a success label. It needs no pending label marker.
Direct writer calls must also supply an invocation descriptor to request version 3.

Each worktree permits one active invocation per report kind. The helper claims it atomically.
A competing invocation stops before grading and cannot replace the active descriptor or report.
Different worktrees use separate git directories. QA and acceptance have separate active claims.
Duplicate preparation for the same ID is idempotent and cannot change fixed inputs.

A retry after failure, interruption, or a new cold Claude call gets a new ID.
An interrupted invocation must be explicitly abandoned before a replacement claims its report kind.
Outrigger abandons its own interrupted ID after the cold process ends, before preparing a retry.
The helper refuses abandonment of another live caller's claim. A manual caller can abandon its own
ended invocation through the same helper; it never needs to remove another caller's files.
Only continuation of the same live invocation keeps its ID. Reports from earlier attempts remain
inspectable but cannot satisfy the new attempt, even when HEAD has not changed.
The writer checks the active ID before atomic publication. Stop retires its marker after consuming
the matching result; marker-free callers finish through the helper after consuming the result.
The invocation claim remains active until that consumer finishes, preventing replacement before reading.

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
The adapter measures checked inputs before and after execution even when executor reuse is disabled.
Capture the complete declared scope before grading and check it again before report publication.
Measure command, tool, and declared environment identity with the checked file contents.
Changed or unreadable inputs make the current attempt incomplete and prevent automatic success or reuse.
Keep the process facts, including a successful exit, but mark the affected evidence unverified.
An affected check that would otherwise pass becomes HANDOFF; actual failures retain their failure status.
This rule applies to the first run as well as cached results.
The existing executor only suppresses cache saving after input changes.
The adapter owns this stronger rule.

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

Required UI results use the following precedence. Only evidence with the current journey fingerprint
counts as a current result. Other criteria and gates still contribute to the overall acceptance verdict.

| Required UI evidence | UI gate result | Overall acceptance consequence |
|---|---|---|
| Any current `VERIFY_FAIL`, including when another journey is unfinished | FAIL | NOT ACCEPTED |
| No current failure; at least one missing, stale, blocked, or uncovered journey | HANDOFF | INCONCLUSIVE unless another criterion or gate fails |
| Complete coverage and every required journey has current `VERIFY_PASS` | PASS | Eligible for ACCEPTED if all other requirements pass |

### Version Enforcement and Rollback

The reader preparation release understands versions 2 and 3. Its automatic-success minimum is 2.
The strict release changes the consumer-owned minimum to 3, independently of the report's fields.
This is a reader policy change as well as a producer default change.
No field in a report can lower the consumer's minimum.

| Consumer | Preparation, version 2 | Preparation, version 3 | Strict release, version 2 | Strict release, version 3 |
|---|---|---|---|---|
| Stop | Existing labeling behavior | Validate evidence and matching invocation | No success label; request a fresh version 3 run | Full validation and invocation match before labeling |
| Acceptance reuse | Existing reuse policy | Validate matching inputs and evidence | Rerun or record incomplete; no successful reuse | Reuse only matching validated evidence |
| Outrigger in TADW report mode | Existing acceptance behavior; prepare QA verifier without enforcement | Exercise independent acceptance and QA checks in compatibility fixtures | Refuse automatic phase success | Verify identity, evidence, and conclusion before advancement |
| Reconcile | Existing manual repair behavior | Validate before selecting findings | Allow legacy manual repair only; never certify success | Validate before selecting findings; never certify success |
| Pre-push | Existing warning and recorded-FAIL policy | Validate; preserve warning and recorded-FAIL policy | Warn on unsupported success evidence; recorded FAIL still refuses | Validate; preserve warning and recorded-FAIL policy |

Milestone 5 activates minimum version 3 in TADW's automatic consumers and Outrigger's TADW report mode.
The strict installed readers default to 3. Callers may raise that minimum but cannot lower it.
Installer checks must confirm this reader revision, its helper dependencies, and its strict minimum.
Outrigger must verify the compatible installed producer and readers before entering strict mode.

Outrigger's companion change adds a QA report check at the phase outcome checkpoint.
Adding an unused Go verifier alone does not satisfy this requirement.
Enable it only when QA is configured to use TADW quality-gates; preserve other QA tools' contracts.
Its inline acceptance mode also retains its separate contract.
Use a proposed Outrigger configuration key, `qa_report_contract=tadw`, to select that capability
before the cold call. Its default is unset; an arbitrary QA tool phrase does not enable this mode.
The existing `acceptance_gate=tadw` selects acceptance report enforcement.
Both modes pass the expected ID and strict minimum into the verifier independently of report contents.

Rollback retains strict readers and minimum version 3. Reverting a producer to version 2 pauses
automatic success until a compatible producer is restored and checks run again.
An unsupported reader prevents cutover. A rollback never silently restores version 2 success.

Legacy QA reconciliation has a dirty-report exception: the supplied ancestor's moved paths must be
a subset of the report's changed files. Acceptance reconciliation instead requires matching HEAD.
Preserve that QA exception for manual repair only. Neither path membership nor a reconcile result
can certify automatic success; a fresh independent grade remains required.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| [0001](../adr/0001-native-tracker-fields-are-canonical.md) | Native tracker fields own acceptance criteria | Capture the native acceptance input before grading |
| [0002](../adr/0002-the-quality-gates-orchestrator-fans-out-to-blocking-subagents.md) | The orchestrator collects blocking lanes and owns the result | Require every planned result without changing dispatch ownership |
| [0003](../adr/0003-a-push-to-main-is-already-published.md) | Main reaches plugin consumers immediately | Publish compatible readers before new reports become the default |
| [0004](../adr/0004-the-pre-push-hook-forgives-by-design.md) | Missing evidence warns rather than blocking push | Keep warning and refusal policy separate from report validation |
| [0011](../adr/0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md) | Findings travel in one report; the fixer never grades its fix | Keep one completed report, two loaders, and independent regrading |
| [0012](../adr/0012-ship-gates-the-code-tree-and-carries-the-close.md) | Ship checks the exact code tree under its own contract | Reuse execution machinery without replacing ship's evidence or tree rules |

The owner selected version 3 when authorizing these review corrections on 2026-10-11.
Milestone 1 records the narrow ADR 0011 amendment before reader implementation begins.
The amendment changes version-specific refusal rules and records the existing manual QA exception.
It preserves findings ownership, injected inputs, and independent regrading.
It also records the consumer minimum, legacy manual repair allowance, and rollback behavior.
Existing UI reporting work joins this coordinated version 3 release; a separate version 2 UI release
is not part of this plan. Reconcile the affected existing designs during decomposition.

## Implementation Milestones

Each milestone must be split into normal-sized beads after plan review.

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Contract and fixtures | Define version 3 inputs, invocation protocol, evidence, UI precedence, and migration policy | M | Valid and invalid fixtures cover every report rule; the new ADR records the selected transition |
| 2 | Compatible readers | Add validators and invocation plumbing to loaders and portable hooks; prepare Outrigger's companion readers | L | Preparation behavior matches the version matrix; invocation transport and installer dependency checks pass |
| 3 | Acceptance evidence | Validate the complete criteria list and gate evidence; integrate the existing UI reporting work | L | UI failure and handoff precedence match fixtures; incomplete criteria or evidence cannot earn accepted |
| 4 | Quality-gates evidence | Capture command facts and stable checked inputs; account for every expected check | L | Missing lanes, interrupted commands, changed inputs, and contradictory results cannot produce PASS |
| 5 | Strict cutover and rollback | Activate consumer minimum 3 and version 3 producers after installation and companion checks | M | Cross-process QA, acceptance, failure, repair, and rollback fixtures match the strict version matrix |
| 6 | Documentation and release checks | Finish user instructions and release checks | M | Documented commands and registered checks match every shipped interface |

Release order is 1, then 2, then 3, then 4, then 5 and 6.
Acceptance and quality-gates producer changes can be prepared independently after their readers exist.
Map each milestone onto the existing beads in the assessment below before creating new implementation
beads. The milestones describe delivery order, not six additional tasks.

Each implementation milestone registers its deterministic checks before shipping its changes.
Milestone 6 verifies the complete registration and release documentation rather than deferring gates.

Version 2 reports are legacy evidence during migration. Never convert them into version 3 by
inventing missing inputs or execution facts. Use the version enforcement matrix throughout migration.
Milestone 5 changes both producer defaults and consumer minimums.

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
12. Given any required journey with current `VERIFY_FAIL`, its UI gate is FAIL and acceptance is
    NOT ACCEPTED, even when another journey is incomplete.
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
21. Given no current UI failures and a missing, stale, blocked, or uncovered required journey,
    its UI gate is HANDOFF. Acceptance is INCONCLUSIVE unless another requirement fails.
    Unavailable required mobile verification follows this rule.
22. Given complete UI coverage and current `VERIFY_PASS` for every required journey, its UI gate
    is PASS. Acceptance is eligible for ACCEPTED only if every other requirement passes.
23. Given version 2 success evidence after strict cutover, Stop applies no success label,
    acceptance refuses successful reuse, and Outrigger refuses TADW phase advancement.
    A producer rollback retains these refusals.
24. Given a cold-call retry at unchanged HEAD, the caller creates a new ID and refuses the earlier
    report. The supplied ID survives hook, skill, writer, and independent verifier processes.
25. Given competing same-kind invocations in one worktree, only the active claimant can grade
    and publish. Another worktree can proceed with independent identity and evidence.
26. Given a checked file or declared command input that changes during execution, the current
    report cannot support automatic success or reuse, even on the first run with reuse disabled.
27. Given legacy dirty QA evidence satisfying the existing ancestor and path-subset exception,
    manual reconcile can select findings. That evidence cannot establish automatic success.
28. Given Outrigger using TADW QA in strict mode, its outcome checkpoint validates the matching
    report before recording QA success. Other QA tools and inline acceptance retain their contracts.

**Coverage:** criteria 1-8 cover report contracts, completeness, and evidence.
Criteria 9-16 cover reader decisions and durable publication.
Criteria 17-20 cover compatibility and installation.
Criteria 21-22 cover UI precedence. Criteria 23-28 cover strict enforcement, invocation lifecycle,
checked-input stability, legacy repair, and the external QA checkpoint.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Older Outrigger readers require version 2 | High | High | Release and test companion readers before producer cutover |
| Portable hooks miss their validator dependencies | High | Medium | Install dependencies together and extend installer checks |
| A schema-valid report contains unsupported claims | High | Medium | Require captured execution results or named observation evidence |
| Arbitrary Markdown cannot be divided reliably into criteria | Medium | Medium | Preserve authoritative text and report ambiguous input as inconclusive |
| Stricter freshness breaks the existing dirty-report repair convenience | Medium | High | Preserve the QA exception for manual repair; require a fresh grade for automatic success |
| New fields drift between separate readers | High | Medium | Give each format one validator and use common fixtures across consumers |
| UI reporting work expands this release | Medium | High | Reuse existing beads and leave unavailable device checks incomplete |
| An interrupted invocation leaves an active claim | Medium | Medium | Make caller-owned abandonment explicit and test retry cleanup without replacing another live claim |
| A general reporting framework grows beyond this request | Medium | Medium | Keep two formats and reuse the existing executor |

## Dependencies

Outrigger needs a companion change for version 3 acceptance verification and QA report enforcement.
Its inline acceptance report strengthening remains separate work in Outrigger.
The existing TADW implementation records and their actual prerequisites are assessed below.
Milestone 1 can start with the selected contract direction. Milestone 2's Stop integration waits
for `tadw-n4xs` and `tadw-5697`; milestone 3's routing integration retains `tadw-qby` through `tadw-440`.
This plan does not authorize a web/mobile split. Milestone 5 waits for installed compatible TADW
readers and producers plus the Outrigger companion checks.

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

| Conflict | Evidence | Selected resolution or integration hold |
|---|---|---|
| UI acceptance remains version 2 in the existing plan; this plan selects version 3 | `tadw-do7x` design; [verification-loop plan](feature-plan-verification-loop.md), Data Model; Outrigger's `acceptanceReportVersion = 2` | Amend the existing plan and bead during decomposition for the coordinated version 3 release |
| ADR 0011 currently specifies version 2 readers | [ADR 0011](../adr/0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md), Consequences; both loaders' `REPORT_VERSION = 2` | Record the narrow amendment in milestone 1 before reader implementation |
| QA reuse currently requires only matching HEAD | `tadw-v6k` design and criterion 1 | Require validated scope and evidence; rerun when inputs, tools, environment, or artifacts cannot be verified |
| An unavailable UI check must not enter mechanical repair as a failed criterion | `tadw-440` requires HANDOFF to mean INCONCLUSIVE; `tadw-do7x` supplies its count | Preserve HANDOFF and INCONCLUSIVE in version 3; never map unfinished UI work to a repairable failure |
| The existing routing bead waits for iOS | `tadw-440` has a blocking edge to `tadw-qby` | Retain that prerequisite and delay routing integration until the provider is available |
| Stop parsing has a pending Python migration | `tadw-5697` and its `tadw-n4xs` prerequisite | Wait for the migration, then integrate the report rules through that owner |
| Existing plans use different freshness rules | Journey results use fingerprints; acceptance reconcile requires matching HEAD; QA reconcile also allows a dirty ancestor with moved paths inside the changed set; ship compares declared inputs | Preserve the QA exception for manual repair; require stable checked inputs and current committed identity for automatic success |
| Some old plans describe a superseded orchestration shape | `tadw-y6h` identifies the stale four-lane plan; ADR 0002 and the current orchestrator define three lanes | Ground expected-check generation in the current skill and ADR, and leave the old plan correction with `tadw-y6h` |

A journey result may retain an older informational `head` when its required content fingerprint
still matches. The acceptance report that cites it must describe the current committed work.
This preserves the existing journey reuse design while preventing path-only reuse of a dirty
acceptance report.

Captured process facts do not decide every gate's status. A CLI probe may expect a nonzero exit,
and interpreted lint results may distinguish warnings from errors.
Apply each gate's documented success predicate to measured facts.
Resolve the remaining `tadw-1suy` mappings before making those mappings contract fixtures.
Milestone 1 owns resolving those mappings for the contract; implementation stays with the existing bead.

The implementation milestone that changes Stop must account for the open `tadw-n4xs` prerequisite.
The implementation milestone that integrates routing must account for the open `tadw-qby` prerequisite.
Neither dependency may disappear merely because this draft calls that work an integration point.
The Stop migration beads still name the old `label_bead_hook.py` module.
The current installer copies `scripts/claim_bead_for_build.py` and removes the old module.
Re-ground those migration beads against the current installer before starting their implementation.

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

During decomposition, reconcile the affected existing plan and bead fields with the selected version
3 direction, and read their dependencies again.
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
Exercise the complete version matrix, including version 2 success after strict cutover and producer
rollback. Include manual legacy QA repair without automatic success.
Exercise a current UI failure together with an incomplete journey, incomplete-only journeys,
and complete current UI passes.
Run a local command that changes its declared input while executing with reuse disabled.
Also change an input after its command finishes but before final report publication.
Exercise ID creation, explicit ID adoption, cross-process handoff, competing claims, interruption,
explicit abandonment, and a retry at unchanged HEAD.
Outrigger fixtures must reach the actual QA outcome checkpoint and cover a non-TADW QA tool.

Register new deterministic suites through the repository's existing gate configuration.
During implementation, run scoped suites first and the repository's required gates before landing.
Document checks validate this planning artifact. The push hook also runs the repository's required
checks. This planning task does not change report behavior.

## Open Questions

- No owner decision blocks milestone 1. Version 3, the narrow ADR amendment, manual legacy QA
  repair, and the existing mobile prerequisite are settled above.
- The owner may later request a separate web release. That request would require an explicit
  amendment to `tadw-440` and its mobile dependency before routing integration.
- A later cleanup policy may set retention periods. This release retains evidence cited by either
  latest completed report and adds no automatic deletion.
- `CONTEXT.md` defines criterion, gate, and verdict but lacks validation report and execution
  evidence. Add these terms through the domain-modeling workflow during implementation.
