#!/usr/bin/env node
// tadw - SessionStart hook
//
// Injects the universal style core plus the response style into every
// new/resumed/cleared/compacted session as raw stdout context. The response
// style is parent-session only (see subagent-start.js for why). Off-switch
// respected. Errors are swallowed so a hook failure never blocks session start.

const { isDisabled, writeHookOutput } = require('./runtime');
const { getStyleCorePreamble, getResponseStylePreamble } = require('./preamble');

try {
  if (!isDisabled()) {
    const context = [getStyleCorePreamble(), getResponseStylePreamble()].join('\n\n');
    writeHookOutput('SessionStart', context);
  }
} catch (e) {
  // Silent fail - a stdout/read error at hook exit must not surface as a failure.
}

// Deliberately no process.exit(0). Everything above is inside the try/catch, so
// falling off the end already exits 0, and it flushes stdout first. See
// writeHookOutput in runtime.js for why an explicit exit is unsafe here.
