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
//  12. Every SessionStart payload fits Claude Code's 10,000-character hook
//      output cap. Over the cap, the output is replaced by a preview and a file
//      path, and the style core's marker survives inside that preview while the
//      response style does not, so the session reads as loaded while most of it
//      is missing. This shipped that way and went unnoticed.
//  13. The manifest wires one SessionStart entry per payload, each passing its
//      own index. The splitter decides how many parts exist; the manifest
//      decides how many are asked for, and a mismatch drops the tail silently.
//  14. No command both shares a skill's name and delegates to that skill by
//      name. The two share one `tadw:` namespace and the command wins, so such
//      a command resolves back to itself. Eighteen shipped that way, hiding
//      271,067 bytes of skill content behind their own summaries.
//  15. The payload sizes docs/HOOKS.md cites are the real ones. That document
//      argues the three-entry split from character counts, and nothing
//      measured them, so its table claimed 4,499 for a core that had grown to
//      4,780. Numbers that carry an argument have to be checked like one.
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

// --- 1d. The documented payload sizes match the real ones ------------------
// docs/HOOKS.md argues the three-entry split from concrete character counts:
// a prose total with its two halves, and a per-entry table. Nothing measured
// them, so editing either document left the argument citing sizes that no
// longer existed. The table said 4,499 for a core that had grown to 4,780.
// The numbers are the evidence for the design, so they are asserted, not
// remembered.
check('docs/HOOKS.md payload sizes match the real payloads', () => {
  const doc = fs.readFileSync(path.join(HOOKS_DIR, '..', 'docs', 'HOOKS.md'), 'utf8');
  const payloads = getSessionStartPayloads();
  const num = (s) => Number(s.replace(/,/g, ''));

  const prose = doc.match(
    /combined payload is ([\d,]+) characters \(style core ([\d,]+), response style ([\d,]+)\)/
  );
  assert.ok(prose, 'docs/HOOKS.md must state the combined payload size and its two halves');

  const core = payloads[0].length;
  const responseStyle = payloads.slice(1).reduce((sum, p) => sum + p.length, 0);
  assert.strictEqual(num(prose[2]), core, `docs/HOOKS.md says the style core is ${prose[2]}, but it is ${core}`);
  assert.strictEqual(
    num(prose[3]),
    responseStyle,
    `docs/HOOKS.md says the response style is ${prose[3]}, but it is ${responseStyle}`
  );
  assert.strictEqual(
    num(prose[1]),
    core + responseStyle,
    `docs/HOOKS.md says the combined payload is ${prose[1]}, but it is ${core + responseStyle}`
  );

  // One table row per payload, each carrying that payload's own length. A row
  // per entry is what makes the "wire one entry per index" argument readable.
  const rows = [...doc.matchAll(/^\| (\d+) \| [^|]+ \| ([\d,]+) \|$/gm)];
  assert.strictEqual(
    rows.length,
    payloads.length,
    `docs/HOOKS.md tabulates ${rows.length} payloads but the splitter produces ${payloads.length}`
  );
  rows.forEach((row, i) => {
    assert.strictEqual(Number(row[1]), i, `docs/HOOKS.md payload table must list entry ${i} in order`);
    assert.strictEqual(
      num(row[2]),
      payloads[i].length,
      `docs/HOOKS.md says payload ${i} is ${row[2]} chars, but it is ${payloads[i].length}`
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

// --- 6b. No command may share a skill's name AND delegate to it by name ---
// `commands/<name>.md` and `skills/<name>/SKILL.md` are addressed as the same
// `tadw:<name>`, and the command wins. So a command body saying "Use the
// `<name>` skill" resolves back to itself and never reaches the skill.
//
// Eighteen commands shipped that way, hiding 271,067 bytes of skill content.
// /bead-audit alone put a 250-byte summary in front of a 51,113-byte rubric, and
// every audit it ran scored from the summary. Check 6 pinned this for one
// command; this generalizes it to every colliding name, because the same defect
// reappeared seventeen more times while that single check kept passing.
//
// The rule: a command may share a skill's name, or delegate to that skill by
// name, but never both. Satisfy it by renaming the command, deleting it (the
// skill then takes the slash name), or reading the SKILL.md from disk.
check('no command both shares a skill name and delegates to that skill by name', () => {
  const root = path.join(HOOKS_DIR, '..');
  const skills = new Set(
    fs
      .readdirSync(path.join(root, 'skills'), { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name)
  );
  const commandDir = path.join(root, 'commands');
  const shared = fs
    .readdirSync(commandDir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => f.slice(0, -3))
    .filter((n) => skills.has(n));

  for (const name of shared) {
    const body = fs
      .readFileSync(path.join(commandDir, `${name}.md`), 'utf8')
      .replace(/^---[\s\S]*?\n---\n/, '');
    const delegates = new RegExp(
      String.raw`(use|load|invoke)\s+the\s+\`?${name}\`?\s+skill`,
      'i'
    ).test(body);
    const readsFile = body.includes(`skills/${name}/SKILL.md`);

    assert.ok(
      !delegates || readsFile,
      `/${name} shares its name with skills/${name}/ and tells the model to load that skill ` +
        `by name. Skill(${name}) returns this command, not the skill. Read ` +
        `\${CLAUDE_PLUGIN_ROOT}/skills/${name}/SKILL.md instead, rename the command, or delete it.`
    );

    // A Read with no fallback fails silently when CLAUDE_PLUGIN_ROOT does not
    // resolve, which is the same class of silent failure as the shadow itself.
    if (readsFile) {
      assert.ok(
        /Glob:/.test(body),
        `/${name} reads its skill from disk but gives no Glob fallback for an ` +
          'unresolved ${CLAUDE_PLUGIN_ROOT}'
      );
    }
  }
});

// --- 6b. Registration: the AGENTS.md name lists match the directories -------
// AGENTS.md claims it registers every component and states a count for each.
// Nothing enforced that, so adding a skill without listing it, or listing one
// and leaving the count behind, shipped green. /validate-plugin is a command an
// LLM runs; this is the mechanical half of the same claim.
// `prefix` is what README.md puts in front of the name. A command is written
// `/build` there and stored as `commands/build.md` on disk, so comparing the
// two without it reports every command as undocumented.
const COMPONENTS = [
  { label: 'Skills', dir: 'skills', prefix: '', names: (root) => componentNames(root, 'skills', true) },
  { label: 'Agents', dir: 'agents', prefix: '', names: (root) => componentNames(root, 'agents', false) },
  { label: 'Commands', dir: 'commands', prefix: '/', names: (root) => componentNames(root, 'commands', false) },
];

function componentNames(root, dir, isDirectory) {
  const entries = fs.readdirSync(path.join(root, dir), { withFileTypes: true });
  return entries
    .filter((e) => (isDirectory ? e.isDirectory() : e.isFile() && e.name.endsWith('.md')))
    .map((e) => (isDirectory ? e.name : e.name.slice(0, -3)))
    .sort();
}

check('AGENTS.md registers every component on disk, with matching counts', () => {
  const root = path.join(HOOKS_DIR, '..');
  const doc = fs.readFileSync(path.join(root, 'AGENTS.md'), 'utf8');

  for (const { label, names } of COMPONENTS) {
    const onDisk = names(root);
    const heading = doc.match(
      new RegExp(String.raw`\*\*Registered ${label}\*\* \((\d+)\)\.`)
    );
    assert.ok(heading, `AGENTS.md must carry a "**Registered ${label}** (N)." section`);

    // The list is the first paragraph after the heading made up ENTIRELY of
    // backticked names. Capturing to the next `**` instead swept in later prose
    // and reported `node` and `hooks` as registered components.
    const isNameList = (para) => {
      const tokens = para.trim().split(/\s+/);
      return tokens.length > 0 && tokens.every((t) => /^`\/?[a-z0-9-]+`$/.test(t));
    };
    const list = doc
      .slice(heading.index + heading[0].length)
      .split(/\n\s*\n/)
      .find(isNameList);
    assert.ok(list, `AGENTS.md has no name list under "Registered ${label}"`);

    const listed = [...list.matchAll(/`\/?([a-z0-9-]+)`/g)].map((m) => m[1]).sort();
    const missing = onDisk.filter((n) => !listed.includes(n));
    const extra = listed.filter((n) => !onDisk.includes(n));

    assert.deepStrictEqual(
      missing,
      [],
      `AGENTS.md "Registered ${label}" omits: ${missing.join(', ')}`
    );
    assert.deepStrictEqual(
      extra,
      [],
      `AGENTS.md "Registered ${label}" names something absent from ${label.toLowerCase()}/: ${extra.join(', ')}`
    );
    assert.strictEqual(
      Number(heading[1]),
      onDisk.length,
      `AGENTS.md says ${label} (${heading[1]}) but ${onDisk.length} exist on disk`
    );
  }
});

// --- 6c. Registration: README.md documents every skill and agent -----------
// Commands are deliberately out of scope. README organizes them by topic, and
// several are aliases for a differently-named skill or agent (/adr -> the
// architecture-decision-record skill), so a name-match assertion would encode a
// rule this repository does not follow and fail on eleven correct entries.
check('README.md documents every component on disk', () => {
  const root = path.join(HOOKS_DIR, '..');
  const readme = fs.readFileSync(path.join(root, 'README.md'), 'utf8');

  // The name must open a backticked token and end it, or be followed by a
  // space. Nine command rows carry an argument in the same backticks, as
  // `/diagnose <bug>`, so requiring the whole token to be the name alone
  // reported every one of them as undocumented. Requiring the boundary keeps
  // `/ux-audit` from matching the `/ux-audit-ios` row.
  const documented = (name) => new RegExp('`' + name + '[`\\s]').test(readme);

  for (const { label, prefix, names } of COMPONENTS) {
    const undocumented = names(root).filter((n) => !documented(`${prefix}${n}`));
    assert.deepStrictEqual(
      undocumented,
      [],
      `README.md never mentions ${label.toLowerCase()}: ${undocumented.join(', ')}`
    );
  }
});

// --- 6d. Every runnable bash block in a skill or command parses ------------
// Three broken snippets shipped inside one skill in a single sitting: a diff
// basis that missed uncommitted work, a `grep -c` whose exit 1 on zero matches
// reads as a failed gate, and a PEM pattern that matched neither common form.
// Syntax checking catches none of those three. It catches the class below them,
// which is why this is a cheap check and not a substitute for running a snippet.
//
// Blocks carrying a <placeholder> are templates, not scripts, and are skipped.
check('every runnable bash block in a skill or command parses', () => {
  const root = path.join(HOOKS_DIR, '..');
  const docs = [
    ...componentNames(root, 'skills', true).map((n) => `skills/${n}/SKILL.md`),
    ...componentNames(root, 'commands', false).map((n) => `commands/${n}.md`),
  ].filter((rel) => fs.existsSync(path.join(root, rel)));

  const fence = /^```(?:bash|sh|shell)[^\n]*\n([\s\S]*?)^```/gm;
  const placeholder = /<[a-z][a-z0-9_.-]*>/;
  const failures = [];
  let checked = 0;

  for (const rel of docs) {
    const text = fs.readFileSync(path.join(root, rel), 'utf8');
    let match;
    let index = 0;
    while ((match = fence.exec(text)) !== null) {
      const body = match[1];
      index += 1;
      if (placeholder.test(body)) continue;
      checked += 1;
      const result = spawnSync('bash', ['-n'], { input: body, encoding: 'utf8' });
      if (result.status !== 0) {
        const first = (result.stderr || '').trim().split('\n')[0];
        failures.push(`${rel} block ${index}: ${first}`);
      }
    }
  }

  assert.ok(checked > 0, 'no bash blocks were checked; the fence pattern stopped matching');
  assert.deepStrictEqual(
    failures,
    [],
    `bash blocks that do not parse:\n  ${failures.join('\n  ')}`
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
