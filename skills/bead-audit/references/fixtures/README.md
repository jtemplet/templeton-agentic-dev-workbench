# Scorecard fixtures

Regression suite for the `bead-audit` Scorecard. Each fixture is a bead body with its
expected audit verdict, score, and band recorded in its own front block. When the Scorecard
rules change, re-audit every fixture and confirm the reported band still matches the
`Expected` block. A fixture whose expected band no longer holds is either a rule regression
or a fixture that needs its expected value updated with a stated reason.

The score is computed from the weights and rules in `SKILL.md` → "Scorecard", never asserted.
Recompute it by hand from the per-section verdicts; do not trust the number in the block
without checking it.

| Fixture | Type | Tests | Expected band |
|---|---|---|---|
| `excellent-task.md` | task | clean bead, all pass, canonical | Excellent |
| `reformat-only.md` | task | content complete, headings non-canonical | Great (structure cap) |
| `all-warn-canonical.md` | task | every section present but weak | Weak (raw 55, WARN tier) |
| `trivial-band.md` | task | perfect but Trivial size | Great (Trivial-band cap) |
| `needs-work-no-ac.md` | task | missing Acceptance Criteria | Weak (NEEDS WORK cap) |
| `bug-without-repro.md` | bug | missing Steps to Reproduce | Weak (NEEDS WORK cap) |
| `epic-without-size.md` | epic | clean, size N/A (renormalized) | Excellent |
| `title-only.md` | task | title plus one line, nothing else | Poor, applyable:false |

These map to the plan's acceptance criteria: excellent-task→1, epic-without-size→3,
reformat-only→4, needs-work-no-ac→5, bug-without-repro→6, all-warn-canonical→7, title-only→2,
trivial-band→the Trivial cap row.
