# 0006. The style core ships as several hook entries, never one

**Date:** 2026-09-01
**Status:** Accepted

## Context

`hooks/style-core-hooks.json` wires the always-on style core. `SessionStart` injects
`hooks/style-core.md` plus the `house-response-style` skill body, so every session starts with
both.

Claude Code caps every hook output string at **10,000 characters**. The cap applies to plain
stdout and to `hookSpecificOutput.additionalContext` alike, so no output format avoids it.
Anything longer is written to a file and replaced with a short preview plus that path.

The combined payload is 14,493 characters: 4,780 for the coding core, 9,713 for the response
style. That is over the cap.

Wired as a single entry, the session received the first 2,000 characters or so plus a file path.
The coding core arrived truncated after principle 4, and **the response style never arrived at
all**.

The part worth remembering is why nobody noticed. Each document opens with a marker line, so a
person can see in any session whether it loaded. The style core's marker is the payload's first
line, inside the surviving preview, so a session looked correctly loaded. The response style's
marker sits at byte 4,780, past the preview cut and inside the discarded remainder. **The one
signal designed to prove the injection worked was the one signal the truncation could not
reach.**

## Options Considered

### Option A: Split across several manifest entries

Ship the payload from several entries that differ only in a payload index. Claude receives the
`additionalContext` of every hook that matched the event, and the cap is per output, so several
entries deliver the whole thing.

- **Pros:** Nothing is lost. Each document arrives whole, marker included. The split is computed
  at run time from the documents themselves, so editing a document re-splits it automatically.
- **Cons:** The manifest carries more than one entry for what reads as one feature, which looks
  like duplication to anyone who has not read this record. The entry count changes as the
  documents change.

### Option B: Shrink the documents under the cap

Cut the style core and the response style until the combined payload fits one entry.

- **Pros:** One entry, no split machinery, nothing to keep in sync.
- **Cons:** The cap becomes an editorial constraint on what the style rules may say. Every future
  addition has to displace something. The response style was in fact cut from 18,886 characters
  to 9,713 on 2026-08-26, and that was worth doing on its own merits, but it did not make the
  combined payload fit: 4,780 plus 9,713 is still over 10,000.

### Option C: Inject a pointer and let the session read the files

Emit a short instruction naming the two files and let the model read them.

- **Pros:** Tiny payload, no cap problem ever.
- **Cons:** Turns a guarantee into a request. A session that does not perform the read starts
  without the style rules, and nothing says so. It also costs a tool call at the start of every
  session, in every project, including sessions that never write code.

## Decision

**Option A. The payload ships from several manifest entries, and they must never be collapsed
into one.**

`getSessionStartPayloads()` in `hooks/preamble.js` decides the split at run time. It cuts on line
boundaries and names the resumed section in each continuation marker, so nothing is
hand-maintained.

Two checks hold the seam shut, both in `node hooks/test-hooks.js`: every payload must fit the
cap, and the manifest must wire exactly one entry per payload. Grow the documents by one part
without adding an entry and the suite fails, rather than dropping the tail in silence.

**Read the entry count from the manifest, never from memory.** It was three until the response
style was cut on 2026-08-26, which brought that document back inside one payload. Today it is
two. The response style now runs 287 characters short of the cap, so the next substantial
addition to it splits again and needs a third entry back.

Option B lost because the cap would start editing the style rules, and because the arithmetic
does not work even after a large cut. Option C lost because it downgrades a guarantee to a
request, and a failed request here is invisible.

## Consequences

**Easier:**

- Both documents arrive whole in every session, markers included, so the loaded-or-not question
  has a trustworthy answer.
- Editing either document is safe. The split recomputes, and the suite fails loudly if the
  manifest no longer matches.

**Harder:**

- The manifest has entries that look redundant. Anyone tidying it up without reading this record
  will reintroduce the exact silent-truncation bug, and the surviving marker will make the result
  look correct.
- The entry count is not a constant. Documentation that states a number goes stale, which is why
  `docs/HOOKS.md` tabulates the sizes and the suite asserts them.
- These hooks fire in **every** project the plugin is loaded for, non-coding sessions included. A
  `SessionStart` hook cannot see the task type.
- Both hooks run through `hooks/run-hook.sh`, which needs `node` on the non-interactive shell's
  PATH. Without `node` the wrapper emits `<!-- house-style-core: FAILED to load ... -->` rather
  than failing silently, because a silent failure here is the thing this whole record exists to
  prevent.
