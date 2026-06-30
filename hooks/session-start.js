#!/usr/bin/env node
// templeton-agentic-dev-workbench - SessionStart hook
//
// Injects the universal style core into every new/resumed/cleared/compacted
// session as raw stdout context. Off-switch respected. Errors are swallowed so
// a hook failure never blocks session start.

const { isDisabled, writeHookOutput } = require('./runtime');
const { getStyleCorePreamble } = require('./preamble');

try {
  if (!isDisabled()) {
    writeHookOutput('SessionStart', getStyleCorePreamble());
  }
} catch (e) {
  // Silent fail - a stdout/read error at hook exit must not surface as a failure.
}

process.exit(0);
