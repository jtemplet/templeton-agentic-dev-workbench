# Feature Plan: `style-testing` (Part 1 of 2), author, reconcile, and wire

**Part 1 delivers the skill and makes it reachable.** Part 2
(`docs/plans/feature-plan-style-testing-part-2.md`) proves it works and fixes an unrelated
documentation defect it uncovered.

**Supersedes the design of bead `tadw-wdk`.** That bead's goal (a framework-independent testing
core) is correct; two of its stated premises are not, and its central design decision was made
under an assumption that no longer holds. See section 3.

**Revision note.** This revision incorporates all nine changes from the plan review, most
importantly the addition of M3b (dispatch wiring), which closes the gap that would have shipped the
skill unreachable.

---

## 1. Goals

| ID | Goal | Owning milestone |
|---|---|---|
| **G1** | A framework-independent test-style core exists, stating how tests should be structured in any language this workbench supports. | M1 |
| **G2** | RSpec-specific guidance survives as a narrow delta rather than as the repo's general testing skill. | M2 |
| **G3** | The core is reachable: discoverable in the docs, and dispatched by the agents and commands that actually do code work. | M3, M3b |
| **G4** | Framework-independence and invocation are enforced mechanically, not by author discipline. | M5a |

Efficacy (does the skill measurably improve the tests a model writes) is **G5**, owned by Part 2.

## 2. Problem

There is no framework-independent test-writing guidance in this workbench. The only test skill,
`style-rspec` (496 lines), is RSpec-on-Rails specific. A grep across `skills/` and `hooks/` finds
zero guidance for pytest, Vitest, Jest, XCTest, Swift Testing, or Minitest; the only hits are
incidental mentions inside `pr-maintenance` and `feature-development`.

The universal core that every other style skill sits on (`hooks/style-core.md`, 72 lines) is a
*production-code* core. Its nine principles cover abstraction, unit size, interfaces, dependency
injection, tell-don't-ask, composition, errors, the step-down rule, and naming. None of them say
anything about how to structure a test. So the gap is not "style-rspec lacks a core"; it is
"there is no testing core for anything to sit on."

The owner writes in multiple languages with different test frameworks and no longer uses RSpec.
Today that means the single richest style asset in the repo is unusable to them.

## 3. Corrections to `tadw-wdk`

| Claim in the bead | Verdict | Evidence |
|---|---|---|
| "Test-writing guidance is Rails-only" | **True** | No pytest/Vitest/XCTest guidance exists anywhere in `skills/` or `hooks/`. |
| "review-rails line 30 defers to style-rspec" | **True** | `skills/review-rails/SKILL.md:30` reads "for test style defer to `style-rspec`". |
| "style-rspec is the only style skill with no universal core beneath it" | **False** | `skills/style-rspec/SKILL.md:27-29` already has a "Universal Core (injected)" section naming `hooks/style-core.md` and stating "Everything below is the RSpec/Rails delta." The real gap is different: `style-core.md` contains no testing guidance at all. |
| AC #3: `grep -rw style-testing ... .claude-plugin/plugin.json` must match | **False, unsatisfiable** | `plugin.json` is 511 bytes: `name`, `version`, `description`, `author`, `license`, `hooks`. It registers **zero** components. `grep -c "style-python\|style-frontend\|review-python" .claude-plugin/plugin.json` returns `0`. Components are auto-discovered from directories. |
| Design: "do NOT make style-rspec framework-agnostic; its Rails specifics are the value" | **Obsolete** | Written when the owner used RSpec on a live project. They no longer do. |
| Size: "style-rspec trim ~60 LOC" | **Understated** | `style-rspec` drops from 496 lines to roughly 90, and the new core is largely net-new authoring. |

**Root cause of the bad acceptance criterion.** `AGENTS.md:355` states plugin.json "defines plugin
metadata, **component registration**, and the `hooks` field." `AGENTS.md:529` and `:537` instruct
"Register in `.claude-plugin/plugin.json` if needed." Both are false for skills, agents, and
commands. The bead author read those lines and wrote a criterion against them. This is a live
documentation defect that will keep generating bad work items until fixed. It is **out of scope for
Part 1** and is owned by Part 2, M4.

## 4. Decisions

| ID | Decision | Rationale |
|---|---|---|
| **D1** | `style-testing` is authored as a genuine testing core, not strip-mined `style-rspec`. | Only about 10 of style-rspec's rules transpose. A pure extraction would omit determinism, test naming, and what-not-to-test, which are core and currently absent. |
| **D2** | The principles body names no framework. Exactly one clearly-marked appendix maps each principle to its idiom in pytest, Vitest/Jest, XCTest/Swift Testing, and Minitest. | Without the mapping the skill is platitudes and unusable across languages; with it inside the principles it stops being a core. Separation preserves both. Enforced by M5a, not by author discipline. |
| **D3** | `style-rspec` is retained as a thin RSpec delta (about 90 lines), not deleted. | Costs little, keeps the `review-rails:30` referrer resolving, and preserves good content if an RSpec project reappears. Deleting is irreversible and buys nothing. |
| **D4** | No sibling delta skills (`style-pytest`, `style-vitest`, ...) are created. | House principle #1: wait for duplication before abstracting. The D2 appendix serves until a real second consumer exists. |
| **D5** | `review-rails` defers to `style-testing` as primary, and to `style-rspec` only when the project actually uses RSpec. | Reflects that the core is now the default and RSpec is the exception. |
| **D6** | The skill's frontmatter `description` is a first-class deliverable with its own acceptance test. | For a model-invoked skill the description is the only thing determining whether it ever fires. `style-rspec`'s description is scoped so narrowly ("RSpec tests in Rails apps") that it can never fire on the owner's current work. That failure mode must not be reproduced. |
| **D7** | The cheap deterministic gates (static check, invocation test) ship in Part 1; the expensive behavioral eval ships in Part 2. | Part 1 must be able to self-verify its own design constraint. Deferring the static check would leave D2 unenforced from the first edit onward. |

## 5. Scope

### In scope (Part 1)

- Authoring `skills/style-testing/SKILL.md` including its frontmatter description.
- Rewriting `skills/style-rspec/SKILL.md` as a delta.
- Rewiring documentation referrers (`AGENTS.md`, `README.md`) and the `review-rails` skill.
- Rewiring dispatch referrers (`agents/software-engineer.md`, `agents/code-reviewer.md`, feature-dev commands).
- The tier-1 static conformance script and the invocation test.

### Out of scope (consolidated)

| Item | Why | Owner |
|---|---|---|
| Sibling framework delta skills (`style-pytest`, `style-vitest`, `style-xctest`) | D4, wait for duplication | Not planned |
| Deleting `style-rspec` | D3, irreversible and buys nothing | Not planned |
| Making testing guidance always-on via `hooks/style-core.md` | Fires in every project and for every consumer on upgrade; blast radius warrants its own decision | Separate change |
| The `plugin.json` documentation defect in `AGENTS.md` | Independent pre-existing defect | Part 2, M4 |
| Behavioral efficacy evaluation (A/B, fixtures, adversarial probes) | Expensive; not required to ship a wired skill | Part 2, M5b |

## 6. Dependencies

| ID | Dependency | Consumed by | Status |
|---|---|---|---|
| **DEP-1** | `commands/validate-plugin.md:30` orphan semantics: "skills not referenced by any **agent or command**". Skill-to-skill references do not satisfy it. | M3b, AC6 | Verified present |
| **DEP-2** | Python 3 stdlib only, matching the no-install convention set by `hooks/test-hooks.js`. | M5a | Available |
| **DEP-3** | Ability to run a model against realistic prompts with the skill available, to measure invocation. | M5a invocation test | Available via subagents |

No external, network, or third-party dependencies. Nothing here blocks on Part 2.

## 7. Milestones

Five milestones, mutually exclusive by artifact touched.

### M1. Author the universal core

Create `skills/style-testing/SKILL.md` (target 200 to 240 lines).

**Frontmatter (D6), draft:**

```yaml
name: style-testing
description: Use when writing, reviewing, or restructuring tests in any language or framework (pytest, Vitest, Jest, XCTest, Swift Testing, Minitest, JUnit, Go testing) - one behavior per test, hoisted declarative setup, deterministic clocks and identification, scenario-named groups, and what not to test
```

The framework list exists for keyword matching at invocation time, not as content. Its presence in
frontmatter is exempt from the M5a leak check.

**Principles.** The first ten transpose from `style-rspec`; the last four are net-new and close the
gaps named in the bead's own Why.

| # | Principle | Transposed from |
|---|---|---|
| 1 | Test at the outermost seam that still runs fast. Exercise the real stack rather than invoking the handler directly. | rspec rule 1 |
| 2 | Name the action under test once and reuse it; do not retype it in every case. | rspec rule 2 |
| 3 | Setup is declarative and lives outside the test body. Arrange is hoisted; the body is Act and Assert. | rspec rule 3 |
| 4 | One behavior per test. A failing test name alone should say what broke. | rspec rule 4 |
| 5 | Group by scenario, named "when.../with.../for...". One scenario per group. | rspec rule 5 |
| 6 | Use the lightest fixture that still proves the behavior. Touch I/O only when the behavior depends on it. | rspec rule 6 |
| 7 | Prefer lazy setup; make it eager only when the state must exist before the action runs. | rspec rule 7 |
| 8 | Identify what you assert on deterministically by unique key, never by "last", "first", or positional index. | rspec rule 8 |
| 9 | Define shared setup at the scope every case that uses it can see. | rspec rule 9 |
| 10 | Prerequisite state exists before the action; address resources through their real addressing mechanism, not hand-built strings. | rspec rule 10 |
| 11 | Tests are deterministic: no dependence on wall clock, RNG, ambient locale or timezone, network, or inter-test execution order. Inject the clock and the seed. | net-new |
| 12 | Test names describe observable behavior, not implementation. | net-new |
| 13 | Do not test framework internals, third-party libraries, generated code, or private methods. Test your behavior through its public surface. | net-new |
| 14 | Assert on one clear cause of failure. Prefer a precise assertion over a broad one that passes for the wrong reason. | net-new |

**Also in M1:** "When to Use / When NOT to Use"; "Anti-Patterns" (each with why it hurts and the
fix, framework-free); "Escape hatches" (genuinely order-dependent integration flows, property-based
tests with a seed, snapshot tests, legacy suites you are told not to restructure); "Quality
Checklist" as framework-free checkboxes; and the **D2 appendix** mapping each principle to its
idiom in pytest, Vitest/Jest, XCTest/Swift Testing, and Minitest, fenced off and excluded from the
leak check.

**Done when:** the file exists, covers all 14 principles plus the appendix, carries the D6
description, and passes M5a.

### M2. Reconcile `style-rspec` into a delta

**Step 0, baseline capture (before any deletion).** Record the pre-rewrite file's git SHA in the
implementing bead so Part 2's non-regression probe can diff against it. M2 lands as its own commit,
independently revertible from M1 and M3.

Rewrite `skills/style-rspec/SKILL.md` from 496 lines to roughly 90.

- Opening section points at `style-testing` as the core it extends, mirroring how
  `style-python:26` points at `hooks/style-core.md`.
- Retain only what does not survive translation: `let`/`let!`/`subject` mechanics, request-spec
  versus controller-spec, FactoryBot `build`/`build_stubbed`/`create`, `it_behaves_like` and
  shared-example variable scoping, nested path helpers, `find_by` over `Model.last`.
- Delete every rule and worked example whose content is now stated framework-free in
  `style-testing`. Keep at most two worked examples.

**Done when:** no rule in `style-rspec` would read as correct advice with the RSpec nouns stripped
out; its opening names `style-testing`; the file is under 120 lines; and it landed as its own commit.

### M3. Rewire documentation referrers

- `skills/review-rails/SKILL.md:30`: change "for test style defer to `style-rspec`" to defer to
  `style-testing`, adding `style-rspec` as the conditional RSpec-only delta (D5).
- `AGENTS.md:168` ("**Testing:** Use the `style-rspec` skill"): retarget to `style-testing`.
- `AGENTS.md:362` registered-skills list: add a `style-testing` entry; amend the `style-rspec`
  entry to "RSpec delta on `style-testing`".
- `README.md:135` skills table: add a `style-testing` row; amend the `style-rspec` row.

**Done when:** `grep -rn "style-testing" AGENTS.md README.md skills/review-rails/SKILL.md` matches
all three files, and no referrer points at `style-rspec` as the general testing skill.

### M3b. Rewire dispatch referrers

**This is the milestone that makes the skill reachable.** M3 alone wires discovery; without M3b the
skill is never loaded by any workflow, and AC6 fails.

- `agents/software-engineer.md:35-39`: the routing table dispatches to a style skill by file
  extension. Add a rule loading `style-testing` for any test file, alongside the language style
  skill. Patterns: `test_*.py`, `*_test.py`, `*.test.ts`, `*.spec.ts`, `*.test.tsx`, `*_spec.rb`,
  `*_test.rb`, `*Tests.swift`, `*_test.go`.
- `agents/software-engineer.md:54`: the "Skip the language style skill" anti-pattern note gains the
  parallel warning for `style-testing` on test files.
- `agents/code-reviewer.md:38-40`: the dispatch table gains a test-file row mapping to
  `style-testing`.
- `commands/python-feature-dev.md:13`: add `style-testing` to the list of skills loaded during the
  implementation phase.

**Done when:** `grep -rn "style-testing" agents/ commands/` matches at least
`agents/software-engineer.md` and `agents/code-reviewer.md`, and `/validate-plugin` does not flag
`style-testing` as an orphan.

### M5a. Static conformance and invocation gates

Ships `skills/style-testing/scripts/check_framework_leak.py` (Python stdlib only, per DEP-2).

**Static check.** Parses `SKILL.md`, splits at the appendix heading, scans only the body above it.

- Fails on any banned token: `let!`, `subject {`, `it_behaves_like`, `describe(`, `beforeEach`,
  `@pytest`, `pytest.fixture`, `conftest`, `XCTAssert`, `@Test`, `expect(`, `rspec`, `jest`,
  `vitest`, `minitest`, `unittest`, `FactoryBot`, `build_stubbed`.
- Frontmatter present; `name:` equals the directory name; `description:` non-empty. Frontmatter is
  exempt from the token scan (D6 puts framework names there deliberately).
- Every required section heading present; appendix covers all four frameworks.
- Exit 0 clean, exit 1 with a line-numbered report otherwise.

**Invocation test.** Eight realistic test-writing prompts ("write tests for this service", "add
unit tests for the parser", "these tests are flaky, fix them", and so on) plus three controls that
are not about tests ("refactor this function", "explain this module", "fix this null deref"). Each
runs in a fresh session with the skill available; record whether `style-testing` is invoked.

**Bar:** at least 7 of 8 test prompts invoke the skill, and at most 1 of 3 controls false-fires.
Missing the bar means the D6 description needs rewording, not that the test is wrong.

**Done when:** the script exits 0 against the M1 artifact, and the invocation test clears its bar.

## 8. Acceptance criteria

1. **Given** a reader opens `skills/style-testing/SKILL.md`, **when** they read the principles,
   anti-patterns, escape hatches, and checklist sections, **then** no rule names a construct from
   any specific test framework. (Definition; AC2 is its enforcement.)
2. **Given** `python3 skills/style-testing/scripts/check_framework_leak.py`, **when** run, **then**
   it exits 0 and reports zero leaked framework tokens outside the appendix and frontmatter.
3. **Given** a reader opens `skills/style-rspec/SKILL.md`, **when** they read its opening section,
   **then** it names `style-testing` as the core it extends, and the file is under 120 lines.
4. **Given** `grep -rn "style-testing" AGENTS.md README.md skills/review-rails/SKILL.md`, **when**
   run, **then** all three files match.
5. **Given** `skills/review-rails/SKILL.md` previously deferred test style to `style-rspec`,
   **when** the rewire lands, **then** it defers to `style-testing` first and names `style-rspec`
   only as the RSpec-conditional delta, and both skills still exist on disk.
6. **Given** the orphan check in `/validate-plugin`, whose rule is "skills not referenced by any
   **agent or command**", **when** run, **then** `style-testing` is referenced by at least one file
   in `agents/` and is not flagged as an orphan.
7. **Given** the M5a invocation test, **when** run over its 8 test prompts and 3 controls, **then**
   at least 7 test prompts invoke `style-testing` and at most 1 control false-fires.
8. **Given** `git log --oneline -- skills/style-rspec/SKILL.md`, **when** inspected after M2,
   **then** the rewrite is an isolated commit that can be reverted without touching M1 or M3.

Efficacy criteria (behavioral A/B scores, unseen-framework probe) belong to Part 2 and are
deliberately absent here.

## 9. Test strategy (Part 1)

Two tiers, both cheap and deterministic. The expensive third tier is Part 2.

**Tier 1, static conformance.** The M5a script. Runs in CI, catches regression on every future
edit, and is what makes D2 a constraint rather than an intention. Proves hygiene only, not efficacy.

**Tier 1.5, invocation.** The M5a prompt battery. Proves the skill can be reached by a model in
practice, which is the failure mode `style-rspec` currently exhibits: a well-written skill nobody
loads. This is the highest-value cheap test in the plan.

**Explicitly deferred to Part 2:** whether the skill actually improves the tests a model writes.
Part 1 can prove the skill is correct-by-construction, wired, and reachable. It cannot prove it is
useful. That is an accepted, named limitation of shipping Part 1 alone.

## 10. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| The core reduces to platitudes once framework nouns are removed. | High | The D2 appendix carries the concreteness. **Part 1 cannot detect this**; the detector is Part 2's behavioral eval. Accepted risk for Part 1, and the main argument for not letting Part 2 slip. |
| The skill ships correct but is never invoked, repeating `style-rspec`'s fate. | High | D6 makes the description a deliverable; M5a's invocation test measures it; M3b guarantees agent-level dispatch independent of model choice. |
| M2 deletes guidance that had no framework-free equivalent. | Medium | Baseline SHA captured at M2 step 0; M2 lands as its own revertible commit; Part 2's non-regression probe diffs against it. |
| The appendix becomes the de-facto content and the principles are ignored. | Medium | Part 2's unseen-framework probe fails if the principles cannot stand alone. Not detectable in Part 1. |
| M3 and M4 both edit `AGENTS.md` (different concerns, different lines). | Low | M4 is in Part 2; sequence Part 2 after Part 1 rather than running them concurrently against the same file. |

## 11. Estimated size

| Milestone | Files | Approx. LOC |
|---|---|---|
| M1 core | 1 new | +235 |
| M2 rspec delta | 1 rewritten | -400 |
| M3 doc rewire | 3 edited | +8 |
| M3b dispatch rewire | 3 edited | +10 |
| M5a gates | 1 script, 1 protocol note | +90 |

Net roughly -57 lines across 10 files. Band: Target for a single bead set of four to six beads.
