---
name: bead-audit
description: "Audit one or more bead issue bodies against the Marr audit, size audit, type-specific section audit, and a grounding audit against the current main branch. Separates three independent verdicts: content (is the substance there?), structure (is it under the canonical heading or native field?), and grounding (is the bead still true of the code as it is today?), so a substantively complete bead in the wrong format is an auto-fixable reformat, and a well-written bead whose target code moved is stale rather than under-specified. Produces an optional weighted scorecard (0-100, banded Poor/Weak/Adequate/Great/Excellent) derived from the verdicts and capped so the band can never contradict the pass/fail verdict or outrank the grounding verdict, for ranking a backlog or targeting a quality band. Honors trackers with native fields (e.g. br's acceptance_criteria/design/notes), self-verifies every drafted fix so it re-passes, and gates write-back with an applyable flag so placeholder-bearing drafts never reach the tracker. Supports a machine-readable JSON output mode for backlog-scale grooming."
---

# Bead Audit

A systematic technique for evaluating bead issue bodies against the same content standards applied during decomposition. Borrows all audit logic from `plan-to-beads`: the Marr audit (Why/How/Done when quality), the size audit (diff-size band), and the type-specific section audit (Acceptance Criteria, Steps to Reproduce, Success Criteria).

This skill is agnostic to the issue tracker. It audits the *text* of a bead body, and, when the bead's repository is available, it additionally checks that text against the code on the main branch. How that text is fetched, and whether corrected text is written back, is the caller's responsibility (a human pasting, a script looping over a backlog, or a `/goal`-style driver).

**Three principles that shape every check:**

1. **Content is not structure.** A bead whose Why/How/Done content is rich but written as `WHY:` prose instead of under `## Why (Computational)` is *correctly specified, wrongly formatted*. That is an auto-fixable reformat (WARN), never an under-specification (FAIL). The audit reports these as separate verdicts.
2. **Specification is not currency.** A bead can be perfectly written and no longer true. If the file its How names was renamed last month, the bead is *stale*, not under-specified, and the fix is to re-ground it, not to write missing content. Grounding is therefore a third verdict on its own axis, never folded into the content verdict.
3. **One canonical structure.** The required headings per type live in exactly one place ("Canonical Bead Structure" below). The audit checks against that list and the drafting template reproduces it byte-for-byte, so a bead that this skill fixes is guaranteed to re-pass.

## When to Use

- Before claiming a bead, to make sure it has enough context to implement without re-reading the parent plan
- During backlog grooming to surface under-specified issues at scale (use JSON mode)
- After inheriting a project or picking up someone else's work
- Before a sprint to verify every in-scope bead is implementation-ready
- After running `/plan-to-beads` on a modified plan to verify the generated beads meet the bar
- To rank a backlog by quality, or gate on a target band, using the Scorecard (request a score; use JSON mode for a loop)
- Before re-opening an aging backlog, to find beads whose premise the code has already overtaken (Grounding Audit)

## When NOT to Use

- To audit a plan document (use `/plan-review` for that)
- For content that is not a bead body (e.g., raw meeting notes, a user story in a different format)
- To decide whether a *finished* unit of work met its bead's acceptance criteria (use `/verify-acceptance`). This skill grades the bead, not the implementation, and its Grounding Audit reads the main branch precisely to avoid grading work in progress

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

Some trackers expose first-class fields for sections that this skill otherwise expects as body headings. For example, `bd` has dedicated `acceptance_criteria`, `design`, and `notes` fields separate from `description`, and surfaces them as their own blocks in `bd show`. Other tooling (`bd ready`, reporting, dashboards) reads those native fields directly.

When a tracker has a native field for a section, **the audit applies to that field's content, not to a body heading**, and the field counts as canonical structure:

| Canonical section | Maps to native field (when the tracker has one) | Example: `bd` |
|---|---|---|
| Acceptance Criteria | the acceptance-criteria field | `--acceptance-criteria` (alias `--acceptance`) |
| How (Algorithmic) | the design / approach field | `--design` |
| Done when / Out of scope / supporting detail | the notes field | `--notes` |
| Why, and anything without a native slot | the description / body field | `-d` / `--description` |

Rules when native fields are present:

- A section whose content lives in the correct native field is `structure: canonical`. Do not flag it for "missing heading."
- A section's content duplicated into the body when a native field exists for it is `structure: variant` (reformat: move it to the native field, do not embed a heading in the description).
- When **drafting a fix**, populate the native field rather than appending a heading to the body. For `bd`, that means `bd update <id> --acceptance-criteria "..."` and `bd update <id> --design "..."`, not stuffing `## Acceptance Criteria` into `--description`.
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

The bead as a whole gets a third verdict, on its own axis:

- **Grounding verdict** - are the bead's claims about existing code still true on main? See "4. Grounding Audit".
  - `grounded`: every load-bearing current-state claim was checked and holds
  - `drifted`: at least one load-bearing current-state claim is false on main
  - `satisfied`: the bead's desired end state already holds, so the work appears done or obsolete
  - `ungroundable`: the repository was unavailable, or the bead names nothing checkable

Grounding never changes a content verdict. It caps the reported band, and it is reported in its own column.

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

### 4. Grounding Audit

Checks whether the bead is still true of the code as it exists today. A bead is written at one moment and read at another, and the gap between them is where a backlog rots: the file gets renamed, the bug gets fixed by a neighboring change, the approach the How proposes stops being possible. None of that shows up in a text audit, because the text is unchanged and still reads well.

**This dimension reads code. The other three do not.** It runs when the bead's repository is available and the bead names something checkable. Otherwise it records `ungroundable`, which is an absence of measurement and must never be reported as `grounded`.

#### Which claims are groundable

This is the rule the dimension turns on. Get it wrong and every open bead reports as drifted.

| Section | Describes | Groundable? |
|---|---|---|
| Why (Computational) | the world as it is | **Yes.** Current-state claims: the bug exists, the file behaves this way, this consumer depends on it |
| How (Algorithmic) | the world as it is, plus a proposed change | **Yes, for its premises only.** The files, symbols, and patterns it names must exist. The change it proposes is not yet real and is not checked |
| Steps to Reproduce | the world as it is | **Yes.** The command must exist and be runnable; the named entry point must be real |
| Estimated size | a prediction | **Partly.** Only the named files, and only for existence |
| Done when (Acceptance) | the world after the work | **No, not for drift.** See the inverse check below |
| Acceptance Criteria | the world after the work | **No, not for drift.** See the inverse check below |
| Success Criteria | the world after the work | **No, not for drift.** See the inverse check below |

An open bead's acceptance criteria are *supposed* to be false right now. Failing them is the bead's whole reason to exist. Never record a `drifted` claim because a desired end state has not been reached.

**The inverse check, which is the valuable one.** Run the desired-state sections the other way: if the end state *already holds* on main, record `satisfied`. Somebody did the work, or a neighboring change made it moot, and nothing told the tracker. A `satisfied` bead is the cheapest thing in a backlog to resolve and the most expensive to keep re-reading.

#### What to check

The same four checks `plan-review` uses for a plan, applied to a bead and bounded the same way:

- **Existence check:** every file path, module, symbol, command, and endpoint the bead names must exist. Use Glob and Grep; do not deep-read.
- **Pattern check:** when the bead says "extend the existing X" or "follow the Y pattern", confirm X and Y are real and roughly match the bead's description.
- **Stack check:** confirm the tools, libraries, and commands the bead relies on are actually in the project (manifest, lockfile, config), not assumed.
- **Behavior check:** when the bead asserts how existing code behaves (a default, a limit, a side effect, an exit code, where something writes), verify the specific code rather than the symbol's existence. Existence passes trivially. Behavioral claims are where the plausible-but-false ones hide, and they are usually the claim the Why rests on.

**Load-bearing only.** Check the claims the bead's argument depends on. A passing mention of an unrelated directory is incidental color; skip it. A quoted measurement in the Why ("scored 0 of 6") is load-bearing when it is the reason the bead exists.

#### Read main, not the working tree

Ground against the **main branch**, not the checkout in front of you. On a feature branch that is mid-implementation, the working tree already contains the change the bead asks for, so the working tree would report the bead `satisfied` and invite closing a bead whose work has not merged.

```bash
git rev-parse --abbrev-ref HEAD          # where am I
git fetch origin main --quiet            # optional; note if skipped
git rev-parse origin/main                # the sha every claim was checked against
git show origin/main:path/to/file.py     # read a file as main has it
git grep -n "pattern" origin/main -- path/    # search main without checking it out
```

Record the ref and short sha in the report. A grounding result without the sha it was measured at cannot be re-checked later, which makes it an assertion rather than a measurement.

Fall back to `main` when there is no `origin`, and say which was used. If neither resolves, the dimension is `ungroundable`.

#### When the dimension cannot run

Record `ungroundable` and name the reason. Do not guess, and do not let a clean report imply verification that did not happen:

- No repository in the working directory, or the bead was pasted as plain text
- The bead's `source_repo_path` (or equivalent) points at a different repository than the one in front of you. Say so, and name both
- **The bead names no repository of record at all** (a pasted body, a fixture, an illustrative example, a bead copied out of another project's tracker). Never check such a bead against whatever repository happens to be open: its claims describe a codebase you do not have, so every existence check fails for the wrong reason and reports `drifted` on a bead that is fine. Absent a repository of record, the honest verdict is `ungroundable`
- The bead names no checkable claim (common for pure-research or discussion beads)
- `main` cannot be resolved

#### Per-claim verdicts

Each checked claim gets `verified`, `drifted`, or `unverifiable`. The bead's grounding verdict is the rollup:

| Grounding verdict | Condition |
|---|---|
| `grounded` | No load-bearing claim is `drifted`, and at least one is `verified` |
| `drifted` | At least one load-bearing claim is `drifted` |
| `satisfied` | The desired end state already holds on main. This takes precedence over `drifted`, and carries the harsher ceiling of the two; report both findings, but resolve the bead before re-specifying it |
| `ungroundable` | No claim could be checked, for one of the reasons above |

An `unverifiable` claim alone does not make a bead `drifted`, which is why `grounded` requires the absence of drift rather than the presence of universal verification. Report every `unverifiable` claim, and note that `grounded` here means "nothing contradicts the bead", not "the bead is fully proven". If every claim came back `unverifiable`, nothing was established at all and the verdict is `ungroundable`, not `grounded`.

#### Never fix the code to match the bead

The Grounding Audit is read-only, and it is the one dimension where that needs saying. When a claim is false, the bead is wrong about the code; the code is not wrong about the bead. Report the drift and offer to re-ground the bead's text. Never edit a source file to make a bead's claim true, and never rewrite the bead's Why to match the code without the author confirming that the original motivation still stands. A bug bead whose repro no longer reproduces may mean the bug was fixed, or may mean the repro moved; those have opposite resolutions and the audit cannot tell them apart.

## Verdict Model

Each bead rolls up to one of three overall states:

| Overall | Condition | Caller action |
|---|---|---|
| **PASS** | Every content verdict is `pass` AND every structure verdict is `canonical` | None |
| **REFORMAT** | Every content verdict is `pass` (or N/A) but at least one structure verdict is `variant`/`absent`, or a Trivial-band warn | Auto-fixable: reformat to canonical headings, no human input needed |
| **NEEDS WORK** | At least one content verdict is `fail` (genuine under-specification or missing required section) | Human input may be required; see drafting guidance |

A WARN on content (borderline-weak) rolls up to REFORMAT if the author chooses to leave it, or NEEDS WORK if they want it tightened. Treat content WARN as REFORMAT-tier for gating purposes unless the caller asks for strict mode.

**Grounding does not enter this rollup.** The three states above answer "is this bead well written?" Grounding answers "is it still true?" A bead can be PASS and `drifted` at the same time, and that combination is common in an aging backlog: it was written well, and the code moved. Folding the two together would change a bead's Overall without anyone touching the bead, and would hide the distinction between "needs writing" and "needs re-grounding", which have different fixes and different owners.

Report grounding as its own column. It reaches the score only through a band cap (see "Bands, capped by verdict"), so a stale bead cannot report Excellent while its premise is false.

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

The grounding verdict applies a second, independent ceiling. Take the lowest of all applicable ceilings:

| Grounding verdict | Band ceiling | Why |
|---|---|---|
| `satisfied` | Weak | The work appears already done. However well written, this bead's remaining value is a status update |
| `drifted` | Adequate | An implementer following it goes to code that is not there. Worse than a formatting defect, comparable to a missing section |
| `grounded` | none | |
| `ungroundable` | none | An unmeasured dimension is not a finding. It must still be named in the report so a clean band is not read as verified |

**Grounding contributes no points and changes no denominator.** It is a ceiling only, so a `grounded` verdict cannot inflate a thin bead, and a `drifted` verdict cannot be offset by strong prose elsewhere. Worked examples:

| Bead state | Raw | Verdict ceiling | Grounding ceiling | Reported |
|---|---|---|---|---|
| task, all pass, canonical, size Target, `grounded` | 100.0 | Excellent | none | **Excellent** |
| task, all pass, canonical, size Target, `drifted` | 100.0 | Excellent | Adequate | **Adequate** |
| task, all pass, canonical, size Target, `satisfied` | 100.0 | Excellent | Weak | **Weak** |
| task, all pass, every heading variant, `drifted` | 90.0 | Great | Adequate | **Adequate** |
| task, no Acceptance Criteria, `grounded` | 78.0 | Weak | none | **Weak** |
| task, all pass, canonical, `ungroundable` | 100.0 | Excellent | none | **Excellent**, marked unverified |

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
- **Issue tracker output** - the user pastes or pipes the output of their CLI (`bd show <id>`, `bd show <id>`, `gh issue view <id>`, etc.)
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

**Then run the Grounding Audit.** Do this once per repository, not once per bead: resolve the ref and sha first, then check every bead's claims against it.

1. Resolve the baseline. `git rev-parse origin/main` (falling back to `main`, and saying which was used). Record the short sha. If neither resolves, or there is no repository, mark every bead `ungroundable` with that reason and skip to Step 4.
2. Confirm the beads belong to this repository. When the tracker records an origin (`bd` sets `source_repo` and `source_repo_path`), compare it to the repository in front of you. A mismatch is `ungroundable`, not a finding against the bead, and the report must name both repositories.
3. For each bead, extract its load-bearing current-state claims from Why, How, and Steps to Reproduce. Check each with the existence, pattern, stack, and behavior checks. Read main with `git show` and `git grep`, never the working tree.
4. Run the inverse check on Done when and Acceptance Criteria: does the desired end state already hold on main? If so, the bead is `satisfied`.
5. Roll up to one grounding verdict per bead.

Grounding is the only dimension that costs repository reads, and it scales with backlog size. When a caller needs a text-only sweep, it may ask for one; record `ungroundable` with the reason "not requested" so the omission is visible in the report rather than silent.

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
**Grounding: grounded / drifted / satisfied / ungroundable** (checked against `origin/main` @ `<short sha>`)

| Claim | Section | Check | Verdict | Evidence |
|---|---|---|---|---|
| "<the claim, quoted from the bead>" | Why | existence / pattern / stack / behavior | verified / drifted / unverifiable | `path/to/file.py:42`, or what was searched and not found |

<one sentence: for REFORMAT, what will be reformatted; for NEEDS WORK, the most critical content gap; for drifted or satisfied, which claim broke and what the bead now needs>
````

Omit the claim table when the verdict is `ungroundable`, and replace it with the one-line reason. Include it whenever any claim was checked, including an all-`verified` result: the evidence is what makes `grounded` re-checkable rather than asserted.

When a score is requested (a caller targeting a band, or a human asking for one), add a trailing `Points` column to the table (the weighted contribution of each dimension, e.g. `20/20`, `10/20`, `size excluded`) and a line under Overall:

```markdown
Score: N/100 → Band   (denominator D after excluding <named N/A dimensions>)
```

After all beads:

````markdown
## Audit Summary

Grounded against `origin/main` @ `<short sha>`.

| Title | Type | Overall | Grounding | Score | Band |
|---|---|---|---|---|---|
| ... | ... | PASS / REFORMAT / NEEDS WORK | grounded / drifted / satisfied / ungroundable | N/100 | Excellent / Great / ... |

PASS: X   REFORMAT (auto-fixable): Y   NEEDS WORK: Z   (of N total)
Grounded: A   Drifted: B   Satisfied: C   Ungroundable: D   (of N total)
````

The `Score` and `Band` columns are present only when scoring was requested; omit them for a plain pass/fail audit. The `Grounding` column is always present: when the dimension did not run, every row reads `ungroundable` and the header line states why, so a reader can never mistake an unchecked backlog for a verified one.

**Report `satisfied` beads first, above the ranked table.** They are resolvable immediately and cost nothing to close, and leaving them buried in a quality ranking sends someone to re-specify work that is already done.

### Step 5: Offer to Draft Fixes

If any bead is REFORMAT or NEEDS WORK, offer to draft corrected bodies:

- **REFORMAT beads** can be fixed mechanically: move the existing substance under canonical headings (or into the correct native field). No new information needed. Draft these without asking.
- **NEEDS WORK beads** need real content. Draft what can be inferred; for anything that cannot, insert `[AUTHOR TO COMPLETE: <what is needed>]` and flag it.

Present each corrected body in a fenced block labeled with the bead title, ready to apply. State what changed per section (one line each).

**A drafted body containing `[AUTHOR TO COMPLETE]` is not "fixed."** Mark it clearly as `applyable: false` (DO NOT APPLY). The placeholder *is* the needs-human boundary: it must reach a person, not get written back to the tracker. A provisional size estimate carrying a `(provisional ...)` marker does **not** make a draft unapplyable; only a `[AUTHOR TO COMPLETE]` placeholder does.

**Drifted and satisfied beads are not drafted, they are escalated.** Both are `applyable: false` regardless of how clean their text is:

- **`drifted`**: report the false claim, the evidence, and what main actually shows. Do not silently rewrite the claim to match the code. A stale premise has two possible resolutions, "the bead is out of date" and "the code regressed", and the audit cannot tell them apart. Offer the author both readings and let them pick. A path that merely moved is the one safe exception: a rename you can prove with `git log --follow` may be drafted as a correction, and must cite the commit that moved it.
- **`satisfied`**: propose closing the bead, not fixing it. Say what on main satisfies it and at which sha. If the evidence is partial, say the work looks done and ask, rather than proposing closure of something half-landed.

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
      "grounding": {
        "verdict": "grounded|drifted|satisfied|ungroundable",
        "reason": "string, required when ungroundable, else null",
        "claims": [
          {
            "claim": "string, quoted from the bead",
            "section": "why|how|steps-to-reproduce|estimated-size|done-when|acceptance-criteria",
            "check": "existence|pattern|stack|behavior",
            "verdict": "verified|drifted|unverifiable",
            "evidence": "string: path:line, or what was searched and not found"
          }
        ],
        "band_ceiling": "adequate|weak|null"
      },
      "corrected_body": "string or null",
      "corrected_fields": { "description": "string|null", "design": "string|null", "acceptance_criteria": "string|null", "notes": "string|null" },
      "applyable": true,
      "blocked_on": ["why", "estimated-size", "grounding"]
    }
  ],
  "grounded_against": { "ref": "origin/main", "sha": "string", "repo_path": "string" },
  "summary": { "total": 0, "pass": 0, "reformat": 0, "needs_work": 0, "applyable": 0, "blocked_on_human": 0, "grounded": 0, "drifted": 0, "satisfied": 0, "ungroundable": 0 }
}
```

Field semantics for a caller (e.g., a `/goal` loop):

- `corrected_body` is the full markdown fix (canonical headings). `null` for PASS beads.
- `corrected_fields` is the optional native-field breakdown for trackers like `bd` (write `acceptance_criteria` to `--acceptance-criteria`, `design` to `--design`, etc., instead of one body blob). Omit or null when the tracker has no native fields.
- `score`, `band`, `score_denominator`, and `excluded_dimensions` come from the Scorecard. Emit them only when scoring was requested; omit for a plain pass/fail audit. `score` is capped by verdict, so `band` may be lower than the raw `score` alone would imply.
- `score_denominator` is the sum of the weights of every dimension that applies to the bead, including Structure (weight 10) and, for a `bug`, Steps to Reproduce (weight 10). Do not compute it as "100 minus excluded weights": that is right for a `task`/`feature` (denominator 100) and an `epic` (90, size excluded) but wrong for a `bug`, whose base is 110. Excluding a dimension removes its weight from this sum.
- Per-check `points` cover only the content dimensions in the `checks` array; they do **not** include the Structure contribution, which is computed once as `10 × (canonical required sections ÷ total required sections)` and is not itself a `checks` entry. The raw numerator is `sum(checks[].points) + structure_points`; `score = round(100 × numerator ÷ score_denominator)`. A consumer recomputing the score must add the structure term separately.
- **`applyable` is the safety gate.** It is `true` only when the draft passed its Step 6 self-verify AND contains no `[AUTHOR TO COMPLETE]` placeholder AND the grounding verdict is not `drifted` or `satisfied`. **A caller MUST NOT write back a bead whose `applyable` is `false`.** Doing so degrades the bead into a placeholder-bearing body that looks fixed but re-fails forever, or, for a drifted bead, laminates good formatting over a false premise.
- `blocked_on` lists what still needs a human. Its values are check names (`why`, `how`, `done-when`, `acceptance-criteria`, `steps-to-reproduce`, `success-criteria`, `estimated-size`) for placeholder-bearing sections, plus the literal `"grounding"` when the verdict is `drifted` or `satisfied`. `"grounding"` is deliberately not a check name: it is a bead-level finding, not a section, and a consumer matching this list against the `checks` array must expect it. Non-empty implies `applyable: false`.
- `grounding.band_ceiling` is `"adequate"` for `drifted`, `"weak"` for `satisfied`, and `null` otherwise. It is already applied to `band`; it is emitted so a consumer can see which ceiling bound the result.
- `grounded_against` records the ref, sha, and repository path every claim was checked against. It is `null` only when every bead is `ungroundable`. A consumer comparing two runs must compare shas: a `grounded` verdict is a statement about one commit, not a permanent property of the bead.

Correct loop contract: iterate `beads`, apply only those with `applyable: true`, and route `applyable: false` beads to a human (do not re-queue them for auto-fix). Re-run until `summary.applyable` is 0 and every remaining bead is either PASS **and** `grounded`/`ungroundable`, or `blocked_on_human`.

**Do not terminate on the Overall verdict alone.** A bead can be PASS and `drifted` at the same time, which is the whole point of keeping the axes separate, so a loop that gates only on non-PASS beads will declare the backlog clean while a bead with a false premise sits in it. `summary.drifted` and `summary.satisfied` must both be 0, or their beads must be listed as routed to a human, before a run reports done.

A loop that re-runs across days must re-ground rather than cache: `summary.grounded` from an old sha says nothing about today's main.

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
- When the tracker has native fields (e.g., `bd`'s acceptance_criteria / design / notes), audit the field's content, treat the field as canonical structure, and write a fix to the native field rather than embedding a heading in the description body.
- Evaluate every applicable dimension. Skip size only for epics and operational beads, and record those as N/A rather than as a finding.
- Default the type to `task` if it cannot be determined, and flag it as a WARN.
- Use the byte-exact headings from "Canonical Bead Structure" when drafting, so a fixed bead re-passes the audit.
- Self-verify every draft (Step 6): re-run the audit against your own draft and confirm it re-passes before returning it.
- Present the full audit report before offering fixes; do not intermix findings with draft corrections.
- Ground against the main branch and record the sha. A grounding verdict without the commit it was measured at is an assertion.
- Report `ungroundable` with its reason whenever the Grounding Audit could not run, and keep the Grounding column in the summary table even then.
- Cite evidence for every grounding claim, including the verified ones: a `path:line`, or what was searched and not found.

**Never:**

- FAIL a bead whose Why/How/Done content is present and adequate but written under non-canonical headings. That is a REFORMAT.
- Force a files/LOC band onto an epic or operational bead.
- Manufacture a passing size band during scoring to suppress a FAIL. (A *drafted* fix may supply a `(provisional ...)`-marked estimate; that is the one allowed inference, and it is distinct from a `[AUTHOR TO COMPLETE]` placeholder.)
- Invent stakeholders, approaches, or acceptance criteria. When content cannot be inferred, use `[AUTHOR TO COMPLETE]`.
- Mark a draft `applyable: true`, or hand a caller a body for write-back, if it contains an `[AUTHOR TO COMPLETE]` placeholder. The placeholder is the needs-human boundary; it must reach a person, never the tracker.
- Treat a heading with no following content as present.
- Add sections not required for the bead's type (e.g., `## Steps to Reproduce` on a task).
- Record a bead as `drifted` because its acceptance criteria do not hold yet. Unmet criteria are the bead's reason to exist; only current-state claims can drift.
- Ground against the working tree. On a feature branch it already contains the change the bead asks for, which reports the bead `satisfied` and invites closing unmerged work.
- Edit a source file to make a bead's claim true, or rewrite a bead's Why to match the code without the author confirming the motivation still stands.
- Report `grounded` when nothing was checked. That is `ungroundable`, and the distinction is the whole value of the dimension.
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
- [ ] The Grounding Audit ran against main (not the working tree), and the ref and sha are stated in the report
- [ ] No bead was marked `drifted` for an unmet acceptance criterion
- [ ] Every grounding claim carries evidence, and every `ungroundable` carries a reason
- [ ] `drifted` and `satisfied` beads are marked `applyable: false` and escalated rather than auto-corrected
- [ ] JSON output (when requested) validates against the schema and `summary` counts (including `applyable` / `blocked_on_human` / the four grounding counts) match the per-bead verdicts
