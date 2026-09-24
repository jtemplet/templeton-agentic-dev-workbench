#!/usr/bin/env python3
"""Turn one recorded ship result into the report and the machine line.

The ship skill asked the model to write the report: to "capture the real
counts", "print failing output trimmed to the failing lines", and shorten a long
title "and keep the id". Each of those is a judgment a model makes differently
on every run, and a count it could not find is a count it is tempted to invent.
Here each is a rule.

COUNTS COME FROM A KNOWN PARSER OR NOT AT ALL. Each parser below recognizes one
runner's summary line exactly. The first that matches the output supplies the
counts; when none matches, the report says the counts are unavailable. A number
is never estimated from output no parser understood.

A FAILURE IS AN EXCERPT, AND THE LOG KEEPS THE REST. The report carries the
last lines of a failed check's output, bounded in lines and in characters, and
names the log that holds all of it. A model caller then reads a fixed amount,
however much the check printed.

THE MACHINE LINE IS LAST, ALWAYS. `render` builds every line from the one
result, and puts the machine line after all of them, because `publish-plugin`
reads the last line and nothing else.

A SHORTENED SUBJECT KEEPS ITS BEAD ID. `commit_subject` cuts the title at a word
boundary and marks the cut, so the id at the end survives any title length.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

EXCERPT_MAX_LINES = 40
EXCERPT_MAX_CHARACTERS = 4000
SUBJECT_MAX_CHARACTERS = 72
COUNTS_UNAVAILABLE = "counts unavailable"


@dataclass(frozen=True)
class Counts:
    passed: int
    failed: int

    def describe(self) -> str:
        return f"{self.passed} passed, {self.failed} failed"


@dataclass(frozen=True)
class CheckReport:
    name: str
    status: str
    log: Path
    counts: Counts | None
    excerpt: str | None


@dataclass(frozen=True)
class ShipResult:
    """Everything the report says, recorded once; `machine_line` is its last line."""

    bead_id: str | None
    checks: tuple[CheckReport, ...]
    machine_line: str


def report_check(name: str, status: str, log: Path) -> CheckReport:
    output = read_log(log)
    excerpt = None if status == "passed" else failure_excerpt(output, log)
    return CheckReport(name, status, log, parse_counts(output), excerpt)


def render(result: ShipResult) -> list[str]:
    bead = result.bead_id or "bead-free"
    return [f"tadw_ship: bead {bead}", *check_lines(result.checks), result.machine_line]


def check_lines(checks: Sequence[CheckReport]) -> list[str]:
    """One line per check, then the excerpt under each one that did not pass.

    A passed check names no log, because a passing gate's logs are removed.
    """
    lines = []
    for check in checks:
        counts = check.counts.describe() if check.counts else COUNTS_UNAVAILABLE
        if check.excerpt is None:
            lines.append(f"tadw_ship: {check.status} {check.name} [{counts}]")
            continue
        lines.append(f"tadw_ship: {check.status} {check.name} (log: {check.log}) [{counts}]")
        if check.excerpt:
            lines.append(check.excerpt)
    return lines


def parse_counts(output: str) -> Counts | None:
    for parser in PARSERS:
        counts = parser(output)
        if counts is not None:
            return counts
    return None


def failure_excerpt(output: str, log: Path) -> str:
    """The last lines of `output`, within both bounds, naming `log` when cut."""
    lines = output.splitlines()
    tail = "\n".join(lines[-EXCERPT_MAX_LINES:])[-EXCERPT_MAX_CHARACTERS:]
    if tail == "\n".join(lines):
        return tail
    return f"[excerpt: the last lines only; the full output is in {log}]\n{tail}"


def commit_subject(kind: str, title: str, bead_id: str) -> str:
    subject = f"{kind}: {title} ({bead_id})"
    if len(subject) <= SUBJECT_MAX_CHARACTERS:
        return subject
    room = max(0, SUBJECT_MAX_CHARACTERS - len(f"{kind}: ... ({bead_id})"))
    head = title[:room]
    if title[room] != " " and " " in head:
        head = head.rsplit(" ", 1)[0]
    return f"{kind}: {head.rstrip()}... ({bead_id})"


def read_log(log: Path) -> str:
    try:
        return log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def pytest_counts(output: str) -> Counts | None:
    summary = last_match(r"^=+ (.*\d+ (?:passed|failed).*) in [\d.]+s.* =+$", output)
    if summary is None:
        return None
    failed = number_before("failed", summary) + number_before("errors?", summary)
    return Counts(number_before("passed", summary), failed)


def unittest_counts(output: str) -> Counts | None:
    ran = last_match(r"^Ran (\d+) tests? in ", output)
    if ran is None:
        return None
    verdict = last_match(r"^(OK.*|FAILED \(.*\))$", output) or ""
    failed = number_after("failures=", verdict) + number_after("errors=", verdict)
    return Counts(int(ran) - failed, failed)


def house_suite_counts(output: str) -> Counts | None:
    """The `All N checks passed.` / `F FAILED, P passed.` line this repository's suites print."""
    passed_all = last_match(r"^All (\d+) checks passed\.$", output)
    if passed_all is not None:
        return Counts(int(passed_all), 0)
    mixed = re.findall(r"^(\d+) FAILED, (\d+) passed\.$", output, re.M)
    if mixed:
        failed, passed = mixed[-1]
        return Counts(int(passed), int(failed))
    return None


PARSERS: Sequence[Callable[[str], Counts | None]] = (
    pytest_counts,
    unittest_counts,
    house_suite_counts,
)


def last_match(pattern: str, output: str) -> str | None:
    matches = re.findall(pattern, output, re.M)
    return matches[-1] if matches else None


def number_before(word: str, text: str) -> int:
    found = re.search(rf"(\d+) {word}", text)
    return int(found.group(1)) if found else 0


def number_after(prefix: str, text: str) -> int:
    found = re.search(rf"{prefix}(\d+)", text)
    return int(found.group(1)) if found else 0
