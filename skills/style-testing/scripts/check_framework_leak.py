#!/usr/bin/env python3
"""Enforce that style-testing's principles stay framework-independent.

The skill's value depends on one structural constraint: the body states testing
principles without naming any test framework, and a single fenced appendix maps
those principles to framework idioms. Author discipline does not hold that line
across edits, so this check does.

Scans everything between the frontmatter and the appendix heading. The
frontmatter is exempt because its description deliberately lists frameworks for
keyword matching at invocation time, and the appendix is exempt because mapping
idioms is its entire job.

Usage:  python3 check_framework_leak.py [path/to/SKILL.md]
Exit:   0 clean, 1 with a line-numbered report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"
APPENDIX_HEADING = re.compile(r"^##\s+Appendix\b", re.IGNORECASE)
FRONTMATTER_FENCE = "---"

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


def split_document(lines: list[str]) -> tuple[list[str], list[tuple[int, str]], list[str]]:
    """Return (frontmatter, numbered body lines, appendix lines)."""
    frontmatter: list[str] = []
    start = 0

    if lines and lines[0].strip() == FRONTMATTER_FENCE:
        for index in range(1, len(lines)):
            if lines[index].strip() == FRONTMATTER_FENCE:
                frontmatter = lines[1:index]
                start = index + 1
                break

    for index in range(start, len(lines)):
        if APPENDIX_HEADING.match(lines[index]):
            body = [(n + 1, lines[n]) for n in range(start, index)]
            return frontmatter, body, lines[index:]

    return frontmatter, [(n + 1, lines[n]) for n in range(start, len(lines))], []


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
                problems.append(f"line {number}: leaked framework token `{token}` in `{line.strip()}`")
    return problems


def check_sections(lines: list[str]) -> list[str]:
    headings = "\n".join(line for line in lines if line.startswith("#"))
    return [
        f"structure: required section `{section}` is missing"
        for section in REQUIRED_SECTIONS
        if section.lower() not in headings.lower()
    ]


def check_appendix_coverage(appendix: list[str]) -> list[str]:
    if not appendix:
        return ["appendix: missing, so the principles have no idiom map"]

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
    frontmatter, body, appendix = split_document(lines)

    problems = [
        *check_frontmatter(frontmatter, skill_path),
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
