---
name: ab-test-design
description: "Design a rigorous A/B test with hypothesis, metrics, sample size, duration, guardrails, rollout plan, and decision criteria for a software product"
---

# A/B Test Design

Design a complete experiment specification for a software product (iOS app or web app). The output is a document that an engineering team can implement directly and a data team can analyze without ambiguity.

## When to Use

- Before building a feature, to define how you'll know it worked
- When you have a hypothesis about user behavior and want to validate it
- When stakeholders disagree about a product direction and data can resolve it
- When deciding between two or more design/UX approaches
- After product research identifies a key assumption to test

## When NOT to Use

- When the change is obviously correct and not worth the delay (bug fixes, legal requirements, accessibility)
- When sample size is too small to reach significance in a reasonable time
- When you can't instrument the relevant metrics
- For infrastructure or backend changes with no user-facing impact
- When you'd ship regardless of results (be honest about this)

## Process

### Step 0: Check for the Cheapest Test First

Before designing a full A/B test, ask: "Is there a cheaper way to validate this hypothesis?"

| Validation method | When to use | Cost |
|---|---|---|
| **Fake door test** | Test demand before building (show the feature entry point, measure clicks) | Trivial |
| **Survey/user interview** | Test qualitative preferences or discover unknown motivations | Low |
| **Prototype test** | Test usability/comprehension of a design before engineering it | Low |
| **Wizard of Oz** | Test the value prop with manual backend fulfillment | Medium |
| **Limited pilot** | Ship to a hand-picked cohort, gather qual feedback | Medium |
| **Full A/B test** | Measure causal impact of a change at scale | High |

If a cheaper method can resolve the key uncertainty, recommend that first and note what results would justify escalating to a full A/B test.

### Step 1: Frame the Hypothesis

Every experiment starts with a hypothesis. Help the user sharpen theirs:

**Template:** "We believe that [change] will cause [metric] to [increase/decrease] by [amount] for [segment] because [reasoning]."

If the user provides a vague idea ("test the new checkout flow"), work with them to produce a testable hypothesis.

Identify:

1. **The intervention** - what specifically changes for the test group
2. **The mechanism** - why you believe it will work (behavioral reasoning, not "because competitors do it")
3. **The expected effect size** - how much movement you expect (be honest; 1-3% is typical for mature products, 5-15% for early-stage or radical changes)

**Cross-reference:** If this experiment tests an assumption from a product research doc or product brief, link to it explicitly.

### Step 2: Define Metrics

Structure metrics in three tiers:

| Tier | Definition | Example |
|---|---|---|
| **Primary metric** | The single metric this experiment is designed to move. Only one. | Conversion rate, retention D7, revenue per user |
| **Secondary metrics** | 2-3 metrics that help explain WHY the primary moved (or didn't) | Funnel step completion, time-on-task, feature adoption |
| **Guardrail metrics** | Metrics that must NOT degrade, even if the primary improves | Crash rate, support tickets, other feature usage, revenue, load time |

For each metric, specify:

- **Exact definition** (what events, what time window, what denominator)
- **Direction of "good"** (higher/lower)
- **Minimum detectable effect (MDE)** you care about
- **Observation window** (how long after exposure to measure; e.g., "7-day conversion")

**Common MDE pitfall:** Don't pick an MDE that's unrealistically small (making the test run forever) or unrealistically large (missing real but modest effects). Ground your MDE in business impact: "a 2% lift in conversion = $X/month, which justifies the engineering cost."

### Step 3: Experiment Design

Specify the technical design:

1. **Randomization unit** - user, session, device, or account? (Default: user. Use session only for stateless changes.)
2. **Allocation** - what % goes to control vs. treatment? (Default: 50/50. Use smaller treatment % for risky changes or limited inventory.)
3. **Targeting** - all users, or a specific segment? (New users only? Paid only? iOS only?)
4. **Duration** - minimum runtime based on:
   - Sample size needed for statistical power
   - Full weekly cycle coverage (at minimum: 1 full week, ideally 2)
   - Novelty effect washout (first 2-3 days of exposure may be inflated)
   - Observation window (if measuring D7 retention, experiment runs at least 7 days beyond last enrollment)
5. **Exclusions** - who should be excluded? (internal users, bots, users in other experiments that conflict)

### Step 4: Experiment Interaction Check

Before finalizing, check for conflicts with other running experiments:

- **Exclusive experiments** - tests that cannot run concurrently because they modify the same surface (e.g., two checkout flow tests)
- **Overlapping experiments** - tests that modify different surfaces but could have interaction effects on shared metrics
- **Safe to overlap** - completely independent experiments on unrelated surfaces

If conflicts exist, recommend: mutual exclusion (different user pools), sequential testing (run one first), or a multi-arm design.

If you don't have visibility into currently running experiments, flag this as an open question for the team.

### Step 5: Sample Size Estimation

Provide a sample size estimate using these inputs:

- Baseline rate for the primary metric
- Minimum detectable effect (MDE)
- Significance level (default: 0.05)
- Statistical power (default: 0.80)
- One-tailed vs. two-tailed (default: two-tailed)

Show the calculation reasoning. Then estimate duration:

```text
Duration = (required sample size per variant) / (daily eligible traffic per variant)
```

**Duration sanity checks:**

- If < 1 week: the test is too short to capture weekly patterns. Extend to at least 7 days.
- If 1-4 weeks: healthy range for most experiments.
- If 4-6 weeks: acceptable for low-traffic products or small MDEs.
- If > 6 weeks: surface the tradeoff. Options: accept a larger MDE, increase traffic allocation, narrow targeting, or use a qualitative validation method instead.

### Step 6: Guardrails and Stopping Rules

Define:

1. **Guardrail thresholds** - at what degradation level do you stop the experiment? (e.g., "if crash rate increases >0.5%, kill treatment within 24 hours")
2. **Early stopping criteria** - conditions for stopping early:
   - Severe harm: guardrail violated (stop immediately)
   - Clear winner: primary metric achieves p<0.001 with meaningful effect size (optional, only with sequential testing)
   - Futility: confidence interval bounds indicate the true effect is below your MDE (stop for futility, reallocate resources)
3. **Do-not-ship criteria** - even if the primary metric improves, what would make you NOT ship?
   - Guardrail violations
   - Segment-specific harm (e.g., primary metric up overall but down for paying users)
   - Qualitative red flags (support ticket surge, social media complaints)

### Step 7: Rollout Plan

Define what happens after the experiment concludes with a positive result:

| Phase | Allocation | Duration | Criteria to Advance |
|---|---|---|---|
| Experiment | 50/50 | [From Step 5] | Primary metric positive, guardrails hold |
| Ramp 1 | 75% treatment | 3-5 days | Guardrails hold at scale |
| Ramp 2 | 90% treatment | 3-5 days | No degradation at higher load |
| Full rollout | 100% | Permanent | Remove feature flag after 2 weeks |

**Rollback trigger:** Define what would cause you to roll back even after full rollout (e.g., delayed metric degradation that only shows up after weeks).

### Step 8: Analysis Plan

Pre-register how you'll analyze results:

1. **Statistical method** - frequentist (t-test, chi-squared, z-test for proportions) or Bayesian? Fixed-horizon or sequential?
2. **Segment cuts** - which segments will you analyze separately? (platform, user tenure, geography, plan type)
3. **Multiple comparison correction** - if analyzing many segments, how will you adjust? (Bonferroni for few comparisons, Benjamini-Hochberg FDR for many)
4. **Heterogeneous treatment effects** - do you expect the effect to differ by segment? If so, which segments are you powered to detect differences in?
5. **Decision framework** - given the results, what actions follow?

| Outcome | Action |
|---|---|
| Primary metric improves significantly, guardrails hold | Proceed to rollout |
| Primary metric improves, but below MDE | Likely don't ship; effect too small to justify complexity |
| Primary metric improves, guardrail degrades | Investigate root cause; likely don't ship |
| Primary metric flat (confidence interval includes 0) | Kill experiment, revisit hypothesis |
| Primary metric degrades | Kill experiment immediately, investigate |

### Step 9: Save the Document

Write to `docs/experiments/experiment-<kebab-case-name>.md` (create directory if needed).

## Output Format

```markdown
# Experiment: [Name]

**Date:** [YYYY-MM-DD]
**Status:** Proposed
**Owner:** [If specified]
**Related docs:** [Links to product brief, research, or roadmap item this tests]

## Hypothesis

We believe that [change] will cause [metric] to [direction] by [amount] for [segment] because [reasoning].

## Cheapest Test Considered

[What cheaper validation methods were considered and why a full A/B test is warranted. Or: recommend a cheaper test first with escalation criteria.]

## Intervention

**Control:** [Current experience - be specific about what users see/do]
**Treatment:** [New experience - be specific about what changes]

[If multiple treatments: describe each variant]

## Metrics

### Primary Metric

- **[Metric name]** - [Exact definition including events, time window, denominator]
  - Baseline: [current value if known]
  - MDE: [minimum effect worth detecting]
  - Direction: [higher/lower is better]
  - Observation window: [how long after exposure]

### Secondary Metrics

- **[Metric]** - [Definition, what it helps explain]

### Guardrail Metrics

- **[Metric]** - [Definition, threshold that triggers alarm]

## Design

| Parameter | Value |
|---|---|
| Randomization unit | [user/session/device] |
| Allocation | [Control %] / [Treatment %] |
| Target population | [Who is eligible] |
| Exclusions | [Who is excluded] |
| Minimum duration | [X days/weeks] |
| Required sample size | [N per variant] |

### Sample Size Reasoning

[Show inputs and logic: baseline rate, MDE, alpha, power, daily traffic estimate, resulting duration]

### Experiment Interactions

[Conflicts with other running experiments, or "no known conflicts"]

## Guardrails & Stopping Rules

- **Stop immediately if:** [condition]
- **Stop for futility if:** [condition]
- **Do not ship if:** [condition, even with positive primary metric]

## Rollout Plan

| Phase | Allocation | Duration | Advance if |
|---|---|---|---|
| Experiment | [X/Y] | [duration] | Primary positive, guardrails hold |
| Ramp 1 | [%] | [days] | Guardrails hold at scale |
| Ramp 2 | [%] | [days] | No degradation |
| Full rollout | 100% | Permanent | Stable for 2 weeks |

**Rollback trigger:** [What would cause reversal after full rollout]

## Analysis Plan

- **Method:** [Frequentist/Bayesian, specific test]
- **Segment cuts:** [List]
- **Correction:** [Bonferroni/FDR/none, with justification]
- **Heterogeneous effects:** [Segments where different treatment effects are expected]

## Decision Framework

| Outcome | Action |
|---|---|
| Primary up significantly, guardrails hold | Proceed to rollout |
| Primary up but below MDE | Likely kill; effect too small |
| Primary up, guardrail violated | Investigate, likely kill |
| Primary flat | Kill, revisit hypothesis |
| Primary down | Kill immediately |

## Implementation Notes

[Engineering considerations: feature flag names, event tracking needed, new instrumentation required, estimated eng effort]

## Open Questions

- [Unresolved decisions]
```

## Key Principles

- **Start with the cheapest test.** A full A/B test is expensive (eng time, user exposure, opportunity cost of running time). Always ask if there's a cheaper way to learn.
- **One primary metric.** If you can't pick one, you don't know what you're testing. Secondary metrics help explain; they don't decide.
- **Pre-register everything.** Decide your analysis plan before seeing results. Post-hoc rationalization is the #1 source of false positives.
- **Guardrails are non-negotiable.** A feature that lifts conversion but increases crashes is not a win.
- **Respect sample size.** Peeking at results early and calling it when it "looks significant" inflates your false positive rate. Either use sequential testing or commit to a fixed horizon.
- **Plan the rollout, not just the test.** An experiment without a rollout plan creates a gap between "results are in" and "feature is live."
- **Think about what you'll do with each outcome.** If you'd ship regardless of results, don't run the experiment; you're wasting time and user trust.
- **Novelty effects are real.** New things get attention. Wait for the novelty to wear off before reading results (minimum: 1 full week).
- **Survivorship bias.** If your metric only measures users who reach a step, make sure you're not losing users at an earlier step.
- **Check for interactions.** Two experiments that modify the same surface can invalidate each other's results.
