# Refresh Workflow (the common case)

This page gives the eight steps that bring an existing product document tree back to current.
You create a tree once. You refresh it every release, so this is the path most runs take.

The steps assume a tree already exists. It may predate this skill, and it may carry no
frontmatter. They bring it back to current, search the changed code again, and reconcile the
findings without creating duplicates.

Read this page alongside `frontmatter-schema.md`, which holds the schemas, and `SKILL.md`, which
holds the principles, the document templates, the two-tier findings model, and the four
reconciliation outcomes.

## Step R0: Add frontmatter to a tree that predates this skill

A tree written before this skill has no frontmatter, so the staleness check cannot run. Add the
frontmatter first. Do this once.

1. For every document, work out `source_refs` by reading what the document actually describes:
   the files, endpoints, and screens it covers. Set `last_reviewed` to the document's last
   git-commit date, which `git log -1 --format=%cd --date=short -- <doc>` prints. Set `altitude`,
   `surface`, and `parent`. Set `status: current`.
2. For a surface whose code lives in another repository, use the external `source_refs` mapping
   form. Set `pin` to that repository's current `HEAD`. The form is in `frontmatter-schema.md`.
3. **This adds to the document. It does not overwrite it.** Adding frontmatter and correcting a
   stale fact does not break the rule against overwriting a tree a person wrote. That rule
   protects the prose and the detail a person added, not the absence of metadata. Keep the prose,
   and add the metadata.

Step R1 belongs to the same one-time pass.

## Step R1: Give an identifier to every finding that exists only as prose

Earlier findings may exist only as prose inside documents, in Open Questions lists and gap lists,
with no identifier. Some may already have a bead that nothing links to. Link them:

1. Create `docs/products/_findings.md` if it is missing. Its schema is in
   `frontmatter-schema.md`.
2. Read every finding written into a document's prose. For each one, assign an `F-NNN`
   identifier, add a ledger row, and write the identifier back into the prose, as
   `**Bug (F-012):** ...`.
3. Link each finding to any bead that already exists. Search the tracker by evidence and by
   keyword. When a finding matches an existing bead, write that bead's identifier into the row's
   Bead column and set the row's status to match. This replaces the hand search that used to
   happen on every run. After it, the ledger is the durable link.

Once R0 and R1 are done, every later refresh reaches the same answer from the same tree.

## Step R2: Find the out-of-date documents

Run the checker:

```bash
python3 <skill>/scripts/check_staleness.py docs/products
```

It reports each document as stale, unverifiable, `stub`, or current. It measures from
`last_reviewed`, or from the document's own commit date when that field is absent, and it diffs
every path in `source_refs`. **Unverifiable** means an external surface whose `probe` repository
was not reachable. Check that repository by hand and update its `pin`. Concentrate the rest of
the refresh on the stale and unverifiable documents.

## Step R3: Reconcile each out-of-date document

Work through the out-of-date documents from the top of the tree down. For each one:

1. Read the `source_refs` paths that changed. The script names exactly which paths moved.
2. Correct the prose against the new reality. Say what changed rather than deleting the old
   framing in silence. Keep the detail a person added.
3. Set `last_reviewed` to today. For an external ref, set `pin` to the external repository's
   current `HEAD`.

## Step R4: Search the changed code again

Run the search techniques from `SKILL.md` again. Concentrate on code that changed since each
document's previous `last_reviewed` date. That is where new bugs, gaps, and debt are most likely,
because new code is where a guarantee gets broken and where a migration gets left unfinished.
Write every new finding to the ledger with a fresh identifier, and repeat that identifier in the
document's prose.

## Step R5: Reconcile the findings (four outcomes)

Give every finding exactly one outcome. This covers the findings carried over and the new ones.
It replaces the older choice between create and skip.

| Outcome | When | What to do |
|---|---|---|
| **New bead** | A promoted finding with no existing bead. The two-tier model in `SKILL.md` defines promotion | Write a bead that passes the `bead-audit` standard; record its identifier in the Bead column |
| **Skip** | It already has a bead, and it has not changed since the last run | Leave it. Do nothing in the tracker |
| **Fold in** | It overlaps an existing bead but is distinct, so it belongs to the same unit of work | Extend that bead: add to its Acceptance Criteria, its Steps to Reproduce, or its scope. Set the ledger row's status to `folded`, and point its Bead column at the bead you extended. Do **not** file a near-duplicate |
| **Close** | It has been fixed since the last run, and the search no longer reproduces it | Set the ledger row's status to `closed`. Keep the row for the record. Close the bead if one exists |

Here is how to spot a fold-in candidate. A new finding shares a surface with an open bead, and
shares evidence with it, such as the same file, endpoint, or area. Treat that finding as a
fold-in candidate. Show it when you ask the user to confirm, and do not file it on your own.

## Step R6: Promote the findings and write the beads

Follow the two-tier model in `SKILL.md`. Every finding already has a ledger row, which Step R4
wrote and which costs almost nothing. Now write a full bead, one that passes the `bead-audit`
standard, only for the findings you promote. Promote every High severity finding without asking.
A Medium or Low finding stays a ledger row until a person promotes it. Write the promoted beads
in one batch through `bead-audit`'s JSON mode, the `--json` output built for whole-backlog work.
Do not run one expensive pass per finding.

## Step R7: Present the result and wait

Summarize four things: the out-of-date documents you reconciled, the external surfaces you
re-pinned, the findings counted by type, severity, and outcome, and the promoted beads. The beads
are drafted, not created. **Wait for confirmation** before you create or fold any bead. Once the
user says yes, apply the tracker changes and write each bead identifier back into the ledger.

## Refresh quality checklist

- [ ] Every document has frontmatter, before you rely on the staleness check
- [ ] Every prose finding has an identifier, written into both the ledger and the prose
- [ ] `check_staleness.py` was run, and the stale and unverifiable documents were the focus
- [ ] Every external surface was checked against its repository and re-pinned
- [ ] The second search concentrated on changed code, and every new finding has an identifier
- [ ] Every finding has exactly one of the four outcomes
- [ ] Fold-in candidates were shown to the user, not filed as near-duplicates
- [ ] Only promoted findings became beads; the rest are still ledger rows
- [ ] Tracker changes were applied only after confirmation, and bead identifiers were written back
