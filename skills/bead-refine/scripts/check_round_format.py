#!/usr/bin/env python3
"""Enforce the output format `skills/bead-refine/SKILL.md` promises.

The skill's value to a product owner depends on one thing: the tables it prints
fit a terminal and say what a bead is. A 13-column table wrapped into unreadable
text is what this check exists to stop coming back. Author discipline did not
hold that line: the rule "keep the Why cell short" was already in the document
when the table grew to 13 columns.

WHAT THIS CHECKS, AND WHAT IT CANNOT

It checks the templates the skill prints, not what a model does at run time. A
template that is wrong guarantees wrong output; a template that is right does
not guarantee right output. `evals/cases/` is where run-time behavior is
measured, and ADR 0005 keeps those measurements off every gate.

Four regions are checked, each delimited by paired HTML comments:

    <!-- refine-round:round-start -->    one or more; each holds a Step 6 round
    <!-- refine-round:round-end -->

    <!-- refine-round:themes-start -->   exactly one; Step 5's ranked theme table
    <!-- refine-round:themes-end -->

    <!-- refine-round:closing-start -->  exactly one; Step 8's closing summary
    <!-- refine-round:closing-end -->

    <!-- refine-round:steps-start -->    exactly one, in commands/bead-refine.md;
    <!-- refine-round:steps-end -->      the numbered list that restates the steps

The step count is the only cross-file check. It compares how many `### Step N:`
headings the skill has against how many numbered items the command lists. It
cannot tell whether a step's wording contradicts the skill; it catches the drift
that actually happens, which is the skill gaining a step the command never
mentions.

WHY MARKERS AND NOT HEADINGS. `check_framework_leak.py` shipped five separate
bypasses from finding its region by a `## ` heading, because that needs a
CommonMark parser to know whether the heading sits inside a code fence. Markers
remove the dependency on parsing markdown. `style-markdown` rule 16 states the
same rule for every document in this repository.

Any marker problem is an ERROR that fails the run. It never silently narrows
what gets checked, because a check that quietly covers nothing reports OK.

Usage:  python3 check_round_format.py [path/to/SKILL.md [path/to/command.md]]
Exit:   0 clean, 1 with a line-numbered report, 2 on operator error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"
DEFAULT_COMMAND = (
    Path(__file__).resolve().parents[3] / "commands" / "bead-refine.md"
)

MARKERS = {
    "round": ("<!-- refine-round:round-start -->", "<!-- refine-round:round-end -->"),
    "themes": ("<!-- refine-round:themes-start -->", "<!-- refine-round:themes-end -->"),
    "closing": ("<!-- refine-round:closing-start -->", "<!-- refine-round:closing-end -->"),
    "steps": ("<!-- refine-round:steps-start -->", "<!-- refine-round:steps-end -->"),
}

# The six columns of the Step 6 round table, in order. The whole point of the
# check: a seventh column, or these six reordered, is a failure.
ROUND_COLUMNS = ("#", "ID", "Title", "Route", "Verdict", "Why")

# What Step 4 may set. A plain hyphen means the milestone names were never
# confirmed, so the route was left unjudged.
ROUTE_VALUES = ("on route", "detour", "hardening", "-")

# The Why cell replaces the document's own 25-word sentence limit with 15,
# because the author reads it in a narrow column beside five others.
WHY_WORD_LIMIT = 15

# Step 5's ranked theme table must carry this column, so the author can see how
# many of a theme's beads no milestone needs.
OFF_ROUTE_COLUMN = "Off route"

# The two lines Step 8 must print: one for the theme, one for the whole backlog.
CLOSING_ROUTE_LINES = ("This theme:", "Whole backlog:")

# The eight fields that left the table for the Detail list. Each is matched by
# the shape it takes in a bullet, so moving one back into a column fails here.
DETAIL_FIELDS = (
    ("type", re.compile(r"\b(task|feature|bug|epic|chore)\b")),
    ("priority", re.compile(r"\bP\d\b")),
    ("age", re.compile(r"\b\d+d old\b")),
    ("idle days", re.compile(r"\b\d+d idle\b")),
    ("blocks", re.compile(r"\bblocks \d+\b")),
    ("blocked by", re.compile(r"\bblocked by \d+\b")),
    ("serves", re.compile(r"\bserves \S")),
    ("target", re.compile(r"\btarget \S")),
)

DETAIL_LABEL = "**Detail**"
DETAIL_BULLET = re.compile(r"^\s*-\s+\*\*\d+\s")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
TABLE_DIVIDER = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
WIDGET = "AskUserQuestion"

# The skill numbers its workflow with `### Step N:` headings, and the command
# restates them as a numbered list. A heading match is safe here because it
# produces a count: rename one and the count drops, which fails loudly.
SKILL_STEP = re.compile(r"^###\s+Step\s+(\d+)\s*:")
COMMAND_STEP = re.compile(r"^(\d+)\.\s+\S")


def cells(row: str) -> list[str]:
    """Split one markdown table row into its cells."""
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def find_regions(lines: list[str], kind: str) -> tuple[list[tuple[int, int]], list[str]]:
    """Return the (start, end) line indexes for one marker kind, plus problems.

    Markers must alternate start, end, start, end. Anything else is a problem
    and yields no regions, so a mangled marker fails loudly rather than
    shrinking what the check covers.
    """
    start_marker, end_marker = MARKERS[kind]
    events = [
        (index, line.strip())
        for index, line in enumerate(lines)
        if line.strip() in (start_marker, end_marker)
    ]

    regions: list[tuple[int, int]] = []
    problems: list[str] = []
    open_at: int | None = None
    for index, marker in events:
        if marker == start_marker:
            if open_at is not None:
                problems.append(
                    f"line {index + 1}: `{start_marker}` opened again "
                    f"before the one on line {open_at + 1} was closed"
                )
                break
            open_at = index
        else:
            if open_at is None:
                problems.append(f"line {index + 1}: `{end_marker}` with no matching start")
                break
            regions.append((open_at, index))
            open_at = None

    if open_at is not None:
        problems.append(f"line {open_at + 1}: `{start_marker}` is never closed")

    return ([], problems) if problems else (regions, [])


def require_region_count(kind: str, regions: list[tuple[int, int]], minimum: int) -> list[str]:
    if len(regions) >= minimum:
        return []
    start_marker, _ = MARKERS[kind]
    return [
        f"structure: expected at least {minimum} `{start_marker}` region(s), found {len(regions)}"
    ]


def tables_in(lines: list[str], start: int, end: int) -> list[tuple[int, list[str]]]:
    """Return each table inside a region as (header line index, its rows)."""
    tables: list[tuple[int, list[str]]] = []
    index = start
    while index <= end:
        if TABLE_ROW.match(lines[index]) and not TABLE_DIVIDER.match(lines[index]):
            header = index
            rows = []
            index += 1
            if index <= end and TABLE_DIVIDER.match(lines[index]):
                index += 1
                while index <= end and TABLE_ROW.match(lines[index]):
                    rows.append(lines[index])
                    index += 1
                tables.append((header, rows))
                continue
        index += 1
    return tables


def check_round(lines: list[str], start: int, end: int) -> list[str]:
    """Check one Step 6 round template: its table, then its Detail list."""
    problems: list[str] = []
    tables = tables_in(lines, start, end)

    if len(tables) != 1:
        return [
            f"line {start + 1}: a round region must hold exactly 1 table, found {len(tables)}"
        ]

    header_index, rows = tables[0]
    header = cells(lines[header_index])
    if tuple(header) != ROUND_COLUMNS:
        problems.append(
            f"line {header_index + 1}: the round table must hold exactly these 6 columns "
            f"in this order: {' | '.join(ROUND_COLUMNS)}. Found: {' | '.join(header)}"
        )
        # Every cell check below indexes by column, so a wrong header makes them
        # meaningless rather than merely noisy.
        return problems

    for offset, row in enumerate(rows):
        number = header_index + 3 + offset
        values = cells(row)
        if len(values) != len(ROUND_COLUMNS):
            problems.append(
                f"line {number}: row has {len(values)} cells, expected {len(ROUND_COLUMNS)}"
            )
            continue

        route = values[ROUND_COLUMNS.index("Route")]
        if route not in ROUTE_VALUES:
            problems.append(
                f"line {number}: Route cell is `{route}`, "
                f"expected one of: {', '.join(ROUTE_VALUES)}"
            )

        why = values[ROUND_COLUMNS.index("Why")]
        words = len(why.split())
        if words > WHY_WORD_LIMIT:
            problems.append(
                f"line {number}: Why cell is {words} words, the limit is {WHY_WORD_LIMIT}: `{why}`"
            )

    problems.extend(check_detail(lines, start, end))
    return problems


def check_detail(lines: list[str], start: int, end: int) -> list[str]:
    """Every round carries a Detail list naming all eight moved fields."""
    region = lines[start : end + 1]
    if not any(line.strip() == DETAIL_LABEL for line in region):
        return [f"line {start + 1}: round region has no `{DETAIL_LABEL}` label"]

    bullets = [line for line in region if DETAIL_BULLET.match(line)]
    if not bullets:
        return [f"line {start + 1}: round region has no numbered Detail bullet"]

    # A bullet wraps, so measure the fields against the whole list rather than
    # against one line of it.
    text = "\n".join(region)
    return [
        f"line {start + 1}: the Detail list names no {name}, "
        "so that field left the table without arriving here"
        for name, pattern in DETAIL_FIELDS
        if not pattern.search(text)
    ]


def check_themes(lines: list[str], start: int, end: int) -> list[str]:
    tables = tables_in(lines, start, end)
    if len(tables) != 1:
        return [
            f"line {start + 1}: the themes region must hold exactly 1 table, found {len(tables)}"
        ]

    header_index, _ = tables[0]
    header = cells(lines[header_index])
    if OFF_ROUTE_COLUMN not in header:
        return [
            f"line {header_index + 1}: the theme table must carry an `{OFF_ROUTE_COLUMN}` "
            f"column. Found: {' | '.join(header)}"
        ]
    return []


def check_closing(lines: list[str], start: int, end: int) -> list[str]:
    region = "\n".join(lines[start : end + 1])
    return [
        f"line {start + 1}: the closing summary prints no `{prefix}` route line"
        for prefix in CLOSING_ROUTE_LINES
        if not re.search(rf"^{re.escape(prefix)}", region, re.M)
    ]


def check_table_precedes_widget(lines: list[str], themes: list[tuple[int, int]]) -> list[str]:
    """The ranked theme table must be printed before the question widget opens.

    The widget caps an option header at 12 characters, so no reasoning fits
    inside it. The table is the only place the evidence can reach the author.
    """
    if not themes:
        return []

    widget_lines = [index for index, line in enumerate(lines) if WIDGET in line]
    if not widget_lines:
        return [f"structure: the skill never mentions `{WIDGET}`, so Step 5 asks nothing"]

    _, themes_end = themes[0]
    if themes_end > widget_lines[0]:
        return [
            f"line {widget_lines[0] + 1}: `{WIDGET}` appears before the theme table ends "
            f"on line {themes_end + 1}. The author would choose with the evidence hidden"
        ]
    return []


def check_step_parity(skill_lines: list[str], command_path: Path) -> list[str]:
    """The command's numbered list must name every step the skill defines.

    This is a count, not a reading. A step whose wording contradicts the skill
    still passes here. What it catches is the skill gaining or losing a step
    while the command's list stays as it was, which is the drift that happens.
    """
    numbers = [int(match.group(1)) for line in skill_lines if (match := SKILL_STEP.match(line))]
    if not numbers:
        return ["structure: the skill defines no `### Step N:` heading"]

    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        return [f"structure: the skill's step numbers are {numbers}, expected {expected}"]

    if not command_path.is_file():
        return [f"structure: no command file at {command_path}"]

    command_lines = command_path.read_text(encoding="utf-8").splitlines()
    regions, problems = find_regions(command_lines, "steps")
    if problems:
        return problems
    problems = require_region_count("steps", regions, 1)
    if problems:
        return problems

    start, end = regions[0]
    listed = [
        int(match.group(1))
        for line in command_lines[start : end + 1]
        if (match := COMMAND_STEP.match(line))
    ]
    if listed != expected:
        return [
            f"{command_path.name}: its numbered list is {listed}, but the skill defines "
            f"{expected}. The command no longer names every step"
        ]
    return []


def main() -> int:
    skill_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SKILL
    command_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else DEFAULT_COMMAND
    if not skill_path.is_file():
        print(f"ERROR: no such file: {skill_path}", file=sys.stderr)
        return 2

    lines = skill_path.read_text(encoding="utf-8").splitlines()

    rounds, problems = find_regions(lines, "round")
    themes, themes_problems = find_regions(lines, "themes")
    closings, closing_problems = find_regions(lines, "closing")
    problems += themes_problems + closing_problems

    problems += require_region_count("round", rounds, 2)
    problems += require_region_count("themes", themes, 1)
    problems += require_region_count("closing", closings, 1)

    for start, end in rounds:
        problems += check_round(lines, start, end)
    for start, end in themes:
        problems += check_themes(lines, start, end)
    for start, end in closings:
        problems += check_closing(lines, start, end)
    problems += check_table_precedes_widget(lines, themes)
    problems += check_step_parity(lines, command_path)

    if problems:
        print(f"FAIL: {len(problems)} problem(s) in {skill_path.name}\n")
        for problem in problems:
            print(f"  {problem}")
        return 1

    steps = sum(1 for line in lines if SKILL_STEP.match(line))
    print(
        f"OK: {skill_path.name} prints {len(rounds)} well-formed round(s), "
        f"a theme table with `{OFF_ROUTE_COLUMN}`, and both closing route lines. "
        f"{command_path.name} lists all {steps} steps"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
