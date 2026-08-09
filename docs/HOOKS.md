# Hooks

Design notes and rationale for the plugin's two hook features. `AGENTS.md` keeps only the
operational summary (what fires, the off-switches, the `node` requirement) and points here for
everything else.

Both features are wired through `hooks/style-core-hooks.json`, registered by the `hooks` field
in `.claude-plugin/plugin.json`. That field takes a single manifest path, so one file carries
both.

## Always-on style core

The plugin ships an always-on coding-style core via Claude Code lifecycle hooks. Unlike the
model-invoked style skills, this fires automatically, so the house style is present even when
the model would not have chosen to load a skill, and even inside spawned subagents (which never
inherit the parent session's loaded skills).

**What it injects.** The universal, language-agnostic core from `hooks/style-core.md` (TRUE
code, ten cross-language principles, and an American-English spelling rule that covers
identifiers, comments, docs, and commit messages, with an explicit carve-out for names you
do not own). The detailed per-language rules stay in the on-demand `style-*` and `review-*`
skills; only the small universal core is always on.

- **`SessionStart`** injects the core plus the response style, sourced from the
  `house-response-style` skill (`skills/house-response-style/SKILL.md`, frontmatter stripped
  at inject time). Injected as raw context into every new, resumed, cleared, compacted, **or
  forked** session (the matcher must list all five sources; omitting one silently skips
  injection for it, with no error and no marker). The same file backs the on-demand
  `/response-style` command, which **reads** it rather than invoking it through the Skill
  tool, so the always-on and invocable surfaces share one source of truth. The rules
  themselves live in the skill and are deliberately not restated here.
- **`SubagentStart`** re-injects the coding-style core only (JSON-wrapped in
  `hookSpecificOutput.additionalContext`) into every spawned subagent. The response style
  is deliberately parent-only: a subagent's final text is consumed by the orchestrator as
  data, so human-facing response rules would be noise there.

**Observability.** Each injected document opens with its own marker line
(`<!-- house-style-core: loaded -->`, `<!-- house-response-style: loaded -->`) so its
presence is visible in any session, not only in a one-time test.

**Off-switch.** Disable both surfaces with either:

- the environment variable `TADW_STYLE_CORE=off` (also accepts `0` / `false`); it inherits
  into the subagent hook process, so one setting covers both surfaces, or
- a persistent flag file at `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`.

**`node` on PATH requirement.** Both hooks run through `hooks/run-hook.sh`, which invokes `node`.
If `node` is not on the non-interactive shell's PATH (common for `fnm`/`nvm` users), the core
cannot be injected, and the wrapper makes that **visible rather than silent**: it emits
`<!-- house-style-core: FAILED to load ... -->` in place of the core (as valid
`hookSpecificOutput` JSON for `SubagentStart`). If you see that marker, the hook ran and could not
execute; if you see no marker at all, the hook did not run (check the matcher and the off-switch).
The wrapper always exits 0, so a failure never blocks the session.

**Why the off-switch is checked twice.** `run-hook.sh` re-implements `isDisabled()` from
`hooks/runtime.js`, because the off-switch has to be honored even when `node` cannot run, which
is exactly when the JS copy is unavailable. The wrapper checks it **before** spawning `node`, so
there is no node-missing path that skips it; an opted-out user gets silence, not a misleading
"FAILED to load" marker for something they turned off themselves. `test-hooks.js` asserts the two
implementations agree across a matrix of env values and the flag file, so the duplication cannot
drift unnoticed.

**No hook script may call `process.exit()`.** Node's stdout writes are synchronous on POSIX
pipes and **asynchronous on Windows pipes**, so an explicit exit can discard whatever has not
flushed yet. Every hook script keeps its work inside a `try`/`catch` and falls off the end
instead, which exits 0 anyway and flushes first. The rationale sits beside `writeHookOutput` in
`hooks/runtime.js`, where the writes happen. Nothing pins this yet: it is a convention held by
a comment, not by a check.

**Blast radius (behavior change).** Declaring `hooks` in `plugin.json` makes these hooks fire
in **every project** the plugin is loaded for, and (if distributed via the marketplace) for
**every consumer on upgrade**. The core fires in non-coding sessions too (product, research,
ASO), because a `SessionStart` hook cannot see the task type; the marker makes it self-evident
and the off-switch is the escape hatch.

**Test.** `node hooks/test-hooks.js` (Node built-ins only, no install) runs 16 checks: the
SessionStart raw output (both documents present, response style frontmatter stripped), the
SubagentStart JSON wrapping (response style absent), both off-switch paths, the **manifest**
(the matcher covers all five SessionStart sources, every referenced script exists, every
command routes through the wrapper with a fallback marker, and the Windows command honors both
off-switch paths, since it cannot be executed on a macOS or Linux runner and would otherwise
drift in silence), that `/response-style` reads the
skill file rather than invoking the disabled skill through the Skill tool, and four covering
`run-hook.sh`: it emits the marker when `node` fails, it stays silent when `node` fails *and*
the off-switch is set, it needs neither an external command nor `HOME`, and its off-switch
agrees with `runtime.js`. One check **executes the manifest commands themselves** against a
working and a broken `node`, because everything else tests the manifest as a string and the
wrapper as a program, never the two together, so a shell-quoting error would ship green. A final
check pins the **report-your-own-work** rule in both response-style sources (the skill and
`preamble.js`'s fallback): the no-jargon rule illustrated only words about system behavior, so
the words an agent uses for its *own* work read as allowed, and "the suite is green" or "that
was a flake" hides the very thing the reader needs (a test count; the argument for why a failure
is unrelated). Four more cover the **acceptance gate** (see below): it arms only on the
fresh-eyes review skills and refuses a session id that could escape the temp directory; its
`Stop` half blocks exactly once and disarms *before* it blocks; its off-switch is independent
of the style core's in both directions; and its manifest commands execute, degrading to
silence rather than to a partial decision when `node` is missing. The suite also asserts that
the count stated in this sentence matches the number
of checks it ran, since that number drifted three times while the suite was being written. Each
check was added after a real defect shipped green under a narrower suite: a matcher missing
`fork`, a dead `/response-style` command, a failure marker that ignored the off-switch, an
off-switch that silently stopped working when `tr` was off the PATH, and an agent reporting its
own work in shorthand the reader could not check.

## Acceptance gate

The same manifest wires a second, independent feature: a `PostToolUse` + `Stop` pair
(`hooks/acceptance-gate.js`) that chains the `verify-acceptance` skill onto the end of a
fresh-eyes review.

**Why two events.** Claude Code has no "slash command finished" event. `PostToolUse` on the
`Skill` tool fires when a skill is **loaded**, not when its work is done, so a check wired
there alone would grade the branch before a single file had been reviewed. `Stop` fires at the
right moment but cannot see what ran earlier in the turn. So `PostToolUse` (matcher `Skill`)
arms a per-session flag at `$TMPDIR/tadw-acceptance-<session_id>.flag` when `review-fresh-eyes`
or `fresh-eyes-cr` loads, and `Stop` consumes that flag and returns
`{"decision":"block"}` once, asking for the acceptance check before the turn ends.

**Loop safety** is the whole risk: a `Stop` hook that blocks and never disarms traps the
session, and a user cannot escape it from inside. Three guards, in order: the flag is deleted
**before** the block is emitted (load-bearing); `stop_hook_active` is honored; and any error
falls through to a silent `exit 0`. A flag older than 24 hours is discarded rather than spent,
so a session that died before its `Stop` fired cannot block an unrelated turn later.

**Not routed through `run-hook.sh`,** unlike the style hooks. That wrapper emits a visible
marker when `node` is missing, which is right for a document injected once per session and
wrong for a hook that fires on every `Skill` call and every stop. This gate degrades silently
on purpose.

**Off-switch,** independent of the style core's so that silencing one does not silence the
other: `TADW_ACCEPTANCE_GATE=off` (also `0` / `false`), or a flag file at
`${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-acceptance-gate-off`.

**Blast radius.** The `Stop` hook fires in every session in every project the plugin is loaded
for, but only speaks when the flag is armed, so a session that never runs a fresh-eyes review
never sees it.

**Test.** Three claims hide inside "the gate works," and they need different methods.

1. *The gate arms and blocks.* Deterministic. `node hooks/test-hooks.js` covers it from inside
   the suite (checks 12-15). `./hooks/manual-gate-test.sh` drives the same sequence from
   outside, with the real hook payloads: arming is silent, the flag appears, `Stop` emits
   `decision=block` naming `verify-acceptance`, the second `Stop` is silent because the block
   consumed the flag, and a 25-hour-old flag is discarded rather than spent. It points `TMPDIR`
   at a scratch directory removed on exit, so it cannot touch a live session's flag, and it
   exits non-zero on any failure. Reach for it when the gate misbehaves in a live session and
   you need to see which step diverges.
2. *Claude Code fires the hooks.* Needs the plugin installed with this manifest, which the
   working tree alone does not give you. Run `claude --debug hooks`, invoke `/fresh-eyes-cr`,
   and watch for `$TMPDIR/tadw-acceptance-<session-id>.flag` and then the block.
3. *The model complies.* Not deterministic. Read the transcript. Two failure modes: it
   acknowledges the block without loading the skill, or it re-runs the fresh-eyes review.

The gate must ship in the same version as the `verify-acceptance` skill. Released apart, it
blocks every fresh-eyes turn asking for a skill that is not installed, and the loop-safety
guards do not help, because that block is still well formed.
