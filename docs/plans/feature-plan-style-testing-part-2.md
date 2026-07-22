# Feature Plan: `style-testing` (Part 2 of 2), prove it works and fix the doc defect

**Part 1** (`docs/plans/feature-plan-style-testing.md`) authors the skill, reconciles `style-rspec`
into a delta, and wires both discovery and dispatch. **Part 2 does two independent things:** it
measures whether the skill actually improves the tests a model writes, and it fixes a pre-existing
documentation defect in `AGENTS.md` that Part 1's review uncovered.

**The two milestones here are independent of each other** and can be decomposed into separate bead
sets. They are bundled only because both are follow-on work to Part 1.

**Sequencing.** Part 2 runs after Part 1 lands. M4 edits `AGENTS.md`, which Part 1's M3 also edits
(different lines, different concerns), so running them concurrently invites a needless conflict.
M5b cannot run at all until the M1 artifact exists.

---

## 1. Goals

| ID | Goal | Owning milestone |
|---|---|---|
| **G5** | The skill's efficacy is measured against an unguided baseline, not assumed. | M5b |
| **G6** | `AGENTS.md` no longer instructs readers to register components in `plugin.json`, so the defect stops generating bad work items. | M4 |

G1 through G4 are owned by Part 1.

## 2. Problem

**For M5b.** Part 1 can prove `style-testing` is correct-by-construction, wired, and reachable. It
cannot prove it is useful. The central risk it names is that the core "reduces to platitudes once
framework nouns are removed," and Part 1 has no detector for that. A prompt document with no
behavioral evaluation is an unverified claim.

**For M4.** `AGENTS.md:355` states `plugin.json` "defines plugin metadata, **component
registration**, and the `hooks` field." `AGENTS.md:529` and `:537` instruct "Register in
`.claude-plugin/plugin.json` if needed." All three are false. `plugin.json` is 511 bytes containing
`name`, `version`, `description`, `author`, `license`, and `hooks`, and registers zero components;
`grep -c "style-python\|style-frontend\|review-python" .claude-plugin/plugin.json` returns `0`.
Components are auto-discovered from their directories. This defect already produced one
unsatisfiable acceptance criterion in bead `tadw-wdk`, which is how it was found.

## 3. Decisions

| ID | Decision | Rationale |
|---|---|---|
| **D8** | The eval discriminates on a pre-registered **trap subset** of rubric criteria, not on the aggregate score alone. | Modern models write decent tests unprompted, so baseline may score 8 or 9 of 10 and a "strictly greater in aggregate" bar becomes unachievable through no fault of the skill. The traps are where an unguided model reliably fails. |
| **D9** | Judging is blind and criterion-by-criterion with cited evidence, and the blinding limitation is stated rather than claimed away. | The treatment suite is often self-identifying through its scenario naming and hoisted setup. Per-criterion scoring with evidence is robust to a judge who guesses the arm; a holistic preference score is not. |
| **D10** | A one-run-per-arm smoke check gates the full matrix. | The full matrix is 36 model runs. A smoke check catches a broken fixture or rubric for one third of the cost. |
| **D11** | M4 fixes the instruction, not just the description. | Correcting `AGENTS.md:355` alone would leave lines 529 and 537 still telling readers to edit `plugin.json`, which is the line that actually caused the defect. |

## 4. Scope

### In scope

- The fixture set, rubrics, eval protocol, and its execution (M5b).
- The three adversarial probes and the live dogfood (M5b tier 3).
- Correcting the three false `plugin.json` claims in `AGENTS.md` (M4).

### Out of scope

| Item | Why |
|---|---|
| Changing the skill's content in response to eval results | A failing fixture produces a finding; the fix is a follow-up bead, so the eval stays an honest measurement rather than a thing to tune against. |
| Adding component registration to `plugin.json` | The auto-discovery behavior is correct; the documentation is what is wrong. |
| Extending the eval to frameworks outside the four fixtures | Covered adequately by the tier-3 unseen-framework probe. |
| Always-on testing guidance via `hooks/style-core.md` | Separate blast radius, separate decision. Same exclusion as Part 1. |

## 5. Dependencies

| ID | Dependency | Consumed by | Status |
|---|---|---|---|
| **DEP-4** | Part 1 landed: `skills/style-testing/SKILL.md` exists and passes M5a. | M5b, all tiers | Blocking |
| **DEP-5** | The pre-rewrite `style-rspec` git SHA captured at Part 1's M2 step 0. | M5b tier 3 non-regression probe | Blocking; unrecoverable if M2 landed without it |
| **DEP-6** | Subagent orchestration for 36 model runs across authoring and judging arms. | M5b tier 2 | Available |
| **DEP-7** | A real project with real code to write tests against. | M5b tier 3 dogfood | Owner-supplied |
| **DEP-8** | None. M4 is a pure documentation edit. | M4 | Available |

## 6. Milestones

### M4. Fix the `plugin.json` registration doc defect

Independent of M5b. Decomposable into a single bead.

- `AGENTS.md:355`: remove the false "component registration" claim. State that skills, agents, and
  commands are auto-discovered from their directories, and that `plugin.json` carries metadata plus
  the `hooks` field only.
- `AGENTS.md:529` (Adding a New Skill) and `AGENTS.md:537` (Adding a New Agent): replace "Register
  in `.claude-plugin/plugin.json` if needed" with the true registration surfaces, namely the
  `AGENTS.md` component lists and the `README.md` table.

**Done when:** no line in `AGENTS.md` instructs a reader to register a component in `plugin.json`,
and a fresh reader following "Adding a New Skill" end to end produces no `plugin.json` edit.

### M5b. Behavioral evaluation

Ships `skills/style-testing/references/fixtures/` and
`skills/style-testing/references/eval-protocol.md`.

#### Fixtures

```
fixtures/
  python-pytest-service/      source.py     rubric.md
  ts-vitest-hook/             source.ts     rubric.md
  swift-xctest-viewmodel/     source.swift  rubric.md
  ruby-minitest-model/        source.rb     rubric.md
```

Each `source.*` is a small unit of behavior worth testing (about 40 to 80 lines) containing a happy
path, an error path, a boundary condition, and at least two **nondeterminism traps**: for example
an injectable clock, a collection whose iteration order is not guaranteed, or a record best located
by unique key rather than by index.

Each `rubric.md` holds 10 binary criteria derived from the 14 principles and phrased for that
fixture. Example, pytest: "setup is in a fixture, not inline in the test body"; "the created record
is located by unique key, not by `[-1]`"; "the clock is injected, not read from `datetime.now()`";
"no single test asserts more than one behavior".

**Trap subset (D8).** Of the 10 criteria, 3 are pre-registered as traps: the ones an unguided model
reliably fails. These are marked in `rubric.md` before any run, and they carry the discriminating
weight in the pass bar.

#### Protocol, per fixture

1. **Baseline arm.** A subagent with no style skill loaded writes a test suite for `source.*`.
2. **Treatment arm.** A subagent with `style-testing` loaded writes a suite for the same file.
3. **Blind judge.** A third subagent receives `rubric.md` and both suites, labeled only A and B in
   randomized order, and scores each criterion independently with cited evidence (D9).
4. Three runs per arm; take the median.

**Smoke check first (D10).** Run one arm-pair per fixture (12 runs) before committing to the full
36. A fixture whose baseline already passes all three traps is a broken fixture, not a null result,
and must be redesigned before the full matrix runs.

#### Pass bar (D8)

All four must hold:

1. Treatment median at least **8 of 10** on every fixture.
2. Treatment median at least equal to baseline on **every** fixture (not strictly greater, which a
   strong baseline can make unachievable).
3. Treatment strictly greater than baseline **on the 3-criterion trap subset**, on every fixture.
4. Zero instances of framework-inappropriate advice, for example telling a pytest suite to use `let`.

A fixture that fails points at a specific defective principle. The response is to record the
finding and open a follow-up bead against the skill's wording, never to adjust the bar.

#### Tier 3, adversarial and dogfood

Runs after the tier-2 bar clears.

- **Unseen framework probe.** Apply the skill to Go's `testing` package, which the appendix does not
  cover. Genuine framework-independence means the 14 principles still apply and no idiom from
  another language is invented.
- **RSpec non-regression.** Give an RSpec task with both `style-testing` and the rewritten
  `style-rspec` loaded. Output must be at least as good as the pre-rewrite 496-line `style-rspec`
  produced alone, diffed against the DEP-5 baseline SHA. This guards Part 1's M2 deletions.
- **Escape-hatch probe.** Give a case where a rule should bend (an order-dependent migration test,
  or a property-based test with a random seed). The skill should surface the escape hatch rather
  than mechanically applying principle 11.
- **Live dogfood.** Write real tests in a real project and run them. They must pass and read well.
  This is the only tier exercising the skill against real code, and it is the final gate.

**Done when:** the smoke check passes, the full matrix clears all four pass-bar conditions, and all
four tier-3 probes pass.

## 7. Acceptance criteria

1. **Given** `grep -n "plugin.json" AGENTS.md`, **when** run, **then** no matching line instructs
   registering a skill, agent, or command in `plugin.json`.
2. **Given** a reader follows `AGENTS.md` "Adding a New Skill" end to end, **when** they finish,
   **then** they have edited no file under `.claude-plugin/`.
3. **Given** the four fixtures each carry a `rubric.md` with 10 binary criteria, **when** inspected
   before any eval run, **then** exactly 3 criteria per fixture are marked as the trap subset.
4. **Given** the smoke check (one arm-pair per fixture), **when** run, **then** no fixture's
   baseline passes all 3 trap criteria; any that does is redesigned before the full matrix.
5. **Given** the full tier-2 matrix, **when** scored, **then** treatment median is at least 8 of 10
   on every fixture, at least equal to baseline on every fixture, and strictly greater than
   baseline on the trap subset on every fixture.
6. **Given** the tier-2 results, **when** reviewed, **then** zero treatment outputs contain advice
   inappropriate to the fixture's framework.
7. **Given** the tier-3 unseen-framework probe against Go's `testing` package, **when** a model
   applies `style-testing`, **then** the output applies the core principles and invents no idiom
   from a different language.
8. **Given** the tier-3 RSpec non-regression probe diffed against the DEP-5 baseline SHA, **when**
   compared, **then** the post-rewrite output is at least as good as the pre-rewrite output.
9. **Given** the tier-3 dogfood, **when** the generated tests are run in a real project, **then**
   they pass.

## 8. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Ceiling effect: baseline already scores 8 or 9 of 10, so the skill cannot demonstrate lift. | High | D8's trap subset. The traps are chosen precisely because unguided models fail them, so the discriminating signal survives a strong baseline. AC4 verifies the traps actually discriminate before the full matrix runs. |
| Blinding is weaker than claimed; the judge infers which arm is which. | Medium | D9: per-criterion scoring with cited evidence rather than holistic preference. The limitation is stated in `eval-protocol.md` rather than claimed away. |
| Eval cost: 36 model runs for tier 2 alone. | Medium | D10's 12-run smoke check gates the full matrix. |
| DEP-5 baseline SHA was not captured during Part 1's M2. | Medium | Recoverable from `git log -- skills/style-rspec/SKILL.md` as long as M2 landed as its own commit, which Part 1's AC8 requires. If M2 was squashed into a larger commit, the probe degrades to a qualitative comparison. |
| The eval becomes a thing to tune the skill against rather than a measurement of it. | Medium | Scope explicitly excludes changing skill content in response to results; findings become follow-up beads. |
| Findings arrive after the skill is already in daily use. | Low | Accepted. Part 1 ships a usable skill; Part 2 improves confidence, not availability. |

## 9. Estimated size

| Milestone | Files | Approx. LOC |
|---|---|---|
| M4 doc defect | 1 edited | ~6 changed |
| M5b fixtures | 8 new (4 sources, 4 rubrics) | +260 |
| M5b protocol | 1 new | +80 |

Net roughly +345 lines across 10 files. M4 is a single bead; M5b is a bead set of three to four.
