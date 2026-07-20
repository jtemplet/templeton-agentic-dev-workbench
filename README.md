# templeton-agentic-dev-workbench

Personal Claude Code plugin — an agentic development workbench with custom agents, skills, and commands for Python, Ruby/Rails, JavaScript/TypeScript/React/Vue, Swift/iOS, and Terraform development.

## Installation

```bash
# Register marketplace
/plugin marketplace add jtemplet/templeton-agentic-marketplace

# Install this plugin
/plugin install templeton-agentic-dev-workbench@templeton-agentic-marketplace
```

## Workflow Pipelines

### Pipeline A — Business Planning

`/business-ideas` → `/plan-feature <idea>` → `/plan-review` → `/plan-to-beads`

| Command | What it does |
|---|---|
| `/business-ideas` | Analyze business model, surface 10 revenue-focused feature ideas |
| `/plan-feature <idea>` | Explore codebase, draft structured plan with acceptance criteria to `docs/plans/` |
| `/plan-review <path>` | Gate on acceptance criteria, evaluate plan across 7 dimensions (incl. MECE audit), render verdict |
| `/plan-to-beads <path>` | Decompose plan into `br` issues; each bead audited for Why, How, and Done when |

### Pipeline B — Code Quality

`/fresh-eyes-cr` → `/quality-gates`

| Command | What it does |
|---|---|
| `/fresh-eyes-cr` | Review changed code with fresh eyes, find and fix bugs directly |
| `/quality-gates` | Run tests, linting, type checks, doc freshness, security scan |

### Debugging

| Command | What it does |
|---|---|
| `/diagnose <bug>` | Investigate thoroughly before fixing, gather evidence, test hypotheses, present root cause |

### PR Maintenance

Keep a long-lived PR rebased on its parent branch and green on CI. Detects the PR's actual base from GitHub (so stacked PRs work), rebases with `--force-with-lease`, and applies minimal CI fixes scoped to files already in the PR diff.

| Command | What it does |
|---|---|
| `/pr-maintain` | One maintenance iteration: detect base branch, rebase, resolve conflicts, push with lease, diagnose and fix failing required CI checks, report |

Pair with `/loop` to run on a schedule:

```text
/loop 6h /pr-maintain
```

### Pipeline C — Product Strategy

`/competitive-analysis` → `/product-research` → `/product-roadmap` → `/product-brief <feature>` → `/ab-test-design <hypothesis>`

| Command | What it does |
|---|---|
| `/competitive-analysis` | Deep competitor teardown with positioning map, moat analysis, trajectory mapping, and feature gap analysis |
| `/product-research` | Synthesize user signals by segment into ranked opportunities using JTBD, anti-jobs, and evidence-weighted scoring |
| `/product-roadmap` | Prioritized roadmap with themes, capacity modeling, bet classification, and Now/Next/Later sequencing |
| `/product-brief <feature>` | PM-to-engineering handoff: problem, success metrics, scope (MVP + full vision), acceptance criteria |
| `/ab-test-design <hypothesis>` | Complete experiment spec with metrics, sample size, rollout plan, guardrails, and decision criteria |

### Product Research

| Command | What it does |
|---|---|
| `/product-analysis <product>` | Objective product analysis: features, pricing, competitors, pain points, market capture |
| `/research-ingest` | Ingest a new source into the Research wiki: read, discuss, summarize, create entity/concept pages |

### Design & UX

| Command | What it does |
|---|---|
| `/ux-audit <app-url>` | Playwright-driven UX audit of a web app, evaluates 7 dimensions (accessibility, design system, IA, interaction, content, emotional design, cognitive load), report saved to `docs/ux-audits/` |
| `/ux-audit-ios <app-name>` | iOS Simulator UX audit via `xcrun simctl`, tests Dynamic Type / Dark Mode / accessibility settings, evaluates same 7 dimensions against Apple HIG, report saved to `docs/ux-audits/` |

### App Store Optimization

| Command | What it does |
|---|---|
| `/aso-audit [app-id]` | ASO health audit across 10 weighted factors (title, subtitle, keyword field, description, screenshots, preview video, ratings, icon, keyword rankings, conversion signals), produces an ASO Score Card and prioritized action plan, report saved to `docs/aso-audits/` |

## Commands

### Code Review

| Command | Description |
|---|---|
| `/code-review` | Auto-detect languages and apply correct review skill per file |
| `/python-code-review` | Python review (PEP 8, Google Style Guide) |
| `/rails-code-review` | Rails 8 review (security, conventions, Hotwire) |
| `/swift-code-review` | Swift/iOS review (Sandi Metz, protocol-oriented design) |
| `/frontend-code-review` | Frontend review (JS/TS/React/Vue, component design, patterns) |
| `/terraform-review` | Terraform/IaC review (security, best practices, modules) |
| `/review-claude-md` | Review and optimize CLAUDE.md/AGENTS.md files |

### Development

| Command | Description |
|---|---|
| `/python-feature-dev <feature>` | Guided Python feature development (4-phase workflow) |
| `/idea-wizard` | Generate 30 improvement ideas, evaluate, distill to top 5 |
| `/adr <topic>` | Record an architectural decision with context and rationale |
| `/agentic-clean-code [target]` | Design or review agentic code (tools, prompts, orchestration) against Clean Code + POODR |

### Maintenance

| Command | Description |
|---|---|
| `/bead-audit [id or content]` | Audit bead bodies (Marr, size, type-specific sections); content-vs-structure verdicts, JSON mode, drafts applyable fixes |
| `/product-surface-docs [dir]` | Build/refresh a MECE/Pyramid product doc tree by surface under docs/products/; surfaces bugs/gaps/debt into a findings ledger |
| `/pr-maintain` | Keep the current branch's PR rebased on its parent and passing CI; safe to pair with `/loop` |
| `/roadmap-dashboard [jsonl]` | Build a self-contained interactive HTML project dashboard at `docs/roadmap.html` from the codebase and the `beads` tracker |
| `/validate-plugin` | Check plugin integrity and cross-references |

### Operations

| Command | Description |
|---|---|
| `/prod-ops` | Safely operate production apps on a Hetzner VPS over SSH (service ops + PostgreSQL data ops) under strong guardrails; loads the `production-ops` skill |

## Skills

| Skill | Description |
|---|---|
| `review-python` | PEP 8 and Google Style Guide review technique |
| `review-rails` | Rails 8 systematic review (security, conventions, performance) |
| `style-rspec` | Opinionated RSpec style (request specs, context-driven) |
| `style-rails` | Rails 8 Way conventions and best practices |
| `style-python` | Python style (Sandi Metz principles adapted for Python) |
| `style-swift` | Swift style (Sandi Metz, protocol-oriented design) |
| `style-frontend` | Frontend style (JS/TS/React/Vue, Sandi Metz principles) |
| `terraform-iac-expert` | Terraform/IaC expertise across AWS, Azure, GCP |
| `style-fizzy` | Vanilla Rails conventions for the Fizzy codebase |
| `idea-wizard` | Structured ideation: generate, evaluate, distill |
| `architecture-decision-record` | ADR format with context, options, and rationale |
| `business-ideas` | Revenue-focused feature ideation with "who pays and why" thesis |
| `plan-review` | Acceptance-criteria gate + 7-dimension plan evaluation (completeness, feasibility, scope, risks, deps, MECE, actionability) |
| `aso-audit` | App Store Optimization audit across 10 weighted factors, ASO Score Card, prioritized action plan |
| `ux-audit` | Web UX audit via Playwright; 7-dimension evaluation with severity-ranked report |
| `ux-audit-ios` | iOS UX audit via Simulator; Dynamic Type / Dark Mode / Bold Text testing against Apple HIG |
| `code-simplify` | Language-agnostic simplification workflow; loads the matching language style skill |
| `review-fresh-eyes` | Bug-and-correctness pass over recently changed code, fixes issues directly |
| `feature-development` | 4-phase guided implementation (discovery, implementation, simplification, linting) across languages |
| `plan-to-beads` | Decompose a feature plan into `br` issues; each bead audited for Why (L1), How (L2), and Done when (acceptance) |
| `bead-audit` | Audit existing bead bodies against the Marr, size, and type-specific section standards; separates content from structure (format-only issues are auto-fixable), honors native tracker fields, optional 0-100 scorecard banded Poor→Excellent and capped by verdict, JSON output for backlog grooming |
| `product-surface-docs` | Build/refresh a MECE/Pyramid product doc tree under `docs/products/` by surface; grounds claims in code, proactively hunts bugs/gaps/debt into `_findings.md` (cheap capture) and promotes actionable ones into bead-audit-compliant beads, ships a staleness checker (in-repo + multi-repo) |
| `research-ingest` | Ingest a new source into the Research wiki, with study quality assessment and cross-referencing |
| `competitive-analysis` | Competitor teardown with positioning map, moat analysis, trajectory, and feature gaps |
| `ab-test-design` | A/B test design with hypothesis, metrics, sample size, rollout plan, and decision criteria |
| `product-research` | User signal synthesis by segment using JTBD, anti-jobs, and evidence-weighted opportunity scoring |
| `product-roadmap` | Roadmap with themes, capacity modeling, bet classification, and Now/Next/Later sequencing |
| `product-brief` | PM-to-engineering handoff: problem, metrics, scope, acceptance criteria, experiment tie-in |
| `agentic-clean-code` | Clean Code + POODR principles for agentic systems: tool design, prompt architecture, orchestration, naming, testability |
| `pr-maintenance` | Keep a single PR rebased on its actual parent branch and green on CI with minimal, in-scope edits; designed to run on a loop |
| `roadmap-dashboard` | Synthesize the codebase and the `beads` tracker into one self-contained, zero-dependency interactive HTML dashboard at `docs/roadmap.html` (executive KPIs, pure HTML/CSS diagrams, Kanban board, prioritized roadmap); ships a `collect_beads.py` collector and versions the output |
| `production-ops` | Safely operate production Docker Compose apps on a single Hetzner VPS over SSH (two-hop `root` -> `su - deploy`); service ops and PostgreSQL data ops under strong guardrails: read-only by default, secret-free `hetzner-prod` alias, mandatory `pg_dump` before any data mutation, transactional one-off writes, verify-after, written rollback, and hard-stops on volume wipes / `prune` / `DROP` / `TRUNCATE` / `WHERE`-less writes |

## Agents

| Agent | Description |
|---|---|
| `code-reviewer` | Auto-detects languages, dispatches to correct review skill (read-only) |
| `software-engineer` | Editing role for code work; routes to code-simplify, review-fresh-eyes, or feature-development based on intent |
| `claude-md-reviewer` | CLAUDE.md optimization with quantitative scoring |
| `feature-planner` | Explores codebase, drafts structured plans with acceptance criteria to `docs/plans/` |
| `project-manager` | Decomposes plans into `br` issues; ensures each bead has Why, How, and acceptance criteria (uses `plan-to-beads` skill) |
| `diagnostician` | Read-only investigation — evidence, hypotheses, root cause |
| `product-analyst` | Objective product analysis (features, pricing, competitors, pain points, market capture) |
| `research-librarian` | Ingests sources into Research wiki: reads, assesses study quality, generates summaries and entity/concept pages (uses `research-ingest` skill) |
| `ux-product-designer` | UX audit of a web app via Playwright, 7-dimension evaluation with severity-ranked report |
| `ux-product-designer-ios` | UX audit of an iOS app via Simulator, tests Dynamic Type / Dark Mode / accessibility, 7-dimension evaluation against Apple HIG |
| `product-manager` | Senior/Staff PM routing agent; dispatches to competitive-analysis, ab-test-design, product-research, product-roadmap, and product-brief skills |
| `product-cartographer` | Maps a codebase into a MECE/Pyramid `docs/products/` tree and proactively hunts for bugs/gaps/debt, logging each to a ledger and promoting actionable ones into bead-audit-compliant beads; refresh-first (uses `product-surface-docs` skill) |

## Architecture

```text
commands/*.md → agents/*.md → skills/*/SKILL.md
     |               |              |
  Invokes       Follows        Implements
```

**Example flow:**

1. User invokes `/rails-code-review` command
2. Command loads `review-rails` skill via the Skill tool
3. Skill defines the systematic review technique
4. Output follows the skill's specified format

## Always-On Style Core

This plugin injects a small, universal coding-style core into **every session and every
spawned subagent** via Claude Code lifecycle hooks (`SessionStart` + `SubagentStart`). The
model-invoked `style-*` / `review-*` skills still carry the detailed per-language rules; the
always-on hook just guarantees the universal core (`hooks/style-core.md`) is present even when
a skill is not loaded and inside subagents that do not inherit the parent's skills. Injected
text opens with a `<!-- house-style-core: loaded -->` marker so you can see it is active.

`SessionStart` additionally injects a response style (`hooks/response-style.md`,
`<!-- house-response-style: loaded -->` marker): respond concisely, suggest a follow-up
question only when the answer genuinely raises one, and end any response that leaves work
open with a "Next actions" section split into "Me (Claude)" and "You". Parent sessions
only; subagents get the coding-style core alone, since their output goes to the
orchestrator, not a human.

**Behavior change on upgrade.** Installing this version makes the style core fire in **every
session for every project** the plugin is loaded for, including non-coding ones (product,
research, ASO). This is intentional. Use the off-switch below for sessions where it is noise.

**Off-switch.** Set `TADW_STYLE_CORE=off` (also `0` / `false`), or create a flag file at
`${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`. Either disables both the session and
subagent injection.

**Requires `node` on PATH.** The hook runs `node`. If `node` is not on the non-interactive
shell's PATH (common with `fnm`/`nvm`), the hook silently does nothing and the core is not
injected (no error, just no marker line). Ensure `node` resolves in a non-interactive shell.

**Test the hooks:** `node hooks/test-hooks.js` (no dependencies, no install).

## Creating Components

### New Skill

1. Create `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`)
2. Register in AGENTS.md

### New Agent

1. Create `agents/<name>.md` with YAML frontmatter (`name`, `description`, `model`, `tools`)
2. Register in AGENTS.md

### New Command

1. Create `commands/<name>.md` with YAML frontmatter (`description`, optional `argument-hint`)
2. Reference an agent or skill in the body
3. Register in AGENTS.md

Run `/validate-plugin` after changes to verify integrity.

## License

MIT License
