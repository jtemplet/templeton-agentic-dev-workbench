<!--
Expected: overall PASS, score 100/100, band Excellent.
Epic: size dimension is N/A (umbrella), so it is excluded from numerator AND denominator.
Denominator = Why 20 + How 20 + Done 20 + Success Criteria 20 + Structure 10 = 90. All content pass
(80) + structure 4/4 canonical (10) = 90 numerator / 90 denominator = 100. PASS, all canonical,
banded Excellent. Verifies renormalization: if size stayed in the denominator (100) the numerator
would still be 90, so the epic would score 90 but any single soft verdict would drop it below the
Excellent line it should never be gated out of. (Success Criteria substitutes for Acceptance
Criteria on an epic; Estimated size is not required.)
-->
Title: Ship self-serve team billing
Type: epic

## Why (Computational)

Teams currently email sales to change seats, which caps growth at the rate sales can process
requests and blocks expansion revenue. Finance and the growth team both depend on self-serve
billing to unlock seat expansion without human involvement.

## How (Algorithmic)

Introduce a billing surface backed by the existing payment provider's subscription API, with
seat count driven by team membership. Sequenced as: read-only invoice view, then plan changes,
then seat proration. Each phase ships behind a flag so billing changes are reversible.

## Done when (Acceptance)

- A team admin can change seats and plans without contacting sales.
- Every billing change is reversible via a flag during rollout.

## Success Criteria

- The share of seat changes handled without a sales touch exceeds 90% within one quarter of launch.
- Expansion revenue attributable to self-serve seat additions is measurable in the billing dashboard.
- No increase in billing-related support tickets after launch.
