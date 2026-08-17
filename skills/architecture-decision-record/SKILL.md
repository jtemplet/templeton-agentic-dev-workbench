---
name: architecture-decision-record
description: "Record architectural decisions with context, options considered, and rationale for future reference"
---

# Architecture Decision Records

## When to Use

- After choosing between multiple design approaches
- When introducing a new technology, pattern, or dependency
- When changing an existing architectural decision
- When the brainstorming skill produces an approved design
- When making a non-obvious technical choice that future-you will wonder about

## When NOT to Use

- Trivial decisions (formatting, naming conventions already covered by style guides)
- Decisions fully dictated by external constraints (no real choice was made)
- Temporary experiments or spikes (use git branches instead)

## Workflow

1. **Check existing ADRs** — read `docs/decisions/` to determine the next sequence number
2. **Gather context** — from conversation, brainstorming output, or codebase exploration
3. **Identify the options** — what alternatives were considered and why
4. **Document the decision** — using the template below
5. **Write the file** — save to `docs/decisions/NNNN-<title-in-kebab-case>.md`
6. **Create a tracking issue** — if status is "Proposed", use `bd create` to track approval

## ADR Template

```markdown
# NNNN. Decision Title

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deprecated | Superseded by [NNNN]

## Context

What is the problem or situation that motivates this decision? Include relevant
technical constraints, business requirements, and prior decisions that apply.

## Options Considered

### Option A: <name>

- **Pros:** ...
- **Cons:** ...

### Option B: <name>

- **Pros:** ...
- **Cons:** ...

### Option C: <name> (if applicable)

- **Pros:** ...
- **Cons:** ...

## Decision

State the decision clearly. One or two sentences. Then explain the reasoning —
why this option over the others.

## Consequences

What becomes easier or more difficult because of this decision? Include both
positive and negative consequences. Be honest about trade-offs.
```

## Numbering

- ADRs are numbered sequentially: `0001`, `0002`, etc.
- If `docs/decisions/` doesn't exist, create it and start at `0001`
- If it exists, read the highest-numbered file and increment

## Superseding Decisions

When a decision replaces a previous one:

1. Create the new ADR with its own number
2. Update the old ADR's status to `Superseded by [NNNN]`
3. Reference the old ADR in the new one's Context section

## Key Principles

- **Capture the "why"** — the decision itself is obvious from code; the reasoning is what gets lost
- **Be concise** — a good ADR is one page, not five
- **Record at decision time** — don't try to reconstruct decisions retroactively
- **Include rejected options** — knowing what was *not* chosen and why is as valuable as the choice itself
