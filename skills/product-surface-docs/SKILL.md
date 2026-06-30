---
name: product-surface-docs
description: Generate, update, and keep current a MECE, Pyramid-Principle product documentation tree under docs/products/, organized by product surface (web, api, iOS, etc.) and drilling down into each surface's capabilities and features. Grounds every claim in the actual codebase, and proactively hunts the code for bugs, feature gaps, and feature debt (invariant falsification, persona x JTBD coverage matrices, dangling-surface and migration sweeps) as a first-class goal. Logs every finding cheaply to a structured ledger and promotes the actionable ones into beads authored to the bead-audit standard. Ships a staleness checker so "keep current" is an executable command, not a vibe. Use when asked to map product surfaces, document what the product does by surface, build or refresh docs/products, or audit the product for bugs, gaps, and debt.
---

# Product Surface Docs

A technique with two co-equal goals: (1) turn a codebase into a navigable, top-down product documentation tree, and (2) **proactively hunt** that codebase for bugs, feature gaps, and feature debt. The tree is one apex overview, a doc per product surface, and a drill-down per capability and feature, organized by the Pyramid Principle (governing thought at the top, supporting detail below) and kept MECE (surfaces are mutually exclusive and collectively exhaustive of the product). The hunt is not a byproduct of writing docs: it is a deliberate audit pass that runs specific techniques against the code, logs every finding cheaply to a ledger, and promotes the actionable findings into beads authored to the `bead-audit` standard.

## The exemplar vs. the spec

The reference implementation is `atlas/docs/products/` (a real, mature tree). Read it as the **gold standard for voice, altitude discipline, depth, and code-grounding**. It is *not* the standard for metadata: atlas predates this skill's frontmatter requirement, so its docs carry no frontmatter. **The spec extends the exemplar.** Match atlas's tone and structure; add the frontmatter and ledger this skill requires. On a tree that predates the spec, the first action is to *adopt* it by retrofitting frontmatter, which is additive and does not count as overwriting human prose (see "Refresh" below and `references/refresh-workflow.md`).

## When to Use

- "Map the product surfaces" / "document what this product does, by surface"
- Standing up `docs/products/` for the first time
- Refreshing an existing tree after a release so it stays current (the common case)
- Auditing the product for bugs, feature gaps, and feature debt

## When NOT to Use

- For engineering/architecture docs (this is product-altitude: what the user gets and where, not how the code is built). Link out to engineering docs, do not duplicate them.
- For a single feature spec (use `/product-brief`).
- For competitor positioning (use `/competitive-analysis`).

## The Two Organizing Principles

### MECE (the horizontal cut)

Surfaces must be **mutually exclusive** (a capability belongs to exactly one surface's tree) and **collectively exhaustive** (every shipped capability appears somewhere). Cut the product surface-first (web / api / iOS / CLI / ...), not feature-first, because each surface has different readers, ship trains, and update cadences. The cost of surface-first is that genuinely cross-surface features (sync, billing) live in one surface's tree and are cross-linked from the others; make that link explicit rather than duplicating content.

Run an explicit MECE audit before writing: list every surface, list every capability, and check for (a) a capability claimed by two surfaces (overlap), and (b) a capability in the code that no doc covers (gap). Overlaps and gaps are findings.

### Pyramid Principle (the vertical cut)

Each document leads with its governing thought (a one-sentence answer to "what is this?"), then the supporting structure, then the detail. Altitude is encoded by directory depth:

```text
docs/products/
  product_overview.md            # APEX: the whole product in one document
  _findings.md                   # the findings ledger (see "Findings" below)
  <surface>/<surface>.md         # SURFACE: web, api, ios (owner doc named after the dir)
  <surface>/<capability>.md      # CAPABILITY: a coherent feature family on that surface
  <surface>/<area>/<area>.md     # AREA: when a surface has sub-areas (e.g. web/dashboard)
  <surface>/<area>/<leaf>/<leaf>.md   # LEAF: a single feature/view, deepest drill-down
```

Naming rule: every directory owns a doc named after it (`web/web.md`, `api/api.md`, `dashboard/dashboard.md`). A leaf is a single file, or a directory-with-owner-doc when it needs children.

Linking rule: every doc opens with a blockquote stating its altitude and linking **up** to its parent, and (above leaf level) ends with a **navigation tree** linking **down** to its children.

## Document Templates by Altitude

Section skeletons. Match the depth and tone of `atlas/docs/products/` (read `product_overview.md`, `web/web.md`, and `web/dashboard/sleep/sleep.md` as exemplars). Every doc starts with the frontmatter block defined in `references/frontmatter-schema.md`.

### Apex: `product_overview.md`

> Governing-thought blockquote ("the top of the pyramid").

- **In one sentence** / **Customer** (personas + anti-personas) / **Job-to-be-Done** (core + sub-jobs)
- **Mechanism** (how it works, conceptually; a text diagram)
- **Surfaces** (the MECE table: surface, role, owner doc link; justify the surface-first cut)
- **Business model** / **Current state** (table; tag rows `Production`, `Live`, `Bug/debt`, `Remaining gap:`)
- **What we measure (and don't)** ("No" rows are findings) / **Open questions** / **Where to go from here** (links down)

### Surface: `<surface>/<surface>.md`

> Altitude blockquote linking up to `product_overview.md`.

- **In one sentence** / **Reader of this document** / **What lives on this surface**
- **User journey / architecture** (a text diagram) / **Route / endpoint / screen tables** (access rules per row)
- **Cross-cutting conventions** (auth, gating, casing, idempotency, rate limits)
- **What's not on this surface (yet)** (gap list; each item is a finding) / **Open questions** / **Navigation tree** (links down; mark stubs)

### Leaf: `<...>/<leaf>.md`

> Altitude blockquote linking up to the parent.

- **Customer** (sub-personas) / **Job-to-be-Done** (leaf-level)
- **What's visible** (the actual UI/output, with exact source-file references) / **States** (loading, empty, error, gated, ...)
- **What's behind it** (stores, endpoints, methodology docs) / **Tier gating / access** (table)
- **Metrics** ("Instrumented today?" column; "No" rows are findings) / **Open questions** (the leaf-level bug/gap/debt list)

## Keeping Current (executable)

Staleness is machine-detectable, not a vibe. Every doc carries frontmatter whose `source_refs` name the code it is a product-altitude view of, and `last_reviewed` records when it was last reconciled. The full schema (including the multi-repo external-ref form for surfaces whose code lives in another repo) is in **`references/frontmatter-schema.md`**.

Detect staleness with the shipped checker:

```bash
python3 <skill>/scripts/check_staleness.py docs/products
```

It reports each doc as **stale** (a `source_ref` changed since `last_reviewed`), **unverifiable** (an external surface whose probe repo was unreachable), **stub** (no `source_refs` yet), or **current**. When a doc has no `last_reviewed` (a tree that predates the spec), the script falls back to the doc's own last git-commit date as the baseline, so the first refresh still works. See `references/refresh-workflow.md` for the full refresh track.

## Active Hunt: Bugs, Gaps, and Debt

Hunting is a first-class objective, run as a deliberate pass. Documenting a surface tells you what *should* be true; the hunt actively tries to *falsify* those claims against the code. Strict taxonomy so findings are MECE:

| Type | Definition | Example |
|---|---|---|
| **Bug** | Shipped behavior contradicts intended/documented behavior or a stated invariant | An endpoint described as tier-gated is ungated server-side |
| **Feature gap** | A capability a persona/JTBD/competitor implies, that does not exist | No demo dashboard for signed-out visitors |
| **Feature debt** | A capability that exists but is incomplete, inconsistent, stale, or degraded | Two parallel API patterns; a doc framing that is now stale |

### Hunt techniques (run these deliberately, per surface)

Do not wait to "notice" findings. Execute the probes:

**Bugs (falsify every stated invariant):**

- **Invariant verification.** For every claimed guarantee (tier gate, auth, per-user isolation, idempotency, response casing), grep the code to confirm it is enforced *everywhere*, not just declared once. Canonical find: a "gated" endpoint family with no `require_tier` on some routes.
- **Boundary handling.** Trace external inputs (sync payloads, webhooks, form data, OAuth callbacks); check null/malformed/oversized handling.
- **Contract mismatches.** Compare API response shapes against what the client consumes.
- **Contradiction sweep.** Find code that contradicts a documented behavior or another part of the code.

**Feature gaps (coverage matrices, not vibes):**

- **Persona x JTBD matrix.** For each persona and job-to-be-done in the apex doc, find the surface that serves it. Empty cells are gaps.
- **Table-stakes check** against category norms and named competitors. **Dangling surfaces:** UI wired to nothing, endpoints with no UI consumer, half-built CRUD. **First-run/empty states** actually built, not just the happy path.

**Feature debt (the incomplete and the stale):**

- **Marker sweep** (`TODO`, `FIXME`, `HACK`, `deprecated`, `legacy`). **Parallel patterns** (unfinished migrations). **Stale framing** (docs/comments/copy that no longer match code). **Under-specified states.** **Convention drift** (a convention enforced on most surfaces but violated on one).

On a refresh, concentrate the hunt on code changed since each doc's `last_reviewed` (the script lists it); new code is the highest-yield place to look.

## Findings: capture cheaply, promote deliberately (two-tier)

A full audit-grade bead per finding is expensive enough that it quietly pressures *under-reporting*, the opposite of what an audit wants. So separate cheap capture from expensive authoring.

### Tier 1: log every finding to the ledger (always, cheap)

Every finding gets a row in `docs/products/_findings.md` and an in-situ mention in the relevant doc. This is cheap, so report **everything**. The ledger is the single source of truth for finding identity; its full schema is in `references/frontmatter-schema.md`. Two rules make findings durable across runs:

- **Stable F-IDs.** Each finding gets an `F-NNN` ID minted from the ledger's `next_id` (monotonic, never reused). Before minting, dedup against the ledger by (type + evidence); reuse the existing ID if the finding already exists.
- **In-situ back-reference.** Every prose finding in a doc carries its F-ID inline (`**Bug (F-001):** ...`). The F-ID is the join between prose and ledger; without it, findings drift into duplicates on the next run.

Severity (High / Medium / Low) is recorded per row and drives promotion.

### Tier 2: promote to a bead (on action, batched)

Author a full `bead-audit`-grade bead only for **promoted** findings: auto-promote High severity; Medium/Low stay ledger rows until a human promotes them. This keeps reporting unthrottled while still producing audit-grade work units for what gets actioned.

A promoted bead is authored to pass the `bead-audit` standard (Marr Why/How/Done when, size, type-specific sections). Map finding type to bead type:

| Finding type | Bead type | Type-specific sections |
|---|---|---|
| Bug | `bug` | Acceptance Criteria + **Steps to Reproduce** |
| Feature gap | `feature` (or `task` if small) | Acceptance Criteria |
| Feature debt | `task` | Acceptance Criteria |

Batch-author the promoted set using `bead-audit`'s JSON/backlog mode rather than one inline pass per finding. Self-verify each draft against `bead-audit` before creation; never create a bead that fails its own audit. Record the created bead's ID in the ledger row's Bead column.

### Reconciliation on a refresh (four outcomes, not two)

For every finding on a refresh, choose exactly one outcome (detailed in `references/refresh-workflow.md`):

| Outcome | When |
|---|---|
| **New bead** | A promoted finding with no existing bead |
| **Skip** | Already has a bead, unchanged |
| **Fold in** | Overlaps an existing bead but is distinct: extend that bead (add to its AC/Steps/scope), mark the row `folded`, point its Bead column at the host bead. Do not file a near-duplicate |
| **Close** | Fixed since last run: mark the row `closed`, keep it for history, close the bead if one exists |

Fold-in is a first-class outcome because overlapping-but-distinct findings are common; surface fold-in candidates (same surface + overlapping evidence) at the confirmation gate rather than auto-filing.

## Required Workflow

**First stand-up** (greenfield tree):

1. **Locate/create the tree.** Default `docs/products/`; match the host repo's convention if one exists.
2. **Discover surfaces** from the codebase (apps/clients, API, CLIs, marketing) using structure and entry points, not guesswork.
3. **MECE audit.** Map every capability to exactly one surface; flag overlaps and gaps as findings. Do not proceed until the cut is MECE.
4. **Draft each doc, top-down** (apex → surface → capability → leaf), grounded in code, with frontmatter and up/down links. Cite exact files.
5. **Active hunt**, deliberately per surface (the techniques above). Log every finding to the ledger (Tier 1) with F-IDs and in-situ back-references.
6. **Coverage index** in `product_overview.md`: which surfaces/capabilities are full vs. stubs.
7. **Promote and present.** Promote High-severity findings (and any the user selects) to drafted beads (Tier 2). Present surfaces, docs, the ledger, and the drafted beads. **Wait for confirmation before creating beads.** On confirmation, create them and write IDs back to the ledger.

**Refresh** (the common case, an existing tree): follow `references/refresh-workflow.md`. In short: adopt frontmatter if missing (additive), migrate prose findings to F-IDs, run `check_staleness.py`, reconcile stale docs, re-hunt the changed code, apply the four reconciliation outcomes, promote, and confirm.

## Additional Resources

- **`scripts/check_staleness.py`**: the executable staleness checker (in-repo + multi-repo, with the bootstrap baseline). Run it to find stale docs.
- **`references/frontmatter-schema.md`**: the per-doc frontmatter schema, the multi-repo external `source_refs` form, and the `_findings.md` ledger schema.
- **`references/refresh-workflow.md`**: the worked refresh track (adopt, migrate findings to F-IDs, detect staleness, reconcile, re-hunt, the four reconciliation outcomes, and promotion).

## Critical Rules

**Always:**

- Match `atlas/docs/products/` for voice, altitude, and code-grounding; add the frontmatter and ledger the spec requires (the spec extends the exemplar).
- Keep the surface cut MECE; treat overlaps and gaps as findings.
- Hunt proactively: run the Active Hunt techniques deliberately against every surface. The hunt is a first-class goal, never a byproduct.
- Ground every product claim in a specific file, endpoint, screen, or commit. A claim with no evidence is a guess and must be marked as one.
- Give every doc the up-link blockquote, the down-link navigation tree (above leaf), and frontmatter with `source_refs` + `last_reviewed`.
- Log every finding to the ledger with a stable F-ID and an in-situ back-reference. Report everything; logging is cheap.
- Promote findings to audit-grade beads deliberately (auto for High severity), and self-verify each draft against `bead-audit` before creation.
- On a refresh, use the four reconciliation outcomes; surface fold-in candidates instead of filing near-duplicates.

**Never:**

- Duplicate engineering/architecture detail; link to it instead.
- Invent capabilities, personas, or metrics the code does not support; put the hoped-for in findings as gaps.
- Let a capability exist in code with no doc, or in two surfaces' trees.
- Suppress a finding to avoid bead-authoring work; capture is Tier 1 and cheap, authoring is Tier 2 and deferred.
- Create or fold a bead without explicit user confirmation, or create one that fails the `bead-audit` standard.
- Treat adding frontmatter or correcting a stale fact as "overwriting a human-authored tree." That rule protects human prose and nuance, not the absence of metadata; metadata and factual corrections are always additive.

## Quality Checklist

- [ ] Surfaces are MECE: every capability maps to exactly one surface, and every code capability is covered
- [ ] The active hunt was run deliberately per surface, not left to incidental noticing
- [ ] `product_overview.md` exists and links down to every surface; every doc has the up-link blockquote and (above leaf) a down-link tree
- [ ] Every doc has frontmatter with `source_refs` (external surfaces use the pinned multi-repo form) and `last_reviewed`
- [ ] `check_staleness.py` runs clean against the tree (no unintended stubs/unverifiables)
- [ ] Every product claim cites a file, endpoint, screen, or commit
- [ ] Every finding is in `_findings.md` with a stable F-ID and an in-situ back-reference; nothing was suppressed to dodge authoring
- [ ] Promoted findings (High severity + selected) are drafted as beads that pass the `bead-audit` standard; the rest remain ledger rows
- [ ] On a refresh, every finding has exactly one of the four outcomes; fold-in candidates were surfaced, not auto-filed
- [ ] Beads were created or folded only after confirmation; bead IDs written back to the ledger
