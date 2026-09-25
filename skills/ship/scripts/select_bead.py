#!/usr/bin/env python3
"""Choose the one bead a ship closes, or say why it ships bead-free or stops.

The ship skill told the model to verify each branch candidate with `bd show`
and "take the first that resolves", and in the next table to stop when "two or
more resolve". Both cannot hold: `bd` accepts a short id, so the candidates
`a7r` and `tadw-a7r` from one branch name both resolve, to the same bead. Taking
the first hid real ambiguity, and stopping on the second stopped ships that had
exactly one bead. This module decides by canonical id instead.

THE ORDER. An explicit id, when the caller gave one, and nothing else is looked
up. Then the branch-name candidates resolve_ground.py proposes. The plan puts a
stored branch mapping between the two; where it lives and who writes it is
still an open question in docs/plans/feature-plan-deterministic-ship.md, so it
is not read here until that is settled.

WHAT STOPS AND WHAT SHIPS BEAD-FREE. An explicit id that does not resolve
stops, whatever the reason, because the caller named a bead and a typo is the
likely cause: it never becomes a bead-free ship. A branch candidate counts only
when it names its bead exactly, as the full id or the hash after the last
hyphen, because `bd show` also resolves a partial id: `ios` in a branch name
once resolved to hdw-ios-send-birth-year-wynj and closed it (tadw-7lxr). An
explicit id keeps partial resolution, because a person typed it. Two distinct
canonical ids from the branch stop, because closing the wrong bead is silent. A closed bead
stops, because something landed this work already. The branch naming no bead,
or no tracker existing at all, ships bead-free. Any other tracker failure stops:
a `bd` that crashed has not said the bead is missing, and shipping bead-free on
it would leave a real bead open.

Exit status of the command line: 0 when a bead or a bead-free ship was chosen
(printed as JSON), 1 when selection stopped (`stop` names why), 2 on operator
error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

EXIT_SELECTED = 0
EXIT_STOP = 1
EXIT_OPERATOR_ERROR = 2

NO_DATABASE_MESSAGE = "no beads database found"


@dataclass(frozen=True)
class Bead:
    id: str
    title: str
    type: str
    status: str


@dataclass(frozen=True)
class Selection:
    """The chosen bead, or None with the reason the ship goes bead-free."""

    bead: Bead | None
    source: str
    bead_free_reason: str | None = None


class SelectionStopped(Exception):
    """Selection cannot choose safely; the ship stops with `SHIP_BLOCKED tracker`."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class TrackerMissing(Exception):
    """No tracker exists here, which is a bead-free ship, not a failure."""


class TrackerFailed(Exception):
    """The tracker exists but could not answer, which is never read as "no bead"."""


Lookup = Callable[[str], Bead | None]


def select_bead(explicit: str | None, candidates: Sequence[str], lookup: Lookup) -> Selection:
    if explicit:
        return select_explicit(explicit, lookup)
    return select_from_branch(candidates, lookup)


def select_explicit(explicit: str, lookup: Lookup) -> Selection:
    try:
        bead = lookup(explicit)
    except (TrackerMissing, TrackerFailed) as error:
        raise SelectionStopped("explicit-unresolved", f"{explicit}: {error}") from error
    if bead is None:
        raise SelectionStopped("explicit-unresolved", f"no bead matches {explicit}")
    return Selection(open_bead(bead), "explicit")


def select_from_branch(candidates: Sequence[str], lookup: Lookup) -> Selection:
    try:
        found = {bead.id: bead for bead in resolved(candidates, lookup)}
    except TrackerMissing:
        return Selection(None, "branch", "no-tracker")
    except TrackerFailed as error:
        raise SelectionStopped("tracker-failed", str(error)) from error
    if not found:
        return Selection(None, "branch", "no-candidate")
    if len(found) > 1:
        raise SelectionStopped("ambiguous", "the branch names " + ", ".join(sorted(found)))
    return Selection(open_bead(next(iter(found.values()))), "branch")


def resolved(candidates: Sequence[str], lookup: Lookup) -> list[Bead]:
    """Only beads the candidate names exactly: `bd show` also resolves a partial id."""
    found = ((candidate, lookup(candidate)) for candidate in candidates)
    return [bead for candidate, bead in found if bead is not None and names(candidate, bead)]


def names(candidate: str, bead: Bead) -> bool:
    """The full id, or the hash after its last hyphen, as `a7r` names `tadw-a7r`."""
    return candidate in (bead.id, bead.id.rsplit("-", 1)[-1])


def open_bead(bead: Bead) -> Bead:
    if bead.status == "closed":
        raise SelectionStopped("already-closed", f"{bead.id} is already closed")
    return bead


def bd_lookup(repo: Path) -> Lookup:
    """A lookup that asks `bd show <id> --json` in `repo`."""

    def lookup(candidate: str) -> Bead | None:
        try:
            completed = subprocess.run(
                ["bd", "show", candidate, "--json"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as error:
            raise TrackerMissing("bd is not on PATH") from error
        return parse_show(candidate, completed)

    return lookup


def parse_show(candidate: str, completed: subprocess.CompletedProcess) -> Bead | None:
    """A bead, None for "no such bead", or an exception for anything else."""
    if NO_DATABASE_MESSAGE in completed.stderr:
        raise TrackerMissing(NO_DATABASE_MESSAGE)
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise TrackerFailed(
            f"bd show {candidate} exited {completed.returncode}: {completed.stderr.strip()}"
        ) from error
    if isinstance(document, dict) and "error" in document:
        return None
    if not isinstance(document, list) or len(document) != 1:
        raise TrackerFailed(f"bd show {candidate} returned an unexpected shape")
    try:
        record = document[0]
        return Bead(record["id"], record["title"], record["issue_type"], record["status"])
    except (KeyError, TypeError) as error:
        raise TrackerFailed(f"bd show {candidate} is missing a field: {error}") from error


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    if not args.repo_root.is_dir():
        print(f"select_bead: not a directory: {args.repo_root}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    try:
        selection = select_bead(args.bead, args.candidates, bd_lookup(args.repo_root))
    except SelectionStopped as stopped:
        print(json.dumps({"stop": stopped.reason, "detail": stopped.detail}, indent=2))
        return EXIT_STOP
    print(json.dumps({"stop": None, **asdict(selection)}, indent=2))
    return EXIT_SELECTED


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--bead", help="an explicit bead id; the candidates are then ignored")
    parser.add_argument("candidates", nargs="*", help="branch-name candidates, best first")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
