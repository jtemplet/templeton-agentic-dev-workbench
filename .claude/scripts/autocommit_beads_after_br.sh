#!/usr/bin/env bash
# Claude Code PostToolUse hook: auto-commit .beads/issues.jsonl after `br` mutations.
#
# `br` commands (update, create, close, label, dep) mutate the beads
# JSONL file but do not commit. Without this hook, every br action
# leaves the tree dirty, which then blocks outrigger's pre-flight and
# creates merge-conflict surface on feature branches.
#
# Triggered after any Bash invocation; only acts when:
#   - the command was a `br` mutation (not show/ready/list/stats/deps)
#   - we are on main
#   - .beads/issues.jsonl is the ONLY dirty tracked file
#
# Best-effort: any failure logs to stderr and exits 0.

set -uo pipefail

log() { echo "[beads-autocommit] $*" >&2; }
quiet_exit() { exit 0; }

payload="$(cat)"
command="$(echo "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
[[ -z "$command" ]] && quiet_exit

# Must be a `br` invocation: at start of line, or after a pipeline/and/separator.
# Anchored to avoid matching brew, br_history, etc.
case "$command" in
  "br "*|*"; br "*|*"&& br "*|*"| br "*|*$'\n'"br "*) ;;
  *) quiet_exit ;;
esac

# Skip only when EVERY br subcommand in the command is read-only.
#
# This replaced a substring test (`*"br show"*|*"br ready"*|...`) that asked
# whether the command line mentioned a read-only subcommand anywhere. So
# `br update x --claim && br show x` counted as read-only, the mutation went
# uncommitted, and the tree stayed dirty: the exact outcome this hook exists to
# prevent. Order made it worse, since only one of the two arrangements was wrong.
#
# An unrecognized subcommand counts as mutating. Erring toward committing is
# cheap here, because the guards below still require .beads/issues.jsonl to be
# the only dirty tracked file, so a false positive commits nothing. A false
# negative leaves real work uncommitted.
READ_ONLY_SUBCOMMANDS=" blocked capabilities changelog completions coordination"
READ_ONLY_SUBCOMMANDS+=" count graph help info lint list orphans ready robot-docs"
READ_ONLY_SUBCOMMANDS+=" scheduler schema search show stale stats status upgrade"
READ_ONLY_SUBCOMMANDS+=" version where "

# Prints the subcommand of each br invocation in $1, one per line. Splits on
# shell separators first, then skips global flags and the value of --db, which is
# the one flag that takes a separate argument.
br_subcommands() {
  echo "$1" | tr ';&|' '\n' | awk '
    {
      for (i = 1; i <= NF; i++) {
        if ($i != "br") continue
        for (j = i + 1; j <= NF; j++) {
          if ($j == "--db") { j++; continue }
          if ($j ~ /^-/) continue
          print $j
          break
        }
        break
      }
    }'
}

mutates=0
while IFS= read -r sub; do
  [[ -z "$sub" ]] && continue
  case "$READ_ONLY_SUBCOMMANDS" in
    *" $sub "*) ;;
    *) mutates=1; break ;;
  esac
done < <(br_subcommands "$command")

if (( mutates == 0 )); then
  log "no mutating br subcommand in the command; skipping"
  quiet_exit
fi

# Bail if the br command itself reported a hard error.
stderr="$(echo "$payload" | jq -r '.tool_response.stderr // empty' 2>/dev/null || true)"
if echo "$stderr" | grep -qiE '^error:|configuration error'; then
  log "br reported an error, skipping"
  quiet_exit
fi

# Locate repo and require main.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || quiet_exit
cd "$REPO_ROOT" || quiet_exit

# If outrigger is mid-run, defer to its own beads coordination. The
# wrapper anchors HEAD at iteration start; if we commit and push to
# main while the agent is working, the iteration fails with
# "main moved during iteration". outrigger holds .outrigger/lock.d/
# for the duration of a run.
if [[ -d "$REPO_ROOT/.outrigger/lock.d" ]]; then
  log "outrigger lock active; skipping auto-commit"
  quiet_exit
fi

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  log "not on main (current: $branch); skipping auto-commit"
  quiet_exit
fi

# Need git and (optionally) the beads file present.
command -v git >/dev/null 2>&1 || quiet_exit
[[ -f .beads/issues.jsonl ]] || quiet_exit

# Only act when the beads file is the sole dirty tracked file.
porcelain="$(git status --porcelain --untracked-files=no)"
[[ -z "$porcelain" ]] && quiet_exit  # nothing to commit, br was a no-op for the file

non_beads="$(echo "$porcelain" | awk 'substr($0,4) != ".beads/issues.jsonl"' | wc -l | tr -d ' ')"
if (( non_beads > 0 )); then
  log "other tracked files are dirty; not auto-committing beads"
  quiet_exit
fi

# Build a commit message from the br invocation itself.
#
# [:cntrl:] rather than a literal newline in the bracket expression. The pattern
# embedded one through $'\n', and BSD grep rejects that outright with "brackets
# ([ ]) not balanced", so on macOS this substitution produced nothing and every
# subject fell through to the generic "beads: state update" below. GNU grep
# accepts it, which is why it went unnoticed. A newline is a control character,
# so the class excludes it on both.
br_cmd="$(echo "$command" \
  | grep -oE '(^|[[:space:];&|])br[[:space:]]+[^|;&[:cntrl:]]*' \
  | head -1 \
  | sed -E 's/^[[:space:];&|]+//; s/[[:space:]]+$//')"
[[ -z "$br_cmd" ]] && br_cmd="br state update"

subject="beads: ${br_cmd#br }"
if [[ ${#subject} -gt 72 ]]; then
  subject="${subject:0:69}..."
fi

git add .beads/issues.jsonl
git commit --quiet -m "$subject

Auto-committed by post-br Claude Code hook."

if git push --quiet 2>/dev/null; then
  log "committed and pushed: $subject"
else
  log "committed locally; push failed (run 'git push' manually)"
fi

exit 0
