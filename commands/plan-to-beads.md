---
description: "Decompose a feature plan into bd (beads) issues with dependencies"
argument-hint: "[path-to-plan-file]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/plan-to-beads/SKILL.md` and follow it to decompose a feature plan into trackable `bd` issues.

Read the file rather than invoking the skill by name. `commands/plan-to-beads.md` and
`skills/plan-to-beads/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(plan-to-beads)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/plan-to-beads/SKILL.md` and read it from there.

The decomposition operates from the `project-manager` role: a project manager who keeps the dependency graph shallow, makes each issue self-contained, and refuses to create issues without explicit confirmation. Refer to `agents/project-manager.md` for the role's beliefs and judgment principles.

The skill will:

1. Read the plan file (or search `docs/plans/` if no path given)
2. Identify natural work units, articulate Marr Levels 1 (Why) and 2 (How) for each, and audit every bead before presenting
3. Map the dependency graph (preferring parallel tracks)
4. **Present the full issue list, including each bead's Why and How, and wait for your confirmation**
5. Create issues with `bd create -d <body>`, wire dependencies with `bd dep add`
6. Run `bd export -o .beads/issues.jsonl` and report the final state

If no argument is provided, the skill will list available plans in `docs/plans/` and ask which to decompose.
