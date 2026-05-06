---
name: product-roadmap
description: "Build a prioritized product roadmap with themes, capacity modeling, bet classification, sequencing, dependencies, and clear rationale for what to build when"
---

# Product Roadmap

Build a prioritized, time-horizoned product roadmap for a software product. The output is a strategic document that aligns engineering, design, and stakeholders on what to build and in what order.

## When to Use

- At the start of a quarter or planning cycle
- After product research or competitive analysis has identified opportunities
- When stakeholders disagree about priorities and you need a structured framework
- When you need to communicate "what's next" to the team

## When NOT to Use

- When you don't have enough input to prioritize (do `product-research` or `competitive-analysis` first)
- For sprint-level task breakdown (use `plan-to-beads` for that)
- When priorities are already decided and you just need to plan implementation (use `feature-planner`)

## Process

### Step 1: Gather and Cross-Reference Inputs

A roadmap synthesizes multiple inputs. Gather what's available:

1. **Product research** - ranked opportunities, JTBD analysis (check `docs/product/research-*`)
2. **Competitive analysis** - gaps, threats, positioning (check `docs/product/competitive-analysis-*`)
3. **Product briefs** - already-scoped features waiting for prioritization (check `docs/product/brief-*`)
4. **Business goals** - revenue targets, growth goals, strategic bets
5. **Technical constraints** - debt that blocks features, platform migrations, infrastructure needs
6. **Existing commitments** - features already promised, partnerships, compliance deadlines
7. **User feedback** - top requests, pain points, churn reasons
8. **Experiment results** - what did recent A/B tests reveal? (check `docs/experiments/`)

**Explicitly link inputs to outputs.** Every item on the roadmap should trace back to an input. If an item has no supporting input, flag it as opinion-driven and ask if that's intentional.

If critical inputs are missing, note them as assumptions and flag them.

### Step 2: Model Capacity

Before prioritizing, understand what you can actually build. A roadmap that ignores capacity is fiction.

**Capacity inputs:**

- **Team size** - how many engineers, designers, and PMs are available?
- **Effective weeks per cycle** - subtract holidays, on-call, maintenance, support burden
- **Typical throughput** - how many S/M/L items did the team ship last cycle? (If unknown, estimate conservatively.)
- **Fixed costs** - what % of capacity goes to maintenance, bugs, on-call, tech debt? (Typical: 20-30%)

**Capacity model:**

```text
Available capacity = (team size) x (effective weeks) x (1 - fixed cost %)
```

Express capacity in "engineering weeks" or a similar unit. Then sanity-check: does the roadmap fit within capacity? If not, cut scope (never extend timelines silently).

**If capacity is unknown:** Ask the user. If they can't provide it, make an explicit assumption ("Assuming a team of 3 engineers, 1 designer, with 70% available capacity after maintenance") and note that the roadmap must be re-evaluated if capacity differs.

### Step 3: Define Themes

Group opportunities and features into 3-5 strategic themes. A theme is a bet about where to invest.

Each theme should answer: "If we invest here, what do we believe will happen?"

**Theme format:**

- **Name** - short, memorable (e.g., "Activation," "Creator Tools," "Enterprise Ready")
- **Thesis** - 1-2 sentences on why this theme matters now
- **Success metric** - how you'll know the bet is paying off (specific, measurable)
- **Investment level** - what % of capacity goes here (themes must sum to ~100%)
- **Bet type** - (see below)

**Bet classification:**

| Bet Type | Description | Expected Outcome | Risk Tolerance |
|---|---|---|---|
| **Table-stakes execution** | Features users expect; competitive parity | Prevent churn, maintain position | Low (must ship, must work) |
| **Optimization** | Improve existing flows based on data | Measurable metric lift (5-20%) | Low-Medium (A/B testable) |
| **Strategic bet** | New capability or market expansion | Step-change growth (if it works) | High (may fail, that's OK) |
| **Exploration** | Validate an assumption before committing | Learning, not shipping | Highest (most will be killed) |

A healthy roadmap has a mix. All table-stakes = no growth. All strategic bets = too risky. Typical distribution:

- 40% table-stakes + optimization
- 40% strategic bets
- 20% exploration

### Step 4: Prioritize Within Themes

For each theme, rank features using ICE:

| Factor | Definition |
|---|---|
| **Impact** | How much will this move the theme's success metric? (1-10) |
| **Confidence** | How sure are you about the impact? (1-10). Low if no user signal or untested assumption. |
| **Ease** | How easy is this to build? (1-10, where 10 = trivial). Factor in technical risk. |

```text
ICE Score = Impact x Confidence x Ease
```

**Scoring discipline:**

- Don't mix themes when ranking. A theme's internal priority is separate from how much capacity it gets.
- Be honest about Confidence. If you haven't validated the assumption, Confidence is 3-5 at best.
- Ease should account for hidden complexity (integrations, migrations, cross-platform).
- If two items have similar ICE scores, prefer the one with higher Confidence (less risky).

### Step 5: Sequence into Time Horizons

Map features across three horizons:

| Horizon | Timeframe | Commitment Level | Detail Level |
|---|---|---|---|
| **Now** | Next 4-6 weeks | Committed, in progress or next up | Fully scoped, assigned |
| **Next** | 6-12 weeks out | High confidence, sequenced | Scoped, not yet staffed |
| **Later** | 12+ weeks out | Directional, subject to change | Concept-level, will re-evaluate |

Sequencing rules:

1. **Dependencies first.** If B requires A, A goes in an earlier horizon.
2. **Quick wins early.** High-ICE, low-effort items go in "Now" to build momentum and validate themes.
3. **De-risk big bets.** If a "Next" item is high-impact but low-confidence, put a validation step in "Now" (prototype, experiment, user test). Never commit to a large strategic bet without validation.
4. **Don't overcommit "Now."** Teams ship 60-70% of what they plan. If capacity model says you can do 5 items, put 3-4 in "Now."
5. **"Later" is a parking lot, not a promise.** Items here will be re-evaluated next cycle.
6. **Exploration items go in "Now" or not at all.** Exploration is about learning quickly; deferring exploration defeats its purpose.

**Capacity check:** After sequencing, verify that "Now" fits within available capacity. If it doesn't, move items to "Next" (don't just assume the team will work faster).

### Step 6: Identify Dependencies and Risks

For each "Now" and "Next" item:

- **Dependencies** - what must happen first? (other features, infrastructure, design, data pipeline, external partner)
- **Risks** - what could derail this? (technical uncertainty, resource constraints, changing requirements, external dependency)
- **Mitigation** - how will you manage the risk?
- **Confidence level** - how likely is this to ship on time? (High/Medium/Low)

Draw a dependency graph for anything non-trivial:

```text
[Infrastructure: Event Pipeline] --> [Feature: Experiment Framework] --> [Feature: A/B Test Dashboard]
```

### Step 7: Define What You're NOT Doing

Equally important: what are you explicitly choosing not to build this cycle, and why?

For each deferred item, state:

- **What** was requested or considered
- **Why not now** (low impact, low confidence, wrong timing, doesn't fit themes, insufficient capacity)
- **What would change this** (what signal or condition would move this to "Now" in a future cycle)

This prevents scope creep and gives the team permission to say no to requests that don't fit the roadmap.

### Step 8: Define Success Criteria and Review Cadence

A roadmap without accountability is a wish list. Define:

1. **Per-theme success metrics** with targets and baselines
2. **Review cadence** - when will you revisit this roadmap? (Recommend: lightweight check every 2 weeks, full re-evaluation every 6-8 weeks)
3. **Kill criteria** - what would cause you to abandon a theme mid-cycle? (e.g., "If Activation experiments show <2% lift after 3 tests, pivot capacity to Retention")

### Step 9: Save the Document

Write to `docs/product/roadmap-<date>.md` (create directory if needed).

## Output Format

```markdown
# Product Roadmap

**Date:** [YYYY-MM-DD]
**Product:** [Product name]
**Planning horizon:** [e.g., Q3 2026]
**Inputs:** [What informed this roadmap, with links to docs/product/ files]
**Team capacity:** [X engineering weeks available this cycle]

## Strategic Context

[2-3 paragraphs: current product state, key metrics, what's working, what's not, what changed since last roadmap]

## Capacity Model

| Resource | Available | Fixed Costs | Net Capacity |
|---|---|---|---|
| Engineering | [X weeks] | [Y% maintenance/support] | [Z weeks] |
| Design | [X weeks] | [Y%] | [Z weeks] |

**Implication:** [What capacity means for scope, e.g., "We can ship ~4 medium features or 2 large + 2 small"]

## Themes

### Theme 1: [Name]

- **Thesis:** [Why this matters now]
- **Bet type:** [Table-stakes / Optimization / Strategic / Exploration]
- **Success metric:** [Specific, measurable, with baseline and target]
- **Investment:** [% of capacity, ~X engineering weeks]
- **Kill criteria:** [What would cause you to abandon this theme]

### Theme 2: [Name]

[Same structure]

[3-5 themes total, must sum to ~100% capacity]

## Roadmap

### Now (Next 4-6 weeks)

| Feature | Theme | Bet Type | ICE | Effort | Owner | Status | Confidence |
|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | S/M/L | [if known] | Planned/In Progress | H/M/L |

**Capacity check:** [X of Y available weeks allocated. Buffer: Z weeks.]

### Next (6-12 weeks)

| Feature | Theme | Bet Type | ICE | Effort | Dependencies | Confidence |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | S/M/L | ... | H/M/L |

### Later (12+ weeks, directional)

| Feature | Theme | Rationale for Deferral | What Would Promote It |
|---|---|---|---|
| ... | ... | [Why not now] | [Signal that would change this] |

## Dependencies

```

[Feature A] --> [Feature B] --> [Feature C]
[Infrastructure X] --> [Feature D]

```text

## Risks

| Risk | Affects | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| ... | [Which items] | High/Med/Low | High/Med/Low | ... |

## Explicitly NOT Doing

| Request/Idea | Source | Reason for Deferral | What Would Change This |
|---|---|---|---|
| ... | [Who asked / where it came from] | [Clear rationale] | [Condition to reconsider] |

## Success Criteria

At the end of this cycle, we'll evaluate:

1. **[Theme 1 metric]** - target: [X], baseline: [Y]
2. **[Theme 2 metric]** - target: [X], baseline: [Y]
3. **Shipped vs. planned** - execution health (target: 70%+ of "Now" items shipped)
4. **Learning velocity** - how many hypotheses did we validate or invalidate?

## Review Cadence

- **Bi-weekly:** Lightweight check. Are we on track? Any blockers? Any new information that changes priorities?
- **End of cycle:** Full retrospective. What did we ship? What did we learn? What moves to the next roadmap?

## Open Questions

- [Decisions that could change priorities]
- [Information needed to increase confidence]
- [Stakeholder alignment needed]
```

## Key Principles

- **Themes over features.** A roadmap without themes is just a prioritized backlog. Themes communicate strategy; features are tactics.
- **Capacity is real.** A roadmap that ignores capacity is a wish list. Model it explicitly. When in doubt, under-commit.
- **Classify your bets.** Table-stakes execution, optimization, strategic bets, and exploration all have different risk profiles and success criteria. A roadmap that's all one type is imbalanced.
- **Horizons, not dates.** "Now/Next/Later" communicates commitment level without false precision. Dates create expectations; horizons create alignment.
- **Dependencies drive sequencing.** The optimal build order isn't highest-priority-first; it's the order that unblocks the most work.
- **"Not doing" is a feature.** Explicitly listing what you won't build prevents drift and gives the team confidence to push back on ad-hoc requests.
- **Trace to inputs.** Every roadmap item should connect to evidence (research, competitive gap, user signal). If it can't, it's opinion, and that's worth flagging.
- **Living document.** A roadmap is a snapshot of current thinking. Re-evaluate at each review cadence. Items in "Later" are hypotheses, not promises.
- **Kill criteria up front.** Deciding when to abandon a bet is easier before you're emotionally invested. Set thresholds early.
