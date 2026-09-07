# 0008. Delegated work runs on a cheaper model, named per job

**Date:** 2026-09-06
**Status:** Accepted

## Context

An agent spends most of its work reading files and writing predictable output, not reasoning.
Both cost the same as reasoning when they run on the largest model.

Twelve of the fourteen files in `agents/` set `model: inherit`, so a subagent runs on whatever
the parent runs on. Derive the count with `grep -l '^model: inherit' agents/*.md | wc -l`. Only
`agents/product-analyst.md` and `agents/bulk-reader.md` name a model of their own.

The clearest case is `agents/quality-gates-orchestrator.md`.
[ADR 0002](0002-the-quality-gates-orchestrator-fans-out-to-blocking-subagents.md) gave it three
concurrent lanes. A lane runs test commands and returns rows, and it inherited the parent's model
to do that.

**The mechanism had no precedent here.** Frontmatter was the only proven form, and the lanes
cannot use it: the orchestrator never names a `subagent_type`, so each lane is a generic dispatch
with no agent file to carry a `model:` line. Whether an `Agent` tool call honors a `model`
parameter was unmeasured, and the answer changed the size of the work from a one-file edit into
an eight-file one.

### The measurement

`tadw-1hs` measured it on 2026-09-06 against Claude Code 2.1.263, copying the shape of ADR 0002's
spike. Two throwaway plugin agents ran under `claude -p --output-format stream-json`. Both
dispatched the same echo agent with the same prompt, and differed only in the parameter:

| Run | What the dispatch carried | The model that answered |
|---|---|---|
| Test | `{"subagent_type": "tadw:spike-model-echo", "model": "haiku", ...}` | `claude-haiku-4-5-20251001` |
| Control | `{"subagent_type": "tadw:spike-model-echo", ...}`, no `model` | `claude-opus-5[1m]` |

The transcript shows the `model` parameter inside a dispatch whose `parent_tool_use_id` is the
calling agent's own dispatch, so the call came from the plugin agent rather than from the session
that invoked it. That is the nesting test ADR 0002 Finding 1 used.

**The control is what makes the answer trustworthy.** The echo agent reports its own model, and a
model can be wrong about itself. It reported a different model in each run, and only the parameter
differed, so the change came from the parameter and not from the agent's guess.

**An `Agent` tool call honors a `model` parameter, including one made from inside a plugin agent.**

## Options Considered

### Option A: name a model per job, in whichever form the job allows

A dispatch that names a `subagent_type` sets `model:` in that agent's frontmatter. A generic
dispatch passes `model` on the `Agent` call. Choose the model from what the job actually does:
`haiku` when the work is reading or mechanical extraction, `sonnet` when the work includes a
judgment nobody downstream can check.

- **Pros:** Every delegated job pays for what it needs. The lanes stop running on the parent's
  model, which is the largest cost in a gate run. `bulk-reader` reads many files on `haiku` and
  returns bullets, so the files never enter the caller's context at all.
- **Cons:** Two forms to remember, and which one applies is a property of the call site rather
  than of the agent. A silently wrong model degrades output without erroring.

### Option B: run every lane on `haiku`

The cheapest option, and the obvious one for a worker that runs commands.

- **Pros:** Lowest cost. One rule, no per-job judgment.
- **Cons:** A lane does more than run a command. It grades Gate 2 change coverage, and it writes
  the Step 5 sentence saying whether a failure looks new. The orchestrator trusts a lane's rows as
  returned and has no way to detect a mis-graded one, so a cheaper judgment fails silently and
  reads as a passing gate.

### Option C: define three named lane agents, each with `model:` frontmatter

The fallback the measurement was run to avoid.

- **Pros:** Uses only the form that was already proven. The model lives next to the agent that
  uses it, where a reader looks for it.
- **Cons:** Three new agent files, three registrations in `AGENTS.md` and `README.md`, and three
  more names in the `quality-gates` family, which ADR 0002 already flagged as crowded. It also
  freezes the lane split into the filesystem, so changing which gates a lane owns becomes a file
  move.

### Option D: leave every agent on `inherit`

- **Pros:** Nothing to maintain, and no way to under-power a job.
- **Cons:** Every delegation costs the parent's rate, including the three lanes that exist
  precisely to keep test-runner output out of the parent's context.

## Decision

**Option A. Name a model per job, and choose it from what the job judges rather than from what it
costs.**

The rule that decides the model is: **a job whose output nobody downstream can check keeps its
judgment.** A lane grades coverage and no one re-grades it, so the lanes run on `sonnet`.
`bulk-reader` returns bullets the caller can check against the files it names, so it runs on
`haiku`.

`agents/quality-gates-orchestrator.md` states `model: "sonnet"` as a rule of the orchestrator and
carries it in the checklist, on the same terms ADR 0002 gave `run_in_background: false`. A check in
`hooks/test-hooks.js` pins it, so dropping it fails the push.

Option B lost on the silent-failure argument, not on quality in general. Option C lost because the
measurement removed its reason to exist. Option D lost to the cost it leaves on the table.

**`bulk-reader` orients, and never supplies the text an edit is based on.** Its answer carries no
reliable line numbers, so an edit built on it edits the wrong line. Every skill that routes
through it reads the specific file it is about to change. Its tools are `Read`, `Grep`, and `Glob`
alone: the tools list, not the prompt, is what stops it writing a file, because an agent cannot
call a tool it was never given.

**A `code-writer` worker is rejected for tests.** The idea was a cheap agent that writes a test
file from a specification, straight to disk, without the parent reading it.
`skills/feature-development/SKILL.md` writes a test per acceptance criterion and then runs a
simplify pass and a lint pass over what it wrote. Writing to disk unseen removes the step that
makes the output match the house style, which is this plugin's whole purpose. A narrower version,
limited to configuration stubs and type stubs, stays available as a later decision.

## Consequences

**Easier:**

- A gate run no longer pays the parent's rate for three lanes of test-runner output.
- A question about many files can be answered without those files entering the asking context.
- The mechanism is measured rather than assumed, so the next agent that wants a cheaper model has
  a proven form to copy and a control run to copy with it.

**Harder:**

- **The wrong model is a silent failure.** A lane on `haiku` returns rows in the right shape and
  grades them worse. Only the pinning check in `hooks/test-hooks.js` stands between an edit and
  that outcome.
- **Two forms, chosen by the call site.** A reader of `agents/quality-gates-orchestrator.md` finds
  the model in the prose rather than in the frontmatter, because a generic dispatch has no
  frontmatter to read.
- **The judgment rule needs applying by hand to each new agent.** "Can anyone downstream check
  this output" is a question, not a lookup.
- **Model names are a harness contract, not a repository one.** `sonnet` and `haiku` are aliases
  that a future release could repoint. The measurement pins Claude Code 2.1.263, as ADR 0002 pins
  2.1.239.
