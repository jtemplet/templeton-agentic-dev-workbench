# 0009. The large skill documents are not split into reference files

**Date:** 2026-09-06
**Status:** Accepted

## Context

Every skill invocation loads the whole skill document. The files under `skills/*/SKILL.md` total
16,986 lines; derive that with `wc -l skills/*/SKILL.md | tail -1`. Several are near a thousand
lines on their own.

The obvious cut is to move reference prose out of the largest documents into `references/` files
and leave a pointer, so the skill loads the pointer and reads the reference only when it needs it.
`docs/plans/feature-plan-token-routing.md` proposed exactly that as its milestone 5.

**This record exists because that cut looks free and is not.** A reader who measures the line
counts will propose it again, and the measurement that says no costs a day to redo.

The measurement ran on 2026-09-06, on the four documents the plan named. Derive each row with:

```bash
awk '/^## /{if(h)print len" "h; h=$0; len=0; next}{len++}END{if(h)print len" "h}' \
  skills/<name>/SKILL.md | sort -rn
```

| Skill | Lines | Cleanly movable | What the rest is |
|---|---|---|---|
| `terraform-iac-expert` | 957 | about 459 | A `## Examples` section of pure reference |
| `review-python` | 897 | about 182 | `## Review Principles` is 558 lines of rules |
| `bead-audit` | 919 | little | No section over 143 lines, and the largest are specs it executes |
| `quality-gates` | 882 | almost none | `## Required Workflow` is 611 lines of gate technique |

`terraform-iac-expert` was the only one holding a large section that lifts cleanly, and it left
the scope first, on the owner's instruction of 2026-09-06, who does not use that skill. What
remained does not look like it.

## Options Considered

### Option A: split nothing, and record the measurement

Leave the four documents whole. Keep the measurement on record so the proposal is answered rather
than re-argued.

- **Pros:** Costs nothing and breaks nothing. A skill document stays one file, which is where a
  reader looks and where `claude plugin validate` parses.
- **Cons:** The 16,986 lines stay. Every invocation of a large skill still loads rules it may not
  reach.

### Option B: split the reference prose out of the three remaining documents

- **Pros:** Cuts what loads on a cold invocation.
- **Cons:** Moves about 182 lines out of one skill, which is about one percent of the total. The
  other two have almost nothing that lifts: a section of rules is not reference prose, because the
  skill applies every rule on every run. The work to split, measure, and judge each section costs
  more than one percent returns.

### Option C: split, and have each skill always read its own reference file

The shape that makes a split safe: no judgment about when to read.

- **Pros:** No risk of a skill acting on rules it did not load.
- **Cons:** Strictly worse than not splitting. The skill pays for a pointer and then a full read,
  which is more than the one read it paid before.

## Decision

**Option A. The large skill documents stay whole, and this record answers the proposal.**

The rule it sets: **a section earns a `references/` file when it is reference the skill reads
sometimes, never when it is rules the skill applies every run.** By that test the four documents
measured hold one qualifying section between them, in a skill that left the scope.

Option B lost on arithmetic rather than on taste. Option C lost because it costs more than the
problem it solves.

**One piece of the proposal survives the drop.** `check_doc_paths.py` could not resolve a
`references/` pointer relative to the document naming it, and two skills already name such files:
`skills/product-surface-docs` names two, and `skills/roadmap-dashboard` names three. A pointer
that went missing in either printed no error. `tadw-ubc` fixed that checker. The gap was real
whether or not anything new was ever split.

A third skill showed the opposite failure. `skills/style-testing/` shipped a `references/` file
that its `SKILL.md` never named, so nothing loaded it and no checker could tell: a path checker
finds a pointer with no file, and cannot find a file with no pointer. That file was a measurement
procedure rather than reference prose, so it moved to
[evals/style-testing/invocation-battery.md](../../evals/style-testing/invocation-battery.md),
where [ADR 0005](0005-the-evals-are-a-measurement-not-a-gate.md) puts a deliberate measurement.

**Where the token savings went instead.**
[ADR 0008](0008-delegated-work-runs-on-a-cheaper-model.md) took them from delegation rather than
from document size: three quality-gates lanes off the parent's model, and a `bulk-reader` agent
that answers a question about many files without those files entering the caller's context. That
is a larger saving than one percent of the skill corpus, and it costs no restructuring.

## Consequences

**Easier:**

- No skill document is split across two files, so a reader, a reviewer, and
  `claude plugin validate` all see the whole technique in one place.
- The proposal has an answer with numbers attached, so the next person to notice the line counts
  reads this instead of re-measuring.
- `check_doc_paths.py` now resolves the `references/` pointers three skills already carry, which
  was the one real defect the proposal uncovered.

**Harder:**

- **The line counts keep growing and nothing watches them.** No gate measures the size of a skill
  document. This record answers the proposal as of 2026-09-06 and does not answer it forever.
- **The measurement is per document.** A new skill that grows a genuinely optional reference
  section is not covered here. The rule above decides it, and somebody has to apply the rule.
- **The four rows above will drift.** They pin one day. Re-derive them with the `awk` command
  before citing them in an argument.
