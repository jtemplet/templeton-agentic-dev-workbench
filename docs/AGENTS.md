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
- https://www.aihero.dev/a-complete-guide-to-agents-md
- https://www.humanlayer.dev/blog/writing-a-good-claude-md

---

### code-simplifier
**Purpose:** Simplify Python and Ruby/Rails code while preserving functionality

**Key Features:**
- Language-agnostic approach with language-specific style guides
- Reduces complexity and improves clarity
- Applies templeton-python-style or rails-conventions automatically

---

### python-feature-developer
**Purpose:** Guided Python feature development with Sandi Metz principles

**Workflow:**
1. Discovery → 2. Implementation → 3. Simplification → 4. Linting

---

### rails-code-reviewer
**Purpose:** Comprehensive Rails 8 code review

**Key Features:**
- Security-first approach with pragmatic severity
- Modern patterns (Hotwire, Turbo, Solid Stack)
- Verification-first methodology

---

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
