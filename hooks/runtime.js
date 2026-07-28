#!/usr/bin/env node
// tadw - shared hook runtime
//
// Centralizes the two pieces of logic that BOTH hook scripts must share so they
// can never drift apart:
//   1. isDisabled()      - the off-switch (env var + persistent flag file)
//   2. writeHookOutput() - the load-bearing stdout format per hook event
//
// Claude-only. No Codex/Copilot branches, no mode tracking.

const fs = require('fs');
const os = require('os');
const path = require('path');

const FLAG_FILE = '.tadw-style-core-off';

// CLAUDE_CONFIG_DIR overrides ~/.claude, matching Claude Code itself. Resolved
// here so both session-start.js and subagent-start.js agree on the flag path.
function getClaudeDir() {
  return process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
}

function getFlagPath() {
  return path.join(getClaudeDir(), FLAG_FILE);
}

// Off-switch. Two independent paths, either one disables both surfaces:
//   - env var TADW_STYLE_CORE set to off / 0 / false (inherited by the subagent
//     hook process, so one export silences session AND subagent injection)
//   - a persistent flag file at $CLAUDE_CONFIG_DIR/.tadw-style-core-off
function isDisabled() {
  const flag = process.env.TADW_STYLE_CORE;
  if (typeof flag === 'string') {
    const normalized = flag.trim().toLowerCase();
    if (normalized === 'off' || normalized === '0' || normalized === 'false') {
      return true;
    }
  }
  try {
    if (fs.existsSync(getFlagPath())) {
      return true;
    }
  } catch (e) {
    // Stat failure is not a reason to disable; fall through to enabled.
  }
  return false;
}

// Load-bearing format rule:
//   SessionStart  -> raw text on stdout (native Claude reads it verbatim)
//   SubagentStart -> MUST be wrapped in hookSpecificOutput JSON or native Claude
//                    silently drops the context and the subagent never sees it.
function writeHookOutput(event, context) {
  if (event === 'SubagentStart') {
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'SubagentStart',
          additionalContext: context,
        },
      })
    );
    return;
  }
  process.stdout.write(context);
}

module.exports = {
  FLAG_FILE,
  getClaudeDir,
  getFlagPath,
  isDisabled,
  writeHookOutput,
};
