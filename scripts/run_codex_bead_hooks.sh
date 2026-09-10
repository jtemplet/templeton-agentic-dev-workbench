#!/usr/bin/env bash
# Run the two Beads behaviors that share Codex's UserPromptSubmit event.
#
# Codex runs one command per event group, and two behaviors need the prompt:
# the `bd` context refresh, and the portable bead-labeling hook. This script
# is that one command.

set -uo pipefail

# The event name comes from argv, because .codex/hooks.json already knows it
# at wiring time. Reading it out of the payload instead put `jq` in charge of
# whether the context refresh runs at all: no `jq`, empty event, no branch
# taken, exit 0. The refresh never needed `jq` before, and a machine without
# it would have lost a working behavior in silence. The payload parse stays as
# the fallback for a caller that passes no argument.
payload="$(cat)"
event="${1:-}"
[[ -n "$event" ]] ||
  event="$(printf '%s' "$payload" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"

# The label script sits in one of two places, and this script is copied into
# repositories that use either. Beside this one is the layout of the workbench
# repository and of an installed pair. Under .claude/scripts of the MAIN
# checkout is where install_label_bead_on_skill_invocation.sh puts it, and the
# git common dir resolves there from a linked worktree too.
resolve_label_hook() {
  local script_dir sibling common installed
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || return 1
  sibling="$script_dir/label_bead_on_skill_invocation.sh"
  if [[ -x "$sibling" ]]; then
    printf '%s' "$sibling"
    return 0
  fi
  common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 1
  [[ -n "$common" ]] || return 1
  installed="${common%/.git}/.claude/scripts/label_bead_on_skill_invocation.sh"
  [[ -x "$installed" ]] || return 1
  printf '%s' "$installed"
}

# A label script this cannot find used to return in silence. That is the exact
# failure the label script's own header records hiding two outages: labeling
# stops, and a broken install looks identical to a working one. So the miss
# goes into that script's own log, in its tab-separated shape, with the fields
# this script cannot know left as "-".
log_missing_label_hook() {
  local common file
  common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 0
  [[ -n "$common" ]] || return 0
  file="$common/bead-label.log"
  printf '%s\t%s\t-\t-\tunresolved\tno-label-script\tscript=codex-runner\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${1:--}" >> "$file" 2>/dev/null || return 0
}

run_label_hook() {
  local hook
  hook="$(resolve_label_hook)" || { log_missing_label_hook "$1"; return 0; }
  # Its stdout goes nowhere. Codex validates a UserPromptSubmit hook's stdout
  # against a schema that accepts no unknown keys, and the label script's
  # inject mode writes Claude Code's JSON shape, which Codex would not act on
  # anyway. No label mode is inject today; two were until 2026-09-09, so this
  # does not rest on that holding. Its stderr is left alone, because Codex
  # records it and the durable log is the record that matters.
  printf '%s' "$payload" | "$hook" >/dev/null || true
}

case "$event" in
  UserPromptSubmit)
    # Context refresh first, and it owns stdout for this event.
    if command -v bd >/dev/null 2>&1; then
      printf '%s' "$payload" | bd codex-hook UserPromptSubmit || true
    fi
    run_label_hook UserPromptSubmit
    ;;
  Stop)
    run_label_hook Stop
    ;;
esac

exit 0
