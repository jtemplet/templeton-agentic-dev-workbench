# Frontmatter and Ledger Schemas

Two files in a product-surface-docs tree are read by a script, so their format is fixed. This
page gives both: the frontmatter every document carries, and the `_findings.md` ledger. The
staleness checker (`scripts/check_staleness.py`) reads against these schemas, so keep every
document conformant, meaning it matches the schema exactly.

## Per-document frontmatter

Every document in `docs/products/` opens with this block. The ledger and the coverage files are
the exception. The staleness checker skips any file whose name starts with an underscore.

```yaml
---
surface: web                       # the surface this document belongs to; the overview uses "overview"
parent: ../dashboard.md            # link to the owner document of the enclosing directory
altitude: leaf                     # overview | surface | capability | area | leaf
last_reviewed: 2026-06-12          # date this document was last checked against code (YYYY-MM-DD)
source_refs:                       # the code this document describes at product level (see below)
  - ui/src/views/SleepView.vue
  - server/health_data_warehouse/domains/sleep/
status: current                    # current | stale | stub
---
```

Field notes:

- **`parent`** is the relative link to the owner document of the enclosing directory. A document
  at `web/dashboard/sleep/sleep.md` has `parent: ../dashboard.md`. The overview document omits
  this field.
- **`altitude`** names the level of the document. The script does nothing with it. It is there so
  a person can read the level, and so `status: stub` makes sense.
- **`last_reviewed`** is the date the staleness check measures from. When it is absent, the script
  falls back to the document file's own last git-commit date. That fallback lets a tree with no
  frontmatter get a real baseline on its first refresh. Always write this field once you author
  or check a document.
- **`status`** is advisory. The script computes each document's state itself and never reads this
  field. Keep it roughly accurate, so a person scanning the tree sees the state.

## `source_refs`: in-repository and external

`source_refs` is the field the staleness check actually reads. It is the set of code paths whose
change should mark this document out of date. There are two forms.

### In-repository (string form)

```yaml
source_refs:
  - ui/src/views/SleepView.vue            # a file
  - server/health_data_warehouse/domains/sleep/   # or a directory (trailing slash optional)
```

The script runs `git log --since=<baseline> -- <path>`. Any commit that touches the path marks
the document out of date.

### External (mapping form) for products spread over several repositories

A product surface can live in a different repository. An iOS app can sit in `atlas-ios` while
web and api sit here. A plain path would then diff to nothing forever, and the surface could
never be detected as out of date. Use the mapping form with a pinned commit:

```yaml
source_refs:
  - repo: atlas-ios                        # logical name of the external repository
    path: Sources/Recovery/                # path within that repository
    pin: 9f3c1a2                            # the commit this document was last checked against
    probe: ../atlas-ios                     # optional: a local checkout to diff against
```

What the script does with `probe`:

- When `probe` exists and is a git repository, the script runs
  `git -C <probe> log <pin>..HEAD -- <path>`. Any output marks the surface out of date. The
  finding is that the document is pinned to an old commit.
- When `probe` is missing or unreachable, the script reports the document as **unverifiable**. It
  does not quietly report it as current. Check that repository by hand, then update `pin`.
- After you check an external surface, set `pin` to the current commit of the external
  repository.

One document may mix in-repository and external refs. The document is out of date when any ref of
either kind has moved.

## The `_findings.md` ledger

The ledger is a required file, not one you improvise. A ledger is the table of every finding.
It sits at the top of the tree, at `docs/products/_findings.md`, and it is the single source of
truth for which finding is which. The staleness checker skips every file whose name starts with
an underscore, so the ledger is never treated as a document.

````markdown
---
kind: findings-ledger
last_updated: 2026-06-12
next_id: 12                         # the next F-NNN to assign; it only counts up, and never repeats
counts:                            # convenience rollup, recomputed on each run
  open: 9
  folded: 1
  closed: 2
---

# Findings Ledger

| ID | Type | Surface | Severity | Status | Title | Evidence | Action | Bead |
|---|---|---|---|---|---|---|---|---|
| F-001 | Bug | api | High | open | training-load endpoints ungated | server/.../training_load.py | add require_tier | hdw-abc1 |
| F-002 | Gap | web | Medium | open | no signed-out demo dashboard | ui/src/views/LandingView.vue | build demo route | - |
| F-007 | Debt | api | Low | folded | dashboards/ vs domain split | server/.../api/routers/ | finish migration | hdw-z93c |
| F-003 | Bug | web | High | closed | stress endpoint ungated | ui/src/stores/stress.js | fixed in 4f21a9 | hdw-2xs3 |
````

What each column and field means:

- **ID**: an `F-NNN` identifier taken from `next_id`. It only counts up, and a number is never
  reused. This is how a finding keeps its identity from one run to the next.
- **Status**: `open` for a live finding, `folded` for one merged into another bead (the Bead
  column names it), and `closed` for one that is fixed. Keep a closed row for the record.
- **Severity**: High means user-facing breakage, lost revenue, or a privacy problem. Medium means
  a degraded experience or a notable missing capability. Low means cosmetic, internal, or
  speculative. Severity decides which findings get promoted to a bead. The two-tier model in
  `SKILL.md` explains promotion.
- **Evidence**: the file, endpoint, screen, or commit the finding rests on. This is also how you
  tell whether a finding already exists: match on type plus evidence.
- **Bead**: the tracker identifier once the finding is promoted, or `-` while it is only a ledger
  row. A `folded` row names the bead it was merged into.

### The identifier repeated in the document

Every finding written into a document's prose **must carry its `F-NNN` identifier**. A finding can
appear in an Open Questions list, in a "What is not on this surface" list, or as an inline tag.
Wherever it appears, write the identifier with it:

```markdown
**Bug (F-001):** `/training-load/*` has no server-side tier gate; the full payload
leaks to the free tier through direct calls to the endpoint. See `api/recovery.md`.
```

The identifier is the only link between the prose and the ledger. Without it, the next run cannot
tell which ledger row a prose finding belongs to, and the same finding gets filed twice.
