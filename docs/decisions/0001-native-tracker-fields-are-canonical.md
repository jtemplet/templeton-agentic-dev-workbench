# 0001. Native tracker fields are canonical for bead sections

**Date:** 2026-07-20
**Status:** Accepted

## Context

Two shipped skills in this repository give contradictory instructions about where a bead's content should live, and the contradiction went unnoticed until a plan review cross-read them.

`plan-to-beads/SKILL.md:486` instructs: "Pass the Why, How, Done when, type-specific sections, AND Estimated size body to `br create` via `-d`; do not strip any section to save a line." Its command templates put every section into the `--description` body as markdown headings.

`bead-audit/SKILL.md:92-99` states the opposite for trackers with first-class fields. `br` has native `design`, `notes`, and `acceptance_criteria` fields, and the skill maps How to `design`, Done when to `notes`, and Acceptance Criteria to `acceptance_criteria`. It then rules that "a section's content duplicated into the body when a native field exists for it is `structure: variant`," an auto-fixable reformat.

The consequence: **every bead this repo's own generator produces is born non-canonical by its own auditor's standard.** The bead created during the session that surfaced this (`tadw-wdk`) has Why, How, Done when, and Estimated size in `description`, `acceptance_criteria` populated natively, and `design` and `notes` empty. It audits as REFORMAT rather than PASS.

This blocks the planned bead-refinement loop (`docs/plans/feature-plan-bead-refine.md`). A refinement run targeting canonical structure would rewrite 100% of the existing backlog on its first iteration, splitting every body across three fields and directly contradicting the skill that created those beads.

## Options Considered

### Option A: Native fields are canonical

Amend `plan-to-beads` to write How to `--design`, Done when and Out of scope to `--notes`, and Acceptance Criteria to `--acceptance-criteria`, leaving Why and Estimated size in the description body.

- **Pros:** `br ready`, `br show`, `br list --json`, and any dashboard read the native fields directly, so the content becomes queryable rather than trapped in a markdown blob. Aligns the generator with the auditor. Uses the tracker as designed.
- **Cons:** Touches a shipped skill. Every existing bead is non-canonical until refined. `br create` cannot set these fields, so creation becomes two calls (create, then update).

### Option B: The description body is canonical

Amend `bead-audit` so body-resident sections count as canonical structure even when the tracker has native fields for them.

- **Pros:** Smallest possible change. No backlog churn. `plan-to-beads` stays as-is. One self-contained markdown body stays trivially portable to trackers without native fields.
- **Cons:** Permanently forfeits `br`'s structured fields. Any tooling reading `acceptance_criteria` sees an empty field on every bead. The tracker's schema becomes decorative.

### Option C: Both accepted, neither preferred

Treat body-resident and field-resident content as equally canonical.

- **Pros:** No migration, no churn, both skills stay as written.
- **Cons:** Removes the audit's ability to say anything about structure at all, which is the check that makes refinement mechanical. Guarantees a permanently mixed backlog where no consumer can rely on either location.

## Decision

**Native tracker fields are canonical.** When a tracker exposes a first-class field for a section, that field is where the content belongs, and the description body carries only sections with no native slot.

For `br`, the mapping is:

| Section | Destination |
|---|---|
| Why (Computational) | `--description` body |
| How (Algorithmic) | `--design` |
| Done when (Acceptance) | `--notes` |
| Out of scope | `--notes` |
| Acceptance Criteria | `--acceptance-criteria` |
| Estimated size | `--description` body |
| Steps to Reproduce / Success Criteria | `--description` body (no native slot) |

Option A wins because the native fields are not decoration: `br ready`, reporting, and the roadmap dashboard read them directly, and content buried in a markdown body is invisible to all of it. Option B would make the tracker's schema permanently vestigial to save one command. Option C is the worst of both, because it removes the structural check that makes automated refinement possible at all.

The migration cost that argued against Option A is real but bounded, and it is exactly the work the bead-refinement loop was designed to do. This repo's backlog currently holds one bead.

## Consequences

**Easier:**

- `br list --json` returns each section in its own field, so a refinement loop or dashboard reads structured data instead of parsing markdown headings.
- `bead-audit`'s structure verdict becomes meaningful and mechanically fixable, which is the precondition for unattended refinement.
- The generator and the auditor finally agree, so a freshly generated bead passes its own audit.

**Harder:**

- Bead creation is now two calls rather than one, because `br create` exposes no flag for `design`, `notes`, or `acceptance_criteria`. `plan-to-beads` must create then immediately update, and must handle a failure between the two (a bead created but not populated).
- Every bead created before this decision is structurally non-canonical and will be flagged by any audit until refined.
- The canonical structure is now tracker-dependent. A repo using plain GitHub Issues still puts everything in the body, so `bead-audit` must keep both paths, and it already does.

**Accepted risk:** the create-then-update sequence is not atomic. If the update fails, a bead exists with a Why but no How, Done when, or Acceptance Criteria, which is worse than the old single-call failure mode. `plan-to-beads` must report any bead left in that state explicitly rather than silently continuing.
