---
description: "Review the backlog by product value in plain English: cluster it into themes, then keep, shrink, merge, defer, kill, promote, or close each bead"
argument-hint: "[topic phrase]"
---

Review the backlog as its product owner. This command answers one question about each bead: **does it deserve to exist?** It is the tool for the moment the backlog has grown past what you can hold in your head, and you no longer remember why half of it is there.

Two neighboring commands answer different questions, and this one must not drift into either:

| Command | Question | Reader |
|---|---|---|
| `/bead-refine` | Does this bead deserve to exist? | you, as product owner |
| `bead-audit` skill | Can this bead be built without mistakes? | the implementing agent |
| `triage-beads` skill | Of the beads worth building, which comes first? | you, choosing today's work |

So this command carries **no score**. `triage-beads` owns the value-over-effort arithmetic, and a second number computed here would contradict it forever. The discipline comes from citing evidence for every verdict, not from a number.

It also **never files a new bead**. Gap-finding belongs to `product-manager` and `/product-surface-docs`; filing belongs to `bead-create`. A command that both prunes and plants will plant more than it prunes, and the backlog gets bigger. Naming a gap in one closing line is the whole permitted output.

## Write every word of this in plain English

You are talking to the product owner, not to an engineer reading a rubric. So **every sentence this command produces follows Simplified Technical English**, the controlled-English standard in ASD-STE100. Take its writing rules, never its licensed word list.

This binds all output: the theme map, the round table, the detail list, the closing summary, and any answer you give when the author asks what a bead is. It also binds any bead body you rewrite under a Shrink.

Six rules carry almost all of it:

1. **One idea per sentence. Twenty-five words at most, and twenty when you tell the reader to do something.** Cut at "which", "so", "but", "because", ", meaning", and ", making".
2. **Define a term in the same sentence you first use it, or do not use it.** Jargon copied out of a skill's own text is the main failure here. `bead-audit` says "band" and "ceiling"; the author does not. Write "rating word" and "the best word it can get".
3. **Name the mechanism, not the metaphor.** "A ceiling stops working" says nothing. "A bead pointing at a deleted file now gets the word Excellent" says what happens.
4. **Say the consequence to the reader.** Not "this improves auditability" but "you cannot tell whether the number is real".
5. **Active voice, and simple tenses.** "The push check stops working", not "the gate would be silently disabled".
6. **Technical names stay exact.** File paths, commands, labels, flags, and bead ids are verbatim, because the author has to type or search for them.

The test is one question: could a ten-year-old read this cell and decide correctly? If not, it is not finished. A verdict the author cannot understand is a verdict they cannot give, so plain language here is not politeness. It is what makes the command work at all.

## Scope (from `$ARGUMENTS`)

- **No argument (map mode).** Cluster every non-closed bead into themes, show the map, and refine one theme you pick.
- **A topic phrase**, such as `/bead-refine new dialog box to capture weight` (topic mode). Gather the beads that match that phrase, plus one dependency hop around them, and refine that set as a single theme.

Either way, one run refines **one theme**. Refining a whole backlog in one sitting is how the session gets abandoned halfway, and a theme's verdicts apply as soon as you confirm that theme, so stopping after one loses nothing.

## Workflow

### Step 1: Verify `bd`, then take the census

```bash
bd list --limit 1
bd stats
```

If `bd` fails, stop. This command cannot review a backlog it cannot read, and there is no pasted-text fallback: the verdicts are `bd` commands.

Then fetch every non-closed bead in one unlimited page:

```bash
bd list --status open,in_progress,blocked,deferred,pinned,hooked --limit 0 --json
```

Three details in that call are load-bearing:

- **`--limit 0`.** `--limit` defaults to 50. Omit it on a backlog of 60 and you review the first 50, then report a complete map.
- **One comma-separated `--status`.** Repeating the flag silently keeps only the last value, so you would review one status and call it the backlog.
- **Every non-closed status, named.** `blocked` beads are exactly the dead weight this command exists to find: a bead nobody will ever unblock still inflates the count. `deferred` beads are ones you already half-killed without deciding.

**Cross-check the sweep before going further.** `bd list --json` returns a bare array with no more-pages flag, so compare its row count against `bd stats`: the rows must equal Total Issues minus Closed. If they disagree, say so and stop, because every count downstream is then wrong.

The JSON already carries `description`, `design`, `acceptance_criteria`, `labels`, `priority`, `created_at`, `updated_at`, `dependency_count`, and `dependent_count`. That is every field the evidence table needs, so no per-bead fetch is required.

If the set is empty, say so and stop.

### Step 2: State the yardstick and let the author correct it

"Why do we even need this?" needs something to measure against. Infer the product's purpose from the repository, in this order, and stop at the first that carries a real statement of what the product is for:

1. `docs/products/*` or an equivalent product doc tree
2. a roadmap document
3. `README.md`
4. `AGENTS.md` or `CLAUDE.md`

Then print what you inferred and **name the file you read**:

```markdown
**Purpose (inferred from `README.md`):** <one or two sentences>

Correct this before I judge anything against it.
```

Wait for the answer. Every theme and bead verdict later must cite this purpose, so an inferred purpose nobody corrected is a fabricated standard applied to real decisions. When no file carries a purpose, say that plainly, propose one from what the code appears to do, and wait.

### Step 3: Build the set under review

**Topic mode.** Match the phrase against each bead's title, `description`, and `design` by meaning, not by keyword. Do this yourself: `bd search` matches keywords in titles only, so it would miss "weigh-in modal" for the phrase "dialog box to capture weight".

Then expand exactly **one hop** in both directions over the seed set:

```bash
bd dep list <seed-ids> --json
bd dep list <seed-ids> --direction=up --json
```

`bd dep list` returns the full issue record for each edge, **including closed beads**, so drop every row whose `status` is `closed` before going further. A closed dependency is finished work, and giving it a verdict would re-litigate something already shipped.

Mark every surviving row `topic` (it matched the phrase) or `adjacent` (it arrived through a dependency edge). Keep that column in the table. An adjacent bead has not been shown to belong to the topic, and killing one on the strength of a theme it never joined is the mistake this column prevents. Stop at one hop: transitive closure over a connected backlog walks to everything.

**Map mode.** Cluster the whole set, per Step 4.

### Step 4: Ground every bead, then cluster into themes (map mode)

**Ground first, because the map reports it.** Take the paths and symbols each bead's `description` and `design` name, and check only whether they still exist:

```bash
git ls-files -- <path>
grep -rn "<symbol>" --include='<glob>' .
```

Read the **output**, never the exit status, in both cases. `git ls-files` on a path that does not exist prints nothing and exits 0, so an exit-status check reports every target present. `grep` exits 1 on zero matches, which is the answer "missing" and not a failed command. Quote the `--include` glob: an unquoted `*.md` is expanded by the shell before `grep` sees it, and under `fish` the command then fails to run at all.

**Ground only the paths the bead treats as already existing.** A path the bead proposes to *create* is not a current-state claim, and checking it reports `target missing` for every bead that adds a file, which is the opposite of the truth. When the bead's own text says it adds, creates, or writes that path, it is not a target. Skip it.

That is the whole grounding check. Read no implementations and judge no correctness: the full Grounding Audit belongs to the `bead-audit` skill, and it costs more than this command can spend per bead. Record `target present` when every named target exists, `target missing` when one does not, and a plain `-` when the bead names nothing checkable. A bead whose target is gone is frequently the answer to "why do we even need this".

Then cluster by **what the work is for**, using three sources in this order:

1. **The repository's own structure**, as the spine. A bead's body names files and directories, so group by the part of the tree the work lands in. This is the honest map of what the project is made of, and it does not inherit your tagging mistakes.
2. **Labels**, to name each cluster and cross-check it. Exclude process labels, which describe how a bead was created or handled rather than what it is for: `needs-human`, `discovered`, `discovered:*`, `source:*`, `source-bead:*`, `accepted`, `reviewed`, `implemented`, `in-development`, and any `refined:*` this command wrote earlier. The test is whether the label would make a useful theme name. "Which part of the product is this for" is a theme; "how did this bead get here" is not.
3. **Meaning**, for whatever the first two leave homeless.

Four rules on the result:

- **Target 4 to 8 themes, each holding 2 or more beads.** Three hides the dead weight inside a big one. Fifteen reproduces the bead-by-bead problem this command exists to escape. A bead that shares a purpose with nothing else is a singleton, and it belongs in `Unclustered` rather than in a theme of one.
- **Every bead lands in exactly one theme.** A bead in two themes gets killed in one and kept in the other, and the count no longer means anything. Pick its primary theme and move on.
- **Keep one explicit `Unclustered` bucket** for the singletons, and print it even when it holds zero. Its count is itself a finding both ways: a backlog of one-offs belonging to no theme is one where the ideas never cohered, and a zero says every bead found a home rather than that the row was dropped.
- **Print the count sum and check it.** The per-theme counts must add up to the set total. Show the arithmetic.

When the set holds fewer than 8 beads, skip clustering, say why, and adjudicate the whole set as one theme.

### Step 5: Rank the themes by suspicion, then let the author pick one

Rank by how likely the theme is to be dead weight, using four signals, all already in the JSON:

- **Staleness**: days since any bead in the theme was updated (`updated_at`)
- **Age**: days since the oldest bead in it was created (`created_at`)
- **Size**: bead count, since a big untouched theme costs the most to carry
- **Grounding**: how many of its beads name code that no longer exists, from Step 4

Print the whole map so nothing is hidden:

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

Every bead in the set sits in one of those rows, in-progress and deferred ones included. The sum is a claim that none was dropped, so it has to cover the whole set rather than the open beads alone.

Then ask, with `AskUserQuestion`: the three highest-suspicion themes as options, plus a fourth that lets the author name another. Their reason strings state the suspicion evidence, so the choice is informed rather than a guess.

### Step 6: Adjudicate one theme in a single round

Reuse the grounding recorded in Step 4. Do not recompute it, and do not deepen it.

Present the whole theme at once:

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

- **`Serves`** comes from the bead's own Why. When the Why names no stakeholder or constraint, the cell reads `nobody named`, which is evidence for Kill in its own right rather than something to fill in on the bead's behalf.
- **The `Why` cell is one plain sentence of 15 words or fewer.** This is the cell the whole decision rests on, and it is read in a narrow column beside twelve others. It is the tightest application of "Write every word of this in plain English" above, so the fifteen-word limit replaces the twenty-five-word one here:
  - One sentence. No subordinate clause. Cut at "which", "so", "but", "because", ", meaning".
  - Common words. Name what happens, not the category it belongs to.
  - No paths, line numbers, shas, or bead ids. Those go in the Detail list below the table.
  - Say the consequence to the reader, not the property of the bead.

  | Instead of | Write |
  |---|---|
  | "A drifted artifact makes the pre-push gate warn-and-allow, so the gate disables itself in silence" | "The push check quietly stops working, and nothing tells you" |
  | "Same design sentence, same plan milestone, and same size estimate as bead 4" | "This is the same work as bead 4, written twice" |
  | "It pins two regressions that already occurred once in commit a093acc" | "Two old bugs can come back, and this would catch them" |
  | "The vague cell is real and unchanged, but three of five items are already enforced" | "Most of this is already checked. Only two items are left" |

- **Every verdict cites its evidence in the `Detail` list**, one bullet per bead, keyed to the row number. The table carries the decision; the list carries the proof. Splitting them is what lets the table stay readable without the verdict becoming a feeling.
- **In-progress beads take no verdict.** Show them for context with `-` in the Verdict column. Someone is mid-flight, and killing a bead under construction is a different decision made with different information.
- **One round, corrected by exception.** Do not walk the beads one at a time. One approval round trip per bead is the cost that stops this from getting done at all.

### Step 7: Apply the confirmed verdicts in one batch

Seven verdicts, each mapping to one `bd` command:

| Verdict | Means | Command |
|---|---|---|
| **Keep** | Earns its place. Fix the priority if it is wrong | `bd update <id> -p <n>` |
| **Shrink** | The valuable part is worth doing, the rest is not | `bd update <id> -d ... --design ... --acceptance ...` |
| **Merge** | A duplicate or a subset of another bead | `bd supersede <id> --with=<keeper-id>` |
| **Defer** | Real, but not now, and you can name the trigger | `bd defer <id> --reason="<trigger>"` |
| **Kill** | Does not serve the purpose. Close it unbuilt | `bd close <id> --reason="refined out: <why>"` |
| **Done** | The work already happened. Close it as shipped | `bd close <id> --reason="already shipped: <evidence>"` |
| **Promote** | Buried, and actually the main event | `bd update <id> -p 1 --parent <new-parent-id>` |

**Kill and Done are different, and the difference has to reach the tracker.** Kill means the work was never worth doing. Done means it happened and nobody closed the bead. Both close it, so the temptation is to treat them as one verdict, and the reason string is where that costs you: a shipped bead closed as `refined out:` tells the next reader you rejected work you actually delivered. A Done verdict therefore takes no `refined-out` label, and its reason names the evidence that the work shipped: a version, a changelog heading, a commit, or a path that now exists. Any aging backlog carries these, because a release bead outlives its release.

Then label what you touched:

```bash
bd update <id> --add-label refined-out
bd update <id> --add-label "refined:$(date -u +%Y-%m)"
```

Five rules on applying:

- **Apply nothing the author did not confirm.** A recommended verdict is a proposal. Silence is not consent, and a Kill applied on a default is unrecoverable in practice.
- **Every Kill carries a reason beginning `refined out:`** plus the `refined-out` label, so `bd list --status=closed --label=refined-out` lists every bead this command ever retired. The reason lives on the bead, where whoever finds it later is already looking. Write no separate report file: a second copy goes stale, and a kill that turns on a real product decision is `/adr`, invoked deliberately.
- **Every bead that took a verdict gets `refined:YYYY-MM`**, kept ones included. A later run can then offer to skip beads refined recently. The date matters because refinement decays: a Keep from March means little in September.
- **A Shrink rewrites the bead, so it must still pass its own audit.** Read `${CLAUDE_PLUGIN_ROOT}/skills/bead-audit/SKILL.md` before rewriting one, and keep each section in its native `bd` field per ADR 0001 (`docs/decisions/0001-native-tracker-fields-are-canonical.md`). A shrunk bead that no longer says why it exists has been damaged, not refined.
- **A pinned bead refuses to close.** `bd close` needs `--force` for one. Report the refusal and ask rather than forcing it: the pin was somebody's deliberate act.
- **A bead with open blockers also refuses to close**, with the same `--force` escape. Do not reach for it. On a Done verdict the blocking edges are usually the stale part: work that shipped without them was never really waiting on them. So remove the false edges with `bd dep remove <id> <blocker-id>` and let the close succeed on its own. Forcing past a refusal leaves the wrong graph behind, and the next reader inherits it.

Report every command's result. If one fails, name the bead, the command, and the error, then continue with the rest. A half-applied batch that says nothing is worse than a failed one that does.

Finally, export, without mentioning it unless it fails:

```bash
bd export -o .beads/issues.jsonl
```

### Step 8: Close the session

```markdown
## Refined: <theme> (N beads)

Kept 4 · Shrank 1 · Merged 2 · Deferred 1 · Killed 3 · Promoted 0

Backlog: 27 open before, 21 after.

Remaining themes, by suspicion: <names>. Run `/bead-refine` again to take the next one.
```

You may add **one** closing line naming a gap the theme made obvious. Name it and stop. Filing it is `/bead-create`, and it is the author's call.

## Critical Rules

**Always:**

- Pass `--limit 0` and one comma-separated `--status`, then cross-check the row count against `bd stats`
- State the inferred purpose, name the file it came from, and wait for a correction before judging anything
- Put every bead in exactly one theme, and print the count sum
- Mark topic-mode rows `topic` or `adjacent`
- Write every sentence in Simplified Technical English, per "Write every word of this in plain English"
- Keep every `Why` cell to one plain sentence of 15 words or fewer, and put its evidence in the `Detail` list
- Apply verdicts in one batch, after confirmation, and report each command's result
- Label every touched bead `refined:YYYY-MM`, and every killed bead `refined-out`

**Never:**

- Compute a value, ROI, or priority score. That is `triage-beads`
- Read implementations to ground a bead. Path existence and a grep are the whole check
- Judge a grounding check by its exit status. `git ls-files` exits 0 on a missing path, and `grep` exits 1 when the answer is "missing"
- Give a verdict to a closed bead pulled in by a dependency edge
- Give an `in_progress` bead a verdict
- Apply a verdict the author did not confirm, or force a pinned bead closed
- File a new bead, or write a session report to `docs/`
- Walk the beads one at a time for approval
- Copy a term out of a skill's own text without defining it in the same sentence
