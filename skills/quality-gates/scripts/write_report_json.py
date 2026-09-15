#!/usr/bin/env python3
"""Validate the quality-gates report, then write it at version 2.

This is the write in the quality-gates skill's JSON Artifact step. The model
used to build the object in inline python3 on every run, and the pre-push hook
reads a drifted file the same way it reads a missing one. The reconcile skills
now read findings, `bead`, `base`, and `changed_files` from this file (ADR
0011), so a script writes it and refuses a bad shape the same way every time.

EVERY VALUE IS INJECTED. The caller passes `--out`, `--head`, `--dirty`,
`--timestamp`, and, when a base resolved, `--changed-files`. The model-written
fields arrive as one JSON object on stdin: `scope`, `gate_source`, `routing`,
`bead`, `base`, `verdict`, `gates`, and `findings`. This script runs no git and
no bd, so its suite needs no repository.

EXIT CODES. 0 prints the written path. 1 is a refusal: stderr names the field
and the problem, and nothing is written. 2 is a usage error: an argument that is
malformed or unreadable, or an `--out` that cannot be written. Every problem
with the stdin object is a refusal, including stdin that does not parse.

THE ORDER OF THE CHECKS. The shape of every field first, then `base` against
`--changed-files`, then the verdict, then the gate each finding names. The first
check that fails is the one reported. A field the report does not define is
refused at every level, so a `head` or `version` on stdin cannot compete with
the argument that sets it.

THE VERDICT IS CHECKED, NOT TRUSTED. It must equal what SKILL.md's Verdict Rules
give for the gate statuses, applied in order: FAIL when any gate is FAIL or
BLOCKED, INCOMPLETE when any is HANDOFF, NO GATES RAN when none is PASS, WARN,
or FAIL, and PASS otherwise.

THE EVIDENCE CAP. Each finding's `evidence` keeps at most 20 lines and 2,000
characters, then a final `[trimmed: <n> more lines]` line, where n counts the
lines not kept whole. Only whole leading lines are kept, with one exception:
when the first line alone is longer than 2,000 characters, its first 2,000
characters are kept, and n counts every line, that one included.

THE WRITE IS ATOMIC. The whole object is validated and built before anything
touches the disk. It goes to a temporary file beside `--out` and is then renamed
onto it, so the pre-push hook never reads a half-written report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn, TextIO

EXIT_WRITTEN = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2

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
SCOPES = ("changed", "all")

MAX_EVIDENCE_LINES = 20
MAX_EVIDENCE_CHARS = 2000
MAX_SHOWN_VALUE_CHARS = 80

HEAD_PATTERN = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class Rule:
    """What a field must hold, and the words a refusal uses to say so."""

    holds: Callable[[Any], bool]
    expected: str


TEXT = Rule(lambda value: isinstance(value, str), "a string")
NON_EMPTY_TEXT = Rule(lambda value: isinstance(value, str) and value != "", "a non-empty string")
OPTIONAL_TEXT = Rule(lambda value: value is None or isinstance(value, str), "a string or null")
OBJECT = Rule(lambda value: isinstance(value, dict), "an object")
OPTIONAL_OBJECT = Rule(lambda value: value is None or isinstance(value, dict), "an object or null")
LIST = Rule(lambda value: isinstance(value, list), "a list")
COUNT = Rule(lambda value: is_integer(value) and value >= 0, "a non-negative integer")
OPTIONAL_LINE = Rule(
    lambda value: value is None or (is_integer(value) and value >= 1),
    "an integer of 1 or more, or null",
)

TOP_LEVEL_RULES = {
    "scope": Rule(lambda value: value in SCOPES, "`changed` or `all`"),
    "gate_source": NON_EMPTY_TEXT,
    "routing": OBJECT,
    "bead": OPTIONAL_TEXT,
    "base": OPTIONAL_OBJECT,
    "verdict": Rule(lambda value: value in VERDICTS, "one of " + ", ".join(VERDICTS)),
    "gates": LIST,
    "findings": LIST,
}
BASE_RULES = {"ref": TEXT, "sha": TEXT}
ROUTE_RULES = {"method": TEXT, "owner": OPTIONAL_TEXT, "files": COUNT, "endpoints": COUNT}
GATE_RULES = {
    "name": NON_EMPTY_TEXT,
    "status": Rule(lambda value: value in GATE_STATUSES, "one of " + ", ".join(GATE_STATUSES)),
    "command": OPTIONAL_TEXT,
    "detail": TEXT,
}
FINDING_RULES = {
    "gate": TEXT,
    "file": OPTIONAL_TEXT,
    "line": OPTIONAL_LINE,
    "problem": NON_EMPTY_TEXT,
    "evidence": OPTIONAL_TEXT,
}


@dataclass(frozen=True)
class RunFacts:
    """The values the caller measured and passed as arguments."""

    head: str
    dirty: bool
    timestamp: str
    changed_files: tuple[str, ...] | None


@dataclass(frozen=True)
class Derivation:
    """The verdict the Verdict Rules give, and what decided it."""

    verdict: str
    reason: str


class InvalidReport(ValueError):
    """The stdin object cannot be written as a version 2 report."""


class UsageError(ValueError):
    """An argument is malformed, unreadable, or names a place nothing can be written."""


def build_report(fields: Any, facts: RunFacts) -> dict[str, Any]:
    """The version 2 report, or InvalidReport naming the first check that fails."""
    check_shape(fields)
    check_base_pairing(fields["base"], facts.changed_files)
    check_verdict(fields["verdict"], fields["gates"])
    check_finding_gates(fields["findings"], fields["gates"])
    return {
        "version": REPORT_VERSION,
        "head": facts.head,
        "dirty": facts.dirty,
        "timestamp": facts.timestamp,
        "scope": fields["scope"],
        "gate_source": fields["gate_source"],
        "routing": fields["routing"],
        "bead": fields["bead"],
        "base": fields["base"],
        "changed_files": None if facts.changed_files is None else list(facts.changed_files),
        "verdict": fields["verdict"],
        "gates": fields["gates"],
        "findings": [capped_finding(finding) for finding in fields["findings"]],
    }


def check_shape(fields: Any) -> None:
    check_entry(fields, TOP_LEVEL_RULES, "stdin")
    if fields["base"] is not None:
        check_entry(fields["base"], BASE_RULES, "`base`")
    for surface, route in fields["routing"].items():
        check_entry(route, ROUTE_RULES, f"`routing.{surface}`")
    check_gates(fields["gates"])
    check_findings(fields["findings"])


def check_gates(gates: list[Any]) -> None:
    seen: set[str] = set()
    for index, gate in enumerate(gates):
        where = f"`gates[{index}]`"
        check_entry(gate, GATE_RULES, where)
        if gate["name"] in seen:
            raise InvalidReport(
                f"{where} repeats the gate name `{gate['name']}`, "
                "and a finding must name exactly one row."
            )
        seen.add(gate["name"])


def check_findings(findings: list[Any]) -> None:
    for index, finding in enumerate(findings):
        where = f"`findings[{index}]`"
        check_entry(finding, FINDING_RULES, where)
        if finding["line"] is not None and finding["file"] is None:
            raise InvalidReport(f"{where} names line {finding['line']} and no `file`.")


def check_entry(entry: Any, rules: dict[str, Rule], where: str) -> None:
    """Refuse a non-object, a missing field, an unexpected field, or a bad value."""
    if not isinstance(entry, dict):
        raise InvalidReport(f"{where} holds {shown(entry)}, and it must be an object.")
    for name in rules:
        if name not in entry:
            raise InvalidReport(f"{where} lacks the field `{name}`.")
    for name in entry:
        if name not in rules:
            raise InvalidReport(f"{where} holds the unexpected field `{name}`.")
    for name, rule in rules.items():
        if not rule.holds(entry[name]):
            raise InvalidReport(
                f"{where} field `{name}` holds {shown(entry[name])}, "
                f"and it must be {rule.expected}."
            )


def check_base_pairing(base: dict[str, str] | None, changed_files: tuple[str, ...] | None) -> None:
    if base is None and changed_files is not None:
        raise InvalidReport("`base` is missing: --changed-files was given, and `base` is null.")
    if base is not None and changed_files is None:
        raise InvalidReport(
            "--changed-files is missing: `base` names a ref, and --changed-files was not given."
        )


def check_verdict(verdict: str, gates: list[dict[str, Any]]) -> None:
    derived = derive_verdict(gates)
    if verdict != derived.verdict:
        raise InvalidReport(
            f"The verdict is {verdict}, and the Verdict Rules give "
            f"{derived.verdict}: {derived.reason}."
        )


def derive_verdict(gates: list[dict[str, Any]]) -> Derivation:
    """Apply the Verdict Rules in order; the first rule that matches decides."""
    failing = gates_with(gates, FAIL, BLOCKED)
    if failing:
        return Derivation(FAIL, named_gates(failing))
    handed_off = gates_with(gates, HANDOFF)
    if handed_off:
        return Derivation(INCOMPLETE, named_gates(handed_off))
    if not gates_with(gates, PASS, WARN, FAIL):
        return Derivation(NO_GATES_RAN, "no gate reached PASS, WARN, or FAIL")
    return Derivation(PASS, "at least one gate ran, and none of them failed")


def check_finding_gates(findings: list[dict[str, Any]], gates: list[dict[str, Any]]) -> None:
    names = {gate["name"] for gate in gates}
    for index, finding in enumerate(findings):
        if finding["gate"] not in names:
            raise InvalidReport(
                f"`findings[{index}]` names the gate `{finding['gate']}`, "
                "and no row in `gates` has that name."
            )


def capped_finding(finding: dict[str, Any]) -> dict[str, Any]:
    evidence = finding["evidence"]
    return {**finding, "evidence": None if evidence is None else cap_evidence(evidence)}


def cap_evidence(text: str) -> str:
    """`text` unchanged when it fits the cap, else its leading lines and a trimmed line.

    Whole leading lines are kept while they number at most 20 and join to at most
    2,000 characters. When not even the first line fits, its first 2,000
    characters are kept instead, and n counts every line, because none was kept
    whole. When every line fits once `\\r\\n` endings become `\\n`, the joined lines
    return with no trimmed line, since nothing was removed.
    """
    lines = text.splitlines()
    if len(lines) <= MAX_EVIDENCE_LINES and len(text) <= MAX_EVIDENCE_CHARS:
        return text
    kept = leading_lines_that_fit(lines)
    if len(kept) == len(lines):
        return "\n".join(kept)
    body = "\n".join(kept) if kept else lines[0][:MAX_EVIDENCE_CHARS]
    return f"{body}\n[trimmed: {len(lines) - len(kept)} more lines]"


def leading_lines_that_fit(lines: list[str]) -> list[str]:
    kept: list[str] = []
    for line in lines[:MAX_EVIDENCE_LINES]:
        if len("\n".join([*kept, line])) > MAX_EVIDENCE_CHARS:
            break
        kept.append(line)
    return kept


def gates_with(gates: list[dict[str, Any]], *statuses: str) -> list[dict[str, Any]]:
    return [gate for gate in gates if gate["status"] in statuses]


def named_gates(gates: list[dict[str, Any]]) -> str:
    return ", ".join(f"gate `{gate['name']}` is {gate['status']}" for gate in gates)


def is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def shown(value: Any) -> str:
    text = repr(value)
    if len(text) <= MAX_SHOWN_VALUE_CHARS:
        return text
    return text[: MAX_SHOWN_VALUE_CHARS - 3] + "..."


def main(
    argv: list[str] | None = None,
    stdin: TextIO = sys.stdin,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
) -> int:
    try:
        args = parse_arguments(argv)
        changed_files = read_changed_files(args.changed_files)
    except UsageError as exc:
        print(f"ERROR: {exc}", file=err)
        return EXIT_USAGE

    facts = RunFacts(args.head, args.dirty, args.timestamp, changed_files)
    try:
        report = build_report(read_fields(stdin), facts)
    except InvalidReport as exc:
        print(f"REFUSED, nothing written: {exc}", file=err)
        return EXIT_REFUSED

    try:
        write_atomically(args.out, report)
    except OSError as exc:
        print(f"ERROR: --out could not be written: {exc}", file=err)
        return EXIT_USAGE
    print(args.out, file=out)
    return EXIT_WRITTEN


class RaisingArgumentParser(argparse.ArgumentParser):
    """An argument parser that raises rather than exits, so main() owns every exit code."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = RaisingArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=output_path, metavar="PATH")
    parser.add_argument("--head", required=True, type=commit_sha, metavar="SHA")
    parser.add_argument("--dirty", required=True, type=true_or_false, metavar="true|false")
    parser.add_argument("--timestamp", required=True, type=utc_timestamp, metavar="UTC")
    parser.add_argument("--changed-files", type=Path, metavar="PATH")
    return parser.parse_args(argv)


def output_path(value: str) -> Path:
    path = Path(value)
    if not path.name:
        raise argparse.ArgumentTypeError(f"{value!r} does not name a file")
    if not path.parent.is_dir():
        raise argparse.ArgumentTypeError(f"the directory {path.parent} does not exist")
    return path


def commit_sha(value: str) -> str:
    sha = value.strip()
    if not HEAD_PATTERN.fullmatch(sha):
        raise argparse.ArgumentTypeError(f"{value!r} is not a 40- or 64-character hex commit id")
    return sha


def true_or_false(value: str) -> bool:
    if value not in ("true", "false"):
        raise argparse.ArgumentTypeError(f"{value!r} is not `true` or `false`")
    return value == "true"


def utc_timestamp(value: str) -> str:
    """`value` when it is exactly YYYY-MM-DDTHH:MM:SSZ.

    The round trip refuses what strptime alone accepts, such as an unpadded month.
    """
    try:
        parsed = datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not {TIMESTAMP_FORMAT}") from exc
    if parsed.strftime(TIMESTAMP_FORMAT) != value:
        raise argparse.ArgumentTypeError(f"{value!r} is not zero-padded {TIMESTAMP_FORMAT}")
    return value


def read_changed_files(path: Path | None) -> tuple[str, ...] | None:
    """The paths `changed_set.py` printed, one per line, with blank lines skipped."""
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError(f"--changed-files could not be read: {exc}") from exc
    return tuple(line for line in text.split("\n") if line.strip())


def read_fields(stdin: TextIO) -> Any:
    try:
        return json.loads(stdin.read())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidReport(f"stdin does not parse as JSON: {exc}") from exc


def write_atomically(path: Path, report: dict[str, Any]) -> None:
    """Write beside `path`, then rename onto it, so no reader sees a partial file."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    sys.exit(main())
