#!/usr/bin/env bash
# Install the bead-labeling hook into the repository you run this from, for Claude
# Code, for Codex, or for both. --agent is required, and the installer never
# guesses it from the folders it finds. `--help` says what each value installs;
# this header says why it behaves as it does.
#
# Run it from the root of a target repository (atlas, fathom, meridian, ...):
#
#     ~/Dev/templeton-agentic-dev-workbench/scripts/install_label_bead_on_skill_invocation.sh --agent claude
#
# The label script runs claim_bead_for_build.py as a sibling to decide the /build
# claim, so every copy of the script gets the module beside it. Without the
# module, /build starts with no claim at all.
#
# --check is the form a pre-push hook can use, and it is also the honest way to
# look at a repository whose copy somebody may have edited on purpose.
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
RUNNER_SCRIPT="run_codex_bead_hooks.sh"
MODULE_SCRIPT="claim_bead_for_build.py"
# What the claim module was called before 2026-10-06. Nothing names it but the
# label script, which this run replaces, so the old file is always safe to remove.
OLD_MODULE_SCRIPT="label_bead_hook.py"
DEST_DIR=".claude/scripts"
CODEX_DEST_DIR=".codex/scripts"
# Where an installer before 2026-10-06 put the runner. Fixed, because --dest-dir
# moves the Claude files and never moved the runner.
OLD_RUNNER_DIR=".claude/scripts"
CHECK_ONLY=false
AGENT=""
DEST_DIR_GIVEN=false

# A status line that names no skills cannot fall out of step with the label
# hook's case table, which is where the skill list lives.
PRE_MESSAGE="labeling bead..."
AGENT_MESSAGE="acceptance-verifier: labeling bead..."
PROMPT_MESSAGE="slash command: labeling bead..."
STOP_MESSAGE="Resolving pending bead labels..."
SUBAGENT_STOP_MESSAGE="Checking for a missing acceptance report..."

# Every registration the hook needs, as the event and, where the event takes
# one, its matcher in parentheses. --check verifies each one, and the jq program
# below wires each one.
#
# PreToolUse is here twice. The Agent registration is how a session that starts
# the acceptance-verifier directly is seen at all: such a start calls no Skill
# tool, so the Skill registration never fires for it.
WIRED_REGISTRATIONS="PreToolUse(Skill) PreToolUse(Agent) UserPromptSubmit Stop SubagentStop"

usage() {
  cat <<'USAGE'
Usage: install_label_bead_on_skill_invocation.sh --agent claude|codex|both [--check] [--dest-dir DIR]

Installs the bead-labeling hook into the git repository containing the current
directory, for the agent you name.

Options:
  --agent VALUE    Required. Which agent to install for:
                     claude  the label script and its module in .claude/scripts,
                             wired into .claude/settings.json
                     codex   the label script, its module, and the Codex runner
                             in .codex/scripts. It changes nothing else under
                             .claude/, and the runner is inert until
                             .codex/hooks.json names it.
                     both    both of the above
                   Every value removes a runner an older installer left in
                   .claude/scripts.
  --check          Report how the installed copies and the wiring differ from
                   the source for that agent, then exit: 0 when all are current,
                   1 otherwise. Copies nothing and deletes nothing.
  --dest-dir DIR   Where to put the Claude label script and its module,
                   relative to the repository root. Default: .claude/scripts
                   It does not apply to --agent codex, which always installs
                   into .codex/scripts, and the installer refuses the pair.
  -h, --help       Print this and exit.

An argument error exits 2. Requires git and jq on PATH. The hook itself needs
bd, jq, and git at runtime, and python3 to list the candidate bead ids and to
claim a bead for /build.
USAGE
}

die() { echo "error: $*" >&2; exit 1; }
usage_error() { echo "error: $*" >&2; usage >&2; exit 2; }

# ---------------------------------------------------------------------
# Arguments and preconditions
# ---------------------------------------------------------------------

while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --check) CHECK_ONLY=true; shift ;;
    --agent)
      [[ $# -ge 2 ]] || usage_error "--agent needs claude, codex, or both"
      AGENT="$2"
      shift 2
      ;;
    --dest-dir)
      [[ $# -ge 2 ]] || usage_error "--dest-dir needs a directory"
      DEST_DIR="${2%/}"
      DEST_DIR_GIVEN=true
      shift 2
      ;;
    *) usage_error "unknown argument: $1" ;;
  esac
done

# The one place the run turns --agent into the agents it acts for. Nothing is
# guessed from the folders a repository already has: a repository with a
# .codex/ folder may still want the Claude hook alone, and the reverse.
case "$AGENT" in
  claude|codex) AGENTS=("$AGENT") ;;
  both) AGENTS=(claude codex) ;;
  "") usage_error "--agent is required: claude, codex, or both" ;;
  *) usage_error "--agent must be claude, codex, or both, not '$AGENT'" ;;
esac

[[ "$AGENT" != "codex" || "$DEST_DIR_GIVEN" == false ]] ||
  usage_error "--dest-dir does not apply to --agent codex; the Codex files always go to $CODEX_DEST_DIR"

# The wiring writes "$CLAUDE_PROJECT_DIR/$DEST_DIR/...", so a destination that
# escapes the repository would produce a settings.json naming a path that does
# not exist for anyone else who clones it.
case "$DEST_DIR" in
  "") usage_error "--dest-dir cannot be empty" ;;
  /*|*..*) usage_error "--dest-dir must be inside the repository, and cannot contain '..'" ;;
esac

command -v git >/dev/null 2>&1 || die "git is not on PATH"
command -v jq >/dev/null 2>&1 || die "jq is not on PATH; it patches settings.json, and the hook needs it at runtime too"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SOURCE_DIR/$HOOK_SCRIPT"
[[ -f "$SOURCE" ]] || die "$HOOK_SCRIPT is not beside this installer (looked in $SOURCE_DIR)"
RUNNER_SOURCE="$SOURCE_DIR/$RUNNER_SCRIPT"
[[ -f "$RUNNER_SOURCE" ]] || die "$RUNNER_SCRIPT is not beside this installer (looked in $SOURCE_DIR)"
MODULE_SOURCE="$SOURCE_DIR/$MODULE_SCRIPT"
[[ -f "$MODULE_SOURCE" ]] || die "$MODULE_SCRIPT is not beside this installer (looked in $SOURCE_DIR)"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  die "not inside a git repository; run this from the repository you want the hook installed in"

DEST="$REPO_ROOT/$DEST_DIR/$HOOK_SCRIPT"
MODULE_DEST="$REPO_ROOT/$DEST_DIR/$MODULE_SCRIPT"
OLD_MODULE_DEST="$REPO_ROOT/$DEST_DIR/$OLD_MODULE_SCRIPT"
CODEX_HOOK_DEST="$REPO_ROOT/$CODEX_DEST_DIR/$HOOK_SCRIPT"
CODEX_MODULE_DEST="$REPO_ROOT/$CODEX_DEST_DIR/$MODULE_SCRIPT"
RUNNER_DEST="$REPO_ROOT/$CODEX_DEST_DIR/$RUNNER_SCRIPT"
OLD_RUNNER_DEST="$REPO_ROOT/$OLD_RUNNER_DIR/$RUNNER_SCRIPT"
CODEX_HOOKS="$REPO_ROOT/.codex/hooks.json"
SETTINGS="$REPO_ROOT/.claude/settings.json"

[[ "$AGENT" == "codex" || "$SOURCE" != "$DEST" ]] ||
  die "source and destination are the same file; run this from the target repository, not from its own source repository"

# ---------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------

# A path as the report shows it: relative to the repository root.
rel() { echo "${1#"$REPO_ROOT"/}"; }

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
# describe_drift <source> <installed>
describe_drift() {
  local source="$1" dest="$2" missing extra
  missing="$(diff "$source" "$dest" | grep -c '^<' || true)"
  extra="$(diff "$source" "$dest" | grep -c '^>' || true)"
  echo "  differs: the installed copy is missing $missing line(s) the source has,"
  echo "           and carries $extra line(s) the source does not"
  echo "  hashes:  source $(hash_of "$source"), installed $(hash_of "$dest")"
}

# The same three states for every copy, so the companions are reported as
# loudly as the one people remember to look at.
# report_copy <label> <source> <installed>
report_copy() {
  local label="$1" source="$2" dest="$3"
  if [[ ! -f "$dest" ]]; then
    echo "$label NOT INSTALLED at $(rel "$dest")"
    return 1
  elif cmp -s "$source" "$dest"; then
    echo "$label current at $(rel "$dest") ($(hash_of "$source"))"
    return 0
  else
    echo "$label DRIFTED at $(rel "$dest")"
    describe_drift "$source" "$dest"
    return 1
  fi
}

# Which registrations name this hook, in the spelling WIRED_REGISTRATIONS uses.
# Wiring drift is its own failure: a current script reached by three events does
# nothing on the fourth, which is exactly how a typed slash command went
# unlabeled while the file was fine.
#
# A matcher is a pattern, so a group whose matcher is Skill|Agent counts for
# both. A group with no matcher on PreToolUse matches every tool, and counts
# for both as well.
wired_registrations() {
  [[ -f "$SETTINGS" ]] || return 0
  jq -r --arg name "$HOOK_SCRIPT" '
    (.hooks // {})
    | to_entries[]
    | .key as $event
    | (.value | if type == "array" then .[] else empty end)
    | select([(.hooks // [])[] | (.command? // "") | contains($name)] | any)
    | if $event == "PreToolUse"
      then ((.matcher // "") | if . == "" or . == "*" then "Skill|Agent" else . end
            | split("|")[] | "PreToolUse(\(.))")
      else $event
      end
  ' "$SETTINGS" 2>/dev/null | sort -u
}

report_wiring() {
  local found missing_events="" e
  found="$(wired_registrations | tr '\n' ' ')"
  for e in $WIRED_REGISTRATIONS; do
    case " $found " in *" $e "*) ;; *) missing_events="$missing_events $e" ;; esac
  done
  if [[ -z "$missing_events" ]]; then
    echo "wiring:   all four events reference the hook"
  else
    echo "wiring:   NOT WIRED for$missing_events in .claude/settings.json"
    return 1
  fi
}

# Codex wiring that names the old runner path runs nothing once the file is
# gone, so it fails --check and earns a warning from an install.
old_runner_is_wired() {
  [[ -f "$CODEX_HOOKS" ]] && grep -qF "$OLD_RUNNER_DIR/$RUNNER_SCRIPT" "$CODEX_HOOKS"
}

# ---------------------------------------------------------------------
# --check: one function per agent, plus the old runner every value checks
# ---------------------------------------------------------------------

check_claude() {
  local failed=0
  report_copy "script:  " "$SOURCE" "$DEST" || failed=1
  if [[ -f "$OLD_MODULE_DEST" ]]; then
    echo "module:   OLD COPY at $(rel "$OLD_MODULE_DEST")"
    failed=1
  fi
  report_copy "module:  " "$MODULE_SOURCE" "$MODULE_DEST" || failed=1
  report_wiring || failed=1
  return "$failed"
}

check_codex() {
  local failed=0
  report_copy "codex runner:" "$RUNNER_SOURCE" "$RUNNER_DEST" || failed=1
  report_copy "codex script:" "$SOURCE" "$CODEX_HOOK_DEST" || failed=1
  report_copy "codex module:" "$MODULE_SOURCE" "$CODEX_MODULE_DEST" || failed=1
  return "$failed"
}

check_old_runner() {
  local failed=0
  if [[ -f "$OLD_RUNNER_DEST" ]]; then
    echo "old runner: OLD COPY at $(rel "$OLD_RUNNER_DEST")"
    failed=1
  fi
  if old_runner_is_wired; then
    echo "old runner: .codex/hooks.json still names $OLD_RUNNER_DIR/$RUNNER_SCRIPT; point it at $CODEX_DEST_DIR/$RUNNER_SCRIPT"
    failed=1
  fi
  return "$failed"
}

if [[ "$CHECK_ONLY" == true ]]; then
  check_failed=false
  for agent in "${AGENTS[@]}"; do
    "check_$agent" || check_failed=true
  done
  check_old_runner || check_failed=true

  if [[ "$check_failed" == true ]]; then
    echo
    echo "Run this installer with --agent $AGENT and without --check to repair what is listed above."
    exit 1
  fi
  exit 0
fi

# ---------------------------------------------------------------------
# Install: copies first, then the wiring
# ---------------------------------------------------------------------
#
# The script lands before the wiring, and the order matters. Stopping between
# them leaves a file nothing calls, which is inert. The reverse order would
# leave wiring pointing at a script that is not there, which labels nothing.
# The guard in the wired command keeps that state quiet rather than noisy, and
# quiet is not the same as working, so the order still stands.

# install_state <source> <installed>: what a copy is about to become
install_state() {
  if [[ -f "$2" ]] && cmp -s "$1" "$2"; then
    echo "already current"
  elif [[ -f "$2" ]]; then
    echo "updated"
  else
    echo "installed"
  fi
}

# install_copy <label> <source> <installed>: copy one file and report what changed
install_copy() {
  local label="$1" source="$2" dest="$3" state
  state="$(install_state "$source" "$dest")"
  # Said BEFORE the copy, because afterwards the evidence is gone. A locally
  # patched copy is the case this exists for: the run still overwrites, and now
  # the report says what it overwrote.
  if [[ "$state" == "updated" ]]; then
    describe_drift "$source" "$dest"
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$source" "$dest"
  if [[ "$dest" == *.sh ]]; then
    chmod +x "$dest"
  fi
  echo "$label $state at $(rel "$dest") ($(hash_of "$dest"))"
}

# Set by wire_claude_settings, and global only so the EXIT trap can reach it.
SETTINGS_TMP=""
trap 'rm -f "$SETTINGS_TMP"' EXIT

# Patch .claude/settings.json so every registration in WIRED_REGISTRATIONS runs
# the hook, then report what changed.
wire_claude_settings() {
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
  local hook_command original settings_existed backup jq_program
  hook_command='d="${CLAUDE_PROJECT_DIR:-}"; test -n "$d" || exit 0; s="$(git -C "$d" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; test -n "$s" || exit 0; s="${s%/.git}/'"$DEST_DIR/$HOOK_SCRIPT"'"; test -x "$s" && exec "$s" || exit 0'

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

  # Per registration: repoint any entry that already names this hook, otherwise
  # append one to the group whose matcher matches, otherwise add that group.
  # Rewriting in place is what makes a second run a repair rather than a
  # duplication.
  #
  # "Already names this hook" is asked per matcher, because PreToolUse carries two
  # registrations. A matcher is a pattern, so a group whose matcher is Skill|Agent
  # already serves both and gains nothing. A group is never widened: one that
  # holds somebody else's hook under Skill keeps firing on Skill alone.
  #
  # Single-quoted on purpose: $cmd, $name, $pre, $agent, $prompt, $stop, and
  # $subagent_stop are jq variables fed by the --arg flags below, and letting
  # bash expand them first would substitute empty strings into the program.
  # shellcheck disable=SC2016
  jq_program='
  def entry($msg): {type: "command", command: $cmd, statusMessage: $msg};

  def is_ours: (.command? // "") | contains($name);

  def patched($msg):
    .type = "command"
    | .command = $cmd
    | if has("statusMessage") then . else .statusMessage = $msg end;

  def serves($matcher):
    $matcher == null
    or ((.matcher // "") | . == "" or . == "*" or (split("|") | index($matcher) != null));

  def wire($event; $matcher; $msg):
    (.hooks[$event] // []) as $groups
    | if [$groups[] | select(serves($matcher)) | (.hooks // [])[] | is_ours] | any
      then
        .hooks[$event] = [
          $groups[]
          | if serves($matcher) and ([(.hooks // [])[] | is_ours] | any)
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
  | wire("PreToolUse"; "Agent"; $agent)
  | wire("UserPromptSubmit"; null; $prompt)
  | wire("Stop"; null; $stop)
  | wire("SubagentStop"; null; $subagent_stop)
  '

  SETTINGS_TMP="$(mktemp "${TMPDIR:-/tmp}/settings.json.XXXXXX")"

  printf '%s' "$original" |
    jq --arg cmd "$hook_command" \
       --arg name "$HOOK_SCRIPT" \
       --arg pre "$PRE_MESSAGE" \
       --arg agent "$AGENT_MESSAGE" \
       --arg prompt "$PROMPT_MESSAGE" \
       --arg stop "$STOP_MESSAGE" \
       --arg subagent_stop "$SUBAGENT_STOP_MESSAGE" \
       "$jq_program" >"$SETTINGS_TMP" ||
    die "jq could not patch the settings (its own error is above); $SETTINGS is untouched"

  # Belt and braces: jq exiting 0 should mean valid JSON on stdout, and an empty
  # file here would mean the write failed in a way that leaves no error behind.
  [[ -s "$SETTINGS_TMP" ]] || die "the patch produced an empty file; $SETTINGS is untouched"
  jq -e . "$SETTINGS_TMP" >/dev/null 2>&1 || die "the patch produced invalid JSON; $SETTINGS is untouched"

  # The backup is taken here rather than earlier, so a run that changes nothing
  # leaves no backup file behind to explain.
  if [[ "$settings_existed" == true ]] && cmp -s "$SETTINGS_TMP" "$SETTINGS"; then
    echo "settings:    already wired in .claude/settings.json"
    echo "backup:      none, the wiring was already in place"
  elif [[ "$settings_existed" == true ]]; then
    backup="$SETTINGS.bak.$(date +%Y%m%d-%H%M%S)"
    cp "$SETTINGS" "$backup"
    cp "$SETTINGS_TMP" "$SETTINGS"
    echo "settings:    wired in .claude/settings.json"
    echo "backup:      $(basename "$backup")"
  else
    mkdir -p "$(dirname "$SETTINGS")"
    cp "$SETTINGS_TMP" "$SETTINGS"
    echo "settings:    created and wired in .claude/settings.json"
    echo "backup:      none, the file did not exist until now"
  fi
}

install_claude() {
  install_copy "hook script:" "$SOURCE" "$DEST"
  install_copy "hook module:" "$MODULE_SOURCE" "$MODULE_DEST"
  if [[ -f "$OLD_MODULE_DEST" ]]; then
    rm -f "$OLD_MODULE_DEST"
    echo "old module:  removed from $(rel "$OLD_MODULE_DEST")"
  fi
  wire_claude_settings
}

install_codex() {
  install_copy "codex runner:" "$RUNNER_SOURCE" "$RUNNER_DEST"
  install_copy "codex script:" "$SOURCE" "$CODEX_HOOK_DEST"
  install_copy "codex module:" "$MODULE_SOURCE" "$CODEX_MODULE_DEST"
}

# The runner has no place in .claude/scripts/ under any --agent value. It goes
# even when .codex/hooks.json still names it: Codex then runs nothing until its
# wiring is fixed, and the warning says what to change.
remove_old_runner() {
  if [[ -f "$OLD_RUNNER_DEST" ]]; then
    rm -f "$OLD_RUNNER_DEST"
    echo "old runner:  removed from $(rel "$OLD_RUNNER_DEST")"
  fi
  if old_runner_is_wired; then
    echo "old runner:  WARNING: .codex/hooks.json still names $OLD_RUNNER_DIR/$RUNNER_SCRIPT,"
    echo "             so Codex labels nothing until it names $CODEX_DEST_DIR/$RUNNER_SCRIPT"
  fi
}

explain_claude() {
  echo
  echo "The four events now referencing the hook:"
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
  echo "Commit .claude/settings.json, $DEST_DIR/$HOOK_SCRIPT and $DEST_DIR/$MODULE_SCRIPT"
  echo "to share the Claude hook with the repo."
}

explain_codex() {
  echo
  echo "Commit $CODEX_DEST_DIR/ to share the Codex files with the repo."
  echo "The Codex runner needs its own entries in .codex/hooks.json, pointing at"
  echo "$CODEX_DEST_DIR/$RUNNER_SCRIPT; docs/PORTABLE-HOOKS.md has them."
}

echo "repository:  $REPO_ROOT"
echo "agent:       $AGENT"
for agent in "${AGENTS[@]}"; do
  "install_$agent"
done
remove_old_runner
for agent in "${AGENTS[@]}"; do
  "explain_$agent"
done
