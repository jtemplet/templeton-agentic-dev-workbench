# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
