#!/usr/bin/env bash
# tadw - test suite for the three hooks in .claude/scripts/
#
# No dependencies beyond what the hooks themselves need (bash, git, jq, coreutils).
# Run with:
#   ./hooks/test-claude-scripts.sh            # every case
#   ./hooks/test-claude-scripts.sh close      # cases whose name matches "close"
#
# WHY THIS EXISTS. These three scripts commit, push, close beads, and label
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
#      alongside br and gh. A stub that answers rev-parse, status --porcelain,
#      merge-base --is-ancestor, branch --show-current and log is a git
#      reimplementation, and the cases would then prove that reimplementation
#      right rather than the hook. Since the guards most worth testing are
#      exactly the git-dependent ones (am I on main, is the tree dirty, did the
#      merge land), the stub records argv, blocks a non-local push, and execs
#      the real git. The criterion's intent holds in full: within a case, git,
#      br and gh all resolve to this harness's own stubs, and case 0 asserts it.
#
# WHAT IS ASSERTED, in descending order of value: the exit status, which is
# always 0 because every failure path is designed to let the session continue;
# the recorded argv of br and git; then the stderr log lines.

set -uo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$HOOKS_DIR")"
SCRIPTS_DIR="${TADW_HOOK_SCRIPTS_DIR:-$REPO_ROOT/.claude/scripts}"
FILTER="${1:-}"

AUTOCOMMIT="$SCRIPTS_DIR/autocommit_beads_after_br.sh"
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
case_ran=0

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

case_start() {
  current_case="$1"
  if [[ -n "$FILTER" && "$current_case" != *"$FILTER"* ]]; then
    case_ran=0
    return 1
  fi
  case_ran=1
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
# br models just enough tracker to drive the hooks: it knows the ids in
# BR_KNOWN, records every invocation, and appends to the beads file on a
# successful close or label so the hooks' "is the beads file dirty" check has
# something real to see.
#
# BR_SHOW_FAIL_AFTER is the interesting knob. `br show <id> --json` on a
# transient failure writes to stderr and leaves stdout EMPTY, and jq exits 0 on
# empty input, which is why the close hook's status guard read as active for
# months while never firing. Letting the first N shows succeed and the rest
# return nothing reproduces that exactly: resolution finds the bead, and the
# later status read comes back empty.
write_stubs() {
  mkdir -p "$BINDIR"

  cat > "$BINDIR/br" <<'STUB'
#!/usr/bin/env bash
# Two logs on purpose. BR_LOG keeps the argv verbatim, which is what a --db
# assertion needs. BR_CALLS keeps it with the global --db flag stripped, so a
# case can anchor on the subcommand without every pattern having to allow for a
# temp-directory path in front of it.
echo "$*" >> "${BR_LOG:-/dev/null}"
args=("$@")
[[ "${args[0]:-}" == "--db" ]] && args=("${args[@]:2}")
echo "${args[*]}" >> "${BR_CALLS:-/dev/null}"
sub="${args[0]:-}"; id="${args[1]:-}"

known() { case " ${BR_KNOWN:-} " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

case "$sub" in
  show)
    known "$id" || { echo "issue not found: $id" >&2; exit 1; }
    if [[ -n "${BR_SHOW_FAIL_AFTER:-}" ]]; then
      n=$(( $(cat "${BR_SHOW_COUNT_FILE:-/dev/null}" 2>/dev/null || echo 0) + 1 ))
      echo "$n" > "${BR_SHOW_COUNT_FILE:-/dev/null}" 2>/dev/null
      if (( n > BR_SHOW_FAIL_AFTER )); then
        echo "transient read failure" >&2   # stdout stays empty, as br does
        exit 0
      fi
    fi
    printf '[{"id":"%s","status":"open","labels":[%s]}]\n' "$id" "${BR_LABELS_JSON:-}"
    ;;
  close)
    case "${BR_CLOSE_MODE:-ok}" in
      refuse-close|refuse-both)
        echo "Error: refusing to close via this form" >&2; exit 1 ;;
    esac
    echo "closed $id" >> "$BR_REPO/.beads/issues.jsonl"
    ;;
  update)
    case "$*" in
      *--status=closed*)
        [[ "${BR_CLOSE_MODE:-ok}" == "refuse-both" ]] && exit 1
        echo "closed $id" >> "$BR_REPO/.beads/issues.jsonl" ;;
      *--add-label*)
        echo "labeled $id" >> "$BR_REPO/.beads/issues.jsonl" ;;
    esac
    ;;
esac
exit 0
STUB

  # A bd stub mirroring the br one. It records into the same logs, so a case can
  # assert on the argv either backend produced without knowing which ran.
  #
  # bd takes no --db: it resolves one workspace per repository through the git
  # common dir. That is the difference the label hook's worktree pinning turns
  # on, so a stub that accepted --db would hide a real regression.
  cat > "$BINDIR/bd" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "${BR_LOG:-/dev/null}"
echo "$*" >> "${BR_CALLS:-/dev/null}"
sub="${1:-}"; id="${2:-}"

known() { case " ${BR_KNOWN:-} " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

case "$sub" in
  show)
    known "$id" || { echo '{"error":"no issues found"}' ; exit 1; }
    printf '[{"id":"%s","status":"open","labels":[%s]}]\n' "$id" "${BR_LABELS_JSON:-}"
    ;;
  export)  : ;;                       # refreshing the export writes nothing here
  comments) : ;;
  update)
    case "$*" in
      *--add-label*)   echo "labeled $id" >> "$BR_REPO/.beads/issues.jsonl" ;;
      *--status=closed*) echo "closed $id" >> "$BR_REPO/.beads/issues.jsonl" ;;
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

  chmod +x "$BINDIR/br" "$BINDIR/bd" "$BINDIR/gh" "$BINDIR/git"
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
  : > "$dir/.beads/beads.db"
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

# make_bd_repo <name> [with-origin]
#
# The same fixture, migrated: bd's declarative marker replaces br's database
# file. Both markers are deliberately NOT left in place together here; that
# combination is a migrated repo and the detector's precedence is pinned in
# outrigger's own suite, not this one. What this fixture is for is proving the
# hooks take their bd arm at all.
make_bd_repo() {
  local dir
  dir="$(new_repo "$@")"
  rm -f "$dir/.beads/beads.db"
  printf '{"backend":"dolt"}\n' > "$dir/.beads/metadata.json"
  sgit "$dir" add -A
  sgit "$dir" commit --quiet -m "migrate to bd"
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

dirty_beads() { echo '{"id":"changed"}' >> "$1/.beads/issues.jsonl"; }

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
  : > "$repo/.brlog"; : > "$repo/.brcalls"; : > "$repo/.gitlog"; : > "$repo/.ghlog"
  ( cd "$repo" \
    && printf '%s' "$body" \
     | PATH="$BINDIR:$PATH" \
       BR_REPO="$repo" BR_LOG="$repo/.brlog" BR_CALLS="$repo/.brcalls" \
       GIT_LOG="$repo/.gitlog" \
       GH_LOG="$repo/.ghlog" BR_SHOW_COUNT_FILE="$repo/.brshows" \
       bash "$script" > "$repo/.hookout" 2> "$repo/.hookerr" )
  HOOK_CODE=$?
}

last_subject() { sgit "$1" log -1 --format=%s; }
head_sha()     { sgit "$1" rev-parse HEAD; }

write_stubs

# ---------------------------------------------------------------------------
# Case 0: the sandbox itself
# ---------------------------------------------------------------------------

if case_start "sandbox: br, bd, git and gh resolve to the harness stubs"; then
  R="$(new_repo sandbox)"
  # bd is in here for a reason: its stub was added without a chmod, so it fell
  # through to the real /opt/homebrew/bin/bd and ran against the sandbox. The
  # case that caught it failed looking exactly like a hook bug.
  out="$(cd "$R" && PATH="$BINDIR:$PATH" bash -c 'command -v br; command -v bd; command -v git; command -v gh')"
  [[ "$(echo "$out" | grep -c "^$BINDIR/")" == "4" ]] \
    && ok "all four resolve inside the harness bin" \
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
# autocommit_beads_after_br.sh
# ---------------------------------------------------------------------------

if case_start "autocommit: a mutation followed by a read still commits"; then
  # f8259ea fix 5. The old test asked whether the command line MENTIONED a
  # read-only subcommand anywhere, so this exact command counted as read-only,
  # the mutation went uncommitted, and the tree stayed dirty.
  R="$(new_repo ac1 with-origin)"; dirty_beads "$R"
  run_hook "$AUTOCOMMIT" "$R" "$(payload PostToolUse 'br update x --claim && br show x')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_match_str "$(last_subject "$R")" "^beads: update x --claim" "committed the mutation"
  assert_match "$R/.gitlog" "^push" "pushed it"
fi

if case_start "autocommit: a read-only command commits nothing"; then
  R="$(new_repo ac2 with-origin)"; dirty_beads "$R"
  before="$(head_sha "$R")"
  run_hook "$AUTOCOMMIT" "$R" "$(payload PostToolUse 'br show x')"
  assert_eq "$(head_sha "$R")" "$before" "no commit"
  assert_no_match "$R/.gitlog" "^commit" "never reached git commit"
  assert_match "$R/.hookerr" "no mutating br subcommand" "said why"
fi

if case_start "autocommit: an unknown subcommand counts as mutating"; then
  R="$(new_repo ac3 with-origin)"; dirty_beads "$R"
  run_hook "$AUTOCOMMIT" "$R" "$(payload PostToolUse 'br frobnicate x')"
  assert_match_str "$(last_subject "$R")" "^beads: frobnicate x" "committed rather than guessed"
fi

if case_start "autocommit: another dirty tracked file blocks the commit"; then
  R="$(new_repo ac4 with-origin)"; dirty_beads "$R"
  echo "unrelated" >> "$R/file.txt"; sgit "$R" add file.txt
  sgit "$R" commit --quiet -m "add file"; echo "more" >> "$R/file.txt"
  before="$(head_sha "$R")"
  run_hook "$AUTOCOMMIT" "$R" "$(payload PostToolUse 'br update x --claim')"
  assert_eq "$(head_sha "$R")" "$before" "no commit"
  assert_match "$R/.hookerr" "other tracked files are dirty" "said why"
fi

if case_start "autocommit: off main, nothing is committed"; then
  R="$(new_repo ac5 with-origin)"; add_branch "$R" feature/x "work"
  sgit "$R" checkout --quiet feature/x; dirty_beads "$R"
  before="$(head_sha "$R")"
  run_hook "$AUTOCOMMIT" "$R" "$(payload PostToolUse 'br update x --claim')"
  assert_eq "$(head_sha "$R")" "$before" "no commit"
  assert_match "$R/.hookerr" "not on main" "said why"
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
  export GH_PR_JSON="$SANDBOX/pr.json" BR_KNOWN="tadw-qg-script-secrets-gate-jbg" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_match "$R/.brcalls" "^close tadw-qg-script-secrets-gate-jbg" "closed the whole id"
  assert_match_str "$(last_subject "$R")" "PR #7 merged" "committed the close"
fi

if case_start "close/pr: two real beads in the body and no trailer refuses"; then
  R="$(new_repo c2 with-origin)"
  pr_json "$SANDBOX/pr.json" "No id here" "Blocks tadw-alpha-one and follows tadw-beta-two"
  export GH_PR_JSON="$SANDBOX/pr.json" BR_KNOWN="tadw-alpha-one tadw-beta-two" BR_LABELS_JSON=""
  before="$(head_sha "$R")"
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_no_match "$R/.brcalls" "^(close|update .* --status=closed)" "closed neither"
  assert_match "$R/.hookerr" "refusing to guess" "said it refused"
  assert_eq "$(head_sha "$R")" "$before" "no commit"
fi

if case_start "close/pr: a Bead trailer beats the title"; then
  R="$(new_repo c3 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" "Bead: tadw-beta-two"
  export GH_PR_JSON="$SANDBOX/pr.json" BR_KNOWN="tadw-alpha-one tadw-beta-two" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_match "$R/.brcalls" "^close tadw-beta-two" "closed the trailer id"
  assert_no_match "$R/.brcalls" "^close tadw-alpha-one" "left the title id alone"
fi

if case_start "close/pr: an empty status read closes nothing"; then
  # f8259ea fix 2. `br show` on a transient failure writes to stderr and leaves
  # stdout empty; jq exits 0 on empty input, so `|| echo unknown` never fired
  # and an unreadable bead fell through to the close.
  R="$(new_repo c4 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON="" \
         BR_SHOW_FAIL_AFTER=1
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  unset BR_SHOW_FAIL_AFTER
  assert_no_match "$R/.brcalls" "^(close|update .* --status=closed)" "closed nothing"
  assert_match "$R/.hookerr" "could not read state" "said why"
fi

if case_start "close/pr: a failed check in stderr does not block the close"; then
  # f8259ea fix 4. The sniff matched an unanchored `failed`, so a successful
  # merge whose check summary mentioned one failed check skipped the close.
  R="$(new_repo c5 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" \
    "$(payload PostToolUse 'gh pr merge 7 --squash' 'Checks: 4 passed, 1 failed. Merged.')"
  assert_match "$R/.brcalls" "^close tadw-alpha-one" "still closed"
fi

if case_start "close/pr: an error in stderr does block the close"; then
  R="$(new_repo c6 with-origin)"
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'gh pr merge 7' 'error: not mergeable')"
  assert_no_match "$R/.brcalls" "^close" "closed nothing"
  assert_match "$R/.hookerr" "reported an error" "said why"
fi

if case_start "close/worktree: br is pinned to the main checkout database"; then
  # f8259ea fix 3. Unpinned, a close from a worktree lands in that worktree's
  # own copy of .beads/beads.db and the real bead stays open.
  MAIN="$(new_repo c7 with-origin)"
  WT="$SANDBOX/c7-wt"
  sgit "$MAIN" worktree add --force --quiet "$WT" main
  pr_json "$SANDBOX/pr.json" "Work on tadw-alpha-one" ""
  export GH_PR_JSON="$SANDBOX/pr.json" BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$WT" "$(payload PostToolUse 'gh pr merge 7 --squash')"
  assert_match "$WT/.brlog" "--db $MAIN/.beads/beads.db" "every br call names the main database"
  assert_no_match "$WT/.brcalls" "^--db" "no call ran unpinned"
fi

# ---------------------------------------------------------------------------
# close_bead_on_pr_merge.sh, local-merge path
# ---------------------------------------------------------------------------

if case_start "close/local: a merged branch closes the bead it names"; then
  R="$(new_repo l1 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/shell" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/shell"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge --ff-only feature/tadw-alpha-one/shell')"
  assert_eq "$HOOK_CODE" 0 "exits 0"
  assert_match "$R/.brcalls" "^close tadw-alpha-one" "closed it"
  assert_match_str "$(last_subject "$R")" "merged feature/tadw-alpha-one/shell into main" "committed the close"
fi

if case_start "close/local: the close is committed but never pushed"; then
  # A local merge is not on the remote yet. Pushing here would carry the whole
  # merged branch, and in a repository that deploys on a push to main that turns
  # "I merged locally" into "I deployed".
  R="$(new_repo l2 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/x"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  assert_no_match "$R/.gitlog" "^push" "no push"
  assert_match "$R/.hookerr" "committed but not pushed" "said so"
fi

if case_start "close/local: git merge --abort closes nothing"; then
  R="$(new_repo l3 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge --abort')"
  assert_eq "$(wc -c < "$R/.brcalls" | tr -d ' ')" 0 "br was never called"
fi

if case_start "close/local: a merge that did not land closes nothing"; then
  R="$(new_repo l4 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  assert_eq "$(wc -c < "$R/.brcalls" | tr -d ' ')" 0 "br was never called"
  assert_match "$R/.hookerr" "did not land" "said why"
fi

if case_start "close/local: br close refused falls back to the update form"; then
  R="$(new_repo l5 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/x"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON="" BR_CLOSE_MODE=refuse-close
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  unset BR_CLOSE_MODE
  assert_match "$R/.brcalls" "^update tadw-alpha-one --status=closed" "used the older form"
  assert_match_str "$(last_subject "$R")" "^beads: close" "still committed"
fi

if case_start "close/local: both close forms failing commits nothing"; then
  R="$(new_repo l6 with-origin)"; add_branch "$R" "feature/tadw-alpha-one/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/tadw-alpha-one/x"
  before="$(head_sha "$R")"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON="" BR_CLOSE_MODE=refuse-both
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/tadw-alpha-one/x')"
  unset BR_CLOSE_MODE
  assert_eq "$HOOK_CODE" 0 "exits 0 so the session continues"
  assert_eq "$(head_sha "$R")" "$before" "no commit"
  assert_match "$R/.hookerr" "close it by hand" "named the manual command"
fi

if case_start "close/local: a branch naming no known bead closes nothing"; then
  R="$(new_repo l7 with-origin)"; add_branch "$R" "feature/nothing-here/x" "work"
  sgit "$R" merge --quiet --no-edit "feature/nothing-here/x"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$CLOSE" "$R" "$(payload PostToolUse 'git merge feature/nothing-here/x')"
  assert_no_match "$R/.brcalls" "^close" "closed nothing"
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
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_match "$R/.brcalls" "--add-label reviewed" "applied the marker's label"
  assert_no_match "$R/.brcalls" "--add-label qa-d" "did not fall back to qa-d"
fi

if case_start "label/stop: a failing report earns no label"; then
  R="$(new_repo b2 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\nqa\n' "$(date +%s)" > "$M/qa-d__tadw-alpha-one"
  sleep 1; write_report "$R" 2 1 0
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.brcalls" "--add-label" "no label"
  assert_match "$R/.hookerr" "QA gate not met" "said why"
fi

if case_start "label/stop: a marker past its TTL is abandoned"; then
  R="$(new_repo b3 with-origin)"
  M="$(marker_dir "$R")"; mkdir -p "$M"
  printf '%s\ntadw-alpha-one\nqa\n' "$(( $(date +%s) - 99999 ))" > "$M/qa-d__tadw-alpha-one"
  sleep 1; write_report "$R" 0 0 0
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload Stop '')"
  assert_no_match "$R/.brcalls" "--add-label" "no label"
  assert_match "$R/.hookerr" "abandoning stale marker" "said why"
  [[ ! -e "$M/qa-d__tadw-alpha-one" ]] && ok "removed the marker" || nope "removed the marker"
fi

if case_start "label/pre: apply mode labels the bead immediately"; then
  R="$(new_repo b4 with-origin)"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$R/.brcalls" "--add-label reviewed" "labeled it reviewed"
  assert_match_str "$(last_subject "$R")" "^beads: label tadw-alpha-one reviewed" "committed the label"
fi

if case_start "label/pre: an already-labeled bead is left alone"; then
  R="$(new_repo b5 with-origin)"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON='"reviewed"'
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_no_match "$R/.brcalls" "--add-label" "no second label"
  assert_match "$R/.hookerr" "already labeled" "said so"
fi

if case_start "label/pre: inject mode single-quotes the database path"; then
  # f8259ea fix 7. The injected text is a command someone pastes later, so an
  # unquoted path containing a space arrives as two arguments and fails where it
  # is pasted rather than here.
  R="$(new_repo "b6 with space" with-origin)"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:verify-acceptance' 'tadw-alpha-one')"
  assert_match "$R/.hookout" "hookSpecificOutput" "emitted hook JSON"
  assert_match "$R/.hookout" "--db '[^']*\.beads/beads\.db'" "quoted the database path"
  jq -e . "$R/.hookout" >/dev/null 2>&1 && ok "the JSON parses" || nope "the JSON parses"
fi

if case_start "label/worktree: br is pinned to the main checkout database"; then
  MAIN="$(new_repo b7 with-origin)"
  WT="$SANDBOX/b7-wt"
  sgit "$MAIN" worktree add --force --quiet "$WT" main
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$WT" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$WT/.brlog" "--db $MAIN/.beads/beads.db" "every br call names the main database"
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
# Every fixture above is br-shaped, so until now these hooks were proven on one
# backend only. The cases below build a MIGRATED repo and assert the arm that
# repo takes, because each of these hooks fails SILENTLY on the wrong backend:
# they log to stderr and exit 0, so the tool call they hang off still succeeds.
# That is exactly how one of these hooks ran `br --db` against a migrated repo
# for four days with nobody noticing.
# ---------------------------------------------------------------------------

if case_start "label/bd: labels through bd, with no --db pin"; then
  R="$(make_bd_repo d1 with-origin)"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  assert_match "$R/.brcalls" "--add-label reviewed" "labeled it reviewed"
  # bd resolves its own workspace. A --db here would mean the br arm ran.
  assert_no_match "$R/.brlog" "[-][-]db" "sent no --db"
fi

if case_start "label/bd: refreshes the export instead of committing it"; then
  R="$(make_bd_repo d2 with-origin)"
  before="$(head_sha "$R")"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:review-fresh-eyes' 'tadw-alpha-one')"
  # The export is what bv and Manifest read, so it must be refreshed...
  assert_match "$R/.brcalls" "export -o" "refreshed the export"
  # ...and NOT committed: bd never writes it, so the committed copy is stale.
  assert_match_str "$(head_sha "$R")" "^$before\$" "created no commit"
fi

if case_start "label/bd: inject mode names bd and carries no database path"; then
  R="$(make_bd_repo "d3 with space" with-origin)"
  export BR_KNOWN="tadw-alpha-one" BR_LABELS_JSON=""
  run_hook "$LABEL" "$R" "$(payload PreToolUse '' '' 'tadw:verify-acceptance' 'tadw-alpha-one')"
  jq -e . "$R/.hookout" >/dev/null 2>&1 && ok "the JSON parses" || nope "the JSON parses"
  assert_match "$R/.hookout" "bd update tadw-alpha-one --add-label" "named bd"
  # Inject mode has no artifact to check afterwards, so a br command handed to
  # a bd repo would fail where it is pasted and nothing would report it.
  assert_no_match "$R/.hookout" "[-][-]db" "carried no database path"
fi

if case_start "autocommit/bd: declines, and says which backend"; then
  R="$(make_bd_repo d4 with-origin)"
  before="$(head_sha "$R")"
  run_hook "$AUTOCOMMIT" "$R" "$(payload PostToolUse 'bd update tadw-alpha-one --add-label reviewed')"
  [[ "$HOOK_CODE" == "0" ]] && ok "exited 0" || nope "exited 0"
  assert_match "$R/.hookerr" "backend is bd" "named the backend"
  assert_match_str "$(head_sha "$R")" "^$before\$" "created no commit"
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
