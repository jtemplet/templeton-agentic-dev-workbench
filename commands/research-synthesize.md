---
description: "Answer a question from the Research wiki: weigh the sources, write a question page, link it from the agenda"
argument-hint: "[the question, or leave blank to pick from the research agenda]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/research-synthesize/SKILL.md` and follow it to answer a
question from the pages already in `Research/wiki/`.

Read the file rather than invoking the skill by name. `commands/research-synthesize.md` and
`skills/research-synthesize/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(research-synthesize)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/research-synthesize/SKILL.md` and read it from there.

The synthesis operates from the `research-librarian` role: a librarian who weighs a claim by the
source's recorded quality rather than by how well it fits the answer, and who keeps both sides
when sources disagree. Refer to `agents/research-librarian.md` for the role's beliefs and
judgment principles.

The skill will:

1. Take the question from the argument, or offer the open items in `Research/questions.md`
2. Find the pages that bear on it through the index, the page text, and the `aliases:` field
3. Read the source summary page behind every claim
4. Weigh each claim by the source's `validity` and `verification` fields
5. Write a question page under `Research/wiki/questions/` with Evidence For and Evidence Against
6. Link the page from `Research/questions.md`

**Usage examples:**

```text
/research-synthesize
/research-synthesize does sleep restriction reduce working memory
/research-synthesize what do the sources say about scaling laws
```
