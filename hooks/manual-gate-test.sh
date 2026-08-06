#!/bin/sh
# tadw - manual drive of the acceptance gate
#
# Usage: ./hooks/manual-gate-test.sh
#
# Layer 1 of testing the gate: given the real hook payloads, does
# acceptance-gate.js arm, block exactly once, and disarm? Deterministic, with no
# Claude Code involved.
#
# hooks/test-hooks.js asserts the same guarantees from inside the Node suite.
# This script exists for the other direction: when the gate misbehaves in a live
# session, run it to see which step diverges, with the payloads visible and the
# flag file on disk where you can look at it.
#
# SCOPE. This runs against the WORKING TREE, not the installed plugin, and it
# speaks to acceptance-gate.js directly rather than through Claude Code. A green
# run says nothing about whether Claude Code fires the hooks, nor about whether
# the model then loads the skill. See "Acceptance gate" in AGENTS.md for those.
#
# ISOLATION. The flag path derives from os.tmpdir(), which honors TMPDIR, so this
# points TMPDIR at a scratch directory removed on exit. It therefore cannot arm,
# consume, or delete the flag of a real session running in parallel.
#
# Unlike the hooks themselves, this fails LOUDLY: it is a test tool, and a
# missing node here means the run proved nothing.

set -u

gate=$(dirname "$0")/acceptance-gate.js
sid=manual-gate-test

command -v node >/dev/null 2>&1 || { echo "node not found on PATH" >&2; exit 1; }
[ -f "$gate" ] || { echo "gate script not found: $gate" >&2; exit 1; }

TMPDIR=$(mktemp -d) || { echo "could not create a scratch TMPDIR" >&2; exit 1; }
export TMPDIR
flag=$TMPDIR/tadw-acceptance-$sid.flag
trap 'rm -rf "$TMPDIR"' EXIT INT TERM

post='{"hook_event_name":"PostToolUse","tool_name":"Skill","tool_input":{"skill":"tadw:fresh-eyes-cr"},"session_id":"'$sid'"}'
stop='{"hook_event_name":"Stop","session_id":"'$sid'"}'

drive() { printf '%s' "$1" | node "$gate"; }

passed=0
failed=0

ok() {
  passed=$((passed + 1))
  echo "  ok   - $1"
}

fail() {
  failed=$((failed + 1))
  echo "  FAIL - $1"
  echo "         $2"
}

echo "acceptance gate, driven by hand:"

# 1. Arming must say nothing. A PostToolUse hook that writes to stdout on every
#    Skill call is the noisy failure mode.
out=$(drive "$post")
if [ -z "$out" ]; then
  ok "arming is silent"
else
  fail "arming is silent" "got: $out"
fi

# 2. The flag is the whole state the two events share.
if [ -f "$flag" ]; then
  ok "flag written to \$TMPDIR"
else
  fail "flag written to \$TMPDIR" "expected: $flag"
fi

# 3. The block must name the skill to load, or it blocks on a dead end.
out=$(drive "$stop")
case $out in
  *'"decision":"block"'*verify-acceptance*)
    ok "Stop emits decision=block naming verify-acceptance" ;;
  *)
    fail "Stop emits decision=block naming verify-acceptance" "got: ${out:-<empty>}" ;;
esac

# 4. The load-bearing loop guard. A Stop hook that blocks without consuming its
#    flag traps the session, and the user cannot escape it from inside.
out=$(drive "$stop")
if [ ! -f "$flag" ] && [ -z "$out" ]; then
  ok "second Stop is silent (flag consumed)"
elif [ -f "$flag" ]; then
  fail "second Stop is silent (flag consumed)" "flag survived the block: $flag"
else
  fail "second Stop is silent (flag consumed)" "got: $out"
fi

# 5. A flag from a session that died before its Stop fired must be discarded,
#    not spent on an unrelated turn a day later. node does the backdating: it is
#    already required here, and `touch -t` spells timestamps differently on BSD
#    and GNU.
drive "$post" >/dev/null
if [ -f "$flag" ]; then
  node -e 'const t = (Date.now() - 25 * 3600 * 1000) / 1000; require("fs").utimesSync(process.argv[1], t, t)' "$flag"
  out=$(drive "$stop")
  if [ -z "$out" ] && [ ! -f "$flag" ]; then
    ok "stale flag (>24h) is discarded, not spent"
  elif [ -n "$out" ]; then
    fail "stale flag (>24h) is discarded, not spent" "a 25h-old flag still blocked: $out"
  else
    fail "stale flag (>24h) is discarded, not spent" "stale flag was not cleaned up: $flag"
  fi
else
  fail "stale flag (>24h) is discarded, not spent" "could not re-arm the gate to set up this case"
fi

total=$((passed + failed))
echo
if [ "$failed" -eq 0 ]; then
  echo "$passed/$total passed. Flags cleaned up."
else
  echo "$passed/$total passed, $failed failed."
fi

[ "$failed" -eq 0 ]
