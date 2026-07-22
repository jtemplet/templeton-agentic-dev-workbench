# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
