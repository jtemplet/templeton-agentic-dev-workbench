#!/usr/bin/env node
// tadw - standalone hook test
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
//   5. The MANIFEST itself: style-core-hooks.json must match every SessionStart
//      source Claude Code can emit. The suite previously tested only the two
//      scripts, so a matcher missing a source (this happened: `fork` was absent,
//      silently skipping style injection for every forked session) shipped green.
//   6. /response-style must NOT route through the Skill tool. The skill sets
//      disable-model-invocation, so the Skill tool refuses it and the command
//      silently no-ops. Regression guard for that exact bug.
//   7. run-hook.sh emits the failure marker when node fails, and stays SILENT
//      when node fails and the off-switch is set. The fallback used to fire
//      regardless, telling an opted-out user something had failed when they
//      had simply turned it off.
//   8. run-hook.sh needs no external command and no HOME. It lowercased with
//      `tr`, so on a PATH without `tr` the off-switch was ignored; and an unset
//      HOME aborted it under `set -u`, emitting neither core nor marker.
//   9. run-hook.sh and runtime.js agree on what "disabled" means. The shell
//      copy exists because the off-switch must hold when node cannot run, and
//      duplicated logic drifts unless something asserts otherwise.
//  10. The manifest commands actually RUN. Everything above tests the manifest
//      as a string and the wrapper as a program, never together, so a shell
//      quoting error would ship green. Matters most for the SubagentStart
//      fallback: JSON nested in single quotes inside a JSON string.
//
// Finally, the check count documented in AGENTS.md is asserted against the real
// total. That number drifted three times while this suite was being written.

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

// Every scratch directory lives under one root that is removed on exit. Calling
// mkdtemp directly leaked ~26 directories per run into the system temp dir,
// which accumulates on a dev machine and on every CI push.
const TMP_ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'tadw-tests-'));
process.on('exit', () => {
  try {
    fs.rmSync(TMP_ROOT, { recursive: true, force: true });
  } catch (e) {
    // Cleanup failure must not mask a test result.
  }
});

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(TMP_ROOT, prefix));
}

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
  const tmp = tmpDir('tadw-on-');
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
  const tmp = tmpDir('tadw-on-');
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
  const tmp = tmpDir('tadw-off-env-');
  for (const value of ['off', '0', 'false']) {
    const env = { ...process.env, CLAUDE_CONFIG_DIR: tmp, TADW_STYLE_CORE: value };
    assert.strictEqual(runHook(SESSION, env), '', `SessionStart must be empty for TADW_STYLE_CORE=${value}`);
    assert.strictEqual(runHook(SUBAGENT, env), '', `SubagentStart must be empty for TADW_STYLE_CORE=${value}`);
  }
});

// --- 4. flag-file off-switch (env unset): both emit empty stdout -----------
check('flag file disables both hooks with env unset', () => {
  const tmp = tmpDir('tadw-off-flag-');
  fs.writeFileSync(path.join(tmp, '.tadw-style-core-off'), '');
  // enabledEnv() deletes TADW_STYLE_CORE, isolating the flag-file path.
  const env = enabledEnv({ CLAUDE_CONFIG_DIR: tmp });
  assert.strictEqual(runHook(SESSION, env), '', 'SessionStart must be empty when flag file present');
  assert.strictEqual(runHook(SUBAGENT, env), '', 'SubagentStart must be empty when flag file present');
});

// --- 5. Manifest: matcher covers every SessionStart source ----------------
// Keep in sync with Claude Code's SessionStart source enum. Adding a source
// here without adding it to the matcher is what silently disables the hook.
const SESSION_START_SOURCES = ['startup', 'resume', 'clear', 'compact', 'fork'];

check('SessionStart matcher covers every session source', () => {
  const manifestPath = path.join(HOOKS_DIR, 'style-core-hooks.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

  const sessionStart = manifest.hooks.SessionStart;
  assert.ok(Array.isArray(sessionStart) && sessionStart.length > 0, 'SessionStart must be declared');

  const matcher = new RegExp(sessionStart[0].matcher);
  for (const source of SESSION_START_SOURCES) {
    assert.ok(matcher.test(source), `matcher must cover the "${source}" session source`);
  }

  assert.ok(Array.isArray(manifest.hooks.SubagentStart), 'SubagentStart must be declared');

  // Every referenced script must exist, or the hook no-ops at runtime.
  for (const entry of [...sessionStart, ...manifest.hooks.SubagentStart]) {
    assert.ok(
      Array.isArray(entry.hooks),
      `each manifest entry must declare a hooks array: ${JSON.stringify(entry)}`
    );
    for (const hook of entry.hooks) {
      const script = hook.command.match(/hooks\/([\w-]+\.js)/);
      assert.ok(script, `command must invoke a hooks/*.js script: ${hook.command}`);
      assert.ok(
        fs.existsSync(path.join(HOOKS_DIR, script[1])),
        `referenced script ${script[1]} must exist`
      );
      // A bare `node ...; exit 0` swallows a missing-node failure into a silent
      // success. run-hook.sh owns emitting the marker AND honouring the
      // off-switch, so the manifest must route through it.
      assert.ok(
        hook.command.includes('run-hook.sh'),
        `command must route through run-hook.sh so failures are visible: ${hook.command}`
      );
      assert.ok(
        /FAILED to load/.test(hook.command),
        `command must supply a failure marker as the fallback: ${hook.command}`
      );

      // commandWindows cannot be executed here (no PowerShell on macOS or on the
      // Linux runner), so assert the properties that would otherwise drift in
      // silence. The realistic failure is editing the POSIX command and
      // forgetting the Windows one, which is how it lost the off-switch before.
      assert.ok(hook.commandWindows, 'each hook must declare a Windows command');
      assert.ok(
        hook.commandWindows.includes('TADW_STYLE_CORE'),
        `commandWindows must honour the env off-switch: ${hook.commandWindows}`
      );
      assert.ok(
        hook.commandWindows.includes('.tadw-style-core-off'),
        `commandWindows must honour the flag-file off-switch: ${hook.commandWindows}`
      );
      assert.ok(
        /FAILED to load/.test(hook.commandWindows),
        `commandWindows must supply a failure marker: ${hook.commandWindows}`
      );
    }
  }
});

// --- 6. /response-style must not go through the Skill tool ----------------
check('/response-style reads the skill file instead of invoking the Skill tool', () => {
  const skillPath = path.join(HOOKS_DIR, '..', 'skills', 'house-response-style', 'SKILL.md');
  const commandPath = path.join(HOOKS_DIR, '..', 'commands', 'response-style.md');
  const skill = fs.readFileSync(skillPath, 'utf8');
  const command = fs.readFileSync(commandPath, 'utf8');

  // The guard only matters while the skill is non-model-invocable.
  if (!skill.includes('disable-model-invocation: true')) return;

  assert.ok(
    /Read\b/.test(command) && command.includes('skills/house-response-style/SKILL.md'),
    'command must instruct reading the SKILL.md file directly'
  );
  assert.ok(
    !/Use the `house-response-style` skill/.test(command),
    'command must not tell the model to invoke the disabled skill via the Skill tool'
  );
});

// --- 7. The wrapper honours the off-switch even when node fails -----------
// The bug this pins: the failure fallback used to fire regardless of the
// off-switch, so a user who had deliberately disabled the hook still got a
// "FAILED to load" marker injected into every session. Nothing had failed.
//
// A `node` shim that exits non-zero stands in for a missing node. Both produce
// a non-zero status from the same branch of run-hook.sh, and a shim keeps the
// rest of PATH intact so the wrapper's own utilities still resolve.
const WRAPPER = path.join(HOOKS_DIR, 'run-hook.sh');
const FALLBACK = '<!-- house-style-core: FAILED to load (test) -->';

function withBrokenNode(env) {
  const shimDir = tmpDir('tadw-shim-');
  fs.writeFileSync(path.join(shimDir, 'node'), '#!/bin/sh\nexit 1\n', { mode: 0o755 });
  return { ...env, PATH: `${shimDir}${path.delimiter}${env.PATH || ''}` };
}

function runWrapper(env) {
  const result = spawnSync('/bin/sh', [WRAPPER, SESSION, FALLBACK], {
    encoding: 'utf8',
    env,
    timeout: 5000,
  });
  assert.strictEqual(result.status, 0, 'run-hook.sh must always exit 0');
  return result.stdout;
}

check('run-hook.sh emits the failure marker when node fails and the core is enabled', () => {
  const tmp = tmpDir('tadw-on-');
  const out = runWrapper(withBrokenNode(enabledEnv({ CLAUDE_CONFIG_DIR: tmp })));
  assert.ok(out.includes(FALLBACK), 'a broken node must produce a visible marker');
});

check('run-hook.sh stays silent when node fails AND the off-switch is set', () => {
  const tmp = tmpDir('tadw-off-');

  for (const value of ['off', '0', 'false', 'OFF', ' off ']) {
    const env = withBrokenNode({ ...process.env, CLAUDE_CONFIG_DIR: tmp, TADW_STYLE_CORE: value });
    assert.strictEqual(
      runWrapper(env),
      '',
      `disabled via TADW_STYLE_CORE=${JSON.stringify(value)} must suppress the marker too`
    );
  }

  // Flag-file path, with the env var explicitly cleared.
  fs.writeFileSync(path.join(tmp, '.tadw-style-core-off'), '');
  assert.strictEqual(
    runWrapper(withBrokenNode(enabledEnv({ CLAUDE_CONFIG_DIR: tmp }))),
    '',
    'the flag file must suppress the marker too'
  );
});

// --- 7b. The wrapper works in a degraded environment ----------------------
// Both bugs pinned here were the wrapper failing at the one job it exists for.
// With `tr` absent from PATH, lowercasing failed silently and TADW_STYLE_CORE=off
// was ignored, so an opted-out user got the marker anyway. With HOME unset,
// `set -u` aborted the script, emitting neither the core nor the marker.
check('run-hook.sh needs no external commands and no HOME', () => {
  const emptyDir = tmpDir('tadw-nopath-');
  const cfg = tmpDir('tadw-cfg-');

  // PATH contains neither `node` nor any coreutil.
  const bare = { PATH: emptyDir, CLAUDE_CONFIG_DIR: cfg };

  assert.strictEqual(
    runWrapper({ ...bare, TADW_STYLE_CORE: 'off' }),
    '',
    'the off-switch must hold even when no external command is available'
  );
  assert.ok(
    runWrapper(bare).includes(FALLBACK),
    'an enabled core with an unusable node must still emit the marker'
  );

  // No HOME and no CLAUDE_CONFIG_DIR: must not abort under `set -u`.
  const homeless = spawnSync('/bin/sh', [WRAPPER, SESSION, FALLBACK], {
    encoding: 'utf8',
    env: { PATH: emptyDir },
    timeout: 5000,
  });
  assert.strictEqual(homeless.status, 0, 'an unset HOME must not abort the wrapper');
  assert.ok(
    homeless.stdout.includes(FALLBACK),
    'an unset HOME must still produce the failure marker, not silence'
  );
});

// --- 8. The two off-switch implementations agree --------------------------
// run-hook.sh re-implements isDisabled() because it must work when node cannot
// run. Duplicated logic drifts, so assert the copies match.
check('run-hook.sh and runtime.js agree on what "disabled" means', () => {
  const { isDisabled } = require('./runtime.js');
  const tmp = tmpDir('tadw-parity-');
  const values = ['off', 'OFF', ' off ', '0', 'false', 'False', 'on', '', 'yes', 'true'];

  for (const value of values) {
    const saved = { core: process.env.TADW_STYLE_CORE, dir: process.env.CLAUDE_CONFIG_DIR };
    process.env.TADW_STYLE_CORE = value;
    process.env.CLAUDE_CONFIG_DIR = tmp;
    const jsSaysDisabled = isDisabled();
    if (saved.core === undefined) delete process.env.TADW_STYLE_CORE;
    else process.env.TADW_STYLE_CORE = saved.core;
    if (saved.dir === undefined) delete process.env.CLAUDE_CONFIG_DIR;
    else process.env.CLAUDE_CONFIG_DIR = saved.dir;

    const env = withBrokenNode({ ...process.env, CLAUDE_CONFIG_DIR: tmp, TADW_STYLE_CORE: value });
    const shellSaysDisabled = runWrapper(env) === '';

    assert.strictEqual(
      shellSaysDisabled,
      jsSaysDisabled,
      `disagreement on TADW_STYLE_CORE=${JSON.stringify(value)}: ` +
        `runtime.js=${jsSaysDisabled}, run-hook.sh=${shellSaysDisabled}`
    );
  }
});

// --- 10. The manifest commands actually RUN --------------------------------
// Checks 5 and 7-9 test the manifest as a string and the wrapper as a program,
// but never the two together, so a shell-quoting error would ship green. That
// matters most for SubagentStart, whose fallback is JSON nested inside single
// quotes inside a JSON string. It had been verified only by hand, which is the
// same discarded-verification pattern that let earlier bugs through twice.
check('the manifest commands execute correctly end to end', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(HOOKS_DIR, 'style-core-hooks.json'), 'utf8'));
  const pluginRoot = path.join(HOOKS_DIR, '..');
  const cfg = tmpDir('tadw-manifest-');

  const runCommand = (event, env) => {
    const raw = manifest.hooks[event][0].hooks[0].command;
    const command = raw.split('${CLAUDE_PLUGIN_ROOT}').join(pluginRoot);
    const result = spawnSync('/bin/sh', ['-c', command], { encoding: 'utf8', env, timeout: 5000 });
    assert.strictEqual(result.status, 0, `${event} command must exit 0`);
    return result.stdout;
  };

  for (const event of ['SessionStart', 'SubagentStart']) {
    const working = runCommand(event, enabledEnv({ CLAUDE_CONFIG_DIR: cfg }));
    assert.ok(working.includes(MARKER), `${event}: a working node must inject the core`);

    const broken = runCommand(event, withBrokenNode(enabledEnv({ CLAUDE_CONFIG_DIR: cfg })));
    assert.ok(
      broken.includes('FAILED to load'),
      `${event}: a broken node must inject the failure marker`
    );

    const disabled = runCommand(
      event,
      withBrokenNode({ ...process.env, CLAUDE_CONFIG_DIR: cfg, TADW_STYLE_CORE: 'off' })
    );
    assert.strictEqual(disabled.trim(), '', `${event}: the off-switch must silence the marker`);
  }

  // The SubagentStart wrapper contract must survive the nested quoting, in both
  // the success and the failure path.
  const okJson = JSON.parse(runCommand('SubagentStart', enabledEnv({ CLAUDE_CONFIG_DIR: cfg })));
  assert.strictEqual(okJson.hookSpecificOutput.hookEventName, 'SubagentStart');

  const failJson = JSON.parse(
    runCommand('SubagentStart', withBrokenNode(enabledEnv({ CLAUDE_CONFIG_DIR: cfg })))
  );
  assert.ok(
    failJson.hookSpecificOutput.additionalContext.includes('FAILED to load'),
    'the SubagentStart fallback must be valid JSON carrying the marker'
  );
});

// The documented count in AGENTS.md has drifted three times while iterating on
// this suite. Assert it rather than remembering it. Runs after the checks so it
// can compare against the real total without inflating it.
const agentsMd = fs.readFileSync(path.join(HOOKS_DIR, '..', 'AGENTS.md'), 'utf8');
const documented = agentsMd.match(/runs (\d+) checks/);
assert.ok(documented, 'AGENTS.md must state how many checks this suite runs');
assert.strictEqual(
  Number(documented[1]),
  passed,
  `AGENTS.md says "runs ${documented[1]} checks" but the suite ran ${passed}`
);

console.log(`\nAll ${passed} checks passed (AGENTS.md count verified).`);
