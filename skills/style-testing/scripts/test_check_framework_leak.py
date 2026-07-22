#!/usr/bin/env python3
"""Regression suite for check_framework_leak.py.

Stdlib only, no install, mirroring hooks/test-hooks.js. Run with:
    python3 skills/style-testing/scripts/test_check_framework_leak.py

Cases are derived from the checker's design contract, not from the list of bugs
that happened to be found. The previous suite enumerated known bugs and reported
"All 15 checks passed" while three live bypasses existed in the function it
covered; enumerating known bugs only ever pins the past.

The contract has three parts, and each has its own group below:

  MARKER CONTRACT   exactly one of each sentinel, or no exemption at all
  EXEMPTION SCOPE   only the region between the sentinels may name a framework
  PARSER INDEPENDENCE  markdown structure, especially code fences, must not be
                    able to move the exempt region. Five bypasses came from the
                    old heading-based split; these cases assert that markdown
                    shape is now simply irrelevant.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_framework_leak.py"
REAL_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"

START = "<!-- leak-check:appendix-start -->"
END = "<!-- leak-check:appendix-end -->"

FRONTMATTER = (
    "---\nname: style-testing\n"
    "description: mentions pytest and Vitest for keyword matching\n---\n"
)
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
APPENDIX = f"\n{START}\n## Appendix\npytest | vitest | xctest | minitest\n{END}\n"

PASS, FAIL = 0, 1


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


# (group, name, content, expected exit, skill directory name)
CASES: tuple[tuple[str, str, str, int, str], ...] = (
    # --- MARKER CONTRACT ---------------------------------------------------
    ("marker", "well-formed markers pass", FRONTMATTER + SECTIONS + APPENDIX, PASS, "style-testing"),
    (
        "marker",
        "missing start marker fails",
        FRONTMATTER + SECTIONS + f"\n## Appendix\npytest | vitest | xctest | minitest\n{END}\n",
        FAIL,
        "style-testing",
    ),
    (
        "marker",
        "missing end marker fails",
        FRONTMATTER + SECTIONS + f"\n{START}\n## Appendix\npytest | vitest | xctest | minitest\n",
        FAIL,
        "style-testing",
    ),
    (
        "marker",
        "duplicate start marker fails rather than picking one",
        FRONTMATTER + SECTIONS + f"\n{START}\n" + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "marker",
        "end marker before start marker fails",
        FRONTMATTER + SECTIONS + f"\n{END}\n## Appendix\npytest | vitest | xctest | minitest\n{START}\n",
        FAIL,
        "style-testing",
    ),
    (
        "marker",
        "FAIL-SAFE: a broken marker contract disables the exemption entirely",
        # The duplicated marker is the only structural problem; the `rspec` token
        # would be exempt under a working contract. It must still be reported.
        FRONTMATTER + SECTIONS + f"\n{START}\n{START}\nuse rspec let! here\n{END}\n",
        FAIL,
        "style-testing",
    ),
    # --- EXEMPTION SCOPE ---------------------------------------------------
    (
        "scope",
        "framework token in the body fails",
        FRONTMATTER + SECTIONS + "\nuse pytest fixtures here\n" + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "scope",
        "framework token between the markers passes",
        FRONTMATTER + SECTIONS + APPENDIX,
        PASS,
        "style-testing",
    ),
    (
        "scope",
        "token AFTER the end marker fails (the exemption is bounded)",
        FRONTMATTER
        + SECTIONS
        + APPENDIX
        + "\n## Further Reading\nAlways use let! and build_stubbed in rspec specs.\n",
        FAIL,
        "style-testing",
    ),
    (
        "scope",
        "token only in frontmatter passes (the description lists frameworks deliberately)",
        FRONTMATTER + SECTIONS + APPENDIX,
        PASS,
        "style-testing",
    ),
    # --- PARSER INDEPENDENCE ----------------------------------------------
    (
        "parser",
        "a `## Appendix` heading inside a code fence cannot move the exempt region",
        FRONTMATTER
        + SECTIONS
        + "\n```\n## Appendix\n```\nuse pytest here\n"
        + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "parser",
        "a ```` block containing ``` cannot move the exempt region",
        FRONTMATTER
        + SECTIONS
        + "\n````\n```\n## Appendix\n```\n````\nuse pytest here\n"
        + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "parser",
        "a closing fence carrying an info string cannot move the exempt region",
        FRONTMATTER
        + SECTIONS
        + "\n```\n```python\n## Appendix\n```\nuse pytest here\n"
        + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "parser",
        "an over-indented fence cannot move the exempt region",
        FRONTMATTER
        + SECTIONS
        + "\n```\n        ```\n## Appendix\n```\nuse pytest here\n"
        + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "parser",
        "an unclosed fence cannot move the exempt region",
        FRONTMATTER + SECTIONS + "\n```\nuse pytest here\n" + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "parser",
        "legitimate fenced pseudocode does not false-positive",
        FRONTMATTER
        + SECTIONS
        + '\n```text\ngroup "when x"\n  given a = 1\n  action = submit(form)\n```\n'
        + APPENDIX,
        PASS,
        "style-testing",
    ),
    # --- OTHER CHECKS ------------------------------------------------------
    ("other", "missing frontmatter fails", SECTIONS + APPENDIX, FAIL, "style-testing"),
    (
        "other",
        "unterminated frontmatter fails",
        "---\nname: style-testing\n" + SECTIONS + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "other",
        "frontmatter name not matching the directory fails",
        FRONTMATTER + SECTIONS + APPENDIX,
        FAIL,
        "style-elsewhere",
    ),
    (
        "other",
        "a missing required section fails",
        FRONTMATTER + "## When to Use\n## Notation\n" + APPENDIX,
        FAIL,
        "style-testing",
    ),
    (
        "other",
        "an appendix missing a required framework fails",
        FRONTMATTER + SECTIONS + f"\n{START}\n## Appendix\npytest | vitest only\n{END}\n",
        FAIL,
        "style-testing",
    ),
    ("other", "empty file fails", "", FAIL, "style-testing"),
)


def main() -> int:
    print("check_framework_leak tests:")
    failures = 0
    group = None

    for case_group, name, content, expected, dirname in CASES:
        if case_group != group:
            group = case_group
            print(f"\n  [{group}]")
        actual = run_checker(content, dirname)
        if actual == expected:
            print(f"    ok - {name}")
        else:
            failures += 1
            want = "pass" if expected == PASS else "fail"
            print(f"    NOT OK - {name}\n        expected the checker to {want}, got exit {actual}")

    print("\n  [shipped artifact]")
    if REAL_SKILL.is_file():
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(REAL_SKILL)], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("    ok - the shipped SKILL.md passes its own checker")
        else:
            failures += 1
            print(f"    NOT OK - the shipped SKILL.md fails its own checker\n{result.stdout}")
    else:
        failures += 1
        print(f"    NOT OK - expected the shipped skill at {REAL_SKILL}")

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1

    print(f"\nAll {len(CASES) + 1} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
