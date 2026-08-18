---
name: ship
description: "Land a reviewed bead's feature branch on main locally: rebase onto the base, run the repository's own check suite as the gate, squash-merge, close the bead, push main, and delete the branch. No PR and no GitHub CI; the local gate is the only thing that decides. Runs unattended, fails closed on a red or undetected gate, never force-pushes main, never hand-edits the tracker JSONL, and ends with one machine-readable SHIP_DONE / SHIP_BLOCKED line."
---

# Ship

The last step of the per-bead build loop. The bead was built, reviewed, gated, and accepted on a
feature branch; this lands that branch on main and closes the bead.

There is no pull request and no GitHub CI in this path. **The repository's own check suite, run
locally on the exact tree that will land, is the whole gate.** Everything else in this skill exists
to make sure that gate runs on the right tree, and that a run which stops leaves a state a human
can name.

## When to Use / When NOT to Use

Use when:

- A bead's work sits on a feature branch, has passed `/quality-gates` and `/verify-acceptance`, and
  is ready to land.
- An orchestrator (outrigger, a `/loop`, a script) needs the ship step of a build loop, unattended.
- Asked to "ship", "land", "merge this branch", or "get this bead onto main" in a repository that
  merges locally rather than through pull requests.

Do NOT use when:

- The repository lands work through pull requests and required GitHub checks. Use `/pr-maintain` to
  keep the PR green, then merge it there.
- The work has not been graded yet. Run `/verify-acceptance` first; this skill runs a check suite,
  it does not grade acceptance criteria.
- You want a report about whether the work is ready. This skill acts: it merges, closes, pushes, and
  deletes a branch.
- The branch carries more than one bead. Split it, or ship it by hand. This skill closes exactly one
  bead and refuses to guess between two.

## The Four Rules That Make This Worth Running

**1. The gate runs on the tree that lands, and nothing lands without it.** The branch is rebased
first, so the rebased tip is byte-for-byte the tree the squash-merge produces. A non-zero exit stops
the run before the merge. A gate that could not be detected, or could not run, is a stop too, never
a skip. "No check command found" is not evidence that the code is good.

**2. Every stop names the state it left.** A rebase is never left in progress, main is never
force-pushed, and the report says where the run stopped, what is on disk now, and what a human
should do next. A half-landed branch that nobody can describe costs more than an unlanded one.

**3. The tracker file is merged by its own tooling, never by hand.** `.beads/issues.jsonl` is an
export of a database. Hand-editing it during a conflict writes a state the database does not hold,
and the next export silently reverts it. Under `bd` the resolution is to take either side and
re-export from the database, which is authoritative; there is no JSONL three-way merge to run.

**4. Unattended means report, never ask.** No prompt, no confirmation, no question. When required
input is missing, stop with a report and the machine line. A skill that blocks on a question inside
an orchestrator hangs the loop.

## Invocation

```text
/tadw:ship                 # derive the bead from the current branch name
/tadw:ship <bead-id>       # ship the branch for this bead
```

Environment, all optional:

| Variable | Effect |
|---|---|
| `TADW_SHIP_CHECK` | The exact gate command. Highest-priority gate source (Step 3). |
| `TADW_SHIP_CHECK_TIMEOUT` | Gate timeout in seconds. Default 900. |

There is no variable that skips the gate, and do not add one. `TADW_PREPUSH=off` is likewise not
yours to set: a repository that gates its own push is entitled to gate this one.

## Required Workflow

Track the six steps with TodoWrite. Each step's stop conditions are absolute: on a stop, go straight
to Step 6 and report.

### Step 1: Resolve the Bead and the Ground

**Read the ground first.** All of these are cheap, and each one can end the run:

```bash
git rev-parse --show-toplevel                       # a repository at all
git branch --show-current                           # the feature branch
git status --porcelain                              # must print nothing
git remote get-url origin                           # origin, or no origin
git worktree list --porcelain                       # who has the default branch checked out
```

Resolve the **default branch** in this order: `git symbolic-ref refs/remotes/origin/HEAD` (strip the
`origin/` prefix), then a local `main`, then a local `master`. Do not hardcode `main` in the commands
you run; this file names it `main` for readability only.

Refuse, in this order, and stop at the first that matches:

| Condition | Detect with | Block reason |
|---|---|---|
| Not a git repository | `git rev-parse` fails | `not-a-repo` |
| Already on the default branch | current branch equals it | `on-default-branch` |
| Detached HEAD | `git branch --show-current` prints nothing | `detached-head` |
| Working tree dirty | `git status --porcelain` prints anything | `dirty-tree` |
| A rebase, merge, or cherry-pick is in progress | the path test below finds any of `rebase-merge`, `rebase-apply`, `MERGE_HEAD`, `CHERRY_PICK_HEAD` | `operation-in-progress` |

Test that last one by asking whether the path exists, never by the exit code of `git rev-parse`.
`--git-path` prints a path and exits 0 whether or not anything is there, so reading its exit code
reports an in-progress rebase on every clean repository and the skill never runs:

```bash
for p in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD; do
  [ -e "$(git rev-parse --git-path "$p")" ] && echo "in progress: $p"
done
```

The dirty-tree refusal is not fussiness. An uncommitted file is either work that should be in the
landing commit or work that should not exist, and both readings change what ships.

**Then resolve the bead.**

With an argument, use it. Without one, read the branch name. The convention is
`outrigger/<short-id>/<slug>`, so the second path segment is the candidate. When the branch has
another shape, scan the whole branch name for tracker-id-shaped tokens instead and verify each.

Verify every candidate against the tracker, longest candidate first, and never trust the shape
alone:

```bash
bd show <candidate> --json
```

Three outcomes:

- **Exactly one candidate resolves.** That is the bead. Say which, and how you found it.
- **Two or more resolve.** Stop with `bead-ambiguous`. Refusing beats closing the wrong bead, which
  is silent and tedious to undo.
- **None resolves, and a tracker exists** (`bd` is on PATH and `.beads/` exists). Stop with
  `bead-unresolved`. Landing work whose bead you cannot name defeats the point of the loop.
- **No tracker at all.** Proceed tracker-free: no close, no sync, and the commit subject carries no
  bead id. Say so in the report, twice: in the header and in the summary.

Read `status` from the same JSON. A bead that is already `closed` stops the run with
`bead-already-closed`; something landed this work already, and finding out which is a human's job.

**Confirm which database `bd` resolved to when you are in a linked worktree.** Under `bd` this is
usually already right: it discovers one database per repository through the git common directory, so
a worktree shares the main checkout's database and a close made there is visible everywhere at once.
That is a change from `br`, which gave every worktree its own SQLite cache and required pinning.

Verify rather than assume, because a wrong answer here closes a bead in a throwaway database while
the real one stays open:

```bash
bd where            # prints the resolved .beads directory and database path
bd worktree info    # says whether this is a linked worktree at all
```

If `bd where` names a database under the worktree rather than the main checkout, stop with
`tracker-not-detected` and say so. Do not close a bead against a database you cannot place.

### Step 2: Bring the Branch Current

Record the branch tip before touching anything. It is the restore point this step's own abort check
compares against:

```bash
BRANCH_TIP="$(git rev-parse HEAD)"
```

Fetch, then rebase onto the base:

```bash
git fetch origin            # skip entirely when there is no origin
git rebase origin/main      # or the local default branch when there is no origin
```

Record the base SHA you rebased onto. Step 4 checks that it has not moved.

**On a conflict, look at the conflicted set before anything else:**

```bash
git diff --name-only --diff-filter=U
```

**If the set is exactly `.beads/issues.jsonl`,** resolve it through tracker tooling, in this order:

1. **A deterministic tracker merge the host repository ships.** Outrigger's `merge-tracker`
   subcommand is the shape to look for. Probe before calling it (`outrigger merge-tracker --help`);
   not every version has one, and a call to a subcommand that does not exist reads as a failed merge.
2. **Re-export from the database.** Under `bd` the Dolt database is the source of truth and the
   JSONL is only its export, so a conflict in the export is not a conflict in the data. Take either
   side to clear the markers, then regenerate:

   ```bash
   git checkout --ours .beads/issues.jsonl   # either side; the next line overwrites it
   bd export -o .beads/issues.jsonl
   ```

   This is not the `br` case, where JSONL was canonical and a three-way merge was the only way to
   avoid losing a write. `br sync --merge` does not exist under `bd` and must not be reached for.

**When neither is available, or the one you ran exits non-zero,** abort the rebase and stop with
`tracker-merge-failed`. Do not fall back to a hand edit of the file. Rule 3 has no exception, and a
JSONL that disagrees with the database is worse than an unlanded branch.

Then verify the result before continuing, because a resolution you did not check is a guess:

```bash
grep -n '^<<<<<<<\|^>>>>>>>' .beads/issues.jsonl || echo "no conflict markers"
python3 -c 'import json; [json.loads(l) for l in open(".beads/issues.jsonl") if l.strip()]'
git add .beads/issues.jsonl
GIT_EDITOR=true git rebase --continue
```

Read that first line as "printing nothing is the pass". Do not rewrite it as `grep -c`, which exits
1 when it counts zero: a clean file would then read as a failed check, and the cleanest possible
result would stop the run. Either verification failing is `tracker-merge-failed`, not a reason to
edit the file by hand.

A rebase can conflict once per replayed commit, so loop this. Cap it at 10 resolutions; past that,
abort and stop with `rebase-conflict`. A branch that conflicts on the tracker ten times has a
history problem this skill cannot fix.

**If the conflicted set holds anything else,** abort at once:

```bash
git rebase --abort
git rev-parse HEAD          # must equal BRANCH_TIP
```

Stop with `rebase-conflict`, and name every conflicted path in the report. Do not resolve a source
conflict here. Resolving one means judging code, this skill's remit is landing code that was already
judged, and the human who wrote the branch is the one who should reconcile it.

**If the abort itself fails,** say so in plain words at the top of the report: the repository is left
mid-rebase, and give the exact `git rebase --abort` command to run. That is the one case where this
skill leaves an operation in progress, and it has to be impossible to miss.

### Step 3: Run the Local Gate

**Detect the gate command** in this order, and stop at the first source that yields one. Record which
source you used; the report names it.

1. **`TADW_SHIP_CHECK`**, run verbatim through the shell. This is the unattended override, and the
   only way an operator states a gate this skill would not have found.
2. **What the repository declares for itself**, in `AGENTS.md` or `CLAUDE.md`: a "Commands for This
   Repo" section, a check list, or a named check script. When it declares a list, the list is the
   gate and every command in it must exit 0.
3. **A `check` target in a task runner**: `make check` for a `Makefile`, `just check`, a `check` task
   in `Taskfile.yml`, a `check` script in `package.json`.
4. **The conventional runner for the detected stack.** Detect by config file, never by binary:

   | Config file | Command |
   |---|---|
   | `pyproject.toml`, `setup.cfg` | `pytest -q` |
   | `Gemfile` | `bundle exec rspec` or `bin/rails test` |
   | `package.json` with a `test` script | `npm test` (or the declared package manager) |
   | `go.mod` | `go test ./...` |
   | `Package.swift` | `swift test` |
   | `Cargo.toml` | `cargo test` |

**No source yields a command: stop with `gate-not-detected`.** This is the fail-closed case rule 1
exists for. Do not land unchecked work because the repository was quiet about its checks. The report
tells the operator to set `TADW_SHIP_CHECK` and re-run.

**Then run it**, on the rebased tip:

```bash
git status --porcelain      # must still print nothing
```

A dirty tree here means the rebase or the tracker merge left something behind, and the gate would
grade a tree that is not the one landing. Stop with `dirty-tree`.

Give the run a bounded timeout (`TADW_SHIP_CHECK_TIMEOUT`, default 900 seconds). Capture the exact
command, the exit code, and the real counts.

| Outcome | What to do |
|---|---|
| Exit 0 | Continue to Step 4. Record the counts. |
| Any non-zero exit | Stop with `gate-failed`. Print the failing output, trimmed to the failing lines. |
| Timeout, exit 127, missing runner | Stop with `gate-blocked`. Name what was missing. |

The branch stays rebased after a gate stop, and the report says so. That is useful state: the fix
goes on top of a branch that is already current.

Never report the gate as "green", "clean", or "passing". Report the command, the exit code, and the
numbers it printed.

### Step 4: Land

**Get onto the default branch.** When another worktree has it checked out, `git switch` refuses.
Read `git worktree list --porcelain`, find that worktree's path, and run **every command that acts
on the default branch, in this step and in Step 5, with `git -C <that-path>`**. Do not remove the
other worktree, and do not detach anything to work around it.

That scoping is not tidiness. Step 5's `git reset --hard origin/main` run from the feature branch's
own worktree resets the feature branch, which is the one copy of the work that has not landed yet.
Before any command that moves a branch pointer, confirm where you are:

```bash
git -C <path> branch --show-current    # must print the default branch
```

```bash
git switch main
git pull --ff-only origin main      # skip when there is no origin
```

A `git pull --ff-only` that fails means local main holds commits `origin/main` does not. Stop with
`main-diverged` and change nothing; reconciling two histories of the default branch is a human's
call, and it is not what this run was asked to do.

**Check that the base has not moved** since Step 2. When `origin/main` is now ahead of the SHA you
rebased onto, the gate result no longer describes what would land. Switch back to the feature branch
first, then re-run Steps 2 and 3 against the new base. Re-running them from the default branch would
rebase main onto itself and gate a tree the branch never produced. This is one of the three attempts
Step 5 counts; on the third, stop with `base-moved`.

**Squash-merge and commit:**

```bash
git merge --squash <branch>
git commit -m "<type>: <title> (<bead-id>)" -m "Closes <bead-id>"
```

The subject takes its `<type>` from the bead's own `type` field:

| Bead type | Subject type |
|---|---|
| `feature`, `epic` | `feat` |
| `bug` | `fix` |
| `docs` | `docs` |
| `chore`, `task` | `chore` |

Use `<title>` verbatim from the bead. When the whole subject exceeds 72 characters, shorten the
title and keep the id; the id is the part a tool reads. With no tracker, write the subject from the
branch slug and the diff, and omit the `Closes` line.

A conflict at `git merge --squash` means the base moved between the pull and the merge. Run
`git merge --abort`, and treat it as `base-moved` above.

Any other non-zero exit from the merge or the commit stops the run with `land-failed`. Clear the
staged merge first (`git merge --abort`, or `git reset --hard HEAD` when the merge already staged
without conflicting), so the default branch is left exactly as the fast-forward found it, and say in
the report which of the two you ran.

**Then close the bead and fold the tracker update into the landing.** Skip this whole block when
Step 1 found no tracker; there is nothing to close and nothing to export.

```bash
bd close <id> --reason "shipped: <subject>"
bd export -o .beads/issues.jsonl   # no-op when export.auto is on; harmless either way
git status --porcelain .beads/
```

Stage whatever `.beads/` reports, not `issues.jsonl` alone. A repository may also track
`interactions.jsonl`, and `bd`'s auto-staging covers only the path in `export.path`.

Three states are possible, and all three are normal:

| What you find | What to do |
|---|---|
| `.beads/issues.jsonl` is dirty | `git add .beads/issues.jsonl` then `git commit --amend --no-edit`. One landing commit carries both. Amending is safe: nothing has been pushed. |
| A commit already sits on top of the landing commit | A repository hook committed the export. Leave it. It is the immediate follow-up commit, and the report names it. |
| Nothing changed | The close was already exported. Say so. |

Report the landing commit's hash after any amend. That hash is what the machine line carries.

**Then publish the database, after `git push` succeeds.** Skip when Step 1 found no tracker.

```bash
bd dolt push
```

This is the step a `git push` does not cover and the one most often missed. `bd` keeps its database
out of git: issue history travels under `refs/dolt/data`, so a landed branch with no `bd dolt push`
leaves every close on the machine that made it. The committed export does not substitute for it,
because JSONL import is upsert-only and cannot represent a deletion.

Treat a failure here as a warning, not a stop. The code has already landed and the bead is already
closed; a failed push is recoverable by running it again. Name it in the report and carry on to the
branch delete.

**A note for whoever reads this next.** In a repository running the `close_bead_on_pr_merge.sh` hook,
the `git merge --squash` here does trip the hook, and the hook does nothing: it requires the merged
ref to become an ancestor of HEAD, and a squash-merge never makes it one. There is no duplicate close
to fix.

### Step 5: Push and Clean Up

**Push, and never force:**

```bash
git push origin main
```

With no origin, there is nothing to push; the land is complete at Step 4, and the report says the
repository has no remote.

**On a rejected push,** someone else landed first. Recover by discarding your landing commit and
redoing the land on the new base, never by forcing:

```bash
git branch --show-current                 # must print the default branch; see Step 4 on worktrees
git fetch origin
git log --oneline origin/main..main       # must contain only the commits THIS run created
git reset --hard origin/main
```

That `git log` is the guard, and it is not optional. When local main carries a commit this run did
not create, stop with `main-diverged` and leave everything alone; a reset would destroy someone
else's work. When the check passes, switch back to the feature branch, which is still there because
cleanup comes after the push, and re-run Steps 2 through 5.

**Bound the whole cycle at 3 attempts**, counting every re-run caused by a moved base or a rejected
push. On the third failure, stop with `push-rejected` and say exactly what is on disk.

**Then clean up.** Verify the content landed before deleting anything:

```bash
git diff --name-only <base>..<branch>              # the files the branch touched
git diff <branch> main -- <those files>            # must print nothing
```

An empty second diff means main now holds the branch's version of every file it touched. Then:

```bash
git branch -D <branch>                             # -d refuses: a squash-merge leaves no merge edge
git ls-remote --exit-code origin <branch> && git push origin --delete <branch>
```

`-D` is correct here and only here, because the verification above already proved the content
landed. When that diff prints anything, keep the branch, say which files still differ, and let a
human decide. Concurrent edits to the same file on main are the usual cause, and they are not a
reason to delete evidence.

When the branch has its own worktree, deleting the branch fails while the worktree holds it. Report
the branch and the worktree path as left behind, with the `git worktree remove` command. Removing a
worktree is not this skill's job.

### Step 6: Report

Emit the report below, then the machine line, then stop. On any stop, label the bead first, when
Step 1 resolved one:

```bash
bd update <id> --add-label needs-human
```

Several stops happen before a bead resolves (`dirty-tree`, `on-default-branch`, `bead-unresolved`).
There is nothing to label there, and the report says so rather than reporting a label it never
applied.

## Output Format

On success:

```markdown
## Shipped

**Bead:** tadw-ship-command-4kx - Create the ship skill (resolved from the branch name)
**Branch:** outrigger/4kx/create-ship-command, rebased onto origin/main at `abc1234`
**Gate:** `make check`, source: Makefile check target, exit 0, 412 passed, 0 failed, 31s
**Landed:** `d4e5f6a` `feat: Create the ship skill (tadw-ship-command-4kx)`
**Tracker:** closed tadw-ship-command-4kx, export folded into the landing commit
**Pushed:** origin/main, attempt 1 of 3
**Cleaned up:** deleted the local branch and origin/outrigger/4kx/create-ship-command

SHIP_DONE d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3
```

On a stop:

```markdown
## Not shipped

**Stopped at:** Step 3, the local gate
**Bead:** tadw-ship-command-4kx (labeled `needs-human`)
**Reason:** `make check` exited 1: 3 failed, 409 passed

<the failing output, trimmed to the failing lines>

**State on disk:**

- The branch is rebased onto `origin/main` at `abc1234` and is 1 commit ahead of its old tip
- No merge was attempted, main is untouched, and no rebase is in progress
- The bead is open and labeled `needs-human`

**What a human should do:** fix the 3 failing tests on the branch, then re-run `/tadw:ship`.
The rebase does not need repeating.

SHIP_BLOCKED gate-failed
```

Both forms end with exactly one machine line, and it is the last line of the output. Nothing follows
it: no summary, no offer, no blank prose. A wrapper reads the last line.

## Block Reasons

`SHIP_BLOCKED` carries one of these slugs, verbatim. Do not invent a new one; when nothing fits, use
`internal-error` and describe it in the prose.

| Slug | Means |
|---|---|
| `not-a-repo` | Not a git repository |
| `on-default-branch` | Run from main; there is no feature branch to land |
| `detached-head` | HEAD is detached |
| `dirty-tree` | Uncommitted changes, at Step 1 or before the gate |
| `operation-in-progress` | A rebase, merge, or cherry-pick was already running |
| `bead-unresolved` | A tracker exists and no bead id resolves |
| `bead-ambiguous` | Two or more real beads resolve from the branch name |
| `bead-already-closed` | The bead is already closed |
| `rebase-conflict` | A conflict outside the tracker file, or ten tracker conflicts |
| `tracker-merge-failed` | Tracker tooling could not merge the JSONL, or its result did not verify |
| `gate-not-detected` | No gate command from any source |
| `gate-failed` | The gate ran and exited non-zero |
| `gate-blocked` | The gate could not run: timeout, exit 127, missing runner |
| `base-moved` | The base moved under the run three times |
| `main-diverged` | Local main holds a commit `origin/main` does not, and this run did not create it: the Step 4 fast-forward refused, or the Step 5 guard caught it |
| `push-rejected` | Three pushes rejected |
| `land-failed` | The merge or the commit failed for a reason not covered above |
| `internal-error` | Anything else; the prose explains it |

## Edge Cases

**No origin.** Skip the fetch, rebase onto the local default branch, land, skip the push, and clean
up the local branch only. Say "no remote" in the report rather than reporting a push that never
happened.

**The default branch is checked out in another worktree.** Run Step 4 with `git -C <that-path>`. Do
not remove that worktree, and do not detach its HEAD.

**The gate is slow.** A 900-second default is deliberate: the gate is the entire safety story, and a
timeout that clips a real suite converts a passing repository into `gate-blocked`. Raise
`TADW_SHIP_CHECK_TIMEOUT` rather than narrowing the gate.

**The bead has open blocking dependencies.** `bd close` refuses without `--force`. Do not pass
`--force`. Stop with `internal-error`, naming the blockers; a bead that cannot close is a fact about
the graph, and overriding it here hides that from everyone.

**Two beads on one branch.** `bead-ambiguous`. Splitting the branch is a human's call.

**The branch is already merged.** The rebase produces an empty branch, and `git merge --squash` stages
nothing, so `git commit` fails with nothing to commit. Report it as already landed, close the bead if
it is open, clean up the branch, and emit `SHIP_DONE` with the hash of the commit on main that
carries the work.

## Critical Rules

**Always:**

- Rebase before the gate, so the gate grades the tree that lands
- Name the gate source, the exact command, its exit code, and its real counts
- Stop before the merge on any gate result other than exit 0
- Resolve a tracker conflict by re-exporting from the database, or through the host repo's tracker
  merge tool, then verify the file parses and holds no conflict markers
- Run `bd dolt push` after `git push`, so issue state leaves the machine with the code
- Abort a rebase you cannot finish, and confirm the branch tip is back where it started
- Verify the content landed before deleting a branch
- Confirm you are on the default branch before any command that moves its pointer, and scope the
  main-side commands with `git -C` when another worktree holds it
- Label the bead `needs-human` on every stop, when Step 1 resolved one
- End with exactly one machine line, as the last line

**Never:**

- Merge on a red gate, a skipped gate, or a gate that could not be detected
- Force-push main, or pass `--force`/`--force-with-lease` to any push
- Hand-edit `.beads/issues.jsonl`, or resolve its conflict with `git checkout --ours/--theirs` alone
- Run `git reset --hard`, `git switch`, or `git pull` against the default branch from a worktree
  that has the feature branch checked out
- Leave a rebase in progress without saying so in the first lines of the report
- Reset local main when it carries a commit this run did not create
- Ask the user a question; stop with a report instead
- Resolve a source-code conflict, fix a failing test, or edit the branch's code in any way
- Report a gate as "green" or "passing" without its numbers
- Close a bead the run did not land, or close two
- Set `TADW_PREPUSH=off`, or otherwise disable a check the repository runs on push

## Quality Checklist

Before emitting the report, verify:

- [ ] The bead is named, with how it resolved, or the report says the repository has no tracker
- [ ] The gate's source, command, exit code, and counts all appear
- [ ] The gate ran after the rebase, on a clean tree
- [ ] No merge happened unless the gate exited 0
- [ ] No rebase is in progress, or the report's first lines say one is and how to clear it
- [ ] The landing commit's subject carries the bead id, and its body carries `Closes <id>`
- [ ] The bead is closed and the export is committed, or the report says why neither happened
- [ ] main was pushed, or the report says there is no origin
- [ ] The branch was deleted only after the content-landed check passed
- [ ] On a stop, the report names the step, the state on disk, and the human's next action
- [ ] The last line is exactly one `SHIP_DONE <hash>` or `SHIP_BLOCKED <reason>`, with a slug from
      the table above
