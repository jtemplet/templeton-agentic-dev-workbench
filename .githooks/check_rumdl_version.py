#!/usr/bin/env python3
"""Assert the local `rumdl` is the version CI installs.

`.rumdl-version` is the one place the version lives. `.github/workflows/lint.yml`
installs that version, and this check compares it to `rumdl --version` here.

Without it the two drift in silence. CI once ran 0.2.33 while the local hooks ran
0.2.77, the two disagreed on MD058, and four pushes passed `.githooks/pre-push`
and then failed the Lint workflow (tadw-36mk).

A missing `rumdl` passes with a note, because `.githooks/pre-push` allows a push
when a tool is missing and names the tool itself.

Usage:  python3 .githooks/check_rumdl_version.py [path/to/.rumdl-version]
Exit:   0 on a match or a missing rumdl, 1 on a mismatch, 2 on operator error.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_VERSION_FILE = Path(__file__).resolve().parent.parent / ".rumdl-version"

# Bare, with no leading `v`, because that is what `rumdl --version` prints.
# lint.yml adds the `v` the release URL needs.
VERSION = re.compile(r"\d+\.\d+\.\d+")

MATCH, MISMATCH, OPERATOR_ERROR = 0, 1, 2


class OperatorError(Exception):
    """The check could not compare anything: fix the setup, not the versions."""


def main(argv: list[str]) -> int:
    version_file = Path(argv[1]) if len(argv) > 1 else DEFAULT_VERSION_FILE
    try:
        pinned = pinned_version(version_file)
        installed = installed_version()
    except OperatorError as error:
        print(f"check_rumdl_version: {error}", file=sys.stderr)
        return OPERATOR_ERROR
    if installed is None:
        print(f"check_rumdl_version: rumdl is not installed; CI runs {pinned}")
        return MATCH
    if installed != pinned:
        print(mismatch_report(installed, pinned, version_file), file=sys.stderr)
        return MISMATCH
    return MATCH


def pinned_version(version_file: Path) -> str:
    try:
        text = version_file.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise OperatorError(f"cannot read {version_file}: {error}") from error
    if not VERSION.fullmatch(text):
        raise OperatorError(
            f"{version_file} must hold one bare version such as 0.2.77, but holds {text!r}"
        )
    return text


def installed_version() -> str | None:
    """The version `rumdl --version` reports, or None when rumdl is not on PATH."""
    if shutil.which("rumdl") is None:
        return None
    result = subprocess.run(["rumdl", "--version"], capture_output=True, text=True, check=False)
    found = VERSION.search(result.stdout)
    if result.returncode != 0 or not found:
        raise OperatorError(
            f"`rumdl --version` exited {result.returncode} and printed "
            f"{(result.stdout + result.stderr).strip()!r}"
        )
    return found.group(0)


def mismatch_report(installed: str, pinned: str, version_file: Path) -> str:
    return (
        f"check_rumdl_version: the local rumdl is {installed}, and CI installs {pinned}.\n"
        f"  To move CI to the local version, write {installed} to {version_file.name}.\n"
        f"  To keep CI where it is, install rumdl {pinned} locally."
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
