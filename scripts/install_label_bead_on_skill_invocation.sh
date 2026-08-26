#!/usr/bin/env bash
# Install the bead-labeling Claude Code hook into the repository you run this from.
#
# Run it from the root of a target repository (atlas, fathom, meridian, ...):
#
#     ~/Dev/templeton-agentic-dev-workbench/scripts/install_label_bead_on_skill_invocation.sh
#
# It does two things:
#
#   1. Copies label_bead_on_skill_invocation.sh, the copy sitting beside this
#      installer, into <repo>/.claude/scripts/ and marks it executable.
#   2. Wires that path into <repo>/.claude/settings.json for the three events
#      the hook dispatches on: PreToolUse (matcher Skill), UserPromptSubmit,
#      and Stop. Everything else in settings.json is left byte-identical.
#
# --check answers the same two questions and changes nothing: it reports how
# the installed copy differs from the source and which of the three events are
# wired, then exits non-zero if either is out of step. That is the form a
# pre-push hook can use, and it is also the honest way to look at a repository
# whose copy somebody may have edited on purpose.
#
# Two properties worth relying on:
#
#   IT IS SAFE TO RE-RUN. A second run overwrites the installed script, points
#   any existing wiring at the canonical path, and adds no duplicate entry. The
#   hook is identified by its file name, so wiring that names an older
#   directory is repaired rather than duplicated. A statusMessage you edited by
#   hand survives.
#
#   IT NEVER LEAVES settings.json WORSE THAN IT FOUND IT. A file that does not
#   parse as JSON is refused rather than patched. The replacement is built in a
#   temp file that jq has already parsed, and the original is copied to
#   settings.json.bak.<timestamp> immediately before being replaced. A run that
#   changes nothing writes no backup, and a repository that had no
#   settings.json still has none if any step fails.

set -euo pipefail

HOOK_SCRIPT="label_bead_on_skill_invocation.sh"
DEST_DIR=".claude/scripts"
CHECK_ONLY=false

# Verbatim from the reference wiring in ~/Dev/atlas/.claude/settings.json, so a
# repo installed by this script shows the same progress lines as that one.
PRE_MESSAGE="feature-development / simplify / code-review / fresh-eyes-cr / qa / verify-acceptance: labeling bead..."
PROMPT_MESSAGE="slash command: labeling bead..."
STOP_MESSAGE="Resolving pending bead labels..."

die() { echo "error: $*" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Usage: install_label_bead_on_skill_invocation.sh [--check] [--dest-dir DIR]

Installs the bead-labeling hook into the git repository containing the current
directory, and wires it into that repository's .claude/settings.json.

Options:
  --check          Report how the installed copy and its wiring differ from the
                   source, then exit: 0 when both are current, 1 otherwise.
                   Copies nothing and touches settings.json not at all.
  --dest-dir DIR   Where to put the hook script, relative to the repository
                   root. Default: .claude/scripts
  -h, --help       Print this and exit.

Requires git and jq on PATH. The hook itself needs bd, jq, and git at runtime.
USAGE
}

# ---------------------------------------------------------------------
# Arguments and preconditions
# ---------------------------------------------------------------------

while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --check) CHECK_ONLY=true; shift ;;
    --dest-dir)
      [[ $# -ge 2 ]] || die "--dest-dir needs a directory"
      DEST_DIR="${2%/}"
      shift 2
      ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

# The wiring writes "$CLAUDE_PROJECT_DIR/$DEST_DIR/...", so a destination that
# escapes the repository would produce a settings.json naming a path that does
# not exist for anyone else who clones it.
case "$DEST_DIR" in
  "") die "--dest-dir cannot be empty" ;;
  /*|*..*) die "--dest-dir must be inside the repository, and cannot contain '..'" ;;
esac

command -v git >/dev/null 2>&1 || die "git is not on PATH"
command -v jq >/dev/null 2>&1 || die "jq is not on PATH; it patches settings.json, and the hook needs it at runtime too"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SOURCE_DIR/$HOOK_SCRIPT"
[[ -f "$SOURCE" ]] || die "$HOOK_SCRIPT is not beside this installer (looked in $SOURCE_DIR)"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  die "not inside a git repository; run this from the repository you want the hook installed in"

DEST="$REPO_ROOT/$DEST_DIR/$HOOK_SCRIPT"
[[ "$SOURCE" != "$DEST" ]] ||
  die "source and destination are the same file; run this from the target repository, not from its own source repository"

SETTINGS="$REPO_ROOT/.claude/settings.json"

# ---------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------

# Twelve hex characters, matching what the hook itself logs on every run, so a
# log line found in some other repository can be matched against a source here.
hash_of() {
  { shasum -a 256 "$1" 2>/dev/null || sha256sum "$1" 2>/dev/null; } | cut -c1-12
}

# One line saying HOW the installed copy differs, because "updated" alone tells
# you a copy changed and nothing about whether that was safe. Line counts, not
# a diff: the useful distinction is "one generation behind the source" from
# "somebody edited this in place", and `diff` itself is right there for the
# rest.
describe_drift() {
  local missing extra
  missing="$(diff "$SOURCE" "$DEST" | grep -c '^<' || true)"
  extra="$(diff "$SOURCE" "$DEST" | grep -c '^>' || true)"
  echo "  differs: the installed copy is missing $missing line(s) the source has,"
  echo "           and carries $extra line(s) the source does not"
  echo "  hashes:  source $(hash_of "$SOURCE"), installed $(hash_of "$DEST")"
}

# Which of the three events name this hook. Wiring drift is its own failure:
# a current script reached by two events labels nothing on the third, which is
# exactly how a typed slash command went unlabeled while the file was fine.
wired_events() {
  [[ -f "$SETTINGS" ]] || return 0
  jq -r --arg name "$HOOK_SCRIPT" '
    (.hooks // {})
    | to_entries[]
    | .key as $event
    | (.value | if type == "array" then .[] else empty end)
    | (.hooks // [])[]
    | select((.command? // "") | contains($name))
    | $event
  ' "$SETTINGS" 2>/dev/null | sort -u
}

if [[ "$CHECK_ONLY" == true ]]; then
  check_failed=false

  if [[ ! -f "$DEST" ]]; then
    echo "script:   NOT INSTALLED at $DEST_DIR/$HOOK_SCRIPT"
    check_failed=true
  elif cmp -s "$SOURCE" "$DEST"; then
    echo "script:   current at $DEST_DIR/$HOOK_SCRIPT ($(hash_of "$SOURCE"))"
  else
    echo "script:   DRIFTED at $DEST_DIR/$HOOK_SCRIPT"
    describe_drift
    check_failed=true
  fi

  found="$(wired_events | tr '\n' ' ')"
  missing_events=""
  for e in PreToolUse UserPromptSubmit Stop; do
    case " $found " in *" $e "*) ;; *) missing_events="$missing_events $e" ;; esac
  done
  if [[ -z "$missing_events" ]]; then
    echo "wiring:   all three events reference the hook"
  else
    echo "wiring:   NOT WIRED for$missing_events in .claude/settings.json"
    check_failed=true
  fi

  if [[ "$check_failed" == true ]]; then
    echo
    echo "Run this installer without --check to bring both into step."
    exit 1
  fi
  exit 0
fi

# ---------------------------------------------------------------------
# Step 1: the hook script
# ---------------------------------------------------------------------
#
# The script lands before the wiring, and the order matters. Stopping here
# leaves a file nothing calls, which is inert. The reverse order would leave
# wiring pointing at a script that is not there, which labels nothing. The
# guard in Step 2 keeps that state quiet rather than noisy, and quiet is not
# the same as working, so the order still stands.

if [[ -f "$DEST" ]] && cmp -s "$SOURCE" "$DEST"; then
  script_result="already current"
elif [[ -f "$DEST" ]]; then
  script_result="updated"
else
  script_result="installed"
fi

# Said BEFORE the copy, because afterwards the evidence is gone. A locally
# patched copy is the case this exists for: the run still overwrites, and now
# the report says what it overwrote.
if [[ "$script_result" == "updated" ]]; then
  describe_drift
fi

mkdir -p "$REPO_ROOT/$DEST_DIR"
cp "$SOURCE" "$DEST"
chmod +x "$DEST"

# ---------------------------------------------------------------------
# Step 2: the wiring
# ---------------------------------------------------------------------

# The literal command string the hook entry carries. $CLAUDE_PROJECT_DIR stays
# unexpanded, and the inner quotes are part of the value, so the command still
# works if a path component ever contains a space.
#
# It resolves the script through the GIT COMMON DIR rather than reading
# $CLAUDE_PROJECT_DIR/.claude directly, so a session running in a linked worktree
# runs the MAIN checkout's copy. Two reasons, and the second is why the earlier
# `test -x` guard was not enough on its own:
#
#   A worktree's copy can be stale. Every worktree checks out its own copy of a
#   tracked file, so a session in one runs whatever that branch happened to have,
#   which is not necessarily the installed version.
#
#   A worktree gets REMOVED under a live session. /tadw:ship deletes the worktree
#   it ran in, the session keeps going, and $CLAUDE_PROJECT_DIR then names a
#   directory that is gone. The guard below made that quiet, by exiting 0 and
#   labeling nothing; resolving through the common dir makes it WORK, because the
#   main checkout is still there. Measured on 2026-08-26: a Stop hook reported
#   "No such file or directory" for a worktree removed minutes earlier.
#
# Three guards, in the order the values become known.
#
# The FIRST guard refuses an empty $CLAUDE_PROJECT_DIR before git sees it, and it
# is not defensive padding. `git -C ""` is not an error: it silently stays in the
# current directory. Without this line an unset project directory resolves
# whatever repository the hook process happens to be standing in, and labels a
# bead there. That is the same hazard the sandbox guard in
# hooks/test-claude-scripts.sh exists for, and that file records it writing four
# branches and two worktrees into a real checkout once already.
#
# The `test -n "$s"` guard covers a project directory that is not a repository at
# all, where git answers nothing and `${s%/.git}` would otherwise reach for
# /.claude/... at the filesystem root. `test -x` then covers a repository that
# never installed the hook.
#
# Shell variables are used here where the path used to be written twice. The
# doubled form cannot express this: the resolution is a command substitution, and
# running it twice would fork git twice on every hook. $-expansion is safe to
# rely on, since $CLAUDE_PROJECT_DIR in this same string already depends on it.
HOOK_COMMAND='d="${CLAUDE_PROJECT_DIR:-}"; test -n "$d" || exit 0; s="$(git -C "$d" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; test -n "$s" || exit 0; s="${s%/.git}/'"$DEST_DIR/$HOOK_SCRIPT"'"; test -x "$s" && exec "$s" || exit 0'

# Read the current settings into a variable rather than patching the file in
# place, and create nothing yet. A repository that had no settings.json must
# still have none if anything below fails.
if [[ -f "$SETTINGS" ]]; then
  jq -e . "$SETTINGS" >/dev/null 2>&1 ||
    die "$SETTINGS is not valid JSON; fix it before installing, since patching it would lose the rest of the file"
  original="$(cat "$SETTINGS")"
  settings_existed=true
else
  original='{}'
  settings_existed=false
fi

# Per event: repoint any entry that already names this hook, otherwise append
# one to the group whose matcher matches, otherwise add that group. Rewriting
# in place is what makes a second run a repair rather than a duplication.
#
# Single-quoted on purpose: $cmd, $name, $pre, $prompt, and $stop are jq
# variables fed by the --arg flags below, and letting bash expand them first
# would substitute empty strings into the program.
# shellcheck disable=SC2016
JQ_PROGRAM='
def entry($msg): {type: "command", command: $cmd, statusMessage: $msg};

def is_ours: (.command? // "") | contains($name);

def patched($msg):
  .type = "command"
  | .command = $cmd
  | if has("statusMessage") then . else .statusMessage = $msg end;

def wire($event; $matcher; $msg):
  (.hooks[$event] // []) as $groups
  | if [$groups[] | (.hooks // [])[] | is_ours] | any
    then
      .hooks[$event] = [
        $groups[]
        | if [(.hooks // [])[] | is_ours] | any
          then .hooks = [.hooks[] | if is_ours then patched($msg) else . end]
          else .
          end
      ]
    else
      ([$groups | to_entries[] | select((.value.matcher // null) == $matcher) | .key] | first) as $i
      | if $i == null
        then .hooks[$event] = $groups + [
          (if $matcher == null then {} else {matcher: $matcher} end) + {hooks: [entry($msg)]}
        ]
        else .hooks[$event][$i].hooks = ((.hooks[$event][$i].hooks // []) + [entry($msg)])
        end
    end;

wire("PreToolUse"; "Skill"; $pre)
| wire("UserPromptSubmit"; null; $prompt)
| wire("Stop"; null; $stop)
'

tmp="$(mktemp "${TMPDIR:-/tmp}/settings.json.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

printf '%s' "$original" |
  jq --arg cmd "$HOOK_COMMAND" \
     --arg name "$HOOK_SCRIPT" \
     --arg pre "$PRE_MESSAGE" \
     --arg prompt "$PROMPT_MESSAGE" \
     --arg stop "$STOP_MESSAGE" \
     "$JQ_PROGRAM" >"$tmp" ||
  die "jq could not patch the settings (its own error is above); $SETTINGS is untouched"

# Belt and braces: jq exiting 0 should mean valid JSON on stdout, and an empty
# file here would mean the write failed in a way that leaves no error behind.
[[ -s "$tmp" ]] || die "the patch produced an empty file; $SETTINGS is untouched"
jq -e . "$tmp" >/dev/null 2>&1 || die "the patch produced invalid JSON; $SETTINGS is untouched"

# The backup is taken here rather than earlier, so a run that changes nothing
# leaves no backup file behind to explain.
if [[ "$settings_existed" == true ]] && cmp -s "$tmp" "$SETTINGS"; then
  settings_result="already wired"
  backup_result="none, the wiring was already in place"
elif [[ "$settings_existed" == true ]]; then
  backup="$SETTINGS.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$SETTINGS" "$backup"
  backup_result="$(basename "$backup")"
  settings_result="wired"
  cp "$tmp" "$SETTINGS"
else
  mkdir -p "$(dirname "$SETTINGS")"
  backup_result="none, the file did not exist until now"
  settings_result="created and wired"
  cp "$tmp" "$SETTINGS"
fi

# ---------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------

echo "repository:  $REPO_ROOT"
echo "hook script: $script_result at $DEST_DIR/$HOOK_SCRIPT ($(hash_of "$DEST"))"
echo "settings:    $settings_result in .claude/settings.json"
echo "backup:      $backup_result"

echo
echo "The three events now referencing the hook:"
# Every event this script writes holds an array, but an unrelated event in
# somebody's settings.json may hold anything. Skipping a non-array keeps a
# report from failing after the install already succeeded.
jq -r --arg name "$HOOK_SCRIPT" '
  (.hooks // {})
  | to_entries[]
  | .key as $event
  | (.value | if type == "array" then .[] else empty end)
  | (.matcher // "-") as $matcher
  | (.hooks // [])[]
  | select((.command? // "") | contains($name))
  | "  \($event) (matcher \($matcher)): \(.command)"
' "$SETTINGS"

echo
echo "Commit .claude/settings.json and $DEST_DIR/$HOOK_SCRIPT to share this with the repo."
