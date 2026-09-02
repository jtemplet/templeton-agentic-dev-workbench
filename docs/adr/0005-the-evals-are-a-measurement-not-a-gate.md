# 0005. The evals are a measurement, not a gate

**Date:** 2026-09-01
**Status:** Accepted

## Context

`evals/` holds a response-style eval harness. It runs 6 cases in `evals/cases/` across two arms,
one with the plugin loaded and one with no plugin at all. The gap between the arms is the
measurement. That is 12 real model calls per run, taking several minutes.

The obvious thing to do with a test suite is to gate on it. This one is excluded from the ship
gate, from `.githooks/pre-push`, and from CI, and the exclusion needs a reason on record, because
it looks like an oversight.

The reason is that the cases are graded against model prose, so they are not deterministic. The
`plain-sentences` case measures sentence length against a 35-word ceiling. Runs on 2026-08-22 and
2026-08-23 produced these longest-sentence figures for the same case and the same prompt:

| Run | Longest sentence |
|---|---|
| 1 | 40 words |
| 2 | 38 words |
| 3 | 37 words |
| 4 | 34 words |
| 5 | 26 words |
| 6 | 22 words |

Three of six exceed the ceiling and three do not. Nothing changed between runs but the model's
sampling.

A second suite sits next to it. `evals/test_run.py` tests the harness itself, calls no model, and
costs about 2 seconds. Cost is not why that one left the git hooks.

## Options Considered

### Option A: Exclude the evals from every gate; run them deliberately

Keep `python3 evals/test_run.py` in the check list so the harness stays tested, and keep
`python3 evals/run.py` out of every hook and out of the ship gate. Run it when you want to
measure whether the style rules still change the model's behavior, and read the delta between
the arms rather than a pass or a fail.

- **Pros:** No gate fails at random. The measurement stays honest, because nobody is under
  pressure to make it green. The harness is still protected by its own deterministic suite.
- **Cons:** A regression in the style rules can land unnoticed, since nothing runs the eval
  automatically. Somebody has to remember to measure.

### Option B: Gate on the evals

Add `python3 evals/run.py` to the check list and let a failing case refuse the push.

- **Pros:** The style rules get automatic protection. A regression cannot land silently.
- **Cons:** By the table above, this gate fails about half the time on an unchanged tree. The
  learned response to a gate that fails at random is to re-run it until it passes, and a gate
  people re-run until green means nothing. It also puts 12 model calls and several minutes into
  every push.

### Option C: Loosen the thresholds until the evals pass reliably

Raise the 35-word ceiling, or grade on an average across runs, so the suite is stable enough to
gate on.

- **Pros:** Keeps automatic protection without the flakiness.
- **Cons:** A threshold set where the model already lands measures nothing. The 35-word ceiling
  exists because it is the rule the style document states; moving it to fit observed behavior
  inverts the purpose. Averaging hides the case the eval was built to catch.

## Decision

**Option A. The evals are a measurement you run deliberately, never a gate.**

`python3 evals/run.py` stays in the "Commands for This Repo" list in AGENTS.md, so it is
discoverable, and stays out of the ship gate, which is defined as that list minus this one
command. No git hook runs anything under `evals/`.

`python3 evals/test_run.py` stays in the check list. It tests the harness, calls no model, and is
deterministic, so it has none of the properties that disqualify the other one.

**Read the delta between the two arms, not a pass or a fail.** The question the harness answers
is whether the style rules still change what the model does, and that question has a magnitude
for an answer, not a boolean.

Option B lost on the same reasoning as [ADR 0004](0004-the-pre-push-hook-forgives-by-design.md):
a check that people learn to bypass protects nothing, and randomness teaches bypassing faster
than strictness does. Option C lost because a threshold tuned to observed behavior stops being a
standard and becomes a description.

## Consequences

**Easier:**

- Every gate in this repository is deterministic. A red gate always means something is wrong,
  which is what makes a red gate worth reading.
- A push costs no model calls and no minutes of waiting.
- The eval can report an uncomfortable result without anybody being tempted to soften it, because
  nothing is blocked by the answer.

**Harder:**

- A regression in the style rules can land and stay landed. Nothing catches it until somebody
  runs the measurement.
- Running the evals is a decision somebody has to make. In practice that means after a
  substantial edit to `hooks/style-core.md` or the `house-response-style` skill, which is exactly
  when it is easiest to forget.
- Each run costs 12 real model calls, so measuring is not free and will not be done casually.
- The distinction between the two suites has to be maintained. Adding a model call to
  `test_run.py` would quietly move it into the category this record excludes.
