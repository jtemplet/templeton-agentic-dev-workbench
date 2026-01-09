# Custom Claude Code Agents

This directory contains specialized agent definitions for use with Claude Code's Task tool.

## Available Agents

### rails-code-reviewer
Comprehensive Rails 8 code reviewer focusing on security, conventions, performance, and maintainability.

**Use when:**
- Reviewing Rails code before merge or PR
- Performing security audits
- Validating Rails 8 conventions and Hotwire patterns

**Example:**
```markdown
I need to dispatch a rails-code-reviewer agent to review my current branch.

The agent will:
1. Load the rails-code-review skill
2. Get the git diff
3. Systematically review: Security → Conventions → Performance → DRY → Logic
4. Provide actionable fixes with before/after code examples
5. Summarize findings with clear merge/fix recommendation
```

## How to Use Agents

### Option 1: Via Task Tool (when agent type is registered)

```python
Task(
  subagent_type="rails-code-reviewer",
  description="Review Rails code changes",
  prompt="""
  Review the changes in 'feature/add-authentication' branch
  compared to 'main'. Focus on security vulnerabilities.
  """
)
```

### Option 2: Manual Invocation (current method)

Since custom agents may not be registered as official subagent types, you can manually follow the agent instructions:

1. Read the agent file (e.g., `rails-code-reviewer.md`)
2. Follow the workflow defined in "Agent Instructions"
3. Use the specified output format
4. Apply the critical rules and quality checklist

### Option 3: Via Slash Command

Create a slash command that loads and follows the agent:

```markdown
# .claude/commands/review-rails.md
---
description: Perform comprehensive Rails code review
---

You are a Rails code review expert following the rails-code-reviewer agent workflow.

Load the rails-code-review skill and review the current branch against main,
providing comprehensive Rails 8 security and convention analysis.
```

## Agent Structure

Each agent file should contain:

```markdown
# Agent Name

## Agent Type
`agent-type-name`

## Description
[One-line description]

## When to Use
[Specific scenarios and triggers]

## Agent Instructions
[Detailed workflow the agent follows]

### Required Workflow
[Step-by-step process]

### Output Format
[Expected output structure]

### Critical Rules
[Always/Never lists]

### Quality Checklist
[Pre-submission verification]

## Example Usage
[Code examples]

## Integration Points
[How it works with other tools/skills]

## Success Metrics
[How to measure effectiveness]
```

## Creating New Agents

1. **Identify the need** - What specialized review/analysis is needed?
2. **Define scope** - What specific expertise does this agent have?
3. **Create workflow** - Step-by-step process the agent follows
4. **Specify output** - Exact format for consistency
5. **Add guardrails** - Critical rules and quality checks
6. **Test it** - Run through example scenarios

## Best Practices

**Do:**
- ✅ Reference existing skills (like rails-code-review)
- ✅ Provide concrete output format with examples
- ✅ Include quality checklist for consistency
- ✅ Define clear "when to use" criteria
- ✅ Specify integration points with other tools

**Don't:**
- ❌ Create generic agents (use built-in ones)
- ❌ Duplicate existing agent functionality
- ❌ Omit workflow steps
- ❌ Leave output format vague
- ❌ Skip the quality checklist

## Contributing

When adding new agents:

1. Follow the agent structure template
2. Test with real scenarios
3. Document integration points
4. Add to this README's "Available Agents" section
5. Consider creating a corresponding skill if needed

## Future: Agent Registration

To make these agents available as official subagent types in the Task tool, they would need to be:

1. Registered in Claude Code's agent marketplace
2. Added to the Task tool's `subagent_type` enum
3. Configured with proper permissions and capabilities

Until then, use Option 2 or 3 above for manual invocation.
