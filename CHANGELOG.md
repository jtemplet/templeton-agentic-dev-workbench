# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.12.0] - 2026-08-24

### Added

- **`/bead-refine`, a review of the backlog by product value.** It answers one question about each
  bead: does it deserve to exist. Nothing answered that before. The `bead-audit` skill asks whether a
  bead can be built without mistakes, and `triage-beads` asks which of the worthwhile ones comes
  first, so both assume every bead should be built. This is a command with no skill, because nothing
  should invoke it contextually. Two modes: with no argument it clusters every non-closed bead into 4
  to 8 themes and refines the one you pick, and with a topic phrase it gathers the beads matching
  that phrase plus one dependency hop. Seven verdicts each map to one `bd` command: Keep, Shrink,
  Merge, Defer, Kill, Done, and Promote. It computes no score, because `triage-beads` owns the
  value-over-effort arithmetic and a second number would contradict it. It files no new bead either:
  a command that both prunes and plants will plant more than it prunes.
- **Every sentence `/bead-refine` writes follows Simplified Technical English.** The reader is the
  product owner, not an engineer reading a rubric, and a verdict they cannot understand is a verdict
  they cannot give. The rule that earns its place is defining a term in the same sentence or not
  using it. Copying jargon out of a skill's own text is the failure it prevents: `bead-audit` says
  "band" and "ceiling", which mean nothing to the person deciding. The `Why` column of the round
  table is capped at one plain sentence of fifteen words, with its evidence in a list below the
  table, so the table stays readable without the verdict becoming a feeling.

### Changed

- **The `auto-ok` label is gone, and nothing in this repository acts on it.** It marked a bead an
  agent could take without asking a person. The label carried no reason, so a reader could not tell
  which of three cases applied: a judgment call, a product or design decision, or a destructive
  action. `bead-create` now states that need in the bead body, where the reason is read. Removed from
  five places in `skills/bead-create/SKILL.md`, from the not-ready example in
  `skills/triage-beads/SKILL.md`, from `docs/ROUTING.md`, and from the label cleanup in
  `.claude/scripts/close_bead_on_pr_merge.sh`. The label was also stripped from all 44 beads that
  carried it.
- **`docs/plans/feature-plan-bead-refine.md` records that it no longer owns the `/bead-refine`
  name.** That plan, from 2026-07-20, reserved the name for a scored quality loop whose milestone 1
  shipped and whose milestones 2 to 4 are blocked. The two are different questions and do not merge,
  so the plan now says a resumed driver needs a new command name.

## [2.11.1] - 2026-08-24

### Fixed

- **`publish-plugin` now forbids amending a pushed release commit, and says what to do instead.**
  Cutting 2.11.0 pushed main at `cc9647e`, then found `b331dac`'s conditional-export change recorded
  nowhere, then amended the pushed commit. An amended commit replaces the one the remote holds, so
  main could then advance only by a force-push, which the skill forbids. Recovery was a
  `git reset --soft` back to the pushed commit and a follow-up commit, so that release is two commits
  and its tag names the second rather than the `chore(release)` one. Step 4 now states that the
  completeness pass finishes before Step 6 opens, Step 6 carries the reset-and-retag recovery for
  when it did not, and both the Never list and the Quality Checklist name the rule. A tag that
  already reached the remote is called out as unrecoverable this way: cut the next patch instead.

## [2.11.0] - 2026-08-24

### Added

- **`publish-plugin`, a skill that cuts and publishes a release.** Publishing was manual and it
  drifted twice: `.claude-plugin/plugin.json` sat at 2.10.1 while main ran 13 commits past its
  release commit, and `v2.10.0` and `v2.10.1` were created locally and never pushed. Neither failure
  announced itself. The skill derives the semver bump from the diff since the last tag against a
  stated rubric, writes the changelog section from the log rather than trusting `Unreleased`, bumps
  the manifest, commits `chore(release): X.Y.Z` touching exactly two files, then tags and pushes main
  before the tag. It delegates a branch land to `ship` rather than carrying a second copy of the
  rebase, gate, and worktree rules. Reading the last tag with `--sort=-v:refname` is deliberate:
  lexical order puts `v2.10.1` above `v2.5.2`, which is how a released tag gets reported as missing.

### Changed

- **`AGENTS.md` is rewritten in Simplified Technical English.** It went from 4,367 words to
  3,613, and from 22 sentences over the ASD-STE100 25-word limit to none. The longest sentence
  was 48 words. Every section now states one fact per sentence and uses the active voice. This
  file is injected into every session in this repository, so its length is a running context
  cost rather than a one-time read.
- **The bead-label hook's rationale moved to `docs/PORTABLE-HOOKS.md`.** It was 78 lines of
  `AGENTS.md`, the longest section in the file, and most of it was incident history rather than
  operating instructions: the `atlas` copy-of-record correction, the 0.53-second `bd show`
  measurement behind the narrowing filters, the two unnoticed outages, and the exit-127 worktree
  failure. `AGENTS.md` keeps what an agent must act on and links to the rest, which is the split
  it already uses for `docs/HOOKS.md`, `docs/ROUTING.md`, and `docs/beads-workflow.md`. No fact
  was dropped: every identifier in the old section still resolves in one of the two files. The
  two documents together are longer than the one they replace, because short sentences take more
  lines. Only the always-loaded half got shorter, which is the half that costs context.

- **`CLAUDE.md` is now a symlink to `AGENTS.md`.** It previously held `@AGENTS.md` plus its own
  copy of the `bd`-managed Beads block, which `AGENTS.md` also carried. The two copies had already
  parted: `AGENTS.md` listed `bd dolt push` in the team-maintainer step and `CLAUDE.md` did not.
  Nothing was lost in the merge, since every other line of `CLAUDE.md` appeared in `AGENTS.md`
  verbatim. One file now means the two names cannot disagree again.
- **`docs/HOOKS.md` payload sizes are asserted rather than remembered.** That document argues the
  three-entry `SessionStart` split from character counts, and nothing measured them, so its table
  said the coding core was 4,499 characters when it had grown to 4,780 and its prose put the
  combined payload at 20,275 when it was 20,411. `node hooks/test-hooks.js` gained a check that
  reads both the prose total and the per-entry table and compares them to the real payloads, so
  editing either injected document now fails the suite instead of silently dating the argument.
  The suite runs 19 checks, up from 18.

- **`/tadw:ship` resolves a `CHANGELOG.md` conflict by keeping both entries.** Step 2 aborted on any
  conflict outside `.beads/issues.jsonl`, on the reasoning that resolving one means judging code. A
  changelog is not code: every branch appends to the same `[Unreleased]` section, so a conflict there
  is structural rather than a disagreement, and both entries are correct. The rule was written by
  exclusion, which is how the changelog got swept in with the source files. Two paths now resolve
  mechanically, in whatever combination the conflicted set holds, and any third path still aborts.
  `.gitattributes` also marks `CHANGELOG.md merge=union` so git keeps both sides here without raising
  the conflict at all. Step 4 gained the third worktree state that this repository is actually in: no
  worktree holding the default branch, and a main checkout parked on an unrelated branch with
  uncommitted files, where the run lands in a temporary worktree instead of moving either one.
- **`/tadw:ship` now ships work that has no bead.** A branch whose name yields no bead id used to
  stop the run, on the reasoning that landing work you cannot name defeats the build loop. That
  reasoning covers a bead that went missing, and not the ordinary case: a unit of work nobody filed a
  bead for, sitting on a reviewed commit. Such a run is now **bead-free**, the path the skill already
  had for a repository with no tracker at all. It skips four things (`bd close`, `bd dolt push`, the
  bead id in the commit subject, and the `Closes` line) and nothing else: every gate, guard, and
  cleanup step still runs, and the report says "bead-free" twice, with the cause. Three tracker stops
  remain, because each one means something is wrong rather than absent: two beads resolving from one
  branch, a bead id passed as an argument that the tracker does not hold, and a bead already closed.
- **`/tadw:ship` is 309 lines shorter, and four of its branches are gone.** The skill was 656 lines
  for a six-command happy path, so most of it was failure handling. Two thirds of the cut is wording:
  the rationale essays behind each rule became one clause each, and the `Critical Rules` "Always"
  list and the 13-item `Quality Checklist` went, because every entry restated a step. The rest is
  behavior, and each removal was checked rather than assumed. **The 19 block-reason slugs are now
  five categories** (`gate`, `conflict`, `tracker`, `git-state`, `internal`), because nothing reads
  them: `SHIP_BLOCKED` appears in this repository only in prose, and `outrigger` never mentions
  `SHIP_DONE`, `SHIP_BLOCKED`, or `tadw:ship` anywhere. Its `closeout_verify=merged` arm checks the
  landing commit is an ancestor of main and the bead reads `closed`, so `SHIP_DONE <hash>` is the
  part of the contract that carries weight, and it is unchanged. The prose beside a stop now carries
  the exact condition, which is what a human reads either way. **The tracker-conflict path no longer
  probes for `outrigger merge-tracker`**, which no installed version ships: `outrigger` answers
  `Unknown command: merge-tracker`. Re-exporting from the database is the whole resolution. **A moved
  base or a rejected push now retries once instead of three times**, dropping the attempt counter
  shared across Steps 4 and 5. **Step 3's six-row runner table became one sentence.** Every guard
  that a dated incident paid for stays: the pre-rebase already-landed check and the worktree removal
  with its three guards (2.10.1), `bd dolt push` and the linked-worktree database check
  (`58d4906`), the `--git-path` existence test, and the gate that fails closed.
- **`pre-push` gained a second stage that refuses a push on a recorded `FAIL` verdict.** A session
  could run `/quality-gates`, read a FAIL, and push anyway, because nothing read the verdict the
  gates recorded. Stage 2 reads `quality-gates-report.json` from the directory
  `git rev-parse --git-dir` resolves, so each worktree reads its own verdict about its own branch.
  Forgiveness is the design: a missing or unparseable report warns and allows, and a verdict
  recorded off the line being pushed warns as stale. Only a recorded FAIL refuses. Both stages
  report separately from one push, and twelve cases in `.githooks/test_prepush.py` pin it against
  real `git push --dry-run` runs.
- **The response-style evals left the ship gate.** The `AGENTS.md` command block *is* the ship gate,
  and it ended with `python3 evals/run.py`, so a non-deterministic paid suite gated every merge.
  Sentence lengths observed across runs were 40, 38, 37, 34, 26, and 22 words against a 35-word
  ceiling. The command stays in the block and the exclusion is stated in prose beside it, the way
  the `pre-push` exclusions are.
- **`/quality-gates` Step 4 is partitioned into lanes with row-level ownership.** It was one
  sequential block of eight gates, so an orchestrator had no statement of who runs what, and three
  cross-gate couplings survived by convention. The table now covers every row the report can
  contain, names the inputs the orchestrator resolves once and no lane may re-derive, and gives the
  per-field rule for reducing two change-coverage rows. The partition is by row rather than by gate,
  because gate 1 splits per suite and gate 2 splits per surface. A residual row keeps the table
  open, so a surface added to `route_qa.py` later cannot end up unowned.
- **The pre-push hook no longer runs anything under `evals/`.** `python3 evals/test_run.py` was its
  fourteenth check, so the hook's documented exclusion list goes from three to four and the stage
  runs 13 checks. Cost is not the argument: that suite calls no model and takes about 2 seconds
  against 68 for the whole stage. The evals are a measurement you run deliberately. Both eval
  commands stay in the `AGENTS.md` list, so the ship gate still runs the harness suite.

- **`/build` now labels its bead `implemented` when the run completes.** The bead-labeling hook
  (both `scripts/label_bead_on_skill_invocation.sh`, which ships to other repositories, and the
  `.claude/scripts/` copy wired here) maps `feature-development` to `implemented` in inject mode,
  gated on the run's own "Feature complete" report with every criterion met. It replaces the
  `coding` label, which the distributed copy applied at invocation and the wired copy never
  applied at all. Apply mode was wrong for this label: the hook fires before the skill runs, so a
  `/build` that stops at Ground for a thin spec would have been labeled implemented. The
  distributed copy also maps the typed `/build` and `/tadw:build` commands, which it previously
  did not recognize, so a typed command labels the same as a Skill-tool invocation.
- **`/quality-gates` now labels its bead `qa-d` from the verdict file, not from an instruction.**
  The hook maps `quality-gates` to gate mode and, at `Stop`, reads
  `<git-dir>/quality-gates-report.json`, the JSON the skill already writes with its verdict verbatim.
  Only a report newer than the pending marker with `"verdict": "PASS"` earns the label; FAIL,
  INCOMPLETE, NO GATES RAN, and an unreadable file leave the bead unlabeled and clear the marker.
  This is what ADR 0002 decided (`docs/decisions/0002-the-quality-gates-orchestrator-fans-out-to-blocking-subagents.md`),
  and it closes `tadw-ci8`: the label no longer depends on which tool ran the gates or on Claude
  honoring an injected instruction. Before this, the distributed copy already used gate mode for
  `quality-gates` but its `Stop` reader knew only `.gstack/qa-reports/*.md`, so the marker sat for
  six hours and expired unlabeled; the wired copy used inject mode, which a typed `/quality-gates`
  never triggered because that command reads `SKILL.md` instead of invoking the skill. The
  marker's third line names the skill, and `Stop` picks the reader from it, so a `/qa` marker
  still reads its `.gstack` report.
- **The two hook copies are one file again.** `.claude/scripts/label_bead_on_skill_invocation.sh`
  is now installed verbatim from `scripts/` by the installer, which also wired `UserPromptSubmit`
  into `.claude/settings.json`. The wired copy's extra `reviewed` entries (`style-frontend`,
  `style-swift`, `style-go`, `terraform-iac-expert`, `agentic-clean-code`) moved into the
  distributed copy first, so nothing it labeled is lost.

### Fixed

- **`AGENTS.md` said CI runs the first four checks in its list; it runs a different four.**
  `.github/workflows/lint.yml` runs `rumdl fmt --check .`, `node hooks/test-hooks.js`, and both
  framework-leak checks, skipping `bash hooks/test-claude-scripts.sh`, which sits third in the
  list. That suite is enforced only by `.githooks/pre-push`, and `AGENTS.md` now says so.
- **`AGENTS.md` claimed `docs/ROUTING.md` covers every row of the routing table.** It covers 18 of
  the 30 commands. Both documents now name the gap, and `tadw-routing-gaps-9wq` covers closing it.
- **`AGENTS.md` ended with an unterminated `<!-- BEGIN BEADS CODEX SETUP -->` marker.** It had no
  closing marker and no block behind it; `bd setup codex` wrote its configuration to `.codex/`
  instead. Removed, so a managed-block rewrite cannot treat the file's tail as its own.
- **`/tadw:ship`'s already-landed check could have destroyed work.** Step 2 built a pathspec by
  expanding a shell variable holding a newline-separated file list. Where `IFS` excludes newline
  that becomes one pathspec with embedded newlines, it matches no file, and `git diff` prints
  nothing and exits 0. Step 2 reads "prints nothing" as "already landed", so the run would skip the
  gate, skip the merge, and delete a branch it never merged. Measured on 2026-08-24: `set -- $FILES`
  reported one argument for a four-file branch, and the documented diff printed 0 lines where
  listing the four paths printed 918. The step now lists the paths, and says why.
- **The wired hook commands failed on every turn when the project directory was gone.** A session
  whose worktree is removed under it keeps running, and `CLAUDE_PROJECT_DIR` then names a directory
  that no longer exists. Every wired command failed before reaching the script: `/bin/sh` reported
  "No such file or directory" and exited 127, and Claude Code showed "Stop hook error",
  "UserPromptSubmit hook error", and "PostToolUse:Bash hook error" on nearly every turn. The hook's
  own failure paths all exit 0 so a session continues, so the wiring was producing exactly the
  failure the script takes care to avoid.
- **`evals/run.py` measured whichever account the shell was last switched to.** It spawned
  `claude -p` with the parent environment inherited whole. A set `ANTHROPIC_API_KEY` failed all 12
  calls at `invocation`, and Bedrock routing was quieter and worse: it completed against another
  account without saying so. `ask()` now builds the child environment from `REDIRECTING_VARS`, five
  names listed one by one with a reason each, and passes everything else through.
- **`decision-matrix-trigger` is graded on its rule, not on markup.** The case had been red in both
  arms since 2026-08-05, and because `python3 evals/run.py` sat in the `AGENTS.md` check list it was
  the ship gate for every branch. Captured through `--json`, the graded string begins "Add a
  nullable column.", so the response led with the recommendation above the table and the rule was
  satisfied; the grader demanded markdown bold or a heading. That was the second formatting proxy to
  fail this case on correct responses. The pattern now requires the first line to name the
  recommended option before any table pipe, which is the order the rule is about.
- **The bead-label hook no longer dirties the tree on every label.** `refresh_export` ran
  `bd export` after every label, leaving the tracked tree modified. Outrigger's pre-flight and
  `/tadw:ship` both refuse a dirty tree, and both hit it in the same session that lost three skills'
  labels. The export now runs in two cases only: the file is already modified, where refreshing it
  dirties nothing further, or `TADW_BEAD_LABEL_EXPORT=1` is set. `bv` reads the `bd` database
  directly, so it loses nothing either way. This had to land with the resolution fix rather than
  after it, because fixing resolution alone would have turned an intermittent collision into one
  firing on every pass.
- **Short and digit-leading bead ids resolve again.** `resolve_bead`'s candidate pattern required at
  least one hyphen and rejected a leading digit, so every short id in a sibling repository was
  invisible to it, and a full build-and-ship session on 2026-08-22 labeled nothing across three
  skills. Candidates now come from three ordered sources: the positional segment of an outrigger
  branch, then the widened pattern, then a cap of twelve unique candidates longest-first. The
  regression case is the real branch that failed.
- **A branch named `<bead-id>-<slug>` now labels its bead.** The bead-labeling hook's candidate
  pattern takes a maximal hyphenated run, so `tadw-b14-hook-resolution-and-clean-tree` arrived as a
  single token, the `tadw-b14` inside it was never offered to the tracker, and the branch resolved
  to no bead: every labeled skill run on it labeled nothing, with no warning beyond a log line.
  Each token now also offers its own hyphen-separated prefixes, longest first, so an id that is
  itself a slug (`tadw-qg-prepush-verdict-gate-tug`) still matches whole before any prefix of it is
  tried, and the branch's positional segment still outranks every prefix. A dotted epic-child
  suffix is never split off, because `hdw-3fe4.3` and `hdw-3fe4` are different beads. The existing
  probe cap bounds the added cost, and it falls on the shortest candidates, so a branch of more
  than twelve hyphen segments resolves nothing rather than probing past the budget. Closes
  `tadw-51e`. This was pre-existing rather than a regression, and it is the same defect
  `close_bead_on_pr_merge.sh` was fixed for from the other direction: its regex was widened so a
  slug id matched whole, and neither hook decomposed a token until now.

## [2.10.1] - 2026-08-21

### Fixed

- **`/ship` no longer reports a shipped bead as blocked.** Its already-merged edge case assumed the
  rebase would produce an empty branch. That holds for a fast-forward or a merge commit, and not for
  a squash-merge, which collapses the branch's commits into one carrying a new patch id. Replaying
  the originals then conflicts with their own landed result, on every file the branch touched, and
  the run aborted with `SHIP_BLOCKED rebase-conflict` about work that had landed cleanly. The case
  is common rather than exotic: it is how most pull requests merge, and how `/ship` itself lands
  work in Step 4, so every bead it shipped was one a later run would misread. Step 2 now compares
  the branch's own files against main **before** rebasing, and routes an empty diff straight to the
  already-merged path.
- **`/ship` now removes the worktree it shipped from.** It previously attempted `git branch -D`,
  watched git refuse because a worktree held the branch, and left both behind with a note that
  removing a worktree was not its job. It now leaves the worktree, removes it from the main
  checkout, then deletes the branch. Three guards come with it: the removal runs from the main
  checkout, because deleting the directory the caller is standing in breaks every command after it;
  the worktree holding the default branch is never removed, matched by branch rather than by
  position; and a dirty worktree stops the removal rather than being forced, since the run still
  shipped and only the cleanup is outstanding.

## [2.10.0] - 2026-08-21

Two things ship together. The tracker is `bd` and only `bd`: the earlier CLI is not installed, and
three shipped skills opened with a gate that could never pass on this machine, so the cutover is a
correctness fix rather than a rename. Alongside it, the plugin gains the two skills it had no
equivalent for, both adapted from Matt Pocock's MIT-licensed set: an interview that runs *before* a
plan exists, and a glossary discipline that gives a project one word per concept.

### Added

- **`grilling`, and `/grill-me`.** The gap it fills: `/plan-feature` explores the codebase and
  drafts a plan, `plan-review` critiques a plan that already exists, and neither one asks the author
  anything first. This interviews you until the design tree is resolved. It computes the
  **frontier**, the questions whose prerequisites are already settled, asks that whole set in one
  numbered round with a recommended answer per question, then recomputes the frontier from your
  answers. A question that depends on another question still open in the same round is deferred, so
  you never answer twice. Facts are the agent's job: it dispatches subagents for anything that takes
  digging and asks you only for decisions. It stops when the frontier is empty and waits for you to
  confirm alignment before anything is written. Its `❓`/`➡️` round format is an explicit, documented
  override of the house response style, which loads in every session and would otherwise argue with
  it. Adapted from <https://github.com/mattpocock/skills>.
- **`domain-modeling`, plus its `CONTEXT-FORMAT.md`.** A project glossary in `CONTEXT.md`, and the
  five active behaviors that keep it true: challenge a term that conflicts with what the glossary
  already says, sharpen an overloaded word into one canonical term, stress-test relationships with
  concrete edge-case scenarios, check a claim against what the code actually does, and write a
  resolved term down the moment it crystallizes rather than batching it. `CONTEXT.md` stays a
  glossary and nothing else: no spec, no scratch pad, no implementation decisions. The original
  shipped its own ADR format writing to `docs/adr/`; that half was dropped, because
  `architecture-decision-record` already owns the format here and writes to `docs/decisions/`. Only
  the three-part offer gate survived (hard to reverse, surprising without context, the result of a
  real trade-off). Adapted from <https://github.com/mattpocock/skills>.
- **`bead-create`, a skill for authoring one bead and filing it.** `plan-to-beads` decomposes a plan
  into many beads; this files a single one from a request, a bug, or a review finding, and does the
  work a plan would otherwise supply: it interviews only for what no artifact can answer, searches
  the tracker for a duplicate before drafting, grounds every current-state claim against
  `origin/main` and records the sha, estimates the diff-size band and splits or refuses, then
  self-audits the draft with the `bead-audit` rubric until it passes. It waits for confirmation, and
  it reads the bead back after creating it, because a create that reports success while leaving
  `design`, `notes`, and `acceptance_criteria` empty is the exact defect ADR 0001 exists to prevent.
  Invoked as `/bead-create`, or by saying "create a bead".

### Fixed

- **`--acceptance`, not `--acceptance-criteria`.** `bd` rejects the longer form as an unknown flag,
  so every `bd update` that `plan-to-beads` prescribed would have failed at the moment it populated
  a new bead. The name came from the earlier CLI and had spread to `bead-audit`, ADR 0001, and the
  bead-refine plan. Verified by creating a bead in a throwaway tracker and reading all four fields
  back.
- **Three availability gates that could never pass.** `plan-to-beads`, `/bead-audit-all`, and
  `triage-beads` each opened with `which br`, whose failure short-circuited the `bd` check beside it
  and made each skill report a working tracker as missing.
- **`collect_beads.py` refreshes the export again.** It shelled out to a command that no longer
  exists and required a `*.db` file that a Dolt workspace does not have, so its refresh had been a
  silent no-op: the dashboard read whatever stale JSONL was on disk. It now runs
  `bd export -o .beads/issues.jsonl`.

### Changed

- **Both `.claude/scripts` hooks are single-backend.** They carried a detector that chose between
  two trackers and a `--db` pin for the one that needed it. `bd` resolves one workspace per
  repository through the git common directory, so the detector, the pin, and the `BACKEND` and
  `tracker_cmd` indirection are gone, and the hooks call `bd` directly.
- **Neither hook commits or pushes the tracker export any more.** Under `bd` the database is
  gitignored and `.beads/issues.jsonl` is a passive export, so committing it staged a file that had
  been stale since the cutover. Both hooks now refresh the export in place and stop. This is what
  makes AGENTS.md's "`bd` never auto-commits or runs git commands" true again.
- **The hook test suite runs on one tracker.** The stub pair became one `bd` stub, the fixture is
  bd-shaped, and the two cases that asserted a `--db` pin were replaced by worktree cases asserting
  that a close and a label from a worktree reach the canonical tracker carrying no pin. 60 checks,
  down from 63, and the suite header records which retired cases lost their subject rather than
  leaving its "every fix has a case" claim silently false.

### Removed

- **`.claude/scripts/autocommit_beads_after_br.sh`**, and its wiring in `.claude/settings.json`. It
  existed to commit a tracker that wrote its state into a git-tracked export. Its first act was to
  detect a `bd` backend and exit, so on this repository it could never do anything. Deleting it
  closed `tadw-0j8`, which was filed against the commits it made unasked.

## [2.9.1] - 2026-08-18

A patch: `ship` gains one command and loses three instructions that named tools `bd` does not have.
Nothing else about a ship run changes.

### Fixed

- **`ship` now runs `bd dolt push` after `git push`.** `bd` keeps its database out of git, so issue
  history travels under `refs/dolt/data` and a landed branch left every close on the machine that
  made it. The committed JSONL export is not a substitute: import is upsert-only and cannot
  represent a deletion. A failure there is reported as a warning rather than a stop, since the code
  has already landed and the bead is already closed by that point.
- **Tracker conflicts resolve by re-exporting from the database.** The instruction was to run
  `br sync --merge` as a three-way merge against `.beads/beads.base.jsonl`. Neither the command nor
  that file exists under `bd`, where the database is the source of truth and the JSONL is derived,
  so taking either side and re-running `bd export` is the whole resolution.
- **Worktree handling verifies instead of pinning.** It claimed "every worktree carries its own copy
  of `.beads/beads.db`" and pinned `bd` to the main checkout. `bd` discovers one database per
  repository through the git common directory, so worktrees already share it. The step is now to
  confirm with `bd where` and stop if the answer names a database under the worktree.
- **The close step stages whatever `.beads/` reports dirty**, not `issues.jsonl` alone, since `bd`'s
  auto-staging covers only the path in `export.path`.

Verified against bd 1.2.2.

## [2.9.0] - 2026-08-17

A minor rather than a patch because `quality-gates` gains a gate that sends real network requests.
Nothing about the existing gates changed, so a run over a diff with no HTTP surface reports exactly
what it reported before, one extra SKIP row aside.

### Added

- **`quality-gates` now picks the QA method from the diff instead of only counting tests.** A new
  Step 3 classifies every changed file into a surface and routes each one: `http-api` to a live curl
  probe, `browser-ui` to `/qa`, `mobile-ui` to `/ios-qa`, and `cli`/`library`/`prompt-assets`/`infra`
  to a coverage review alone. A full-stack diff gets several methods at once, and each handoff surface
  takes its own row in the report, because a FAIL and a HANDOFF mean different next moves and one
  status cannot hold both.
- **Gate 8, a live API probe.** It sends actual `curl` requests at the endpoints the diff changed, one
  probe per case rather than per route, and grades status, headers, and body. It answers the question
  a green unit test cannot: whether the endpoint works through the real stack. A worked example in the
  skill shows the shape it catches, a route whose validator test passes while the route itself
  answers 500.
- **`skills/quality-gates/scripts/route_qa.py`**, the router, with `test_route_qa.py`. It exists as a
  script rather than prose because a model told to "detect the shape of what changed" reads six file
  extensions and hands a REST-only diff to a browser tool. Content evidence outranks path evidence, so
  a `.json.jbuilder` view is an API and not a template, and a Next.js `app/api/**/route.ts` is an API
  and not a library. Every content rule is confined to its own language: the router classified
  *itself* as a REST API and a SwiftUI screen before that, because it holds every pattern it searches
  for.
- **`skills/quality-gates/scripts/probe_api.py`**, the prober, with `test_probe_api.py`. Three of its
  rules are in a script because they cannot survive as prose: it probes `http://127.0.0.1:3000` unless
  the caller names another URL and never infers a host from a config file or a URL found in the
  repository, because it sends DELETE; it stops any server it started in a `finally`, so an aborted run
  leaks no listener onto the port the next run probes; and it separates a refused connection from a
  failing endpoint, because BLOCKED and FAIL send the author to different files.

  A supplied host outside `localhost`, `127.0.0.0/8`, and `::1` is used as given, since supplying it is
  the caller saying so, and `--base-url` points one spec somewhere else without editing it. What
  replaces a refusal is that it cannot go unmentioned: the host rides the summary line on stdout,
  marked `(NOT this machine)`, which is the line the skill copies into its report. A spec that starts a
  local server and then probes a remote host draws its own warning, since that combination reads as a
  working gate while the local server answers nothing.

### Changed

- **`quality-gates` no longer mentions an issue tracker.** Its whole input is the diff, and the
  `br close` reference in "When to use" implied otherwise. `/verify-acceptance` remains the skill that
  grades against written criteria.
- **The report and its JSON artifact carry a `routing` block**, so a consumer can tell a PASS that
  probed endpoints from a PASS over a diff whose only surface was handed off.
- **`.githooks/pre-push` runs the two new suites**, which takes it from about 32 seconds to about 46.
  Roughly 11 of those are `test_probe_api.py`, which starts real servers on real sockets; that is the
  only way to prove which host it addresses and that no process leaks.

### Fixed

- **`.githooks/test_prepush.py` derived its check counts from three hardcoded `12`s**, so adding any
  check to `AGENTS.md` broke three unrelated cases. They now read the count from the hook's own list,
  the same drift the hook's own comment warns about.
- **Seven defects in the two new scripts, found by a fresh-eyes pass before either shipped.** Four
  were reproduced by running them; three were found by reading and then reproduced against a copy
  with the one fix reverted. Each has a named case in its suite.
  - **A binary response body crashed the gate.** `subprocess.run(text=True)` decodes strictly, so an
    endpoint answering with a PNG, PDF, or gzip body raised `UnicodeDecodeError` and ended the run in
    a traceback rather than any of the three statuses it can report. An export endpoint is the
    example this skill ships. It now reads bytes and decodes with replacement, as
    `check_hygiene.py` already does.
  - **`api.get('/x')` in a `.tsx` file routed a React change to curl.** That is how an axios or fetch
    wrapper is CALLED from a component, and reading it as a route definition scored the component
    http-api at specificity 3, outranking its own `.tsx` rule. The browser-ui surface vanished and
    the `/qa` handoff with it: the exact misroute the router exists to prevent, pointing the other
    way. `api` is no longer a route receiver and the Express extractor skips JSX entirely.
  - **`diff.mnemonicPrefix` in a caller's git config blanked every `changed` flag.** That key writes
    `+++ w/path` instead of `+++ b/path`, so no path key matched, every endpoint reported
    `changed: false`, the probe spec came out empty, and the gate checked nothing while reading as
    fine. All four prefix keys are now pinned, which is what `check_hygiene.py` already did and what
    this script copied incompletely.
  - **A malformed expectation was skipped rather than refused.** `"header_contains": ["content-type"]`
    was silently ignored, so a probe with one real expectation and one malformed one reported PASS.
    Both `header_contains` and `body_json` now raise.
  - **`0.0.0.0` with a declared server printed a false warning** that the probes would not reach the
    server it starts. The check read the warning list instead of the host, and `0.0.0.0` reaches the
    local server where it works at all.
  - **An HTTP status of `000` was graded as a failing endpoint.** curl writes that when a request went
    out and no HTTP response came back, which is BLOCKED, not FAIL.
  - **`tempfile.mkstemp` leaked its descriptor**, since only the path half of its return value was
    kept.

- **Ten cases the change-coverage gate found untested, all now covered.** Running `/quality-gates`
  against this change failed its own Gate 2: six of the nine endpoint extractors had no case, and
  neither did `insecure_tls`, `--paths-from FILE`, the `unread` warning, or the no-HTTP-status guard.
  The suites go to 39 and 38 cases. Each new case was verified by mutation: the extractor or branch it
  covers was disabled on a copy, and the case was observed to fail. Two notes on how two of them are
  tested, since neither is obvious:
  - **`insecure_tls` asserts on the printed command, not on a TLS handshake.** What can break is the
    flag not being passed, and the printed command is where that is observable through the real entry
    point. Whether curl then accepts a self-signed certificate is curl's behavior, and proving it
    would cost the suite an openssl dependency.
  - **The no-HTTP-status guard stubs `curl` on PATH**, the way `hooks/test-claude-scripts.sh` stubs
    `br` and `gh`. No real server reaches that branch: an empty reply exits 52 and a timeout exits 28,
    both already caught by the returncode branch.

## [2.8.0] - 2026-08-16

A minor rather than a patch because it adds a skill, which is a change to the plugin's shipped
surface. The rest of the release is this repository's own tooling, carried over from what had
accumulated on `main` since the v2.7.3 tag.

### Added

- **`ship` (39 skills now), the last step of the per-bead build loop.** It lands an accepted bead's
  feature branch on `main` locally, with no pull request and no GitHub CI: the repository's own
  check suite, run on the rebased tip, is the entire gate. Invoked as `/tadw:ship [<bead-id>]`, and
  registered nowhere else, so it joins `business-ideas`, `idea-wizard`, and `triage-beads` as an
  accepted `/validate-plugin` orphan.

  It rebases before gating, so the gate grades the tree the squash-merge produces rather than a
  tree that no longer exists. It resolves a `.beads/issues.jsonl` conflict through the host repo's
  tracker merge tool or `br sync --merge`, and **aborts on any other conflict**: resolving a source
  conflict means judging code, and this skill's remit is landing code that was already judged. It
  squash-merges as `<type>: <title> (<bead-id>)`, closes the bead, folds the export into the
  landing commit, pushes without ever forcing, and deletes the branch only after checking that
  `main` holds the branch's version of every file the branch touched.

  Two things are deliberate and worth not undoing. **An undetected gate is a stop, not a skip**
  (`gate-not-detected`); "no check command found" is not evidence that the code is good, and
  `TADW_SHIP_CHECK` is the escape hatch that keeps that honest. And it **never asks a question**,
  because it is built to run inside an orchestrator, where a prompt hangs the loop. Every run ends
  with one machine-readable `SHIP_DONE <hash>` or `SHIP_BLOCKED <reason>` line, with the reason
  drawn from a fixed slug table.

  Two defects came out of running the commands rather than reading them, and both would have fired
  on the first real invocation. `git rev-parse --git-path rebase-merge` prints a path and exits 0
  on a clean repository, so detecting an in-progress rebase by its exit code blocks every run; the
  skill tests for the path instead. And `grep -c` exits 1 when it counts zero, so verifying the
  merged tracker file that way turns the cleanest possible result into a failure, which is the same
  trap `quality-gates` Gate 7 already carries a note about.

  The worst one came from reading. Its `git -C <worktree>` scoping rule covered only the landing
  step, while the push-recovery step also runs `git reset --hard origin/main`. Run from the feature
  branch's own worktree, that resets the feature branch, which at that moment holds the only copy
  of the work that has not landed. The rule now spans both steps and requires confirming the
  checked-out branch before any command that moves a branch pointer.

- **The three hooks in `.claude/scripts/` have a test suite**
  (`hooks/test-claude-scripts.sh`, 60 checks across 21 cases). They commit, push, close beads and
  label them, which makes them the code here most able to do damage unasked, and they had no
  automated coverage at all. Registered in the AGENTS.md command block and in `.githooks/pre-push`.

  Each case builds a throwaway git repository and prepends a directory of stubs to PATH, so the
  shipped scripts run unmodified with no test-only branch in them, and each stub records the argv
  it received. `br` and `gh` are fully faked. **git is real, behind a recording stub** that blocks
  any push to a non-local remote: a stub answering `rev-parse`, `status --porcelain`,
  `merge-base --is-ancestor` and `log` is a git reimplementation, and the cases would then prove
  that reimplementation right rather than the hook, which is the wrong subject when the guards
  most worth testing are exactly the git-dependent ones.

  Every fix from f8259ea has a case, and each was **observed** to fail against a copy of the
  script with that one fix reverted, not assumed to. Eight of eight are pinned that way. The
  mechanism is reusable: `TADW_HOOK_SCRIPTS_DIR` points the suite at a directory of modified
  copies.

  A filter matching no case now exits non-zero. It reported success while asserting nothing, which
  made one fix look pinned by a case that never ran, and that hole was found while checking the
  reverts rather than by reading.

  **Every git command goes through one guarded wrapper that refuses a target outside the sandbox.**
  This is the suite's own scar. `git -C ""` is not an error: it stays in the current directory,
  which is the repository under test. An early version of the repository builder died under
  `set -u` on macOS bash 3.2 and returned an empty path, and the helpers then created four
  branches, committed, and registered two worktrees in this checkout, on a branch nobody asked
  for. Nothing was pushed and it was fully recoverable, but a suite that writes to the repository
  it is testing is the one failure that has to be impossible rather than unlikely. Three checks
  now assert the guard fires, including on this repository's own root.

- **`close_bead_on_pr_merge.sh` now closes a bead after a local `git merge`, not only after
  `gh pr merge`.** A repository can be configured to merge without a PR, and a person can merge
  locally on one that usually does not. Either way the hook never fired, the bead stayed open, and
  someone closed it by hand later without knowing why it had not closed itself.

  The local path asks git what the PR path asks GitHub. `state == MERGED` becomes "is this ref an
  ancestor of HEAD", which covers a merge stopped by conflicts, one refused by `--ff-only`, and a
  ref that never existed. `git merge --abort`, `--quit`, and `--continue` are filtered out first
  and on their own, because each contains the string `git merge` and the first of them means the
  work was thrown away. The ref comes from the command, falling back to the reflog when git chose
  it. The bead id is resolved from the ref name and the commits the merge brought in
  (`HEAD@{1}..`, which is exactly that set), through the same verify-every-candidate,
  refuse-to-guess path the PR sources use.

  **It commits the close and does not push it.** After a PR merge the remote already holds the
  merge, so pushing carries the tracker update alone. After a local merge it would carry the whole
  merged branch, which the author has not pushed and may not be ready to: in a repository that
  deploys on a push to main, a hook that pushes turns "I merged locally" into "I deployed".

### Fixed

- **The same hook could not close anything on br 0.2.15, and reported that only to a stream nobody
  reads.** It ran `br update <id> --status=closed`, and br now refuses terminal-state transitions
  through `update` so its close policy (reason, acceptance criteria, attribution) is enforced. The
  failure arm logs to stderr and exits 0, by design, so the hook looked like it had worked: the
  session continued, and the bead stayed open. Found when a merge in a consuming repository left
  its bead open and the hook was read to find out why.

  It now calls `br close --reason`, keeps the `update` form as a fallback for older br where
  `close` may not exist, and when both fail it prints the command to run by hand.

- **`autocommit_beads_after_br.sh` named no br command in its commit subjects on macOS.** The
  pattern that extracts the invocation embedded a literal newline in a bracket expression through
  `$'\n'`, and BSD grep rejects that outright with "brackets ([ ]) not balanced". The substitution
  therefore produced nothing and every subject fell through to the generic "beads: state update".
  GNU grep accepts the pattern, which is why it survived review. `[:cntrl:]` excludes the newline
  on both. Found by the new suite on its first run, which is the argument for the suite.

## [2.7.3] - 2026-08-15

Everything landed on `main` after the v2.7.2 tag. A patch rather than a minor because nothing
here changes the plugin's shipped surface: no skill, agent, or command was added or renamed, and
the new files are this repository's own tooling.

### Added

- **An eval case can now run against a fixture repository, so a skill's behavior is testable at
  all.** `evals/run.py` hardcoded `cwd=REPO_ROOT` inside `ask()`, and that one line is why no case
  could plant a defect. Two optional `case.json` keys fix it, both absent from the six shipped
  cases: `fixture` names a directory under `evals/fixtures/`, and `single_arm` runs the
  with-plugin arm alone.

  A fixture is two directories, and the split is the design. `base/` is copied in, committed as
  one commit, and pushed to a bare origin beside the checkout; `plant/` is copied over the tree
  afterward and left **uncommitted**. A defect committed into `base/` would sit in the baseline a
  changed-scope run compares against, so the gate under test would correctly report nothing. The
  bare origin exists so `origin/main` resolves: without it `changed_set.py` exits 3 and every gate
  widens to `--all`, so a scoped run could not be tested. A fresh fixture is built **per run**,
  not per case, because `quality-gates` writes its verdict inside the git directory it graded and
  a shared tree would let one run read another's answer. `--keep-fixtures` leaves them on disk.

  `evals/test_run.py` pins all of it with 19 checks and no model call, using a fake `claude` on
  `PATH` that reports its own working directory. That test is the one that matters: with it absent,
  reverting `ask()` to `cwd=str(REPO_ROOT)`, the exact defect this work removes, passed all
  fourteen other checks. Registered in the `AGENTS.md` block and in the pre-push hook.

- **The repository's own checks run before a push, instead of being remembered.** `.githooks/pre-push`
  runs eleven of the commands in the `AGENTS.md` block, about 21 seconds. Every check runs even
  after one fails and all failures report together; a missing tool warns by name and allows, since
  an unpushable clone is worse than an unchecked push; `TADW_PREPUSH=off` is a documented escape.
  A run where every tool was missing used to print "checks passed", which is the one sentence it
  must not print when nothing was verified, and it now reports how little ran. `test_prepush.py`
  pins the behavior against real `git push --dry-run` runs in a throwaway fixture.

- **The hygiene marker count is a tested script.** `skills/quality-gates/scripts/check_hygiene.py`
  counts the `TODO`, `FIXME`, `HACK`, and `XXX` markers a diff adds. The shell recipe it replaces
  carried a load-bearing `|| true`, because `grep -c` exits 1 when it counts zero, so retyping the
  line without it reported a broken toolchain on the cleanest possible result. It also counts
  markers rather than lines, requires a word boundary so `AUTODOC` is not a TODO, and identifies a
  `+++` diff header structurally rather than by prefix.

- **A portable installer for the bead-labeling hook**, under `scripts/`. Run it from any repository
  and it copies the hook to `.claude/scripts/` and wires `PreToolUse`, `UserPromptSubmit`, and
  `Stop` in that repository's `settings.json`, after backing it up. Re-running repairs wiring that
  names an older path rather than duplicating it, a `statusMessage` edited by hand survives, and a
  file that does not parse as JSON is refused rather than patched.

### Changed

- **The quality-gates skill now invokes the three bundled scripts instead of restating them.** The
  v2.7.2 entry below closes with "Not wired in yet", and this is that wiring. Step 2, Gate 6, and
  Gate 7 each carry a `python3 "${CLAUDE_PLUGIN_ROOT}/..."` invocation and an exit-status mapping
  table; the inline key-format regexes, the file-glob list, and the `grep -c` recipe are gone. The
  rationale prose stays, because the script encodes the rules and the prose is what stops a later
  editor from relaxing them: why prefixed formats only, why an untracked `.env` matters, and why
  `git diff "$BASE"...HEAD` is the wrong basis. Gate 6 still prefers a scanner the project already
  configures.

  Two consequences were handled in the same change. A repository with no remote made
  `changed_set.py` exit 3, and Gate 7 would then have run with an empty `--base`, which exits 2,
  which maps to BLOCKED, which fails the whole run; Gate 7 now records SKIP with that reason.
  Hygiene and doc freshness now name re-runnable commands, so the artifact rule that sent them to
  a null `command` applies to change coverage alone.

- **The style core says outright what it used to leave implied.** A class has a single
  responsibility, meaning one reason to change; a function's name says which one thing it does,
  and "you cannot name it without and" now carries "split it"; a class takes its collaborators
  through its initializer and a function takes them as parameters; names make code
  self-documenting. The core is payload 0 of three `SessionStart` entries and is never split, so
  it grew from 4,499 to 4,780 characters against a 10,000-character cap. The combined payload is
  20,275 characters, corrected in the three places that documented it.

## [2.7.2] - 2026-08-13

### Added

- **The changed-set resolution is a tested script instead of a recipe the model retypes.**
  `skills/quality-gates/scripts/changed_set.py` resolves the base and prints the changed paths, one
  per line. Step 2 of the quality-gates skill was two git commands plus a base-resolution fallback,
  reassembled on every run, and getting it wrong narrows every gate while the report still reads as
  a scoped pass.

  Three decisions are load-bearing. The diff is `git diff "$BASE"` with no `...HEAD`, because the
  three-dot form stops at the last commit and this skill runs before a commit more often than after
  one, so the very work being checked would drop out of scope. **An unresolvable base exits 3**,
  distinct from exit 0 with no output and from exit 2 for operator error: the prose conflated the
  first two, and treating a missing base as an empty diff covers nothing while reporting
  confidently. The base SHA, the ref it came from, and the count go to stderr, so stdout stays a
  path list a caller can pipe without filtering.

  The base ref is resolved rather than assumed. `origin/HEAD` first, then `origin/main`, first merge
  base wins, so a repository whose default branch is `trunk` or `master` still resolves. A path
  whose name contains a newline is named on stderr and left out of stdout, because printing it would
  hand every downstream reader two paths that do not exist.

  `test_changed_set.py` pins it with 21 checks over throwaway origin-plus-clone fixtures, and is
  registered in the `AGENTS.md` command block. Each of the five behaviors above was mutation-checked:
  breaking it fails the case that owns it.

  **Not wired in yet.** `SKILL.md` Step 2 still carries the prose recipe. Pointing the skill at this
  script is a separate bead, so this release ships the script and its suite alone.

### Fixed

- **Three bead hooks under `.claude/scripts/` and the secrets gate, from a fresh-eyes pass over the
  six files added in v2.7.1.** Eight findings, seven fixed. These landed in `main` after the v2.7.1
  tag, so they ship here.

  `close_bead_on_pr_merge.sh` could never close a bead in this repository: the id regex stopped after
  one hyphen group, so `tadw-qg-script-secrets-gate-jbg` extracted as `tadw-qg` and resolved to
  nothing. Resolution now verifies every candidate against the tracker, honors an explicit
  `Bead: <id>` trailer, and fails closed when one source names two different real beads. A dead
  `status == "unknown"` guard let a transient read failure fall through to a close, `br` ran unpinned
  so a close from a worktree landed in that worktree's database copy, and an unanchored `failed`
  match skipped the close whenever a check summary mentioned one failed check.

  `autocommit_beads_after_br.sh` read `br update x --claim && br show x` as read-only, because it
  substring-matched a read-only subcommand anywhere in the line, so the mutation went uncommitted.
  `label_bead_on_skill_invocation.sh` hardcoded one label while the marker filename already encoded
  it, which would mislabel a second gate-mode entry.

  `check_secrets.py` skipped files over 2 MiB and undecodable files in silence, then printed OK.
  Skipping is now configurable through `--max-scan-bytes`, never silent, and the clean verdict
  narrows to "in what was scanned". A skip is not a finding and does not change the exit status, or
  one undecodable file would fail this gate forever.

  Still uncovered: the three shell hooks have no automated tests, so those six fixes rest on manual
  verification. Tracked as `tadw-hooks-test-harness-12b`.

## [2.7.1] - 2026-08-12

### Added

- **`/quality-gates` writes its verdict as JSON, so a tool can read the conclusion.** The report
  was markdown only, which meant no downstream check could act on it, and the pre-push hook planned
  for the next release cannot gate on a verdict it cannot parse. Step 5 now writes
  `quality-gates-report.json` carrying `version`, `head`, `dirty`, `timestamp`, `scope`,
  `gate_source`, `verdict`, and a per-gate array of name, status, command, and detail. `verdict` is
  one of `PASS`, `FAIL`, `INCOMPLETE`, or `NO GATES RAN` verbatim, and the `gates` array carries one
  entry per row of the markdown table, including SKIP, BLOCKED, and HANDOFF rows.

  Three details are load-bearing rather than incidental. The path resolves through
  `git rev-parse --git-dir` and never a hardcoded `.git/`, because `.git` is a file rather than a
  directory inside a linked worktree, and because `--git-dir` returns a distinct path per worktree
  so two worktrees on two branches keep two verdicts instead of overwriting one. `--git-common-dir`
  is forbidden by name: it looks like the more careful choice and is the one that collides. The
  object is built with `json.dump` rather than assembled as text, because the pre-push consumer
  cannot tell a corrupt report from a missing one, and it reports the missing case, so a botched
  write sends the author to fix the wrong thing. The write happens before the report is emitted,
  since the report's new **Artifact** line states what the write did.

  `dirty` is recorded for a human reader and has no automated consumer. The skill runs before the
  commit nearly every time, so nearly every honest report is dirty, and a gate blocking on it would
  block constantly.

### Changed

- **The report-only rules now say "nothing in the working tree" instead of "nothing".** Writing an
  artifact made three separate absolute claims false, and a skill that violates its own Critical
  Rules on every run is worse than no artifact. All three move together, because the next reader
  trusts whichever copy is weaker: the `quality-gates` skill's "Never" entry and checklist item,
  and the report-only line in `commands/quality-gates.md`.

- **`verify-acceptance` is told explicitly not to write the artifact.** It runs four gates of
  seven, so an artifact from that run would record a partial verdict, and the pre-push hook would
  then decide a push on a conclusion nobody drew. Its own claims therefore stay absolute and get
  stronger rather than weaker: it writes no file at all.

## [2.7.0] - 2026-08-10

### Changed

- **BREAKING: `/python-feature-dev` is now `/build`.** The old name was wrong, and its own last
  line admitted it: the workflow dispatches to Ruby, Swift, and TypeScript as readily as to
  Python. Anything invoking `tadw:python-feature-dev` must switch to `tadw:build`. Renamed with
  `git mv`, so history follows the file.

- **`feature-development` takes a bead id and reads the spec instead of interviewing you.** Its
  Discovery phase asked 3 to 7 questions that a bead which passed `/bead-audit` already answers in
  its `design` and `acceptance_criteria` fields, so driving it from a tracked issue meant retyping
  the tracker. Phase 1 now reads `br show <id> --json` and refuses two cases outright: criteria too
  vague to build against (it loads `bead-audit` and stops), and a bead whose own notes say to split
  it first. The interview survives for the no-bead case, so `software-engineer` routing for
  "implement X" still works.

- **A new Orient phase, because detecting a file extension is not understanding a repository.** The
  skill matched `.py` and called that language detection, which would load `style-python` for
  `atlas` without noticing it is FastAPI on SQLAlchemy, or that its `AGENTS.md` forbids external
  calls. Phase 2 reads `AGENTS.md`/`CLAUDE.md`, then the dependency manifest for the framework and
  test runner, then the two or three existing files nearest the change. It also loads a
  project-local style skill when one covers the surface, and says the local skill wins over the
  general language skill on conflict. That is the mechanism that reaches `jbuilder-style` and
  `style-fizzy`; extension matching never could.

- **The skill leaves tracker state alone and does not grade itself.** No claim, no status change,
  no close. It stops at implemented and hands off to `/quality-gates` then `/verify-acceptance`,
  because a step that both writes code and rules on whether the code met its criteria is the
  self-grading `verify-acceptance` exists to prevent.

- **Pipeline B reverses its last two steps: `/fresh-eyes-cr` → `/quality-gates` →
  `/verify-acceptance`.** `verify-acceptance` already reads the `quality-gates` skill and runs four
  of its gates, so running the gates first means the grader cites results that exist rather than
  re-deriving a subset. Updated in `README.md` and `AGENTS.md`.

- **`AGENTS.md` "Landing the Plane" gains `/verify-acceptance` as step 3**, after the gates, so the
  session-completion checklist and Pipeline B stop describing different workflows. Qualified with
  "if it has one", since not every session works against a bead.

### Added

- **`style-go`**, the Go style skill. `feature-development` already read `go.mod` when detecting a
  stack but had no Go skill to load, so Go fell to the degraded path. Written against the
  conventions already in a real Go repository rather than invented: `fmt.Errorf("read %s: %w", ...)`
  wrapping, doc comments that open with the identifier, `defer` beside the open, table-driven tests
  with named cases, and a `gofmt` → `go vet` → `staticcheck` → `go test -race` order.

  Eleven deltas on the injected core, each with a BAD → why → GOOD example: accept interfaces and
  return structs with the interface declared at the consumer; wrap errors and add a sentinel only
  where a caller branches; make the zero value useful; `context.Context` first and never stored in a
  struct; every goroutine has a defined exit; pass arguments until four; name for the call site;
  doc comments start with the identifier; `defer` beside acquisition; happy path leftmost; standard
  library before a dependency.

  Two universal rules are deliberately overridden, and the skill says so rather than leaving a
  reader to notice the contradiction. "Compose over inherit" is not a choice in Go, so the delta
  becomes when an interface earns its place at all. And the core says comment only the why, but
  exported doc comments **are** the API documentation `go doc` renders, so that exception is scoped
  to exported identifiers while the core still governs comments inside function bodies.

  Wired into every component that dispatches by language, so it is not an orphan:
  `feature-development`'s extension and linter tables, `code-simplify`'s extension table and
  frontmatter, and the `software-engineer` agent's style list. Registered in `AGENTS.md` (38 skills),
  the `README.md` skills table, and a new Go section in `docs/ROUTING.md`.

  Not verified: nothing compiles the 11 Go examples. `gofmt -e` parses 2 as whole files and 9 as
  deliberate fragments, which matches `style-python`'s 4.

### Fixed

- **`plan-review`'s skill description omitted the acceptance-criteria gate and the verdict**, both
  of which `commands/plan-review.md` and the `README.md` row already described. Frontmatter is
  invocation-trigger text, so the runtime deciding whether to load the skill could not see two of
  the things it does.

- **Two defects in the rewritten `feature-development`, found by a fresh-eyes pass over it.** The
  in-progress row told the reader to detect that "someone else claimed it" without saying how; it
  now names `status` and `assignee` and states that `assignee` is absent from the JSON when nobody
  holds the bead, verified by setting and clearing it. And an untested criterion was called "a
  failing grade", where `verify-acceptance` defines UNVERIFIABLE as yielding INCONCLUSIVE and says
  outright it is not a soft FAIL.

## [2.6.0] - 2026-08-10

### Added

- **`triage-beads`, a skill that turns the open `br` backlog into a one-screen "what next"
  readout.** One Start-here pick with its claim command, then Quick wins / User impact / Keep
  momentum buckets, a blocked list naming the blocker that holds each one, and a priority tail
  capped at ten. It is a conversion of a Linear triage command, and the conversion is the point:
  readiness comes from `br ready` and `br blocked`, and PageRank, betweenness, and unblock counts
  come from one `bv --robot-triage` call, so the numbers are measured instead of inferred. The three
  axes `bv` does not score (effort, user impact, momentum) stay a read of each bead body, and the
  skill reports them separately rather than averaging them into one score that hides the choice
  being made. Registered in `AGENTS.md`, the `README.md` skills table, and `docs/ROUTING.md`, and
  accepted as an orphan because it is invoked directly as `/triage-beads`.

  Every command and field claim in it was exercised against `br` 0.2.15 and `bv` v0.18 rather than
  read out of help text, which is where the traps it documents came from. `dependency_count` sums
  `blocks`, `parent-child`, and `related` edges alike, so a child of an open epic carries a
  dependency and is ready at the same time, and only a `blocks` edge releases work when it closes.
  `bv`'s `quick_ref.blocked_count` reads 0 on a backlog with six dependency-blocked beads. A
  `br ready` row carries neither `due_at`, `defer_until`, nor `dependent_count`. `br list`,
  `br blocked`, and `br ready` truncate at 50, 50, and 20 without saying so. `br show` returns a
  one-element array. `br epic status` reports child counts and no member ids. `--format toon` emits
  ordinary JSON with a stderr-only warning when the `tru` helper is absent. And `br update --claim`
  exits 4 on a bead that is blocked or already claimed, which is why blocked beads stay out of the
  actionable buckets: the command the readout prints would not work on them.

### Fixed

- **`docs/beads-workflow.md` placed the `bv --robot-triage` fields at the root of the output.**
  `quick_ref`, `recommendations`, `quick_wins`, `blockers_to_clear`, `project_health`, and
  `commands` sit one level down in `bv` v0.18, under a `triage` key. Reading the documented path
  yields null for all six. The correction is a hand-maintained note below the generated block, so a
  `bv` re-injection into `AGENTS.md` cannot overwrite it, and the skill reads through
  `(.triage // .)` so both shapes work.

## [2.5.2] - 2026-08-10

### Removed

- **The acceptance gate, the `PostToolUse` + `Stop` hook pair that chained `verify-acceptance`
  onto the end of a fresh-eyes review.** Deleted `hooks/acceptance-gate.js`, its manifest
  entries, and `hooks/manual-gate-test.sh`, along with the four checks in `hooks/test-hooks.js`
  that covered it (18 remain). The `verify-acceptance` skill and `/verify-acceptance` command
  stay; the check is now invoked by hand. `TADW_ACCEPTANCE_GATE` and the
  `.tadw-acceptance-gate-off` flag file no longer do anything, and a leftover flag file is
  inert rather than harmful. `hooks/style-core-hooks.json` declares `SessionStart` and
  `SubagentStart` only, so `isFeatureDisabled()` in `runtime.js` collapsed back into
  `isDisabled()`, its single caller.

## [2.5.1] - 2026-08-09

### Fixed

- **`/quality-gates` guessed the gate list from file extensions, so it found nothing here and
  called that a pass.** Run against this repository it saw no `package.json` and no
  `pyproject.toml`, reported every gate SKIP, and concluded overall PASS while missing all six
  checks `AGENTS.md` declares. Gate discovery now reads `AGENTS.md`, then CI config, then a task
  runner, and only guesses when none of those names a check. The report says which source it used.

- **A configured gate that could not run degraded to SKIP, and SKIP did not affect the result.**
  "No linter is configured" and "the linter is configured but not installed" collapsed to the same
  status, so a broken toolchain reported a clean bill of health. The second is now BLOCKED, which
  fails the run. A run where every gate skipped reports NO GATES RAN rather than PASS, the same
  vacuous-satisfaction reading `verify-acceptance` already refuses for criteria.

- **The doc-freshness gate was three prose steps that did not survive first contact.** Told to
  extract "tokens that look like a path", it reported **194 missing paths on a repository with no
  broken links**: slash commands, `<name>` placeholders, and a worked example in its own text. A
  gate that cries wolf gets ignored, and the real miss gets ignored with it. It is now
  `skills/quality-gates/scripts/check_doc_paths.py`, with `test_check_doc_paths.py` pinning 18
  cases, six of them one per false positive from that run.

- **A Terraform `resource` block was fenced as `bash`** in `terraform-iac-expert`, found by the
  new fence check. Split into a `bash` fence and an `hcl` fence.

### Added

- **`quality-gates` is now a skill**, at `skills/quality-gates/SKILL.md`. It was 95 lines of
  technique living in `commands/`, where no agent or skill could reach it, so `verify-acceptance`
  carried its own copy of a four-gate subset that could drift. The command is a Read wrapper, and
  `verify-acceptance` reads the same file.

- **A change-coverage gate**, which is the reason to run the skill rather than the test command by
  hand. A green suite says the old code still works; this asks whether the new code is exercised.
  It enumerates the cases the diff introduces, requires a unit test for each and an end-to-end test
  through the real entry point for every CLI command or HTTP route touched, then grades the
  **span**: the classes of input, boundary, state, and outcome each case can take. One passing test
  covers one point of a span, and no coverage percentage will tell you that. It stays proportionate
  by rule: one test per class, never the cross-product, never a test for an unreachable branch, and
  never defensive code around a failure that cannot happen. A browser or mobile UI change is
  HANDOFF to `/qa`, which makes the verdict INCOMPLETE rather than PASS.

- **The default scope is the change, not the repository.** `--changed` runs the tests covering the
  changed code and narrows lint, doc freshness, and hygiene to changed files, and the report states
  that the full suite did not run. Two gates stay wide on purpose: type checking analyzes the whole
  project and reports only changed files, because a type error surfaces in the consumer, and the
  secret scan always covers the whole tree.

- **Three checks in the hook suite, which grows from 19 to 22**, each covering a case the first
  real `/quality-gates` run found nothing enforcing: `AGENTS.md` registers every skill, agent, and
  command on disk with a matching count; `README.md` mentions every skill and agent; and every
  runnable `bash` block in a skill or command parses under `bash -n`. Blocks carrying a
  `<placeholder>` are templates and are skipped. That last check would **not** have caught the three
  snippet bugs that prompted it, all of which were syntactically valid. Only executing a snippet
  finds those.

- **`.docpaths-ignore`**, for paths a documented tool creates at runtime. `docs/roadmap.html` does
  not exist until someone runs the dashboard. A `doc:` prefix skips a whole document, which is what
  plans need: a plan names the tree it intends to create, so every path in it is a miss until the
  work lands.

### Known gaps

- `docs/ROUTING.md` omits 15 commands. Asserting that invariant means writing 15 entries first, so
  it is left for a separate pass and nothing enforces it today.

## [2.5.0] - 2026-08-09

### Fixed

- **Eighteen commands shadowed the skill they told you to load.** `commands/<name>.md` and
  `skills/<name>/SKILL.md` are addressed as the same `tadw:<name>`, and the command wins. Every
  one of the eighteen opened with "Use the `<name>` skill", which resolved back to itself, so
  **271,067 bytes of skill content was unreachable by name**. `/bead-audit` alone put a
  250-byte summary in front of a 51,113-byte rubric, and every audit it ran scored from the
  summary. A wrong number produced that way is indistinguishable downstream from a right one.

  Seven commands were **deleted**: `/ab-test-design`, `/business-ideas`,
  `/competitive-analysis`, `/idea-wizard`, `/product-brief`, `/product-research`,
  `/product-roadmap`, plus `/bead-audit` in 2.4.2. Each was a one-line delegation whose content
  the skill already carried; `/business-ideas` and `/idea-wizard` duplicated a step already at
  line 12 of their own `SKILL.md`. **Typing `/<name>` still works**: the skill takes the slash
  name once the shadow is gone, verified by deleting one, restarting, and reading the menu.

  Ten commands were **converted to read the skill from disk** rather than name it:
  `/agentic-clean-code`, `/aso-audit`, `/plan-review`, `/plan-to-beads`,
  `/product-surface-docs`, `/research-ingest`, `/roadmap-dashboard`, `/ux-audit`,
  `/ux-audit-ios`, `/verify-acceptance`. These carry real per-invocation content (role framing,
  argument resolution, output paths, prerequisites) that would be lost by deletion.

  Five **agents** were routing by name to skills the surviving commands still shadow, which the
  original report missed entirely: `product-cartographer`, `project-manager`,
  `research-librarian`, `ux-product-designer`, `ux-product-designer-ios`. Each now reads its
  skill from disk. `product-manager` needed no change: deleting its five commands repaired it.

- **`house-response-style` contradicted itself on sentence length.** Its frontmatter said "a
  hard twenty-five-word sentence limit" while its body said twenty-five words for an
  explanation and twenty for an instruction. The frontmatter dropped the instruction case, and
  the frontmatter is what the runtime reads. `README.md` said only "capped sentence length".
  All three now state both numbers. The rule itself is unchanged.

### Added

- **Check 18, pinning the namespace rule.** A command sharing a skill directory's name may not
  tell the model to load that skill by name. It also requires a `Glob` fallback wherever a
  command reads a `SKILL.md`, because a Read with no fallback fails silently when
  `${CLAUDE_PLUGIN_ROOT}` does not resolve, which is the same class of silent failure as the
  shadow it replaced. Check 6 already pinned this for `/response-style` alone, and kept passing
  while the defect appeared seventeen more times, so the check is now general.

  Proven to discriminate, not merely to pass: injecting a delegate-by-name regression into
  `/ux-audit` exits 1 naming that command, removing only its `Glob` fallback exits 1 naming
  that, and restoring leaves the file byte-identical with the suite green. The suite is now 19
  checks.

- **A "When to use" column on the README skills table**, all 35 rows. Each cell is condensed
  from that skill's own `## When to Use` section. Four skills have no such section
  (`agentic-clean-code`, `house-response-style`, `ux-audit`, `ux-audit-ios`); those cells were
  written from the skill's frontmatter and body instead.

- **The namespace rule, written down** in `AGENTS.md` and `README.md`: a command may share a
  skill's name, or delegate to that skill by name, but never both. Three ways to satisfy it:
  rename the command, delete it, or read the `SKILL.md` from disk.

### Changed

- **The registered command count is 36 to 29.** No slash name stopped working; seven of them
  now resolve to their skill rather than to a stub. `argument-hint` is lost on those seven,
  which affects the menu hint only, not argument passing.
- `business-ideas` and `idea-wizard` are now referenced by no agent and no command, so
  `/validate-plugin` reports them as orphans. Accepted and recorded in `AGENTS.md`: both are
  invoked directly as `/<name>`, and a referrer would add nothing.

## [2.4.2] - 2026-08-08

### Fixed

- **The `SessionStart` hook was delivering about a tenth of what it injected.** Claude Code
  caps every hook output string at 10,000 characters, covering plain stdout and
  `hookSpecificOutput.additionalContext` alike, and replaces anything longer with a short
  preview plus a file path. The payload is 19,996 characters: the coding core at 4,499 and the
  response style at 15,495. Sessions received the first ~2,000 characters. The coding core
  arrived cut off after principle 4 of 10, and **the response style never arrived at all**.

  The failure was invisible from inside a session, which is the part worth remembering. The
  coding core's marker sits at byte 5, inside the surviving preview, so a session read as
  correctly loaded. The response style's marker sits at byte 4,507, inside the discarded
  remainder. The one signal designed to prove the injection worked was the one signal the
  truncation could not reach, and it had been reporting success since the hook shipped.

  The fix is to split, not to shrink. The cap is per output, and Claude receives the
  `additionalContext` of every hook that matched the event, so `SessionStart` now ships from
  three manifest entries differing only in a payload index (core 4,499; response style parts
  of 9,854 and 5,777). `getSessionStartPayloads()` computes the split at run time on line
  boundaries, so editing either document re-splits it and nothing is hand-maintained.
  Continuation parts name the section they resume, which buys back the context a mid-section
  cut loses for one line instead of one manifest entry.

  Two checks hold the seam shut, bringing the suite to 18: every payload must fit the cap,
  asserted against real stdout rather than the computed string, and the manifest must wire
  exactly one entry per payload with its own index. The splitter decides how many parts exist
  while the manifest decides how many are asked for, and a mismatch drops the tail in silence.

  `run-hook.sh` now forwards its remaining arguments to the script, which is how the index
  reaches `session-start.js`. An index past the end emits nothing, so a stale manifest entry
  cannot duplicate a part if the documents shrink.

- **`bead-audit` was loading with no metadata at all.** Its `description` was an unquoted YAML
  scalar containing `verdicts: content`, and the colon-space ended the scalar early, so the
  whole frontmatter block failed to parse. Both `name` and `description` were silently dropped
  at load time, which is what the runtime reads to decide whether to invoke a skill. Quoting
  the description fixes it, and `claude plugin validate .` passes again. This shipped in 2.4.1.

### Changed

- **`AGENTS.md` cut from 767 lines to 231, about 12,060 tokens to 2,850.** The file loads in
  full on every session in this repo, and roughly 91% of it restated content that already
  lived elsewhere. The worst case was `house-response-style`, whose rules were in context three
  times at once: injected by the hook, and restated at two separate places in `AGENTS.md`. That
  copy had drifted, dropping the two rules the skill declares as outranking everything else and
  adding two ASD-STE100 rules the skill deliberately refuses. Sessions were following the
  drifted summary, because the hook's copy was being truncated away.

  The registry lists became name indexes; descriptions live in the `README.md` tables and in
  each component's frontmatter, which is what the runtime actually reads. Hook design notes
  moved to `docs/HOOKS.md`, the language catalog to a 28-row routing table with the long form
  in `docs/ROUTING.md`, and component anatomy to `docs/AUTHORING.md`. The inline `br` and `bv`
  blocks gave way to `docs/beads-workflow.md`, with six commands that existed only in
  `AGENTS.md` added there first.

  "Landing the Plane" and the manifest namespace rule stay verbatim. Neither exists anywhere
  else in the repo, and the first has to be in context at the end of a session, where a pointer
  would not be followed.

### Added

- **A "Commands for This Repo" block in `AGENTS.md`.** `rumdl`, the two test suites, and
  `evals/run.py` were documented nowhere in a 767-line file, yet CI fails on
  `rumdl fmt --check .`.

## [2.4.1] - 2026-08-06

### Added

- **A grounding audit in `bead-audit`, checking each bead against the code on `main`.** The
  audit could previously certify a bead as Excellent while every file it named had been
  renamed. Grounding is a third verdict on its own axis (`grounded` / `drifted` / `satisfied` /
  `ungroundable`), never folded into the content verdict, because a bead whose target code
  moved is *stale*, not under-specified, and the fix is to re-ground it rather than to write
  missing content.

  Only **current-state** claims are checkable. A bead's Why, How, and Steps to Reproduce
  describe the world as it is; its Done when and Acceptance Criteria describe the world after
  the work, and are supposed to be false while the bead is open. Checking those for drift would
  fail every open bead, so they run the other way: an end state that **already holds** makes the
  bead `satisfied`, and the proposal is to close it, not to fix it.

  Claims are checked against `origin/main` with `git show` and `git grep`, never the working
  tree, which on a feature branch already contains the change the bead asks for and would
  report unmerged work as `satisfied`. `ungroundable` (no repository, a different repository,
  no repository of record, nothing checkable) is reported explicitly, so an unchecked backlog
  is never mistaken for a verified one. Grounding contributes no points; it applies a band
  ceiling (`drifted` caps at Adequate, `satisfied` at Weak) and forces `applyable: false`,
  because a false premise has two opposite resolutions ("the bead is stale" and "the code
  regressed") that the audit cannot tell apart. The four checks (existence, pattern, stack,
  behavior) are deliberately the same ones `plan-review` uses.
- **A `Grounding` column and a `satisfied` callout in the `/bead-audit-all` report**, plus a
  step that resolves the baseline sha once for the whole sweep instead of per bead. `satisfied`
  beads are listed **above** the table: they appear done on `main` and can be closed
  immediately, so burying them in a quality ranking sends someone to re-specify finished work.

### Fixed

- **`/bead-audit-all` now reads `skills/bead-audit/SKILL.md` from disk instead of invoking it
  through the Skill tool, which never reached the rubric.** `commands/<name>.md` and
  `skills/<name>/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
  `Skill(bead-audit)` returned the twenty-line command body whose first line is "Use the
  `bead-audit` skill", redirecting to itself. Every sweep therefore scored from a summary
  rather than from the weights, the caps, and the renormalization rules, and reported confident
  numbers computed from nothing. Step 4 now also asserts that three headings are present in the
  file it read, because a wrong number here is indistinguishable from a right one downstream.
  Same fix, and same reason, as `/response-style`.

### Known issues

- **`/bead-audit` still has the collision described above and does not load the rubric.** Until
  it is fixed, audit a single bead through `/bead-audit-all` and ignore the other rows.
  Eighteen commands collide with a same-named skill; the collision is only a live bug where the
  command's body delegates with "load the skill" instead of carrying its own instructions, and
  only `/bead-audit-all` has been fixed so far.
- **The two grounding band ceilings are unpinned by any fixture.** Exercising `drifted` and
  `satisfied` needs a real repository at a known sha, which a pasted-body suite cannot provide.
  All eight fixtures name no repository of record and are therefore `ungroundable`, which
  proves the ceilings do not fire when they should not, and proves nothing about whether they
  fire when they should.

## [2.4.0] - 2026-08-06

### Added

- **An acceptance gate that chains `verify-acceptance` onto the end of a fresh-eyes review.**
  Claude Code has no "slash command finished" event, so `hooks/acceptance-gate.js` uses two:
  `PostToolUse` on the `Skill` tool arms a per-session flag when `review-fresh-eyes` or
  `fresh-eyes-cr` loads, and `Stop` consumes that flag and blocks once. `PostToolUse` alone
  fires when a skill is *loaded*, not when its work is done, so a check wired there would grade
  the branch before a single file had been reviewed. Loop safety is the whole risk: a `Stop`
  hook that blocks and never disarms traps the session, and the user cannot escape it from
  inside. The flag is therefore deleted **before** the block is emitted, `stop_hook_active` is
  honored, any error falls through to a silent exit, and a flag older than 24 hours is
  discarded rather than spent on an unrelated turn. Off-switch: `TADW_ACCEPTANCE_GATE=off`, or
  a flag file at `${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-acceptance-gate-off`.
- **The `verify-acceptance` skill and the `/verify-acceptance` command.** Grades a finished
  unit of work against its bead's `acceptance_criteria` and the QA gates, one criterion at a
  time. Its one load-bearing rule: grade against an artifact, never against the diff. Reading a
  diff and concluding it should satisfy a criterion is a prediction, not a check, so a
  criterion with no named test, no command output, and no `file:line` is UNVERIFIABLE rather
  than PASS. Report-only: it never edits code, never closes a bead, and never invents criteria
  when the bead records none, since a made-up criterion always passes.
- **`hooks/manual-gate-test.sh`**, which drives the gate by hand with the real hook payloads:
  arming is silent, the flag appears, `Stop` emits `decision=block` naming the skill, the
  second `Stop` is silent, and a 25-hour-old flag is discarded. It points `TMPDIR` at a scratch
  directory removed on exit, so it cannot touch a live session's flag. Use it when the gate
  misbehaves in a session and you need to see which step diverges. Verified to discriminate: it
  exits non-zero against three separately injected regressions (disarm removed, trigger list
  narrowed, block reason no longer naming the skill).
- **Checks 12-15 in `hooks/test-hooks.js`**, covering the gate: it arms only on the fresh-eyes
  review skills and refuses a session id that could escape the temp directory, its `Stop` half
  blocks exactly once and disarms first, its off-switch is independent of the style core's in
  both directions, and its manifest commands execute rather than merely parsing.

### Fixed

- **No hook script calls `process.exit(0)` after writing to stdout.** Node's stdout writes are
  synchronous on POSIX pipes but **asynchronous on Windows pipes**, so an explicit exit can
  discard whatever has not flushed. The truncation would be silent and platform-specific: valid
  output everywhere it was tested, a half-written object in production on Windows. Removing the
  call is the entire fix, because every branch already sits inside a `try`/`catch`, so falling
  off the end exits 0 anyway and flushes first. It could never have helped the one path that
  does exit non-zero either, since a failed `require` throws before the line is reached.
  Affects `session-start.js`, `subagent-start.js`, and `acceptance-gate.js`.
- **`verify-acceptance` could return ACCEPTED having graded nothing.** The rule read "every
  criterion PASS", which zero criteria satisfy vacuously, so the UNRESOLVED path the skill
  itself routes to (no bead found, acceptance table skipped) rendered ACCEPTED. That is the
  exact outcome the skill exists to refuse. ACCEPTED now requires at least one criterion
  graded, and the unresolved case is named alongside the empty-criteria case.
- **`/verify-acceptance` ignored the bead id it documented.** The command offered a bead id
  argument, but the skill's Step 1 had no branch for one and always auto-resolved. Step 1 now
  takes a supplied id first, confirms it exists, and stops rather than falling back when it
  does not. The command also declares the `argument-hint` every other argument-taking command
  in `commands/` declares.
- **`README.md` described a missing `node` as a silent no-op.** It has not been silent since
  `run-hook.sh` was introduced: the wrapper emits a `FAILED to load` marker in place of the
  core. The README now states the real behavior and distinguishes "marker present, `node`
  broken" from "no marker, the hook never ran".
- **The `[Unreleased]` compare link pointed at `v1.14.0`.** It now points at `v2.3.1`, the
  latest tag. Only `v1.13.0`, `v1.14.0`, `v1.15.0`, `v1.15.1`, and `v2.3.1` were ever tagged, so
  the releases from 1.16.0 to 2.3.0 still have no compare link; adding one would produce a dead
  link rather than a useful one.

### Changed

- **`runtime.js` off-switch is parameterized.** `isFeatureDisabled(envVar, flagFile)` now
  carries the shape, and `isDisabled()` is its style-core specialization. The plugin ships two
  independent hook features, and one shared switch would mean silencing the per-turn gate also
  silenced the once-per-session style core.
- **`plugin.json` still points at a single hooks manifest**, so `style-core-hooks.json` now
  declares all four events. The file name is narrower than its contents; the alternative was a
  second manifest the `hooks` field cannot reference.
- Documentation: `AGENTS.md` and `README.md` cover the gate, the new skill and command, and
  the three separate things "does the gate work" can mean, each needing a different test.

## [2.3.1] - 2026-08-05

### Added

- **`Report your own work plainly` is now a top-level section**, stated as a six-part output
  contract rather than a word ban: give the number, name what failed, say what you did about
  it, give the evidence instead of the verdict, say what you did not run, and say where you
  stopped. It was a table nested under sub-point 2 of ten numbered STE rules, which is the
  least prominent place in the document for the rule that governs the claim you make most
  often. `preamble.js`'s fallback carries the contract too.
- **The label rule is now conditional: never let a label stand alone.** "Green" and "a flake"
  are legitimate beside the facts they stand for, and forbidden without them. The flat ban
  that preceded it was measured against three versions of this document and failed all
  fourteen runs, while those same runs gave the count, the re-run, and the reason every time.
  The harm the ban was written to prevent, a label swallowing the argument, did not occur
  once. Shorthand that carries no facts of its own ("smoke test", "round-trip", "surfaced",
  "lands", "wire up") stays forbidden outright, since it has nothing to stand beside.
- **`forbid_label_alone`, a conditional grader in `evals/run.py`.** It takes a `pattern` and
  an `unless_all` list, and fails only when the label appears and a supporting fact is
  missing. `evals/cases/self-report-plainly` now uses it, and its substance checks keep their
  current strictness. Its count and re-run patterns also accept `3,499` and "retry", which
  the old patterns failed on answers that were otherwise complete.
- **A rule for work you could not finish.** The document treated reporting success as its
  highest-drift case and said nothing about reporting failure, which is its twin.

### Fixed

- **The document violated four of its own rules.** It used an em-dash, which the global house
  rule bans everywhere. It banned "lands" as borrowed metaphor and then used "land" in that
  same sense twice. Four of its sentences ran past its own twenty-five-word limit, one of
  them inside the rule that sets the limit.
- **"Lead with the answer" and "never state the recommendation twice" could not both hold**
  when the answer was a choice. The matrix section now states one legal order for each case:
  the lead sentence is the recommendation when the choice is the whole answer, and a separate
  line carries it when the choice sits inside a longer answer.
- **ASD-STE100's scope is now stated.** The rules were written unconditionally while "Tone
  follows the task" exempted creative and personal work without saying what it exempted. The
  scope note keeps accuracy, answer-first, and literal language for that work, and drops the
  sentence caps. The spec is named at every point the rules are invoked, so "STE" never
  appears without "ASD-STE100" nearby.
- **Cross-references name their target instead of numbering it.** Four sections each number
  from 1, so "Rule 1 above outranks all of them" could have meant accuracy or lead-with-the-
  answer.
- **The pre-send check no longer prints `3499`**, the exact test count used by
  `evals/cases/self-report-plainly`. The document was priming the number its own eval requires
  back, so that check partly measured recall of the document.

### Changed

- **`house-response-style` is now derived from ASD-STE100 alone.** Three sections still
  tracked the `i-have-adhd` skill this style grew out of, closely enough to read as its copy:
  the pre-send check (same delete list, same order, same "reads only the first line and the
  last line" test), the escape hatches (four of its six items, two near-verbatim), and the
  reader-facts list under "Why this shape". All three are rewritten from the standard's own
  premise, that the reader must act on the document, often quickly and often in a second
  language. Four smaller echoes went with them: the "Great question" opener, "anything else?"
  as the named closing ritual, "2 to 4 ranked options", and the persistence sentence. The
  rules themselves are unchanged; only the wording and the derivation are new.
- **"When to break these rules" is now "Where these rules yield"**, and states what it yields
  to: accuracy, which is rule 1. The old heading described the reader's action; the new one
  describes the rule's behavior, and each item now names the situation rather than the
  permission.
- **The pre-send check is three named passes** (cut, rewrite, check your own claims) followed
  by two tests of the finished draft. It was one list of deletions with a verify step, which
  gave the self-reporting pass no place of its own. `evals/cases/self-report-plainly`
  referred to "step 9" of a check that has had no numbered steps since 2.3.0; it now names
  the pass.

## [2.3.0] - 2026-08-05

### Added

- **`house-response-style` extends the no-jargon rule to self-reporting.** Rule 3 listed
  only words about system behavior ("tombstone", "reap", "drain"), so the words an agent
  uses for its *own* work read as allowed. That is the highest-drift case in a coding
  session: the model reports on itself constantly, and the reader cannot audit the
  shorthand. "The suite is green" hides the test count. "That was a flake" hides the whole
  argument for why a failure is unrelated, which is what failed, what was re-run, and why
  the change cannot be the cause. A replacement table now covers both, plus "smoke test",
  "round-trip", "surfaced", "lands", "wire up", and "quick win". Step 9 of the pre-send
  check makes re-reading every claim about your own work a required pass, and asks for a
  number wherever one exists.
- **`evals/cases/self-report-plainly`** hands the model the exact situation that produces
  those two words (a passing suite plus one test that failed once and then passed) and
  forbids them, while requiring the count, the re-run, and the reason the failure is
  unrelated. Verified to discriminate: 10 of 10 graders pass on a plain report and 6 fail on
  the jargon version.
- **Check 11 in `hooks/test-hooks.js`** pins the rule in both response-style sources, the
  skill and `preamble.js`'s fallback, so a failed file read cannot silently drop it.

### Changed

- **The standard is now named in full where the rule is stated.** The section is "Write in
  Simplified Technical English, which is specified in ASD-STE100", and its opening states
  that ASD-STE100 is the controlled-English standard published by the AeroSpace and Defence
  Industries Association of Europe. The two halves are now listed explicitly: follow the
  writing rules, never the licensed dictionary. Previously the name and the number appeared
  only in passing, so a reader could not tell what to look up, and the split between the
  rules and the dictionary was one clause easy to miss. A line records that the title is
  "Simplified", not "Simple". Check 11 asserts that both sources carry the full name, the
  number, and the dictionary exclusion.
- **Two rules now outrank the rest: accuracy beats brevity, and label your confidence.** The
  file had no tie-breaker for the case where a shorter answer would be less true, and nothing
  asking the model to separate what it verified from what it inferred. Both are now stated
  first, above every wording rule.
- **`house-response-style` is 20% shorter, with the repetition removed.** "Lead with the
  answer" was stated in four places and narration-cutting in three; each is now stated once,
  plus one deliberate reference (the exception list, and the pre-send check, which is a
  different action from the rule). Every Bad/Good example pair survives, because the evals
  show those are what change behavior.
- **Two absolute rules relaxed to match how engineers actually read.** Terminology
  consistency now applies "where ambiguity would cost the reader" rather than banning
  synonyms outright, and the jargon rule now targets borrowed metaphor while explicitly
  allowing domain terms an engineer reads fluently (`serialize`, `refactor`, `idempotent`,
  `bootstrap`). The metaphor examples are unchanged: "hydrate" and "tombstone" hide a
  mechanism, which is the case worth banning.
- **New "Match the reader" section:** depth follows the reader's demonstrated knowledge, and
  tone follows the task, since these rules target technical answers and not every response is
  one.
- **The sentence limit keeps its number.** It was briefly relaxed to "short enough to read
  once" and then restored, because measurement contradicted the change: with no number, the
  model wrote 31- and 32-word sentences. The joiner guidance added alongside it ("cut at
  'which', 'so', 'but', 'since', 'because'") is what makes the number reachable, since length
  comes from two statements joined rather than one long statement.

### Fixed

- **`decision-matrix-trigger`'s grader demanded the literal word "recommend".** It failed 3
  of 3 runs on responses that were following the rule correctly: the model opened with
  `**Add the nullable column to `users`.**`, a bold imperative, which satisfies "lead with
  the answer" better than a labelled restatement. The check now asserts the response *opens*
  with a bold span or heading, which accepts every correct form and still rejects a response
  that builds up to its recommendation. The case remains failing for a separate,
  undiagnosed reason recorded in its `known_failing` field.
- **`max_sentence_words` raised from 25 to 35 in the two cases that use it.** The 25-word
  check failed every run, including on the file as it stood before this session (0 of 3,
  worst case 39 words), so it was reporting a permanent red rather than a regression. The
  skill still states 25 as the target; the grader is now a ceiling on runaway sentences. The
  gap is documented in `evals/README.md` and in each case's `why`.

## [2.2.0] - 2026-08-04

### Added

- **`house-response-style` now mandates Simplified Technical English.** A new "Write in
  Simplified Technical English" section adopts the ASD-STE100 writing rules: one word carries
  one meaning and one part of speech, no jargon or borrowed metaphor ("tombstone", "reap",
  "drain", "hydrate", "poison pill"), active voice with imperative instructions, simple verb
  tenses, one instruction per sentence, 20 words maximum for an instruction and 25 for an
  explanation, positive phrasing, no dropped articles, no noun stacks over three, English
  instead of Latin abbreviations, and condition-before-instruction ordering in warnings.
  Technical names and technical verbs (file paths, commands, settings, error text) stay
  verbatim, which is itself an STE allowance; an unavoidable term is defined in the same
  sentence that uses it.
  - **The section states its own limit.** It adopts the writing rules only and explicitly
    disclaims the controlled dictionary, which is licensed material that cannot be shipped
    here and would strip ordinary technical conversation down to manual-speak. Guessing at
    dictionary membership is called out as prohibited rather than left to inference.
  - Scoped explicitly to wording, not content, so no fact, caveat, number, or warning is
    dropped to make a sentence simpler.
- **American English is now mandatory, in both injected documents.** `hooks/style-core.md`
  gains a "Spelling" section covering identifiers, comments, documentation, commit messages,
  log lines, and user-facing strings, so the rule reaches sessions *and* subagents (the
  coding core is injected into both). `house-response-style` gains rule 14 for prose. Both
  carry the same exception: match the spelling of a name you do not own, so an API field
  called `colour` stays `colour` rather than being silently renamed across a boundary. The
  degraded-path fallbacks in `preamble.js` carry the rule too.
  - Existing British spellings in the repository were normalized in the same pass
    ("honoured", "honours", "honouring", "recognisable" across `AGENTS.md`, `CHANGELOG.md`,
    `hooks/test-hooks.js`, and `skills/style-testing/scripts/check_framework_leak.py`), so
    the repository now follows the rule it ships.
- **`house-response-style` now requires a decision matrix for hard choices.** A new "Put hard
  choices in a decision matrix" section with a three-part trigger test (2-4 real options,
  more than one factor that matters, expensive to undo or directly asked), an explicit skip
  rule so obvious calls stay prose, a column/cell format that bans bare scores, and a worked
  example ending in a bold recommendation plus the condition that would reverse it.

### Changed

- The "Why this shape" rationale gains a fourth fact (a word the reader has to decode costs
  more than a longer sentence), and the pre-send check gains three rewrite passes and a
  second verify question covering the matrix.
- **The decision matrix now fixes the order of its parts**, resolving a contradiction the
  eval suite caught. "Be concise" says lead with the answer; the matrix section said end
  with a bold recommendation. When the question is "which should I pick?", the
  recommendation *is* the answer, so the two rules pulled in opposite directions and the
  model could satisfy only one. The recommendation now leads in bold above the table, the
  table shows the work, and one line after it names what would change the answer. Stating
  it twice is called out as wrong.
- **The Simplified Technical English section is roughly half its previous length.** It no
  longer explains what ASD-STE100 is or recounts its history; the reader is a model that
  already knows the standard. What remains is the delta: which half of the standard applies
  (writing rules, not the licensed dictionary), that the rules govern wording and never
  content, the thirteen rules stated once each, and the four examples that actually steer
  behavior.
- `preamble.js`'s degraded-path response-style fallback carries the plain-language and
  decision-matrix rules, so a failed read of `SKILL.md` no longer silently drops them.

### Fixed

- `AGENTS.md` described the injected coding-style core as "nine cross-language principles";
  `hooks/style-core.md` ships ten.
- `README.md` was missing two registration rows that `AGENTS.md` already carried: the
  `house-response-style` skill and the `/response-style` command. Both surfaces now list all
  34 skills, 12 agents, and 36 commands.
- **Four components loaded with empty metadata.** `claude plugin validate --strict` (the
  official validator, which parses the YAML rather than pattern-matching it like
  `/validate-plugin` does) found unparseable frontmatter in `skills/production-ops/SKILL.md`,
  `skills/review-fresh-eyes/SKILL.md`, `agents/claude-md-reviewer.md`, and
  `agents/software-engineer.md`. All four had an unquoted `description` containing a colon
  followed by a space, which YAML reads as a nested key; the parse failed and every
  frontmatter field (`name`, `description`, `tools`) was silently dropped at load time. The
  three single-line descriptions are now quoted, and `claude-md-reviewer`'s multi-line
  description (which spans blank lines and contains double quotes) is now a block scalar.
  The repository validator missed these because it read frontmatter as text; the root cause
  was confirmed by validating a scratch plugin with and without the quotes.

## [2.1.0] - 2026-07-28

### Changed

- **`plan-review` now grounds plans in the codebase and drafts what is missing.** Shaped by a
  live run against a real plan (which caught a conditionally-wrong behavioral claim no
  text-only review could have seen):
  - **Codebase Grounding** is a required step: existence, pattern, stack, and behavior checks
    over every claim the design depends on; findings route to Feasibility (1-2 unverifiable
    claims YELLOW, approach hinges on code that does not exist or behave as described RED).
  - **Completeness is anchored to the `/plan-feature` canonical section list**, so a plan can no
    longer score GREEN by silently omitting a section (previously it was judged only against the
    headings it declared).
  - **Draft, don't instruct:** a missing or failed Acceptance Criteria section gets a paste-ready
    draft in the review (3-6 testable criteria derived from goals and scope), and a missing
    Testing Strategy gets a drafted test plan; never just "add criteria". The gate's
    where-to-look list now includes test-plan sections with objectively pass/fail assertions.
  - **Mechanical verdicts:** any RED is Major Rework; 2+ YELLOW or a milestone-1 blocker is
    Needs Revision; otherwise Ready. The summary must state whether milestone 1 is blocked.
  - **Open Questions** now score under Dependencies when work depends on them; the
    Roles-vs-stages MECE pairing applies only when the plan assigns owners (solo plans skip it).
  - **Report-only with an offer-to-apply handoff** that follows the plan's own revision
    conventions, plus a re-review protocol: verify a prior revision note against the body, and
    never re-litigate decisions the plan records with rationale and evidence.

## [2.0.0] - 2026-07-27

### Changed

- **BREAKING: the plugin is now named `tadw`.** Every skill, agent, and command was addressed
  through a 31-character prefix (`templeton-agentic-dev-workbench:fresh-eyes-cr`) before the part
  that carried any meaning. The invocation namespace is derived from the plugin's name, so shortening
  the name shortens every invocation: `tadw:fresh-eyes-cr`, `tadw:code-reviewer`, `/tadw:quality-gates`.

  There is no compatibility shim. Listing the plugin under both names would install every skill and
  command twice and fire the `SessionStart` hook twice per session, so this is a clean cut. To
  upgrade:

  ```bash
  /plugin marketplace update templeton-agentic-marketplace
  /plugin uninstall templeton-agentic-dev-workbench@templeton-agentic-marketplace
  /plugin install tadw@templeton-agentic-marketplace
  ```

  Then restart the session. Anything outside this repo that names a skill or agent by its full
  prefix (`.outrigger/config` files, `RALPH.md`/`AGENT.md` prose, `Skill(...)` and `Agent(...)`
  permission entries in `.claude/settings.local.json`) needs the prefix rewritten; a stale prefix
  fails to resolve rather than falling back.

  Unaffected: the repository name and its git remote, the `TADW_STYLE_CORE` environment variable and
  the `.tadw-style-core-off` flag file, and the `tadw-*` beads issue prefix. Those were never derived
  from the plugin name and keep working untouched.

## [1.19.2] - 2026-07-22

### Fixed

- **The failure marker ignored the off-switch.** The `|| echo <marker>` fallback added in 1.18.1
  fired whenever `node` failed, including for users who had deliberately disabled the style core.
  They got `<!-- house-style-core: FAILED to load -->` injected into every session, which is both
  noise and a lie: nothing failed, they turned it off. Hooks now run through `hooks/run-hook.sh`,
  which checks the off-switch **before** spawning `node`. That ordering is the fix, since no
  node-missing path can skip a check that already happened.
- **The wrapper depended on the environment it exists to survive.** Two defects found while
  iterating on the fix above, both the same silent-no-op class it was meant to eliminate. It
  lowercased with `tr`, so on a PATH without `tr` the substitution failed silently, the value read
  as empty, and `TADW_STYLE_CORE=off` was ignored entirely. And an unset `HOME` aborted it under
  `set -u`, emitting neither the core nor the marker. It now uses no external command and defaults
  `HOME`, verified under both `sh` and `dash`.
- **A temp-directory leak in the hook suite,** pre-existing and worsened by the new checks: roughly
  26 directories per run were left in the system temp dir, accumulating on every dev machine and
  CI push. All scratch directories now live under one root removed on exit.
- **`TypeError` instead of a clean assertion** when a manifest entry lacks a `hooks` array.

### Changed

- **The hook suite goes from 6 to 11 checks**, each added after a real defect shipped green under
  a narrower suite. The two most valuable are new kinds rather than new cases. One **executes the
  real manifest commands** against a working and a broken `node`; everything else tested the
  manifest as a string and the wrapper as a program, never together, so a shell-quoting error
  could ship green (it matters most for the `SubagentStart` fallback, which is JSON nested inside
  single quotes inside a JSON string). The other guards `commandWindows`, which cannot be executed
  on macOS or the Linux runner and had no guard at all, which is how it lost the off-switch in the
  first place; the suite now asserts it references both off-switch paths and a failure marker.
- **The check count documented in `AGENTS.md` is asserted, not remembered.** It drifted three
  times while this work was in progress, so the suite now compares the documented number against
  the number of checks it actually ran.

### Known limitations

- `runtime.js` resolves the default config dir with `os.homedir()`, which falls back to the
  password database, while `run-hook.sh` uses `$HOME` only. They diverge solely when `HOME` is
  unset **and** the flag file exists **and** `node` is broken. Closing it needs either an external
  command or tilde expansion, which `dash` does not perform with `HOME` unset, so it is documented
  in place rather than fixed by reintroducing the dependency the wrapper just removed.
- `commandWindows` is guarded structurally but remains unexecuted; no PowerShell is available on
  macOS or the CI runner.

## [1.19.1] - 2026-07-22

### Fixed

- **The sentinel markers could be widened to exempt the whole document, and the check reported
  OK.** Moving `<!-- leak-check:appendix-start -->` above the principles left both markers well
  formed and every required heading present, so nothing objected: the checker scanned one line and
  printed a clean pass. Unlike the five bypasses this design replaced, that needs a deliberate
  edit rather than ordinary markdown, but a self-check that can be silently disabled by moving one
  line is not much of a self-check. The required principle sections must now appear as `## `
  headings OUTSIDE the exempt region, so widening the markers past them fails with a named
  section rather than passing. Found by adversarial testing of the new design, not by review.

## [1.19.0] - 2026-07-22

### Changed

- **The framework-leak check no longer parses markdown.** It located the exempt appendix by
  finding a `## Appendix` heading, which meant it had to know whether that heading sat inside a
  fenced code block. Five bypasses shipped from that one decision: a fenced fake heading, a ````
  block containing ```, a closing fence carrying an info string, an over-indented fence, and an
  exemption that ran to end of file. Each was patched by adding another CommonMark rule to a
  hand-rolled scanner, and each patch left the next rule unimplemented. The exempt region is now
  delimited by explicit `<!-- leak-check:appendix-start -->` and `<!-- leak-check:appendix-end -->`
  sentinels, and the fence scanner is deleted. Two properties make that safe: exactly one of each
  marker is required, so a marker duplicated inside a code sample is an error rather than an
  ambiguous choice; and any marker problem disables the exemption entirely and scans the whole
  document, so the failure mode is a visible false positive rather than a silent pass.
- **The exemption is bounded.** It previously ran from the appendix heading to end of file, so a
  section appended after the appendix was silently exempt. It now covers only the region between
  the two markers.
- **The regression suite derives its cases from the design contract, not from known bugs.** The
  previous suite enumerated bugs already found and reported "All 15 checks passed" while three
  live bypasses existed in the function it covered. Cases are now grouped by contract (marker
  contract, exemption scope, parser independence) and cover 23 checks, including all five historic
  bypasses as parser-independence assertions and the previously untested frontmatter
  name-versus-directory branch.

### Fixed

- **CI ran no tests at all.** The only job was `rumdl fmt --check .`, so both `hooks/test-hooks.js`
  and the leak checker suite were run only when a human remembered. A `tests` job now runs both
  suites plus the leak check on the shipped skill. Both are stdlib-only, so no install step is
  needed.
- **Markdown linting was failing on `main`.** Files added earlier today carried five `rumdl`
  violations, so the one CI job that did exist was red and unnoticed. Fixed, including a
  line-initial `36.` in a plan document that markdown was rendering as an ordered list item.

## [1.18.3] - 2026-07-22

### Fixed

- **The 1.18.2 fence fix was incomplete and left a second bypass open.** It treated any
  fence-looking line as a toggle, so a ```` block containing a ``` line read as closed. The
  `## Appendix` heading inside that block was then seen as a real heading, split the document
  early, and exempted everything after it. A file with `pytest` in its body exited 0 again, the
  same failure the previous release claimed to fix. Fence matching now follows CommonMark: a block
  opened with N of a character closes only on a run of at least N of that same character, so a
  `~~~` line inside a ``` block is correctly treated as content.

### Added

- **A 15-case regression suite for the leak checker** at
  `skills/style-testing/scripts/test_check_framework_leak.py` (stdlib only, no install, mirroring
  `hooks/test-hooks.js`). Two bypasses shipped in consecutive releases because this script had no
  tests and each ad-hoc verification was thrown away. The suite pins both bypasses, the
  code-comment heading bug, the guard against false-positives on legitimate fenced pseudocode, and
  asserts the shipped `SKILL.md` satisfies its own checker. Reverting either fence fix now fails
  the suite.

## [1.18.2] - 2026-07-22

### Fixed

- **`check_framework_leak.py` could be silently disabled by a code fence.** The script split the
  document at the first line matching `## Appendix` without checking whether that line was inside
  a fenced code block. A fence containing that heading (entirely plausible in a document that
  shows its own structure) ended the body early, so every framework token after it was treated as
  appendix content and exempted. A file containing `pytest` in its body passed the check. The
  script is now fence-aware.
- **Required-section detection accepted code comments as headings.** `check_sections` collected
  every line starting with `#`, which includes shell and Python comments inside fenced examples.
  A file whose only real heading was the appendix passed the structural check because
  `# Principles` appeared in a code sample. Headings are now only counted outside fences.

Both bugs shared one root cause and were found by edge-case testing rather than review; the
regression cases are documented in the fix commit.

## [1.18.1] - 2026-07-22

### Fixed

- **The `SessionStart` matcher missed the `fork` session source, so forked sessions got no style
  injection at all.** Claude Code declares five `SessionStart` sources; the matcher listed four.
  Any session created by a conversation rewind, a branch, or `--fork-session` started with no
  coding-style core and no response style, silently, with no error and no marker to notice it by.
  The matcher is now `startup|resume|clear|compact|fork`.
- **`/response-style` was a no-op.** The command told the model to load the `house-response-style`
  skill, but that skill sets `disable-model-invocation: true`, so the Skill tool hard-refuses it.
  The one designed recovery path for style drift after a compaction, and the only way to get the
  response style inside a subagent, therefore did nothing. The command now **reads**
  `skills/house-response-style/SKILL.md` directly, which keeps the single source of truth while
  preserving the skill's non-model-invocable design.
- **Hook failures are now visible instead of silent.** Each command was `node "..."; exit 0`,
  which converted every possible failure (missing `node`, syntax error, bad permissions) into a
  successful no-op. Commands are now `node "..." || echo <failure marker>`, so a failure injects
  `<!-- house-style-core: FAILED to load ... -->` rather than nothing. The absence of any marker
  now means the hook did not run; a FAILED marker means it ran and could not execute. The
  `SubagentStart` fallback emits valid JSON so the wrapper contract still holds.
- **`AGENTS.md` claimed `plugin.json` performs component registration. It does not.** The file
  carries metadata plus the `hooks` field and lists zero components; skills, agents, and commands
  are auto-discovered from their directories. The "Adding a New Skill" and "Adding a New Agent"
  steps told readers to edit it, which had already produced one unsatisfiable acceptance criterion
  in the tracker. They now name the real registration surfaces, and the skill steps add the
  orphan-check requirement that `/validate-plugin` enforces.

### Changed

- **`hooks/test-hooks.js` now covers the manifest, not just the scripts.** The suite went from 4
  checks to 6, adding one that asserts the `SessionStart` matcher covers all five sources, that
  every referenced script exists, and that no command can fail silently; and one that guards
  `/response-style` against being routed back through the Skill tool. Both of the bugs fixed above
  shipped green under the old suite, which never opened `style-core-hooks.json`.

## [1.18.0] - 2026-07-22

### Added

- **`style-testing`, a universal framework-independent test-style core.** Until now the only
  test guidance in this workbench was `style-rspec`, so anyone working in pytest, Vitest, XCTest,
  or Minitest got nothing, even though most of what makes a good test is framework-independent.
  The new skill carries 14 principles: ten transposed from `style-rspec` (outermost fast seam,
  name the action once, hoisted declarative setup, one behavior per test, scenario-named groups,
  lightest sufficient fixture, lazy-unless-ordering-matters, deterministic identification by
  unique key, shared setup visible to every case, prerequisites before the action) and four
  net-new that nothing in the repo covered (determinism with injected clocks and seeds,
  behavior-not-implementation naming, what not to test, and one clear cause of failure per
  assertion). Examples use a declared neutral pseudocode so no rule reads as belonging to one
  framework, and a single fenced appendix maps every principle to its pytest, Vitest/Jest,
  XCTest/Swift Testing, and Minitest idiom.
- **`check_framework_leak.py`, enforcement for the above.** The core's value rests entirely on
  the principles staying framework-free while the appendix carries the concreteness. Author
  discipline does not hold that line across edits, so a stdlib-only script does: it scans
  everything between the frontmatter and the appendix for framework tokens and fails the build on
  any leak. It caught a `style-rspec` reference in the skill's own introduction on its first run.
- **An invocation battery for the skill's `description`.** For a model-invoked skill the
  description is the only thing that determines whether it ever fires, and `style-rspec` is the
  cautionary example: its description was scoped so narrowly ("RSpec tests in Rails apps") that it
  could not fire on this repo's current work. The battery at
  `skills/style-testing/references/invocation-battery.md` runs 8 realistic test prompts and 3
  controls against a 7-of-8 bar. First run passed 8/8 with 0/3 false fires.

### Changed

- **`style-rspec` is now a thin delta on `style-testing`, down from 496 lines to 119.** Everything
  that would still read as correct advice with the RSpec nouns stripped out moved into the core.
  What remains is the RSpec spelling of those principles as a mapping table, plus four genuinely
  Rails mechanics with no framework-free parent: `let` versus `let!` evaluation semantics,
  `expect { subject }` versus a bare `subject` call, FactoryBot's three build strategies, and
  `it_behaves_like` resolving variables at invocation rather than definition.
- **Test files now route to `style-testing` through the agents, not just the docs.**
  `software-engineer` and `code-reviewer` dispatch to style skills by file extension and had no
  entry for test files at all, so a skill wired only into `AGENTS.md` and `README.md` would have
  shipped unreachable, which is precisely the state `style-rspec` was in. Both agents plus
  `/python-feature-dev` now match test-file patterns across Python, TypeScript, Ruby, Swift, and
  Go. This also satisfies `/validate-plugin`'s orphan rule, which counts referrers in `agents/`
  and `commands/` but not `skills/`.
- **`review-rails` defers to `style-testing` for test style,** naming `style-rspec` only when the
  project's suite is actually RSpec.
- **The `bv` agent-instructions block moved out of `AGENTS.md` into `docs/beads-workflow.md`.**
  Ninety lines of generated tracker documentation, largely duplicating the existing "Issue
  Tracking (br + bv)" section, had been appended to the top-level agent instructions. `AGENTS.md`
  drops from 727 to 642 lines and links to the extracted file, which records its own provenance
  including the marker `bv` uses, so a future re-injection is recognizable rather than mysterious.

## [1.17.0] - 2026-07-22

### Changed

- **Response style is now a single-source skill.** The always-on response style
  moved from a hooks-local copy (`hooks/response-style.md`) into a proper skill
  at `skills/house-response-style/SKILL.md`, and the `SessionStart` hook now
  reads that file (stripping its YAML frontmatter) as its source. The always-on
  injection and the new on-demand surface can no longer drift, mirroring the
  single-source pattern the coding-style core already uses for the `style-*`
  skills. Parent-session-only injection, the off-switch, the fallback, and the
  parent-only-not-subagent policy are unchanged.

### Added

- **`/response-style` command and `house-response-style` skill.** The response
  style is now directly invocable to re-anchor after a compaction or to load the
  rules inside a subagent (which does not inherit the parent session's injected
  style). The skill body is more thorough than the prior hooks copy: it states
  its persistence, grounds the rules in *why* (the answer is the payload, the
  reader scans rather than parses, structure is a signal), pairs each concise
  rule with a Bad/Good example, lists escape hatches (explain/walk-me-through,
  a rule that would delete the answer, destructive actions, real ambiguity), and
  closes with a pre-send check.
- `test-hooks.js` now asserts the response-style frontmatter is stripped before
  injection (no skill frontmatter keys leak into the injected text).

## [1.16.0] - 2026-07-20

### Added

- **Acceptance criteria enforced across the plan and bead pipeline.** Every
  plan and bead must now carry testable acceptance criteria, closing a gap
  where `/plan-feature` could emit a plan with none while `/plan-review` and
  `/plan-to-beads` required them. `feature-planner` gains an Acceptance
  Criteria section and a per-milestone "Done when" column; `plan-review` gains
  an Acceptance Criteria gate that runs before scoring (a plan with none, or
  only subjective ones, is Actionability RED → Major Rework); `project-manager`
  gains the matching belief and refusals; `feature-development` captures
  criteria in discovery.
- **`/agentic-clean-code` command**, giving the existing `agentic-clean-code`
  skill an entry point instead of leaving it an orphan.
- **`/bead-audit-all` command**: a bounded, report-only sweep of the whole
  backlog. Enumerates every bead via `br list --status open --limit 0 --json`,
  runs the `bead-audit` skill on each exactly once, and prints a ranked
  health table (worst band first). Distinct from `/goal`, it terminates on its
  own rather than installing a Stop hook, and never writes back.
- **Scorecard in `bead-audit`.** An optional weighted 0-100 score, banded
  Poor / Weak / Adequate / Great / Excellent, derived from the existing
  content and structure verdicts and capped so the band can never outrank the
  pass/fail verdict (Excellent is exactly equivalent to PASS). `score`, `band`,
  `score_denominator`, and `excluded_dimensions` added to the JSON output. Ships
  a fixture regression suite under `skills/bead-audit/references/fixtures/`.
- **ADR 0001: native tracker fields are canonical.** `br`'s `design`, `notes`,
  and `acceptance_criteria` fields are the canonical home for those sections,
  not the description body. `plan-to-beads` now writes each section to its
  native field (create-then-update), so generated beads pass `bead-audit`'s
  structure check on creation.
- **`docs/plans/feature-plan-bead-refine.md`**, the plan for a scored backlog
  refinement loop. Milestone 1 (the scorecard above) shipped; the driver is
  deferred pending a state-machine respecification of its termination logic.

### Fixed

- `plan-to-beads`: replaced `printf` with quoted heredocs in the `br update`
  examples, so acceptance criteria containing a literal `%` are no longer
  silently corrupted; reworked Step 5b to handle the two-call model's
  created-but-unpopulated failure state without producing duplicate beads.
- `bead-audit`: corrected the JSON `score_denominator` documentation (a bug's
  base is 110, not 100) and clarified that per-check `points` exclude the
  separately-computed structure contribution.

### Changed

- `.beads/.gitignore` excludes `br`'s local `.br_history/`.

## [1.15.1] - 2026-07-13

### Added

- Always-on response style (`hooks/response-style.md`): the `SessionStart` hook
  now injects a second document alongside the coding-style core that governs
  how responses to the user are written. Three rule sets: be concise (lead
  with the answer, cut narration, selective rather than compressed); suggest
  one follow-up question ("Worth asking next: ...") only when the answer
  genuinely raises it, never as a ritual; and end any response that leaves
  work open with a "Next actions" section split by owner ("Me (Claude)" vs
  "You"), omitted entirely when nothing is open. Injected
  into parent sessions only; `SubagentStart` deliberately keeps injecting the
  coding-style core alone, since a subagent's final text is consumed by the
  orchestrator as data, not read by a human. Opens with its own
  `<!-- house-response-style: loaded -->` marker; covered by `test-hooks.js`
  (present in `SessionStart`, absent in `SubagentStart`); shares the existing
  off-switch (`TADW_STYLE_CORE=off` / flag file).

## [1.15.0] - 2026-07-08

### Added

- `production-ops` skill and `/prod-ops` command: safely operate the production
  apps (atlas, meridian, compass, ...) that run as Docker Compose stacks on a
  single Hetzner VPS, over a two-hop SSH login (`root`, then `su - deploy`).
  Covers service ops (status, logs, restart, `up -d`, recreate) and PostgreSQL
  data ops (migrations, backups, one-off data fixes) under strong guardrails:
  read-only by default, a secret-free `hetzner-prod` SSH alias (no IP in the
  repo), a mandatory `pg_dump` before any data mutation, transactional one-off
  writes with a matched row count, verify-after, a written rollback for every
  risky change, and hard-stops (refuse + escalate) on volume wipes, `prune`,
  `DROP`/`TRUNCATE`, and `WHERE`-less `UPDATE`/`DELETE`. Host-specific facts are
  pinned in a single Environment Profile block so the technique stays generic and
  retargetable.

## [1.14.0] - 2026-07-07

### Added

- `roadmap-dashboard` skill and `/roadmap-dashboard` command: synthesize the
  codebase and the `beads` tracker into one self-contained, zero-dependency
  interactive HTML dashboard at `docs/roadmap.html` (executive KPIs, pure
  HTML/CSS diagrams, Kanban board, prioritized roadmap). Ships a bundled
  `collect_beads.py` data-collection script and versions the output
  (`docs/roadmap-vX.Y.html`) instead of overwriting a prior report.

### Changed

- `product-surface-docs` skill and `/product-surface-docs` command are now
  refresh-first: when a `docs/products/` tree already exists, the run updates it
  in place (human prose preserved, facts corrected additively, `last_reviewed`
  bumped, findings reconciled against the ledger) rather than regenerating from
  scratch. Full generation happens only for a surface, or a tree, that does not
  yet exist, which makes the command safe to run on a schedule.
- Style core (`hooks/style-core.md`): promoted "comment the why, not the what"
  to its own standalone principle, and aligned the `review-rails` skill with it.
- Documentation: `AGENTS.md` and `README.md` updated to cover the new command
  and skill.

### Fixed

- `.gitignore` now excludes Python `__pycache__/` and `.pyc` build artifacts,
  and a previously tracked `.pyc` was removed from version control.

---

Releases prior to 1.14.0 predate this changelog; their history is recorded in
the git tags and commit log (latest prior tag: `v1.13.0`).

[Unreleased]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.12.0...HEAD
[2.12.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.11.1...v2.12.0
[2.11.1]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.11.0...v2.11.1
[2.11.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.10.1...v2.11.0
[2.10.1]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.10.0...v2.10.1
[2.10.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.9.1...v2.10.0
[2.9.1]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.9.0...v2.9.1
[2.9.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.8.0...v2.9.0
[2.8.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.7.3...v2.8.0
[2.7.3]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.7.2...v2.7.3
[2.7.2]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.7.1...v2.7.2
[2.7.1]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.7.0...v2.7.1
[2.7.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.6.0...v2.7.0
[2.6.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.5.2...v2.6.0
[2.5.2]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.5.1...v2.5.2
[2.5.1]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.5.0...v2.5.1
[2.5.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.4.2...v2.5.0
[2.4.2]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.4.1...v2.4.2
[2.4.1]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.4.0...v2.4.1
[2.4.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v2.3.1...v2.4.0
[1.14.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v1.13.0...v1.14.0
