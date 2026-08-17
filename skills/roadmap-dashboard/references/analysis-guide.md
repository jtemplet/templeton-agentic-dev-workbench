# Analysis Guide: Grounding the Dashboard in Evidence

The dashboard is only as good as the engineering assessment behind it. This reference covers
how to inspect the codebase, how to read the beads data, and how to compute a defensible
completion percentage. Do the analysis first; render second.

## Data Sources to Inspect

1. **Codebase.** Entry points, module layout, service boundaries, database schema/migrations,
   API route definitions, config files, CI/CD pipelines, and the test suite (what exists,
   what passes).
2. **Beads tracker.** The authoritative list of outstanding work. Collect it with the bundled
   script, never by eyeballing the JSONL by hand.
3. **Implicit signals.** `TODO`/`FIXME`/`HACK` comments, ADRs (often under `docs/decisions/`),
   and issue IDs referenced in recent commit messages (`git log --oneline -50`).

## Collecting Beads Data

SKILL.md step 1 covers running the collector (`collect_beads.py --out ...`) and reading its
JSON back; do not repeat that here. Flags worth knowing: `--jsonl PATH` points at an explicit
export instead of auto-discovering `.beads/`; `--no-refresh` skips the `bd export -o .beads/issues.jsonl`.
The output shape (a `summary` block plus per-issue fields) is documented field-by-field in
`references/beads-extraction.md`.

When `summary.total == 0` (no workspace, or an empty tracker), state plainly in the dashboard
that no tracker data was found and derive the roadmap from `TODO`s, open questions, and code
gaps instead, marking everything `[Inference]`.

## Cross-Referencing Code Against Beads

For each major subsystem, classify its implementation maturity by reconciling what the code
shows against what the beads say:

- **Built:** feature exists in code, has tests, and no open beads block it.
- **Partial:** code exists but has open beads, failing/missing tests, or `TODO`s in the path.
- **Stubbed:** interface/placeholder exists but core logic is absent or a bead marks it as
  not-started.
- **Planned:** only a bead exists; no code yet.

This classification drives the diagram colors (green/amber/red/gray) and the subsystem panels.

## Computing Overall Completion %

Do **not** publish the raw bead ratio (`done / total`) as the project completion figure. It
is a useful input, not the answer: a repo with three trivial closed beads is not 100% done.

Blend three signals into a single defensible number and show the rationale:

1. **Task completion** (`summary.task_completion_pct`): weight by remaining effort
   (`estimated_minutes_remaining` vs `_total`) when estimates exist, since a large open bead
   should count more than a small one.
2. **Feature maturity**: the share of major subsystems classified Built vs Partial/Stubbed/Planned.
3. **Production-readiness**: tests passing, CI green, migrations applied, no Critical open beads.

State the rationale in one or two sentences next to the hero gauge, e.g. "62%: core auth and
API are built and tested; the dashboard UI and billing subsystem remain (7 open beads, ~14h
estimated, 1 Critical)." Attach a `[Inference] Confidence: NN%` badge to the figure.

## Risk Identification

Enumerate risks from concrete evidence, not vibes: untested critical paths, single points of
failure, `blocked` beads on the critical path, schema changes without migrations, secrets in
config, stale dependencies, and any Critical-priority open bead. Place each on the 3×3 risk
matrix (Likelihood × Impact) in the dashboard and tie it to the bead or file that evidences it.

## Roadmap Sequencing

Order the outstanding beads by engineering value and velocity, respecting `blocked_by`:

- **Ready + Critical/High** first (unblocked, high priority).
- **Unblockers** next: beads that many others depend on, even if individually small.
- **Blocked** beads sequenced after their upstreams, grouped by the milestone they unlock.

For each roadmap item expose: Priority Tier, Effort (from `estimated_minutes`, or `[Inference]`),
Difficulty, Upstream Dependencies (`blocked_by`), Expected Impact, and Parallelization-Safety
(safe when it shares no files/subsystem with other in-flight work and has no unmet deps).
