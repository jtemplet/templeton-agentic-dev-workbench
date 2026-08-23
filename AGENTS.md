# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. `CLAUDE.md` re-includes this file with `@AGENTS.md`.

## Repository Overview

This is a personal Claude Code plugin repository - an agentic development workbench containing custom agents, skills, and commands for Python, Ruby/Rails, JavaScript/TypeScript (React/Vue), Swift/iOS, and Terraform development.

## Commands for This Repo

These are the checks that run against this repository itself. CI
(`.github/workflows/lint.yml`) runs the first four on every push and pull request.
`.githooks/pre-push` runs all of them except the last three, so most of this list is enforced
locally rather than remembered (see "Git hooks" below).

```bash
rumdl fmt --check .                                          # what CI runs; ./lint.sh formats in place
node hooks/test-hooks.js                                      # hook suite, incl. the docs/HOOKS.md count assertion
bash hooks/test-claude-scripts.sh                             # suite for the two .claude/scripts hooks
python3 skills/style-testing/scripts/test_check_framework_leak.py   # regression suite for the leak checker
python3 skills/style-testing/scripts/check_framework_leak.py        # assert style-testing stays framework-free
python3 skills/quality-gates/scripts/test_check_doc_paths.py        # regression suite for the doc-path checker
python3 skills/quality-gates/scripts/check_doc_paths.py             # assert every documented path exists
python3 skills/quality-gates/scripts/test_changed_set.py            # regression suite for the changed-set resolver
python3 skills/quality-gates/scripts/test_check_secrets.py          # regression suite for the secret scanner
python3 skills/quality-gates/scripts/check_secrets.py                # assert no secret file or key sits in the tree
python3 skills/quality-gates/scripts/test_check_hygiene.py          # regression suite for the hygiene counter
python3 skills/quality-gates/scripts/test_route_qa.py                # regression suite for the QA-method router
python3 skills/quality-gates/scripts/test_probe_api.py               # regression suite for the live API probe
python3 evals/test_run.py                                     # regression suite for the eval harness; calls no model
python3 .githooks/test_prepush.py                             # regression suite for the pre-push hook
claude plugin validate .                                      # parses every SKILL.md frontmatter
python3 evals/run.py                                          # response-style evals
```

Run `/validate-plugin` after adding or renaming a component.

**The ship gate is this list minus `python3 evals/run.py`.** `/tadw:ship` takes its gate from
this block, and the response-style evals are the wrong shape for one. They are graded against
model prose, so they are not deterministic: `plain-sentences` measures sentence length against a
35-word ceiling, and runs on 2026-08-22 and 2026-08-23 produced 40, 38, 37, 34, 26, and 22 words.
A gate that fails at random teaches people to re-run until it is green, which is how a gate stops
meaning anything. Each run also costs twelve real model calls and several minutes.

Run them deliberately, to measure whether the style rules still change the model's behavior. The
number to read is the delta between the two arms, not a pass or a fail.

### Git hooks (one-time setup per clone)

Two hooks live in `.githooks/`. Wire them once per clone, because `core.hooksPath` is local
config and does not travel with the repository:

```bash
git config core.hooksPath .githooks
```

One command serves both hooks, which is most of the argument for running it on a fresh clone.

**`pre-push` runs the check list above**, minus the last three: `claude plugin validate .`
(`reference-transaction` already gates it at the tag, and spawning the CLI is the slowest check),
`python3 evals/run.py` (every case is a real model call, too slow and too costly for a push), and
`python3 .githooks/test_prepush.py` (it pushes inside a fixture wired to this hook, so running it
here would recurse).

It takes about 46 seconds on a warm machine, nearly all of it in the six heaviest suites.
`test_probe_api.py` accounts for roughly 11 of those seconds and cannot be made much faster: it
starts real servers and waits on real sockets, which is the only way to check which host it
addresses and that it leaks no process. Three behaviors are deliberate:

- **Every check runs even after one fails**, and all failures report together. Stopping at the
  first makes you push, fail, fix, push, and fail again on the next one.
- **A missing tool warns by name and allows the push.** Neither `rumdl` nor `node` is universally
  installed, and an unpushable clone is a worse failure than an unchecked push. If every tool is
  missing the push still proceeds, but the hook reports that nothing was verified instead of
  reporting a pass: a run that checked nothing has not earned the word "passed".
- **`TADW_PREPUSH=off` skips it**, documented here rather than left as a workaround people invent
  under deadline. It is exact: any other value, including empty, leaves the hook on.

A push that only deletes a remote ref pushes no code, so it runs nothing. A push that deletes one
ref and updates another does carry code, so it is checked. On success the hook prints one line,
carrying how many checks ran and how long they took. `.githooks/test_prepush.py` pins all of this
against real `git push --dry-run` runs in a throwaway fixture.

**`reference-transaction` refuses to create a `v*` tag** when `claude plugin validate` fails. Git
has no pre-tag hook, so this is the only one that sees a tag being created and can still stop it.
It gates tags only: commits, branches, and non-`v` tags are untouched. A missing `claude` on PATH
warns and allows, since an untaggable repository is worse than an unchecked tag.

## Architecture

Three component directories, auto-discovered by Claude Code from their file layout:

```text
commands/*.md → agents/*.md → skills/*/SKILL.md
     ↓               ↓              ↓
  Invokes       Follows        Implements
```

A command is a shortcut that loads an agent or a skill. An agent is a workflow definition that
references skills. A skill holds the technique itself. Component anatomy and the authoring
templates live in [docs/AUTHORING.md](docs/AUTHORING.md).

## Task Routing

| Task | Command | Skill or agent |
|---|---|---|
| Review any change, auto-detect language | `/code-review` | `code-reviewer` agent |
| Review Python | `/python-code-review` | `review-python` |
| Review Rails | `/rails-code-review` | `review-rails` |
| Review Swift/iOS | `/swift-code-review` | `style-swift` |
| Review JS/TS/React/Vue | `/frontend-code-review` | `style-frontend` |
| Write or review Go | - | `style-go` |
| Review Terraform | `/terraform-review` | `terraform-iac-expert` |
| Review agents, tools, prompts | `/agentic-clean-code` | `agentic-clean-code` |
| Build a feature from a bead | `/build <bead-id>` | `feature-development` + a `style-*` skill |
| Simplify code | - | `code-simplify` |
| Find and fix bugs in a diff | `/fresh-eyes-cr` | `review-fresh-eyes` |
| Investigate a bug before fixing | `/diagnose` | `diagnostician` agent |
| Write or restructure tests | - | `style-testing`, plus `style-rspec` for RSpec |
| Run the QA gates | `/quality-gates` | `quality-gates` |
| Grade work against its bead | `/verify-acceptance` | `verify-acceptance` |
| Land a finished bead's branch on main | `/tadw:ship` (the skill itself) | `ship` |
| Align before planning or building | `/grill-me` | `grilling` |
| Sharpen the project's vocabulary | - | `domain-modeling` |
| Plan a feature | `/plan-feature`, `/plan-review` | `feature-planner` agent, `plan-review` |
| Break a plan into issues | `/plan-to-beads` | `project-manager` agent |
| File one well-crafted bead | `/bead-create` (the skill itself) | `bead-create` |
| Audit issue quality | `/bead-audit` (the skill itself), `/bead-audit-all` | `bead-audit` |
| Decide what to work on next | `/triage-beads` (the skill itself) | `triage-beads` |
| Product strategy | `/competitive-analysis`, `/product-research`, `/product-roadmap`, `/product-brief`, `/ab-test-design` | `product-manager` agent |
| Generate ideas | `/idea-wizard`, `/business-ideas` | `idea-wizard`, `business-ideas` |
| Record a decision | `/adr` | `architecture-decision-record` |
| Audit UX | `/ux-audit`, `/ux-audit-ios` | `ux-product-designer` agents |
| Audit an App Store listing | `/aso-audit` | `aso-audit` |
| Map product surfaces to docs | `/product-surface-docs` | `product-cartographer` agent |
| Build a project dashboard | `/roadmap-dashboard` | `roadmap-dashboard` |
| Keep a PR green | `/pr-maintain` | `pr-maintenance` |
| Operate production | `/prod-ops` | `production-ops` |
| Review a CLAUDE.md | `/review-claude-md` | `claude-md-reviewer` agent |

What each one does in full is in [docs/ROUTING.md](docs/ROUTING.md).

**Pipelines.** Each step feeds the next. The per-step detail is in `README.md`.

```text
A  Business Planning:  /business-ideas → /plan-feature → /plan-review → /plan-to-beads
B  Code Quality:       /fresh-eyes-cr → /quality-gates → /verify-acceptance → /tadw:ship
C  Product Strategy:   /competitive-analysis → /product-research → /product-roadmap → /product-brief → /ab-test-design
```

## Plugin Configuration

### Manifest File

`.claude-plugin/plugin.json` defines plugin metadata and the `hooks` field that wires the
always-on style core (see "Hooks" below). It does **not** register components: skills, agents,
and commands are auto-discovered from their directories, and `plugin.json` lists none of them.
Registration means two places: the name lists in this file, which `/validate-plugin` checks
against the directories on disk, and the description tables in `README.md`.

The `name` field (`tadw`) is also the **invocation namespace**: every component in this plugin is
addressed as `tadw:<component>` (`tadw:fresh-eyes-cr`, `tadw:code-reviewer`). Changing `name` renames
every invocation path at once, including the ones hardcoded in other repos, so treat it as a breaking
change. It was `templeton-agentic-dev-workbench` before 2.0.0. Unrelated to the namespace despite the
shared letters: the `TADW_STYLE_CORE` off-switch and the `tadw-*` beads issue prefix.

**Registered Skills** (42). One-line descriptions live in the `README.md` skills
table and in each `skills/<name>/SKILL.md` frontmatter, which is what the runtime actually
reads when deciding what to invoke.

`ab-test-design` `agentic-clean-code` `architecture-decision-record` `aso-audit` `bead-audit`
`bead-create` `business-ideas` `code-simplify` `competitive-analysis` `domain-modeling`
`feature-development` `grilling` `house-response-style` `idea-wizard` `plan-review`
`plan-to-beads` `pr-maintenance`
`product-brief` `product-research` `product-roadmap` `product-surface-docs` `production-ops`
`quality-gates` `research-ingest` `review-fresh-eyes` `review-python` `review-rails`
`roadmap-dashboard` `ship` `style-fizzy` `style-frontend` `style-go` `style-python` `style-rails`
`style-rspec` `style-swift` `style-testing` `terraform-iac-expert` `triage-beads` `ux-audit`
`ux-audit-ios` `verify-acceptance`

**Registered Agents** (12). Descriptions live in the `README.md` agents table and in
each `agents/<name>.md` frontmatter.

`claude-md-reviewer` `code-reviewer` `diagnostician` `feature-planner` `product-analyst`
`product-cartographer` `product-manager` `project-manager` `research-librarian`
`software-engineer` `ux-product-designer` `ux-product-designer-ios`

**Registered Commands** (30). Descriptions live in the `README.md` command tables
and in each `commands/<name>.md` frontmatter.

`/adr` `/agentic-clean-code` `/aso-audit` `/bead-audit-all` `/build` `/code-review` `/diagnose`
`/fresh-eyes-cr` `/frontend-code-review` `/grill-me` `/plan-feature` `/plan-review` `/plan-to-beads`
`/pr-maintain` `/prod-ops` `/product-analysis` `/product-surface-docs` `/python-code-review`
`/quality-gates` `/rails-code-review` `/research-ingest` `/response-style`
`/review-claude-md` `/roadmap-dashboard` `/swift-code-review` `/terraform-review` `/ux-audit`
`/ux-audit-ios` `/validate-plugin` `/verify-acceptance`

### Hooks

`hooks/style-core-hooks.json` (registered by the `hooks` field in `plugin.json`, which takes a
single manifest path) wires one feature. Design notes, rationale, and the test
strategy live in [docs/HOOKS.md](docs/HOOKS.md).

- **Always-on style core.** `SessionStart` injects `hooks/style-core.md` plus the
  `house-response-style` skill body; `SubagentStart` injects the coding core only. Each
  document opens with a marker line so you can see in any session whether it loaded.
  Off-switch: `TADW_STYLE_CORE=off`, or a flag file at
  `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`.
  The payload is 20,275 characters and Claude Code caps each hook output at 10,000, so
  `SessionStart` ships as three manifest entries that differ only in a payload index. Do not
  collapse them back into one; the tail is discarded in silence, and the marker that says it
  loaded survives inside the surviving preview.

Both style hooks run through `hooks/run-hook.sh`, which needs `node` on the non-interactive
shell's PATH. Without it the core cannot be injected, and the wrapper emits
`<!-- house-style-core: FAILED to load ... -->` rather than failing silently.

These hooks fire in **every project** the plugin is loaded for, including non-coding sessions,
because a `SessionStart` hook cannot see the task type.

### Portable hooks for other repositories

`scripts/` holds hooks that belong to a **project** rather than to this plugin, with an installer
each. They are not wired here, and `plugin.json` does not reference them.

- `scripts/label_bead_on_skill_invocation.sh` labels the bead a skill invocation acts on, wired to
  `PreToolUse` (matcher `Skill`), `UserPromptSubmit`, and `Stop`. The copy of record lives in the
  `atlas` repository; this one is a copy for distribution.
- `scripts/install_label_bead_on_skill_invocation.sh` installs it into whatever repository you run
  it from: it copies the hook to `.claude/scripts/`, backs up `.claude/settings.json`, and wires
  the three events. Safe to re-run, and it repairs wiring that names an older path rather than
  duplicating it. `--dest-dir` moves the destination.

Note what this gives the target repository: labeling a bead refreshes `.beads/issues.jsonl` with
`bd export`, so the export stays current for `bv` and dashboards. It commits nothing and pushes
nothing. The hook used to commit and push that file, which is what `tadw-0j8` was filed against;
the commit path went away with the `bd` cutover, and that bead is closed.

## Key Design Principles

### Verification-First Approach

Before flagging code as problematic:

1. Check if tests pass
2. Verify Rails/Python version
3. Understand modern framework patterns
4. Confirm issue actually exists

**Rule:** If tests pass and code works, maximum severity is MEDIUM.

### Pragmatic Over Pure

Working non-standard code is better than non-working standard code. Context matters - understand framework conventions before suggesting changes.

### Agent Integration

Agents should:

- Reference existing skills (don't duplicate knowledge)
- Provide concrete output formats with examples
- Include quality checklists for consistency
- Define clear integration points with other tools

## Common Tasks

**Adding a skill, agent, or command.** Create the file, then register it in two places: the name
list in this file, and the description table in `README.md`. Do **not** edit
`.claude-plugin/plugin.json`; components are auto-discovered from their directories. A skill that
no agent or command references is an orphan and `/validate-plugin` will flag it. Templates are in
[docs/AUTHORING.md](docs/AUTHORING.md).

Run `/validate-plugin` after adding, renaming, or removing a component.

**A command may share a skill's name, or delegate to that skill by name, but never both.**
`commands/<name>.md` and `skills/<name>/SKILL.md` are addressed as the same `tadw:<name>` and the
command wins, so a command body saying "Use the `<name>` skill" resolves back to itself. Give the
command a different name, delete it (the skill then takes the slash name), or have it
`**Read** ${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` instead of invoking it.

`bead-create`, `business-ideas`, `domain-modeling`, `idea-wizard`, `ship`, and `triage-beads` are
referenced by no agent and no command, which `/validate-plugin` reports as orphans. That is
accepted: all six are invoked directly as `/<name>`, so a referrer would add nothing.
`domain-modeling` is additionally reachable from the `grilling` skill, which the orphan check does
not see, because it only follows agent and command references. Treat the orphan rule as a prompt to
check the skill is still reachable, not as a requirement that something point at it.

## Issue Tracking (bd + bv)

This project uses **bd** (beads) for issue CRUD and **bv** (beads_viewer) for triage and planning.

**Key principle:** `bd` never auto-commits or runs git commands. All git operations are explicit.

### The author never handles tracker plumbing

Standing instruction from the repository owner, and it outranks any workflow step below.

1. **Never ask the author to run `bd export`, and never ask about `.beads/issues.jsonl`.** That
   file is a passive export, not something a person maintains. An agent that needs it current
   runs the export itself, silently, as part of whatever it was already doing.
2. **Never ask the author to sync the Dolt remote.** Syncing is a machine's job. An agent that
   is already pushing runs the sync too, or it says nothing about it.
3. **Report tracker plumbing only when it fails.** A successful export is not news. A failed
   one is, because the beads then exist on one machine only.

This constrains agents, not `bd` itself. `bd` stays explicit, per the key principle above. The
automation belongs in this repository's own `.githooks/`, where it is tracked in git and the
author can read it. `tadw-pm8` covers building it; until that lands, agents absorb the step by
hand and stay quiet about it.

Full `bd` and `bv` usage for agents, covering the `--robot-*` triage flags, scoping and filtering
recipes, the issue-management command set, and the git policy, lives in
[docs/beads-workflow.md](docs/beads-workflow.md). Read it before running any tracker command.

### Workflow

1. `bv --robot-next` - find out what to work on (or `/triage-beads` for an ROI-ranked readout)
2. `bd update <id> --claim` - claim the issue
3. Do the work
4. `bd close <id>` - close when done

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Use `bd create` for anything that needs follow-up
2. **Run quality gates** (if code changed) - Use `/quality-gates` to run tests, linters, type checks, doc freshness, and security scan
3. **Grade the work against its bead** (if it has one) - Use `/verify-acceptance`, which cites the
   gate results from step 2 rather than re-deriving them. A NOT ACCEPTED verdict means the work is
   not done; fix it or reopen the bead rather than closing it in step 4.
4. **Update issue status** - `bd close` finished work, `bd update` in-progress items
5. **PUSH TO REMOTE** - This is MANDATORY:

   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```

   Tracker state rides along without being mentioned. See "The author never handles tracker
   plumbing" above.
6. **Clean up** - Clear stashes, prune remote branches
7. **Verify** - All changes committed AND pushed
8. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See <https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md> for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:

   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```

5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**

- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
