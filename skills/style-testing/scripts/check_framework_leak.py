#!/usr/bin/env python3
"""Enforce that style-testing's principles stay framework-independent.

The skill's value depends on one structural constraint: the body states testing
principles without naming any test framework, and a single appendix maps those
principles to framework idioms. Author discipline does not hold that line across
edits, so this check does.

The exempt region is delimited by explicit sentinel comments, NOT by parsing
markdown:

    <!-- leak-check:appendix-start -->
    ... framework idioms live here ...
    <!-- leak-check:appendix-end -->

Why sentinels. This check previously found the appendix by locating a `## Appendix`
heading, which required knowing whether that heading sat inside a fenced code
block. Five separate bypasses shipped from that one decision (a fenced fake
heading, a ```` block containing ```, a closing fence carrying an info string, an
over-indented fence, and an exemption that ran to end of file). Each was patched
by adding another CommonMark rule to a hand-rolled scanner, and each patch left
the next rule unimplemented. Sentinels remove the dependency on parsing markdown
at all.

Two properties make that safe:

  1. Exactly one of each marker is required. A marker duplicated anywhere, for
     example inside a code sample, is an ERROR rather than an ambiguous choice
     of which one to honour.
  2. Any marker problem disables the exemption entirely and scans the whole
     document. The failure mode is a false positive you can see, never a silent
     pass.

Frontmatter is exempt because its description deliberately lists frameworks for
keyword matching at invocation time.

Known limitation: required-section detection matches `## ` headings by text, so a
`## Principles` line inside a fenced code sample would satisfy that check. That
weakens a structural check; it cannot exempt a framework token, because token
scanning depends only on the sentinels.

Usage:  python3 check_framework_leak.py [path/to/SKILL.md]
Exit:   0 clean, 1 with a line-numbered report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"
FRONTMATTER_FENCE = "---"
APPENDIX_START = "<!-- leak-check:appendix-start -->"
APPENDIX_END = "<!-- leak-check:appendix-end -->"
H2_HEADING = re.compile(r"^##\s+(.+?)\s*$")

# Substrings that must not appear in the body. Matched case-insensitively.
BANNED_TOKENS = (
    # Framework names
    "rspec", "pytest", "jest", "vitest", "minitest", "unittest", "xctest", "junit",
    # Framework-specific constructs
    "let!", "subject {", "it_behaves_like", "describe(", "beforeeach", "aftereach",
    "conftest", "xctassert", "@test", "@fixture", "expect(", "factorybot",
    "build_stubbed", "assert_equal", "@pytest",
)

REQUIRED_SECTIONS = (
    "When to Use",
    "Notation",
    "Principles",
    "Anti-Patterns",
    "Escape Hatches",
    "Apply Workflow",
    "Quality Checklist",
    "Appendix",
)

# The appendix earns its exemption only by actually covering every framework the
# description promises. Each entry is a set of acceptable spellings.
REQUIRED_APPENDIX_FRAMEWORKS = (
    ("pytest",),
    ("vitest", "jest"),
    ("xctest", "swift testing"),
    ("minitest",),
)


def frontmatter_bounds(lines: list[str]) -> tuple[list[str], int]:
    """Return (frontmatter lines, index of the first body line)."""
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return [], 0

    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_FENCE:
            return lines[1:index], index + 1

    # Unterminated frontmatter: report it as missing and scan from the top.
    return [], 0


def locate_appendix(lines: list[str], start_index: int) -> tuple[int | None, int | None, list[str]]:
    """Find the sentinel-delimited appendix.

    Returns (start line index, end line index, problems). Any problem yields
    (None, None, problems), which disables the exemption so the whole document
    is scanned. Ambiguity must never silently widen the exempt region.
    """
    starts = [i for i in range(start_index, len(lines)) if lines[i].strip() == APPENDIX_START]
    ends = [i for i in range(start_index, len(lines)) if lines[i].strip() == APPENDIX_END]

    problems: list[str] = []
    if len(starts) != 1:
        problems.append(
            f"appendix: expected exactly 1 `{APPENDIX_START}` marker, found {len(starts)}"
        )
    if len(ends) != 1:
        problems.append(
            f"appendix: expected exactly 1 `{APPENDIX_END}` marker, found {len(ends)}"
        )
    if not problems and ends[0] < starts[0]:
        problems.append(
            f"appendix: end marker (line {ends[0] + 1}) precedes start marker (line {starts[0] + 1})"
        )

    if problems:
        return None, None, problems
    return starts[0], ends[0], []


def check_frontmatter(frontmatter: list[str], skill_path: Path) -> list[str]:
    if not frontmatter:
        return ["frontmatter: missing or unterminated"]

    problems: list[str] = []
    text = "\n".join(frontmatter)

    name_match = re.search(r"^name:\s*(\S+)\s*$", text, re.MULTILINE)
    expected = skill_path.parent.name
    if not name_match:
        problems.append("frontmatter: no `name:` field")
    elif name_match.group(1) != expected:
        problems.append(
            f"frontmatter: name `{name_match.group(1)}` does not match directory `{expected}`"
        )

    description_match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    if not description_match or not description_match.group(1).strip():
        problems.append("frontmatter: no `description:` field, so the skill can never be invoked")

    return problems


def check_body_tokens(body: list[tuple[int, str]]) -> list[str]:
    problems: list[str] = []
    for number, line in body:
        lowered = line.lower()
        for token in BANNED_TOKENS:
            if token in lowered:
                problems.append(
                    f"line {number}: leaked framework token `{token}` in `{line.strip()}`"
                )
    return problems


def check_sections(lines: list[str]) -> list[str]:
    headings = "\n".join(match.group(1) for match in map(H2_HEADING.match, lines) if match)
    return [
        f"structure: required section `{section}` is missing"
        for section in REQUIRED_SECTIONS
        if section.lower() not in headings.lower()
    ]


def check_appendix_coverage(appendix: list[str]) -> list[str]:
    text = "\n".join(appendix).lower()
    return [
        f"appendix: no coverage for {' / '.join(spellings)}"
        for spellings in REQUIRED_APPENDIX_FRAMEWORKS
        if not any(spelling in text for spelling in spellings)
    ]


def main() -> int:
    skill_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SKILL
    if not skill_path.is_file():
        print(f"FAIL: no such file: {skill_path}", file=sys.stderr)
        return 1

    lines = skill_path.read_text(encoding="utf-8").splitlines()
    frontmatter, body_start = frontmatter_bounds(lines)
    start, end, marker_problems = locate_appendix(lines, body_start)

    if start is None or end is None:
        # No trustworthy exemption: scan everything after the frontmatter.
        body = [(n + 1, lines[n]) for n in range(body_start, len(lines))]
        appendix: list[str] = []
    else:
        body = [
            (n + 1, lines[n])
            for n in range(body_start, len(lines))
            if not start <= n <= end
        ]
        appendix = lines[start + 1 : end]

    problems = [
        *check_frontmatter(frontmatter, skill_path),
        *marker_problems,
        *check_sections(lines),
        *check_body_tokens(body),
        *check_appendix_coverage(appendix),
    ]

    if problems:
        print(f"FAIL: {len(problems)} problem(s) in {skill_path.name}\n")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print(f"OK: {skill_path.name} is framework-independent ({len(body)} body lines scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
