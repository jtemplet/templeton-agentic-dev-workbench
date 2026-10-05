# Ship gate contract

This document fixes three things the deterministic ship plan
([feature-plan-deterministic-ship.md](plans/feature-plan-deterministic-ship.md)) needs before any
implementation: the gate configuration format, the steps that move a repository onto it, and the
method that measures the current workflow so a later run can be compared to it.

## Where the gate comes from

The runner takes the first of these that exists, and reads no other source:

1. `TADW_SHIP_CHECK`, one shell command.
2. `.tadw/ship-gates.json`, in the format below.
3. The repository's executable pre-push hook. The runner finds it with
   `git rev-parse --git-path hooks/pre-push`, so `core.hooksPath` is honored. It runs in the
   candidate worktree with the arguments and stdin line git gives a push of the candidate to the
   default branch. A hook given an empty stdin reads it as a delete-only push, and many hooks then
   check nothing.
4. The repository's executable pre-commit hook. It already runs when the runner commits the
   candidate, so a commit it refuses stops the run with `SHIP_BLOCKED gate`.

With none of the four, the run stops with `SHIP_BLOCKED gate` and names adding a pre-push hook.

Sources 3 and 4 need no setup, because a repository's hooks are the bar a person's push already
clears (`tadw-awsr`). A thin hook makes a thin gate. The fix for that is a stronger hook, which also
protects a push made without ship. Use source 1 or 2 only when ship needs a different gate from a
plain push. The real push runs the pre-push hook a second time, on the same commit; the runner
never pushes with `--no-verify`.

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
      "tools": ["node"],
      "env": ["CLAUDE_CONFIG_DIR"],
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
| `inputs` | no | Repository-relative globs for the files the result depends on. | `[]` |
| `tools` | no | Names of the programs the command runs, as found on `PATH`. | `[]` |
| `env` | no | Names of the environment variables the result depends on. | `[]` |
| `cwd` | no | Working directory, relative to the repository root, staying inside it. | `"."` |
| `timeout` | no | Seconds before the check is stopped, a positive whole number. | `900` |
| `depends_on` | no | Names of other gates that must finish before this one starts. | `[]` |
| `resources` | no | Shared resources, such as `tracker`. Gates naming the same one run in sequence. | `[]` |
| `reuse` | no | Whether a saved result may satisfy this gate. See "The reuse rule" below. | `false` |

Four rules keep the format honest:

- **`inputs`, `tools`, and `env` are what the reuse rule compares.** `reuse` is forced to `false`
  for a gate with no `inputs`, and for a gate whose `tools` omit the first word of its `command`.
  Such a gate cannot name what its result depends on, and rerunning is the safe answer. An absent
  `env` is allowed, and it declares that the result depends on no variable.
- **`depends_on` must be acyclic.** A gate cannot depend on itself, and a loop of gates is
  rejected with the loop named, because no scheduler could start any gate on it.
- **Unknown keys are errors.** A misspelled `timeout` must not fall back to the default in silence.
- **A command is an argument list.** No quoting rule applies. Only `TADW_SHIP_CHECK` is a shell
  string.

`skills/ship/scripts/read_gate_config.py --repo-root <path>` validates the file, prints every
problem to stderr, and prints the normalized configuration, with each default filled in, to
stdout. It exits 0 when valid, 1 when invalid, and 2 when the file is missing.

## The reuse rule

A gate with `"reuse": true` can pass without running. The executor,
`skills/ship/scripts/run_checks.py`, saves each pass of that gate. On a later run it takes the
saved pass in place of the check, only when everything the gate declares still matches.

**Rerunning is the default.** A check runs again in every case below.

| Case | Example |
|---|---|
| No saved result exists | The first run in a clone |
| The saved result is not a pass, or cannot be read | A damaged file in the store |
| The command or its `cwd` changed | A new flag in `command` |
| A file matching `inputs` changed, appeared, or went away | An edit to the script under test |
| An `inputs` glob matches no file | A misspelled path |
| A tool resolves to another path, or prints another version | An upgraded `python3` |
| A tool is not on `PATH`, or its `--version` fails | A tool with no `--version` flag |
| A variable named in `env` has another value, or is newly set or unset | A changed `TMPDIR` |
| `git` cannot list the files | A directory outside a repository |

A commit hash is never compared. Two trees at one commit can differ in every row above.

**What the executor reads.** It reads all of this when the check is due to start, and again after
the check passes. It saves the pass only when both readings are equal. The second reading runs
each tool's `--version` again, because the check may have changed a tool.

- **Files.** It lists tracked files, and untracked files that git does not ignore, with
  `git ls-files --cached --others --exclude-standard`. It hashes the working-tree content of each
  file that matches an `inputs` glob. `**` crosses directories, and `*` stays inside one. A file
  that git ignores is never an input, so a gate that reads one must not set `reuse`.
- **Tools.** For each name in `tools`, it records the resolved path and the output of
  `<tool> --version`. The first word of `command` must be in `tools`, or the gate is never reused.
  List every other program the command runs too; nothing checks that part of the list for you.
- **Variables.** For each name in `env`, it records a hash of the value, or that the variable is
  unset. The store never holds the value itself.

**Where passes are saved.** The store is the directory `tadw-check-results` under the path
`git rev-parse --git-common-dir` prints. It holds one JSON file per command and working directory,
and each run replaces the file. Every worktree of a repository shares the store. Sharing is safe,
because a saved pass is matched on content and never on the worktree that wrote it. Ship depends
on the sharing: it gates a temporary worktree, removes it, and then pushes from another checkout.
Delete the directory to make every check run again.

**Both callers save and reuse.** `tadw_ship.py` gives each reusable gate its declarations.
`.githooks/pre-push` names its checks by number, so the executor finds the gate for a check by
its command. It considers only a gate whose `cwd` is `"."`, because every check in the hook runs
at the repository root. The check takes the declarations of the gate with the same argument list.
A run that reused a result says so. Ship prints the count on stderr, and the hook adds it to its
summary line.

**Each caller keeps its own policy.** A reused result is a pass and nothing else. A failed, timed
out, or interrupted check is never saved, so ship still stops on it and the hook still reports it.

No gate in this repository sets `reuse` yet. `/tadw:ship` reads this file through the installed
plugin's copy of `read_gate_config.py`, and a copy older than this rule rejects `tools` and `env`
as unknown keys. `tadw-sbaq` marks the first two gates once the installed copy accepts them.
Add `reuse` to another gate only after you have read what its command reads. Many of the suites
here read `AGENTS.md`, a `SKILL.md`, or the tracker, and each of those is an input. A suite that
builds git repositories also depends on the user's git configuration, which no key can declare.
`check-executor-suite` is one, so it does not set `reuse`.

## Migration procedure

<!-- ship-setup:start -->

Migration is optional, one-time, and per repository. A repository whose hooks run its checks needs
none of it. Follow it only when ship's gate must differ from the hooks. This repository finished
step 4 before the skill switched.

1. **Choose a route.** Set `TADW_SHIP_CHECK` to one command that runs the whole gate, or write
   `.tadw/ship-gates.json`. The override needs no file, and it outranks the file when both exist.
2. **List the checks the repository runs today.** Take them from the workflow being replaced, for
   example the command block in `AGENTS.md`. Leave out any check that is deliberately not a gate,
   such as a model eval.
3. **Write one gate per check.** Split each shell line into an argument list, and add `inputs` where
   you can name them. Leave `reuse` off until "The reuse rule" above holds for the gate.
   Add `depends_on` or `resources` only where a check needs one; a check that
   uses the tracker database names the resource `tracker`.
4. **Validate, then compare.** Run `read_gate_config.py`. Then check that the gate names and
   commands match the source list, one for one. A missing check is a check nothing enforces.
5. **Measure both versions** with the baseline method below, so the speed comparison starts from
   numbers.

A repository with no file, no override, and no hook stops with `SHIP_BLOCKED gate` and the setup
action. That stop is deliberate: the runner never guesses a check the repository does not run.

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
`TADW_SHIP_CHECK_TIMEOUT` bounds the override command and the pre-push hook, with a default of 900
seconds. Raise it for a hook that runs a long test suite. A gate from the file uses its own
`timeout` key and ignores the variable, so raise that key for a slow configured gate. A value
that is not a positive whole number stops the run and names that variable as the fix.

This repository finished step 4 with `.tadw/ship-gates.json`.
`skills/ship/scripts/test_tadw_ship.py` checks that its commands match the `AGENTS.md` block, so
a check added to one and not the other fails that suite.

## Baseline method

`skills/ship/scripts/measure_gate_baseline.py` runs a gate command and records, for each run, the
elapsed seconds, the number of check processes started, and the exit code. It reports the medians.
It counts a check process by putting a counting shim ahead of each named tool on `PATH`, so a tool
started by absolute path or through `sys.executable` is not counted. Name the tools to count with
`--tool`; the default is `rumdl`, `node`, `python3`, `bash`, and `claude`.

To measure the current workflow:

1. Check out a fixed commit, with a clean working tree.
2. Take the command string the current ship run executes, from `TADW_SHIP_CHECK` or the
   `AGENTS.md` block.
3. Cold: clear the caches you care about, then run
   `measure_gate_baseline.py --repo-root <repo> --warmup 0 --runs 3 --command "<gate>"`.
4. Warm: run the same command with `--warmup 1 --runs 3`.
5. Keep both JSON outputs with the commit hash. Report cold and warm separately, even when cold
   regresses.

Run the new command the same way against the same commit. The plan's speed criterion passes only
when the warm run starts fewer check processes and has a lower median elapsed time.
