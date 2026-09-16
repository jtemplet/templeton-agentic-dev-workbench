#!/bin/sh
# tadw - style-core hook wrapper
#
# Usage: run-hook.sh <script-path> <fallback-text> [script-args...]
#
# Runs a hook script on bun when bun is on PATH, and on node otherwise. Makes
# failure VISIBLE (emits <fallback-text>) instead of the silent no-op a bare
# `node ...; exit 0` produces when the runtime is missing.
#
# Any arguments after <fallback-text> are passed through to the script. The
# SessionStart payload exceeds Claude Code's 10,000-character per-hook cap, so it
# is emitted by several manifest entries that differ only in a payload index.
#
# Why the off-switch is re-implemented here. It must be honored even when no
# JavaScript runtime is available, which is precisely when runtime.js
# isDisabled() cannot be consulted. That forces a second implementation outside
# JavaScript. Two things keep the copies honest:
#
#   1. The check runs BEFORE the runtime is spawned, so the off-switch behaves
#      identically whether the runtime works, fails, or is absent. There is no
#      missing-runtime path that skips it.
#   2. hooks/test-hooks.js asserts this file and runtime.js agree across a
#      matrix of env values and the flag file.
#
# Always exits 0: a broken hook must never block a session.

set -u

script=$1
fallback=$2
shift 2

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
  # exists AND no runtime works, where the marker would be emitted despite the flag.
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

# Pin the two variables runtime.js reads, so the PROJECT cannot set them.
#
# bun loads the current directory's .env into its own environment; node does
# not. Both names below are normally unset in a session, and an unset variable
# is exactly what a .env entry fills, so under bun alone a project could silence
# the core or move the flag-file lookup, exiting 0 with neither the core nor the
# marker to show for it. That is the silent no-op this wrapper exists to
# eliminate, reached by a new door.
#
# A real environment variable beats a .env entry, so exporting the session's own
# values closes the door on every bun version and on both platforms. Not
# `bun --no-env-file`: it arrived in bun 1.3.3, and an older bun answers an
# unknown flag by printing its help and exiting 0 WITHOUT running the script,
# which would inject that help text into the session and emit no marker. The
# wrapper cannot even detect that, because bun exits 0 on an unknown flag.
#
# `on` stands in for unset. It has to be non-empty: assigning an empty string to
# an environment variable in PowerShell deletes it, which would hand .env the
# unset variable back on Windows. Any value that is not off/0/false enables.
export TADW_STYLE_CORE="${TADW_STYLE_CORE:-on}"

# Resolved from the same expression is_disabled() uses, so the shell copy and
# the JS copy read one directory.
#
# Skipped when HOME is unset, which leaves one case open: HOME unset AND the
# runtime is bun AND the project's .env sets CLAUDE_CONFIG_DIR. The flag-file
# lookup then follows .env for the JS copy alone. Closing it needs some value to
# export, and both candidates cost more than the hole. `/.claude` is what this
# script's own is_disabled() reads, but os.homedir() falls back to the password
# database, so exporting it would stop node finding a flag file in the real home
# directory; a path that cannot exist does the same. A flag file the user really
# set outranks a .env entry they may never have read.
if [ -n "${HOME:-}" ]; then
  export CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
fi

# The runtime is chosen by presence, never by failure. A bun that exits non-zero
# is NOT retried on node: the script would run twice, and a partial first write
# would repeat whatever stdout it had already emitted. `command -v` is a shell
# builtin, so this keeps the wrapper free of external commands.
if command -v bun > /dev/null 2>&1; then
  runtime=bun
else
  runtime=node
fi

if ! "$runtime" "$script" "$@"; then
  printf '%s\n' "$fallback"
fi

exit 0
