# Development Workflow

Use [AGENTS.md](../AGENTS.md) as the source of truth for work in this repository. It lists the
local checks, task routes, Beads rules, Git rules, and session close steps.

## Start work

Use `bv --robot-next` to find ready work, or `/triage-beads` to rank it. Read the bead with
`bd show <id>`, then claim it with `bd update <id> --claim`. Read
[Beads Workflow](beads-workflow.md) for tracker commands and their behavior.

## Build and verify

Use `/build <id>` to implement a bead. Use the task routes in `AGENTS.md` for work that does not
start from a bead. Read [Style Routing](style-routing.md) to select code and test style skills.

Run the checks that [AGENTS.md](../AGENTS.md) lists for the files you changed. For code changes,
use `/quality-gates`. When the work has a bead, give its gate report to `/verify-acceptance`. Use
`/tadw:ship` to land a finished bead branch. The [README pipelines](../README.md#workflow-pipelines)
show how these steps fit together.

## Close the session

Follow the **Landing the Plane** steps in [AGENTS.md](../AGENTS.md#landing-the-plane-session-completion).
That section owns issue status, checks, pushes, cleanup, and handoff.
