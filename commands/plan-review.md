---
description: "Fresh-eyes review of a feature plan for completeness, feasibility, and gaps"
argument-hint: "[path-to-plan-file]"
---

Use the `plan-review` skill to evaluate a feature implementation plan.

If a file path is provided, review that plan. If only a name is given, look for a matching file in `docs/plans/`. If no argument is provided, list available plans in `docs/plans/` and ask the user to pick one.

Evaluate the plan across 6 dimensions (Completeness, Feasibility, Scope, Risks, Dependencies, Actionability), identify gaps with suggestions, and render a verdict: Ready / Needs Revision / Major Rework.
