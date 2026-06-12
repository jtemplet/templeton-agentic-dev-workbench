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

Every issue body uses this structure. Sections marked with a type tag are required only for beads of that type.

````markdown
## Why (Computational)

[The problem this solves. The stakeholder or motivating constraint. What depends on this.]

## How (Algorithmic)

[The approach, strategy, or representation. Key data flows, contracts, or sequencing.]

## Done when (Acceptance)

[Specific, verifiable conditions. Two people must be able to agree independently whether each
criterion is satisfied without asking the author. Prefer observable behavior, named tests,
or measurable thresholds over subjective judgements.]

<!-- Required for type: task, feature, bug -->
## Acceptance Criteria

[Formal, testable conditions written from the user or system perspective. Use Given/When/Then
or numbered criteria. These complement Done when by capturing the observable behavior a QA
reviewer or product owner would check, not just the implementer.]

<!-- Required for type: bug only (in addition to Acceptance Criteria) -->
## Steps to Reproduce

1. [First step]
2. [Second step]
3. ...

**Expected behavior:** [what should happen]
**Actual behavior:** [what currently happens]
**Environment / version:** [branch, OS, relevant config, if known]

<!-- Required for type: epic only -->
## Success Criteria

[High-level outcomes that signal the epic is delivering value. These are business- or
product-level indicators (e.g., metric thresholds, user capability unlocked, milestone
reached), not line-by-line implementation checks. Each criterion must be verifiable at
the epic level by a stakeholder who has not read the child beads.]

## Estimated size

[<files> files, <LOC> LOC, band: Trivial / Target / Stretch. One-sentence justification if Stretch.
See "The Size Window" for bands. This estimate is also what the loop's diff-budget gate measures
against; budgeting in advance prevents iteration timeouts.]

## Out of scope (optional)

[Anything explicitly deferred to a sibling or follow-up bead.]
````

### Done when vs. Acceptance Criteria (normative)

`## Done when (Acceptance)` and `## Acceptance Criteria` are **not** duplicates. They sit at different altitudes and a complete task/feature/bug bead has both:

- **Done when (Acceptance)** states the *outcome-level* conditions that mean the work is finished. This is the implementer's definition of done, phrased as observable end states.
- **Acceptance Criteria** is the *formal, testable checklist* a reviewer or QA walks through to verify those outcomes. Prefer Given/When/Then or a numbered list of concrete, individually-checkable assertions.

Rule of thumb: if you can hand the line to QA and they can mark it pass/fail without interpretation, it belongs in **Acceptance Criteria**. If it describes the end state in the implementer's words, it belongs in **Done when**.

**Worked example** (a "rate-limit failed logins" bead):

```markdown
## Done when (Acceptance)
- Repeated failed logins from one source are throttled.
- The threshold is configurable without a redeploy.

## Acceptance Criteria
1. Given 5 failed logins in 60s from one IP, When a 6th is attempted, Then the response status is 429.
2. Given the RATE_LIMIT env var is changed, When config reloads, Then the new limit applies without a process restart.
3. Given a successful login, When the rolling window elapses, Then the failure counter resets to 0.
```

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

### Type-specific section audit

A bead **fails** and must be fixed when a required section for its type is absent or empty:

- **task, feature, or bug** with no `## Acceptance Criteria` section, or whose Acceptance Criteria are as vague as "it works" or "user can do X" without specifying the observable signal.
- **bug** with no `## Steps to Reproduce` section, or whose steps cannot be followed by someone unfamiliar with the code (missing preconditions, ambiguous environment, no expected vs. actual contrast).
- **epic** with no `## Success Criteria` section, or whose Success Criteria list only implementation checks (those belong in child-bead Done when sections, not the epic). Epic Success Criteria must be legible to a product stakeholder who has not read the child beads.

A bead **passes** the type-specific audit when:

- **task/feature**: `## Acceptance Criteria` contains at least one testable, observable condition.
- **bug**: `## Acceptance Criteria` and `## Steps to Reproduce` are both present; Steps to Reproduce includes expected vs. actual behavior.
- **epic**: `## Success Criteria` contains at least one outcome-level indicator (metric, capability, milestone) that a non-technical stakeholder could evaluate.

## The Size Window

Every bead must fit within a diff-size window before it is created. Beads that are too large fail to ship in one autonomous iteration; beads that are too small cost more in branch + review + PR overhead than the change is worth. The window is expressed in two dimensions, files-touched and lines-of-code-changed (insertions + deletions vs the base branch).

| Band | Files | LOC | What it means | Action |
|---|---|---|---|---|
| **Trivial** | 1 | < 20 | One-line tweak, typo, single-import fix | Just commit directly; do not file a bead |
| **Target** | 1 to 5 | 20 to 300 | Reviewable as a small diff (fresh-eyes-review path); fits comfortably in one iteration | This is the goal for every bead |
| **Stretch** | up to 10 | up to 600 | Reviewable but requires the full code-reviewer; pushes against one-iteration limits | Acceptable with justification |
| **Too big** | > 10 | > 600 | Either won't finish in one iteration or couples too many concerns | Split before creating |
| **Hard ceiling** | > 30 | > 2000 | Exceeds the autonomous wrapper's diff-budget defaults (outrigger and similar runners abort here) | Never create |

The target band is calibrated against the common "small diff" threshold in code-review skills (under ~5 files / ~250 LOC reviews fast and lands cleanly). The hard ceiling mirrors outrigger's wrapper defaults (`MAX_FILES_CHANGED=30`, `MAX_LOC_CHANGED=2000`); a bead above that line cannot be shipped autonomously even with full budget.

**When dimensions disagree, the worse band wins.** A bead at 8 files / 700 LOC is Too big (LOC dominates), not Stretch. A bead at 12 files / 400 LOC is Too big (files dominates), not Stretch. The "worse" rule is conservative on purpose: a bead that fails on either dimension fails to ship autonomously, so split before creating.

### Why this matters

A real failure that motivated this rule: bead `outrigger-yov` was a 451-LOC / 6-file port (function + tests + wrapper wire-up + docs). It fit the wrapper's hard budget but did not fit one 20-minute iteration, timing out at step 8 of 14. The agent spent $0.62 making real progress, but the bead could not close autonomously. Two right-sized beads (the port, then wire-up + docs) would have shipped cleanly.

### Anti-patterns that signal a too-big bead

- **Conjunctive titles**: "Port X **and** wire X to callers" / "Add Y **and** migrate existing usages". The conjunction is the split line.
- **Test code counted separately**: a 150-LOC implementation with 200 LOC of tests is a 350-LOC bead, not a 150-LOC one. Tests are part of the diff.
- **Documentation as a phase**: if shipping the bead requires non-trivial doc updates (e.g., architecture diagram, README section, CLAUDE.md edits), count those LOC. If they dominate, split the doc work into its own bead.
- **"Add feature X with full coverage"**: vague scope. Force an estimate; usually decomposes into 2 to 4 right-sized beads.
- **Single bead, multiple distinct call sites**: "Implement X and update the 8 callers" is 1 + 8 sub-tasks. The first is a bead; the call-site migrations are either one bead (if mechanical) or sibling beads (if each needs judgment).

### Audit checks (size)

A bead **fails** the size audit and must be split when:

- The estimated size is in the "Too big" or "Hard ceiling" band.
- The title contains a conjunction (`and`, `+`, `plus`, `with`) that names two work units. The conjunction itself is only a hint; the load-bearing rule is "names two work units." A title like "Add user auth middleware **with** rate limiting" is two work units; "Add user auth middleware **with** tests" is one (tests are part of the diff).
- The How describes two or more distinct approaches or call-site changes that could ship separately.
- A reviewer reading the Done when cannot tell which acceptance criterion belongs to which work unit (compound scope).

A bead **fails** the size audit and must be merged with a sibling (or just committed) when:

- The estimated size is in the "Trivial" band AND no upstream / downstream work depends on it being a separate trackable unit.

### Estimating size

Estimation is rough; the goal is to spot which band a bead falls in, not to predict to the line. Use whichever of these gives the fastest signal:

1. **Read the How** and count the files or modules it names. If you can name 1 to 5 specific files, you are probably in Target band.
2. **For ports, refactors, or pattern applications**, look at the source file(s) being ported. Output LOC is usually within 1.5x of input LOC for a faithful port; for a refactor that adds tests, multiply by ~2.
3. **For greenfield features**, sketch the function or component surface. Each significant function is roughly 30 to 80 LOC; each test typically adds another 30 to 100 LOC.
4. **When uncertain, round up.** A bead estimated at "300 to 600 LOC" should be treated as 600 (Stretch). If 600 is the upper bound, plan to split.

If you cannot estimate within one band, ask the user to clarify scope or split speculatively. Do not write an estimate of "unknown".

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

- Fall in the Target or Stretch size band (see "The Size Window")
- Have enough context to implement without re-reading the whole plan
- Map to a single milestone or a clear sub-task of one

**Structural check.** Every plan stage maps to at least one bead, and every bead maps back to a stage. Flag orphans on either side before running the Marr audit.

For each issue, prepare:

| Field | Value |
|---|---|
| **Title** | Short, action-oriented (e.g., "Add user auth middleware"). No conjunctions ("and", "+", "plus", "with") that bundle two work units |
| **Type** | `task`, `feature`, `bug`, or `epic`. This determines which type-specific sections are required (see "Type-specific section audit") |
| **Priority** | 1 (critical) / 2 (high) / 3 (medium) / 4 (low) |
| **Labels** | Comma-separated, derived from plan (e.g., "backend,auth,milestone-1") |
| **Dependencies** | Which other issues must finish first (by title reference) |
| **Why (L1: Computational)** | Drafted per the body shape above |
| **How (L2: Algorithmic)** | Drafted per the body shape above |
| **Done when (Acceptance)** | Drafted per the body shape above |
| **Acceptance Criteria** | Required for task, feature, bug. Testable, observable conditions from a QA or product perspective |
| **Steps to Reproduce** | Required for bug only. Numbered steps + expected vs. actual behavior |
| **Success Criteria** | Required for epic only. Outcome-level indicators legible to a product stakeholder |
| **Estimated size** | `<files>` files, `<LOC>` LOC, band: Trivial / Target / Stretch / Too big. See "The Size Window" |

Draft Why, How, Done when, type-specific sections, AND the size estimate per the body shape, then **run the full audit on every bead** (Marr audit, size audit, AND type-specific section audit) using the checks in "The Marr Audit Standard", "The Size Window", and "Type-specific section audit" above:

- Rewrite any bead whose Why, How, or Done when fails. Do not defer this to the user confirmation gate; weak descriptions waste the user's review time.
- Draft the type-specific sections for every bead before presenting: `## Acceptance Criteria` for task/feature/bug, `## Steps to Reproduce` for bug, `## Success Criteria` for epic. Rewrite any that are vague or fail the type-specific audit; do not defer to the user confirmation gate.
- Merge two beads if they share the same Why and How. Split one bead if its How actually describes two independent approaches.
- Stop and ask the user if you cannot articulate a Why for a bead. That usually means it is an implementation detail of another bead, not a real work unit.
- Stop and ask the user if you cannot write a Done when that a second person could verify. That usually means the bead's scope is unclear or it depends on a judgment call that should be made explicit.
- **Split any bead in the Too-big or Hard-ceiling size band.** Use the anti-pattern checklist in "The Size Window" to find the split line. Re-run the Marr audit on each child bead.
- **Demote any Trivial-band bead to a direct commit.** Note in the final report which work units were not filed as beads and why.

**Derive dependencies from the How.** Where one bead's How references another bead's output (e.g., "consume the new auth middleware"), capture that as a dependency. The How is a source of dep edges, not just a description.

Do not proceed to Step 3 until every bead passes the audit.

### Step 3: Present and Confirm

Show the user the complete list, and surface the Why, How, Done when, type-specific sections, AND Estimated size for each bead so they can verify the full audit, not just the metadata:

````markdown
## Proposed Issues

| # | Title | Type | Priority | Labels | Size (files / LOC, band) | Depends On |
|---|---|---|---|---|---|---|
| 1 | ... | task | P2 | backend,milestone-1 | 3 / 180, Target | - |
| 2 | ... | bug | P2 | backend,milestone-1 | 4 / 250, Target | #1 |
| 3 | ... | epic | P3 | frontend,milestone-2 | 2 / 90, Target | - |

### Bead bodies

## #1: <Title> (task)

*Why (L1):* <one or two sentences naming the problem and the stakeholder or constraint>

*How (L2):* <one or two sentences naming the approach and the key decision>

*Done when:* <bullet list of verifiable conditions>

*Acceptance Criteria:* <testable, observable conditions from a QA or product perspective>

*Estimated size:* <files> files, <LOC> LOC, band: <band>. <one-sentence justification if Stretch>

## #2: <Title> (bug)

*Why (L1):* ...

*How (L2):* ...

*Done when:* ...

*Acceptance Criteria:* ...

*Steps to Reproduce:*
1. ...
2. ...
**Expected:** ... **Actual:** ...

*Estimated size:* ...

## #3: <Title> (epic)

*Why (L1):* ...

*How (L2):* ...

*Done when:* ...

*Success Criteria:* <outcome-level indicators legible to a product stakeholder>

*Estimated size:* ...

**Parallel tracks:** Issues 1-2 (backend), Issue 3 (frontend) can proceed independently.
**Total issues:** X
**Trivial work units rolled into direct commits (not filed as beads):** <list, or "none">
````

**WAIT for user confirmation before proceeding.** The user may want to adjust titles, priorities, dependencies, Why/How, or Done when content. Treat any edit as a re-audit: confirm the rewrite still passes before moving on.

### Step 4: Verify br is Available

```bash
which br && br list --limit 1
```

If `br` is not found, stop and inform the user.

### Step 5: Create Issues

For each confirmed issue, pass the full body via `-d` so the Why, How, Done when, type-specific sections, and Estimated size all live in the issue. Use `-t <type>` to set the bead type (`task`, `feature`, `bug`, or `epic`).

**task or feature:**

```bash
br create "<Title>" -p <priority> -t task -l "<labels>" -d "$(cat <<'EOF'
## Why (Computational)
<L1 content>

## How (Algorithmic)
<L2 content>

## Done when (Acceptance)
- <criterion 1>
- <criterion 2>

## Acceptance Criteria
- <testable, observable condition 1>
- <testable, observable condition 2>

## Estimated size
<files> files, <LOC> LOC, band: <band>. <one-sentence justification if Stretch>
EOF
)"
```

**bug:**

```bash
br create "<Title>" -p <priority> -t bug -l "<labels>" -d "$(cat <<'EOF'
## Why (Computational)
<L1 content>

## How (Algorithmic)
<L2 content>

## Done when (Acceptance)
- <criterion 1>
- <criterion 2>

## Acceptance Criteria
- <testable, observable condition 1>

## Steps to Reproduce
1. <step>
2. <step>

**Expected behavior:** <what should happen>
**Actual behavior:** <what currently happens>
**Environment / version:** <branch, OS, relevant config>

## Estimated size
<files> files, <LOC> LOC, band: <band>. <one-sentence justification if Stretch>
EOF
)"
```

**epic:**

```bash
br create "<Title>" -p <priority> -t epic -l "<labels>" -d "$(cat <<'EOF'
## Why (Computational)
<L1 content>

## How (Algorithmic)
<L2 content>

## Done when (Acceptance)
- <criterion 1>
- <criterion 2>

## Success Criteria
- <outcome-level indicator 1>
- <outcome-level indicator 2>

## Estimated size
<files> files, <LOC> LOC, band: <band>. <one-sentence justification if Stretch>
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
- Assign a type (`task`, `feature`, `bug`, or `epic`) to every bead before drafting its body
- Articulate Marr Level 1 (Why) and Level 2 (How) for every bead before presenting
- Draft Done when for every bead; each criterion must be verifiable by a second person without asking the author
- Draft `## Acceptance Criteria` for every task, feature, and bug bead; draft `## Steps to Reproduce` for every bug bead; draft `## Success Criteria` for every epic bead
- Estimate size (files + LOC + band) for every bead before presenting
- Run the full audit on every bead (Marr AND size AND type-specific section) and rewrite, split, or demote failures before the confirmation gate
- Present the complete issue list, including each bead's type, Why, How, Done when, type-specific sections, AND size estimate, and WAIT for user confirmation before creating
- Verify `br` is available before attempting to create issues
- Pass the Why, How, Done when, type-specific sections, AND Estimated size body to `br create` via `-d`; do not strip any section to save a line
- Make each issue self-contained with enough context to implement independently
- Keep the dependency graph shallow, prefer parallel tracks over deep chains

**Never:**

- Create a bead that fails the Marr audit (see "Audit checks" above for the canonical pass/fail criteria)
- Create a bead that fails the size audit (Too big, Hard ceiling, or Trivial-and-standalone; see "The Size Window")
- Create a bead that fails the type-specific section audit (missing `## Acceptance Criteria` for task/feature/bug, missing `## Steps to Reproduce` for bug, or missing `## Success Criteria` for epic)
- Create issues without user confirmation
- Create circular dependencies
- Assume `br` is installed without checking

## Quality Checklist

Before reporting completion, verify:

- [ ] All milestones from the plan are covered by at least one issue
- [ ] Each issue has a clear, action-oriented title with no work-unit-bundling conjunction
- [ ] Every issue has an explicit type (`task`, `feature`, `bug`, or `epic`)
- [ ] Every issue body uses the `## Why (Computational)` / `## How (Algorithmic)` / `## Done when (Acceptance)` structure
- [ ] Every `## Done when` section contains at least one condition a second person could verify independently
- [ ] Every task, feature, and bug bead includes `## Acceptance Criteria` with at least one testable, observable condition
- [ ] Every bug bead includes `## Steps to Reproduce` with numbered steps and expected vs. actual behavior
- [ ] Every epic bead includes `## Success Criteria` with at least one outcome-level indicator legible to a product stakeholder
- [ ] Every bead falls in the Target or Stretch size band (Stretch beads include a one-sentence justification)
- [ ] No bead is in the Too-big or Hard-ceiling band
- [ ] Trivial-band work units were demoted to direct commits and listed in the final report
- [ ] Dependencies are correct and acyclic
- [ ] Longest dependency chain is at most 3 issues; if longer, a parallel split was missed
- [ ] `br sync --flush-only` was run
- [ ] Execution order is logical and maximizes parallelism
