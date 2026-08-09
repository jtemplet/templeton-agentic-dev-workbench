# Authoring Components

The anatomy of each component type and the templates for writing a new one.
`AGENTS.md` keeps only the routing table and the registration rule, and points here.

## Plugin Structure

This repository follows the Claude Code plugin architecture with three main directories:

- **`agents/`** - Custom agent definitions that can be invoked via the Task tool or manually followed
- **`commands/`** - Slash commands (e.g., `/rails-code-review`) that provide quick access to workflows
- **`skills/`** - Reusable skill modules that encode best practices and systematic techniques

## Component Relationships

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

## Agent Architecture

Agents are structured workflow definitions located in `agents/`. Each agent:

- Defines a specific role or expertise area
- References skills via the Skill tool
- Specifies required workflow steps
- Defines output format and quality checklist
- Includes integration points with other tools

## Skill Architecture

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

## Creating New Skills

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

## Creating New Agents

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

## Creating New Commands

Commands are shortcuts placed in `commands/`:

```markdown
---
description: One-line description
---

[Instructions that load agent or skill]
```
