#!/usr/bin/env python3
"""Run rumdl's MD013 line-length rule on the changed Markdown files alone.

changed_set.py names the files a push touches. This script runs MD013, the
100-column wrap rule, only on the `.md` files in that set, never on the 87
files that already carry a line past 100 columns. Whole-tree coverage for
every other rumdl rule stays in the separate `rumdl check .` invocation in
`.githooks/pre-push`; this script is scoped to MD013 on purpose, so the two
never report the same finding twice.

STDOUT AND STDERR PASS THROUGH FROM rumdl UNCHANGED, so a failure names the
file and line the same way a whole-tree run would.

FORGIVES WHAT IT CANNOT CHECK. A missing `rumdl`, a base `changed_set.py`
cannot resolve, no changed `.md` file, or a changed `.md` file that no longer
exists on disk: each exits 0. `.githooks/pre-push` already treats a missing
tool as a reason to skip, not fail, and this script holds the same rule for
the conditions the hook's own tool detection cannot see, because it only
inspects the command it runs, `python3`. A deleted file has no line to check,
and `rumdl check` exits 2 on a path it cannot find rather than skipping it, so
this script filters deletions out before rumdl ever sees them.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CHANGED_SET = SCRIPT_DIR / "changed_set.py"

EXIT_OK = 0
EXIT_FOUND = 1


def changed_markdown_files() -> list[str]:
    """The changed `.md` paths that still exist, or an empty list when none
    changed, none remain, or the base could not be resolved.

    Runs changed_set.py as a subprocess rather than importing it, matching how
    test_changed_set.py already exercises it: as the CLI contract every caller
    actually uses. changed_set.py reports a deleted path too, since it comes
    straight from `git diff --name-only`; `rumdl check` cannot read a path
    that is gone, so a deletion is filtered out here rather than left for
    rumdl to error on.
    """
    result = subprocess.run(
        [sys.executable, str(CHANGED_SET)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [
        line
        for line in result.stdout.splitlines()
        if line.endswith(".md") and Path(line).is_file()
    ]


def main() -> int:
    if shutil.which("rumdl") is None:
        print("check_markdown_wrap: rumdl not on PATH, skipping", file=sys.stderr)
        return EXIT_OK

    files = changed_markdown_files()
    if not files:
        return EXIT_OK

    result = subprocess.run(["rumdl", "check", "--enable", "MD013", *files])
    return EXIT_OK if result.returncode == 0 else EXIT_FOUND


if __name__ == "__main__":
    raise SystemExit(main())
