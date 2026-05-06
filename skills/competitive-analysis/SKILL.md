---
name: competitive-analysis
description: "Deep competitor teardown with positioning map, moat analysis, feature gaps, trajectory mapping, and strategic implications for a software product"
---

# Competitive Analysis

Produce a structured competitive analysis for a software product (iOS app, web app, or SaaS). The output helps a product team understand where they sit in the market, where competitors are heading, and where the gaps are.

## When to Use

- Before a major feature planning cycle to understand the landscape
- When entering a new market or adjacent space
- When a competitor ships something notable and you need to assess the threat
- When stakeholders ask "how do we compare to X?"

## When NOT to Use

- For quick "what does competitor X do?" lookups (just search the web directly)
- When you already know the landscape and need to decide what to build (use `product-roadmap` instead)
- For pricing-only comparisons (the `product-analyst` agent covers this more thoroughly)

## Process

### Step 1: Define the Competitive Frame

Before researching, establish:

1. **Your product** - what it does, who it serves, what stage it's at
2. **Category definition** - what market are you competing in? (Be specific: "collaborative design tools for product teams" not "software")
3. **Competition types to analyze:**
   - Direct (same job-to-be-done, same solution approach)
   - Indirect (same job-to-be-done, different solution approach)
   - Potential (adjacent players who could enter your space)

If the user hasn't specified competitors, identify 5-8 through web research. If they have, research those plus 2-3 they may have missed.

**Cross-reference:** Check `docs/product/` for prior research that provides context on user segments or product positioning.

### Step 2: Research Each Competitor

For each competitor, gather:

- **Core value proposition** - their one-liner positioning
- **Target segment** - who they serve (size, industry, persona)
- **Key features** - what they ship, especially recent launches
- **Pricing model** - how they charge, entry price, enterprise tier
- **Distribution** - how they acquire users (PLG, sales-led, marketplace, etc.)
- **Traction signals** - downloads, reviews, funding, team size, notable customers
- **Recent moves** - last 6 months of notable launches or pivots
- **Trajectory** - where they're heading based on hiring, acquisitions, product announcements

Use targeted web searches:

- `"<competitor>" features site:<competitor-domain>`
- `"<competitor>" pricing`
- `"<competitor>" review site:g2.com OR site:producthunt.com`
- `"<competitor>" funding OR raise OR series`
- `"<competitor>" vs "<other competitor>"`
- `site:apps.apple.com "<competitor>"` (for iOS)
- `"<competitor>" hiring site:linkedin.com` (trajectory signal)
- `"<competitor>" roadmap OR "coming soon" OR "what's new"` (trajectory signal)

### Step 3: Build the Positioning Map

Create a 2x2 positioning map using the two most strategically relevant dimensions for this market. Common axes:

- Simple vs. Powerful
- Self-serve vs. Sales-led
- Horizontal vs. Vertical
- SMB-focused vs. Enterprise-focused
- Price (low vs. high)
- Breadth vs. Depth

Place each competitor on the map. Identify which quadrants are crowded and which are underserved.

Format as a text diagram:

```text
                    [Axis Label High]
                         |
         Competitor A    |    Competitor B
                         |
[Axis Low] -------------|-------------- [Axis High]
                         |
         Competitor C    |    YOUR PRODUCT
                         |
                    [Axis Label Low]
```

**Key insight required:** Don't just place dots. State what the map reveals about market structure and where the whitespace is.

### Step 4: Moat Analysis

For each competitor (and yourself), assess defensibility:

| Moat Type | Description | Strength (0-5) |
|---|---|---|
| **Network effects** | Does the product get better as more people use it? | |
| **Switching costs** | How painful is it for users to leave? (data lock-in, workflow dependency, integrations) | |
| **Data advantages** | Does usage generate proprietary data that improves the product? | |
| **Brand/Trust** | Is there brand recognition or trust that a new entrant can't easily replicate? | |
| **Distribution** | Do they have a channel advantage (app store ranking, SEO, partnerships, embedded in workflow)? | |
| **Economies of scale** | Do they have cost advantages that grow with volume? | |

Identify:

- **Strongest moat in the market** - who has the most defensible position and why?
- **Your moat (or lack thereof)** - be honest. If you have no moat, that's critical strategic context.
- **Moat-building opportunities** - what could you do to build defensibility?

### Step 5: Trajectory Analysis

Static competitive analysis is insufficient. Map where each competitor is *heading*:

For each competitor, assess:

- **Investment direction** - what are they hiring for? What have they acquired?
- **Product velocity** - how fast are they shipping? Is it accelerating?
- **Strategic bets** - what big moves are they making? (new markets, platform plays, AI pivots)
- **Convergence risk** - are they moving toward your positioning?

Produce a trajectory map: where is each competitor today vs. where will they likely be in 12 months?

### Step 6: Feature Gap Analysis

Build a feature comparison matrix:

| Capability | Your Product | Competitor A | Competitor B | Competitor C |
|---|---|---|---|---|
| Feature 1 | Yes/No/Partial | ... | ... | ... |
| Feature 2 | ... | ... | ... | ... |

Then classify gaps:

1. **Table-stakes gaps** - features all competitors have that you don't (urgent: users expect these)
2. **Differentiation opportunities** - features no one has but users want (evidence required)
3. **Over-investment areas** - features you have that competitors don't and users don't value
4. **Emerging standards** - features 1-2 competitors just launched that will become table-stakes within 12 months

### Step 7: Strategic Implications

Synthesize findings into:

1. **Positioning recommendation** - where should you play on the map? Why? How does this differ from where you are today?
2. **Must-have gaps** - what must you build to stay competitive? (Rank by urgency.)
3. **Differentiation bets** - what could you build that creates distance? (Rank by defensibility.)
4. **Threats to watch** - which competitive moves should trigger a response? Define specific triggers.
5. **What NOT to build** - features that would move you toward a crowded quadrant or that competitors have moats around
6. **Moat-building actions** - what should you do to become more defensible?

### Step 8: Save the Document

Write to `docs/product/competitive-analysis-<date>.md` (create directory if needed).

## Output Format

```markdown
# Competitive Analysis: [Product/Category]

**Date:** [YYYY-MM-DD]
**Category:** [Market definition]
**Competitors Analyzed:** [List]
**Prior work referenced:** [Links to prior PM docs, if any]

## Executive Summary

[3-4 sentences: where you sit, biggest threat, biggest opportunity, most urgent action]

## Positioning Map

[2x2 text diagram with axis labels and competitor placement]

**Key Insight:** [What the map reveals about market structure]
**Whitespace:** [Which positions are underserved and why]

## Competitor Profiles

### [Competitor Name]

- **Positioning:** [One-liner]
- **Target:** [Segment]
- **Pricing:** [Model and entry price]
- **Strengths:** [2-3 bullets]
- **Weaknesses:** [2-3 bullets]
- **Moat:** [Primary defensibility, strength 0-5]
- **Recent Moves:** [Notable launches/pivots in last 6 months]
- **Trajectory:** [Where they're heading in the next 12 months]
- **Threat Level:** High / Medium / Low - [why]

[Repeat for each competitor]

## Moat Analysis

| Competitor | Network Effects | Switching Costs | Data Advantage | Brand | Distribution | Scale |
|---|---|---|---|---|---|---|
| Your Product | [0-5] | [0-5] | [0-5] | [0-5] | [0-5] | [0-5] |
| Competitor A | ... | ... | ... | ... | ... | ... |

**Key Finding:** [Who has the strongest moat, what type, and what that means for you]
**Moat-Building Opportunity:** [What you could do to become more defensible]

## Trajectory Map

| Competitor | Current Position | 12-Month Direction | Convergence Risk |
|---|---|---|---|
| ... | [Where they are] | [Where they're heading] | High/Med/Low |

**Implication:** [What trajectory patterns mean for your strategy]

## Feature Gap Analysis

[Matrix table]

### Table-Stakes Gaps (Must Build)

1. **[Feature]** - [Why it's table stakes, which competitors have it, user expectation evidence]

### Emerging Standards (Build Within 12 Months)

1. **[Feature]** - [Who just launched it, why it'll become expected]

### Differentiation Opportunities (Could Build)

1. **[Feature]** - [Evidence of user demand, why competitors haven't built it, defensibility potential]

### Over-Investment (Consider Deprioritizing)

1. **[Feature]** - [Why it may not be earning its keep]

## Strategic Recommendations

### Position To Win

[1-2 paragraphs: recommended positioning and why. Reference moat analysis and trajectory.]

### Priority Actions

| Priority | Action | Rationale | Effort | Confidence |
|---|---|---|---|---|
| 1 | ... | ... | S/M/L | High/Med/Low |
| 2 | ... | ... | S/M/L | High/Med/Low |
| 3 | ... | ... | S/M/L | High/Med/Low |

### Moat-Building Actions

- **[Action]** - [How this builds defensibility over time]

### Threats to Monitor

- **[Threat]** - [Specific trigger that should cause you to respond, and what the response would be]

### What NOT to Build

- **[Feature/Direction]** - [Why pursuing this is a trap: crowded quadrant, competitor moat, etc.]

## Open Questions

- [Unresolved questions that need more research or user data]
```

## Key Principles

- **Compete on your terms, not theirs.** The goal isn't feature parity; it's finding positioning where you win.
- **Static snapshots lie.** Where competitors are today matters less than where they're heading. Always include trajectory.
- **Moats matter more than features.** A feature without defensibility is a 6-month head start at best. Prioritize actions that build moats.
- **Evidence over intuition.** Every claim about a competitor should be backed by something you found in research.
- **Respect competitors.** Acknowledge where they're genuinely better. Dismissing competitors leads to blind spots.
- **Actionable over comprehensive.** A shorter analysis with clear "do this next" beats an encyclopedic reference doc.
- **Time-bound.** Competitive landscapes shift. Date everything. Assume this analysis has a 3-6 month shelf life.
