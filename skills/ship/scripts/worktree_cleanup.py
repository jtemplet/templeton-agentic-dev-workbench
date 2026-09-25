#!/usr/bin/env python3
"""Remove ship's worktrees from a checkout that survives, and say where the caller must go.

A child process cannot change its parent shell's directory. When ship removes the
worktree its caller started in, the caller's shell is left in a directory that no
longer exists, and only the caller can move it. So this module moves the Python
process to the stable checkout first, and returns that checkout as the `cd` target.

The stable checkout is the main worktree, because `git worktree remove` never
removes it. A process standing in a worktree is reported, never obeyed: it is
usually this run's own caller.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


# Each ship script carries this loader: a shared one would itself have to be loaded by path.
def load_sibling(name: str) -> ModuleType:
    """Load a helper from this file's own directory, never from another installed copy."""
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resolve_ground = load_sibling("resolve_ground")
check_worktree_occupants = load_sibling("check_worktree_occupants")

ProcessCwds = Callable[[], dict[int, str]]


class NoStableCheckout(Exception):
    """No checkout outlives every worktree ship may remove, so the run must stop first."""


@dataclass(frozen=True)
class Cleanup:
    lines: tuple[str, ...]
    cd_target: Path | None


@dataclass(frozen=True)
class Removal:
    worktree: Path
    refusal: str | None

    @property
    def removed(self) -> bool:
        return self.refusal is None

    def line(self) -> str:
        if self.removed:
            return f"tadw_ship: removed the worktree {self.worktree}"
        return f"tadw_ship: left the worktree {self.worktree} behind: {self.refusal}"


def stable_checkout(repo: Path) -> Path:
    worktrees = resolve_ground.read_worktrees(repo)
    require_repository(repo, worktrees)
    main_path = Path(worktrees[0]["path"]).resolve()
    require_usable_main(repo, worktrees[0], main_path)
    require_outside_linked_worktrees(main_path, linked_worktree_paths(worktrees))
    return main_path


def remove_worktrees(
    worktrees: Sequence[Path],
    stable: Path,
    start: Path,
    process_cwds: ProcessCwds = check_worktree_occupants.process_cwds,
) -> Cleanup:
    # Resolve before the chdir: a relative path means something else once the process moves.
    start = start.resolve()
    targets = resolved(worktrees)
    os.chdir(stable)
    warnings = occupant_warnings(targets, measure_occupancy(process_cwds))
    removals = [remove_worktree(stable, worktree) for worktree in targets]
    return Cleanup(
        (*warnings, *(removal.line() for removal in removals)),
        cd_target(start, removals, stable),
    )


def require_repository(repo: Path, worktrees: list[dict]) -> None:
    if not worktrees:
        raise NoStableCheckout(f"git lists no worktree for {repo}, so it is not a repository")


def require_usable_main(repo: Path, main: dict, main_path: Path) -> None:
    """The main worktree must be a checkout, because the caller is sent there."""
    if main["bare"]:
        raise NoStableCheckout(
            f"the main worktree {main_path} is bare, so no checkout outlives the worktree removal"
        )
    # With --separate-git-dir, a deleted main checkout is listed as its git directory.
    if str(main_path) == resolve_ground.absolute_git_path(repo, "rev-parse", "--git-common-dir"):
        raise NoStableCheckout(
            f"the main checkout was deleted, and git lists its git directory {main_path} instead"
        )


def linked_worktree_paths(worktrees: list[dict]) -> list[Path]:
    return resolved(Path(worktree["path"]) for worktree in worktrees[1:])


def require_outside_linked_worktrees(main: Path, linked: list[Path]) -> None:
    for worktree in linked:
        if main.is_relative_to(worktree):
            raise NoStableCheckout(
                f"the main worktree {main} sits inside the linked worktree {worktree}, "
                "so removing that worktree would remove it too"
            )


def resolved(paths: Iterable[Path]) -> list[Path]:
    return [path.resolve() for path in paths]


def occupant_warnings(worktrees: list[Path], occupancy: Occupancy) -> list[str]:
    return [line for worktree in worktrees for line in occupancy.report(worktree)]


def remove_worktree(stable: Path, worktree: Path) -> Removal:
    return Removal(worktree, git_worktree_remove(stable, worktree))


def cd_target(start: Path, removals: list[Removal], stable: Path) -> Path | None:
    if any(removal.removed and start.is_relative_to(removal.worktree) for removal in removals):
        return stable
    return None


class MeasuredOccupancy:
    """One `lsof` snapshot serves every worktree, because removing one moves no process."""

    def __init__(self, cwds: dict[int, str]) -> None:
        self.cwds = cwds

    def report(self, worktree: Path) -> list[str]:
        return [
            f"tadw_ship: pid {pid} ({check_worktree_occupants.command_name(pid)}) stands in "
            f"{cwd}, and removing {worktree} does not stop it"
            for pid, cwd in check_worktree_occupants.occupants(worktree, self.cwds)
        ]


class UnmeasuredOccupancy:
    def __init__(self, reason: check_worktree_occupants.LsofUnavailable) -> None:
        self.reason = reason

    def report(self, worktree: Path) -> list[str]:
        return [f"tadw_ship: could not check who stands in {worktree}: {self.reason}"]


Occupancy = MeasuredOccupancy | UnmeasuredOccupancy


def measure_occupancy(process_cwds: ProcessCwds) -> Occupancy:
    try:
        return MeasuredOccupancy(process_cwds())
    except check_worktree_occupants.LsofUnavailable as reason:
        return UnmeasuredOccupancy(reason)


def git_worktree_remove(stable: Path, worktree: Path) -> str | None:
    """None when git removed the worktree, or git's own reason for refusing."""
    completed = subprocess.run(
        ["git", "-C", str(stable), "worktree", "remove", str(worktree)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return None
    return completed.stderr.strip() or f"git worktree remove exited {completed.returncode}"
