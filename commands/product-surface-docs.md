---
description: "Build and refresh a product documentation tree under docs/products/, one document per product surface, and report the bugs, gaps, and debt found along the way"
argument-hint: "[target dir, default docs/products/]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/product-surface-docs/SKILL.md`. Follow it to turn this
codebase into a product documentation tree organized by surface.

Read that file. Do not invoke the skill by its name. `commands/product-surface-docs.md` and
`skills/product-surface-docs/SKILL.md` share one `tadw:` invocation namespace, and the command
wins. So `Skill(product-surface-docs)` returns this file and never reaches the skill. If that
path does not resolve, find the file with `Glob: **/skills/product-surface-docs/SKILL.md` and
read it from there.

This runs in the `product-cartographer` role: a senior technical product documentarian and
auditor. The role maps the product surfaces. In the same pass, it searches the code for bugs,
feature gaps, and feature debt. Read `agents/product-cartographer.md` for the role's obligations
and judgment principles.

**Refresh first. This is safe to run on a schedule, such as once a week.** When a
`docs/products/` tree already exists, this updates it in place and follows the refresh workflow.
It does not write the tree again from nothing. It keeps every existing document and the prose a
person wrote. It corrects facts by adding to them, sets `last_reviewed` to today, and matches
each finding against the ledger. It writes a document from nothing only for a surface, or a whole
tree, that does not exist yet. The skill checks for an existing tree before it writes anything.

The skill will:

1. Check whether a `docs/products/` tree already exists. When it does, take the **refresh
   workflow**: update in place, keep the prose, and never overwrite a whole document. When it
   does not, build the tree for the first time
2. Find the real product surfaces in the codebase, such as web, api, iOS, and a command-line
   tool. Then check that each capability belongs to exactly one surface, and that no capability
   is missing
3. Write or update every document. The tree holds one `product_overview.md` for the whole
   product, one document for each surface, and one for each capability and feature below it.
   Each document opens with a one-sentence answer to "what is this?" and links to the document
   above it and to the documents below it
4. On an existing tree, follow the refresh workflow. Add frontmatter where it is missing, find
   the documents whose code has changed, correct the facts that changed, and keep what is still
   accurate
5. Ground every product claim in a specific file, endpoint, screen, or commit
6. Search for every bug, feature gap, and feature debt. Write each one to the
   `docs/products/_findings.md` ledger with an `F-NNN` identifier that never changes, and repeat
   that identifier in the document itself. Report everything, because a ledger row is cheap
7. Turn the findings worth acting on into beads written to the `bead-audit` standard. Promote
   every High severity finding without asking. Author the beads in one batch, and check each
   draft against the audit. On a refresh, give each finding exactly one outcome: new bead, skip,
   fold into an existing bead, or close
8. Stamp each document with frontmatter: `source_refs`, `last_reviewed`, and `status`. A surface
   whose code lives in another repository uses the pinned multi-repository form. Include
   `check_staleness.py`, so a later run finds out-of-date documents by running a command
9. Present a summary, the findings ledger, and the drafted beads. Then **wait for confirmation**
   before creating or folding any bead

Match `atlas/docs/products/` for voice and for how deep each document goes. This skill adds the
frontmatter and the ledger that atlas does not have. The target directory defaults to
`docs/products/`. Pass a different path in `$ARGUMENTS` to override it.
