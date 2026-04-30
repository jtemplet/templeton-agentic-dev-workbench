---
name: plan-to-beads
description: Decompose a feature implementation plan into trackable br (beads_rust) issues with a dependency graph. Reads the plan, identifies self-contained work units, presents the proposed issue list for confirmation, then creates issues and wires dependencies. Keeps the graph shallow and prefers parallel tracks.
---

# Plan to Beads

A systematic technique for converting a written feature plan into actionable `br` issues. Each issue is self-contained (1 to 3 days of focused work) and the dependency graph is shallow enough to support parallel execution.

## When to Use

- After a feature plan has been written and reviewed (e.g., via `/plan-feature` and `/plan-review`)
- When work is about to start and needs to be broken into trackable issues
- When an existing plan needs to be re-decomposed because scope has shifted

## When NOT to Use

- For a single-issue task (just `br create` directly)
- For exploratory work where the scope is not yet known
- When `br` is not installed or not available in the environment

## Required Workflow

### Step 1: Read the Plan

Read the plan file from `$ARGUMENTS`. If no path is provided, search `docs/plans/` for the most recent plan:

```bash
ls -t docs/plans/feature-plan-*.md | head -5
```

Ask the user to pick if multiple exist.

### Step 2: Extract Work Units

From the plan's milestones, components, and scope, identify natural work units. Each issue should:

- Be completable in 1 to 3 days of focused work
- Have enough context to implement without re-reading the whole plan
- Map to a single milestone or a clear sub-task of one

For each issue, prepare:

| Field | Value |
|---|---|
| **Title** | Short, action-oriented (e.g., "Add user auth middleware") |
| **Priority** | 1 (critical) / 2 (high) / 3 (medium) / 4 (low) |
| **Labels** | Comma-separated, derived from plan (e.g., "backend,auth,milestone-1") |
| **Dependencies** | Which other issues must finish first (by title reference) |

### Step 3: Present and Confirm

Show the user the complete list in a table:

```markdown
## Proposed Issues

| # | Title | Priority | Labels | Depends On |
|---|---|---|---|---|
| 1 | ... | P2 | backend,milestone-1 | - |
| 2 | ... | P2 | backend,milestone-1 | #1 |
| 3 | ... | P3 | frontend,milestone-2 | - |

**Parallel tracks:** Issues 1-2 (backend), Issue 3 (frontend) can proceed independently.
**Total issues:** X
```

**WAIT for user confirmation before proceeding.** The user may want to adjust titles, priorities, or dependencies.

### Step 4: Verify br is Available

```bash
which br && br list --limit 1
```

If `br` is not found, stop and inform the user.

### Step 5: Create Issues

For each confirmed issue, run:

```bash
br create "<Title>" -p <priority> -t task -l "<labels>"
```

Capture the issue ID from each creation output.

### Step 6: Wire Dependencies

For each dependency relationship:

```bash
br dep add <issue-id> <depends-on-id>
```

**Never create circular dependencies.** If A depends on B, B must not depend on A (directly or transitively).

### Step 7: Sync and Report

```bash
br sync --flush-only
```

Then present the final report:

```markdown
## Issues Created

| ID | Title | Priority | Labels |
|---|---|---|---|
| ... | ... | ... | ... |

## Dependency Graph

- Issue X depends on Issue Y
- ...

## Suggested Execution Order

1. Start with: [issues with no deps]
2. Then: [issues whose deps are now met]
3. Finally: [remaining issues]
```

## Critical Rules

**Always:**

- Read the full plan before identifying work units
- Present the complete issue list and WAIT for user confirmation before creating
- Verify `br` is available before attempting to create issues
- Run `br sync --flush-only` after all issues are created
- Make each issue self-contained with enough context to implement independently
- Keep the dependency graph shallow, prefer parallel tracks over deep chains

**Never:**

- Create issues without user confirmation
- Create circular dependencies
- Skip the sync step
- Create issues that are too granular (< 1 hour) or too large (> 1 week)
- Assume `br` is installed without checking

## Quality Checklist

Before reporting completion, verify:

- [ ] All milestones from the plan are covered by at least one issue
- [ ] Each issue has a clear, action-oriented title
- [ ] Dependencies are correct and acyclic
- [ ] `br sync --flush-only` was run
- [ ] Execution order is logical and maximizes parallelism
