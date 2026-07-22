# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  including the marker `bv` uses, so a future re-injection is recognisable rather than mysterious.

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

[Unreleased]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v1.14.0...HEAD
[1.14.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v1.13.0...v1.14.0
