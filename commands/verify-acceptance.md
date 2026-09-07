---
description: "Check whether the current unit of work met its bead's acceptance criteria and passed the QA gates"
argument-hint: "[bead-id]"
---

Use the `acceptance-verifier` agent to grade the current unit of work: $ARGUMENTS

The agent runs on `sonnet` regardless of this session's own model, per
[ADR 0008](../docs/adr/0008-delegated-work-runs-on-a-cheaper-model.md). Grading is a judgment
nobody downstream re-checks, so it keeps a model that can judge. It still costs less than the
sessions that most often call it.

The agent will:

1. Resolve the bead from `bd list --status in_progress`, the branch name, or the commit messages
2. Read its `acceptance_criteria` (and any `## Done when` block in `notes`)
3. Grade each criterion PASS / FAIL / UNVERIFIABLE against evidence, never against the diff
4. Run the QA gates (tests, linting, type checking) and record their real counts
5. Report one verdict table: ACCEPTED, NOT ACCEPTED, or INCONCLUSIVE

**Paste the `/quality-gates` output into the agent's prompt when this session already has it.**
The agent runs in its own context window and cannot read this conversation, so gate results it is
not given are results it re-runs. Without them it runs the whole suite a second time to reach the
same verdict.

Report-only. It never edits code, never closes a bead, and never invents criteria when the bead
records none. It never applies the `accepted` label either: read its verdict, and when it is
ACCEPTED, run `bd update <bead-id> --add-label accepted` yourself.

Pass a bead id as an argument to grade that bead instead of the auto-resolved one. No argument needed otherwise.

Invoke it by hand with `/verify-acceptance`, usually right after a fresh-eyes review.
