---
name: bead-refine
description: "Refine a bd (beads) backlog by product value: cluster every non-closed bead into themes, pick one theme, and give each bead in it one of seven verdicts (keep, shrink, merge, defer, kill, done, promote). Use whenever someone asks to refine the backlog, prune it, clean it out, or decide whether a bead still deserves to exist, even if they do not say refine by name. It answers 'does this bead deserve to exist?' for a product owner. It is not for 'can this bead be built without mistakes?', which is the bead-audit skill, and not for 'which bead comes first?', which is triage-beads. It computes no score and files no new bead. It grounds each bead by checking only whether the paths and symbols the bead names still exist. It applies the verdicts as bd commands in one batch, and only after the author confirms them."
---

# Bead Refine

Decide which beads deserve to exist. A bead is one issue in the `bd` tracker. Give each bead one of
seven verdicts: keep, shrink, merge, defer, kill, done, or promote.

| Component | Question | Reader |
|---|---|---|
| `bead-refine` skill | Does this bead deserve to exist? | you, as product owner |
| `bead-audit` skill | Can this bead be built without mistakes? | the implementing agent |
| `triage-beads` skill | Of the beads worth building, which comes first? | you, choosing today's work |

**Compute no score.** `triage-beads` owns the value-over-effort arithmetic. A second number here
would disagree with it, and then neither could be trusted. Cite evidence for every verdict instead.

**File no new bead.** `product-manager` and `/product-surface-docs` find gaps. `bead-create` files
them. A skill that both removes and adds beads adds more than it removes. Naming a gap in one
closing line is all this skill may do about it.

**Stop when `bd` does not run.** The verdicts are `bd` commands, so there is no pasted-text
fallback.

## Write the output in plain English

You are writing to the product owner, not to an engineer reading a rubric. Use the writing rules of
Simplified Technical English, specified in ASD-STE100, never its licensed word list.
`house-response-style` carries the same rules.

This binds the theme map, the round table, the detail list, the closing summary, and any bead body
you rewrite under a Shrink verdict. Four rules carry most of it:

1. **Twenty-five words per sentence, and twenty for an instruction.** Cut at "which", "so", "but",
   "because", ", meaning".
2. **Define a term in the sentence that uses it, or drop the term.** Jargon copied from another
   skill is the main failure. `bead-audit` says "band" and "ceiling". The author does not. Write
   "rating word".
3. **Name the mechanism, not the metaphor.** Not "a ceiling stops working", but "a bead pointing at
   a deleted file now gets the word Excellent".
4. **Say the consequence to the reader.** Not "this improves auditability", but "you cannot tell
   whether the number is real".

Use active voice and simple tenses. Keep paths, commands, labels, flags, and bead ids verbatim,
because the author has to type or search for them. The test: could a ten-year-old read a table cell
and decide correctly?

## Scope

The caller passes nothing, or a topic phrase.

- **No argument, which is map mode.** Cluster every non-closed bead into themes and refine the one
  the author picks.
- **A topic phrase, which is topic mode.** Gather the beads matching the phrase, add one dependency
  hop, and refine that set as a single theme.

One run refines **one theme**. A theme's verdicts apply as soon as the author confirms that theme,
so stopping after one loses nothing.

## Required Workflow

### Step 1: Verify bd, then take the census

```bash
bd list --limit 1
bd stats
bd list --status open,in_progress,blocked,deferred,pinned,hooked --limit 0 --json
```

Three details in that last call decide whether the result is right:

- **`--limit 0`.** The default is 50. Omit it on a backlog of 60 and you review the first 50, then
  report a complete map.
- **One comma-separated `--status`.** Repeating the flag keeps only the last value, and says
  nothing about the ones it dropped.
- **Every non-closed status.** A `blocked` bead nobody will ever unblock still inflates the count.
  A `deferred` bead is one the author half-killed without deciding.

**Cross-check before going further.** `bd list --json` returns a bare array with no more-pages
flag. Compare its row count against `bd stats`: the rows must equal Total Issues minus Closed. If
they disagree, say so and stop, because every count after this point is wrong.

The JSON carries `description`, `design`, `acceptance_criteria`, `labels`, `priority`,
`created_at`, `updated_at`, `dependency_count`, and `dependent_count`. Fetch no bead a second time.

If the set is empty, say so and stop.

### Step 2: State the yardstick and let the author correct it

"Why do we even need this?" needs something to measure against. Read these in order, and stop at
the first that states what the product is for: `docs/products/`, a roadmap document, `README.md`,
then `AGENTS.md` or `CLAUDE.md`.

Print what you inferred, and **name the file you read**:

```markdown
**Purpose (inferred from `README.md`):** <one or two sentences>

Correct this before I judge anything against it.
```

Wait for the answer. Every verdict later cites this purpose, and an inferred purpose nobody
corrected is a made-up standard applied to real decisions. When no file carries a purpose, say so,
propose one from what the code appears to do, and wait.

### Step 3: Build the set under review

**Map mode.** Take the whole set to Step 4.

**Topic mode.** Match the phrase against each bead's title, `description`, and `design` by meaning.
Do this yourself. `bd search` matches keywords in titles only, so it would miss "weigh-in modal"
for the phrase "dialog box to capture weight".

Then expand exactly **one hop** in both directions. Walking every edge in a connected backlog
reaches everything.

```bash
bd dep list <seed-ids> --json
bd dep list <seed-ids> --direction=up --json
```

`bd dep list` returns the full record for each bead on an edge, **including closed beads**. Drop
every row whose `status` is `closed`. Giving a verdict to finished work would re-open it.

Mark every surviving bead `topic` (it matched the phrase) or `adjacent` (it arrived through an
edge), and keep that column in the table. An adjacent bead has not been shown to belong to the
topic, and killing one on the strength of a theme it never joined is the mistake this column
prevents.

### Step 4: Ground every bead, then cluster into themes

**Ground every bead, in both modes.** Take the paths and symbols each bead's `description` and
`design` name. Check only whether they still exist:

```bash
git ls-files -- <path>
grep -rn "<symbol>" --include='<glob>' .
```

Read the **output** of both commands, never the exit status. `git ls-files` prints nothing and
exits 0 on a missing path, so an exit-status check would report every target present. `grep` exits
1 on zero matches, and that is the answer "missing" rather than a failed command. Quote the
`--include` glob: the shell expands an unquoted `*.md` before `grep` sees it, and under `fish` the
command then fails to run.

**Ground only the paths the bead treats as already existing.** When the bead's own text says it
adds, creates, or writes that path, skip it. Checking it would report `target missing` for every
bead that adds a file, which is the opposite of the truth.

Record `target present`, `target missing`, or a plain `-` when the bead names nothing checkable. A
bead whose target is gone is frequently the answer to "why do we even need this".

That is the whole grounding check. Read no implementations and judge no correctness. The full
Grounding Audit belongs to `bead-audit`, and it costs more than this skill can spend per bead.

**Then cluster, in map mode only.** Topic mode already has its set, and Step 3 refines it as one
theme. Cluster by what the work is for, using three sources in this order:

1. **The repository's own structure**, as the spine. A bead's body names files and directories, so
   group by the part of the tree the work lands in. This map does not inherit the author's tagging
   mistakes.
2. **Labels**, to name each cluster and check it. Exclude process labels, which say how a bead was
   created rather than what it is for: `needs-human`, `discovered`, `discovered:*`, `source:*`,
   `source-bead:*`, `accepted`, `reviewed`, `implemented`, `in-development`, and any `refined:*`
   this skill wrote earlier. The test is whether the label would make a useful theme name.
3. **Meaning**, for whatever the first two leave homeless.

Four rules on the result:

- **Aim for 4 to 8 themes, each holding 2 or more beads.** Three themes hide the unwanted beads
  inside a big one. Fifteen reproduce the bead-by-bead problem this skill exists to escape.
- **Put every bead in exactly one theme.** A bead in two themes gets killed in one and kept in the
  other, and then the count means nothing.
- **Keep one `Unclustered` bucket** for the beads that share a purpose with nothing else, and print
  it even when it holds zero. Its count is a finding either way. A zero says every bead found a
  home, rather than that the row was dropped.
- **Print the count sum.** The per-theme counts must add up to the set total. Show the arithmetic.

When the set holds fewer than 8 beads, skip clustering, say why, and judge it as one theme.

### Step 5: Rank the themes by suspicion, then let the author pick one

Rank by how likely a theme is to hold beads nobody will build. Four signals, all already in the
JSON: **staleness** (days since any bead was updated), **age** (days since the oldest was created),
**size** (bead count, because a big untouched theme costs the most to carry), and **grounding**
(how many beads name code that no longer exists).

```markdown
## Backlog themes (N beads, M themes)

**Purpose:** <as confirmed in Step 2>

| Theme | Beads | Oldest | Last touched | Targets present | What it is for |
|---|---|---|---|---|---|
| <name> | 9 | 94d | 61d | 4 of 9 | <one clause> |
| Unclustered | 3 | 40d | 12d | 3 of 3 | singletons, no shared purpose |

Counts: 9 + 8 + 6 + 3 = 26. Set total 26 (24 open, 1 in_progress, 1 deferred).
Matches `bd stats`: 56 total - 30 closed = 26.
```

The sum is a claim that no bead was dropped, so it covers the whole set, including the in-progress
and deferred beads.

Then ask with `AskUserQuestion`. Offer the three highest-suspicion themes, plus a fourth option
letting the author name another. Each option's reason states its suspicion evidence.

### Step 6: Judge one theme in a single round

Reuse the grounding from Step 4. Do not compute it again, and do not deepen it. Present the whole
theme at once:

```markdown
## Theme: <name> (N beads)

Judged against: <purpose, one clause>

| # | ID | Title | Type | P | Age | Idle | Blocks | Blocked by | Serves | Target | Verdict | Why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | tadw-abc | ... | task | 3 | 94d | 61d | 0 | 0 | <who, from the Why> | present | Kill | <one short sentence> |

**Detail**

- **1 tadw-abc**: <the evidence for that verdict: a path, a line number, a sha, a sibling bead id, or a field value>

Reply with your corrections, for example "3 and 7 keep, rest as proposed".
```

Rules for that table:

- **`Serves`** comes from the bead's own Why. When the Why names no stakeholder and no constraint,
  the cell reads `nobody named`. That is evidence for Kill on its own. Do not fill it in on the
  bead's behalf.
- **The `Why` cell is one plain sentence of 15 words or fewer.** The whole decision rests on this
  cell, and the author reads it in a narrow column beside twelve others. So 15 words replaces the
  25-word limit here. No subordinate clause, no paths, no line numbers, no shas, no bead ids. Say
  the consequence to the reader, not the property of the bead.

  | Instead of | Write |
  |---|---|
  | "A drifted artifact makes the pre-push gate warn-and-allow, so the gate disables itself in silence" | "The push check quietly stops working, and nothing tells you" |
  | "Same design sentence, same plan milestone, and same size estimate as bead 4" | "This is the same work as bead 4, written twice" |
  | "It pins two regressions that already occurred once in commit a093acc" | "Two old bugs can come back, and this would catch them" |
  | "The vague cell is real and unchanged, but three of five items are already enforced" | "Most of this is already checked. Only two items are left" |

- **Put every verdict's evidence in the `Detail` list**, one bullet per bead, keyed to the row
  number. The table carries the decision, the list carries the proof. Splitting them keeps the
  table readable without the verdict becoming a feeling.
- **Give an in-progress bead no verdict.** Show it with `-` in the Verdict column. Killing a bead
  under construction is a different decision made with different information.
- **One round, corrected by exception.** Do not walk the beads one at a time. One approval round
  trip per bead is the cost that stops this from getting done at all.

### Step 7: Apply the confirmed verdicts in one batch

| Verdict | Means | Command |
|---|---|---|
| **Keep** | Earns its place. Fix the priority if it is wrong | `bd update <id> -p <n>` |
| **Shrink** | The valuable part is worth doing, the rest is not | `bd update <id> -d ... --design ... --acceptance ...` |
| **Merge** | A duplicate or a subset of another bead | `bd supersede <id> --with=<keeper-id>` |
| **Defer** | Real, but not now, and you can name the trigger | `bd defer <id> --reason="<trigger>"` |
| **Kill** | Does not serve the purpose. Close it unbuilt | `bd close <id> --reason="refined out: <why>"` |
| **Done** | The work already happened. Close it as shipped | `bd close <id> --reason="already shipped: <evidence>"` |
| **Promote** | Buried, and actually the main event | `bd update <id> -p 1 --parent <new-parent-id>` |

**Kill and Done are different, and the difference has to reach the tracker.** Kill means the work
was never worth doing. Done means it happened and nobody closed the bead. Both close the bead, so
the reason string is where treating them as one costs you. A shipped bead closed as `refined out:`
tells the next reader you rejected work you actually delivered. So a Done verdict takes no
`refined-out` label, and its reason names the evidence that the work shipped: a version, a
changelog heading, a commit, or a path that now exists.

```bash
bd update <id> --add-label refined-out
bd update <id> --add-label "refined:$(date -u +%Y-%m)"
```

Five rules on applying:

- **Apply nothing the author did not confirm.** A recommended verdict is a proposal, silence is not
  consent, and in practice you cannot undo a Kill applied on a default.
- **Give every Kill a reason beginning `refined out:`**, plus the `refined-out` label. Then
  `bd list --status=closed --label=refined-out` lists every bead this skill retired. Write no
  separate report file, because a second copy goes stale. A kill that turns on a real product
  decision is `/adr`, invoked deliberately.
- **Label every bead that took a verdict `refined:YYYY-MM`**, including the kept ones. A later run
  can then skip beads refined recently. Refinement decays: a Keep from March means little in
  September.
- **A Shrink rewrites the bead, so the bead must still pass its own audit.** Read
  `${CLAUDE_PLUGIN_ROOT}/skills/bead-audit/SKILL.md` first, and keep each section in its native
  `bd` field, per ADR 0001,
  [native tracker fields are canonical](../../docs/adr/0001-native-tracker-fields-are-canonical.md).
- **A pinned bead, and a bead with open blockers, both refuse to close.** Do not reach for
  `--force`. Report a pin and ask, because somebody pinned it deliberately. On a Done verdict the
  blocking edges are usually the stale part, because work that shipped without them was never
  waiting on them: remove the false edges with `bd dep remove <id> <blocker-id>` and let the close
  succeed on its own. Forcing leaves the wrong graph behind, and the next reader inherits it.

Report the result of every command. If one fails, name the bead, the command, and the error, then
continue with the rest. A half-applied batch that says nothing is worse than a failed one that
does.

Finally, export. Mention it only if it fails:

```bash
bd export -o .beads/issues.jsonl
```

### Step 8: Close the session

```markdown
## Refined: <theme> (N beads)

Kept 4 · Shrank 1 · Merged 2 · Deferred 1 · Killed 3 · Done 0 · Promoted 0

Backlog: 27 open before, 21 after.

Remaining themes, by suspicion: <names>. Run `/bead-refine` again to take the next one.
```

You may add **one** closing line naming a gap the theme made obvious. Name it and stop. Filing it
is `/bead-create`, and it is the author's call.

## Critical Rules

**Always:**

- Pass `--limit 0` and one comma-separated `--status`, then check the row count against `bd stats`
- State the inferred purpose, name the file it came from, and wait for a correction before judging
  anything
- Put every bead in exactly one theme, and print the count sum
- Mark topic-mode beads `topic` or `adjacent`
- Write every sentence in Simplified Technical English, per "Write the output in plain English"
- Keep every `Why` cell to one plain sentence of 15 words or fewer, and put its evidence in the
  `Detail` list
- Apply verdicts in one batch, after confirmation, and report the result of each command
- Label every touched bead `refined:YYYY-MM`, and every killed bead `refined-out`

**Never:**

- Compute a value score, an ROI score, or a priority score. That is `triage-beads`
- Read implementations to ground a bead. Checking that a path exists, plus one `grep`, is the whole
  check
- Judge a grounding check by its exit status. `git ls-files` exits 0 on a missing path, and `grep`
  exits 1 when the answer is "missing"
- Give a verdict to a closed bead pulled in by a dependency edge
- Give a verdict to an `in_progress` bead
- Apply a verdict the author did not confirm, or force a pinned bead closed
- File a new bead, or write a session report to `docs/`
- Walk the beads one at a time for approval
- Copy a term out of another skill's text without defining it in the same sentence
