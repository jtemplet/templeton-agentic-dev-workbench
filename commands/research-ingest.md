---
description: "Ingest a new source into the Research wiki — read, discuss, summarize, and integrate"
argument-hint: "[path/to/source or leave blank to auto-detect new sources]"
---

Use the `research-ingest` agent to process new source documents in `Research/sources/`.

The agent will:

1. Detect new (unprocessed) sources in `Research/sources/`
2. Read the source fully
3. Present key takeaways for discussion
4. Create a source summary page in `Research/wiki/`
5. Create or update entity and concept pages
6. Update `Research/index.md` and `Research/log.md`

**Usage examples:**

```
/research-ingest
/research-ingest Research/sources/attention-is-all-you-need.pdf
/research-ingest Research/sources/scaling-laws-for-neural-lms.md
```
