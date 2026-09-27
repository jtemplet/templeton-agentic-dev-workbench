#!/bin/sh
# Block file edits made while sitting on a repository's default branch.
#
# Fires as a Claude Code PreToolUse hook on Edit|Write, which is the moment a branch
# should be created: before the first file is written, not at commit time when the
# work is already spread across the tree.
#
# Exit codes: 0 allows the call, 2 blocks it and returns the message to the model.
# Any condition this cannot evaluate (no git, not a repo, detached HEAD) allows the
# call, so the guard never blocks work it does not understand.

# Which directory's branch to read. The file being edited decides, because the session
# can sit in one checkout while the edit lands in another repository or linked
# worktree; judging that edit by the session's branch refused legitimate work and
# taught agents to write through Bash, which this guard cannot see. The hook input
# names the file as tool_input.file_path (notebook_path for NotebookEdit).
#
# With no readable path, fall back to the session: its own working directory first,
# because CLAUDE_PROJECT_DIR keeps naming the launch directory even after the session
# moves into a linked worktree, then CLAUDE_PROJECT_DIR when the working directory is
# not inside a work tree at all.
command -v git >/dev/null 2>&1 || exit 0

# A path that names a file Write is about to create may sit in directories that do
# not exist yet, so walk up to the nearest one that does.
nearest_existing_dir() {
  d=$(dirname -- "$1")
  while [ ! -d "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]; do
    d=$(dirname -- "$d")
  done
  printf '%s\n' "$d"
}

# jq when present; otherwise a narrow sed that fails open (no match, no path).
target_path() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -r '.tool_input | (.file_path // .notebook_path // empty)' 2>/dev/null
  else
    printf '%s' "$1" | sed -n \
      -e 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
      -e 's/.*"notebook_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1
  fi
}

input=
[ -t 0 ] || input=$(cat)
path=$(target_path "$input")

if [ -n "$path" ]; then
  case "$path" in
    /*) ;;
    *) path=$PWD/$path ;;
  esac
  dir=$(nearest_existing_dir "$path")
elif git -C "$PWD" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  dir=$PWD
else
  dir=${CLAUDE_PROJECT_DIR:-$PWD}
fi

git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0

# Detached HEAD is not a branch to protect.
[ "$branch" = "HEAD" ] && exit 0

# The repo's own default, falling back to the two conventional names. Reading
# origin/HEAD means a repo whose default is neither "main" nor "master" is still
# guarded, and a repo where "main" is not the default is not guarded by accident.
default=$(git -C "$dir" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
default=${default#origin/}

case "$branch" in
  "$default"|main|master) ;;
  *) exit 0 ;;
esac

# An escape hatch for the times editing the default branch is the intent.
[ -n "$ALLOW_EDIT_DEFAULT_BRANCH" ] && exit 0

cat >&2 <<MSG
Refusing to edit files while on "$branch", this repository's default branch.

Create a branch first, then retry the edit. Uncommitted work carries across:

    git checkout -b <type>/<scope>/<short-description>

To edit the default branch deliberately, re-run with ALLOW_EDIT_DEFAULT_BRANCH=1
set, or ask the user to unset this guard.
MSG
exit 2
