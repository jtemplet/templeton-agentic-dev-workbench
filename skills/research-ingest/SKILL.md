---
name: research-ingest
description: Ingest a new source document into the Research wiki. Reads the source, assesses study quality, discusses key takeaways with the user, then creates source summary and entity/concept pages, cross-references them to existing wiki content, and updates the index and log. Follows the Karpathy LLM Wiki pattern; does not modify the immutable Research/sources/ files.
---

# Research Ingest

A systematic technique for adding a new source to a Research wiki. Reads the source, evaluates methodological rigor, discusses with the user, creates structured wiki pages with calibrated validity context, cross-references aggressively, and updates the index and log.

Follows the [Karpathy LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): the human curates sources and directs analysis; the skill does the summarizing, cross-referencing, filing, and bookkeeping.

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

Then read `Research/log.md` to determine which sources have already been ingested. Any file in `Research/sources/` not mentioned in the log is a candidate.

If no new sources are found, inform the user and stop.

### Step 2: Read the Source

Read the source document fully using the Read tool. For PDFs, use the `pages` parameter to read in chunks if needed (max 20 pages per request); read the entire document across multiple calls.

While reading, identify:

- **Key findings or arguments** - the main claims of the source
- **Entities** - people, organizations, systems, datasets mentioned
- **Concepts** - theories, techniques, frameworks, methodologies
- **Methodology** - how the research was conducted
- **Connections** - how this relates to existing wiki content
- **Contradictions** - where this source disagrees with existing wiki pages

### Step 2b: Assess Study Quality

Before discussing with the user, evaluate the methodological rigor and potential biases of the source. This assessment informs how much weight to give the findings.

**Funding and Conflicts of Interest:**

- Who funded the research? (government grant, industry sponsor, foundation, authors' institution)
- Do the authors disclose any conflicts of interest?
- Is the funder's interest aligned with a particular outcome?
- Rate funding bias risk: **Low** (independent/government) | **Medium** (mixed/unclear) | **High** (industry-funded with aligned interests)

**Study Design:**

- What type of study is this? (RCT, cohort, case-control, cross-sectional, meta-analysis, systematic review, case study, opinion/commentary)
- Is it experimental or observational?
- Is there a control group? If not, why not, and how does this affect interpretation?
- Is blinding used? (single-blind, double-blind, triple-blind, open-label) - note that double-blind is the gold standard for eliminating bias
- Is randomization used? If so, how was it implemented?
- Rate study design: **Strong** | **Moderate** | **Weak**, based on position in the evidence hierarchy (meta-analysis > RCT > cohort > case-control > case series > opinion)

**Sample:**

- What is the sample size (n)?
- Is the sample size justified with a power calculation?
- How was the sample recruited? Is it representative of the population the findings are generalized to?
- Are there important demographic limitations (age, sex, geography, socioeconomic status)?
- What is the response/dropout rate, and could attrition bias the results?
- Rate sample quality: **Strong** (n >= 1000, representative, low attrition) | **Moderate** | **Weak** (small n, convenience sample, high dropout)

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

**Overall Validity Assessment:**

Produce a short verdict using this format:

```
Validity: [High / Moderate / Low / Unclear]
- Study design: [type + rating]
- Sample: [n=X, rating]
- Blinding: [yes/no/partial, type]
- Funding: [funder name/type, bias risk]
- Key caveats: [1 to 3 bullet points on the most important limitations]
```

This validity assessment is NOT a reason to dismiss the source; it is context for interpreting the findings. A small, industry-funded study may still surface a real signal; a large RCT may have design flaws. The goal is calibrated skepticism.

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
created_at: <today>
source_type: <paper|article|report|book-chapter|transcript|other>
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

Include sections: Key Takeaways, Study Quality Assessment, Summary, Methodology, Key Findings, Relevance, Quotes, Questions.

The **Study Quality Assessment** section must include the full validity verdict from Step 2b: study design, sample size, blinding, funding source and bias risk, and key caveats. This section should always be visible so future readers calibrate their trust in the findings appropriately.

Incorporate the user's emphasis guidance from Step 3.

### Step 5: Create or Update Entity and Concept Pages

For each significant entity or concept identified:

1. **Check if a wiki page already exists**, use Grep/Glob to search `Research/wiki/`
2. **If it exists**, read the page, update it with information from the new source, increment `source_count`, update `last_updated`, and add the new source to its Sources section
3. **If it doesn't exist**, create a new page at `Research/wiki/<Entity-or-Concept>.md` using this structure:

```yaml
---
tags:
  - research
  - wiki
  - <entity|concept>
type: research-wiki
status: in-progress
created_at: <today>
last_updated: <today>
source_count: 1
related_notes: []
---
```

Include sections: Overview, Key Points, Sources, Connections, Open Questions.

**Cross-reference aggressively.** Every wiki page should link to related pages using `[[wikilinks]]`. Also link to relevant notes elsewhere in the vault when connections exist.

### Step 6: Update the Index

Read `Research/index.md` and update it:

1. Add the new source summary to the **Sources** section
2. Add any new entity pages to the **Entities** section
3. Add any new concept pages to the **Concepts** section
4. Update the **Stats** at the bottom (source count, wiki page count, last updated date)

Each entry format: `- [[Page Title]], one-line summary`

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
- Assess study quality (funding, design, sample, blinding) before discussing with the user
- Include the validity assessment in the briefing AND the source summary page
- Discuss key points with the user before writing wiki pages
- Wait for user input after the briefing, do not skip the discussion
- Use `[[wikilinks]]` for all internal references
- Update the index and log on every ingest
- Check for existing wiki pages before creating duplicates
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
- [ ] Study quality assessed: funding source, study design, sample size, blinding
- [ ] Validity verdict included in briefing AND source summary page
- [ ] Source summary frontmatter includes validity metadata fields
- [ ] Key points were discussed with the user and their guidance incorporated
- [ ] Source summary page created with complete frontmatter and all sections
- [ ] All significant entities and concepts have wiki pages (created or updated)
- [ ] Cross-references link new pages to existing wiki pages
- [ ] `Research/index.md` updated with all new/changed pages
- [ ] `Research/log.md` has an entry for this ingest
- [ ] No files in `Research/sources/` were modified
- [ ] Any contradictions are flagged with callout blocks on both pages
