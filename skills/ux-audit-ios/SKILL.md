---
name: ux-audit-ios
description: Conduct a comprehensive UX audit of an iOS app running in the Simulator. Captures screenshots via xcrun simctl, tests Dynamic Type and Dark Mode and Bold Text configurations, and produces a severity-ranked report covering all seven design dimensions against Apple HIG standards.
---

# UX Audit (iOS)

A systematic technique for evaluating an iOS app running in the Simulator. Uses a guided interaction model (the user navigates; the auditor captures screenshots and analyzes). Produces a severity-ranked report against Apple HIG.

## Core Evaluation Dimensions

Every audit assesses all seven dimensions adapted for iOS. Skipping any produces an incomplete audit.

| # | Dimension | What you're evaluating |
|---|-----------|----------------------|
| 1 | **Accessibility & Inclusivity** | Dynamic Type support, VoiceOver readiness, contrast ratios, touch targets (44pt minimum per HIG), Reduce Motion respect, Bold Text support, color not used as sole indicator |
| 2 | **Design System Coherence** | Consistent use of SF Symbols, system vs. custom components, typographic scale, spacing rhythm, color palette intentionality, dark mode fidelity |
| 3 | **Information Architecture** | Tab bar structure, navigation hierarchy depth, sheet/modal usage, back-button predictability, deep link handling |
| 4 | **Interaction Design** | Gesture vocabulary, haptic feedback, transitions, pull-to-refresh, swipe actions, long press menus, loading and skeleton states, error recovery |
| 5 | **Content & Microcopy** | Label clarity, error message quality, empty state messaging, onboarding copy, permission request framing, action verb specificity |
| 6 | **Emotional Design & Trust** | First-launch impression, permission request timing, onboarding respect, delight moments, App Store trust alignment, dark pattern absence |
| 7 | **Cognitive Load & Clarity** | Clutter, competing actions, decision fatigue, information density, signal-to-noise ratio, tab bar complexity, bottom sheet overuse |

## Required Workflow

### Step 0: Understand Context

1. Locate the project's `AGENTS.md` (try the working directory; fall back to `CLAUDE.md` if missing)
2. Read it fully and extract:
   - Product purpose
   - Target user (who they are, what they know, what they need)
   - Primary workflows / jobs-to-be-done
   - Any stated design principles or brand values
3. If neither file exists or context is too thin to evaluate against, **stop and ask the user** for: product purpose, primary user, and the top 1 to 3 workflows to evaluate. Do not proceed in a vacuum.
4. Form a **design hypothesis**: given this user and this goal, what should the ideal experience feel like? Snappy and confident? Calm and guided? Playful and discoverable? This hypothesis frames every finding below.

### Step 1: Parse Input and Verify Simulator

`$ARGUMENTS` should contain the app's bundle ID, app name, or other identifier. If missing, ask for it. Optionally accept extra hints (specific flows to focus on, test account credentials, known pain points).

**Verify the Simulator is ready:**

```bash
# Check for a booted simulator
xcrun simctl list devices booted
```

If no simulator is booted, tell the user:
> No booted simulator found. Please launch the iOS Simulator with your app running, then re-run this audit. You can boot a simulator with:
> `xcrun simctl boot <device-id>` or open it from Xcode.

If a simulator is booted but the app may not be running, note this and ask the user to confirm the app is on screen.

Create the output directory: `docs/ux-audits/`. Determine an audit slug: `<YYYY-MM-DD>-<app-name>`. Screenshots will live under `docs/ux-audits/<slug>/screenshots/`.

Clean the status bar for professional screenshots:

```bash
xcrun simctl status_bar booted override --time "9:41" --batteryLevel 100 --batteryState charged --cellularBars 4 --wifiBars 3
```

### Step 2: Explore the App (Guided via Simulator)

Because `xcrun simctl` cannot interact with UI elements semantically (no equivalent to Playwright's `click` or `type`), this audit uses a **guided interaction model**: you capture screenshots and the user navigates on your behalf.

**How to interact with the user:**

- Be specific about what you need: "Please tap the 'Sign Up' button" not "navigate to registration"
- After each request, capture a screenshot to verify the state
- Batch related navigation requests when possible: "Please complete the sign-up form with test data and tap Submit. I'll screenshot the result."
- If the user says they can't reach a state (e.g., "I don't have test data for that"), note it as untested and move on

**Screenshot capture pattern:**

```bash
xcrun simctl io booted screenshot docs/ux-audits/<slug>/screenshots/<filename>.png
```

Use descriptive, numbered filenames: `01-landing-light.png`, `02-tab-home.png`, `03-signup-form.png`, etc.

## 2a. First impression (5-second test)

1. Capture the current screen (the app's landing/home state)
2. Assess from the screenshot alone:
   - Can you identify what this app does within 5 seconds?
   - Is the primary action obvious?
   - What is the visual hierarchy communicating (1st, 2nd, 3rd level)?
   - What emotion does the screen evoke?
   - Does it feel like a native iOS app or a wrapped web view?

## 2b. Primary workflow walkthrough

Walk the primary workflow from AGENTS.md end-to-end:

1. Identify the entry point and ask the user to navigate there if not already
2. At each step, capture a screenshot
3. Note: tap count to reach the goal, clarity of progress, confidence level at each step
4. Ask the user to complete the flow successfully at least once
5. After each screen transition, capture and evaluate before requesting the next action

## 2c. Edge cases and error states

Ask the user to trigger these, capturing screenshots of each:

- Empty form submission (validation behavior)
- Invalid input (error message quality, inline vs. alert)
- Successful submission (confirmation: inline, toast, modal, or new screen?)
- Empty states (no data, first-time user, search with no results)
- Loading states (if observable, ask user to trigger on slow network or note if tested)
- Navigation back (state preservation after going back)
- At least one alternate or secondary path

If a state cannot be triggered, note it as **untested** rather than skipping silently.

## 2d. Accessibility configurations

Test each configuration programmatically, capturing screenshots after each change:

```bash
# Dynamic Type: test at two extremes
xcrun simctl ui booted content_size extra-large
# Screenshot, then:
xcrun simctl ui booted content_size accessibility-extra-extra-extra-large
# Screenshot, then reset:
xcrun simctl ui booted content_size large
```

```bash
# Dark mode
xcrun simctl ui booted appearance dark
# Screenshot key screens, then:
xcrun simctl ui booted appearance light
```

```bash
# Bold text
xcrun simctl ui booted increase_contrast enabled
# Screenshot, then:
xcrun simctl ui booted increase_contrast disabled
```

For each configuration, capture the primary screen and the most critical screen of the primary workflow. Assess:

- **Dynamic Type:** Does text scale? Do layouts accommodate larger text or does it clip/overlap/truncate? Do touch targets remain adequate?
- **Dark mode:** Are all elements visible? Any hardcoded colors that don't adapt? Are images/icons legible on dark backgrounds? Is contrast maintained?
- **Bold text / increased contrast:** Does the app respond? Are boundaries and text clearer?

## 2e. Device size evaluation

If time permits and the user can switch simulators, request screenshots from:

- iPhone SE (small: 375x667) - does the layout compress gracefully?
- iPhone 16 Pro Max (large: 430x932) - is the extra space used well or just padded?
- iPad (if applicable) - does the app use split view, sidebars, or just scale up the phone layout?

If switching simulators is impractical, note it as a limitation and evaluate based on the current device's screenshots.

## 2f. System integration checks

Ask the user to verify (or capture evidence of):

- Permission request dialogs: when do they appear? Is there a pre-permission screen explaining why?
- Notification appearance (if applicable)
- Share sheet integration (if applicable)
- Widget appearance (if applicable)
- Spotlight search indexing (if applicable)

Note any that are not applicable or not testable.

Save all screenshots into `docs/ux-audits/<slug>/screenshots/` with descriptive, numbered filenames.

Keep a running log of (screenshot filename, what it shows, which flow step, which configuration). You will cite these in the report.

### Step 3: Evaluate Against All Seven Dimensions

For each dimension, evaluate every screen and flow you captured. This is the analytical core of the audit.

## Dimension 1: Accessibility & Inclusivity

- Dynamic Type: does the app scale text at all sizes? Layout integrity at XXXL?
- Touch targets: minimum 44x44pt per Apple HIG (stricter than web's 44x44 CSS px)
- Color: not used as sole indicator of state (errors, selections, toggles)
- Contrast: text, icons, and interactive element boundaries
- Dark mode: full support or partial/broken?
- Bold Text: does the app respond to the system setting?
- Reduce Motion: are there animations that might be problematic? (Note: hard to verify from screenshots alone; flag if heavy animations are visible)
- VoiceOver readiness: are custom controls clearly labeled? Are images decorative or informational? (Inferred from visual inspection; note limitations)

## Dimension 2: Design System Coherence

- SF Symbols: used consistently? Or a mix of SF Symbols and custom icons?
- System components: UIKit/SwiftUI standard controls where appropriate? Or custom components that fight user expectations?
- Typography: how many distinct text styles? Does it use the iOS type scale (Large Title, Title, Headline, Body, etc.) or custom?
- Spacing: consistent rhythm or ad-hoc?
- Color: intentional palette? Do colors carry consistent meaning? Do they adapt to dark mode?
- Component consistency: are similar elements (cells, buttons, inputs) rendered the same way across screens?
- Overall: does this feel like one app or several stitched together?

## Dimension 3: Information Architecture

- Tab bar: how many tabs? (HIG recommends 3-5.) Is the primary action accessible from the default tab?
- Navigation depth: how many levels deep does the hierarchy go? More than 3 levels creates "where am I?" anxiety
- Modal/sheet usage: are modals used for focused tasks or as a lazy navigation pattern?
- Back button: does it always work predictably? Is state preserved?
- Search: is content findable? Is search prominent enough for the content volume?

## Dimension 4: Interaction Design

- Gesture vocabulary: does the app use standard iOS gestures (swipe back, pull to refresh, swipe to delete)? Any custom gestures without discoverability cues?
- Haptic feedback: noted if the user reports it; otherwise flag where haptics would be expected (destructive actions, mode changes, selections)
- Transitions: do navigation transitions follow iOS conventions (push/pop, modal present/dismiss)? Any jarring custom transitions?
- Feedback: does every tap produce a visible response? Buttons that don't highlight on press feel broken.
- Loading: spinner vs. skeleton screen vs. blank. Is progress communicated?
- Error recovery: when something fails, is the path back obvious?
- Destructive actions: confirmation before delete? Can it be undone?

## Dimension 5: Content & Microcopy

- Labels: specific action verbs or vague ("OK", "Done", "Continue")?
- Error messages: informative + actionable, or generic ("Something went wrong")?
- Empty states: helpful guidance with a clear CTA, or a sad face and nothing else?
- Permission requests: pre-permission screen that explains value before the system dialog?
- Onboarding copy: respectful of time, or a 5-screen carousel the user will skip?
- Tone: consistent with brand? Appropriate to the moment?

## Dimension 6: Emotional Design & Trust

- First launch: does the app feel trustworthy and polished from the first screen?
- Onboarding: does it respect the user's time? Can it be skipped? Does it teach by doing?
- Permission timing: asks for permissions in context (e.g., camera access when taking a photo) vs. up front (app launch bombardment)?
- Delight: any small moments of craft that signal care? (Animations, illustrations, micro-interactions)
- Dark patterns: forced account creation before value is shown, confirmshaming in cancellation flows, hidden subscription traps, difficulty deleting account. Flag ANY instance.
- App Store alignment: does the in-app experience match what the App Store listing promises?

## Dimension 7: Cognitive Load & Clarity

This remains the most important dimension. Every screen gets this assessment:

- Element count: how many distinct things compete for attention?
- Action clarity: is the primary action obvious without reading every label?
- Decision load: how many choices is the user asked to make simultaneously?
- Information density: signal-to-noise ratio. What could be removed without loss?
- Tab bar clarity: are tab icons + labels immediately understandable?
- Bottom sheet / action sheet overuse: are these used for appropriate tasks or as a dumping ground?
- Scanning path: does the eye flow naturally from most important to least?

### Step 4: Write the Report

Save to `docs/ux-audits/<slug>.md`. Reference screenshots with relative paths (e.g., `![Landing](./<slug>/screenshots/01-landing-light.png)`).

```markdown
# UX Audit: <App Name> (iOS)

**Date:** <today's date>
**App:** <app name + bundle ID if known>
**Simulator:** <device model + iOS version>
**Auditor:** UX Product Designer Agent (iOS)
**Design hypothesis:** <one sentence: what should this experience feel like for the target user?>

---

## 1. Product Understanding

- **Purpose:** <from AGENTS.md>
- **Target user:** <from AGENTS.md>
- **Primary workflow(s) evaluated:** <list>
- **Design hypothesis:** <expanded: given this user and goal, the experience should feel [X]. It should prioritize [Y] over [Z]>

[1 to 2 paragraphs framing what the product is trying to do for whom, in your own words. This is the lens for everything below.]

## 2. First Impression

What the landing screen communicates before any interaction:

- **Can I tell what this does?** Yes/No + explanation
- **Is the primary action obvious?** Yes/No + explanation
- **Does it feel native?** Yes/No + explanation (system components, navigation patterns, platform conventions)
- **What emotion does this evoke?** <describe>
- **Screenshot:** <reference>

## 3. Issues (Ranked by Severity)

For each issue:

### [Severity] <Short title>

- **Dimension:** <which of the 7 dimensions>
- **Description:** <what's wrong>
- **HIG reference:** <relevant Apple HIG section, if applicable>
- **Why it matters:** <tie back to user goal; what does it cost the user?>
- **Evidence:** <screenshot reference + flow step + configuration (light/dark/XXXL/etc.)>

(Group by severity: Critical, High, Medium, Low. Within each, order by impact on the primary workflow.)

**Severity definitions:**

- **Critical:** Blocks the primary workflow, breaks trust, or excludes users (accessibility failure, data loss risk)
- **High:** Significantly degrades the experience or violates core HIG principles in a way users will notice
- **Medium:** Noticeable friction that doesn't block completion but erodes perceived quality
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

- 5: Apple-quality. Could be featured in an HIG case study
- 4: Strong, minor polish needed
- 3: Adequate, noticeable gaps but functional
- 2: Below standard, significant issues that erode trust
- 1: Failing, fundamental problems

## 5. Clutter and Cognitive Load Deep-Dive

This section is mandatory and must be substantive. For each key screen:

- **Screen:** <name + screenshot reference>
- **Element count:** approximate number of distinct visual elements
- **Competing actions:** list any cases where multiple elements vie for primary attention
- **What could be removed:** specific elements that don't earn their place
- **Decision load:** how many choices the user faces, and whether that's appropriate
- **Verdict:** clean / acceptable / cluttered / overwhelming

## 6. Accessibility Configuration Results

Dedicated section documenting how the app responds to system accessibility settings:

### Dynamic Type

- **Default size:** <observations>
- **Extra Large:** <observations, screenshot reference>
- **Accessibility XXXL:** <observations, screenshot reference>
- **Verdict:** full support / partial support / broken

### Dark Mode

- **Observations:** <what adapts, what doesn't>
- **Screenshot:** <reference>
- **Verdict:** full support / partial / hardcoded colors found

### Bold Text / Increased Contrast

- **Observations:** <does the app respond?>
- **Verdict:** supported / not supported

### Touch Targets

- **Minimum observed:** <estimate in points>
- **Problem areas:** <specific elements below 44pt>

### Dark Pattern Check

- **Result:** clean / issues found
- **Details:** <if issues found>

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

- Name the specific screen or element
- Describe the exact change
- Explain the expected improvement

These should be concrete enough for a developer to implement without further design input.

## 9. Strategic Observations

Optional but valuable. 1 to 3 paragraphs on higher-level patterns:

- Is the app fighting the platform or embracing it?
- Is there a fundamental navigation or conceptual problem?
- What would Apple's design team do differently?
- Is the app using SwiftUI/UIKit capabilities or leaving power on the table?
- Where is the app relative to its maturity stage, and what should it focus on next?

## 10. Untested Areas

List anything that could not be tested in this session:

- States that couldn't be triggered
- Features that require real data or accounts
- Haptic feedback (not verifiable from screenshots)
- VoiceOver navigation (requires manual testing)
- Performance under load
- Widget, Spotlight, or notification behavior

## Appendix: Flows Walked

| # | Flow | Configuration | Screenshots |
|---|------|---------------|-------------|
| 1 | <flow name> | Light, default text | `01-landing-light.png`, `02-...` |
| 2 | <flow name> | Dark mode | `08-landing-dark.png`, ... |
| 3 | <primary screen> | Dynamic Type XXXL | `12-home-xxxl.png`, ... |
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
- Test Dynamic Type at both extra-large and XXXL accessibility sizes.
- Test Dark Mode on the primary screen and the most critical flow screen.
- Reference Apple HIG when a finding relates to a documented guideline.
- Flag dark patterns. Even one is a Critical finding.
- Document what you could NOT test in section 10.
- Reset simulator appearance settings when done.

**Never:**

- Evaluate the app in a vacuum. If context is missing, ask.
- Give generic advice ("improve the UX", "make it more intuitive", "follow HIG").
- Recommend additions when removing or simplifying would solve the problem.
- Inflate severity. Critical means it blocks the primary workflow, breaks trust, or excludes users.
- Skip the clutter and confusion assessment. It is the most important section.
- Skip the accessibility configuration testing. It is the second most important section.
- Fabricate findings. Every issue needs a screenshot reference.
- Praise things that are merely adequate. Reserve positive callouts for genuinely exceptional craft.
- Ignore dark patterns. Confirmshaming, forced account creation before value, hidden subscriptions, or account deletion obstruction are all Critical.
- Assume the user can switch simulators. Work with what's booted.

## Quality Checklist

Before delivering:

- [ ] AGENTS.md (or fallback context) was read and summarized in section 1
- [ ] Design hypothesis formed and stated
- [ ] First impression assessment performed and documented
- [ ] Simulator verified as booted with app running
- [ ] Status bar cleaned for professional screenshots
- [ ] Primary workflow walked end-to-end (user-guided)
- [ ] At least one form or input flow exercised
- [ ] Error states and empty states captured (or noted as untested)
- [ ] At least one alternate path explored
- [ ] Dynamic Type tested at extra-large and XXXL
- [ ] Dark Mode tested on key screens
- [ ] Bold Text / Increased Contrast tested
- [ ] Screenshots saved under `docs/ux-audits/<slug>/screenshots/`
- [ ] Every issue in section 3 cites a screenshot and names a dimension
- [ ] All seven dimension scorecards completed
- [ ] Clutter and cognitive load deep-dive completed (not skipped, not hand-waved)
- [ ] Accessibility configuration results documented with pass/fail
- [ ] Dark pattern check explicitly performed and documented
- [ ] Untested areas honestly documented in section 10
- [ ] Recommendations are concrete, typed, and effort-rated
- [ ] Quick Wins are genuinely low-effort and developer-actionable
- [ ] Simulator appearance settings reset to defaults
