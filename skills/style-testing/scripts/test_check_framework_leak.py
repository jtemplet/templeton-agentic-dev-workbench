#!/usr/bin/env python3
"""Regression suite for check_framework_leak.py.

Stdlib only, no install, mirroring hooks/test-hooks.js. Run with:
    python3 skills/style-testing/scripts/test_check_framework_leak.py

The checker exists to stop framework tokens leaking into style-testing's
principles. Two separate bypasses shipped before this suite existed, both from
markdown fence handling, both of which let a file containing `pytest` in its
body exit 0:

  1. A `## Appendix` heading inside a fenced code block split the document
     early, exempting everything after it.
  2. After (1) was fixed with a naive toggle, a ```` block containing a ```
     line read as closed, re-exposing the same heading.

Every case below is a real defect that shipped or a guard against one.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_framework_leak.py"
REAL_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"

FRONTMATTER = "---\nname: style-testing\ndescription: mentions pytest and Vitest for keyword matching\n---\n"
SECTIONS = "\n".join(
    f"## {section}"
    for section in (
        "When to Use",
        "Notation",
        "Principles",
        "Anti-Patterns",
        "Escape Hatches",
        "Apply Workflow",
        "Quality Checklist",
    )
)
APPENDIX = "\n## Appendix\npytest | vitest | xctest | minitest\n"


def run_checker(content: str, dirname: str = "style-testing") -> int:
    """Write content to a throwaway skill directory and return the exit code."""
    root = tempfile.mkdtemp()
    try:
        skill_dir = Path(root) / dirname
        skill_dir.mkdir(parents=True)
        target = skill_dir / "SKILL.md"
        target.write_text(content, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(target)], capture_output=True, text=True
        )
        return result.returncode
    finally:
        shutil.rmtree(root)


PASS, FAIL = 0, 1

CASES: tuple[tuple[str, str, int], ...] = (
    (
        "clean file passes",
        FRONTMATTER + SECTIONS + APPENDIX,
        PASS,
    ),
    (
        "framework token in the body fails",
        FRONTMATTER + SECTIONS + "\nuse pytest fixtures here\n" + APPENDIX,
        FAIL,
    ),
    (
        "token only in frontmatter passes (description lists frameworks deliberately)",
        FRONTMATTER + SECTIONS + APPENDIX,
        PASS,
    ),
    (
        "token in the appendix passes (mapping idioms is its job)",
        FRONTMATTER + SECTIONS + APPENDIX + "\nrspec uses let!\n",
        PASS,
    ),
    (
        "REGRESSION: fake appendix heading inside a ``` fence must not split the document",
        FRONTMATTER + SECTIONS + "\n```\n## Appendix\n```\nuse pytest here\n" + APPENDIX,
        FAIL,
    ),
    (
        "REGRESSION: ```` block containing ``` must not read as closed",
        FRONTMATTER + SECTIONS + "\n````\n```\n## Appendix\n```\n````\nuse pytest here\n" + APPENDIX,
        FAIL,
    ),
    (
        "REGRESSION: a ~~~ line inside a ``` block is content, not a closer",
        FRONTMATTER + SECTIONS + "\n```\n~~~\n## Appendix\n```\nuse pytest here\n" + APPENDIX,
        FAIL,
    ),
    (
        "REGRESSION: required sections must be real headings, not code comments",
        FRONTMATTER
        + "\n```\n# When to Use\n# Notation\n# Principles\n# Anti-Patterns\n"
        "# Escape Hatches\n# Apply Workflow\n# Quality Checklist\n```\n"
        + APPENDIX,
        FAIL,
    ),
    (
        "legitimate fenced pseudocode does not false-positive",
        FRONTMATTER + SECTIONS + '\n```text\ngroup "when x"\n  given a = 1\n```\n' + APPENDIX,
        PASS,
    ),
    (
        "unclosed fence fails loudly rather than silently exempting",
        FRONTMATTER + SECTIONS + "\n```\nsome code\n" + APPENDIX,
        FAIL,
    ),
    (
        "missing frontmatter fails",
        SECTIONS + APPENDIX,
        FAIL,
    ),
    (
        "missing appendix fails",
        FRONTMATTER + SECTIONS,
        FAIL,
    ),
    (
        "appendix missing a required framework fails",
        FRONTMATTER + SECTIONS + "\n## Appendix\npytest | vitest only\n",
        FAIL,
    ),
    (
        "empty file fails",
        "",
        FAIL,
    ),
)


def main() -> int:
    print("check_framework_leak tests:")
    failures = 0

    for name, content, expected in CASES:
        actual = run_checker(content)
        if actual == expected:
            print(f"  ok - {name}")
        else:
            failures += 1
            want = "pass" if expected == PASS else "fail"
            print(f"  NOT OK - {name}\n      expected the checker to {want}, got exit {actual}")

    # The shipped skill must satisfy its own checker.
    if REAL_SKILL.is_file():
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(REAL_SKILL)], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  ok - the shipped SKILL.md passes its own checker")
        else:
            failures += 1
            print(f"  NOT OK - the shipped SKILL.md fails its own checker\n{result.stdout}")

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1

    print(f"\nAll {len(CASES) + 1} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
