# 0012. Ship gates the code tree and carries the close

**Date:** 2026-09-28
**Status:** Accepted

## Context

For `/tadw:ship`, close the bead after the gate and before the landing commit. Stage 3 of
`.githooks/pre-push` warns about an export change and creates no commit.

The target after `SHIP_DONE` is an empty `git status --porcelain` in the default-branch checkout.
Today, `candidate.land_candidate` commits and gates the code, then advances the default branch.
`ship_workflow.publish` closes the bead after that commit, which changes the export in the tree.

Issue `tadw-pm8` made stage 3 of `.githooks/pre-push` commit a changed export by itself. A push
cannot include a commit created by its own pre-push hook, so that tracker-only commit waits for the
next push.

`candidate.py` promises that ship “gates the exact commit it lands.” The [clean tree after ship
plan](../plans/feature-plan-clean-tree-after-ship.md) changes this promise. Ship will gate the exact
code tree, and the landing commit will add only `.beads/issues.jsonl`.

ADR 0010 keeps the pre-commit export rule. This decision replaces only its pre-push backstop: stage
3 will warn about a changed export and will not commit it.

The 2026-09-28 discussion considered the close timing options below.

## Options Considered

### Option A: Close before the gate, then reopen on failure

- **Pros:** The close is already in the export before the gate. A successful run needs no later
  tracker write.
- **Cons:** A failed gate closes the bead until ship reopens it. A stop before reopening can leave a
  closed bead with no landing commit.

### Option B: Close after the gate and before the landing commit

- **Pros:** A failed gate leaves the bead open. A successful landing commit can carry the close,
  and stage 3 no longer needs to create a tracker-only commit.
- **Cons:** Ship must build and check a landing commit after the gate. The landing commit also carries
  the other tracker changes present when ship exports the file.

### Option C: Amend the landing commit before the push

- **Pros:** The close can appear in the landing commit without a separate tracker-only commit.
- **Cons:** Amending runs commit hooks again. If a pre-commit hook is the gate, the amend runs the
  full gate a second time.

### Option D: Keep today's order

- **Pros:** The gate checks the same commit that ship lands. Ship needs no new landing commit step.
- **Cons:** Closing the bead after that commit changes the export in the working tree. Stage 3 then
  creates a tracker-only commit that cannot join the push already in progress.

## Decision

**Choose Option B.** After the gate passes, ship closes the bead and exports the tracker. Ship then
builds a landing commit whose tree differs from the gated tree only in `.beads/issues.jsonl`.
`git commit-tree` creates that commit without running the pre-commit hook a second time.

Ship stops if any other path differs between the gated tree and the landing tree. The ship skill
therefore gates the exact code tree it lands, while the landing commit records the close.

Stage 3 of `.githooks/pre-push` compares a temporary export with the committed export. When they
differ, it warns that tracker changes have no commit. It does not write `.beads/issues.jsonl` or
create a commit. The warning still allows the push, as ADR 0004 requires.

## Consequences

**Easier:**

- A successful ship puts the close in the landing commit and leaves the export clean.
- A failed gate leaves the bead open.
- Stage 3 warns about pending tracker changes without creating a tracker-only commit.

**Harder:**

- The landing commit can include other tracker changes present when ship exports the file.
- A tracker write after that export can still dirty the working tree. Ship warns when it detects
  that change.
- Stage 3 no longer repairs an export missed by the pre-commit hook. The warning says that the
  change will enter a later commit.
