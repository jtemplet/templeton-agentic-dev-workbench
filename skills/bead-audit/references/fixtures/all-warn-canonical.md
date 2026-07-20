<!--
Expected: overall REFORMAT (weak content), raw score 55/100, band Weak.
Deterministic arithmetic (task denominator 100):
  Why/How/Done/AC each present under canonical headings but borderline-weak => content warn = 0.5,
    so 4 x (0.5 x 20) = 40.
  Structure 5/5 canonical = 10.
  Estimated size is an explicit Trivial band => size warn = 0.5 x 10 = 5.
  Numerator 40 + 10 + 5 = 55; raw 55/100 bands Weak.
Two cap rows independently apply and both set the ceiling to Great: WARN (any content warn, no
content fail) and Trivial-band warn. The reported band is the lower of (Weak score, Great ceiling)
= Weak either way. The size band is stated explicitly (Trivial) rather than left vague so the
score is reproducible: a vague "some files" estimate could be read as fail (0) rather than warn
(5) and the fixture would stop being a deterministic oracle.
This is the "weak but complete" bead that has no [AUTHOR TO COMPLETE] placeholder, so it is
applyable:true yet cannot be auto-improved: the stalled case the driver must handle.
-->
Title: Improve the export feature
Type: task

## Why (Computational)

Users want a better export. It would be good to have.

## How (Algorithmic)

Update the export code to be more robust and handle more cases.

## Done when (Acceptance)

- Export works better than before.
- Fewer complaints about exports.

## Acceptance Criteria

1. The export is improved.
2. Users are happier with it.

## Estimated size

1 file, ~15 LOC, band: Trivial.
