# Hooks

Design notes and rationale for the plugin's hook feature. `AGENTS.md` keeps only the
operational summary (what fires, the off-switch, the `node` requirement) and points here for
everything else.

It is wired through `hooks/style-core-hooks.json`, registered by the `hooks` field in
`.claude-plugin/plugin.json`. That field takes a single manifest path.

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

**Output size, and why `SessionStart` is wired as three entries.** Claude Code caps every
hook output string at **10,000 characters**. The cap applies to plain stdout and to
`hookSpecificOutput.additionalContext` alike, so no output format avoids it. Anything longer
is written to a file and replaced with a short preview plus that path.

The combined payload is 19,996 characters (style core 4,499, response style 15,495), almost
exactly twice the cap. Under a single entry the session received the first ~2,000 characters
and a file path. The coding core arrived truncated after principle 4, and **the response style
never arrived at all**.

That failure was invisible from inside a session, and this is the part worth remembering. The
style core's marker sits at byte 5, inside the surviving preview, so a session looked correctly
loaded. The response style's marker sits at byte 4,507, inside the discarded remainder. The one
signal designed to prove the injection worked was the one signal the truncation could not
reach.

The fix is to split, not to shrink. Because the cap is per output and Claude receives the
`additionalContext` of every hook that matched the event, the payload ships from several
manifest entries that differ only in a payload index:

| Entry | Payload | Characters |
|---|---|---|
| 0 | Coding-style core | 4,499 |
| 1 | Response style, part 1 | 9,854 |
| 2 | Response style, part 2 | 5,777 |

`getSessionStartPayloads()` in `hooks/preamble.js` decides the split at run time, cutting on
line boundaries and naming the resumed section in each continuation marker. Nothing is
hand-maintained, so editing the skill re-splits it automatically. Two checks hold the seam
shut: every payload must fit the cap, and the manifest must wire exactly one entry per
payload. Grow the documents by one part without adding an entry and the suite fails rather
than dropping the tail in silence.

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

**Test.** `node hooks/test-hooks.js` (Node built-ins only, no install) runs 18 checks: the
SessionStart raw output across every indexed entry (both documents present, the parts
reassembling to the whole response style, an out-of-range index silent, response style
frontmatter stripped), the two that hold the split shut (every payload inside the
10,000-character cap, and one manifest entry per payload with its own index), the
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
is unrelated). Three cover **repository
structure**, added after a `/quality-gates` run found nothing enforcing them: `AGENTS.md`
registers every skill, agent, and command on disk with a count that matches; `README.md`
mentions every skill and agent (commands are out of scope, since several are aliases for a
differently-named skill and README groups them by topic); and every `bash` block in a skill or
command parses under `bash -n`, skipping blocks that carry a `<placeholder>` because those are
templates rather than scripts. That last one caught a Terraform `resource` block fenced as
`bash`. It would not have caught the three snippet bugs that prompted it, all of which were
syntactically valid; only executing a snippet finds those. The suite also asserts that
the count stated in this sentence matches the number
of checks it ran, since that number drifted three times while the suite was being written. Each
check was added after a real defect shipped green under a narrower suite: a matcher missing
`fork`, a dead `/response-style` command, a failure marker that ignored the off-switch, an
off-switch that silently stopped working when `tr` was off the PATH, and an agent reporting its
own work in shorthand the reader could not check.
