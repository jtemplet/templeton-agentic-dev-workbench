---
description: "Ingest a new source into the Research wiki: read, discuss, summarize, and integrate"
argument-hint: "[path/to/source or leave blank to auto-detect new sources]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/research-ingest/SKILL.md` and follow it to process new source documents in `Research/sources/`.

Read the file rather than invoking the skill by name. `commands/research-ingest.md` and
`skills/research-ingest/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(research-ingest)` returns this file and never reaches the skill.

The ingest operates from the `research-librarian` role: a librarian who applies calibrated skepticism to every source, cross-references aggressively, and treats the user-discussion step as part of the work rather than a formality. Refer to `agents/research-librarian.md` for the role's beliefs and judgment principles.

The skill will:

1. Detect new (unprocessed) sources in `Research/sources/`
2. Read the source fully
3. Assess study quality (funding, design, sample, blinding)
4. Present key takeaways and validity verdict for discussion
5. Create a source summary page in `Research/wiki/`
6. Create or update entity and concept pages with `[[wikilinks]]`
7. Update `Research/index.md` and `Research/log.md`

**Usage examples:**

```text
/research-ingest
/research-ingest Research/sources/attention-is-all-you-need.pdf
/research-ingest Research/sources/scaling-laws-for-neural-lms.md
```
