# AGENTS.md

This file guides Claude Code (claude.ai/code) in this repository. `CLAUDE.md` is a symlink to
it, so both names load the same text and neither can drift from the other.

## Repository Overview

A personal Claude Code plugin: an agentic development workbench of agents, skills, and commands.
It covers Python, Ruby/Rails, JavaScript/TypeScript (React and Vue), Swift/iOS, Go, and
Terraform.

## Commands for This Repo

These checks run against this repository itself.

CI (`.github/workflows/lint.yml`) runs four of them on every push and pull request:
`rumdl fmt --check .`, `node hooks/test-hooks.js`, and both framework-leak checks. It skips
`bash hooks/test-claude-scripts.sh`, so only the local hook enforces that suite.
`.githooks/pre-push` runs all of them except the last four. See "Git hooks" below.

```bash
rumdl fmt --check .                                          # what CI runs; ./lint.sh formats in place
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
they are not deterministic. `plain-sentences` measures sentence length against a 35-word ceiling.
Runs on 2026-08-22 and 2026-08-23 produced 40, 38, 37, 34, 26, and 22 words. A gate that fails at
random teaches people to re-run it until it passes, and a gate like that means nothing. Each run
also costs twelve real model calls and several minutes.

Run the evals deliberately, to measure whether the style rules still change the model's behavior.
Read the delta between the two arms, not a pass or a fail.

### Git hooks (one-time setup per clone)

Two hooks live in `.githooks/`. Wire them once per clone. `core.hooksPath` is local config, and
it does not travel with the repository:

```bash
git config core.hooksPath .githooks
```

One command serves both hooks.

**`pre-push` runs the check list above, minus the last four.** Each exclusion has its own reason:

- `claude plugin validate .`: `reference-transaction` already gates it at the tag, and spawning
  the CLI is the slowest check.
- `python3 .githooks/test_prepush.py`: it pushes inside a fixture wired to this hook, so running
  it here would recurse.
- Both eval commands: see the next paragraph.

**No git hook runs anything under `evals/`.** `python3 evals/run.py` makes a real model call for
every case, which is too slow and too costly for a push. `python3 evals/test_run.py` calls no
model and costs about 2 seconds, so cost is not why it left the hook. The evals are a measurement
you run deliberately. Both stay in the list above, so the ship gate still runs the harness suite.

That leaves 12 checks. They take tens of seconds, and the figure moves with the machine. It was
46 seconds when first measured warm, and 68 seconds for a dry-run push on 2026-08-23. Six suites
carry nearly all of it.

`test_probe_api.py` takes about 11 of those seconds, and it cannot be made much faster. It starts
real servers and waits on real sockets. That is the only way to check which host it addresses,
and that it leaks no process.

Three behaviors are deliberate:

- **Every check runs, even after one fails**, and all failures report together. A hook that
  stopped at the first would make you push, fail, fix, and fail again on the next one.
- **A missing tool warns by name and allows the push.** Neither `rumdl` nor `node` is universally
  installed, and an unpushable clone is worse than an unchecked push. If every tool is missing,
  the push still proceeds. The hook then reports that it verified nothing, because a run that
  checked nothing has not earned the word "passed".
- **`TADW_PREPUSH=off` skips the hook.** It is documented here so that nobody invents a
  workaround under deadline. The value is exact: any other value, empty included, leaves the
  hook on.

A push that only deletes a remote ref carries no code, so the hook runs nothing. A push that
deletes one ref and updates another does carry code, so the hook checks it.

When the checks pass, this stage prints one line carrying how many ran and how long they took.
`.githooks/test_prepush.py` pins all of it against real `git push --dry-run` runs in a throwaway
fixture.

**`pre-push` has a second stage: the verdict `/quality-gates` recorded.** Git calls exactly one
pre-push hook, so both stages share the file. Each stage reports under its own message, so one
push answers both questions.

The stage reads `quality-gates-report.json` from the directory `git rev-parse --git-dir`
resolves. That directory is per worktree, so a linked worktree reads its own verdict rather than
the main checkout's.

This stage forgives by design:

- **Only a recorded verdict of `FAIL` refuses the push.** The message names the verdict, the head
  it was recorded for, and the time. It names both exits too: re-run `/quality-gates`, or set
  `TADW_PREPUSH=off`.
- **A missing or unreadable report warns and allows.** Absence is not evidence of a problem.
  Blocking there would refuse every documentation push from a fresh clone, and would teach people
  to turn the hook off.
- **A verdict recorded off the line you are pushing warns as stale, and allows.** It describes
  some other tree. A `FAIL` still refuses in that state, because one command refreshes it.

**`reference-transaction` refuses to create a `v*` tag when `claude plugin validate` fails.** Git
has no pre-tag hook, so this is the only hook that sees a tag being created and can still stop
it. It gates tags alone, and leaves commits, branches, and non-`v` tags untouched. A missing
`claude` on PATH warns and allows, because an untaggable repository is worse than an unchecked
tag.

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
| Grade work against its bead | `/verify-acceptance` | `verify-acceptance` |
| Land a finished bead's branch on main | `/tadw:ship` (the skill itself) | `ship` |
| Cut and publish a plugin release | `/publish-plugin` (the skill itself) | `publish-plugin` |
| Align before planning or building | `/grill-me` | `grilling` |
| Sharpen the project's vocabulary | - | `domain-modeling` |
| Plan a feature | `/plan-feature`, `/plan-review` | `feature-planner` agent, `plan-review` |
| Break a plan into issues | `/plan-to-beads` | `project-manager` agent |
| File one well-crafted bead | `/bead-create` (the skill itself) | `bead-create` |
| Audit issue quality | `/bead-audit` (the skill itself), `/bead-audit-all` | `bead-audit` |
| Prune the backlog by product value | `/bead-refine` | `bead-refine` |
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

[docs/ROUTING.md](docs/ROUTING.md) expands the rows above into workflows, grouped by language
and by task. It covers 18 of the 30 commands, not all of them: `/aso-audit`, `/diagnose`,
`/fresh-eyes-cr`, `/plan-review`, `/prod-ops`, `/product-surface-docs`, `/research-ingest`,
`/response-style`, `/review-claude-md`, `/ux-audit`, `/ux-audit-ios`, and `/validate-plugin`
have a one-line description in `README.md` and none there yet. `tadw-routing-gaps-9wq` covers
closing that.

**Pipelines.** Each step feeds the next. The per-step detail is in `README.md`.

```text
A  Business Planning:  /business-ideas → /plan-feature → /plan-review → /plan-to-beads
B  Code Quality:       /fresh-eyes-cr → /quality-gates → /verify-acceptance → /tadw:ship → /publish-plugin
C  Product Strategy:   /competitive-analysis → /product-research → /product-roadmap → /product-brief → /ab-test-design
```

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

Doing it by hand is how the state drifted twice, and neither failure announced itself: `plugin.json`
sat at 2.10.1 while main ran 13 commits past its release commit, and `v2.10.0` and `v2.10.1` were
created locally and never pushed. Read the last tag with `git tag --list 'v*' --sort=-v:refname`,
because lexical order puts `v2.10.1` above `v2.5.2` and a released tag then reads as missing.

**Registered Skills** (45). One-line descriptions live in the `README.md` skills
table and in each `skills/<name>/SKILL.md` frontmatter, which is what the runtime actually
reads when deciding what to invoke.

`ab-test-design` `agentic-clean-code` `architecture-decision-record` `aso-audit` `bead-audit`
`bead-create` `bead-refine` `business-ideas` `code-simplify` `competitive-analysis` `domain-modeling`
`feature-development` `grilling` `house-response-style` `idea-wizard` `plan-review`
`plan-to-beads` `pr-maintenance`
`product-brief` `product-research` `product-roadmap` `product-surface-docs` `production-ops`
`publish-plugin`
`quality-gates` `research-ingest` `review-fresh-eyes` `review-python` `review-rails`
`roadmap-dashboard` `ship` `style-fizzy` `style-frontend` `style-go` `style-markdown` `style-python` `style-rails`
`style-rspec` `style-swift` `style-testing` `terraform-iac-expert` `triage-beads` `ux-audit`
`ux-audit-ios` `verify-acceptance`

**Registered Agents** (12). Descriptions live in the `README.md` agents table and in
each `agents/<name>.md` frontmatter.

`claude-md-reviewer` `code-reviewer` `diagnostician` `feature-planner` `product-analyst`
`product-cartographer` `product-manager` `project-manager` `research-librarian`
`software-engineer` `ux-product-designer` `ux-product-designer-ios`

**Registered Commands** (31). Descriptions live in the `README.md` command tables
and in each `commands/<name>.md` frontmatter.

`/adr` `/agentic-clean-code` `/aso-audit` `/bead-audit-all` `/bead-refine` `/build` `/code-review` `/diagnose`
`/fresh-eyes-cr` `/frontend-code-review` `/grill-me` `/plan-feature` `/plan-review` `/plan-to-beads`
`/pr-maintain` `/prod-ops` `/product-analysis` `/product-surface-docs` `/python-code-review`
`/quality-gates` `/rails-code-review` `/research-ingest` `/response-style`
`/review-claude-md` `/roadmap-dashboard` `/swift-code-review` `/terraform-review` `/ux-audit`
`/ux-audit-ios` `/validate-plugin` `/verify-acceptance`

### Hooks

`hooks/style-core-hooks.json` wires one feature. The `hooks` field in `plugin.json` registers it,
and takes a single manifest path. Design notes, rationale, and the test strategy live in
[docs/HOOKS.md](docs/HOOKS.md).

**Always-on style core.** `SessionStart` injects `hooks/style-core.md` plus the
`house-response-style` skill body. `SubagentStart` injects the coding core alone. Each document
opens with a marker line, so you can see in any session whether it loaded. Off-switch:
`TADW_STYLE_CORE=off`, or a flag file at `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`.

The payload exceeds the 10,000-character cap Claude Code puts on each hook output. So
`SessionStart` ships as several manifest entries that differ only in a payload index, two of
them today. `docs/HOOKS.md` tabulates the exact sizes, and `node hooks/test-hooks.js` asserts
them.

Do not collapse those entries into one. The tail is then discarded in silence, and the marker
that says the core loaded survives inside the surviving preview.

**Read the count from the manifest, never from memory.** It was three until the response style
was cut to 9,713 characters on 2026-08-26, which brought that document back inside one payload.
`getSessionStartPayloads()` decides the split at run time, and the suite fails when the manifest
disagrees with it.

Both style hooks run through `hooks/run-hook.sh`, which needs `node` on the non-interactive
shell's PATH. Without `node`, the wrapper emits
`<!-- house-style-core: FAILED to load ... -->` instead of failing silently.

These hooks fire in **every project** the plugin is loaded for, non-coding sessions included. A
`SessionStart` hook cannot see the task type.

### Portable hooks for other repositories

`scripts/` holds hooks that belong to a **project** rather than to this plugin, with an installer
for each. They are not wired here, and `plugin.json` does not reference them.

- `scripts/label_bead_on_skill_invocation.sh` labels the bead that a skill invocation acts on. It
  is wired to `PreToolUse` (matcher `Skill`), `UserPromptSubmit`, and `Stop`. **This is the copy
  of record**, and deployed copies are downstream of it.
- `scripts/install_label_bead_on_skill_invocation.sh` installs it into whatever repository you
  run it from. Re-running it is safe. `--dest-dir` moves the destination.
- `... --check` reports whether the installed copy matches the source, and whether all three
  events reference it. It changes nothing, and exits 1 when either is out of step.

Two properties matter to the target repository:

- **Labeling leaves the working tree as clean as it found it.** It writes to the `bd` database,
  and commits and pushes nothing. Refreshing `.beads/issues.jsonl` is conditional: it happens
  when the export is already modified, or when `TADW_BEAD_LABEL_EXPORT=1` is set.
- **Every failure path exits 0**, so a skill runs whether or not its bead could be labeled. Two
  records make an outage visible: the log at `<git-common-dir>/bead-label.log`, and `--doctor`,
  which resolves the current branch and prints what each labeled command would do.

**A session can outlive the directory it was started in.** Landing a bead removes its worktree.
Each wired command guards on `test -x <path>`, so a missing script is a silent no-op rather than
a `Stop hook error` every turn. That guard only stops the noise. Such a session labels nothing,
so end it and start a new one in a directory that exists.

Rationale, incident history, and the candidate-narrowing filters live in
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

### Agent Integration

An agent should:

- Reference an existing skill rather than duplicate its knowledge.
- Give concrete output formats, with examples.
- Carry a quality checklist, for consistency.
- Name its integration points with other tools.

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

**Five skills are accepted orphans.** `/validate-plugin` reports `business-ideas`,
`domain-modeling`, `idea-wizard`, `publish-plugin`, and `ship` as orphans, because no agent and no
command references them. You invoke all five directly as `/<name>`, so a referrer would add
nothing.

Two of the seven listed before are no longer orphans. `commands/bead-refine.md` now names
`bead-create` and `triage-beads`, so the check finds them.

The check follows agent and command references alone, so it misses two live paths: the `grilling`
skill reaches `domain-modeling`, and `publish-plugin` invokes `ship` to land a branch. It also
matches on the skill's name, so `commands/adr.md` counts as a referrer of
`architecture-decision-record` even though it writes the name without backticks. Read the orphan
rule as a prompt to check that a skill is still reachable, not as a defect list.

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
   runs the export itself, silently.
2. **Never ask the author to sync the Dolt remote.** Syncing is a machine's job. An agent that is
   already pushing runs the sync too, or says nothing about it.
3. **Report tracker plumbing only when it fails.** A successful export is not news. A failed one
   is, because the beads then exist on one machine alone.

This constrains agents, not `bd` itself. `bd` stays explicit. The automation belongs in this
repository's own `.githooks/`, where git tracks it and the author can read it. `tadw-pm8` covers
building it. Until it lands, agents absorb the step by hand and stay quiet about it.

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

**Publishing is a separate decision, not step 9.** The push in step 5 already put the change in
front of every consumer, because the marketplace follows this repository's default branch.
Numbering and tagging that state is `/publish-plugin`. Several landings usually batch into one
release. See "Releasing" above.

**Rules:**

- The work is not complete until `git push` succeeds.
- Never stop before pushing, because that leaves the work stranded locally.
- Never say "ready to push when you are". You push.
- If the push fails, resolve the cause and retry until it succeeds.

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
