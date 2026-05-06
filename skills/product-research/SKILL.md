---
name: product-research
description: "Synthesize user signals by segment, size opportunities using JTBD and opportunity scoring, and rank what to build next with evidence quality weighting"
---

# Product Research

Synthesize available signals (user feedback, analytics, market data, support tickets) into ranked product opportunities. Uses Jobs-to-Be-Done framing and opportunity scoring to produce a prioritized list of what to build next, segmented by user type.

## When to Use

- At the start of a planning cycle when you need to decide what to build
- When you have scattered user feedback but no clear priorities
- When you want to ground feature decisions in user needs rather than stakeholder opinions
- After a competitive analysis, to translate gaps into user-centric opportunities

## When NOT to Use

- When priorities are already decided and you just need to execute
- When you have zero user signal (no feedback, no analytics, no support data); you need inputs to synthesize
- For quick feature validation (use `ab-test-design` instead)

## Process

### Step 1: Define User Segments

Before gathering signals, establish who you're researching for. Different segments have different jobs.

Identify 2-4 distinct user segments based on:

- **Behavior** - how they use the product (power users vs. casual, daily vs. weekly)
- **Lifecycle stage** - new users, activated users, power users, churned users
- **Job context** - what they're hiring the product to do (may vary by segment)
- **Business value** - which segments drive revenue, retention, or growth?

**Segment template:**

- **Name** - memorable label (e.g., "Weekend Creators," "Enterprise Admins")
- **Description** - who they are in 1-2 sentences
- **Size estimate** - % of user base (if knowable)
- **Strategic importance** - why this segment matters (revenue, growth, retention)

This segmentation informs everything downstream: different segments may have different jobs, different satisfaction levels, and different priorities.

### Step 2: Gather Signals

Collect inputs from every available source. Don't skip sources because they seem minor; weak signals compound.

**Internal sources (check the codebase and docs):**

- User feedback files, feature request logs
- Support ticket patterns (common complaints, recurring themes)
- Analytics summaries (if available in docs)
- Previous research, user interview notes
- App Store / Play Store reviews
- Churn reasons, cancellation surveys

**External research:**

- App Store reviews (search: `site:apps.apple.com "<product>"`)
- Play Store reviews (search: `site:play.google.com "<product>"`)
- Reddit/forum discussions about the product or category
- Competitor feature launches (what are they solving that you're not?)
- Industry reports, trend pieces
- Social media mentions, Twitter/X discussions
- Hacker News threads about the category

**Cross-reference:** Check `docs/product/` for prior competitive analysis. Gaps found there are signal.

For each signal, note:

- **What users say** (verbatim if possible)
- **What they're trying to do** (the underlying job)
- **Which segment** this signal applies to
- **Evidence quality** (see below)
- **How many people seem to have this need** (frequency signal)
- **How painful it is** (severity signal)

### Step 3: Weight Evidence Quality

Not all signals are equal. Weight evidence by reliability:

| Evidence Type | Weight | Rationale |
|---|---|---|
| Quantitative data (analytics, large-scale surveys, A/B test results) | High | Large N, objective measurement |
| App Store/Play Store reviews (100+ mentioning a theme) | High | Large N, unprompted, public commitment |
| Structured user interviews (5+) | Medium-High | Deep insight, but small N |
| Support tickets (pattern across 50+) | Medium-High | Real pain, but biased toward vocal users |
| Forum/Reddit threads (multiple threads, engaged discussion) | Medium | Self-selected audience, but genuine signal |
| Individual user requests (email, DM, Slack) | Low-Medium | Could be one loud voice |
| Stakeholder opinions without data | Low | Capture but label explicitly as opinion |
| Your own intuition | Label only | Note it honestly, but don't weight it as evidence |

When scoring opportunities later, note the evidence quality supporting each job. An opportunity with high evidence quality and medium importance may warrant action before an opportunity with low evidence quality and high importance.

### Step 4: Identify Jobs-to-Be-Done

Group signals into Jobs-to-Be-Done (JTBD). A job is progress a user is trying to make in a specific circumstance.

**Job format:** "When [situation], I want to [motivation], so I can [expected outcome]."

Examples:

- "When I'm commuting, I want to review my daily tasks, so I can arrive at work ready to start."
- "When I receive a payment, I want to immediately see it in my dashboard, so I can confirm the transaction went through."

**Also identify Anti-Jobs** (things users are trying to avoid):

**Anti-job format:** "When [situation], I want to avoid [negative outcome], so I don't [consequence]."

Examples:

- "When I'm setting up the app, I want to avoid entering redundant information, so I don't abandon onboarding."
- "When I'm in a meeting, I want to avoid notification noise, so I don't lose focus."

Anti-jobs often reveal opportunities that pure "what do users want?" thinking misses. Removing friction is often higher-leverage than adding features.

For each job (and anti-job), assess:

| Dimension | Question |
|---|---|
| **Importance** | How much does this matter to users? (1-10) |
| **Satisfaction** | How well does the current solution serve this job? (1-10) |
| **Frequency** | How often do users encounter this job? (daily/weekly/monthly/rarely) |
| **Segment** | Which user segment(s) have this job? |
| **Evidence quality** | High/Medium/Low (from Step 3) |

### Step 5: Opportunity Scoring

Use the Opportunity Score formula to prioritize:

```text
Opportunity Score = Importance + max(Importance - Satisfaction, 0)
```

- Score > 15: Underserved, high-opportunity
- Score 12-15: Worth investigating
- Score < 12: Adequately served or low importance

**Adjusted scoring:** When evidence quality is Low, discount the score by 20-30% (note the adjustment). High-confidence opportunities should rank above same-score low-confidence ones.

Rank all jobs by opportunity score. The highest-scoring jobs represent the biggest gaps between what users need and what they currently have.

### Step 6: Size the Opportunities

For the top 5-7 opportunities, estimate:

1. **Addressable users** - what % of your user base has this job? (Segment-specific.)
2. **Impact if solved** - what metric would improve? By roughly how much?
3. **Build cost** - rough effort to address this job (S/M/L)
4. **Competitive pressure** - are competitors solving this already? (From competitive analysis if available.)
5. **Evidence confidence** - how confident are you in the scoring? (High/Medium/Low)

Produce an opportunity ranking:

| Rank | Job | Segment | Opp Score | Evidence | Addressable % | Impact | Effort | Competitive Pressure |
|---|---|---|---|---|---|---|---|---|
| 1 | ... | ... | ... | H/M/L | ... | ... | S/M/L | None/Some/High |

### Step 7: Translate to Feature Concepts

For the top 3-5 opportunities, generate 1-2 concrete feature concepts per job:

- **Feature name** - specific and descriptive
- **What it does** - 2-3 sentences, specific enough for an engineer to understand scope
- **How it addresses the job** - connect it back to the JTBD
- **Target segment** - which segment benefits most
- **Key assumption** - what must be true for this to work? (this becomes your experiment hypothesis)
- **Validation approach** - how would you test this before building the full thing? (prototype, fake door test, Wizard of Oz, survey, A/B test)
- **Risk** - what could go wrong?

### Step 8: Save the Document

Write to `docs/product/research-<topic-slug>-<date>.md` (create directory if needed).

## Output Format

```markdown
# Product Research: [Topic/Area]

**Date:** [YYYY-MM-DD]
**Product:** [Product name]
**Sources consulted:** [List of signal sources with evidence quality]
**Prior work referenced:** [Links to competitive analysis, prior research, etc.]

## Executive Summary

[3-4 sentences: biggest unmet need, which segment it affects, top opportunity, recommended next step]

## User Segments

### [Segment 1: Name]

- **Who:** [Description]
- **Size:** [% of base or absolute number]
- **Strategic importance:** [Why they matter]
- **Primary jobs:** [Quick summary]

[Repeat for each segment]

## Signal Summary

### User Feedback Themes

| Theme | Segment | Frequency | Severity | Evidence Quality | Example Quote |
|---|---|---|---|---|---|
| ... | ... | High/Med/Low | High/Med/Low | High/Med/Low | "..." |

### Key Observations

- [Observation with evidence and segment attribution]

## Jobs-to-Be-Done

### [Job 1: Short title]

> When [situation], I want to [motivation], so I can [outcome].

- **Importance:** [1-10]
- **Satisfaction:** [1-10]
- **Opportunity Score:** [calculated]
- **Frequency:** [daily/weekly/monthly]
- **Segment:** [which segment(s)]
- **Evidence:** [What signals point to this job, quality rating]

### Anti-Jobs

### [Anti-Job 1: Short title]

> When [situation], I want to avoid [negative outcome], so I don't [consequence].

- **Importance:** [1-10]
- **Current friction level:** [1-10, where 10 = extremely painful]
- **Segment:** [which segment(s)]
- **Evidence:** [What signals point to this anti-job]

## Opportunity Ranking

| Rank | Job | Segment | Opp Score | Evidence | Addressable % | Impact | Effort | Competitive Pressure |
|---|---|---|---|---|---|---|---|---|
| 1 | ... | ... | ... | H/M/L | ... | ... | S/M/L | None/Some/High |

## Feature Concepts

### For: [Job Title] (Rank #1, Segment: [X])

**Concept A: [Feature Name]**

- **What:** [Specific description]
- **How it addresses the job:** [Connection to JTBD]
- **Target segment:** [Primary beneficiary]
- **Key assumption:** [What must be true]
- **Validation:** [How to test cheaply]
- **Risk:** [What could go wrong]
- **Effort:** [S/M/L]

**Concept B: [Feature Name]**

[Same structure]

[Repeat for top 3-5 jobs]

## Recommendations

### Build Next (High Evidence, High Opportunity)

1. **[Feature]** - [1-sentence rationale grounded in opportunity score and evidence quality]

### Validate First (High Opportunity, Low Evidence)

1. **[Feature]** - [What to test and how before committing to full build]

### Quick Wins (Low Effort Anti-Jobs)

1. **[Friction removal]** - [What to fix and expected impact]

### Defer (Low Priority or Wrong Timing)

1. **[Feature/Job]** - [Why this isn't the right time: low addressable %, high effort, low evidence, etc.]

## Evidence Gaps

[What you still don't know that would change priorities. Be specific about what research would increase confidence and how to get it.]

## Open Questions

- [Decisions that require stakeholder input]
- [Research that would increase confidence]
```

## Key Principles

- **Segment before synthesizing.** "Users want X" is almost always wrong; specific users in specific contexts want X. Unsegmented research produces features that delight no one fully.
- **Jobs, not features.** Think about what users are trying to accomplish, not what buttons to add. Features are hypotheses about how to serve jobs.
- **Anti-jobs are underrated.** Removing friction is often higher-leverage than adding capabilities. Users switching FROM something tells you as much as users asking FOR something.
- **Frequency x severity = urgency.** A daily annoyance matters more than a rare catastrophe, and a rare catastrophe matters more than a daily non-issue.
- **Satisfaction is relative.** A job that's 8/10 important but 7/10 satisfied is low opportunity. A job that's 6/10 important but 2/10 satisfied is high opportunity.
- **Weight your evidence.** 5 vocal Slack users are not the same as 2000 app store reviews showing a pattern. Make evidence quality explicit in your scoring.
- **Inputs over opinions.** If you catch yourself generating "insights" without citing evidence, stop. That's opinion dressed as research.
- **Validation before commitment.** The output of research is hypotheses to test, not features to build. The cheapest way to learn is rarely "build the whole thing."
- **Acknowledge gaps.** If you have weak signal in an area, say so. Manufactured confidence is worse than honest uncertainty.
