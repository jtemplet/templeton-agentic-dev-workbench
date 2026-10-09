"""The one place the ship scripts start git.

Each function takes a directory and the git arguments, runs `git -C <directory> ...` with
captured text output, and returns that output verbatim. Callers strip it themselves.

  run   the CompletedProcess; a non-zero exit is the caller's to read
  read  stdout; a non-zero exit raises GitFailed
  ask   stdout, or None on a non-zero exit, for commands where "no" is an answer

A missing git raises GitUnavailable from all three, because no git is a failure and not an answer.

Both errors derive from GitProcessError, so one `except` clause names every way git can fail. Each
script loads this module with its own `load_sibling`, which returns the module already registered
for this directory, so every ship script catches the same classes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitProcessError(RuntimeError):
    """git could not be run, or ran and exited non-zero."""


class GitUnavailable(GitProcessError):
    """git is not on PATH."""


class GitFailed(GitProcessError):
    """git ran and exited non-zero."""

    def __init__(self, arguments: tuple[str, ...], returncode: int, stdout: str, stderr: str):
        detail = stderr.strip() or f"exit {returncode}"
        super().__init__(f"git {' '.join(arguments)}: {detail}")
        self.arguments = arguments
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run(directory: Path, *arguments: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise GitUnavailable("git is not on PATH") from error


def read(directory: Path, *arguments: str) -> str:
    completed = run(directory, *arguments)
    if completed.returncode != 0:
        raise GitFailed(arguments, completed.returncode, completed.stdout, completed.stderr)
    return completed.stdout


def ask(directory: Path, *arguments: str) -> str | None:
    completed = run(directory, *arguments)
    return None if completed.returncode != 0 else completed.stdout
