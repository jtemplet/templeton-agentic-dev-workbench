#!/usr/bin/env python3
"""Check a version 2 quality-gates report, then split its findings by scope.

This is step 1 of the reconcile-quality-gates skill. It refuses a missing,
stale, or foreign report before the skill edits anything. Those checks are the
same on every run, so a script decides them the same way each time (ADR 0011).

EVERY INPUT IS INJECTED. The skill passes the report path, the current HEAD, the
output of `git status --porcelain=v1 -z`, and the bead id it was given. This
script runs no git and no bd, so its suite needs no repository.

EXIT CODES. 0 prints the findings as JSON. 1 prints the BLOCKED machine line as
the only stdout line, with any detail on stderr. 2 is a usage error. 3 means the
verdict is PASS or NO GATES RAN, so there is nothing to fix.

THE ORDER OF THE REASONS is the plan's reasons table, and the first that holds
wins. All ten tokens are constants here, including the two only the skill can
decide, so one test can check them against SKILL.md.

WHAT IS IN SCOPE. A finding whose gate row is FAIL, and whose `file` is in
`changed_files` or is null. A null `file` stays in scope because the skill
re-runs the gate's command to find the file. When `changed_files` is null, no
base resolved, so every FAIL finding is in scope and `scope_known` is false.
Every other finding prints as out of scope, with only its gate, file, and
problem, because the skill never fixes it.

WHEN NOTHING IS IN SCOPE. A FAIL finding that exists is outside the change, so
the run stops with `failures-outside-change`. Otherwise a BLOCKED gate stops it
with `needs-environment`, and anything else, such as a HANDOFF gate or a FAIL
gate with no finding, stops it with `needs-human-check`.

`uncommitted-changes` covers only the files that in-scope findings name. The
skill applies the same rule to a file it finds by re-running a command.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn, TextIO

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

DONE_LINE = "RECONCILE_QUALITY_GATES_DONE"
BLOCKED_LINE = "RECONCILE_QUALITY_GATES_BLOCKED"

EXIT_FINDINGS = 0
EXIT_BLOCKED = 1
EXIT_USAGE = 2
EXIT_NOTHING_TO_FIX = 3

REPORT_VERSION = 2

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
SKIP = "SKIP"
BLOCKED = "BLOCKED"
HANDOFF = "HANDOFF"
INCOMPLETE = "INCOMPLETE"
NO_GATES_RAN = "NO GATES RAN"
GATE_STATUSES = (PASS, FAIL, WARN, SKIP, BLOCKED, HANDOFF)
VERDICTS = (PASS, FAIL, INCOMPLETE, NO_GATES_RAN)
NOTHING_TO_FIX_VERDICTS = (PASS, NO_GATES_RAN)

HEAD_PATTERN = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")


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
    verdict: str
    exit_code: int = field(default=EXIT_NOTHING_TO_FIX, init=False)

    def emit(self, out: TextIO, err: TextIO) -> None:
        print(f"The verdict is {self.verdict}; nothing to fix.", file=err)


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


class UntrustedReport(ValueError):
    """The report fails one of reasons 1 to 4, so nothing in it can be used."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason


class UsageError(ValueError):
    """An argument is malformed or unreadable."""


def load_findings(inputs: LoaderInputs) -> Outcome:
    """The scoped findings, or the first BLOCKED reason that holds."""
    try:
        report = trusted_report(inputs)
    except UntrustedReport as exc:
        return Blocked(exc.reason, str(exc))
    if report["verdict"] in NOTHING_TO_FIX_VERDICTS:
        return NothingToFix(report["verdict"])
    return scope_findings(report, inputs.dirty_paths)


def trusted_report(inputs: LoaderInputs) -> dict[str, Any]:
    if inputs.report_text is None:
        raise UntrustedReport(REPORT_MISSING, "No quality-gates report exists at --report.")
    report = parse_report(inputs.report_text)
    check_checked_commit(report, inputs.head)
    check_checked_bead(report, inputs.bead)
    return report


def check_checked_commit(report: dict[str, Any], head: str) -> None:
    if report["head"] != head:
        raise UntrustedReport(
            REPORT_STALE, f"The report checked {report['head']}, and HEAD is {head}."
        )


def check_checked_bead(report: dict[str, Any], bead: str | None) -> None:
    if bead is not None and bead != report["bead"]:
        raise UntrustedReport(
            BEAD_MISMATCH, f"The report checked bead {report['bead']}, not {bead}."
        )


def parse_report(text: str) -> dict[str, Any]:
    report = decoded(text)
    check_version(report)
    check_entry(report, TOP_LEVEL_RULES)
    check_base_pairing(report)
    check_gates(report["gates"])
    check_findings(report)
    return report


def decoded(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise unreadable(f"The report does not parse as JSON: {exc}") from exc


def check_version(report: Any) -> None:
    if not isinstance(report, dict):
        raise unreadable("The report is not a JSON object.")
    version = report.get("version", "absent")
    if version != REPORT_VERSION:
        raise unreadable(f"The report's version is {version}, and this loader reads version 2.")


def check_base_pairing(report: dict[str, Any]) -> None:
    if (report["base"] is None) != (report["changed_files"] is None):
        raise unreadable("`base` and `changed_files` must both be null, or neither.")


def check_gates(gates: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for gate in gates:
        check_entry(gate, GATE_RULES)
        if gate["name"] in seen:
            raise unreadable(f"The gate name `{gate['name']}` repeats in `gates`.")
        seen.add(gate["name"])


def check_findings(report: dict[str, Any]) -> None:
    names = {gate["name"] for gate in report["gates"]}
    for finding in report["findings"]:
        check_entry(finding, FINDING_RULES)
        if finding["gate"] not in names:
            raise unreadable(f"A finding names the gate `{finding['gate']}`, and no row has it.")


def check_entry(entry: dict[str, Any], rules: dict[str, Callable[[Any], bool]]) -> None:
    for name, is_valid in rules.items():
        if name not in entry:
            raise unreadable(f"The report lacks the version 2 field `{name}`.")
        if not is_valid(entry[name]):
            raise unreadable(f"The field `{name}` holds {entry[name]!r}, which is not valid.")


def unreadable(detail: str) -> UntrustedReport:
    return UntrustedReport(REPORT_UNREADABLE, detail)


def scope_findings(report: dict[str, Any], dirty_paths: frozenset[str]) -> Outcome:
    in_scope, out_of_scope = split_by_scope(report)
    if not in_scope:
        return nothing_in_scope(report)
    named_files = {entry["file"] for entry in in_scope if entry["file"] is not None}
    dirty = sorted(dirty_paths & named_files)
    if dirty:
        return Blocked(UNCOMMITTED_CHANGES, "Commit these files first: " + ", ".join(dirty))
    return Findings(in_scope, out_of_scope, report["base"], report["bead"])


def split_by_scope(report: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gates = {gate["name"]: gate for gate in report["gates"]}
    changed_files = report["changed_files"]
    findings = report["findings"]
    in_scope = [
        {**finding, "command": gates[finding["gate"]]["command"]}
        for finding in findings
        if is_in_scope(finding, gates[finding["gate"]], changed_files)
    ]
    out_of_scope = [
        {key: finding[key] for key in ("gate", "file", "problem")}
        for finding in findings
        if not is_in_scope(finding, gates[finding["gate"]], changed_files)
    ]
    return in_scope, out_of_scope


def is_in_scope(
    finding: dict[str, Any], gate: dict[str, Any], changed_files: list[str] | None
) -> bool:
    return gate["status"] == FAIL and in_changed_set(finding["file"], changed_files)


def in_changed_set(path: str | None, changed_files: list[str] | None) -> bool:
    return path is None or changed_files is None or path in changed_files


def nothing_in_scope(report: dict[str, Any]) -> Blocked:
    failing = {gate["name"] for gate in report["gates"] if gate["status"] == FAIL}
    if any(finding["gate"] in failing for finding in report["findings"]):
        return Blocked(
            FAILURES_OUTSIDE_CHANGE, "Every FAIL finding is in a file outside `changed_files`."
        )
    if any(gate["status"] == BLOCKED for gate in report["gates"]):
        return Blocked(NEEDS_ENVIRONMENT, "Nothing is in scope, and a gate is BLOCKED.")
    verdict = report["verdict"]
    return Blocked(NEEDS_HUMAN_CHECK, f"Nothing is in scope, and the verdict is {verdict}.")


def is_text(value: Any) -> bool:
    return isinstance(value, str)


def is_optional_text(value: Any) -> bool:
    return value is None or isinstance(value, str)


def is_object_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, dict) for v in value)


def is_optional_text_list(value: Any) -> bool:
    return value is None or (isinstance(value, list) and all(isinstance(v, str) for v in value))


def is_optional_base(value: Any) -> bool:
    return value is None or (
        isinstance(value, dict) and is_text(value.get("ref")) and is_text(value.get("sha"))
    )


def is_optional_line(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 1)


TOP_LEVEL_RULES: dict[str, Callable[[Any], bool]] = {
    "head": is_text,
    "bead": is_optional_text,
    "base": is_optional_base,
    "changed_files": is_optional_text_list,
    "verdict": lambda value: value in VERDICTS,
    "gates": is_object_list,
    "findings": is_object_list,
}
GATE_RULES: dict[str, Callable[[Any], bool]] = {
    "name": is_text,
    "status": lambda value: value in GATE_STATUSES,
    "command": is_optional_text,
}
FINDING_RULES: dict[str, Callable[[Any], bool]] = {
    "gate": is_text,
    "file": is_optional_text,
    "line": is_optional_line,
    "problem": is_text,
    "evidence": is_optional_text,
}


def main(argv: list[str] | None = None, out: TextIO = sys.stdout, err: TextIO = sys.stderr) -> int:
    try:
        args = parse_arguments(argv)
    except UsageError as exc:
        print(f"ERROR: {exc}", file=err)
        return EXIT_USAGE
    outcome = outcome_for(args)
    outcome.emit(out, err)
    return outcome.exit_code


def outcome_for(args: argparse.Namespace) -> Outcome:
    try:
        report_text = read_report(args.report)
    except UntrustedReport as exc:
        return Blocked(exc.reason, str(exc))
    return load_findings(LoaderInputs(report_text, args.head, args.dirty_paths, args.bead))


class RaisingArgumentParser(argparse.ArgumentParser):
    """An argument parser that raises rather than exits, so main() owns every exit code."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = RaisingArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", required=True, type=report_path, metavar="PATH")
    parser.add_argument("--head", required=True, type=commit_sha, metavar="SHA")
    parser.add_argument(
        "--dirty-files", dest="dirty_paths", required=True, type=dirty_paths_in, metavar="PATH"
    )
    parser.add_argument("--bead", type=bead_id, metavar="ID")
    return parser.parse_args(argv)


def report_path(value: str) -> Path:
    path = Path(value)
    if not path.name:
        raise argparse.ArgumentTypeError(f"{value!r} does not name a file")
    return path


def commit_sha(value: str) -> str:
    sha = value.strip()
    if not HEAD_PATTERN.fullmatch(sha):
        raise argparse.ArgumentTypeError(f"{value!r} is not a 40- or 64-character hex commit id")
    return sha


def bead_id(value: str) -> str:
    bead = value.strip()
    if not bead:
        raise argparse.ArgumentTypeError("a given --bead must name a bead")
    return bead


def dirty_paths_in(value: str) -> frozenset[str]:
    try:
        raw = Path(value).read_bytes()
    except OSError as exc:
        raise argparse.ArgumentTypeError(f"could not be read: {exc}") from exc
    return parse_porcelain_z(raw.decode("utf-8", errors="surrogateescape"))


def read_report(path: Path) -> str | None:
    """The report's text, or None when no file exists at `path`.

    A file that exists but will not open raises, so it stops as
    `report-unreadable` with its own cause rather than a JSON parse error.
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise unreadable(f"The report at {path} could not be read: {exc}") from exc


def parse_porcelain_z(raw: str) -> frozenset[str]:
    """Every path `git status --porcelain=v1 -z` names, both sides of a rename.

    Each record is `XY PATH`, NUL-terminated. A rename or copy puts its original
    path in the next NUL-terminated field, and both paths count as dirty.
    """
    fields = iter(raw.split("\0"))
    paths: set[str] = set()
    for record in fields:
        paths.add(record[3:])
        if "R" in record[:2] or "C" in record[:2]:
            paths.add(next(fields, ""))
    return frozenset(paths - {""})


if __name__ == "__main__":
    sys.exit(main())
