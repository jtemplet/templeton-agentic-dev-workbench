---
description: "Keep the current branch's PR rebased on its parent and passing CI. One iteration per invocation. Safe to run on a loop."
---

Use the `pr-maintainer` agent to run a single maintenance iteration on the current branch's open PR.

The agent will:

1. Detect the current branch, its open PR, and the PR's actual base branch (not hardcoded `main`)
2. Rebase onto the base branch, resolving semantic conflicts with full-file context
3. Push with `git push --force-with-lease` if a rebase happened
4. Read required CI check status
5. If required checks are failing, apply the smallest possible fix scoped to files already in the PR diff
6. Report rebase status, CI status, files touched, and any manual actions needed

The agent is read-and-edit scoped (no force-push without lease, no edits outside the PR's file list, hard-stop on conflicts in migrations/lockfiles/secrets).

## Running on a Loop

Pair with the `loop` skill to keep the PR healthy automatically:

```
/loop 6h /pr-maintain
```

Each iteration is idempotent. If there is nothing to do, the command reports "PR is up to date and green" and exits.

## When Not to Use

- On the default branch (there is no PR to maintain)
- Before opening a PR on GitHub (open the PR first)
- For large refactors or architectural fixes to CI (this command makes targeted fixes only)
