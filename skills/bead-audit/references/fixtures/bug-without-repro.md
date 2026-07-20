<!--
Expected: overall NEEDS WORK, raw score 89.4/100, band Weak (NEEDS WORK cap).
Bug denominator is 110 (Why 20 + How 20 + Done 20 + AC 20 + Steps 10 + Size 10, plus Structure 10).
Why/How/Done/AC pass (80) + size Target pass (10) + structure: Steps absent so 5/6 canonical =>
10 * 5/6 = 8.33. Numerator 98.33 / 110 = 89.4 raw. Missing required Steps to Reproduce is a content
fail => NEEDS WORK => ceiling Weak. Without a weighted Steps dimension this bead would score ~100
and band Weak: an incoherent report. Auto-fix inserts [AUTHOR TO COMPLETE] for Steps =>
applyable:false, blocked_on:[steps-to-reproduce].
-->
Title: Avatar upload fails silently for HEIC files
Type: bug

## Why (Computational)

iPhone users uploading a profile photo get no avatar and no error; the file is a HEIC and the
processor drops it without a message. Support sees this weekly and the trust-and-safety team
needs uploads to fail loudly, not silently, so users are not left confused.

## How (Algorithmic)

Detect HEIC by magic bytes at the upload boundary and either transcode via the existing image
pipeline or reject with a clear message. Chosen over relying on the file extension because iOS
share sheets often mislabel the type.

## Done when (Acceptance)

- HEIC uploads either succeed as a converted avatar or fail with a visible error.
- No upload path fails silently.

## Acceptance Criteria

1. Given a HEIC file, when uploaded as an avatar, then either the avatar appears or a visible error is shown.
2. Given any rejected upload, when it fails, then the user sees an explicit error message.

## Estimated size

2 files, ~110 LOC, band: Target.
