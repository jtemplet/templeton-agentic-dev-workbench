#!/usr/bin/env python3
"""Regression suite for worktree_cleanup.py.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_worktree_cleanup.py

Every case builds a real repository with real linked worktrees in a temporary
directory, because the behavior under test is what git removes and where the
process stands afterward. A scenario several cases read is built once and cached,
because its result is immutable.

  tadw-kgql criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. A caller who started inside a removed          case_start_inside_a_removed_worktree_gets_a_cd,
     worktree gets `cd <stable-path>` before the    case_start_in_the_worktree_root_gets_a_cd,
     final machine line (the line itself, and its   case_relative_start_still_gets_a_cd
     place, are pinned in test_ship_report.py)
  2. A caller who started outside every removed     case_start_in_the_stable_checkout_gets_no_cd,
     worktree gets no `cd` line                     case_start_in_a_kept_worktree_gets_no_cd
  3. No stable checkout: named reason, raised       case_bare_main_worktree_has_no_stable_checkout,
     before any mutation (the runner's stop is      case_non_repository_has_no_stable_checkout,
     pinned in test_tadw_ship.py)                   case_main_inside_a_linked_worktree_is_not_stable,
                                                    case_deleted_separate_git_dir_main_is_not_stable

  Design decisions in the module docstring
  ------------------------------------------------------------------------------
  The stable checkout is the main worktree          case_stable_checkout_is_the_main_worktree
  The process moves to the stable checkout          case_process_stands_in_the_stable_checkout
  Occupants are reported, then removed anyway       case_occupant_is_reported_and_removed,
                                                    case_unmeasurable_occupants_are_said
  Occupants are measured once per cleanup           case_occupants_are_measured_once
  A worktree with changes is left behind            case_dirty_worktree_is_left_behind
  Paths are resolved before the process moves       case_relative_start_still_gets_a_cd,
                                                    case_relative_worktree_path_is_removed
"""

from __future__ import annotations

import contextlib
import functools
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

HERE = Path(__file__).resolve().parent


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


worktree_cleanup = load("worktree_cleanup")

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


def git(directory: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True, check=True
    ).stdout


def nobody_stands_anywhere() -> dict[int, str]:
    return {}


@contextlib.contextmanager
def repository() -> Iterator[Path]:
    """A main checkout with one commit, restoring this process's directory afterward."""
    before = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        main = Path(directory).resolve() / "main"
        subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True)
        git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
            "-m", "base")  # fmt: skip
        try:
            yield main
        finally:
            os.chdir(before)


def add_worktree(main: Path, name: str) -> Path:
    path = main.parent / name
    git(main, "worktree", "add", "-q", "-b", name, str(path))
    (path / "sub").mkdir()
    return path


class Cleaned(NamedTuple):
    stable: Path
    cleanup: worktree_cleanup.Cleanup
    cwd: Path


@functools.cache
def cleaned(start_in: str) -> Cleaned:
    """Remove the `feature` worktree, starting in `start_in` relative to the temporary root."""
    with repository() as main:
        for name in ("feature", "other"):
            add_worktree(main, name)
        start = main.parent / start_in
        stable = worktree_cleanup.stable_checkout(start)
        cleanup = worktree_cleanup.remove_worktrees(
            [main.parent / "feature"], stable, start, nobody_stands_anywhere
        )
        return Cleaned(stable, cleanup, Path.cwd())


@functools.cache
def cleaned_from_relative_paths() -> Cleaned:
    """Stand in `feature/sub`, then name the start as `.` and the worktree as `..`."""
    with repository() as main:
        add_worktree(main, "feature")
        os.chdir(main.parent / "feature" / "sub")
        cleanup = worktree_cleanup.remove_worktrees(
            [Path("..")], main, Path(), nobody_stands_anywhere
        )
        return Cleaned(main, cleanup, Path.cwd())


def assert_cd_to_stable(run: Cleaned, start_in: str) -> None:
    assert run.cleanup.cd_target == run.stable, (
        f"starting in {start_in}: expected {run.stable}, got {run.cleanup.cd_target}"
    )


def assert_no_stable_checkout(repo: Path, reason: str) -> None:
    try:
        worktree_cleanup.stable_checkout(repo)
    except worktree_cleanup.NoStableCheckout as missing:
        assert reason in str(missing), str(missing)
    else:
        raise AssertionError(f"{repo} must not have a stable checkout")


def case_start_inside_a_removed_worktree_gets_a_cd() -> None:
    assert_cd_to_stable(cleaned("feature/sub"), "feature/sub")


def case_start_in_the_worktree_root_gets_a_cd() -> None:
    assert_cd_to_stable(cleaned("feature"), "feature")


def case_relative_start_still_gets_a_cd() -> None:
    assert_cd_to_stable(cleaned_from_relative_paths(), "feature/sub, named as .")


def case_relative_worktree_path_is_removed() -> None:
    lines = cleaned_from_relative_paths().cleanup.lines
    assert any("removed the worktree" in line for line in lines), lines


def case_start_in_the_stable_checkout_gets_no_cd() -> None:
    cd_target = cleaned("main").cleanup.cd_target
    assert cd_target is None, f"expected no cd target, got {cd_target}"


def case_start_in_a_kept_worktree_gets_no_cd() -> None:
    cd_target = cleaned("other/sub").cleanup.cd_target
    assert cd_target is None, f"expected no cd target, got {cd_target}"


def case_stable_checkout_is_the_main_worktree() -> None:
    with repository() as main:
        feature = add_worktree(main, "feature")
        assert worktree_cleanup.stable_checkout(feature / "sub") == main


def case_process_stands_in_the_stable_checkout() -> None:
    run = cleaned("feature/sub")
    assert run.cwd == run.stable, f"expected the process in {run.stable}, found {run.cwd}"


def case_bare_main_worktree_has_no_stable_checkout() -> None:
    with repository() as main:
        bare = main.parent / "bare.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(main), str(bare)], check=True)
        linked = main.parent / "linked"
        git(bare, "worktree", "add", "-q", str(linked), "main")
        assert_no_stable_checkout(linked, "is bare")


def case_non_repository_has_no_stable_checkout() -> None:
    with tempfile.TemporaryDirectory() as directory:
        assert_no_stable_checkout(Path(directory), "not a repository")


def case_main_inside_a_linked_worktree_is_not_stable() -> None:
    with repository() as main:
        outer = add_worktree(main, "outer")
        nested = outer / "main"
        main.rename(nested)
        git(nested, "worktree", "repair")
        assert_no_stable_checkout(nested, "sits inside the linked worktree")


def case_deleted_separate_git_dir_main_is_not_stable() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        main = root / "main"
        subprocess.run(["git", "init", "-q", "--separate-git-dir", str(root / "gitdir"), str(main)],
                       check=True)  # fmt: skip
        git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
            "-m", "base")  # fmt: skip
        linked = add_worktree(main, "linked")
        shutil.rmtree(main)
        assert_no_stable_checkout(linked, "the main checkout was deleted")


def case_occupant_is_reported_and_removed() -> None:
    with repository() as main:
        feature = add_worktree(main, "feature")
        cleanup = worktree_cleanup.remove_worktrees(
            [feature], main, main, lambda: {4242: str(feature / "sub")}
        )
        assert any("pid 4242" in line for line in cleanup.lines), cleanup.lines
        assert not feature.exists(), "an occupied worktree is still removed"


def case_unmeasurable_occupants_are_said() -> None:
    def lsof_missing() -> dict[int, str]:
        raise worktree_cleanup.check_worktree_occupants.LsofUnavailable("lsof is not on PATH")

    with repository() as main:
        feature = add_worktree(main, "feature")
        cleanup = worktree_cleanup.remove_worktrees([feature], main, main, lsof_missing)
        assert any("could not check who stands" in line for line in cleanup.lines), cleanup.lines
        assert not feature.exists(), "an unmeasured worktree is still removed"


def case_occupants_are_measured_once() -> None:
    measured = []

    def counting_process_cwds() -> dict[int, str]:
        measured.append(1)
        return {}

    with repository() as main:
        worktrees = [add_worktree(main, name) for name in ("feature", "other")]
        worktree_cleanup.remove_worktrees(worktrees, main, main, counting_process_cwds)
    assert len(measured) == 1, f"expected one lsof pass for two worktrees, got {len(measured)}"


def case_dirty_worktree_is_left_behind() -> None:
    with repository() as main:
        feature = add_worktree(main, "feature")
        (feature / "notes.txt").write_text("unsaved work\n")
        cleanup = worktree_cleanup.remove_worktrees(
            [feature], main, feature, nobody_stands_anywhere
        )
        assert feature.exists(), "git must refuse a worktree with changes"
        assert any("left the worktree" in line for line in cleanup.lines), cleanup.lines
        assert cleanup.cd_target is None, "a caller whose directory survived needs no cd"


for name, fn in [
    ("a caller inside a removed worktree gets a cd target",
     case_start_inside_a_removed_worktree_gets_a_cd),
    ("a caller in the worktree root gets a cd target", case_start_in_the_worktree_root_gets_a_cd),
    ("a caller in the stable checkout gets no cd line",
     case_start_in_the_stable_checkout_gets_no_cd),
    ("a caller in a kept worktree gets no cd line", case_start_in_a_kept_worktree_gets_no_cd),
    ("the stable checkout is the main worktree", case_stable_checkout_is_the_main_worktree),
    ("the process stands in the stable checkout after cleanup",
     case_process_stands_in_the_stable_checkout),
    ("a bare main worktree is no stable checkout",
     case_bare_main_worktree_has_no_stable_checkout),
    ("a directory outside git has no stable checkout",
     case_non_repository_has_no_stable_checkout),
    ("a main worktree inside a linked worktree is not stable",
     case_main_inside_a_linked_worktree_is_not_stable),
    ("a deleted main checkout under a separate git directory is not stable",
     case_deleted_separate_git_dir_main_is_not_stable),
    ("a relative start directory still gets a cd target", case_relative_start_still_gets_a_cd),
    ("a relative worktree path is removed", case_relative_worktree_path_is_removed),
    ("an occupant is reported, and the worktree is removed anyway",
     case_occupant_is_reported_and_removed),
    ("occupants that cannot be measured are said so", case_unmeasurable_occupants_are_said),
    ("occupants are measured once per cleanup", case_occupants_are_measured_once),
    ("a worktree with changes is left behind", case_dirty_worktree_is_left_behind),
]:  # fmt: skip
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
