---
description: "Fresh-eyes review of a feature plan: acceptance-criteria gate, codebase grounding, 7-dimension evaluation with MECE audit, and a verdict"
argument-hint: "[path-to-plan-file]"
---

Use the `plan-review` skill to evaluate a feature implementation plan.

If a file path is provided, review that plan. If only a name is given, look for a matching file in `docs/plans/`. If no argument is provided, list available plans in `docs/plans/` and ask the user to pick one.

Run the acceptance-criteria gate first, verify the plan's claims against the actual codebase (codebase grounding), evaluate the plan across 7 dimensions (Completeness, Feasibility, Scope, Risks, Dependencies, MECE, Actionability), run a dedicated MECE audit for overlaps and gaps, and render a verdict: Ready / Needs Revision / Major Rework.

The review is report-only: when Acceptance Criteria or Testing Strategy is missing, include a paste-ready draft in Recommended Changes and offer to apply it; never edit the plan file unprompted. On Ready, point to `/plan-to-beads` as the next step.
