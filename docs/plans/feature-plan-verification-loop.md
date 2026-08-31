# Feature Plan: The Verification Loop

**Date:** 2026-08-31
**Status:** Draft

## Summary

This plugin can prove that a change compiles, passes its tests, and answers a real HTTP request. It
cannot prove that a change works in the running application. This plan adds `verify-app`, a skill
that drives the real application and returns PASS or FAIL, and gives it the two documents it needs
to know how to launch the application and where each feature lives.

## Motivation

Three facts, each checked against the current tree, describe one hole.

**A change to a web page or a phone screen leaves this pipeline ungraded.**
`skills/quality-gates/SKILL.md` Step 3 routes a `browser-ui` change to `/qa` and a `mobile-ui`
change to `/ios-qa`. Both belong to other plugins. The row is a HANDOFF, and the run is INCOMPLETE.

**A change like that can still be graded ACCEPTED.** `skills/verify-acceptance/SKILL.md` Step 4
runs three gates: Tests, Lint and Format, and Type Checking. That subset holds no HANDOFF row. So a
change to a web page whose acceptance criterion cites a passing component test is graded ACCEPTED,
and nobody opened the page.

**The agent that investigates a bug cannot reproduce it.** `agents/diagnostician.md` Step 2 is
called "Reproduce and Gather Evidence". Its frontmatter declares four tools: `Read`, `Bash`,
`Grep`, and `Glob`. It cannot open the application it is investigating.

Two skills here do drive a running application, `ux-audit` through Playwright and `ux-audit-ios`
through `xcrun simctl`. Both judge design quality. Neither answers the question "did this change
work".

The person benefiting is the person who runs pipeline B on a change to a web page. Today that
person is the only thing standing between a broken screen and a closed bead.

## Scope

### In Scope

- A new skill, `verify-app`, that launches the application, drives one journey, and reports PASS or
  FAIL with the step that broke.
- A new skill, `verify-app-ios`, that does the same in the iOS Simulator.
- A new agent, `verify-app`, so a caller can run a verification in its own context window.
- A new command, `/verify-app`.
- A new per-project control document at `docs/verification/control.md`, holding how to launch the
  application, how to sign in, and which browser tool to load.
- A new **How to drive this** section in the leaf document template of
  `skills/product-surface-docs/SKILL.md`.
- A change to `skills/quality-gates/SKILL.md` Step 3, so the `browser-ui` and `mobile-ui` rows name
  `tadw:verify-app` and `tadw:verify-app-ios` instead of `/qa` and `/ios-qa`.
- A change to `skills/verify-acceptance/SKILL.md`, so an unresolved HANDOFF makes the verdict
  INCONCLUSIVE.
- Two browser tools added to the `agents/diagnostician.md` tool list, plus a reproduction step that
  uses them.
- A new checker, `skills/product-surface-docs/scripts/check_drive_blocks.py`, with its regression
  suite, and both added to the check list in `CLAUDE.md`.
- One eval case that measures whether `verify-app` loads when a person asks whether a change works.

### Out of Scope

- The eval invocation battery for all 45 skills. `docs/eval-driven-development.html` section 11
  already specifies it. It is a different subject, so it becomes beads rather than part of this
  plan.
- Any change to `ux-audit` or `ux-audit-ios`. They audit design, and this plan does not touch that
  job.
- Deleting `/qa` and `/ios-qa` from a user's setup. This plan stops pointing at them. It does not
  stop anyone from running them.
- A test application committed to this repository and driven on every push. The live seam is one
  recorded run, not an automated one.
- Any cloud agent, automatic bug reproduction from an inbox, or automatic merge.

## Technical Approach

### Architecture

`verify-app` is its own skill, and `quality-gates` routes to it. That keeps each skill to one job,
and it removes the outside plugin from the middle of pipeline B.

```text
/build -> /fresh-eyes-cr -> /quality-gates -> /verify-acceptance -> /tadw:ship
                                  |
                                  +-- HANDOFF browser-ui -> tadw:verify-app
                                  +-- HANDOFF mobile-ui  -> tadw:verify-app-ios
```

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
| `skills/quality-gates/SKILL.md` | Point the two handoff rows at the new skills | Modified |
| `skills/verify-acceptance/SKILL.md` | An unresolved HANDOFF makes the verdict INCONCLUSIVE | Modified |
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

Two documents gain a required shape.

`docs/verification/control.md` holds six fields. A project fills them once.

| Field | Holds |
|---|---|
| `launch` | The command that starts the application, and the port it answers on |
| `ready_check` | A command that returns 0 once the application answers, for the polling loop |
| `base_url` | The address to drive, on this machine |
| `auth` | How to reach a signed-in session without clicking through a signup form |
| `browser` | Which browser tool to load, and the exact `ToolSearch` query for it |
| `teardown` | What to clean up, or a plain statement that nothing needs cleaning |

Each leaf document under `docs/products/` gains a **How to drive this** section with five lines.

| Line | Holds |
|---|---|
| Route | The path to navigate to, relative to `base_url` |
| Precondition | The state that must exist first, such as a signed-in lender |
| Selector | The stable identifier to bind to, such as a test id or an accessibility role |
| Action | The steps a person takes on this screen |
| Success signal | The observation that proves the feature ran |

### API / Interface

`/verify-app` takes one of three inputs, in this order of preference.

1. A journey name that matches a leaf document, such as `/verify-app deals`.
2. Nothing, in which case it reads the changed set and picks the leaf documents the change touches.
3. A plain sentence describing the journey, used when no leaf document covers it yet.

It writes no file. It reports one table: the step, what was observed, and PASS or FAIL. Its last
line is machine-readable, `VERIFY_PASS` or `VERIFY_FAIL <step>`, so `quality-gates` can read a
result it dispatched.

`check_drive_blocks.py` takes a directory, defaults to `docs/products`, and prints one line per
leaf document missing the block. It exits 0 when every leaf document carries one, 1 when any does
not, and 2 on operator error. It accepts `--json`, matching `check_staleness.py`.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| 0001 | A bead's How goes in the native `design` field, Done when in `notes`, and Acceptance Criteria in `acceptance_criteria`. The description body is not the place for them | Every bead `/plan-to-beads` creates from this plan writes those three native fields |
| 0002 | An agent in this plugin can dispatch a subagent and receive its result. The quality-gates orchestrator fans out to blocking subagents | `agents/verify-app.md` is dispatchable, so the orchestrator can run the browser lane beside the other three rather than after them |

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | The drive block | Add **How to drive this** to the leaf template in `skills/product-surface-docs/SKILL.md`. Write `check_drive_blocks.py` and its regression suite. Add both to the check list in `CLAUDE.md` | S | `python3 skills/product-surface-docs/scripts/test_check_drive_blocks.py` passes, and `check_drive_blocks.py` reports every leaf document in a fixture tree that carries no block |
| 2 | The control document | Write `skills/verify-app/references/control-template.md` with the six fields | S | The template holds all six fields, and `python3 skills/quality-gates/scripts/check_doc_paths.py` exits 0 |
| 3 | `verify-app` | Write the skill, the agent, and the command. Cover launch, the ready poll, authentication, snapshot before each screen, and the PASS or FAIL report with its machine-readable last line | M | `claude plugin validate .` exits 0, `/validate-plugin` reports no orphan and no broken reference, and the three registration places name the component |
| 4 | `verify-app-ios` | The same skill for the iOS Simulator, driven by `xcrun simctl`. Reuse the technique from `skills/ux-audit-ios/SKILL.md` for capture and for setting Dynamic Type | M | `claude plugin validate .` exits 0, and the skill is registered in the three places |
| 5 | The wiring | Point the two handoff rows in `skills/quality-gates/SKILL.md` Step 3 at the new skills. Add a browser lane row to its owner table. Make an unresolved HANDOFF give an INCONCLUSIVE verdict in `skills/verify-acceptance/SKILL.md` | S | Both files name `tadw:verify-app`, neither names `/qa`, and the verdict rules in `verify-acceptance` list HANDOFF |
| 6 | Diagnostician reproduction | Add the browser tools to the `agents/diagnostician.md` tool list. Rewrite Step 2 to drive the application when the bug is in a web page, and to say plainly when it could not | S | The frontmatter lists the browser tools, and the quality checklist item "The failing behavior was actually reproduced or observed" names how |
| 7 | The two proofs | Add `evals/cases/verify-app-loads/case.json`. Run `verify-app` once against a real running application and record the transcript in the bead | M | The eval case passes 3 of 3 runs on the with-plugin arm, and the bead holds the transcript of a run that returned a verdict |

## Acceptance Criteria

1. Given a change that touches a web page, when `/quality-gates` runs, then the handoff row names
   `tadw:verify-app` and names no skill from another plugin.
2. Given a `quality-gates` report holding an unresolved HANDOFF row, when `/verify-acceptance`
   runs, then the verdict is INCONCLUSIVE and the report says which handoff is unresolved.
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
   list holds two more entries than it holds today.
9. Given `/validate-plugin`, when it runs after this work, then it reports no broken reference and
   no orphan other than the four `CLAUDE.md` names as accepted.

**Coverage:** criteria 1, 2, and 5 prove the wiring and the checker in scope. Criteria 3 and 4
prove `verify-app` itself. Criterion 6 proves the diagnostician change. Criterion 7 proves the eval
case. Criteria 8 and 9 prove registration. The `verify-app-ios` skill is proven by criteria 8 and 9
alone, which is stated under Risks below.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| `verify-app-ios` ships unproven, because no criterion drives a simulator | Med | High | Accept it for now, and file a bead to record one live iOS run. The web half carries the technique, and the iOS half copies it |
| A drive block goes stale when the user interface changes, so a verification fails on a selector rather than on a defect | High | High | `verify-app` reports a selector mismatch as a distinct outcome, not as FAIL. `check_staleness.py` already flags a leaf document whose source files moved |
| Requiring a drive block on every leaf document turns a large existing tree red on the first run | Med | Med | `check_drive_blocks.py` reports a missing block as a finding, and the check enters the pre-push list only for this repository, which has no `docs/products` tree |
| The skill grows into a second `/qa`, taking on fixing as well as reporting | Med | Med | `verify-app` reports and never edits, matching `quality-gates`. Write that into its Critical Rules |
| A browser run costs minutes and tokens on every gate run | Med | Med | It runs only when Step 3 routes a `browser-ui` surface, which a change to documentation or a library never does |
| Scope grows to cover the eval battery | Low | Med | Out of Scope names it, and it becomes beads instead |

## Dependencies

- A browser tool must already be enabled in the project being verified. The Playwright plugin is
  the first choice, because `skills/ux-audit/SKILL.md` already uses it. The `claude-in-chrome`
  tools are the fallback. A skill cannot install either one.
- `xcrun simctl` and Xcode, for milestone 4 only.
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
- Whether the browser lane in the `quality-gates` orchestrator waits for the other three lanes or
  runs beside them. ADR 0002 allows either. Measure it after milestone 5 rather than deciding now.
