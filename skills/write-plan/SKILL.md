---
name: write-plan
description: "Write up the plan, design, or approach this conversation has already worked out, and save it to docs/plans/feature-plan-<name>.md. Use whenever someone says write the plan, write this up, turn this into a plan, document what we decided, save this as a plan, write the spec, put this in a plan file, or make a plan doc, and as the step that follows /grill-me or /grill-with-docs once the interview is finished. Synthesizes what the current window settled rather than interviewing again: collects every decision that was made and the option it beat, verifies each file path, module, and API it is about to name against the codebase, picks the test seams and confirms them, reads docs/adr/ so no ADR is contradicted, then fills the canonical plan template it owns, which /plan-review grades for completeness and /plan-to-beads decomposes into beads. Not for a cold start where nothing has been decided yet: that is /plan-from-idea, which explores from one sentence in its own context and cannot see this conversation. Not for judging a plan that already exists (/plan-review), not for breaking a reviewed plan into issues (/plan-to-beads), and not for work small enough to fit one bead (/bead-create)."
---

# Write Plan

Turns a design that has already been decided into the plan file the rest of the pipeline reads.

**This skill owns the canonical plan template.** `/plan-review` grades against it and
`/plan-to-beads` decomposes it, so both depend on the section list below. The `feature-planner`
agent reads this file for the template rather than carrying its own copy.

## The Rule That Makes This Worth Running

**Synthesize what the conversation decided. Do not interview.**

The window you are in already holds the answers: the interview happened, the codebase was read,
the tradeoffs were argued. Asking again wastes the user's time and invites a second, different
answer to a question that is already closed. If a decision is genuinely absent, write it under
**Open Questions** and say so in the report. Do not stop the write to ask.

The one exception is the test seams in step 3. That is a decision the conversation usually has
not made, and it is cheap to confirm and expensive to get wrong.

## When to Use / When NOT to Use

Use when:

- `/grill-me` or `/grill-with-docs` just finished and the design tree is resolved.
- A design was settled in conversation and now needs to become a document.
- A prototype answered its question and the answer needs recording.

Do NOT use when:

- Nothing has been decided yet. Use `/plan-from-idea`, which explores and drafts from one sentence.
- The plan file already exists and needs judging. Use `/plan-review`.
- The plan is written and needs breaking into work. Use `/plan-to-beads`.
- The work is one bead's worth. Use `/bead-create` and skip the plan entirely.

**Check the window before you start.** If this conversation holds no design discussion, say so and
route to `/plan-from-idea` rather than inventing a plan from the feature name.

## Process

### Step 1: Collect what was decided

Re-read the conversation and list, for yourself:

- What is being built, and the problem it solves.
- Every decision that was made, and the option it beat.
- Every boundary that was drawn, which becomes Out of Scope.
- Every question that was raised and left open.

A decision the user made outranks your own judgment about it. You are recording, not re-deciding.

### Step 2: Ground the claims you are about to write

The plan names real files, modules, and APIs, and `/plan-review` verifies every one of them
against the repository. So verify them here, before writing, with Glob and Grep.

This is deliberately the opposite of the advice that a plan should avoid file paths because they
rot. A path that rots is caught by the next review; a plan too vague to name anything is not
checkable at all.

Explore the codebase now for anything the conversation asserted but never confirmed. Reuse what
the window already established rather than re-reading it.

### Step 3: Pick the test seams

A **seam** is the place where the feature gets tested: the boundary a test drives it through.

1. Prefer a seam that already exists over a new one.
2. Use the highest seam that can still prove the behavior. A test at a high seam survives a
   refactor underneath it; a test bound to an internal function does not.
3. Fewer seams is better. One is the target.
4. When a new seam is needed, propose it at the highest point that works.

**Confirm the seams with the user before writing the file.** State them in one short list and ask
whether they match expectations. This is the only question this skill asks.

### Step 4: Read the decisions and the glossary that bind this plan

Read `docs/adr/` when the repository has one. These are choices already made and not open
for re-litigation. Open any whose subject the plan touches.

An ADR that contradicts the plan outranks the plan. Change the approach, or say plainly in
**Open Questions** that the plan proposes superseding that ADR and name it.

**Then read `CONTEXT.md`, when the repository has one.** That file is the project's glossary,
meaning the list of terms and what each one means here. Take every domain term in the plan from it,
and use the glossary's word rather than a synonym. When the file does not exist, fall back to the
codebase's own names. A plan that renames the domain's terms costs every later reader a
translation. `/plan-to-beads` then copies those renamed terms into every bead it files.

A concept the glossary does not carry is a signal, not an error. It means one of two things.
Either the plan is inventing a word the project does not use, or the glossary has a real gap.
Say which under **Open Questions**. Do not write to `CONTEXT.md`. [ADR
0007](../../docs/adr/0007-a-tadw-skill-wins-over-an-overlapping-external-skill.md) keeps
`mattpocock-skills:domain-modeling` as the only skill that writes it.

### Step 5: Write the file

**Load the `style-markdown` skill first, before the first line.** A plan under `docs/plans/` is a
prompt asset: an agent reads it and acts on it, and `/plan-to-beads` turns its sentences into bead
text. A sentence with two readings becomes a bead with the wrong one. That skill governs the prose
here: Simplified Technical English, one meaning per word, no jargon, and sentences a ten-year-old
can follow, with every technical name left exact. Rewriting a plan to that style afterward costs
more than writing to it once.

Fill the template below and write it to `docs/plans/feature-plan-<kebab-case-name>.md`, creating
`docs/plans/` if it does not exist. Never leave a section as TBD or TODO: fill it, mark it
`N/A because ...`, or move the unknown to Open Questions.

### Step 6: Report

Give the user the file path, a two-sentence summary, the seams you settled on, and every open
question that needs their input. Then point at `/plan-review` as the next step.

## The Canonical Template

Data Model and API/Interface may be dropped when genuinely not applicable. Every other section is
required, because `/plan-review` scores Completeness against exactly this list.

````markdown
# Feature Plan: [Feature Name]

**Date:** [YYYY-MM-DD]
**Status:** Draft

## Summary

[2-3 sentence description of what this feature does and why it matters]

## Motivation

[Why build this? What problem does it solve? Who benefits?]

## Scope

### In Scope

- [Specific deliverable 1]
- [Specific deliverable 2]

### Out of Scope

- [Explicitly excluded thing 1]
- [Explicitly excluded thing 2]

## Technical Approach

### Architecture

[How this fits into the existing system. Include component relationships.]

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| ... | ... | New / Modified |

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| ... | Existing / New | ... |

[One line on why this seam and not a lower one. Confirmed with the user in step 3.]

### Data Model

[New tables, fields, or schema changes. Skip if N/A.]

### API / Interface

[New endpoints, CLI commands, or UI changes. Skip if N/A.]

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| 0001 | ... | ... |

[Write "None found" when the repository has no `docs/adr/`.]

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | ... | ... | S/M/L | [verifiable completion condition] |
| 2 | ... | ... | S/M/L | [verifiable completion condition] |

## Acceptance Criteria

[Formal, testable conditions that prove the feature is delivered. Written from the user or
system perspective, not the implementer's. Use Given/When/Then or numbered assertions. Two
people must be able to agree independently whether each is satisfied without asking the author.]

1. Given [precondition], when [action], then [observable result].
2. ...

**Coverage:** every item in "In Scope" and every goal in "Motivation" is proven by at least
one criterion above.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| ... | High/Med/Low | High/Med/Low | ... |

## Dependencies

- [External dependency or prerequisite 1]
- [None if truly independent]

## Testing Strategy

- [Test levels and the key scenarios each covers, driven through the seams named above]

## Open Questions

- [Unresolved decision 1]
- [None if all decisions are made]
````

## Inlining a Snippet

Prose is the default. Inline code only when it encodes a decision more precisely than prose can:
a state machine, a reducer, a schema, a type shape. Trim it to the decision-bearing part, never a
working demo. When it came from a prototype, say so in one clause.

## Quality Checklist

Before writing the file:

- [ ] Every decision in the file traces to something the conversation actually settled
- [ ] No question was asked that the conversation had already answered
- [ ] Every file path, module, and API named in the plan was verified to exist
- [ ] Test Seams is filled, the seams were confirmed with the user, and the count is as low as the behavior allows
- [ ] `docs/adr/` was read, and any ADR the plan touches appears in Decisions That Bind This Plan
- [ ] `CONTEXT.md` was read, and every domain term in the plan uses the glossary's word
- [ ] Acceptance Criteria is present and every criterion is testable, with no "works well" or "is fast"
- [ ] Every In Scope item and every stated goal is proven by at least one criterion
- [ ] Every milestone carries a "Done when" condition a second person could check
- [ ] Risks include at least one technical and one scope risk
- [ ] Open Questions holds genuine unknowns, not sections left unfinished
- [ ] No section is TBD or TODO
- [ ] `style-markdown` was loaded before writing, and the prose follows it

## Integration

| Before | After |
|---|---|
| `/grill-me` or `/grill-with-docs` resolves the design tree | `/plan-review` grades the file this skill wrote |
| A prototype answers its design question | `/plan-to-beads` decomposes the reviewed plan |

`/plan-from-idea` is the alternative entry point, for when there is nothing in the window to
synthesize. It explores from one sentence in its own context and writes this same template.
