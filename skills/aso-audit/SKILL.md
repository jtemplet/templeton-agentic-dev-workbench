---
name: aso-audit
description: "Comprehensive App Store Optimization audit across 10 weighted factors, producing an ASO Score Card and prioritized action plan for iOS and Android"
---

# ASO Audit

Conduct an App Store Optimization health audit for an iOS or Google Play app. Score 10 ranking factors on a 0-10 scale, calculate a weighted ASO Score (0-100), and produce a prioritized action plan grouped by effort.

## When to Use

- Before launching a new app, to validate metadata is optimized for discoverability
- Diagnosing why an existing app has low organic install volume or rankings
- Periodic ASO health check (quarterly is a reasonable cadence)
- Comparing optimization quality against top category competitors

## When NOT to Use

- For paid acquisition / Apple Search Ads strategy (this skill covers organic ASO only)
- For pure keyword research with no audit context (do that as a separate exercise first)
- For general marketing strategy beyond the app stores

## Process

1. **Gather context**
   - Read `app-marketing-context.md` if present in the working directory
   - Ask for the App ID (Apple numeric ID or Google Play package name)
   - Ask for the target country (default: US)
   - Ask for the platform: iOS, Android, or Both
2. **Collect data**
   - If an ASO data source is connected (e.g., Appeeky MCP, App Store Connect, Sensor Tower), fetch: app metadata (title, subtitle, description, screenshots, ratings), current keyword rankings, top 3-5 category competitors, category chart position, and review sentiment
   - If no data source is available, ask the user to paste their current metadata and provide competitor app names
3. **Score the 10 ranking factors** using the framework below. Each factor gets a 0-10 score with a one-line justification.
4. **Calculate the ASO Score**
   - `score = (sum(weight_i * factor_score_i) / sum(weight_i)) * 10`
   - Use only the weights applicable to the platform being audited (skip Subtitle and Keyword Field for Android)
5. **Compare against competitors** on title, subtitle, screenshots, ratings, and category position
6. **Produce a prioritized action plan**, grouped into Quick Wins (today), High-Impact Changes (this week), and Strategic Recommendations (this month)
7. **Render the report** using the Output Format below
8. **Write the report to disk** at `docs/aso-audits/<YYYY-MM-DD>-<app-slug>.md` (matching the `docs/ux-audits/` convention). Use kebab-case for `<app-slug>` (e.g., `atlas-body`). Create the `docs/aso-audits/` directory if it does not exist.

## Audit Framework

Weights below are the relative importance of each factor. Apply only the rows applicable to the target platform; the score is normalized so weights need not sum to 100.

| # | Factor | iOS Weight | Android Weight |
|---|---|---|---|
| 1 | Title | 20 | 20 |
| 2 | Subtitle | 15 | n/a |
| 3 | Keyword Field | 15 | n/a |
| 4 | Description | 5 | 15 |
| 5 | Screenshots | 15 | 15 |
| 6 | App Preview Video | 5 | 5 |
| 7 | Ratings & Reviews | 15 | 15 |
| 8 | Icon | 5 | 5 |
| 9 | Keyword Rankings | 10 | 10 |
| 10 | Conversion Signals | 5 | 5 |

### 1. Title

| Check | What to look for |
|---|---|
| Keyword presence | Contains the #1 target keyword? |
| Character usage | Close to 30 chars (iOS) / 50 chars (Google Play)? |
| Brand vs keyword balance | Is the brand name necessary, or wasting space? |
| Readability | Reads naturally, not keyword-stuffed? |
| Uniqueness | Distinct from competitors? |

**Scoring guidance**

- **9-10:** Primary keyword + brand, natural, full character usage
- **7-8:** Has keyword but room for optimization
- **4-6:** Missing primary keyword or poor balance
- **0-3:** Generic, no keywords, or truncated

### 2. Subtitle (iOS only)

| Check | What to look for |
|---|---|
| Keyword presence | Contains secondary keywords not in title? |
| No repetition | Doesn't repeat title keywords? |
| Value proposition | Communicates a benefit? |
| Character usage | Close to 30 characters? |

### 3. Keyword Field (iOS only, 100 chars)

| Check | What to look for |
|---|---|
| No repetition | No keywords repeated from title or subtitle? |
| Comma formatting | Commas used as separators with no spaces? |
| Singular forms | Singular forms used (Apple indexes both forms)? |
| Character usage | All 100 characters used? |
| Relevance | All keywords relevant to the app? |
| No wasted words | No brand names, category names, or generic terms like "app"? |

### 4. Description

| Check | What to look for |
|---|---|
| First 3 lines | Compelling hook above the fold? |
| Feature highlights | Clear benefits, not just feature lists? |
| Keyword density (Android) | Natural keyword usage throughout (Google Play indexes the description)? |
| Formatting | Uses line breaks, bullets, or emoji for scannability? |
| Call to action | Clear CTA at the end? |
| Social proof | Mentions awards, press, or user counts? |

### 5. Screenshots

| Check | What to look for |
|---|---|
| Count | All 10 (iOS) / 8 (Android) slots used? |
| First 3 | Most compelling features shown first (above the fold in search)? |
| Text overlays | Clear, readable, benefit-driven captions? |
| Consistency | Cohesive design language? |
| Localization | Localized for the target market? |
| Device frames | Modern device frames, or frameless edge-to-edge? |

### 6. App Preview Video

| Check | What to look for |
|---|---|
| Exists | Is there a preview video at all? |
| First 3 seconds | Strong hook in the first 3 seconds? |
| Length | 15-30 seconds? |
| Sound | Works without sound (captions or visual storytelling)? |

### 7. Ratings & Reviews

| Check | What to look for |
|---|---|
| Average rating | 4.5+ stars? |
| Rating count | Sufficient volume for the category? |
| Recent reviews | Positive trend in the last 30 days? |
| Review responses | Developer responds to negative reviews? |
| Rating prompts | Strategic in-app rating prompts at moments of delight? |

### 8. Icon

| Check | What to look for |
|---|---|
| Distinctiveness | Stands out in search results and category browsing? |
| Simplicity | Clear and recognizable at small sizes? |
| Category fit | Matches category visual conventions? |
| No text | Avoids text (unreadable at small sizes)? |

### 9. Keyword Rankings

| Check | What to look for |
|---|---|
| Top 10 keywords | Ranks in top 10 for target keywords? |
| Keyword coverage | Ranks for enough relevant keywords? |
| Trend | Rankings improving or declining over time? |
| Competitor gap | Missing keywords that competitors rank for? |

### 10. Conversion Signals

| Check | What to look for |
|---|---|
| Promotional text | Using promotional text for timely messaging (iOS)? |
| What's New | Recent, informative update notes? |
| In-App Events | Using in-app events for visibility (iOS)? |
| Custom Product Pages | Multiple product pages targeting different audiences (iOS)? |

## Output Format

```markdown
# ASO Audit: [App Name] ([Platform], [Country])

## ASO Score Card

**Overall ASO Score: [X]/100**

| Factor | Score | Bar |
|---|---|---|
| Title              | [X]/10 | ████████░░ |
| Subtitle           | [X]/10 | ██████░░░░ |
| Keyword Field      | [X]/10 | ████░░░░░░ |
| Description        | [X]/10 | ████████░░ |
| Screenshots        | [X]/10 | ██████████ |
| Preview Video      | [X]/10 | ██░░░░░░░░ |
| Ratings & Reviews  | [X]/10 | ████████░░ |
| Icon               | [X]/10 | ████████░░ |
| Keyword Rankings   | [X]/10 | ██████░░░░ |
| Conversion Signals | [X]/10 | ████░░░░░░ |

## Quick Wins (implement today)

1. [Change], expected impact: [...]
2. ...

## High-Impact Changes (this week)

1. ...

## Strategic Recommendations (this month)

1. ...

## Competitor Comparison

| Metric | This App | Competitor 1 | Competitor 2 | Competitor 3 |
|---|---|---|---|---|
| Title              | ... | ... | ... | ... |
| Subtitle           | ... | ... | ... | ... |
| Avg Rating         | ... | ... | ... | ... |
| Category Position  | ... | ... | ... | ... |
| Screenshot Count   | ... | ... | ... | ... |

## Notes

- Data sources used: [list]
- Limitations / missing data: [list]
```

## Key Principles

- **Score honestly**: a 5/10 with clear reasoning is more useful than an inflated 8/10
- **Prioritize by impact, not effort**: quick wins come first only when they meaningfully move the score
- **Justify every score**: one line per factor explaining the rating, so the user can act on it
- **Platform-aware**: never penalize an Android app for lacking a subtitle, or an iOS app for keyword density patterns specific to Google Play
- **Cite the data**: when scoring, reference the actual metadata or competitor evidence, not generic guidance
- **Recommend specifics**: say "change subtitle from X to Y" instead of "improve subtitle"
