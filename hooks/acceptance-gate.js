#!/usr/bin/env node
// tadw - acceptance gate hook (PostToolUse + Stop)
//
// Chains the acceptance check onto the end of a fresh-eyes review.
//
// Why two events instead of one. Claude Code has no "slash command finished"
// event. PostToolUse on the Skill tool fires when the skill is LOADED, not when
// its work is done, so a check wired there would grade the branch before a
// single file had been reviewed. Stop fires when the agent is about to hand
// back, which is the right moment, but it fires on every turn and cannot see
// what ran earlier. So the two are paired:
//
//   PostToolUse(Skill)  arms a per-session flag when the fresh-eyes review loads
//   Stop                consumes the flag and blocks once, asking for the check
//
// Loop safety is the whole risk here: a Stop hook that blocks unconditionally
// traps the session forever. Three guards, in order:
//   1. The flag is deleted BEFORE the block is emitted, so the second Stop of
//      the same turn finds nothing to do. This is the load-bearing one.
//   2. stop_hook_active is honored, which Claude Code sets once it is already
//      continuing from a Stop hook.
//   3. Any error at all falls through to a silent exit 0. A gate that cannot
//      decide must let the session end.
//
// This runs `node` directly rather than through run-hook.sh, unlike the style
// hooks. run-hook.sh emits a visible marker when node is missing, which is right
// for a document injected once per session and wrong for a hook that fires on
// every tool call and every stop. A missing gate here costs a skipped nudge, so
// it degrades silently on purpose.

const fs = require('fs');
const os = require('os');
const path = require('path');

const { isFeatureDisabled } = require('./runtime');

const ENV_VAR = 'TADW_ACCEPTANCE_GATE';
const FLAG_FILE = '.tadw-acceptance-gate-off';

// The skills whose completion should trigger the acceptance check. Both spellings
// are listed because `/fresh-eyes-cr` reaches the review through two Skill calls:
// the command itself, then the skill the command names.
const TRIGGER_SKILLS = new Set(['review-fresh-eyes', 'fresh-eyes-cr']);

// Only these keys of tool_input are searched for a skill name. Scanning every
// string value would arm the gate whenever "fresh-eyes-cr" appeared in some
// unrelated skill's free-text args.
const SKILL_NAME_KEYS = ['skill', 'name', 'command'];

// A flag older than this is from a session that died before its Stop fired.
// Consuming it would block a turn that has nothing to do with a code review.
const FLAG_MAX_AGE_MS = 24 * 60 * 60 * 1000;

const BLOCK_REASON = [
  'A fresh-eyes review just completed in this session.',
  'Load the `verify-acceptance` skill now and follow it.',
  'It checks this unit of work against its bead acceptance criteria and the QA gates.',
  'Report its verdict table before you stop.',
  'Do not run the fresh-eyes review again.',
  'If the skill reports NOT ACCEPTED, report that verdict as it stands; do not start fixing it unless the user asks.',
].join(' ');

// Session ids come from the harness, but they land in a filesystem path, so
// treat them as untrusted: anything outside this character set is refused rather
// than sanitized, since a rewritten id could collide with another session's flag.
function flagPathFor(sessionId) {
  if (typeof sessionId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(sessionId)) {
    return null;
  }
  return path.join(os.tmpdir(), `tadw-acceptance-${sessionId}.flag`);
}

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch (e) {
    return '';
  }
}

function namesSkillUnderTest(toolInput) {
  if (!toolInput || typeof toolInput !== 'object') {
    return false;
  }
  for (const key of SKILL_NAME_KEYS) {
    const value = toolInput[key];
    if (typeof value !== 'string') {
      continue;
    }
    // Strip the plugin namespace: `/fresh-eyes-cr` arrives as `tadw:fresh-eyes-cr`.
    const bare = value.trim().split(':').pop();
    if (TRIGGER_SKILLS.has(bare)) {
      return true;
    }
  }
  return false;
}

// PostToolUse: arm the flag, say nothing. Writing is idempotent, so a review
// reached through both the command and the skill arms once.
function handlePostToolUse(payload) {
  if (payload.tool_name !== 'Skill') {
    return;
  }
  if (!namesSkillUnderTest(payload.tool_input)) {
    return;
  }
  const flag = flagPathFor(payload.session_id);
  if (!flag) {
    return;
  }
  fs.writeFileSync(flag, `${payload.session_id}\n`);
}

// Stop: consume the flag and block once.
function handleStop(payload) {
  if (payload.stop_hook_active === true) {
    return;
  }
  const flag = flagPathFor(payload.session_id);
  if (!flag || !fs.existsSync(flag)) {
    return;
  }

  const stale = Date.now() - fs.statSync(flag).mtimeMs > FLAG_MAX_AGE_MS;

  // Disarm first, always, including on the stale path. Every later step can
  // throw; none of them may leave an armed flag behind.
  fs.unlinkSync(flag);

  if (stale) {
    return;
  }

  process.stdout.write(JSON.stringify({ decision: 'block', reason: BLOCK_REASON }));
}

try {
  if (!isFeatureDisabled(ENV_VAR, FLAG_FILE)) {
    const payload = JSON.parse(readStdin() || '{}');
    if (payload.hook_event_name === 'PostToolUse') {
      handlePostToolUse(payload);
    } else if (payload.hook_event_name === 'Stop') {
      handleStop(payload);
    }
  }
} catch (e) {
  // Silent fail. A gate that cannot decide must never block the session, and
  // partial stdout here would be parsed as a malformed hook decision.
}

// Deliberately no process.exit(0). Both handlers run inside the try/catch, so
// falling off the end already exits 0, and it flushes stdout first. An explicit
// exit could truncate the decision object on a Windows pipe, which is the
// partial stdout the catch above exists to avoid. See writeHookOutput in
// runtime.js.
