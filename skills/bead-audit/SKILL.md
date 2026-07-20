---
name: bead-audit
description: Audit one or more bead issue bodies against the Marr audit, size audit, and type-specific section audit. Separates a content verdict (is the substance there?) from a structure verdict (is it under the canonical heading or native field?), so a substantively complete bead in the wrong format is an auto-fixable reformat, not a failure. Produces an optional weighted scorecard (0-100, banded Poor/Weak/Adequate/Great/Excellent) derived from the verdicts and capped so the band can never contradict the pass/fail verdict, for ranking a backlog or targeting a quality band. Honors trackers with native fields (e.g. br's acceptance_criteria/design/notes), self-verifies every drafted fix so it re-passes, and gates write-back with an applyable flag so placeholder-bearing drafts never reach the tracker. Supports a machine-readable JSON output mode for backlog-scale grooming.
---

# Bead Audit

A systematic technique for evaluating bead issue bodies against the same content standards applied during decomposition. Borrows all audit logic from `plan-to-beads`: the Marr audit (Why/How/Done when quality), the size audit (diff-size band), and the type-specific section audit (Acceptance Criteria, Steps to Reproduce, Success Criteria).

This skill is agnostic to the issue tracker. It audits the *text* of a bead body. How that text is fetched, and whether corrected text is written back, is the caller's responsibility (a human pasting, a script looping over a backlog, or a `/goal`-style driver).

**Two principles that shape every check:**

1. **Content is not structure.** A bead whose Why/How/Done content is rich but written as `WHY:` prose instead of under `## Why (Computational)` is *correctly specified, wrongly formatted*. That is an auto-fixable reformat (WARN), never an under-specification (FAIL). The audit reports these as separate verdicts.
2. **One canonical structure.** The required headings per type live in exactly one place ("Canonical Bead Structure" below). The audit checks against that list and the drafting template reproduces it byte-for-byte, so a bead that this skill fixes is guaranteed to re-pass.

## When to Use

- Before claiming a bead, to make sure it has enough context to implement without re-reading the parent plan
- During backlog grooming to surface under-specified issues at scale (use JSON mode)
- After inheriting a project or picking up someone else's work
- Before a sprint to verify every in-scope bead is implementation-ready
- After running `/plan-to-beads` on a modified plan to verify the generated beads meet the bar
- To rank a backlog by quality, or gate on a target band, using the Scorecard (request a score; use JSON mode for a loop)

## When NOT to Use

- To audit a plan document (use `/plan-review` for that)
- For content that is not a bead body (e.g., raw meeting notes, a user story in a different format)

## Canonical Bead Structure

This is the single source of truth for required headings. The audit and the drafting template both reference this list. Heading strings are byte-exact and match `plan-to-beads`.

| Section | Heading (byte-exact) | Required for |
|---|---|---|
| Why | `## Why (Computational)` | all types |
| How | `## How (Algorithmic)` | all types |
| Done when | `## Done when (Acceptance)` | all types |
| Acceptance Criteria | `## Acceptance Criteria` | task, feature, bug |
| Steps to Reproduce | `## Steps to Reproduce` | bug |
| Success Criteria | `## Success Criteria` | epic |
| Estimated size | `## Estimated size` | task, feature, bug (code-bearing). N/A for epic and operational beads |
| Out of scope | `## Out of scope (optional)` | optional, any type |

### Done when vs. Acceptance Criteria (normative)

These are **not** duplicates. They sit at different altitudes and a complete bead has both:

- **Done when (Acceptance)** states the *outcome-level* conditions that mean the work is finished. This is the implementer's definition of done, phrased as observable end states.
- **Acceptance Criteria** is the *formal, testable checklist* a reviewer or QA walks through to verify those outcomes. Prefer Given/When/Then or a numbered list of concrete, individually-checkable assertions.

Rule of thumb: if you can hand the line to QA and they can mark it pass/fail without interpretation, it belongs in **Acceptance Criteria**. If it describes the end state in the implementer's words, it belongs in **Done when**.

**Worked example** (a "rate-limit failed logins" bead):

```markdown
## Done when (Acceptance)
- Repeated failed logins from one source are throttled.
- The threshold is configurable without a redeploy.

## Acceptance Criteria
1. Given 5 failed logins in 60s from one IP, When a 6th is attempted, Then the response status is 429.
2. Given the RATE_LIMIT env var is changed, When config reloads, Then the new limit applies without a process restart.
3. Given a successful login, When the rolling window elapses, Then the failure counter resets to 0.
```

## Heading Recognition

The audit detects a section's **content** by matching the leading keyword of any heading or label, case-insensitively, ignoring decoration (leading `#`, `*`, `:`, a hyphen, or a dash). It detects a section's **structure** by checking whether that content sits under the byte-exact canonical heading.

| Section | Recognized as this section | Canonical (structure passes) |
|---|---|---|
| Why | `## Why`, `### Why`, `**Why:**`, `Why:`, `WHY:`, `Why -` | `## Why (Computational)` |
| How | `## How`, `**How:**`, `How:`, `HOW:` | `## How (Algorithmic)` |
| Done when | `## Done`, `## Done when`, `Done when:`, `DONE WHEN:` | `## Done when (Acceptance)` |
| Acceptance Criteria | `## Acceptance Criteria`, `Acceptance Criteria:`, `AC:` | `## Acceptance Criteria` |
| Steps to Reproduce | `## Steps to Reproduce`, `Repro:`, `Steps:` | `## Steps to Reproduce` |
| Success Criteria | `## Success Criteria`, `Success Criteria:` | `## Success Criteria` |
| Estimated size | `## Estimated size`, `Size:`, `Estimate:` | `## Estimated size` |

If content for a section is found only under a variant (or as labeled inline prose), the **content** check evaluates the substance normally and the **structure** check returns `variant` (an auto-fixable reformat). Content is treated as absent only when no recognized heading or label carries substance for that section.

### Trackers with native structured fields

Some trackers expose first-class fields for sections that this skill otherwise expects as body headings. For example, `br` has dedicated `acceptance_criteria`, `design`, and `notes` fields separate from `description`, and surfaces them as their own blocks in `br show`. Other tooling (`br ready`, reporting, dashboards) reads those native fields directly.

When a tracker has a native field for a section, **the audit applies to that field's content, not to a body heading**, and the field counts as canonical structure:

| Canonical section | Maps to native field (when the tracker has one) | Example: `br` |
|---|---|---|
| Acceptance Criteria | the acceptance-criteria field | `--acceptance-criteria` (alias `--acceptance`) |
| How (Algorithmic) | the design / approach field | `--design` |
| Done when / Out of scope / supporting detail | the notes field | `--notes` |
| Why, and anything without a native slot | the description / body field | `-d` / `--description` |

Rules when native fields are present:

- A section whose content lives in the correct native field is `structure: canonical`. Do not flag it for "missing heading."
- A section's content duplicated into the body when a native field exists for it is `structure: variant` (reformat: move it to the native field, do not embed a heading in the description).
- When **drafting a fix**, populate the native field rather than appending a heading to the body. For `br`, that means `br update <id> --acceptance-criteria "..."` and `br update <id> --design "..."`, not stuffing `## Acceptance Criteria` into `--description`.
- The canonical headings still govern plain-markdown trackers (GitHub Issues, a pasted blob) and the in-body fallback when no native field exists.

If you cannot tell whether the tracker has native fields (e.g., the user pasted a plain body), audit against the canonical headings and note that a fix may belong in a native field if the destination tracker has one.

## Audit Dimensions

Every required section gets two independent verdicts:

- **Content verdict** - is the substance present and adequate? Drives FAIL.
  - `pass`: substance present and meets the quality bar
  - `warn`: present but weak (borderline; flagged for the author)
  - `fail`: absent, vacuous, or a restatement of the title
- **Structure verdict** - is the substance under the canonical heading?
  - `canonical`: under the byte-exact heading
  - `variant`: under a recognized variant or inline label (auto-fixable reformat)
  - `absent`: no heading at all; content was found by inference (auto-fixable reformat)

A section with `content: pass` and `structure: variant` is a **reformat**, not a failure. This is the single most important behavior of the skill.

### 1. Marr Audit (Why / How / Done when)

Content quality bar per section:

| Section | content: pass | content: fail |
|---|---|---|
| Why | Names a stakeholder, motivating constraint, or downstream consumer | Absent, just a restatement of the title, or says only "this is needed" |
| How | States an approach or strategy with at least one key decision or trade-off | Absent, is actually Level 3 implementation detail ("edit `app.py` line 42"), or says only "implement the feature" |
| Done when | At least one outcome-level condition a second person could verify without asking the author | Absent, or vague: "it works", "tests pass" (without naming which), "feature is complete", "looks good" |

### 2. Size Audit

Evaluates the `## Estimated size` section against the diff-size window. **This dimension does not apply to every bead.**

| Band | Files | LOC | Verdict |
|---|---|---|---|
| **N/A (umbrella)** | - | - | Pass. Epics coordinate child beads and carry ~0 direct diff. Never FAIL an epic on size |
| **N/A (operational)** | - | - | Pass. Ops/chore/infra beads (config, deploy, manual production change, external-system work) have no meaningful repo diff |
| **Trivial** | 1 | < 20 | Warn: should be a direct commit, not a bead |
| **Target** | 1-5 | 20-300 | Pass |
| **Stretch** | up to 10 | up to 600 | Pass only if a one-sentence justification is present |
| **Too big** | > 10 | > 600 | Fail: must be split |
| **Hard ceiling** | > 30 | > 2000 | Fail: cannot ship autonomously |

**When dimensions disagree, the worse band wins** (code-bearing beads only).

**Applicability rules:**

- **Epics** are always `N/A (umbrella)`. The `## Estimated size` section is not required and its absence is not a finding.
- **Operational beads** (work is config/deploy/infra/manual ops with no meaningful code diff, evident from the type or the How) are `N/A (operational)`. A `## Estimated size` of "N/A (operational)" passes; absence is not a finding.
- **Code-bearing beads** (task/feature/bug that change the repo) require `## Estimated size`. If it is absent, flag it as a missing section (a content FAIL on size), not a band failure. Do not guess a band from the title or body **for the purpose of scoring** (you may not invent a passing band to suppress the FAIL during the audit).

**Size is the one section where a drafted fix may infer a value.** The audit rule "do not guess a band" governs *scoring*; it does not forbid a *drafted fix* from supplying a reasonable estimate. When fixing a missing `## Estimated size`, derive a provisional band from the How (file/module count, port vs. greenfield) and mark it explicitly as provisional:

```markdown
## Estimated size
~3 files, ~150 LOC, band: Target (provisional - inferred from the How, author to confirm)
```

A provisional size estimate is **not** a blocking `[AUTHOR TO COMPLETE]` placeholder (see "Drafting Corrected Content"); it is low-risk and safe to write back, but it must carry the `(provisional ...)` marker so the author knows it was inferred. If the How is too thin to infer even a band, then fall back to `[AUTHOR TO COMPLETE: estimate size]`, which *does* block write-back.

### 3. Type-specific Section Audit

Checks for sections required by the bead's declared type. The type is taken from whichever field in the provided content names the issue type (a `Type:` metadata line, a `<!-- type: bug -->` annotation, or the caller's explicit statement). Default to `task` if the type cannot be determined, and flag this as a WARN (missing type declaration).

| Type | Required sections | content: pass criteria |
|---|---|---|
| `task` | Acceptance Criteria | At least one testable, observable condition |
| `feature` | Acceptance Criteria | At least one testable, observable condition |
| `bug` | Acceptance Criteria + Steps to Reproduce | AC: at least one observable condition; Steps: numbered steps with expected vs. actual behavior |
| `epic` | Success Criteria | At least one outcome-level indicator legible to a product stakeholder who has not read child beads |

These sections also get the content/structure split: rich Acceptance Criteria written as `AC:` prose is a reformat (WARN), not a missing-section FAIL.

## Verdict Model

Each bead rolls up to one of three overall states:

| Overall | Condition | Caller action |
|---|---|---|
| **PASS** | Every content verdict is `pass` AND every structure verdict is `canonical` | None |
| **REFORMAT** | Every content verdict is `pass` (or N/A) but at least one structure verdict is `variant`/`absent`, or a Trivial-band warn | Auto-fixable: reformat to canonical headings, no human input needed |
| **NEEDS WORK** | At least one content verdict is `fail` (genuine under-specification or missing required section) | Human input may be required; see drafting guidance |

A WARN on content (borderline-weak) rolls up to REFORMAT if the author chooses to leave it, or NEEDS WORK if they want it tightened. Treat content WARN as REFORMAT-tier for gating purposes unless the caller asks for strict mode.

## Scorecard

The three-state verdict answers "is this bead done?" The scorecard answers "how close, and which band?" so a caller (a human triaging, or a refinement loop targeting a band) can rank and gate. The score **refines the verdict; it never overrides it.** The bands are constructed so that Excellent is exactly equivalent to PASS.

### The score is derived, never asserted

Every point traces to a verdict this skill already produced in the Audit Dimensions above. You may not assign a score directly, and a report that states a score must show the per-dimension verdicts and the weighted sum beside it, so the arithmetic is checkable. Inflating a score is therefore visible, and (because of the caps below) cannot by itself lift a bead past its verdict ceiling.

### Weights

| Dimension | Weight | Applies to |
|---|---|---|
| Why (Computational) | 20 | all types |
| How (Algorithmic) | 20 | all types |
| Done when (Acceptance) | 20 | all types |
| Acceptance Criteria (Success Criteria for `epic`) | 20 | all types |
| Steps to Reproduce | 10 | `bug` only |
| Estimated size | 10 | code-bearing beads only |
| Structure | 10 | all types |

**Content points per dimension:** `pass` earns the full weight, `warn` half, `fail` zero.

**Structure points:** `10 × (canonical required sections ÷ total required sections)`. A section that is `variant` or `absent` is not canonical; a section in its correct native field (per "Trackers with native structured fields") is canonical.

### Renormalization (off the audit's own N/A verdict)

The denominator is the sum of applicable weights, not a fixed 100. A dimension is **excluded from both numerator and denominator whenever this skill's own audit already recorded it N/A** (per the Size Audit's applicability rules: `N/A (umbrella)` for epics, `N/A (operational)` for ops beads, and Steps to Reproduce for any non-bug type). This ties applicability to a verdict the skill computed, not to a fresh type or label guess, so it cannot contradict the Size Audit and cannot be gamed by re-declaring a bead operational at scoring time. When a dimension is dropped, the report must name it and the reason ("size N/A (operational), excluded").

There is no `pass`/`warn`/`fail` for an N/A dimension, so it is never scored zero; it simply leaves the denominator.

### Bands, capped by verdict

Compute the raw score, map it to a band, then take the **lower** of that band and the ceiling implied by the rollup verdict:

| Band | Score |
|---|---|
| Excellent | 90-100 |
| Great | 75-89 |
| Adequate | 60-74 |
| Weak | 40-59 |
| Poor | below 40 |

| Rollup verdict | Condition | Band ceiling |
|---|---|---|
| NEEDS WORK | any required-section content `fail` | Weak |
| REFORMAT (structure) | all content `pass`, any structure `variant`/`absent` | Great |
| REFORMAT (weak content) | any content `warn`, no content `fail` | Great |
| REFORMAT (Trivial-band warn) | all content `pass`, structure canonical, size band Trivial | Great |
| PASS | all content `pass`, all structure `canonical`, size not Trivial | Excellent (no cap) |

The caps exist because the raw score contradicts the verdict at realistic inputs. Worked examples, computed from the weights and rules above:

| Bead state | Raw | Uncapped | Ceiling | Reported |
|---|---|---|---|---|
| task, all sections pass, canonical, size Target | 100.0 | Excellent | Excellent | **Excellent** |
| task, no Acceptance Criteria (content fail) | 78.0 | Great | Weak | **Weak** |
| task, all content pass, every heading variant | 90.0 | Excellent | Great | **Great** |
| bug, no Steps to Reproduce (content fail) | 89.4 | Great | Weak | **Weak** |
| task, all content warn, canonical | 55.0 | Weak | Great | **Weak** |
| task, all pass, canonical, size Trivial | 95.0 | Excellent | Great | **Great** |
| epic, all sections pass, size N/A | 100.0 | Excellent | Excellent | **Excellent** |

The lower-of-two rule means a cap only ever pulls a band down (rows 3 and 6); it never lifts one, so a NEEDS WORK bead can never report above Weak no matter how high its raw score (rows 2 and 4). The bug row denominator is 110 (Why+How+Done+AC+Steps+Size = 100, plus Structure 10), and 5 of 6 sections canonical gives structure `10 × 5/6`; recompute it to confirm the skill and the caller agree.

### Scorecard in the report

When a score is requested, extend the per-bead table (Step 4) with a trailing `points` column and print `Score: N/100 → Band` under the Overall line. In JSON mode, add `score` (number) and `band` (string) to each bead object.

## Required Workflow

### Step 1: Receive Bead Content

Accept bead content in whatever form the user provides:

- **Pasted body text** - the user pastes the bead body directly
- **File path** - read the file at the given path
- **Issue tracker output** - the user pastes or pipes the output of their CLI (`bd show <id>`, `br show <id>`, `gh issue view <id>`, etc.)
- **Multiple beads** - any of the above repeated, or a file containing multiple bead bodies

Do not assume any particular CLI is available. If the user provides IDs but no content, ask how to fetch the bodies. If nothing is provided, ask for at least one bead.

### Step 2: Parse Each Bead

For each bead body, extract:

- **Title** - from a `Title:` line, a top-level `#` heading, or the caller's label
- **Type** - from a `Type:` line, an annotation, or the caller's statement; default to `task` with a WARN if absent
- **Sections** - locate each canonical section via "Heading Recognition". Record, per section, the substance found and which heading carried it (canonical / variant / absent)

A heading with no following content is treated as having no content for that section.

### Step 3: Run All Applicable Audits Per Bead

For each bead, evaluate every applicable dimension. Produce a content verdict and a structure verdict for each required section, per "Audit Dimensions". Skip the size dimension for epics and operational beads (record it as N/A, not as a finding).

### Step 4: Present the Audit Report

Default output is human markdown (see "Output Modes" for JSON). For each bead:

````markdown
## Bead: <Title> (type: <type>)

| Section | Content | Structure | Note |
|---|---|---|---|
| Why (Computational) | pass / warn / fail | canonical / variant / absent | <reason if not clean> |
| How (Algorithmic) | pass / warn / fail | canonical / variant / absent | |
| Done when (Acceptance) | pass / warn / fail | canonical / variant / absent | |
| Acceptance Criteria | pass / warn / fail | canonical / variant / absent | |
| Estimated size | pass / warn / fail / N/A | n/a | <band, or "N/A (umbrella)"> |

**Overall: PASS / REFORMAT / NEEDS WORK**

<one sentence: for REFORMAT, what will be reformatted; for NEEDS WORK, the most critical content gap>
````

When a score is requested (a caller targeting a band, or a human asking for one), add a trailing `Points` column to the table (the weighted contribution of each dimension, e.g. `20/20`, `10/20`, `size excluded`) and a line under Overall:

```markdown
Score: N/100 → Band   (denominator D after excluding <named N/A dimensions>)
```

After all beads:

````markdown
## Audit Summary

| Title | Type | Overall | Score | Band |
|---|---|---|---|---|
| ... | ... | PASS / REFORMAT / NEEDS WORK | N/100 | Excellent / Great / ... |

PASS: X   REFORMAT (auto-fixable): Y   NEEDS WORK: Z   (of N total)
````

The `Score` and `Band` columns are present only when scoring was requested; omit them for a plain pass/fail audit.

### Step 5: Offer to Draft Fixes

If any bead is REFORMAT or NEEDS WORK, offer to draft corrected bodies:

- **REFORMAT beads** can be fixed mechanically: move the existing substance under canonical headings (or into the correct native field). No new information needed. Draft these without asking.
- **NEEDS WORK beads** need real content. Draft what can be inferred; for anything that cannot, insert `[AUTHOR TO COMPLETE: <what is needed>]` and flag it.

Present each corrected body in a fenced block labeled with the bead title, ready to apply. State what changed per section (one line each).

**A drafted body containing `[AUTHOR TO COMPLETE]` is not "fixed."** Mark it clearly as `applyable: false` (DO NOT APPLY). The placeholder *is* the needs-human boundary: it must reach a person, not get written back to the tracker. A provisional size estimate carrying a `(provisional ...)` marker does **not** make a draft unapplyable; only a `[AUTHOR TO COMPLETE]` placeholder does.

### Step 6: Self-Verify Each Draft (idempotency check)

The skill's core promise is "a bead this skill fixes re-passes the audit." That promise is only real if you check it. Before returning any corrected body, **re-run the audit against your own draft**:

1. Run Heading Recognition over the draft. Every required section for the type must resolve to `structure: canonical` (or sit in the correct native field).
2. Re-evaluate each content verdict against the draft. Every required section must be `content: pass` (size may be `pass` with a provisional marker).
3. Scan for any remaining `[AUTHOR TO COMPLETE]` placeholder. If one exists, the draft is `applyable: false`.

A draft is `applyable: true` only when (1) and (2) hold and (3) finds no placeholder. If a draft you intended to be a clean fix does not re-pass, fix the draft and repeat; do not return a draft that fails its own audit.

## Output Modes

**Markdown (default).** The tables in Step 4. For human review.

**JSON (`--json`, or when the caller requests structured output).** Emit a single JSON object so a grooming loop can gate programmatically. The skill does not write to any tracker; it returns this object and the caller applies it.

```json
{
  "beads": [
    {
      "id": "<id or title>",
      "type": "task|feature|bug|epic",
      "overall": "pass|reformat|needs_work",
      "score": 100,
      "band": "excellent|great|adequate|weak|poor",
      "score_denominator": 100,
      "excluded_dimensions": ["estimated-size"],
      "checks": [
        {
          "dimension": "marr|size|type-specific",
          "check": "why|how|done-when|estimated-size|acceptance-criteria|steps-to-reproduce|success-criteria",
          "content": "pass|warn|fail|n/a",
          "structure": "canonical|variant|absent|n/a",
          "points": 20,
          "note": "string"
        }
      ],
      "corrected_body": "string or null",
      "corrected_fields": { "description": "string|null", "design": "string|null", "acceptance_criteria": "string|null", "notes": "string|null" },
      "applyable": true,
      "blocked_on": ["why", "estimated-size"]
    }
  ],
  "summary": { "total": 0, "pass": 0, "reformat": 0, "needs_work": 0, "applyable": 0, "blocked_on_human": 0 }
}
```

Field semantics for a caller (e.g., a `/goal` loop):

- `corrected_body` is the full markdown fix (canonical headings). `null` for PASS beads.
- `corrected_fields` is the optional native-field breakdown for trackers like `br` (write `acceptance_criteria` to `--acceptance-criteria`, `design` to `--design`, etc., instead of one body blob). Omit or null when the tracker has no native fields.
- `score`, `band`, `score_denominator`, and `excluded_dimensions` come from the Scorecard. Emit them only when scoring was requested; omit for a plain pass/fail audit. `score` is capped by verdict, so `band` may be lower than the raw `score` alone would imply; `per-check` `points` sum to the raw numerator, and `score_denominator` is 100 minus the weights of every `excluded_dimensions` entry.
- **`applyable` is the safety gate.** It is `true` only when the draft passed its Step 6 self-verify AND contains no `[AUTHOR TO COMPLETE]` placeholder. **A caller MUST NOT write back a bead whose `applyable` is `false`.** Doing so degrades the bead into a placeholder-bearing body that looks fixed but re-fails forever.
- `blocked_on` lists the checks that still need a human (the placeholders). Non-empty implies `applyable: false`.

Correct loop contract: iterate `beads`, apply only those with `applyable: true`, and route `applyable: false` beads to a human (do not re-queue them for auto-fix). Re-run until `summary.applyable` is 0 and the only remaining non-PASS beads are `blocked_on_human`.

## Drafting Corrected Content

Reproduce the bead using the byte-exact headings from "Canonical Bead Structure". For a REFORMAT, this means relocating existing prose under the right heading and preserving its substance verbatim. For NEEDS WORK, fill the gap or insert a placeholder.

```markdown
## Why (Computational)

[The problem this solves. The stakeholder or motivating constraint. What depends on this.]

## How (Algorithmic)

[The approach, strategy, or representation. Key data flows, contracts, or sequencing.]

## Done when (Acceptance)

[Outcome-level conditions that mean the work is done, in the implementer's words.]

<!-- For task, feature, bug -->
## Acceptance Criteria

[Formal, testable checklist. Given/When/Then or numbered concrete assertions. See "Done when vs. Acceptance Criteria".]

<!-- For bug only -->
## Steps to Reproduce

1. [First step]
2. [Second step]

**Expected behavior:** [what should happen]
**Actual behavior:** [what currently happens]
**Environment / version:** [branch, OS, config, if known]

<!-- For epic only -->
## Success Criteria

[High-level outcome-level indicators legible to a product stakeholder.]

<!-- For code-bearing beads only; omit for epics and operational beads -->
## Estimated size

[<files> files, <LOC> LOC, band: <band>. One-sentence justification if Stretch.]

## Out of scope (optional)

[Anything explicitly deferred to a sibling or follow-up bead.]
```

### Guidance for weak sections

**Rewriting a vague Why:** Ask what breaks or stays broken if this bead is never done, who asked for it, and which downstream bead depends on it. At least one must appear.

**Rewriting a vague How:** A good How names the approach, not the action. "Extract the auth check into a Rack middleware registered before the session store" is a How; "update the auth code" is not. If the approach cannot be determined from the bead alone, insert a placeholder and flag it.

**Rewriting a vague Done when:** Each line must answer "how would a second person know this is true without asking the author?" Prefer named tests pass, specific endpoint returns X, metric crosses threshold Y.

**Filling missing type sections:** If the body carries enough to infer Acceptance Criteria / Steps to Reproduce / Success Criteria, draft them. Otherwise insert `[AUTHOR TO COMPLETE: <what is needed>]`.

## Critical Rules

**Always:**

- Separate the content verdict from the structure verdict. Never FAIL a section for heading format alone; a substantively complete section in a variant format is a REFORMAT.
- Read the full bead body before auditing; do not infer content from the title alone.
- When the tracker has native fields (e.g., `br`'s acceptance_criteria / design / notes), audit the field's content, treat the field as canonical structure, and write a fix to the native field rather than embedding a heading in the description body.
- Evaluate every applicable dimension. Skip size only for epics and operational beads, and record those as N/A rather than as a finding.
- Default the type to `task` if it cannot be determined, and flag it as a WARN.
- Use the byte-exact headings from "Canonical Bead Structure" when drafting, so a fixed bead re-passes the audit.
- Self-verify every draft (Step 6): re-run the audit against your own draft and confirm it re-passes before returning it.
- Present the full audit report before offering fixes; do not intermix findings with draft corrections.

**Never:**

- FAIL a bead whose Why/How/Done content is present and adequate but written under non-canonical headings. That is a REFORMAT.
- Force a files/LOC band onto an epic or operational bead.
- Manufacture a passing size band during scoring to suppress a FAIL. (A *drafted* fix may supply a `(provisional ...)`-marked estimate; that is the one allowed inference, and it is distinct from a `[AUTHOR TO COMPLETE]` placeholder.)
- Invent stakeholders, approaches, or acceptance criteria. When content cannot be inferred, use `[AUTHOR TO COMPLETE]`.
- Mark a draft `applyable: true`, or hand a caller a body for write-back, if it contains an `[AUTHOR TO COMPLETE]` placeholder. The placeholder is the needs-human boundary; it must reach a person, never the tracker.
- Treat a heading with no following content as present.
- Add sections not required for the bead's type (e.g., `## Steps to Reproduce` on a task).
- Forbid automation. The skill issues no tracker write commands itself, but it returns corrected content (markdown or JSON) precisely so a caller can apply the `applyable` ones at backlog scale.

## Quality Checklist

Before reporting completion, verify:

- [ ] Every provided bead was parsed and audited
- [ ] Each required section has both a content verdict and a structure verdict
- [ ] No bead was failed for heading format alone (format-only issues are REFORMAT)
- [ ] Native-field content (where the tracker has fields) was audited as canonical, not flagged as a missing heading
- [ ] Size was recorded as N/A for epics and operational beads, not forced into a band
- [ ] Any inferred size estimate in a drafted fix carries the `(provisional ...)` marker
- [ ] Every drafted fix was self-verified by re-auditing it (Step 6) and re-passes
- [ ] Corrected drafts use the byte-exact canonical headings (or write to the correct native field)
- [ ] No draft marked `applyable: true` contains an `[AUTHOR TO COMPLETE]` placeholder
- [ ] Beads with un-inferable gaps carry an `[AUTHOR TO COMPLETE]` placeholder, are marked `applyable: false`, and are routed to a human rather than written back
- [ ] JSON output (when requested) validates against the schema and `summary` counts (including `applyable` / `blocked_on_human`) match the per-bead verdicts
