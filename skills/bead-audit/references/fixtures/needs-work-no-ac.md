<!--
Expected: overall NEEDS WORK, raw score 78/100, band Weak (NEEDS WORK cap).
Why/How/Done pass (60) + structure: AC section absent so 4/5 canonical => 8 + size Target pass (10)
= 78 raw. Missing required Acceptance Criteria is a content fail, so verdict is NEEDS WORK and the
ceiling is Weak. Raw 78 would band Great; the cap makes it Weak. This is the bead a Great-target
loop would wrongly skip if not for the cap. Auto-fix inserts [AUTHOR TO COMPLETE] for AC =>
applyable:false, blocked_on:[acceptance-criteria].
-->
Title: Add CSV import for the contacts list
Type: task

## Why (Computational)

Customers migrating from a competitor arrive with contacts in a CSV and no way to load them,
so onboarding stalls at step one and sales has been doing manual imports by hand. The
onboarding funnel depends on self-serve import existing.

## How (Algorithmic)

Add an upload endpoint that streams the CSV through the existing contact validator row by row,
collecting per-row errors rather than failing the whole file. Chosen over a bulk insert so a
single malformed row does not reject a 2000-row file.

## Done when (Acceptance)

- A user can upload a CSV and see their contacts imported.
- Malformed rows are reported without rejecting the whole file.

## Estimated size

3 files, ~160 LOC, band: Target.
