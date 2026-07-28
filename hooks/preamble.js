#!/usr/bin/env node
// tadw - injected-preamble loaders
//
// Reads the canonical injected text from its markdown source. If a read fails
// for any reason, returns a small hardcoded fallback so the hook still injects
// the observability marker and the spirit of the doc rather than blanking out.
//
// Two documents, two audiences:
//   style-core.md            - coding style; injected into sessions AND subagents.
//   house-response-style skill - how to talk to the user; parent sessions only,
//                       because subagents report to the orchestrator, not a human.
//
// The response style is sourced from the skill's SKILL.md (not a hooks-local copy)
// so the always-on hook and the on-demand /response-style invocation can never
// drift. Its YAML frontmatter is stripped before injection; style-core.md has
// none, so it is injected verbatim.

const fs = require('fs');
const path = require('path');

const STYLE_CORE_PATH = path.join(__dirname, 'style-core.md');
const RESPONSE_STYLE_PATH = path.join(
  __dirname,
  '..',
  'skills',
  'house-response-style',
  'SKILL.md'
);

const FRONTMATTER = /^---\r?\n[\s\S]*?\r?\n---\r?\n/;

// Mirrors the opening marker of style-core.md so a degraded run is still
// observable in-session and still carries the headline principles.
const FALLBACK = [
  '<!-- house-style-core: loaded (fallback) -->',
  '',
  '# House Coding-Style Core',
  '',
  'Write TRUE code (Transparent, Reasonable, Usable, Exemplary). Wait for',
  'duplication before abstracting; keep units small and single-purpose; keep',
  'interfaces simple; inject dependencies; tell, do not ask; compose over',
  'inherit; fail fast with explicit errors; read top-down; let names do the',
  'documenting. Favor correctness over speed and simplicity over cleverness.',
  '',
].join('\n');

const RESPONSE_FALLBACK = [
  '<!-- house-response-style: loaded (fallback) -->',
  '',
  '# House Response Style',
  '',
  'Respond concisely: lead with the answer, cut narration, keep only detail',
  'that changes what the reader does next. When anything is left open, end',
  'with a "Next actions" section split into "Me (Claude)" and "You"; omit it',
  'entirely when nothing is open. After answering a question, suggest one',
  'follow-up ("Worth asking next: ...") only when the answer genuinely raises',
  'it, never as a ritual.',
  '',
].join('\n');

function readOrFallback(filePath, fallback) {
  try {
    const text = fs.readFileSync(filePath, 'utf8');
    // Guard against an empty/whitespace file blanking the injection.
    return text.trim().length > 0 ? text : fallback;
  } catch (e) {
    return fallback;
  }
}

function getStyleCorePreamble() {
  return readOrFallback(STYLE_CORE_PATH, FALLBACK);
}

function getResponseStylePreamble() {
  const text = readOrFallback(RESPONSE_STYLE_PATH, RESPONSE_FALLBACK);
  return text.replace(FRONTMATTER, '');
}

module.exports = {
  getStyleCorePreamble,
  getResponseStylePreamble,
  STYLE_CORE_PATH,
  RESPONSE_STYLE_PATH,
  FALLBACK,
  RESPONSE_FALLBACK,
};
