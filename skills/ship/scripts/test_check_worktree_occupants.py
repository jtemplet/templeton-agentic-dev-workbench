#!/usr/bin/env python3
"""Regression suite for check_worktree_occupants.py.

Stdlib only, no install, mirroring test_check_hygiene.py. Run with:
    python3 skills/ship/scripts/test_check_worktree_occupants.py

Every case that needs an occupant starts a real `sleep` process with its working
directory set, so the detection under test runs against the operating system
rather than a stubbed process table. Each such case reaps its process in a
`finally`, and `case_it_kills_nothing` asserts the occupant is still alive after
the run, which is criterion 3's whole content.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-t1u criterion                             Pinned by
  ------------------------------------------------------------------------------
  2. An occupied worktree reports the pid       case_occupied_reports_the_pid
  3. It kills nothing                           case_it_kills_nothing
  3. It removes nothing                         case_it_removes_nothing
  4. Never warns about an empty worktree        case_unoccupied_is_silent

  Design decisions in the script's docstring:
  A subdirectory occupant counts                case_subdirectory_occupant_counts
  A shared string prefix does not               case_sibling_prefix_is_not_reported
  Both sides resolve before comparing           case_symlinked_path_is_found
  Operator error is 2, never 1                  case_missing_worktree_exits_2,
                                                case_nonexistent_path_exits_2,
                                                case_empty_worktree_argument_exits_2,
                                                case_lsof_missing_exits_2
  An empty lsof answer is an error, not "no"    case_lsof_silent_exits_2
  Stdlib only                                   case_no_third_party_imports
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_worktree_occupants.py"

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


def run(
    worktree: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--worktree", str(worktree)],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def occupy(directory: Path) -> subprocess.Popen:
    """A live process whose working directory is `directory`.

    `sleep` is the smallest thing that holds a cwd and does nothing else.
    """
    process = subprocess.Popen(["sleep", "30"], cwd=str(directory))
    # lsof cannot see a process the kernel has not finished publishing yet, and
    # the cases below assert on absence as well as presence, so a race here
    # would flip either verdict.
    time.sleep(0.15)
    return process


def temp_dir() -> Path:
    return Path(tempfile.mkdtemp()).resolve()


print("\n  [what an occupied worktree costs]")


def case_occupied_reports_the_pid() -> None:
    """Criterion 2. A live process in the worktree is reported by pid, exit 1."""
    worktree = temp_dir()
    process = occupy(worktree)
    try:
        result = run(worktree)
        assert result.returncode == 1, (
            f"occupied must exit 1, got {result.returncode}: {result.stderr}"
        )
        assert f"pid {process.pid}" in result.stdout, (
            f"must name the pid: {result.stdout!r}"
        )
        assert "WARNING" in result.stdout, f"must warn: {result.stdout!r}"
    finally:
        process.kill()
        process.wait()


def case_occupied_names_the_consequence() -> None:
    """Criterion 1's runtime half: the warning says what the operator loses."""
    worktree = temp_dir()
    process = occupy(worktree)
    try:
        result = run(worktree)
        assert "labels no bead" in result.stdout, (
            f"must name the consequence: {result.stdout!r}"
        )
    finally:
        process.kill()
        process.wait()


def case_it_kills_nothing() -> None:
    """Criterion 3. The occupant is still running after the check."""
    worktree = temp_dir()
    process = occupy(worktree)
    try:
        run(worktree)
        assert process.poll() is None, "the occupying process must still be alive"
    finally:
        process.kill()
        process.wait()


def case_it_removes_nothing() -> None:
    """Criterion 3. The worktree and its contents survive the check."""
    worktree = temp_dir()
    (worktree / "keep.txt").write_text("x", encoding="utf-8")
    process = occupy(worktree)
    try:
        run(worktree)
        assert worktree.is_dir(), "the worktree must survive"
        assert (worktree / "keep.txt").is_file(), "its contents must survive"
    finally:
        process.kill()
        process.wait()


for name, fn in [
    (
        "an occupied worktree reports the pid [criterion 2]",
        case_occupied_reports_the_pid,
    ),
    (
        "the warning names what the operator loses [criterion 1]",
        case_occupied_names_the_consequence,
    ),
    ("it kills nothing [criterion 3]", case_it_kills_nothing),
    ("it removes nothing [criterion 3]", case_it_removes_nothing),
]:
    check(name, fn)

print("\n  [what an empty worktree must not cost]")


def case_unoccupied_is_silent() -> None:
    """Criterion 4. Nobody there means exit 0 and no warning."""
    worktree = temp_dir()
    result = run(worktree)
    assert result.returncode == 0, (
        f"unoccupied must exit 0, got {result.returncode}: {result.stderr}"
    )
    assert "WARNING" not in result.stdout, f"must not warn: {result.stdout!r}"
    assert "OK:" in result.stdout, f"must say it checked: {result.stdout!r}"


def case_sibling_prefix_is_not_reported() -> None:
    """`/w/feature-2` shares a string prefix with `/w/feature` and is not in it."""
    parent = temp_dir()
    target = parent / "feature"
    sibling = parent / "feature-2"
    target.mkdir()
    sibling.mkdir()
    process = occupy(sibling)
    try:
        result = run(target)
        assert result.returncode == 0, (
            f"a sibling sharing a prefix must not count, got {result.returncode}: {result.stdout!r}"
        )
    finally:
        process.kill()
        process.wait()


for name, fn in [
    (
        "an unoccupied worktree exits 0 and does not warn [criterion 4]",
        case_unoccupied_is_silent,
    ),
    (
        "a sibling sharing a string prefix is not reported [criterion 4]",
        case_sibling_prefix_is_not_reported,
    ),
]:
    check(name, fn)

print("\n  [how a path is matched]")


def case_subdirectory_occupant_counts() -> None:
    """A process one level down is just as stranded as one at the root."""
    worktree = temp_dir()
    inner = worktree / "src" / "deep"
    inner.mkdir(parents=True)
    process = occupy(inner)
    try:
        result = run(worktree)
        assert result.returncode == 1, (
            f"a subdirectory occupant must count: {result.stdout!r}"
        )
        assert f"pid {process.pid}" in result.stdout, (
            f"must name the pid: {result.stdout!r}"
        )
    finally:
        process.kill()
        process.wait()


def case_symlinked_path_is_found() -> None:
    """A worktree reached through a symlink resolves to the same directory.

    This is the macOS `/tmp` to `/private/tmp` case. A string compare of the two
    spellings finds nothing, and the warning that should fire never does.
    """
    worktree = temp_dir()
    link_parent = temp_dir()
    link = link_parent / "via-link"
    link.symlink_to(worktree)
    process = occupy(worktree)
    try:
        result = run(link)
        assert result.returncode == 1, (
            f"a symlinked spelling must find the same occupant: {result.stdout!r}"
        )
    finally:
        process.kill()
        process.wait()


for name, fn in [
    ("a subdirectory occupant counts", case_subdirectory_occupant_counts),
    ("a symlinked spelling finds the same occupant", case_symlinked_path_is_found),
]:
    check(name, fn)

print("\n  [operator error is 2, never 1]")


def case_missing_worktree_exits_2() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True
    )
    assert result.returncode == 2, f"argparse must exit 2, got {result.returncode}"


def case_nonexistent_path_exits_2() -> None:
    result = run(Path(tempfile.mkdtemp()) / "not-here")
    assert result.returncode == 2, (
        f"a missing directory must exit 2, got {result.returncode}"
    )
    assert "ERROR" in result.stderr, f"must say why: {result.stderr!r}"


def case_empty_worktree_argument_exits_2() -> None:
    result = run("   ")
    assert result.returncode == 2, f"a blank path must exit 2, got {result.returncode}"


def case_lsof_missing_exits_2() -> None:
    """No lsof means no measurement, and a "nobody is there" answer would lie."""
    worktree = temp_dir()
    empty_path = tempfile.mkdtemp()
    result = run(worktree, env={"PATH": empty_path})
    assert result.returncode == 2, (
        f"a missing lsof must exit 2, never 0, got {result.returncode}: {result.stdout!r}"
    )
    assert "lsof" in result.stderr, f"must name what was missing: {result.stderr!r}"


def case_lsof_silent_exits_2() -> None:
    """An lsof that prints nothing is a failure, not an empty worktree."""
    worktree = temp_dir()
    stub_dir = Path(tempfile.mkdtemp())
    stub = stub_dir / "lsof"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    result = run(worktree, env={"PATH": f"{stub_dir}:{os.environ['PATH']}"})
    assert result.returncode == 2, (
        f"a silent lsof must exit 2, never 0, got {result.returncode}: {result.stdout!r}"
    )


for name, fn in [
    ("a missing --worktree exits 2", case_missing_worktree_exits_2),
    ("a path that is not a directory exits 2", case_nonexistent_path_exits_2),
    ("a blank --worktree exits 2", case_empty_worktree_argument_exits_2),
    ("lsof missing from PATH exits 2, never 0", case_lsof_missing_exits_2),
    ("an lsof that prints nothing exits 2, never 0", case_lsof_silent_exits_2),
]:
    check(name, fn)

print("\n  [the shape of the file itself]")


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__",
        "argparse",
        "os",
        "re",
        "shutil",
        "subprocess",
        "sys",
        "tempfile",
        "time",
        "pathlib",
    }
    for path in (SCRIPT, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(
            re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M)
        )
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)

print(
    f"\nAll {passed} checks passed."
    if not failed
    else f"\n{failed} FAILED, {passed} passed."
)
sys.exit(1 if failed else 0)
