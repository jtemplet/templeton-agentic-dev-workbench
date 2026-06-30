#!/usr/bin/env node
// templeton-agentic-dev-workbench - style-core preamble loader
//
// Reads the canonical injected text from style-core.md. If that read fails for
// any reason, returns a small hardcoded fallback so the hook still injects the
// observability marker and the spirit of the core rather than blanking out.

const fs = require('fs');
const path = require('path');

const STYLE_CORE_PATH = path.join(__dirname, 'style-core.md');

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

function getStyleCorePreamble() {
  try {
    const text = fs.readFileSync(STYLE_CORE_PATH, 'utf8');
    // Guard against an empty/whitespace file blanking the injection.
    return text.trim().length > 0 ? text : FALLBACK;
  } catch (e) {
    return FALLBACK;
  }
}

module.exports = { getStyleCorePreamble, STYLE_CORE_PATH, FALLBACK };
