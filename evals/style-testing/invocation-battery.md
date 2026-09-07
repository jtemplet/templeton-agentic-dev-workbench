# style-testing Invocation Battery

Measures whether the skill's frontmatter `description` actually causes it to fire. A skill that is
well written but never invoked is worthless; `style-rspec` is the cautionary example, its
description scoped so narrowly ("RSpec tests in Rails apps") that it could not fire on this repo's
current work.

This is an **invocation eval**, the first of the three types
[docs/eval-driven-development.html](../../docs/eval-driven-development.html) defines. That document
carries the method; this file is the one worked battery, and the shape to copy for another skill.
It is a deliberate measurement and never a gate, on the terms
[ADR 0005](../../docs/adr/0005-the-evals-are-a-measurement-not-a-gate.md) sets, so no git hook runs
it.

It ran once, as acceptance criterion 7 of the bead that built `style-testing`. The result is under
"Last run" below.

## Prerequisite: the skill must be in the session's registry

**A fresh session is necessary but not sufficient.** A session loads the versioned marketplace
cache, never the working tree, so a skill edited here is invisible until it ships. Run the battery
first thing in a fresh session, and to iterate on a `description` without a publish cycle, use the
symlink dev loop in section 5 of
[docs/eval-driven-development.html](../../docs/eval-driven-development.html). That section also
carries the two caveats, including removing the symlink once the skill ships.

**Verify before running.** Ask a subagent to list its available skills matching "style". If
`style-testing` is absent, stop; the registry has not picked it up and every prompt will miss.

## Procedure

For each prompt below, spawn a fresh subagent with this instruction:

> Do not use any tools and do not perform the task. Decide which skills, if any, you would invoke
> from your available skills list for the request below. Return only:
> `{"skills": [...], "reasoning": "one sentence"}`
>
> Request: `<prompt>`

Record whether `style-testing` appears in `skills`. Prompts run independently; do not batch them
into one subagent, which would let it infer that skill selection is what is being measured.

## Positive prompts (expect `style-testing`)

| # | Prompt | Notes |
|---|---|---|
| 1 | Write unit tests for `skills/style-testing/scripts/check_framework_leak.py` | Explicit, in-repo, Python |
| 2 | Add tests covering the error paths in this parser. | Explicit, language unstated |
| 3 | These tests fail intermittently in CI but pass locally. Fix them. | Flakiness, principle 11 territory, never says "write tests" |
| 4 | Review my test suite and tell me what is wrong with it. | Review rather than authoring |
| 5 | I am adding a new API endpoint. What tests should I write for it? | Advisory, no code yet |
| 6 | Write tests for a React hook that fetches and caches user data. | TypeScript, should NOT pull `style-rspec` |
| 7 | Convert these controller specs to request specs. | Should pull BOTH `style-testing` and `style-rspec` |
| 8 | Add pytest coverage for the new billing calculator module. | Names a framework in the description's keyword list |

## Control prompts (expect NO `style-testing`)

| # | Prompt | Why it must not fire |
|---|---|---|
| C1 | Refactor `check_framework_leak.py` to be simpler. | Touches a test-adjacent file but is not test work |
| C2 | Explain what the SessionStart hook injects. | Pure explanation |
| C3 | Fix the null dereference in this function. | Bug fix, no test involvement |

## Pass bar (AC7)

- At least **7 of 8** positive prompts invoke `style-testing`.
- At most **1 of 3** controls false-fires.
- Prompt 7 additionally invokes `style-rspec`; prompt 6 does not.

## Last run: 2026-07-22, PASS (8/8 positive, 0/3 control)

| Prompt | `style-testing` invoked | Also selected |
|---|---|---|
| 1 write unit tests for the leak checker | yes | `style-python` |
| 2 tests for parser error paths | yes | none (language unstated) |
| 3 intermittent CI failures | yes | `diagnose`, `quality-gates` |
| 4 review my test suite | yes | none |
| 5 what tests for a new endpoint | yes | none |
| 6 tests for a React hook | yes | `style-frontend`, correctly **not** `style-rspec` |
| 7 controller specs to request specs | yes | `style-rspec`, as required |
| 8 pytest coverage for billing | yes | none |
| C1 refactor the leak checker | no | `code-simplify` |
| C2 explain the SessionStart hook | no | none |
| C3 fix a null dereference | no | none |

Both bonus conditions held: prompt 7 pulled `style-rspec` alongside the core, prompt 6 did not.
Prompt 3 is the most informative pass, since it never uses the word "write" or names a framework
and still routed on the determinism language in the description.

## On failure

A miss is a defect in the **description**, not in the battery. Reword the frontmatter
`description` in `skills/style-testing/SKILL.md` and re-run. Do not lower the bar, and do not edit
a prompt to make it pass. Record which prompts missed, since the pattern says what the description
is failing to cover (an activity verb, a framework keyword, a review-versus-authoring framing).
