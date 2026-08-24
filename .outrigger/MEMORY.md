# Repository memory

Short-form operational memory for this repo: failure modes, fragile
subsystems, and recurring review findings worth re-surfacing to the agent on
every run. This file is visible and operator-editable; the memory loader only
reads it, it never rewrites it.

## Format

Each `- ` bullet is one entry. Everything else (these headings, this prose,
blank lines, HTML comments) is ignored, so keep the file readable.

An entry may open with a `(phases: a, b)` scope to surface only in those
phases; an entry with no scope applies to every phase. Phase names match the
pipeline phases: `development`, `simplify`, `review`, `reconcile`, `qa`,
`closeout`.

## Entries

<!--
Examples (delete these once you add real entries):
- A finding that every phase should heed, with no scope.
- (phases: review) A recurring review finding to re-surface during code review.
- (phases: qa) A known-fragile subsystem QA should exercise carefully.
-->
