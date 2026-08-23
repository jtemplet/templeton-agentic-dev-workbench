# Evals

For the method behind this suite, and for how to extend it to other skills, commands, and
agents, open [docs/eval-driven-development.html](../docs/eval-driven-development.html). This
file covers only what is here today.

An eval is a test for behavior that has no single correct output. A unit test asserts
`add(2, 2) == 4`. You cannot assert that on a written answer, because a thousand different
sentences are all correct. So instead of comparing the output to one expected string, an
eval scores it against a rule.

Every eval has the same four parts:

1. **A prompt.** A fixed question you send to the model.
2. **An arm.** The configuration under test. Here that means "with the plugin loaded"
   against "without it", so you can tell whether the plugin changed anything.
3. **A grader.** The thing that decides pass or fail. It is either deterministic (a
   script) or a judge (a second model call that reads the answer and rules on it).
4. **Runs.** The same prompt sent more than once, because the model is not deterministic.
   One passing run proves nothing. Three tell you whether it is reliable.

## Why these evals are deterministic

Most of the response-style rules are mechanically checkable, so no judge is needed:

| Rule | How it is graded |
|---|---|
| No borrowed metaphors | The word "tombstone" is either in the output or it is not |
| Decision matrix when required | A markdown table is either present or it is not |
| No matrix for an obvious call | Same check, inverted |
| Sentence length limits | Count the words between sentence endings |
| Technical names kept exact | The literal string `TADW_STYLE_CORE=off` appears |
| Plain self-reporting | The count, the re-run, and the reason are present, and no label appears without them |

**One grader is conditional.** `forbid_label_alone` fails a label only when a fact it stands
for is missing. It takes a `pattern` and an `unless_all` list, and passes when the pattern is
absent, or when the pattern appears and every `unless_all` pattern also appears. It exists
because a flat ban on "flake" and "green" failed 14 of 14 runs across three versions of the
skill, while those same runs carried the count, the re-run, and the reason every time. A
grader that fails a complete report measures the vocabulary, not the rule.

**One grader is deliberately looser than its rule.** The skill states a 25-word sentence
limit; `max_sentence_words` fails only above 35. Measured, the model does not hold 25 on an
explanation carrying a three-item list, and a check that can never pass stops being run. So
the grader is a ceiling on runaway sentences, not a restatement of the target: it catches the
39-word case this suite has produced, and 25 stays the number to write toward. Keep the
tighter number in the rule and the looser one in the grader.

## Current state

**13 of 18 runs pass** (2026-08-05, `--runs 3`, sonnet, with-plugin arm only), measured
before `self-report-plainly` was changed to `forbid_label_alone`. `decision-matrix-trigger`,
`exact-names`, and `jargon-tombstone` pass 3 of 3. `decision-matrix-suppress` and
`plain-sentences` pass 2 of 3. `self-report-plainly` passed 0 of 3, and 0 of 5 on a longer
re-run.

An earlier line here claimed 15 of 18 with five cases at 3 of 3, and that claim did not
survive re-measurement: the same three hard cases scored 2 of 9 against the tree it described.
Treat any number in this section as stale until you re-run it.

**`self-report-plainly` drove a rule change, not a grader change.** Across three versions of
the skill, 14 of 14 runs used "flake", "flaky", or "green". Every one of those runs also gave
the count, said the test was run again, and said the change touches no JavaScript file. So the
harm the ban was written to prevent, a label swallowing the argument, never occurred. The rule
now forbids the label only where a fact it stands for is missing, and the grader follows it.
That is the one legitimate reason to move a bar: the measurement showed the bar was in the
wrong place. Loosening a grader because a rule is inconvenient is still how a suite stops
measuring anything.

**Which account answers.** `run.py` builds the environment for each `claude -p` call instead of
inheriting yours, and drops the five variables in `REDIRECTING_VARS` on the way. So the suite
measures the account you are logged into, whatever your shell was last switched to. A set
`ANTHROPIC_API_KEY` used to fail all twelve calls at `invocation` with a connectors warning that
read like a style regression; Bedrock routing was worse, because it completed and measured
somewhere else without saying so.

A deterministic grader is free, instant, and never flaky. Reach for a model judge only for
a rule you genuinely cannot express as a pattern, such as "is the tone right". None of the
rules here need one.

## Why a local runner

The official harness, `claude plugin eval`, is in early access and does not run on this
machine yet. `evals/run.py` does the same job with the standard library only. It runs each
prompt through `claude -p --plugin-dir <repo>`, which loads the plugin **from this working
tree** rather than from the installed cache under `~/.claude/plugins/cache/`. That matters:
without `--plugin-dir`, you would be testing the last released version and not your edits.

## Running them

```bash
# every case, both arms, 1 run each
python3 evals/run.py

# one case, 3 runs, on the model you actually use
python3 evals/run.py --case decision-matrix-trigger --runs 3 --model opus

# skip the no-plugin baseline (faster, but you lose the comparison)
python3 evals/run.py --no-baseline
```

Each run is a real model call and costs real money. Start with `--model haiku` to confirm
the plumbing works, then re-run on the model you use day to day. A style rule that a large
model follows and a small one ignores is still worth knowing about.

## Reading the output

`with-plugin` is the arm that has the style loaded. `baseline` is the same prompt with no
plugin. The number that matters is the gap between them. If both arms score the same, the
rule was already the model's default and the instruction is doing nothing. If the baseline
fails and the with-plugin arm passes, the rule is earning its place.

## Adding a case

Create `evals/cases/<name>/case.json`:

```json
{
  "prompt": "The question to ask.",
  "why": "Which rule this is testing, in one line.",
  "checks": {
    "forbid_regex":  [{"pattern": "tombstone", "why": "borrowed metaphor"}],
    "require_regex": [{"pattern": "deleted",   "why": "must name the real behavior"}],
    "require_markdown_table": true,
    "forbid_markdown_table": false,
    "max_sentence_words": 25
  }
}
```

Every field under `checks` is optional. Omit what does not apply. Patterns are Python
regular expressions, matched case-insensitively against the answer.

**Always include at least one negative case.** `decision-matrix-suppress` exists so that
"always draw a table" fails the suite. Without it, a model that tables everything would
score perfectly and you would never learn that it over-applies the rule.

## Testing a skill against a planted defect

The six response-style cases ask a question and grade the prose. Testing a skill such as
`quality-gates` needs the opposite: a repository with a specific defect in it, and an
assertion about what the skill reports. Two optional keys do that, and both default to the
old behavior, so a case that omits them runs exactly as before.

```json
{
  "prompt": "/quality-gates",
  "why": "An all-skip run must report NO GATES RAN, never PASS.",
  "fixture": "gates-all-skip",
  "single_arm": true,
  "checks": {
    "require_regex": [{"pattern": "NO GATES RAN", "why": "the verdict rule under test"}],
    "forbid_regex":  [{"pattern": "Overall: PASS", "why": "an all-skip run proves nothing"}]
  }
}
```

**`fixture`** names a directory under `evals/fixtures/`. The harness builds a throwaway
repository from it under your temp directory and runs the model there instead of here.
`--plugin-dir` still points at this working tree, so the plugin under test is your edits;
only the repository the model looks at changes.

A fixture holds up to two parts:

| Directory | What happens to it |
|---|---|
| `base/` | Required. Copied in, committed as the one initial commit, and pushed to a bare origin beside the checkout |
| `plant/` | Optional. Copied over the tree afterward and left **uncommitted** |

**The split is the point.** A skill that scopes itself to the change compares the working
tree against `origin/main`. A defect committed into `base/` would sit in the baseline, and
the gate would correctly report nothing. So `base/` is the repository as it was, and
`plant/` is the change under judgment. Put a `pyproject.toml` that configures an absent
type checker in `base/`; put the untested function or the fake key in `plant/`.

The bare origin exists for the same reason. Without `origin/main`,
`skills/quality-gates/scripts/changed_set.py` exits 3, and the skill widens every gate to
`--all`, so a scoped run cannot be tested at all.

Each **run** gets its own copy, not each case. A skill can write into the tree it graded:
`quality-gates` records its verdict at `<git-dir>/quality-gates-report.json`, and a second
run sharing that tree could read the first run's answer instead of producing its own. Pass
`--keep-fixtures` to leave each one on disk, with its path printed, which is how you inspect
a case that failed for an unclear reason.

**`single_arm`** runs the with-plugin arm only. Fixture cases want it, because their prompt
is usually a slash command: `/quality-gates` does not exist without the plugin, so the
baseline arm would measure nothing and would double the cost of every run. That is D7 in
`docs/plans/quality-gates-hardening.md`. It is opt-in, so a case that omits it, or sets it
to `false`, still runs both arms.

A misnamed fixture is caught when the cases load, before any model call, since a typo should
cost an error rather than the price of a run against the wrong directory.

`evals/test_run.py` pins all of the above and calls no model, so it is free to run.

## Known limits

- `max_sentence_words` strips fenced code blocks, inline code, and table rows before
  counting, but it splits sentences on `.`, `!`, and `?`, so an abbreviation inside a
  sentence can split it early. It is a smoke detector, not a linter.
- One run per case is the default because it is cheap. It is not enough to call a rule
  reliable. Use `--runs 3` before you trust a result.
- The baseline arm still loads this repository's `CLAUDE.md` and `AGENTS.md` as project
  context, because that is project context and not plugin context. The arms differ only by
  the plugin, which is what you want, but neither arm is a blank slate.
