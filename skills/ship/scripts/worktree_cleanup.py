#!/usr/bin/env python3
"""Remove ship's worktrees from a checkout that survives, and say where the caller must go.

A child process cannot change its parent shell's directory. So when ship removes
the worktree its caller started in, the caller's shell is left standing in a
directory that no longer exists, and only the caller can move it. This module
moves the Python process to a stable checkout before it removes anything, and
returns that checkout as the `cd` target when the starting directory was inside
a removed worktree. `ship_report.render` prints the target before the machine
line.

THE STABLE CHECKOUT IS THE MAIN WORKTREE. Git never removes the main worktree
with `git worktree remove`, so it outlives every worktree ship may remove. A
bare repository has no main checkout, and a main worktree whose directory is
gone cannot hold a shell, so both stop the run. `stable_checkout` is called
before the first Git or tracker mutation, so such a stop changes nothing.

OCCUPANTS ARE REPORTED, THEN THE WORKTREE IS REMOVED ANYWAY. The process
standing in a worktree is usually this run's own caller, so a live process is a
warning, never a refusal. `git worktree remove` still refuses a worktree with
changes, and that worktree is reported as left behind.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
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
    """What the removal did, and where the caller must go when it removed their directory."""

    lines: tuple[str, ...]
    cd_target: Path | None


def stable_checkout(repo: Path) -> Path:
    worktrees = resolve_ground.read_worktrees(repo)
    if not worktrees:
        raise NoStableCheckout(f"git lists no worktree for {repo}, so it is not a repository")
    main = worktrees[0]
    path = Path(main["path"]).resolve()
    if main["bare"]:
        raise NoStableCheckout(
            f"the main worktree {path} is bare, so no checkout outlives the worktree removal"
        )
    if not path.is_dir():
        raise NoStableCheckout(f"the main worktree {path} does not exist on disk")
    linked = (Path(worktree["path"]).resolve() for worktree in worktrees[1:])
    holder = next((directory for directory in linked if path.is_relative_to(directory)), None)
    if holder is not None:
        raise NoStableCheckout(
            f"the main worktree {path} sits inside the linked worktree {holder}, "
            "so removing that worktree would remove it too"
        )
    return path


def remove_worktrees(
    worktrees: Sequence[Path],
    stable: Path,
    start: Path,
    process_cwds: ProcessCwds = check_worktree_occupants.process_cwds,
) -> Cleanup:
    """Move to `stable`, then remove each worktree, reporting who stood in it first.

    `start` is the directory the run started in. Every path is resolved before the
    `chdir`, because a relative path means something else once the process has moved.
    """
    start = start.resolve()
    targets = [path.resolve() for path in worktrees]
    os.chdir(stable)
    snapshot = occupancy_snapshot(process_cwds)
    lines: list[str] = []
    removed: list[Path] = []
    for worktree in targets:
        lines.extend(occupant_lines(worktree, snapshot))
        refusal = git_worktree_remove(stable, worktree)
        if refusal is None:
            removed.append(worktree)
            lines.append(f"tadw_ship: removed the worktree {worktree}")
        else:
            lines.append(f"tadw_ship: left the worktree {worktree} behind: {refusal}")
    started_in_removed = any(start.is_relative_to(worktree) for worktree in removed)
    return Cleanup(tuple(lines), stable if started_in_removed else None)


def occupancy_snapshot(
    process_cwds: ProcessCwds,
) -> dict[int, str] | check_worktree_occupants.LsofUnavailable:
    """One `lsof` pass for every worktree, because removing one moves no other process."""
    try:
        return process_cwds()
    except check_worktree_occupants.LsofUnavailable as error:
        return error


def occupant_lines(
    worktree: Path, snapshot: dict[int, str] | check_worktree_occupants.LsofUnavailable
) -> list[str]:
    if isinstance(snapshot, check_worktree_occupants.LsofUnavailable):
        return [f"tadw_ship: could not check who stands in {worktree}: {snapshot}"]
    found = check_worktree_occupants.occupants(worktree, snapshot)
    return [
        f"tadw_ship: pid {pid} ({check_worktree_occupants.command_name(pid)}) stands in "
        f"{cwd}, and removing {worktree} does not stop it"
        for pid, cwd in found
    ]


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
