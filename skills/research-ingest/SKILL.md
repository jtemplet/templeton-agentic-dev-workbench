---
name: research-ingest
description: Ingest a new source document into the Research wiki. Reads the source, assesses study quality, discusses key takeaways with the user, then creates source summary and entity/concept pages, cross-references them to existing wiki content, and updates the index and log. Follows the Karpathy LLM Wiki pattern; does not modify the immutable Research/sources/ files.
---

# Research Ingest

A systematic technique for adding a new source to a Research wiki. Reads the source, evaluates
methodological rigor, discusses with the user, creates structured wiki pages with calibrated
validity context, cross-references aggressively, and updates the index and log.

Follows the
[Karpathy LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
the human curates sources and directs analysis; the skill does the summarizing,
cross-referencing, filing, and bookkeeping.

## When to Use

- A new file has appeared in `Research/sources/` that has not yet been logged
- The user explicitly asks to process a research paper, article, report, or transcript
- Existing wiki pages need to be updated with information from a new source

## When NOT to Use

- For ad-hoc note-taking outside the wiki structure
- When `Research/sources/` and `Research/wiki/` directories don't exist (this is wiki-specific)
- For sources you cannot read in full (the workflow assumes complete comprehension)

## Required Workflow

### Step 1: Identify Sources to Ingest

Check `$ARGUMENTS` for a specific source file path. If none provided, scan for unprocessed sources:

```bash
ls Research/sources/
```

Then read `Research/log.md` to determine which sources have already been ingested. Any file in
`Research/sources/` not mentioned in the log is a candidate.

If no new sources are found, inform the user and stop.

### Step 2: Read the Source

Read the source document fully using the Read tool. For PDFs, use the `pages` parameter to read
in chunks if needed (max 20 pages per request); read the entire document across multiple calls.

While reading, identify:

- **Key findings or arguments** - the main claims of the source
- **Entities** - people, organizations, systems, datasets mentioned
- **Concepts** - theories, techniques, frameworks, methodologies
- **Methodology** - how the research was conducted
- **Connections** - how this relates to existing wiki content
- **Contradictions** - where this source disagrees with existing wiki pages

### Step 2b: Assess Study Quality

Before discussing with the user, evaluate the methodological rigor and potential biases of the
source. This assessment informs how much weight to give the findings.

**First, name the genre.** Pick one genre from the table below, write it down, and ask only that
genre's questions. A clinical-trial question asked of an essay returns "not applicable", and the
question that would have caught a weak essay never gets asked.

| Genre | `genre:` value | What it covers |
|---|---|---|
| Empirical study | `empirical-study` | A trial, cohort, survey, meta-analysis, or any paper reporting data it collected |
| ML or CS paper | `ml-cs-paper` | A paper whose result is a model, an algorithm, or a benchmark score |
| Journalism | `journalism` | A news article, an investigation, or a magazine feature by a reporter |
| Essay or opinion | `essay-opinion` | A blog post, an editorial, a position paper, a manifesto |
| Transcript or talk | `transcript-talk` | A conference talk, a podcast, an interview, a lecture |
| Book chapter | `book-chapter` | A chapter or section of a published book |

Two cases the table does not cover:

- **The source mixes genres.** Run the rubric for the form you are reading. A reporter writing
  about one study is journalism, because the reporting is what you have to judge.
- **No genre fits.** Run the closest rubric, record `genre: other` on the page, and say in the
  briefing which rubric you ran and why.

Then run that genre's rubric below. Every genre ends at the same **Overall Validity Assessment**
block, so pages stay comparable across genres.

#### Rubric: Empirical study

**Funding and Conflicts of Interest:**

- Who funded the research? (government grant, industry sponsor, foundation, authors' institution)
- Do the authors disclose any conflicts of interest?
- Is the funder's interest aligned with a particular outcome?
- Rate funding bias risk: **Low** (independent/government) | **Medium** (mixed/unclear) |
  **High** (industry-funded with aligned interests)

**Study Design:**

- What type of study is this? (RCT, cohort, case-control, cross-sectional, meta-analysis,
  systematic review, case study, opinion/commentary)
- Is it experimental or observational?
- Is there a control group? If not, why not, and how does this affect interpretation?
- Is blinding used? (single-blind, double-blind, triple-blind, open-label) - note that
  double-blind is the gold standard for eliminating bias
- Is randomization used? If so, how was it implemented?
- Rate study design: **Strong** | **Moderate** | **Weak**, based on position in the evidence
  hierarchy (meta-analysis > RCT > cohort > case-control > case series > opinion)

**Sample:**

- What is the sample size (n)?
- Is the sample size justified with a power calculation?
- How was the sample recruited? Is it representative of the population the findings are
  generalized to?
- Are there important demographic limitations (age, sex, geography, socioeconomic status)?
- What is the response/dropout rate, and could attrition bias the results?
- Rate sample quality: **Strong** (n >= 1000, representative, low attrition) | **Moderate** |
  **Weak** (small n, convenience sample, high dropout)

**Statistical and Methodological Rigor:**

- Are effect sizes reported alongside p-values or confidence intervals?
- Are multiple comparisons corrected for?
- Is the statistical method appropriate for the data type?
- Are confounders identified and controlled for?
- Are limitations acknowledged honestly?

**Peer Review and Publication:**

- Is the source peer-reviewed? Published in a reputable journal?
- Has it been replicated or contradicted by other studies?
- Is this a preprint (not yet peer-reviewed)?

#### Rubric: ML or CS paper

- What baselines does the paper compare against, and are they the strongest current methods or a
  weak straw man?
- What does the code release include: source code, model weights, training data, or none of them?
- Do the benchmarks support the claim, and is the reported score measured on data the authors did
  not tune on?
- Does the paper report its compute cost, its hyperparameter search, and how many runs each number
  came from?
- Rate study design: **Strong** (strong baselines, full code release, held-out evaluation) |
  **Moderate** | **Weak** (weak baselines, nothing released, tuned on the test set)

#### Rubric: Journalism

- Does the article rest on primary sources the reporter saw, or on secondary reporting of someone
  else's work?
- Are the sources named, and how many independent sources support the central claim?
- What is the outlet's track record, and does it publish corrections when it gets something wrong?
- Does the article separate what was observed from what the reporter concludes?
- Rate study design: **Strong** (primary, named, multi-source) | **Moderate** | **Weak** (single
  anonymous source, or rewritten from another outlet)

#### Rubric: Essay or opinion

- What does the author gain if the reader agrees? Name the incentive: a product, a job, a book, a
  reputation.
- Which claims carry evidence, and which rest on argument alone?
- Does the essay answer the strongest version of the opposing case, or the weakest one?
- Are the cited facts checkable, and do the citations say what the essay says they say?
- Rate study design: **Strong** (evidence-backed, fair to opponents) | **Moderate** | **Weak**
  (assertion only, or a straw man of the other side)

#### Rubric: Transcript or talk

- What is the speaker's expertise here, and what did they build or study themselves?
- Which claims can be checked against a written source, and which exist only in this talk?
- Was the talk prepared and reviewed, or spoken without notes?
- Who hosted or paid for the talk, and is the speaker selling something?
- Rate study design: **Strong** (practitioner, claims checkable elsewhere) | **Moderate** |
  **Weak** (off-the-cuff claims that appear nowhere else)

#### Rubric: Book chapter

- Does the chapter cite its sources, and do those citations point to primary work?
- How old is this edition, and has the field moved since it was published?
- Did the publisher apply editorial or academic review?
- Is the chapter reporting the author's own research, or summarizing other people's?
- Rate study design: **Strong** (cited, current edition, reviewed) | **Moderate** | **Weak**
  (uncited, dated, self-published)

#### Overall Validity Assessment

Every genre ends here, with the same fields, so two pages can be compared. Write `n/a` in any field
the genre does not have. An essay has no sample and no blinding, and `n/a` answers those two fields
instead of leaving them blank.

This governs the verdict block below, not the page frontmatter. Each frontmatter field declares its
own values, and two of them mean different things: `not-applicable` says the genre has no blinding
to report, and `not-reported` says the source should have reported it and did not.

Produce a short verdict using this format:

```text
Validity: [High / Moderate / Low / Unclear]
- Study design: [type + rating]
- Sample: [n=X, rating]
- Blinding: [yes/no/partial, type]
- Funding: [funder name/type, bias risk]
- Key caveats: [1 to 3 bullet points on the most important limitations]
```

This validity assessment is NOT a reason to dismiss the source; it is context for interpreting
the findings. A small, industry-funded study may still surface a real signal; a large RCT may
have design flaws. The goal is calibrated skepticism.

### Step 3: Discuss Key Points with the User

Present a structured briefing:

```markdown
## Source: <Title>

**Authors:** ...
**Year:** ...

### Key Takeaways

1. ...
2. ...
3. ...

### Study Quality Assessment

**Genre:** [empirical-study | ml-cs-paper | journalism | essay-opinion | transcript-talk | book-chapter | other]

**Validity:** [High / Moderate / Low / Unclear]

- **Study design:** [type + rating]
- **Sample:** [n=X, rating]
- **Blinding:** [type or none]
- **Funding:** [funder, bias risk]
- **Key caveats:** [1 to 3 most important limitations]

### Entities Identified

- [Entity], brief description

### Concepts Identified

- [Concept], brief description

### Connections to Existing Wiki

- Links to [[Existing Page]] because ...

### Contradictions or Tensions

- This source claims X, but [[Existing Page]] says Y
```

Then ask the user:

- Given the study quality, how much weight do you want to give these findings?
- What should be emphasized or de-emphasized?
- Are there specific entities or concepts to focus on?
- Any connections to their broader vault they want captured?
- Should any of the identified contradictions be flagged prominently?

**Wait for user input before proceeding.** The user's guidance shapes how the source is integrated.

### Step 4: Create Source Summary Page

Read `Research/index.md` to understand what already exists in the wiki.

Create a source summary page at `Research/wiki/<Source-Title>.md` with this structure:

```yaml
---
tags:
  - research
  - source
type: research-source
status: processed
aliases: [<short title>, <citation key such as "Smith 2024">]
created_at: <today>
source_type: <paper|article|report|book-chapter|transcript|other>
genre: <empirical-study|ml-cs-paper|journalism|essay-opinion|transcript-talk|book-chapter|other>
authors: [<author names>]
year: <publication year>
url: <if available>
doi: <if available>
funding: <funder name or "not disclosed">
funding_bias_risk: <low|medium|high|unclear>
study_design: <RCT|cohort|case-control|cross-sectional|meta-analysis|systematic-review|case-study|opinion|other>
sample_size: <n=X or "N/A">
blinding: <double-blind|single-blind|open-label|not-applicable|not-reported>
validity: <high|moderate|low|unclear>
last_updated: <today>
related_notes: []
---
```

Include sections: Key Takeaways, Study Quality Assessment, Summary, Methodology, Key Findings,
Relevance, Quotes, Questions.

The **Study Quality Assessment** section must include the genre and the full validity verdict
from Step 2b: study design, sample size, blinding, funding source and bias risk, and key
caveats. Carry `n/a` through from the verdict into this section, not into the frontmatter; a
blank field reads as an oversight, and `n/a` reads as an answer. This section should always be
visible so future readers calibrate their trust in the findings appropriately.

Incorporate the user's emphasis guidance from Step 3.

### Step 5: Create or Update Entity and Concept Pages

For each significant entity or concept identified:

1. **Search for a page under any of the name's forms.** Search the page titles and the `aliases`
   lines, and search nothing else:

   ```bash
   ls Research/wiki/ | grep -i "<name>"                 # the title
   grep -ril "^aliases:.*<name>" Research/wiki/          # the aliases
   ```

   Run both once per form: the acronym, the spelled-out form, the singular, and the plural. A
   page titled `Large Language Models` must be found by the name `LLM` when it lists `LLM` as an
   alias.

   Never search the page bodies for this. A body search matches every page that mentions the
   term, which in a wiki of any size returns most of the wiki and answers nothing.

   A title search matches a substring, so it can return a source summary whose title contains
   the name. Read the `type:` field of each hit. Only `type: research-wiki` is an entity or
   concept page; `type: research-source` is a summary of one source and is never the page to
   update here.
2. **If the search finds a page under the name or under one of its aliases**, read the page,
   update it with information from the new source, increment `source_count`, update
   `last_updated`, add the new source to its Sources section, and add any new synonym this
   source used to its `aliases`. Never create a second page for a name an existing page already
   lists as an alias.
3. **If no page carries the name or an alias of it**, create a new page at
   `Research/wiki/<Entity-or-Concept>.md` using this structure:

```yaml
---
tags:
  - research
  - wiki
  - <entity|concept>
  - <theme, as a lower-case hyphenated tag such as exercise-physiology>
type: research-wiki
status: in-progress
aliases: [<synonym>, <acronym>, <plural or spelled-out form>]
created_at: <today>
last_updated: <today>
source_count: 1
related_notes: []
---
```

Include sections: Overview, Key Points, Sources, Connections, Open Questions.

**Give every page a theme tag, and reuse the tags already in the wiki.** A theme tag names the
subject the page belongs to, such as `exercise-physiology` or `ai-coding-agents`. It is the
fourth tag, after the three that describe the page's shape rather than its subject: `research`,
`wiki`, and `entity` or `concept`. Read the theme tags already in use with
`grep -rh "^  - " Research/wiki/ | sort -u`, and reuse a matching one rather than coining a
second name for the same subject. The Map of Content rule below counts pages by this tag, so a
page without one joins no theme and appears in no hub page.

**Fill `aliases` when you create the page, not later.** List every other name a writer might use
for this page: the acronym, the spelled-out form, the plural, and any synonym the source used.
Obsidian resolves a `[[wikilink]]` written with any listed alias to this page, so an alias is what
stops a second page for the same idea. Leave the list empty only when the name has exactly one
form, and say so in the page's Overview section.

**Cross-reference aggressively.** Every wiki page should link to related pages using
`[[wikilinks]]`. Also link to relevant notes elsewhere in the vault when connections exist.

**Create a Map of Content page once a theme reaches eight pages.** A Map of Content page, written
MOC, is a hub page that lists every page on one theme, so the reader has one place to start
instead of a search. A theme is the subject that a group of pages share, and a page declares its
theme through the topic tags in its frontmatter.

Do this for each theme the current ingest touched:

1. Count the pages in `Research/wiki/` carrying that theme's tag, with
   `grep -rl "^  - <theme-tag>$" Research/wiki/ | wc -l`. Count a theme tag only. Never count
   `research`, `wiki`, `entity`, or `concept`: those name a page's shape, not its subject, and
   counting one of them groups the whole wiki into a single hub page.
2. When the count is under eight, do nothing. Seven pages are still readable as a list in the
   index.
3. When the count is eight or more and no `Research/wiki/MOC-<Theme>.md` exists, create it with
   the frontmatter below. Do not reuse the entity and concept schema above: a hub page summarizes
   no source, so `source_count` does not apply to it.

   ```yaml
   ---
   tags:
     - research
     - moc
     - <theme>
   type: research-moc
   status: in-progress
   aliases: [<other names for the theme>]
   created_at: <today>
   last_updated: <today>
   ---
   ```

   Below the frontmatter write a one-line statement of what the theme covers. Then list every
   page in the count as a `[[wikilink]]`. **Give each link a one-line summary of that page.** A
   list of bare links is the search result the hub page exists to replace.
4. When the count is eight or more and the MOC page exists, add the pages this ingest created to
   it, each with its one-line summary, and update its `last_updated`.

### Step 6: Update the Index

Read `Research/index.md` and update it:

1. Add the new source summary to the **Sources** section
2. Add any new entity pages to the **Entities** section
3. Add any new concept pages to the **Concepts** section
4. Add any new Map of Content page to the **Entities** or **Concepts** section, whichever its
   theme belongs to

Each entry format: `- [[Page Title]], one-line summary`

**Write no count into the index.** Do not add a Stats block, a source total, a page total, or a
last-updated date to `Research/index.md`. Delete any Stats block you find there. The index
carries the page lists alone.

Every ingest changes those numbers. This skill cannot recount them on every run, and a stale
count looks exactly like a fresh one.

### Step 7: Update the Log

Append an entry to `Research/log.md`:

```markdown
## [YYYY-MM-DD] ingest | <Source Title>

- **Source:** <filename in Research/sources/>
- **Authors:** <author names>
- **Pages created:** [[Page 1]], [[Page 2]], ...
- **Pages updated:** [[Page 3]], [[Page 4]], ...
- **Key takeaway:** <one-sentence summary of the most important finding>
```

### Step 8: Report

Provide a final summary:

```markdown
## Ingest Complete: <Source Title>

### Pages Created

- [[Source Summary Page]]
- [[New Entity Page]]
- [[New Concept Page]]

### Pages Updated

- [[Existing Page]], added findings from this source

### Open Questions

- Questions raised by this source worth investigating

### Suggested Next Sources

- Topics or papers that would fill gaps identified during ingest
```

## Handling Contradictions

When new information contradicts existing wiki content:

1. **Do not silently overwrite.** Flag the contradiction explicitly.
2. Add a `> [!warning] Contradiction` callout on both the new and existing pages.
3. Include citations to both sources.
4. Let the user decide which claim to prioritize, or maintain both with context.

## Critical Rules

**Always:**

- Read the entire source document before summarizing
- Name the source's genre, then assess study quality with that genre's rubric, before discussing
  with the user
- Include the validity assessment in the briefing AND the source summary page
- Discuss key points with the user before writing wiki pages
- Wait for user input after the briefing, do not skip the discussion
- Use `[[wikilinks]]` for all internal references
- Update the index and log on every ingest, with page lists and no count
- Search the name and every alias of it before creating a page, so a synonym updates the
  existing page instead of creating a second one
- Flag contradictions explicitly with callout blocks
- Increment `source_count` and update `last_updated` on existing pages

**Never:**

- Modify files in `Research/sources/`, these are immutable
- Skip the user discussion step, the user's guidance shapes the integration
- Create wiki pages without YAML frontmatter
- Leave orphan pages, every new page must be linked from at least the index
- Silently overwrite existing wiki content with contradictory information
- Ingest a source that has already been logged

## Quality Checklist

Before reporting completion, verify:

- [ ] Source was read in full
- [ ] Genre named, and study quality assessed with that genre's rubric
- [ ] Validity verdict included in briefing AND source summary page
- [ ] Source summary frontmatter includes the genre and the validity metadata fields
- [ ] Key points were discussed with the user and their guidance incorporated
- [ ] Source summary page created with complete frontmatter and all sections
- [ ] All significant entities and concepts have wiki pages (created or updated)
- [ ] Every page created carries an `aliases` list, or states in its Overview that its name has
      one form
- [ ] The name and every alias of it was searched before each page was created, and no page
      duplicates a name an existing page lists as an alias
- [ ] Every theme this ingest touched that holds eight or more pages has a Map of Content page,
      created or updated
- [ ] Cross-references link new pages to existing wiki pages
- [ ] `Research/index.md` updated with all new/changed pages, and carries no count
- [ ] `Research/log.md` has an entry for this ingest
- [ ] No files in `Research/sources/` were modified
- [ ] Any contradictions are flagged with callout blocks on both pages
