---
description: "Implement a bead's spec in the house style: read the bead, learn the repo's conventions, code criterion by criterion, simplify, lint"
argument-hint: "[bead-id | feature-description]"
---

Use the `feature-development` skill to implement: $ARGUMENTS

The implementation operates from the `software-engineer` role: a working engineer who reads the spec before asking, applies the project's conventions, and verifies before declaring success. Refer to `agents/software-engineer.md` for the role's beliefs and judgment principles.

`$ARGUMENTS` is normally a **bead id**. The skill then reads the spec from `bd show <id> --json` rather than interviewing you about what the bead already records. Pass a free-text description instead when no bead exists, and the skill will interview you and write the acceptance criteria first.

The skill will:

1. **Ground** - Read the bead's Why, How, and Done when. Stop if the criteria are too thin to build against, or if its own notes say to split it first
2. **Orient** - Read `AGENTS.md`/`CLAUDE.md`, the repository's `development_workflow.md` (under `docs`, `.agent_docs`, or `agent_docs`), the dependency manifest, and the two or three existing files nearest the change. Create the worktree or branch the workflow document names, then load the matching style skills (`style-python`, `style-rails`, `style-frontend`, `style-swift`, `style-go`, or `style-markdown`), plus `style-testing` for any test file and any project-local style skill
3. **Implement** - Code criterion by criterion, each with a test named after the criterion it proves
4. **Simplify** - Apply the `/simplify` command, then re-run the tests
5. **Lint** - Run the project's own linter, or the language's standard one

If no arguments are provided, the skill will ask for a bead id or a feature description.

It stops at implemented. It does not claim the bead, change its status, or close
it, and it does not grade its own work. Run `/quality-gates` and then
 `/verify-acceptance` for that.

This workflow is language-agnostic: the skill picks the style guide, test runner,
and linter from what the repository actually contains.
