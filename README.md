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

`/business-ideas` → `/plan-feature <idea>` → `/review-plan` → `/plan-to-beads`

| Command | What it does |
|---|---|
| `/business-ideas` | Analyze business model, surface 10 revenue-focused feature ideas |
| `/plan-feature <idea>` | Explore codebase, draft structured plan to `docs/plans/` |
| `/review-plan <path>` | Evaluate plan across 6 dimensions, render verdict |
| `/plan-to-beads <path>` | Decompose plan into `br` issues with dependency graph |

### Pipeline B — Code Quality

`/fresh-eyes-cr` → `/quality-gates`

| Command | What it does |
|---|---|
| `/fresh-eyes-cr` | Review changed code with fresh eyes, find and fix bugs directly |
| `/quality-gates` | Run tests, linting, type checks, doc freshness, security scan |

### Debugging

| Command | What it does |
|---|---|
| `/diagnose <bug>` | Investigate thoroughly before fixing — gather evidence, test hypotheses, present root cause |

### Product Research

| Command | What it does |
|---|---|
| `/product-analysis <product>` | Objective product analysis — features, pricing, competitors, pain points, market capture |

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

### Maintenance

| Command | Description |
|---|---|
| `/validate-plugin` | Check plugin integrity and cross-references |

## Skills

| Skill | Description |
|---|---|
| `python-code-review` | PEP 8 and Google Style Guide review technique |
| `rails-code-review` | Rails 8 systematic review (security, conventions, performance) |
| `templeton-rspec-style` | Opinionated RSpec style (request specs, context-driven) |
| `rails-conventions` | Rails 8 Way conventions and best practices |
| `templeton-python-style` | Python style (Sandi Metz principles adapted for Python) |
| `templeton-swift-style` | Swift style (Sandi Metz, protocol-oriented design) |
| `templeton-frontend-style` | Frontend style (JS/TS/React/Vue, Sandi Metz principles) |
| `terraform-iac-expert` | Terraform/IaC expertise across AWS, Azure, GCP |
| `fizzy-style` | Vanilla Rails conventions for the Fizzy codebase |
| `idea-wizard` | Structured ideation: generate, evaluate, distill |
| `architecture-decision-record` | ADR format with context, options, and rationale |
| `business-ideas` | Revenue-focused feature ideation with "who pays and why" thesis |
| `plan-review` | 6-dimension plan evaluation (completeness, feasibility, scope, risks, deps, actionability) |

## Agents

| Agent | Description |
|---|---|
| `code-reviewer` | Auto-detects languages, dispatches to correct review skill |
| `code-simplifier` | Simplifies Python/Ruby code while preserving functionality |
| `python-feature-developer` | Guided 4-phase Python feature development |
| `frontend-code-reviewer` | Frontend code review (JS/TS/React/Vue) |
| `claude-md-reviewer` | CLAUDE.md optimization with quantitative scoring |
| `feature-planner` | Explores codebase, drafts structured plans to `docs/plans/` |
| `plan-to-beads` | Decomposes plans into `br` issues with dependency graph |
| `fresh-eyes-reviewer` | Reviews changed code for bugs, fixes them directly |
| `diagnostician` | Read-only investigation — evidence, hypotheses, root cause |
| `product-analyst` | Objective product analysis (features, pricing, competitors, pain points, market capture) |

## Architecture

```text
commands/*.md → agents/*.md → skills/*/SKILL.md
     |               |              |
  Invokes       Follows        Implements
```

**Example flow:**

1. User invokes `/rails-code-review` command
2. Command loads `rails-code-review` skill via the Skill tool
3. Skill defines the systematic review technique
4. Output follows the skill's specified format

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
