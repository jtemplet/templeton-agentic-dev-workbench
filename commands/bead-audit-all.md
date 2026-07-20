---
description: "Audit every bead in the tracker in one pass: enumerate, score each, report a ranked backlog-health table"
argument-hint: "[open|all] [--json]"
---

Run a single-pass audit over the whole backlog: enumerate the beads, run the `bead-audit` skill on each one once, and report a ranked health table. This is the bounded, report-only backlog sweep. It does not loop, does not persist a goal, and does not write back to the tracker unless you explicitly ask afterward.

For a single bead, use `/bead-audit` instead. This command is for grooming the whole backlog at once.

## Scope (from `$ARGUMENTS`)

- no argument, or `open`: audit open beads only (the actionable backlog). This is the default.
- `all`: include every status (open, in_progress, deferred, closed). Auditing closed beads is rarely useful; prefer the default unless you are taking inventory.
- `--json`: emit the `bead-audit` skill's machine-readable JSON per bead instead of the markdown table, for a downstream grooming loop.

## Workflow

1. **Verify `br` is available.** Run `which br`. If it is missing, this command cannot enumerate; tell the user and offer to audit bead bodies they paste instead (the `bead-audit` skill is tracker-agnostic and takes pasted content).

2. **Enumerate in one unlimited page.** Fetch every bead in scope with a single call:

   ```bash
   br list --status open --limit 0 --json
   ```

   `--limit` defaults to 50, so omitting `--limit 0` would silently audit only the first 50 beads and then report a clean sweep. Always pass `--limit 0` (unlimited), and after reading confirm `has_more` is false. For `all`, repeat the flag per status: `--status open --status in_progress --status deferred --status closed`.

   If the backlog is empty, say so and stop; there is nothing to audit.

3. **Audit each bead once.** Load the `bead-audit` skill via the Skill tool. Pass every bead's fields to it, treating `br`'s native fields (`design`, `notes`, `acceptance_criteria`) as canonical structure per ADR 0001 (`docs/decisions/0001-native-tracker-fields-are-canonical.md`). Request the scorecard so each bead gets a score and band. Audit each bead exactly once; do not re-audit.

4. **Report a ranked table**, worst band first, so the weakest beads surface at the top:

   ```markdown
   ## Backlog Audit (N beads, scope: <open|all>)

   | ID | Title | Type | Overall | Score | Band |
   |---|---|---|---|---|---|
   | ... | ... | ... | NEEDS WORK / REFORMAT / PASS | 55/100 | Weak |

   PASS: X   REFORMAT (auto-fixable): Y   NEEDS WORK: Z   (of N)
   Median band: <band>. Beads below Great: <count>.
   ```

   Under the table, list only the beads that are REFORMAT or NEEDS WORK, each with the one most critical gap, so the user knows what to fix first.

5. **Do not write back.** This command reports; it never edits a bead. To apply a fix, hand a specific bead to `/bead-audit` and confirm the drafted correction there.

## Why this is single-pass, not a goal loop

The work is bounded: enumerate, audit each once, report. It terminates on its own, so it does not need the `/goal` Stop-hook machinery (which exists to keep a session running until an open-ended condition holds). Running this command again simply re-audits the current backlog from scratch; it holds no state between runs.
