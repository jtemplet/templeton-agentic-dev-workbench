---
name: product-brief
description: "Write a product brief (PM-to-engineering handoff) with problem statement, user segments, success metrics, scope, acceptance criteria, and experiment tie-in"
---

# Product Brief

Write a product brief that serves as the handoff from product thinking to engineering implementation. This is the bridge between "what should we build?" (research/roadmap) and "how do we build it?" (feature plan/implementation).

A good brief answers: What problem are we solving, for whom, how will we know it worked, and what's in/out of scope?

## When to Use

- After a feature has been prioritized on the roadmap and needs scoping for engineering
- When a designer needs clear requirements to start design work
- Before writing a feature plan (the brief defines WHAT and WHY; the feature plan defines HOW)
- When stakeholders need to align on a feature's scope before committing resources

## When NOT to Use

- For features that are already well-understood and just need implementation (go straight to `feature-planner`)
- For exploratory work where the problem isn't yet clear (use `product-research` first)
- For bug fixes or technical improvements with no user-facing change

## Process

### Step 1: Define the Problem

Start with the user problem, not the solution. A brief without a clear problem statement will drift.

1. **Problem statement** - 2-3 sentences describing the pain point or opportunity. Specific, not abstract.
2. **Who has this problem** - which user segment(s) from your research?
3. **How do they solve it today** - current workaround or competing solution
4. **Why now** - what makes this the right time to solve it? (competitive pressure, user growth, strategic priority, data from an experiment)

**Cross-reference:** Link to the product research doc, competitive analysis, or roadmap item that surfaces this problem. If there's no prior PM work supporting this brief, flag that as a risk.

### Step 2: Define Success

Before describing the solution, define what success looks like:

1. **Primary success metric** - the single metric this feature is designed to move
   - Metric name and exact definition
   - Current baseline
   - Target (be specific: "+5% D7 retention" not "improve retention")
   - Measurement timeline (when will you evaluate?)

2. **Secondary metrics** - 2-3 supporting indicators

3. **Guardrails** - metrics that must not degrade

4. **Qualitative success signals** - what would you see in user feedback if this works? (e.g., "users mention sharing in app store reviews")

**Connect to experiment:** If this feature will be A/B tested, note the hypothesis here. If a brief already has an experiment doc in `docs/experiments/`, link to it.

### Step 3: Define the Solution (High-Level)

Describe the proposed solution at a level that engineers and designers can evaluate, without over-specifying implementation details.

1. **Core concept** - 1-2 paragraph description of what we're building
2. **User flow** - step-by-step description of the user experience (not wireframes; those are design's job)
3. **Key interactions** - what can the user do? What feedback do they get?
4. **Platform considerations** - iOS, web, or both? Any platform-specific behavior?

**Do NOT include:** database schemas, API designs, specific UI layouts, or technology choices. Those belong in the feature plan.

### Step 4: Define Scope

Clear scope boundaries prevent the most common failure mode: features that balloon during implementation.

**In scope:**

- Specific capabilities that will be delivered
- User segments that will be served
- Platforms that will be supported

**Out of scope:**

- Things that could be part of this feature but won't be (be specific)
- Future enhancements that are intentionally deferred (V2 thinking)
- Adjacent features that are related but separate

**MVP vs. Full Vision:**

If the full solution is large, define an MVP (Minimum Viable Product) that can ship independently:

- **MVP** - the smallest version that delivers user value and tests the key assumption
- **Full vision** - what this becomes if the MVP validates the hypothesis
- **What connects them** - what do you learn from MVP that informs the full build?

### Step 5: Acceptance Criteria

Define what "done" looks like. These are testable conditions that engineering and QA can verify.

Format: "Given [context], when [action], then [expected outcome]."

Examples:

- "Given a user on the free plan, when they tap 'Upgrade,' then they see pricing options within 200ms."
- "Given a user with 3+ saved items, when they open the app, then their saved items appear in recency order."

Include:

- **Happy path** - the primary flow works as described
- **Edge cases** - empty states, error states, boundary conditions
- **Performance** - any latency, throughput, or reliability requirements
- **Accessibility** - relevant a11y requirements for this feature

### Step 6: Risks and Open Questions

1. **Technical risks** - things that might be harder than expected
2. **Design risks** - UX patterns that might not work as imagined
3. **Business risks** - external factors that could make this less valuable
4. **Dependencies** - other teams, services, or features this relies on
5. **Open questions** - decisions that still need to be made (and who makes them)

### Step 7: Save the Document

Write to `docs/product/brief-<feature-slug>.md` (create directory if needed).

## Output Format

```markdown
# Product Brief: [Feature Name]

**Date:** [YYYY-MM-DD]
**Status:** Draft / In Review / Approved
**Author:** [PM name if known]
**Related docs:**

- Research: [link to product research doc]
- Competitive: [link to competitive analysis]
- Roadmap: [link to roadmap, which theme/item]
- Experiment: [link to experiment doc, if exists]

## Problem

### What's the problem?

[2-3 sentences. Specific, evidence-backed.]

### Who has it?

[User segment(s). Reference research if available.]

### How do they solve it today?

[Current workaround, competing solution, or "they don't and suffer."]

### Why now?

[What makes this the right time: data, competitive pressure, strategic priority]

## Success Metrics

### Primary Metric

- **[Metric name]:** [Exact definition]
- **Baseline:** [Current value]
- **Target:** [Specific goal]
- **Evaluate by:** [Date or timeframe]

### Secondary Metrics

- **[Metric]** - [Definition, expected direction]

### Guardrails

- **[Metric]** - [Must not degrade below X]

### Qualitative Signals

- [What success looks like in user behavior/feedback]

## Solution

### Core Concept

[1-2 paragraphs describing the solution at a high level]

### User Flow

1. [Step 1: User does X]
2. [Step 2: System responds with Y]
3. [Step 3: User sees Z]

### Platform

- [ ] iOS
- [ ] Web
- [ ] Both

[Platform-specific notes if relevant]

## Scope

### In Scope (MVP)

- [Specific deliverable 1]
- [Specific deliverable 2]

### In Scope (Full Vision, post-MVP)

- [Enhancement 1, contingent on MVP validation]
- [Enhancement 2]

### Out of Scope

- [Explicitly excluded 1] - [why]
- [Explicitly excluded 2] - [why]

### MVP Validation Gate

[What must be true after MVP ships to justify building the full vision? Specific metrics or signals.]

## Acceptance Criteria

### Happy Path

- Given [context], when [action], then [outcome]
- ...

### Edge Cases

- Given [empty state / error / boundary], when [action], then [outcome]
- ...

### Performance

- [Latency, throughput, or reliability requirements]

### Accessibility

- [Relevant a11y requirements]

## Risks & Dependencies

### Risks

| Risk | Type | Impact | Mitigation |
|---|---|---|---|
| ... | Technical/Design/Business | High/Med/Low | ... |

### Dependencies

- [Team/service/feature this relies on]

### Open Questions

| Question | Owner | Deadline |
|---|---|---|
| ... | [Who decides] | [When] |

## Next Steps

1. [Design: create wireframes/prototype]
2. [Engineering: write feature plan]
3. [Data: instrument metrics]
4. [PM: resolve open questions by X date]
```

## Key Principles

- **Problem before solution.** If you can't articulate the problem clearly, you're not ready to write a brief. Go back to research.
- **Metrics before scope.** Define what success looks like before defining what you'll build. This prevents building things that "feel done" but don't move the needle.
- **MVP is not "half-assed V1."** MVP means the smallest thing that delivers user value AND tests your riskiest assumption. It must be genuinely useful on its own.
- **Scope is what you say NO to.** The "Out of Scope" section is as important as "In Scope." If your out-of-scope list is empty, your scope isn't defined.
- **Acceptance criteria are testable.** "Users should find it intuitive" is not testable. "Given X, when Y, then Z" is testable.
- **Trace everything back.** A brief without links to research, competitive analysis, or user signal is just opinion with formatting.
- **Open questions are fine.** A brief with genuine open questions is more honest than one with premature decisions. Just assign an owner and deadline to each.
- **This is not a spec.** Don't prescribe implementation details, database schemas, or API contracts. Engineers own those decisions. You own the problem, the success criteria, and the scope.
