---
name: plan-review
description: "Fresh-eyes review of a feature plan for completeness, feasibility, scope risks, and actionability"
---

# Plan Review

Evaluate a feature implementation plan across 6 dimensions, identify gaps, and provide a clear verdict.

## Evaluation Dimensions

Rate each dimension GREEN / YELLOW / RED:

| Dimension | GREEN | YELLOW | RED |
|---|---|---|---|
| **Completeness** | All sections filled, no TBDs | Minor gaps or vague sections | Major sections missing or empty |
| **Feasibility** | Technical approach is sound and proven | Some unknowns but manageable | Relies on unproven tech or unclear how it works |
| **Scope** | Clear in/out boundaries, right-sized | Scope creep risk or slightly over-ambitious | Unbounded, no clear stopping point |
| **Risks** | Risks identified with mitigations | Risks listed but mitigations weak | No risk analysis or obvious blind spots |
| **Dependencies** | All deps identified, none blocking | Some deps unclear or potentially blocking | Critical deps missing or unresolvable |
| **Actionability** | A developer could start tomorrow | Needs 1-2 clarifications first | Too vague to act on without major rework |

## Process

1. **Read the plan thoroughly** — understand the full scope and intent
2. **Score each dimension** — assign GREEN/YELLOW/RED with a 1-sentence justification
3. **Identify gaps** — specific things that are missing or unclear, each with a suggestion for how to fill it
4. **Note strengths** — what the plan does well (2-3 items)
5. **Produce recommended changes** — a prioritized checklist of what to fix before implementation
6. **Render verdict** — Ready / Needs Revision / Major Rework

## Output Format

```markdown
## Plan Review: [Plan Title]

### Dimension Scores

| Dimension | Rating | Justification |
|---|---|---|
| Completeness | GREEN/YELLOW/RED | ... |
| Feasibility | GREEN/YELLOW/RED | ... |
| Scope | GREEN/YELLOW/RED | ... |
| Risks | GREEN/YELLOW/RED | ... |
| Dependencies | GREEN/YELLOW/RED | ... |
| Actionability | GREEN/YELLOW/RED | ... |

### Gaps Found

1. **[Gap]** — [Suggestion to fill it]
2. ...

### Strengths

- ...

### Recommended Changes

- [ ] [Highest priority fix]
- [ ] ...

### Verdict: [Ready / Needs Revision / Major Rework]

[1-2 sentence summary of overall assessment]
```

## Verdict Criteria

- **Ready** — All GREEN, or mix of GREEN/YELLOW with no blockers. A developer can start.
- **Needs Revision** — One or more YELLOW with gaps that could cause problems. Fixable in an hour or two.
- **Major Rework** — Any RED, or multiple YELLOW with compounding risk. Plan needs significant changes.

## When to Use

- After writing a feature plan, before starting implementation
- When reviewing someone else's plan for quality
- As a gate before decomposing a plan into issues

## When NOT to Use

- On plans that are intentionally lightweight (spikes, experiments)
- When the plan is already being implemented and it's too late to revise

## Key Principles

- **Every gap must come with a suggestion** — don't just say "missing X", say "add X by doing Y"
- **Focus on what would make implementation fail** — not style or formatting nits
- **Respect the plan's intent** — review what it's trying to do, not what you'd do differently
- **Be specific** — "the API section is vague" is useless; "the API section doesn't specify auth mechanism" is useful
