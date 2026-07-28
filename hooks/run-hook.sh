#!/bin/sh
# tadw - style-core hook wrapper
#
# Usage: run-hook.sh <script-path> <fallback-text>
#
# Runs a hook script, and makes failure VISIBLE (emits <fallback-text>) instead
# of the silent no-op a bare `node ...; exit 0` produces when node is missing.
#
# Why the off-switch is re-implemented here. It must be honoured even when node
# is unavailable, which is precisely when runtime.js isDisabled() cannot be
# consulted. That forces a second implementation outside node. Two things keep
# the copies honest:
#
#   1. The check runs BEFORE node is spawned, so the off-switch behaves
#      identically whether node works, fails, or is absent. There is no
#      node-missing path that skips it.
#   2. hooks/test-hooks.js asserts this file and runtime.js agree across a
#      matrix of env values and the flag file.
#
# Always exits 0: a broken hook must never block a session.

set -u

script=$1
fallback=$2

# Mirror runtime.js isDisabled(): trim, case-insensitive match on off/0/false,
# or the persistent flag file under CLAUDE_CONFIG_DIR (default ~/.claude).
#
# No external commands. This wrapper's whole job is behaving correctly in a
# degraded environment, so it cannot depend on one being present: an earlier
# version lowercased with `tr`, and on a PATH without `tr` the substitution
# failed silently, the value read as empty, and TADW_STYLE_CORE=off was ignored.
# Bracket expressions do the same work using only shell pattern matching.
#
# HOME is defaulted too. Under `set -u` an unset HOME aborted the script, which
# produced neither the core nor the failure marker: the exact silent no-op this
# wrapper exists to eliminate.
is_disabled() {
  value=${TADW_STYLE_CORE:-}
  value=${value#"${value%%[![:space:]]*}"}
  value=${value%"${value##*[![:space:]]}"}

  case $value in
    [Oo][Ff][Ff] | 0 | [Ff][Aa][Ll][Ss][Ee]) return 0 ;;
  esac

  # Known, deliberate divergence: runtime.js resolves the default config dir with
  # os.homedir(), which falls back to the password database when HOME is unset;
  # this uses $HOME only. They differ solely when HOME is unset AND the flag file
  # exists AND node is broken, where the marker would be emitted despite the flag.
  # Closing it needs either an external command (`getent`) or tilde expansion,
  # which dash does not perform with HOME unset. Not worth reintroducing a
  # dependency this wrapper just removed.
  [ -f "${CLAUDE_CONFIG_DIR:-${HOME:-}/.claude}/.tadw-style-core-off" ]
}

# Opted out means silent, including the failure marker. Emitting a
# "FAILED to load" diagnostic to someone who deliberately disabled the hook is
# both noise and a lie: nothing failed, they turned it off.
if is_disabled; then
  exit 0
fi

if ! node "$script"; then
  printf '%s\n' "$fallback"
fi

exit 0
