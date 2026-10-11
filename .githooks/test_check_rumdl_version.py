#!/usr/bin/env python3
"""Regression suite for check_rumdl_version.py.

Stdlib only, no install, mirroring the other suites in this repository. Run with:
    python3 .githooks/test_check_rumdl_version.py

Each case runs the checker against a version file and a stub `rumdl` on a PATH
the case controls, so no case depends on the rumdl this machine has.

  VERSIONS COMPARED     a match passes, a mismatch fails and names both versions
  MISSING RUMDL         passes with a note, as the hook's missing-tool policy does
  OPERATOR ERRORS       a missing or malformed version file, or an unreadable
                        `rumdl --version`, exits 2 rather than passing
  ONE SOURCE            lint.yml reads the file and carries no literal version
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECKER = REPO / ".githooks" / "check_rumdl_version.py"
VERSION_FILE = REPO / ".rumdl-version"
WORKFLOW = REPO / ".github" / "workflows" / "lint.yml"

PASS, FAIL, ERROR = 0, 1, 2

passed = 0
failed = 0


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def run_checker(
    pinned: str | None, rumdl_prints: str | None, rumdl_exit: int = 0
) -> subprocess.CompletedProcess:
    """Run the checker with `pinned` in the version file and a stub rumdl on PATH.

    `pinned=None` leaves the version file absent, and `rumdl_prints=None` leaves
    rumdl off the PATH.
    """
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        version_file = tmp / ".rumdl-version"
        if pinned is not None:
            version_file.write_text(pinned, encoding="utf-8")
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        if rumdl_prints is not None:
            stub = bin_dir / "rumdl"
            stub.write_text(f"#!/bin/sh\necho '{rumdl_prints}'\nexit {rumdl_exit}\n", encoding="utf-8")
            stub.chmod(0o755)
        return subprocess.run(
            [sys.executable, str(CHECKER), str(version_file)],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PATH": str(bin_dir)},
        )


def case_matching_versions_pass() -> None:
    result = run_checker("0.2.77\n", "rumdl 0.2.77")
    assert result.returncode == PASS, result.stderr
    assert result.stdout + result.stderr == "", "a match must print nothing"


def case_mismatch_fails_and_names_both_versions() -> None:
    result = run_checker("0.2.33\n", "rumdl 0.2.77")
    assert result.returncode == FAIL, result.stdout + result.stderr
    for version in ("0.2.33", "0.2.77"):
        assert version in result.stderr, f"{version} must be named: {result.stderr}"


def case_longer_version_is_not_a_match() -> None:
    result = run_checker("0.2.7\n", "rumdl 0.2.77")
    assert result.returncode == FAIL, "0.2.7 must not match 0.2.77 by prefix"


def case_missing_rumdl_passes_with_a_note() -> None:
    result = run_checker("0.2.77\n", None)
    assert result.returncode == PASS, result.stderr
    assert "not installed" in result.stdout, f"the absence must be stated: {result.stdout}"


def case_missing_version_file_is_an_operator_error() -> None:
    result = run_checker(None, "rumdl 0.2.77")
    assert result.returncode == ERROR, result.stdout + result.stderr


def case_malformed_version_file_is_an_operator_error() -> None:
    for text in ("", "v0.2.77\n", "latest\n", "0.2.77\n0.2.78\n"):
        result = run_checker(text, "rumdl 0.2.77")
        assert result.returncode == ERROR, f"{text!r} must be refused: {result.stderr}"


def case_unreadable_rumdl_version_is_an_operator_error() -> None:
    assert run_checker("0.2.77\n", "no version here").returncode == ERROR
    assert run_checker("0.2.77\n", "rumdl 0.2.77", rumdl_exit=3).returncode == ERROR


def case_workflow_reads_the_version_file() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert ".rumdl-version" in workflow, "lint.yml must install the version in .rumdl-version"
    literal = re.search(r"RUMDL_VERSION:\s*v?\d", workflow)
    assert not literal, f"lint.yml must carry no literal rumdl version: {literal.group(0)}"


def case_repository_version_file_is_well_formed() -> None:
    text = VERSION_FILE.read_text(encoding="utf-8")
    assert re.fullmatch(r"\d+\.\d+\.\d+\n", text), f".rumdl-version holds {text!r}"


print("\n  [versions compared]")
check("matching versions pass in silence", case_matching_versions_pass)
check("a mismatch fails and names both versions", case_mismatch_fails_and_names_both_versions)
check("a version that is only a prefix is a mismatch", case_longer_version_is_not_a_match)

print("\n  [missing rumdl]")
check("a missing rumdl passes with a note", case_missing_rumdl_passes_with_a_note)

print("\n  [operator errors]")
check("a missing version file exits 2", case_missing_version_file_is_an_operator_error)
check("a malformed version file exits 2", case_malformed_version_file_is_an_operator_error)
check("an unreadable `rumdl --version` exits 2", case_unreadable_rumdl_version_is_an_operator_error)

print("\n  [one source]")
check("lint.yml reads the version file", case_workflow_reads_the_version_file)
check("the repository's version file is well formed", case_repository_version_file_is_well_formed)

print(f"\n  {passed} passed, {failed} failed\n")
sys.exit(1 if failed else 0)
