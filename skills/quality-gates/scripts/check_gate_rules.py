#!/usr/bin/env python3
"""Pin the quality-gates rules that let two runs on one tree agree.

tadw-6pyo found rules in `skills/quality-gates/SKILL.md` that left a choice to
the grader, so two runs on one tree picked different rows or statuses. The fix
is prose, and prose drifts. This check pins the parts of it that a script can
read: the worked examples, and the sentences that state a rule.

WHAT THIS CHECKS, AND WHAT IT CANNOT

It reads the document, never a run. A run that ignores a rule still passes
here. The three-run measurement in the bead is what tests run-time behavior.

Five regions are read, each delimited by paired HTML comments:

    <!-- quality-gates-writer:start -->          the JSON artifact example
    <!-- quality-gates-report:start -->          the Output Format example
    <!-- quality-gates-project-checks:start -->  the Project Checks section
    <!-- quality-gates-gate1:start -->           the Gate 1 section
    <!-- quality-gates-narrowing:start -->       Step 2's scope table

WHY THE PROSE IS MATCHED BY PHRASE. A rule stated in a sentence has no other
shape a script can read. So the Project Checks section must say "its own report
row" and must not say "single", and Gate 1 must say what happens to a suite
Step 2 "did not select". Step 2's scope table must say what lint does with "no
changed file it reads", and must keep Doc freshness on its default set at
`--changed`. Reword any of them, and this check fails loudly rather
than passing over a rule it can no longer see.

Usage:  python3 check_gate_rules.py [path/to/SKILL.md]
Exit:   0 clean, 1 with a report of each problem, 2 on operator error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"

MARKERS = {
    "writer": ("<!-- quality-gates-writer:start -->", "<!-- quality-gates-writer:end -->"),
    "report": ("<!-- quality-gates-report:start -->", "<!-- quality-gates-report:end -->"),
    "project": (
        "<!-- quality-gates-project-checks:start -->",
        "<!-- quality-gates-project-checks:end -->",
    ),
    "gate1": ("<!-- quality-gates-gate1:start -->", "<!-- quality-gates-gate1:end -->"),
    "narrowing": (
        "<!-- quality-gates-narrowing:start -->",
        "<!-- quality-gates-narrowing:end -->",
    ),
}

PROJECT_CHECKS = re.compile(r"^Project checks(: .+)?$")

JSON_GATE = re.compile(r'"name": "(?P<name>[^"]+)".*?"command": (?:null|"(?P<command>(?:[^"\\]|\\.)*)")')
TABLE_GATE = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|[^|]*\|\s*(?P<command>[^|]*?)\s*\|")

# A command runs a test suite when it names a test runner, or a script whose
# file name marks it as a test. Step 1 sends every such command to Gate 1.
# The JSON artifact holds one command per row, so a row that chains two cannot
# be re-run from its `command` field as one exact command.
CHAINED = re.compile(r"&&|\|\||;")

ONE_ROW_PHRASE = "its own report row"
SINGLE_ROW = re.compile(r"\bsingle\b", re.I)
UNSELECTED_PHRASE = "did not select"
NOTHING_TO_READ_PHRASE = "no changed file it reads"
DOC_FRESHNESS_ROW = re.compile(r"^\|\s*Doc freshness\s*\|\s*(?P<changed>[^|]*?)\s*\|")
DEFAULT_SET = "default document set"

TEST_SUITE = re.compile(
    r"(^|[\s/])(pytest|vitest|jest|rspec|minitest|go test|npm test"
    r"|test[\w-]*\.\w+|[\w-]+_test\.\w+)(\s|$)"
)


def main() -> int:
    skill_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SKILL
    if not skill_path.is_file():
        print(f"ERROR: no such file: {skill_path}", file=sys.stderr)
        return 2

    lines = skill_path.read_text(encoding="utf-8").splitlines()
    problems = check_skill(lines)
    if problems:
        print(f"FAIL: {len(problems)} problem(s) in {skill_path.name}\n")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"OK: {skill_path.name} keeps every pinned quality-gates rule")
    return 0


def check_skill(lines: list[str]) -> list[str]:
    bounds, problems = {}, []
    for kind in MARKERS:
        bounds[kind], kind_problems = region(lines, kind)
        problems += kind_problems
    if problems:
        return problems
    examples = json_gates(lines, bounds["writer"]) + table_gates(lines, bounds["report"])
    return (
        check_project_checks_commands(examples)
        + check_one_command_per_row(examples)
        + check_project_checks_prose(lines, bounds["project"])
        + check_unselected_suite_rule(lines, bounds["gate1"])
        + check_narrowing(lines, bounds["narrowing"])
    )


def region(lines: list[str], kind: str) -> tuple[tuple[int, int], list[str]]:
    """The one (start, end) line index pair for a marker kind, or a problem."""
    start_marker, end_marker = MARKERS[kind]
    starts = [index for index, line in enumerate(lines) if line.strip() == start_marker]
    ends = [index for index, line in enumerate(lines) if line.strip() == end_marker]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return (0, 0), [
            f"structure: expected one `{start_marker}` followed by one `{end_marker}`, "
            f"found {len(starts)} start(s) and {len(ends)} end(s)"
        ]
    return (starts[0], ends[0]), []


def json_gates(lines: list[str], bounds: tuple[int, int]) -> list[tuple[int, str, str | None]]:
    """Each JSON example gate as (1-based line, name, command)."""
    start, end = bounds
    return [
        (index + 1, match["name"], match["command"])
        for index in range(start, end + 1)
        if (match := JSON_GATE.search(lines[index]))
    ]


def table_gates(lines: list[str], bounds: tuple[int, int]) -> list[tuple[int, str, str | None]]:
    """Each report-table example row as (1-based line, name, command)."""
    start, end = bounds
    rows = []
    for index in range(start, end + 1):
        match = TABLE_GATE.match(lines[index])
        if match and match["command"].startswith("`"):
            rows.append((index + 1, match["name"], match["command"].strip("`")))
    return rows


def check_project_checks_commands(examples: list[tuple[int, str, str | None]]) -> list[str]:
    return [
        f"line {line}: `{name}` runs a test suite, `{command}`, which Step 1 sends to Gate 1"
        for line, name, command in examples
        if PROJECT_CHECKS.match(name) and command and TEST_SUITE.search(command)
    ]



def check_one_command_per_row(examples: list[tuple[int, str, str | None]]) -> list[str]:
    return [
        f"line {line}: `{name}` chains several commands, `{command}`; a row holds one command"
        for line, name, command in examples
        if PROJECT_CHECKS.match(name) and command and CHAINED.search(command)
    ]


def check_project_checks_prose(lines: list[str], bounds: tuple[int, int]) -> list[str]:
    """The section must give each command its own row, as Naming Each Row does."""
    start, end = bounds
    text = " ".join(line.strip() for line in lines[start : end + 1])
    problems = []
    if ONE_ROW_PHRASE not in text:
        problems.append(
            f"line {start + 1}: the Project Checks section never says each command gets "
            f"`{ONE_ROW_PHRASE}`"
        )
    if SINGLE_ROW.search(text):
        problems.append(
            f"line {start + 1}: the Project Checks section says `single`, which contradicts "
            "one report row per command"
        )
    return problems



def check_unselected_suite_rule(lines: list[str], bounds: tuple[int, int]) -> list[str]:
    """At --changed, Gate 1 must state what the report shows for a suite it did not run."""
    start, end = bounds
    text = " ".join(line.strip() for line in lines[start : end + 1])
    if UNSELECTED_PHRASE in text:
        return []
    return [
        f"line {start + 1}: Gate 1 never states what the report shows for a suite "
        f"Step 2 `{UNSELECTED_PHRASE}`"
    ]



def check_narrowing(lines: list[str], bounds: tuple[int, int]) -> list[str]:
    """At --changed, lint says what happens with nothing to read; doc freshness never narrows.

    A renamed or deleted source file breaks a path in a document nobody changed,
    so narrowing doc freshness to changed documents misses exactly that.
    """
    start, end = bounds
    region = lines[start : end + 1]
    problems = []
    if NOTHING_TO_READ_PHRASE not in " ".join(line.strip() for line in region):
        problems.append(
            f"line {start + 1}: Step 2's scope table never says what lint does when there is "
            f"`{NOTHING_TO_READ_PHRASE}`"
        )
    rows = [(start + offset + 1, match) for offset, line in enumerate(region)
            if (match := DOC_FRESHNESS_ROW.match(line))]
    if len(rows) != 1 or DEFAULT_SET not in rows[0][1]["changed"]:
        where = rows[0][0] if rows else start + 1
        problems.append(
            f"line {where}: the scope table needs one Doc freshness row whose `--changed` cell "
            f"runs the `{DEFAULT_SET}`"
        )
    return problems


if __name__ == "__main__":
    sys.exit(main())
