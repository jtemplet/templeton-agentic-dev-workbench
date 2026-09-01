---
name: research-synthesize
description: Answer a question from the Research wiki instead of from a single source. Use whenever someone asks what the research says about something, asks the wiki a question, or asks to compare, reconcile, or weigh what several sources claim. Reads the wiki pages that bear on the question, and weighs each claim by the source's recorded validity and verification. Writes the answer as a question page under Research/wiki/questions/, and links it from the research agenda in Research/questions.md. With no question given, it offers the open items on that agenda. Not for adding a new source to the wiki: that is the research-ingest skill.
---

# Research Synthesize

Answers one question from everything the Research wiki already holds. The answer is a page, not
a reply, so the next reader gets the reasoning and the sources rather than a sentence.

This is the reading half of the [Karpathy LLM Wiki
pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The
`research-ingest` skill files what a source says. This skill asks the filed sources a question.

## When to Use

- Someone asks what the research says about a topic the wiki covers.
- Two sources appear to disagree and the disagreement needs a written resolution.
- An open item on the research agenda in `Research/questions.md` is ready to be answered.

## When NOT to Use

- A new source needs to be added to the wiki. Use `research-ingest`.
- The wiki does not exist, meaning there is no `Research/wiki/` directory.
- The question is about the world rather than about the wiki. This skill reads the wiki, and it
  searches the web for nothing.

## Required Workflow

### Step 1: Get the question

Check `$ARGUMENTS` for a question. Use it as written when one is there.

When `$ARGUMENTS` is empty, read `Research/questions.md`, which is the research agenda. Offer its
open items with `AskUserQuestion` and wait for a pick.

**Answer nothing until a question is picked.** A run that guesses which agenda item mattered
wastes the reader's trust in every page it writes.

Two cases end the step early:

- `Research/questions.md` does not exist, or holds no open item. Say so, and ask for a question.
- The user picks nothing. Stop, and write no page.

### Step 2: Find the pages that bear on the question

Search the wiki three ways, because each finds pages the others miss:

1. Read `Research/index.md`, which lists every page with a one-line summary.
2. Grep `Research/wiki/` for the question's nouns, and for each noun's synonyms.
3. Grep the `aliases:` frontmatter field, which holds the alternate names a page answers to.

A page created before the wiki carried `aliases:` has no such field. Treat its title as its only
name, and do not report the missing field as a problem.

Collect two sets: the entity and concept pages that discuss the question, and the source summary
pages behind them. Read both sets. A concept page states the claim; the source page behind it
carries the validity that decides how much the claim is worth.

### Step 3: Weigh each claim

A claim's weight comes from the source page that carries it, through two frontmatter fields that
`research-ingest` writes: `validity` and `verification`.

Start from `validity`:

| `validity` | Starting weight |
|---|---|
| `high` | Strong |
| `moderate` | Moderate |
| `low` | Weak |
| `unclear` | Weak |

Then apply `verification`, which records whether the source was checked against the web for
retractions and replications:

| `verification` | Effect on the starting weight |
|---|---|
| `verified` | No change. |
| `partially-verified` | No change. |
| `unverified` | Drop one step, so Strong becomes Moderate and Moderate becomes Weak. |
| Field absent | Treat it as `unverified`, and say so on the page. |

A source page is missing the `verification` field when it was ingested before the wiki started
recording verification. Dropping its weight one step is deliberate: an unchecked source and a
checked one must not read the same to a future reader.

**Never raise a weight above what the fields say.** A claim that matches your expectation is not
better evidence for matching it.

### Step 4: Draft the answer and its confidence

Write the answer the weighted evidence supports, then set `confidence` from this table:

| `confidence` | The state that earns it |
|---|---|
| `high` | Two or more Strong sources agree, and no Strong source disagrees. |
| `moderate` | One Strong source, or three or more Moderate sources that agree. |
| `low` | Everything else, including any question where Strong sources disagree. |

Strong sources that disagree produce `low` confidence on purpose. A real split in the evidence is
not a strong answer, however strong each side is.

### Step 5: Write the question page

Create the page at `Research/wiki/questions/<Question-Title>.md`, creating
`Research/wiki/questions/` when it does not exist. Build the filename from the question in title
case, with hyphens for spaces.

Read the page first when it already exists, and update it rather than replacing it. A question
answered twice keeps its history.

```yaml
---
tags:
  - research
  - question
type: research-question
status: <open|answered|superseded>
created_at: <today>
last_updated: <today>
confidence: <high|moderate|low>
sources_for: [<source page titles>]
sources_against: [<source page titles>]
---
```

The body carries five sections, in this order:

**Question.** The question in one sentence, as it was asked.

**Current Answer.** The answer the weighted evidence supports, in two or three sentences. State
the confidence and the reason for it in the same paragraph.

**Evidence For.** One line per supporting claim. Every line cites the source page and its
validity, so a reader can weigh the line without opening anything:

```markdown
- [[Source Page Title]] (validity: high, verification: verified): the claim, in one sentence.
```

**Evidence Against.** The same shape, for every claim that contradicts the answer. Write "None
found in the wiki" when there is none, rather than deleting the section.

**What Would Change This Answer.** Two or three bullets naming the finding, the source type, or
the replication that would move the answer. This section is what stops a thin wiki from reading
as settled.

### Step 6: Update the research agenda

Append or update the question's line in `Research/questions.md`, creating the file when it does
not exist:

```markdown
- [x] [[Does X Cause Y]], answered 2026-08-31, confidence: moderate
```

Mark the checkbox only when `status` is `answered`. An item whose page exists but whose status is
`open` keeps an unchecked box, so the agenda still shows the work.

**Every question page is linked from the agenda.** A page nothing links to is a page nobody
finds, and the wiki already has one index too many to search by hand.

### Step 7: Report

```markdown
## Synthesized: <Question>

**Answer:** <one sentence>
**Confidence:** <high|moderate|low>, because <the row from Step 4 that applied>

**Page written:** [[Question Page]]
**Sources weighed:** <count>, of which <count> were dropped one step for missing verification

### Gaps found

- <a claim no source in the wiki supports or contradicts>

### Suggested next sources

- <the source that would raise the confidence, and which row it would move>
```

## Handling Contradictions

Two sources disagreeing is the normal case, not an error. Both belong on the page: the supporting
claim under Evidence For, and the contradicting claim under Evidence Against.

**Never drop the losing side.** A page that records only the winning claim cannot be re-judged
when a third source arrives.

When the disagreement is sharp enough that a reader could act on the wrong half, add the same
callout `research-ingest` uses, on the question page and on both source pages:

```markdown
> [!warning] Contradiction
> [[Source A]] claims X. [[Source B]] claims Y. See [[The Question Page]].
```

## Critical Rules

**Always:**

- Answer only the question that was asked or picked.
- Read the source summary page behind a claim before weighing the claim.
- Take every weight from the `validity` and `verification` fields, never from your own reading.
- Treat an absent `verification` field as `unverified`, and say so on the page.
- Cite the source page and its validity on every evidence line.
- Keep both sides when sources disagree.
- Link every question page from `Research/questions.md`.
- Give the page a `confidence` field and a "What Would Change This Answer" section.

**Never:**

- Modify files in `Research/sources/`. These are immutable.
- Write a page before a question is picked in the no-argument mode.
- Answer from your own knowledge when the wiki holds nothing. Report the gap instead.
- Raise a claim's weight above what its source's frontmatter states.
- Delete the Evidence Against section when it is empty. Write "None found in the wiki".
- Replace an existing question page without reading it first.

## Quality Checklist

Before reporting completion, verify:

- [ ] The question came from `$ARGUMENTS`, or from an agenda item the user picked
- [ ] The wiki was searched three ways: the index, the page text, and the `aliases:` field
- [ ] Every claim's weight traces to a source page's `validity` and `verification`
- [ ] Every source page missing `verification` was dropped one step, and the page says so
- [ ] Every evidence line cites a source page and its validity
- [ ] Contradicting sources appear under Evidence Against, not deleted
- [ ] The page carries `status`, `confidence`, `sources_for`, and `sources_against`
- [ ] The page carries a "What Would Change This Answer" section
- [ ] `Research/questions.md` links the page, and its checkbox matches the page's `status`
- [ ] No file in `Research/sources/` was modified

## Integration

| Before | After |
|---|---|
| `research-ingest` files the sources this skill reads | A gap this skill reports becomes the next source to ingest |
| An ingest appends its Open Questions to `Research/questions.md` | The answered question stays on the agenda as a record |
