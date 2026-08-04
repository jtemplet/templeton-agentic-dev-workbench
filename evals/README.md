# Evals

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

## Known limits

- `max_sentence_words` strips fenced code blocks, inline code, and table rows before
  counting, but it splits sentences on `.`, `!`, and `?`, so an abbreviation inside a
  sentence can split it early. It is a smoke detector, not a linter.
- One run per case is the default because it is cheap. It is not enough to call a rule
  reliable. Use `--runs 3` before you trust a result.
- The baseline arm still loads this repository's `CLAUDE.md` and `AGENTS.md` as project
  context, because that is project context and not plugin context. The arms differ only by
  the plugin, which is what you want, but neither arm is a blank slate.
