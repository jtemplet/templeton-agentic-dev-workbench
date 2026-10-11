<!--
Expected: overall NEEDS WORK, score 75/100, band Weak (NEEDS WORK cap).
Milestone: size N/A (umbrella). The missing `Estimated size` section is not a finding, and it
leaves the numerator AND the denominator.
Denominator: 90 (Why 20 + How 20 + Done when 20 + Success Criteria 20 + Structure 10).
Success Criteria: content fail, structure absent. It is the one finding on this bead.
Why, How, and Done when pass (60) + structure 3/4 canonical (7.5) = 67.5 / 90 = 75.0.
Raw 75.0 maps to Great, and the NEEDS WORK ceiling lowers the band to Weak.
A draft fix cannot infer what a stakeholder would see, so it carries
`[AUTHOR TO COMPLETE: success criteria]` and is applyable:false.
-->
Title: Deliver self-serve team billing to every paid team
Type: milestone

```text
description:
  **Ask:** Deliver self-serve billing, so a team admin changes seats without a sales email.

  ## Why (Computational)

  Teams email sales to change seats today. That limits growth to the pace of the sales team, and
  the finance team cannot forecast seat revenue from requests that sit in an inbox.

design:
  Deliver in three child beads, in this order: the read-only invoice view, plan changes, then
  seat proration. Each one ships behind its own flag, so a billing fault is reversible in a day.

notes:
  ## Done when (Acceptance)

  - The three child beads are closed, and each one has a recorded acceptance verdict.
  - The three flags are on for every paid team.
```
