#!/usr/bin/env python3
"""Validate the acceptance report, then write it at version 2.

This is the write in the verify-acceptance skill's Verdict Artifact step. The
model used to build the object in inline python3 on every run, and version 1
carried a bead id and seven counts with no criterion text. `reconcile-acceptance`
needs each criterion's text, verdict, evidence, and command (ADR 0011), and the
label hook needs the counts to agree with those criteria, so a script writes the
file and refuses a bad shape the same way every time.

EVERY VALUE IS INJECTED. The caller passes `--out`, `--head`, and, when a base
resolved, `--changed-files`. The model-written fields arrive as one JSON object
on stdin: `bead`, `base`, the seven counts, `criteria`, and `gates`. This script
runs no git and no bd, so its suite needs no repository.

EXIT CODES. 0 prints the written path. 1 is a refusal: stderr names the field
and the problem, and nothing is written. 2 is a usage error: an argument that is
malformed or unreadable, or an `--out` that cannot be written. Every problem
with the stdin object is a refusal, including stdin that does not parse.

THE ORDER OF THE CHECKS. The `verdict` field first, then the shape of every
field, then `base` against `--changed-files`, then the seven counts against the
rows. The first check that fails is the one reported. A field the report does
not define is refused at every level, so a `version`, `head`, or `changed_files`
on stdin cannot compete with the argument that sets it.

THERE IS NO VERDICT FIELD, AND ITS ABSENCE IS CHECKED FIRST. SKILL.md gives the
reason: a run that wrote "verdict": "ACCEPTED" beside a failing criterion would
be labeling work it had just graded as failed, which is the self-grading failure
that skill exists to prevent. The label hook reads the counts and decides.
Refusing a `verdict` as one more unexpected field would bury that, so it gets a
check of its own and a message that says why.

THE COUNTS ARE CHECKED, NOT TRUSTED. Each of the seven must equal the tally its
rows give, computed the way `load_findings.py` computes it. A count that
disagrees is how a report comes to read ACCEPTED over a criterion graded FAIL.

THE EVIDENCE CAP. Each criterion's `evidence` keeps at most 20 lines and 2,000
characters, then a final `[trimmed: <n> more lines]` line, where n counts the
lines not kept whole. Only whole leading lines are kept, with one exception:
when the first line alone is longer than 2,000 characters, its first 2,000
characters are kept, and n counts every line, that one included. A gate's
`detail` is left alone, because SKILL.md already requires it to be a one-line
result such as "Tests: 218 passed, 0 failed".

THE WRITE IS ATOMIC. The whole object is validated and built before anything
touches the disk. It goes to a temporary file beside `--out` and is then renamed
onto it, so no reader ever sees a half-written report.

WHY THIS IS NOT write_report_json.py. The two writers share the cap and the
rules-dict machinery and little else: different fields, a different set of gate
statuses (no WARN and no HANDOFF here), a `criteria` array in place of
`findings`, and seven counts in place of a verdict. ADR 0011 settled the same
question for the two loaders: "A shared loader would need a mode argument or a
third file, and house rule 1 waits for a third copy." Do not merge them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, TextIO

EXIT_WRITTEN = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2

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

MAX_EVIDENCE_LINES = 20
MAX_EVIDENCE_CHARS = 2000
MAX_SHOWN_VALUE_CHARS = 80

HEAD_PATTERN = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")


@dataclass(frozen=True)
class Rule:
    """What a field must hold, and the words a refusal uses to say so."""

    holds: Callable[[Any], bool]
    expected: str


TEXT = Rule(lambda value: isinstance(value, str), "a string")
NON_EMPTY_TEXT = Rule(lambda value: isinstance(value, str) and value != "", "a non-empty string")
OPTIONAL_TEXT = Rule(lambda value: value is None or isinstance(value, str), "a string or null")
OPTIONAL_OBJECT = Rule(lambda value: value is None or isinstance(value, dict), "an object or null")
LIST = Rule(lambda value: isinstance(value, list), "a list")
COUNT = Rule(lambda value: is_integer(value) and value >= 0, "a non-negative integer")
CRITERION_NUMBER = Rule(
    lambda value: is_integer(value) and value >= 1,
    "an integer of 1 or more",
)
# `bead` is null when the run graded no bead, and a bead id otherwise. The empty
# string is neither, and `load_findings.py` would compare it against the id the
# caller asked for.
OPTIONAL_BEAD = Rule(
    lambda value: value is None or (isinstance(value, str) and value != ""),
    "a non-empty string or null",
)

TOP_LEVEL_RULES = {
    "bead": OPTIONAL_BEAD,
    "base": OPTIONAL_OBJECT,
    **dict.fromkeys(COUNT_FIELDS, COUNT),
    "criteria": LIST,
    "gates": LIST,
}
BASE_RULES = {"ref": TEXT, "sha": TEXT}
CRITERION_RULES = {
    "number": CRITERION_NUMBER,
    "text": TEXT,
    "verdict": Rule(
        lambda value: value in CRITERION_VERDICTS,
        "one of " + ", ".join(CRITERION_VERDICTS),
    ),
    "evidence": OPTIONAL_TEXT,
    "command": OPTIONAL_TEXT,
}
GATE_RULES = {
    "name": NON_EMPTY_TEXT,
    "status": Rule(lambda value: value in GATE_STATUSES, "one of " + ", ".join(GATE_STATUSES)),
    "command": OPTIONAL_TEXT,
    "detail": TEXT,
}


@dataclass(frozen=True)
class RunFacts:
    """The values the caller measured and passed as arguments."""

    head: str
    changed_files: tuple[str, ...] | None


class InvalidReport(ValueError):
    """The stdin object cannot be written as a version 2 acceptance report."""


class UsageError(ValueError):
    """An argument is malformed, unreadable, or names a place nothing can be written."""


def build_report(fields: Any, facts: RunFacts) -> dict[str, Any]:
    """The version 2 report, or InvalidReport naming the first check that fails."""
    check_no_verdict(fields)
    check_shape(fields)
    check_base_pairing(fields["base"], facts.changed_files)
    check_counts(fields)
    return {
        "version": REPORT_VERSION,
        "head": facts.head,
        "bead": fields["bead"],
        "base": fields["base"],
        "changed_files": None if facts.changed_files is None else list(facts.changed_files),
        **{name: fields[name] for name in COUNT_FIELDS},
        "criteria": [capped_criterion(criterion) for criterion in fields["criteria"]],
        "gates": fields["gates"],
    }


def check_no_verdict(fields: Any) -> None:
    """Refuse a top-level `verdict` before anything else, and say why it is absent.

    A criterion keeps its own `verdict`, which is the row this run graded. The
    top-level one would be the conclusion those rows add up to, and that is the
    label hook's to draw from the counts.
    """
    if isinstance(fields, dict) and "verdict" in fields:
        raise InvalidReport(
            "stdin holds a `verdict` field, and this report has none by design: "
            "a run that recorded ACCEPTED beside a criterion it graded FAIL would be "
            "labeling its own work. The counts decide, and the label hook reads them."
        )


def check_shape(fields: Any) -> None:
    check_entry(fields, TOP_LEVEL_RULES, "stdin")
    if fields["base"] is not None:
        check_entry(fields["base"], BASE_RULES, "`base`")
    check_criteria(fields["criteria"])
    check_gates(fields["gates"])


def check_criteria(criteria: list[Any]) -> None:
    seen: set[int] = set()
    for index, criterion in enumerate(criteria):
        where = f"`criteria[{index}]`"
        check_entry(criterion, CRITERION_RULES, where)
        if criterion["number"] in seen:
            raise InvalidReport(
                f"{where} repeats the criterion number `{criterion['number']}`, "
                "and a finding must name exactly one row."
            )
        seen.add(criterion["number"])


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


def check_entry(entry: Any, rules: dict[str, Rule], where: str) -> None:
    """Refuse a non-object, a missing field, an unexpected field, or a bad value."""
    if not isinstance(entry, dict):
        raise InvalidReport(f"{where} holds {shown(entry)}, and it must be an object.")
    check_field_names(entry, rules, where)
    check_field_values(entry, rules, where)


def check_field_names(entry: dict[str, Any], rules: dict[str, Rule], where: str) -> None:
    for name in rules:
        if name not in entry:
            raise InvalidReport(f"{where} lacks the field `{name}`.")
    for name in entry:
        if name not in rules:
            raise InvalidReport(f"{where} holds the unexpected field `{name}`.")


def check_field_values(entry: dict[str, Any], rules: dict[str, Rule], where: str) -> None:
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


def check_counts(fields: dict[str, Any]) -> None:
    """Refuse a count the rows do not give, naming the count, the value, and the tally."""
    for name, tally in tallies_of(fields).items():
        if fields[name] != tally:
            raise InvalidReport(f"`{name}` is {fields[name]}, and the rows count {tally}.")


def tallies_of(fields: dict[str, Any]) -> dict[str, int]:
    """What each of the seven counts must be, as `load_findings.py` computes it."""
    return {
        "criteria_total": len(fields["criteria"]),
        "criteria_passed": len(criteria_with(fields, PASS)),
        "criteria_failed": len(criteria_with(fields, FAIL)),
        "criteria_unverifiable": len(criteria_with(fields, UNVERIFIABLE)),
        "gates_total": len(fields["gates"]),
        "gates_failed": len(gates_with(fields, FAIL)),
        "gates_blocked": len(gates_with(fields, BLOCKED)),
    }


def criteria_with(fields: dict[str, Any], verdict: str) -> list[dict[str, Any]]:
    return [row for row in fields["criteria"] if row["verdict"] == verdict]


def gates_with(fields: dict[str, Any], status: str) -> list[dict[str, Any]]:
    return [row for row in fields["gates"] if row["status"] == status]


def capped_criterion(criterion: dict[str, Any]) -> dict[str, Any]:
    evidence = criterion["evidence"]
    return {**criterion, "evidence": None if evidence is None else cap_evidence(evidence)}


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
        written = write_report(argv, stdin)
    except UsageError as exc:
        print(f"ERROR: {exc}", file=err)
        return EXIT_USAGE
    except InvalidReport as exc:
        print(f"REFUSED, nothing written: {exc}", file=err)
        return EXIT_REFUSED
    print(written, file=out)
    return EXIT_WRITTEN


def write_report(argv: list[str] | None, stdin: TextIO) -> Path:
    """The path written, with every argument read before stdin is.

    The arguments come first so that a malformed one exits 2 rather than hiding
    behind whatever the stdin object also got wrong.
    """
    args = parse_arguments(argv)
    facts = RunFacts(args.head, read_changed_files(args.changed_files))
    report = build_report(read_fields(stdin), facts)
    write_to(args.out, report)
    return args.out


class RaisingArgumentParser(argparse.ArgumentParser):
    """An argument parser that raises rather than exits, so main() owns every exit code."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = RaisingArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=output_path, metavar="PATH")
    parser.add_argument("--head", required=True, type=commit_sha, metavar="SHA")
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


def write_to(path: Path, report: dict[str, Any]) -> None:
    """An unwritable `--out` is the caller's mistake, not a bad report, so it exits 2."""
    try:
        write_atomically(path, report)
    except OSError as exc:
        raise UsageError(f"--out could not be written: {exc}") from exc


def write_atomically(path: Path, report: dict[str, Any]) -> None:
    """Write beside `path`, then rename onto it, so no reader sees a partial file."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        dump_json(temporary, report)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def dump_json(path: Path, report: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    sys.exit(main())
