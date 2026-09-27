#!/bin/sh
# Tests for guard_default_branch.sh. Each case builds throwaway repositories under a
# temp directory, feeds the hook the JSON Claude Code would send, and asserts the exit
# status: 0 allows the edit, 2 blocks it.
#
# Run: sh ~/.claude/scripts/test_guard_default_branch.sh

GUARD=${GUARD_SCRIPT:-$(cd "$(dirname "$0")" && pwd)/guard_default_branch.sh}
ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT
pass=0
fail=0

git_quiet() { git -c user.name=t -c user.email=t@t "$@" >/dev/null 2>&1; }

make_repo() { # make_repo <dir>: a repository on main with one commit
  mkdir -p "$1"
  git_quiet -C "$1" init -b main
  git_quiet -C "$1" commit --allow-empty -m init
}

# expect <name> <want> <session-dir> <stdin-json> [extra PATH prefix]
expect() {
  name=$1 want=$2 from=$3 json=$4
  got=$(cd "$from" && printf '%s' "$json" | env -u CLAUDE_PROJECT_DIR -u ALLOW_EDIT_DEFAULT_BRANCH \
    sh "$GUARD" >/dev/null 2>&1; echo $?)
  if [ "$got" = "$want" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    echo "FAIL $name: want exit $want, got $got"
  fi
}

session=$ROOT/session
other=$ROOT/other
make_repo "$session"
make_repo "$other"
git_quiet -C "$other" worktree add "$ROOT/other-wt" -b feature/x
: > "$other/tracked.txt"
: > "$ROOT/other-wt/tracked.txt"
outside=$ROOT/outside
mkdir -p "$outside"

edit() { printf '{"tool_input":{"file_path":"%s"}}' "$1"; }

expect "criterion 1: session on main, edit in another repo's feature worktree" 0 "$session" "$(edit "$ROOT/other-wt/tracked.txt")"
expect "criterion 2: edit on a default branch is blocked, whatever the session dir" 2 "$outside" "$(edit "$other/tracked.txt")"
expect "criterion 2: session on a feature worktree, edit lands on another repo's main" 2 "$ROOT/other-wt" "$(edit "$session/new.txt")"
expect "criterion 3: new file in a directory that does not exist yet, on main" 2 "$outside" "$(edit "$other/a/b/c/new.txt")"
expect "criterion 3: new file in a missing directory, on a feature branch" 0 "$session" "$(edit "$ROOT/other-wt/a/b/new.txt")"
expect "criterion 4: no file_path falls back to the session on main" 2 "$session" '{"tool_input":{}}'
expect "criterion 4: no file_path falls back to the session on a feature branch" 0 "$ROOT/other-wt" '{"tool_input":{}}'
expect "criterion 4: unparseable input falls back to the session on main" 2 "$session" 'not json'
expect "criterion 4: empty input falls back to the session on main" 2 "$session" ''
expect "notebook_path is read like file_path" 0 "$session" '{"tool_input":{"notebook_path":"'"$ROOT"'/other-wt/n.ipynb"}}'
expect "relative path resolves against the session directory" 2 "$session" '{"tool_input":{"file_path":"x/new.txt"}}'
expect "file outside any repository is allowed" 0 "$session" "$(edit "$outside/notes.txt")"

# The sed fallback: run with a PATH that has no jq.
nojq=$ROOT/nojq
mkdir -p "$nojq"
for tool in sh git sed head dirname cat env printf; do
  src=$(command -v "$tool") && [ -x "$src" ] && ln -s "$src" "$nojq/$tool"
done
got=$(cd "$session" && printf '%s' "$(edit "$ROOT/other-wt/tracked.txt")" | PATH=$nojq \
  "$nojq/env" -u CLAUDE_PROJECT_DIR "$nojq/sh" "$GUARD" >/dev/null 2>&1; echo $?)
if PATH=$nojq command -v jq >/dev/null 2>&1; then
  echo "FAIL sed fallback: jq still reachable"; fail=$((fail + 1))
elif [ "$got" = 0 ]; then
  pass=$((pass + 1))
else
  echo "FAIL sed fallback: want exit 0, got $got"; fail=$((fail + 1))
fi

echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
