#!/usr/bin/env node
// templeton-agentic-dev-workbench - standalone hook test
//
// No dependencies, no package.json: uses only Node built-ins. Run with:
//   node hooks/test-hooks.js
//
// Asserts the load-bearing guarantees of the style-core hooks:
//   1. SessionStart  stdout is the RAW preamble and contains the style-core
//      marker AND the response-style marker (parent sessions get both docs).
//      The response style is sourced from the house-response-style SKILL.md, so
//      its YAML frontmatter must be stripped before injection.
//   2. SubagentStart stdout parses as JSON and
//      hookSpecificOutput.additionalContext contains the style-core preamble
//      + marker, and does NOT contain the response style (orchestrator-facing
//      output must not carry human-facing response rules).
//   3. env off-switch (TADW_STYLE_CORE=off) => both emit EMPTY stdout.
//   4. flag-file off-switch (env unset, flag file present) => both emit EMPTY
//      stdout. This path is invisible to env-var tests, so it is covered here.

const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HOOKS_DIR = __dirname;
const SESSION = path.join(HOOKS_DIR, 'session-start.js');
const SUBAGENT = path.join(HOOKS_DIR, 'subagent-start.js');
const MARKER = '<!-- house-style-core: loaded';
const RESPONSE_MARKER = '<!-- house-response-style: loaded';

// Run a hook script with a controlled environment and return its stdout.
function runHook(scriptPath, env) {
  const result = spawnSync(process.execPath, [scriptPath], {
    encoding: 'utf8',
    env,
    timeout: 5000,
  });
  assert.strictEqual(result.status, 0, `${scriptPath} should exit 0`);
  return result.stdout;
}

// Base env with the off-switch env var explicitly cleared, so flag-file tests
// are not masked by an env var leaking in from the caller's shell.
function enabledEnv(extra = {}) {
  const env = { ...process.env, ...extra };
  delete env.TADW_STYLE_CORE;
  return env;
}

let passed = 0;
function check(name, fn) {
  fn();
  passed += 1;
  console.log(`  ok - ${name}`);
}

console.log('style-core hook tests:');

// --- 1. SessionStart: raw preamble containing both docs --------------------
check('SessionStart emits raw preamble with style core and response style', () => {
  // Point CLAUDE_CONFIG_DIR at an empty temp dir so a real ~/.claude flag file
  // can never disable the enabled-path tests.
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tadw-on-'));
  const out = runHook(SESSION, enabledEnv({ CLAUDE_CONFIG_DIR: tmp }));
  assert.ok(out.includes(MARKER), 'stdout must contain the style-core marker');
  assert.ok(out.includes('House Coding-Style Core'), 'stdout must contain the core header');
  assert.ok(out.includes(RESPONSE_MARKER), 'stdout must contain the response-style marker');
  assert.ok(out.includes('House Response Style'), 'stdout must contain the response-style header');
  assert.ok(
    !out.includes('disable-model-invocation'),
    'response-style frontmatter must be stripped (no skill frontmatter keys in injected text)'
  );
  assert.ok(!out.trimStart().startsWith('{'), 'SessionStart stdout must be raw, not JSON');
});

// --- 2. SubagentStart: JSON-wrapped additionalContext ----------------------
check('SubagentStart emits JSON with additionalContext containing the preamble', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tadw-on-'));
  const out = runHook(SUBAGENT, enabledEnv({ CLAUDE_CONFIG_DIR: tmp }));
  const parsed = JSON.parse(out); // throws if not valid JSON
  assert.strictEqual(
    parsed.hookSpecificOutput.hookEventName,
    'SubagentStart',
    'hookEventName must be SubagentStart'
  );
  const ctx = parsed.hookSpecificOutput.additionalContext;
  assert.ok(typeof ctx === 'string' && ctx.includes(MARKER), 'additionalContext must contain the marker');
  assert.ok(ctx.includes('House Coding-Style Core'), 'additionalContext must contain the core header');
  assert.ok(
    !ctx.includes(RESPONSE_MARKER),
    'additionalContext must NOT contain the response style (parent sessions only)'
  );
});

// --- 3. env off-switch: both emit empty stdout -----------------------------
check('TADW_STYLE_CORE=off disables both hooks', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tadw-off-env-'));
  for (const value of ['off', '0', 'false']) {
    const env = { ...process.env, CLAUDE_CONFIG_DIR: tmp, TADW_STYLE_CORE: value };
    assert.strictEqual(runHook(SESSION, env), '', `SessionStart must be empty for TADW_STYLE_CORE=${value}`);
    assert.strictEqual(runHook(SUBAGENT, env), '', `SubagentStart must be empty for TADW_STYLE_CORE=${value}`);
  }
});

// --- 4. flag-file off-switch (env unset): both emit empty stdout -----------
check('flag file disables both hooks with env unset', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tadw-off-flag-'));
  fs.writeFileSync(path.join(tmp, '.tadw-style-core-off'), '');
  // enabledEnv() deletes TADW_STYLE_CORE, isolating the flag-file path.
  const env = enabledEnv({ CLAUDE_CONFIG_DIR: tmp });
  assert.strictEqual(runHook(SESSION, env), '', 'SessionStart must be empty when flag file present');
  assert.strictEqual(runHook(SUBAGENT, env), '', 'SubagentStart must be empty when flag file present');
});

console.log(`\nAll ${passed} checks passed.`);
