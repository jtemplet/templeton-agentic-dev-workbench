# Frontmatter and Ledger Schemas

The canonical schemas for the two machine-read artifacts in a product-surface-docs tree: the per-doc frontmatter and the `_findings.md` ledger. The staleness checker (`scripts/check_staleness.py`) reads against these, so keep docs conformant.

## Per-doc frontmatter

Every doc in `docs/products/` (except the ledger and coverage artifacts, see below) opens with this block:

```yaml
---
surface: web                       # the surface this doc belongs to; apex uses "overview"
parent: ../dashboard.md            # up-link to the enclosing directory's owner doc; apex omits
altitude: leaf                     # overview | surface | capability | area | leaf
last_reviewed: 2026-06-12          # date this doc was last reconciled against code (YYYY-MM-DD)
source_refs:                       # the code this doc is a product-altitude view of (see below)
  - ui/src/views/SleepView.vue
  - server/health_data_warehouse/domains/sleep/
status: current                    # current | stale | stub
---
```

Field notes:

- **`parent`** is the relative link to the owner doc of the enclosing directory level (a leaf at `web/dashboard/sleep/sleep.md` has `parent: ../dashboard.md`). The apex doc omits it.
- **`altitude`** drives nothing in the script but documents the pyramid level and keeps `status: stub` legible.
- **`last_reviewed`** is the staleness baseline. If absent, the script falls back to the doc file's own last git-commit date (the bootstrap rule), so a frontmatter-less tree still gets a real baseline on its first refresh. Always write it once you author or reconcile a doc.
- **`status`** is advisory and is recomputed by the script; keep it roughly accurate so a human scanning the tree sees the state.

## `source_refs`: in-repo and external

`source_refs` is the load-bearing field: it is the set of code paths whose change should make this doc stale. Two forms:

### In-repo (string form)

```yaml
source_refs:
  - ui/src/views/SleepView.vue            # a file
  - server/health_data_warehouse/domains/sleep/   # or a directory (trailing slash optional)
```

The script runs `git log --since=<baseline> -- <path>`; any commit touching the path marks the doc stale.

### External (mapping form) for multi-repo products

A product surface can live in a different repo (e.g. an iOS app in `atlas-ios` while web+api are here). A plain path would diff to nothing forever and the surface could never be detected as stale. Use the mapping form with a pinned SHA:

```yaml
source_refs:
  - repo: atlas-ios                        # logical name of the external repo
    path: Sources/Recovery/                # path within that repo
    pin: 9f3c1a2                            # the external repo SHA this doc was last reconciled against
    probe: ../atlas-ios                     # optional: a local checkout to diff against
```

Probe behavior in the script:

- If `probe` exists and is a git repo, it runs `git -C <probe> log <pin>..HEAD -- <path>`. Non-empty output marks the surface stale; the finding is that the doc is pinned to an old SHA.
- If `probe` is missing or unreachable, the doc is reported **unverifiable** (not silently current). The reconciler must then check that repo by hand and bump `pin`.
- After reconciling an external surface, update `pin` to the external repo's current HEAD SHA.

Mixed in-repo and external refs on one doc are fine; the doc is stale if any ref (either kind) has advanced.

## The `_findings.md` ledger

The ledger is a first-class artifact, not an improvised file. It lives at the top of the tree (`docs/products/_findings.md`) and is the single source of truth for finding identity. Underscore-prefixed files are skipped by the staleness checker.

````markdown
---
kind: findings-ledger
last_updated: 2026-06-12
next_id: 12                         # the next F-ID to mint; monotonic, never reused
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

Column and field semantics:

- **ID**: `F-NNN`, minted from `next_id`, monotonic, never reused. This is the durable identity across runs.
- **Status**: `open` (live finding), `folded` (merged into another bead, see Bead column), `closed` (fixed; keep the row for history).
- **Severity**: High (user-facing breakage, revenue leak, privacy issue), Medium (degraded experience or notable missing capability), Low (cosmetic, internal, speculative). Severity drives promotion (see the two-tier model in SKILL.md).
- **Evidence**: the file/endpoint/screen/commit that grounds the finding. This is also the dedup key (type + evidence) when deciding whether a finding already exists.
- **Bead**: the tracker ID once promoted, or `-` while the finding is a ledger-only row. A `folded` row points at the bead it was merged into.

### In-situ back-reference (the join)

Every finding written in a doc's prose (an Open Question, a "What's not on this surface" bullet, an inline tag) **must carry its F-ID**, so the prose and the ledger stay joined across runs:

```markdown
**Bug (F-001):** `/training-load/*` has no server-side tier gate; the full payload
leaks to free via direct API calls. See `api/recovery.md`.
```

Without the back-reference there is no deterministic way to map a prose finding on the next run to its ledger row, and findings drift into duplicates. The F-ID is the link.
