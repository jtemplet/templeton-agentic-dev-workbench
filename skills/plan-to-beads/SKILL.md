---
name: plan-to-beads
description: Decompose a feature implementation plan into trackable bd (beads) issues with a dependency graph. Each bead requires Why (Marr L1), How (Marr L2), and Done when (acceptance criteria) before creation. Presents the full list for confirmation, then creates issues and wires dependencies. Keeps the graph shallow and prefers parallel tracks.
---

# Plan to Beads

A systematic technique for converting a written feature plan into actionable `bd` issues. Each issue
is self-contained (1 to 3 days of focused work) and the dependency graph is shallow enough to
support parallel execution.

## When to Use

- After a feature plan has been written and reviewed, for example by `/write-plan` and
  `/plan-review`
- When work is about to start and needs to be broken into trackable issues
- When an existing plan needs to be re-decomposed because scope has shifted

## When NOT to Use

- For a single-issue task (just `bd create` directly)
- For exploratory work where the scope is not yet known
- When `bd` is not installed or not available in the environment

## The Marr Audit Standard

Every bead must articulate at least **Marr Levels 1 and 2** before it is created. (David Marr,
*Vision*, 1982.)

| Level | Name | The question it answers | Required for every bead? |
|---|---|---|---|
| 1 | **Computational** | *What problem is this solving, and why does it matter?* | Yes |
| 2 | **Algorithmic** | *What is the approach or representation? How, conceptually, will it work?* | Yes |
| 3 | **Implementation** | *What are the exact files, libraries, and code shapes?* | Optional; may be deferred to the implementer |

**Why this matters for beads:** A bead with only Level 3, such as "edit `auth.py` to call
`bcrypt.hashpw`", breaks easily. The next person cannot tell whether to question the approach
when the situation changes. A bead with only Level 1 ("we need auth") is a wish, not a work
unit. Levels 1 and 2 together let the implementer make sound trade-offs without re-reading the
parent plan.

### Required body shape

[docs/bead-body-contract.md](../../docs/bead-body-contract.md) owns the bead body shape. Read it
before you draft the first bead. It names every section, gives the byte-exact heading, says which
type requires it, and says which `bd` field holds it. It also explains why Done when and Acceptance
Criteria are different sections, with a worked example.

This skill keeps no second copy of that list, and neither does `bead-audit`, because two copies
drift apart ([ADR 0001](../../docs/adr/0001-native-tracker-fields-are-canonical.md)). Where this
skill and the contract disagree, the contract wins.

Two things to carry from the contract into Step 5 below:

- **A section goes in its native `bd` field, never in the description body.** The contract's
  "Where each section goes" table names the field for each section. Step 5 below has the exact
  create commands. Follow those, and paste no template from the contract into
  `bd create -d`.
- **Write `## How (Algorithmic)` and `## Acceptance Criteria` nowhere on `bd`.** The field name
  already says which section it is. Both headings still govern a tracker with no native fields,
  such as GitHub Issues.

### Audit checks

A bead **fails** the audit and must be rewritten when:

- The Why is just a restatement of the title. One example: the title reads "Add auth middleware",
  and the Why reads "We need to add auth middleware".
- The Why names no stakeholder, motivating constraint, or downstream consumer. "This is needed" is
  not a Why.
- The How is missing, or is actually Level 3 ("edit `app.py` line 42"). Implementation specifics are
  not an approach.
- The How does not constrain the approach. "Implement the middleware" describes nothing.
- Two beads share the same Why and How. The work-unit boundary is wrong; merge them or sharpen the
  split.
- The Done when is absent.
- The Done when is vague: "it works", "tests pass" (without naming which), "feature is complete",
  "looks good".
- The Done when cannot be verified by a second person without asking the author.

A bead **passes** when all three of these hold. The Why names a stakeholder or a motivating
constraint. The How states an approach with at least one key decision or trade-off. The Done when
lists at least one condition a second person could verify independently.

### Type-specific section audit

A bead **fails** and must be fixed when a required section for its type is absent or empty:

- **task, feature, or bug** with no `## Acceptance Criteria` section, or whose Acceptance Criteria
  are as vague as "it works" or "user can do X" without specifying the observable signal.
- **bug** with no `## Steps to Reproduce` section, or whose steps cannot be followed by someone
  unfamiliar with the code (missing preconditions, ambiguous environment, no expected vs. actual
  contrast).
- **epic** with no `## Success Criteria` section, or whose Success Criteria list only implementation
  checks (those belong in child-bead Done when sections, not the epic). Epic Success Criteria must
  be legible to a product stakeholder who has not read the child beads.

A bead **passes** the type-specific audit when:

- **task/feature**: `## Acceptance Criteria` contains at least one testable, observable condition.
- **bug**: `## Acceptance Criteria` and `## Steps to Reproduce` are both present; Steps to Reproduce
  includes expected vs. actual behavior.
- **epic**: `## Success Criteria` contains at least one outcome-level indicator (metric, capability,
  milestone) that a non-technical stakeholder could evaluate.

## The Size Window

Every bead must fit within a diff-size window before it is created. Beads that are too large fail to
ship in one autonomous iteration; beads that are too small cost more in branch + review + PR
overhead than the change is worth. The window is expressed in two dimensions, files-touched and
lines-of-code-changed (insertions + deletions vs the base branch).

| Band | Files | LOC | What it means | Action |
|---|---|---|---|---|
| **Trivial** | 1 | < 20 | One-line tweak, typo, single-import fix | Just commit directly; do not file a bead |
| **Target** | 1 to 5 | 20 to 300 | Reviewable as a small diff (review-fresh-eyes path); fits comfortably in one iteration | This is the goal for every bead |
| **Stretch** | up to 10 | up to 600 | Reviewable but requires the full code-reviewer; pushes against one-iteration limits | Acceptable with justification |
| **Too big** | > 10 | > 600 | Either won't finish in one iteration or couples too many concerns | Split before creating |
| **Hard ceiling** | > 30 | > 2000 | Exceeds the autonomous wrapper's diff-budget defaults (outrigger and similar runners abort here) | Never create |

The target band is calibrated against the common "small diff" threshold in code-review skills (under
~5 files / ~250 LOC reviews fast and lands cleanly). The hard ceiling mirrors outrigger's wrapper
defaults (`MAX_FILES_CHANGED=30`, `MAX_LOC_CHANGED=2000`); a bead above that line cannot be shipped
autonomously even with full budget.

**When dimensions disagree, the worse band wins.** A bead at 8 files / 700 LOC is Too big (LOC
dominates), not Stretch. A bead at 12 files / 400 LOC is Too big (files dominates), not Stretch. The
"worse" rule is conservative on purpose: a bead that fails on either dimension fails to ship
autonomously, so split before creating.

### Anti-patterns that signal a too-big bead

- **Conjunctive titles**: "Port X **and** wire X to callers" / "Add Y **and** migrate existing
  usages". The conjunction is the split line.
- **Test code counted separately**: a 150-LOC implementation with 200 LOC of tests is a 350-LOC
  bead, not a 150-LOC one. Tests are part of the diff.
- **Documentation as a phase**: if shipping the bead needs substantial doc updates, count those
  LOC. Such an update can be an architecture diagram, a README section, or CLAUDE.md edits. If
  they dominate, split the doc work into its own bead.
- **"Add feature X with full coverage"**: vague scope. Force an estimate; usually decomposes into 2
  to 4 right-sized beads.
- **Single bead, multiple distinct call sites**: "Implement X and update the 8 callers" is 1 + 8
  sub-tasks. The first is a bead; the call-site migrations are either one bead (if mechanical) or
  sibling beads (if each needs judgment).

### Audit checks (size)

A bead **fails** the size audit and must be split when:

- The estimated size is in the "Too big" or "Hard ceiling" band.
- The title contains a conjunction (`and`, `+`, `plus`, `with`) that names two work units. The
  conjunction itself is only a hint. The rule that decides is "names two work units". "Add user auth
  middleware **with** rate limiting" is two work units. "Add user auth middleware **with** tests" is
  one, because the tests are part of the diff.
- The How describes two or more distinct approaches or call-site changes that could ship separately.
- A reviewer reading the Done when cannot tell which acceptance criterion belongs to which work unit
  (compound scope).

A bead **fails** the size audit and must be merged with a sibling (or just committed) when:

- The estimated size is in the "Trivial" band AND no upstream / downstream work depends on it being
  a separate trackable unit.

### Estimating size

Estimation is rough; the goal is to spot which band a bead falls in, not to predict to the line. Use
whichever of these gives the fastest signal:

1. **Read the How** and count the files or modules it names. If you can name 1 to 5 specific files,
   you are probably in Target band.
2. **For ports, refactors, or pattern applications**, look at the source file(s) being ported.
   Output LOC is usually within 1.5x of input LOC for a faithful port; for a refactor that adds
   tests, multiply by ~2.
3. **For greenfield features**, sketch the function or component surface. Each significant function
   is roughly 30 to 80 LOC; each test typically adds another 30 to 100 LOC.
4. **When uncertain, round up.** A bead estimated at "300 to 600 LOC" should be treated as 600
   (Stretch). If 600 is the upper bound, plan to split.

If you cannot estimate within one band, ask the user to clarify scope or split speculatively. Do not
write an estimate of "unknown".

## Required Workflow

### Step 1: Read the Plan

Read the plan file from `$ARGUMENTS`. If no path is provided, search `docs/plans/` for the most
recent plan:

```bash
ls -t docs/plans/feature-plan-*.md | head -5
```

Ask the user to pick if multiple exist.

### Step 2: Extract Work Units, Articulate Levels 1 and 2, Draft Acceptance Criteria, and Audit

**Re-decomposition check (do this first).** Records may already exist for this plan. List them,
the closed records included:

```bash
bd list --label plan:<plan-name> --all --json
```

`<plan-name>` is the name in the `plan:` label that the plan's earlier records carry. For a first
decomposition, use the plan's file name without `feature-plan-` and `.md`. Also search the
existing records for the plan's file name, because an earlier decomposition may carry no `plan:`
label.

Sort every record you find into one of two groups, by its `labels` array:

- **Keyed.** The record carries a `plan-unit:<key>` label. Step 5 finds it by that key.
- **Older.** The record carries no `plan-unit:` label. Propose an explicit mapping from each
  proposed unit to an existing native ID, and show that mapping in Step 3. Never match on the
  title alone, because a title changes and two records can share one.

Then show what this run would add, change, and remove against the existing records. An existing
record that is open, in progress, or closed gets a change proposal first. Do not defer, reparent,
close, or reopen it without the user's approval. Do not silently re-create a record.

**Read `CONTEXT.md` next, when the repository has one.** That file is the project's glossary,
meaning the list of terms and what each one means here. Take every bead title's vocabulary from it,
and every domain term in the body too. Use the glossary's word for a thing rather than a synonym.
A bead outlives the session that filed it, so a synonym costs every later reader a translation.

A concept the glossary does not carry is a signal, not an error. It means one of two things.
Either the plan is inventing a word the project does not use, or the glossary has a real gap.
Say which at the confirmation gate in Step 3. Do not write to `CONTEXT.md`. [ADR
0007](../../docs/adr/0007-a-tadw-skill-wins-over-an-overlapping-external-skill.md) keeps
`mattpocock-skills:domain-modeling` as the only skill that writes it.

From the plan's milestones, components, and scope, identify natural work units. Each issue should:

- Fall in the Target or Stretch size band (see "The Size Window")
- Have enough context to implement without re-reading the whole plan
- Map to a single milestone or a clear sub-task of one

**Structural check.** Every plan stage maps to at least one bead, and every bead maps back to a
stage. Flag orphans on either side before running the Marr audit.

**Inherit acceptance criteria from the plan.** Plans written by `/write-plan` or `/plan-from-idea`
carry an `## Acceptance Criteria` section and a per-milestone "Done when" column. Trace each
plan-level criterion to the bead that satisfies it, and derive that bead's `## Acceptance Criteria`
from it rather than inventing a parallel set. Two failure modes to surface at the confirmation gate:

- A plan criterion no bead proves. This is a decomposition gap; add or widen a bead.
- A bead proving no plan criterion. This is scope the plan never asked for; cut it or confirm it is
  deliberate.

If the plan has no acceptance criteria at all, say so, author them per bead from the plan's goals
and scope, and recommend the user run `/plan-review` on the plan. Do not silently paper over an
unprovable plan.

**Inherit binding ADRs from the plan.** Plans written by `/write-plan` or `/plan-from-idea`
carry a `## Decisions That Bind This Plan` section. It is a table that names each ADR, the rule
that ADR sets, and how the plan honors it. Read that section. For each ADR in it, decide which
beads the ADR constrains. Write the ADR number and its rule into the `design` field of each of
those beads, as part of the How. Add no new heading and no separate note for it. A binding rule
limits the approach, and `design` is the native field that holds the approach
([ADR 0001](../../docs/adr/0001-native-tracker-fields-are-canonical.md)).

Surface one failure mode at the confirmation gate in Step 3, before any bead is created: an ADR the
plan names that no bead inherits. Name that ADR by its number. Either a bead is missing the rule, or
the plan lists an ADR that does not constrain this work. Ask the user which.

If the plan has no such section, or the section reads "None found", say so once and create the
beads as usual. A repository with no `docs/adr/` is normal, not an error.

**Give every proposed bead a work-unit key, the epic included.** A work-unit key is a short
kebab-case name for one approved unit of work, such as `hold-new-beads`. The label pair
`plan:<plan-name>` plus `plan-unit:<key>` is the bead's identity across sessions. Step 5 uses that
pair to find a record whose native ID this session never saw.

- The key names the approved unit of work, not its title and not its position in the list.
- A title change keeps the key.
- A split makes a new key for each new unit.
- Never reuse a key for different work. Show the replacement or the retirement of a unit in
  Step 3, and wait for approval.

For each issue, prepare:

| Field | Value |
|---|---|
| **Work-unit key** | Stable kebab-case name for the approved unit, such as `hold-new-beads`. It becomes the label `plan-unit:<key>` |
| **Title** | Short and action-oriented, such as "Add user auth middleware". No conjunctions ("and", "+", "plus", "with") that bundle two work units |
| **Type** | `task`, `feature`, `bug`, or `epic`. This determines which type-specific sections are required (see "Type-specific section audit") |
| **Priority** | `P0` (critical) / `P1` (high) / `P2` (medium) / `P3` (low) / `P4` (backlog) |
| **Labels** | Comma-separated. Always `plan:<plan-name>` and `plan-unit:<key>`, then the labels derived from the plan, such as "backend,auth,milestone-1" |
| **Dependencies** | Which other issues must finish first (by title reference) |
| **Why (L1: Computational)** | Drafted per the body shape above |
| **How (L2: Algorithmic)** | Drafted per the body shape above |
| **Done when (Acceptance)** | Drafted per the body shape above |
| **Acceptance Criteria** | Required for task, feature, bug. Testable, observable conditions from a QA or product perspective |
| **Steps to Reproduce** | Required for bug only. Numbered steps + expected vs. actual behavior |
| **Success Criteria** | Required for epic only. Outcome-level indicators legible to a product stakeholder |
| **Estimated size** | `<files>` files, `<LOC>` LOC, band: Trivial / Target / Stretch / Too big. See "The Size Window" |

Draft the Why, the How, the Done when, the type-specific sections, AND the size estimate, per the
body shape. Then **run the full audit on every bead**: the Marr audit, the size audit, AND the
type-specific section audit. Use the checks in "The Marr Audit Standard", "The Size Window", and
"Type-specific section audit" above:

- Rewrite any bead whose Why, How, or Done when fails. Do not defer this to the user confirmation
  gate; weak descriptions waste the user's review time.
- Draft the type-specific sections for every bead before presenting: `## Acceptance Criteria` for
  task/feature/bug, `## Steps to Reproduce` for bug, `## Success Criteria` for epic. Rewrite any
  that are vague or fail the type-specific audit; do not defer to the user confirmation gate.
- Merge two beads if they share the same Why and How. Split one bead if its How actually describes
  two independent approaches.
- Stop and ask the user if you cannot articulate a Why for a bead. That usually means it is an
  implementation detail of another bead, not a real work unit.
- Stop and ask the user if you cannot write a Done when that a second person could verify. That
  usually means the bead's scope is unclear or it depends on a judgment call that should be made
  explicit.
- **Split any bead in the Too-big or Hard-ceiling size band.** Use the anti-pattern checklist in
  "The Size Window" to find the split line. Re-run the Marr audit on each child bead.
- **Demote any Trivial-band bead to a direct commit.** Note in the final report which work units
  were not filed as beads and why.

**Derive dependencies from the How.** One bead's How may reference another bead's output, such as
"consume the new auth middleware". Capture that as a dependency. The How is a source of dep edges,
not just a description.

Do not proceed to Step 3 until every bead passes the audit.

### Step 3: Present and Confirm

Show the user the complete list. Include the Why, How, Done when, type-specific sections, AND
Estimated size for each bead. The user can then verify the full audit, not just the metadata:

````markdown
## Proposed Issues

| # | Key | Title | Type | Priority | Labels | Size (files / LOC, band) | Depends On |
|---|---|---|---|---|---|---|---|
| 1 | add-auth-check | ... | task | P2 | backend,milestone-1 | 3 / 180, Target | - |
| 2 | fix-token-expiry | ... | bug | P2 | backend,milestone-1 | 4 / 250, Target | #1 |
| 3 | account-settings | ... | epic | P3 | frontend,milestone-2 | 2 / 90, Target | - |

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
**Existing records for this plan:** <native ID, key or "no key", status, proposed change; or "none">
**Proposed mapping for older records:** <proposed key to existing native ID; or "none">
**Keys replaced or retired:** <key, and the unit that replaces it; or "none">
````

**WAIT for user confirmation before proceeding.** The user may want to adjust titles, priorities,
dependencies, Why/How, or Done when content. Treat any edit as a re-audit: confirm the rewrite still
passes before moving on.

The confirmation covers only what the proposal showed. A mapping, or a change to an existing
record, that the proposal did not show still needs the user's approval.

### Step 4: Check bd and Its Create Flags

Run both commands before any write to the tracker:

```bash
bd list --limit 1
bd create --help
```

If `bd` is not found, or `bd list` fails, stop and inform the user.

The help text must list each of these flags: `--design`, `--notes`, `--acceptance`, `--parent`,
`--status`, and `--no-inherit-labels`. If one is missing, stop and tell the user to upgrade `bd`.
Do not fall back to `bd create` followed by `bd update`. That pair leaves a half-written record in
the tracker between the two calls.

### Step 5: Reconcile Each Key, Then Create Deferred Records

**Hold every new record until the whole graph passes Step 6b.** Create each record with the status
`deferred`, complete in its native fields, in one `bd create` call. `bd ready` leaves out a
deferred record, so nobody starts work on a graph that is still incomplete.

**Run one publisher per plan.** A publisher is a session that writes this plan's records. The
identity labels are recovery identifiers. They are not a uniqueness constraint and not a lock:
`bd` accepts a second record that carries the same pair. Two publishers can each create the same
unit.

#### Reconcile before every create

Do this for each work-unit key, in a first run and in every resumed run. Query the exact pair:

```bash
bd list --label plan:<plan-name> --label plan-unit:<key> --all --json
```

A repeated `--label` returns only the records that carry both labels. Keep `--all`. Without it,
`bd` leaves out a closed record, and finished work then looks like a missing unit.

| The pair query returns | Do this |
|---|---|
| One record | Reuse its native ID and read it with `bd show <id> --json`. Apply only the repairs the user approved, with `bd update`. Never reset a record that is in progress or closed |
| No record | Create the record, but only when no earlier create for this key has an unknown result |
| More than one record | Stop creation and stop release. Report every matching native ID, and wait for the user |

**A lost response is an unknown result, not proof of failure.** A create can succeed while the
session loses its output, for example when the session ends before it reads the ID. Query the pair
again before any retry. The pair still finds a record after its title changes.

A create failed for certain only when `bd` exited non-zero with an error. A failed create leaves no
record. One example is `Error: parent issue <id> not found`.

**An unresolved earlier create stops the run.** A create is unresolved when you cannot tell whether
it finished, for example because another session may still be running it. Stop creation and stop
release, then report the key and the operation. Do not retry blindly. A blind retry makes a second
record, and the pair query then returns two.

**Add a key to an older record only after the user approves the mapping.** Step 2 proposed a
mapping from each proposed unit to an existing native ID. For each approved line of that mapping,
run:

```bash
bd update <id> --add-label plan:<plan-name> --add-label plan-unit:<key>
```

Add both labels, because an older record may carry no `plan:` label, and the pair query finds only
a record that carries both. Then run the pair query for that key and follow the table above.
Create no replacement for an older record while its mapping waits for approval.

#### Create each record in one call

Create the epic before its children, because a child's `--parent` needs the epic's native ID.

**Write each section to its canonical destination.** The "Where each section goes" table in
[docs/bead-body-contract.md](../../docs/bead-body-contract.md) names the `bd` field for every
section. [ADR 0001](../../docs/adr/0001-native-tracker-fields-are-canonical.md) records why the
native field wins over the description body. That ADR also records that creation took two calls,
because `bd create` then had no flag for `design`, `notes`, or `acceptance_criteria`. `bd` has
those flags now. The ADR's rule still binds, and only the two-call mechanism is gone.

Writing everything into `-d` instead produces a bead that fails `bead-audit`'s structure check on
day one, which is the defect that ADR exists to fix.

**epic:** Success Criteria has no native slot, so it stays in the body. An epic carries no size
estimate and no `--acceptance`.

```bash
epic_id=$(bd create "<Title>" -t epic -p P2 -s deferred \
  -l "plan:<plan-name>,plan-unit:<key>,<labels>" --silent \
  -d "$(cat <<'EOF'
**Ask:** <one sentence, 20 words or fewer, saying what the bead wants done>

## Why (Computational)
<L1 content>

## Success Criteria
- <outcome-level indicator 1>
- <outcome-level indicator 2>
EOF
)" \
  --design "<L2 content>" \
  --notes "$(cat <<'EOF'
## Done when (Acceptance)
- <criterion 1>
- <criterion 2>
EOF
)")
```

**task or feature:**

```bash
id=$(bd create "<Title>" -t task -p P2 -s deferred \
  --parent "$epic_id" --no-inherit-labels \
  -l "plan:<plan-name>,plan-unit:<key>,<labels>" --silent \
  -d "$(cat <<'EOF'
**Ask:** <one sentence, 20 words or fewer, saying what the bead wants done>

## Why (Computational)
<L1 content>

## Estimated size
<files> files, <LOC> LOC, band: <band>. <one-sentence justification if Stretch>
EOF
)" \
  --design "<L2 content>" \
  --notes "$(cat <<'EOF'
## Done when (Acceptance)
- <criterion 1>
- <criterion 2>
EOF
)" \
  --acceptance "$(cat <<'EOF'
1. Given <precondition>, when <action>, then <observable result>.
2. ...
EOF
)")
```

**Pass `--no-inherit-labels` on every child, and list every approved label in its `-l`.** Without
that flag, a child created with `--parent` inherits every label of its parent, the parent's
`plan-unit:<key>` included. The pair query for the epic's key then returns the epic and the child.
The flag also stops the inherited `plan:<plan-name>`, so the child's `-l` must name it. A bead with
no parent takes neither `--parent` nor `--no-inherit-labels`.

**bug:** the same call with `-t bug`. Steps to Reproduce has no native slot, so it stays in the
body alongside Why and Estimated size. Pass this description in `-d`:

```markdown
**Ask:** <one sentence, 20 words or fewer, saying what the bead wants done>

## Why (Computational)
<L1 content>

## Steps to Reproduce
1. <step>
2. <step>

**Expected behavior:** <what should happen>
**Actual behavior:** <what currently happens>
**Environment / version:** <branch, OS, relevant config>

## Estimated size
<files> files, <LOC> LOC, band: <band>. <one-sentence justification if Stretch>
```

The flag is `--acceptance`; `bd` rejects `--acceptance-criteria` as an unknown flag.

Use the quoted `cat <<'EOF'` heredoc, not `printf`, for these values. Acceptance criteria and
Done-when lines routinely contain a literal `%`, for example "95% of requests return 200". `printf`
would read that as a format directive and silently corrupt the text. A quoted heredoc passes every
character through unchanged.

`--silent` prints only the native ID. Write each ID down beside its key as soon as the call
returns. If `bd create` exits non-zero, go to Step 5b. If the call returns no ID and no error, the
result is unknown: query the pair before any other command.

### Step 5b: Keep the Holds After a Known Failure

A known failure is a `bd` command that exited non-zero, or a readback that shows a wrong value. It
has three kinds: a failed create, a wrong or missing field, and a failed relationship. A
relationship is a `--parent` link or a `bd dep add` prerequisite.

After any known failure:

1. Stop. Run no further create and no release. Every new record stays `deferred`.
2. Report the failed operation with its exact error, the work-unit keys it touched, and every
   native ID known so far.
3. Ask the user how to proceed, and wait. The records are shared state, so the user owns the
   recovery decision.
4. Repair an existing record with `bd update <id>`, never with a second `bd create`. A second
   create makes a duplicate identity.
5. For a key that has no record, go back to "Reconcile before every create" in Step 5.

This command lists the records that are still held:

```bash
bd list --label plan:<plan-name> --status deferred --json
```

### Step 6: Add Prerequisites

Add each approved prerequisite while every new record is still deferred:

```bash
bd dep add <issue-id> <depends-on-id>
```

The first ID is the bead that waits. The second ID is the bead whose output it needs.

- **Each prerequisite names the output the dependent bead needs.** Keep that reason for the final
  report. A shared parent or a preferred order is not a prerequisite.
- **Add no blocking dependency from an epic to its own children.** `--parent` already records that
  the child belongs to the epic.
- **A refused dependency is a known failure.** `bd dep add` exits 1 on a missing ID. It also exits 1
  with `Error: adding dependency would create a cycle` when the dependency would close a cycle. Go
  to Step 5b.

### Step 6b: Read Back and Validate Before Any Release

Read every record of the graph from the tracker, the reused records included:

```bash
bd show <id> --json
bd list --parent <epic-id> --all --json
bd dep cycles
```

A report this skill formatted itself is not evidence. The tracker read is.

| Check | It passes when |
|---|---|
| Hold | Every new record has the `status` `deferred` |
| Native fields | `description`, `design`, `notes`, and `acceptance_criteria` each hold the sections the contract's "Where each section goes" table assigns. An epic has an empty `acceptance_criteria` |
| Identity | `labels` holds `plan:<plan-name>` and `plan-unit:<key>`, and the pair query returns exactly one record |
| Parent | `parent` is the approved parent, and the epic's list of children equals the approved children |
| Prerequisites | Each approved prerequisite is in the dependent record's `dependencies` with the `dependency_type` `blocks`. The prerequisite's record does not list the dependent. No unapproved `blocks` dependency exists |
| Cycles | `bd dep cycles` reports none |
| Coverage | Every plan acceptance criterion maps to a bead, and every bead maps to a criterion |

If one check fails, open no record. Treat it as a known failure and go to Step 5b.

### Step 7: Release, Then Report

**Release only after every check in Step 6b passes.** Release the epic before its children. Use
this guarded form, one ID for each call:

```bash
bd update <id> --if-status deferred -s open
```

`--if-status deferred` makes `bd` write only when the record is still deferred. A record that
somebody already started or closed is then never reset. Never release with `-s open` alone.

Release the records this run created. Release an existing deferred record only when the user
approved that change in Step 3.

**Exit 13 means the record was not deferred, and `bd` wrote nothing.** Either the record is
already released, or it is in progress or closed. Read it back with `bd show <id> --json` and
report its status. Never force it.

**A failure during release is a partial release, not a failed graph.** The content and the
relationships already passed Step 6b. Report which records are still deferred; the command at the
end of Step 5b lists them. On resume, change only the remaining approved statuses. Do not
re-create, re-wire, or re-validate content that passed, unless a readback shows it changed.

**The tracker export needs no step here.** `.beads/issues.jsonl` is a passive local copy of the
tracker, and git ignores it. The commit and push hooks refresh it. Every `bd` command reads the
database, not that file, and that covers `bd dep add`. This is the repository policy in
[AGENTS.md](../../AGENTS.md), under "The author never handles tracker plumbing".
[ADR 0010](../../docs/adr/0010-the-tracker-export-rides-the-commit-and-the-audit-log-is-untracked.md)
records that the export is a passive copy of the tracker.

- Run `bd export -o .beads/issues.jsonl` yourself, silently, only when a tool you are about to run
  needs the file current.
- Never ask the user to run the export. Report it only when it fails.
- Never edit `.beads/issues.jsonl` by hand.
- This skill grants no authority to sync a Dolt remote.

Then present the final report. Read every value in it from the tracker. Take the ready work from
`bd ready`, never from the order of the plan.

```markdown
## Published Records

| ID | Key | Title | Type | Priority | Parent | Status |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... |

## Dependencies

| Bead | Needs | Reason: the output it needs |
|---|---|---|
| ... | ... | ... |

## Coverage

| Plan acceptance criterion | Bead |
|---|---|
| ... | ... |

## Ready Work

- <each ID that `bd ready` returns for this plan, or "none">

## Holds

| ID | Key | Why it is still deferred |
|---|---|---|
| ... | ... | ... |

## Recovery

<Write this section only when a record is held or a result is unknown. Otherwise write "none".>

- Pair query to run first: `bd list --label plan:<plan-name> --label plan-unit:<key> --all --json`
- Stop conditions: more than one match, an unresolved create, or exit 13 on a release
- Next approved action for each held record: <the repair, or the remaining release>

## Trivial Work Units Not Filed

- <each unit rolled into a direct commit, and why; or "none">
```

### Step 7b (optional): Record the decomposition in the plan file

Append a one-line note to the plan's Status section: `Decomposed: <YYYY-MM-DD>, see bd <id-range>`.
This lets the next agent reading the plan know it has been decomposed without re-running the skill.
Skip if the plan file is read-only or if the user prefers tracking elsewhere.

## Critical Rules

**Always = invariants the agent must hold during execution. Quality Checklist = pre-completion
verification. Each fact lives in exactly one list.**

**Always:**

- Read the full plan before identifying work units
- Assign a type (`task`, `feature`, `bug`, or `epic`) to every bead before drafting its body
- Articulate Marr Level 1 (Why) and Level 2 (How) for every bead before presenting
- Draft Done when for every bead; each criterion must be verifiable by a second person without
  asking the author
- Draft `## Acceptance Criteria` for every task, feature, and bug bead; draft
  `## Steps to Reproduce` for every bug bead; draft `## Success Criteria` for every epic bead
- Estimate size (files + LOC + band) for every bead before presenting
- Run the full audit on every bead (Marr AND size AND type-specific section) and rewrite, split, or
  demote failures before the confirmation gate
- Present the complete issue list, including each bead's type, Why, How, Done when, type-specific
  sections, AND size estimate, and WAIT for user confirmation before creating
- Check `bd` and the `bd create` flags in Step 4 before any write to the tracker
- Write every section to its canonical destination per ADR 0001. Use native tracker fields where
  they exist, which on `bd` are `--design`, `--notes`, and `--acceptance`. Use the description body
  only for sections with no native field. Write them all in the one `bd create` call
- Give every proposed bead a work-unit key, and put `plan:<plan-name>` and `plan-unit:<key>` on
  the record in its create call
- Run one publisher per plan; the identity labels are not a lock
- Query the exact label pair with `--all` before every create, in a first run and in a resumed run
- Create every new record with the status `deferred`, the epic before its children, and pass
  `--no-inherit-labels` on every child
- Keep every new record deferred after a known failure, report it, and ask the user
- Release with `bd update <id> --if-status deferred -s open`, the epic before its children
- Make each issue self-contained with enough context to implement independently
- Keep the dependency graph shallow, prefer parallel tracks over deep chains

**Never:**

- Create a bead that fails the Marr audit (see "Audit checks" above for the canonical pass/fail
  criteria)
- Create a bead that fails the size audit (Too big, Hard ceiling, or Trivial-and-standalone; see
  "The Size Window")
- Create a bead that fails the type-specific section audit (missing `## Acceptance Criteria` for
  task/feature/bug, missing `## Steps to Reproduce` for bug, or missing `## Success Criteria` for
  epic)
- Create issues without user confirmation
- Create circular dependencies
- Fall back to `bd create` followed by `bd update` when a create flag is missing
- Retry a create whose result is unknown, or create or release while a pair query returns more than
  one record
- Match an existing record on its title alone, or add a key to an older record before the user
  approves the mapping
- Defer, reparent, close, or reopen an existing record without the user's approval
- Repair an existing record with a second `bd create`
- Add a blocking dependency from an epic to its own children
- Ask the user to run `bd export`, edit `.beads/issues.jsonl` by hand, or sync a Dolt remote

## Quality Checklist

Before reporting completion, verify:

- [ ] All milestones from the plan are covered by at least one issue
- [ ] Each issue has a clear, action-oriented title with no work-unit-bundling conjunction
- [ ] Every issue has an explicit type (`task`, `feature`, `bug`, or `epic`)
- [ ] Every issue carries Why, How, and Done when, each written to its canonical destination per ADR
  0001 (native field where one exists, description body otherwise)
- [ ] Every ADR in the plan's `## Decisions That Bind This Plan` section has its number and its rule
  in the `design` field of each bead it constrains, or was named at the confirmation gate as
  inherited by no bead
- [ ] Every record of the graph was read back with `bd show <id> --json` and passed every check in
  Step 6b before the first release
- [ ] Each `plan:<plan-name>` and `plan-unit:<key>` pair returns exactly one record
- [ ] Every `## Done when` section contains at least one condition a second person could verify
  independently
- [ ] Every task, feature, and bug bead includes `## Acceptance Criteria` with at least one
  testable, observable condition
- [ ] Every bug bead includes `## Steps to Reproduce` with numbered steps and expected vs. actual
  behavior
- [ ] Every epic bead includes `## Success Criteria` with at least one outcome-level indicator
  legible to a product stakeholder
- [ ] Every bead falls in the Target or Stretch size band (Stretch beads include a one-sentence
  justification)
- [ ] No bead is in the Too-big or Hard-ceiling band
- [ ] Trivial-band work units were demoted to direct commits and listed in the final report
- [ ] Every prerequisite reads back as `blocks` in the approved direction, and `bd dep cycles`
  reports none
- [ ] Longest dependency chain is at most 3 issues; if longer, a parallel split was missed
- [ ] Every record that is still deferred appears under Holds in the final report with its reason
- [ ] The final report lists native IDs with their keys, each dependency reason, coverage, ready
  work from `bd ready`, holds, and recovery instructions when a record is held or a result is
  unknown
- [ ] Execution order is logical and maximizes parallelism
