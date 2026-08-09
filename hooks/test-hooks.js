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
//  11. Both response-style sources carry the report-your-own-work rule. Rule 3
//      (no jargon) listed only words about system behavior, so the words an
//      agent reaches for to describe its OWN work ("green", "a flake") read as
//      allowed. That is the highest-drift case: shorthand the reader cannot
//      audit. Pinned in the skill AND in preamble.js's fallback, because a
//      failed file read must not silently drop the rule.
//  12. The acceptance gate arms only on the fresh-eyes review skills, and
//      refuses a session id that could escape the temp directory.
//  13. The Stop half blocks exactly once and disarms first. This is the one
//      failure here that a user cannot escape from inside the session: a Stop
//      hook that blocks without consuming its flag traps the turn forever.
//  14. The gate's off-switch is its own. A shared switch would mean silencing a
//      per-turn gate also silenced the once-per-session style core.
//  15. The gate's manifest entries execute, and a missing node degrades to
//      silence rather than to a partial decision payload.
//  16. Every SessionStart payload fits Claude Code's 10,000-character hook
//      output cap. Over the cap, the output is replaced by a preview and a file
//      path, and the style core's marker survives inside that preview while the
//      response style does not, so the session reads as loaded while most of it
//      is missing. This shipped that way and went unnoticed.
//  17. The manifest wires one SessionStart entry per payload, each passing its
//      own index. The splitter decides how many parts exist; the manifest
//      decides how many are asked for, and a mismatch drops the tail silently.
//
// Finally, the check count documented in docs/HOOKS.md is asserted against the
// real total. That number drifted three times while this suite was being written.

const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  getSessionStartPayloads,
  getResponseStylePreamble,
  HOOK_OUTPUT_CAP,
} = require('./preamble');

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
// Extra args go to the script: session-start.js takes a payload index.
function runHook(scriptPath, env, args = []) {
  const result = spawnSync(process.execPath, [scriptPath, ...args], {
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
// Emitted across several indexed entries, so assert the UNION. Asserting only
// index 0 would pass while the response style never left the disk, which is the
// failure that went unnoticed for the whole life of the single-entry version.
check('SessionStart emits raw preamble with style core and response style', () => {
  // Point CLAUDE_CONFIG_DIR at an empty temp dir so a real ~/.claude flag file
  // can never disable the enabled-path tests.
  const tmp = tmpDir('tadw-on-');
  const env = enabledEnv({ CLAUDE_CONFIG_DIR: tmp });
  const parts = getSessionStartPayloads().map((_, i) => runHook(SESSION, env, [String(i)]));
  const out = parts.join('\n');

  assert.ok(out.includes(MARKER), 'stdout must contain the style-core marker');
  assert.ok(out.includes('House Coding-Style Core'), 'stdout must contain the core header');
  assert.ok(out.includes(RESPONSE_MARKER), 'stdout must contain the response-style marker');
  assert.ok(out.includes('House Response Style'), 'stdout must contain the response-style header');
  assert.ok(
    !out.includes('disable-model-invocation'),
    'response-style frontmatter must be stripped (no skill frontmatter keys in injected text)'
  );
  for (const part of parts) {
    assert.ok(!part.trimStart().startsWith('{'), 'SessionStart stdout must be raw, not JSON');
  }

  // Nothing is lost at a split boundary. Compare ignoring whitespace, since a
  // cut consumes the newline that joined the two sides.
  const normalize = (t) => t.replace(/\s+/g, ' ').trim();
  const rejoined = parts
    .slice(1)
    .map((p) => p.replace(/^<!-- house-response-style: continued[^\n]*-->\n\n/, ''))
    .join('\n');
  assert.strictEqual(
    normalize(rejoined),
    normalize(getResponseStylePreamble()),
    'the emitted parts must reassemble to the whole response style'
  );

  // An index past the end must be silent, so shrinking the documents cannot
  // make a stale manifest entry emit a duplicate or an error.
  assert.strictEqual(
    runHook(SESSION, env, [String(getSessionStartPayloads().length)]),
    '',
    'an out-of-range payload index must emit nothing'
  );
});

// --- 1b. Every payload fits the documented cap -----------------------------
// Claude Code caps each hook output string at 10,000 characters and replaces
// anything longer with a preview plus a file path. That degradation is silent
// from inside the session: the marker still arrives at the top of the preview,
// so the injection reads as successful while most of it is missing.
check('every SessionStart payload fits the 10,000-character hook output cap', () => {
  const tmp = tmpDir('tadw-cap-');
  const env = enabledEnv({ CLAUDE_CONFIG_DIR: tmp });
  const payloads = getSessionStartPayloads();

  payloads.forEach((payload, i) => {
    assert.ok(
      payload.length <= HOOK_OUTPUT_CAP,
      `payload ${i} is ${payload.length} chars, over the ${HOOK_OUTPUT_CAP} cap`
    );
    // The real stdout, not just the computed string: the wrapper adds nothing
    // today, but a future change to it would be invisible to the check above.
    const out = runHook(SESSION, env, [String(i)]);
    assert.ok(
      out.length <= HOOK_OUTPUT_CAP,
      `emitted payload ${i} is ${out.length} chars, over the ${HOOK_OUTPUT_CAP} cap`
    );
  });

  const subagent = runHook(SUBAGENT, env);
  assert.ok(
    subagent.length <= HOOK_OUTPUT_CAP,
    `SubagentStart emits ${subagent.length} chars, over the ${HOOK_OUTPUT_CAP} cap`
  );
});

// --- 1c. The manifest wires one entry per payload --------------------------
// The splitter decides how many parts there are; the manifest decides how many
// are asked for. If the documents grow by one part and the manifest does not,
// the tail is dropped without a word.
check('the manifest wires one SessionStart entry per payload', () => {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(HOOKS_DIR, 'style-core-hooks.json'), 'utf8')
  );
  const entries = manifest.hooks.SessionStart[0].hooks;
  const payloads = getSessionStartPayloads();

  assert.strictEqual(
    entries.length,
    payloads.length,
    `manifest wires ${entries.length} SessionStart entries but the splitter produces ${payloads.length} payloads`
  );

  // Each entry must request its own index, or two entries emit the same part.
  entries.forEach((entry, i) => {
    assert.ok(
      new RegExp(`session-start\\.js"?\\s+"[^"]*"\\s+${i};`).test(entry.command),
      `SessionStart entry ${i} must pass payload index ${i}: ${entry.command}`
    );
    assert.ok(
      new RegExp(`session-start\\.js"\\s+${i}\\s`).test(entry.commandWindows),
      `Windows SessionStart entry ${i} must pass payload index ${i}`
    );
  });
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
      // success. run-hook.sh owns emitting the marker AND honoring the
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
        `commandWindows must honor the env off-switch: ${hook.commandWindows}`
      );
      assert.ok(
        hook.commandWindows.includes('.tadw-style-core-off'),
        `commandWindows must honor the flag-file off-switch: ${hook.commandWindows}`
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

// --- 7. The wrapper honors the off-switch even when node fails -----------
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

// --- 11. The report-your-own-work rule survives in both sources -----------
// Rule 3 (no jargon) illustrated only words about system behavior (reap, drain,
// hydrate), so the words an agent uses for its OWN work read as allowed. That is
// the highest-drift case, because the reader cannot audit the shorthand: "green"
// hides a test count, and "a flake" hides the whole argument for why a failure
// is unrelated. Pinned in both sources so a fallback injection keeps the rule.
check('both response-style sources carry the report-your-own-work rule', () => {
  const skill = fs.readFileSync(
    path.join(HOOKS_DIR, '..', 'skills', 'house-response-style', 'SKILL.md'),
    'utf8'
  );
  const { RESPONSE_FALLBACK } = require('./preamble');

  assert.ok(
    /binds hardest when you report your own work/.test(skill),
    'SKILL.md must extend the no-jargon rule to self-reporting'
  );
  assert.ok(
    skill.includes('every test passes') && skill.includes('passed on re-run'),
    'SKILL.md must give the "green" and "flake" replacements explicitly'
  );
  assert.ok(
    /claim about work you just did/i.test(skill),
    'the pre-send check must include the self-reporting pass'
  );
  assert.ok(
    RESPONSE_FALLBACK.includes('report your own work') &&
      RESPONSE_FALLBACK.includes('every test'),
    'the degraded-path fallback must carry the rule too'
  );

  // Both sources must name the standard and its number, and must take only its
  // writing rules. Without the number a reader cannot look the standard up; with
  // the dictionary included the rule becomes unfollowable, since that half is
  // licensed and cannot be consulted.
  for (const [label, text] of [['SKILL.md', skill], ['the fallback', RESPONSE_FALLBACK]]) {
    assert.ok(
      /Simplified Technical English/.test(text),
      `${label} must use the standard's real name, "Simplified Technical English"`
    );
    assert.ok(/ASD-STE100/.test(text), `${label} must cite ASD-STE100 by number`);
    assert.ok(
      /dictionary/i.test(text),
      `${label} must exclude the licensed dictionary, not just cite the standard`
    );
  }
});

// --- 12-15. The acceptance gate (PostToolUse + Stop) ----------------------
// This pair chains verify-acceptance onto the end of a fresh-eyes review. Its
// failure mode is not a missing document, it is a trapped session: a Stop hook
// that blocks and never disarms cannot be escaped from inside the session. So
// the loop-safety guard is asserted directly, not reasoned about.
const GATE = path.join(HOOKS_DIR, 'acceptance-gate.js');

// The flag lands in os.tmpdir(), which honors TMPDIR. Each gate test gets its
// own, so a leftover flag from one check cannot arm another.
// The caller's own TADW_ACCEPTANCE_GATE is cleared BEFORE `extra` is applied,
// so a shell that has the gate turned off cannot mask the enabled-path checks,
// and an off-switch case can still set the value it is testing.
function gateEnv(extra = {}) {
  const base = { ...process.env, TMPDIR: tmpDir('tadw-gate-') };
  delete base.TADW_ACCEPTANCE_GATE;
  return { ...base, ...extra };
}

function runGate(payload, env) {
  const result = spawnSync(process.execPath, [GATE], {
    encoding: 'utf8',
    input: JSON.stringify(payload),
    env,
    timeout: 5000,
  });
  assert.strictEqual(result.status, 0, 'acceptance-gate.js must always exit 0');
  return result.stdout;
}

function armed(env, sessionId) {
  return fs.existsSync(path.join(env.TMPDIR, `tadw-acceptance-${sessionId}.flag`));
}

const postToolUse = (skill, sessionId, overrides = {}) => ({
  hook_event_name: 'PostToolUse',
  tool_name: 'Skill',
  tool_input: { skill },
  session_id: sessionId,
  ...overrides,
});

check('PostToolUse arms only on the fresh-eyes review skills', () => {
  // Both spellings arm: /fresh-eyes-cr reaches the review through two Skill
  // calls, the command and then the skill it names.
  for (const skill of ['review-fresh-eyes', 'tadw:review-fresh-eyes', 'fresh-eyes-cr', 'tadw:fresh-eyes-cr']) {
    const env = gateEnv();
    assert.strictEqual(runGate(postToolUse(skill, 'sess-arm'), env), '', 'arming must emit nothing');
    assert.ok(armed(env, 'sess-arm'), `${skill} must arm the gate`);
  }

  // Unrelated skills, unrelated tools, and the skill name appearing only in
  // free-text args must all leave the gate disarmed. That last one is why the
  // search is limited to the skill/name/command keys.
  const cases = [
    postToolUse('tadw:code-review', 'sess-no'),
    postToolUse('review-rails', 'sess-no'),
    { ...postToolUse('tadw:code-review', 'sess-no'), tool_input: { skill: 'tadw:code-review', args: 'after fresh-eyes-cr' } },
    { ...postToolUse('review-fresh-eyes', 'sess-no'), tool_name: 'Read' },
  ];
  for (const payload of cases) {
    const env = gateEnv();
    runGate(payload, env);
    assert.ok(!armed(env, 'sess-no'), `must not arm: ${JSON.stringify(payload.tool_input)}`);
  }

  // A session id that could escape the temp directory is refused outright
  // rather than rewritten, since a rewrite could collide with another session.
  for (const bad of ['../escape', 'a/b', '', undefined]) {
    const env = gateEnv();
    assert.strictEqual(runGate(postToolUse('review-fresh-eyes', bad), env), '', 'a bad session id must be a silent no-op');
    assert.strictEqual(fs.readdirSync(env.TMPDIR).length, 0, `session id ${JSON.stringify(bad)} must write no flag`);
  }
});

check('Stop blocks exactly once per armed review, then disarms', () => {
  const env = gateEnv();
  const stop = { hook_event_name: 'Stop', session_id: 'sess-stop' };

  // Unarmed: silent. A Stop hook that speaks on every turn is the noisy failure.
  assert.strictEqual(runGate(stop, env), '', 'an unarmed Stop must emit nothing');

  runGate(postToolUse('review-fresh-eyes', 'sess-stop'), env);
  const blocked = JSON.parse(runGate(stop, env));
  assert.strictEqual(blocked.decision, 'block', 'an armed Stop must block');
  assert.ok(/verify-acceptance/.test(blocked.reason), 'the reason must name the skill to load');
  assert.ok(
    /not run the fresh-eyes review again/i.test(blocked.reason),
    'the reason must forbid re-running the review, or the two hooks re-arm each other forever'
  );

  // The load-bearing guard: the flag is consumed, so the next Stop ends the turn.
  assert.ok(!armed(env, 'sess-stop'), 'the flag must be consumed by the block');
  assert.strictEqual(runGate(stop, env), '', 'the second Stop must not block again');

  // Second guard: Claude Code sets stop_hook_active once it is already
  // continuing from a Stop hook. Honored even with the flag armed.
  runGate(postToolUse('review-fresh-eyes', 'sess-stop'), env);
  assert.strictEqual(
    runGate({ ...stop, stop_hook_active: true }, env),
    '',
    'stop_hook_active must suppress the block'
  );

  // A flag left by a session that died before its Stop fired must be discarded,
  // not spent on an unrelated turn a week later.
  const stale = gateEnv();
  runGate(postToolUse('review-fresh-eyes', 'sess-stale'), stale);
  const flagPath = path.join(stale.TMPDIR, 'tadw-acceptance-sess-stale.flag');
  const old = Date.now() - 25 * 60 * 60 * 1000;
  fs.utimesSync(flagPath, old / 1000, old / 1000);
  assert.strictEqual(
    runGate({ hook_event_name: 'Stop', session_id: 'sess-stale' }, stale),
    '',
    'a stale flag must not block'
  );
  assert.ok(!fs.existsSync(flagPath), 'a stale flag must still be cleaned up');
});

check('the acceptance gate has its own off-switch, independent of the style core', () => {
  for (const value of ['off', '0', 'false', 'OFF', ' off ']) {
    const env = gateEnv({ TADW_ACCEPTANCE_GATE: value });
    runGate(postToolUse('review-fresh-eyes', 'sess-off'), env);
    assert.ok(!armed(env, 'sess-off'), `TADW_ACCEPTANCE_GATE=${JSON.stringify(value)} must stop arming`);
  }

  // Flag-file path, invisible to the env-var cases above.
  const cfg = tmpDir('tadw-gate-cfg-');
  fs.writeFileSync(path.join(cfg, '.tadw-acceptance-gate-off'), '');
  const flagEnv = gateEnv({ CLAUDE_CONFIG_DIR: cfg });
  runGate(postToolUse('review-fresh-eyes', 'sess-flagoff'), flagEnv);
  assert.ok(!armed(flagEnv, 'sess-flagoff'), 'the flag file must stop arming');

  // Independence in both directions. One shared switch would mean turning off a
  // once-per-turn gate also silenced the style core, and vice versa.
  const styleOff = gateEnv({ TADW_STYLE_CORE: 'off', CLAUDE_CONFIG_DIR: tmpDir('tadw-gate-style-') });
  runGate(postToolUse('review-fresh-eyes', 'sess-styleoff'), styleOff);
  assert.ok(armed(styleOff, 'sess-styleoff'), 'TADW_STYLE_CORE must not disable the acceptance gate');

  const gateOffCfg = tmpDir('tadw-style-still-on-');
  fs.writeFileSync(path.join(gateOffCfg, '.tadw-acceptance-gate-off'), '');
  const out = runHook(SESSION, enabledEnv({ CLAUDE_CONFIG_DIR: gateOffCfg }));
  assert.ok(out.includes(MARKER), 'the acceptance off-switch must not disable the style core');
});

check('the manifest wires the acceptance gate and its commands run', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(HOOKS_DIR, 'style-core-hooks.json'), 'utf8'));

  const post = manifest.hooks.PostToolUse;
  const stop = manifest.hooks.Stop;
  assert.ok(Array.isArray(post) && post.length > 0, 'PostToolUse must be declared');
  assert.ok(Array.isArray(stop) && stop.length > 0, 'Stop must be declared');

  // A PostToolUse matcher that missed the Skill tool would arm nothing; a Stop
  // matcher scoped to anything would drop the block. Stop takes no matcher.
  assert.ok(new RegExp(post[0].matcher).test('Skill'), 'the PostToolUse matcher must cover the Skill tool');
  assert.ok(!('matcher' in stop[0]), 'the Stop entry must not be scoped by a matcher');

  for (const entry of [...post, ...stop]) {
    for (const hook of entry.hooks) {
      assert.ok(
        hook.command.includes('hooks/acceptance-gate.js'),
        `command must invoke the gate: ${hook.command}`
      );
      // No run-hook.sh here, deliberately: its fallback marker would print on
      // every tool call, and its off-switch is the style core's, not this one's.
      assert.ok(
        !hook.command.includes('run-hook.sh'),
        'the gate must not route through the style-core wrapper'
      );
      assert.ok(hook.commandWindows, 'each gate hook must declare a Windows command');
      assert.ok(
        hook.commandWindows.includes('acceptance-gate.js'),
        `commandWindows must invoke the gate: ${hook.commandWindows}`
      );
    }
  }

  // Execute the real manifest strings, for the same reason check 10 exists: a
  // shell-quoting error in a command tested only as a string ships green.
  const pluginRoot = path.join(HOOKS_DIR, '..');
  const env = gateEnv();
  const runCommand = (event, payload) => {
    const command = manifest.hooks[event][0].hooks[0].command
      .split('${CLAUDE_PLUGIN_ROOT}')
      .join(pluginRoot);
    const result = spawnSync('/bin/sh', ['-c', command], {
      encoding: 'utf8',
      input: JSON.stringify(payload),
      env,
      timeout: 5000,
    });
    assert.strictEqual(result.status, 0, `${event} command must exit 0`);
    return result.stdout;
  };

  runCommand('PostToolUse', postToolUse('review-fresh-eyes', 'sess-manifest'));
  assert.ok(armed(env, 'sess-manifest'), 'the manifest PostToolUse command must arm the gate');
  const decision = JSON.parse(runCommand('Stop', { hook_event_name: 'Stop', session_id: 'sess-manifest' }));
  assert.strictEqual(decision.decision, 'block', 'the manifest Stop command must emit the block');

  // A missing node must degrade to silence, never to a broken hook payload.
  const broken = withBrokenNode(gateEnv());
  const quiet = spawnSync(
    '/bin/sh',
    ['-c', manifest.hooks.Stop[0].hooks[0].command.split('${CLAUDE_PLUGIN_ROOT}').join(pluginRoot)],
    { encoding: 'utf8', input: '{"hook_event_name":"Stop","session_id":"x"}', env: broken, timeout: 5000 }
  );
  assert.strictEqual(quiet.status, 0, 'a missing node must still exit 0');
  assert.strictEqual(quiet.stdout.trim(), '', 'a missing node must emit nothing, not a partial decision');

  // The skill the block names must exist, or the gate blocks on a dead end.
  assert.ok(
    fs.existsSync(path.join(pluginRoot, 'skills', 'verify-acceptance', 'SKILL.md')),
    'the verify-acceptance skill must exist'
  );
});

// The documented count has drifted three times while iterating on this suite.
// Assert it rather than remembering it. Runs after the checks so it can compare
// against the real total without inflating it. The prose moved from AGENTS.md to
// docs/HOOKS.md; this read must move with it or the assertion silently loses its
// subject.
const hooksDoc = fs.readFileSync(
  path.join(HOOKS_DIR, '..', 'docs', 'HOOKS.md'),
  'utf8'
);
const documented = hooksDoc.match(/runs (\d+) checks/);
assert.ok(documented, 'docs/HOOKS.md must state how many checks this suite runs');
assert.strictEqual(
  Number(documented[1]),
  passed,
  `docs/HOOKS.md says "runs ${documented[1]} checks" but the suite ran ${passed}`
);

console.log(`\nAll ${passed} checks passed (docs/HOOKS.md count verified).`);
