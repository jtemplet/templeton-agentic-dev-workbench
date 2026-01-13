# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal Claude Code plugin repository - an agentic development workbench containing custom agents, skills, and commands for Python and Ruby/Rails development.

## Architecture

### Plugin Structure

This repository follows the Claude Code plugin architecture with three main directories:

- **`agents/`** - Custom agent definitions that can be invoked via the Task tool or manually followed
- **`commands/`** - Slash commands (e.g., `/rails-code-review`) that provide quick access to workflows
- **`skills/`** - Reusable skill modules that encode best practices and systematic techniques

### Component Relationships

```
commands/*.md → agents/*.md → skills/*/SKILL.md
     ↓               ↓              ↓
  Invokes       Follows        Implements
```

**Example Flow:**
1. User invokes `/rails-code-review` command
2. Command loads `agents/rails-code-reviewer.md` workflow
3. Agent uses `skills/rails-code-review/SKILL.md` for systematic review technique
4. Output follows agent's specified format

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
```
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

**Code Review:** Use `/rails-code-review` or the `rails-code-reviewer` agent
- Rails 8-aware with modern Hotwire/Turbo patterns
- Security-first approach with pragmatic severity assessment
- Understands `where.missing`, `broadcast_refresh_to`, Solid Stack patterns

**Testing:** Use the `rails-rspec-tester` skill
- Opinionated RSpec style
- Request specs over controller specs
- Context-driven organization

**Conventions:** Use the `rails-way-conventions` skill
- Enforces Rails 8 conventions and best practices
- Ensures idiomatic Rails patterns

**Common Commands:**
```bash
# Running tests
bundle exec rspec

# Running code review
git diff main...HEAD  # See changes to be reviewed
```

### Infrastructure as Code

**Terraform Review:** Use the `terraform-iac-expert` skill
- Reviews Terraform configurations
- Checks for security and best practices
- Validates resource configurations

## Plugin Configuration

### Manifest File

`.claude-plugin/plugin.json` defines plugin metadata and component registration:

**Registered Skills:**
- `python-code-review` - PEP 8 and Google Style Guide reviews
- `rails-code-review` - Rails 8-aware systematic code review
- `rails-rspec-tester` - Opinionated RSpec testing patterns
- `rails-way-conventions` - Rails conventions and best practices
- `templeton-python-style` - Python style preferences (Sandi Metz principles)
- `terraform-iac-expert` - Infrastructure as Code reviews

**Registered Agents:**
- `code-simplifier` - Language-agnostic code simplification (Python & Ruby/Rails)
- `python-feature-developer` - Guided Python feature development
- `rails-code-reviewer` - Comprehensive Rails code review workflow

**Registered Commands:**
- `/python-code-review` - Quick Python code review
- `/python-feature-dev` - Start Python feature development
- `/rails-code-review` - Quick Rails code review

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
- Focus is on Python and Ruby/Rails development
- Skills encode proven techniques to prevent repeating solved problems
- Agents provide consistent, structured workflows
- Commands provide quick access to common operations
