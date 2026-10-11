<!--
Expected: overall PASS, score 100/100, band Excellent.
Milestone: size is N/A (umbrella), so it leaves the numerator AND the denominator.
Denominator: 90 (Why 20 + How 20 + Done when 20 + Success Criteria 20 + Structure 10).
All content pass (80) + structure 4/4 canonical (10) = 90 / 90 = 100.
The How sits in the native `design` field and the Done when sits in the native `notes` field, so
both are canonical with no heading. The bead has no `## Estimated size` section and an empty
acceptance field. Neither is a finding on a milestone.
-->
Title: Deliver self-serve team billing to every paid team
Type: milestone

```text
description:
  **Ask:** Deliver self-serve billing, so a team admin changes seats without a sales email.

  ## Why (Computational)

  Teams email sales to change seats today. That limits growth to the pace of the sales team, and
  the finance team cannot forecast seat revenue from requests that sit in an inbox.

  ## Success Criteria

  - A team admin can add or remove a seat and see the new invoice amount in the same session.
  - More than 90% of seat changes in the first quarter need no contact with the sales team.
  - The count of billing support requests does not rise in the month after the release.

design:
  Deliver in three child beads, in this order: the read-only invoice view, plan changes, then
  seat proration. Each one ships behind its own flag, so a billing fault is reversible in a day.

notes:
  ## Done when (Acceptance)

  - The three child beads are closed, and each one has a recorded acceptance verdict.
  - The three flags are on for every paid team.
```
