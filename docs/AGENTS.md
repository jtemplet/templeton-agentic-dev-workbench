# Agents

Custom agents for agentic development workflows.

## Available Agents

### claude-md-reviewer

**Purpose:** Optimize CLAUDE.md/AGENTS.md files for maximum AI agent effectiveness

**Key Features:**

- Quantitative health scoring (0-100)
- Token waste analysis with concrete impact estimates
- Auto-refactoring with validation
- Framework-specific optimizations (Next.js, Rails, Nx, etc.)
- CI/CD integration hooks
- Team collaboration tools
- Usage analytics and regression detection

**Usage:**

```bash
# Review mode (recommendations only)
"Review our CLAUDE.md and provide optimization recommendations"

# Refactor mode (auto-implement)
"Auto-refactor our CLAUDE.md using progressive disclosure"

# Monitor mode (continuous validation)
"Set up monitoring for CLAUDE.md to prevent regression"
```

**Based on research from:**

- <https://www.aihero.dev/a-complete-guide-to-agents-md>
- <https://www.humanlayer.dev/blog/writing-a-good-claude-md>

---

### software-engineer

**Purpose:** Editing role for code work (simplify, fix bugs, implement features); routes to the appropriate skill based on user intent

**Skills it composes:**

- `code-simplify` skill - Simplification across all supported languages
- `fresh-eyes-review` skill - Bug-and-correctness pass on changed code
- `feature-development` skill - 4-phase guided implementation (discovery, implementation, simplification, linting)
- Loads the matching language style skill (`templeton-python-style`, `templeton-frontend-style`, `templeton-swift-style`, `rails-conventions`) automatically

---

> For the full agent and skill list, see `AGENTS.md` (root) and `README.md`. This file documents only the agents that have extended notes worth keeping outside the manifest.

## Creating New Agents

See `AGENTS.md` section "Adding a New Agent" for detailed guidance on creating agents.

(Note: `/docs/PLUGIN_DEVELOPMENT.md` will be created if you run the claude-md-reviewer agent on AGENTS.md)

**Quick reference:**

```markdown
---
name: agent-name
description: Use when... Examples: <example>...</example>
model: inherit
color: blue
tools: ["Read", "Write"]
---

You are [role]...

**Core Responsibilities:**
[List responsibilities]

**Process:**
[Step-by-step workflow]

**Output Format:**
[Expected output]
```
