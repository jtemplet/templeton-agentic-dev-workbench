#!/usr/bin/env bash
# Claude Code PostToolUse hook: close the bead a merge landed.
#
# Triggered after any Bash invocation, and acts on two shapes of merge:
#
#   PR    `gh pr merge ...`, where GitHub is the authority on whether it merged.
#   LOCAL `git merge <ref>` run on main, where the repository is: the ref is an
#         ancestor of HEAD afterwards, or the merge did not happen.
#
# The local shape exists because a repository can be configured to merge without
# a PR, and because a person can merge locally on a repository that usually does
# not. Either way the bead stayed open and someone closed it by hand later,
# which is the failure this hook was written to prevent.
#
# The file name still says pr_merge. Renaming it would break the settings.json
# entry in every repository that has installed it, and the name is cheaper to
# explain than that is to fix.
#
# Reads the hook payload from stdin per Claude Code's hook contract:
#   https://docs.anthropic.com/en/docs/claude-code/hooks
#
# Flow:
#   1. Classify the command: a PR merge, a local merge, or neither.
#   2. Confirm the merge actually landed. Ask gh for MERGED, or ask git whether
#      the ref is now an ancestor of HEAD.
#   3. Resolve the bead id from the sources that shape offers, verifying every
#      candidate against the tracker and refusing to guess between two.
#   4. Close it with `bd close --reason`, then drop the workflow labels.
#   5. Commit the beads file, and push it on the PR path only. See the note
#      above the push for why the local path stops at the commit.
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

# ---- Classify the trigger ----
#
# The mid-merge subcommands are checked first and on their own. `git merge
# --abort` contains the string `git merge`, and treating it as a merge would
# close a bead for work that was just thrown away.
case "$command" in
  *"git merge --abort"*|*"git merge --quit"*|*"git merge --continue"*) quiet_exit ;;
esac

merge_kind=""
case "$command" in
  *"gh pr merge"*) merge_kind="pr" ;;
  *"git merge"*)   merge_kind="local" ;;
  *) quiet_exit ;;
esac

# Don't run if the merge itself reported a hard error.
#
# Anchored, and deliberately narrow. The pattern was 'error:|failed|not
# mergeable', unanchored, and gh writes progress and check summaries to stderr.
# A successful merge whose summary mentioned one failed check therefore matched,
# and the bead never closed. Best practice is to gate on authoritative state
# rather than on text: the `state == MERGED` check below is the real gate, and
# this is only a cheap early-out.
stderr="$(echo "$payload" | jq -r '.tool_response.stderr // empty' 2>/dev/null || true)"
if echo "$stderr" | grep -qiE '^(error|fatal)[:[:space:]]'; then
  log "merge command reported an error, skipping"
  quiet_exit
fi

# ---- Find the repo and require main ----
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || quiet_exit
cd "$REPO_ROOT" || quiet_exit

# Defer to outrigger if it's mid-run: it manages its own tracker and git state,
# and a hook closing a bead underneath it races that.
if [[ -d "$REPO_ROOT/.outrigger/lock.d" ]]; then
  log "outrigger lock active; skipping bead close"
  quiet_exit
fi

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  log "not on main (current: $branch); skipping bead update"
  quiet_exit
fi

# bd is the only tracker this hook supports. It takes no --db pin: it resolves
# one workspace per repository through the git common dir, so a run from a
# worktree reaches the same database as a run from the main checkout. That
# matters here because the branch guard above does not exclude a worktree; a
# worktree can also be on main.
# Required tools. gh only on the PR path: a local merge never asks GitHub
# anything, and a machine without gh should still close its beads.
required_tools=(bd jq git)
[[ "$merge_kind" == "pr" ]] && required_tools+=(gh)
for t in "${required_tools[@]}"; do
  command -v "$t" >/dev/null 2>&1 || { log "$t not on PATH"; quiet_exit; }
done

pr_id=""
merged_ref=""

if [[ "$merge_kind" == "pr" ]]; then
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
else
  # ---- Find what the local merge merged ----
  #
  # The command is the statement of intent, so read it first, and cut it at the
  # first shell operator: `git merge x && git push` must not offer `&&` as the
  # ref. Flags are dropped, and what survives has to look like a ref.
  merge_args="$(echo "$command" | sed -n 's/.*git merge[[:space:]]*//p' | sed 's/[;&|].*//')"
  merged_ref="$(echo "$merge_args" \
    | tr ' ' '\n' \
    | grep -vE '^-' \
    | grep -E '^[A-Za-z0-9._/@{}^~-]+$' \
    | head -1 || true)"

  # No ref in the command means git chose one (a configured upstream, or a merge
  # already in progress). The reflog records what it picked: "merge <ref>: ...".
  if [[ -z "$merged_ref" ]]; then
    merged_ref="$(git reflog -1 --format=%gs 2>/dev/null \
      | sed -n 's/^merge \([^:]*\):.*/\1/p' | head -1 || true)"
  fi
  [[ -z "$merged_ref" ]] && { log "could not tell what was merged"; quiet_exit; }

  # ---- Confirm the merge really landed ----
  #
  # The authoritative check, and the local counterpart of state == MERGED. It
  # covers the cases the stderr scan cannot: a merge that stopped on conflicts,
  # one refused by --ff-only, and one whose ref never existed. Anything short of
  # "this ref is now in main's history" closes nothing.
  if ! git rev-parse --verify --quiet "$merged_ref" >/dev/null 2>&1; then
    log "$merged_ref does not resolve; skipping"
    quiet_exit
  fi
  if ! git merge-base --is-ancestor "$merged_ref" HEAD 2>/dev/null; then
    log "$merged_ref is not an ancestor of HEAD, so the merge did not land; skipping"
    quiet_exit
  fi
fi

# ---- Find the bead id ----
#
# Four rules, in order. This hook CLOSES a bead, and a wrong close is silent and
# tedious to undo, so the design favors closing nothing over closing a guess.
#
#   1. NEVER trust the extraction. A hyphenated word is not an id: bead ids here
#      run from a short suffix to a full slug, so shape alone cannot tell them
#      apart from ordinary prose. Every candidate is verified against the tracker
#      and the regex only narrows the search.
#   2. An explicit `Bead: <id>` trailer wins outright. Inference is the fallback,
#      never the primary signal. A trailer is the one signal an author states
#      exactly, and it costs a PR template line to adopt.
#   3. Otherwise take the sources in priority order and stop at the first that
#      yields a real bead. Title and branch are specific and author-chosen; body
#      and commit headlines are where cross-references live.
#   4. FAIL CLOSED on ambiguity. When one source names two different real beads,
#      refuse and say so. A PR body routinely references a blocker or a follow-up,
#      and picking between them by position is a coin flip with a silent loser.
#
# The regex allows repeated hyphen groups so a full slug matches whole. The old
# `[a-z]+-[a-z0-9]{2,8}` stopped after one group and extracted `tadw-qg` from
# `tadw-qg-script-secrets-gate-jbg`, which resolves to nothing, so this hook could
# never close a bead in this repository. The trailing (\.[0-9]+)* keeps epic-child
# ids intact: without it hdw-3fe4.3 collapses to the parent epic hdw-3fe4 and
# closes the wrong thing (hdw-irhq).
BEAD_ID_RE='[a-z][a-z0-9]*(-[a-z0-9]+)+(\.[0-9]+)*'

# Candidates verified per source. Bounded because this runs on a PostToolUse
# hook: a long PR body can hold dozens of hyphenated words, and each candidate
# costs one bd call.
MAX_ID_CANDIDATES=25

# Prints the distinct tracker ids named in $1, longest candidate first so a full
# slug is tried before its own prefix. Empty output means the text names none.
resolve_ids_in() {
  local text="$1" candidate found id seen=""
  while IFS= read -r candidate; do
    [[ -z "$candidate" ]] && continue
    found="$(bd show "$candidate" --json 2>/dev/null || true)"
    # A missing id prints its error to stderr and leaves stdout empty.
    [[ -z "$found" ]] && continue
    id="$(echo "$found" | jq -r '((.[0].id // .id) // empty)' 2>/dev/null || true)"
    [[ -z "$id" ]] && continue
    case " $seen " in *" $id "*) continue ;; esac
    seen+=" $id"
    echo "$id"
  done < <(echo "$text" \
    | grep -oE "$BEAD_ID_RE" \
    | awk '{ print length, $0 }' \
    | sort -rn -k1,1 \
    | cut -d' ' -f2- \
    | awk '!s[$0]++' \
    | head -"$MAX_ID_CANDIDATES")
}

# The four sources, filled from whichever trigger fired. The resolution below
# reads them by name and does not care which shape produced them.
if [[ "$merge_kind" == "pr" ]]; then
  title="$(echo "$pr_json"  | jq -r '.title')"
  branchref="$(echo "$pr_json"  | jq -r '.headRefName')"
  body="$(echo "$pr_json"   | jq -r '.body // ""')"
  commits="$(echo "$pr_json" | jq -r '.commits[].messageHeadline' 2>/dev/null || true)"
else
  # A local merge has no title and no PR body. The ref name carries the same
  # signal a head branch does, and the commits it brought in carry the rest.
  #
  # HEAD@{1} is main as it stood before this merge, so the range is exactly the
  # commits the merge added. The reflog is one command old here, because this
  # hook runs immediately after the merge. Where it is unavailable (a fresh
  # clone, an expired reflog) fall back to the ref's own recent history, which
  # over-reads rather than under-reads: every candidate is verified against the
  # tracker anyway, and two real beads make it refuse rather than guess.
  title=""
  branchref="$merged_ref"
  if git rev-parse --verify --quiet 'HEAD@{1}' >/dev/null 2>&1; then
    commits="$(git log --format=%s "$merged_ref" --not 'HEAD@{1}' 2>/dev/null || true)"
    body="$(git log --format=%B "$merged_ref" --not 'HEAD@{1}' 2>/dev/null || true)"
  else
    commits="$(git log -30 --format=%s "$merged_ref" 2>/dev/null || true)"
    body="$(git log -30 --format=%B "$merged_ref" 2>/dev/null || true)"
  fi
fi

bead_id=""

# Rule 2: an explicit trailer, from the body or a commit headline.
trailer="$(printf '%s\n%s\n' "$body" "$commits" \
  | grep -iE '^[[:space:]]*bead:[[:space:]]*'"$BEAD_ID_RE" \
  | head -1 \
  | grep -oE "$BEAD_ID_RE" \
  | head -1 || true)"
if [[ -n "$trailer" ]]; then
  bead_id="$(resolve_ids_in "$trailer")"
  if [[ -z "$bead_id" ]]; then
    log "Bead: trailer names '$trailer', which the tracker does not know; ignoring it"
  else
    log "resolved $bead_id from an explicit Bead: trailer"
  fi
fi

# Rules 3 and 4: priority order, one source at a time, refusing to guess.
if [[ -z "$bead_id" ]]; then
  for src_name in title branchref body commits; do
    matches="$(resolve_ids_in "${!src_name}")"
    [[ -z "$matches" ]] && continue
    if [[ "$(echo "$matches" | wc -l | tr -d ' ')" -gt 1 ]]; then
      log "PR #$pr_id $src_name names more than one real bead: $(echo "$matches" | tr '\n' ' ')"
      log "refusing to guess which to close; add a 'Bead: <id>' trailer to the PR body"
      quiet_exit
    fi
    bead_id="$matches"
    log "resolved $bead_id from the PR $src_name"
    break
  done
fi

if [[ -z "$bead_id" ]]; then
  if [[ "$merge_kind" == "pr" ]]; then
    log "no bead id found in PR #$pr_id title/branch/body/commits"
  else
    log "no bead id found in the ref name or the commits $merged_ref brought in"
  fi
  quiet_exit
fi

# ---- Pull main so we close against the merged state ----
#
# PR path only. There the merge happened on the remote, so the local beads file
# is behind by definition and closing without pulling writes against a stale
# base. A local merge already has the merged state in the working tree, and
# pulling there would drag in unrelated remote commits behind a tracker update.
if [[ "$merge_kind" == "pr" ]]; then
  git fetch --quiet 2>/dev/null || true
  git pull --quiet --ff-only 2>/dev/null || {
    log "git pull --ff-only failed; skipping"
    quiet_exit
  }
fi

# ---- Close the bead if not already closed ----
status="$(bd show "$bead_id" --json 2>/dev/null | jq -r '(.[0].status // .status) // "unknown"' 2>/dev/null || echo unknown)"
if [[ "$status" == "closed" ]]; then
  log "$bead_id already closed"
  quiet_exit
fi
# Empty as well as "unknown". `bd show <missing-id> --json` writes its error to
# stderr and leaves stdout empty, and jq exits 0 on empty input, so the `|| echo
# unknown` above never fires and this guard read as dead code. Without the -z
# arm, an unreadable bead falls through to the close below.
if [[ -z "$status" || "$status" == "unknown" ]]; then
  log "could not read state for $bead_id"
  quiet_exit
fi

# `close`, not `update --status=closed`.
#
# A tracker can refuse the update form outright, because a terminal-state
# transition has to go through `close` for the close policy (reason, acceptance
# criteria, attribution) to be enforced. This hook once used only the update
# form, and its failure arm logs to stderr and exits 0, so against such a
# tracker the hook was inert: it ran, it logged into a stream nobody reads, and
# the bead stayed open. The update form is kept as a fallback for a build where
# `close` is missing.
if [[ "$merge_kind" == "pr" ]]; then
  close_reason="Merged in PR #${pr_id}, closed by the post-merge hook."
else
  close_reason="Merged ${merged_ref} into ${branch}, closed by the post-merge hook."
fi

if bd close "$bead_id" --reason "$close_reason" >/dev/null 2>&1; then
  :
elif bd update "$bead_id" --status=closed >/dev/null 2>&1; then
  log "closed $bead_id through the older update form; close was refused"
else
  log "could not close $bead_id: both 'bd close' and 'bd update --status=closed' failed"
  log "close it by hand: bd close $bead_id --reason '...'"
  quiet_exit
fi

bd update "$bead_id" --remove-label in-review   >/dev/null 2>&1 || true
bd update "$bead_id" --remove-label auto-ok     >/dev/null 2>&1 || true
bd update "$bead_id" --remove-label in-progress >/dev/null 2>&1 || true

# ---- Refresh the export ----
#
# There is nothing for git to carry: the bd database is gitignored, and
# .beads/issues.jsonl is a passive export bd never refreshes on its own, so
# committing it would stage a file that has been stale since the cutover.
# Refresh the export so bv and Manifest see the close, and stop. The person's
# own next commit takes the refreshed export with it.
bd export -o .beads/issues.jsonl >/dev/null 2>&1 \
  || log "export refresh failed after closing $bead_id"
log "closed $bead_id; export refreshed, nothing committed"
exit 0
