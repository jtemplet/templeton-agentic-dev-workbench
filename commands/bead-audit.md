---
description: "Audit one or more bead issue bodies against the Marr, size, and type-specific section standards"
argument-hint: "[bead-id or content] [--json]"
---

Use the `bead-audit` skill to evaluate bead bodies against the same content standards applied during decomposition.

Provide bead content in any form: paste the body directly, give a file path, or paste the output of your issue tracker's show command. The skill does not assume any particular CLI is available. Add `--json` for machine-readable output when grooming a backlog programmatically.

The skill will:

1. Parse each bead body into its canonical sections, recognizing common heading variants (`## Why`, `WHY:`, `**Why:**`) so format differences do not hide present content
2. Run the applicable audits per bead: Marr (Why / How / Done when), size (skipped for epics and operational beads), and type-specific sections (Acceptance Criteria for task/feature/bug, Steps to Reproduce for bug, Success Criteria for epic)
3. Report a **content verdict** (is the substance there?) and a **structure verdict** (is it under the canonical heading?) per section, rolling up to PASS / REFORMAT (auto-fixable) / NEEDS WORK
4. Offer to draft corrected content (into the byte-exact canonical headings, or into native tracker fields like `br`'s acceptance_criteria/design/notes), self-verify each draft so it re-passes, and mark each `applyable` so a `/goal`-style loop only writes back complete fixes

A substantively complete bead in the wrong format is a REFORMAT, not a failure. Drafts that still need human input carry an `[AUTHOR TO COMPLETE]` placeholder and are flagged `applyable: false` so they are never written back. Use this before claiming a bead, during backlog grooming, or after inheriting a project.
