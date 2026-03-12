---
name: business-ideas
description: "Analyze a project's business model and surface 10 revenue-focused feature ideas with clear 'who pays and why' theses"
---

# Business Ideas Generator

Analyze the current project's business model, revenue streams, and user base, then generate revenue-focused feature ideas.

## Process

1. **Explore the business context** — search for business-relevant files (`*business*`, `*revenue*`, `*model*`, `*pricing*`, `*subscription*`, `*billing*`, `README.md`, `docs/`) to understand the product, revenue streams, target users, and competitive landscape
2. **Generate 15 candidate ideas** — each focused on one of these levers:
   - **Revenue expansion** — new monetization, upsells, premium tiers
   - **Acquisition** — features that bring new users/customers
   - **Retention** — features that reduce churn and increase stickiness
   - **Monetization efficiency** — better conversion, pricing optimization, reducing friction in purchase flows
3. **Critically evaluate each** — reject ideas that are vague ("improve UX"), expensive relative to return, or lack a clear revenue thesis. State the rejection reason explicitly.
4. **Rank survivors** — score by (revenue impact x confidence) / effort
5. **Present top 10** — in ranked order with full detail

## Output Per Idea

| Field | Description |
|---|---|
| **Title** | Concise, specific name |
| **Revenue Thesis** | 2-3 sentences: who pays, why they pay, how much incremental revenue |
| **Target Segment** | Which user/customer segment this serves |
| **Revenue Lever** | Expansion / Acquisition / Retention / Monetization Efficiency |
| **Effort** | S (days) / M (1-2 weeks) / L (weeks+) |
| **Confidence** | 0-100% that this actually moves revenue |
| **Key Risk** | The single biggest reason this might fail |

## When to Use

- When brainstorming features with business impact
- At the start of a planning cycle to prioritize revenue-generating work
- When a project needs to justify its investment or find new revenue angles

## When NOT to Use

- On open-source or non-commercial projects without revenue goals
- When the task is already scoped and you just need to build it
- When the project has no discernible business model to analyze

## Key Principles

- **Every idea needs a "who pays and why" thesis** — if you can't articulate it, the idea isn't ready
- **Explore before ideating** — understand the actual business model, don't assume
- **Effort-aware** — a brilliant L-sized idea ranks below a solid S-sized idea at similar confidence
- **Honest confidence scores** — 30% with clear reasoning beats inflated 85%
- **Reject generously** — if fewer than 10 survive evaluation, that's fine; don't pad the list
