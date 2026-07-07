#!/usr/bin/env python3
"""Collect and normalize beads issues into a single JSON blob for the roadmap dashboard.

This is the deterministic data layer for the `roadmap-dashboard` skill. It answers one
question: "what does the beads tracker say about the outstanding work?" and emits a
stable JSON shape the dashboard builder can consume without re-deriving the parsing each run.

Source of truth: the beads JSONL export (`.beads/issues.jsonl`). When `br` is available and
a DB exists, the JSONL is refreshed first (`br sync --flush-only`) so the export is current;
the JSONL is then parsed directly, because it carries full records including dependencies.

Usage:
    collect_beads.py [--dir PATH] [--jsonl PATH] [--out PATH] [--no-refresh]

Exit codes:
    0  success (a missing workspace or empty tracker still emits the empty shape and exits 0)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# beads priority integers -> human tiers (0=Critical ... 4=Backlog)
PRIORITY_LABELS = {0: "Critical", 1: "High", 2: "Medium", 3: "Low", 4: "Backlog"}

# statuses beads treats as "finished work"
DONE_STATUSES = {"closed", "done"}
IN_PROGRESS_STATUSES = {"in_progress", "in-progress"}

# beads dependency types that actually gate readiness. A `related`/`parent-child`/
# `discovered-from` edge is context, not a blocker, so it must not mark an issue blocked.
BLOCKING_DEP_TYPES = {"blocks", "conditional-blocks", "waits-for"}


def find_beads_dir(start: Path) -> Path | None:
    """Walk upward from `start` looking for a `.beads/` directory."""
    for candidate in [start, *start.parents]:
        beads = candidate / ".beads"
        if beads.is_dir():
            return beads
    return None


def refresh_jsonl(beads_dir: Path) -> None:
    """Best-effort flush of the beads DB to JSONL so the export is current.

    Silent no-op when `br` is not on PATH or the flush fails; the caller falls back
    to whatever JSONL already exists on disk.
    """
    if shutil.which("br") is None:
        return
    if not any(beads_dir.glob("*.db")):
        return
    try:
        subprocess.run(
            ["br", "sync", "--flush-only"],
            cwd=beads_dir.parent,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        # A stale JSONL is better than aborting the whole dashboard build.
        pass


def load_issues(jsonl_path: Path) -> list[dict]:
    """Parse a beads JSONL export, tolerating blank lines and tombstones."""
    issues: list[dict] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            print("warning: skipping malformed JSONL line", file=sys.stderr)
            continue
        # Skip soft-deleted tombstones; they are not real outstanding work.
        if record.get("deleted_at") or record.get("delete_reason"):
            continue
        issues.append(record)
    return issues


def _dep_target(dep) -> str | None:
    """Pull the target issue ID out of a dependency edge in any of its shapes.

    The canonical beads field is `depends_on_id`; the fallbacks tolerate hand-edited
    JSONL and older exports.
    """
    if isinstance(dep, str):
        return dep
    if isinstance(dep, dict):
        return (
            dep.get("depends_on_id")
            or dep.get("depends_on")
            or dep.get("target")
            or dep.get("to")
            or dep.get("id")
        )
    return None


def extract_dep_edges(record: dict) -> tuple[list[str], list[str]]:
    """Split a record's dependency edges into (all_targets, blocking_targets).

    `all_targets` feeds the full dependency graph; `blocking_targets` is the subset whose
    edge type gates readiness. Bare-string edges have no type, so they are treated as
    blocking to stay backward-compatible with untyped exports.
    """
    all_targets: list[str] = []
    blocking: list[str] = []
    for dep in record.get("dependencies") or []:
        target = _dep_target(dep)
        if not target:
            continue
        all_targets.append(target)
        dep_type = dep.get("type") if isinstance(dep, dict) else None
        if dep_type is None or dep_type in BLOCKING_DEP_TYPES:
            blocking.append(target)
    return all_targets, blocking


def normalize(record: dict) -> dict:
    """Reduce a raw beads record to the fields the dashboard renders."""
    priority = record.get("priority")
    est_minutes = record.get("estimated_minutes")
    all_deps, blocking_deps = extract_dep_edges(record)
    return {
        "id": record.get("id"),
        "title": record.get("title", ""),
        "status": (record.get("status") or "open").lower(),
        "priority": priority,
        "priority_label": PRIORITY_LABELS.get(priority, "Unset"),
        "type": record.get("issue_type") or record.get("type") or "task",
        "assignee": record.get("assignee"),
        "estimated_minutes": est_minutes,
        "labels": record.get("labels") or [],
        "dependencies": all_deps,          # every edge, for the full graph
        "blocking_deps": blocking_deps,     # only readiness-gating edges
        "acceptance_criteria": record.get("acceptance_criteria"),
        "design": record.get("design"),
        "description": record.get("description"),
    }


def annotate_readiness(issues: list[dict]) -> None:
    """Mark each open issue as blocked when any dependency is not yet done.

    `blocked_by` lists only the unfinished upstream IDs, so the dependency graph can
    highlight the true critical path rather than every historical edge.
    """
    status_by_id = {i["id"]: i["status"] for i in issues}
    for issue in issues:
        unmet = [
            dep
            for dep in issue["blocking_deps"]
            if status_by_id.get(dep) not in DONE_STATUSES
            and dep in status_by_id  # ignore dangling refs to closed/purged beads
        ]
        issue["blocked_by"] = unmet
        is_open = issue["status"] not in DONE_STATUSES
        issue["ready"] = is_open and not unmet
        issue["blocked"] = is_open and bool(unmet)


def summarize(issues: list[dict]) -> dict:
    """Roll up the counts the executive dashboard needs at a glance."""
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    by_type: dict[str, int] = {}
    total_est = 0
    remaining_est = 0
    for issue in issues:
        by_status[issue["status"]] = by_status.get(issue["status"], 0) + 1
        by_priority[issue["priority_label"]] = by_priority.get(issue["priority_label"], 0) + 1
        by_type[issue["type"]] = by_type.get(issue["type"], 0) + 1
        est = issue["estimated_minutes"] or 0
        total_est += est
        if issue["status"] not in DONE_STATUSES:
            remaining_est += est

    done = sum(1 for i in issues if i["status"] in DONE_STATUSES)
    total = len(issues)
    return {
        "total": total,
        "done": done,
        "remaining": total - done,
        "in_progress": sum(1 for i in issues if i["status"] in IN_PROGRESS_STATUSES),
        "ready": sum(1 for i in issues if i["ready"]),
        "blocked": sum(1 for i in issues if i["blocked"]),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_type": by_type,
        "estimated_minutes_total": total_est,
        "estimated_minutes_remaining": remaining_est,
        # Task-count completion only. The dashboard must blend this with a code-grounded
        # assessment; a raw bead ratio is not the project's true completion percentage.
        "task_completion_pct": round(100 * done / total) if total else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path.cwd(),
                        help="Directory to start the .beads/ search from (default: cwd)")
    parser.add_argument("--jsonl", type=Path, default=None,
                        help="Explicit path to a beads issues.jsonl (skips auto-discovery)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write JSON here instead of stdout")
    parser.add_argument("--no-refresh", action="store_true",
                        help="Do not run `br sync --flush-only` before reading the JSONL")
    args = parser.parse_args()

    if args.jsonl is not None:
        jsonl_path = args.jsonl
    else:
        beads_dir = find_beads_dir(args.dir.resolve())
        if beads_dir is None:
            # No tracker in this repo. Emit the empty shape (exit 0) so the dashboard's
            # documented "no beads data" fallback path works instead of aborting.
            print("warning: no .beads/ workspace found; emitting empty result",
                  file=sys.stderr)
            jsonl_path = None
        else:
            if not args.no_refresh:
                refresh_jsonl(beads_dir)
            jsonl_path = beads_dir / "issues.jsonl"

    if jsonl_path is None:
        raw = []
    elif not jsonl_path.exists():
        print(f"warning: {jsonl_path} does not exist; emitting empty result", file=sys.stderr)
        raw = []
    else:
        raw = load_issues(jsonl_path)

    issues = [normalize(r) for r in raw if r.get("id")]
    annotate_readiness(issues)
    result = {
        "source": str(jsonl_path) if jsonl_path is not None else None,
        "summary": summarize(issues),
        "issues": issues,
    }

    payload = json.dumps(result, indent=2, default=str)
    if args.out is not None:
        args.out.write_text(payload, encoding="utf-8")
        print(f"wrote {len(issues)} issues to {args.out}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
