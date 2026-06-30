#!/usr/bin/env node
// templeton-agentic-dev-workbench - SubagentStart hook
//
// SessionStart context is parent-thread only and never reaches spawned
// subagents, so without this every Task-spawned agent runs style-core-unaware.
// Re-injects the same core into each subagent, JSON-wrapped (required by native
// Claude or the context is silently dropped).
//
// The off-switch check MUST run here too - otherwise disabling the session
// preamble would still inject into every subagent.

const { isDisabled, writeHookOutput } = require('./runtime');
const { getStyleCorePreamble } = require('./preamble');

try {
  if (!isDisabled()) {
    writeHookOutput('SubagentStart', getStyleCorePreamble());
  }
} catch (e) {
  // Silent fail - a stdout/read error at hook exit must not surface as a failure.
}

process.exit(0);
