#!/usr/bin/env python3
"""Decide what an interrupted or refused ship does next, from recorded and observed state.

Every function here is pure: it takes what the record says and what the
repository and tracker say now, and returns one action. ship_workflow.py runs
the action. Keeping the decision apart from the git and bd calls lets each rule
be tested on its own.

TWO RULES OUTRANK THE REST.

  1. A bead is this run's close only when the tracker still shows the exact
     close the run recorded: status, closed_at, and updated_at. A bead closed by
     another run, or edited since, is never reopened automatically.
  2. A landing already on the default branch is never built again, and a
     landing that is not there is never assumed to be.
"""

from __future__ import annotations

import enum
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


def load_sibling(name: str) -> ModuleType:
    """Load a helper from this file's own directory, never from another installed copy."""
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ship_progress = load_sibling("ship_progress")
Progress = ship_progress.Progress
BeadClose = ship_progress.BeadClose


class Resume(enum.Enum):
    RESTART = "restart"  # nothing needs recovery: discard the record and ship afresh
    ADVANCE = "advance"  # the recorded landing is verified: move the default branch to it
    REBUILD = "rebuild"  # this run's close stands, but its landing is gone: build a new one
    PUBLISH = "publish"  # the default branch carries the landing: push, then clean up
    CLEAN_UP = "clean-up"  # the landing is published: clean up only
    STOP_TRACKER = "tracker"
    STOP_GIT = "git-state"


@dataclass(frozen=True)
class Observed:
    """The repository and tracker as recovery finds them."""

    bead: BeadClose | None
    default_tip: str
    branch_tip: str | None
    landing_exists: bool
    landing_on_default: bool


@dataclass(frozen=True)
class Decision:
    action: Resume
    reason: str


def resume_action(recorded: Progress, observed: Observed) -> Decision:
    """The one safe next step for a run recorded as `recorded`."""
    if not recorded.needs_recovery():
        return before_close(recorded, observed)
    if recorded.state == ship_progress.CLOSING:
        return while_closing(recorded, observed)
    if observed.landing_on_default:
        return after_landing(recorded)
    if recorded.state in (ship_progress.LANDED, ship_progress.PUSHED):
        short = (recorded.landing_commit or "")[:12]
        return Decision(Resume.STOP_GIT, f"the recorded landing {short} is no longer on "
                        f"{recorded.default_branch}")  # fmt: skip
    return closed_before_landing(recorded, observed)


def before_close(recorded: Progress, observed: Observed) -> Decision:
    if observed.bead is not None and observed.bead.status == "closed":
        return Decision(
            Resume.STOP_TRACKER,
            f"{recorded.bead_id} is {observed.bead.describe()}, but this run never closed it; "
            "it was not reopened",
        )
    return Decision(Resume.RESTART, "no step that needs recovery had finished")


def while_closing(recorded: Progress, observed: Observed) -> Decision:
    if observed.bead is not None and observed.bead.status != "closed":
        return Decision(Resume.RESTART, f"{recorded.bead_id} was never closed")
    return Decision(
        Resume.STOP_TRACKER,
        f"the run stopped while closing {recorded.bead_id}, which is now "
        f"{describe(observed.bead)}; nothing shows whether this run closed it",
    )


def after_landing(recorded: Progress) -> Decision:
    if recorded.state == ship_progress.PUSHED:
        return Decision(Resume.CLEAN_UP, "the landing was pushed")
    return Decision(Resume.PUBLISH, f"{recorded.default_branch} carries the landing")


def closed_before_landing(recorded: Progress, observed: Observed) -> Decision:
    """This run may have closed the bead, and the default branch lacks its landing."""
    if recorded.bead_id is not None and not closed_by_this_run(recorded.close, observed.bead):
        return Decision(
            Resume.STOP_TRACKER,
            f"{recorded.bead_id} is {describe(observed.bead)}, not the close this run recorded "
            f"({describe(recorded.close)}); it was not reopened",
        )
    if landing_still_current(recorded, observed):
        return Decision(Resume.ADVANCE, "the recorded landing is verified and its base is current")
    return Decision(Resume.REBUILD, "the recorded landing cannot be used; build a new candidate")


def closed_by_this_run(recorded: BeadClose | None, current: BeadClose | None) -> bool:
    return recorded is not None and current == recorded and current.status == "closed"


def landing_still_current(recorded: Progress, observed: Observed) -> bool:
    return (
        recorded.state == ship_progress.LANDING
        and observed.landing_exists
        and observed.default_tip == recorded.parent
        and observed.branch_tip == recorded.branch_tip
    )


def describe(close: BeadClose | None) -> str:
    return "unknown" if close is None else close.describe()


class PushFailure(enum.Enum):
    MOVED = "the destination moved"
    AUTH = "authentication failed"
    HOOK = "a hook refused the push"
    UNCERTAIN = "the result is uncertain"


# Refusals are reported as they are: the destination is never inspected, and nothing rebuilt.
REFUSALS = (PushFailure.AUTH, PushFailure.HOOK)


class PushNext(enum.Enum):
    DONE = "done"  # the destination already carries the landing
    RETRY = "retry"
    REBUILD = "rebuild"
    REPORT = "report"


# Checked in order: hook output can quote any text, so git's own markers come first.
# Git prints `failed to push some refs` for a refused push, never for a failed connection.
PUSH_MARKERS = (
    (PushFailure.HOOK, ("[remote rejected]", "hook declined")),
    (PushFailure.MOVED, ("(fetch first)", "(non-fast-forward)", "[rejected]")),
    (PushFailure.HOOK, ("failed to push some refs",)),
    (
        PushFailure.AUTH,
        (
            "authentication failed",
            "permission denied",
            "could not read username",
            "access denied",
            "403",
        ),
    ),  # fmt: skip
    (
        PushFailure.UNCERTAIN,
        (
            "could not resolve host",
            "timed out",
            "connection",
            "remote end hung up",
            "early eof",
            "could not read from remote",
        ),
    ),  # fmt: skip
)


def classify_push_failure(stderr: str) -> PushFailure:
    """A local pre-push refusal prints only `failed to push some refs`; nothing else is sure."""
    text = stderr.lower()
    for failure, markers in PUSH_MARKERS:
        if any(marker in text for marker in markers):
            return failure
    return PushFailure.UNCERTAIN


@dataclass(frozen=True)
class RemoteView:
    """The destination as a fresh fetch shows it; `readable` is False when the fetch failed."""

    readable: bool
    carries_landing: bool = False
    behind_landing: bool = False


def after_push_failure(
    failure: PushFailure, remote: RemoteView | None, *, retried: bool
) -> PushNext:
    """A refusal is reported as it is; every other failure is checked against the destination."""
    if failure in REFUSALS or not remote.readable:
        return PushNext.REPORT
    if remote.carries_landing:
        return PushNext.DONE
    if remote.behind_landing:
        return PushNext.REPORT if retried else PushNext.RETRY
    return PushNext.REBUILD
