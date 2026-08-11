#!/usr/bin/env bash
# Claude Code PostToolUse hook: close the bead associated with a merged PR.
#
# Triggered after any Bash invocation; only acts on successful `gh pr merge`
# commands. Reads the hook payload from stdin per Claude Code's hook
# contract:
#   https://docs.anthropic.com/en/docs/claude-code/hooks
#
# Flow:
#   1. Confirm the Bash command was `gh pr merge`.
#   2. Extract the PR identifier (number or URL).
#   3. Ask gh whether the PR actually merged.
#   4. Extract the bead ID from the PR title, branch name, or commit
#      messages.
#   5. Pull main so we have the merged beads file as the base.
#   6. Run `br update <id> --status=closed` and remove in-review /
#      auto-ok / in-progress labels.
#   7. Commit and push the beads file.
#
# The hook is best-effort: any failure prints to stderr and exits 0 so
# the Claude session continues. On success it prints a one-line summary.

set -uo pipefail

log() { echo "[bead-close] $*" >&2; }
quiet_exit() { exit 0; }

# ---- Read the hook payload ----
payload="$(cat)"
command="$(echo "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
[[ -z "$command" ]] && quiet_exit

# ---- Filter to `gh pr merge` ----
case "$command" in
  *"gh pr merge"*) ;;
  *) quiet_exit ;;
esac

# Don't run if the merge itself reported an error.
stderr="$(echo "$payload" | jq -r '.tool_response.stderr // empty' 2>/dev/null || true)"
if echo "$stderr" | grep -qiE 'error:|failed|not mergeable'; then
  log "merge command reported an error, skipping"
  quiet_exit
fi

# ---- Find the repo and require main ----
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || quiet_exit
cd "$REPO_ROOT" || quiet_exit

# Defer to outrigger if it's mid-run (see autocommit_beads_after_br.sh).
if [[ -d "$REPO_ROOT/.outrigger/lock.d" ]]; then
  log "outrigger lock active; skipping bead close"
  quiet_exit
fi

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  log "not on main (current: $branch); skipping bead update"
  quiet_exit
fi

# Required tools
for t in gh br jq git; do
  command -v "$t" >/dev/null 2>&1 || { log "$t not on PATH"; quiet_exit; }
done

# ---- Extract PR id from the command ----
# Accepts: gh pr merge 208 --squash | gh pr merge --squash 208 |
#          gh pr merge https://github.com/.../pull/208
pr_id="$(echo "$command" | tr ' ' '\n' | awk '
  /^[0-9]+$/        { print; exit }
  /github\.com.*pull\/[0-9]+/ {
    sub(/.*\/pull\//, ""); sub(/[^0-9].*/, ""); print; exit
  }
')"

# If no id was given, gh resolves the PR from the current branch.
# That branch is gone by now (post-merge), so resolve via origin's
# most recently merged PR. Best effort.
if [[ -z "$pr_id" ]]; then
  pr_id="$(gh pr list --state merged --limit 1 --json number -q '.[0].number' 2>/dev/null || true)"
fi
[[ -z "$pr_id" ]] && { log "could not determine PR id"; quiet_exit; }

# ---- Confirm the PR really merged ----
pr_json="$(gh pr view "$pr_id" --json title,headRefName,state,body,commits 2>/dev/null || true)"
[[ -z "$pr_json" ]] && { log "gh pr view $pr_id failed"; quiet_exit; }

state="$(echo "$pr_json" | jq -r '.state')"
if [[ "$state" != "MERGED" ]]; then
  log "PR #$pr_id is $state, not MERGED; skipping"
  quiet_exit
fi

# ---- Find the bead id ----
# Look in title, branch name, body, then commit headlines. Match
# anything that looks like a beads-style id: <letters>-<alnum>{2,8}, plus an
# optional dotted child suffix (hdw-3fe4.3, hdw-3fe4.3.1). The (\.[0-9]+)* is
# required: without it the regex stops at the dot and an epic-CHILD id like
# hdw-3fe4.3 collapses to the parent epic hdw-3fe4, closing the epic by mistake
# (hdw-irhq).
title="$(echo "$pr_json"  | jq -r '.title')"
brref="$(echo "$pr_json"  | jq -r '.headRefName')"
body="$(echo "$pr_json"   | jq -r '.body // ""')"
commits="$(echo "$pr_json" | jq -r '.commits[].messageHeadline' 2>/dev/null || true)"

bead_id=""
for src in "$title" "$brref" "$body" "$commits"; do
  hit="$(echo "$src" | grep -oE '[a-z]+-[a-z0-9]{2,8}(\.[0-9]+)*' | head -1 || true)"
  if [[ -n "$hit" ]]; then bead_id="$hit"; break; fi
done

[[ -z "$bead_id" ]] && { log "no bead id found in PR #$pr_id title/branch/body"; quiet_exit; }

# ---- Pull main so we close against the merged state ----
git fetch --quiet 2>/dev/null || true
git pull --quiet --ff-only 2>/dev/null || {
  log "git pull --ff-only failed; skipping"
  quiet_exit
}

# ---- Close the bead if not already closed ----
status="$(br show "$bead_id" --json 2>/dev/null | jq -r '(.[0].status // .status) // "unknown"' 2>/dev/null || echo unknown)"
if [[ "$status" == "closed" ]]; then
  log "$bead_id already closed"
  quiet_exit
fi
if [[ "$status" == "unknown" ]]; then
  log "could not read state for $bead_id"
  quiet_exit
fi

br update "$bead_id" --status=closed       >/dev/null 2>&1 || { log "br status update failed"; quiet_exit; }
br update "$bead_id" --remove-label in-review   >/dev/null 2>&1 || true
br update "$bead_id" --remove-label auto-ok     >/dev/null 2>&1 || true
br update "$bead_id" --remove-label in-progress >/dev/null 2>&1 || true

# ---- Commit and push the beads file ----
if ! git diff --quiet -- .beads/issues.jsonl; then
  repo="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "<repo>")"
  git add .beads/issues.jsonl
  git commit --quiet -m "beads: close ${bead_id} (PR #${pr_id} merged)

Auto-closed by post-merge Claude Code hook.
PR: https://github.com/${repo}/pull/${pr_id}"
  if git push --quiet 2>/dev/null; then
    log "closed $bead_id (PR #$pr_id)"
  else
    log "closed $bead_id locally; push failed (run 'git push' manually)"
  fi
fi

exit 0
