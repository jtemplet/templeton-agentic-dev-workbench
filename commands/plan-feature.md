---
description: "Generate a detailed implementation plan for a feature idea"
argument-hint: "[feature-idea-description]"
---

Use the `feature-planner` agent to create a detailed implementation plan for the requested feature.

The agent will:

1. Parse the feature idea from your input
2. Explore the codebase to understand architecture, patterns, and constraints
3. Draft a structured plan with summary, scope, technical approach, milestones, risks, and testing strategy
4. Write the plan to `docs/plans/feature-plan-<name>.md`
5. Report the file path and key decisions

If no feature description is provided, ask the user what they want to build.
