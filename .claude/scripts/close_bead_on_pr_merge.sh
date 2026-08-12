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

# Don't run if the merge itself reported a hard error.
#
# Anchored, and deliberately narrow. The pattern was 'error:|failed|not
# mergeable', unanchored, and gh writes progress and check summaries to stderr.
# A successful merge whose summary mentioned one failed check therefore matched,
# and the bead never closed. Best practice is to gate on authoritative state
# rather than on text: the `state == MERGED` check below is the real gate, and
# this is only a cheap early-out. Mirrors the anchoring in
# autocommit_beads_after_br.sh.
stderr="$(echo "$payload" | jq -r '.tool_response.stderr // empty' 2>/dev/null || true)"
if echo "$stderr" | grep -qiE '^(error|fatal)[:[:space:]]'; then
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

# Pin br to the MAIN checkout's database. Every worktree checks out its own copy
# of .beads/beads.db, so an unpinned br run from a worktree reads and writes that
# copy instead of the canonical tracker: the close would land in a throwaway
# database and the real bead would stay open. The branch guard above does not
# prevent this, because a worktree can also be on main.
#
# Duplicated from label_bead_on_skill_invocation.sh rather than extracted into a
# shared library. This is the second occurrence, and the house rule is to leave
# duplication at two and extract on the third.
GIT_COMMON="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
br_cmd=(br)
if [[ -n "$GIT_COMMON" ]]; then
  MAIN_ROOT="$(dirname "$GIT_COMMON")"
  if [[ -f "$MAIN_ROOT/.beads/beads.db" ]]; then
    br_cmd=(br --db "$MAIN_ROOT/.beads/beads.db")
  fi
fi

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
# costs one br call.
MAX_ID_CANDIDATES=25

# Prints the distinct tracker ids named in $1, longest candidate first so a full
# slug is tried before its own prefix. Empty output means the text names none.
resolve_ids_in() {
  local text="$1" candidate found id seen=""
  while IFS= read -r candidate; do
    [[ -z "$candidate" ]] && continue
    found="$("${br_cmd[@]}" show "$candidate" --json 2>/dev/null || true)"
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

title="$(echo "$pr_json"  | jq -r '.title')"
brref="$(echo "$pr_json"  | jq -r '.headRefName')"
body="$(echo "$pr_json"   | jq -r '.body // ""')"
commits="$(echo "$pr_json" | jq -r '.commits[].messageHeadline' 2>/dev/null || true)"

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
  for src_name in title brref body commits; do
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

[[ -z "$bead_id" ]] && { log "no bead id found in PR #$pr_id title/branch/body/commits"; quiet_exit; }

# ---- Pull main so we close against the merged state ----
git fetch --quiet 2>/dev/null || true
git pull --quiet --ff-only 2>/dev/null || {
  log "git pull --ff-only failed; skipping"
  quiet_exit
}

# ---- Close the bead if not already closed ----
status="$("${br_cmd[@]}" show "$bead_id" --json 2>/dev/null | jq -r '(.[0].status // .status) // "unknown"' 2>/dev/null || echo unknown)"
if [[ "$status" == "closed" ]]; then
  log "$bead_id already closed"
  quiet_exit
fi
# Empty as well as "unknown". `br show <missing-id> --json` writes its error to
# stderr and leaves stdout empty, and jq exits 0 on empty input, so the `|| echo
# unknown` above never fires and this guard read as dead code. Without the -z
# arm, an unreadable bead falls through to the close below.
if [[ -z "$status" || "$status" == "unknown" ]]; then
  log "could not read state for $bead_id"
  quiet_exit
fi

"${br_cmd[@]}" update "$bead_id" --status=closed       >/dev/null 2>&1 || { log "br status update failed"; quiet_exit; }
"${br_cmd[@]}" update "$bead_id" --remove-label in-review   >/dev/null 2>&1 || true
"${br_cmd[@]}" update "$bead_id" --remove-label auto-ok     >/dev/null 2>&1 || true
"${br_cmd[@]}" update "$bead_id" --remove-label in-progress >/dev/null 2>&1 || true

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
