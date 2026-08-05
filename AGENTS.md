# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. `CLAUDE.md` re-includes this file with `@AGENTS.md`.

## Repository Overview

This is a personal Claude Code plugin repository - an agentic development workbench containing custom agents, skills, and commands for Python, Ruby/Rails, JavaScript/TypeScript (React/Vue), Swift/iOS, and Terraform development.

## Architecture

### Plugin Structure

This repository follows the Claude Code plugin architecture with three main directories:

- **`agents/`** - Custom agent definitions that can be invoked via the Task tool or manually followed
- **`commands/`** - Slash commands (e.g., `/rails-code-review`) that provide quick access to workflows
- **`skills/`** - Reusable skill modules that encode best practices and systematic techniques

### Component Relationships

```text
commands/*.md → agents/*.md → skills/*/SKILL.md
     ↓               ↓              ↓
  Invokes       Follows        Implements
```

**Example Flow:**

1. User invokes `/rails-code-review` command
2. Command loads `review-rails` skill via the Skill tool
3. Skill defines the systematic review technique
4. Output follows the skill's specified format

### Agent Architecture

Agents are structured workflow definitions located in `agents/`. Each agent:

- Defines a specific role or expertise area
- References skills via the Skill tool
- Specifies required workflow steps
- Defines output format and quality checklist
- Includes integration points with other tools

### Skill Architecture

Skills are located in `skills/*/SKILL.md` and contain:

- YAML frontmatter with `name` and `description`
- Systematic techniques and frameworks
- When to use / when not to use guidelines
- Integration patterns with workflows
- Quick reference documentation

Skills can be invoked:

1. Directly: "Use the review-rails skill"
2. Via commands: `/rails-code-review`
3. Via agent workflows: Task tool with custom agent

## Development Patterns

### Creating New Skills

Skills should be self-contained in `skills/<skill-name>/`:

```text
skills/
  my-skill/
    SKILL.md      # Main skill content with YAML frontmatter
    README.md     # User-facing documentation (optional)
```

**SKILL.md structure:**

```markdown
---
name: skill-name
description: One-line description for when to use this skill
---

# Skill Title

## When to Use

[Specific scenarios]

## Implementation

[Step-by-step technique]
```

### Creating New Agents

Agents should be placed in `agents/` and follow this structure:

```markdown
---
name: agent-name
description: When to use this agent
model: inherit
tools: [list of allowed tools]
---

# Role: [Agent Role]

## Core Responsibilities

[What this agent does]

## Required Workflow

[Exact steps to follow]

## Output Format

[Expected output structure]

## Critical Rules

[Always/Never lists]

## Quality Checklist

[Pre-completion verification]
```

### Creating New Commands

Commands are shortcuts placed in `commands/`:

```markdown
---
description: One-line description
---

[Instructions that load agent or skill]
```

## Language-Specific Workflows

### Python Development

**Code Review:** Use `/python-code-review` or the `review-python` skill

- Checks PEP 8 and Google Python Style Guide compliance
- Reviews security, performance, and maintainability

**Feature Development:** Use `/python-feature-dev` or the `software-engineer` agent + `feature-development` skill

- 4-phase workflow: discovery, implementation, simplification, linting
- Loads `style-python` for Python file style decisions
- Runs `ruff` for linting

**Code Simplification:** Use the `software-engineer` agent + `code-simplify` skill

- Works across Python, Ruby/Rails, Frontend, Swift
- Loads the matching language style skill automatically
- Reduces complexity while preserving functionality

### Rails Development

**Code Review:** Use `/rails-code-review` or `/code-review` (auto-detects Rails)

- Rails 8-aware with modern Hotwire/Turbo patterns
- Security-first approach with pragmatic severity assessment
- Understands `where.missing`, `broadcast_refresh_to`, Solid Stack patterns

**Testing:** Use the `style-testing` skill (language-agnostic), plus `style-rspec` if the project uses RSpec

- `style-testing` owns the principles: one behavior per test, hoisted declarative setup,
  deterministic clocks and identification, scenario-named groups, what not to test
- `style-rspec` adds only the RSpec/Rails spelling: request specs over controller specs,
  `let`/`let!`/`subject` mechanics, FactoryBot build strategies

**Conventions:** Use the `style-rails` skill

- Enforces Rails 8 conventions and best practices
- Ensures idiomatic Rails patterns

**Common Commands:**

```bash
# Running tests
bundle exec rspec

# Running code review
git diff main...HEAD  # See changes to be reviewed
```

### Swift/iOS Development

**Code Review:** Use `/swift-code-review` or the `style-swift` skill

- Sandi Metz principles adapted for Swift
- Protocol-oriented design over class inheritance
- TRUE code (Transparent, Reasonable, Usable, Exemplary)

### Frontend Development

**Code Review:** Use `/frontend-code-review` (frontend-scoped shortcut for `/code-review`)

- Loads the `style-frontend` skill from the `code-reviewer` agent
- JavaScript/TypeScript, React, and Vue code reviews (read-only)
- Sandi Metz principles adapted for frontend
- Focuses on separation of concerns (logic vs presentation)
- Checks component design, TypeScript usage, and modern patterns
- Validates proper hook/composable patterns

**Style Guide:** Use the `style-frontend` skill

- TRUE components (Transparent, Reasonable, Usable, Exemplary)
- Wait for duplication before abstracting
- Small, focused components (~100-150 lines)
- Extract business logic to custom hooks (React) or composables (Vue)
- Composition over props explosion

### Infrastructure as Code

**Terraform Review:** Use `/terraform-review` or the `terraform-iac-expert` skill

- Reviews Terraform configurations
- Checks for security and best practices
- Validates resource configurations

### Agentic Systems

**Design & Review:** Use the `agentic-clean-code` skill

- Clean Code (Uncle Bob) and POODR (Sandi Metz) principles transposed to the agentic context
- Covers tool design (SRP, explicit contracts, idempotency, no surprise side effects)
- Covers prompt architecture (small prompts, no implicit state, context objects)
- Covers orchestration (separation of planning from execution, explicit agent boundaries, fail-loud error policies)
- Includes a smell checklist for reviewing agents, tools, and prompts before ship
- Invoke with `/agentic-clean-code [target]`, or let it auto-detect the agent/skill/tool files changed on the branch

### Product Management

**Competitive Analysis:** Use `/competitive-analysis` or the `competitive-analysis` skill

- Deep competitor teardown with positioning maps
- Feature gap analysis (table-stakes, differentiation, over-investment)
- Strategic recommendations with priority actions

**A/B Test Design:** Use `/ab-test-design` or the `ab-test-design` skill

- Complete experiment spec with hypothesis, metrics, sample size
- Guardrails, stopping rules, and pre-registered analysis plan
- Decision framework for every possible outcome

**Product Research:** Use `/product-research` or the `product-research` skill

- Synthesizes user signals into Jobs-to-Be-Done
- Opportunity scoring (Importance + Importance - Satisfaction)
- Ranked feature concepts with validation approaches

**Product Roadmap:** Use `/product-roadmap` or the `product-roadmap` skill

- Theme-based prioritization with ICE scoring
- Now/Next/Later time horizons with dependencies
- Explicit "not doing" list to prevent scope creep

**Product Brief:** Use `/product-brief` or the `product-brief` skill

- PM-to-engineering handoff document
- Problem statement, success metrics, scope (MVP + full vision)
- Acceptance criteria and experiment tie-in

**Product Analysis:** Use `/product-analysis` or the `product-analyst` agent

- Objective product analysis (features, pricing, competitors, pain points)
- Market capture and positioning assessment

### Ideation & Planning

**Idea Generation:** Use `/idea-wizard` or the `idea-wizard` skill

- Generates 30 improvement ideas for the current project
- Critically evaluates each, rejects weak candidates
- Distills to top 5 with confidence scores and actionable plans

**Decision Records:** Use `/adr` or the `architecture-decision-record` skill

- Records architectural decisions with context and rationale
- Tracks options considered and trade-offs
- Saves to `docs/decisions/NNNN-<topic>.md`

### Workflow Pipelines

**Pipeline A - Business Planning:**

`/business-ideas` → pick an idea → `/plan-feature <idea>` → `/plan-review docs/plans/...` → `/plan-to-beads docs/plans/...`

- **Business Ideas:** Analyzes the project's business model, generates 15 revenue-focused candidates, critically evaluates, presents top 10
- **Plan Feature:** Explores the codebase, drafts a structured implementation plan with testable acceptance criteria and a per-milestone "Done when", writes to `docs/plans/feature-plan-<name>.md`
- **Plan Review:** Runs an acceptance-criteria gate (a plan with none, or with only subjective ones, is Actionability RED), grounds the plan's claims in the actual codebase (named files, patterns, and stack must exist), evaluates the plan across 7 dimensions (completeness anchored to the `/plan-feature` template, feasibility, scope, risks, dependencies, MECE, actionability), runs a MECE audit for overlaps and gaps, renders a mechanical verdict; report-only, drafting missing Acceptance Criteria / Testing Strategy paste-ready and offering to apply
- **Plan to Beads:** Decomposes the plan into `br` issues with dependency graph, articulates Marr Levels 1 (Why) and 2 (How) and acceptance criteria (Done when) per bead, audits each, then confirms with user before creating

**Pipeline B - Product Strategy:**

`/competitive-analysis` → `/product-research` → `/product-roadmap` → `/product-brief <feature>` → `/ab-test-design <hypothesis>`

- **Competitive Analysis:** Researches competitors, builds positioning map with moat analysis, identifies feature gaps and trajectory
- **Product Research:** Synthesizes user signals by segment into Jobs-to-Be-Done, scores opportunities with evidence weighting
- **Product Roadmap:** Prioritizes features into themes with capacity modeling, bet classification, and Now/Next/Later horizons
- **Product Brief:** For a prioritized feature, writes the PM-to-engineering handoff with problem, metrics, scope, and acceptance criteria
- **A/B Test Design:** For any feature hypothesis, produces a complete experiment spec with rollout plan

**Pipeline C - Code Quality:**

`/fresh-eyes-cr` → `/quality-gates`

- **Fresh Eyes CR:** Auto-detects changed files, reads full files for context, finds and fixes bugs directly
- **Quality Gates:** Runs tests, linting, type checks, documentation freshness, and security scan with pass/fail/skip per gate

### Multi-Language Reviews

**Auto-Detecting Review:** Use `/code-review` or the `code-reviewer` agent

- Detects languages from changed files automatically
- Dispatches to the correct skill per language
- Produces a single consolidated review report

### Project Reporting

**Roadmap Dashboard:** Use `/roadmap-dashboard` or the `roadmap-dashboard` skill directly

- Synthesizes the codebase and the `beads` tracker into a single self-contained interactive HTML dashboard at `docs/roadmap.html`
- Collects tracker data with a bundled `collect_beads.py` script (refreshes JSONL, normalizes priorities, filters dependency edges to the blocking types, and annotates ready/blocked/blocked_by; always exits 0, emitting an empty shape when no tracker exists)
- Cross-references code against beads to classify each subsystem as Built / Partial / Stubbed / Planned and compute a blended, defensible completion percentage
- Renders zero-dependency pure HTML/CSS/vanilla-JS diagrams (architecture current-vs-target, data flow, DB relationships, dependency graph, milestone timeline + risk matrix), a Kanban board, collapsible deep-dives, a sticky TOC, and print CSS
- Versions the output (`docs/roadmap-vX.Y.html`) instead of overwriting a prior report; marks inferences with `[Inference]` tags and confidence scores

### PR Maintenance

**Keep a PR Green:** Use `/pr-maintain` or the `pr-maintenance` skill directly

- Detects the PR's actual base branch from GitHub (not hardcoded `origin/main`), so stacked PRs work
- Rebases with `git push --force-with-lease` (never plain `--force`)
- AI-assisted conflict resolution with hard-stops on migrations, lockfiles, and secrets
- Fixes failing required CI checks with edits scoped to files already in the PR diff
- Never modifies test assertions in files that were not already in the PR diff (prevents masking real failures)
- Idempotent per iteration, safe to run on a loop

**Running on a loop:**

```text
/loop 6h /pr-maintain
```

Each iteration reports rebase status, CI status, files touched, and any manual actions the user needs to take.

## Plugin Configuration

### Manifest File

`.claude-plugin/plugin.json` defines plugin metadata and the `hooks` field that wires the
always-on style core (see "Always-on style core (hooks)" below). It does **not** register
components: skills, agents, and commands are auto-discovered from their directories, and
`plugin.json` lists none of them. The registration surfaces are the component lists in this file
and the table in `README.md`.

The `name` field (`tadw`) is also the **invocation namespace**: every component in this plugin is
addressed as `tadw:<component>` (`tadw:fresh-eyes-cr`, `tadw:code-reviewer`). Changing `name` renames
every invocation path at once, including the ones hardcoded in other repos, so treat it as a breaking
change. It was `templeton-agentic-dev-workbench` before 2.0.0. Unrelated to the namespace despite the
shared letters: the `TADW_STYLE_CORE` off-switch and the `tadw-*` beads issue prefix.

**Registered Skills:**

- `review-python` - PEP 8 and Google Style Guide reviews
- `review-rails` - Rails 8-aware systematic code review
- `style-testing` - Universal, framework-independent test-style core (14 principles, plus a fenced appendix mapping each to its pytest/Vitest/XCTest/Minitest idiom); enforced framework-free by `scripts/check_framework_leak.py`, which has its own 15-case regression suite at `scripts/test_check_framework_leak.py` (`python3 skills/style-testing/scripts/test_check_framework_leak.py`)
- `style-rspec` - RSpec/Rails delta on `style-testing`
- `style-rails` - Rails conventions and best practices
- `style-python` - Python style preferences (Sandi Metz principles)
- `style-swift` - Swift/iOS with Sandi Metz principles and protocol-oriented design
- `style-frontend` - JavaScript/TypeScript/React/Vue with Sandi Metz principles
- `terraform-iac-expert` - Infrastructure as Code reviews
- `style-fizzy` - Vanilla Rails conventions for the Fizzy codebase
- `idea-wizard` - Generate 30 ideas, evaluate, distill to top 5
- `architecture-decision-record` - Record decisions with context, options, and rationale
- `business-ideas` - Analyze business model and surface 10 revenue-focused feature ideas
- `plan-review` - Fresh-eyes plan review that gates on the presence and testability of acceptance criteria, grounds the plan's claims in the codebase, judges completeness against the `/plan-feature` template, and audits MECE coverage; report-only, with paste-ready drafts for missing Acceptance Criteria / Testing Strategy and an offer-to-apply handoff
- `aso-audit` - App Store Optimization audit across 10 weighted factors with ASO Score Card and prioritized action plan
- `ux-audit` - Web UX audit via Playwright across 7 design dimensions with severity-ranked report
- `ux-audit-ios` - iOS UX audit via Simulator with Dynamic Type / Dark Mode / Bold Text testing against Apple HIG
- `code-simplify` - Language-agnostic simplification workflow that loads the matching language style skill
- `review-fresh-eyes` - Bug-and-correctness pass over recently changed code, fixes issues directly
- `feature-development` - 4-phase guided implementation (discovery, implementation, simplification, linting), language-agnostic
- `plan-to-beads` - Decompose a feature plan into br (beads_rust) issues with dependencies, auditing each bead against Marr Levels 1 (Why), 2 (How), and acceptance criteria (Done when) before creation
- `product-surface-docs` - Generate, refresh, and keep current a MECE/Pyramid-Principle product documentation tree under `docs/products/`, organized by product surface (web/api/iOS/...) and drilling into each surface's capabilities; grounds claims in code, proactively hunts bugs/gaps/debt into a `_findings.md` ledger with stable F-IDs (cheap capture, report everything) and promotes the actionable ones into `bead-audit`-compliant beads, ships a `check_staleness.py` (in-repo + multi-repo) so staleness is a command, and uses progressive disclosure (scripts/ + references/)
- `bead-audit` - Audit one or more bead issue bodies against the Marr audit, size audit, and type-specific section audit; tracker-agnostic (accepts pasted text, files, or any CLI output) but honors native tracker fields (e.g. `br`'s acceptance_criteria/design/notes); separates content verdict from structure verdict (format-only issues are an auto-fixable REFORMAT, not a FAIL), exempts epics and operational beads from the size band, self-verifies each drafted fix so it re-passes, gates write-back with an `applyable` flag so placeholder-bearing drafts never reach the tracker, and supports a JSON output mode for backlog-scale grooming. Emits an optional weighted scorecard (0-100, banded Poor/Weak/Adequate/Great/Excellent) derived from the verdicts and capped so the band can never outrank the pass/fail verdict, for ranking a backlog or gating on a target band; the rubric ships with a fixture regression suite under `references/fixtures/`
- `research-ingest` - Ingest a new source into the Research wiki, with study quality assessment and cross-referencing
- `competitive-analysis` - Deep competitor teardown with positioning map, moat analysis, trajectory mapping, and feature gap analysis
- `ab-test-design` - Rigorous A/B test design with hypothesis, metrics, sample size, rollout plan, guardrails, and decision criteria
- `product-research` - Synthesize user signals by segment into ranked opportunities using JTBD, anti-jobs, and evidence-weighted opportunity scoring
- `product-roadmap` - Prioritized roadmap with themes, capacity modeling, bet classification, Now/Next/Later sequencing, and dependencies
- `product-brief` - PM-to-engineering handoff with problem statement, success metrics, scope (MVP + full vision), acceptance criteria, and experiment tie-in
- `agentic-clean-code` - Clean Code and POODR principles transposed to agentic systems (tool design, prompt architecture, orchestration, naming, testability) for designing or reviewing agents, tools, and prompts
- `pr-maintenance` - Keep a single PR rebased on its actual parent branch and green on CI with minimal, in-scope edits; designed to run on a loop
- `roadmap-dashboard` - Synthesize the codebase and the `beads` tracker into one self-contained, zero-dependency interactive HTML dashboard at `docs/roadmap.html` (executive KPIs, pure HTML/CSS diagrams, Kanban board, prioritized roadmap); ships a `collect_beads.py` data-collection script and versions the output instead of overwriting
- `production-ops` - Safely operate the production apps (atlas, meridian, compass, ...) as Docker Compose stacks on a single Hetzner VPS over a two-hop SSH login (root, then `su - deploy`); covers service ops and PostgreSQL data ops under strong guardrails (read-only by default, secret-free `hetzner-prod` alias, mandatory `pg_dump` before any data mutation, transactional one-off writes, verify-after, written rollback, and hard-stops on volume wipes/`prune`/`DROP`/`TRUNCATE`/`WHERE`-less writes)
- `house-response-style` - The always-on response style as a single-source skill: lead with the answer, cut narration, write in **Simplified Technical English, the controlled-English standard specified in ASD-STE100** (its **writing rules** only, explicitly not its licensed dictionary: one word one meaning, one part of speech per word, active voice and imperative instructions, no jargon or borrowed metaphor like "tombstone", one instruction per sentence, 20-word instructions and 25-word explanations, positive phrasing, condition-before-instruction warnings, American English, with technical names and technical verbs kept verbatim, and self-reporting stated plainly rather than as "green" or "a flake" - the highest-drift case, since the reader cannot audit either word), put multi-factor choices in a decision matrix with a bold recommendation, structure only genuinely multi-part answers, suggest a follow-up only when earned, and end open work with an owner-split "Next actions" section. The `SessionStart` hook reads this file (frontmatter stripped) so the injected style and the on-demand `/response-style` command share one source of truth; carries a "why," Bad/Good pairs, escape hatches, and a pre-send check

**Registered Agents:**

- `code-reviewer` - Auto-detecting code review (dispatches to correct skill per language); read-only role
- `software-engineer` - Editing role for code work (simplify, fix bugs, implement features); routes to the right skill based on user intent
- `claude-md-reviewer` - CLAUDE.md optimization with quantitative scoring
- `feature-planner` - Generates detailed implementation plans, each with testable acceptance criteria, written to docs/plans/
- `project-manager` - Decomposes feature plans into br issues with dependencies, ensuring each bead carries Marr Levels 1 and 2 and acceptance criteria (uses `plan-to-beads` skill)
- `diagnostician` - Investigates bugs thoroughly before any fix is attempted
- `product-analyst` - Objective product analysis (features, pricing, competitors, pain points, market capture)
- `research-librarian` - Ingests new sources into the Research wiki, reads, discusses key points, generates summaries, creates entity/concept pages, updates index and log (uses `research-ingest` skill)
- `ux-product-designer` - Senior product designer that conducts a UX audit of a running web app via Playwright, grounded in AGENTS.md context, and produces a severity-ranked report across 7 design dimensions
- `ux-product-designer-ios` - Senior product designer that conducts a UX audit of an iOS app in the Simulator via xcrun simctl, tests Dynamic Type / Dark Mode / accessibility settings, and produces a severity-ranked report against Apple HIG standards
- `product-manager` - Senior/Staff PM who routes to competitive analysis, A/B test design, product research, and roadmap skills
- `product-cartographer` - Senior technical product documentarian and auditor who maps a codebase into a MECE/Pyramid `docs/products/` tree and, in the same pass, proactively hunts for bugs/gaps/debt, logging each to a findings ledger (cheap) and promoting the actionable ones into `bead-audit`-compliant beads; refresh-first, with a staleness checker (uses `product-surface-docs` skill)

**Registered Commands:**

- `/code-review` - Auto-detecting code review across all languages
- `/python-code-review` - Quick Python code review
- `/python-feature-dev` - Start Python feature development
- `/rails-code-review` - Quick Rails code review
- `/swift-code-review` - Swift/iOS code review
- `/frontend-code-review` - Frontend code review (JS/TS/React/Vue)
- `/terraform-review` - Terraform/IaC review
- `/review-claude-md` - CLAUDE.md optimization review
- `/validate-plugin` - Check plugin integrity and cross-references
- `/idea-wizard` - Generate and evaluate improvement ideas
- `/adr` - Record an architectural decision
- `/agentic-clean-code` - Design or review agentic systems (tools, prompts, orchestration) against Clean Code and POODR principles
- `/business-ideas` - Analyze business model, surface 10 revenue-focused feature ideas
- `/plan-feature` - Generate a detailed implementation plan for a feature
- `/plan-review` - Fresh-eyes review of a feature plan (report-only; grounds claims in the codebase, drafts missing acceptance criteria and test plans, offers to apply)
- `/plan-to-beads` - Decompose a feature plan into br issues with dependencies; each bead audited for Why (L1), How (L2), and Done when (acceptance criteria) before creation
- `/product-surface-docs` - Build/refresh a MECE/Pyramid product doc tree under `docs/products/` by surface, grounded in code, surfacing bugs/gaps/debt into a findings ledger
- `/bead-audit` - Audit one or more bead bodies; paste content directly, give a file path, or pipe your issue tracker's output - no specific CLI required
- `/bead-audit-all` - Single-pass, report-only audit of the whole backlog: enumerate every bead via `br`, score each once, report a ranked health table (worst band first). Bounded, not a `/goal` loop
- `/fresh-eyes-cr` - Review and fix obvious bugs in all changed code
- `/quality-gates` - Run tests, linting, type checks, docs, and security scan
- `/diagnose` - Investigate a bug thoroughly before attempting any fix
- `/product-analysis` - Generate an objective product analysis document
- `/research-ingest` - Ingest a new source into the Research wiki
- `/ux-audit` - Conduct a UX audit of a running web app (Playwright-driven), report saved to `docs/ux-audits/`
- `/ux-audit-ios` - Conduct a UX audit of an iOS app in the Simulator (xcrun simctl-driven), report saved to `docs/ux-audits/`
- `/aso-audit` - App Store Optimization audit across 10 weighted factors with ASO Score Card and prioritized action plan, report saved to `docs/aso-audits/`
- `/competitive-analysis` - Deep competitor analysis with positioning map, moat analysis, and gap analysis
- `/ab-test-design` - Design a rigorous A/B test for a feature hypothesis
- `/product-research` - Synthesize user signals into ranked product opportunities
- `/product-roadmap` - Build a prioritized product roadmap with themes and sequencing
- `/product-brief` - Write a product brief (PM-to-engineering handoff) for a feature
- `/pr-maintain` - Keep the current branch's PR rebased on its parent and passing CI; one iteration per invocation, safe to pair with `/loop`
- `/roadmap-dashboard` - Build a self-contained interactive HTML project dashboard at `docs/roadmap.html` from the codebase and the `beads` tracker
- `/prod-ops` - Safely operate the production apps on the Hetzner VPS over SSH (service ops + PostgreSQL data ops) under strong guardrails; loads the `production-ops` skill
- `/response-style` - Re-assert the house response style (concise, answer-first, Simplified Technical English, decision matrices for hard choices, owner-split "Next actions") to re-anchor after a compaction or inside a subagent; **reads** `skills/house-response-style/SKILL.md` directly rather than invoking it via the Skill tool, which refuses it because the skill sets `disable-model-invocation: true`

### Always-on style core (hooks)

The plugin ships an always-on coding-style core via Claude Code lifecycle hooks
(`hooks/style-core-hooks.json`, registered through the `hooks` field in `plugin.json`).
Unlike the model-invoked style skills, this fires automatically, so the house style is
present even when the model would not have chosen to load a skill, and even inside spawned
subagents (which never inherit the parent session's loaded skills).

**What it injects.** The universal, language-agnostic core from `hooks/style-core.md` (TRUE
code, ten cross-language principles, and an American-English spelling rule that covers
identifiers, comments, docs, and commit messages, with an explicit carve-out for names you
do not own). The detailed per-language rules stay in the
on-demand `style-*` and `review-*` skills; only the small universal core is always on.

- **`SessionStart`** injects the core plus the response style, sourced from the
  `house-response-style` skill (`skills/house-response-style/SKILL.md`, frontmatter stripped
  at inject time): respond concisely; write in Simplified Technical English, the
  controlled-English standard specified in ASD-STE100 (its writing rules only, never its
  licensed dictionary), using American English, and report your own work plainly rather than
  as "green" or "a flake"; put multi-factor
  choices in a decision matrix; suggest a follow-up
  question only when the answer genuinely raises one; end any response that leaves work open
  with a "Next actions" section split into "Me (Claude)" and "You". Injected as raw context
  into every new, resumed,
  cleared, compacted, **or forked** session (the matcher must list all five sources; omitting
  one silently skips injection for it, with no error and no marker). The same file backs the
  on-demand `/response-style` command, which **reads** it rather than invoking it through the
  Skill tool, so the always-on and invocable surfaces share one source of truth.
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

**Blast radius (behavior change).** Declaring `hooks` in `plugin.json` makes these hooks fire
in **every project** the plugin is loaded for, and (if distributed via the marketplace) for
**every consumer on upgrade**. The core fires in non-coding sessions too (product, research,
ASO), because a `SessionStart` hook cannot see the task type; the marker makes it self-evident
and the off-switch is the escape hatch.

**Test.** `node hooks/test-hooks.js` (Node built-ins only, no install) runs 12 checks: the
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
is unrelated). The suite also asserts that the count stated in this sentence matches the number
of checks it ran, since that number drifted three times while the suite was being written. Each
check was added after a real defect shipped green under a narrower suite: a matcher missing
`fork`, a dead `/response-style` command, a failure marker that ignored the off-switch, an
off-switch that silently stopped working when `tr` was off the PATH, and an agent reporting its
own work in shorthand the reader could not check.

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

### Adding a New Skill

1. Create directory: `skills/<skill-name>/`
2. Create `SKILL.md` with frontmatter and content
3. (Optional) Add `README.md` for user documentation
4. Add it to the "Registered Skills" list in this file and the skills table in `README.md`
   (do **not** edit `.claude-plugin/plugin.json`; skills are auto-discovered)
5. Reference it from an agent or command, or `/validate-plugin` will flag it as an orphan

### Adding a New Agent

1. Create file: `agents/<agent-name>.md`
2. Follow agent structure template
3. Reference existing skills where appropriate
4. Test with real scenarios
5. Add it to the "Registered Agents" list in this file and the agents table in `README.md`
   (do **not** edit `.claude-plugin/plugin.json`; agents are auto-discovered)

### Adding a New Command

1. Create file: `commands/<command-name>.md`
2. Add frontmatter with description
3. Write instructions that load appropriate agent or skill

## Notes

- This is a personal development workbench, not a production system
- Focus is on Python, Ruby/Rails, Swift/iOS, and Terraform development
- Skills encode proven techniques to prevent repeating solved problems
- Agents provide consistent, structured workflows
- Commands provide quick access to common operations
- Use `/validate-plugin` to check plugin integrity after making changes

## Issue Tracking (br + bv)

This project uses **br** (beads_rust) for issue CRUD and **bv** (beads_viewer) for triage and planning.

**Key principle:** `br` never auto-commits or runs git commands. All git operations are explicit.

### Common br Commands

```bash
# Issue lifecycle
br create "Issue title" -p 2 -t bug -l "label1,label2"
br list                              # List open issues
br show <id>                         # Show issue details
br update <id> --status in_progress
br update <id> --claim               # Atomic: assign to self + set in_progress
br close <id>                        # Close an issue
br ready                             # List unblocked, non-deferred issues

# Sync DB <-> JSONL (for git)
br sync --flush-only                 # Export DB -> JSONL (before git commit)
br sync --import-only                # Import JSONL -> DB (after git pull)
br sync --merge                      # 3-way merge after pull conflicts

# Dependencies
br dep add <issue> <depends-on>
br dep tree <issue>

# Labels
br label list-all                    # All labels with counts
```

### Common bv Commands

```bash
# Triage and planning (use these to decide what to work on)
bv --robot-next                      # Top pick + claim command
bv --robot-triage                    # Full triage: picks, quick wins, blockers
bv --robot-plan                      # Dependency-respecting execution tracks

# Analysis
bv --robot-insights                  # Graph metrics + critical path
bv --robot-alerts                    # Stale issues, blocking cascades
bv --robot-suggest                   # Duplicates, missing deps, label assignments
```

### Workflow

1. `bv --robot-next` — find out what to work on
2. `br update <id> --claim` — claim the issue
3. Do the work
4. `br close <id>` — close when done
5. `br sync --flush-only` — export to JSONL before committing

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

## Beads Workflow Integration

Full `br` and `bv` usage for agents, covering the `--robot-*` triage flags, scoping and filtering
recipes, the issue-management command set, and the git policy, lives in
[docs/beads-workflow.md](docs/beads-workflow.md). Read it before running any tracker command.
