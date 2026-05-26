---
name: plan-to-beads
description: Decompose a feature implementation plan into trackable br (beads_rust) issues with a dependency graph. Each bead requires Why (Marr L1), How (Marr L2), and Done when (acceptance criteria) before creation. Presents the full list for confirmation, then creates issues and wires dependencies. Keeps the graph shallow and prefers parallel tracks.
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

## The Marr Audit Standard

Every bead must articulate at least **Marr Levels 1 and 2** before it is created. (David Marr, *Vision*, 1982.)

| Level | Name | The question it answers | Required for every bead? |
|---|---|---|---|
| 1 | **Computational** | *What problem is this solving, and why does it matter?* | Yes |
| 2 | **Algorithmic** | *What is the approach or representation? How, conceptually, will it work?* | Yes |
| 3 | **Implementation** | *What are the exact files, libraries, and code shapes?* | Optional; may be deferred to the implementer |

**Why this matters for beads:** A bead with only Level 3 ("edit `auth.py` to call `bcrypt.hashpw`") is brittle; the next person can't tell whether to question the approach when reality shifts. A bead with only Level 1 ("we need auth") is a wish, not a work unit. Levels 1 and 2 together let the implementer make sound trade-offs without re-reading the parent plan.

### Required body shape

Every issue body uses this structure:

````markdown
## Why (Computational)

[The problem this solves. The stakeholder or motivating constraint. What depends on this.]

## How (Algorithmic)

[The approach, strategy, or representation. Key data flows, contracts, or sequencing.]

## Done when (Acceptance)

[Specific, verifiable conditions. Two people must be able to agree independently whether each
criterion is satisfied without asking the author. Prefer observable behavior, named tests,
or measurable thresholds over subjective judgements.]

## Out of scope (optional)

[Anything explicitly deferred to a sibling or follow-up bead.]
````

### Audit checks

A bead **fails** the audit and must be rewritten when:

- The Why is just a restatement of the title (e.g., title "Add auth middleware", Why "We need to add auth middleware").
- The Why names no stakeholder, motivating constraint, or downstream consumer. "This is needed" is not a Why.
- The How is missing, or is actually Level 3 ("edit `app.py` line 42"). Implementation specifics are not an approach.
- The How does not constrain the approach. "Implement the middleware" describes nothing.
- Two beads share the same Why and How. The work-unit boundary is wrong; merge them or sharpen the split.
- The Done when is absent.
- The Done when is vague: "it works", "tests pass" (without naming which), "feature is complete", "looks good".
- The Done when cannot be verified by a second person without asking the author.

A bead **passes** when the Why names a stakeholder or motivating constraint, the How states an approach with at least one key decision or trade-off, and the Done when lists at least one condition a second person could verify independently.

## Required Workflow

### Step 1: Read the Plan

Read the plan file from `$ARGUMENTS`. If no path is provided, search `docs/plans/` for the most recent plan:

```bash
ls -t docs/plans/feature-plan-*.md | head -5
```

Ask the user to pick if multiple exist.

### Step 2: Extract Work Units, Articulate Levels 1 and 2, Draft Acceptance Criteria, and Audit

**Re-decomposition check (do this first).** If beads already exist for this plan (search by `plan:<plan-name>` label, or by the plan's filename in issue references), present a diff of new / changed / removed beads against the existing set and require the user's confirmation before any create, update, or close. Do not silently re-create.

From the plan's milestones, components, and scope, identify natural work units. Each issue should:

- Be completable in 1 to 3 days of focused work
- Have enough context to implement without re-reading the whole plan
- Map to a single milestone or a clear sub-task of one

**Structural check.** Every plan stage maps to at least one bead, and every bead maps back to a stage. Flag orphans on either side before running the Marr audit.

For each issue, prepare:

| Field | Value |
|---|---|
| **Title** | Short, action-oriented (e.g., "Add user auth middleware") |
| **Priority** | 1 (critical) / 2 (high) / 3 (medium) / 4 (low) |
| **Labels** | Comma-separated, derived from plan (e.g., "backend,auth,milestone-1") |
| **Dependencies** | Which other issues must finish first (by title reference) |
| **Why (L1: Computational)** | Drafted per the body shape above |
| **How (L2: Algorithmic)** | Drafted per the body shape above |
| **Done when (Acceptance)** | Drafted per the body shape above |

Draft Why, How, and Done when per the body shape, then **run the full audit on every bead** using the checks in "The Marr Audit Standard" above:

- Rewrite any bead whose Why, How, or Done when fails. Do not defer this to the user confirmation gate; weak descriptions waste the user's review time.
- Merge two beads if they share the same Why and How. Split one bead if its How actually describes two independent approaches.
- Stop and ask the user if you cannot articulate a Why for a bead. That usually means it is an implementation detail of another bead, not a real work unit.
- Stop and ask the user if you cannot write a Done when that a second person could verify. That usually means the bead's scope is unclear or it depends on a judgment call that should be made explicit.

**Derive dependencies from the How.** Where one bead's How references another bead's output (e.g., "consume the new auth middleware"), capture that as a dependency. The How is a source of dep edges, not just a description.

Do not proceed to Step 3 until every bead passes the audit.

### Step 3: Present and Confirm

Show the user the complete list, and surface the Why, How, and Done when for each bead so they can verify the full audit, not just the metadata:

````markdown
## Proposed Issues

| # | Title | Priority | Labels | Depends On |
|---|---|---|---|---|
| 1 | ... | P2 | backend,milestone-1 | - |
| 2 | ... | P2 | backend,milestone-1 | #1 |
| 3 | ... | P3 | frontend,milestone-2 | - |

### Bead bodies

## #1: <Title>

*Why (L1):* <one or two sentences naming the problem and the stakeholder or constraint>

*How (L2):* <one or two sentences naming the approach and the key decision>

*Done when:* <bullet list of verifiable conditions>

## #2: <Title>

*Why (L1):* ...

*How (L2):* ...

*Done when:* ...

**Parallel tracks:** Issues 1-2 (backend), Issue 3 (frontend) can proceed independently.
**Total issues:** X
````

**WAIT for user confirmation before proceeding.** The user may want to adjust titles, priorities, dependencies, Why/How, or Done when content. Treat any edit as a re-audit: confirm the rewrite still passes before moving on.

### Step 4: Verify br is Available

```bash
which br && br list --limit 1
```

If `br` is not found, stop and inform the user.

### Step 5: Create Issues

For each confirmed issue, pass the full body via `-d` so the Why, How, and Done when all live in the issue:

```bash
br create "<Title>" -p <priority> -t task -l "<labels>" -d "$(cat <<'EOF'
## Why (Computational)
<L1 content>

## How (Algorithmic)
<L2 content>

## Done when (Acceptance)
- <criterion 1>
- <criterion 2>
EOF
)"
```

Capture the issue ID from each creation output. If `br create` exits non-zero, stop and proceed to Step 5b; do not retry blindly.

`br create` defaults the status to `open`. If a bead should start as `deferred` or `in_progress`, pass `-s <status>`.

### Step 5b: Handle Partial Failure

If `br create` exited non-zero before all beads were created, do not proceed to Step 6. Issue creation is a side effect on shared state; the user owns the recovery decision.

1. Capture the IDs that were created successfully (with their titles).
2. Capture the bead that failed and the error message verbatim.
3. Identify the remaining beads that were never attempted.
4. Present all three lists to the user, then ask which path to take:

   - **Fix and resume**: address the cause of the failure, then re-run Step 5 starting from the failed bead. Successful creates stay in place.
   - **Delete and retry**: close the partial creates with `br update <id> --status closed` (preferred over a hard delete; preserves the audit trail), fix the cause, then re-run Step 5 with the full list.
   - **Keep as is**: accept the partial state, file a follow-up bead documenting what's missing, then proceed to Step 6 wiring only the IDs that were created.

5. Do not pick for the user. Wait for an explicit choice before any further `br` command.

### Step 6: Wire Dependencies

For each dependency relationship:

```bash
br dep add <issue-id> <depends-on-id>
```

Step 5's auto-flush usually handles this. If the run used `--no-auto-flush`, run `br sync --flush-only` between Steps 5 and 6 so dependency wiring can resolve the new IDs.

The acyclicity rule is enforced via the Never list above; if A depends on B, B must not depend on A directly or transitively.

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

### Step 7b (optional): Record the decomposition in the plan file

Append a one-line note to the plan's Status section: `Decomposed: <YYYY-MM-DD>, see br <id-range>`. This lets the next agent reading the plan know it has been decomposed without re-running the skill. Skip if the plan file is read-only or if the user prefers tracking elsewhere.

## Critical Rules

**Always = invariants the agent must hold during execution. Quality Checklist = pre-completion verification. Each fact lives in exactly one list.**

**Always:**

- Read the full plan before identifying work units
- Articulate Marr Level 1 (Why) and Level 2 (How) for every bead before presenting
- Draft Done when for every bead; each criterion must be verifiable by a second person without asking the author
- Run the full audit on every bead and rewrite failures before the confirmation gate
- Present the complete issue list, including each bead's Why, How, and Done when, and WAIT for user confirmation before creating
- Verify `br` is available before attempting to create issues
- Pass the Why, How, and Done when body to `br create` via `-d`; do not strip any section to save a line
- Make each issue self-contained with enough context to implement independently
- Keep the dependency graph shallow, prefer parallel tracks over deep chains

**Never:**

- Create a bead that fails the Marr audit (see "Audit checks" above for the canonical pass/fail criteria)
- Create issues without user confirmation
- Create circular dependencies
- Create issues that are too granular (< 1 hour) or too large (> 1 week)
- Assume `br` is installed without checking

## Quality Checklist

Before reporting completion, verify:

- [ ] All milestones from the plan are covered by at least one issue
- [ ] Each issue has a clear, action-oriented title
- [ ] Every issue body uses the `## Why (Computational)` / `## How (Algorithmic)` / `## Done when (Acceptance)` structure
- [ ] Every `## Done when` section contains at least one condition a second person could verify independently
- [ ] Dependencies are correct and acyclic
- [ ] Longest dependency chain is at most 3 issues; if longer, a parallel split was missed
- [ ] `br sync --flush-only` was run
- [ ] Execution order is logical and maximizes parallelism
