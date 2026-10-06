# Feature Plan: The Verification Loop

**Date:** 2026-08-31
**Revised:** 2026-10-05, to reflect the browser verifier and journey helper now in the repository
**Status:** In Progress

## Summary

This plugin now drives browser journeys with `verify-app` and maps changed files to journeys with
`journeys.py`. This plan connects those tools to QA and acceptance, saves results, and adds an iOS
verifier.

## Motivation

The browser verifier and journey helper exist, but the QA and acceptance pipeline does not use
their results yet.

**A browser or mobile UI change still leaves a QA handoff.**
`skills/quality-gates/scripts/route_qa.py` routes browser changes to `agent-browser` and mobile
changes to `agent-device`. Each handoff leaves the quality-gates run INCOMPLETE, even when a
separate verification later passes.

**Acceptance does not include a UI verification result.**
`skills/verify-acceptance/SKILL.md` runs Tests, Lint and Format, and Type Checking. Its report has no
field for a browser or mobile handoff, so those results cannot affect its verdict.

**The diagnostician cannot reproduce a browser bug.**
`agents/diagnostician.md` has no browser tool, so it cannot open the application during an
investigation.

`verify-app` drives browser journeys, but it does not save results for later runs. The repository
has no `verify-app-ios` skill yet.

The people running Pipeline B need QA and acceptance to consume the browser and mobile results.

## Scope

### Existing Foundation

- `verify-app` provides a browser skill, agent, command, and control template.
- `skills/product-surface-docs/scripts/check_drive_blocks.py` checks feature drive blocks.
- `skills/verify-app/scripts/journeys.py` matches changed files to journeys and fingerprints their
  source files.

### Remaining In Scope

- Add `verify-app-ios` for journeys in the iOS Simulator, driven by `agent-device`.
- Save each verification result and its journey fingerprint in `<git-dir>/verify-app-report.json`.
- Route browser and mobile UI handoffs to `tadw:verify-app` and `tadw:verify-app-ios`.
- Make acceptance read the needed journeys and saved results, then report unresolved handoffs as
  INCONCLUSIVE.
- Give the diagnostician browser tools and a step for reproducing browser bugs.
- Add an eval case that measures whether `verify-app` loads for a relevant request.

### Out of Scope

- The full skill invocation eval battery. [Section 11 of the eval guide](../eval-driven-development.html)
  specifies it. It is a different subject, so it stays outside this plan.
- Any change to `ux-review` or `ux-review-ios`. They audit design, and this plan does not touch that
  job.
- Deleting `/qa` and `/ios-qa` from a user's setup. This plan stops pointing at them. It does not
  stop anyone from running them.
- A test application committed to this repository and driven on every push. The live seam is one
  recorded run, not an automated one.
- Any cloud agent, automatic bug reproduction from an inbox, or automatic merge.

## Technical Approach

### Target Architecture

`verify-app` is its own skill, and `quality-gates` names it as the owner of a handoff. That keeps
each skill to one job, and it removes the outside tools from the middle of pipeline B.

```text
/build -> /fresh-eyes-cr -> /quality-gates -> /verify-acceptance -> /tadw:ship
                                  |
                                  +-- HANDOFF browser-ui -> tadw:verify-app
                                  +-- HANDOFF mobile-ui  -> tadw:verify-app-ios
```

**A check never runs another check.** `quality-gates` writes the HANDOFF row and stops. The caller,
a person or outrigger, runs `/verify-app`. This is rule 3 of ADR 0011.

**A result travels in a report file, never in a transcript.** `verify-app` writes
`<git-dir>/verify-app-report.json`, and `verify-acceptance` reads it. A transcript does not cross
outrigger's `claude -p` process boundary, and ADR 0011 rejected it for that reason.

**A script grades the handoff, not the model.** `verify-acceptance` runs `route_qa.py` and
`journeys.py` on its changed set. Then it passes both outputs and the `verify-app` report file to
`write_acceptance_report.py`. The writer builds each handoff row from one fixed table:

| What the report file holds | Handoff row |
|---|---|
| `VERIFY_PASS` with the current fingerprint, for every needed journey | PASS |
| `VERIFY_FAIL` with the current fingerprint, for any needed journey | FAIL |
| Anything else: no result, an old fingerprint, STALE, BLOCKED, or a changed file no journey covers | HANDOFF |

A HANDOFF row makes the verdict INCONCLUSIVE, never NOT ACCEPTED. A check nobody ran proves nothing
either way, which is the case an UNVERIFIABLE criterion already covers
(`skills/verify-acceptance/SKILL.md:338`). NOT ACCEPTED would send the work to
`reconcile-acceptance`, which fixes FAIL rows and would find none.

**A saved pass is reused by fingerprint, never by commit.** `verify-acceptance` runs `/verify-app`
only for a needed journey whose saved result is missing or carries an old fingerprint.
`docs/ship-gate-contract.md` sets the same rule for ship: "A commit hash is never compared."

`verify-app` reads two documents before it drives anything.

```text
docs/verification/control.md          how to launch, how to sign in, which browser tool
docs/products/<surface>/<leaf>.md     ## How to drive this, one block per feature
```

The split copies a shape that already works. `ll:verify-commons` holds the environment, the
authentication, and the reporting rules for every LoanLabs verification, and each `ll:verify-*`
skill holds one journey. Here the plugin holds the technique, `docs/verification/control.md` holds
what every journey in one project shares, and each leaf document holds one feature's route and
selectors.

Putting the per-feature half in `docs/products/` reuses three things that exist: the tree, the
frontmatter schema in `skills/product-surface-docs/references/frontmatter-schema.md`, and the
staleness checker `skills/product-surface-docs/scripts/check_staleness.py`. A separate map of the
same product would need its own copy of all three.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `skills/verify-app/SKILL.md` | Drive a web application and report PASS or FAIL | New |
| `skills/verify-app/references/control-template.md` | The template a project copies to `docs/verification/control.md` | New |
| `skills/verify-app-ios/SKILL.md` | The same job in the iOS Simulator | New |
| `agents/verify-app.md` | Run a verification in its own context window | New |
| `commands/verify-app.md` | Read the skill, take a journey name or a diff | New |
| `skills/product-surface-docs/SKILL.md` | Add **How to drive this** to the leaf template | Modified |
| `skills/product-surface-docs/scripts/check_drive_blocks.py` | Report which leaf documents carry no drive block | New |
| `skills/product-surface-docs/scripts/test_check_drive_blocks.py` | Regression suite for that checker | New |
| `skills/verify-app/scripts/journeys.py` | Name the journeys a changed set needs, and fingerprint each one | New |
| `skills/verify-app/scripts/write_verify_report.py` | Write one result per journey to `<git-dir>/verify-app-report.json` | New |
| `skills/quality-gates/scripts/route_qa.py` | Name the new skills as the two handoff owners | Modified |
| `skills/quality-gates/SKILL.md` | Point the two handoff rows at the new skills | Modified |
| `skills/verify-acceptance/scripts/write_acceptance_report.py` | Grade each handoff from the fixed table, and count `gates_handoff` | Modified |
| `skills/reconcile-acceptance/scripts/load_findings.py` | Read a HANDOFF row and the `gates_handoff` count | Modified |
| `scripts/label_bead_on_skill_invocation.sh` | Refuse `accepted` when `gates_handoff` is above zero | Modified |
| `skills/verify-acceptance/SKILL.md` | Route the change, pass the paths, and grade an unresolved HANDOFF as INCONCLUSIVE | Modified |
| `agents/diagnostician.md` | Add the browser tools and a reproduction step | Modified |
| `evals/cases/verify-app-loads/case.json` | Measure whether the skill loads on a realistic request | New |
| `CLAUDE.md`, `README.md`, `docs/ROUTING.md` | Register the new components and the new checks | Modified |

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| The pre-push check list in `CLAUDE.md` | Existing, extended | Every new file parses, every path it names exists, and every leaf document carries a drive block |
| `evals/run.py` with one invocation case | Existing, extended | `verify-app` loads when a person asks whether a change works |
| One recorded run against a running application | New | The skill drives a real application and returns a verdict, rather than describing how to |

Three seams, because each proves something the other two cannot. The check list proves structure
and never runs a model. The eval proves the document loads, which is the failure this repository
has shipped twice, recorded in `docs/eval-driven-development.html` section 1. The recorded run
proves the technique works, and no cheaper seam can prove that.

The live seam stays a recorded run rather than an automated one. Automating it means committing a
test application to a repository of prompt assets, and maintaining a second application to test the
first.

### Data Model

Two documents gain a required shape, and two report files change.

`docs/verification/control.md` holds six fields. A project fills them once.

| Field | Holds |
|---|---|
| `launch` | The command that starts the application, and the port it answers on |
| `ready_check` | A command that returns 0 once the application answers, for the polling loop |
| `base_url` | The address to drive, on this machine |
| `auth` | How to reach a signed-in session without clicking through a signup form |
| `browser` | The `agent-browser` command-line tool, the prefix for its session name, and its flags |
| `teardown` | What to clean up, or a plain statement that nothing needs cleaning |

Each leaf document under `docs/products/` gains a **How to drive this** section with five lines.

| Line | Holds |
|---|---|
| Route | The path to navigate to, relative to `base_url` |
| Precondition | The state that must exist first, such as a signed-in lender |
| Selector | The stable identifier to bind to, such as a test id or an accessibility role |
| Action | The steps a person takes on this screen |
| Success signal | The observation that proves the feature ran |

`<git-dir>/verify-app-report.json` is new, at version 1. It holds one result per journey, keyed by
the journey name. A run of one journey replaces that journey's result and keeps every other one.

| Field | Holds |
|---|---|
| `head`, `dirty`, `timestamp` | The commit, whether the tree had uncommitted work, and when the run ended. For a person to read |
| `surface` | `browser-ui` or `mobile-ui` |
| `outcome` | `VERIFY_PASS`, `VERIFY_FAIL`, `VERIFY_STALE`, or `VERIFY_BLOCKED` |
| `step` or `reason` | The step that broke, or why the run could not start |
| `fingerprint` | The hash `journeys.py` gave the journey. This field, not `head`, decides freshness |

`<git-dir>/acceptance-report.json` stays at version 2 and gains one count, `gates_handoff`, and one
gate status, HANDOFF. Outrigger reads this file with Go's `json.Unmarshal`, which ignores an unknown
field. It also requires the `accepted` label, so the label hook stays the guard and outrigger needs
no change (`cmd/outrigger-phased/verifyacceptance.go:41` in the outrigger repository).

### API / Interface

`/verify-app` takes one of three inputs, in this order of preference.

1. A journey name that matches a leaf document, such as `/verify-app deals`.
2. Nothing, in which case it reads the changed set and picks the leaf documents the change touches.
3. A plain sentence describing the journey, used when no leaf document covers it yet.

It edits no file in the working tree. It writes exactly one file,
`<git-dir>/verify-app-report.json`, as `quality-gates` writes its own report inside `<git-dir>`.
It reports one table: the step, what was observed, and PASS or FAIL. Its last line is
machine-readable: `VERIFY_PASS`, `VERIFY_FAIL <step>`, `VERIFY_STALE <step>`, or
`VERIFY_BLOCKED <reason>`.

`journeys.py` takes `--changed-files`, `--docs-root`, and `--repo-root`, and prints one JSON object.
The object names every leaf document whose `source_refs` include a changed file, with a fingerprint
for each. It also lists every changed file that no journey covers. It runs no git: the caller
passes the changed set, per rule 4 of ADR 0011.

`check_drive_blocks.py` takes a directory, defaults to `docs/products`, and prints one line per
leaf document missing the block. It exits 0 when every leaf document carries one, 1 when any does
not, and 2 on operator error. It accepts `--json`, matching `check_staleness.py`.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| 0001 | A bead's How goes in the native `design` field, Done when in `notes`, and Acceptance Criteria in `acceptance_criteria`. The description body is not the place for them | Every bead `/plan-to-beads` creates from this plan writes those three native fields |
| 0002 | An agent in this plugin can dispatch a subagent and receive its result. The quality-gates orchestrator fans out to blocking subagents | `agents/verify-app.md` is dispatchable, so a caller can run a verification in its own context window |
| 0011 | A check result travels in a report file inside `<git-dir>`, never in a transcript. A check never runs the next step. A script runs no git and is told its inputs | `verify-app` writes its report file, `quality-gates` names the owner and runs nothing, and `journeys.py` and both writers take every value as an argument |

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | The drive block | Add **How to drive this** to the leaf template in `skills/product-surface-docs/SKILL.md`. Write `check_drive_blocks.py` and its regression suite. Add both to the check list in `CLAUDE.md` | S | `python3 skills/product-surface-docs/scripts/test_check_drive_blocks.py` passes, and `check_drive_blocks.py` reports every leaf document in a fixture tree that carries no block |
| 2 | The control document | Write `skills/verify-app/references/control-template.md` with the six fields | S | The template holds all six fields, and `python3 skills/quality-gates/scripts/check_doc_paths.py` exits 0 |
| 3 | `verify-app` | Write the skill, the agent, and the command. Cover launch, the ready poll, authentication, snapshot before each screen, and the PASS or FAIL report with its machine-readable last line | M | `claude plugin validate .` exits 0, `/validate-plugin` reports no orphan and no broken reference, and the three registration places name the component |
| 4 | `verify-app-ios` (tadw-qby) | The same skill for the iOS Simulator, driven by the `agent-device` command-line tool, which can tap where `xcrun simctl` cannot. Add a `device` section to the control template. Write each result to the `verify-app` report file under surface `mobile-ui` | M | `claude plugin validate .` exits 0, the skill is registered in the three places, and one recorded run returned a verdict |
| 5a | The journeys script (tadw-6xhi) | Write `journeys.py` and its regression suite. Add the suite to the check list in `CLAUDE.md` and to `.tadw/ship-gates.json` | S | One command names the journeys a changed set needs, and a fingerprint changes only when one of that journey's files changes |
| 5b | The `verify-app` report file (tadw-imgg) | Write `write_verify_report.py` and its suite. Call it from Step 6 of `verify-app`. Reword its Never rule to allow the one file inside `<git-dir>` | M | Every run on a leaf-document journey leaves that journey's outcome and fingerprint in the report file, and the working tree is unchanged |
| 5c | The handoff grading (tadw-do7x) | Teach `write_acceptance_report.py` the fixed table and `gates_handoff`. Teach `load_findings.py` and the label hook the same count | M | An unchecked UI change leaves `gates_handoff` above zero and the bead without `accepted` |
| 5d | The routing (tadw-440) | Point `route_qa.py` and `skills/quality-gates/SKILL.md` at the new skills. Make `verify-acceptance` route the change, pass the paths, reuse a saved pass by fingerprint, and grade HANDOFF as INCONCLUSIVE | S | Every handoff owner is a `tadw:verify-*` skill, and an unchecked UI change grades INCONCLUSIVE |
| 6 | Diagnostician reproduction | Add the browser tools to the `agents/diagnostician.md` tool list. Rewrite Step 2 to drive the application when the bug is in a web page, and to say plainly when it could not | S | The frontmatter lists the browser tools, and the quality checklist item "The failing behavior was actually reproduced or observed" names how |
| 7 | The two proofs | Add `evals/cases/verify-app-loads/case.json`. Run `verify-app` once against a real running application and record the transcript in the bead | M | The eval case passes 3 of 3 runs on the with-plugin arm, and the bead holds the transcript of a run that returned a verdict |

## Acceptance Criteria

1. Given a change that touches a web page, when `/quality-gates` runs, then the handoff row names
   `tadw:verify-app` and names no skill from another plugin.
2. Given a UI change with no `verify-app` result for its journeys, when `/verify-acceptance` runs,
   then the verdict is INCONCLUSIVE, the report names the surface and the journeys to run, and the
   bead does not get the `accepted` label.
3. Given a project with `docs/verification/control.md` and a leaf document carrying a drive block,
   when `/verify-app <journey>` runs, then it launches the application, drives the journey, and
   ends with `VERIFY_PASS` or `VERIFY_FAIL <step>`.
4. Given a journey whose success signal never appears, when `/verify-app` runs, then it reports
   FAIL, names the step that broke, and quotes the on-screen error text.
5. Given a `docs/products` tree where one leaf document carries no drive block, when
   `python3 skills/product-surface-docs/scripts/check_drive_blocks.py` runs, then it names that
   document and exits 1.
6. Given a bug in a web page, when the `diagnostician` agent investigates, then its Evidence
   Collected section holds an observation it made in the running application, or a plain statement
   that it could not reach the application and why.
7. Given the prompt "does this change actually work in the app?" in a fresh session, when the
   plugin is loaded, then `verify-app` is among the loaded skills in at least 3 of 3 runs.
8. Given the full check list in `CLAUDE.md`, when every command in it runs, then all pass, and the
   list names `test_check_drive_blocks.py`, `check_drive_blocks.py`, `test_journeys.py`, and
   `test_write_verify_report.py`.
9. Given `/validate-plugin`, when it runs after this work, then it reports no broken reference and
   no orphan other than the ones `CLAUDE.md` names as accepted.
10. Given a `VERIFY_PASS` result for every needed journey, when one of those journeys' source files
    changes, then the next `/verify-acceptance` grades the handoff HANDOFF again, and it runs
    `/verify-app` only for that journey.

**Coverage:** criteria 1, 2, 5, and 10 prove the routing, the handoff grading, and the checker in
scope. Criteria 3 and 4 prove `verify-app` itself. Criterion 6 proves the diagnostician change.
Criterion 7 proves the eval case. Criteria 8 and 9 prove registration. The `verify-app-ios` skill
is proven by criteria 8 and 9 alone, which is stated under Risks below.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| `verify-app-ios` ships unproven, because no criterion drives a simulator | Med | High | Accept it for now, and file a bead to record one live iOS run. The web half carries the technique, and the iOS half copies it |
| A drive block goes stale when the user interface changes, so a verification fails on a selector rather than on a defect | High | High | `verify-app` reports a selector mismatch as a distinct outcome, not as FAIL. `check_staleness.py` already flags a leaf document whose source files moved |
| Requiring a drive block on every leaf document turns a large existing tree red on the first run | Med | Med | `check_drive_blocks.py` reports a missing block as a finding, and the check enters the pre-push list only for this repository, which has no `docs/products` tree |
| The skill grows into a second `/qa`, taking on fixing as well as reporting | Med | Med | `verify-app` edits no file in the working tree and writes only its report file, matching `quality-gates`. Write that into its Critical Rules |
| A browser run costs minutes and tokens on every gate run | Med | Med | It runs only when routing finds a `browser-ui` surface, and only for a needed journey whose saved pass is missing or carries an old fingerprint |
| A gate status that one reader does not know lets a UI change through, or breaks a reader | High | Med | Milestone 5c changes the writer, the loader, and the label hook in one bead, with a test for each |
| A pass on an unrelated journey settles the handoff | High | Med | The writer requires a pass for every journey whose `source_refs` include a changed file, and a changed file that no journey covers keeps the row HANDOFF |
| Scope grows to cover the eval battery | Low | Med | Out of Scope names it, and it becomes beads instead |

## Dependencies

- The `agent-browser` command-line tool must be on the PATH of the machine running `verify-app`.
  The owner chose it on 2026-09-23, in place of a browser tool loaded through `ToolSearch`. A skill
  cannot install it, so `verify-app` stops with `VERIFY_BLOCKED browser` and the install command.
- The `agent-device` command-line tool, version 0.21.0 or later, and Xcode with an iOS Simulator,
  for milestone 4 only. The owner chose `agent-device` on 2026-09-10 and confirmed it on
  2026-10-05.
- A running application to record the live seam against, for milestone 7.
- No dependency on `/qa`, `/ios-qa`, or the `ll` plugin. This plan removes the first two from the
  pipeline and copies a shape from the third without importing it.

## Testing Strategy

- **Structural, and no model call.**
  `python3 skills/product-surface-docs/scripts/test_check_drive_blocks.py` covers the new checker:
  a tree where every leaf document carries a block, a tree missing one, a tree with no leaf
  documents, and a directory that does not exist. `claude plugin validate .` and
  `python3 skills/quality-gates/scripts/check_doc_paths.py` cover the new components. All three run
  in the pre-push hook.
- **Behavioral, one eval case.** `evals/cases/verify-app-loads/case.json` sends a realistic request
  and grades whether the skill loaded. This needs a change to `evals/run.py`, whose `ask` function
  returns plain text today and cannot see which skill loaded. Reading that needs
  `--output-format stream-json` and a parse of the transcript. That change is the smallest part of
  the invocation battery, and this plan takes only that part.
- **Live, once per skill.** Run `/verify-app` against a real application, once for a journey that
  works and once for a journey with a known defect. Record both transcripts in the milestone 7
  bead. The second run matters more, because a verification that cannot fail is not a verification.

## Open Questions

- Which application records the live seam in milestone 7. The LoanLabs factory repository already
  has drive information in `ll:verify-commons`, so it is the cheapest choice. The owner of that
  answer is the repository owner.
- Whether `check_drive_blocks.py` belongs in the pre-push list of a project that has a large
  `docs/products` tree. It is safe here, because this repository has no such tree. A project
  adopting it later needs a way to accept a leaf document that no one can drive, such as a
  document about a background job.
