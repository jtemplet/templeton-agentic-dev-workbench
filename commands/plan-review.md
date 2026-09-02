---
description: "Fresh-eyes review of a feature plan: acceptance-criteria gate, codebase grounding, 7-dimension evaluation with MECE check, and a verdict"
argument-hint: "[path-to-plan-file]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/plan-review/SKILL.md` and follow it to evaluate a feature implementation plan.

Read the file rather than invoking the skill by name. `commands/plan-review.md` and
`skills/plan-review/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(plan-review)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/plan-review/SKILL.md` and read it from there.

If a file path is provided, review that plan. If only a name is given, look for a matching file in `docs/plans/`. If no argument is provided, list available plans in `docs/plans/` and ask the user to pick one.

Run the acceptance-criteria gate first, verify the plan's claims against the actual codebase (codebase grounding), evaluate the plan across 7 dimensions (Completeness, Feasibility, Scope, Risks, Dependencies, MECE, Actionability), run a dedicated MECE check for overlaps and gaps, and render a verdict: Ready / Needs Revision / Major Rework.

The review is report-only: when Acceptance Criteria or Testing Strategy is missing, include a paste-ready draft in Recommended Changes and offer to apply it; never edit the plan file unprompted. On Ready, point to `/plan-to-beads` as the next step.
