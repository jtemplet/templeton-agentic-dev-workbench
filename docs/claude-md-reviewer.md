# CLAUDE.md Reviewer Agent

An advanced agent for optimizing CLAUDE.md and AGENTS.md files based on research-backed best practices.

## Overview

The `claude-md-reviewer` agent analyzes AI agent configuration files and provides quantitative optimization recommendations with optional auto-refactoring.

**Key Features:**
- 🎯 Quantitative health scoring (0-100)
- 📊 Token waste analysis with concrete impact estimates
- 🤖 Auto-refactoring with validation
- 🔍 Framework-specific optimizations
- 📈 Regression detection and monitoring
- 👥 Team collaboration tools

## Quick Start

### Basic Review (Recommendations Only)

```
"Review our CLAUDE.md and provide optimization recommendations"
```

The agent will:
1. Calculate health score (0-100)
2. Identify token waste
3. Detect anti-patterns
4. Provide refactoring plan
5. Show before/after impact

### Auto-Refactor Mode

```
"Auto-refactor CLAUDE.md using progressive disclosure"
```

The agent will:
1. Analyze current state
2. Create docs/ directory structure
3. Move content to appropriate files
4. Update root CLAUDE.md with references
5. Validate all changes
6. Create git commit

### Monitor Mode

```
"Set up CI/CD hook to prevent CLAUDE.md regression"
```

The agent will:
1. Generate pre-commit hook
2. Set validation thresholds
3. Create monitoring guidelines

## Operating Modes

### Mode 1: Review (Default)
- Analyze and score
- Provide recommendations
- Show impact estimates
- User implements manually

**Use when:** You want to understand issues before making changes

### Mode 2: Refactor
- Perform analysis
- Auto-implement changes
- Validate everything
- Create git commit

**Use when:** You trust the analysis and want fast results

### Mode 3: Monitor
- Track changes over time
- Alert on regression
- Generate analytics

**Use when:** You want to maintain optimization long-term

## Health Score Calculation

The agent calculates a 0-100 health score based on four components:

```
Health Score = (
  Token Efficiency × 0.35 +
  Instruction Budget × 0.25 +
  Staleness Risk × 0.20 +
  Progressive Disclosure × 0.20
)
```

### Token Efficiency (35% weight)
- **Target:** ~180 tokens (45 lines × 4 tokens/line)
- **Calculation:** min(100, (ideal_tokens / actual_tokens) × 100)
- **Why:** Every token loads on every request

### Instruction Budget (25% weight)
- **Target:** ≤20 instructions in root file
- **Calculation:** max(0, 100 - ((instruction_count - 20) × 5))
- **Why:** LLMs can follow ~150-200 instructions total, Claude Code uses ~50

### Staleness Risk (20% weight)
- **Penalties:**
  - File paths: -10 points each
  - Code snippets: -15 points each
- **Why:** Stale documentation poisons context

### Progressive Disclosure (20% weight)
- **Calculation:** (referenced_docs / total_content_areas) × 100
- **Why:** Task-specific content should load on-demand

## Example Output

```markdown
## Health Score: 12/100 (Grade F)

Breakdown:
- Token Efficiency: 16/100 → 5.6 points (1104 tokens vs 180 ideal)
- Instruction Budget: 25/100 → 6.3 points (35 instructions vs 20 target)
- Staleness Risk: 0/100 → 0.0 points (8 file paths, 2 code snippets)
- Progressive Disclosure: 0/100 → 0.0 points (no separate docs/)

After Optimization: 100/100 (Grade A+)
- Lines: 276 → 45 (83% reduction)
- Tokens: 1,104 → 180 (924 tokens saved per request)
- Instructions: 35 → 8 (77% reduction)
- Health score: 12 → 100 (+88 points improvement)
- Response time: ~200ms faster (estimated)
```

## Progressive Disclosure Strategy

The agent recommends extracting content to separate files:

| Content Type | Target File | Benefits |
|--------------|-------------|----------|
| Python workflows | `docs/PYTHON_WORKFLOWS.md` | Loads only for Python tasks |
| Rails workflows | `docs/RAILS_WORKFLOWS.md` | Loads only for Rails tasks |
| Testing patterns | `docs/TESTING.md` | Loads only when testing |
| Architecture | `docs/ARCHITECTURE.md` | Human reference, not agent |
| Plugin dev | `docs/PLUGIN_DEVELOPMENT.md` | Loads only when creating plugins |
| Build process | `docs/BUILD.md` | Loads only for build tasks |

## Framework-Specific Intelligence

The agent detects your project type and provides tailored recommendations:

**Next.js Project:**
```markdown
✅ Detected: Next.js 15 with App Router
💡 Reference official Next.js docs for routing patterns
⚠️ Document App Router, not Pages Router (detected in codebase)
```

**Nx Monorepo:**
```markdown
✅ Detected: Nx workspace with 8 apps, 12 libraries
📋 Recommended structure:
   - root/CLAUDE.md → Workspace overview
   - apps/*/CLAUDE.md → App-specific guidance
   - libs/*/CLAUDE.md → Library conventions
```

## Validation & Testing

After refactoring, the agent generates test queries:

```markdown
## Validation Tests

1. **Python workflow discovery:**
   Query: "Review this Python code for PEP 8"
   Expected: Loads docs/PYTHON_WORKFLOWS.md

2. **Plugin development discovery:**
   Query: "Create a new skill"
   Expected: Loads docs/PLUGIN_DEVELOPMENT.md

3. **Link resolution:**
   All progressive disclosure links must resolve
```

## CI/CD Integration

The agent can generate pre-commit hooks:

```bash
#!/bin/bash
# Prevents CLAUDE.md regression

MAX_LINES=100
MAX_INSTRUCTIONS=25
MAX_TOKENS=500

# Validate CLAUDE.md stays optimized
# Fails commit if thresholds exceeded
```

## Research Foundation

Based on research from:
- **aihero.dev:** [A Complete Guide To AGENTS.md](https://www.aihero.dev/a-complete-guide-to-agents-md)
- **humanlayer.dev:** [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

Key principles:
- LLMs are stateless (context matters every time)
- Instruction budget is limited (~150-200 total)
- Stale documentation poisons context
- Progressive disclosure > inline documentation
- Use linters, not CLAUDE.md, for style rules

## Advanced Features

### Codebase Alignment Verification
Checks documented claims against actual code:
- Verifies tech stack mentions
- Validates build commands exist
- Detects file path 404s
- Compares documented patterns vs reality

### Team Collaboration
For multi-developer teams:
- Identifies conflicting opinions
- Facilitates consensus
- Generates team guidelines
- Creates onboarding checklists

### Usage Analytics
Tracks which docs Claude actually loads:
- High-value files (frequently accessed)
- Low-value files (rarely accessed)
- Recommendations for consolidation

## See Also

- **Example Output:** `agents/claude-md-reviewer-example-output.md`
- **Improvements Summary:** `IMPROVEMENTS.md`
- **Command:** `/review-claude-md`

## Confidence & Reliability

**Overall Confidence: 82%** (weighted by impact)

The agent implements research-backed best practices with:
- High confidence improvements (85-95%): Core analysis, quantification, validation
- Medium confidence improvements (70-80%): Team features, export formats
- Low confidence improvements (60-70%): Watch mode, pattern library

All high-impact features have high confidence ratings.
