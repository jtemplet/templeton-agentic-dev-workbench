# Beads Field Mapping

How each field emitted by `scripts/collect_beads.py` maps onto the dashboard. The script is
the only supported way to read the tracker; do not hand-parse the JSONL.

## Per-Issue Fields → Dashboard Elements

| Field | Type | Where it renders |
|---|---|---|
| `id` | string | Kanban card ID (monospace), roadmap table, dependency graph node label |
| `title` | string | Card title, roadmap row, subsystem panel line item |
| `status` | string | Kanban column routing; maturity signal |
| `priority` | int 0-4 | Sort key for the roadmap |
| `priority_label` | string | Priority Tier badge (Critical/High/Medium/Low/Backlog) |
| `type` | string | Icon/label on cards (feature/bug/task/epic) |
| `assignee` | string/null | Card footer; `-` when null |
| `estimated_minutes` | int/null | Effort column; roll up for the "remaining work" KPI; `[Inference]` when null |
| `labels` | list | Grouping / subsystem attribution when labels name a component |
| `dependencies` | list of IDs | Every upstream edge (all types), for the full dependency graph |
| `blocking_deps` | list of IDs | Upstreams whose edge type gates readiness (`blocks`/`conditional-blocks`/`waits-for`); `related`/`parent-child` edges are excluded |
| `blocked_by` | list of IDs | The **unmet** subset of `blocking_deps`; drives blocked state and critical path |
| `ready` | bool | Open + no unmet deps → eligible for "next" and Todo (ready) styling |
| `blocked` | bool | Open + has unmet deps → blocked badge on Kanban/graph |
| `acceptance_criteria` | string/null | "Done when" detail in subsystem panels and roadmap tooltips |
| `design` | string/null | Technical context for the subsystem deep-dive |
| `description` | string/null | Card detail / panel body |

## Status → Kanban Column

- `open`, `ready`, `blocked` → **Todo** (badge the blocked ones)
- `in_progress`, `in-progress` → **In Progress**
- `closed`, `done` → **Done**

Any unrecognized status defaults to Todo; surface it verbatim so nothing is silently dropped.

## Priority Integer → Tier Label

`0 = Critical, 1 = High, 2 = Medium, 3 = Low, 4 = Backlog` (already mapped to `priority_label`
by the script; use that field directly). A missing priority renders as `Unset`, not a guess.

## Summary Block → KPIs

`summary` provides `total, done, remaining, in_progress, ready, blocked, by_status,
by_priority, by_type, estimated_minutes_total, estimated_minutes_remaining,
task_completion_pct`. Feed these into the KPI cards and the by-priority/by-type mini-charts.
Remember: `task_completion_pct` is one input to the blended completion figure, not the figure
itself (see `references/analysis-guide.md`).

## Dependency Tiers for the Graph

To lay out the dependency graph in topological tiers: tier 0 = issues with no `blocked_by`;
each subsequent tier = issues whose `blocked_by` are all satisfied by earlier tiers. Render
tiers as horizontal rows top-to-bottom. The critical path is the longest chain of
`blocked_by` edges; mark those nodes with the danger-colored border.
