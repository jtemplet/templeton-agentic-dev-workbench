---
description: "Refine the backlog by product value, in plain English: cluster it into themes, then give each bead one of seven verdicts: keep, shrink, merge, defer, kill, done, or promote. Use whenever asked to refine the backlog, a theme, or a bead's place in it. Not for a request to 'audit' or 'ground' a bead's text against the code: those words belong to the `bead-audit` skill, which answers 'can it be built without mistakes'; this command answers 'does it deserve to exist'."
argument-hint: "[topic phrase]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/bead-refine/SKILL.md`. Follow it to review the backlog as its
product owner and decide which beads deserve to exist.

Read that file. Do not invoke the skill by its name. `commands/bead-refine.md` and
`skills/bead-refine/SKILL.md` share one `tadw:` invocation namespace, and the command wins. So
`Skill(bead-refine)` returns this file and never reaches the skill. If that path does not resolve,
find the file with `Glob: **/skills/bead-refine/SKILL.md` and read it from there.

Pass whatever is in `$ARGUMENTS` to the skill as its scope. With no argument the skill clusters
every non-closed bead into themes and refines the one you pick. With a topic phrase it gathers the
beads matching that phrase, adds one dependency hop, and refines that set.

Two neighboring skills answer different questions, and this one must not drift into either:

| Component | Question | Reader |
|---|---|---|
| `/bead-refine` | Does this bead deserve to exist? | you, as product owner |
| `bead-audit` skill | Can this bead be built without mistakes? | the implementing agent |
| `triage-beads` skill | Of the beads worth building, which comes first? | you, choosing today's work |

The skill will:

1. Check that `bd` runs, fetch every non-closed bead in one unlimited page, and check the row count
   against `bd stats` before trusting any later number
2. Infer what the product is for from `docs/products/`, a roadmap, `README.md`, or `AGENTS.md`, name
   the file it read, and wait for you to correct it
3. Ground each bead by checking only whether the paths and symbols it names still exist, reading the
   output of `git ls-files` and `grep` rather than their exit status
4. Cluster the backlog into 4 to 8 themes, keep one `Unclustered` bucket for the singletons, and
   print the count sum so no bead was dropped
5. Rank the themes by staleness, age, size, and grounding, then ask which one to refine
6. Present that whole theme in one round, each bead carrying a verdict, a 15-word plain-English
   reason, and its evidence in a detail list below the table
7. Apply the confirmed verdicts in one batch as `bd` commands, label every touched bead
   `refined:YYYY-MM`, label every killed bead `refined-out`, and report the result of each command

**It computes no score.** `triage-beads` owns the value-over-effort arithmetic, and a second number
computed here would disagree with it forever. The discipline comes from citing evidence for every
verdict.

**It files no new bead.** Finding gaps belongs to the `product-manager` agent and
`/product-surface-docs`. Filing belongs to `bead-create`. A command that both removes and adds beads
adds more than it removes, and the backlog grows. Naming a gap in one closing line is all it may do.

**It applies nothing you did not confirm.** A recommended verdict is a proposal, and silence is not
consent. In practice you cannot undo a Kill applied on a default.

One run refines one theme. Refining a whole backlog in one sitting is how the session gets abandoned
halfway. A theme's verdicts apply as soon as you confirm that theme. So stopping after one theme
loses nothing.
