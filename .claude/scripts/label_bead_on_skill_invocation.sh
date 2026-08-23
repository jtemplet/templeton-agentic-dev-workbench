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
    quiet_exit
  }

  if has_label "$RESOLVED_JSON" "$LABEL"; then
    log "$RESOLVED_ID already labeled $LABEL"
    quiet_exit
  fi

  case "$MODE" in
    apply)
      add_label "$RESOLVED_ID" "$LABEL"
      ;;
    gate)
      mkdir -p "$MARKER_DIR" 2>/dev/null || quiet_exit
      printf '%s\n%s\n%s\n' "$(date +%s)" "$RESOLVED_ID" "$skill" \
        > "$MARKER_DIR/${LABEL}__${RESOLVED_ID}"
      log "pending $LABEL for $RESOLVED_ID; Stop will check the run's report"
      ;;
    inject)
      # The command in this string is for someone to run later. bd resolves its
      # own workspace, so it is one bare word with no path to quote.
      jq -n --arg event "$event" --arg ctx "When this /${skill} run is complete, add the \`${LABEL}\` label to bead ${RESOLVED_ID}, but ONLY if ${GATE}. If it does not clear that gate, add no label and say so. The command is: bd update ${RESOLVED_ID} --add-label ${LABEL}" \
        '{hookSpecificOutput:{hookEventName:$event,additionalContext:$ctx}}'
      log "deferred $LABEL for $RESOLVED_ID to the run's verdict"
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

handle_stop() {
  init_repo
  [[ -d "$MARKER_DIR" ]] || quiet_exit

  local marker basename_marker marker_label created bead_id skill report now
  now="$(date +%s)"
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
      rm -f "$marker"
      continue
    fi

    # Only a report written after the marker can describe this run.
    skill="$(sed -n '3p' "$marker" 2>/dev/null)"
    report="$(report_after "$marker" "$skill")"
    [[ -z "$report" ]] && continue   # run still in progress

    if report_passes "$report" "$skill"; then
      add_label "$bead_id" "$marker_label"
    fi
    rm -f "$marker"
  done
}

# ---------------------------------------------------------------------

payload="$(cat)"
event="$(echo "$payload" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"

case "$event" in
  PreToolUse)       handle_pre "$payload" ;;
  UserPromptSubmit) handle_prompt "$payload" ;;
  Stop)             handle_stop ;;
  *)                quiet_exit ;;
esac

exit 0
