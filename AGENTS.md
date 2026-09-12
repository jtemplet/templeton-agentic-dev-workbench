# AGENTS.md

This file guides Claude Code (claude.ai/code) in this repository. `CLAUDE.md` is a symlink to
it, so both names load the same text and neither can drift from the other.

## Repository Overview

A personal Claude Code plugin: an agentic development workbench of agents, skills, and commands.
It covers Python, Ruby/Rails, JavaScript/TypeScript (React and Vue), Swift/iOS, Go, and
Terraform.

## Commands for This Repo

These checks run against this repository itself.

CI (`.github/workflows/lint.yml`) runs seven of them on every push and pull request:
`rumdl fmt --check .`, `rumdl check . --extend-disable MD013`, `node hooks/test-hooks.js`, both
framework-leak checks, and both refine-round format checks. It skips
`bash hooks/test-claude-scripts.sh`, so only the local hook enforces that suite. `.githooks/pre-push`
runs all of them except the last four. See "Git hooks" below.

```bash
rumdl fmt --check .                                          # what CI runs; ./lint.sh formats in place
rumdl check . --extend-disable MD013                         # the linter, not the formatter: a broken relative link fails here
python3 skills/quality-gates/scripts/check_markdown_wrap.py   # MD013 at 100 columns, scoped to the changed set
node hooks/test-hooks.js                                      # hook suite, incl. the docs/HOOKS.md count assertion
bash hooks/test-claude-scripts.sh                             # suite for the two .claude/scripts hooks
python3 skills/style-testing/scripts/test_check_framework_leak.py   # regression suite for the leak checker
python3 skills/style-testing/scripts/check_framework_leak.py        # assert style-testing stays framework-free
python3 skills/quality-gates/scripts/test_check_doc_paths.py        # regression suite for the doc-path checker
python3 skills/quality-gates/scripts/check_doc_paths.py             # assert every documented path exists
python3 skills/quality-gates/scripts/test_changed_set.py            # regression suite for the changed-set resolver
python3 skills/quality-gates/scripts/test_check_hygiene.py          # regression suite for the hygiene counter
python3 skills/quality-gates/scripts/test_route_qa.py                # regression suite for the QA-method router
python3 skills/quality-gates/scripts/test_probe_api.py               # regression suite for the live API probe
python3 skills/quality-gates/scripts/test_check_documented_bd_commands.py   # regression suite for the bd-command checker
python3 skills/quality-gates/scripts/check_documented_bd_commands.py        # assert every fenced bd command runs
python3 skills/quality-gates/scripts/test_check_documented_paths.py         # regression suite for the documented-path checker
python3 skills/quality-gates/scripts/check_documented_paths.py              # assert every documented plugin-script path resolves and runs
python3 skills/product-surface-docs/scripts/test_check_drive_blocks.py      # regression suite for the drive-block checker
python3 skills/product-surface-docs/scripts/check_drive_blocks.py           # assert every leaf document carries a drive block
python3 skills/bead-refine/scripts/test_check_round_format.py               # regression suite for the refine-round format checker
python3 skills/bead-refine/scripts/check_round_format.py                    # assert the refine round table keeps its 6 columns
python3 skills/ship/scripts/test_check_worktree_occupants.py   # regression suite for the worktree occupant check
python3 .githooks/test_prepush.py                             # regression suite for the pre-push hook
claude plugin validate .                                      # parses every SKILL.md frontmatter
python3 evals/test_run.py                                     # regression suite for the eval harness; calls no model
python3 evals/run.py                                          # response-style evals
```

Run `/validate-plugin` after you add, rename, or remove a component.

**The ship gate is this list minus `python3 evals/run.py`.** `/tadw:ship` takes its gate from
this block.

The response-style evals are the wrong shape for a gate. They are graded against model prose, so
they are not deterministic. `plain-sentences` measures sentence length against a 35-word ceiling,
and the model lands on both sides of it. Derive the case count with `ls -d evals/cases/*/ | wc -l`,
then double it for the number of model calls a run makes.

Run the evals deliberately, to measure whether the style rules still change the model's behavior.
Read the delta between the two arms, not a pass or a fail.
[ADR 0005](docs/adr/0005-the-evals-are-a-measurement-not-a-gate.md) records the options that lost.

### Git hooks (one-time setup per clone)

Six hooks live in `.githooks/`. Wire them once per clone. `core.hooksPath` is local config, and
it does not travel with the repository:

```bash
git config core.hooksPath .githooks
bd hooks list                      # five hooks, each "installed"
```

One command serves them all. `pre-push` and `reference-transaction` carry this repository's own
gates; the other four are beads shims that call `bd hooks run <hook>`.

**`pre-push` runs the check list above, minus the last four.** Every check runs even after one
fails, and all failures report together. A missing tool warns by name and allows the push.

**`pre-push` then refuses the push only when `/quality-gates` recorded a `FAIL` verdict.** A
missing report, or a verdict recorded for some other head, warns and allows.
[ADR 0004](docs/adr/0004-the-pre-push-hook-forgives-by-design.md) records why the hook forgives
rather than failing closed.

**`TADW_PREPUSH=off` skips the hook.** It is documented here so that nobody invents a workaround
under deadline. The value is exact: any other value, empty included, leaves the hook on.

The per-hook mechanism is in [.githooks/AGENTS.md](.githooks/AGENTS.md), which loads when you
work under `.githooks/`.

**`reference-transaction` refuses to create a `v*` tag when `claude plugin validate` fails.**
`/publish-plugin` is what creates those tags, so that skill treats this refusal as a stop rather
than something to route around. See "Releasing" below.

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
| Write or review Markdown | - | `style-markdown` |
| Review Terraform | `/terraform-review` | `terraform-iac-expert` |
| Review agents, tools, prompts | `/agentic-clean-code` | `agentic-clean-code` |
| Build a feature from a bead | `/build <bead-id>` | `feature-development` + a `style-*` skill |
| Simplify code | - | `code-simplify` |
| Find and fix bugs in a diff | `/fresh-eyes-cr` | `review-fresh-eyes` |
| Investigate a bug before fixing | `/diagnose` | `diagnostician` agent |
| Write or restructure tests | - | `style-testing`, plus `style-rspec` for RSpec |
| Run the QA gates | `/quality-gates` | `quality-gates` |
| Grade work against its bead | `/verify-acceptance` | `acceptance-verifier` agent, running `verify-acceptance` |
| Land a finished bead's branch on main | `/tadw:ship` (the skill itself) | `ship` |
| Cut and publish a plugin release | `/publish-plugin` (the skill itself) | `publish-plugin` |
| Align before planning or building | `/grill-me` | `grilling` |
| Sharpen the project's vocabulary | - | `mattpocock-skills:domain-modeling` (external) |
| Write the plan a conversation just decided | `/write-plan` | `write-plan` |
| Plan a feature from one sentence | `/plan-from-idea`, `/plan-review` | `feature-planner` agent, `plan-review` |
| Break a plan into issues | `/plan-to-beads` | `project-manager` agent |
| File one well-crafted bead | `/bead-create` (the skill itself) | `bead-create` |
| Audit issue quality | `/bead-audit` (the skill itself), `/bead-audit-all` | `bead-audit` |
| Prune the backlog by product value | `/bead-refine` | `bead-refine` |
| Decide what to work on next | `/triage-beads` (the skill itself) | `triage-beads` |
| Product strategy | `/competitive-analysis`, `/product-research`, `/product-roadmap`, `/product-brief`, `/ab-test-design` | `product-manager` agent |
| Generate ideas | `/idea-wizard`, `/business-ideas` | `idea-wizard`, `business-ideas` |
| Record a decision | `/adr` | `architecture-decision-record` |
| Audit UX | `/ux-review`, `/ux-review-ios` | `ux-product-designer` agents |
| Audit an App Store listing | `/aso-review` | `aso-review` |
| Map product surfaces to docs | `/product-surface-docs` | `product-cartographer` agent |
| Build a project dashboard | `/roadmap-dashboard` | `roadmap-dashboard` |
| Operate production | `/prod-ops` | `production-ops` |
| Review a CLAUDE.md | `/review-claude-md` | `claude-md-reviewer` agent |

The rows above name the skill a human reaches for. [docs/style-routing.md](docs/style-routing.md)
is the dispatch three documents execute (`code-simplify`, `feature-development`, and the
`software-engineer` agent): it maps a file extension to its style skill, names what stacks on top
for test files and project-local surfaces, and defines when a Markdown file is the deliverable.

[docs/ROUTING.md](docs/ROUTING.md) expands the rows above into workflows, grouped by language
and by task. Not every command has an entry there yet; `tadw-routing-gaps-9wq` tracks the gaps.

**Pipelines.** Each step feeds the next. The per-step detail is in `README.md`.

```text
A  Business Planning:  /business-ideas → /grill-me → /write-plan → /plan-review → /plan-to-beads → /bead-audit-all
B  Code Quality:       /build → /fresh-eyes-cr → /quality-gates → /verify-acceptance → /tadw:ship → /publish-plugin
C  Product Strategy:   /competitive-analysis → /product-research → /product-roadmap → /product-brief → /ab-test-design
D  Bug on-ramp:        /diagnose → /bead-create → pipeline B
```

A hands work to B through the tracker, not through the transcript: A ends with beads, and B starts
by reading one. D exists because a bug never arrives as a plan, so it needs its own route onto B.

### Session shape

Which context window a step runs in matters as much as its order.

**Keep all of pipeline A in one unbroken window.** The interview, the plan, the review, and the
beads all build on the same thinking. Do not clear or compact until `/bead-audit-all` has run.

**`/write-plan` is the step after grilling, not `/plan-from-idea`.** The `feature-planner` agent
behind `/plan-from-idea` runs in its own context and cannot see the interview, so it re-explores
the codebase and can re-ask questions the grilling already closed. `/write-plan` runs in this
window and synthesizes what was decided. Reach for `/plan-from-idea` only on a cold start, where
there is nothing in the window to synthesize.

**Clear the context between every `/build`.** A bead is self-contained on purpose: `/build`
Phase 1 reads the bead from `bd`, never from the transcript. So the previous bead's context adds
nothing and costs the window. Five builds in one session leave the last one reasoning at the
bottom of a full context, which is where the quality drops first.

**Audit the beads while the planning context is still loaded.** `/build` Phase 1 stops when a
bead's criteria are vague or its `design` is empty, so a thin bead bounces the build. Running
`/bead-audit-all` right after `/plan-to-beads` catches that while the plan is still in the window,
where the fix takes seconds. After a clear the same fix costs a full re-read.

**`/verify-acceptance` cites the gate results rather than re-deriving them.** Paste the
`/quality-gates` output into its prompt. It dispatches to the `acceptance-verifier` agent, which
runs in its own context window and cannot read this one, so gate results it is not given are gate
results it runs again. Without them the whole suite runs twice to produce one verdict.

**`/code-review` is the conventions pass, and pipeline B does not include it.** `/fresh-eyes-cr`
hunts bugs and says so: real bugs, not style preferences. `/build`'s Simplify and Lint phases
cover the author's own conventions on the code they just wrote. Add `/code-review` when the diff
is large or touches unfamiliar code, and skip it otherwise.

## Plugin Configuration

### Manifest File

`.claude-plugin/plugin.json` holds the plugin metadata and the `hooks` field. That field wires
the always-on style core, described under "Hooks" below.

It does **not** register components. Claude Code auto-discovers skills, agents, and commands from
their directories, and `plugin.json` lists none of them. Registration means two places: the name
lists in this file, and the description tables in `README.md`. `/validate-plugin` checks the
lists against the directories on disk.

The `name` field (`tadw`) is also the **invocation namespace**. Every component is addressed as
`tadw:<component>`, such as `tadw:fresh-eyes-cr` or `tadw:code-reviewer`. Changing `name` renames
every invocation path at once, including the paths hardcoded in other repositories, so treat it
as a breaking change. It was `templeton-agentic-dev-workbench` before 2.0.0.

Two things share those letters and mean something else: the `TADW_STYLE_CORE` off-switch, and the
`tadw-*` beads issue prefix.

### Releasing

**A push to `main` is already published.** The marketplace entry for this plugin lives in the
separate `jtemplet/templeton-agentic-marketplace` repository, and it pins `tadw` at
`"version": "latest"` against this repository's git URL, so every consumer follows the default
branch. There is no publish workflow and no upload step. The `version` field and the `vX.Y.Z` tag do
not gate distribution; they are how a person tells which published state they are running.

**Use `/publish-plugin`.** It derives the semver bump from the diff since the last tag, writes the
`CHANGELOG.md` section, bumps the manifest, commits `chore(release): X.Y.Z` touching exactly those
two files, then tags and pushes main before the tag. Its bump rubric and stop conditions are in
`skills/publish-plugin/SKILL.md`, and `docs/ROUTING.md` summarizes them.

Read the last tag with `git tag --list 'v*' --sort=-v:refname`, because lexical order puts
`v2.10.1` above `v2.5.2` and a released tag then reads as missing.

**Registered Skills** (45). One-line descriptions live in the `README.md` skills
table and in each `skills/<name>/SKILL.md` frontmatter, which is what the runtime actually
reads when deciding what to invoke.

`ab-test-design` `agentic-clean-code` `architecture-decision-record` `aso-review` `bead-audit`
`bead-create` `bead-refine` `business-ideas` `code-simplify` `competitive-analysis`
`feature-development` `grilling` `house-response-style` `idea-wizard` `plan-review`
`plan-to-beads`
`product-brief` `product-research` `product-roadmap` `product-surface-docs` `production-ops`
`publish-plugin` `quality-gates`
`research-ingest` `research-synthesize` `review-fresh-eyes` `review-python` `review-rails`
`roadmap-dashboard` `ship` `style-fizzy` `style-frontend` `style-go` `style-markdown`
`style-python` `style-rails` `style-rspec` `style-swift` `style-testing` `terraform-iac-expert`
`triage-beads` `ux-review` `ux-review-ios` `verify-acceptance` `write-plan`

**Registered Agents** (15). Descriptions live in the `README.md` agents table and in
each `agents/<name>.md` frontmatter.

`acceptance-verifier` `bulk-reader` `claude-md-reviewer` `code-reviewer` `diagnostician`
`feature-planner` `product-analyst`
`product-cartographer` `product-manager` `project-manager` `quality-gates-orchestrator`
`research-librarian` `software-engineer` `ux-product-designer` `ux-product-designer-ios`

**Registered Commands** (31). Descriptions live in the `README.md` command tables
and in each `commands/<name>.md` frontmatter.

`/adr` `/agentic-clean-code` `/aso-review` `/bead-audit-all` `/bead-refine` `/build` `/code-review`
`/diagnose` `/fresh-eyes-cr` `/frontend-code-review` `/grill-me` `/plan-from-idea` `/plan-review`
`/plan-to-beads` `/prod-ops` `/product-analysis` `/product-surface-docs` `/python-code-review`
`/quality-gates` `/rails-code-review` `/research-ingest` `/research-synthesize` `/response-style`
`/review-claude-md` `/roadmap-dashboard` `/swift-code-review` `/terraform-review` `/ux-review`
`/ux-review-ios` `/validate-plugin` `/verify-acceptance`

### Hooks

`hooks/style-core-hooks.json` wires one feature. The `hooks` field in `plugin.json` registers it,
and takes a single manifest path. Design notes, rationale, and the test strategy live in
[docs/HOOKS.md](docs/HOOKS.md).

**Always-on style core.** `SessionStart` injects `hooks/style-core.md` plus the
`house-response-style` skill body. `SubagentStart` injects the coding core alone. Each document
opens with a marker line, so you can see in any session whether it loaded. Off-switch:
`TADW_STYLE_CORE=off`, or a flag file at `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`.

The payload exceeds the 10,000-character cap Claude Code puts on each hook output, so
`SessionStart` ships as several manifest entries. **Do not collapse those entries into one.** The
tail is then discarded in silence, and the marker that says the core loaded survives inside the
surviving preview.
[ADR 0006](docs/adr/0006-the-style-core-ships-as-several-hook-entries.md) records the incident.
Read the entry count from the manifest, never from memory; `docs/HOOKS.md` tabulates the sizes,
and `node hooks/test-hooks.js` fails when the manifest disagrees with the run-time split.

Both style hooks run through `hooks/run-hook.sh`, which needs `node` on the non-interactive
shell's PATH. Without `node`, the wrapper emits
`<!-- house-style-core: FAILED to load ... -->` instead of failing silently.

These hooks fire in **every project** the plugin is loaded for, non-coding sessions included. A
`SessionStart` hook cannot see the task type.

### Portable hooks for other repositories

`scripts/` holds hooks that belong to a **project** rather than to this plugin, with an installer
for each. They are not wired here, and `plugin.json` does not reference them.
`scripts/label_bead_on_skill_invocation.sh` is **the copy of record**: change it there, never in
a deployed copy.

The operating detail is in [scripts/AGENTS.md](scripts/AGENTS.md), which loads when you work
under `scripts/`. Rationale and incident history live in
[docs/PORTABLE-HOOKS.md](docs/PORTABLE-HOOKS.md).

## Key Design Principles

### Verification-First Approach

Before you call code problematic:

1. Check that the tests pass.
2. Verify the Rails or Python version.
3. Understand the modern framework patterns.
4. Confirm that the issue exists.

**Rule:** if the tests pass and the code works, the maximum severity is MEDIUM.

### Pragmatic Over Pure

Working non-standard code beats non-working standard code. Understand a framework's conventions
before you suggest a change.

### Architecture Decision Records

`docs/adr/` holds them and `/adr` writes them. It was named docs/decisions until 2026-08-28, and
that directory is gone. It moved so that `mattpocock-skills:domain-modeling`, which writes ADRs
to `docs/adr/` and cannot be told otherwise, lands them where everything here reads. Three rules
keep the directory from becoming write-only.

**Two skills write into it, in two formats.** `/adr` writes the structured template in
`skills/architecture-decision-record/SKILL.md`: Context, Options Considered with pros and cons,
Decision, Consequences. `mattpocock-skills:domain-modeling` writes its own, which can be a single
paragraph. Both scan the directory and increment the number, so they never collide on a filename.
Prefer `/adr` when the rejected options are worth recording, which is most of the time.

**An ADR earns its place when reversing the decision would cost more than a day, and somebody
would otherwise argue it again.** Everything smaller belongs in the bead's `design` field, where it
already is. `docs/adr/0001-native-tracker-fields-are-canonical.md` is the model to copy:
`plan-to-beads` cites it by name five times, including in its own checklist, so it is a rule other
components obey rather than a record of a past argument. An ADR that nothing cites is a diary
entry, and it makes the ones that do carry rules harder to find.

**Write them at two moments, not as a habit.** When `grilling` resolves a choice that is hard to
reverse, `mattpocock-skills:domain-modeling` offers an ADR; accept when reversal is expensive. When
`/plan-review` returns Needs Revision over a contested design choice, the argument just made is
already the Context section.

**They are read at build time, which is what makes writing one worthwhile.** `/build` Phase 2
reads this directory before the first edit and reports which records bind the change, and Phase 3
lists any decision that constrains work beyond the current bead as an ADR candidate. A record
nothing reads changes no code.

## Common Tasks

**Adding a skill, agent, or command.** Create the file. Then register it in two places: the name
list in this file, and the description table in `README.md`. Do **not** edit
`.claude-plugin/plugin.json`, because components are auto-discovered from their directories.
Templates are in [docs/AUTHORING.md](docs/AUTHORING.md). Run `/validate-plugin` afterward.

**A command may share a skill's name, or delegate to that skill by name, but never both.**
`commands/<name>.md` and `skills/<name>/SKILL.md` are addressed as the same `tadw:<name>`, and the
command wins. So a command body that says "Use the `<name>` skill" resolves back to itself. Three
fixes: rename the command, delete it so the skill takes the slash name, or have it **Read**
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`.

**Four skills are accepted orphans.** `/validate-plugin` reports `business-ideas`,
`idea-wizard`, `publish-plugin`, and `ship` as orphans, because no agent and no command references
them. You invoke all four directly as `/<name>`, so a referrer would add nothing.

The check follows agent and command references alone, so it misses one live path: `publish-plugin`
invokes `ship` to land a branch. It also matches on the skill's name, so `commands/adr.md` counts
as a referrer of `architecture-decision-record` even though it writes the name without backticks.
Read the orphan rule as a prompt to check that a skill is still reachable, not as a defect list.

## Issue Tracking (bd + bv)

This project uses **bd** (beads) for issue CRUD, and **bv** (beads_viewer) for triage and
planning.

**Key principle:** `bd` never auto-commits and never runs git commands. Every git operation is
explicit.

[docs/beads-workflow.md](docs/beads-workflow.md) carries full `bd` and `bv` usage for agents. It
covers the `--robot-*` triage flags, the scoping and filtering recipes, the issue-management
command set, and the git policy. Read it before you run any tracker command.

### The author never handles tracker plumbing

This is a standing instruction from the repository owner. It outranks any workflow step below.

1. **Never ask the author to run `bd export`, and never ask about `.beads/issues.jsonl`.** That
   file is a passive export, not something a person maintains. An agent that needs it current
   right now, mid-task, still runs the export itself, silently.
2. **Never ask the author to sync the Dolt remote.** Syncing is a machine's job. An agent that is
   already pushing runs the sync too, or says nothing about it.
3. **Report tracker plumbing only when it fails.** A successful export is not news. A failed one
   is, because the beads then exist on one machine alone.

This constrains agents, not `bd` itself. `bd` stays explicit. **`.githooks/pre-push` automates the
baseline case** (`tadw-pm8`): every push exports the tracker and, if the export changed, commits
it as a follow-up commit. That commit lands on the next push, not the one that triggered it,
because git resolves what to push before the hook runs and cannot fold a new commit into a push
already in flight. The step never gates the push: a missing `bd`, or a failed export, only warns.
It carries the text export alone; the Dolt remote sync stays manual, per rule 2, until
`bd dolt remote list` and `bd dolt show` agree on whether a remote exists.

Rule 1 still applies within a task. The hook only catches state on the way out, so a skill that
needs the export current *before* it decides what to commit, such as `ship` resolving a rebase
conflict on `.beads/issues.jsonl`, still runs `bd export` itself.

### Workflow

1. Run `bv --robot-next` to find the next task, or `/triage-beads` for an ROI-ranked readout.
2. Run `bd update <id> --claim` to claim the issue.
3. Do the work.
4. Run `bd close <id>` when it is done.

## Landing the Plane (Session Completion)

Complete every step below before you end a work session. The work is not complete until
`git push` succeeds.

1. **File issues for remaining work.** Use `bd create` for anything that needs follow-up.
2. **Run the quality gates**, if the code changed. `/quality-gates` runs the tests, linters, type
   checks, doc freshness, and a security scan.
3. **Grade the work against its bead**, if it has one. `/verify-acceptance` cites the gate
   results from step 2 rather than re-deriving them. A NOT ACCEPTED verdict means the work is not
   done. Fix it, or reopen the bead. Do not close it in step 4.
4. **Update issue status.** `bd close` finished work, and `bd update` in-progress items.
5. **Push to the remote.** This step is mandatory:

   ```bash
   git pull --rebase
   git push
   git status  # must report "up to date with origin"
   ```

   Tracker state rides along unmentioned. See "The author never handles tracker plumbing" above.

   If step 2 recorded a FAIL verdict, the pre-push hook refuses this push. Fix the gate rather
   than pushing past it. `TADW_PREPUSH=off` is the documented way out.
6. **Clean up.** Clear the stashes, and prune the remote branches.
7. **Verify.** Every change is committed and pushed.
8. **Hand off.** Give the next session its context.

See [ADR 0003](docs/adr/0003-a-push-to-main-is-already-published.md) for why there is no publish
step, and what that costs.

**Publishing is a separate decision, not step 9.** The push in step 5 already put the change in
front of every consumer, because the marketplace follows this repository's default branch.
Numbering and tagging that state is `/publish-plugin`. Several landings usually batch into one
release. See "Releasing" above.

**Rules:**

- The work is not complete until `git push` succeeds.
- Never stop before pushing, because that leaves the work stranded locally.
- Never say "ready to push when you are". You push.
- If the push fails, resolve the cause and retry until it succeeds.

## Agent skills

Configuration the external `mattpocock-skills` engineering skills read. Each file below is the
one place that answers its question, so a skill never has to guess.

### Issue tracker

Issues live in **bd (beads)**, not in GitHub Issues; the GitHub remote carries code alone. See
[docs/agents/issue-tracker.md](docs/agents/issue-tracker.md).

### Triage labels

The five canonical triage roles keep their default names. `ready-for-human` is a routing
decision and is not the same label as `needs-human`, which the `ship` skill applies on a stop.
See [docs/agents/triage-labels.md](docs/agents/triage-labels.md).

### Domain docs

Single-context: one `CONTEXT.md` at the root, plus `docs/adr/`. Both exist. See
[docs/agents/domain.md](docs/agents/domain.md).

### Which plugin's skill wins

**Where a tadw skill and a `mattpocock-skills` skill answer the same question, use the tadw
one.** It writes bd beads with the native fields ADR 0001 makes canonical, grounds its claims
against `main`, and emits the lines the pipelines read. Two skills are the deliberate exception
and stay his: `domain-modeling`, which tadw deleted its own in favor of, and `grill-with-docs`,
which `/write-plan` names as a valid predecessor. The full mapping, including the partial
overlaps, is in
[docs/agents/skill-precedence.md](docs/agents/skill-precedence.md), and the reasoning is in
[ADR 0007](docs/adr/0007-a-tadw-skill-wins-over-an-overlapping-external-skill.md).

MD013 stays off for the block below. `bd` owns its content and verifies it against the `hash` in
the opening comment, so a line inside it must never be hand-wrapped to satisfy the linter.

<!-- rumdl-disable MD013 -->
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
<!-- rumdl-enable MD013 -->
