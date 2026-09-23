# Ship gate baseline

This is the measured baseline that the deterministic ship plan compares against
([ship-gate-contract.md](ship-gate-contract.md) defines the method). It sets the speed target for
milestone 1.

## What was measured

| Item | Value |
|---|---|
| Commit | `ba9b6bab2d9503e76dfbb7b304112bb690ee12b2` |
| Command | The `AGENTS.md` command block minus `python3 evals/run.py`, joined with `;` in order |
| Runner | `skills/ship/scripts/measure_gate_baseline.py`, 3 measured runs per case |
| Tools counted | `rumdl`, `node`, `python3`, `bash`, `claude` (all found on `PATH`) |
| Working tree | Clean at the measured commit; measured in its linked worktree |

Every measured run of the command exited 0.

## Results

| Case | Warmup runs | Median elapsed | Median check processes |
|---|---|---|---|
| Cold | 0 | 402.1 seconds | 3,870 |
| Warm | 1 | 367.8 seconds | 3,870 |

Individual runs, in order:

| Case | Elapsed seconds | Check processes |
|---|---|---|
| Cold | 402.1, 418.6, 358.0 | 3,870, 3,868, 3,872 |
| Warm | 364.8, 367.8, 382.4 | 3,870, 3,868, 3,872 |

Processes by tool in the first cold run: `python3` 2,772, `bash` 944, `rumdl` 103, `node` 50,
`claude` 1.

## Caveats

- **"Cold" here means no warmup run.** No cache was cleared before it, so the cold and warm medians
  differ by about 34 seconds and both include whatever the operating system had cached.
- **The count is a lower bound.** A tool started by absolute path or through `sys.executable` is
  not counted. Most of the `python3` and `bash` starts come from the test suites that build
  temporary repositories, including `.githooks/test_prepush.py`.
- **The run-to-run spread is large.** Elapsed time varied by up to 60 seconds between runs of the
  same case. The process count varied by 4.
- These are one machine and one day. They are a comparison point, not a general speed claim.

## Speed target

The plan's criterion 26 passes when, for the same commit and the same checks, a warm ship-and-push
run with the new command satisfies both:

- It starts fewer than **3,870** check processes (this baseline's median).
- Its median elapsed time is below **367.8 seconds** (this baseline's warm median).

Report the new command's cold result separately, even when it is slower.
