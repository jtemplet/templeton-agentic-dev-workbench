#!/usr/bin/env bash
# Claude Code hook: label the bead a skill invocation acts on.
#
# Wired to two events and dispatches on hook_event_name:
#
#   PreToolUse (matcher Skill)  Decides what a skill invocation means.
#   Stop                        Resolves labels that needed an outcome.
#
# Three modes, because a PreToolUse hook fires BEFORE the skill runs.
# Measured: the PostToolUse hook for the same call fires ~30ms later, so
# it is equally blind. Only Stop fires after the work.
#
#   apply   The label describes the invocation itself, so it is written
#           immediately. /simplify, /code-review, /tadw:fresh-eyes-cr.
#
#   gate    The label describes an outcome that leaves a readable
#           artifact. /qa writes .gstack/qa-reports/*.md. PreToolUse
#           drops a pending marker; Stop reads the report and applies
#           the label only if the report is newer than the marker and
#           clears the gate. Deterministic, no model involvement.
#
#           This repository has no .gstack/ and /qa is a gstack skill,
#           so gate mode is dormant here: the marker is written and Stop
#           finds no report, leaving it to expire at MARKER_TTL_SECONDS.
#           It is retained rather than deleted because /qa is invocable
#           from any project once gstack is installed, and a browser QA
#           run in this repository would then be graded correctly. This
#           repository's own QA path is /tadw:quality-gates, which is
#           report-only prose and therefore uses inject mode.
#
#   inject  The label describes an outcome with no artifact.
#           /verify-acceptance is report-only and its verdict exists
#           solely in prose, so grepping for it would be string-matching
#           against output formatting that can drift. PreToolUse emits
#           an instruction naming the bead, the gate, and the command,
#           and Claude applies the label at the end. Weaker than gate,
#           and honest about being weaker.
#
# Every failure path logs to stderr and exits 0, so a skill runs whether
# or not the bead could be labeled. Only inject mode writes to stdout,
# and only well-formed hook JSON.

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

log() { echo "[bead-label] $*" >&2; }
quiet_exit() { exit 0; }

# ---------------------------------------------------------------------
# Shared setup
# ---------------------------------------------------------------------

# Sets REPO_ROOT, MAIN_ROOT, MARKER_DIR. Exits when
# not usable.
init_repo() {
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || quiet_exit
  cd "$REPO_ROOT" || quiet_exit


  # MAIN_ROOT is the main checkout, which is where the tracker lives. A worktree
  # has its own .beads/ copy, and work done from one must still land in the
  # canonical tracker.
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

# Refresh the export rather than commit it. The label lives in a gitignored bd
# database, and .beads/issues.jsonl is a passive export bd never refreshes on
# its own: committing it would carry a stale file into the diff, while leaving
# it alone would make the label invisible to bv and Manifest.
refresh_export() {
  bd export -o "$BEADS_FILE" >/dev/null 2>&1 \
    || log "export refresh failed; bv and Manifest will lag"
}

# ---------------------------------------------------------------------
# Bead resolution
# ---------------------------------------------------------------------

# Bead ids here range from a four-character suffix to a full slug, so
# shape alone cannot tell an id from an ordinary hyphenated word. Every
# candidate is verified against the tracker; the pattern only narrows
# the search. Longest first, so a slug id beats its own prefix.
resolve_bead() {
  local args="$1" branch="$2" sources pr_id pr_json candidates candidate found id
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

  candidates="$(echo "$sources" \
    | grep -oE '[a-z][a-z0-9]*(-[a-z0-9]+)+(\.[0-9]+)*' \
    | awk '{ print length, $0 }' \
    | sort -rn -k1,1 \
    | cut -d' ' -f2- \
    | awk '!seen[$0]++')"
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

handle_pre() {
  local payload="$1" skill label mode gate args branch

  skill="$(echo "$payload" | jq -r '.tool_input.skill // empty' 2>/dev/null || true)"
  [[ -z "$skill" ]] && quiet_exit

  # These are SKILL names, never command names. The payload field is
  # tool_input.skill, so a slash command reaches this map only under the
  # name of the skill it invokes. Where the two differ the command name
  # never matches: /tadw:fresh-eyes-cr invokes tadw:review-fresh-eyes,
  # and /tadw:code-review dispatches through the code-reviewer agent to
  # a per-language review skill. Before adding an entry, confirm the
  # name against the plugin's skills/ directory rather than its
  # commands/ directory.
  #
  # Both the plugin-qualified and bare forms, since the payload may
  # carry either depending on how the skill was resolved.
  case "$skill" in
    simplify|tadw:code-simplify)
      label="simplified"; mode="apply" ;;
    code-review|code-review:code-review|\
    review-fresh-eyes|tadw:review-fresh-eyes|\
    review-python|tadw:review-python|\
    review-rails|tadw:review-rails|\
    style-frontend|tadw:style-frontend|\
    style-swift|tadw:style-swift|\
    style-go|tadw:style-go|\
    terraform-iac-expert|tadw:terraform-iac-expert|\
    agentic-clean-code|tadw:agentic-clean-code)
      label="reviewed";   mode="apply" ;;
    qa|gstack:qa)
      label="qa-d";       mode="gate" ;;
    quality-gates|tadw:quality-gates)
      label="qa-d";       mode="inject"
      gate="the overall verdict is PASS (INCOMPLETE, NO GATES RAN, and any FAIL or BLOCKED gate all fail this gate)" ;;
    verify-acceptance|tadw:verify-acceptance)
      label="accepted";   mode="inject"
      gate="the final verdict is ACCEPTED, which means every criterion PASS and no gate FAIL (NOT ACCEPTED and INCONCLUSIVE both fail this gate)" ;;
    *) quiet_exit ;;
  esac

  init_repo
  args="$(echo "$payload" | jq -r '.tool_input.args // ""' 2>/dev/null || true)"
  branch="$(git branch --show-current 2>/dev/null || true)"

  resolve_bead "$args" "$branch" || {
    log "no candidate resolved to a bead (branch '$branch')"
    quiet_exit
  }

  if has_label "$RESOLVED_JSON" "$label"; then
    log "$RESOLVED_ID already labeled $label"
    quiet_exit
  fi

  case "$mode" in
    apply)
      add_label "$RESOLVED_ID" "$label"
      ;;
    gate)
      mkdir -p "$MARKER_DIR" 2>/dev/null || quiet_exit
      printf '%s\n%s\n%s\n' "$(date +%s)" "$RESOLVED_ID" "$skill" \
        > "$MARKER_DIR/${label}__${RESOLVED_ID}"
      log "pending $label for $RESOLVED_ID; Stop will check the QA report"
      ;;
    inject)
      # The command in this string is for someone to run later. bd resolves its
      # own workspace, so it is one bare word with no path to quote.
      jq -n --arg ctx "When this /${skill} run is complete, add the \`${label}\` label to bead ${RESOLVED_ID}, but ONLY if ${gate}. If it does not clear that gate, add no label and say so. The command is: bd update ${RESOLVED_ID} --add-label ${label}" \
        '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$ctx}}'
      log "deferred $label for $RESOLVED_ID to the run's verdict"
      ;;
  esac
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

handle_stop() {
  init_repo
  [[ -d "$MARKER_DIR" ]] || quiet_exit

  local marker basename_marker marker_label created bead_id report now
  now="$(date +%s)"
  for marker in "$MARKER_DIR"/*; do
    [[ -e "$marker" ]] || continue

    # Read the label back from the filename, which gate mode writes as
    # "${label}__${id}". Hardcoding "qa-d" here was correct only because gate
    # mode is the sole marker writer and qa-d its only label. It would relabel a
    # second gate-mode entry as qa-d in silence, and the filename already
    # carries the answer.
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
      rm -f "$marker"
      continue
    fi

    # Only a report written after the marker can describe this run.
    report="$(newest_qa_report_after "$marker")"
    [[ -z "$report" ]] && continue   # run still in progress

    if qa_report_passes "$report"; then
      add_label "$bead_id" "$marker_label"
    fi
    rm -f "$marker"
  done
}

# ---------------------------------------------------------------------

payload="$(cat)"
event="$(echo "$payload" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"

case "$event" in
  PreToolUse) handle_pre "$payload" ;;
  Stop)       handle_stop ;;
  *)          quiet_exit ;;
esac

exit 0
