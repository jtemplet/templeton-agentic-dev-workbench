# Feature Plan: Research Brain Upgrade

**Date:** 2026-08-31
**Status:** Draft

## Summary

Upgrade the Research wiki tooling from a filing system into a working knowledge base. Five
changes: a synthesis skill that answers questions across sources, a validity rubric that adapts
to the source's genre, a web verification step, a batch ingest mode, and Obsidian-native page
output. The work edits `skills/research-ingest/SKILL.md`, `agents/research-librarian.md`, and
`commands/research-ingest.md`, and adds one new skill and one new command.

## Motivation

The current pipeline only puts knowledge in. Nothing ever reads the wiki back, so it is an
archive, not a brain. Four more frictions compound this:

- The validity rubric in Step 2b is written for clinical trials. For an ML paper or an essay,
  most of its questions return "not applicable" noise.
- The rubric asks "has it been replicated?" but the `research-librarian` agent has no
  `WebSearch` or `WebFetch` tool, so the answer is a guess.
- The mandatory per-source discussion means ten new sources cost ten conversations, so
  backlogs form.
- Pages lack `aliases:` frontmatter and hub pages, so the Obsidian graph fragments into
  synonym islands, and the hand-maintained `Research/index.md` drifts.

The beneficiary is the vault owner: ingests get faster and more honest, and the wiki starts
answering questions.

## Scope

### In Scope

- A genre-adaptive validity rubric inside `skills/research-ingest/SKILL.md` Step 2b.
- A new web verification step (Step 2c) and the `WebSearch` and `WebFetch` tools on
  `agents/research-librarian.md`.
- A batch ingest mode that drafts into `Research/staging/` and holds one review conversation.
- Obsidian-native output: `aliases:` frontmatter, MOC hub pages, and a query-generated index.
- A new `research-synthesize` skill and `/research-synthesize` command: question pages plus a
  living research agenda.
- Registration of the new components in `CLAUDE.md` and `README.md`, and the validator pass.

### Out of Scope

- A gardening or maintenance skill (dedupe, orphan sweep, stale-page refresh). File it as a
  follow-up bead.
- Any change to files in `Research/sources/`. They stay immutable.
- An automated behavioral test harness for these skills. The seams stay the existing
  validators, per the seam decision below.
- Changes to any other skill, agent, or command in this plugin.
- Migrating existing wiki pages in any vault. The new page shapes apply from the next ingest
  onward.

## Technical Approach

### Architecture

The ingest half keeps its shape: `commands/research-ingest.md` Reads
`skills/research-ingest/SKILL.md`, and `agents/research-librarian.md` supplies the judgment
layer. The five changes slot into that shape as edits.

The synthesis half mirrors it: a new `commands/research-synthesize.md` Reads a new
`skills/research-synthesize/SKILL.md`. The command must Read the skill file rather than invoke
it, because a command and a skill with one name share the `tadw:` namespace and the command
wins. `commands/research-ingest.md` lines 8 to 10 already document this pattern; copy it.

The two halves meet in the data. Ingest writes pages with validity frontmatter; synthesis reads
that frontmatter to weight claims. Ingest appends to the research agenda; synthesis and later
ingests close agenda items.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `skills/research-ingest/SKILL.md` | Genre rubric, Step 2c, batch mode, Obsidian-native output | Modified |
| `agents/research-librarian.md` | Add `WebSearch` and `WebFetch`; extend beliefs and judgment notes | Modified |
| `commands/research-ingest.md` | Document the batch trigger and the new step list | Modified |
| `skills/research-synthesize/SKILL.md` | Answer a question across sources; write question pages | New |
| `commands/research-synthesize.md` | Entry point; Reads the synthesis SKILL.md | New |
| `CLAUDE.md` name lists and `README.md` tables | Register the two new components | Modified |

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| `rumdl fmt --check .` | Existing | Every edited or new Markdown file is well formed |
| `claude plugin validate .` | Existing | Both new frontmatter blocks parse |
| `/validate-plugin` | Existing | Registration lists match the directories on disk |
| `python3 skills/quality-gates/scripts/check_doc_paths.py` | Existing | Every path the documents name exists |

The components are prose, so the highest seams that exist are the repository's validators. The
user confirmed this seam set on 2026-08-31 and declined a new behavioral harness. Skill behavior
is proven manually against the acceptance criteria.

### Data Model

The wiki page frontmatter is the data model. Changes, all additive:

**Source summary pages** gain three fields:

```yaml
genre: <empirical-study|ml-cs-paper|journalism|essay-opinion|transcript-talk|book-chapter|other>
verification: <verified|partially-verified|unverified>
verification_notes: <one line: retraction check, replication check, DOI resolution>
```

**Entity and concept pages** gain one field:

```yaml
aliases: [<synonyms, abbreviations, alternate spellings>]
```

**Question pages** are a new page type at `Research/wiki/questions/<Question>.md`:

```yaml
---
tags: [research, question]
type: research-question
status: <open|answered|superseded>
created_at: <date>
last_updated: <date>
confidence: <high|moderate|low>
sources_for: []
sources_against: []
---
```

Body sections: Question, Current Answer, Evidence For, Evidence Against, What Would Change This
Answer.

**The research agenda** is one file, `Research/questions.md`. Each line is a checkbox item
linking to a question page or naming an unexplored question with the source that raised it.

**The staging area** is `Research/staging/`, holding draft pages during a batch ingest. It is
empty between ingests; promotion moves files into `Research/wiki/`.

### API / Interface

`/research-ingest` keeps its signature. New behavior: when the scan in Step 1 finds two or more
unprocessed sources, the skill offers batch mode through `AskUserQuestion`. Single-source runs
keep the current interactive flow unchanged.

`/research-synthesize <question>` is new. With a question argument, it answers that question.
With no argument, it reads `Research/questions.md` and offers the open items for selection.

### The five changes in detail

**1. Genre-adaptive validity rubric.** Step 2b gains a genre detection step and a routing
table. Each genre gets a short rubric of five or so questions in place of the one-size clinical
list: empirical study (the current rubric, unchanged), ML/CS paper (benchmarks, baselines, code
and data release, compute honesty), journalism (primary or secondary sourcing, named sources,
outlet track record), essay or opinion (author incentive, argument versus evidence), transcript
or talk (speaker expertise, claims checkable elsewhere), book chapter (citations, edition age).
Every genre still ends in the same `Validity:` verdict block, so pages stay comparable.

**2. Web verification.** A new Step 2c, bounded to three lookups: resolve the DOI or canonical
URL, search for retractions and corrections, search for replications or contradicting work.
Record the outcome in the `verification` and `verification_notes` fields. When web tools are
unavailable, write `verification: unverified` and say so in the briefing; never block the
ingest on it.

**3. Batch mode.** Step 1 counts unprocessed sources. For two or more, the skill reads and
assesses all of them, writes draft briefings and draft pages into `Research/staging/`, then
holds one review conversation covering the whole batch with `AskUserQuestion`. After review it
promotes the drafts, applies the user's emphasis edits, and updates the index and log once.
The "wait for user input" rule survives: the wait happens once per batch instead of once per
source.

**4. Obsidian-native output.** Three edits to Steps 4 through 6. Every entity and concept page
gets `aliases:` populated at creation, and the cross-reference instruction tells the writer to
check aliases before creating a new page, so `[[LLM]]` and `[[Large Language Models]]` resolve
to one page. A new instruction creates or updates a MOC page, meaning a Map of Content hub page
listing a theme's pages, whenever a theme has eight or more pages. Step 6 is rewritten around
the index decision in Open Questions; until that is decided, the skill keeps maintaining
`Research/index.md` by hand but drops the Stats block, because a hand-written count is a claim
the skill cannot keep true.

**5. Synthesis skill.** `skills/research-synthesize/SKILL.md` defines: read the question, find
candidate pages through the index, aliases, and Grep, read the source summaries behind them,
weight each claim by the source's `validity` and `verification` frontmatter, write or update
the question page, and update `Research/questions.md`. The agenda is fed from the other side
too: the ingest skill's Step 7 appends each of the source's Open Questions to
`Research/questions.md` alongside its log entry. Contradiction handling reuses the ingest
skill's callout protocol.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| 0001 | Native tracker fields are canonical for beads | Applies at decomposition time, when `/plan-to-beads` runs; nothing in this plan touches the tracker |
| 0002 | The quality-gates orchestrator fans out to blocking subagents | Not touched; this plan changes no gate |

Neither ADR constrains the design itself.

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Genre rubric | Rewrite Step 2b with genre detection and six genre rubrics; add `genre` to the frontmatter schema | M | Each genre has its own question list, and every genre ends in the same `Validity:` block |
| 2 | Web verification | Add Step 2c to the skill; add `WebSearch` and `WebFetch` to the agent's tools line; add the degraded path | S | The agent frontmatter lists both tools, and the skill states the no-web fallback |
| 3 | Batch mode | Add the batch branch to Step 1, the staging flow, and the single review conversation | M | The skill states the two-source trigger, the `Research/staging/` flow, and the one-wait rule |
| 4 | Obsidian-native output | Add `aliases:`, the alias check before page creation, the MOC rule, and the Stats-block removal; update the Quality Checklist rows to match | M | Steps 4 to 6 carry all four instructions, and the checklist rows match |
| 5 | Synthesis skill and command | Write `skills/research-synthesize/SKILL.md` and `commands/research-synthesize.md`; extend the ingest skill's Step 7 to append each Open Question to `Research/questions.md`; extend the agent's description to cover synthesis, if Open Question 3 is answered that way | L | Both files exist, the command Reads the skill, and the ingest skill's Step 7 appends Open Questions to `Research/questions.md` |
| 6 | Registration and validation | Update the `CLAUDE.md` name lists and counts, both `README.md` tables, the agent's README row, and the routing-gap sentence; run all four seams | S | All four seam commands exit 0 |

## Acceptance Criteria

1. Given an ML paper as the source, when Step 2b runs, then the briefing asks about baselines
   and code release and does not ask about blinding.
2. Given any genre, when Step 2b completes, then the output ends in the unchanged `Validity:`
   verdict block.
3. Given a source with a DOI and working web tools, when Step 2c runs, then the source page
   records `verification` and `verification_notes` naming the retraction and replication
   checks.
4. Given no web access, when Step 2c runs, then the ingest completes with
   `verification: unverified` and the briefing says verification was skipped.
5. Given three unprocessed sources, when `/research-ingest` runs, then the user is offered
   batch mode, drafts appear in `Research/staging/`, and exactly one review conversation
   happens before anything is written to `Research/wiki/`.
6. Given one unprocessed source, when `/research-ingest` runs, then the flow matches the
   current single-source behavior.
7. Given a new concept page, when it is created, then its frontmatter carries `aliases:`, and
   no second page exists for a name that an existing page already lists as an alias.
8. Given a theme reaching eight pages, when an ingest touches that theme, then a MOC page for
   it is created or updated.
9. Given `/research-synthesize "does X cause Y"`, when it completes, then a question page
   exists with Evidence For and Evidence Against sections, each entry citing a source page and
   its validity, and `Research/questions.md` links it.
10. Given an ingest whose source page lists Open Questions, when the ingest completes, then
    each question appears in `Research/questions.md`.
11. When milestone 6 finishes, then `rumdl fmt --check .`, `claude plugin validate .`,
    `/validate-plugin`, and `check_doc_paths.py` all pass, and the `CLAUDE.md` skill and
    command lists include the new names.
12. Given `/research-synthesize` with no argument, when it runs, then the open items in
    `Research/questions.md` are offered for selection and none is answered until one is picked.

**Coverage:** criteria 1 and 2 prove the genre rubric; 3 and 4 the verification step; 5 and 6
batch mode; 7 and 8 the Obsidian-native output; 9, 10, and 12 the synthesis half; 11 the
registration. Every In Scope item is covered.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| SKILL.md grows past useful loading size with six rubrics and a batch flow | Med | Med | Keep each genre rubric to five questions; move nothing to a second file unless the skill passes 500 lines |
| Batch mode erodes the user-discussion principle in practice | High | Low | The one-wait rule is explicit, and promotion out of staging is forbidden before the review conversation |
| Web lookups stall or mislead the validity verdict | Med | Med | Step 2c is capped at three lookups, and verification informs the verdict but never overrides the design rubric |
| Index automation choice (Open Questions) blocks milestone 4 | Med | Med | Milestone 4 ships the hand-maintained index minus the Stats block; the query index lands when the question is answered |
| Synthesis answers overweight a thin wiki and read as authoritative | Med | Med | The question page schema requires `confidence` and a What Would Change This Answer section |

## Dependencies

- `WebSearch` and `WebFetch` must be available to subagents in the user's Claude Code
  environment for Step 2c to verify anything. The degraded path removes the hard dependency.
- The Obsidian index automation depends on the vault having Bases or the Dataview plugin. That
  choice is an Open Question, and milestone 4 does not wait on it.

## Testing Strategy

- The four validator seams above run after every milestone and gate milestone 6.
- Skill behavior is checked manually against acceptance criteria 1 to 10 by running
  `/research-ingest` and `/research-synthesize` in a vault with a few sample sources. This is a
  deliberate manual step; the user declined a behavioral harness.

## Open Questions

- Index automation: replace the body of `Research/index.md` with an Obsidian Bases view, a
  Dataview query, or keep hand maintenance? Depends on which plugin the vault runs. Owner: the
  user.
- Should the research agenda live at `Research/questions.md` (proposed) or as a wiki page
  inside `Research/wiki/`? Owner: the user; the plan proceeds with `Research/questions.md`
  unless overruled.
- Should `agents/research-librarian.md` also carry the synthesis role, or stay ingest-only with
  the command loading the synthesis skill directly? The plan proposes extending the agent's
  description and letting it route by task. Owner: the user. Milestone 5 owns the edit if the
  answer is yes.

## Revision Log

**2026-08-31, after `/plan-review`.** The review returned Ready with one YELLOW on MECE, for
three minor gaps. All five of its recommended changes are applied:

- Criterion 7 now states an observable outcome instead of an internal check.
- Criterion 12 covers `/research-synthesize` with no argument.
- Milestone 5 names the ingest step the agenda harvest edits, which is Step 7.
- Milestone 5 owns the agent-description edit that Open Question 3 may require.
- Milestone 4 lists the Quality Checklist update its "Done when" condition already checked.
