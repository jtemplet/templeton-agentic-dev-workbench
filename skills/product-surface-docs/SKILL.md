---
name: product-surface-docs
description: Build and refresh a product documentation tree under docs/products/, organized by product surface such as web, api, and iOS. The tree holds one document per surface, and one for each capability and feature below it. Grounds every claim in the codebase, and searches that codebase for bugs, feature gaps, and feature debt as a required goal rather than a side effect. Records every finding in a ledger, and turns the ones worth acting on into beads written to the bead-audit standard. Includes a staleness checker, so keeping the tree current is a command you run. Use when asked to map product surfaces, document what the product does by surface, build or refresh docs/products, or audit the product for bugs, gaps, and debt.
---

# Product Surface Docs

This skill does two things, and both matter equally. It turns a codebase into a documentation
tree you can read from the top down. It also searches that codebase for bugs,
feature gaps, and feature debt.

The tree holds one overview document for the whole product, one document per product surface, and
one document for each capability and feature below that. Each document opens with a one-sentence
answer to "what is this?", then the supporting structure, then the detail. Each capability belongs
to exactly one surface, and no capability is left out.

The search is not a side effect of writing documents. It is a deliberate audit pass. It runs
named techniques against the code, writes every finding to a ledger, and turns the findings worth
acting on into beads written to the `bead-audit` standard. A ledger is a table of every finding.

## The tree to copy, and what this skill adds

Copy `atlas/docs/products/`, a real and mature tree. Read it for voice, for keeping each document
at one level, for how deep to go, and for how to ground a claim in code.

Do not copy its metadata. Atlas predates this skill's frontmatter requirement, so its documents
carry no frontmatter. This skill extends the tree you copy. Match the tone and structure of atlas,
then add the frontmatter and the ledger this skill requires.

On a tree that predates this skill, the first action is to add the frontmatter to it. That adds
to each document and does not overwrite it. See "Required Workflow" below, and
`references/refresh-workflow.md`.

## When to Use

- "Map the product surfaces", or "document what this product does, by surface"
- Creating `docs/products/` for the first time
- Refreshing an existing tree after a release, so it stays current. This is the common case
- Auditing the product for bugs, feature gaps, and feature debt

## When NOT to Use

- For engineering and architecture documents. This tree sits at product level: what the user gets
  and where, not how the code is built. Link out to the engineering documents instead of
  repeating them.
- For a single feature spec. Use `/product-brief`.
- For competitor positioning. Use `/competitive-analysis`.

## How the Tree Is Divided

### Every capability belongs to one surface

Every capability belongs to exactly one surface's tree. Every capability the product actually
has appears somewhere. Divide the product by surface first, such as web, api, iOS, and a
command-line tool. Do not divide it by feature first. Each surface has different readers and
different release schedules, and each changes at a different rate.

That has a cost. A feature that genuinely belongs to more than one surface, such as sync or
billing, lives in one surface's tree. Link to it from the other surfaces. Write the link rather
than repeating the content.

Check the division before you write anything. List every surface. List every capability. Then
look for two problems: a capability claimed by two surfaces, and a capability in the code that
no document covers. Each one is a finding.

### The five levels of the tree

Every document sits at one of five levels: overview, surface, capability, area, or leaf. A leaf is
the deepest level, a single feature or view. Directory depth sets the level:

```text
docs/products/
  product_overview.md            # OVERVIEW: the whole product in one document
  _findings.md                   # the findings ledger (see "Findings" below)
  <surface>/<surface>.md         # SURFACE: web, api, ios (owner document named after the dir)
  <surface>/<capability>.md      # CAPABILITY: a coherent feature family on that surface
  <surface>/<area>/<area>.md     # AREA: when a surface has sub-areas, such as web/dashboard
  <surface>/<area>/<leaf>/<leaf>.md   # LEAF: a single feature or view, the deepest level
```

Naming rule: every directory owns a document named after it, such as `web/web.md`, `api/api.md`,
and `dashboard/dashboard.md`. A leaf is a single file. It becomes a directory with an owner
document when it needs children.

Linking rule: every document opens with a blockquote. That blockquote names the document's level
and links to the document above it. Every document except a leaf ends with a list of links to the
documents below it. Call that list the navigation tree.

## Document Templates by Level

The section headings below give each document's shape. Match the depth and tone of
`atlas/docs/products/`. Read `product_overview.md`, `web/web.md`, and
`web/dashboard/sleep/sleep.md` there as the examples. Every document starts with the frontmatter
block defined in `references/frontmatter-schema.md`.

### Overview: `product_overview.md`

> The one-sentence answer for the whole product.

- **In one sentence** / **Customer** (personas, and the people this is not for) /
  **Job-to-be-Done** (the main job, and the jobs under it)
- **Mechanism** (how it works, in concept; a text diagram)
- **Surfaces** (a table of surface, role, and a link to the owner document; say why the product
  is divided by surface)
- **Business model** / **Current state** (a table; tag rows `Production`, `Live`, `Bug/debt`, and
  `Remaining gap:`)
- **What we measure (and don't)** (every "No" row is a finding) / **Open questions** / **Where to
  go from here** (links to the documents below)

### Surface: `<surface>/<surface>.md`

> The one-sentence answer for this surface, linking up to `product_overview.md`.

- **In one sentence** / **Reader of this document** / **What lives on this surface**
- **User journey and architecture** (a text diagram) / **Route, endpoint, and screen tables**
  (the access rule for each row)
- **Conventions that span the surface** (authentication, gating, casing, idempotency meaning the
  same call twice does what one call does, and rate limits)
- **What is not on this surface (yet)** (a gap list; every item is a finding) / **Open questions**
  / **Navigation tree** (links to the documents below; mark the stubs)

### Leaf: `<...>/<leaf>.md`

> The one-sentence answer for this feature, linking up to the document above it.

- **Customer** (the personas under the surface's personas) / **Job-to-be-Done** (at this level)
- **What is visible** (the actual user interface or output, with exact source-file references) /
  **States** (loading, empty, error, gated, and so on)
- **What is behind it** (stores, endpoints, methodology documents) / **Tier gating and access**
  (a table)
- **Metrics** (with an "Instrumented today?" column; every "No" row is a finding) / **Open
  questions** (the bugs, gaps, and debt at this level)

## Keeping Current (a command, not a judgment call)

A script decides whether a document is out of date. Every document carries frontmatter.
Its `source_refs` field names the code the document describes at product level. Its
`last_reviewed` field records when the document was last checked against that code. The full
schema is in **`references/frontmatter-schema.md`**, including the form for a surface whose code
lives in another repository.

Run the checker included with this skill:

```bash
python3 <skill>/scripts/check_staleness.py docs/products
```

It reports each document as one of four states:

- **stale**: a path in `source_refs` changed since `last_reviewed`.
- **unverifiable**: an external surface whose `probe` repository was not reachable.
- **stub**: the document has no `source_refs` yet.
- **current**: nothing in `source_refs` has moved.

When a document has no `last_reviewed`, which happens on a tree that predates this skill, the
script falls back to the document's own last git-commit date. So the first refresh still works.
The full refresh workflow is in `references/refresh-workflow.md`.

## The Search for Bugs, Gaps, and Debt

Searching is a required goal, run as a deliberate pass. Writing a document tells you what
*should* be true. The search tries to prove those claims false against the code. Every finding is
exactly one of three types:

| Type | Definition | Example |
|---|---|---|
| **Bug** | The released behavior contradicts the intended behavior, the documented behavior, or a stated guarantee | An endpoint described as tier-gated is ungated on the server |
| **Feature gap** | A capability that a persona, a job, or a competitor implies, and that does not exist | No demo dashboard for signed-out visitors |
| **Feature debt** | A capability that exists but is incomplete, inconsistent, out of date, or degraded | Two parallel patterns in the api, the interface other programs call; a document framing that is now out of date |

### Search techniques, run deliberately on each surface

Do not wait to notice a finding. Run these checks.

**Bugs. Try to prove every stated guarantee false:**

- **Guarantee check.** For every guarantee the product claims, grep the code to confirm the code
  enforces it *everywhere*, not just once. Guarantees include tier gates, authentication,
  per-user isolation, idempotency, and response casing, meaning the letter case of field names.
  The common example is a family of endpoints described as gated, with no `require_tier` on some
  of its routes.
- **Bad input from outside.** Trace every input that comes from outside. Examples are a sync
  payload, a webhook, form data, and an OAuth callback, meaning the redirect a sign-in provider
  sends back. Check what happens when the input is missing, malformed, or oversized.
- **Contract mismatches.** Compare the shape of each api response against what the client reads.
- **Contradiction search.** Find code that contradicts a documented behavior, or contradicts
  another part of the code.

**Feature gaps. Build a coverage table, do not guess:**

- **The persona and job table.** For each persona and each job-to-be-done in the overview
  document, find the surface that serves it. An empty cell is a gap.
- **The features the category expects.** Compare the product against category norms and against
  named competitors.
- **Surfaces connected to nothing.** Look for a user interface wired to no code, an endpoint no
  client calls, and half-built create, read, update, and delete.
- **First-run and empty states.** Check that they are actually built, not just the path where
  everything works.

**Feature debt. Find the unfinished and the out of date:**

- **Marker search.** Grep for `TODO`, `FIXME`, `HACK`, `deprecated`, and `legacy`.
- **Parallel patterns.** Two ways of doing one thing means a migration was left unfinished.
- **Out-of-date framing.** Find documents, comments, and copy that no longer match the code.
- **Under-specified states.** Find a state the code reaches and nothing describes.
- **A convention one surface breaks.** Find a convention that most surfaces follow and one
  surface does not.

On a refresh, concentrate the search on code that changed since each document's `last_reviewed`
date. New code is where new problems are most likely.

## Findings: record every one, promote only some

Writing a full bead for every finding costs enough that it quietly pushes people to report less.
That is the opposite of what an audit wants. So recording a finding and writing a bead are two
separate tiers.

### Tier 1: record every finding in the ledger (always, and cheap)

Every finding gets a row in `docs/products/_findings.md`, and a mention in the document it
belongs to. This is cheap, so report **everything**. The ledger is the single source of truth for
which finding is which. Its full schema is in `references/frontmatter-schema.md`. Two rules keep
findings identifiable from one run to the next:

- **An identifier that never changes.** Each finding gets an `F-NNN` identifier taken from the
  ledger's `next_id`. The number only counts up, and it is never reused. Before you assign one,
  check whether the finding already exists: match on type plus evidence. Reuse the existing
  identifier when it does.
- **The identifier repeated in the document.** Every finding written into a document's prose
  carries its identifier inline, as `**Bug (F-001):** ...`. That identifier is the only link
  between the prose and the ledger. Without it, findings turn into duplicates on the next run.

Record a severity of High, Medium, or Low on each row. Severity decides which findings get
promoted.

### Tier 2: promote a finding to a bead (on action, in one batch)

Write a full bead, one that passes the `bead-audit` standard, only for the findings you
**promote**. Promote every High severity finding without asking. A Medium or Low finding stays a
ledger row until a person promotes it. Reporting stays unrestricted, and every work unit people
act on still passes the `bead-audit` standard.

A promoted bead is written to pass the `bead-audit` standard. That means the Marr Why, How, and
Done when sections, the size band, meaning the estimated size of the change, and the sections its
type requires. Map each finding type to a bead type:

| Finding type | Bead type | Sections that type requires |
|---|---|---|
| Bug | `bug` | Acceptance Criteria and **Steps to Reproduce** |
| Feature gap | `feature`, or `task` when it is small | Acceptance Criteria |
| Feature debt | `task` | Acceptance Criteria |

Write the promoted set in one batch through `bead-audit`'s JSON mode, the `--json` output built
for whole-backlog work. Do not run one inline pass per finding. Check every draft against
`bead-audit` before you create it, and never create a bead that fails its own audit. Write the
created bead's identifier into the ledger row's Bead column.

### Reconciling on a refresh (four outcomes, not two)

On a refresh, give every finding exactly one outcome. `references/refresh-workflow.md` covers
each in detail.

| Outcome | When |
|---|---|
| **New bead** | A promoted finding with no existing bead |
| **Skip** | It already has a bead, and nothing changed |
| **Fold in** | It overlaps an existing bead but is distinct. Extend that bead: add to its Acceptance Criteria, its Steps to Reproduce, or its scope. Set the row to `folded`, and point its Bead column at the bead you extended. Do not file a near-duplicate |
| **Close** | It has been fixed since the last run. Set the row to `closed`, keep the row for the record, and close the bead if one exists |

Fold in is a real outcome, not an afterthought, because a finding that overlaps another and is
still distinct is common. Show every fold-in candidate when you ask the user to confirm. A
candidate shares a surface and evidence with an open bead. Do not file it on your own.

## Required Workflow

**Decide first: refresh, or first build.** Before anything else, check whether the target tree
already exists. Look for `docs/products/product_overview.md`, or any document under the target
directory.

**When the tree exists, the refresh workflow is the default and the required path.** This is the
common case, and it is what a weekly scheduled run does. A refresh updates documents in place. It
keeps the prose and the detail a person wrote, corrects out-of-date facts by adding to them, sets
`last_reviewed` to today, and reconciles findings against the ledger. Write a document from
nothing only when it does not exist yet, such as a brand-new surface, a brand-new capability, or a
whole tree in a repository that has none. Never delete or overwrite a whole existing document as a
way to write it again.

**First build** (a repository with no documents under the target directory):

1. **Find or create the tree.** The default is `docs/products/`. Match the host repository's own
   convention when it has one.
2. **Find the surfaces** in the codebase, such as apps and clients, the api, command-line tools,
   and marketing. Read the structure and the entry points. Do not guess.
3. **Check the division.** Map every capability to exactly one surface. Record every overlap and
   every gap as a finding. Do not go on until each capability belongs to exactly one surface,
   and none is missing.
4. **Draft each document, top down**, from the overview to the surfaces to the capabilities to
   the leaves. Ground each one in code, give it frontmatter, and link it to the document above
   and the documents below. Cite exact files.
5. **Search deliberately, one surface at a time**, using the techniques above. Write every
   finding to the ledger with its identifier, and repeat that identifier in the document.
6. **Add a coverage index** to `product_overview.md`: which surfaces and capabilities are full,
   and which are stubs.
7. **Promote and present.** Promote every High severity finding, plus any the user picks, into
   drafted beads. Present the surfaces, the documents, the ledger, and the drafted beads. **Wait
   for confirmation before you create any bead.** Once the user says yes, create them and write
   their identifiers back into the ledger.

**Refresh** (the common case, on an existing tree): follow `references/refresh-workflow.md`. In
short, add frontmatter where it is missing, and give every prose finding an identifier. Run
`check_staleness.py`, and reconcile the out-of-date documents. Search the changed code again,
apply the four outcomes, promote, and confirm.

## Additional Resources

- **`scripts/check_staleness.py`**: the staleness checker. It handles this repository and other
  repositories, and it falls back to a document's commit date. Run it to find out-of-date
  documents.
- **`references/frontmatter-schema.md`**: the frontmatter schema for each document, the form for
  `source_refs` that point at another repository, and the `_findings.md` ledger schema.
- **`references/refresh-workflow.md`**: the refresh workflow, worked step by step. It covers
  adding frontmatter, giving prose findings an identifier, finding out-of-date documents,
  reconciling them, searching again, the four outcomes, and promotion.

## Critical Rules

**Always:**

- Match `atlas/docs/products/` for voice, for keeping each document at one level, and for
  grounding claims in code. Add the frontmatter and the ledger this skill requires on top of it.
- Keep each capability in exactly one surface, and leave none out. Treat every overlap and every
  gap as a finding.
- Search on purpose: run the search techniques deliberately against every surface. The search is
  a required goal, never a side effect.
- Ground every product claim in a specific file, endpoint, screen, or commit. A claim with no
  evidence is a guess, and you must mark it as one.
- Give every document the blockquote that links up, the navigation tree that links down (every
  level except a leaf), and frontmatter with `source_refs` and `last_reviewed`.
- Write every finding to the ledger with an identifier that never changes, and repeat that
  identifier in the document. Report everything, because a ledger row is cheap.
- Promote findings to beads on purpose, and automatically for High severity. Check every draft
  against `bead-audit` before you create it.
- On a refresh, use the four outcomes. Show fold-in candidates instead of filing near-duplicates.

**Never:**

- Repeat engineering or architecture detail. Link to it instead.
- Invent a capability, a persona, or a metric the code does not support. Put what you wish
  existed into the findings as a gap.
- Let a capability exist in code with no document, or sit in two surfaces' trees.
- Drop a finding to avoid the work of writing a bead. Recording is Tier 1 and cheap. Writing the
  bead is Tier 2, and it comes later.
- Create or fold a bead without the user's explicit confirmation, or create one that fails the
  `bead-audit` standard.
- Treat adding frontmatter or correcting an out-of-date fact as overwriting a tree a person
  wrote. That rule protects the prose and the detail a person added, not the absence of metadata.
  Metadata and factual corrections always add to a document.
- Write an existing tree again from nothing, or delete or overwrite a whole document that already
  exists. When a tree is present, refresh it in place. A scheduled weekly run must destroy
  nothing. Write from nothing only for documents that do not yet exist.

## Quality Checklist

- [ ] Every capability maps to exactly one surface, and every capability in the code is covered
- [ ] The search ran deliberately on every surface, rather than turning up findings along the way
- [ ] `product_overview.md` exists and links down to every surface. Every document has the
      blockquote that links up, and every level except a leaf has the list that links down
- [ ] Every document has frontmatter with `source_refs` and `last_reviewed`. A surface whose code
      is in another repository uses the pinned form
- [ ] `check_staleness.py` runs against the tree with no unexpected `stub` or unverifiable result
- [ ] Every product claim cites a file, endpoint, screen, or commit
- [ ] Every finding is in `_findings.md` with an identifier that never changes, and that
      identifier also appears in the document. Nothing was dropped to avoid writing a bead
- [ ] Every promoted finding, meaning High severity plus the ones the user picked, is drafted as
      a bead that passes the `bead-audit` standard. The rest are still ledger rows
- [ ] On a refresh, every finding has exactly one of the four outcomes, and fold-in candidates
      were shown rather than filed
- [ ] Beads were created or folded only after confirmation, and their identifiers were written
      back into the ledger
