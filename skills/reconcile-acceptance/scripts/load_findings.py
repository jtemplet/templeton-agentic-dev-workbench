#!/usr/bin/env python3
"""Check a version 2 acceptance report, then split its findings by scope.

This is step 1 of the reconcile-acceptance skill. It refuses a missing, stale,
or foreign report before the skill edits anything. Those checks are the same on
every run, so a script decides them the same way each time (ADR 0011).

EVERY INPUT IS INJECTED. The skill passes the report path, the current HEAD, the
output of `git status --porcelain=v1 -z`, and the bead id it was given. This
script runs no git and no bd, so its suite needs no repository.

EXIT CODES. 0 prints the findings as JSON. 1 prints the BLOCKED machine line as
the only stdout line, with any detail on stderr. 2 is a usage error. 3 means the
counts make the report ACCEPTED, so there is nothing to fix.

THE ORDER OF THE REASONS is the plan's reasons table, and the first that holds
wins. All ten tokens are constants here, including the three only the skill can
decide, so one test can check them against SKILL.md.

WHY `failures-outside-change` NEVER PRINTS HERE. Acceptance findings name no
file, so no finding can sit outside the change before the skill re-runs its
command. `uncommitted-changes` still prints, by a wider rule than the
quality-gates loader uses: any path in `changed_files` with uncommitted changes
blocks a run that has something to fix, because any of them may be the file a
fix edits. With `base` null there is no changed set, and the skill decides.

WHAT IS IN SCOPE. FAIL criteria and FAIL gates. UNVERIFIABLE criteria and
BLOCKED gates are out of scope, and print without `evidence` or `command`,
because the skill never fixes them. PASS and SKIP rows are not findings.

ACCEPTED IS THE LABEL HOOK'S RULE, read from the counts: at least one criterion,
every criterion PASS, at least one gate, and no gate FAIL or BLOCKED. A report
that is not ACCEPTED yet has nothing in scope and nothing BLOCKED, such as one
grading no criteria, stops with `needs-human-check`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TextIO

REPORT_MISSING = "report-missing"
REPORT_UNREADABLE = "report-unreadable"
REPORT_STALE = "report-stale"
BEAD_MISMATCH = "bead-mismatch"
UNCOMMITTED_CHANGES = "uncommitted-changes"
FAILURES_OUTSIDE_CHANGE = "failures-outside-change"
NEEDS_ENVIRONMENT = "needs-environment"
NEEDS_HUMAN_CHECK = "needs-human-check"
FINDING_NOT_FIXED = "finding-not-fixed"
COMMIT_FAILED = "commit-failed"

REASONS = (
    REPORT_MISSING,
    REPORT_UNREADABLE,
    REPORT_STALE,
    BEAD_MISMATCH,
    UNCOMMITTED_CHANGES,
    FAILURES_OUTSIDE_CHANGE,
    NEEDS_ENVIRONMENT,
    NEEDS_HUMAN_CHECK,
    FINDING_NOT_FIXED,
    COMMIT_FAILED,
)

DONE_LINE = "RECONCILE_ACCEPTANCE_DONE"
BLOCKED_LINE = "RECONCILE_ACCEPTANCE_BLOCKED"

EXIT_FINDINGS = 0
EXIT_BLOCKED = 1
EXIT_USAGE = 2
EXIT_NOTHING_TO_FIX = 3

REPORT_VERSION = 2

PASS = "PASS"
FAIL = "FAIL"
UNVERIFIABLE = "UNVERIFIABLE"
BLOCKED = "BLOCKED"
SKIP = "SKIP"
CRITERION_VERDICTS = (PASS, FAIL, UNVERIFIABLE)
GATE_STATUSES = (PASS, FAIL, BLOCKED, SKIP)

COUNT_FIELDS = (
    "criteria_total",
    "criteria_passed",
    "criteria_failed",
    "criteria_unverifiable",
    "gates_total",
    "gates_failed",
    "gates_blocked",
)


@dataclass(frozen=True)
class LoaderInputs:
    report_text: str | None
    head: str
    dirty_paths: frozenset[str]
    bead: str | None = None


@dataclass(frozen=True)
class Blocked:
    reason: str
    detail: str = ""
    exit_code: int = field(default=EXIT_BLOCKED, init=False)

    def emit(self, out: TextIO, err: TextIO) -> None:
        if self.detail:
            print(self.detail, file=err)
        print(f"{BLOCKED_LINE} {self.reason}", file=out)


@dataclass(frozen=True)
class NothingToFix:
    exit_code: int = field(default=EXIT_NOTHING_TO_FIX, init=False)

    def emit(self, out: TextIO, err: TextIO) -> None:
        print("The counts make this report ACCEPTED; nothing to fix.", file=err)


@dataclass(frozen=True)
class Findings:
    in_scope: list[dict[str, Any]]
    out_of_scope: list[dict[str, Any]]
    base: dict[str, str] | None
    bead: str | None
    exit_code: int = field(default=EXIT_FINDINGS, init=False)

    def emit(self, out: TextIO, err: TextIO) -> None:
        document = {
            "in_scope": self.in_scope,
            "out_of_scope": self.out_of_scope,
            "base": self.base,
            "bead": self.bead,
            "scope_known": self.base is not None,
        }
        json.dump(document, out, indent=2)
        out.write("\n")


Outcome = Blocked | NothingToFix | Findings


class UnreadableReport(ValueError):
    """The report file will not open, or is not a version 2 acceptance report."""


def load_findings(inputs: LoaderInputs) -> Outcome:
    """The scoped findings, or the first BLOCKED reason that holds."""
    if inputs.report_text is None:
        return Blocked(REPORT_MISSING, "No acceptance report exists at --report.")
    try:
        report = parse_report(inputs.report_text)
    except UnreadableReport as exc:
        return Blocked(REPORT_UNREADABLE, str(exc))
    if report["head"] != inputs.head:
        return Blocked(
            REPORT_STALE,
            f"The report graded {report['head']}, and HEAD is {inputs.head}.",
        )
    if inputs.bead is not None and inputs.bead != report["bead"]:
        return Blocked(
            BEAD_MISMATCH,
            f"The report graded bead {report['bead']}, not {inputs.bead}.",
        )
    if is_accepted(report):
        return NothingToFix()
    return scope_findings(report, inputs.dirty_paths)


def parse_report(text: str) -> dict[str, Any]:
    try:
        report = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UnreadableReport(f"The report does not parse as JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise UnreadableReport("The report is not a JSON object.")
    version = report.get("version", "absent")
    if version != REPORT_VERSION:
        raise UnreadableReport(
            f"The report's version is {version}, and this loader reads version 2."
        )
    check_top_level(report)
    for criterion in report["criteria"]:
        check_criterion(criterion)
    for gate in report["gates"]:
        check_gate(gate)
    check_counts_match_rows(report)
    return report


def check_top_level(report: dict[str, Any]) -> None:
    require(report, "head", is_text)
    require(report, "bead", is_optional_text)
    require(report, "base", is_optional_base)
    require(report, "changed_files", is_optional_text_list)
    require(report, "criteria", is_object_list)
    require(report, "gates", is_object_list)
    for name in COUNT_FIELDS:
        require(report, name, is_count)
    if (report["base"] is None) != (report["changed_files"] is None):
        raise UnreadableReport("`base` and `changed_files` must both be null, or neither.")


def check_criterion(criterion: dict[str, Any]) -> None:
    require(criterion, "number", is_count)
    require(criterion, "text", is_text)
    require(criterion, "verdict", lambda value: value in CRITERION_VERDICTS)
    require(criterion, "evidence", is_optional_text)
    require(criterion, "command", is_optional_text)


def check_gate(gate: dict[str, Any]) -> None:
    require(gate, "name", is_text)
    require(gate, "status", lambda value: value in GATE_STATUSES)
    require(gate, "command", is_optional_text)
    require(gate, "detail", is_text)


def check_counts_match_rows(report: dict[str, Any]) -> None:
    tallies = {
        "criteria_total": len(report["criteria"]),
        "criteria_passed": len(criteria_with(report, PASS)),
        "criteria_failed": len(criteria_with(report, FAIL)),
        "criteria_unverifiable": len(criteria_with(report, UNVERIFIABLE)),
        "gates_total": len(report["gates"]),
        "gates_failed": len(gates_with(report, FAIL)),
        "gates_blocked": len(gates_with(report, BLOCKED)),
    }
    for name, tally in tallies.items():
        if report[name] != tally:
            raise UnreadableReport(f"`{name}` is {report[name]}, and the rows count {tally}.")


def is_accepted(report: dict[str, Any]) -> bool:
    return (
        report["criteria_total"] > 0
        and report["criteria_passed"] == report["criteria_total"]
        and report["gates_total"] > 0
        and report["gates_failed"] == 0
        and report["gates_blocked"] == 0
    )


def scope_findings(report: dict[str, Any], dirty_paths: frozenset[str]) -> Outcome:
    in_scope = [criterion_entry(c) for c in criteria_with(report, FAIL)]
    in_scope += [gate_entry(g) for g in gates_with(report, FAIL)]

    if in_scope:
        dirty_changed = sorted(dirty_paths.intersection(report["changed_files"] or []))
        if dirty_changed:
            return Blocked(
                UNCOMMITTED_CHANGES,
                "Commit these changed files first: " + ", ".join(dirty_changed),
            )
        return Findings(in_scope, out_of_scope(report), report["base"], report["bead"])

    if gates_with(report, BLOCKED):
        return Blocked(NEEDS_ENVIRONMENT, "Nothing is in scope, and a gate is BLOCKED.")
    return Blocked(NEEDS_HUMAN_CHECK, "Nothing is in scope, and the report is not ACCEPTED.")


def criterion_entry(criterion: dict[str, Any]) -> dict[str, Any]:
    return {
        "criterion": criterion["number"],
        "text": criterion["text"],
        "verdict": criterion["verdict"],
        "evidence": criterion["evidence"],
        "command": criterion["command"],
    }


def gate_entry(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate": gate["name"],
        "status": gate["status"],
        "command": gate["command"],
        "detail": gate["detail"],
    }


def out_of_scope(report: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        {"criterion": c["number"], "text": c["text"], "verdict": c["verdict"]}
        for c in criteria_with(report, UNVERIFIABLE)
    ]
    entries += [
        {"gate": g["name"], "status": g["status"], "detail": g["detail"]}
        for g in gates_with(report, BLOCKED)
    ]
    return entries


def criteria_with(report: dict[str, Any], verdict: str) -> list[dict[str, Any]]:
    return [c for c in report["criteria"] if c["verdict"] == verdict]


def gates_with(report: dict[str, Any], status: str) -> list[dict[str, Any]]:
    return [g for g in report["gates"] if g["status"] == status]


def require(entry: dict[str, Any], name: str, is_valid: Callable[[Any], bool]) -> None:
    if name not in entry:
        raise UnreadableReport(f"The report lacks the version 2 field `{name}`.")
    if not is_valid(entry[name]):
        raise UnreadableReport(f"The field `{name}` holds {entry[name]!r}, which is not valid.")


def is_text(value: Any) -> bool:
    return isinstance(value, str)


def is_optional_text(value: Any) -> bool:
    return value is None or isinstance(value, str)


def is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_object_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, dict) for v in value)


def is_optional_text_list(value: Any) -> bool:
    return value is None or (isinstance(value, list) and all(isinstance(v, str) for v in value))


def is_optional_base(value: Any) -> bool:
    return value is None or (
        isinstance(value, dict) and is_text(value.get("ref")) and is_text(value.get("sha"))
    )


def main(argv: list[str] | None = None, out: TextIO = sys.stdout, err: TextIO = sys.stderr) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", required=True, metavar="PATH")
    parser.add_argument("--head", required=True, metavar="SHA")
    parser.add_argument("--dirty-files", required=True, metavar="PATH")
    parser.add_argument("--bead", metavar="ID")
    args = parser.parse_args(argv)

    head = args.head.strip()
    if not head:
        print("ERROR: --head must name a commit", file=err)
        return EXIT_USAGE
    bead = None if args.bead is None else args.bead.strip()
    if bead == "":
        print("ERROR: --bead, when given, must name a bead", file=err)
        return EXIT_USAGE
    try:
        with open(args.dirty_files, "rb") as handle:
            dirty_raw = handle.read().decode("utf-8", errors="surrogateescape")
    except OSError as exc:
        print(f"ERROR: --dirty-files could not be read: {exc}", file=err)
        return EXIT_USAGE

    try:
        report_text = read_report(args.report)
    except UnreadableReport as exc:
        outcome: Outcome = Blocked(REPORT_UNREADABLE, str(exc))
    else:
        dirty_paths = parse_porcelain_z(dirty_raw)
        outcome = load_findings(LoaderInputs(report_text, head, dirty_paths, bead))
    outcome.emit(out, err)
    return outcome.exit_code


def read_report(path: str) -> str | None:
    """The report's text, or None when no file exists at `path`.

    A file that exists but will not open raises, so it stops as
    `report-unreadable` with its own cause rather than a JSON parse error.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise UnreadableReport(f"The report at {path} could not be read: {exc}") from exc


def parse_porcelain_z(raw: str) -> frozenset[str]:
    """Every path `git status --porcelain=v1 -z` names, both sides of a rename.

    Each record is `XY PATH`, NUL-terminated. A rename or copy puts its original
    path in the next NUL-terminated field, and both paths count as dirty.
    """
    fields = iter(raw.split("\0"))
    paths: set[str] = set()
    for record in fields:
        if len(record) < 4:
            continue
        status, path = record[:2], record[3:]
        paths.add(path)
        if "R" in status or "C" in status:
            paths.add(next(fields, ""))
    paths.discard("")
    return frozenset(paths)


if __name__ == "__main__":
    sys.exit(main())
