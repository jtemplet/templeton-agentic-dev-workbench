#!/usr/bin/env node
// tadw - SessionStart hook
//
// Injects the universal style core plus the response style into every
// new/resumed/cleared/compacted/forked session as raw stdout context. The
// response style is parent-session only (see subagent-start.js for why).
// Off-switch respected. Errors are swallowed so a hook failure never blocks
// session start.
//
// Usage: session-start.js [payload-index]
//
// Claude Code caps each hook output string at 10,000 characters, so the combined
// 20,275-character payload cannot ship from one entry. It is split across
// several manifest entries that differ only in this index; Claude receives the
// additionalContext of every hook that matched the event. An index past the end
// emits nothing, which keeps the manifest safe when the documents shrink.
//
// getSessionStartPayloads() decides how many parts there are. If it ever returns
// more than the manifest wires, the tail would be dropped in silence, so
// hooks/test-hooks.js asserts the two counts agree.

const { isDisabled, writeHookOutput } = require('./runtime');
const { getSessionStartPayloads } = require('./preamble');

try {
  if (!isDisabled()) {
    const index = Number.parseInt(process.argv[2], 10) || 0;
    const payloads = getSessionStartPayloads();
    if (index >= 0 && index < payloads.length) {
      writeHookOutput('SessionStart', payloads[index]);
    }
  }
} catch (e) {
  // Silent fail - a stdout/read error at hook exit must not surface as a failure.
}

// Deliberately no process.exit(0). Everything above is inside the try/catch, so
// falling off the end already exits 0, and it flushes stdout first. See
// writeHookOutput in runtime.js for why an explicit exit is unsafe here.
