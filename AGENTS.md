# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal Claude Code plugin repository - an agentic development workbench containing custom agents, skills, and commands for Python, Ruby/Rails, Swift/iOS, and Terraform development.

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
2. Command loads `rails-code-review` skill via the Skill tool
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

1. Directly: "Use the rails-code-review skill"
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

**Code Review:** Use `/python-code-review` or the `python-code-review` skill

- Checks PEP 8 and Google Python Style Guide compliance
- Reviews security, performance, and maintainability

**Feature Development:** Use the `python-feature-developer` agent

- Follows Sandi Metz principles via `templeton-python-style` skill
- 4-phase workflow: discovery → implementation → simplification → linting

**Code Simplification:** Use the `code-simplifier` agent

- Works with both Python and Ruby/Rails
- Applies language-specific style guides automatically
- Reduces complexity while preserving functionality

### Rails Development

**Code Review:** Use `/rails-code-review` or `/code-review` (auto-detects Rails)

- Rails 8-aware with modern Hotwire/Turbo patterns
- Security-first approach with pragmatic severity assessment
- Understands `where.missing`, `broadcast_refresh_to`, Solid Stack patterns

**Testing:** Use the `templeton-rspec-style` skill

- Opinionated RSpec style
- Request specs over controller specs
- Context-driven organization

**Conventions:** Use the `rails-conventions` skill

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

**Code Review:** Use `/swift-code-review` or the `templeton-swift-style` skill

- Sandi Metz principles adapted for Swift
- Protocol-oriented design over class inheritance
- TRUE code (Transparent, Reasonable, Usable, Exemplary)

### Frontend Development

**Code Review:** Use `/frontend-code-review` or the `frontend-code-reviewer` agent

- JavaScript/TypeScript, React, and Vue code reviews
- Sandi Metz principles adapted for frontend
- Focuses on separation of concerns (logic vs presentation)
- Checks component design, TypeScript usage, and modern patterns
- Validates proper hook/composable patterns

**Style Guide:** Use the `templeton-frontend-style` skill

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

`/business-ideas` → pick an idea → `/plan-feature <idea>` → `/review-plan docs/plans/...` → `/plan-to-beads docs/plans/...`

- **Business Ideas:** Analyzes the project's business model, generates 15 revenue-focused candidates, critically evaluates, presents top 10
- **Plan Feature:** Explores the codebase, drafts a structured implementation plan, writes to `docs/plans/feature-plan-<name>.md`
- **Review Plan:** Evaluates the plan across 6 dimensions (completeness, feasibility, scope, risks, dependencies, actionability), renders a verdict
- **Plan to Beads:** Decomposes the plan into `br` issues with dependency graph, confirms with user before creating

**Pipeline B - Code Quality:**

`/fresh-eyes-cr` → `/quality-gates`

- **Fresh Eyes CR:** Auto-detects changed files, reads full files for context, finds and fixes bugs directly
- **Quality Gates:** Runs tests, linting, type checks, documentation freshness, and security scan with pass/fail/skip per gate

### Multi-Language Reviews

**Auto-Detecting Review:** Use `/code-review` or the `code-reviewer` agent

- Detects languages from changed files automatically
- Dispatches to the correct skill per language
- Produces a single consolidated review report

## Plugin Configuration

### Manifest File

`.claude-plugin/plugin.json` defines plugin metadata and component registration:

**Registered Skills:**

- `python-code-review` - PEP 8 and Google Style Guide reviews
- `rails-code-review` - Rails 8-aware systematic code review
- `templeton-rspec-style` - Opinionated RSpec testing patterns
- `rails-conventions` - Rails conventions and best practices
- `templeton-python-style` - Python style preferences (Sandi Metz principles)
- `templeton-swift-style` - Swift/iOS with Sandi Metz principles and protocol-oriented design
- `templeton-frontend-style` - JavaScript/TypeScript/React/Vue with Sandi Metz principles
- `terraform-iac-expert` - Infrastructure as Code reviews
- `fizzy-style` - Vanilla Rails conventions for the Fizzy codebase
- `idea-wizard` - Generate 30 ideas, evaluate, distill to top 5
- `architecture-decision-record` - Record decisions with context, options, and rationale
- `business-ideas` - Analyze business model and surface 10 revenue-focused feature ideas
- `plan-review` - Fresh-eyes plan review for completeness, feasibility, and gaps

**Registered Agents:**

- `code-reviewer` - Auto-detecting code review (dispatches to correct skill per language)
- `code-simplifier` - Language-agnostic code simplification (Python & Ruby/Rails)
- `python-feature-developer` - Guided Python feature development
- `frontend-code-reviewer` - Comprehensive frontend code review (JS/TS/React/Vue)
- `claude-md-reviewer` - CLAUDE.md optimization with quantitative scoring
- `feature-planner` - Generates detailed implementation plans written to docs/plans/
- `plan-to-beads` - Decomposes feature plans into br issues with dependencies
- `fresh-eyes-reviewer` - Reviews and fixes code with fresh eyes
- `diagnostician` - Investigates bugs thoroughly before any fix is attempted

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
- `/business-ideas` - Analyze business model, surface 10 revenue-focused feature ideas
- `/plan-feature` - Generate a detailed implementation plan for a feature
- `/review-plan` - Fresh-eyes review of a feature plan
- `/plan-to-beads` - Decompose a feature plan into br issues with dependencies
- `/fresh-eyes-cr` - Review and fix obvious bugs in all changed code
- `/quality-gates` - Run tests, linting, type checks, docs, and security scan
- `/diagnose` - Investigate a bug thoroughly before attempting any fix

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
4. Register in `.claude-plugin/plugin.json` if needed

### Adding a New Agent

1. Create file: `agents/<agent-name>.md`
2. Follow agent structure template
3. Reference existing skills where appropriate
4. Test with real scenarios
5. Register in `.claude-plugin/plugin.json` if needed

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
