---
name: ship
description: "Land a reviewed bead's feature branch on main locally: rebase onto the base, run the repository's own check suite as the gate, squash-merge, close the bead, push main, and delete the branch. No PR and no GitHub CI; the local gate is the only thing that decides. Runs unattended, fails closed on a red or undetected gate, never force-pushes main, never hand-edits the tracker JSONL, and ends with one machine-readable SHIP_DONE / SHIP_BLOCKED line."
---

# Ship

Lands an accepted bead's feature branch on main and closes the bead. There is no pull request and no
GitHub CI. **The repository's own check suite, run on the exact tree that lands, is the whole gate.**

Use it when a bead passed `/quality-gates` and `/verify-acceptance`, or when an orchestrator needs an
unattended ship step. Do not use it when the repository merges through pull requests (use
`/pr-maintain`), when the work is not graded yet, when you want a readiness report instead of an
action, or when the branch carries two beads.

Four rules govern every step:

1. **Rebase, then gate, then merge.** A gate that fails, times out, or cannot be detected stops the
   run. "No check command found" is not evidence that the code is good.
2. **Every stop names the state on disk and the next human action.** Never leave a rebase in
   progress, and never force-push main.
3. **Tracker tooling merges `.beads/issues.jsonl`.** A hand edit writes a state the database does not
   hold, and the next export reverts it.
4. **Report, never ask.** A question inside an orchestrator hangs the loop.

## Invocation

```text
/tadw:ship                 # derive the bead from the current branch name
/tadw:ship <bead-id>       # ship the branch for this bead
```

`TADW_SHIP_CHECK` sets the exact gate command and outranks every other gate source.
`TADW_SHIP_CHECK_TIMEOUT` sets the gate timeout in seconds, default 900. No variable skips the gate,
and do not add one. Do not set `TADW_PREPUSH=off` either.

## Required workflow

Track the six steps with TodoWrite. On a stop, go straight to Step 6 and report.

### Step 1: Resolve the ground and the bead

```bash
git rev-parse --show-toplevel                       # a repository at all
git branch --show-current                           # the feature branch
git status --porcelain                              # must print nothing
git remote get-url origin                           # origin, or no origin
git worktree list --porcelain                       # who has the default branch checked out
```

Resolve the **default branch** in this order: `git symbolic-ref refs/remotes/origin/HEAD` (strip the
`origin/` prefix), then a local `main`, then a local `master`. Never hardcode `main` in a command you
run; this file writes `main` for readability only.

Five conditions stop the run with `git-state`. Check them in this order, and name the one you found:
no repository at all, HEAD already on the default branch, detached HEAD, a dirty tree, or a rebase,
merge, or cherry-pick already in progress.

Test that last one by asking whether the path exists. `git rev-parse --git-path` exits 0 either way,
so its exit code reports an in-progress rebase in every clean repository:

```bash
for p in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD; do
  [ -e "$(git rev-parse --git-path "$p")" ] && echo "in progress: $p"
done
```

**Then resolve the bead.** With an argument, use it. Without one, take the second segment of an
`outrigger/<short-id>/<slug>` branch name, or scan any other branch name for id-shaped tokens. Verify
every candidate with `bd show <candidate> --json`, longest first, and never trust the shape alone.

| Outcome | What to do |
|---|---|
| Exactly one resolves | That is the bead. Say which, and how you found it. |
| Two or more resolve | Stop with `tracker`. Closing the wrong bead is silent and hard to undo. |
| An explicit `<bead-id>` argument does not resolve | Stop with `tracker`. The caller named a bead this tracker does not hold, and a typo is the likely cause. |
| `status` is already `closed` | Stop with `tracker`. Something landed this work already. |
| The branch name yields no candidate, or there is no tracker | **Ship bead-free.** Not every unit of work has a bead, and a missing one is no reason to strand a reviewed commit. |

**A bead-free ship changes four things and nothing else:** no `bd close`, no `bd dolt push`, no bead id
in the commit subject, and no `Closes` line in its body. Every gate, guard, and cleanup step still
runs. Say "bead-free" in the report header and again in the summary, and name which of the two causes
applied.

**In a linked worktree, confirm the database.** `bd` finds one database per repository through the git
common directory, so a worktree shares the main checkout's. If `bd where` names a database under the
worktree, stop with `tracker`; closing a bead in a throwaway database leaves the real one open.
`bd worktree info` says whether this is a linked worktree at all.

### Step 2: Bring the branch current

```bash
BRANCH_TIP="$(git rev-parse HEAD)"
git fetch origin                                   # skip when there is no origin
comm -12 <(git diff --name-only origin/main...HEAD | sort) \
         <(git diff --name-only HEAD origin/main | sort)
```

That intersects the files this branch touched with the files that still differ from main.
**Printing nothing means the work already landed.** Close the bead if there is one, clean up per
Step 5, and emit `SHIP_DONE` with the hash on main that carries the work. Run no gate and attempt no
merge.

**Do not rewrite this as a shell variable holding the file list.** A newline-separated list expands to
one pathspec wherever `IFS` excludes newline, that pathspec matches no file, and `git diff` then prints
nothing and exits 0. The check reads that as "already landed" and the run deletes a branch it never
merged. Measured on 2026-08-24: `set -- $FILES` reported `args=1` for a four-file branch, and the
documented diff printed 0 lines where listing the four paths printed 918.

**Run this check BEFORE the rebase.** A squash-merge gives the landed commit a new patch id, so the
rebase conflicts on every touched file instead of going empty. Rebase first and a shipped bead reports
`SHIP_BLOCKED conflict`, which is the opposite of the truth.

Then rebase with `git rebase origin/main`, or onto the local default branch when there is no origin.
Record the base SHA; Step 4 checks that it has not moved. **On a conflict, read the conflicted set
first** with `git diff --name-only --diff-filter=U`.

**Two paths resolve mechanically, and every other path does not.** Resolve `.beads/issues.jsonl` and
`CHANGELOG.md` by the rules below, in whatever combination the conflicted set holds. Abort as soon as
the set holds one path outside those two.

**`.beads/issues.jsonl`:** the database is the source of truth and the file is only its export, so take
either side and regenerate it.

```bash
git checkout --ours .beads/issues.jsonl   # either side; the next line overwrites it
bd export -o .beads/issues.jsonl
grep -n '^<<<<<<<\|^>>>>>>>' .beads/issues.jsonl || echo "no conflict markers"
python3 -c 'import json; [json.loads(l) for l in open(".beads/issues.jsonl") if l.strip()]'
git add .beads/issues.jsonl
```

Printing nothing is the pass on that `grep` line. Do not rewrite it as `grep -c`, which exits 1 when
it counts zero, so the cleanest possible result would stop the run. If either verification fails, stop
with `tracker` rather than editing the file by hand. Rule 3 has no exception.

**`CHANGELOG.md`: keep both entries.** An append-only section conflicts whenever main gains an entry
first, and both entries are correct, so nothing here needs judgment. Delete the `<<<<<<<`, `=======`,
and `>>>>>>>` lines, keep every entry from both sides, and put main's entries first so two runs produce
the same file.

```bash
grep -n '^<<<<<<<\|^=======\|^>>>>>>>' CHANGELOG.md || echo "no conflict markers"
git add CHANGELOG.md
```

Both sides must survive. Confirm that one distinctive line from each side is still in the file, and
stop with `conflict` if either is missing. A repository can prevent this conflict outright with
`CHANGELOG.md merge=union` in `.gitattributes`, which keeps both sides and never raises the conflict.
Prefer that where you own the repository; this resolution covers the branches that predate it.

Continue the rebase once the conflicted set is empty:

```bash
GIT_EDITOR=true git rebase --continue
```

A rebase conflicts once per replayed commit, so repeat the whole block, capped at 10 resolutions.

**If the conflicted set holds any other path,** abort at once and stop with `conflict`, naming every
conflicted path. Never resolve a source conflict here; the person who wrote the branch does that. If
the abort itself fails, say so in the first lines of the report and give the exact
`git rebase --abort` command. That is the one case where this skill leaves an operation in progress.

```bash
git rebase --abort
git rev-parse HEAD          # must equal BRANCH_TIP
```

### Step 3: Run the local gate

Detect the gate command in this order, stop at the first source that yields one, and record the
source; the report names it.

1. **`TADW_SHIP_CHECK`**, run verbatim through the shell.
2. **What `AGENTS.md` or `CLAUDE.md` declares**: a "Commands for This Repo" section, a check list, or
   a named check script. Every command in a declared list must exit 0.
3. **A `check` target in a task runner**: `make check`, `just check`, a `check` task in
   `Taskfile.yml`, or a `check` script in `package.json`.
4. **The stack's conventional test command**, detected by config file and never by binary:
   `pytest -q`, `bundle exec rspec` or `bin/rails test`, `npm test`, `go test ./...`, `swift test`,
   `cargo test`.

**If no source yields a command, stop with `gate`**, and tell the operator to set `TADW_SHIP_CHECK`
and re-run.

Then run it on the rebased tip. Check `git status --porcelain` once more first: anything there means
the rebase or the tracker merge left something behind, so stop with `git-state`. Bound the run with
`TADW_SHIP_CHECK_TIMEOUT`, and capture the command, the exit code, and the real counts.

Exit 0 continues to Step 4. Any other outcome stops the run with `gate`: name whether it failed,
timed out, exited 127, or could not find its runner, and print failing output trimmed to the failing
lines.

The branch stays rebased after a gate stop, and the report says so, because the fix then goes on top
of a current branch. Never report the gate as "green", "clean", or "passing". Report the command, the
exit code, and the numbers it printed.

### Step 4: Land

**Get onto the default branch**, in whichever of these three states the repository is in. Then run
**every command that acts on the default branch, here and in Step 5, with `git -C <that-path>`**. Step
5's `git reset --hard origin/main` resets the feature branch when it runs from the feature branch's
worktree, and that branch holds the one copy of unlanded work.

| State | What to do |
|---|---|
| This worktree can switch, and no other holds the default branch | `git switch` to it here. `<that-path>` is this worktree. |
| Another worktree holds the default branch | Use that path. Do not remove that worktree, and do not detach it. |
| No worktree holds it, and this one must not move | Add a temporary worktree for it, land there, and remove it in Step 5 before you touch the feature branch's worktree. |

The third state is the one to watch for: a main checkout parked on an unrelated branch, with
uncommitted files. Switching it would disturb work this run never looked at.

```bash
git -C <path> branch --show-current    # must print the default branch
git switch main
git pull --ff-only origin main         # skip when there is no origin
```

A failed `git pull --ff-only` means local main holds commits `origin/main` does not. Stop with
`git-state` and change nothing.

**Check that the base has not moved** since Step 2. If `origin/main` is now ahead of the SHA you
rebased onto, the gate result no longer describes what lands. Switch back to the feature branch, then
re-run Steps 2 and 3 against the new base; re-running them from the default branch would rebase main
onto itself. If the base moves a second time, stop with `git-state`.

```bash
git merge --squash <branch>
git commit -m "<type>: <title> (<bead-id>)" -m "Closes <bead-id>"
```

The `<type>` comes from the bead's `type` field: `feat` for `feature` and `epic`, `fix` for `bug`,
`docs` for `docs`, `chore` for `chore` and `task`. Use `<title>` verbatim from the bead; if the
subject exceeds 72 characters, shorten the title and keep the id. On a bead-free ship, write the
subject from the branch slug and the diff, and omit the `Closes` line.

A conflict at `git merge --squash` means the base moved between the pull and the merge. Run
`git merge --abort` and treat it as a moved base. Any other non-zero exit stops the run with
`git-state`: clear the staged merge first with `git merge --abort`, or with `git reset --hard HEAD`
when the merge staged without conflicting, and say which you ran.

**Then close the bead and fold the export into the landing commit.** Skip this block on a bead-free
ship:

```bash
bd close <id> --reason "shipped: <subject>"
bd export -o .beads/issues.jsonl   # no-op when export.auto is on; harmless either way
git status --porcelain .beads/
```

Stage whatever `.beads/` reports, not `issues.jsonl` alone, because a repository may also track
`interactions.jsonl` and `bd` auto-stages only `export.path`.

| What you find | What to do |
|---|---|
| `.beads/issues.jsonl` is dirty | `git add .beads/issues.jsonl`, then `git commit --amend --no-edit`. Amending is safe, because nothing is pushed yet. |
| A commit sits on top of the landing commit | A repository hook committed the export. Leave it, and name it in the report. |
| Nothing changed | The close was already exported. Say so. |

Report the landing commit's hash after any amend; the machine line carries that hash.

### Step 5: Push and clean up

Run `git push origin main`. With no origin, the land is complete at Step 4; say "no remote" rather
than reporting a push that never happened.

**On a rejected push,** someone else landed first. Discard your landing commit and redo the land on
the new base, and never force:

```bash
git branch --show-current                 # must print the default branch; see Step 4 on worktrees
git fetch origin
git log --oneline origin/main..main       # must contain only the commits THIS run created
git reset --hard origin/main
```

That `git log` guard is not optional. If local main carries a commit this run did not create, stop
with `git-state` and change nothing, because a reset would destroy someone else's work. When the check
passes, switch back to the feature branch and re-run Steps 2 through 5 once. If the second push is
rejected too, stop with `git-state` and say what is on disk.

**Then run `bd dolt push`**, unless the ship is bead-free. `git push` does not cover it: issue history
travels under `refs/dolt/data`, and the committed export is no substitute, because JSONL import is
upsert-only and cannot express a deletion. A failure here is a warning, not a stop. Name it in the
report and carry on, because running it again recovers.

**Then clean up.** Verify the content landed before you delete anything:

```bash
comm -12 <(git diff --name-only <base>..<branch> | sort) \
         <(git diff --name-only <branch> main | sort)   # must print nothing
git branch -D <branch>                             # -d refuses: a squash-merge leaves no merge edge
git ls-remote --exit-code origin <branch> && git push origin --delete <branch>
```

Empty output means main holds the branch's version of every file it touched, and that check is what
makes `-D` correct here. If it prints anything, keep the branch, say which files differ, and let a
human decide. Build the pathspec no other way; Step 2 explains what a variable holding the list does
here.

**When a worktree holds the branch, remove the worktree first**, because `git branch -D` refuses while
one does:

```bash
git worktree list --porcelain                       # find the worktree holding <branch>
cd <main-checkout>                                  # LEAVE the worktree before removing it
git -C <main-checkout> worktree remove <worktree-path>
git -C <main-checkout> branch -D <branch>
```

- **Leave the worktree before removing it.** This skill often runs inside the worktree it deletes.
  Remove the directory you stand in, and every later command fails, including the ones that report
  what happened. Say in the report that the caller's shell moved.
- **Never remove the worktree holding the default branch.** Match on the branch you are shipping,
  never on position in `git worktree list --porcelain`.
- **A dirty worktree stops the removal, and that is correct.** Report it as left behind, with the path
  and the reason, and still count the run as shipped: the code landed, and only cleanup is
  outstanding.

### Step 6: Report

On a stop, run `bd update <id> --add-label needs-human` first, when Step 1 resolved a bead. Some stops
happen before that; the report then says nothing was labeled. Emit the report, then the machine line,
then stop.

## Output format

```markdown
## Shipped

**Bead:** tadw-ship-command-4kx - Create the ship skill (resolved from the branch name)
**Branch:** outrigger/4kx/create-ship-command, rebased onto origin/main at `abc1234`
**Gate:** `make check`, source: Makefile check target, exit 0, 412 passed, 0 failed, 31s
**Landed:** `d4e5f6a` `feat: Create the ship skill (tadw-ship-command-4kx)`
**Tracker:** closed tadw-ship-command-4kx, export folded into the landing commit, `bd dolt push` ok
**Pushed:** origin/main
**Cleaned up:** removed the worktree at .outrigger/worktrees/4kx-create-ship-command, deleted the
local branch and origin/outrigger/4kx/create-ship-command. Your shell moved to /Users/you/Dev/project

SHIP_DONE d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3
```

```markdown
## Not shipped

**Stopped at:** Step 3, the local gate
**Bead:** tadw-ship-command-4kx (labeled `needs-human`)
**Reason:** `make check` exited 1: 3 failed, 409 passed

<the failing output, trimmed to the failing lines>

**State on disk:** the branch is rebased onto `origin/main` at `abc1234`, no merge was attempted,
main is untouched, no rebase is in progress, and the bead is open.

**What a human should do:** fix the 3 failing tests on the branch, then re-run `/tadw:ship`.
The rebase does not need repeating.

SHIP_BLOCKED gate
```

Every report names the gate source, command, exit code, and counts. Every stop names the step, the
exact condition it found, the state on disk, and the human's next action. The slug is a category, so
the prose carries what actually happened.

Both forms end with exactly one machine line, as the last line of the output: no summary, no offer, no
prose after it. A wrapper reads the last line, and `SHIP_DONE` carries the landing commit's hash,
which is what an orchestrator checks against main.

| Slug | Means |
|---|---|
| `gate` | The gate failed, timed out, could not run, or could not be detected |
| `conflict` | A source conflict on rebase or merge; this skill does not judge code |
| `tracker` | A named bead does not exist, two beads resolve from the branch, or the bead is already closed; or its database could not be placed, or its export could not be regenerated. A branch that names no bead at all ships bead-free instead. |
| `git-state` | The repository was not fit to ship from, or main moved under the run: a dirty tree, a rebase already running, a diverged or twice-moved main, a twice-rejected push, or a failed merge |
| `internal` | Anything else; the prose explains it |

## Never

- Merge on a red gate, a skipped gate, or a gate you could not detect. Raise
  `TADW_SHIP_CHECK_TIMEOUT` rather than narrowing a slow gate.
- Force-push main, or pass `--force` or `--force-with-lease` to any push
- Hand-edit `.beads/issues.jsonl`, or resolve its conflict with `git checkout --ours/--theirs` alone
- Run `git reset --hard`, `git switch`, or `git pull` against the default branch from a worktree that
  holds the feature branch
- Reset local main when it carries a commit this run did not create
- Remove the worktree holding the default branch, or force-remove a dirty one
- Read a rebase conflict as real before checking whether the work already landed
- Resolve a source conflict, fix a failing test, or edit the branch's code
- Close a bead this run did not land, close two, or pass `--force` to `bd close`. A bead with open
  blocking dependencies stops the run with `internal`, naming the blockers.
- Ask the user a question; stop with a report instead
