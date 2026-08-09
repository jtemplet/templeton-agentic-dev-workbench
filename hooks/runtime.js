#!/usr/bin/env node
// tadw - shared hook runtime
//
// Centralizes the logic every hook script must share so the copies can never
// drift apart:
//   1. isFeatureDisabled() - the off-switch shape (env var + persistent flag
//                            file), parameterized per feature
//   2. isDisabled()        - the style core's off-switch, in those terms
//   3. writeHookOutput()   - the load-bearing stdout format per hook event
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

// The off-switch shape, parameterized by feature. Two independent paths, either
// one disables the feature:
//   - an env var set to off / 0 / false (it inherits into child hook processes,
//     so one export silences every surface of that feature)
//   - a persistent flag file under $CLAUDE_CONFIG_DIR
//
// Parameterized because the plugin now ships two independent hook features (the
// style core and the acceptance gate). One shared switch would make disabling
// the noisier one also silence the other.
function isFeatureDisabled(envVar, flagFile) {
  const flag = process.env[envVar];
  if (typeof flag === 'string') {
    const normalized = flag.trim().toLowerCase();
    if (normalized === 'off' || normalized === '0' || normalized === 'false') {
      return true;
    }
  }
  try {
    if (fs.existsSync(path.join(getClaudeDir(), flagFile))) {
      return true;
    }
  } catch (e) {
    // Stat failure is not a reason to disable; fall through to enabled.
  }
  return false;
}

// The style core's off-switch: TADW_STYLE_CORE, or .tadw-style-core-off.
// run-hook.sh re-implements this in shell; hooks/test-hooks.js asserts the two
// agree, so change them together.
function isDisabled() {
  return isFeatureDisabled('TADW_STYLE_CORE', FLAG_FILE);
}

// Load-bearing format rule:
//   SessionStart  -> raw text on stdout (native Claude reads it verbatim)
//   SubagentStart -> MUST be wrapped in hookSpecificOutput JSON or native Claude
//                    silently drops the context and the subagent never sees it.
//
// The format is not a way around the size limit. Claude Code caps every hook
// output string at 10,000 characters, stdout and additionalContext alike, and
// replaces anything longer with a preview plus a file path. Splitting the
// payload across manifest entries is what handles that; see
// getSessionStartPayloads in preamble.js and the Output size section of
// docs/HOOKS.md.
//
// No caller of this may follow it with process.exit(). Node's stdout writes are
// synchronous on POSIX pipes but ASYNCHRONOUS on Windows pipes, so an explicit
// exit can discard whatever has not flushed yet. A hook script that falls off
// the end instead exits 0 anyway, and flushes first. That truncation would be
// silent and platform-specific: valid JSON in testing, a half-written object in
// production on Windows.
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
  isFeatureDisabled,
  writeHookOutput,
};
