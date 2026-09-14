# Git hooks

Two hooks carry this repository's own gates (`pre-push` and `reference-transaction`); four are
beads shims that call `bd hooks run <hook>`: `pre-commit`, `post-merge`, `post-checkout`, and
`prepare-commit-msg`. Those four did not exist before, so beads did no flushing, no importing
after a pull, and added no identity trailers; the shims beads had written sat in `.beads/hooks`,
which git never reads while `core.hooksPath` names this directory.

The root `AGENTS.md` keeps the setup command and the rules that bind every push: what `pre-push`
runs, when it refuses, the `TADW_PREPUSH=off` switch, and the `v*` tag gate. This file holds the
mechanism under each of them. `CLAUDE.md` here is a symlink to this file.

**`pre-push` is deliberately not a beads shim.** It exports the tracker and commits `.beads/`
itself, on the terms recorded in the comments at the end of `.githooks/pre-push`, and calling
`bd hooks run pre-push` there would export twice. `bd hooks list` therefore reports it with an
empty version; that is expected.

## Stage one: the check list

Each command the root `AGENTS.md` list excludes from the hook has its own reason:

- `claude plugin validate .`: `reference-transaction` already gates it at the tag, and spawning
  the CLI is the slowest check.
- `python3 .githooks/test_prepush.py`: it pushes inside a fixture wired to this hook, so running
  it here would recurse.
- Both eval commands: see the next paragraph.

**No git hook runs anything under `evals/`.** `python3 evals/run.py` makes a real model call for
every case, which is too slow and too costly for a push. `python3 evals/test_run.py` calls no
model and costs about 2 seconds, so cost is not why it left the hook. The evals are a measurement
you run deliberately. Both stay in the root `AGENTS.md` check list, so the ship gate still runs
the harness suite.

Derive the number of checks with `grep -c '^check ' .githooks/pre-push`.

**The checks run at the same time.** Each `check` line assigns its check to a background job, and
the jobs start after the last line. A push waits for the slowest check rather than for the sum. A
passing push prints how many seconds the checks took on its summary line. The report still lists
failures in the order of the `check` lines, because each check writes to its own numbered files.

**No more jobs run at once than `getconf _NPROCESSORS_ONLN` reports processors.** Past that, the
checks compete for the CPU, and a check that waits on a timeout or a race can fail a clean push.

`test_probe_api.py` cannot be made much faster. It starts real servers and waits on real sockets,
which is the only way to check which host it addresses, and that it leaks no process.

**`after_previous=yes` above a `check` line puts that check in the job of the check on the line
above.** The two then run one after the other. The flag applies to that one line. When the check
above was skipped for a missing tool, the flagged check gets a job of its own. The two
`bd`-command checks are paired this way, because `bd` opens its embedded Dolt database inside each
process.

**An interrupted push is refused, never passed.** On HUP, INT, or TERM during the checks, the hook
does three things, then exits 129, 130, or 143:

1. **It freezes every process under it** with SIGSTOP, and looks again until nothing new turns up.
   A stopped process cannot start another one.
2. **It sends SIGINT to the checks**, so a Python check runs its own cleanup. A background job
   starts with SIGINT ignored, and `sh` cannot undo that, so the hook starts each check through
   `python3`, which resets SIGINT and then becomes the check.
3. **It sends SIGTERM to whatever still runs after a grace period,** after freezing it again with
   every process it started in the meantime.

A check that started but recorded no exit status counts as failed. Once the checks finish, a signal
only ends the hook.

**Stage 3 can still leave the export staged.** A signal between its `git add .beads/` and its
`git commit` leaves `.beads/` staged in the index. The serial hook had the same gap.

Two behaviors are deliberate:

- **Every check runs, even after one fails**, and all failures report together. A hook that
  stopped at the first would make you push, fail, fix, and fail again on the next one.
- **A missing tool warns by name and allows the push.** Neither `rumdl` nor `node` is universally
  installed, and an unpushable clone is worse than an unchecked push. If every tool is missing,
  the push still proceeds. The hook then reports that it verified nothing, because a run that
  checked nothing has not earned the word "passed".

A push that only deletes a remote ref carries no code, so the hook runs nothing. A push that
deletes one ref and updates another does carry code, so the hook checks it.

When the checks pass, this stage prints one line carrying how many ran and how long they took.
`.githooks/test_prepush.py` pins all of it against real `git push --dry-run` runs in a throwaway
fixture.

## Stage two: the recorded verdict

**`pre-push` has a second stage: the verdict `/quality-gates` recorded.** Git calls exactly one
pre-push hook, so both stages share the file. Each stage reports under its own message, so one
push answers both questions.

The stage reads `quality-gates-report.json` from the directory `git rev-parse --git-dir`
resolves. That directory is per worktree, so a linked worktree reads its own verdict rather than
the main checkout's.

This stage forgives by design:

- **Only a recorded verdict of `FAIL` refuses the push.** The message names the verdict, the head
  it was recorded for, and the time. It names both exits too: re-run `/quality-gates`, or set
  `TADW_PREPUSH=off`.
- **A missing or unreadable report warns and allows.** Absence is not evidence of a problem.
  Blocking there would refuse every documentation push from a fresh clone, and would teach people
  to turn the hook off.
- **A verdict recorded off the line you are pushing warns as stale, and allows.** It describes
  some other tree. A `FAIL` still refuses in that state, because one command refreshes it.

## `reference-transaction`

It refuses to create a `v*` tag when `claude plugin validate` fails. Git has no pre-tag hook, so
this is the only hook that sees a tag being created and can still stop it. It gates tags alone,
and leaves commits, branches, and non-`v` tags untouched. A missing `claude` on PATH warns and
allows, because an untaggable repository is worse than an unchecked tag.
