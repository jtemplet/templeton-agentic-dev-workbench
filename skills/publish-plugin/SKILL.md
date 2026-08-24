---
name: publish-plugin
description: "Cut and publish a release of this plugin: derive the semver bump from the changes since the last tag, write the CHANGELOG version section, bump .claude-plugin/plugin.json, land any feature branch by delegating to the ship skill, commit as chore(release): X.Y.Z, tag vX.Y.Z, and push main and the tag. Fails closed on an undecidable bump, a dirty tree, or the tag hook's validation refusal, and ends with one machine-readable PUBLISH_DONE / PUBLISH_BLOCKED line."
---

# Publish Plugin

Turns whatever has landed on main into a numbered, tagged, published release.

**Pushing main is the publish.** The marketplace entry for this plugin pins
`"version": "latest"` against the repository's git URL, so every consumer follows the default
branch. A commit on main is already published, whether or not anybody bumped a version. The tag
and the manifest version are how a human finds out *which* published state they are running, and
that is the whole reason this skill exists.

It exists because the manual path drifted twice. `plugin.json` sat at `2.10.1` while main ran 13
commits past its release commit, and `v2.10.0` and `v2.10.1` were created locally and never
pushed. Neither failure announced itself.

## When to Use / When NOT to Use

Use when:

- Work has landed on main and should become a numbered release.
- A feature branch is finished and should land *and* ship as a release in one pass.
- Asked to "publish the plugin", "cut a release", "bump the version and tag it", or "release X.Y.Z".

Do NOT use when:

- The work has not been gated. `ship` runs the repository's check suite as its gate; this skill
  runs that gate too, but it is not a substitute for `/quality-gates` or `/verify-acceptance`.
- You want to know *whether* to release. This skill releases. Ask for the changelog diff instead.
- The repository is not this plugin. The bump rubric below is written against a Claude Code
  plugin's public surface: component names, hook wiring, flags, and environment variables.

## The Four Rules

**1. The bump is derived, never chosen.** It comes from the changes since the last tag, read
against the rubric in Step 2. State the rule that decided it and the evidence, so the number can be
argued with. A bump nobody can justify is a number nobody trusts.

**2. The release commit is its own commit, and it touches exactly two files.** `CHANGELOG.md` and
`.claude-plugin/plugin.json`. Never fold it into a feature squash. Releases here batch several
landings, so tying the bump to one branch would misdate every other change in it, and the tag must
point at a tree whose manifest states the version the tag claims.

**3. The tag is created locally and pushed in the same run.** A local-only tag is the exact drift
this skill was written against. `reference-transaction` gates tag creation on
`claude plugin validate`, and its refusal is a stop, not a warning to route around.

**4. Every stop names the state it left.** Say whether the tag exists, whether main was pushed, and
whether the release commit is on disk. A half-published release that nobody can describe is worse
than an unpublished one.

## Invocation

```text
/publish-plugin                  # release what is on main
/publish-plugin <branch>         # land that branch first, then release
/publish-plugin --as 3.0.0       # override the derived version
/publish-plugin --dry-run        # decide and report, change nothing
```

Environment, all optional:

| Variable | Effect |
|---|---|
| `TADW_PUBLISH_CHECK` | The exact gate command. Overrides the detected gate in Step 5. |
| `TADW_PUBLISH_CHECK_TIMEOUT` | Gate timeout in seconds. Default 900. |

There is no variable that skips the gate or the tag hook, and do not add one. `TADW_PREPUSH=off` is
likewise not yours to set.

## Required Workflow

Track the seven steps with TodoWrite. On any stop, go straight to Step 7 and report.

### Step 1: Read the Ground

Every one of these is cheap, and each can end the run:

```bash
git rev-parse --show-toplevel                  # a repository at all
test -f .claude-plugin/plugin.json             # this plugin, not some other repo
git branch --show-current
git status --porcelain                         # must print nothing
git worktree list --porcelain                  # who holds the default branch
git fetch origin --tags
```

Resolve the **default branch** from `git symbolic-ref refs/remotes/origin/HEAD`, then a local
`main`, then `master`. This file writes `main` for readability only.

Refuse, in this order, stopping at the first match:

| Condition | Block reason |
|---|---|
| Not a git repository, or no `.claude-plugin/plugin.json` | `not-a-plugin-repo` |
| Working tree dirty | `dirty-tree` |
| A rebase, merge, or cherry-pick in progress | `operation-in-progress` |
| `origin/main` holds commits local main does not, and cannot fast-forward | `main-diverged` |

Test the in-progress case by asking whether the path exists, never by `git rev-parse`'s exit code,
which is 0 whether or not the path is there:

```bash
for p in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD; do
  [ -e "$(git rev-parse --git-path "$p")" ] && echo "in progress: $p"
done
```

**Read the current version and the last tag:**

```bash
python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])"
git tag --list 'v*' --sort=-v:refname | head -5   # LAST_TAG is the first line
git describe --tags --abbrev=0 --match 'v*'       # cross-check only
```

**The first line of the sorted list is `LAST_TAG`.** Two rules behind that:

- Use `--sort=-v:refname`, never plain `git tag --list`. Lexical order puts `v2.10.1` above
  `v2.5.2`, and reading the last line of an unsorted list is how a released tag gets reported as
  missing.
- `git describe` is the cross-check, not the answer. It only sees tags reachable from HEAD, so a tag
  made on another branch is invisible to it. When the two disagree, take the sorted list and say they
  disagreed, since that means a release was tagged off this line.

**Then check the tags against the remote,** because a local-only tag is the drift this skill closes:

```bash
git ls-remote --tags origin 'v*'
```

An unpushed tag is not a stop. Name each one, and push it by name in Step 6 alongside the new one.

### Step 2: Derive the Bump

**Read what changed since the last tag.** Both the shape and the substance:

```bash
git log --oneline "$LAST_TAG"..origin/main
git diff --stat "$LAST_TAG"..origin/main
git diff --name-status "$LAST_TAG"..origin/main -- skills/ agents/ commands/ hooks/
```

When a branch was named at invocation, include its commits too; they are part of this release.

**Apply this rubric.** Take the highest tier any change reaches, and name the change that decided
it:

| Bump | What earns it |
|---|---|
| **MAJOR** | A component renamed or removed, so an existing invocation path stops resolving. A change to `name` in `plugin.json`, which renames every `tadw:<component>` path at once. A removed or renamed flag, environment variable, or documented file path. A changed machine-readable contract, such as `ship`'s `SHIP_DONE` line or the `quality-gates` JSON artifact. |
| **MINOR** | A new skill, agent, or command. A new capability inside an existing one. A new flag, environment variable, or hook event. A new gate or check that can now fail a run that used to pass. |
| **PATCH** | A fix to existing behavior. A documentation or comment edit. A test-only change. A wording change that alters no interface. |

Two tie-breaks, because they are the cases that get argued:

- **A new check that can fail a previously passing run is MINOR, not PATCH.** It changes what the
  plugin does to its user's repository, even though nothing was added to the API surface.
- **Removing a check is PATCH unless something documented named it.** Nothing stops resolving.
  Removing `evals/test_run.py` from `pre-push` in 2026-08 is the worked example: the command still
  exists and the ship gate still runs it.

**Read the `Unreleased` section of `CHANGELOG.md` as evidence, never as the answer.** It records
what a human thought was notable. The diff records what actually changed, and the two disagree
whenever somebody forgot to write an entry.

**Stop with `bump-undecidable` when the rubric does not reach a tier**, which happens when the range
holds no change at all. An empty range means the release was already cut; say which tag holds it.

Report the decision in one line before continuing: the tier, the rule, and the change that earned
it. With `--as`, use the given version and say that the derived bump was overridden, along with what
it would have been.

**Then check that the version you just derived is not already taken,** before doing any work toward
it:

```bash
git rev-parse --verify --quiet "refs/tags/v$NEW_VERSION"   # prints nothing when free
git ls-remote --tags origin "refs/tags/v$NEW_VERSION"      # prints nothing when free
```

Either one printing a line stops the run with `tag-exists`. Check both, because the local and the
remote disagree often enough to matter: this is the repository where two tags existed locally and on
no remote. Never move or delete the existing tag; cut the next version instead.

### Step 3: Land the Branch, When One Was Named

Skip this step entirely when releasing what is already on main.

**Delegate to the `ship` skill.** Do not reimplement the land. `ship` owns rebasing onto the base,
gating the rebased tip, resolving a `.beads/issues.jsonl` conflict through `bd export`,
squash-merging, closing the bead, pushing main without forcing, and the worktree rules that keep a
linked worktree from resetting the branch it holds. That is a large body of edge cases, and a second
copy of it would drift from the first.

Read `ship`'s last line, which is its contract:

| `ship` reports | What to do |
|---|---|
| `SHIP_DONE <hash>` | Continue. That hash is the base of this release. |
| `SHIP_BLOCKED <reason>` | Stop with `land-failed`, and pass `ship`'s reason through verbatim. |

Nothing is published on a blocked land. The branch keeps its work, and the report says so.

### Step 4: Write the Changelog

**Move the `Unreleased` section into a version section.** Keep the Keep a Changelog shape the file
already uses, which is the `### Added` / `### Changed` / `### Fixed` / `### Removed` subheadings,
and one bolded lead sentence per entry:

```markdown
## [Unreleased]

## [2.11.0] - 2026-08-23

### Added

- **One bolded sentence naming the change.** Then the why, and what it replaces.
```

Four rules for the section, and the first is the one that gets skipped:

1. **Every entry in it must be true of the diff.** Read `git log` for this range and add an entry
   for anything the `Unreleased` section never recorded. A changelog that documents three of eight
   changes is worse than an empty one, because it reads as complete.
2. **The date is the release date, in `YYYY-MM-DD`.** Take it from `date +%F`, never from memory.
3. **Leave an empty `## [Unreleased]` heading above the new section.** The next change has somewhere
   to go, and its absence is why entries end up in the wrong version.
4. **Add the compare link to the footer**, above the previous version's line, in the existing shape:

   ```text
   [2.11.0]: https://github.com/<owner>/<repo>/compare/v2.10.1...v2.11.0
   ```

   Read `<owner>/<repo>` from `git remote get-url origin`. Do not hardcode it; a fork publishes from
   its own URL.
5. **Re-point the `[Unreleased]` compare link at the new tag.** It sits at the top of the footer
   block and reads `compare/<previous>...HEAD`. Nothing else updates it, and it is stale in this
   repository right now: it names `v2.10.0` while 2.10.1 is released.

Then verify the file before it becomes a commit:

```bash
grep -n '^## \[' CHANGELOG.md | head -5          # new section directly under Unreleased
grep -n "^\[$NEW_VERSION\]:" CHANGELOG.md        # exactly one footer link for the new version
grep -n '^\[Unreleased\]:' CHANGELOG.md          # must now compare from the new tag
```

**Do not lint this file with `rumdl`.** `CHANGELOG.md` sits in `.rumdl.toml`'s `exclude` list, and
passing it by name does not override that: `rumdl fmt --check CHANGELOG.md` prints
`No markdown files found to check.` and exits 0, so it reports success having checked nothing.
`--no-config` does reach the file, and then exits 1 on 901 issues under rules this repository
disables on purpose. The three greps above are the check.

### Step 5: Bump the Manifest and Gate

**Get onto the default branch first, and find out who holds it.** Everything from here writes to
main, and after Step 3 you are standing wherever `ship` left you, which may be the deleted branch's
old position or a detached HEAD:

```bash
git worktree list --porcelain          # which worktree has the default branch
git switch main                        # fails when another worktree holds it
git -C <that-path> branch --show-current   # must print the default branch
```

**When a linked worktree holds main, `git switch` refuses,** and every command in this step and Step
6 runs with `git -C <that-path>` instead. Do not remove that worktree, and do not detach anything to
work around it. That is not hypothetical in this repository: a release run on 2026-08-23 found main
checked out in `.worktrees/`, and `git switch main` exited with
`fatal: 'main' is already used by worktree at ...`. Confirm with the `branch --show-current` line
above before any command that moves a branch pointer or writes a file.

Then bring it current, and refuse rather than reconcile:

```bash
git -C <path> pull --ff-only origin main
```

A failure here is `main-diverged`. Local main holds something `origin/main` does not, and choosing
between two histories of the default branch is a human's call.

**Write the version into the manifest,** and change nothing else in it:

```bash
python3 - "$NEW_VERSION" <<'PY'
import json, sys
path = ".claude-plugin/plugin.json"
with open(path, encoding="utf-8") as handle:
    manifest = json.load(handle)
manifest["version"] = sys.argv[1]
with open(path, "w", encoding="utf-8") as handle:
    json.dump(manifest, handle, indent=2)
    handle.write("\n")
PY
git diff --stat .claude-plugin/plugin.json        # must be 1 insertion, 1 deletion
```

That diff check is the point of writing it through `json`: a hand edit reflows or reorders keys, and
a one-line change proves nothing else moved. When it reports more than one line, restore the file
and edit the single `version` line in place instead.

**Then run the gate on the tree that will be tagged.** Detect the command in this order and stop at
the first that yields one:

1. `TADW_PUBLISH_CHECK`, run verbatim.
2. The repository's own declared list: the "Commands for This Repo" block in `AGENTS.md` or
   `CLAUDE.md`. Every command in it must exit 0, minus any the block itself excludes by name.
3. A `check` target in a task runner.

**No source yields a command: stop with `gate-not-detected`.** A release is the worst possible place
to publish unchecked work, since the marketplace serves main to every consumer immediately.

Give it a bounded timeout (`TADW_PUBLISH_CHECK_TIMEOUT`, default 900 seconds). Record the command,
the exit code, and the real counts. Any non-zero exit stops with `gate-failed`, before the commit.

Never report the gate as "green" or "passing". Give the command, the exit code, and the numbers.

**With `--dry-run`, stop here.** Report the derived version, the changelog section you would write,
and the gate result. Restore both files so the tree is exactly as you found it, and say that you
did.

### Step 6: Commit, Tag, and Push

**Commit exactly the two files:**

```bash
git add CHANGELOG.md .claude-plugin/plugin.json
git status --porcelain                            # must show only those two
git commit -m "chore(release): $NEW_VERSION" -m "<one line saying what ships and why this tier>"
```

Anything else in `git status` means an earlier step left a file behind. Stop with `dirty-tree`
rather than sweeping it into a release commit.

**Tag the release commit, annotated:**

```bash
git tag -a "v$NEW_VERSION" -m "$NEW_VERSION"
```

`reference-transaction` runs `claude plugin validate` here and refuses the tag when it fails. That
is the gate the 2.4.1 frontmatter bug went out through, so treat a refusal as a stop:
`validate-refused-tag`. The release commit stays on disk, unpushed and untagged, and the report says
so along with the validation output.

A missing `claude` on PATH makes the hook warn and allow. Say so in the report; the tag exists but
nothing validated it.

**Push main first, then the tags:**

```bash
git push origin main
git push origin "v$NEW_VERSION"
git push origin v2.10.0 v2.10.1                   # each older tag Step 1 found, BY NAME
git ls-remote --tags origin "v$NEW_VERSION"       # must print the tag
```

Main goes first on purpose. A tag on the remote that names a commit the remote does not have is a
broken reference for everyone who fetches it.

**Name every tag you push, and never use `git push origin --tags`.** That flag pushes every local
tag, including private ones somebody made to mark an experiment, and publishing a ref is not
reversible for anyone who has already fetched it. Step 1 listed the missing tags; push exactly those.

**On a rejected push**, someone landed while this ran. Do not force, and do not reset a main that
carries a commit this run did not create. Delete the local tag, rebase the release commit onto the
new `origin/main`, and re-run Steps 5 and 6 so the gate grades what will actually be tagged. Bound
the whole cycle at 3 attempts, then stop with `push-rejected`.

**Verify the published state before reporting success:**

```bash
git ls-remote origin main                         # matches the local release commit
python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])"
```

### Step 7: Report

Emit the report, then the machine line, then stop.

## Output Format

On success:

```markdown
## Published 2.11.0

**Bump:** MINOR. A new skill (`skills/publish-plugin/SKILL.md`) is added, and the rubric's MINOR
tier covers a new component. Nothing was renamed or removed, so nothing reaches MAJOR.
**Range:** `v2.10.1..main`, 14 commits, 23 files
**Landed first:** `outrigger/tadw-muo/publish-plugin-skill` via `ship`, `SHIP_DONE a1b2c3d`
**Changelog:** `## [2.11.0] - 2026-08-23`, 4 entries under Added and Changed, 2 of them written
from the log because `Unreleased` never recorded them
**Gate:** the `AGENTS.md` list minus `python3 evals/run.py`, 16 commands, all exit 0, 121s
**Release commit:** `e5f6a7b` `chore(release): 2.11.0`, touching CHANGELOG.md and plugin.json
**Tag:** `v2.11.0`, annotated, `claude plugin validate` passed at the tag hook
**Pushed:** `origin/main` at `e5f6a7b`, then `v2.11.0`. Also pushed `v2.10.0` and `v2.10.1`, which
existed locally and had never left the machine.

PUBLISH_DONE 2.11.0 e5f6a7b
```

On a stop:

```markdown
## Not published

**Stopped at:** Step 6, the tag
**Reason:** `claude plugin validate` failed at the `reference-transaction` hook

<the validation output>

**State on disk:**

- `chore(release): 2.11.0` is committed on main and is NOT pushed
- No tag was created, so nothing names this release
- The changelog and the manifest both say 2.11.0

**What a human should do:** fix the validation error, `git commit --amend` if the fix belongs in the
release commit, then re-run `/publish-plugin --as 2.11.0`.

PUBLISH_BLOCKED validate-refused-tag
```

Both forms end with exactly one machine line, as the last line. Nothing follows it.

## Block Reasons

| Slug | Means |
|---|---|
| `not-a-plugin-repo` | No repository, or no `.claude-plugin/plugin.json` |
| `dirty-tree` | Uncommitted changes, at Step 1 or before the release commit |
| `operation-in-progress` | A rebase, merge, or cherry-pick was already running |
| `main-diverged` | Local main cannot fast-forward to `origin/main` |
| `bump-undecidable` | The rubric reached no tier, which means the range holds no change |
| `land-failed` | `ship` reported `SHIP_BLOCKED`; its reason is quoted |
| `gate-not-detected` | No gate command from any source |
| `gate-failed` | The gate ran and exited non-zero |
| `gate-blocked` | The gate could not run: timeout, exit 127, missing runner |
| `tag-exists` | `vX.Y.Z` already exists locally or on the remote |
| `validate-refused-tag` | The `reference-transaction` hook refused the tag |
| `push-rejected` | Three pushes rejected |
| `internal-error` | Anything else; the prose explains it |

## Edge Cases

**The version in `plugin.json` is already ahead of the last tag.** Someone bumped and never tagged,
which is what happened at 2.10.1. Do not bump again. Tag the existing version if the tree is
unchanged since the bump commit, and say that is what you did. When main has moved since, derive
the bump from the last *tag*, not from the manifest, and report both numbers.

**`vX.Y.Z` already exists.** Stop with `tag-exists`. Never move or delete a published tag; a
consumer may already have fetched it. Cut the next version instead.

**The `Unreleased` section is empty but the range is not.** Write the section from the log. That is
the common case, not an exception: entries get skipped whenever work lands through `ship` rather
than by hand.

**A MAJOR bump.** Say in the report which invocation paths stop resolving, and name them. The
`name` field in `plugin.json` is the invocation namespace, so changing it renames every
`tadw:<component>` path, including ones hardcoded in other repositories.

**No origin.** There is nothing to publish. The commit and the tag are local, the report says so,
and the machine line is `PUBLISH_BLOCKED internal-error` with that stated plainly. A plugin nobody
can fetch has not been released.

## Critical Rules

**Always:**

- Derive the bump from the diff and name the rule that decided it
- Read the last tag with `--sort=-v:refname`, never lexical order
- Keep the release commit to `CHANGELOG.md` and `.claude-plugin/plugin.json`
- Write the manifest through a JSON round-trip, and prove the diff is one line
- Run the repository's gate on the tree that will be tagged, after the bump
- Delegate the land to `ship`, and pass its block reason through unchanged
- Push main before the tag
- Push a tag in the same run that creates it, including older tags that never left the machine
- Push every tag by name
- Confirm you are on the default branch before any command that moves its pointer, and scope the
  main-side commands with `git -C` when a linked worktree holds it
- Check that `vX.Y.Z` is free, locally and on the remote, before doing work toward it
- End with exactly one machine line, as the last line

**Never:**

- Fold the version bump into a feature branch's squash commit
- Move, delete, or re-point a tag that exists on the remote
- Force-push main, or push past a `reference-transaction` refusal
- Run `git push origin --tags`, which publishes every local tag
- Lint `CHANGELOG.md` with `rumdl`; the config excludes it, and passing it by name checks nothing
- Detach a worktree's HEAD, or remove a worktree, to get at the default branch
- Set `TADW_PREPUSH=off`, or add a variable that skips the gate or the tag hook
- Choose a bump because it feels right, or bump twice for one release
- Report a gate as "green" without its numbers
- Write a changelog entry the diff does not support, or leave a real change unrecorded

## Quality Checklist

Before emitting the report, verify:

- [ ] The bump tier, the rule behind it, and the deciding change all appear
- [ ] The commit range is named, with its commit and file counts
- [ ] Every changelog entry maps to something in the range, and nothing in the range is unrecorded
- [ ] `## [Unreleased]` is still present and empty, above the new section
- [ ] The footer holds exactly one compare link for the new version
- [ ] The `[Unreleased]` footer link now compares from the new tag
- [ ] `vX.Y.Z` was free locally and on the remote before any work went toward it
- [ ] The manifest diff is one line
- [ ] The gate's command, exit code, and counts all appear, and it ran after the bump
- [ ] The release commit touches exactly two files
- [ ] The tag is annotated, and `git ls-remote` confirms it reached the remote
- [ ] Main was pushed before the tag, and every tag was pushed by name
- [ ] The release commit was made on the default branch, scoped with `git -C` if a worktree held it
- [ ] On a stop, the report says whether the commit, the tag, and the push happened
- [ ] The last line is exactly one `PUBLISH_DONE <version> <hash>` or `PUBLISH_BLOCKED <reason>`
