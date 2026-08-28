---
description: "Draft a feature plan from one sentence: explore the codebase in a fresh context, then write it to docs/plans/"
argument-hint: "[feature-idea-description]"
---

Use the `feature-planner` agent to create a detailed implementation plan for the requested feature.

**First, check whether this is the right command.** The agent runs in its own context window and
cannot see this conversation. If the design was already worked out here, in a grilling or any
other discussion, use `/write-plan` instead: it synthesizes what was decided rather than
re-deriving it, and it will not ask you questions you have already answered.

`/plan-from-idea` is for the cold start: one sentence, nothing decided, no interview behind you.

The agent will:

1. Parse the feature idea from your input
2. Explore the codebase to understand architecture, patterns, and constraints
3. Read `docs/adr/` for the ADRs that bind the area
4. Pick the test seams: existing over new, highest that proves the behavior, as few as possible
5. Draft the plan using the canonical template owned by the `write-plan` skill
6. Write it to `docs/plans/feature-plan-<name>.md`
7. Report the file path, the seams, and the open questions

If no feature description is provided, ask the user what they want to build.
