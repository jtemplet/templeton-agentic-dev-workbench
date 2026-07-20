<!--
Expected: overall REFORMAT (Trivial-band warn), raw score 95/100, band Great.
All content pass (80), structure 5/5 canonical (10), size band Trivial => size warn = half of
10 = 5. Raw 95 would band Excellent; the Trivial-band cap pulls it to Great. Per SKILL.md the
right action is a direct commit, not a bead; the driver cannot auto-fix this (closing is out of
scope), so it is another stalled case.
-->
Title: Fix typo in the welcome email subject line
Type: task

## Why (Computational)

The welcome email subject reads "Wecome" instead of "Welcome". It is the first thing every new
signup sees, and support has forwarded three screenshots of it. Marketing owns the mailer copy
and asked for the fix.

## How (Algorithmic)

Correct the single string in the welcome mailer template. No logic change; the string is a
static literal in one view.

## Done when (Acceptance)

- The welcome email subject reads "Welcome".

## Acceptance Criteria

1. Given a new signup, when the welcome email is sent, then the subject line is spelled "Welcome".

## Estimated size

1 file, 1 LOC, band: Trivial.
