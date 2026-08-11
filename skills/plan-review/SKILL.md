---
name: plan-review
description: "Fresh-eyes review of a feature plan: acceptance-criteria gate, codebase grounding, 7-dimension evaluation with MECE audit, and a verdict"
---

# Plan Review

Evaluate a feature implementation plan across 7 dimensions, ground its claims in the real codebase, run a dedicated MECE audit, identify gaps and overlaps, and provide a clear verdict.

**Report-only.** This review never edits the plan file. When a required section is missing (most often Acceptance Criteria or Testing Strategy), draft it in the report, paste-ready, and offer to apply it; apply only when the user says so.

## Evaluation Dimensions

Rate each dimension GREEN / YELLOW / RED. Use a comma, semicolon, or parentheses inside justifications (no em-dashes or en-dashes).

**Single bucket per finding.** Each issue is scored under exactly one dimension. When a finding could fit two, route it to MECE; the other dimensions own *presence and quality*, MECE owns *coverage and pairing*.

| Dimension | What it owns | GREEN | YELLOW | RED |
|---|---|---|---|---|
| **Completeness** | Every canonical section is present and non-empty (see Canonical Sections) | All canonical sections filled or explicitly N/A, no TBDs | 1-2 sections vague or thin | A canonical section is missing or empty, including one the plan never declared |
| **Feasibility** | Technical approach is sound and grounded in the real codebase (see Codebase Grounding) | Approach is proven; every named file, module, and API verified to exist | Some unknowns but manageable, or 1-2 claims unverifiable | Relies on unproven tech, or the approach hinges on code that does not exist as described |
| **Scope** | In-scope and out-of-scope are both declared and right-sized | Both lists present, boundaries crisp, sized for the team | Boundaries declared but slightly over-ambitious or under-specified | Scope unbounded, or out-of-scope list missing entirely |
| **Risks** | Risks are identified | At least the obvious risks are named | Risk list is thin or surface-level | No risk analysis at all |
| **Dependencies** | Dependencies are identified and resolvable | All deps named and known to be available | Some deps unclear or potentially blocking | Critical deps missing or unresolvable |
| **MECE** | Coverage and pairing across the plan (see MECE Audit) | No overlaps; every required pairing covered | 1-2 minor overlaps or gaps, fixable without restructuring | Any major MECE finding (orphan goal, orphan stage, missing rollout/migration, conflicting ownership) |
| **Actionability** | A developer could start, and acceptance criteria prove when the work is done | Acceptance criteria present and testable; each milestone or stage has verifiable completion conditions | Needs 1-2 clarifications, or 1-2 stages lack verifiable completion conditions, or some criteria are subjective | Too vague to act on, or the plan has no acceptance criteria (see the Acceptance Criteria gate) |

## Canonical Sections

Completeness is judged against the `/plan-feature` template, not against whatever headings the plan happens to declare. A plan cannot score GREEN by silently omitting a section. The canonical set:

Summary, Motivation, Scope (In and Out), Technical Approach, Implementation Milestones, Acceptance Criteria, Risks & Mitigations, Dependencies, Testing Strategy, Open Questions.

Data Model and API/Interface (subsections of Technical Approach) may be absent when genuinely not applicable. Every other section must be present, or carry an explicit "N/A because ..." line. Hold plans not authored by `/plan-feature` to the same set, mapping their headings by substance rather than name.

**Draft, don't instruct.** When Acceptance Criteria or Testing Strategy is missing or empty, the fix in Recommended Changes must be a paste-ready draft (criteria derived from the plan's goals and scope; a test plan naming test levels and key scenarios), never just "add acceptance criteria" or "add tests".

## Codebase Grounding

Do not review the plan from its own text alone. Before scoring, verify the plan's claims against the repository:

- **Existence check:** every file path, module, class, and API endpoint the plan names must exist. Use Glob and Grep; do not deep-read.
- **Pattern check:** when the plan says "extend the existing X" or "follow the Y pattern", confirm X and Y are real and roughly match the plan's description of them.
- **Stack check:** confirm the frameworks, libraries, and tools the plan relies on are actually in the project (manifest, lockfile, or config), not assumed.
- **Behavior check:** when the plan asserts how existing code behaves (a format, a scope, a side effect, where something writes or appends), verify the specific code, not just that the symbol exists. Existence checks pass trivially; the wrong-number-that-looks-right failures live in behavioral claims. Apply this only to claims the design depends on; skip incidental color.

Findings route to Feasibility: 1-2 unverifiable claims are YELLOW; an approach that hinges on code that does not exist or behave as described is RED. Keep it bounded: grounding verifies existence, rough shape, and load-bearing behavior; it is not a design review of the referenced code.

## The Acceptance Criteria Gate

Run this before scoring anything else. A plan without acceptance criteria cannot be reviewed for actionability, cannot be decomposed into beads, and cannot be proven done.

**Where to look.** Criteria count toward the gate wherever they appear: under `## Acceptance Criteria`, `Done when`, `Success Criteria`, `Definition of Done`, as per-milestone completion conditions in the work-breakdown table, or in a `Tests` / test-plan section whose assertions are objectively pass/fail. Substance beats formatting; criteria in the right shape under a non-canonical heading pass the gate (note the naming as a minor finding).

**The gate fails when any of these hold:**

- No acceptance criteria exist anywhere in the plan, under any heading.
- Criteria exist but are all subjective: "works well", "is intuitive", "is fast", "users are happy", "tests pass" without naming which.
- Criteria restate the scope list rather than stating an observable outcome ("build the auth middleware" is a task, not a criterion).
- A second person could not decide pass/fail on a criterion without asking the author.

**Consequence of a failed gate:** Actionability is RED, which routes to a **Major Rework** verdict. Say so explicitly in the verdict summary and put the missing criteria at the top of Recommended Changes. Draft them yourself: derive 3-6 testable criteria from the plan's goals and scope, in Given/When/Then or numbered-assertion form, paste-ready, then offer to apply them to the plan file (do not edit without the user's go-ahead).

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
- **Stages vs. feature whole**: If every stage shipped, would the feature be done? Common omissions: rollout/feature flags, data migration, test coverage, observability, docs, deprecation of replaced code, rollback path.
- **In-scope + Out-of-scope**: Together cover the obvious adjacent concerns. Common blind spots: error paths, empty states, permissions/authorization, internationalization, accessibility, performance budgets, telemetry.
- **Acceptance criteria vs. goals**: Each goal has at least one acceptance criterion that proves it.
- **Risks vs. mitigations**: Every named risk has a stated mitigation or an explicit "accepted" note.
- **Dependencies vs. stages**: Every external dependency is consumed by a named stage; no orphan deps and no stages with unstated deps.
- **Roles vs. stages** (only when the plan assigns owners): every stage has a named owner and no owner has no work. A plan with no ownership model (e.g., solo work) skips this pairing; do not flag the absence of owners as a gap.
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

## Open Questions

An Open Questions section is healthy; unresolved decisions the work depends on are not. Score them under Dependencies:

- An open question that blocks the first milestone, or that an acceptance criterion depends on, is a Dependencies YELLOW.
- An open question the whole approach hinges on (the plan cannot proceed on either answer without restructuring) is a Dependencies RED.
- Questions that only affect later milestones or post-launch decisions are fine; note them, do not score them.

## Process

1. **Read the plan thoroughly**: understand the full scope and intent.
2. **Ground the plan in the codebase**: run the Codebase Grounding checks (existence, pattern, stack); route findings to Feasibility.
3. **Run the Acceptance Criteria gate**: locate the criteria, judge them testable or not, and record the result. This sets the Actionability floor before any other scoring.
4. **Score each dimension**: assign GREEN/YELLOW/RED with a 1-sentence justification.
5. **Run the MECE audit**: list every overlap and gap explicitly using the categories above; classify each as major or minor.
6. **Identify other gaps**: non-MECE gaps (e.g., vague language, missing rationale), each with a suggestion for how to fill it.
7. **Note strengths**: what the plan does well (2-3 items).
8. **Produce recommended changes**: a prioritized checklist of what to fix before implementation; a failed acceptance-criteria gate goes first, then MECE majors. Missing Acceptance Criteria or Testing Strategy sections appear here as paste-ready drafts (see Draft, don't instruct).
9. **Render verdict**: Ready / Needs Revision / Major Rework. On Needs Revision or Major Rework, the summary must state whether milestone 1 is blocked or can start while the plan is revised.
10. **Hand off**: on Ready, point to `/plan-to-beads <path>` as the next step. Otherwise, offer to apply the Recommended Changes (including any drafted sections) to the plan file and re-review; do not edit unprompted. When applying, follow the plan's own revision conventions (dated revision notes, changelog blocks) and cite the review as the source of the changes.

## Re-reviews

When the plan records a prior review's changes (a revision note, a changelog block):

- **Verify the revision note against the body.** Each change the note claims must actually appear; a claimed-but-absent fix is a Completeness finding.
- **Do not re-litigate recorded decisions.** A decision the plan states with rationale and evidence (measurements, a rejected-alternatives entry) is settled; review what the decision might have missed, not whether you would have made it.

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

- [ ] [Highest priority fix: a failed acceptance-criteria gate first, then MECE majors.
      A missing Acceptance Criteria or Testing Strategy section appears here as a
      paste-ready draft, not an instruction to write one.]
- [ ] ...

### Verdict: [Ready / Needs Revision / Major Rework]

[1-2 sentence summary. On Needs Revision or Major Rework, state explicitly whether
milestone 1 is blocked or can start while the plan is revised.]

### Next Step

[Ready: "Run /plan-to-beads <path>". Otherwise: offer to apply the Recommended Changes,
including any drafted sections, to the plan file and re-review.]
```

## Verdict Criteria

Apply these rules top-down; the first that matches wins:

- **Major Rework**: any dimension is RED.
- **Needs Revision**: two or more dimensions are YELLOW, or any Recommended Change must land before milestone 1 can start.
- **Ready**: everything else (no RED, at most one YELLOW, nothing blocking milestone 1). A developer can start.

The MECE dimension's bands already encode major-vs-minor severity, so a major MECE finding will surface here as MECE = RED and route through "any dimension is RED" above.

## When to Use

- After writing a feature plan, before starting implementation
- When reviewing someone else's plan for quality
- As a gate before decomposing a plan into issues

## When NOT to Use

- On plans that are intentionally lightweight (spikes, experiments)
- When the plan is already being implemented and it's too late to revise

## Key Principles

- **Single bucket per finding**: each issue is scored under exactly one dimension. When it could fit two (most often Completeness/Scope/Risks/Dependencies vs. MECE), route to MECE. The other dimensions own *presence and quality*; MECE owns *coverage and pairing*.
- **Ground before judging**: verify the plan's claims against the repository before scoring Feasibility; a plan reviewed only from its own text can be internally consistent and still wrong.
- **Every gap must come with a suggestion**; don't just say "missing X", say "add X by doing Y". For missing Acceptance Criteria or Testing Strategy, the suggestion is a paste-ready draft.
- **Focus on what would make implementation fail**, not style or formatting nits.
- **Respect the plan's intent**; review what it's trying to do, not what you'd do differently.
- **Be specific**: "the API section is vague" is useless; "the API section doesn't specify the auth mechanism" is useful.
- **MECE first, prose second**: a clean partition of work catches more downstream pain than tightening any single sentence. When in doubt, fix the overlap or gap before polishing the wording.
