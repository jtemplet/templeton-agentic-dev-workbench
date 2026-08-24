#!/usr/bin/env bash
# tadw - test suite for the two hooks in .claude/scripts/
#
# No dependencies beyond what the hooks themselves need (bash, git, jq, coreutils).
# Run with:
#   ./hooks/test-claude-scripts.sh            # every case
#   ./hooks/test-claude-scripts.sh close      # cases whose name matches "close"
#
# WHY THIS EXISTS. These two scripts commit, push, close beads, and label
# them. They are the code here most able to do damage unasked, and until this
# suite they had no automated coverage at all. A fresh-eyes pass over 9ce0f8a
# found eight defects; f8259ea fixed seven of them with manual verification and
# no pinned tests. Two of those were guards that READ as active and never fired,
# which is the class a test catches and a careful reading does not.
#
# So every one of those fixes has a case here, and each case was OBSERVED to
# fail against a copy of the script with that one fix reverted. Point
# TADW_HOOK_SCRIPTS_DIR at a directory of modified copies to repeat that.
#
# Three of those cases are gone with the tracker cutover, because their subject
# is gone: fix 5 lived in autocommit_beads_after_br.sh, which was a workaround
# for a tracker that wrote its state into a git-tracked export, and fixes 3 and
# 7 both turned on the --db pin that bd does not take. What replaced them are
# worktree cases asserting that a hook run from a worktree still reaches the
# canonical tracker, which is the behavior the pin existed to protect.
#
# HOW A CASE RUNS. Three rules, and the third is a deliberate departure from
# what the bead specified:
#
#   1. FAKE ON PATH, never inside the script. Each case prepends a directory of
#      stubs to PATH, so the shipped code runs unmodified, with no test-only
#      branch in it. Every stub records the argv it received, which is how a
#      case asserts what the hook TRIED to do rather than what it achieved.
#
#   2. NOTHING LEAVES THE SANDBOX. Every case runs in a throwaway repository
#      under a temp directory. No case reads or writes the real tracker, and no
#      case can reach a network: the git stub refuses any push whose remote is
#      not a local path, and the repositories that push have a bare repo on disk
#      as their origin.
#
#   3. git IS REAL, BEHIND A RECORDING STUB. The bead asked for a git stub
#      alongside the tracker and gh. A stub that answers rev-parse, status --porcelain,
#      merge-base --is-ancestor, branch --show-current and log is a git
#      reimplementation, and the cases would then prove that reimplementation
#      right rather than the hook. Since the guards most worth testing are
#      exactly the git-dependent ones (am I on main, is the tree dirty, did the
#      merge land), the stub records argv, blocks a non-local push, and execs
#      the real git. The criterion's intent holds in full: within a case, git,
#      bd and gh all resolve to this harness's own stubs, and case 0 asserts it.
#
# WHAT IS ASSERTED, in descending order of value: the exit status, which is
# always 0 because every failure path is designed to let the session continue;
# the recorded argv of bd and git; then the stderr log lines.

set -uo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$HOOKS_DIR")"
SCRIPTS_DIR="${TADW_HOOK_SCRIPTS_DIR:-$REPO_ROOT/.claude/scripts}"
FILTER="${1:-}"

CLOSE="$SCRIPTS_DIR/close_bead_on_pr_merge.sh"
LABEL="$SCRIPTS_DIR/label_bead_on_skill_invocation.sh"

REAL_GIT="$(command -v git)"
# Resolved with pwd -P. On macOS mktemp hands back /var/..., which is a symlink
# to /private/var/..., and git reports the resolved form. A --db assertion built
# from the unresolved path then never matches what the hook actually ran.
SANDBOX="$(cd "$(mktemp -d)" && pwd -P)"
BINDIR="$SANDBOX/bin"
trap 'rm -rf "$SANDBOX"' EXIT

[[ -n "$SANDBOX" && -d "$SANDBOX" ]] || { echo "FATAL: no sandbox directory" >&2; exit 2; }

passed=0
failed=0
current_case=""

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

case_start() {
  current_case="$1"
  if [[ -n "$FILTER" && "$current_case" != *"$FILTER"* ]]; then
    return 1
  fi
  echo
  echo "$current_case"
  return 0
}

ok()  { echo "  ok   - $1"; passed=$((passed + 1)); }
nope() {
  echo "  FAIL - $1"
  # Truncated: a failing assertion against a long file would otherwise print the
  # whole file and bury every other result.
  [[ -n "${2:-}" ]] && echo "         saw: $(echo "$2" | cut -c1-300)"
  failed=$((failed + 1))
}

# File and string forms are separate because the file form reads its subject
# TWICE, once to match and once to report. A process substitution can only be
# read once, so passing one here reports an empty "saw" line and, worse, fails
# the existence test and reports a pass as a failure.
assert_match() {  # assert_match <file> <pattern> <label>
  local body; body="$(cat "$1" 2>/dev/null || true)"
  assert_match_str "$body" "$2" "$3"
}

assert_no_match() {  # assert_no_match <file> <pattern> <label>
  local body; body="$(cat "$1" 2>/dev/null || true)"
  assert_no_match_str "$body" "$2" "$3"
}

assert_match_str() {  # assert_match_str <string> <pattern> <label>
  if echo "$1" | grep -qE -- "$2"; then ok "$3"
  else nope "$3" "$(echo "$1" | tr '\n' '|')"; fi
}

assert_no_match_str() {  # assert_no_match_str <string> <pattern> <label>
  if echo "$1" | grep -qE -- "$2"; then nope "$3" "$(echo "$1" | tr '\n' '|')"
  else ok "$3"; fi
}

assert_eq() {  # assert_eq <actual> <expected> <label>
  if [[ "$1" == "$2" ]]; then ok "$3"; else nope "$3" "$1 (wanted $2)"; fi
}

# ---------------------------------------------------------------------------
# The sandbox guard
# ---------------------------------------------------------------------------
#
# EVERY git command this suite runs against a case repository goes through sgit,
# and sgit aborts unless the target is inside $SANDBOX.
#
# This is not belt-and-braces. `git -C ""` is not an error: it silently stays in
# the current directory, which is the repository under test. An early version of
# new_repo died under `set -u` and returned an empty path, and the helpers below
# then created four branches, committed, and registered two worktrees in the real
# checkout, on a branch the author had not asked for. Nothing was pushed and it
# was recoverable, but a test suite that writes to the repository it is testing
# is the one failure mode that must be impossible rather than unlikely.
sandbox_path() {
  case "${1:-}" in
    "$SANDBOX"/?*) return 0 ;;
  esac
  echo "FATAL: refusing to write '${1:-<empty>}': outside $SANDBOX" >&2
  exit 2
}

sgit() {
  local dir="${1:-}"
  shift
  case "$dir" in
    "$SANDBOX"/?*) ;;
    *)
      echo "FATAL: refusing to run git in '${dir:-<empty>}': outside $SANDBOX" >&2
      exit 2 ;;
  esac
  # The one place the real binary is named with -C. Everything else goes through
  # this function, which is what makes the guard above unavoidable.
  "$REAL_GIT" -C "$dir" "$@"
}

# ---------------------------------------------------------------------------
# The stubs
# ---------------------------------------------------------------------------
#
# bd models just enough tracker to drive the hooks: it knows the ids in
# BD_KNOWN, records every invocation, and appends to the beads file on a
# successful CLOSE so the close hook's "is the beads file dirty" check has
# something real to see.
#
# A label deliberately writes nothing there. Real `bd update --add-label`
# writes the Dolt database, and .beads/issues.jsonl only changes when
# `bd export` rewrites it. A stub that dirtied the file on every label would
# make the label hook's own "is the export already modified" test always true,
# which is the exact condition refresh_export now turns on.
#
# BD_ID_PREFIX models bd resolving a short id to a full one: `bd show zkc.5`
# answers with id fathom-zkc.5. The hook must then label the RESOLVED id, not
# the candidate string it guessed.
#
# bd takes no --db: it resolves one workspace per repository through the git
# common dir. That is what the hooks' worktree handling turns on, so a stub that
# accepted --db would hide a real regression.
#
# BD_SHOW_FAIL_AFTER is the interesting knob. `bd show <id> --json` on a
# transient failure writes to stderr and leaves stdout EMPTY, and jq exits 0 on
# empty input, which is why the close hook's status guard read as active for
# months while never firing. Letting the first N shows succeed and the rest
# return nothing reproduces that exactly: resolution finds the bead, and the
# later status read comes back empty.
write_stubs() {
  mkdir -p "$BINDIR"

  cat > "$BINDIR/bd" <<'STUB'
#!/usr/bin/env bash
# Two logs on purpose. BD_LOG keeps the argv verbatim; BD_CALLS is what a case
# anchors a subcommand pattern against.
echo "$*" >> "${BD_LOG:-/dev/null}"
echo "$*" >> "${BD_CALLS:-/dev/null}"
sub="${1:-}"; id="${2:-}"

known() { case " ${BD_KNOWN:-} " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

case "$sub" in
  show)
    known "$id" || { echo '{"error":"no issues found"}' >&2; exit 1; }
    if [[ -n "${BD_SHOW_FAIL_AFTER:-}" ]]; then
      n=$(( $(cat "${BD_SHOW_COUNT_FILE:-/dev/null}" 2>/dev/null || echo 0) + 1 ))
      echo "$n" > "${BD_SHOW_COUNT_FILE:-/dev/null}" 2>/dev/null
      if (( n > BD_SHOW_FAIL_AFTER )); then
        echo "transient read failure" >&2   # stdout stays empty, as bd does
        exit 0
      fi
    fi
    printf '[{"id":"%s","status":"open","labels":[%s]}]\n' "${BD_ID_PREFIX:-}$id" "${BD_LABELS_JSON:-}"
    ;;
  close)
    case "${BD_CLOSE_MODE:-ok}" in
      refuse-close|refuse-both)
        echo "Error: refusing to close via this form" >&2; exit 1 ;;
    esac
    echo "closed $id" >> "$BD_REPO/.beads/issues.jsonl"
    ;;
  export)
    # Real `bd export -o <file>` REWRITES that file, which is the whole reason
    # a refresh dirties the tree. A stub that wrote nothing made every
    # "left the tree clean" assertion pass whether or not the hook exported.
    out=""; prev=""
    for a in "$@"; do [[ "$prev" == "-o" ]] && out="$a"; prev="$a"; done
    [[ -n "$out" ]] && printf '{"id":"exported-at-%s"}\n' "$(date +%s)" > "$out"
    ;;
  comments) : ;;
  update)
    case "$*" in
      *--status=closed*)
        [[ "${BD_CLOSE_MODE:-ok}" == "refuse-both" ]] && exit 1
        echo "closed $id" >> "$BD_REPO/.beads/issues.jsonl" ;;
      *--add-label*) : ;;   # the label lands in the database, never in the export
    esac
    ;;
esac
exit 0
STUB

  cat > "$BINDIR/gh" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "${GH_LOG:-/dev/null}"
case "$*" in
  *"pr view"*)  cat "${GH_PR_JSON:-/dev/null}" ;;
  *"repo view"*) echo "owner/repo" ;;
  *"pr list"*)  echo "" ;;
esac
exit 0
STUB

  # Records, refuses to leave the machine, then delegates to the real git.
  cat > "$BINDIR/git" <<STUB
#!/usr/bin/env bash
echo "\$*" >> "\${GIT_LOG:-/dev/null}"
if [[ "\${1:-}" == "push" || "\${1:-}" == "fetch" || "\${1:-}" == "pull" ]]; then
  url="\$("$REAL_GIT" remote get-url origin 2>/dev/null || true)"
  case "\$url" in
    ""|/*|file:*) ;;
    *) echo "test harness: refusing to \$1 to a non-local remote (\$url)" >&2; exit 1 ;;
  esac
fi
exec "$REAL_GIT" "\$@"
STUB

  chmod +x "$BINDIR/bd" "$BINDIR/gh" "$BINDIR/git"
}

# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

# new_repo <name> [with-origin] -> echoes the path
new_repo() {
  # Declared one per line on purpose. macOS ships bash 3.2, which evaluates
  # every right-hand side of a multi-name `local` before assigning any of them,
  # so `local a="$1" b="$SANDBOX/$a"` dies under `set -u` with "a: unbound
  # variable". The shipped hooks are safe because their multi-name locals only
  # read positional parameters, never an earlier name from the same statement.
  local name="$1"
  local origin="${2:-}"
  local dir="$SANDBOX/$name"
  rm -rf "$dir"; mkdir -p "$dir/.beads"
  sgit "$dir" init --quiet -b main
  sgit "$dir" config user.email hooks@example.test
  sgit "$dir" config user.name "Hook Suite"
  echo '{"id":"seed"}' > "$dir/.beads/issues.jsonl"
  printf '{"backend":"dolt"}\n' > "$dir/.beads/metadata.json"
  sgit "$dir" add -A
  sgit "$dir" commit --quiet -m "seed"
  if [[ "$origin" == "with-origin" ]]; then
    sandbox_path "$SANDBOX/$name-origin.git"
    "$REAL_GIT" init --quiet --bare "$SANDBOX/$name-origin.git"
    sgit "$dir" remote add origin "$SANDBOX/$name-origin.git"
    sgit "$dir" push --quiet -u origin main
  fi
  echo "$dir"
}

# add_branch <repo> <branch> <commit-subject>
add_branch() {
  local dir="$1" branch="$2" subject="$3"
  sgit "$dir" checkout --quiet -b "$branch"
  echo "work" >> "$dir/file.txt"
  sgit "$dir" add -A
  sgit "$dir" commit --quiet -m "$subject"
  sgit "$dir" checkout --quiet main
}

# on_branch <repo> <branch>: create it and STAY there, unlike add_branch which
# returns to main. Branch-derived resolution can only be tested from the branch.
on_branch() {
  local dir="$1" branch="$2"
  sgit "$dir" checkout --quiet -b "$branch"
  echo "work" >> "$dir/file.txt"
  sgit "$dir" add -A
  sgit "$dir" commit --quiet -m "work on $branch"
}

payload() {  # payload <event> <command> [stderr] [skill] [args]
  jq -n --arg e "${1:-}" --arg c "${2:-}" --arg err "${3:-}" \
        --arg s "${4:-}" --arg a "${5:-}" \
    '{hook_event_name:$e, tool_input:({command:$c} + (if $s == "" then {} else {skill:$s, args:$a} end)),
      tool_response:{stderr:$err}}'
}

# run_hook <script> <repo> <payload>; sets HOOK_CODE and writes .hookout/.hookerr
run_hook() {
  local script="$1" repo="$2" body="$3"
  sandbox_path "$repo"
  : > "$repo/.bdlog"; : > "$repo/.bdcalls"; : > "$repo/.gitlog"; : > "$repo/.ghlog"
  ( cd "$repo" \
    && printf '%s' "$body" \
     | PATH="$BINDIR:$PATH" \
       BD_REPO="$repo" BD_LOG="$repo/.bdlog" BD_CALLS="$repo/.bdcalls" \
       GIT_LOG="$repo/.gitlog" \
       GH_LOG="$repo/.ghlog" BD_SHOW_COUNT_FILE="$repo/.bdshows" \
       bash "$script" > "$repo/.hookout" 2> "$repo/.hookerr" )
  HOOK_CODE=$?
}

head_sha()     { sgit "$1" rev-parse HEAD; }

write_stubs

# ---------------------------------------------------------------------------
# Case 0: the sandbox itself
# ---------------------------------------------------------------------------

if case_start "sandbox: bd, git and gh resolve to the harness stubs"; then
  R="$(new_repo sandbox)"
  # bd is in here for a reason: its stub was added without a chmod, so it fell
  # through to the real /opt/homebrew/bin/bd and ran against the sandbox. The
  # case that caught it failed looking exactly like a hook bug.
  out="$(cd "$R" && PATH="$BINDIR:$PATH" bash -c 'command -v bd; command -v git; command -v gh')"
  [[ "$(echo "$out" | grep -c "^$BINDIR/")" == "3" ]] \
    && ok "all three resolve inside the harness bin" \
    || nope "all three resolve inside the harness bin" "$out"

  # The guard that keeps every git command inside the sandbox. Run in a
  # subshell, because firing it exits the suite, which is the point: a case that
  # has lost track of its repository must not carry on against the real one.
  guard_out="$( ( sgit "" status ) 2>&1 )"; guard_code=$?
  assert_eq "$guard_code" 2 "an empty path aborts the suite"
  assert_match_str "$guard_out" "refusing to run git in '<empty>'" "and says why"
  guard_out="$( ( sgit "$REPO_ROOT" status ) 2>&1 )"; guard_code=$?
  assert_eq "$guard_code" 2 "the repository under test is refused too"

  # A push to a remote that is not a local path must be refused, so no case can
  # reach a network even if a hook decides to push.
  sgit "$R" remote add origin https://example.invalid/x.git
  ( cd "$R" && PATH="$BINDIR:$PATH" git push --quiet origin main ) > /dev/null 2>"$R/.pusherr"
  assert_match "$R/.pusherr" "refusing to push to a non-local remote" "a non-local push is blocked"
fi

# ---------------------------------------------------------------------------
# close_bead_on_pr_merge.sh, PR path
# ---------------------------------------------------------------------------

pr_json() {  # pr_json <file> <title> <body> [headRef]
  jq -n --arg t "$2" --arg b "$3" --arg h "${4:-feature/x}" \
    '{title:$t, headRefName:$h, state:"MERGED", body:$b, commits:[{messageHeadline:"work"}]}' > "$1"
}

if case_start "close/pr: a full slug id in the title is closed whole"; then
  # f8259ea fix 1. The old regex stopped after one hyphen group and extracted
  # `tadw-qg` from `tadw-qg-script-secrets-gate-jbg`, which resolves to nothing,
  # so this hook could never close a bead in this repository.
  R="$(new_repo c1 with-origin)"
  pr_json "$SANDBOX/pr.json" "Add the gate (tadw-qg-script-secrets-gate-jbg)" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BD_KNOWN="tadw-qg-script-secrets-gate-jbg" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_match "$R/.bdcalls" "^close tadw-qg-script-secrets-gate-jbg" "closed the whole id"
  assert_match "$R/.bdcalls" "^export -o" "refreshed the export"
  assert_no_match "$R/.gitlog" "^commit" "committed nothing"
fi

if case_start "close/pr: two real beads in the body and no trailer refuses"; then
  R="$(new_repo c2 with-origin)"
  pr_json "$SANDBOX/pr.json" "No id here" "Blocks tadw-alpha-one and follows tadw-beta-two"
  export GH_PR_JSON="$SANDBOX/pr.json" BD_KNOWN="tadw-alpha-one tadw-beta-two" BD_LABELS_JSON=""
  before="$(head_sha "$R")"
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_no_match "$R/.bdcalls" "^(close|update .* --status=closed)" "closed neither"
  assert_match "$R/.hookerr" "refusing to guess" "said it refused"
  assert_eq "$(head_sha "$R")" "$before" "no commit"
fi

if case_start "close/pr: a Bead trailer beats the title"; then
  R="$(new_repo c3 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" "Bead: tadw-beta-two"
  export GH_PR_JSON="$SANDBOX/pr.json" BD_KNOWN="tadw-alpha-one tadw-beta-two" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_match "$R/.bdcalls" "^close tadw-beta-two" "closed the trailer id"
  assert_no_match "$R/.bdcalls" "^close tadw-alpha-one" "left the title id alone"
fi

if case_start "close/pr: an empty status read closes nothing"; then
  # f8259ea fix 2. `bd show` on a transient failure writes to stderr and leaves
  # stdout empty; jq exits 0 on empty input, so `|| echo unknown` never fired
  # and an unreadable bead fell through to the close.
  R="$(new_repo c4 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON="" \
         BD_SHOW_FAIL_AFTER=1
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  unset BD_SHOW_FAIL_AFTER
  assert_no_match "$R/.bdcalls" "^(close|update .* --status=closed)" "closed nothing"
  assert_match "$R/.hookerr" "could not read state" "said why"
fi

if case_start "close/pr: a failed check in stderr does not block the close"; then
  # f8259ea fix 4. The sniff matched an unanchored `failed`, so a successful
  # merge whose check summary mentioned one failed check skipped the close.
  R="$(new_repo c5 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" \
    "$(payload PostToolUse 'gh pr merge 7 --squash' 'Checks: 4 passed, 1 failed. Merged.')"
  assert_match "$R/.bdcalls" "^close tadw-alpha-one" "still closed"
fi

if case_start "close/pr: an error in stderr does block the close"; then
  R="$(new_repo c6 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7' 'error: not mergeable')"
  assert_no_match "$R/.bdcalls" "^close" "closed nothing"
  assert_match "$R/.hookerr" "reported an error" "said why"
fi

if case_start "close/worktree: a close from a worktree reaches the tracker unpinned"; then
  # bd resolves one workspace per repository through the git common dir, so a
  # close from a worktree lands in the canonical tracker with no --db pin. A
  # --db here would mean the hook grew a pin that bd does not take.
  MAIN="$(new_repo c7 with-origin)"
  WT="$SANDBOX/c7-wt"
  sgit "$MAIN" worktree add --force --quiet "$WT" main
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$WT" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_match "$WT/.bdcalls" "^close tadw-alpha-one" "closed the bead from the worktree"
  assert_no_match "$WT/.bdlog" "[-][-]db" "sent no --db"
fi

# ---------------------------------------------------------------------------
# close_bead_on_pr_merge.sh, local-merge path
# ---------------------------------------------------------------------------

if case_start "close/local: a merged branch closes the bead it names"; then
  R="$(new_repo l1 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/shell" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/shell"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge --ff-only feature/tadw-alpha-one/shell')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_match "$R/.bdcalls" "^close tadw-alpha-one" "closed it"
  assert_match "$R/.bdcalls" "^export -o" "refreshed the export"
fi

if case_start "close/local: the close neither commits nor pushes"; then
  # A local merge is not on the remote yet. Pushing here would carry the whole
  # merged branch, and in a repository that deploys on a push to main that turns
  # "I merged locally" into "I deployed". There is nothing to commit either: the
  # bd database is gitignored and the export is refreshed in place.
  R="$(new_repo l2 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/x"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  assert_no_match "$R/.gitlog" "^push" "no push"
  assert_no_match "$R/.gitlog" "^commit" "no commit"
  assert_match "$R/.hookerr" "nothing committed" "said so"
fi

if case_start "close/local: git merge --abort closes nothing"; then
  R="$(new_repo l3 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge --abort')"
  assert_eq "$(wc -c < "$R/.bdcalls" | tr -d ' ')" 0 "bd was never called"
fi

if case_start "close/local: a merge that did not land closes nothing"; then
  R="$(new_repo l4 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  assert_eq "$(wc -c < "$R/.bdcalls" | tr -d ' ')" 0 "bd was never called"
  assert_match "$R/.hookerr" "did not land" "said why"
fi

if case_start "close/local: a refused close falls back to the update form"; then
  R="$(new_repo l5 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/x"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON="" BD_CLOSE_MODE=refuse-close
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  unset BD_CLOSE_MODE
  assert_match "$R/.bdcalls" "^update tadw-alpha-one --status=closed" "used the older form"
  assert_match "$R/.bdcalls" "^export -o" "still refreshed the export"
fi

if case_start "close/local: both close forms failing commits nothing"; then
  R="$(new_repo l6 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/x"
  before="$(head_sha "$R")"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON="" BD_CLOSE_MODE=refuse-both
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  unset BD_CLOSE_MODE
  assert_eq "$HOOK_CODE" 0 "exits 0 so the session continues"
  assert_eq "$(head_sha "$R")" "$before" "no commit"
  assert_match "$R/.hookerr" "close it by hand" "named the manual command"
fi

if case_start "close/local: a branch naming no known bead closes nothing"; then
  R="$(new_repo l7 with-origin)"; add_branch "$R" "feature/nothing-here/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/nothing-here/x"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/nothing-here/x')"
  assert_no_match "$R/.bdcalls" "^close" "closed nothing"
  assert_match "$R/.hookerr" "no bead id found" "said so"
fi

# ---------------------------------------------------------------------------
# label_bead_on_skill_invocation.sh
# ---------------------------------------------------------------------------

marker_dir() { echo "$1/.git/pending-bead-labels"; }

write_report() {  # write_report <repo> <critical> <high> <deferred>
  mkdir -p "$1/.gstack/qa-reports"
  cat > "$1/.gstack/qa-reports/qa-report-x-2026-01-01.md" <<EOF
| Severity | Count |
|---|---|
| Critical | $2 |
| High | $3 |
| Deferred | $4 |
EOF
}

if case_start "label/stop: the marker filename decides the label, not qa-d"; then
  # f8259ea fix 6. Stop hardcoded qa-d while the filename already carried the
  # label, so a second gate-mode entry would be mislabeled in silence.
  R="$(new_repo b1 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\nqa\n' "$(date +%s)" > "$M/reviewed__tadw-alpha-one"
  sleep 1; write_report "$R" 0 0 0
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$R/.bdcalls" "--add-label reviewed" "applied the marker's label"
  assert_no_match "$R/.bdcalls" "--add-label qa-d" "did not fall back to qa-d"
fi

if case_start "label/stop: a failing report earns no label"; then
  R="$(new_repo b2 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\nqa\n' "$(date +%s)" > "$M/qa-d__tadw-alpha-one"
  sleep 1; write_report "$R" 2 1 0
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.bdcalls" "--add-label" "no label"
  assert_match "$R/.hookerr" "QA gate not met" "said why"
fi

if case_start "label/stop: a marker past its TTL is abandoned"; then
  R="$(new_repo b3 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\nqa\n' "$(( $(date +%s) - 99999 ))" > "$M/qa-d__tadw-alpha-one"
  sleep 1; write_report "$R" 0 0 0
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.bdcalls" "--add-label" "no label"
  assert_match "$R/.hookerr" "abandoning stale marker" "said why"
  [[ ! -e "$M/qa-d__tadw-alpha-one" ]] && ok "removed the marker" || nope "removed the marker"
fi

# /quality-gates writes <git-dir>/quality-gates-report.json with its verdict.
write_qg_report() {  # write_qg_report <repo> <verdict>
  jq -n --arg v "$2" '{version:1, verdict:$v, gates:[]}' > "$1/.git/quality-gates-report.json"
}

qg_marker() {  # qg_marker <repo> <bead> [created-epoch]
  local M; M="$(marker_dir "$1")"; mkdir -p "$M"
  printf '%s\n%s\ntadw:quality-gates\n' "${3:-$(date +%s)}" "$2" > "$M/qa-d__$2"
}

if case_start "label/pre: quality-gates drops a gate marker and injects nothing"; then
  # tadw-ci8. The skill writes a machine-readable verdict, so the label waits
  # for Stop to read it rather than for Claude to remember an instruction.
  R="$(new_repo q1 with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:quality-gates' 'tadw-alpha-one')"
  assert_no_match "$R/.bdcalls" "--add-label" "applied no label up front"
  [[ ! -s "$R/.hookout" ]] && ok "injected nothing" || nope "injected nothing" "$(cat "$R/.hookout")"
  M="$(marker_dir "$R")"
  [[ -f "$M/qa-d__tadw-alpha-one" ]] && ok "dropped the marker" || nope "dropped the marker"
  assert_match_str "$(sed -n 3p "$M/qa-d__tadw-alpha-one" 2>/dev/null)" "^tadw:quality-gates$" "the marker names the skill"
fi

if case_start "label/stop: a PASS quality-gates report newer than the marker labels qa-d"; then
  R="$(new_repo q2 with-origin)"
  qg_marker "$R" tadw-alpha-one
  sleep 1; write_qg_report "$R" PASS
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$R/.bdcalls" "--add-label qa-d" "labeled it qa-d"
  assert_match "$R/.hookerr" "verdict PASS" "said why"
  [[ ! -e "$(marker_dir "$R")/qa-d__tadw-alpha-one" ]] && ok "cleared the marker" || nope "cleared the marker"
fi

if case_start "label/stop: any quality-gates verdict but PASS earns no label"; then
  for v in FAIL INCOMPLETE "NO GATES RAN"; do
    R="$(new_repo "q3-${v// /-}" with-origin)"
    qg_marker "$R" tadw-alpha-one
    sleep 1; write_qg_report "$R" "$v"
    export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
    run_hook "$LABEL" "$R" "$(payload Stop '')"
    assert_no_match "$R/.bdcalls" "--add-label" "no label on $v"
    [[ ! -e "$(marker_dir "$R")/qa-d__tadw-alpha-one" ]] && ok "cleared the marker on $v" || nope "cleared the marker on $v"
  done
fi

if case_start "label/stop: a quality-gates report older than the marker means the run is still going"; then
  R="$(new_repo q4 with-origin)"
  write_qg_report "$R" PASS
  sleep 1; qg_marker "$R" tadw-alpha-one
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.bdcalls" "--add-label" "no label from a stale report"
  [[ -e "$(marker_dir "$R")/qa-d__tadw-alpha-one" ]] && ok "kept the marker" || nope "kept the marker"
fi

if case_start "label/stop: a quality-gates marker ignores a passing /qa report"; then
  # The marker's skill picks the reader. A browser QA report written by a
  # concurrent /qa run says nothing about the gates.
  R="$(new_repo q5 with-origin)"
  qg_marker "$R" tadw-alpha-one
  sleep 1; write_report "$R" 0 0 0
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.bdcalls" "--add-label" "no label from the wrong artifact"
  [[ -e "$(marker_dir "$R")/qa-d__tadw-alpha-one" ]] && ok "kept the marker" || nope "kept the marker"
fi

if case_start "label/stop: a /qa marker still reads the .gstack report"; then
  R="$(new_repo q6 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\ngstack:qa\n' "$(date +%s)" > "$M/qa-d__tadw-alpha-one"
  sleep 1; write_report "$R" 0 0 0
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$R/.bdcalls" "--add-label qa-d" "labeled it qa-d"
fi

if case_start "label/pre: apply mode labels the bead immediately"; then
  R="$(new_repo b4 with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$R/.bdcalls" "--add-label reviewed" "labeled it reviewed"
  assert_no_match "$R/.gitlog" "^commit" "committed nothing"
fi

if case_start "label/pre: feature-development defers implemented to the run's end"; then
  # "implemented" is an outcome. A /build run that stops at Ground must not
  # carry it, so the hook injects the instruction and applies nothing itself.
  R="$(new_repo b4i with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:feature-development' 'tadw-alpha-one')"
  assert_no_match "$R/.bdcalls" "--add-label" "applied no label up front"
  jq -e . "$R/.hookout" >/dev/null 2>&1 && ok "the JSON parses" || nope "the JSON parses"
  assert_match "$R/.hookout" "bd update tadw-alpha-one --add-label implemented" "named the command"
  assert_match "$R/.hookout" "Feature complete" "gated on the run's own report"
  assert_match "$R/.hookerr" "deferred implemented" "said so"
fi

if case_start "label/prompt: a typed /tadw:build resolves to feature-development"; then
  R="$(new_repo b4p with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(jq -n '{hook_event_name:"UserPromptSubmit", prompt:"/tadw:build tadw-alpha-one"}')"
  assert_no_match "$R/.bdcalls" "--add-label" "applied no label up front"
  assert_match "$R/.hookout" "bd update tadw-alpha-one --add-label implemented" "named the command"
  assert_match "$R/.hookout" '"hookEventName": *"UserPromptSubmit"' "labeled its output with the right event"
fi

if case_start "label/pre: an already-labeled bead is left alone"; then
  R="$(new_repo b5 with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON='"reviewed"'
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_no_match "$R/.bdcalls" "--add-label" "no second label"
  assert_match "$R/.hookerr" "already labeled" "said so"
fi

# ---------------------------------------------------------------------------
# Bead resolution from the branch
#
# The class of defect these pin cost a whole build-and-ship session on
# 2026-08-22: three skills ran in ~/Dev/fathom on an outrigger branch and the
# bead shipped carrying none of their labels. Nothing in the session said so.
# The candidate pattern required at least one hyphen and rejected a leading
# digit, and every short bead id in that repository is hyphen-free, so the only
# candidate an outrigger branch ever offered was its slug.
# ---------------------------------------------------------------------------

if case_start "label/resolve: an outrigger branch resolves its hyphen-free short id"; then
  # THE regression case for that outage. zkc.5 carries no hyphen and ends in a
  # digit, so the old pattern never offered it at all.
  R="$(new_repo r1 with-origin)"
  on_branch "$R" "outrigger/zkc.5/rank-beads-and-reminders-deterministical"
  # bd answers a short id with the full one, and the hook must label what bd
  # returned rather than the string it guessed.
  export BD_KNOWN="zkc.5" BD_LABELS_JSON="" BD_ID_PREFIX="fathom-"
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_match "$R/.bdcalls" "^show zkc\.5" "probed the short id"
  assert_match "$R/.bdcalls" "^update fathom-zkc\.5 --add-label reviewed" "labeled the id bd resolved to"
  unset BD_ID_PREFIX
fi

if case_start "label/resolve: an ordinary hyphenated id still resolves, with and without a third segment"; then
  # The widened pattern must break nothing the existing branch cases cover.
  for b in "feature/tadw-alpha-one/x" "feature/tadw-alpha-one"; do
    R="$(new_repo "r2-${b//\//-}" with-origin)"
    on_branch "$R" "$b"
    export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
    run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
    assert_match "$R/.bdcalls" "^update tadw-alpha-one --add-label reviewed" "resolved from $b"
  done
fi

if case_start "label/resolve: a branch naming no bead resolves nothing and says so"; then
  R="$(new_repo r3 with-origin)"   # stays on main
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_eq "$HOOK_CODE" 0 "exits 0 anyway, so the skill still runs"
  assert_no_match "$R/.bdcalls" "--add-label" "labeled nothing"
  assert_match "$R/.hookerr" "no candidate resolved to a bead" "said so"
fi

if case_start "label/resolve: the positional segment beats a longer slug that also resolves"; then
  # Both resolve, and the slug is the LONGER token, so longest-first alone would
  # pick it. Segment two is the id outrigger put there on purpose.
  R="$(new_repo r4 with-origin)"
  on_branch "$R" "outrigger/tadw-alpha-one/tadw-beta-two-and-then-some"
  export BD_KNOWN="tadw-alpha-one tadw-beta-two-and-then-some" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_match "$R/.bdcalls" "^update tadw-alpha-one --add-label reviewed" "labeled the positional id"
  assert_no_match "$R/.bdcalls" "^update tadw-beta-two-and-then-some" "left the slug alone"
fi

if case_start "label/resolve: the probe count is capped, whatever the branch offers"; then
  # Each candidate is a bd show subprocess on the critical path of every skill
  # start. The widened pattern matches every lowercase word, so without a cap a
  # long branch or a prose-heavy PR body would pay for all of them.
  R="$(new_repo r5 with-origin)"
  on_branch "$R" "x/aa-01/bb-02/cc-03/dd-04/ee-05/ff-06/gg-07/hh-08/ii-09/jj-10/kk-11/ll-12/mm-13/nn-14/oo-15/pp-16"
  export BD_KNOWN="" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_eq "$(grep -c '^show ' "$R/.bdcalls")" "12" "probed twelve candidates and stopped"
  assert_no_match "$R/.bdcalls" "--add-label" "labeled nothing"
fi

if case_start "label/worktree: a label from a worktree reaches the tracker unpinned"; then
  MAIN="$(new_repo b7 with-origin)"
  WT="$SANDBOX/b7-wt"
  sgit "$MAIN" worktree add --force --quiet "$WT" main
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$WT" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$WT/.bdcalls" "--add-label reviewed" "labeled the bead from the worktree"
  assert_no_match "$WT/.bdlog" "[-][-]db" "sent no --db"
fi

# ---------------------------------------------------------------------------
# Narrowing the candidate list before paying for it
#
# Every surviving candidate costs one `bd show` subprocess, and this hook
# BLOCKS UserPromptSubmit. Measured against fathom's tracker on 2026-08-23, one
# bd show takes 0.53s, so twelve of them is six seconds of a person waiting to
# type. Widening the pattern to see hyphen-free ids made this worse, not
# better: it now matches every lowercase word in a prompt.
#
# Both filters only narrow. bd still decides, and every case below asserts
# against the recorded argv of bd, which is what the hook TRIED.
# ---------------------------------------------------------------------------

seed_export() {  # seed_export <repo> <id>...: the ids the prefix filter learns from
  local dir="$1"; shift
  : > "$dir/.beads/issues.jsonl"
  local id
  for id in "$@"; do printf '{"id":"%s"}\n' "$id" >> "$dir/.beads/issues.jsonl"; done
  sgit "$dir" add -A && sgit "$dir" commit --quiet -m "seed export"
}

if case_start "label/narrow: hyphenated words that carry no known prefix never reach bd"; then
  # The noise is LONGER than the real id, so longest-first probes it first.
  # Counting probes is the assertion that matters: "did it label the bead" is
  # true either way, and says nothing about what the person waited for.
  R="$(new_repo n1 with-origin)"
  seed_export "$R" "tadw-alpha-one"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(jq -n '{hook_event_name:"UserPromptSubmit",
    prompt:"/simplify tadw-alpha-one needs-human-review-immediately pre-commit-hook-configuration"}')"
  assert_match "$R/.bdcalls" "--add-label simplified" "still labeled the bead"
  assert_eq "$(grep -c '^show ' "$R/.bdcalls")" "1" "reached the id on the first probe"
  assert_no_match "$R/.bdcalls" "^show needs-human" "never probed needs-human"
  assert_no_match "$R/.bdcalls" "^show pre-commit" "never probed pre-commit"
fi

if case_start "label/narrow: a historical prefix in the export still resolves"; then
  # fathom's case: issues from before its cutover carry life-os- and new ones
  # carry fathom-, and only the newer prefix is in config.yaml. A filter built
  # from the config alone would drop every older bead.
  R="$(new_repo n2 with-origin)"
  seed_export "$R" "fathom-new-one" "life-os-old-one"
  printf 'issue-prefix: fathom\n' > "$R/.beads/config.yaml"
  on_branch "$R" "feature/life-os-old-one"
  export BD_KNOWN="life-os-old-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_match "$R/.bdcalls" "--add-label reviewed" "resolved the historical prefix"
fi

if case_start "label/narrow: the positional segment is exempt from the prefix filter"; then
  # Segment two is not a guess about shape, so a shape filter must not overrule
  # it. Here it is hyphenated and carries a prefix this repository has never
  # seen, which is exactly what the filter is built to reject.
  R="$(new_repo n3 with-origin)"
  seed_export "$R" "tadw-alpha-one"
  on_branch "$R" "outrigger/other-team-bead/rank-beads-and-reminders"
  export BD_KNOWN="other-team-bead" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_match "$R/.bdcalls" "^show other-team-bead" "probed it anyway"
  assert_match "$R/.bdcalls" "--add-label reviewed" "and labeled the bead"
fi

if case_start "label/narrow: ordinary words in a prompt cost no tracker call at all"; then
  # The widened pattern matches every lowercase word, so this is the case that
  # would otherwise be six seconds of blocked input for no bead.
  R="$(new_repo n4 with-origin)"
  seed_export "$R" "tadw-alpha-one"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(jq -n '{hook_event_name:"UserPromptSubmit",
    prompt:"/simplify run the pre-commit and code-review checks before you push"}')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_eq "$(grep -c '^show ' "$R/.bdcalls")" "0" "probed nothing"
  assert_match "$R/.hookerr" "no candidate resolved to a bead" "and said so"
fi

if case_start "label/narrow: a bare id keeps its digit-and-length exemption"; then
  R="$(new_repo n5 with-origin)"
  seed_export "$R" "fathom-alpha-one"
  export BD_KNOWN="e12" BD_LABELS_JSON="" BD_ID_PREFIX="fathom-"
  run_hook "$LABEL" "$R" "$(jq -n '{hook_event_name:"UserPromptSubmit", prompt:"/simplify e12"}')"
  assert_match "$R/.bdcalls" "^show e12" "probed the bare short id"
  assert_match "$R/.bdcalls" "^update fathom-e12 --add-label simplified" "and labeled it"
  unset BD_ID_PREFIX
fi

if case_start "label/narrow: a repository with no prefixes to learn keeps the old behavior"; then
  # Echoing no prefixes DISABLES the hyphen filter rather than rejecting
  # everything, so a fresh clone with no export behaves as it did before.
  R="$(new_repo n6 with-origin)"
  : > "$R/.beads/issues.jsonl"
  sgit "$R" add -A && sgit "$R" commit --quiet -m "empty export"
  on_branch "$R" "feature/tadw-alpha-one"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_match "$R/.bdcalls" "--add-label reviewed" "resolved with the filter disabled"
fi

# ---------------------------------------------------------------------------
# The durable log, and --doctor
#
# The hook exits 0 on every failure path, so a skill runs whether or not its
# bead could be labeled. That contract is deliberate and unchanged. It is also
# why two total outages went unnoticed: stderr was the only record, and nothing
# surfaces it. These cases pin the record that is readable afterwards, and the
# command that answers the same question beforehand.
# ---------------------------------------------------------------------------

label_log() { echo "$1/.git/bead-label.log"; }

if case_start "label/log: a successful label writes one line naming branch, bead and action"; then
  R="$(new_repo g1 with-origin)"
  on_branch "$R" "outrigger/tadw-alpha-one/some-slug"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  L="$(label_log "$R")"
  assert_eq "$(wc -l < "$L" | tr -d ' ')" "1" "wrote exactly one line"
  assert_match "$L" "PreToolUse" "named the event"
  assert_match "$L" "outrigger/tadw-alpha-one/some-slug" "named the branch"
  assert_match "$L" "tadw-alpha-one" "named the bead"
  assert_match "$L" "applied reviewed" "named the action"
fi

if case_start "label/log: an unresolved run still exits 0 and still says so in the log"; then
  # The outage signature. Without this line the only trace is stderr, which is
  # exactly how two of these went unnoticed.
  R="$(new_repo g2 with-origin)"
  export BD_KNOWN="" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' '')"
  assert_eq "$HOOK_CODE" 0 "exits 0, so the skill still runs"
  L="$(label_log "$R")"
  assert_eq "$(wc -l < "$L" | tr -d ' ')" "1" "wrote exactly one line"
  assert_match "$L" "unresolved" "recorded that nothing resolved"
  assert_match "$L" "wanted reviewed" "named the label it could not apply"
fi

if case_start "label/log: a gate withheld at Stop is recorded, not just dropped"; then
  R="$(new_repo g3 with-origin)"
  qg_marker "$R" tadw-alpha-one
  sleep 1; write_qg_report "$R" FAIL
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.bdcalls" "--add-label" "applied no label"
  assert_match "$(label_log "$R")" "withheld qa-d" "recorded the withholding"
fi

if case_start "label/log: an unmapped skill writes nothing at all"; then
  # A hook correctly declining to label /adr is not an outcome. Logging it
  # would bury the lines that are.
  R="$(new_repo g4 with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:adr' 'tadw-alpha-one')"
  [[ ! -e "$(label_log "$R")" ]] && ok "wrote no log file" || nope "wrote no log file" "$(cat "$(label_log "$R")")"
fi

if case_start "label/log: the log is capped, so a long-lived checkout cannot grow it forever"; then
  R="$(new_repo g5 with-origin)"
  L="$(label_log "$R")"
  # 1500 lines of history, which is what months of /simplify and /code-review
  # look like in a checkout nobody cleans up.
  awk 'BEGIN { for (i = 1; i <= 1500; i++) print "old-line-" i }' > "$L"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_eq "$(wc -l < "$L" | tr -d ' ')" "1000" "trimmed to the last 1000 lines"
  assert_match "$L" "applied reviewed" "kept the newest line"
  assert_no_match "$L" "old-line-1\$" "dropped the oldest"
  [[ ! -e "$L.trimming" ]] && ok "left no partial file behind" || nope "left no partial file behind"
fi

if case_start "label/doctor: names the bead and the labels, and writes nothing"; then
  R="$(new_repo g6 with-origin)"
  on_branch "$R" "outrigger/tadw-alpha-one/some-slug"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  : > "$R/.bdcalls"
  ( cd "$R" && PATH="$BINDIR:$PATH" BD_REPO="$R" BD_LOG="$R/.bdlog" BD_CALLS="$R/.bdcalls" \
      bash "$LABEL" --doctor > "$R/.docout" 2> "$R/.docerr" )
  assert_eq "$?" 0 "exits 0"
  assert_match "$R/.docout" "outrigger/tadw-alpha-one/some-slug" "named the branch"
  assert_match "$R/.docout" "bead: *tadw-alpha-one" "named the bead"
  assert_match "$R/.docout" "/fresh-eyes-cr .*reviewed" "named a label it would apply"
  assert_match "$R/.docout" "/quality-gates .*qa-d" "named the gated label too"
  # Writing nothing is the whole contract: no label, no export, no log line.
  assert_no_match "$R/.bdcalls" "--add-label" "applied no label"
  assert_no_match "$R/.bdcalls" "export -o" "refreshed no export"
  [[ ! -e "$(label_log "$R")" ]] && ok "wrote no log line" || nope "wrote no log line"
fi

if case_start "label/doctor: returns without waiting on stdin"; then
  # The event path blocks on `cat`. --doctor is run from a terminal where no
  # hook payload is ever coming, so it must be handled before that read.
  R="$(new_repo g7 with-origin)"
  on_branch "$R" "outrigger/tadw-alpha-one/some-slug"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  # An stdin that stays OPEN and produces nothing. A `cat` here would hang.
  ( cd "$R" && PATH="$BINDIR:$PATH" BD_REPO="$R" BD_CALLS="$R/.bdcalls" \
      bash "$LABEL" --doctor > "$R/.docout" 2>&1 < <(sleep 20) ) &
  doctor_pid=$!
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    kill -0 "$doctor_pid" 2>/dev/null || break
    sleep 0.5
  done
  if kill -0 "$doctor_pid" 2>/dev/null; then
    kill "$doctor_pid" 2>/dev/null
    nope "finished without reading stdin"
  else
    ok "finished without reading stdin"
  fi
  wait "$doctor_pid" 2>/dev/null
  assert_match "$R/.docout" "tadw-alpha-one" "and still resolved the bead"
fi

# ---------------------------------------------------------------------------
# inject-mode accounting
#
# gate mode leaves a marker Stop resolves against an artifact. inject mode had
# no state at all, so a dropped label left no trace: in the 2026-08-22 session
# /tadw:verify-acceptance reached ACCEPTED, which clears its gate, and no
# "accepted" label was applied. Nothing recorded that one had been owed.
#
# Stop still applies no inject label. It only says whether the run did.
# ---------------------------------------------------------------------------

if case_start "label/inject: PreToolUse leaves a marker a gate marker can be told from"; then
  R="$(new_repo j1 with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:verify-acceptance' 'tadw-alpha-one')"
  M="$(marker_dir "$R")/accepted__tadw-alpha-one"
  [[ -f "$M" ]] && ok "wrote a marker" || nope "wrote a marker"
  assert_match_str "$(sed -n 4p "$M" 2>/dev/null)" "^inject\$" "its fourth line says inject"
  assert_no_match "$R/.bdcalls" "--add-label" "and still applied no label itself"
fi

if case_start "label/inject: Stop records a label the run was owed and never applied"; then
  R="$(new_repo j2 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\ntadw:verify-acceptance\ninject\n' "$(date +%s)" > "$M/accepted__tadw-alpha-one"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""   # the bead does NOT carry it
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.bdcalls" "--add-label" "applied no label, which is not Stop's call to make"
  assert_match "$(label_log "$R")" "OWED accepted" "recorded the debt"
  [[ ! -e "$M/accepted__tadw-alpha-one" ]] && ok "cleared the marker" || nope "cleared the marker"
fi

if case_start "label/inject: Stop confirms a label the run did apply"; then
  R="$(new_repo j3 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\ntadw:verify-acceptance\ninject\n' "$(date +%s)" > "$M/accepted__tadw-alpha-one"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON='"accepted"'
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$(label_log "$R")" "confirmed accepted" "recorded that the run applied it"
  assert_no_match "$R/.bdcalls" "--add-label" "did not apply it a second time"
fi

if case_start "label/inject: an unreadable bead is reported as unconfirmed, not as owed"; then
  # bd writes its errors to stderr and leaves stdout empty. Calling that "owed"
  # would report a debt that may not exist; this is the same empty-read trap
  # that hid a broken guard in the close hook for months.
  R="$(new_repo j4 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\ntadw:verify-acceptance\ninject\n' "$(date +%s)" > "$M/accepted__tadw-alpha-one"
  export BD_KNOWN="" BD_LABELS_JSON=""    # bd show finds nothing
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$(label_log "$R")" "could not confirm accepted" "said it could not tell"
  assert_no_match "$(label_log "$R")" "OWED" "did not claim a debt it cannot see"
fi

if case_start "label/inject: a marker past its TTL is abandoned, not resolved"; then
  R="$(new_repo j5 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\ntadw:verify-acceptance\ninject\n' "$(( $(date +%s) - 99999 ))" > "$M/accepted__tadw-alpha-one"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$R/.hookerr" "abandoning stale marker" "abandoned it"
  assert_no_match "$(label_log "$R")" "OWED" "claimed no debt from a run that never finished"
  [[ ! -e "$M/accepted__tadw-alpha-one" ]] && ok "removed the marker" || nope "removed the marker"
fi

if case_start "label/inject: a marker with no mode line is still treated as a gate marker"; then
  # Markers written before the mode line existed are on disk in real clones.
  R="$(new_repo j6 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\ntadw:quality-gates\n' "$(date +%s)" > "$M/qa-d__tadw-alpha-one"
  sleep 1; write_qg_report "$R" PASS
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$R/.bdcalls" "--add-label qa-d" "read its report and labeled it"
fi

if case_start "label/ship: /tadw:ship maps to nothing, on purpose"; then
  # /tadw:ship closes the bead, so a label applied at the same moment says
  # nothing the closed state does not. The script carries a comment recording
  # that; this asserts the behavior the comment describes.
  R="$(new_repo j7 with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(jq -n '{hook_event_name:"UserPromptSubmit", prompt:"/tadw:ship tadw-alpha-one"}')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_no_match "$R/.bdcalls" "--add-label" "labeled nothing"
  [[ ! -d "$(marker_dir "$R")" ]] && ok "left no marker for Stop to resolve" || nope "left no marker for Stop to resolve"
  assert_match_str "$(grep -c 'deliberately absent' "$LABEL")" "^1\$" "and the script records why"
fi

# ---------------------------------------------------------------------------
# install_label_bead_on_skill_invocation.sh
#
# Deployed copies of the hook drift from the source, and nothing used to say
# how. Two kinds of drift, and each fails on its own: a stale script, and a
# script that is current but reached by fewer than three events. The second is
# how a typed slash command went unlabeled while the file itself was fine.
# ---------------------------------------------------------------------------

INSTALLER_SRC="$SANDBOX/installer-src"
mkdir -p "$INSTALLER_SRC"
cp "$REPO_ROOT/scripts/install_label_bead_on_skill_invocation.sh" \
   "$REPO_ROOT/scripts/label_bead_on_skill_invocation.sh" "$INSTALLER_SRC/"
INSTALLER="$INSTALLER_SRC/install_label_bead_on_skill_invocation.sh"

run_installer() {  # run_installer <repo> [args...]; sets INSTALL_CODE, writes .instout
  local repo="$1"; shift
  sandbox_path "$repo"
  ( cd "$repo" && PATH="$BINDIR:$PATH" bash "$INSTALLER" "$@" ) > "$repo/.instout" 2>&1
  INSTALL_CODE=$?
}

installed_hook() { echo "$1/.claude/scripts/label_bead_on_skill_invocation.sh"; }

if case_start "install: a second run reports already current and rewrites no settings"; then
  R="$(new_repo i1)"
  run_installer "$R"
  assert_eq "$INSTALL_CODE" 0 "the first run succeeds"
  assert_match "$R/.instout" "hook script: installed" "reported the install"
  [[ -x "$(installed_hook "$R")" ]] && ok "left it executable" || nope "left it executable"

  run_installer "$R"
  assert_eq "$INSTALL_CODE" 0 "the second run succeeds"
  assert_match "$R/.instout" "hook script: already current" "reported already current"
  assert_match "$R/.instout" "settings:    already wired" "left the wiring alone"
  assert_match "$R/.instout" "backup:      none" "wrote no backup for a no-op run"
fi

if case_start "install: a locally modified copy is described before it is overwritten"; then
  # The report has to come BEFORE the copy, because afterwards the evidence it
  # describes no longer exists.
  R="$(new_repo i2)"
  run_installer "$R"
  echo '# somebody patched this by hand' >> "$(installed_hook "$R")"
  run_installer "$R"
  assert_match "$R/.instout" "carries 1 line\(s\) the source does not" "counted what it overwrote"
  assert_match "$R/.instout" "hashes:  source [0-9a-f]{12}, installed [0-9a-f]{12}" "named both hashes"
  assert_match "$R/.instout" "hook script: updated" "and then updated it"
fi

if case_start "install/check: a current install passes and changes nothing"; then
  R="$(new_repo i3)"
  run_installer "$R"
  before="$(cat "$R/.claude/settings.json")"
  run_installer "$R" --check
  assert_eq "$INSTALL_CODE" 0 "exits 0"
  assert_match "$R/.instout" "script:   current" "called the script current"
  assert_match "$R/.instout" "wiring:   all three events" "called the wiring complete"
  assert_eq "$(cat "$R/.claude/settings.json")" "$before" "left settings.json byte-identical"
fi

if case_start "install/check: a drifted copy fails and is left exactly as it was"; then
  R="$(new_repo i4)"
  run_installer "$R"
  echo '# local patch' >> "$(installed_hook "$R")"
  before="$(cat "$(installed_hook "$R")")"
  run_installer "$R" --check
  assert_eq "$INSTALL_CODE" 1 "exits non-zero, so a pre-push hook can use it"
  assert_match "$R/.instout" "script:   DRIFTED" "said the script drifted"
  assert_match "$R/.instout" "carries 1 line" "said how"
  assert_eq "$(cat "$(installed_hook "$R")")" "$before" "copied nothing over it"
fi

if case_start "install/check: wiring that is missing an event fails even with a current script"; then
  # tadw-ci8's failure mode exactly: the file was fine and UserPromptSubmit was
  # not wired, so every typed slash command went unlabeled.
  R="$(new_repo i5)"
  run_installer "$R"
  jq 'del(.hooks.UserPromptSubmit)' "$R/.claude/settings.json" > "$R/.s" && mv "$R/.s" "$R/.claude/settings.json"
  run_installer "$R" --check
  assert_eq "$INSTALL_CODE" 1 "exits non-zero"
  assert_match "$R/.instout" "script:   current" "still calls the script current"
  assert_match "$R/.instout" "NOT WIRED for UserPromptSubmit" "names the event that is missing"
fi

if case_start "install/check: an uninstalled repository reports that, rather than a diff"; then
  R="$(new_repo i6)"
  run_installer "$R" --check
  assert_eq "$INSTALL_CODE" 1 "exits non-zero"
  assert_match "$R/.instout" "script:   NOT INSTALLED" "said it is not installed"
  [[ ! -e "$(installed_hook "$R")" ]] && ok "installed nothing" || nope "installed nothing"
fi

# ---------------------------------------------------------------------------
# The wired command string itself
#
# Every case above runs the hook script directly, so none of them exercises the
# shell line settings.json actually carries. That line is where tadw-1rf lived:
# a session outlived the worktree it was started in, $CLAUDE_PROJECT_DIR then
# named a directory that was gone, /bin/sh exited 127 before reaching the
# script, and Claude Code reported a hook error on nearly every turn. The script
# exits 0 on every failure path it can see; this is the failure it cannot see.
# ---------------------------------------------------------------------------

HOOK_SCRIPT_NAME="label_bead_on_skill_invocation.sh"

# The command as installed, read back out of settings.json rather than rebuilt
# here. A test that rebuilds the string proves the test right, not the wiring.
wired_command() {  # wired_command <repo> <event>
  jq -r --arg e "$2" --arg name "$HOOK_SCRIPT_NAME" '
    .hooks[$e][] | (.hooks // [])[] | select((.command? // "") | contains($name)) | .command
  ' "$1/.claude/settings.json" | head -1
}

# run_wired <repo> <project-dir> <payload>; sets WIRED_CODE, writes .wiredout/.wirederr
run_wired() {
  local repo="$1" project_dir="$2" body="$3" cmd
  sandbox_path "$repo"
  cmd="$(wired_command "$repo" Stop)"
  : > "$repo/.bdlog"; : > "$repo/.bdcalls"

  # An empty command would be `sh -c ""`, which exits 0 and prints nothing, so
  # every assertion in these cases would pass against wiring that is not there.
  # That is the hole the footer of this file warns about, one layer down.
  if [[ -z "$cmd" ]]; then
    WIRED_CODE=125
    printf 'NOT WIRED: no Stop command in settings.json names %s\n' "$HOOK_SCRIPT_NAME" \
      > "$repo/.wiredout"
    cp "$repo/.wiredout" "$repo/.wirederr"
    return
  fi

  # The payload arrives on stdin from a FILE, not a pipe. The guard exits without
  # reading it, and `pipefail` is on for this suite, so a payload bigger than the
  # pipe buffer would kill printf with SIGPIPE and hand back 141 as the hook's
  # exit status. Measured: 200KB gives 141, the payloads here give 0. A file
  # keeps WIRED_CODE the hook's own status at any payload size.
  printf '%s' "$body" > "$repo/.wiredin"
  ( cd "$repo" \
    && PATH="$BINDIR:$PATH" \
       CLAUDE_PROJECT_DIR="$project_dir" \
       BD_REPO="$repo" BD_LOG="$repo/.bdlog" BD_CALLS="$repo/.bdcalls" \
       BD_SHOW_COUNT_FILE="$repo/.bdshows" \
       sh -c "$cmd" < "$repo/.wiredin" > "$repo/.wiredout" 2> "$repo/.wirederr" )
  WIRED_CODE=$?
}

if case_start "install/wiring: a project directory that is gone is silent, not an error"; then
  # No tracker state and no origin: the point of the case is that the script
  # never runs, so anything it would have read is setup that proves nothing.
  R="$(new_repo w1)"
  run_installer "$R"
  run_wired "$R" "$SANDBOX/w1-removed-under-the-session" "$(payload Stop '')"
  assert_eq "$WIRED_CODE" 0 "exits 0, so Claude Code reports no hook error"
  # Both streams, because Claude Code surfaces either one as the hook's output.
  assert_eq "$(cat "$R/.wiredout")" "" "wrote nothing to stdout"
  assert_eq "$(cat "$R/.wirederr")" "" "wrote nothing to stderr"
fi

if case_start "install/wiring: the guard still runs the script when it is there"; then
  # The other half of the guard. A wiring that is quiet in both states labels
  # nothing and reports nothing, which is worse than the error it replaced.
  R="$(new_repo w2)"
  run_installer "$R"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  qg_marker "$R" tadw-alpha-one
  sleep 1; write_qg_report "$R" PASS
  run_wired "$R" "$R" "$(payload Stop '')"
  assert_eq "$WIRED_CODE" 0 "exits 0"
  assert_match "$R/.bdcalls" "--add-label qa-d" "reached the script, which labeled the bead"
fi

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

if case_start "registration: AGENTS.md names this suite and the path resolves"; then
  agents="$REPO_ROOT/AGENTS.md"
  assert_match "$agents" "hooks/test-claude-scripts\.sh" "AGENTS.md lists the suite"
  named="$(grep -oE '[A-Za-z0-9_./-]*test-claude-scripts\.sh' "$agents" | head -1)"
  [[ -f "$REPO_ROOT/${named#./}" ]] \
    && ok "the path it names exists on disk" \
    || nope "the path it names exists on disk" "$named"
fi

# ---------------------------------------------------------------------------
# The bd arm.
#
# These hooks fail SILENTLY when they cannot reach the tracker: they log to
# stderr and exit 0, so the tool call they hang off still succeeds. That is how
# one of them ran against the wrong database for four days with nobody noticing,
# which is why the arm is asserted rather than assumed.
# ---------------------------------------------------------------------------

if case_start "label/bd: labels through bd, with no --db pin"; then
  R="$(new_repo d1 with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$R/.bdcalls" "--add-label reviewed" "labeled it reviewed"
  # bd resolves its own workspace, so no call may carry a --db pin.
  assert_no_match "$R/.bdlog" "[-][-]db" "sent no --db"
fi

# ---------------------------------------------------------------------------
# The export, and the clean tree
#
# These four replace one earlier case that asserted the opposite: that a label
# ALWAYS refreshed .beads/issues.jsonl. It did, and that is what left the tree
# modified after every /simplify, /code-review and /tadw:fresh-eyes-cr. Two
# tools then refuse to run: outrigger's pre-flight and /tadw:ship Step 4.
# ---------------------------------------------------------------------------

if case_start "label/export: a clean tree is left clean, and uncommitted"; then
  R="$(new_repo d2 with-origin)"
  before="$(head_sha "$R")"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$R/.bdcalls" "--add-label reviewed" "labeled the bead"
  assert_no_match "$R/.bdcalls" "export -o" "refreshed no export"
  assert_match "$R/.hookerr" "to keep the tree clean" "said why"
  # The whole point. Anything left here is what the next tool aborts on.
  assert_eq "$(sgit "$R" status --porcelain | grep -v '^?? \.' || true)" "" "left no tracked file modified"
  # And still no commit: bd never writes the export, so a committed copy is stale.
  assert_match_str "$(head_sha "$R")" "^$before\$" "created no commit"
fi

if case_start "label/export: TADW_BEAD_LABEL_EXPORT=1 refreshes it anyway"; then
  R="$(new_repo d2b with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON="" TADW_BEAD_LABEL_EXPORT=1
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$R/.bdcalls" "export -o" "refreshed the export on request"
  unset TADW_BEAD_LABEL_EXPORT
fi

if case_start "label/export: an already-modified export is refreshed without the flag"; then
  # Refreshing a file that is already dirty dirties nothing further, so the
  # reason for skipping does not apply and freshness wins.
  R="$(new_repo d2c with-origin)"
  # An id carrying this repository's own prefix. A made-up one would teach
  # known_id_prefixes a prefix this repository does not use, and the candidate
  # filter would then correctly drop the very bead the case is about.
  echo '{"id":"tadw-alpha-one","note":"edited by hand"}' >> "$R/.beads/issues.jsonl"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$R/.bdcalls" "export -o" "refreshed the already-dirty export"
fi

if case_start "label/export: a Stop-resolved gate label also leaves the tree clean"; then
  # add_label is the shared path, so gate mode inherits the same rule. Asserted
  # rather than assumed: Stop is the arm that runs unattended at the end of a
  # session, which is exactly when a dirtied tree is hardest to notice.
  R="$(new_repo d2d with-origin)"
  qg_marker "$R" tadw-alpha-one
  sleep 1; write_qg_report "$R" PASS
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$R/.bdcalls" "--add-label qa-d" "labeled it qa-d"
  assert_no_match "$R/.bdcalls" "export -o" "refreshed no export"
  assert_eq "$(sgit "$R" status --porcelain | grep -v '^?? \.' || true)" "" "left no tracked file modified"
fi

if case_start "label/bd: inject mode names bd and carries no database path"; then
  R="$(new_repo "d3 with space" with-origin)"
  export BD_KNOWN="tadw-alpha-one" BD_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:verify-acceptance' 'tadw-alpha-one')"
  jq -e . "$R/.hookout" >/dev/null 2>&1 && ok "the JSON parses" || nope "the JSON parses"
  assert_match "$R/.hookout" "bd update tadw-alpha-one --add-label" "named bd"
  # Inject mode has no artifact to check afterwards, so a malformed command
  # would fail where it is pasted and nothing would report it.
  assert_no_match "$R/.hookout" "[-][-]db" "carried no database path"
fi

# ---------------------------------------------------------------------------

echo
if (( failed > 0 )); then
  echo "$passed checks passed, $failed FAILED"
  exit 1
fi
# A filter that matches no case must not report success. Without this the
# mutation check reads "the suite passed" from a run that asserted nothing, and
# a fix would look pinned by a case that never executed. This exact hole hid an
# unpinned fix while this suite was being written.
if (( passed == 0 )); then
  echo "no checks ran${FILTER:+ (filter: $FILTER)}"
  exit 1
fi
echo "All $passed checks passed."
