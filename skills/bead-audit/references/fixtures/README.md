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

## Grounding and these fixtures

Every fixture here is a pasted body describing a fictional login rate-limiter, and it names
**no repository of record**. All eight are therefore `ungroundable` under the last-but-one
bullet of `SKILL.md` → "When the dimension cannot run", which applies no band ceiling, so
the expected bands above are unchanged by the Grounding Audit.

**This is load-bearing, not incidental.** These fixtures live inside a repository, so an
auditor that grounds a bead against "whatever repo is open" would run their existence checks
against `tadw`, find no login endpoint and no rate limiter, and report `drifted` on all
eight. That applies the Adequate ceiling and drops `excellent-task.md` from Excellent to
Adequate, failing the suite for a reason that has nothing to do with the Scorecard. If you
see fixture bands move after a grounding rule change, check that rule first: the fixtures
are almost certainly being grounded against a repository they were never about.

The grounding ceilings themselves are **not covered by a fixture**, because exercising them
needs a real repository at a known sha, which a pasted-body suite cannot provide. The
worked-example table in `SKILL.md` → "Bands, capped by verdict" is the only check on that
arithmetic today. Two states are entirely unpinned: `drifted` (Adequate ceiling) and
`satisfied` (Weak ceiling). Covering them needs a fixture repository, and until one exists
this suite proves the ceilings do not fire when they should not, and proves nothing about
whether they fire when they should.
