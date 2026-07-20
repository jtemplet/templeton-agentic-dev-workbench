---
name: plan-review
description: "Fresh-eyes review of a feature plan for completeness, feasibility, scope risks, MECE adherence, and actionability"
---

# Plan Review

Evaluate a feature implementation plan across 7 dimensions, run a dedicated MECE audit, identify gaps and overlaps, and provide a clear verdict.

## Evaluation Dimensions

Rate each dimension GREEN / YELLOW / RED. Use a comma, semicolon, or parentheses inside justifications (no em-dashes or en-dashes).

**Single bucket per finding.** Each issue is scored under exactly one dimension. When a finding could fit two, route it to MECE; the other dimensions own *presence and quality*, MECE owns *coverage and pairing*.

| Dimension | What it owns | GREEN | YELLOW | RED |
|---|---|---|---|---|
| **Completeness** | Every named section is present and non-empty | All declared sections filled, no TBDs | 1-2 sections vague or thin | A declared section is empty or missing entirely |
| **Feasibility** | Technical approach is sound | Approach is proven and well-understood | Some unknowns but manageable | Relies on unproven tech or unclear how it works |
| **Scope** | In-scope and out-of-scope are both declared and right-sized | Both lists present, boundaries crisp, sized for the team | Boundaries declared but slightly over-ambitious or under-specified | Scope unbounded, or out-of-scope list missing entirely |
| **Risks** | Risks are identified | At least the obvious risks are named | Risk list is thin or surface-level | No risk analysis at all |
| **Dependencies** | Dependencies are identified and resolvable | All deps named and known to be available | Some deps unclear or potentially blocking | Critical deps missing or unresolvable |
| **MECE** | Coverage and pairing across the plan (see MECE Audit) | No overlaps; every required pairing covered | 1-2 minor overlaps or gaps, fixable without restructuring | Any major MECE finding (orphan goal, orphan stage, missing rollout/migration, conflicting ownership) |
| **Actionability** | A developer could start, and acceptance criteria prove when the work is done | Acceptance criteria present and testable; each milestone or stage has verifiable completion conditions | Needs 1-2 clarifications, or 1-2 stages lack verifiable completion conditions, or some criteria are subjective | Too vague to act on, or the plan has no acceptance criteria (see the Acceptance Criteria gate) |

## The Acceptance Criteria Gate

Run this before scoring anything else. A plan without acceptance criteria cannot be reviewed for actionability, cannot be decomposed into beads, and cannot be proven done.

**Where to look.** Criteria count toward the gate wherever they appear: under `## Acceptance Criteria`, `Done when`, `Success Criteria`, `Definition of Done`, or as per-milestone completion conditions in the work-breakdown table. Substance beats formatting; criteria in the right shape under a non-canonical heading pass the gate (note the naming as a minor finding).

**The gate fails when any of these hold:**

- No acceptance criteria exist anywhere in the plan, under any heading.
- Criteria exist but are all subjective: "works well", "is intuitive", "is fast", "users are happy", "tests pass" without naming which.
- Criteria restate the scope list rather than stating an observable outcome ("build the auth middleware" is a task, not a criterion).
- A second person could not decide pass/fail on a criterion without asking the author.

**Consequence of a failed gate:** Actionability is RED, which routes to a **Major Rework** verdict. Say so explicitly in the verdict summary and put "add acceptance criteria" at the top of Recommended Changes with a concrete starting draft, not just the instruction to add them.

**Partial coverage is not a gate failure.** If criteria exist and are testable but do not cover every goal or scope item, the gate PASSES. Coverage belongs to MECE ("Acceptance criteria vs. goals"), so route the uncovered goals there as gaps and leave Actionability scored on presence and quality alone. Scoring it in both places would double-count one finding and violate Single bucket per finding.

## MECE Audit

MECE = **Mutually Exclusive, Collectively Exhaustive**. Run these checks explicitly; do not infer them from the other dimensions.

**No-stages adapter:** if the plan has no explicit stages, treat the top-level work breakdown (milestones, components, or task list) as the stages analog throughout this audit.

### Mutually Exclusive (no overlap or redundancy)

For each pair below, look for two items that restate the same intent or split responsibility ambiguously:

- **Goals**: Two goals describing the same outcome? A goal that is actually a sub-goal of another?
- **Stages / phases**: Does any stage repeat work from another? Are sequencing boundaries crisp (Stage N finishes a thing; Stage N+1 doesn't redo it)?
- **Files / modules affected**: When multiple stages touch the same file, is the responsibility split unambiguously (different functions, different change types)?
- **In-scope items**: Listed only once, no duplicate framings under different headings?
- **Requirements / acceptance criteria**: Each criterion a distinct, independently verifiable check?
- **Risks**: Same underlying risk stated twice in different language?

### Collectively Exhaustive (no gaps)

For each pairing below, check that the union covers the whole problem space:

- **Goals vs. work breakdown**: Every goal has at least one stage that owns delivering it. Every stage maps back to at least one goal.
- **Stages vs. feature whole**: If every stage shipped, would the feature be done? Common omissions: rollout/feature flags, data migration, observability, docs, deprecation of replaced code, rollback path.
- **In-scope + Out-of-scope**: Together cover the obvious adjacent concerns. Common blind spots: error paths, empty states, permissions/authorization, internationalization, accessibility, performance budgets, telemetry.
- **Acceptance criteria vs. goals**: Each goal has at least one acceptance criterion that proves it.
- **Risks vs. mitigations**: Every named risk has a stated mitigation or an explicit "accepted" note.
- **Dependencies vs. stages**: Every external dependency is consumed by a named stage; no orphan deps and no stages with unstated deps.
- **Roles vs. stages**: Every stage has a named owner (person or role); no orphan owners with no work.
- **Acceptance criteria vs. success metrics**: Every success metric has at least one acceptance criterion that proves it, or an explicit note that the metric is measured post-launch only.

### MECE severity

A MECE finding is **major** (counts toward RED) when:

- A goal has no owning work, or a stage has no owning goal.
- An obvious feature-completeness category is entirely missing (e.g., no rollout plan for a user-facing change, no migration step for a schema change).
- Two stages claim conflicting ownership of the same change.

A MECE finding is **minor** (counts toward YELLOW) when:

- Two items partially overlap but can be merged or reworded in one edit.
- A small adjacent concern is missing but easy to add (e.g., a single missing acceptance criterion).

**Tiebreaker:** when a finding fits neither list cleanly, default to minor unless it would block shipping.

## Process

1. **Read the plan thoroughly**: understand the full scope and intent.
2. **Run the Acceptance Criteria gate**: locate the criteria, judge them testable or not, and record the result. This sets the Actionability floor before any other scoring.
3. **Score each dimension**: assign GREEN/YELLOW/RED with a 1-sentence justification.
4. **Run the MECE audit**: list every overlap and gap explicitly using the categories above; classify each as major or minor.
5. **Identify other gaps**: non-MECE gaps (e.g., vague language, missing rationale), each with a suggestion for how to fill it.
6. **Note strengths**: what the plan does well (2-3 items).
7. **Produce recommended changes**: a prioritized checklist of what to fix before implementation; a failed acceptance-criteria gate goes first, then MECE majors.
8. **Render verdict**: Ready / Needs Revision / Major Rework.

## Output Format

```markdown
## Plan Review: [Plan Title]

### Acceptance Criteria Gate: [PASS / FAIL]

[Where the criteria live and whether they are testable. On FAIL, name which of the four
failure conditions triggered it. On PASS with partial coverage, name the uncovered goals.]

### Dimension Scores

| Dimension | Rating | Justification |
|---|---|---|
| Completeness | GREEN/YELLOW/RED | ... |
| Feasibility | GREEN/YELLOW/RED | ... |
| Scope | GREEN/YELLOW/RED | ... |
| Risks | GREEN/YELLOW/RED | ... |
| Dependencies | GREEN/YELLOW/RED | ... |
| MECE | GREEN/YELLOW/RED | ... |
| Actionability | GREEN/YELLOW/RED | ... |

### MECE Findings

**Overlaps (not Mutually Exclusive):**

- **[Category]**: [Item A] and [Item B] both [describe overlap]. Severity: major/minor. Suggest: [merge / split / clarify boundary].
- (or: "None found.")

**Gaps (not Collectively Exhaustive):**

- **[Category]**: [What is missing] is not covered. Severity: major/minor. Suggest: [specific item to add].
- (or: "None found.")

### Other Gaps

1. **[Gap]**: [Suggestion to fill it]
2. ...

### Strengths

- ...

### Recommended Changes

- [ ] [Highest priority fix: a failed acceptance-criteria gate first, then MECE majors]
- [ ] ...

### Verdict: [Ready / Needs Revision / Major Rework]

[1-2 sentence summary of overall assessment]
```

## Verdict Criteria

- **Ready**: All GREEN, or mix of GREEN/YELLOW with no blockers. A developer can start.
- **Needs Revision**: One or more YELLOW with gaps that could cause problems. Fixable in an hour or two.
- **Major Rework**: Any RED, or multiple YELLOW with compounding risk. Plan needs significant changes.

The MECE dimension's bands already encode major-vs-minor severity, so a major MECE finding will surface here as MECE = RED and route through "Any RED" above.

## When to Use

- After writing a feature plan, before starting implementation
- When reviewing someone else's plan for quality
- As a gate before decomposing a plan into issues

## When NOT to Use

- On plans that are intentionally lightweight (spikes, experiments)
- When the plan is already being implemented and it's too late to revise

## Key Principles

- **Single bucket per finding**: each issue is scored under exactly one dimension. When it could fit two (most often Completeness/Scope/Risks/Dependencies vs. MECE), route to MECE. The other dimensions own *presence and quality*; MECE owns *coverage and pairing*.
- **Every gap must come with a suggestion**; don't just say "missing X", say "add X by doing Y".
- **Focus on what would make implementation fail**, not style or formatting nits.
- **Respect the plan's intent**; review what it's trying to do, not what you'd do differently.
- **Be specific**: "the API section is vague" is useless; "the API section doesn't specify the auth mechanism" is useful.
- **MECE first, prose second**: a clean partition of work catches more downstream pain than tightening any single sentence. When in doubt, fix the overlap or gap before polishing the wording.
