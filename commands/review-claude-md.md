---
description: Review and optimize CLAUDE.md or AGENTS.md files with quantitative analysis and auto-refactoring
---

Use the `claude-md-reviewer` agent to analyze and optimize CLAUDE.md or AGENTS.md files.

## Capabilities

**Analysis:**

- Quantitative health scoring (0-100)
- Token waste calculation with impact estimates
- Anti-pattern detection with confidence scores
- Codebase alignment verification
- Framework-specific optimizations

**Modes:**

- **Review:** Recommendations only (default)
- **Refactor:** Auto-implement with validation
- **Monitor:** Continuous regression detection

**Outputs:**

- Detailed report with before/after comparisons
- Progressive disclosure strategy
- Validation tests
- Optional CI/CD hooks

## Usage Examples

```text
# Review mode (default)
"Review our CLAUDE.md and provide optimization recommendations"

# Refactor mode
"Auto-refactor CLAUDE.md using progressive disclosure"

# With specific target
"Review docs/AGENTS.md and show token savings"

# Set up monitoring
"Set up CI/CD hook to prevent CLAUDE.md regression"
```

If no file specified, reviews `CLAUDE.md` or `AGENTS.md` at repository root.
