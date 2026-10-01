# Development Workflow

Guidelines for contributing to the Atlas project using `bd` (beads) for issue tracking.

---

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd dolt push               # Sync with git

# Create a branch for your work (git hooks auto-update beads status)
git checkout -b feature/<id>/<short-description>     # For features
git checkout -b task/<id>/<short-description>        # For tasks
git checkout -b bug/<id>/<short-description>         # For bugs
```

---

## GitHub Flow & Merge Policy

**This project follows GitHub Flow:**

- `main` branch is always deployable and protected
- All work happens in feature/task/bug branches
- Changes are integrated via merge (or pull request for review)
- Never push directly to `main` - always work in a branch

## Landing on main: use `/tadw:ship`, never do it by hand

**Once you have consent to land, `/tadw:ship` performs the land. Do not assemble one from the
commands in this file.** This section and the ones below describe the policy, the branch names, and
the hooks. They are not a procedure for landing, and following them as though they were produces a
land that looks correct and is not.

The skill does five things in an order that matters, and a hand-rolled land drops some of them
silently:

| Step | What it does | What a hand-rolled land tends to skip |
|---|---|---|
| 2 | Rebase onto the base, resolving `.beads/issues.jsonl` by re-export | Usually done |
| 3 | Detect this repository's check command and require exit 0 | **Skipped.** No gate ran, and nothing said so |
| 4 | `git merge --squash`, one commit, `<type>: <title> (<bead-id>)` | **Skipped.** Fast-forwarding several commits leaves a history that does not match the convention |
| 4 | Close the bead and fold the export into the landing commit with `--amend` | Leaves the export as a second commit |
| 5 | `git push origin main`, then `bd dolt push`, then delete the branch | **`bd dolt push` skipped.** Issue history travels under `refs/dolt/data`; the committed JSONL cannot express a deletion, so new beads stay on one machine |

This was written after a documentation change landed on 2026-09-05 as two fast-forwarded commits
with no gate run and no `bd dolt push`, because the agent read this file, followed it faithfully,
and never learned the skill existed. The failure was invisible: every step it did run passed.

**A bare "ship" in a request names this skill.** So do "build", "review", and "triage". See the
skill-invocation rule in [`CLAUDE.md`](../CLAUDE.md).

Use `/tadw:pr-maintain` instead when the change goes through a pull request. `/tadw:ship` opens no
PR and reads no GitHub CI; the local gate is the only thing that decides.

---

## CRITICAL: Agent Merge Policy

**Agents MUST NEVER merge to main without explicit user consent.**

When work is complete:

1. Verify tests pass and code is ready
2. Present the work to the user
3. Ask: "Ready to merge to main, create a PR for review, or make changes?"
4. Wait for user decision before executing merge

This applies to ALL merges - features, tasks, bugfixes, documentation, everything.

**Exception:** The user may explicitly say "merge to main when done" at the start of a task. In this
 case, confirm understanding and proceed accordingly when complete.

---

## Branch & Worktree Naming Convention

When starting work on an issue, create a branch using this format:

```text
[feature|task|bug]/<beads-id>/<short-description>
```

**Examples:**

```bash
git checkout -b feature/3po.1.1/add-jwt-security-schemes
git checkout -b fix/hdw-26ze/stress-verdict-one-vocabulary
git checkout -b task/hdw-plb/design-dashboard-layout
git checkout -b bug/9j7/fix-email-template-rendering
```

The four accepted prefixes are `feature/`, `fix/`, `task/`, and `bug/`. The
bead id must be its own segment, never glued to the slug: the resolver reads
segment two verbatim, so `fix/hdw-26ze/slug` resolves and `fix/hdw-26ze-slug`
does not.

**Why this matters:**

- Git hooks and the Claude bead hook both read the branch name
- **`/build`:** Running it marks an `open` issue `in_progress`. A closed issue is
  left alone, so re-reading a spec cannot reopen it. Checkout no longer does
  this: checking out a branch is not the same as starting work on it.
- **Pre-push hook:** Push to existing PR → marks issue as `in_review`
- **Post-merge hook:** `git pull origin main` after PR merge → marks issue as `closed`

Neither hook touches `.beads/issues.jsonl` any more. It is a passive export,
refreshed by whoever touches the tracker; auto-committing it mid-checkout or
mid-push broke every tool that requires a clean tree.

---

## Pre-commit Hook (Local Linting)

The `pre-commit` hook lints **staged** changes before each commit, using the same
tools and config as the CI workflow in the Atlas repository, plus markdown:

- **Python** (`*.py` staged): `uv run ruff check --no-fix .`
- **Frontend** (`ui/*` staged): `npm run lint:check`
- **Markdown** (`*.md` staged): `rumdl check <staged files>` (staged files only,
  because the repo has a large pre-existing rumdl backlog; not run in CI)

Each linter runs only when a file of that type is staged, so a backend-only commit
skips the slower frontend lint. All are **report-only** (no auto-fix), so the hook
never rewrites your working tree mid-commit; it reports and **blocks** the commit on
any issue. The hook then flushes the beads DB to `.beads/issues.jsonl`.

It also **warns when the export holds beads that no commit carries**. A bead created
mid-session lives in the database and, after the flush, in your working tree. Nothing
commits it while the work sits on a feature branch, because those deliberately leave
`.beads` alone. On 2026-08-11 the committed export sat three records behind the database
across five merges before a rebase surfaced it. The warning names the ids; the fix is to
commit `.beads/issues.jsonl` on `main`. It never blocks, because the right moment to
commit the export is often not the commit you are making.

It also **refuses a staged `.beads/issues.jsonl` that carries a duplicate issue id**.
That is never something you typed; it is the signature of a bad merge, and `bd`
refuses to read the whole file once it happens. See "Beads Merge Driver" below.

```bash
# Install (or refresh) both hooks and the beads merge driver:
./scripts/git-hooks/install.sh

# Bypass for a single commit (use sparingly):
git commit --no-verify
```

The tracked source is the file scripts/git-hooks/pre-commit in the Atlas repository;
edit it there and re-run the installer. `ruff` and `eslint` are also enforced by CI;
`rumdl` is local-only.

---

## Post-merge Hook (Beads Auto-Close)

The `post-merge` hook closes beads whose IDs appear in the **subjects** of commits
that just arrived on `main`, so `git pull origin main` after a PR merge marks the
issue `closed` and commits the flushed `.beads/issues.jsonl`.

```bash
# Install (or refresh) the hook in your clone:
./scripts/git-hooks/install.sh
```

The tracked source is the file scripts/git-hooks/post-merge in the Atlas repository;
edit it there and re-run the installer.

Two things it does **not** do, both of which bite in practice:

- **Only commit subjects are scanned**, never bodies. A `Closes hdw-...` line in a PR
  description is invisible to it, and a squash merge whose subject is the PR title
  (`feat(ui): ... (#262)`) carries no ID, so nothing closes. Put the ID in the subject
  or close the bead by hand.
- **Any ID in a subject closes that bead**, including a parent epic. Reference only the
  child being closed.

---

## Beads Merge Driver

`.beads/issues.jsonl` is a keyed export: one JSON object per line, keyed by `id`. It
used to be versioned with `merge=union`, which appends both sides of a merge. When two
branches touched the same bead, git kept **both** records and reported success. `bd`
then refused the entire file:

```text
Configuration error: Duplicate issue id 'hdw-...' in .beads/issues.jsonl at line 569
```

The failure was silent locally. GitHub does not apply the union driver, so it reported
the PR as `CONFLICTING` while a local merge reported clean, and that disagreement was
the only reason it ever got noticed.

`.gitattributes` now points the file at a driver that reconciles **by issue id**, with
the later `updated_at` winning. Install it with:

```bash
./scripts/git-hooks/install.sh
git config --get merge.beads-jsonl.driver   # verify
```

Three properties worth knowing:

- **It degrades safely.** A clone without the driver configured falls back to git's
  default 3-way merge, which conflicts loudly. That is manual, never corrupt.
- **A conflict leaves valid JSONL, not conflict markers.** Markers would make the file
  unparseable for `bd`. When the driver cannot order two edits it keeps ours, says so on
  stderr, and exits non-zero. Resolve with `bd export -o .beads/issues.jsonl`, since the database is
  the real source of truth and the JSONL is only its export.
- **The pre-commit hook is the backstop.** It refuses a staged file carrying a duplicate
  id, so the corruption cannot be committed even where the driver is not installed.

The driver is the file scripts/git-hooks/beads_jsonl_merge.py in the Atlas repository,
with its rules pinned in that repository's tests/test_beads_jsonl_merge.py.

**Avoid the conflict entirely where you can.** Bead state belongs on `main`, not on a
feature branch. A branch that commits its own `.beads/issues.jsonl` edits is the case
that produces these merges in the first place.

---

## Working with Issues

### Finding Work

**Check what's ready:**

```bash
bd ready              # Tasks with no blockers
bd list --status=open # All open issues
```

**Review issue details:**

```bash
bd show <id>
```

This shows dependencies, description, acceptance criteria, and blocking relationships.

### Claiming Work

When starting a task:

```bash
bd update <id> --status in_progress
```

This signals you're working on it and helps avoid duplicate effort.

### Completing Work

Close issues when done:

```bash
bd close <id>
bd close <id1> <id2> <id3>  # Close multiple at once
```

Add a reason if helpful:

```bash
bd close <id> --reason="Implemented PostgreSQL migration"
```

---

## Session Completion Workflow

When wrapping up a work session, consider this checklist to ensure work is properly captured:

1. **Create issues for remaining work** — File new issues for anything discovered but not completed
2. **Run quality gates** — Tests, linters, type checks (if code changed)
3. **Update issue status** — Close completed work, update progress on in-progress items
4. **Sync with remote:**

   ```bash
   git pull --rebase      # Get latest changes
   bd dolt push                # Sync beads database
   git push               # Push your changes
   git status             # Verify clean state
   ```

5. **Verify completion** — Ensure all changes are committed and pushed

**Why this matters:** Issues and code should stay synchronized with the remote repository to
preserve context across sessions.

---

## Working with Dependencies

### Adding Dependencies

If a task depends on another:

```bash
bd dep add <issue-id> <depends-on-id>
```

**Example:**

```bash
bd create --title="Implement PostgreSQL schema" --type=task
# Creates hdw-123

bd create --title="Update pipeline to use PostgreSQL" --type=task
# Creates hdw-124

bd dep add hdw-124 hdw-123
# hdw-124 depends on hdw-123 completing first
```

### Checking Blocked Work

See what's blocked and why:

```bash
bd blocked
```

This helps identify which blockers to tackle first.

---

## Project Health

### Statistics

View project metrics:

```bash
bd stats
```

Shows open/closed/blocked counts and average lead time.

### Validation

Check for issues:

```bash
bd doctor
```

Identifies sync problems, orphaned dependencies, or configuration issues.

---

## Git Integration

`bd` integrates with git to persist issue data across branches:

**On ephemeral branches:**

```bash
bd dolt pull           # Pull latest beads from the Dolt remote
```

**Check sync status:**

```bash
bd vc status
```

**Best practice:** Run `bd dolt pull` before starting work and before pushing to ensure you
have the latest issue state.

---

## Creating Multiple Issues

For large features, break them into smaller tasks:

```bash
# Create parent epic
bd create --title="PostgreSQL Migration" --type=epic --priority=1

# Create child tasks
bd create --title="Design PostgreSQL schema" --type=task
bd create --title="Update ETL scripts" --type=task
bd create --title="Migrate existing data" --type=task
bd create --title="Update documentation" --type=task

# Add dependencies as needed
bd dep add hdw-125 hdw-124  # ETL scripts depend on schema
bd dep add hdw-126 hdw-125  # Data migration depends on scripts
```

**Tip:** For many issues, consider using parallel task creation to speed things up.

---

## Common Workflows

### Starting New Work

```bash
bd ready                                    # Find available tasks
bd show <id>                                # Review details

# Create a branch (the id must be its own segment)
git checkout -b feature/<id>/<description>  # For features/stories
# or
git checkout -b fix/<id>/<description>      # For fixes
# or
git checkout -b task/<id>/<description>     # For tasks
# or
git checkout -b bug/<id>/<description>      # For bugs

# Do the work...
git add .
git commit -m "description of changes"

git push -u origin HEAD    # pre-push hook marks in_review if PR exists
# Open a PR on GitHub, get it merged
git checkout main && git pull origin main  # post-merge hook closes the issue
```

The last three lines above are the pull-request path. **When the change lands locally instead, stop
after the commit and run `/tadw:ship`**, which rebases, gates, squash-merges, closes the bead,
pushes, runs `bd dolt push`, and deletes the branch. Do not hand-roll those steps; see
[Landing on main](#landing-on-main-use-tadwship-never-do-it-by-hand).

**Pro tip:** `/build` claims the issue and the git hooks handle the rest from the
branch name, so you rarely need to run `bd update` by hand.

### Discovering New Work During Implementation

If you discover issues while working:

```bash
bd create --title="Fix data validation bug" --type=bug --priority=2
bd dep add <current-issue-id> <new-issue-id>  # If it blocks your current work
```

This captures technical debt and unexpected work for later prioritization.

### Completing a Feature

```bash
# Run tests/linters on your branch
pytest tests/
# or bash scripts/run_tests.sh

# Commit your work
git add .
git commit -m "Implement feature X (hdw-<id>)"

# Create follow-up issues if needed
bd create --title="Add integration tests for feature X" --type=task

# Push and open a PR on GitHub
git push -u origin HEAD
# Open PR with issue ID in the title: "Implement feature X (hdw-<id>) (#42)"
# After PR is merged on GitHub:
git checkout main && git pull origin main  # post-merge hook auto-closes the issue

# Verify cleanup
git status               # Should be clean
bd show <id>            # Should show 'closed'
```

**Include the issue ID in your PR title:** e.g., `"Implement feature X (hdw-<id>) (#42)"`.
The post-merge hook scans commit subjects on `git pull origin main` to auto-close the issue.
If the PR title lacks the ID, close manually with `bd close <id>`.

---

## Best Practices

**Branch naming is critical for automation:**

- Always use `[feature|task|bug]/<hdw-id>/<short-description>` format
- The git hooks depend on this pattern to auto-update issue status
- Mismatched branch names = manual status updates (git hooks won't trigger)

**PR title convention:**

- Include the issue ID in your PR title: `"Fix login redirect (hdw-abc) (#42)"`
- The post-merge hook scans commit subjects to auto-close the issue on `git pull`
- If the PR title lacks the ID, close manually with `bd close <id>`

**Track work strategically:**

- Use `bd` for multi-session work, dependencies, and discovered work
- Use `TodoWrite` for simple single-session execution steps
- When in doubt, prefer `bd` — persistence you don't need beats lost context

**Keep issues updated:**

- Branch hooks auto-update status, but add notes for context
- If you update status manually, keep branch name in sync
- Close completed work promptly (or merge to main, which auto-closes)

**Sync regularly:**

- Pull beads updates before starting work
- Push both code and beads changes when finishing

**Break down large tasks:**

- Epic → Features → Tasks → Subtasks
- Use dependencies to show relationships
- Smaller issues = faster iteration

---

## Troubleshooting

### "Orphaned dependency" warnings

Run the repair command:

```bash
bd repair-deps --fix
```

### Sync conflicts

Check what's out of sync:

```bash
bd vc status
```

Pull latest from main:

```bash
bd dolt pull
```

### Lost issue context

Restore full history from git:

```bash
bd restore <issue-id>
```

---

## Additional Resources

- **Beads documentation:** Run `bd --help` or `bd <command> --help`
- **Issue search:** `bd search "keyword"` to find issues by text
- **Labels:** Organize work with `bd label add <id> <label>`
