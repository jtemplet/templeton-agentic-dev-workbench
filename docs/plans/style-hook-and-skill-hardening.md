# Upgrade templeton-agentic-dev-workbench: always-on style hook + skill hardening

## Context

**The problem.** The `templeton-agentic-dev-workbench` plugin ships your preferred coding
style (TRUE code, wait-for-duplication, small focused units, composition over inheritance)
as *model-invoked skills* (`templeton-python-style`, `templeton-frontend-style`, etc.). A
model-invoked skill loads only when the agent reads its `description:` and decides on its own
that it is relevant. That decision is inconsistent, especially in long sessions and inside
spawned subagents (which never inherit the parent's loaded skills). Result: your house style
is applied unevenly.

**The reference fix.** The `ponytail` plugin solves the same class of problem with *always-on
lifecycle hooks*: a `SessionStart` hook injects its ruleset into every session, and a
`SubagentStart` hook re-injects it into every spawned subagent. The text is physically
prepended to context every cycle, so the agent cannot drift. We will replicate that harness
(Claude Code only) for the *universal* coding-style core.

**The intended outcome.**

1. The small, language-agnostic coding-style **core** is injected on every session and every
   subagent automatically (no reliance on the model choosing to load it).
2. The coding skills (style + review) are deep-rewritten to a consistent, rigorous structure.
3. The 9 highest-signal skills are renamed with functional prefixes (`style-*`, `review-*`)
   for clarity; already-prefixed skills are left alone to avoid pointless churn.

**Decisions already made (do not re-litigate):**

- Hook scope: **Claude Code only** (no Codex/Copilot/AGENTS-adapter wiring in the hooks).
- Rename set: **9 high-signal skills only** (the 6 style + 3 review skills). Keep `product-*`,
  `plan-*`, `*-audit`, `ux-*`, `research-ingest`, `code-simplify`, `idea-wizard`,
  `feature-development`, `terraform-iac-expert`, `agentic-clean-code`,
  `architecture-decision-record` as-is.
- Hardening: **deep rewrite** of the coding skills to a shared skeleton.
- Anti-drift: **core injected, skills are deltas.** `hooks/style-core.md` holds the universal
  principles (injected). Each style skill points at it and contains only language-specific
  deltas. No duplication, so drift is structurally impossible.
- Observability: **the injected preamble opens with a visible marker line** (e.g.
  `<!-- house-style-core: loaded -->` plus a short human header) so presence is observable in
  any session, not only in the one-time smoke test. (We deliberately drop ponytail's statusline
  badge to stay Claude-only and minimal; the marker is the cheaper substitute.)
- Scope of injection: **the core fires in every session, including non-coding ones** (product,
  research, ASO), because a `SessionStart` hook cannot see the task type. Accepted on purpose:
  the core is a short screenful and the marker makes it self-evidently a coding-style note. The
  off-switch (below) is the escape hatch for sessions where it is noise.
- Blast radius: declaring `hooks` in `plugin.json` makes the hook fire in **every project** the
  plugin is loaded for, and (if distributed via the marketplace) for **every consumer on
  upgrade**. This is a behavior change that must be called out in the README / a CHANGELOG note.

> Answer to your direct question ("is it OK that all my skills are lumped together if we add the
> hook, or should I separate them?"): **Separation by *delivery mechanism* is the real win, not
> tidiness.** You cannot inject all 30 skills into every session, that is massive, mostly-irrelevant
> context. Only the universal style core belongs in the always-on hook. Everything task-specific
> (review, plan review, product, research, audits, and the *detailed* per-language style rules)
> stays as on-demand skills because it is invoked deliberately. The flat `skills/` layout is
> required by Claude's loader anyway (it only discovers `skills/<name>/SKILL.md`); functional
> *naming* + AGENTS.md sections give the grouping. So: keep them in one flat dir, group by prefix,
> and lift just the core into the hook.

## Work on a feature branch

`git checkout -b feat/style-hook-and-skill-hardening`. The rename churn touches ~15 files plus
two large docs; a branch keeps `main` clean and makes the whole upgrade one revertible unit.
Commit per phase (each phase is independently revertible). Slash command names never change, so
there is no downstream breakage for existing muscle memory.

**Step 1 (before Phase 0):** create the branch, then copy this finalized plan into the repo at
`docs/plans/style-hook-and-skill-hardening.md` (the repo's existing plan convention, written by
the `feature-planner` agent and read by `plan-review`). Commit: "Add implementation plan for
style-core hooks + skill hardening." All subsequent phases build on that branch.

---

## Phase 0 - Baseline + capability verification (gate)

- **Verify `SubagentStart` is a supported hook event** in the user's Claude Code version before
  building on it. The whole subagent-reliability half of this upgrade depends on it, and because
  the hook scripts swallow errors and `exit 0`, a non-firing event fails **silently** (no error,
  just no injection). Confirm via the Claude Code hooks docs / `/hooks` for this version, or by a
  throwaway echo hook on `SubagentStart` that writes a sentinel and spawning a subagent to see it
  fire. If `SubagentStart` is unavailable, stop and revise (the session-only half still works,
  but the plan's core promise does not).
- **Confirm what `/validate-plugin` actually checks.** Read `commands/validate-plugin.md` (and any
  backing script) and verify it cross-references skill *names* across agents/commands and checks
  doc alignment. The rename phase leans on this as a safety net; if it does not do cross-reference
  / doc-alignment, the net is the explicit `grep` in Phase 3, not `/validate-plugin`.
- Run `/validate-plugin` on the clean tree to capture a known-good baseline. It will already
  flag a **pre-existing bug**: `commands/rails-code-review.md` (lines 5, 33) references a
  `rails-code-reviewer` *agent* that does not exist (no `agents/rails-code-reviewer.md`).
- Run `bash lint.sh` (runs `rumdl fmt .` in place) so the tree is formatting-clean before edits,
  making later diffs pure content.

---

## Phase 1 - Deep-rewrite the coding skills (under current names, before any rename)

Rewrite the bodies in place under their *current* names. Doing the rewrite before the rename
keeps diffs readable (renaming + rewriting in one commit is unreviewable).

**Skills to rewrite (Tier 1 first):**

- Style/convention authorities: `templeton-python-style`, `templeton-frontend-style`,
  `templeton-swift-style`, `templeton-rspec-style`, `rails-conventions`, `fizzy-style`.
- Review skills: `python-code-review`, `rails-code-review`, `fresh-eyes-review`,
  `terraform-iac-expert`.
- Code-action workflows: `code-simplify`, `feature-development`.
- Light touch (already strong): `agentic-clean-code`.

**Shared skeleton for every style/review skill:**

```text
## When to Use / When NOT to Use      # explicit triggers + non-triggers (stops over/under-firing)
## Universal Core (injected)          # one-line pointer to hooks/style-core.md; NOT duplicated
## Language/Domain Principles         # the deltas: numbered, imperative ("Do X", "Never Y")
## Anti-Patterns                      # each: bad example -> why -> corrected example
## Worked Examples                    # 1-2 full before/after with rationale
## Review/Apply Workflow              # ordered steps
## Output Format                      # exact report template (review skills)
## Quality Checklist                  # pre-completion verification
```

Enforce: imperative voice, every principle paired with a concrete anti-pattern + fix,
standardized review severity (CRITICAL/HIGH/MEDIUM/LOW, with the existing "if tests pass, max
MEDIUM" rule from AGENTS.md).

**Produce the final delta-structured skills in this phase (not Phase 4).** Since the rewrite is
already touching every body, write each style skill in its final shape now: the "Universal Core
(injected)" section is a one-line pointer to `hooks/style-core.md`, and the body carries only the
language-specific deltas, no duplicated universal principles. Phase 4 then touches *docs only*,
never skill bodies. (This removes the Phase-1/Phase-4 ownership overlap the review flagged.)

**Draft `hooks/style-core.md` content as part of this phase:** distill the universal principles
shared across the four style skills (TRUE code; rule-of-three / wait-for-duplication; small
focused units; Tell-Don't-Ask; composition over inheritance; fail-fast / explicit errors;
step-down readability; self-documenting names over comments). Short (a screenful), imperative,
language-agnostic. Open it with the observability marker (`<!-- house-style-core: loaded -->` +
a short human header). This becomes the injected text in Phase 2. Note: `agentic-clean-code` is
about *building agents*, not human code style, so it does **not** seed the core.

**Done-definition for the rewrite (quality gate, not just structural):** every style/review skill
must have (a) a non-empty "When to Use / When NOT to Use" with at least one explicit non-trigger,
(b) the injected-core pointer instead of duplicated principles, (c) every numbered principle
paired with a concrete anti-pattern + corrected fix, and (d) at least one full before/after
worked example. Review skills additionally must carry the exact Output Format template and the
standardized severity scale. A skill missing any of these is not done.

**Gate:** the done-definition above (self-check each skill) + `bash lint.sh` + `/validate-plugin`.
Commit: "Deep-rewrite coding skills as delta-structured; extract universal style core."

---

## Phase 2 - Add the Claude-only hook harness (additive, low-risk)

Create `hooks/` mirroring ponytail's harness, stripped of Codex/Copilot and all mode logic.

**Files to create:**

| File | Responsibility |
|---|---|
| `hooks/style-core.md` | The canonical injected text (from Phase 1). Single source of truth. Plain markdown, no frontmatter. **First line is the observability marker** (`<!-- house-style-core: loaded -->` + a one-line human header) so its presence is visible in-session. |
| `hooks/preamble.js` | `getStyleCorePreamble()`: read `style-core.md`, return string. try/catch with a small hardcoded fallback so a missing file never blanks the hook. |
| `hooks/runtime.js` | `isDisabled()` (off-switch) + `writeHookOutput(event, context)`. **Load-bearing format rule:** `SessionStart` -> raw `process.stdout.write(context)`; `SubagentStart` -> `process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: "SubagentStart", additionalContext: context } }))`. If the SubagentStart output is not JSON-wrapped, native Claude silently drops the context. |
| `hooks/session-start.js` | `if (isDisabled()) exit(0); else writeHookOutput('SessionStart', getStyleCorePreamble())`, wrapped in try/catch, `exit 0`. |
| `hooks/subagent-start.js` | Identical guard + `writeHookOutput('SubagentStart', ...)`. The off-switch check **must** run here too. |
| `hooks/style-core-hooks.json` | The manifest. Wires `SessionStart` (matcher `startup\|resume\|clear\|compact`) and `SubagentStart` (no matcher) to the two scripts. Use ponytail's `node "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.js"; exit 0` form + the `commandWindows` `Get-Command node` guard + `timeout: 5` + `statusMessage`. Omit `UserPromptSubmit` (that was ponytail's mode tracker; no modes here). |
| `hooks/test-hooks.js` | Standalone `node:child_process` spawnSync + `node:assert` test (no deps, no package.json). Asserts: SessionStart stdout = raw preamble (contains the marker phrase); SubagentStart stdout parses as JSON and `hookSpecificOutput.additionalContext` contains the preamble; with `TADW_STYLE_CORE=off` in env, both emit empty stdout; **with the flag file present (and env unset), both emit empty stdout** (covers the flag-file path, which env-var tests miss). Run with `node hooks/test-hooks.js`. |

**Off-switch:** primary env var `TADW_STYLE_CORE=off` (also `0`/`false`); optional persistent
flag file at `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`. The env var inherits into
the subagent hook process (same process tree), so one setting disables both surfaces. Resolve the
flag-file path identically in both scripts (centralize in `runtime.js`). **Both off-switch paths
must be covered by `test-hooks.js`**; if the flag file feels like unneeded surface, drop it and
keep the env var alone rather than shipping it untested.

**plugin.json edit:** add `"hooks": "./hooks/style-core-hooks.json"` and bump `version`
`1.12.0` -> `1.13.0`.

**Gate:** `node hooks/test-hooks.js` (must pass, especially the SubagentStart JSON-wrap and
off-switch cases) + `/validate-plugin`. Commit: "Add Claude-only style-core hooks (SessionStart + SubagentStart)."

---

## Phase 3 - Rename the 9 high-signal skills (riskiest phase)

Rename map:

| Current | New |
|---|---|
| `templeton-python-style` | `style-python` |
| `templeton-frontend-style` | `style-frontend` |
| `templeton-swift-style` | `style-swift` |
| `templeton-rspec-style` | `style-rspec` |
| `rails-conventions` | `style-rails` |
| `fizzy-style` | `style-fizzy` |
| `python-code-review` | `review-python` |
| `rails-code-review` | `review-rails` |
| `fresh-eyes-review` | `review-fresh-eyes` |

For **each** skill, one at a time:

1. `git mv skills/<old> skills/<new>` (preserves history).
2. Update its own `SKILL.md` frontmatter `name: <old>` -> `name: <new>` (the dir==name invariant
   is enforced by validate-plugin check #4; it holds for all 9 today).
3. Update every external reference, then assert `grep -rn '<old>' agents commands skills/*/SKILL.md AGENTS.md README.md` returns zero (ignore command self-refs like the `/rails-code-review` slash name, which is a command, not a skill).

**Reference-update checklist (where the 9 names appear):**

- **Agents:** `agents/code-reviewer.md` (frontmatter description list + body extension->skill
  table); `agents/software-engineer.md` (frontmatter description + body routing to the style
  skills + the `fresh-eyes-review`/`code-simplify` mentions).
- **Commands (filenames/slash names stay; only in-body skill names change):**
  `commands/python-code-review.md`, `commands/rails-code-review.md`,
  `commands/swift-code-review.md`, `commands/frontend-code-review.md`, `commands/code-review.md`,
  `commands/fresh-eyes-cr.md`, `commands/python-feature-dev.md`.
- **Cross-skill references (easy to miss):**
  - `skills/code-simplify/SKILL.md` routing table (line ~44): `templeton-python-style`,
    `rails-conventions`, `fizzy-style`, `templeton-frontend-style`, `templeton-swift-style`
    (+ the description on line 3).
  - `skills/feature-development/SKILL.md` routing table (line ~76) + description (line 3): the
    four style skills incl. `rails-conventions`.
- **Docs (this phase owns NAME REPLACEMENT only):** in `AGENTS.md` (Registered Skills list, agent
  descriptions, Language-Specific Workflows prose for Python/Rails/Swift/Frontend) and `README.md`
  (Skills table + Agents table + pipeline prose), replace old skill names with new ones. Highest
  miss-risk surfaces; grep each old name explicitly. (Phase 4 owns *new doc sections*, not name
  edits, so the two passes do not collide.)

**Fix the pre-existing bug here:** rewrite `commands/rails-code-review.md` lines 5 and 33 to
reference the `review-rails` *skill* (not the nonexistent `rails-code-reviewer` agent).

**Naming note:** `rails-conventions` -> `style-rails` is chosen for routing symmetry (it is the
Ruby target in `code-simplify`/`feature-development`/`software-engineer`). Accept the slight
semantic shift from "conventions" to "style."

**Gate:** dir==frontmatter check (`for d in skills/*/; do n=$(basename $d); fm=$(grep -m1 '^name:'
"$d/SKILL.md" | sed 's/name: *//'); [ "$n" = "$fm" ] || echo "MISMATCH $n"; done`) + `bash lint.sh`

- `/validate-plugin` (checks #2 cross-references and #5 doc alignment are the safety net). Commit:
"Rename style/review skills with functional prefixes; update all references; fix ghost agent ref."

---

## Phase 4 - Document the hooks (docs-only; skill bodies were finalized in Phase 1)

Skill bodies are already delta-structured and pointing at `hooks/style-core.md` (done in Phase 1),
and their names were replaced in docs (done in Phase 3). This phase adds *new doc sections* only:

- **AGENTS.md:** add an "Always-on style core (hooks)" section: what it injects, the marker line,
  the off-switch (env var + flag file), the `node`-on-PATH requirement, the global/marketplace
  blast radius, and the `node hooks/test-hooks.js` test command.
- **README.md:** add a hooks section documenting the off-switch and the **node PATH dependency**
  (see Risks), plus a CHANGELOG/behavior-change note that loading this version makes the style
  core fire in every session.

**Gate:** `bash lint.sh` + `/validate-plugin`. Commit: "Document always-on style core hooks (behavior change + off-switch)."

---

## Phase 5 - Final verification + land

- `/validate-plugin` (expect PASS; the ghost-agent finding should now be resolved).
- `node hooks/test-hooks.js` once more.
- `rumdl fmt --check .` to confirm no pending formatting (non-mutating check).
- **End-to-end smoke test of the hook (the whole point of the upgrade):**
  - SessionStart: `node hooks/session-start.js` -> stdout is the raw `style-core.md` text.
  - SubagentStart: `node hooks/subagent-start.js | python3 -m json.tool` -> valid JSON with
    `hookSpecificOutput.additionalContext` = the core text.
  - Off-switch: `TADW_STYLE_CORE=off node hooks/session-start.js` -> empty stdout.
- **HARD GATE - live subagent injection (do not skip; this is the upgrade's core promise).**
  Start a fresh Claude Code session in a scratch repo with the plugin loaded, confirm the style
  core (look for the marker line) is present in the parent session, then spawn a subagent (e.g.
  via the `software-engineer` agent) and confirm the core reached the subagent too. Because a
  non-firing `SubagentStart` fails silently, this live check is the only thing that proves the
  subagent half actually works; treat a miss here as a release blocker, not a note.
- Push branch / open PR per normal flow.

---

## Risks & gaps

0. **Silent failure of the reliability goal (the meta-risk).** Every failure mode of this harness
   is silent by design: missing `node`, an unsupported `SubagentStart` event, a non-JSON-wrapped
   subagent payload, and the `; exit 0` idiom all produce *no error*, just no injection. So "no
   error" is NOT evidence the upgrade works. The only proof is positive observation: the Phase 0
   `SubagentStart` capability check, the `test-hooks.js` assertions, and the Phase 5 hard live
   gate. The in-session marker line exists so a silent miss is visible to the user day-to-day.
1. **`node` PATH dependency (biggest correctness risk).** The hook command is literally `node
   "..."`. If `node` is not on the non-interactive shell's PATH (fnm/nvm users: it often is not),
   the hook no-ops, the `; exit 0` idiom prevents an error but the preamble silently will not
   inject. README must state this; the Windows variant already guards with `Get-Command node`.
2. **Off-switch must be checked in `subagent-start.js`, not only `session-start.js`** - otherwise
   disabling the session preamble still injects into every Task subagent. Covered by the env var
   (inherited by the subagent hook process) and verified in `test-hooks.js`.
3. **SubagentStart output must be JSON-wrapped** or native Claude drops it silently. This is the
   single load-bearing format detail; `test-hooks.js` asserts it.
4. **`lint.sh` mutates** (`rumdl fmt .` in place). Run it as its own step and review the diff so it
   does not silently reformat unrelated files. `MD013` is disabled, so long example lines are fine.
   Use `rumdl fmt --check .` for the non-mutating final gate.
5. **Docs are the heaviest miss-risk** (AGENTS.md Registered lists + Language-Specific Workflows;
   README tables). `/validate-plugin` check #5 is the net, but grep each old name explicitly.
6. **Not a Node project today** - keep it that way. `test-hooks.js` uses only Node built-ins; no
   `package.json`, no `npm install`. Run it as `node hooks/test-hooks.js`.
7. **Out of scope / untouched:** `.in_use/` (gitignored session leases), `.beads/` (empty br
   tracker), `.code-workspace` (glob-based skill refs, needs no edit). `agentic-clean-code` gets a
   light touch only and does not seed the injected core.

## Critical files

- `.claude-plugin/plugin.json` - add `hooks` field + version bump.
- `hooks/` (new) - `style-core.md`, `preamble.js`, `runtime.js`, `session-start.js`,
  `subagent-start.js`, `style-core-hooks.json`, `test-hooks.js`.
- `AGENTS.md`, `README.md` - largest reference + doc surfaces.
- `agents/software-engineer.md`, `agents/code-reviewer.md` - route to the most-renamed skills.
- `skills/code-simplify/SKILL.md`, `skills/feature-development/SKILL.md` - cross-reference the
  renamed style skills via routing tables.
- `commands/rails-code-review.md` - fix the pre-existing ghost-agent reference.
- Reference harness to mirror: `/Users/jtempleton/local/src/ponytail/hooks/ponytail-runtime.js`
  (SessionStart-raw vs SubagentStart-JSON-wrapped) and `.../hooks/claude-codex-hooks.json`
  (manifest shape, `; exit 0` idiom, Windows guard).
