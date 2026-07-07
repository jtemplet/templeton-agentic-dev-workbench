---
description: "Generate, refresh, and keep current a MECE/Pyramid product documentation tree under docs/products/, by surface, and surface bugs/gaps/debt"
argument-hint: "[target dir, default docs/products/]"
---

Use the `product-surface-docs` skill to turn this codebase into a top-down, surface-organized product documentation tree.

This operates from the `product-cartographer` role: a senior technical product documentarian and auditor who maps the product surfaces and, in the same pass, proactively hunts the code for bugs, feature gaps, and feature debt. Refer to `agents/product-cartographer.md` for the role's obligations and judgment principles.

**Refresh-first, and safe to run on a schedule (e.g. weekly).** When a `docs/products/` tree already exists, this updates it in place: it follows the refresh track rather than regenerating from scratch. Existing docs are preserved and reconciled, not blown away; human prose and nuance are kept, facts are corrected additively, `last_reviewed` is bumped, and findings are reconciled against the ledger. Full-generation only happens for a surface (or the whole tree) that does not exist yet. Before writing, the skill checks for an existing tree and takes the refresh path when it finds one.

The skill will:

1. Detect whether a `docs/products/` tree already exists. If it does, take the **refresh track** (update in place, preserve prose, never wholesale-overwrite); if it does not, do a first stand-up. Either way, discover the real product surfaces from the codebase (web, api, iOS, CLI, etc.) and run a MECE audit so every capability maps to exactly one surface and nothing is missed
2. Refresh (or, for anything not yet documented, generate) the apex `product_overview.md`, a doc per surface, and drill-down docs per capability and feature, each leading with its governing thought and linking up and down the pyramid; on an existing tree it follows the refresh track (adopt frontmatter if missing, detect staleness, reconcile changed facts, preserve everything still accurate)
3. Ground every product claim in a specific file, endpoint, screen, or commit
4. Proactively hunt for every bug, feature gap, and feature debt, logging each cheaply to the `docs/products/_findings.md` ledger with a stable F-ID and an in-situ back-reference (report everything)
5. Promote the actionable findings (auto for High severity) into beads authored to the `bead-audit` standard, batch-authored and self-verified; on a refresh, reconcile each finding as new / skip / fold-in / close
6. Stamp each doc with frontmatter (`source_refs`, `last_reviewed`, `status`; external surfaces use a pinned multi-repo ref) and ship a `check_staleness.py` so a later run detects staleness as a command, not a vibe
7. Present a summary, the findings ledger, and the drafted beads, and **wait for confirmation** before creating or folding any beads

The gold-standard structure to match is `atlas/docs/products/` for voice and altitude (the spec adds the frontmatter and ledger atlas predates). Target directory defaults to `docs/products/`; pass a different path in `$ARGUMENTS` to override.
