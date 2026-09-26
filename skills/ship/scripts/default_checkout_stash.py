#!/usr/bin/env python3
"""Set aside a dirty default-branch checkout for the length of a ship, then put it back.

The landing fast-forwards the default branch inside the checkout that holds it, and git
refuses that over changed tracked files. The candidate is built and gated in a temporary
worktree, so those changes never reach the checked tree. Ship therefore stashes them
before the first step and restores them after the last, whatever the run's outcome.

ONLY THE CHANGED TRACKED FILES MOVE. An untracked file blocks nothing, so it stays put.
The tracker export is left out as well: `bd` rewrites it from any worktree, the landing
already restores it (candidate.restore_stale_export), and popping a stale copy over the
landed one would conflict.

A RESTORE THAT CONFLICTS KEEPS THE STASH. The landing has already happened by then, so the
run still ends as it would have, with a warning naming the stash commit to apply by hand.
The stash is popped only when it is still the newest entry, because popping some other
entry would restore work that was never ours.
"""

from __future__ import annotations

import contextlib
import importlib.util
import sys
from collections.abc import Callable, Iterator
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


candidate = load_sibling("candidate")
resolve_ground = load_sibling("resolve_ground")

STASH_REFERENCE = "refs/stash"
Report = Callable[[str], None]


@dataclass(frozen=True)
class Stash:
    """The entry ship created: where it was made, and the commit that identifies it."""

    holder: Path
    commit: str
    paths: tuple[str, ...]


@contextlib.contextmanager
def default_checkout_set_aside(
    holder: str | None, default_branch: str, report: Report
) -> Iterator[Stash | None]:
    """Stash the holder's changed tracked files, run the body, and restore them on the way out.

    Raises `candidate.CandidateStop` before the body runs when the stash cannot be made,
    so nothing has moved yet.
    """
    stash = set_aside(holder, default_branch)
    if stash is not None:
        report(f"stashed {len(stash.paths)} changed file(s) in {stash.holder} for the ship")
    try:
        yield stash
    finally:
        if stash is not None:
            report(restore(stash))


def set_aside(holder: str | None, default_branch: str) -> Stash | None:
    """None when there is no holder or nothing to move; an unreadable status stops later."""
    if holder is None:
        return None
    directory = Path(holder)
    paths = movable_changes(directory)
    if not paths:
        return None
    message = f"tadw-ship: {default_branch} changes held during the ship"
    candidate.git(directory, "stash", "push", "--quiet", "-m", message, "--", *paths)
    return Stash(directory, candidate.resolve_commit(directory, STASH_REFERENCE), tuple(paths))


def movable_changes(directory: Path) -> list[str]:
    changed = resolve_ground.read_status(directory, untracked=False)
    return [path for path in changed or [] if path != candidate.EXPORT_PATH]


def restore(stash: Stash) -> str:
    """The report line: restored, or a warning that names the commit left in the stash."""
    newest = candidate.git_or_none(
        stash.holder, "rev-parse", "--verify", "--quiet", STASH_REFERENCE
    )
    if newest != stash.commit:
        return keep_line(stash, "another stash entry was made meanwhile")
    popped = candidate.run_git(stash.holder, ("stash", "pop", "--quiet", "--index"))
    if popped.returncode != 0:
        detail = (popped.stderr or popped.stdout).strip().splitlines()
        return keep_line(stash, detail[-1] if detail else "git stash pop failed")
    return f"restored {len(stash.paths)} changed file(s) in {stash.holder}, staged state kept"


def keep_line(stash: Stash, reason: str) -> str:
    return (
        f"warning: could not restore the changes stashed in {stash.holder}: {reason}; "
        f"they are kept as stash commit {stash.commit[:12]}; run "
        f"`git stash apply {stash.commit[:12]}` there"
    )
