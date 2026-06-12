# Refresh Workflow (the common case)

Standing up a tree happens once; refreshing it happens every release. This is the worked refresh track. It assumes a tree already exists (possibly authored before this skill, possibly without frontmatter) and brings it back to current, re-hunts the changed code, and reconciles findings without creating duplicates.

Read alongside `frontmatter-schema.md` (the schemas) and `SKILL.md` (the principles, templates, two-tier findings, and reconciliation outcomes).

## Step R0: Adopt the tree (one-time, if it predates the spec)

A tree authored before this skill has no frontmatter, so the deterministic staleness story cannot fire. Adopt it first:

1. For every doc, derive `source_refs` by reading what the doc actually documents (the files/endpoints/screens it describes), set `last_reviewed` to the doc's last git-commit date (`git log -1 --format=%cd --date=short -- <doc>`), set `altitude`/`surface`/`parent`, and `status: current`.
2. For surfaces whose code lives in another repo, use the external `source_refs` mapping form with a `pin` set to that repo's current HEAD (see `frontmatter-schema.md`).
3. **This is additive, not an overwrite.** Adding frontmatter and correcting stale facts does not violate "never overwrite a human-authored tree"; that rule protects human prose and nuance, not the absence of metadata. Preserve the prose; add the metadata.

Adoption is also where the **finding-identity migration** happens (Step R1).

## Step R1: Migrate prose-only findings to F-IDs (one-time)

Prior findings may exist only as prose inside docs (Open Questions, gap lists) with no IDs, and possibly as already-filed beads with no ledger link. Bind them:

1. Create `docs/products/_findings.md` if absent (schema in `frontmatter-schema.md`).
2. Walk every doc's in-situ findings. For each, mint an `F-ID`, add a ledger row, and back-annotate the prose with the `F-ID` (`**Bug (F-012):** ...`).
3. Bind to existing beads: search the tracker by evidence/keyword; when a finding matches an existing bead, record that bead's ID in the row's Bead column and set status accordingly. This is the one-time reconciliation that the keyword-search-and-hope step was doing by hand; after it, the ledger is the durable join.

After R0+R1, every subsequent refresh is deterministic.

## Step R2: Detect staleness

Run the checker:

```bash
python3 <skill>/scripts/check_staleness.py docs/products
```

It reports each doc as stale / unverifiable / stub / current, using `last_reviewed` (or the doc's commit date as the bootstrap baseline) and diffing `source_refs`. **Unverifiable** means an external surface whose probe repo was not reachable; check that repo by hand and bump its `pin`. Concentrate the rest of the refresh on the stale and unverifiable docs.

## Step R3: Reconcile each stale doc

For each stale doc, in pyramid order:

1. Read the changed `source_refs` (the script lists exactly which paths moved).
2. Reconcile the prose against the new reality. Correct stale framing explicitly (say what changed); preserve human nuance.
3. Bump `last_reviewed` to today and, for external refs, update `pin` to the external repo's current HEAD.

## Step R4: Concentrated re-hunt

Re-run the Active Hunt techniques (SKILL.md), but focus on code changed since each doc's prior `last_reviewed`, the highest-yield place for new bugs/gaps/debt. New code is where invariants get violated and migrations get left half-done. Log new findings to the ledger with fresh F-IDs and in-situ back-references.

## Step R5: Reconcile findings (four outcomes)

For every finding (carried-over and new), choose exactly one outcome. This replaces the old binary create/skip:

| Outcome | When | What to do |
|---|---|---|
| **New bead** | A promoted finding (see two-tier model) with no existing bead | Author an audit-grade bead; record its ID in the Bead column |
| **Skip** | Already has a bead, unchanged since last run | Leave it; no tracker action |
| **Fold in** | Overlaps an existing bead but is distinct (a near-duplicate that belongs to the same work unit) | Extend that bead (add to its Acceptance Criteria / Steps to Reproduce / scope), set the ledger row status to `folded` and point its Bead column at the host bead. Do **not** file a near-duplicate |
| **Close** | The finding has been fixed since last run (the hunt no longer reproduces it) | Set the ledger row status to `closed`, keep the row for history, close the bead if one exists |

Detecting fold-in candidates: when a new finding shares a surface and overlapping evidence (same file/endpoint/area) with an existing open bead, treat it as a fold-in candidate and surface it at the confirmation gate rather than auto-filing.

## Step R6: Promote and author beads (two-tier)

Per the two-tier model in SKILL.md: every finding is already a ledger row (cheap, done in R4). Now author full `bead-audit`-grade beads only for the **promoted** set (auto-promote High severity; Medium/Low stay ledger rows until a human promotes them). Batch-author the promoted set using `bead-audit`'s JSON/backlog mode rather than one expensive inline pass.

## Step R7: Present and confirm

Summarize: stale docs reconciled, external surfaces re-pinned, findings by type/severity/outcome, and the promoted beads (drafted, not yet created). **Wait for confirmation** before creating or folding any beads. On confirmation, apply the tracker changes and write bead IDs back into the ledger.

## Refresh quality checklist

- [ ] Tree adopted (frontmatter present on every doc) before relying on staleness
- [ ] Prose findings migrated to F-IDs with in-situ back-references
- [ ] `check_staleness.py` was run; stale + unverifiable docs were the focus
- [ ] External surfaces verified against their repo and re-pinned
- [ ] Re-hunt concentrated on changed code, new findings logged with F-IDs
- [ ] Every finding has exactly one of the four outcomes
- [ ] Fold-in candidates were surfaced, not auto-filed as near-duplicates
- [ ] Only promoted findings were authored as beads; the rest remain ledger rows
- [ ] Tracker changes applied only after confirmation; bead IDs written back
