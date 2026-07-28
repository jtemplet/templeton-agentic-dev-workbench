---
description: "Decompose a feature plan into br (beads_rust) issues with dependencies"
argument-hint: "[path-to-plan-file]"
---

Use the `plan-to-beads` agent to decompose a feature plan into trackable `br` issues.

The agent will:

1. Read the plan file (or search `docs/plans/` if no path given)
2. Identify natural work units from milestones and components
3. Map the dependency graph (preferring parallel tracks)
4. **Present the full issue list and wait for your confirmation**
5. Create issues with `br create`, wire dependencies with `br dep add`
6. Run `br sync --flush-only` and report the final state

If no argument is provided, list available plans in `docs/plans/` and ask which to decompose.
