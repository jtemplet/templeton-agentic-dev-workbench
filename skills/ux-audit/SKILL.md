---
name: ux-audit
description: Conduct a comprehensive UX audit of a running web app via Playwright. Captures screenshots, exercises forms and error states, performs keyboard accessibility and three-viewport responsive evaluation, then produces a severity-ranked report covering accessibility, design system, IA, interaction, content, emotional design, and cognitive load.
---

# UX Audit (Web)

A systematic technique for evaluating a running web app across seven UX dimensions. Produces a severity-ranked report with screenshot evidence and concrete recommendations.

## Core Evaluation Dimensions

Every audit assesses all seven dimensions. Skipping any produces an incomplete audit.

| # | Dimension | What you're evaluating |
|---|-----------|----------------------|
| 1 | **Accessibility & Inclusivity** | WCAG compliance, keyboard navigation, focus management, contrast, screen reader semantics, touch targets, motion sensitivity |
| 2 | **Design System Coherence** | Spacing rhythm, typographic scale, color usage, component consistency, visual language cohesion |
| 3 | **Information Architecture** | Navigation structure, findability, mental model alignment, progressive disclosure, content hierarchy |
| 4 | **Interaction Design** | Transitions, feedback loops, loading patterns, state management, error recovery, animation purpose |
| 5 | **Content & Microcopy** | Label clarity, error message quality, empty state messaging, tone consistency, action verb specificity |
| 6 | **Emotional Design & Trust** | Confidence during critical flows, delight in low-stakes moments, trust signals, dark pattern absence, brand personality |
| 7 | **Cognitive Load & Clarity** | Clutter, competing actions, decision fatigue, information density, signal-to-noise ratio |

## Required Workflow

### Step 0: Understand Context

1. Locate the project's `AGENTS.md` (try the working directory; fall back to `CLAUDE.md` if missing)
2. Read it fully and extract:
   - Product purpose
   - Target user (who they are, what they know, what they need)
   - Primary workflows / jobs-to-be-done
   - Any stated design principles or brand values
3. If neither file exists or context is too thin to evaluate against, **stop and ask the user** for: product purpose, primary user, and the top 1 to 3 workflows to evaluate. Do not proceed in a vacuum.
4. Form a **design hypothesis**: given this user and this goal, what should the ideal experience feel like? Fast and confident? Calm and guided? Playful and exploratory? This hypothesis frames every finding below.

### Step 1: Parse Input

`$ARGUMENTS` should contain the app URL. If missing, ask for it. Optionally accept extra hints (credentials, specific flows to focus on, known pain points).

Create the output directory: `docs/ux-audits/`. Determine an audit slug: `<YYYY-MM-DD>-<app-host-or-name>`. Screenshots will live under `docs/ux-audits/<slug>/screenshots/`.

### Step 2: Explore the App (via Playwright)

Use the Playwright MCP tools to systematically walk the experience. Snapshots (`browser_snapshot`) are for understanding the DOM and accessibility tree. Screenshots (`browser_take_screenshot`) are evidence for the report.

**2a. First impression (5-second test)**

1. Navigate to the URL
2. Take a screenshot immediately
3. Before clicking anything, assess from the snapshot alone:
   - Can you identify what this product does within 5 seconds?
   - Is the primary action obvious?
   - What is the visual hierarchy communicating (1st, 2nd, 3rd level)?
   - What emotion does the page evoke?

**2b. Primary workflow walkthrough**

Walk the primary workflow from AGENTS.md end-to-end:

1. Identify the entry point
2. At each step, take a snapshot (for navigation) and a screenshot (for evidence)
3. Note: time-to-action (how many clicks/steps to reach the goal), clarity of progress, confidence level at each step
4. Complete the flow successfully at least once

**2c. Edge cases and error states**

Exercise these systematically:

- Empty form submission (validation behavior)
- Invalid input (error message quality, recovery path)
- Successful submission (confirmation feedback)
- Empty states (no data, first-time user, search with no results)
- Loading states (if observable)
- Back-button behavior (state preservation)
- At least one alternate or secondary path

**2d. Accessibility pass**

Using snapshots and interaction:

1. Tab through the primary flow using `browser_press_key` with Tab. Note:
   - Is there a visible focus indicator on every interactive element?
   - Does tab order follow visual order?
   - Can you complete the primary flow using only keyboard?
2. Inspect the snapshot's accessibility tree:
   - Are images using meaningful alt text (not filename-as-alt, not empty on informational images)?
   - Do form inputs have associated labels?
   - Are ARIA roles used correctly (not misused or redundant)?
   - Is heading hierarchy logical (h1 > h2 > h3, no skipped levels)?
3. Evaluate contrast by examining the visual screenshot:
   - Small text against its background (target: 4.5:1 WCAG AA)
   - Interactive element boundaries
   - Disabled state readability
4. Check `browser_console_messages` for accessibility warnings

**2e. Responsive evaluation**

Test at three breakpoints minimum:

1. Desktop (default viewport, already tested)
2. Tablet: `browser_resize` to ~768x1024
3. Mobile: `browser_resize` to ~390x844

For each:
- Screenshot the landing page and the most critical screen of the primary flow
- Assess: what adapts, what collapses, what disappears, what breaks?
- Note touch target sizing (minimum 44x44 CSS pixels per WCAG 2.5.8)
- Check if horizontal scroll appears where it shouldn't

**2f. Console and network**

Capture `browser_console_messages` and `browser_network_requests`. Flag:
- JavaScript errors visible to the user (broken interactions)
- Failed network requests (missing images, broken API calls)
- Mixed content warnings
- Performance-related signals (very slow requests)

Save all screenshots into `docs/ux-audits/<slug>/screenshots/` with descriptive, numbered filenames (e.g., `01-landing-desktop.png`, `02-signup-form.png`, `03-validation-error.png`, `04-landing-tablet.png`).

Keep a running log of (screenshot filename, what it shows, which flow step, which viewport). You will cite these in the report.

When all exploration is complete, call `browser_close`.

### Step 3: Evaluate Against All Seven Dimensions

For each dimension, evaluate every screen and flow you explored. This is the analytical core of the audit.

**Dimension 1: Accessibility & Inclusivity**

- Keyboard navigation: can every interactive element be reached and activated?
- Focus management: is focus visible, logical, and trapped correctly in modals?
- Semantic HTML: headings, landmarks, form labels, alt text
- Color: not used as the sole indicator of state (error, success, selected)
- Contrast: text, icons, and interactive boundaries
- Touch targets: 44x44 minimum on mobile
- Motion: any animation that can't be disabled? Flashing content?

**Dimension 2: Design System Coherence**

- Typography: how many distinct font sizes, weights, and families? Is there a clear scale (e.g., 12/14/16/20/24/32)?
- Spacing: consistent rhythm or ad-hoc padding/margins?
- Color: intentional palette or drift? Do colors carry consistent meaning (primary, destructive, muted)?
- Components: are similar elements (buttons, cards, inputs) rendered consistently across screens?
- Iconography: consistent style, size, and meaning?
- Overall: would a designer say this comes from one coherent system, or several stitched together?

**Dimension 3: Information Architecture**

- Navigation: is the structure obvious? Can you get to any major feature in 2-3 clicks?
- Mental model: does the organization match how users think about the domain?
- Findability: would a new user know where to look for [key feature]?
- Progressive disclosure: is complexity revealed gradually or dumped up front?
- Breadcrumbs / wayfinding: do you always know where you are?

**Dimension 4: Interaction Design**

- Feedback: does every user action produce a clear response? (Click, submit, toggle, delete)
- State communication: can you always tell what state the system is in? (Loading, empty, error, success)
- Transitions: do they serve a purpose (orienting, connecting, confirming) or are they decorative?
- Error recovery: when something goes wrong, is the path back obvious and short?
- Undo/reversibility: can destructive actions be undone or at least confirmed?
- Loading perception: skeleton screens vs. spinners vs. blank screens. Is the wait acknowledged?
- Optimistic UI: where applicable, does the interface respond immediately?

**Dimension 5: Content & Microcopy**

- Labels: specific action verbs ("Save draft" vs. "Submit") or vague ("OK", "Continue")?
- Error messages: do they explain what happened, why, and how to fix it?
- Empty states: helpful guidance or dead ends?
- Tone: consistent with brand? Appropriate to the moment? (Error messages shouldn't be playful if the user might lose data.)
- Jargon: does copy assume knowledge the target user may not have?
- Scannability: can users get the gist without reading every word?

**Dimension 6: Emotional Design & Trust**

- First impression: does the landing page inspire confidence in the product's quality?
- Critical moments: during payment, data entry, account creation, is there adequate reassurance?
- Delight: are there small moments of polish that signal craft? (But not at the cost of usability.)
- Trust signals: social proof, security indicators, clear privacy communication where expected
- Dark patterns: forced continuity, confirmshaming, hidden costs, trick questions, roach motels, misdirection, bait-and-switch. Flag ANY instance of these.
- Brand personality: does the experience feel like it was made by people who care, or assembled from templates?

**Dimension 7: Cognitive Load & Clarity**

This remains the most important dimension. Every screen gets this assessment:

- Element count: how many distinct things compete for attention?
- Action clarity: is the primary action obvious without reading every label?
- Decision load: how many choices is the user asked to make at once?
- Information density: signal-to-noise ratio. What could be removed without loss?
- Competing priorities: are there multiple elements styled as primary actions?
- Ambiguity: any labels, icons, or layouts where the meaning is unclear?
- Scanning path: does the eye flow naturally from most important to least?

### Step 4: Write the Report

Save to `docs/ux-audits/<slug>.md`. Reference screenshots with relative paths (e.g., `![Landing](./<slug>/screenshots/01-landing-desktop.png)`).

```markdown
# UX Audit: <App Name>

**Date:** <today's date>
**URL audited:** <url>
**Auditor:** UX Product Designer Agent
**Design hypothesis:** <one sentence: what should this experience feel like for the target user?>

---

## 1. Product Understanding

- **Purpose:** <from AGENTS.md>
- **Target user:** <from AGENTS.md>
- **Primary workflow(s) evaluated:** <list>
- **Design hypothesis:** <expanded: given this user and goal, the experience should feel [X]. It should prioritize [Y] over [Z]>

[1 to 2 paragraphs framing what the product is trying to do for whom, in your own words. This is the lens for everything below.]

## 2. Five-Second Test

What the landing page communicates before any interaction:
- **Can I tell what this does?** Yes/No + explanation
- **Is the primary action obvious?** Yes/No + explanation
- **What emotion does this evoke?** <describe>
- **Screenshot:** <reference>

## 3. Issues (Ranked by Severity)

For each issue:

### [Severity] <Short title>

- **Dimension:** <which of the 7 dimensions>
- **Description:** <what's wrong>
- **Why it matters:** <tie back to user goal; what does it cost the user?>
- **Evidence:** <screenshot reference + flow step>

(Group by severity: Critical, High, Medium, Low. Within each, order by impact on the primary workflow.)

**Severity definitions:**
- **Critical:** Blocks the primary workflow, breaks trust, or excludes users (accessibility failure)
- **High:** Significantly degrades the experience or causes measurable confusion/abandonment
- **Medium:** Noticeable friction that doesn't block completion but erodes quality
- **Low:** Polish issues visible to trained eyes; users can work around them

## 4. Dimension Scorecards

Rate each dimension on a 5-point scale with brief justification:

| Dimension | Score | Summary |
|-----------|-------|---------|
| Accessibility & Inclusivity | /5 | |
| Design System Coherence | /5 | |
| Information Architecture | /5 | |
| Interaction Design | /5 | |
| Content & Microcopy | /5 | |
| Emotional Design & Trust | /5 | |
| Cognitive Load & Clarity | /5 | |
| **Overall** | **/5** | |

**Scoring guide:**
- 5: Exceptional, sets the standard (Apple, Stripe level)
- 4: Strong, minor polish needed
- 3: Adequate, noticeable gaps but functional
- 2: Below standard, significant issues
- 1: Failing, fundamental problems

## 5. Clutter and Cognitive Load Deep-Dive

This section is mandatory and must be substantive. For each key screen:

- **Screen:** <name + screenshot reference>
- **Element count:** approximate number of distinct visual elements
- **Competing actions:** list any cases where multiple elements vie for primary attention
- **What could be removed:** specific elements that don't earn their place
- **Decision load:** how many choices the user faces, and whether that's appropriate
- **Verdict:** clean / acceptable / cluttered / overwhelming

## 6. Accessibility Summary

Dedicated section because accessibility failures are often invisible to sighted evaluators:

- **Keyboard navigability:** pass / partial / fail + details
- **Focus indicators:** present / inconsistent / absent
- **Heading hierarchy:** correct / issues found
- **Form labels:** all labeled / gaps found
- **Color as sole indicator:** none found / issues found
- **Contrast:** passes / issues found (cite specific elements)
- **Touch targets (mobile):** adequate / undersized (cite specific elements)
- **Dark pattern check:** clean / issues found

## 7. Recommendations

For each, tie to a specific issue from section 3:

- **Issue:** <reference>
  **Recommendation:** <concrete fix: name the element, the change, and the expected effect>
  **Type:** Subtraction | Simplification | Restructure | Addition
  **Effort:** Low | Medium | High
  **Impact:** Low | Medium | High

(Prefer Subtraction and Simplification. If recommending an Addition, justify why removal or simplification won't solve the problem.)

## 8. Quick Wins

Bulleted list of high-impact, low-effort changes. Each must:
- Name the specific element or screen
- Describe the exact change
- Explain the expected improvement

These should be concrete enough for a developer to implement without further design input.

## 9. Strategic Observations

Optional but valuable. 1 to 3 paragraphs on higher-level patterns:
- Is the product trying to do too many things?
- Is there a fundamental IA or conceptual problem?
- What would the Apple / Airbnb / Stripe version of this product prioritize differently?
- Where is the product relative to its maturity stage, and what should it focus on next?

## Appendix: Flows Walked

| # | Flow | Viewport | Screenshots |
|---|------|----------|-------------|
| 1 | <flow name> | Desktop | `01-landing-desktop.png`, `02-...` |
| 2 | <flow name> | Mobile | `04-landing-mobile.png`, ... |
```

Report the file path back to the user.

## Critical Rules

**Always:**
- Read AGENTS.md before evaluating. Context is non-negotiable.
- Form a design hypothesis before evaluating. Without one, findings lack a frame.
- Evaluate all seven dimensions explicitly. Partial audits are rejected.
- Tie every finding back to a user goal from AGENTS.md.
- Cite screenshots as evidence for every issue.
- Prefer subtraction over addition in recommendations.
- Be specific: name the element, name the change, name the expected effect.
- Walk the primary workflow end-to-end at least once.
- Perform the keyboard accessibility pass. Do not skip it.
- Test at three viewport sizes minimum.
- Flag dark patterns. Even one is a Critical finding.
- Close the browser when done.

**Never:**
- Evaluate the app in a vacuum. If context is missing, ask.
- Give generic advice ("improve the UX", "make it more intuitive", "consider accessibility").
- Recommend additions when removing or simplifying would solve the problem.
- Inflate severity. Critical means it blocks the primary workflow, breaks trust, or excludes users.
- Skip the clutter and confusion assessment. It is the most important section.
- Skip the accessibility assessment. It is the second most important section.
- Fabricate findings. Every issue needs a screenshot or interaction trace.
- Praise things that are merely adequate. Reserve positive callouts for genuinely exceptional craft.
- Ignore dark patterns. If you see confirmshaming, hidden costs, forced continuity, or trick questions, flag them as Critical regardless of visual polish.

## Quality Checklist

Before delivering:

- [ ] AGENTS.md (or fallback context) was read and summarized in section 1
- [ ] Design hypothesis formed and stated
- [ ] Five-second test performed and documented
- [ ] Primary workflow walked end-to-end
- [ ] At least one form exercised (empty submit, invalid input, valid input)
- [ ] Error states and empty states exercised
- [ ] At least one alternate path explored
- [ ] Keyboard accessibility pass completed (Tab through primary flow)
- [ ] Heading hierarchy and form labels checked via snapshot
- [ ] Three viewports tested (desktop, tablet, mobile)
- [ ] Console errors and network failures checked
- [ ] Screenshots saved under `docs/ux-audits/<slug>/screenshots/`
- [ ] Every issue in section 3 cites a screenshot and names a dimension
- [ ] All seven dimension scorecards completed
- [ ] Clutter and cognitive load deep-dive completed (not skipped, not hand-waved)
- [ ] Accessibility summary completed with pass/fail per criterion
- [ ] Dark pattern check explicitly performed and documented
- [ ] Recommendations are concrete, typed, and effort-rated
- [ ] Quick Wins are genuinely low-effort and developer-actionable
- [ ] Browser closed
