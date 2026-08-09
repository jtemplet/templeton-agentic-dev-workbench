---
description: "Audit every bead in the tracker in one pass: enumerate, score each, report a ranked backlog-health table"
argument-hint: "[open|all] [--json]"
---

Run a single-pass audit over the whole backlog: enumerate the beads, read the `bead-audit` rubric once, apply it to each bead exactly once, and report a ranked health table. This is the bounded, report-only backlog sweep. It does not loop, does not persist a goal, and does not write back to the tracker unless you explicitly ask afterward.

The rubric is **read from disk**, not invoked through the Skill tool. Step 4 explains why, and that step is load-bearing: skip it and every score in the report is invented.

This command is for grooming the whole backlog at once. For a single bead, use `/bead-audit`, which now loads the rubric directly: the command file that shadowed the skill was removed.

## Scope (from `$ARGUMENTS`)

- no argument, or `open`: audit open beads only (the actionable backlog). This is the default.
- `all`: include every status (open, in_progress, deferred, closed). Auditing closed beads is rarely useful; prefer the default unless you are taking inventory.
- `--json`: emit the machine-readable JSON per bead defined in the rubric's "Output Modes" section, instead of the markdown table, for a downstream grooming loop.

## Workflow

1. **Verify `br` is available.** Run `which br`. If it is missing, this command cannot enumerate; tell the user and offer to audit bead bodies they paste instead (the `bead-audit` skill is tracker-agnostic and takes pasted content).

2. **Enumerate in one unlimited page.** Fetch every bead in scope with a single call:

   ```bash
   br list --status open --limit 0 --json
   ```

   `--limit` defaults to 50, so omitting `--limit 0` would silently audit only the first 50 beads and then report a clean sweep. Always pass `--limit 0` (unlimited), and after reading confirm `has_more` is false. For `all`, repeat the flag per status: `--status open --status in_progress --status deferred --status closed`.

   If the backlog is empty, say so and stop; there is nothing to audit.

3. **Resolve the grounding baseline once.** The `bead-audit` skill's Grounding Audit reads the main branch, and every bead in this sweep shares one repository. Resolve it a single time before auditing, and reuse it:

   ```bash
   git rev-parse --abbrev-ref HEAD     # note if this is not main
   git rev-parse --short origin/main   # the sha every claim is checked against
   ```

   Fall back to `main` when there is no `origin`, and say which was used. If neither resolves, or the beads' `source_repo_path` names a different repository, every bead is `ungroundable` and the report must say so rather than omitting the column.

4. **Load the audit rubric by reading it.** **Read** the file `${CLAUDE_PLUGIN_ROOT}/skills/bead-audit/SKILL.md`. If that path does not resolve, locate it with `Glob: **/skills/bead-audit/SKILL.md` and read it from there.

   Read the file directly rather than invoking it through the Skill tool. `commands/bead-audit.md` used to shadow the skill and return a twenty-line summary in its place; that file is now deleted, so `Skill(bead-audit)` does reach the rubric. The explicit Read stays anyway, because it is verifiable: the next step asserts which headings the file contains, and no skill invocation can make that promise. The audit needs the weights, the caps, the renormalization rules, and the heading-recognition table. Running it on a summary produces confident scores computed from nothing.

   **Confirm before scoring.** The file you read must contain the headings "Scorecard", "Bands, capped by verdict", and "4. Grounding Audit". If it does not, you have the wrong file: stop and say so rather than scoring from memory. A wrong number here is indistinguishable from a right one downstream.

5. **Audit each bead once.** Apply the rubric you just read to every bead, treating `br`'s native fields (`design`, `notes`, `acceptance_criteria`) as canonical structure per ADR 0001 (`docs/decisions/0001-native-tracker-fields-are-canonical.md`). Produce the scorecard so each bead gets a score and band, showing the per-dimension verdicts and the weighted sum beside it so the arithmetic stays checkable. Audit each bead exactly once; do not re-audit.

   Grounding is the one dimension that costs repository reads, so it scales with backlog size. On a large backlog, ground the beads you will act on and mark the rest `ungroundable` with the reason "not checked at this scope". Never let an unchecked bead report `grounded`.

6. **Report a ranked table**, worst band first, so the weakest beads surface at the top:

   ```markdown
   ## Backlog Audit (N beads, scope: <open|all>)

   Grounded against `origin/main` @ `<short sha>`.

   | ID | Title | Type | Overall | Grounding | Score | Band |
   |---|---|---|---|---|---|---|
   | ... | ... | ... | NEEDS WORK / REFORMAT / PASS | drifted | 55/100 | Weak |

   PASS: X   REFORMAT (auto-fixable): Y   NEEDS WORK: Z   (of N)
   Grounded: A   Drifted: B   Satisfied: C   Ungroundable: D   (of N)
   Median band: <band>. Beads below Great: <count>.
   ```

   **List `satisfied` beads above the table.** They appear done on main and can be closed immediately, so burying them in a quality ranking sends someone to re-specify finished work.

   Under the table, list only the beads that are REFORMAT, NEEDS WORK, or `drifted`, each with the one most critical gap, so the user knows what to fix first.

7. **Do not write back.** This command reports; it never edits a bead, and it never edits code to make a bead's claim true.

   To apply a fix, draft the correction for that one bead here, against the rubric you already read in step 4, and confirm it with the user before any `br update`. Do **not** hand off to `/bead-audit`: that command still redirects to itself rather than loading the rubric (the collision described in step 4), so the handoff would drop the audit standards on the floor at exactly the moment they matter most, when text is about to be written back to the tracker.

## Why this is single-pass, not a goal loop

The work is bounded: enumerate, audit each once, report. It terminates on its own, so it does not need the `/goal` Stop-hook machinery (which exists to keep a session running until an open-ended condition holds). Running this command again simply re-audits the current backlog from scratch; it holds no state between runs.
