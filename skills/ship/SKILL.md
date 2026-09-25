---
name: ship
description: "Land a reviewed bead's feature branch on the default branch by running the tadw-ship runner once. It gates the exact commit it lands, closes the bead, pushes without forcing, and ends with one SHIP_DONE / SHIP_BLOCKED line. Use after /quality-gates and /verify-acceptance pass, or as an unattended orchestrator step."
---

# Ship

Run the ship runner once, and pass its result on. The runner takes every step itself, so this skill
adds no step and no judgment. Do not use it when the repository merges through pull requests, or
when the branch carries two beads.

## Setup

The runner needs a gate: `TADW_SHIP_CHECK`, one shell command, or `.tadw/ship-gates.json`, one gate
per check. With neither, the run stops with `SHIP_BLOCKED gate`.
[docs/ship-gate-contract.md](../../docs/ship-gate-contract.md) gives the one-time setup steps.

## Run

From the checkout that holds the feature branch, run:

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/tadw-ship" <bead-id>
```

Omit `<bead-id>` to take the bead from the branch name. If the command still starts with a dollar
sign, use the base directory printed above this skill, with `/skills/ship` removed from its end.
Never search the disk for another installed copy.

The gate can take many minutes. Run the command in the background, or with the longest tool
timeout, and wait for it to exit. Never start a second run while one is still going.

The last line is the machine line: `SHIP_DONE <hash>` with exit 0, or `SHIP_BLOCKED <slug>` with
exit 1.

## Report

Show the user the runner's output. Then, in order:

1. When the output holds a `cd <path>` line, run that `cd` before any other command. Tell the
   user that their own terminal needs it too.
2. On `SHIP_BLOCKED`, when a line reads `shipping <bead-id>`, run
   `bd update <bead-id> --add-label needs-human`.
3. End your reply with the runner's machine line, copied exactly, as its last line.

When the output has no machine line, the runner failed before it could report. Quote the error, and
end with `SHIP_BLOCKED internal`.

<!-- stop-slugs:start -->

| Slug | Means |
|---|---|
| `gate` | No gate is configured, or a gate failed, timed out, or could not start |
| `conflict` | A rebase or squash conflict in a path the runner does not resolve |
| `tracker` | The bead is missing, closed, or ambiguous, or `bd close` or `bd export` failed |
| `git-state` | The repository was not fit to ship from, the default branch moved, or the push failed |
| `internal` | Anything else; the lines above the machine line say what |

<!-- stop-slugs:end -->

## Never

- Repeat a step by hand, or run a script under `skills/ship/scripts/` instead of the runner.
- Set `TADW_SHIP_CHECK` to skip or narrow the gate, or set `TADW_PREPUSH=off`.
- Force a push, or edit `.beads/issues.jsonl` by hand.
- Ask the user a question. Report, and stop.
