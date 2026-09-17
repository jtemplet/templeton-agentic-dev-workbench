---
name: ship
description: "Land a reviewed bead's feature branch on main locally: rebase onto the base, run the repository's own check suite as the gate, squash-merge, close the bead, push main, delete the branch, and name which bead to pick up next. No PR and no GitHub CI; the local gate is the only thing that decides. Runs unattended, fails closed on a red or undetected gate, never force-pushes main, never hand-edits the tracker JSONL, and ends with one machine-readable SHIP_DONE / SHIP_BLOCKED line."
---

# Ship

Lands an accepted bead's feature branch on main and closes the bead. There is no pull request and no
GitHub CI. **The repository's own check suite, run on the exact tree that lands, is the whole gate.**

Use it when a bead passed `/quality-gates` and `/verify-acceptance`, or when an orchestrator needs an
unattended ship step. Do not use it when the repository merges through pull requests, when the
work is not graded yet, when you want a readiness report instead of an action, or when the branch
carries two beads.

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

Work the six steps in order. On a stop, go straight to Step 6 and report.

<!-- plugin-root-fallback -->
**Steps 1, 2, and 5 call a plugin script.** Each command below finds it when `CLAUDE_PLUGIN_ROOT`
is unset; the `find` fallback searches the installed plugin cache, and Claude Code uses the loaded
plugin root first. All four scripts share one exit-code contract: **0 is the clean answer, 1 is a
condition the report must name, and 2 is operator error, which stops the run with `internal`.** Each
one holds a mechanism this file used to spend a paragraph guarding, so run it rather than rebuilding
what it does.

### Step 1: Resolve the ground and the bead

```bash
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/ship/scripts/resolve_ground.py' -print -quit 2>/dev/null)"
```

One JSON object carries every fact this step needs, and its keys are named below as each is used.
**Exit 1 means `stop` names a condition, and the run stops with `git-state`.** Name that condition
and quote the field that shows it.

| `stop` | What it found |
|---|---|
| `no-repository` | There is no git repository here |
| `no-default-branch` | No `origin/HEAD`, no `main`, no `master`, so there is nothing to ship onto |
| `operation-in-progress` | `in_progress` names the rebase, merge, or cherry-pick already running |
| `on-default-branch` | HEAD is already on the default branch |
| `detached-head` | HEAD is detached |
| `dirty-tracked` | `dirty_tracked` lists the changed tracked files |

**Never hardcode `main` in a command you run.** Use `default_branch`; this file writes `main` for
readability only. **Name any `untracked` path in the report and carry on**, because a gate that
writes build output is normal and only a changed tracked file blocks a rebase.

**Then resolve the bead.** With an argument, use it. Without one, verify each token in
`bead_candidates` with `bd show <candidate> --json`, in the order the script printed them, and take
the first that resolves. The script proposes; `bd` decides. Never trust the shape alone.

| Outcome | What to do |
|---|---|
| Exactly one resolves | That is the bead. Say which, and how you found it. |
| Two or more resolve | Stop with `tracker`. Closing the wrong bead is silent and hard to undo. |
| An explicit `<bead-id>` argument does not resolve | Stop with `tracker`. The caller named a bead this tracker does not hold, and a typo is the likely cause. |
| `status` is already `closed` | Stop with `tracker`. Something landed this work already. |
| No candidate resolves, or there is no tracker | **Ship bead-free.** Not every unit of work has a bead, and a missing one is no reason to strand a reviewed commit. |

**A bead-free ship changes four things and nothing else:** no `bd close`, no `bd dolt push`, no bead
id in the commit subject, and no `Closes` line in its body. Every gate, guard, and cleanup step
still runs. Say "bead-free" in the report header and again in the summary, and name which of the two
causes applied.

**In a linked worktree, confirm the database.** `is_linked_worktree` says whether this is one. `bd`
finds one database per repository through `git_common_dir`, so a worktree shares the main checkout's.
If `bd where` names a database under `repo_root` instead, stop with `tracker`; closing a bead in a
throwaway database leaves the real one open.

### Step 2: Bring the branch current

```bash
BRANCH_TIP="$(git rev-parse HEAD)"
git fetch origin                                   # skip when there is no origin
```

**Then ask whether the work already landed, and ask it before the rebase.**

```bash
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/ship/scripts/landed_check.py' -print -quit 2>/dev/null)" \
  --base origin/main --branch HEAD --target origin/main
```

**Exit 0, printing nothing, means the work already landed.** Close the bead if there is one, clean
up per Step 5, and emit `SHIP_DONE` with the hash on main that carries the work. Run no gate and
attempt no merge. Exit 1 lists what is still outstanding, which is the ordinary case.

**The order matters.** A squash-merge gives the landed commit a new patch id, so the rebase
conflicts on every touched file instead of going empty. Rebase first and a shipped bead reports
`SHIP_BLOCKED conflict`, which is the opposite of the truth.

Then rebase with `git rebase origin/main`, or onto the local default branch when there is no origin.
Record the base SHA; Step 4 checks that it has not moved.

**On a conflict, run the resolver rather than reading the conflicted set yourself:**

```bash
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/ship/scripts/resolve_rebase_conflict.py' -print -quit 2>/dev/null)"
```

Two paths resolve mechanically and every other path does not. The resolver regenerates
`.beads/issues.jsonl` from the database, which is its source of truth, keeps both sides of a
`CHANGELOG.md` conflict with the default branch's entries first, verifies each result, and stages
what it resolved.

**It checks the whole conflicted set before it touches one file**, so a single path outside those
two leaves every file exactly as the rebase left it, and `stop` is `conflict`. A verification
failure is different: it comes after the check, so either stop can follow a path that already
resolved. Read `resolved` for what it staged, and never assume a stop means nothing was written.
`stop` is `tracker` when the export could not be regenerated or did not verify, and `conflict` when
the changelog could not be merged.

Continue the rebase once the resolver exits 0:

```bash
GIT_EDITOR=true git rebase --continue
```

A rebase conflicts once per replayed commit, so repeat both commands, capped at 10 resolutions.

**On either stop, abort at once** and report the slug with every path in `detail`. Never resolve a
source conflict here; the person who wrote the branch does that. Rule 3 has no exception either:
when the resolver refuses `.beads/issues.jsonl`, do not edit it by hand.

```bash
git rebase --abort
git rev-parse HEAD          # must equal BRANCH_TIP
```

If the abort itself fails, say so in the first lines of the report and give the exact
`git rebase --abort` command. That is the one case where this skill leaves an operation in progress.

A repository can prevent the `CHANGELOG.md` conflict outright with `CHANGELOG.md merge=union` in
`.gitattributes`, which keeps both sides and never raises the conflict. Prefer that where you own
the repository; the resolver covers the branches that predate it.

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

**Get onto the default branch.** Then run **every command that acts on it, here and in Step 5, with
`git -C <that-path>`**, because Step 5's `git reset --hard origin/main` resets the feature branch when
it runs from that branch's worktree, and the feature branch holds the one copy of unlanded work.
Step 1's `default_branch_worktree` names the path, or is `null` when no worktree holds it.

| State | What to do |
|---|---|
| `default_branch_worktree` is `null`, and this worktree can switch | `git switch` to it here. `<that-path>` is this worktree. |
| `default_branch_worktree` names another path | Use that path. Do not remove that worktree, and do not detach it. |
| It is `null`, and this worktree must not move | Add a temporary worktree for it, land there, and remove it in Step 5 before you touch the feature branch's worktree. |

The third row covers a main checkout parked on an unrelated branch with uncommitted files.
Switching it would disturb work this run never looked at.

```bash
git -C <path> branch --show-current    # must print the default branch
git switch main
git pull --ff-only origin main         # skip when there is no origin
git log --oneline origin/main..main    # skip when there is no origin
```

**A successful `git pull --ff-only` is no evidence that the default branch holds nothing unpushed.**
It fails only on a real divergence, where each side holds a commit the other lacks; a main that is
merely ahead prints "Already up to date." and exits 0. On a real divergence, stop with `git-state`
and change nothing.

**Then list what the default branch already carries.** This run has created no commit yet, so every
commit `git log --oneline origin/main..main` prints was already there, and Step 5's push publishes
it. Record each hash and subject for the report, and **do not stop for them**: they are the
operator's own finished commits on their own default branch, and any push of that branch was always
going to publish them. When the range prints nothing, write no line and no "none" placeholder.

**With no origin, run neither command.** `origin/main` does not resolve there, so `git log` exits 128
with `fatal: ambiguous argument`, which an unattended run reads as a stop. Step 5 pushes nothing in
that state, so the report line is omitted.

**Check that the base has not moved** since Step 2. If `origin/main` is now ahead of the SHA you
rebased onto, the gate result no longer describes what lands. Switch back to the feature branch, then
re-run Steps 2 and 3 against the new base; re-running them from the default branch would rebase main
onto itself. If the base moves a second time, stop with `git-state`.

```bash
git merge --squash <branch>          # stages the whole diff; writes no commit
git status --porcelain               # staged entries, and no `U` path
```

**`git merge --squash` stages the diff and leaves HEAD alone**, printing
`Squash commit -- not updating HEAD`. The landing commit comes at the end of this step, once the
tracker export has joined the same staged tree, so it is written once and its hash never moves.

**Clear a squash merge with `git reset --hard HEAD`, never `git merge --abort`.** A squash records no
`MERGE_HEAD`, so the abort exits 128 with `fatal: There is no merge to abort (MERGE_HEAD missing)`,
after a clean squash and a conflicted one alike.

A conflict at `git merge --squash` means the base moved between the pull and the merge. Reset, and
treat it as a moved base. Any other non-zero exit stops the run with `git-state`: reset, and say that
you ran it.

**Then close the bead and stage its export into that same tree.** Skip this block on a bead-free
ship, and go straight to the commit:

```bash
bd close <id> --reason "shipped: <subject>" --suggest-next
bd export -o .beads/issues.jsonl   # no-op when export.auto is on; harmless either way
git status --porcelain .beads/
git add .beads/                    # stage whatever that reported, not issues.jsonl alone
```

**`--suggest-next` prints the beads this close released from their blocker**, under a
`Newly unblocked:` heading it prints only when the close released at least one. Each line carries the
id, the title, and the priority. Keep that list; Step 6 puts it in the report.

Stage the whole of `.beads/`, because a repository may also track `interactions.jsonl` and `bd`
auto-stages only `export.path`. **An empty `git status --porcelain .beads/` is a normal outcome, not
a failed export:** `bd export` is deterministic, so an empty result means the close was already
exported. Say so, and carry on.

**If `bd close` fails, stop with `tracker`.** Clear the staged merge with `git reset --hard HEAD`
first, so the bead stays open and the tree agrees with it. Nothing landed, and the report says so.

**Then write the landing commit, once:**

```bash
git commit -m "<type>: <title> (<bead-id>)" -m "Closes <bead-id>"
git rev-parse HEAD                   # the hash the machine line carries
git status --porcelain               # must print nothing
```

The `<type>` comes from the bead's `type` field: `feat` for `feature` and `epic`, `fix` for `bug`,
`docs` for `docs`, `chore` for `chore` and `task`. Use `<title>` verbatim from the bead; if the
subject exceeds 72 characters, shorten the title and keep the id. On a bead-free ship, write the
subject from the branch slug and the diff, and omit the `Closes` line.

**Do not amend this commit.** The export is already inside it, so an amend would only move a hash
that Step 6 has to report.

**If the commit itself fails, stop with `git-state`.** The bead is then closed and nothing landed,
which is the one state this step can leave that the disk does not show. Say it in the first lines
of the report, and give the human `bd reopen <id>` as the action.

| What you find after the commit | What to do |
|---|---|
| `git status --porcelain` prints nothing | The land is complete. Report the hash `git rev-parse HEAD` printed. |
| A commit sits on top of the landing commit | A repository hook committed something. Leave it, and name it in the report. |
| Anything is still staged or modified | A hook rewrote the tree. Stop with `git-state`, and name the paths. |

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

**That `git log` guard is not optional.** If local main carries a commit this run did not create,
stop with `git-state` and change nothing, because a reset would destroy someone else's work. The
commits Step 4 recorded are such commits, so they stop this reset too. When the check passes, switch
back to the feature branch and re-run Steps 2 through 5 once. If the second push is rejected too,
stop with `git-state` and say what is on disk.

**Then run `bd dolt push`**, unless the ship is bead-free. `git push` does not cover it: issue history
travels under `refs/dolt/data`, and the committed export is no substitute, because JSONL import is
upsert-only and cannot express a deletion. A failure here is a warning, not a stop, because running
it again recovers. Name it in the report and carry on.

**Then record what follows the shipped bead, before cleanup**, because removing a worktree can move
the shell out of the repository and `bd` finds its database through the git common directory.

```bash
bd ready -n 1 --json
```

Read the array it prints, never its exit code, which is 0 whether the array holds a bead or is empty.
Keep that output verbatim: Step 6 pastes it into the form the Output format table below specifies,
and derives nothing of its own. **This lookup never stops the run**, because it reads the tracker
after the push, when the ship is already complete.

**Then clean up.** Verify the content landed before you delete anything, with the same script
Step 2 ran and the base this run rebased onto:

```bash
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/ship/scripts/landed_check.py' -print -quit 2>/dev/null)" \
  --base <base> --branch <branch> --target main
git branch -D <branch>                             # -d refuses: a squash-merge leaves no merge edge
git ls-remote --exit-code origin <branch> && git push origin --delete <branch>
```

**Exit 0 is what makes `-D` correct here:** main holds the branch's version of every file the branch
authored. Exit 1 lists the files that still differ, so keep the branch, say which files, and let a
human decide. The check ignores `.beads/`, because Step 4's own commit rewrites the export on every
ship that has a bead, and without that exclusion this check fires on every such ship.

**When a worktree holds the branch, remove the worktree first**, because `git branch -D` refuses while
one does. `worktrees` from Step 1 says which path holds it:

```bash
python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" "$HOME/.claude-personal" \
  -path '*/skills/ship/scripts/check_worktree_occupants.py' -print -quit 2>/dev/null)" \
  --worktree <worktree-path>                        # who is still standing in it
cd <main-checkout>                                  # LEAVE the worktree before removing it
git -C <main-checkout> worktree remove <worktree-path>
git -C <main-checkout> branch -D <branch>
```

- **Leave the worktree before removing it.** This skill often runs inside the worktree it deletes.
  Remove the directory you stand in, and every later command fails, including the ones that report
  what happened. Say in the report that the caller's shell moved.
- **Say what a session left there loses, before removing it.** The removal does not stop a session
  standing in the worktree. That session keeps running against a path that no longer exists, and it
  goes quiet rather than failing, so nobody tells its owner. End it, or restart it somewhere that
  still exists.
- **Report the occupants, then remove anyway.** `check_worktree_occupants.py` exits 0 when nobody
  stands there; exit 1 lists each pid and its command, and that list goes in the report. Exit 2 means
  it could not measure, which is not the same as nobody being there, so say that instead of claiming
  the worktree was clear. **It kills nothing and removes nothing**, and neither do you: a live pid is
  a warning, never a refusal, because the session it would refuse for is usually this run's caller.
- **Never remove the worktree holding the default branch.** Match on the branch you are shipping,
  never on position in `git worktree list --porcelain`.
- **A dirty worktree stops the removal, and that is correct.** Report it as left behind, with the path
  and the reason, and still count the run as shipped: the code landed, and only cleanup is
  outstanding.

### Step 6: Report

On a stop, run `bd update <id> --add-label needs-human` first, when Step 1 resolved a bead. Some stops
happen before that; the report then says nothing was labeled.

**The Next row comes from Step 5, and from nowhere else.** Paste what those commands printed. Do not
re-run them here, and never write the row from memory. A run that names a bead it did not read has
invented one, and the reader cannot tell the difference.

`bd ready` orders by priority, which is not a ranking by value. The row names a starting point, and
`/triage-beads` is what ranks the backlog.

**A stop carries no Next row.** Nothing shipped, so nothing follows; the bead this run just attempted
is still the next thing to work on.

Emit the report, then the machine line, then stop.

## Output format

```markdown
## Shipped

**Bead:** tadw-ship-command-4kx - Create the ship skill (resolved from the branch name)
**Branch:** outrigger/4kx/create-ship-command, rebased onto origin/main at `abc1234`
**Gate:** `make check`, source: Makefile check target, exit 0, 412 passed, 0 failed, 31s
**Landed:** `d4e5f6a` `feat: Create the ship skill (tadw-ship-command-4kx)`
**Tracker:** closed tadw-ship-command-4kx, export folded into the landing commit, `bd dolt push` ok
**Pushed:** origin/main
**Also published:** 2 commits that were already on main and unpushed: `a1b2c3d` `fix: clamp the
retry budget`, `b2c3d4e` `docs: correct the hook count`. The push carried them. (Omit this line when
the default branch was equal to its remote, and when there is no origin.)
**Cleaned up:** removed the worktree at .outrigger/worktrees/4kx-create-ship-command, deleted the
local branch and origin/outrigger/4kx/create-ship-command. Your shell moved to /Users/you/Dev/project
**Still standing there:** pid 27169 (claude). That session labels no bead now; end it. (Omit this
line when the occupant check found nobody.)
**Next:** closing this bead unblocked 2: `tadw-ship-report-7bq` Report the gate source (P1),
`tadw-ship-timeout-2mn` Bound the gate with a timeout (P3). Claim one with
`bd update <id> --claim`.

SHIP_DONE d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3
```

The **Next:** row is always the last line before the machine line, and Step 5 measured every form of
it. This table is the only place its wording is specified:

| What Step 5 found | The row opens with |
|---|---|
| The close released beads | `closing this bead unblocked 2:` then every id, title, and priority |
| The top of `bd ready` | `nothing was unblocked; the top of bd ready is` then that id, title, and priority |
| An empty array | `nothing was unblocked, and bd ready is empty` |
| The lookup failed | `lookup failed: bd ready -n 1 --json exited 1` |

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

Both forms end with exactly one machine line, as the last line of the output: no summary, no offer,
no prose after it. A wrapper reads the last line, and `SHIP_DONE` carries the landing commit's hash,
which is what an orchestrator checks against main.

| Slug | Means |
|---|---|
| `gate` | The gate failed, timed out, could not run, or could not be detected |
| `conflict` | A source conflict on rebase or merge; this skill does not judge code |
| `tracker` | A named bead does not exist, two beads resolve from the branch, or the bead is already closed; or its database could not be placed, or its export could not be regenerated. A branch that names no bead at all ships bead-free instead. |
| `git-state` | The repository was not fit to ship from, or main moved under the run: any `stop` Step 1's script named, a diverged or twice-moved main, a twice-rejected push, or a failed merge |
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
- Kill a process standing in a worktree, or refuse the removal because one is. Report the pid
  and remove anyway; whose session it is, is not this skill's call.
- Read a rebase conflict as real before checking whether the work already landed
- Resolve a source conflict, fix a failing test, or edit the branch's code
- Close a bead this run did not land, close two, or pass `--force` to `bd close`. A bead with open
  blocking dependencies stops the run with `internal`, naming the blockers.
- Stop the run because the next-bead lookup failed, or claim the bead it names. The lookup is a read
  that runs after the push, and choosing what to work on next is the operator's call.
- Write the Next row from anything but what the Step 5 commands printed. Naming a bead you did not
  read is inventing one, and a reader cannot tell an invented row from a measured one.
- Rebuild a plugin script's work as a shell pipeline, or read its answer from anything but its exit
  code and its output. Each one exists because the pipeline it replaced had a trap in it, and a
  rebuilt pipeline re-enters that trap with nothing left to catch it.
- Ask the user a question; stop with a report instead
