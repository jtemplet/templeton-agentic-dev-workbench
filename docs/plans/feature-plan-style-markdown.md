# Feature Plan: `style-markdown`

**Date:** 2026-08-26
**Status:** Revised 2026-08-27
**Decomposed:** 2026-08-27, see bd `tadw-49i`, `tadw-rkx`, `tadw-d91`, `tadw-ynb`, `tadw-2l3`
**Revisions:** 2026-08-27, owner decisions recorded under "Resolved Questions" (100-column wrap,
no `code-reviewer` row, rumdl pin bump, no project-local override sentence), which added Decision 5
and M6. 2026-08-27, applied a `/plan-review` pass: corrected the tracked-file counts from 258 and 42
to 129 and 22, replaced a misattributed `AGENTS.md` quotation, added the M6 risk row, acceptance
criterion 14, the wrap-rule scope bullet, a rollback note, and renumbered Decision 6 to 5.

## Summary

`style-markdown` is the house style for authoring Markdown as a work product, a sibling of
`style-python`, `style-go`, `style-frontend`, `style-swift`, and `style-rails`. It fills the one
gap in `/tadw:build`'s routing: `feature-development` maps file extensions to style skills, and
its table covers programming languages only, so a bead whose deliverable is a `SKILL.md` or a
`docs/*.md` page loads no house style at all. That is most of the work in this repository, where
129 of the tracked files are Markdown and 22 are Python.

## Motivation

**The routing gap is real and mechanical.** `skills/feature-development/SKILL.md:82-88` is a
five-row table keyed on `.py`, `.rb`, `.js`, `.swift`, and `.go`. The instruction directly below
it says: "For an unlisted language, say so, name what you will follow instead (the injected core
plus the conventions you read in step 3), and continue." So `/tadw:build tadw-some-doc-bead` in
this repository announces that it has no style guide and proceeds on improvisation.
`skills/code-simplify/SKILL.md:41-47` carries the same table and the same gap.

**The house rules for Markdown exist, but they do not ship and they do not hold.** The em-dash
ban lives in the repository owner's private `~/.claude/CLAUDE.md`, which no plugin consumer ever
loads. Inside this repository it has drifted anyway: 105 em-dashes remain across 10 agent,
command, and skill files, tracked as `tadw-em-dash-cleanup-mtl`. Some of them sit inside output
templates that an agent fills in and emits, so the rule is being broken at runtime in documents
handed to a reader.

**Three beneficiaries, in order.** The agent running `/tadw:build` in this repository, which is
where nearly every bead's deliverable is Markdown. Any consumer of the `tadw` plugin who writes
documentation with `/tadw:build`. The maintainer, who currently reviews Markdown against rules
that live only in their own head and their own machine's config.

## Scope

### In Scope

- A new skill at `skills/style-markdown/SKILL.md`, matching the sibling shape: frontmatter with
  `name` and `description`, a "When to Use / When NOT to Use" section, a "Universal Core
  (injected)" section that names what it does not restate, numbered principles, an anti-pattern
  table, and a quality checklist. Target length 250 to 320 lines, in line with `style-python`
  (300), `style-go` (307), and `style-testing` (277).
- One skill covering all Markdown, with an agent-reader versus human-reader delta table inside
  it. See "Decision 1".
- An explicit layering statement naming what each lower layer already owns, so no rule in the
  skill duplicates `hooks/style-core.md`, `skills/house-response-style/SKILL.md`, or rumdl. See
  "Decision 2".
- Routing edits so the skill is loaded automatically: `skills/feature-development/SKILL.md`,
  `skills/code-simplify/SKILL.md`, `agents/software-engineer.md`, and `commands/build.md`.
- Registration edits: the `AGENTS.md` skill name list and its count (43 to 44), the `README.md`
  skills table, and a `docs/ROUTING.md` section.
- Mechanizing the em-dash ban through rumdl's MD061 rule plus adding `rumdl check .` to the
  check list, rather than through a new Python guard script. See "Decision 4".
- The 100-column wrap rule, stated in the skill at M1 and enforced through MD013 at M6. See
  "Decision 5".

### Out of Scope

- **A Markdown review command** (`/markdown-review`) or a `review-markdown` skill. The style
  skills that carry review guidance do so inline; a separate read-only review command is a
  different feature and would need its own bead.
- **A row in `agents/code-reviewer.md`'s dispatch table.** That agent reviews changed *code*, and
  routing every diff that touches a README into a Markdown review is a scope decision to make
  deliberately, not a side effect of this plan.
- **Rewriting existing documents to the new style.** The skill governs what is written next.
  Rewording the tree to match it would produce a diff nobody can review, and the skill will contain
  a rule against exactly that. The one mechanical exception is the 100-column reflow, which is M6,
  lands on its own bead, and changes line breaks without touching wording. See "Decision 5".
- **Removing the 105 existing em-dashes.** That is `tadw-em-dash-cleanup-mtl`, already filed. M5
  depends on it and does not absorb it.
- **A `style-markdown` delta for a specific documentation system** (MkDocs, Docusaurus, Quarto).
  rumdl supports those flavors; this repository uses none of them.
- **Replacing or extending `docs/AUTHORING.md`.** That file owns which frontmatter fields exist
  for each component type. The skill owns how the `description` text is written.
- **Changing `check_doc_paths.py`.** Its scope stays README, AGENTS, and CLAUDE, and its verdict
  stays WARN.

## Technical Approach

### Architecture

The skill sits in the same slot as every other `style-*` skill: a leaf that other skills load,
never a workflow that loads others.

```text
hooks/style-core.md          (injected: SessionStart + SubagentStart)
skills/house-response-style  (injected: SessionStart only)
        |
        |  deltas on top
        v
skills/style-markdown/SKILL.md
        ^
        |  loaded by extension match
        |
skills/feature-development   <- commands/build.md, agents/software-engineer.md
skills/code-simplify
```

There is no new hook, no manifest change, and no script wired into a workflow. Claude Code
auto-discovers the skill from `skills/style-markdown/SKILL.md`, exactly as `AGENTS.md` describes
under "Manifest File".

### Decision 1: one skill, not two

**Recommendation: one skill.** The agent-reader versus human-reader distinction becomes the
skill's spine, stated in the opening paragraph and expressed as one delta table, rather than a
second registered component.

| | One skill with a delta table | Two skills (`style-markdown-agent`, `style-markdown-docs`) |
|---|---|---|
| Registration cost | One name list entry, one README row, one routing row | Two of each, plus a rule for which one to load |
| Routing | Extension match, same as every sibling | Extension match cannot tell the two apart; needs a content heuristic |
| Shared material | Stated once | Duplicated, and the duplicate drifts |
| Risk | The agent-reader insight gets buried in an appendix | Neither skill is long enough to justify itself |

The routing argument settles it. Both kinds of document are `.md`, so a two-skill split needs a
rule keyed on file *purpose*, which the loading skill cannot evaluate before reading the file. The
mitigation for the burial risk is structural: the agent-reader framing goes in the first paragraph
and in the frontmatter `description`, not in a trailing section.

Files in this repository do not split cleanly either. `README.md` is written for a person and read
by agents doing repository orientation. `AGENTS.md` is read by both and is the file that outranks
every style skill. A split would force a false choice on both.

### Decision 2: the layering rule, which is what keeps the skill from being redundant

This is the single largest risk in the feature, so it gets a mechanism rather than a caution. Every
rule that goes in the skill must pass a **delta test**: name the layer that does not already cover
it. A rule that fails the test does not go in.

| Layer | Loaded how | Already owns | Therefore off limits to `style-markdown` |
|---|---|---|---|
| rumdl, 76 rules | `rumdl fmt --check .` in CI, `rumdl check .` proposed in M5 | Heading increments (MD001), heading style (MD003), one H1 (MD025), list marker consistency (MD004), fence language present (MD040), bare URLs (MD034), table pipe and column consistency (MD055, MD056, MD060), blank lines around fences, tables, and lists, relative link targets exist (MD057), link fragments resolve (MD051), descriptive link text (MD059), unused reference definitions (MD053), trailing newline (MD047) | Any prose restating a mechanical rule. Point at the linter instead. |
| `hooks/style-core.md` | `SessionStart` and `SubagentStart` hooks, always on | The ten TRUE-code principles, and **American spelling, explicitly naming "documentation"** | American spelling. Restating it is the exact redundancy this decision exists to prevent. |
| `skills/house-response-style/SKILL.md` | `SessionStart` only, parent sessions, not subagents | Sentence-level writing: one word for one thing, no metaphors, 25-word and 20-word sentence caps, active voice, plain words, technical names verbatim, define the term in the sentence that uses it | Every sentence-level rule. The skill cites this document as its sentence standard. |
| `style-markdown` | Extension match from `feature-development` or `code-simplify` | Document-level decisions: what a document is for, what shape carries a fact, what to link instead of inline, how a document survives edits | Its own material only. |

**The `house-response-style` boundary, stated exactly.** That document governs a response to the
user. An authored `.md` file is not a response. But its *sentence* rules transfer whole, and its
*response* rules do not. The skill states the split rather than restating either half:

- **Transfers to authored Markdown:** the three rules that outrank the rest, "Say exactly what you
  mean" in full, the ASD-STE100 sentence rules, and "Match the reader".
- **Does not transfer:** "Lead with the answer" as a first-sentence rule (a document leads with its
  purpose, which is the same principle at a different scale), "Cut narration" as written for a
  transcript, "Report your own work", and "End with next actions". A document has no transcript to
  recap and no owner split to close on.
- **The load instruction is the skill's contribution here, not a restatement.**
  `house-response-style` is injected at `SessionStart` into parent sessions only. A subagent that
  writes Markdown, which is exactly what `/tadw:build` produces, never receives it. So
  `style-markdown` instructs: when authoring Markdown inside a subagent, load `/response-style`
  alongside this skill. That closes a live hole rather than duplicating a document.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `skills/style-markdown/SKILL.md` | The skill itself | New |
| `skills/feature-development/SKILL.md` | Add the `.md` row to the Phase 2 style-skill table | Modified |
| `skills/code-simplify/SKILL.md` | Add the `.md` row to the Step 2 table, name the skill in the frontmatter description, add the behavior-preservation caution | Modified |
| `agents/software-engineer.md` | Add the bullet to "Language-aware style" | Modified |
| `commands/build.md` | Add the skill to the Phase 2 list at line 15 | Modified |
| `AGENTS.md` (`CLAUDE.md` is a symlink) | Skill name list, count 43 to 44, routing table row | Modified |
| `README.md` | Skills table row | Modified |
| `docs/ROUTING.md` | A "Markdown and Documentation" section, matching the Go section's shape | Modified |
| `.rumdl.toml` | `[MD061] terms` for the em-dash and en-dash (M5) | Modified |
| `AGENTS.md` check list and `.githooks/pre-push` | Add `rumdl check .` (M5) | Modified |

### Data Model

Not applicable.

### API / Interface

The skill is addressed as `/style-markdown` or `tadw:style-markdown`. It gains no command file.
`AGENTS.md` lines 370 to 373 record the namespace hazard: `commands/<name>.md` and
`skills/<name>/SKILL.md` are addressed as the same `tadw:<name>`, and the command wins, so a
command body that only names its own skill resolves back to itself.

### Content: what goes in, with the delta test applied

Each candidate below carries a verdict and the layer that fails to cover it.

| Candidate | Verdict | Reasoning |
|---|---|---|
| **Who reads this document** | **Keep, as the spine** | No layer covers it. An instruction a model executes and an explanation a person reads fail differently: the model follows a stale instruction literally, the person notices and asks. Consequences: state the rule before the rationale, never leave a decision to inference, and never write a sentence whose meaning depends on a judgment the reader cannot make. |
| **Link out instead of inlining** | **Keep** | No layer covers it, and it is the most repository-characteristic rule here. `AGENTS.md` delegates to `docs/HOOKS.md`, `docs/ROUTING.md`, `docs/AUTHORING.md`, and `docs/PORTABLE-HOOKS.md` rather than growing. Every `style-*` skill carries a "Universal Core (injected)" section naming what it will not repeat. The rule: a document has one job; inline the decision the reader needs to act, link the reference they need to verify. |
| **A number in a document is a claim** | **Keep** | No layer covers it, and it has an incident behind it. `AGENTS.md` says of the hook payload count: "Read the count from the manifest, never from memory", because the figure was three until the response style was cut on 2026-08-26. The registered-skill count in `AGENTS.md` is the same kind of claim, and this plan bumps it. Rule: derive a number from the source, or do not write it. |
| **HTML comment sentinels for machine-read regions** | **Keep** | No layer covers it, and it is grounded in a documented failure. `check_framework_leak.py` located its exempt region by a `## Appendix` heading, and five separate bypasses shipped from that one decision. Rule: when a script must find a region of a document, mark it with a paired HTML comment, never with a heading. |
| **Table versus list versus prose** | **Keep, as a delta** | `house-response-style` has a table rule, but it is scoped to a *response* offering two to four options. The document-scale rule is different: a table when every item has the same fields, a list when items are parallel but unstructured, prose otherwise. State it as a delta and cite the response rule. |
| **Link style: backticked path versus Markdown link** | **Keep, narrow** | rumdl covers existence, fragments, and link text. What is left is the distinction `check_doc_paths.py` already keys on: a backticked repo-relative path *names* a file, a Markdown link says the reader should *go* there. Both are checked, by different tools, so choosing wrongly changes which check sees it. |
| **Line width and hard wrapping** | **Keep, as a stated rule at 100 columns** | Decided by the owner on 2026-08-27. The skill states it plainly: wrap prose at 100 columns, and never reflow a file you are only patching, because reflowing turns a one-line diff into a paragraph-sized one. Enforcement is staged, because the tree is not clean: MD013 is disabled today with the reason recorded in `.rumdl.toml`, and enabling it at `line_length = 100, code_blocks = false, tables = false` reports 1,391 findings in 87 of 123 files. See M6 for the staging, and Decision 5 for why the reflow cannot be automated. |
| **Fence language tags** | **Cut the rule, keep one line** | MD040 enforces presence and `rumdl fmt` auto-fixes it to `text`. What rumdl cannot tell you is which tag is right for non-code, and this repository's answer is `text`. One line, pointing at the linter for the rest. |
| **Heading hierarchy** | **Mostly cut** | MD001, MD003, MD025, and MD080 are mechanical. What survives: what the H1 and the first paragraph owe the reader, which is the document's contract in one sentence. |
| **American spelling** | **Cut** | `hooks/style-core.md` covers it and names "documentation" explicitly. |
| **The em-dash and en-dash ban** | **Keep, one line, plus M5** | No layer covers it today. It lives in a private global `CLAUDE.md` that ships with nothing, so a plugin consumer never sees it. One line in the skill makes it travel; M5 makes it enforced. |
| **The step-down rule applied to prose** | **Keep, one sentence** | `style-core.md` principle 8 is about ordering code. Applying it at document scale is an extension. Keep it to a sentence to stay clear of `house-response-style`'s "lead with the answer". |
| **Frontmatter `description` as an invocation contract** | **Keep, narrow** | `docs/AUTHORING.md` shows which fields exist; nothing says how to write the text. The `description` is what the runtime reads when deciding whether to invoke the skill, so it is a trigger contract in the third person naming its conditions, not a summary. Cross-link `AUTHORING.md` for the field list. |
| **No TBD or TODO in a shipped document** | **Keep, folded in** | Folded into "a document states what is true now, and marks what is not yet decided as an open question with an owner". |
| **Sentence length, voice, word choice** | **Cut, and cite** | `house-response-style` owns all of it. The skill's contribution is the subagent load instruction in Decision 2. |
| **Anti-pattern table** | **Keep** | Matches the sibling shape. Candidates: a heading with no content before the next heading, a list of one item, a table whose every row says the same thing in one column, a link labeled "here", a document that opens by describing itself, a count written from memory, a wholesale reflow inside an unrelated change. |

### Routing edits, exact

**`skills/feature-development/SKILL.md`, the table at lines 82 to 88.**

Before:

```markdown
| Extension | Style skill |
|---|---|
| `.py` | `style-python` |
| `.rb`, `.erb`, `.rake` | `style-rails` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.vue` | `style-frontend` |
| `.swift` | `style-swift` |
| `.go` | `style-go` |
```

After:

```markdown
| Extension | Style skill |
|---|---|
| `.py` | `style-python` |
| `.rb`, `.erb`, `.rake` | `style-rails` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.vue` | `style-frontend` |
| `.swift` | `style-swift` |
| `.go` | `style-go` |
| `.md`, `.markdown` | `style-markdown`, when the document is the deliverable |
```

Plus one paragraph below the table, because the qualifier needs a definition:

> A Markdown file is the deliverable when the bead's acceptance criteria are satisfied by what the
> document says: a skill, an agent, a command, a `docs/` page, an ADR, a plan. It is not the
> deliverable when you are appending a line to a changelog or a release note beside a code change.
> In a repository whose product is documentation, this row fires on most beads, and that is the
> intent.

**`skills/code-simplify/SKILL.md`, the table at lines 41 to 47.** Add the same row, in that
table's column-heading and parenthetical style:

```markdown
| `.md`, `.markdown` | `style-markdown` |
```

In that file's frontmatter `description`, which enumerates the style skills, append
`style-markdown for Markdown` to the parenthetical list.

**`skills/code-simplify` also needs one added caution**, because its contract is "preserving exact
functionality" and a document has no tests. Add to Step 2 or to "What NOT to Simplify":

> For a Markdown deliverable, behavior preservation means the document still gives the same
> instruction. There is no test to run, so the check is a reading: every rule, path, command, and
> number that survived the edit must still be true, and nothing the document told the reader to do
> may have quietly changed.

**`agents/software-engineer.md`, the "Language-aware style" list at lines 35 to 40.** Add:

```markdown
- `style-markdown` for Markdown deliverables (`.md`, `.markdown`): a skill, agent, command, doc, ADR, or plan
```

**`commands/build.md` line 15.** The Phase 2 sentence lists `style-python`, `style-rails`,
`style-frontend`, and `style-swift`. It already omits `style-go`, so fix both: name
`style-markdown` and `style-go` in that list.

### Registration edits, exact

1. **`AGENTS.md` skill count.** `**Registered Skills** (43)` becomes `(44)`. Verify against
   `ls skills | wc -l` rather than against this plan, per the skill's own "a number is a claim"
   rule.
2. **`AGENTS.md` name list.** Insert `style-markdown` in alphabetical position, between
   `style-go` and `style-python` on the line that currently reads
   `` `roadmap-dashboard` `ship` `style-fizzy` `style-frontend` `style-go` `style-python` `style-rails` ``.
3. **`AGENTS.md` task routing table.** Add a row after the Go row:
   `| Write or review Markdown | - | style-markdown |`, with the skill name backticked to match
   the surrounding rows.
4. **`README.md` skills table**, after the `style-go` row at line 174, matching the existing
   three-column shape:
   `` | `style-markdown` | Markdown style for documents an agent reads and executes: link out instead of inlining, sentinels for machine-read regions, numbers derived not remembered | Writing a skill, agent, command, doc, ADR, or plan | ``
5. **`docs/ROUTING.md`.** Add a `### Markdown and Documentation` section after `### Go
   Development`, in the same "**Style Guide:** Use the `style-markdown` skill" plus bullet-list
   shape. `tadw-routing-gaps-9wq` covers the 12 uncovered commands and is not affected by this.

`CLAUDE.md` is a symlink to `AGENTS.md`, so edits 1 through 3 land once.

### Decision 3: the orphan check

`style-markdown` will **not** be reported as an orphan. `/validate-plugin` Step 3 finds skills
"not referenced by any agent or command", and after the routing edits the skill is named in
`agents/software-engineer.md` and `commands/build.md` directly, in addition to two skills. The
seven accepted orphans listed in `AGENTS.md` stay seven.

### Decision 4: no new guard script; use rumdl MD061 instead

**Recommendation: do not write a `check_markdown_style.py`.** Four reasons, in order of weight.

1. **The one invariant with proven drift is already enforceable by the linter this repository
   runs.** rumdl has MD061, "Forbidden terms". Verified against rumdl 0.2.33 on this tree: with
   `[MD061] terms = ["<em-dash>", "<en-dash>"]` merged into the repository's own `.rumdl.toml`,
   `rumdl check .` reports **88 findings in 10 of 123 files** and nothing else. MD061 skips fenced
   code blocks, inline code spans, and YAML frontmatter, which is exactly right here: code samples
   and quoted external text must keep their punctuation.
2. **`style-testing` earned its checker for a reason that does not transfer.** Its invariant is
   "no framework token appears in the body, and one delimited appendix is exempt". No linter can
   express that, and author discipline demonstrably failed to hold it. `style-markdown` has no
   analogous single structural invariant. Writing a script to enforce prose judgment reproduces
   the failure documented in `check_doc_paths.py`'s own header: the prose gate reported 194 misses,
   none of them real.
3. **`check_doc_paths.py` already covers path claims.** A second document checker would overlap
   its rules and disagree with it at the edges.
4. **The gate has a budget.** `.githooks/pre-push` runs 14 checks in tens of seconds, measured at
   46 seconds warm and 68 seconds for a dry-run push. Every new suite is a permanent tax on every
   push in the repository.

**What to add instead, and a hole it closes.** CI runs `rumdl fmt --check .`, which is the
formatter, not the linter. Verified: a document containing a broken relative link and a
non-descriptive link label passes `rumdl fmt --check` with exit 0, while `rumdl check` exits 1 and
names both. So today a broken relative link anywhere outside README, AGENTS, and CLAUDE is caught
by nothing: `check_doc_paths.py` defaults to those three files, and its verdict is WARN by design.
`rumdl check .` currently reports zero issues across 123 files, so adding it to the check list
costs one line and breaks nothing.

### Decision 5: state the 100-column rule now, enforce it after a measured reflow

The owner chose 100 columns on 2026-08-27. Two facts, both measured on this tree with rumdl
0.2.33, decide how to get there rather than whether to.

1. **The tree is far from the rule.** With MD013 enabled at `line_length = 100`,
   `code_blocks = false`, `tables = false`, `rumdl check .` reports **1,391 findings in 87 of
   123 files**. The largest single file is `skills/bead-audit/SKILL.md` at 129 findings. Frontmatter
   is skipped, so a long `description:` field is never flagged, which is correct.
2. **There is no autofix.** `rumdl rule MD013` advertises "Fix is always available", but neither
   `rumdl fmt` nor `rumdl check --fix` reflows a single line. Verified on a copy of
   `skills/style-go/SKILL.md`: both commands leave the file byte-identical, and all 28 findings
   survive. Reflowing 1,391 lines is therefore hand work or a purpose-built script, not a flag.

So enabling MD013 in the same change that adds the skill would either fail the gate on 87 files or
force a reflow diff nobody can review. The rule and its enforcement separate:

- **M1 states the rule in the skill.** Every document written from that point forward wraps at 100.
- **M6 does the reflow and turns MD013 on**, as its own bead, so the mechanical diff lands alone
  and stays reviewable file by file.

This is the same staging M5 uses for the em-dash ban, and for the same reason: a rule the tree
already violates cannot be gated on the day it is written down.

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Author the skill | Write `skills/style-markdown/SKILL.md` to the sibling shape, applying the delta test in Decision 2 to every rule. Include the layering table, the agent-reader spine, the principles kept in the content table, an anti-pattern table, and a quality checklist. | M | The file exists, is 250 to 320 lines, `claude plugin validate .` parses its frontmatter, `rumdl fmt --check .` passes, `rumdl check .` reports zero issues on it, and it contains a "Universal Core (injected)" section naming `hooks/style-core.md`, `house-response-style`, and rumdl as the three layers it does not restate. |
| 2 | Wire the routing | Apply the four routing edits exactly as specified: `feature-development`, `code-simplify` (table, frontmatter description, and the behavior-preservation caution), `software-engineer`, `build.md`. | S | `grep -rl "style-markdown" skills/feature-development/SKILL.md skills/code-simplify/SKILL.md agents/software-engineer.md commands/build.md` returns all four paths, and `commands/build.md` line 15 names both `style-markdown` and `style-go`. |
| 3 | Register the skill | Apply the five registration edits: `AGENTS.md` count, name list, and routing row; `README.md` table row; `docs/ROUTING.md` section. | S | `/validate-plugin` reports zero errors, reports `style-markdown` as referenced rather than orphaned, reports the accepted-orphan set unchanged at seven, and `AGENTS.md`'s stated skill count equals `ls skills \| wc -l`. |
| 4 | Verify the whole gate | Run the full check list from `AGENTS.md`, minus the evals. | S | All 14 checks pass, including `python3 skills/quality-gates/scripts/check_doc_paths.py`, and `python3 skills/style-testing/scripts/check_framework_leak.py` still passes untouched. |
| 5 | Mechanize the em-dash ban | Bump `RUMDL_VERSION` in `.github/workflows/lint.yml` from `v0.2.18` to `v0.2.33`, the version MD061 was verified on. Add the `[MD061]` terms to `.rumdl.toml` with a comment naming the rule's source and its frontmatter blind spot, add `rumdl check .` to the `AGENTS.md` check list and to `.githooks/pre-push`, and update the pre-push check count in `AGENTS.md` from 14 to 15. **Blocked on `tadw-em-dash-cleanup-mtl`.** | S | `rumdl check .` exits 0 on a clean tree, exits 1 naming file and line when an em-dash is added to prose in any tracked `.md` file, exits 0 when that same em-dash sits inside a fenced code block, and `python3 .githooks/test_prepush.py` passes with the new check counted, and the CI Markdown job installs `v0.2.33`. |
| 6 | Enforce the 100-column wrap | Reflow prose to 100 columns across the tree, then remove `MD013` from the `disable` list in `.rumdl.toml` and add `[MD013] line_length = 100, code_blocks = false, tables = false`. Its own bead, landed as a reflow-only change touching no wording. **Depends on M5 having added `rumdl check .` to the gate**, since `rumdl fmt --check` does not run MD013. | L | `rumdl check .` exits 0 across all tracked Markdown, the diff changes line breaks only (`git diff --word-diff` reports no added or removed words), and `python3 skills/quality-gates/scripts/check_doc_paths.py` still passes. |

**Ordering.** M1 through M4 are one deliverable and should land together; the skill is not useful
unreachable, which is the failure the `style-testing` plan caught late and fixed by adding a
dispatch milestone. M5 is independently deliverable and can land before or after, subject to its
block.

**Rollback.** For M1 through M4 it is deleting `skills/style-markdown/SKILL.md` and reverting the
routing and registration rows, which touch no logic. For M5 and M6 it is reverting the `.rumdl.toml`
keys each one adds.

**M5's fallback if `tadw-em-dash-cleanup-mtl` stalls.** Add `rumdl check .` to the check list now
without the MD061 terms. That closes the broken-relative-link hole immediately at zero cost, and
the MD061 line becomes a one-line follow-up on the cleanup bead.

## Acceptance Criteria

1. Given a repository whose next change is a Markdown deliverable, when `/tadw:build <bead-id>`
   runs Phase 2, then its "Oriented" output names `style-markdown` under "Style skills loaded",
   and it does not emit the "For an unlisted language" fallback sentence.
2. Given `skills/code-simplify/SKILL.md` and a diff containing only `.md` files, when Step 2's
   table is read, then it maps `.md` and `.markdown` to `style-markdown`, and the file states what
   behavior preservation means for a document.
3. Given `/validate-plugin`, when it runs after the change, then it reports zero errors, does not
   list `style-markdown` among orphaned skills, and lists exactly the seven accepted orphans named
   in `AGENTS.md`.
4. Given `ls skills | wc -l`, when compared to the number in `AGENTS.md`'s `**Registered Skills**`
   heading, then the two are equal, and both read 44.
5. Given `grep -o 'style-markdown' README.md AGENTS.md docs/ROUTING.md`, when run, then each of the
   three files matches at least once.
6. Given `skills/style-markdown/SKILL.md`, when its rules are read one at a time, then no rule
   restates a rumdl rule that is enabled in `.rumdl.toml`, no rule restates American spelling, and
   no rule restates a sentence-level rule from `house-response-style`. Verification is a checklist
   walk: for each numbered principle, the reviewer names the layer that does not cover it. A
   principle for which no such layer can be named fails this criterion.
7. Given `skills/style-markdown/SKILL.md`, when searched, then it contains an explicit instruction
   to load `/response-style` when authoring Markdown inside a subagent, and it names
   `hooks/style-core.md`, `house-response-style`, and rumdl as the three layers beneath it.
8. Given the skill's frontmatter `description`, when read by someone who has not read the body,
   then it names Markdown, names the agent-reader framing, and states the trigger conditions in
   the third person, matching the shape of `style-go`'s description.
9. Given `rumdl fmt --check .` and `python3 skills/quality-gates/scripts/check_doc_paths.py`, when
   run after every edit in M1 through M4, then both exit 0.
10. Given the full `AGENTS.md` check list minus `python3 evals/run.py`, when run after M4, then
    every check passes and the count of checks run is reported.
11. (M5) Given a tracked `.md` file with an em-dash added to a prose sentence, when `rumdl check .`
    runs, then it exits 1 and reports `[MD061]` with that file and line number.
12. (M5) Given the same em-dash placed inside a fenced code block or a YAML frontmatter value, when
    `rumdl check .` runs, then it exits 0, because quoted and external text keeps its punctuation.
13. (M5) Given `python3 .githooks/test_prepush.py`, when run after `rumdl check .` is added to the
    hook, then it passes, and the hook's success line reports 15 checks rather than 14.
14. (M6) Given the tree after the reflow, when `rumdl check .` runs with MD013 enabled at
    `line_length = 100`, then it exits 0 across all tracked Markdown, and `git diff --word-diff`
    for that change reports no added or removed words.

**Coverage.** Criteria 1 and 2 prove the routing gap in "Motivation" is closed. Criteria 3, 4, and
5 prove registration. Criteria 6, 7, and 8 prove the redundancy risk is controlled and prove the
"one skill with an explicit layering statement" scope item. Criteria 9 and 10 prove the change does
not break the existing gates. Criteria 11 through 13 prove the em-dash motivation and the
mechanization scope item. Criterion 14 proves the 100-column wrap rule of Decision 5. The "one skill covering all Markdown" item is proven by criteria 1, 2,
and 3 together: a single name appears in every routing and registration surface.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **The skill is redundant with the injected cores.** Most of what one would write about "how to write well" is already in `house-response-style`, and spelling is already in `style-core.md`. A redundant skill is worse than none: it burns context and teaches the model that style skills repeat themselves. | High | High | The delta test in Decision 2, made an acceptance criterion (6). Every rule must name the layer that does not cover it, checked rule by rule at review. The content table has already cut four candidate areas on this basis. |
| **The skill restates rumdl.** Prose about heading levels, fence tags, and blank lines is the easiest filler to write and the least useful. | Medium | High | The layering table enumerates the rumdl rules that are off limits. Criterion 6 checks it. M5's `rumdl check .` makes the linter the visible authority. |
| **Scope creep into "how to author a tadw component".** Frontmatter, description writing, and the component templates sit right next to Markdown style and could swallow the skill. | Medium | Medium | The boundary is written into the plan: `docs/AUTHORING.md` owns which fields exist, `style-markdown` owns how the `description` text reads. Everything else about component anatomy stays out, and is listed under Out of Scope. |
| **The `.md` row fires too often.** In a repository with a README, nearly every change touches Markdown, so `/tadw:build` could load the skill for a one-line changelog append. | Low | Medium | The row carries the "when the document is the deliverable" qualifier, and the paragraph below the table defines it with examples on both sides. |
| **M5 blocks on a bead open since 2026-08-06.** `tadw-em-dash-cleanup-mtl` is P2 and untouched. | Medium | Medium | The M5 fallback: land `rumdl check .` without the MD061 terms, which is free today and closes the broken-link hole. The MD061 line then rides on the cleanup bead. |
| **MD061 catches only the body.** Verified: it skips YAML frontmatter, where three em-dashes currently sit. So the mechanized rule has a known blind spot. | Low | High | State the limit in the `.rumdl.toml` comment, as `check_framework_leak.py` states its own known limitation. Three occurrences in frontmatter is not worth a bespoke scanner. |
| **`docs/ROUTING.md` drifts further.** Adding a section grows a file that `tadw-routing-gaps-9wq` already tracks as incomplete. | Low | Low | The new section follows the Go section's exact shape, so it does not add a new pattern to reconcile later. |
| **The em-dash ban is stated in two places that can drift.** The skill states it and the private global `CLAUDE.md` also states it. | Low | Low | The skill is the shipping copy of record for Markdown. It states the rule once and points at MD061 for enforcement. |
| **M6 is 1,391 hand-edited lines with no autofix.** Verified: neither `rumdl fmt` nor `rumdl check --fix` reflows a line. The comparable mechanical-cleanup bead, `tadw-em-dash-cleanup-mtl`, has sat open since 2026-08-06. | Medium | High | Accept that the rule ships stated but unenforced until M6 lands, which is the position the em-dash ban is in today. Before starting M6, decide whether a one-off reflow script is in scope; 87 files by hand is what stalls the bead. |

## Dependencies

- **`tadw-em-dash-cleanup-mtl`** blocks M5 only. M1 through M4 do not depend on it.
- **rumdl v0.2.33** for MD061 and for MD013. The owner approved the bump on 2026-08-27, so M5
  raises `RUMDL_VERSION` in `.github/workflows/lint.yml` from `v0.2.18` to `v0.2.33` rather than
  first testing whether the older pin happens to carry MD061. Confirmed present at line 17 of that
  workflow. One line, and it removes the uncertainty instead of measuring it.
- **M6 depends on M5**, not the reverse. CI runs `rumdl fmt --check .`, the formatter, which never
  evaluates MD013. Until M5 adds `rumdl check .` to the gate, turning MD013 on would enforce
  nothing.
- No new runtime dependency, no manifest change, no hook change.

## Testing Strategy

There is no unit test for a Markdown skill, so verification is three layers.

**Mechanical, run on every edit:**

- `rumdl fmt --check .`, which is what CI runs.
- `rumdl check .`, which catches what `fmt --check` does not: broken relative links, link fragments
  that do not resolve, and non-descriptive link text. Verified as a real gap, not a hypothetical.
- `claude plugin validate .`, which parses the new frontmatter.
- `python3 skills/quality-gates/scripts/check_doc_paths.py`, since this plan adds paths to
  `AGENTS.md` and `README.md`.
- The full `AGENTS.md` check list minus the evals, once, at M4.

**Structural, run once at M3:**

- `/validate-plugin`, for the orphan check, the frontmatter name-matches-directory check, and the
  documentation-alignment check between `AGENTS.md` and disk.

**Behavioral, the scenarios that actually matter:**

1. **The routing scenario.** Run `/tadw:build` against a bead whose deliverable is a Markdown file
   in this repository, and read its "Oriented" output. `style-markdown` must appear under "Style
   skills loaded". This is the feature working or not working.
2. **The negative routing scenario.** Run `/tadw:build` against a bead whose deliverable is Python
   with an incidental README line. `style-markdown` should not load, and if it does, the report
   should say why. This tests the qualifier, which is the part most likely to be misread.
3. **The subagent scenario.** Author a document inside a subagent, which does not receive
   `house-response-style`. Confirm the skill's load instruction is followed and the sentence rules
   are in effect.
4. **The redundancy walk.** Read the finished skill against `hooks/style-core.md`,
   `skills/house-response-style/SKILL.md`, and the `rumdl rule` output, one principle at a time.
   This is acceptance criterion 6, and it is a human review step, not a script.
5. **The MD061 fixture, at M5.** A three-case fixture: an em-dash in prose (must fail), the same
   em-dash inside a fenced block (must pass), and the same in frontmatter (documented to pass, with
   the limit recorded). These can live as a throwaway fixture during M5 rather than as a committed
   suite, since MD061 is rumdl's rule and rumdl tests it.

**Not tested, and why.** No blind A/B eval of whether the skill improves the Markdown a model
writes. That is the shape of `tadw-geh` for `style-testing`, which is still open, and the eval
harness is deliberately excluded from every gate because it is non-deterministic and costs real
model calls. If efficacy measurement is wanted, file it as a sibling bead to `tadw-geh` rather than
building it here.

## Resolved Questions

Decided by the owner on 2026-08-27.

1. **Wrap column: 100, stated as a rule.** Not advisory. The skill says it plainly, and M6 makes it
   enforceable after a measured reflow. See Decision 5 for the measurement and why it stages.
2. **`agents/code-reviewer.md` gets no `.md` row.** It stays Out of Scope. The consequence is
   accepted and worth writing down: in this repository `/code-review` continues to review almost
   nothing, because nearly every diff here is Markdown. File it as its own bead when it starts to
   cost something.
3. **Bump the CI rumdl pin to v0.2.33.** Folded into M5. This replaces the question of whether
   `v0.2.18` carries MD061; the plan no longer needs the answer.
4. **No project-local override sentence.** The `style-fizzy` precedent does not carry over, so
   `style-markdown` says nothing about a project-local Markdown skill winning. The sentence the
   draft planned to include is cut. `feature-development` Phase 2 already states the general
   precedence rule, and restating it here would be the exact duplication the delta test in
   Decision 2 exists to prevent.

## Open Questions

None. Every question this plan raised has been decided, and the decisions are recorded above.
