#!/usr/bin/env python3
"""Record what a ship run has changed, so an interrupted run can resume from verified state.

Closing a bead and publishing a commit share no transaction (tadw-dur4). A run
stopped between the two leaves a closed bead with no landing, or a landing with
no push, and nothing else remembers which. This module is that memory.

THE RECORD LIVES IN THE COMMON GIT DIRECTORY, at `<git-common-dir>/tadw-ship/`.
Every worktree shares that directory, and cleanup removes only worktrees, so no
step of a ship can delete its own record.

THE STATE IS WRITTEN BEFORE AND AFTER EACH MUTATION. A record read back after an
interruption names the last step that surely finished, and the one that may have
started. Recovery (ship_recovery.py) re-reads the repository and the tracker to
learn which, and never trusts the record alone.

THE CANDIDATE IS KEPT UNDER `refs/tadw-ship/`. The temporary worktree is removed
on every path, so a ref is what keeps a retained candidate commit reachable.

ONE RUN AT A TIME. `exclusive_run` takes an exclusive `flock` on a lock file
beside the record. The kernel releases it when the process ends, however it
ends, so a killed run never leaves a stale lock behind.
"""

from __future__ import annotations

import contextlib
import dataclasses
import fcntl
import json
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import IO

VERSION = 1
STATE_DIRECTORY = "tadw-ship"
RECORD_NAME = "progress.json"
LOCK_NAME = "lock"
CANDIDATE_REF = "refs/tadw-ship/candidate"
LANDING_REF = "refs/tadw-ship/landing"

# The states, in the order a run passes through them. REOPENED follows a close
# this run reversed. A rebuild passes through STARTED and CANDIDATE again while
# its close stands, so a recorded close needs recovery in every state.
STARTED = "started"
CANDIDATE = "candidate"
CLOSING = "closing"
CLOSED = "closed"
LANDING = "landing"
LANDED = "landed"
PUSHED = "pushed"
REOPENED = "reopened"
STATES = (STARTED, CANDIDATE, CLOSING, CLOSED, LANDING, LANDED, PUSHED, REOPENED)
NEEDS_RECOVERY = frozenset({CLOSING, CLOSED, LANDING, LANDED, PUSHED})


class ShipBusy(Exception):
    """Another ship run holds this repository's lock."""


class ProgressUnreadable(Exception):
    """A record exists but cannot be trusted; recovery stops rather than guess."""


@dataclasses.dataclass(frozen=True)
class BeadClose:
    """The tracker fields that identify one close: a later close or edit changes them."""

    status: str
    closed_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_show(cls, record: dict) -> BeadClose:
        return cls(record["status"], record.get("closed_at"), record.get("updated_at"))

    def describe(self) -> str:
        if self.closed_at is None:
            return self.status
        return f"{self.status} (closed_at {self.closed_at}, updated_at {self.updated_at})"


@dataclasses.dataclass(frozen=True)
class Progress:
    """One run's record. Each field is filled in by the step that learns it."""

    run_id: str
    state: str
    branch: str
    default_branch: str
    bead_id: str | None = None
    bead_title: str | None = None
    bead_type: str | None = None
    parent: str | None = None
    branch_tip: str | None = None
    candidate_worktree: str | None = None
    checked_commit: str | None = None
    landing_commit: str | None = None
    close: BeadClose | None = None

    @classmethod
    def begin(cls, branch: str, default_branch: str, **bead: str | None) -> Progress:
        return cls(uuid.uuid4().hex, STARTED, branch, default_branch, **bead)

    def needs_recovery(self) -> bool:
        return self.state in NEEDS_RECOVERY or self.close is not None

    def holds_unlanded_close(self) -> bool:
        """This run's close stands, and no landing of it has reached the default branch."""
        return self.close is not None and self.state not in (LANDING, LANDED, PUSHED)


class ProgressStore:
    """The record for one repository, with the refs that keep its candidate reachable."""

    def __init__(self, git_common_dir: Path) -> None:
        self.git_common_dir = Path(git_common_dir)
        self.current: Progress | None = None

    @property
    def directory(self) -> Path:
        return self.git_common_dir / STATE_DIRECTORY

    @property
    def path(self) -> Path:
        return self.directory / RECORD_NAME

    def load(self) -> Progress | None:
        if not self.path.exists():
            return None
        try:
            self.current = parse_record(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ProgressUnreadable(f"{self.path}: {error}") from error
        return self.current

    def mark(self, state: str, **facts: object) -> None:
        """Move the current record to `state`, adding what the step just learned."""
        self.save(dataclasses.replace(self.current, state=state, **facts))

    def save(self, progress: Progress) -> None:
        if progress.state not in STATES:
            raise ValueError(f"unknown ship state {progress.state!r}")
        keep_reachable(self.git_common_dir, self.current, progress)
        write_atomically(self.path, json.dumps(record_of(progress), indent=2) + "\n")
        self.current = progress

    def clear(self) -> None:
        for ref in (CANDIDATE_REF, LANDING_REF):
            git(self.git_common_dir, "update-ref", "-d", ref)
        with contextlib.suppress(FileNotFoundError):
            self.path.unlink()
        self.current = None


@contextlib.contextmanager
def exclusive_run(store: ProgressStore) -> Iterator[None]:
    """Hold the repository's ship lock for the body; raise `ShipBusy` when another run has it."""
    store.directory.mkdir(parents=True, exist_ok=True)
    lock = store.directory / LOCK_NAME
    with lock.open("a", encoding="utf-8") as handle:
        take_lock(handle, lock)
        yield


def take_lock(handle: IO[str], lock: Path) -> None:
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise ShipBusy(f"another tadw-ship run holds {lock}") from error


def write_atomically(path: Path, text: str) -> None:
    """A reader never sees half a record: the new one replaces the old in one rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    written = path.with_suffix(".tmp")
    written.write_text(text, encoding="utf-8")
    written.replace(path)


def record_of(progress: Progress) -> dict:
    return {"version": VERSION, **dataclasses.asdict(progress)}


def parse_record(document: dict) -> Progress:
    if document.pop("version") != VERSION:
        raise ValueError("unknown record version")
    close = document.pop("close")
    progress = Progress(**document, close=None if close is None else BeadClose(**close))
    if progress.state not in STATES:
        raise ValueError(f"unknown ship state {progress.state!r}")
    return progress


def keep_reachable(git_common_dir: Path, before: Progress | None, after: Progress) -> None:
    """Point each ref at its commit, touching only a ref whose commit changed."""
    for ref, field in ((CANDIDATE_REF, "checked_commit"), (LANDING_REF, "landing_commit")):
        commit = getattr(after, field)
        if commit is not None and commit != getattr(before, field, None):
            git(git_common_dir, "update-ref", ref, commit)


def git(git_common_dir: Path, *arguments: str) -> None:
    """Ref upkeep is best effort: the record, not the ref, is what recovery reads first."""
    with contextlib.suppress(FileNotFoundError):
        subprocess.run(
            ["git", f"--git-dir={git_common_dir}", *arguments],
            capture_output=True,
            check=False,
        )
