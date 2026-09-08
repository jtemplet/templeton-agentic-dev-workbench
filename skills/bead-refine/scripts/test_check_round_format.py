#!/usr/bin/env python3
"""Regression suite for check_round_format.py.

Stdlib only, no install, mirroring the other suites in this repository. Run with:
    python3 skills/bead-refine/scripts/test_check_round_format.py

Cases come from the checker's contract, not from the list of bugs that happened
to be found. Enumerating known bugs only ever pins the past, and the suite then
reports a clean run while a live bypass sits in the function it covers.

The contract has six parts, and each has its own group below:

  MARKER CONTRACT       markers pair up, or the run fails loudly
  ROUND TABLE           six named columns, in order, and nothing else
  CELL VALUES           the Route cell holds one of four values, the Why cell
                        holds at most fifteen words
  DETAIL LIST           all eight moved fields arrive in the bullet list
  THEME AND CLOSING     Step 5 carries `Off route`, Step 8 prints both route lines
  ORDERING              the ranked table is printed before the question widget
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_round_format.py"
REAL_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"
REAL_COMMAND = Path(__file__).resolve().parents[3] / "commands" / "bead-refine.md"

STEPS_START = "<!-- refine-round:steps-start -->"
STEPS_END = "<!-- refine-round:steps-end -->"

ROUND_START = "<!-- refine-round:round-start -->"
ROUND_END = "<!-- refine-round:round-end -->"
THEMES_START = "<!-- refine-round:themes-start -->"
THEMES_END = "<!-- refine-round:themes-end -->"
CLOSING_START = "<!-- refine-round:closing-start -->"
CLOSING_END = "<!-- refine-round:closing-end -->"

PASS, FAIL, ERROR = 0, 1, 2

HEADER = "| # | ID | Title | Route | Verdict | Why |\n|---|---|---|---|---|---|"
ROW = "| 1 | acme-4kp | Retry a refused send | on route | Keep | A refused send is lost today |"
DETAIL = (
    "**Detail**\n\n"
    "- **1 acme-4kp**: task, P1, 12d old, 3d idle, blocks 2, blocked by 0, "
    "serves every subscriber, target present. Evidence here."
)
THEME_TABLE = (
    "| Theme | Beads | Oldest | Last touched | Targets present | Off route | What it is for |\n"
    "|---|---|---|---|---|---|---|\n"
    "| Weekly email | 9 | 94d | 61d | 4 of 9 | 2 + 3 | sending the report |"
)
CLOSING = (
    "Kept 4 - Killed 3\n\n"
    "This theme: 5 on route, 4 detours, 2 hardening.\n"
    "Whole backlog: 12 on route, 9 detours, 6 hardening, of the 27 beads routed in Step 4."
)


def round_region(header: str = HEADER, row: str = ROW, detail: str = DETAIL) -> str:
    body = "\n".join(part for part in (header, row, "", detail) if part is not None)
    return f"{ROUND_START}\n\n{body}\n\n{ROUND_END}"


def document(
    rounds: str | None = None,
    themes: str | None = None,
    closing: str | None = None,
    widget_before_themes: bool = False,
    widget: bool = True,
    steps: int = 8,
) -> str:
    """Assemble a minimal document that satisfies every rule unless told not to."""
    if rounds is None:
        rounds = f"{round_region()}\n\n{round_region()}"
    if themes is None:
        themes = f"{THEMES_START}\n\n{THEME_TABLE}\n\n{THEMES_END}"
    if closing is None:
        closing = f"{CLOSING_START}\n\n{CLOSING}\n\n{CLOSING_END}"

    ask = "Then ask with `AskUserQuestion`." if widget else "Then ask the author."
    parts = ["# Bead Refine", ""]
    if widget_before_themes:
        parts += [ask, "", themes]
    else:
        parts += [themes, "", ask]
    parts += ["", rounds, "", closing, ""]
    parts += [f"### Step {n}: do a thing\n" for n in range(1, steps + 1)]
    return "\n".join(parts)


def command_file(steps: int = 8, markers: bool = True) -> str:
    body = "\n".join(f"{n}. Do step {n}" for n in range(1, steps + 1))
    if not markers:
        return f"The skill will:\n\n{body}\n"
    return f"The skill will:\n\n{STEPS_START}\n\n{body}\n\n{STEPS_END}\n"


def run_checker(content: str, command: str | None = None) -> int:
    """Write content to a throwaway SKILL.md and return the checker's exit code."""
    if command is None:
        command = command_file()
    with tempfile.TemporaryDirectory() as root:
        skill = Path(root) / "SKILL.md"
        skill.write_text(content, encoding="utf-8")
        command_path = Path(root) / "bead-refine.md"
        command_path.write_text(command, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(skill), str(command_path)],
            capture_output=True,
            text=True,
        )
        return result.returncode


def why_of(words: int) -> str:
    return f"| 1 | acme-4kp | Title | detour | Kill | {' '.join(['word'] * words)} |"


def header_of(*columns: str) -> str:
    divider = "|" + "|".join("---" for _ in columns) + "|"
    return "| " + " | ".join(columns) + " |\n" + divider


CASES = (
    # ---- MARKER CONTRACT ----
    ("markers", "a valid document passes", document(), PASS),
    (
        "markers",
        "a round region that is never closed fails",
        document(rounds=f"{round_region()}\n\n{ROUND_START}\n\n{HEADER}\n{ROW}\n\n{DETAIL}"),
        FAIL,
    ),
    (
        "markers",
        "a round end with no start fails",
        document(rounds=f"{round_region()}\n\n{round_region()}\n\n{ROUND_END}"),
        FAIL,
    ),
    (
        "markers",
        "a round start opened twice before closing fails",
        document(rounds=f"{ROUND_START}\n{ROUND_START}\n{HEADER}\n{ROW}\n\n{DETAIL}\n{ROUND_END}"),
        FAIL,
    ),
    ("markers", "one round region is not enough", document(rounds=round_region()), FAIL),
    ("markers", "no round region at all fails", document(rounds=""), FAIL),
    ("markers", "a missing themes region fails", document(themes=""), FAIL),
    ("markers", "a missing closing region fails", document(closing=""), FAIL),
    (
        "markers",
        "a themes region opened twice fails",
        document(themes=f"{THEMES_START}\n{THEMES_START}\n{THEME_TABLE}\n{THEMES_END}"),
        FAIL,
    ),
    # ---- ROUND TABLE ----
    (
        "round table",
        "a seventh column fails",
        document(
            rounds=round_region(
                header=header_of("#", "ID", "Title", "Route", "Verdict", "Why", "Target"),
                row="| 1 | acme-4kp | T | detour | Kill | short reason | present |",
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "round table",
        "a `Topic` column fails, so the topic marker cannot come back as a column",
        document(
            rounds=round_region(
                header=header_of("#", "ID", "Title", "Route", "Verdict", "Why", "Topic"),
                row="| 1 | acme-4kp | T | detour | Kill | short reason | adjacent |",
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "round table",
        "the six columns reordered fails",
        document(
            rounds=round_region(
                header=header_of("#", "ID", "Title", "Verdict", "Route", "Why"),
                row="| 1 | acme-4kp | T | Kill | detour | short reason |",
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "round table",
        "a renamed column fails",
        document(
            rounds=round_region(
                header=header_of("#", "ID", "Title", "Path", "Verdict", "Why"),
                row="| 1 | acme-4kp | T | detour | Kill | short reason |",
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "round table",
        "a data row with seven cells fails",
        document(
            rounds=round_region(row="| 1 | acme-4kp | T | detour | Kill | short reason | extra |")
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "round table",
        "a round region holding two tables fails",
        document(rounds=round_region(row=f"{ROW}\n\n{HEADER}\n{ROW}") + "\n\n" + round_region()),
        FAIL,
    ),
    (
        "round table",
        "a round region holding no table fails",
        document(rounds=f"{ROUND_START}\n\n{DETAIL}\n\n{ROUND_END}\n\n" + round_region()),
        FAIL,
    ),
    # ---- CELL VALUES ----
    (
        "cell values",
        "route `on route` passes",
        document(rounds=round_region(row=ROW) + "\n\n" + round_region()),
        PASS,
    ),
    (
        "cell values",
        "route `detour` passes",
        document(
            rounds=round_region(row="| 1 | acme-4kp | T | detour | Kill | short |")
            + "\n\n"
            + round_region()
        ),
        PASS,
    ),
    (
        "cell values",
        "route `hardening` passes",
        document(
            rounds=round_region(row="| 1 | acme-4kp | T | hardening | Kill | short |")
            + "\n\n"
            + round_region()
        ),
        PASS,
    ),
    (
        "cell values",
        "route as a plain hyphen passes, meaning the route was unjudged",
        document(
            rounds=round_region(row="| 1 | acme-4kp | T | - | Kill | short |")
            + "\n\n"
            + round_region()
        ),
        PASS,
    ),
    (
        "cell values",
        "an invented route value fails",
        document(
            rounds=round_region(row="| 1 | acme-4kp | T | sidetrack | Kill | short |")
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "cell values",
        "a route value capitalized differently fails",
        document(
            rounds=round_region(row="| 1 | acme-4kp | T | Detour | Kill | short |")
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "cell values",
        "a Why cell of exactly 15 words passes",
        document(rounds=round_region(row=why_of(15)) + "\n\n" + round_region()),
        PASS,
    ),
    (
        "cell values",
        "a Why cell of 16 words fails",
        document(rounds=round_region(row=why_of(16)) + "\n\n" + round_region()),
        FAIL,
    ),
    # ---- DETAIL LIST ----
    (
        "detail list",
        "a round with no Detail label fails",
        document(rounds=round_region(detail="some prose") + "\n\n" + round_region()),
        FAIL,
    ),
    (
        "detail list",
        "a Detail label with no numbered bullet fails",
        document(rounds=round_region(detail="**Detail**\n\n- nothing numbered") + "\n\n" + round_region()),
        FAIL,
    ),
    (
        "detail list",
        "a Detail list missing `serves` fails",
        document(
            rounds=round_region(
                detail="**Detail**\n\n- **1 acme-4kp**: task, P1, 12d old, 3d idle, "
                "blocks 2, blocked by 0, target present."
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "detail list",
        "a Detail list missing `blocked by` fails",
        document(
            rounds=round_region(
                detail="**Detail**\n\n- **1 acme-4kp**: task, P1, 12d old, 3d idle, "
                "blocks 2, serves everyone, target present."
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "detail list",
        "a Detail list missing the priority fails",
        document(
            rounds=round_region(
                detail="**Detail**\n\n- **1 acme-4kp**: task, 12d old, 3d idle, "
                "blocks 2, blocked by 0, serves everyone, target present."
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "detail list",
        "a Detail list missing the idle days fails",
        document(
            rounds=round_region(
                detail="**Detail**\n\n- **1 acme-4kp**: task, P1, 12d old, "
                "blocks 2, blocked by 0, serves everyone, target present."
            )
            + "\n\n"
            + round_region()
        ),
        FAIL,
    ),
    (
        "detail list",
        "a Detail bullet that wraps over two lines still passes",
        document(
            rounds=round_region(
                detail="**Detail**\n\n- **1 acme-4kp**: task, P1, 12d old, 3d idle,\n"
                "  blocks 2, blocked by 0, serves everyone, target present."
            )
            + "\n\n"
            + round_region()
        ),
        PASS,
    ),
    # ---- THEME AND CLOSING ----
    (
        "theme and closing",
        "a theme table without `Off route` fails",
        document(
            themes=f"{THEMES_START}\n\n"
            + header_of("Theme", "Beads", "Oldest", "Last touched", "What it is for")
            + "\n| Weekly email | 9 | 94d | 61d | sending the report |\n\n"
            + THEMES_END
        ),
        FAIL,
    ),
    (
        "theme and closing",
        "a themes region holding no table fails",
        document(themes=f"{THEMES_START}\n\nno table here\n\n{THEMES_END}"),
        FAIL,
    ),
    (
        "theme and closing",
        "a closing summary missing the backlog route line fails",
        document(
            closing=f"{CLOSING_START}\n\nThis theme: 5 on route, 4 detours, 2 hardening.\n\n{CLOSING_END}"
        ),
        FAIL,
    ),
    (
        "theme and closing",
        "a closing summary missing the theme route line fails",
        document(
            closing=f"{CLOSING_START}\n\nWhole backlog: 12 on route, 9 detours, 6 hardening.\n\n{CLOSING_END}"
        ),
        FAIL,
    ),
    (
        "theme and closing",
        "a closing summary with neither route line fails",
        document(closing=f"{CLOSING_START}\n\nKept 4 - Killed 3\n\n{CLOSING_END}"),
        FAIL,
    ),
    # ---- ORDERING ----
    (
        "ordering",
        "the widget after the theme table passes",
        document(widget_before_themes=False),
        PASS,
    ),
    (
        "ordering",
        "the widget before the theme table fails",
        document(widget_before_themes=True),
        FAIL,
    ),
    (
        "ordering",
        "a skill that never opens the widget fails",
        document(widget=False),
        FAIL,
    ),
    # ---- PARSER INDEPENDENCE ----
    (
        "parser independence",
        "a `## ` heading inside a round region does not move the region",
        document(rounds=round_region(header=f"## Theme: Weekly email\n\n{HEADER}") + "\n\n" + round_region()),
        PASS,
    ),
    (
        "parser independence",
        "an empty document fails",
        "",
        FAIL,
    ),
)

# (group, name, skill content, command content, expected exit)
STEP_CASES = (
    (
        "step parity",
        "eight skill steps and eight listed steps pass",
        document(steps=8),
        command_file(steps=8),
        PASS,
    ),
    (
        "step parity",
        "a skill step the command never lists fails",
        document(steps=9),
        command_file(steps=8),
        FAIL,
    ),
    (
        "step parity",
        "a command listing a step the skill dropped fails",
        document(steps=7),
        command_file(steps=8),
        FAIL,
    ),
    (
        "step parity",
        "a command with no step markers fails",
        document(steps=8),
        command_file(steps=8, markers=False),
        FAIL,
    ),
    (
        "step parity",
        "a skill with no step headings fails",
        document(steps=0),
        command_file(steps=8),
        FAIL,
    ),
    (
        "step parity",
        "numbered prose outside the step markers is not counted",
        document(steps=8),
        "1. Not a step, it sits above the markers\n\n" + command_file(steps=8),
        PASS,
    ),
)


def main() -> int:
    print("check_round_format tests:")
    failures = 0
    group = None

    for case_group, name, content, expected in CASES:
        if case_group != group:
            group = case_group
            print(f"\n  [{group}]")
        actual = run_checker(content)
        if actual == expected:
            print(f"    ok - {name}")
        else:
            failures += 1
            want = {PASS: "pass", FAIL: "fail", ERROR: "error"}[expected]
            print(f"    NOT OK - {name}\n        expected the checker to {want}, got exit {actual}")

    for case_group, name, skill, command, expected in STEP_CASES:
        if case_group != group:
            group = case_group
            print(f"\n  [{group}]")
        actual = run_checker(skill, command)
        if actual == expected:
            print(f"    ok - {name}")
        else:
            failures += 1
            want = {PASS: "pass", FAIL: "fail", ERROR: "error"}[expected]
            print(f"    NOT OK - {name}\n        expected the checker to {want}, got exit {actual}")

    print("\n  [operator error]")
    result = subprocess.run(
        [sys.executable, str(CHECKER), "/nonexistent/SKILL.md"], capture_output=True, text=True
    )
    if result.returncode == ERROR:
        print("    ok - a missing file exits 2, not 1")
    else:
        failures += 1
        print(f"    NOT OK - a missing file should exit 2, got exit {result.returncode}")

    print("\n  [shipped artifact]")
    if REAL_SKILL.is_file() and REAL_COMMAND.is_file():
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(REAL_SKILL), str(REAL_COMMAND)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("    ok - the shipped SKILL.md and command pass their own checker")
        else:
            failures += 1
            print(f"    NOT OK - the shipped files fail their own checker\n{result.stdout}")
    else:
        failures += 1
        print(f"    NOT OK - expected {REAL_SKILL} and {REAL_COMMAND}")

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1

    print(f"\nAll {len(CASES) + len(STEP_CASES) + 2} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
