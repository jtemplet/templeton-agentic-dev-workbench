---
name: pr-maintenance
description: Keep the current branch's open PR rebased on its parent branch and green on CI. Detects the PR's actual base branch (not hardcoded main), rebases with AI-assisted conflict resolution, diagnoses CI failures, and applies the smallest possible fixes scoped to files already in the PR diff. Designed to be run on a loop.
---

# PR Maintenance

A systematic technique for keeping a single PR healthy: rebased on its parent branch and passing required CI checks. Designed to be idempotent so it can run on a loop (e.g., `/loop 6h /pr-maintain`) without causing drift.

## When to Use

- Long-lived PRs that need to stay current with their base branch
- Stacked PRs where the base branch is not `main`
- Before stepping away from a PR you want to land later
- On a recurring schedule via `/loop` to keep everything green between work sessions

## When NOT to Use

- On the default branch itself (there is no PR to maintain)
- On a PR that has no open GitHub PR yet (open one first)
- For large refactors or architectural changes to fix CI (this skill is for targeted fixes only)
- When you want to change what the PR does (this skill does not add features)

## Required Workflow

### Step 1: Detect Context

Before doing anything else, establish:

1. **Current branch**

   ```bash
   CURRENT=$(git rev-parse --abbrev-ref HEAD)
   ```

   If the current branch is the default branch (e.g., `main`, `master`), stop immediately and report: "Cannot maintain a PR from the default branch."

2. **Open PR for this branch**

   ```bash
   gh pr view --json number,baseRefName,headRefName,state,isDraft,mergeable,mergeStateStatus
   ```

   If no PR exists or the PR is closed/merged, stop and report: "No open PR for branch `<name>`."

3. **Parent (base) branch** from the PR itself, not a hardcoded value:

   ```bash
   BASE=$(gh pr view --json baseRefName -q .baseRefName)
   ```

   This handles stacked PRs correctly. The parent is whatever branch the PR targets, which may be `main`, a release branch, or another feature branch.

4. **Required CI checks** and overall status:

   ```bash
   gh pr checks
   gh pr view --json statusCheckRollup
   ```

### Step 2: Rebase Onto Parent

1. Fetch the parent:

   ```bash
   git fetch origin "$BASE"
   ```

2. Check whether the branch is already up to date:

   ```bash
   git rev-list --count "HEAD..origin/$BASE"
   ```

   If `0`, the branch already contains everything in parent. Skip the rest of Step 2 and Steps 3 and 4 (no rebase or push needed); go directly to Step 5 (Read CI Status).

3. Require a clean working tree (abort if dirty rather than stashing silently):

   ```bash
   git status --porcelain
   ```

   If anything is uncommitted, stop and report: "Uncommitted changes in working tree. Commit or stash before running pr-maintenance."

4. Rebase:

   ```bash
   git rebase "origin/$BASE"
   ```

5. **If rebase succeeds cleanly**, proceed to push with lease.

6. **If rebase hits conflicts**, resolve them carefully (next step).

### Step 3: Conflict Resolution (AI-Assisted)

When `git rebase` stops on conflicts:

1. Identify conflicted files:

   ```bash
   git diff --name-only --diff-filter=U
   ```

2. **Hard-stop files.** If any conflicted path matches these patterns, abort the rebase and escalate to the user:

   - `db/migrate/**`, `**/migrations/**` (schema changes are too risky to auto-merge)
   - `**/secrets/**`, `.env*`, `**/credentials/**`
   - `**/Gemfile.lock`, `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`, `**/Cargo.lock`, `**/poetry.lock`, `**/uv.lock` (lockfile semantic conflicts)

   Abort with:

   ```bash
   git rebase --abort
   ```

   Report which files triggered the hard-stop and stop the iteration.

3. **For every other conflict**, resolve with full context:

   - Read the entire conflicted file (not just the hunk)
   - Read both sides of every conflict marker (`<<<<<<<` to `=======` to `>>>>>>>`)
   - Understand the semantic intent of each side:
     - What was the PR's change trying to accomplish?
     - What did the base branch introduce?
     - Do they overlap logically, or are they independent edits to nearby lines?
   - Write a resolution that preserves both intents where possible
   - Never discard one side wholesale without explanation

4. Stage resolved files and continue:

   ```bash
   git add <files>
   git rebase --continue
   ```

5. **Validate after rebase.** If a local test command is detectable, run it on the rebased state (see Step 6 for detection). If tests fail in a way that appears caused by the conflict resolution, abort the whole rebase:

   ```bash
   git rebase --abort  # or: git reset --hard ORIG_HEAD if rebase is done
   ```

   Report which resolution caused the failure and escalate to the user.

6. **Commit resolution narrative.** Rebases do not produce a separate commit, but record the resolution decisions in the iteration report (Step 7) so the user can review what was resolved and revert the push if a resolution looks wrong.

### Step 4: Push With Lease

After a successful rebase:

```bash
git push --force-with-lease
```

Never use plain `--force`. If `--force-with-lease` fails because the remote has moved:

- Do NOT retry with `--force`.
- Do NOT reset the local branch. Leave the rebased commits in place so the user can inspect them.
- Abort the iteration and report: "Remote branch moved during rebase. Someone else pushed. Local branch still holds the rebased commits; reconcile manually (e.g., `git fetch && git log origin/<branch>..HEAD` to see what would have been pushed, then `git reset --hard origin/<branch>` to discard and re-run, or resolve manually and push)."

### Step 5: Read CI Status

```bash
gh pr checks --required
gh pr view --json statusCheckRollup
```

Classify the result:

- **All required checks passing** -> proceed to Step 7 (report success, no code changes)
- **Required checks still running** -> proceed to Step 7 (report pending, no code changes this iteration)
- **Required checks failing** -> proceed to Step 6

Non-required checks that are red do not trigger fixes. Report them in the summary but do not act.

### Step 6: Fix Failing Required Checks

**Scope rule (hard):** Only edit files that are already in the PR diff.

Compute the PR diff file list:

```bash
gh pr diff --name-only
```

Keep this list. Every edit in this step must be to a file in that list. If the fix requires touching a file NOT in the list, stop and escalate to the user.

For each failing required check:

1. **Download the relevant logs** for the failing job:

   ```bash
   gh run list --branch "$CURRENT" --limit 5
   gh run view <run-id> --log-failed
   ```

2. **Identify the specific failure** (a test, a lint rule, a type error, a build step). Focus on the first failure, not the whole log.

3. **Decide if it is fixable within scope.** If the failure points to:

   - A file in the PR diff that has a genuine bug -> fixable
   - A file NOT in the PR diff -> out of scope, escalate
   - A test assertion that looks incorrect and the test file is NOT in the PR diff -> out of scope, escalate (this prevents masking real failures by adjusting tests)
   - A flaky test (intermittent, unrelated to the change) -> do not modify, report as flaky
   - An infrastructure failure (npm registry down, GitHub Actions outage) -> do not modify, report and wait

4. **Apply the smallest possible fix.** One file at a time, one change at a time. No refactoring. No cleanup of surrounding code.

5. **Validate locally** (see test command detection below).

6. **Commit and push:**

   ```bash
   git add <file>
   git commit -m "fix: <one-line description of the specific failure>"
   git push
   ```

   Regular `git push` here, not `--force-with-lease`, because this is a fast-forward (no rebase involved).

### Test Command Detection

Before pushing a CI fix, try to validate locally. Check in this order and run the first one found:

1. `bin/ci` (if executable)
2. `bin/test` (if executable)
3. `package.json` contains `"test"` script -> `npm test` or `pnpm test` or `yarn test` (match the lockfile)
4. `pytest.ini`, `pyproject.toml` with pytest config, or `tests/` directory -> `pytest`
5. `Gemfile` with rspec -> `bundle exec rspec`
6. `go.mod` present -> `go test ./...`

If none match, skip local validation and rely on remote CI. Report which command was used (or that none was found) in the summary.

### Step 7: Report

Always produce this report, even when no action was taken:

```markdown
## PR Maintenance Iteration

**Branch:** `<current-branch>`
**PR:** #<number> -> `<base-branch>`
**Timestamp:** <ISO-8601 UTC>

### Rebase

- Status: done / skipped / blocked
- Commits replayed: <N>
- Conflicts encountered: <N>
- Conflict resolution notes:
  - `<file>`: <one-line description of how it was resolved>
  - ...

### CI Status

- Overall: green / failing / pending
- Required checks:
  - `<check-name>`: passing / failing / pending
  - ...
- Non-required failures (informational, not acted on):
  - `<check-name>`: <brief reason>

### Code Changes This Iteration

- `<file>`: <one-line description>
- ...

(or: "No code changes this iteration.")

### Next Actions

- (list anything the user needs to resolve manually)
- (or: "None. PR is up to date and green.")
```

## Critical Rules

**Always:**

- Detect the base branch from the PR itself (`gh pr view --json baseRefName`)
- Use `git push --force-with-lease`, never `--force`
- Constrain CI-fix edits to files already in the PR diff
- Read full files before resolving conflicts (not just hunks)
- Abort and escalate when a conflict touches migrations, lockfiles, or secrets
- Validate locally before pushing a CI fix, when a test command is detectable
- Produce the iteration report every time, even on no-op runs

**Never:**

- Assume the parent is `origin/main`
- Use `git push --force` (no lease)
- Modify commits on branches other than the current one
- Modify test assertions in files that are NOT in the PR diff
- Edit files outside the PR diff to make CI pass
- Refactor or clean up code while fixing CI
- Continue an iteration after a hard-stop conflict (migrations, lockfiles, secrets)
- Retry after a `--force-with-lease` failure with plain `--force`

## Quality Checklist

Before reporting completion, verify:

- [ ] Base branch was read from the PR, not hardcoded
- [ ] Working tree was clean before rebase
- [ ] Rebase used `--force-with-lease` if it pushed
- [ ] All conflict resolutions are documented in the report
- [ ] Every code edit is within the PR's existing file list
- [ ] Local validation was attempted (or explicitly reported as skipped)
- [ ] Report includes rebase status, CI status, code changes, and next actions
- [ ] Iteration is idempotent: running it again immediately would be a no-op
