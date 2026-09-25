# Ship gate contract

This document fixes three things the deterministic ship plan
([feature-plan-deterministic-ship.md](plans/feature-plan-deterministic-ship.md)) needs before any
implementation: the gate configuration format, the steps that move a repository onto it, and the
method that measures the current workflow so a later run can be compared to it.

## The gate configuration format

A repository declares its ship gate in `.tadw/ship-gates.json`, version 1. The file is plain JSON.
It does not depend on Markdown: a reader never infers a check from prose. `TADW_SHIP_CHECK` still
outranks the file, and `TADW_SHIP_CHECK_TIMEOUT` keeps its meaning.

```json
{
  "version": 1,
  "gates": [
    {
      "name": "markdown-format",
      "command": ["rumdl", "fmt", "--check", "."],
      "inputs": ["**/*.md", ".rumdl.toml"]
    },
    {
      "name": "hook-suite",
      "command": ["node", "hooks/test-hooks.js"],
      "inputs": ["hooks/**"],
      "depends_on": ["markdown-format"],
      "resources": ["tracker"],
      "timeout": 300,
      "reuse": true
    }
  ]
}
```

| Key | Required | Meaning | Default |
|---|---|---|---|
| `version` | yes | The format version. Only `1` is valid. | - |
| `gates` | yes | A non-empty list of gate objects. | - |
| `name` | yes | A unique, non-empty name for the gate. | - |
| `command` | yes | The command as an argument list, never a shell string. | - |
| `inputs` | no | Repository-relative globs that the result depends on. | `[]` |
| `cwd` | no | Working directory, relative to the repository root, staying inside it. | `"."` |
| `timeout` | no | Seconds before the check is stopped, a positive whole number. | `900` |
| `depends_on` | no | Names of other gates that must finish before this one starts. | `[]` |
| `resources` | no | Shared resources, such as `tracker`. Gates naming the same one run in sequence. | `[]` |
| `reuse` | no | Whether a saved result may satisfy this gate. Milestone 5 defines the rule. | `false` |

Three rules keep the format honest:

- **Inputs are what a later reuse rule compares.** A gate with no `inputs` says it cannot name
  them, so `reuse` is forced to `false` for it. Rerunning is the safe answer.
- **`depends_on` must be acyclic.** A gate cannot depend on itself, and a loop of gates is
  rejected with the loop named, because no scheduler could start any gate on it.
- **Unknown keys are errors.** A misspelled `timeout` must not fall back to the default in silence.
- **A command is an argument list.** No quoting rule applies. Only `TADW_SHIP_CHECK` is a shell
  string.

`skills/ship/scripts/read_gate_config.py --repo-root <path>` validates the file, prints every
problem to stderr, and prints the normalized configuration, with each default filled in, to
stdout. It exits 0 when valid, 1 when invalid, and 2 when the file is missing.

## Migration procedure

<!-- ship-setup:start -->

Migration is one-time and per repository. `/tadw:ship` runs the Python command, so a repository
needs this setup before its first ship. This repository finished step 4 before the skill switched.

1. **Choose a route.** Set `TADW_SHIP_CHECK` to one command that runs the whole gate, or write
   `.tadw/ship-gates.json`. The override needs no file, and it outranks the file when both exist.
2. **List the checks the repository runs today.** Take them from the workflow being replaced, for
   example the command block in `AGENTS.md`. Leave out any check that is deliberately not a gate,
   such as a model eval.
3. **Write one gate per check.** Split each shell line into an argument list, and add `inputs` where
   you can name them. Add `depends_on` or `resources` only where a check needs one; a check that
   uses the tracker database names the resource `tracker`.
4. **Validate, then compare.** Run `read_gate_config.py`. Then check that the gate names and
   commands match the source list, one for one. A missing check is a check nothing enforces.
5. **Measure both versions** with the baseline method below, so the speed comparison starts from
   numbers.

After the switch, a repository with no file and no override stops with `SHIP_BLOCKED gate` and the
setup action. That stop is deliberate: a repository cannot be migrated from here.

<!-- ship-setup:end -->

`tadw-ship --repo-root <path> --check-gate` shows which gate a ship run would select, and stops
there. `tadw-ship` is `bin/tadw-ship`, and `skills/ship/scripts/tadw_ship.py` takes the same
flags. It prints `{"source": ..., "gates": [...]}` and exits 0. `source` is `TADW_SHIP_CHECK` or
`.tadw/ship-gates.json`, and each gate has every default filled in. The override appears as one
gate named `TADW_SHIP_CHECK` whose command is `["sh", "-c", <the value>]`. With no usable gate,
it names each problem and the setup action on stderr, prints `SHIP_BLOCKED gate`, and exits 1. It
selects the gate before it runs any `git` or `bd` command, so that stop changes nothing.

`tadw_ship.py --repo-root <path> --run-gate` selects the same gate and runs it through
`skills/ship/scripts/run_checks.py`, the executor the pre-push hook shares. It honors each gate's
`timeout`, `depends_on`, and `resources`, and runs no more gates at once than the machine has
processors. Ship's policy stays strict: a gate that fails, times out, cannot start, or is
interrupted stops the run with `SHIP_BLOCKED gate`, and a missing tool is never skipped. A gate
that can never start, because it depends on a later gate that shares one of its resources, is
recorded as not run, so it stops the run too rather than waiting forever.

A blank `TADW_SHIP_CHECK` counts as unset, because an empty command would pass every ship.
`TADW_SHIP_CHECK_TIMEOUT` bounds the override command alone. A gate from the file uses its own
`timeout` key and ignores the variable, so raise that key for a slow configured gate. A value
that is not a positive whole number stops the run and names that variable as the fix.

This repository finished step 4 with `.tadw/ship-gates.json`.
`skills/ship/scripts/test_tadw_ship.py` checks that its commands match the `AGENTS.md` block
minus `python3 evals/run.py`, so a check added to one and not the other fails that suite.

## Baseline method

`skills/ship/scripts/measure_gate_baseline.py` runs a gate command and records, for each run, the
elapsed seconds, the number of check processes started, and the exit code. It reports the medians.
It counts a check process by putting a counting shim ahead of each named tool on `PATH`, so a tool
started by absolute path or through `sys.executable` is not counted. Name the tools to count with
`--tool`; the default is `rumdl`, `node`, `python3`, `bash`, and `claude`.

To measure the current workflow:

1. Check out a fixed commit, with a clean working tree.
2. Take the command string the current ship run executes, from `TADW_SHIP_CHECK` or the
   `AGENTS.md` block minus `python3 evals/run.py`.
3. Cold: clear the caches you care about, then run
   `measure_gate_baseline.py --repo-root <repo> --warmup 0 --runs 3 --command "<gate>"`.
4. Warm: run the same command with `--warmup 1 --runs 3`.
5. Keep both JSON outputs with the commit hash. Report cold and warm separately, even when cold
   regresses.

Run the new command the same way against the same commit. The plan's speed criterion passes only
when the warm run starts fewer check processes and has a lower median elapsed time.
