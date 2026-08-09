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
  'documenting. Use American English everywhere (color, behavior, initialize),',
  'except when quoting a name you do not own. Favor correctness over speed and',
  'simplicity over cleverness.',
  '',
].join('\n');

const RESPONSE_FALLBACK = [
  '<!-- house-response-style: loaded (fallback) -->',
  '',
  '# House Response Style',
  '',
  'Two rules outrank the rest: accuracy beats brevity (never drop a fact,',
  'caveat, number, or warning to shorten a sentence), and label your',
  'confidence (separate what you verified from what you infer or guess).',
  '',
  'Respond concisely: lead with the answer, cut narration, keep only detail',
  'that changes what the reader does next. Use Simplified Technical English,',
  'the controlled-English standard specified in ASD-STE100. Follow its',
  'writing rules; never follow its licensed dictionary. The rules: keep',
  'terminology consistent where ambiguity would cost the reader, use active',
  'voice, prefer literal language to borrowed metaphor (domain terms an',
  'engineer reads fluently are fine), and hold sentences to twenty-five words',
  'for an explanation and twenty for an instruction, splitting at "which",',
  '"so", "but", "since", "because", ", meaning", and ", making".',
  'Keep technical names (files, commands, settings) verbatim, and define an',
  'unavoidable term in the same sentence you use it. Use American English.',
  'ASD-STE100 governs technical and informational answers; for creative or',
  'personal work keep accuracy and the answer first, and drop the caps.',
  'When you report your own work, follow a fixed shape: give the number',
  'where one exists, name what failed, say what you did about it, give the',
  'evidence instead of the verdict, and say what you did not run and where',
  'you stopped. Never let a label stand alone: "green" and "a flake" are',
  'legitimate beside the facts they stand for, never instead of them.',
  'Write "every test passes" with the count. Write "the test failed once',
  'and passed on re-run, and my change touches no file it reads". Match',
  'depth to the reader\'s',
  'demonstrated knowledge, and adapt tone to the task.',
  'When the reader has to choose between options that',
  'trade off on more than one factor, put those trade-offs in a table and end',
  'with a bold one-line recommendation. When the user must do something next,',
  'end with a "Next actions" section split into "Me (Claude)" and "You"; omit',
  'it entirely when nothing is open. After answering a question, suggest one',
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

// Claude Code caps every hook output string at 10,000 characters, and the cap
// applies to plain stdout and to hookSpecificOutput.additionalContext alike.
// Output past the cap is written to a file and replaced with a short preview
// plus that path, so the model gets a pointer it has no reason to follow.
//
// This is not a theoretical limit. The combined payload was 19,996 characters,
// almost exactly twice the cap, and the response style (which sits second) never
// reached a single session. Only the style core's opening survived, carrying the
// marker that says it loaded, so the failure read as success.
const HOOK_OUTPUT_CAP = 10000;

// Reserved out of each part for the continuation marker prepended below.
const MARKER_RESERVE = 80;

// Split text into the fewest parts that each fit the cap, cutting at line
// boundaries. Returns { text, section } per part, where `section` names the
// `## ` heading in effect where that part begins.
//
// Packing greedily rather than on section boundaries is deliberate. Section
// packing costs a whole extra part here (the sections do not divide evenly), and
// each part costs a manifest entry. Naming the resumed section in the
// continuation marker restores the context that a mid-section cut loses, for one
// line instead of one entry.
function splitForCap(text, maxChars) {
  const headingOf = (line) => (line.startsWith('## ') ? line.slice(3).trim() : null);

  if (text.length <= maxChars) {
    return [{ text, section: null }];
  }

  const parts = [];
  let current = '';
  let currentSection = null; // heading in effect where `current` begins
  let heading = null; // most recent heading seen

  const flush = () => {
    if (current.length > 0) {
      parts.push({ text: current.replace(/\n+$/, ''), section: currentSection });
      current = '';
    }
  };

  for (const line of text.split('\n')) {
    const candidate = current.length === 0 ? line : `${current}\n${line}`;

    if (candidate.length <= maxChars) {
      current = candidate;
      heading = headingOf(line) || heading;
      continue;
    }

    flush();
    currentSection = heading;
    // A single line longer than the cap is vanishingly unlikely in prose, but
    // dropping its tail silently is the exact failure this function prevents.
    // Cut it explicitly so the caller's assertion can see the overflow.
    current = line.length <= maxChars ? line : line.slice(0, maxChars);
    heading = headingOf(line) || heading;
  }

  flush();
  return parts;
}

// Every payload the SessionStart hook must emit, in order. The manifest wires
// one entry per index. If this returns more payloads than the manifest has
// entries, the tail is silently dropped, so hooks/test-hooks.js asserts the two
// counts agree rather than trusting them to stay in step.
function getSessionStartPayloads(maxChars = HOOK_OUTPUT_CAP) {
  const budget = maxChars - MARKER_RESERVE;
  const responseParts = splitForCap(getResponseStylePreamble(), budget);
  const total = responseParts.length;

  const labeled = responseParts.map((part, i) => {
    if (i === 0) {
      return part.text;
    }
    const resumes = part.section ? `, resuming "${part.section}"` : '';
    return `<!-- house-response-style: continued (part ${i + 1} of ${total}${resumes}) -->\n\n${part.text}`;
  });

  return [getStyleCorePreamble(), ...labeled];
}

module.exports = {
  getStyleCorePreamble,
  getResponseStylePreamble,
  getSessionStartPayloads,
  splitForCap,
  HOOK_OUTPUT_CAP,
  STYLE_CORE_PATH,
  RESPONSE_STYLE_PATH,
  FALLBACK,
  RESPONSE_FALLBACK,
};
