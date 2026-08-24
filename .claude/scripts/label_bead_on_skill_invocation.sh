#!/usr/bin/env bash
# Claude Code hook: label the bead a skill invocation acts on.
#
# Wired to three events and dispatches on hook_event_name:
#
#   PreToolUse (matcher Skill)  Claude invoked the Skill tool.
#   UserPromptSubmit            A person typed the slash command, which
#                               calls no tool, so PreToolUse never sees
#                               it. Same flow, keyed on the command name.
#   Stop                        Resolves labels that needed an outcome.
#
# Both entry points converge on run_label_flow, so a skill labels the same
# whichever way it was started.
#
# Three modes, because a PreToolUse hook fires BEFORE the skill runs.
# Measured: the PostToolUse hook for the same call fires ~30ms later, so
# it is equally blind. Only Stop fires after the work.
#
#   apply   The label describes the invocation itself, so it is written
#           immediately. /simplify, /code-review, /tadw:fresh-eyes-cr.
#
#   gate    The label describes an outcome that leaves a readable
#           artifact. /qa writes .gstack/qa-reports/*.md, and
#           /quality-gates writes <git-dir>/quality-gates-report.json
#           carrying its verdict verbatim. PreToolUse drops a pending
#           marker naming the skill; Stop reads that skill's report and
#           applies the label only if the report is newer than the
#           marker and clears the gate. Deterministic, no model
#           involvement.
#
#   inject  The label describes an outcome with no artifact.
#           /verify-acceptance is report-only and its verdict exists
#           solely in prose, so grepping for it would be string-matching
#           against output formatting that can drift. /build is the
#           same: it ends in a "Feature complete" report, and a run that
#           stops at Ground never earns "implemented". PreToolUse emits
#           an instruction naming the bead, the gate, and the command,
#           and Claude applies the label at the end. Weaker than gate,
#           and honest about being weaker.
#
# Every failure path logs to stderr and exits 0, so a skill runs whether
# or not the bead could be labeled. Only inject mode writes to stdout,
# and only well-formed hook JSON.
#
# Because exiting 0 hides an outage, every invocation with a job to do
# also appends its outcome to <git-common-dir>/bead-label.log, and
# `--doctor` answers the same question ahead of time for the current
# branch, writing nothing.

set -uo pipefail

BEADS_FILE=".beads/issues.jsonl"

# What "everything passes" means for a /qa report. Tunable on purpose:
# /qa fixes what it finds, so demanding zero issues found would deny the
# label to a run that did its job. This asks instead that nothing
# serious and nothing unfinished remain.
QA_MAX_CRITICAL=0
QA_MAX_HIGH=0
QA_MAX_DEFERRED=0

# A pending marker older than this is abandoned rather than resolved, so
# a run that never finished cannot label a later unrelated turn.
MARKER_TTL_SECONDS=21600  # 6 hours

# How many candidates resolve_bead will verify. Each one is a bd show
# subprocess on the critical path of every skill start, and the widened
# pattern below offers far more tokens than any branch really carries.
# Twelve sits well above the real branches measured here and still bounds
# the cost of a prose-heavy PR body.
MAX_BEAD_PROBES=12

# The durable log is truncated to its last this-many lines. The hook fires on
# every /simplify and /code-review in a long-lived checkout, so the file has to
# be bounded; a rotation scheme is more machinery than reading back the last
# few hundred outcomes ever needs.
LOG_MAX_LINES=1000

# Deployed copies of this script drift from the source in scripts/, and a log
# line that does not say WHICH copy wrote it cannot tell a stale copy from a
# broken one.
#
# The hash is read from the file at run time rather than stamped in at install
# time. Stamping would make every installed copy differ from its source by
# exactly the line asserting they are the same, which is the drift this exists
# to detect. Reading it costs one subprocess, and only on an invocation that
# already had a job to do.
SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_HASH=""

log() { echo "[bead-label] $*" >&2; }
quiet_exit() { exit 0; }

# Twelve hex characters of the script's own sha256. Cached, since handle_stop
# can log several outcomes in one run. shasum is the macOS spelling and
# sha256sum the GNU one; if neither is there the log says "unknown" rather than
# losing the line.
script_hash() {
  if [[ -z "$SCRIPT_HASH" ]]; then
    SCRIPT_HASH="$( { shasum -a 256 "$SCRIPT_PATH" 2>/dev/null || sha256sum "$SCRIPT_PATH" 2>/dev/null; } | cut -c1-12)"
    [[ -n "$SCRIPT_HASH" ]] || SCRIPT_HASH="unknown"
  fi
  echo "$SCRIPT_HASH"
}

# ---------------------------------------------------------------------
# The durable log
# ---------------------------------------------------------------------
#
# Every failure path here exits 0 by design, so a skill runs whether or not its
# bead could be labeled. That is right, and it is also why a total outage is
# invisible: the only record was stderr, which nothing surfaces in normal use.
# It has now hidden one twice. Between the 2026-08-12 tracker cutover and the
# fix for it, every label attempt logged a failure nobody read and no bead was
# labeled. Then a full build-and-ship session on 2026-08-22 ran three labeled
# skills against an unresolvable branch and shipped the bead unlabeled, found
# afterwards by inspection rather than by anything in the session.
#
# So the outcome also goes somewhere a person can read later. Exiting 0 is
# unchanged; this adds visibility, not a failure mode. One tab-separated line
# per invocation that got as far as HAVING a job to do: timestamp, event,
# skill, branch, resolved id or "unresolved", action, and the hash of the copy
# of this script that wrote it. An unmapped skill writes nothing, since a hook
# correctly declining to label /adr is not an outcome and logging it would bury
# the ones that are.
#
# log_outcome <event> <skill> <branch> <id-or-empty> <action>
log_outcome() {
  [[ -n "${GIT_COMMON:-}" ]] || return 0
  local file="$GIT_COMMON/bead-label.log"
  printf '%s\t%s\t%s\t%s\t%s\t%s\tscript=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "${2:--}" "${3:--}" "${4:-unresolved}" "$5" \
    "$(script_hash)" \
    >> "$file" 2>/dev/null || return 0
  trim_log "$file"
}

trim_log() {
  local file="$1" lines trimmed
  lines="$(wc -l < "$file" 2>/dev/null || echo 0)"
  (( lines > LOG_MAX_LINES )) || return 0
  trimmed="$file.trimming"
  # Written whole and then moved, so a run interrupted mid-trim leaves the log
  # intact rather than half a file.
  if tail -n "$LOG_MAX_LINES" "$file" > "$trimmed" 2>/dev/null; then
    mv "$trimmed" "$file" 2>/dev/null || rm -f "$trimmed" 2>/dev/null
  else
    rm -f "$trimmed" 2>/dev/null
  fi
}

# ---------------------------------------------------------------------
# Shared setup
# ---------------------------------------------------------------------

# Sets REPO_ROOT, MAIN_ROOT, MARKER_DIR. Exits when
# not usable.
init_repo() {
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || quiet_exit
  cd "$REPO_ROOT" || quiet_exit

  GIT_COMMON="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
  MAIN_ROOT="$(dirname "$GIT_COMMON")"

  # bd is the only tracker this hook supports. It takes no --db pin: it resolves
  # one workspace per repository through the git common dir, so it finds the
  # same database from a worktree as from the main checkout.
  local beads_dir="$MAIN_ROOT/.beads"
  [[ -d "$beads_dir" ]] || { log "no beads workspace under $beads_dir"; quiet_exit; }
  local t
  for t in bd jq git; do
    command -v "$t" >/dev/null 2>&1 || { log "$t not on PATH"; quiet_exit; }
  done

  # Markers live inside the git common dir: never tracked, never dirty
  # the tree, and shared across worktrees.
  MARKER_DIR="$GIT_COMMON/pending-bead-labels"
}

has_label() {
  local json="$1" label="$2"
  echo "$json" | jq -e --arg l "$label" \
    '((.[0].labels // .labels) // []) | index($l)' >/dev/null 2>&1
}

add_label() {
  local bead_id="$1" label="$2"
  bd update "$bead_id" --add-label "$label" >/dev/null 2>&1 || {
    log "bd update $bead_id --add-label $label failed"
    return 1
  }
  log "labeled $bead_id $label"
  refresh_export
}

# Leave the working tree exactly as clean as it was found.
#
# .beads/issues.jsonl is a passive export bd never refreshes on its own, and
# committing it would carry a stale file into the diff. So this used to refresh
# it after every label. That cost landed on two other tools, both of which
# refuse to run on a dirty tree: outrigger aborts its pre-flight with "tracked
# files are modified (uncommitted changes)", and /tadw:ship Step 4 found the
# file already modified before its squash-merge and had to back it up and
# discard it. Both fired in the 2026-08-22 fathom session while this hook was
# labeling nothing at all; apply mode runs on every /simplify, /code-review and
# /tadw:fresh-eyes-cr, so a working hook would have collided on every review
# pass.
#
# The default flipped rather than the feature going away. Refreshing an export
# that is ALREADY modified dirties nothing further, so that case still runs.
# bv reads the bd database directly and loses nothing either way. Manifest's
# reader is unconfirmed, and TADW_BEAD_LABEL_EXPORT=1 restores the old behavior
# for it, or for anyone who genuinely needs the file fresh mid-session.
refresh_export() {
  if [[ "${TADW_BEAD_LABEL_EXPORT:-}" != "1" ]] \
    && [[ -z "$(git status --porcelain -- "$BEADS_FILE" 2>/dev/null)" ]]; then
    log "left $BEADS_FILE alone to keep the tree clean (TADW_BEAD_LABEL_EXPORT=1 to refresh it)"
    return 0
  fi
  bd export -o "$BEADS_FILE" >/dev/null 2>&1 \
    || log "export refresh failed; bv and Manifest will lag"
}

# ---------------------------------------------------------------------
# Bead resolution
# ---------------------------------------------------------------------

# Bead ids here range from a bare three-character suffix to a full slug,
# so shape alone cannot tell an id from an ordinary word. Every candidate
# is verified against the tracker; the sources below only narrow the
# search, and bd decides.
#
# Three ordered sources, because the pattern alone was blind to the
# branches this ecosystem actually produces. The pattern used to require
# a hyphen, and outrigger writes outrigger/<short-id>/<slug> where every
# short id in fathom is hyphen-free (zkc.5, e12, 9ma). So the only
# candidate it ever offered from such a branch was the slug, which
# resolves to nothing. Every outrigger branch in that repository went
# unlabeled.
#
#   1. Positional. Segment two of a branch with three or more segments
#      is outrigger's short id verbatim, so it goes first.
#   2. Pattern, widened to make the hyphen optional and admit a leading
#      digit, so zkc.5, e12 and 9ma become candidates at all.
#   3. Cap. At most MAX_BEAD_PROBES candidates, since each one is a
#      bd show subprocess.
#
# Within the pattern's output, id-shaped tokens (carrying a hyphen or a
# dot) rank above bare words, and each group is longest first so a slug
# id beats its own prefix. The two tiers are what keeps the widened
# pattern affordable: it now matches every lowercase word, and a PR body
# of prose would otherwise spend the whole probe budget on words longer
# than the id it is looking for.
resolve_bead() {
  local args="$1" branch="$2" sources pr_id pr_json positional matched candidates candidate found id
  sources="$args"$'\n'"${branch//\// }"

  pr_id="$(echo "$args" | tr ' ' '\n' | awk '
    /^#?[0-9]+$/      { gsub(/#/, ""); print; exit }
    /github\.com.*pull\/[0-9]+/ {
      sub(/.*\/pull\//, ""); sub(/[^0-9].*/, ""); print; exit
    }
  ')"
  if [[ -n "$pr_id" ]] && command -v gh >/dev/null 2>&1; then
    pr_json="$(gh pr view "$pr_id" --json title,headRefName,body 2>/dev/null || true)"
    if [[ -n "$pr_json" ]]; then
      sources+=$'\n'"$(echo "$pr_json" | jq -r '.title, (.headRefName | gsub("/"; " ")), (.body // "")' 2>/dev/null || true)"
    fi
  fi

  positional=""
  if [[ "$(awk -F/ '{ print NF }' <<< "$branch")" -ge 3 ]]; then
    positional="$(cut -d/ -f2 <<< "$branch")"
  fi

  # Sorted on two keys: tier first (1 for id-shaped, 2 for a bare word),
  # then length descending within the tier.
  matched="$(echo "$sources" \
    | grep -oE '[a-z0-9][a-z0-9]*(-[a-z0-9]+)*(\.[0-9]+)*' \
    | awk '{ print ($0 ~ /[-.]/ ? 1 : 2), length, $0 }' \
    | sort -k1,1n -k2,2nr \
    | cut -d' ' -f3-)"

  candidates="$(printf '%s\n%s\n' "$positional" "$matched" \
    | awk 'NF && !seen[$0]++' \
    | head -n "$MAX_BEAD_PROBES")"
  [[ -z "$candidates" ]] && return 1

  while IFS= read -r candidate; do
    [[ -z "$candidate" ]] && continue
    found="$(bd show "$candidate" --json 2>/dev/null || true)"
    [[ -z "$found" ]] && continue
    id="$(echo "$found" | jq -r '((.[0].id // .id) // empty)' 2>/dev/null || true)"
    if [[ -n "$id" ]]; then
      RESOLVED_ID="$id"
      RESOLVED_JSON="$found"
      return 0
    fi
  done <<< "$candidates"
  return 1
}

# ---------------------------------------------------------------------
# PreToolUse
# ---------------------------------------------------------------------

# Sets LABEL, MODE and GATE for a skill name. Returns 1 when unmapped.
#
# These are SKILL names, never command names. The PreToolUse payload field
# is tool_input.skill, so a skill reaches this map under the name it was
# resolved to. Where the command name differs it never matches here:
# /tadw:fresh-eyes-cr invokes tadw:review-fresh-eyes, and /tadw:code-review
# dispatches through the code-reviewer agent to a per-language review
# skill. Before adding an entry, confirm the name against the plugin's
# skills/ directory rather than its commands/ directory. To map a command
# name, use skill_for_command below instead.
#
# Both the plugin-qualified and bare forms, since the payload may carry
# either depending on how the skill was resolved.
classify_skill() {
  local skill="$1"
  GATE=""
  case "$skill" in
    # Ordered the way the work moves: implemented, simplified, reviewed, qa-d, accepted.
    #
    # "implemented" is an outcome, not an invocation: /build stops at Ground
    # when the spec is too thin, and a label applied up front would call that
    # run implemented. So it waits for the run's own "Feature complete" report.
    feature-development|tadw:feature-development)
      LABEL="implemented"; MODE="inject"
      GATE="the run reached its Feature complete report with every acceptance criterion met and its tests passing (a run that stopped at Ground, reported a criterion not met, or ended with a failing test does not clear this gate)" ;;
    simplify|tadw:code-simplify)
      LABEL="simplified"; MODE="apply" ;;
    code-review|code-review:code-review|\
    review-fresh-eyes|tadw:review-fresh-eyes|\
    review-python|tadw:review-python|\
    review-rails|tadw:review-rails|\
    style-frontend|tadw:style-frontend|\
    style-swift|tadw:style-swift|\
    style-go|tadw:style-go|\
    terraform-iac-expert|tadw:terraform-iac-expert|\
    agentic-clean-code|tadw:agentic-clean-code)
      LABEL="reviewed";   MODE="apply" ;;
    # Both leave an artifact Stop can read, one each; the marker records
    # which skill ran, and Stop picks the reader from that.
    qa|gstack:qa|quality-gates|tadw:quality-gates)
      LABEL="qa-d";       MODE="gate" ;;
    verify-acceptance|tadw:verify-acceptance)
      LABEL="accepted";   MODE="inject"
      GATE="the final verdict is ACCEPTED, which means every criterion PASS and no gate FAIL (NOT ACCEPTED and INCONCLUSIVE both fail this gate)" ;;
    *) return 1 ;;
  esac
  return 0
}

# The shared flow, once a skill name is known. $3 names the hook event so
# inject mode can label its own output correctly.
run_label_flow() {
  local skill="$1" args="$2" event="$3" branch

  init_repo
  branch="$(git branch --show-current 2>/dev/null || true)"

  resolve_bead "$args" "$branch" || {
    log "no candidate resolved to a bead (branch '$branch')"
    log_outcome "$event" "$skill" "$branch" "" "wanted $LABEL, no candidate resolved to a bead"
    quiet_exit
  }

  if has_label "$RESOLVED_JSON" "$LABEL"; then
    log "$RESOLVED_ID already labeled $LABEL"
    log_outcome "$event" "$skill" "$branch" "$RESOLVED_ID" "already labeled $LABEL"
    quiet_exit
  fi

  case "$MODE" in
    apply)
      if add_label "$RESOLVED_ID" "$LABEL"; then
        log_outcome "$event" "$skill" "$branch" "$RESOLVED_ID" "applied $LABEL"
      else
        log_outcome "$event" "$skill" "$branch" "$RESOLVED_ID" "FAILED to apply $LABEL"
      fi
      ;;
    gate)
      mkdir -p "$MARKER_DIR" 2>/dev/null || {
        log_outcome "$event" "$skill" "$branch" "$RESOLVED_ID" "FAILED to write a $LABEL marker"
        quiet_exit
      }
      printf '%s\n%s\n%s\ngate\n' "$(date +%s)" "$RESOLVED_ID" "$skill" \
        > "$MARKER_DIR/${LABEL}__${RESOLVED_ID}"
      log "pending $LABEL for $RESOLVED_ID; Stop will check the run's report"
      log_outcome "$event" "$skill" "$branch" "$RESOLVED_ID" "pending $LABEL, Stop reads the report"
      ;;
    inject)
      # A marker beside gate's, and its fourth line is what tells them apart.
      # Stop cannot DECIDE an inject label, because inject mode exists exactly
      # where there is no artifact to read. What it can do is say afterwards
      # whether the label the run was asked for ever appeared. Without this a
      # dropped inject label leaves no trace at all: the instruction went to
      # Claude, Claude did not act on it, and nothing recorded a debt.
      if mkdir -p "$MARKER_DIR" 2>/dev/null; then
        printf '%s\n%s\n%s\ninject\n' "$(date +%s)" "$RESOLVED_ID" "$skill" \
          > "$MARKER_DIR/${LABEL}__${RESOLVED_ID}"
      else
        log "could not record that $LABEL was asked for; Stop will not miss it"
      fi
      # The command in this string is for someone to run later. bd resolves its
      # own workspace, so it is one bare word with no path to quote.
      jq -n --arg event "$event" --arg ctx "When this /${skill} run is complete, add the \`${LABEL}\` label to bead ${RESOLVED_ID}, but ONLY if ${GATE}. If it does not clear that gate, add no label and say so. The command is: bd update ${RESOLVED_ID} --add-label ${LABEL}" \
        '{hookSpecificOutput:{hookEventName:$event,additionalContext:$ctx}}'
      log "deferred $LABEL for $RESOLVED_ID to the run's verdict"
      log_outcome "$event" "$skill" "$branch" "$RESOLVED_ID" "deferred $LABEL to the run's verdict"
      ;;
  esac
}

handle_pre() {
  local payload="$1" skill args

  skill="$(echo "$payload" | jq -r '.tool_input.skill // empty' 2>/dev/null || true)"
  [[ -z "$skill" ]] && quiet_exit
  classify_skill "$skill" || quiet_exit

  args="$(echo "$payload" | jq -r '.tool_input.args // ""' 2>/dev/null || true)"
  run_label_flow "$skill" "$args" PreToolUse
}

# ---------------------------------------------------------------------
# UserPromptSubmit
# ---------------------------------------------------------------------

# Maps a slash-command name to the skill it invokes, printing the skill
# name. Returns 1 when the command is not one we label.
#
# This map exists because PreToolUse cannot see a typed slash command. It
# fires on the Skill TOOL, and typing /foo calls no tool, so without this
# the run finishes unlabeled. Worse for quality-gates and
# verify-acceptance, whose command files tell the reader to open SKILL.md
# directly rather than invoke the skill by name, making the documented
# path the unlabeled one.
#
# Keep this keyed on COMMAND names, the opposite of classify_skill. Where
# the two differ, only the mapping below is correct.
#
# `ship` and `tadw:ship` are deliberately absent, and this is the record of
# that decision rather than an oversight. /tadw:ship CLOSES the bead, so a
# label applied at the same moment carries no information the closed state does
# not already carry. Adding an entry here would buy a label nobody reads and a
# marker Stop then has to resolve.
skill_for_command() {
  case "$1" in
    # /build is the documented entry point (commands/build.md invokes the
    # skill); the bare skill name also resolves, since no command shadows it.
    build|tadw:build|\
    feature-development|tadw:feature-development) echo "tadw:feature-development" ;;
    simplify|tadw:code-simplify)              echo "tadw:code-simplify" ;;
    code-review|code-review:code-review)      echo "code-review:code-review" ;;
    fresh-eyes-cr|tadw:fresh-eyes-cr)         echo "tadw:review-fresh-eyes" ;;
    qa|gstack:qa)                             echo "gstack:qa" ;;
    quality-gates|tadw:quality-gates)         echo "tadw:quality-gates" ;;
    verify-acceptance|tadw:verify-acceptance) echo "tadw:verify-acceptance" ;;
    *) return 1 ;;
  esac
  return 0
}

handle_prompt() {
  local payload="$1" prompt command skill args

  prompt="$(echo "$payload" | jq -r '.prompt // empty' 2>/dev/null || true)"
  [[ -z "$prompt" ]] && quiet_exit

  # Only a prompt that STARTS with the command counts. A prompt merely
  # mentioning /qa is talking about it, not running it.
  [[ "$prompt" =~ ^[[:space:]]*/([A-Za-z0-9_:-]+)[[:space:]]*(.*)$ ]] || quiet_exit
  command="${BASH_REMATCH[1]}"
  args="${BASH_REMATCH[2]}"

  skill="$(skill_for_command "$command")" || quiet_exit
  classify_skill "$skill" || quiet_exit

  run_label_flow "$skill" "$args" UserPromptSubmit
}

# ---------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------

# Reads a "| Critical | 3 |" style row and prints the count, or nothing
# when the row is absent or unparseable.
report_count() {
  local report="$1" row="$2"
  grep -iE "^\|[[:space:]]*\**${row}\**[[:space:]]*\|" "$report" 2>/dev/null \
    | head -1 \
    | awk -F'|' '{ gsub(/[^0-9]/, "", $3); print $3 }'
}

# Prints the newest QA report written after the marker file $1, or
# nothing. Compares against the marker's own mtime with `-newer`, which
# is POSIX. BSD find rejects `-newermt @<epoch>` outright ("Can't parse
# date/time"), and xargs -r is likewise a GNU extension, so neither is
# safe here.
newest_qa_report_after() {
  local marker="$1" newest="" f
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    if [[ -z "$newest" || "$f" -nt "$newest" ]]; then newest="$f"; fi
  done < <(find .gstack/qa-reports -maxdepth 1 -name 'qa-report-*.md' -type f -newer "$marker" 2>/dev/null)
  [[ -n "$newest" ]] && echo "$newest"
}

# /quality-gates writes one JSON verdict per clone or worktree at
# <git-dir>/quality-gates-report.json. Resolved with --git-dir, never the
# common dir, so a worktree reads its own verdict and not a sibling's.
newest_quality_gates_report_after() {
  local marker="$1" report
  report="$(git rev-parse --path-format=absolute --git-dir 2>/dev/null)/quality-gates-report.json"
  [[ -f "$report" && "$report" -nt "$marker" ]] && echo "$report"
}

# Fails closed: only a verbatim PASS earns the label. FAIL, INCOMPLETE,
# NO GATES RAN, and a file with no readable verdict all leave it off.
quality_gates_report_passes() {
  local report="$1" verdict
  verdict="$(jq -r '.verdict // empty' "$report" 2>/dev/null)"
  if [[ -z "$verdict" ]]; then
    log "could not read a verdict from $report; not labeling"
    return 1
  fi
  if [[ "$verdict" != "PASS" ]]; then
    log "quality-gates verdict $verdict; not labeling"
    return 1
  fi
  log "quality-gates verdict PASS via $report"
  return 0
}

# The marker's third line names the skill, and the skill decides which
# artifact to read. Anything unrecognized falls back to the /qa reader,
# which is what every marker meant before the line was used.
report_after() {
  local marker="$1" skill="$2"
  case "$skill" in
    quality-gates|tadw:quality-gates) newest_quality_gates_report_after "$marker" ;;
    *) newest_qa_report_after "$marker" ;;
  esac
}

report_passes() {
  local report="$1" skill="$2"
  case "$skill" in
    quality-gates|tadw:quality-gates) quality_gates_report_passes "$report" ;;
    *) qa_report_passes "$report" ;;
  esac
}

# Fails closed: an unparseable report never earns the label.
qa_report_passes() {
  local report="$1" crit high deferred
  crit="$(report_count "$report" Critical)"
  high="$(report_count "$report" High)"
  deferred="$(report_count "$report" Deferred)"

  if [[ -z "$crit" || -z "$high" ]]; then
    log "could not parse severity counts from $report; not labeling"
    return 1
  fi
  # A report with no Ship Readiness block has nothing deferred.
  [[ -z "$deferred" ]] && deferred=0

  if (( crit > QA_MAX_CRITICAL || high > QA_MAX_HIGH || deferred > QA_MAX_DEFERRED )); then
    log "QA gate not met (critical=$crit high=$high deferred=$deferred)"
    return 1
  fi
  log "QA gate met (critical=$crit high=$high deferred=$deferred) via $report"
  return 0
}

# Says whether an inject label ever landed. It applies nothing: the run was
# asked to, and either did or did not. Reading the bead is the only way to know,
# since inject mode has no artifact by definition.
resolve_inject_marker() {
  local bead_id="$1" label="$2" skill="$3" branch="$4" found
  found="$(bd show "$bead_id" --json 2>/dev/null || true)"

  # An empty read is not the same as a missing label. bd writes its errors to
  # stderr and leaves stdout empty, so calling that "owed" would report a debt
  # that may not exist.
  if [[ -z "$found" ]]; then
    log "could not read $bead_id to confirm $label"
    log_outcome Stop "$skill" "$branch" "$bead_id" "could not confirm $label, $bead_id would not read"
    return 0
  fi

  if has_label "$found" "$label"; then
    log "$bead_id carries $label; the run applied it"
    log_outcome Stop "$skill" "$branch" "$bead_id" "confirmed $label, the run applied it"
  else
    log "$bead_id was owed $label and does not carry it"
    log_outcome Stop "$skill" "$branch" "$bead_id" "OWED $label, the run never applied it"
  fi
}

handle_stop() {
  init_repo
  [[ -d "$MARKER_DIR" ]] || quiet_exit

  local marker basename_marker marker_label created bead_id skill mode report now branch
  now="$(date +%s)"
  branch="$(git branch --show-current 2>/dev/null || true)"
  for marker in "$MARKER_DIR"/*; do
    [[ -e "$marker" ]] || continue

    # The label comes from the filename, not a constant. Hardcoding qa-d here
    # would silently mislabel any second gate-mode entry as qa-d, and the
    # filename already carries the answer.
    basename_marker="$(basename "$marker")"
    marker_label="${basename_marker%%__*}"
    if [[ -z "$marker_label" || "$marker_label" == "$basename_marker" ]]; then
      log "marker $basename_marker carries no label prefix; discarding"
      rm -f "$marker"
      continue
    fi

    created="$(sed -n '1p' "$marker" 2>/dev/null)"
    bead_id="$(sed -n '2p' "$marker" 2>/dev/null)"
    [[ -z "$created" || -z "$bead_id" ]] && { rm -f "$marker"; continue; }

    if (( now - created > MARKER_TTL_SECONDS )); then
      log "abandoning stale marker $(basename "$marker")"
      log_outcome Stop "$(sed -n '3p' "$marker" 2>/dev/null)" "$branch" "$bead_id" \
        "abandoned $marker_label, the marker outlived its TTL"
      rm -f "$marker"
      continue
    fi

    skill="$(sed -n '3p' "$marker" 2>/dev/null)"

    # A marker written before the mode line existed is a gate marker, which is
    # what every marker meant then.
    mode="$(sed -n '4p' "$marker" 2>/dev/null)"
    [[ -n "$mode" ]] || mode="gate"
    if [[ "$mode" == "inject" ]]; then
      resolve_inject_marker "$bead_id" "$marker_label" "$skill" "$branch"
      rm -f "$marker"
      continue
    fi

    # Only a report written after the marker can describe this run.
    report="$(report_after "$marker" "$skill")"
    [[ -z "$report" ]] && continue   # run still in progress

    if report_passes "$report" "$skill"; then
      if add_label "$bead_id" "$marker_label"; then
        log_outcome Stop "$skill" "$branch" "$bead_id" "applied $marker_label, the report passed"
      else
        log_outcome Stop "$skill" "$branch" "$bead_id" "FAILED to apply $marker_label"
      fi
    else
      log_outcome Stop "$skill" "$branch" "$bead_id" "withheld $marker_label, the report did not pass"
    fi
    rm -f "$marker"
  done
}

# ---------------------------------------------------------------------
# --doctor
# ---------------------------------------------------------------------

# Answers the question the log answers after the fact, before the fact: on this
# branch, right now, would a labeled skill find its bead? It resolves and
# prints, and writes nothing at all: no label, no export, no marker, no log
# line. bd show is the only tracker call it makes, and that is read-only.
#
# The commands below are the ones a person types. Each is put through the same
# skill_for_command and classify_skill the hook uses, so a command that has
# stopped mapping reports "not labeled" here rather than quietly diverging from
# a second list kept in step by hand.
DOCTOR_COMMANDS="build simplify code-review fresh-eyes-cr qa quality-gates verify-acceptance"

run_doctor() {
  local branch command skill

  init_repo
  branch="$(git branch --show-current 2>/dev/null || true)"

  echo "repository: $REPO_ROOT"
  echo "script:     $SCRIPT_PATH ($(script_hash))"
  echo "branch:     ${branch:-<none, detached HEAD>}"

  if ! resolve_bead "" "$branch"; then
    echo "bead:       none. No candidate from this branch resolved to a bead,"
    echo "            so every labeled skill run here would label nothing."
    return 0
  fi

  echo "bead:       $RESOLVED_ID"
  echo "labels:     $(echo "$RESOLVED_JSON" | jq -r '(((.[0].labels // .labels) // []) | join(", ")) | if . == "" then "<none>" else . end' 2>/dev/null || echo "<unreadable>")"
  echo
  echo "What each labeled command would do here:"
  for command in $DOCTOR_COMMANDS; do
    if ! skill="$(skill_for_command "$command")"; then
      printf '  /%-18s not labeled\n' "$command"
      continue
    fi
    if ! classify_skill "$skill"; then
      printf '  /%-18s not labeled (%s is unmapped)\n' "$command" "$skill"
      continue
    fi
    if has_label "$RESOLVED_JSON" "$LABEL"; then
      printf '  /%-18s nothing; %s already carries "%s"\n' "$command" "$RESOLVED_ID" "$LABEL"
    else
      printf '  /%-18s %s "%s"\n' "$command" "$(doctor_verb "$MODE")" "$LABEL"
    fi
  done
}

# What a mode does, in the words a person would use for it.
doctor_verb() {
  case "$1" in
    apply) echo "add" ;;
    gate)  echo "wait for its report, then add" ;;
    *)     echo "ask the run to add" ;;
  esac
}

# ---------------------------------------------------------------------

# Guarded ahead of the payload read on purpose. Everything below blocks on
# stdin, and --doctor is run from a terminal where no hook payload is coming.
if [[ "${1:-}" == "--doctor" ]]; then
  run_doctor
  exit 0
fi

payload="$(cat)"
event="$(echo "$payload" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"

case "$event" in
  PreToolUse)       handle_pre "$payload" ;;
  UserPromptSubmit) handle_prompt "$payload" ;;
  Stop)             handle_stop ;;
  *)                quiet_exit ;;
esac

exit 0
