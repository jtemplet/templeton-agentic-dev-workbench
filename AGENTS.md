# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. `CLAUDE.md` re-includes this file with `@AGENTS.md`.

## Repository Overview

This is a personal Claude Code plugin repository - an agentic development workbench containing custom agents, skills, and commands for Python, Ruby/Rails, JavaScript/TypeScript (React/Vue), Swift/iOS, and Terraform development.

## Commands for This Repo

These are the checks that run against this repository itself. CI (`.github/workflows/lint.yml`)
runs the first two on every push and pull request.

```bash
rumdl fmt --check .                                          # what CI runs; ./lint.sh formats in place
node hooks/test-hooks.js                                      # hook suite, incl. the docs/HOOKS.md count assertion
python3 skills/style-testing/scripts/test_check_framework_leak.py   # regression suite for the leak checker
python3 skills/style-testing/scripts/check_framework_leak.py        # assert style-testing stays framework-free
python3 skills/quality-gates/scripts/test_check_doc_paths.py        # regression suite for the doc-path checker
python3 skills/quality-gates/scripts/check_doc_paths.py             # assert every documented path exists
claude plugin validate .                                      # parses every SKILL.md frontmatter
python3 evals/run.py                                          # response-style evals
```

Run `/validate-plugin` after adding or renaming a component.

### Release gate (one-time setup per clone)

`.githooks/reference-transaction` refuses to create a `v*` tag when
`claude plugin validate` fails. Git has no pre-tag hook, so this is the only one that sees a
tag being created and can still stop it. Wire it once per clone, because `core.hooksPath` is
local config and does not travel with the repository:

```bash
git config core.hooksPath .githooks
```

It gates tags only. Commits, branches, and non-`v` tags are untouched. A missing `claude` on
PATH warns and allows, since an untaggable repository is worse than an unchecked tag.

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
| Review Terraform | `/terraform-review` | `terraform-iac-expert` |
| Review agents, tools, prompts | `/agentic-clean-code` | `agentic-clean-code` |
| Build a feature | `/python-feature-dev` | `feature-development` + a `style-*` skill |
| Simplify code | - | `code-simplify` |
| Find and fix bugs in a diff | `/fresh-eyes-cr` | `review-fresh-eyes` |
| Investigate a bug before fixing | `/diagnose` | `diagnostician` agent |
| Write or restructure tests | - | `style-testing`, plus `style-rspec` for RSpec |
| Run the QA gates | `/quality-gates` | `quality-gates` |
| Grade work against its bead | `/verify-acceptance` | `verify-acceptance` |
| Plan a feature | `/plan-feature`, `/plan-review` | `feature-planner` agent, `plan-review` |
| Break a plan into issues | `/plan-to-beads` | `project-manager` agent |
| Audit issue quality | `/bead-audit` (the skill itself), `/bead-audit-all` | `bead-audit` |
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
B  Code Quality:       /fresh-eyes-cr → /verify-acceptance → /quality-gates
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

**Registered Skills** (36). One-line descriptions live in the `README.md` skills
table and in each `skills/<name>/SKILL.md` frontmatter, which is what the runtime actually
reads when deciding what to invoke.

`ab-test-design` `agentic-clean-code` `architecture-decision-record` `aso-audit` `bead-audit`
`business-ideas` `code-simplify` `competitive-analysis` `feature-development`
`house-response-style` `idea-wizard` `plan-review` `plan-to-beads` `pr-maintenance`
`product-brief` `product-research` `product-roadmap` `product-surface-docs` `production-ops`
`quality-gates` `research-ingest` `review-fresh-eyes` `review-python` `review-rails`
`roadmap-dashboard` `style-fizzy` `style-frontend` `style-python` `style-rails` `style-rspec`
`style-swift` `style-testing` `terraform-iac-expert` `ux-audit` `ux-audit-ios`
`verify-acceptance`

**Registered Agents** (12). Descriptions live in the `README.md` agents table and in
each `agents/<name>.md` frontmatter.

`claude-md-reviewer` `code-reviewer` `diagnostician` `feature-planner` `product-analyst`
`product-cartographer` `product-manager` `project-manager` `research-librarian`
`software-engineer` `ux-product-designer` `ux-product-designer-ios`

**Registered Commands** (29). Descriptions live in the `README.md` command tables
and in each `commands/<name>.md` frontmatter.

`/adr` `/agentic-clean-code` `/aso-audit` `/bead-audit-all` `/code-review` `/diagnose`
`/fresh-eyes-cr` `/frontend-code-review` `/plan-feature` `/plan-review` `/plan-to-beads`
`/pr-maintain` `/prod-ops` `/product-analysis` `/product-surface-docs` `/python-code-review`
`/python-feature-dev` `/quality-gates` `/rails-code-review` `/research-ingest` `/response-style`
`/review-claude-md` `/roadmap-dashboard` `/swift-code-review` `/terraform-review` `/ux-audit`
`/ux-audit-ios` `/validate-plugin` `/verify-acceptance`

### Hooks

`hooks/style-core-hooks.json` (registered by the `hooks` field in `plugin.json`, which takes a
single manifest path) wires two independent features. Design notes, rationale, and the test
strategy live in [docs/HOOKS.md](docs/HOOKS.md).

- **Always-on style core.** `SessionStart` injects `hooks/style-core.md` plus the
  `house-response-style` skill body; `SubagentStart` injects the coding core only. Each
  document opens with a marker line so you can see in any session whether it loaded.
  Off-switch: `TADW_STYLE_CORE=off`, or a flag file at
  `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`.
  The payload is 19,996 characters and Claude Code caps each hook output at 10,000, so
  `SessionStart` ships as three manifest entries that differ only in a payload index. Do not
  collapse them back into one; the tail is discarded in silence, and the marker that says it
  loaded survives inside the surviving preview.
- **Acceptance gate.** A `PostToolUse` + `Stop` pair chains the `verify-acceptance` skill onto
  the end of a fresh-eyes review. Off-switch, independent of the style core's:
  `TADW_ACCEPTANCE_GATE=off`, or a flag file at
  `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-acceptance-gate-off`.

Both style hooks run through `hooks/run-hook.sh`, which needs `node` on the non-interactive
shell's PATH. Without it the core cannot be injected, and the wrapper emits
`<!-- house-style-core: FAILED to load ... -->` rather than failing silently.

These hooks fire in **every project** the plugin is loaded for, including non-coding sessions,
because a `SessionStart` hook cannot see the task type.

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

`business-ideas` and `idea-wizard` are referenced by no agent and no command, which
`/validate-plugin` reports as orphans. That is accepted: both are invoked directly as
`/<name>`, so a referrer would add nothing. Treat the orphan rule as a prompt to check the
skill is still reachable, not as a requirement that something point at it.

## Issue Tracking (br + bv)

This project uses **br** (beads_rust) for issue CRUD and **bv** (beads_viewer) for triage and planning.

**Key principle:** `br` never auto-commits or runs git commands. All git operations are explicit.

Full `br` and `bv` usage for agents, covering the `--robot-*` triage flags, scoping and filtering
recipes, the issue-management command set, and the git policy, lives in
[docs/beads-workflow.md](docs/beads-workflow.md). Read it before running any tracker command.

### Workflow

1. `bv --robot-next` - find out what to work on
2. `br update <id> --claim` - claim the issue
3. Do the work
4. `br close <id>` - close when done
5. `br sync --flush-only` - export to JSONL before committing

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Use `br create` for anything that needs follow-up
2. **Run quality gates** (if code changed) - Use `/quality-gates` to run tests, linters, type checks, doc freshness, and security scan
3. **Update issue status** - `br close` finished work, `br update` in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:

   ```bash
   git pull --rebase
   br sync --flush-only
   git push
   git status  # MUST show "up to date with origin"
   ```

5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
