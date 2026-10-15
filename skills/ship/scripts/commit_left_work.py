#!/usr/bin/env python3
"""Commit the work a feature branch left uncommitted, so the landing carries it.

Ship used to stop on a modified tracked file (`dirty-tracked`), so every author
had to commit and run ship again. An untracked file never stopped it, so a new
file nobody added was left out of the landing, and it later made
`git worktree remove` refuse. Both now go into one commit on the feature branch
before ship reads its ground. The subject does not matter: ship squashes the
branch, and the default branch gets the bead's title.

It acts only where the ground reports no stop or `dirty-tracked`. The stop order
puts every condition that makes a commit wrong ahead of that one: the default
branch, a detached HEAD, an operation in progress, and an unreadable status.
Ignored files never appear in the status it reads.

A path whose name looks like a secret stops the run before anything is staged.
The commit runs through the repository's hooks, because a commit they refuse is
one the author would have been refused too. A refused commit leaves nothing
staged.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path, PurePosixPath
from types import ModuleType


# Each ship script carries this loader: a shared one would itself have to be loaded by path.
def load_sibling(name: str) -> ModuleType:
    """Load a helper from this file's own directory, never from another installed copy.

    A helper already registered from that file is returned as it is, so every script shares one
    set of classes."""
    path = Path(__file__).resolve().parent / f"{name}.py"
    loaded = sys.modules.get(name)
    if loaded is not None and Path(getattr(loaded, "__file__", "")).resolve() == path:
        return loaded
    return execute_sibling(name, path)


def execute_sibling(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


git_process = load_sibling("git_process")
resolve_ground = load_sibling("resolve_ground")

SUBJECT = "chore: commit the work left uncommitted at ship"
COMMITTABLE_STOPS = (None, "dirty-tracked")
SECRET_SUFFIXES = (".pem", ".p8", ".p12", ".key")
# `.env.example` and its kin are the documented shape of a secret, not a secret.
TEMPLATE_SUFFIXES = (".example", ".sample", ".template")


class LeftWorkStop(Exception):
    """The left work was not committed, and nothing was staged."""


def commit_left_work(repo: Path) -> list[str]:
    """Commit every modified and untracked path, and return them; [] when there were none."""
    paths = left_paths(resolve_ground.resolve_ground(repo))
    if paths:
        refuse_secrets(paths)
        commit(repo, paths)
    return paths


def left_paths(ground: dict) -> list[str]:
    if ground["stop"] not in COMMITTABLE_STOPS:
        return []
    return sorted({*ground["dirty_tracked"], *ground["untracked"]})


def refuse_secrets(paths: list[str]) -> None:
    secrets = [path for path in paths if looks_secret(path)]
    if secrets:
        raise LeftWorkStop(
            f"the uncommitted work includes a path that looks like a secret: {', '.join(secrets)}. "
            "Commit it, ignore it, or remove it by hand, then run ship again."
        )


def looks_secret(path: str) -> bool:
    name = PurePosixPath(path).name
    if name.endswith(TEMPLATE_SUFFIXES):
        return False
    return name == ".env" or name.startswith(".env.") or name.endswith(SECRET_SUFFIXES)


def commit(repo: Path, paths: list[str]) -> None:
    git_process.read(repo, "add", "--", *paths)
    completed = git_process.run(repo, "commit", "--quiet", "-m", SUBJECT)
    if completed.returncode != 0:
        git_process.run(repo, "reset", "--quiet", "--", *paths)
        detail = (completed.stderr or completed.stdout).strip()
        raise LeftWorkStop(f"the commit of the uncommitted work was refused: {detail}")
