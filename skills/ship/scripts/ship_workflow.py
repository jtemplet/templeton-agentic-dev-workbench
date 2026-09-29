#!/usr/bin/env python3
"""Ship one bead: ground, rebase, gate, close into the landing commit, push, and clean up.

The order is the ship skill's (skills/ship/SKILL.md). Every step is a helper
that already exists; this module runs them in order, and turns the stop each
helper raises into one of the report's slugs: gate, conflict, tracker,
git-state, or internal.

ONLY THE LANDING MOVES THE DEFAULT BRANCH. `candidate.land_candidate` gates the
code tree, closes the bead, and adds that close to a landing commit. A stop
before the branch moves reopens the bead and leaves the default branch as it was.

CLEANUP WAITS FOR THE LANDED CHECK. Deleting the branch is safe only once the
default branch holds every file the branch authored, so a branch with
outstanding files keeps its worktree and its name.

AN INTERRUPTED RUN RESUMES (tadw-dur4). One run at a time holds the repository's
lock, and each mutation is recorded before and after it runs (ship_progress.py).
The next run finds the record, checks it against the repository and the tracker,
and takes the one step ship_recovery.py allows. A stop that leaves this run's
close or its unpushed landing behind keeps the record, so a re-run resumes it.

A PUSH FAILURE IS CLASSIFIED BEFORE IT IS ANSWERED. A refusal is reported, a
moved destination rebuilds the candidate on it, and an uncertain result is
checked against the destination before the push is retried.
"""

from __future__ import annotations

import dataclasses
import functools
import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import NamedTuple, NoReturn


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
select_bead = load_sibling("select_bead")
resolve_rebase_conflict = load_sibling("resolve_rebase_conflict")
candidate = load_sibling("candidate")
landed_check = load_sibling("landed_check")
ship_report = load_sibling("ship_report")
worktree_cleanup = load_sibling("worktree_cleanup")
default_checkout_stash = load_sibling("default_checkout_stash")
ship_progress = load_sibling("ship_progress")
ship_recovery = load_sibling("ship_recovery")
Resume = ship_recovery.Resume
PushNext = ship_recovery.PushNext

# Every other `CandidateStop` reason is a repository that was not fit to land on.
CANDIDATE_SLUGS = {
    "gate": "gate",
    "conflict": "conflict",
    "export": "tracker",
    "export-drift": "tracker",
    "audit-log": "tracker",
}
GIT_ERRORS = (resolve_ground.GitError, resolve_rebase_conflict.GitError, landed_check.GitError)
COMMIT_KINDS = {"feature": "feat", "epic": "feat", "bug": "fix", "docs": "docs"}
MAX_RESOLUTIONS = 10
MAX_LANDINGS = 2
NOTHING_CHANGED = "nothing was changed."
NOT_LANDED = "the default branch was not moved."


class ShipStop(Exception):
    """The run stops here; `slug` goes on the machine line, `explanation` above it."""

    def __init__(self, slug: str, *explanation: str) -> None:
        super().__init__(f"{slug}: {'; '.join(explanation)}")
        self.slug = slug
        self.explanation = explanation


@dataclass(frozen=True)
class Request:
    """One ship: its repository, where its caller started, and the checkout that outlives it."""

    repo: Path
    start: Path
    stable: Path
    bead_id: str | None


@dataclass(frozen=True)
class Shipped:
    bead_id: str | None
    commit: str
    cd_target: Path | None


class DestinationMoved(Exception):
    """origin's default branch moved after the landing, so the candidate is rebuilt on it."""


@dataclass(frozen=True)
class Run:
    """What every step of one locked run shares."""

    request: Request
    ground: dict
    gate: candidate.Gate
    store: ship_progress.ProgressStore

    @property
    def repo(self) -> Path:
        return self.request.repo

    @property
    def default(self) -> str:
        return self.ground["default_branch"]


def ship(request: Request, gate: candidate.Gate) -> Shipped:
    """Run every step in order; raise `ShipStop` at the first one that cannot go on."""
    try:
        return run_steps_without_git_errors(request, gate)
    except candidate.CandidateStop as stopped:
        slug = CANDIDATE_SLUGS.get(stopped.reason, "git-state")
        raise ShipStop(slug, stopped.detail, NOT_LANDED) from stopped


def run_steps_without_git_errors(request: Request, gate: candidate.Gate) -> Shipped:
    """A helper that could not run git at all stops the run as `internal`."""
    try:
        return run_steps(request, gate)
    except GIT_ERRORS as error:
        raise ShipStop("internal", str(error)) from error


def run_steps(request: Request, gate: candidate.Gate) -> Shipped:
    ground = read_ground(request.repo)
    store = ship_progress.ProgressStore(Path(ground["git_common_dir"]))
    try:
        with ship_progress.exclusive_run(store):
            return run_locked(Run(request, ground, gate, store))
    except ship_progress.ShipBusy as busy:
        raise ShipStop("git-state", str(busy), NOTHING_CHANGED) from busy


def run_locked(run: Run) -> Shipped:
    holder = run.ground["default_branch_worktree"]
    with default_checkout_stash.default_checkout_set_aside(holder, run.default, say):
        shipped = resume_or_ship_settled(run)
    run.store.clear()
    return shipped


def resume_or_ship_settled(run: Run) -> Shipped:
    try:
        return resume_or_ship(run)
    except BaseException as error:
        settle(run, error)
        raise


def resume_or_ship(run: Run) -> Shipped:
    recorded = load_progress(run.store)
    if recorded is not None:
        resumed = resume(run, recorded)
        if resumed is not None:
            return resumed
    return ship_fresh(run, choose_bead(run.request, run.ground))


def ship_fresh(run: Run, bead: select_bead.Bead | None) -> Shipped:
    if run.ground["has_origin"]:
        catch_up(run.repo, run.default)
    if bead is not None and already_landed(run.repo, run.ground):
        return close_landed(run, bead)
    run.store.save(
        ship_progress.Progress.begin(run.ground["branch"], run.default, **bead_fields(bead))
    )
    return land_and_publish(run, bead)


def land_and_publish(
    run: Run,
    bead: select_bead.Bead | None,
    *,
    closed: bool = False,
    landing: candidate.Landing | None = None,
) -> Shipped:
    """Land and push; a moved destination rewinds this run's landing and builds it again."""
    for _ in range(MAX_LANDINGS):
        landing = landing or rebased_landing(run, bead, closed)
        if published(run, bead, landing):
            return finish(run, bead, landing)
        closed, landing = bead is not None, None
    raise ShipStop(
        "git-state",
        f"origin/{run.default} moved again after {MAX_LANDINGS} landings",
        NOT_LANDED,
    )


def rebased_landing(run: Run, bead: select_bead.Bead | None, closed: bool) -> candidate.Landing:
    rebase(run.repo, run.default)
    return land(run, bead, closed)


def published(run: Run, bead: select_bead.Bead | None, landing: candidate.Landing) -> bool:
    """False when the destination moved: this run's landing is then rewound off the branch."""
    try:
        publish(run.repo, run.ground, bead, landing.commit)
    except DestinationMoved as moved:
        return rewound(run, bead, landing, moved)
    run.store.mark(ship_progress.PUSHED)
    return True


def rewound(
    run: Run, bead: select_bead.Bead | None, landing: candidate.Landing, moved: DestinationMoved
) -> bool:
    say(str(moved))
    rewind_default(run, bead, landing)
    return False


def finish(run: Run, bead: select_bead.Bead | None, landing: candidate.Landing) -> Shipped:
    warn_export_drift(run.request.stable)
    bead_id = None if bead is None else bead.id
    return Shipped(bead_id, landing.commit, clean_up(run.request, run.ground, landing))


def bead_fields(bead: select_bead.Bead | None) -> dict[str, str | None]:
    if bead is None:
        return {}
    return {"bead_id": bead.id, "bead_title": bead.title, "bead_type": bead.type}


def load_progress(store: ship_progress.ProgressStore) -> ship_progress.Progress | None:
    try:
        return store.load()
    except ship_progress.ProgressUnreadable as unreadable:
        raise ShipStop(
            "git-state",
            f"the ship progress record cannot be read: {unreadable}",
            f"{NOTHING_CHANGED} Check the repository and the bead, then remove the record.",
        ) from unreadable


def settle(run: Run, error: BaseException) -> None:
    """On a stop: reverse a close this run still holds, then keep only a record worth resuming."""
    recorded = run.store.current
    if recorded is None:
        return
    if recorded.holds_unlanded_close() and not is_tracker_stop(error):
        reverse_after_stop(run, recorded, error)
    keep_only_a_record_to_resume(run.store)


def keep_only_a_record_to_resume(store: ship_progress.ProgressStore) -> None:
    if store.current.needs_recovery():
        say(kept_line(store))
    else:
        store.clear()


def reverse_after_stop(run: Run, recorded: ship_progress.Progress, error: BaseException) -> None:
    try:
        reverse_close(run, recorded_bead(recorded), run.repo)
    except candidate.CandidateStop as refused:
        say(kept_line(run.store))
        raise ShipStop("tracker", str(error), refused.detail, NOT_LANDED) from refused


def is_tracker_stop(error: BaseException) -> bool:
    if isinstance(error, ShipStop):
        return error.slug == "tracker"
    return isinstance(error, candidate.CandidateStop) and CANDIDATE_SLUGS.get(error.reason) == (
        "tracker"
    )


def kept_line(store: ship_progress.ProgressStore) -> str:
    return (
        f"kept the progress record at {store.path} and the candidate at "
        f"{ship_progress.CANDIDATE_REF}; run tadw-ship again to resume"
    )


def resume(run: Run, recorded: ship_progress.Progress) -> Shipped | None:
    """Take the one step recovery allows; None means ship afresh."""
    decision = decide_resume(run.repo, recorded)
    if decision.action is Resume.RESTART:
        run.store.clear()
        return None
    if decision.action in (Resume.STOP_TRACKER, Resume.STOP_GIT):
        raise ShipStop(decision.action.value, decision.reason)
    return continue_recorded(run, recorded, decision.action)


def decide_resume(repo: Path, recorded: ship_progress.Progress) -> ship_recovery.Decision:
    say(f"found run {recorded.run_id[:12]} of {recorded.bead_id or recorded.branch} "
        f"stopped at {recorded.state}")  # fmt: skip
    remove_stale_candidate(repo, recorded)
    decision = ship_recovery.resume_action(recorded, observe(repo, recorded))
    say(decision.reason)
    return decision


def continue_recorded(run: Run, recorded: ship_progress.Progress, action: Resume) -> Shipped:
    require_own_branch(run, recorded, action)
    run = dataclasses.replace(run, ground={**run.ground, "branch": recorded.branch})
    bead = None if recorded.bead_id is None else recorded_bead(recorded)
    if action is Resume.REBUILD:
        return rebuild(run, bead)
    return publish_recorded(run, bead, recorded_landing(recorded), action)


def require_own_branch(run: Run, recorded: ship_progress.Progress, action: Resume) -> None:
    """Advancing or rebuilding uses the recorded branch, so it must be the one checked out."""
    if action in (Resume.ADVANCE, Resume.REBUILD) and run.ground["branch"] != recorded.branch:
        raise ShipStop(
            "git-state",
            f"the interrupted ship must resume from its own branch, {recorded.branch}",
        )


def rebuild(run: Run, bead: select_bead.Bead | None) -> Shipped:
    if run.ground["has_origin"]:
        catch_up(run.repo, run.default)
    return land_and_publish(run, bead, closed=bead is not None)


def publish_recorded(
    run: Run, bead: select_bead.Bead | None, landing: candidate.Landing, action: Resume
) -> Shipped:
    if action is Resume.ADVANCE:
        candidate.advance_default_branch(run.repo, run.default, landing.parent, landing.commit)
        run.store.mark(ship_progress.LANDED)
    if action is Resume.CLEAN_UP:
        return finish(run, bead, landing)
    return land_and_publish(run, bead, landing=landing)


def observe(repo: Path, recorded: ship_progress.Progress) -> ship_recovery.Observed:
    default = f"refs/heads/{recorded.default_branch}"
    landing = recorded.landing_commit
    exists = landing is not None and candidate.commit_or_none(repo, landing) is not None
    return ship_recovery.Observed(
        bead=None if recorded.bead_id is None else read_bead_close(repo, recorded.bead_id),
        default_tip=candidate.resolve_commit(repo, default),
        branch_tip=candidate.commit_or_none(repo, f"refs/heads/{recorded.branch}"),
        landing_exists=exists,
        landing_on_default=exists
        and candidate.default_branch_contains(repo, recorded.default_branch, landing),
    )


def remove_stale_candidate(repo: Path, recorded: ship_progress.Progress) -> None:
    """A killed run leaves its temporary worktree; only that recorded path is removed."""
    path = recorded.candidate_worktree
    if path is None or not is_registered_candidate(repo, Path(path)):
        return
    candidate.preserve_audit_log(Path(path), repo)
    candidate.remove_worktree(repo, Path(path))
    say(f"removed the interrupted run's candidate worktree {path}")


def is_registered_candidate(repo: Path, path: Path) -> bool:
    if not path.parent.name.startswith(candidate.WORKTREE_PREFIX):
        return False
    registered = {worktree["path"] for worktree in resolve_ground.read_worktrees(repo)}
    return str(path) in registered or str(path.resolve()) in registered


def recorded_bead(recorded: ship_progress.Progress) -> select_bead.Bead:
    return select_bead.Bead(recorded.bead_id, recorded.bead_title, recorded.bead_type, "closed")


def recorded_landing(recorded: ship_progress.Progress) -> candidate.Landing:
    return candidate.Landing(
        recorded.parent, recorded.landing_commit, recorded.checked_commit or "", ()
    )


def rewind_default(run: Run, bead: select_bead.Bead | None, landing: candidate.Landing) -> None:
    """Move the default branch back off this run's unpushed landing, and only that landing."""
    require_default_at_landing(run, landing)
    move_default_back(run.repo, run.default, run.ground["default_branch_worktree"], landing)
    mark_rewound(run.store, bead)
    say(f"rewound {run.default} from {landing.commit[:12]} to {landing.parent[:12]}")
    follow_origin(run.repo, run.default)


def mark_rewound(store: ship_progress.ProgressStore, bead: select_bead.Bead | None) -> None:
    """A rewound bead ship still holds this run's close; a bead-free one holds nothing."""
    state = ship_progress.CLOSED if bead is not None else ship_progress.STARTED
    store.mark(state, landing_commit=None)


def require_default_at_landing(run: Run, landing: candidate.Landing) -> None:
    if candidate.resolve_commit(run.repo, f"refs/heads/{run.default}") != landing.commit:
        raise ShipStop(
            "git-state",
            f"{run.default} moved past the landing {landing.commit[:12]}; it was not rewound",
        )


def move_default_back(
    repo: Path, default: str, holder: str | None, landing: candidate.Landing
) -> None:
    """Through the checkout that holds the branch, when one does, so its files follow."""
    if holder is None:
        candidate.git(repo, "update-ref", f"refs/heads/{default}", landing.parent, landing.commit)
        return
    candidate.restore_stale_export(Path(holder), default)
    candidate.git(Path(holder), "reset", "--keep", "--quiet", landing.parent)


def already_landed(repo: Path, ground: dict) -> bool:
    """The branch has commits of its own, and the default branch already holds all their files."""
    default = f"refs/heads/{ground['default_branch']}"
    branch = f"refs/heads/{ground['branch']}"
    if not candidate.git(repo, "rev-list", "--max-count=1", f"{default}..{branch}"):
        return False
    authored = landed_check.changed_paths(repo, f"{default}...{branch}")
    if all(landed_by_ship(path) for path in authored):
        return False
    return not landed_check.outstanding_paths(
        repo, landed_check.Comparison(default, branch, default)
    )


def landed_by_ship(path: str) -> bool:
    return any(landed_check.is_under(path, prefix) for prefix in landed_check.ALWAYS_EXCLUDED)


def close_landed(run: Run, bead: select_bead.Bead) -> Shipped:
    tip = candidate.resolve_commit(run.repo, f"refs/heads/{run.default}")
    say(f"{run.ground['branch']} already landed on {run.default} at {tip[:12]}; "
        f"closing {bead.id} with no gate and no rebase")  # fmt: skip
    close_bead(run.repo, bead)
    warn_export_drift(run.request.stable)
    return Shipped(bead.id, tip, None)


def read_ground(repo: Path) -> dict:
    ground = resolve_ground.resolve_ground(repo)
    if ground["stop"]:
        problem = f"the repository is not fit to ship from: {ground['stop']}"
        raise ShipStop("git-state", problem, NOTHING_CHANGED)
    return ground


def choose_bead(request: Request, ground: dict) -> select_bead.Bead | None:
    lookup = select_bead.bd_lookup(request.repo)
    try:
        selection = select_bead.select_bead(request.bead_id, ground["bead_candidates"], lookup)
    except select_bead.SelectionStopped as stopped:
        raise ShipStop("tracker", str(stopped), NOTHING_CHANGED) from stopped
    say(describe_selection(selection))
    return selection.bead


def describe_selection(selection: select_bead.Selection) -> str:
    if selection.bead is None:
        return f"bead-free ship ({selection.bead_free_reason})"
    return f"shipping {selection.bead.id}, selected by {selection.source}"


def catch_up(repo: Path, default: str) -> None:
    candidate.git(repo, "fetch", "--quiet", "origin")
    follow_origin(repo, default)


def follow_origin(repo: Path, default: str) -> None:
    """Fast-forward to the last fetched origin/<default>; fetching is the caller's step."""
    local = candidate.resolve_commit(repo, f"refs/heads/{default}")
    remote = candidate.commit_or_none(repo, f"refs/remotes/origin/{default}")
    if remote is not None and not is_ancestor(repo, remote, local):
        fast_forward(repo, default, local, remote)


def fast_forward(repo: Path, default: str, local: str, remote: str) -> None:
    if not is_ancestor(repo, local, remote):
        raise ShipStop("git-state", f"{default} and origin/{default} have diverged", NOT_LANDED)
    restored_export_in = candidate.advance_default_branch(repo, default, local, remote)
    if restored_export_in is not None:
        emit([candidate.restored_export_line(restored_export_in)])
    say(f"fast-forwarded {default} to origin/{default} at {remote[:12]}")


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    arguments = ("merge-base", "--is-ancestor", ancestor, descendant)
    return candidate.run_git(repo, arguments).returncode == 0


def rebase(repo: Path, default: str) -> None:
    """Rebase onto the local default branch, resolving only what needs no judgment."""
    if candidate.run_git(repo, ("rebase", "--quiet", f"refs/heads/{default}")).returncode == 0:
        return
    for _ in range(MAX_RESOLUTIONS):
        if resolve_and_continue(repo):
            return
    abort_rebase(repo, "conflict", f"the rebase still conflicts after {MAX_RESOLUTIONS} rounds")


def resolve_and_continue(repo: Path) -> bool:
    outcome = resolve_rebase_conflict.resolve_conflicts(repo)
    if outcome["stop"]:
        abort_rebase(repo, outcome["stop"], outcome["detail"])
    return continue_rebase(repo)


def continue_rebase(repo: Path) -> bool:
    """Continue without opening an editor; GIT_EDITOR outranks every configured editor."""
    completed = subprocess.run(
        ["git", "-C", str(repo), "rebase", "--continue"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GIT_EDITOR": "true"},
    )
    return completed.returncode == 0


def abort_rebase(repo: Path, slug: str, detail: str) -> NoReturn:
    if candidate.run_git(repo, ("rebase", "--abort")).returncode == 0:
        raise ShipStop(slug, detail, f"the rebase was aborted; {NOT_LANDED}")
    raise ShipStop(slug, detail, f"git rebase --abort failed; run it yourself in {repo}")


def land(run: Run, bead: select_bead.Bead | None, closed: bool) -> candidate.Landing:
    """`closed` is a bead this run already closed, so the candidate's export carries it."""
    subject = commit_subject(bead, run.ground["branch"])
    plan = candidate.Plan(run.ground["branch"], run.default, subject, run.store)
    tracker = tracker_actions(run, bead, closed)
    landing = candidate.land_candidate(run.repo, plan, run.gate, tracker)
    emit(landing.report_lines())
    return landing


def tracker_actions(
    run: Run, bead: select_bead.Bead | None, closed: bool
) -> candidate.TrackerActions | None:
    if bead is None:
        return None
    close = functools.partial(close_recorded, run.store, bead)
    reopen = functools.partial(reverse_close, run, bead)
    actions = candidate.BeadActions(close, reopen, already_closed=closed)
    return candidate.TrackerActions(bd_export, actions)


def close_recorded(
    store: ship_progress.ProgressStore, bead: select_bead.Bead, directory: Path
) -> None:
    store.mark(ship_progress.CLOSING)
    close_bead(directory, bead)
    store.mark(ship_progress.CLOSED, close=read_bead_close(directory, bead.id))


def reverse_close(run: Run, bead: select_bead.Bead, directory: Path) -> None:
    """Reopen only the exact close this run recorded, then regenerate the export."""
    current = read_bead_close(directory, bead.id)
    if current.status == "closed":
        require_this_runs_close(run.store.current.close, bead, current)
        reopen_and_export(run.request.stable, bead, directory)
    run.store.mark(ship_progress.REOPENED, close=None)


def reopen_and_export(stable: Path, bead: select_bead.Bead, directory: Path) -> None:
    reopen_bead(directory, bead)
    regenerate_export(stable)


def require_this_runs_close(
    recorded: ship_progress.BeadClose | None,
    bead: select_bead.Bead,
    current: ship_progress.BeadClose,
) -> None:
    if not ship_recovery.closed_by_this_run(recorded, current):
        raise candidate.CandidateStop(
            "export",
            f"{bead.id} is {current.describe()}, not the close this run recorded "
            f"({ship_recovery.describe(recorded)}); it was not reopened",
        )


def regenerate_export(checkout: Path) -> None:
    export = checkout / candidate.EXPORT_PATH
    if export.parent.is_dir() and not bd_export(checkout, export):
        say(f"warning: bd export could not regenerate {export} after the reopen")


def read_bead_close(directory: Path, bead_id: str) -> ship_progress.BeadClose:
    completed = run_bd(directory, "show", bead_id, "--json")
    try:
        return bead_close_of(bead_id, completed)
    except (select_bead.TrackerMissing, select_bead.TrackerFailed, KeyError, TypeError) as error:
        raise candidate.CandidateStop(
            "export", f"bd show {bead_id} gave no readable status: {error}"
        ) from error


def bead_close_of(
    bead_id: str, completed: subprocess.CompletedProcess | None
) -> ship_progress.BeadClose:
    if completed is None:
        raise select_bead.TrackerMissing("bd is not on PATH")
    record = select_bead.show_record(bead_id, completed)
    if record is None:
        raise select_bead.TrackerFailed(f"no bead matches {bead_id}")
    return ship_progress.BeadClose.from_show(record)


def commit_subject(bead: select_bead.Bead | None, branch: str) -> str:
    if bead is None:
        return f"chore: Land {branch}"
    return ship_report.commit_subject(COMMIT_KINDS.get(bead.type, "chore"), bead.title, bead.id)


def bd_export(directory: Path, target: Path) -> bool:
    completed = run_bd(directory, "export", "-o", str(target))
    return completed is not None and completed.returncode == 0 and target.is_file()


def publish(repo: Path, ground: dict, bead: select_bead.Bead | None, commit: str) -> None:
    """Push the landing commit and record what comes next; only a failed push stops."""
    push(repo, ground, commit)
    sync_tracker(repo, ground, bead)
    record_next(repo)


def close_bead(directory: Path, bead: select_bead.Bead) -> None:
    completed = run_bd(
        directory, "close", bead.id, "--reason", f"shipped: {bead.title}", "--suggest-next"
    )
    if completed is None or completed.returncode != 0:
        raise candidate.CandidateStop(
            "export", f"bd close {bead.id} failed: {bd_failure(completed)}"
        )
    emit(f"tadw_ship: {line}" for line in completed.stdout.splitlines() if line.strip())


def reopen_bead(directory: Path, bead: select_bead.Bead) -> None:
    completed = run_bd(directory, "reopen", bead.id)
    if completed is None or completed.returncode != 0:
        raise candidate.CandidateStop(
            "export", f"bd reopen {bead.id} failed: {bd_failure(completed)}"
        )
    emit(f"tadw_ship: {line}" for line in completed.stdout.splitlines() if line.strip())


def warn_export_drift(directory: Path) -> None:
    """Name a tracker export that changed after the landing commit was built."""
    changed = candidate.git(directory, "status", "--porcelain", "--", candidate.EXPORT_PATH)
    if changed:
        say(f"warning: {candidate.EXPORT_PATH} differs from HEAD after ship")


def push(repo: Path, ground: dict, commit: str) -> None:
    """With no origin the land is complete locally, and nothing is pushed."""
    if ground["has_origin"]:
        push_default(repo, ground["default_branch"], commit)


def push_default(repo: Path, default: str, commit: str) -> None:
    """Retry once, and only after the destination shows the first push did not land."""
    push = Push(repo, default, commit)
    if not pushed(push, retried=False):
        say(f"origin/{default} does not carry {commit[:12]}; retrying the push once")
        pushed(push, retried=True)


class Push(NamedTuple):
    repo: Path
    default: str
    commit: str


def pushed(push: Push, *, retried: bool) -> bool:
    """True once the destination carries the landing; False when one retry is worth making."""
    reference = f"refs/heads/{push.default}"
    arguments = ("push", "--quiet", "origin", f"{reference}:{reference}")
    completed = candidate.run_git(push.repo, arguments)
    if completed.returncode == 0:
        report_unpushed(push.repo, push.default, push.commit)
        return True
    return answer_push_failure(push, completed.stderr, retried=retried)


def answer_push_failure(push: Push, stderr: str, *, retried: bool) -> bool:
    failure = ship_recovery.classify_push_failure(stderr)
    remote = None if failure in ship_recovery.REFUSALS else inspect_destination(*push)
    step = ship_recovery.after_push_failure(failure, remote, retried=retried)
    if step is PushNext.RETRY:
        return False
    return act_on_push_failure(push, step, f"{failure.value}: {stderr.strip()}")


def act_on_push_failure(push: Push, step: PushNext, cause: str) -> bool:
    """True when the landing is published after all; otherwise raise."""
    if step is PushNext.DONE:
        say(f"the push reported a failure, but origin/{push.default} carries {push.commit[:12]}")
        return True
    if step is PushNext.REBUILD:
        raise DestinationMoved(f"origin/{push.default} moved; rebuilding the candidate on it")
    raise ShipStop(
        "git-state",
        f"git push origin {push.default} failed, {cause}",
        f"{push.default} carries {push.commit} locally, unpushed; run tadw-ship again to resume "
        "the push; never force the push",
    )


def inspect_destination(repo: Path, default: str, commit: str) -> ship_recovery.RemoteView:
    if candidate.run_git(repo, ("fetch", "--quiet", "origin")).returncode != 0:
        return ship_recovery.RemoteView(readable=False)
    tip = candidate.commit_or_none(repo, f"refs/remotes/origin/{default}")
    if tip is None:
        return ship_recovery.RemoteView(readable=True, behind_landing=True)
    return ship_recovery.RemoteView(
        readable=True,
        carries_landing=is_ancestor(repo, commit, tip),
        behind_landing=is_ancestor(repo, tip, commit),
    )


def report_unpushed(repo: Path, default: str, commit: str) -> None:
    """After the landing a `CandidateStop` would claim the default branch never moved."""
    try:
        later = candidate.later_local_commits(repo, default, commit)
    except candidate.CandidateStop as stopped:
        say(f"warning: could not list commits after {commit[:12]}: {stopped.detail}")
        return
    emit(candidate.unpushed_report_lines(later))


def sync_tracker(repo: Path, ground: dict, bead: select_bead.Bead | None) -> None:
    """A failed sync warns: running `bd dolt push` again recovers it."""
    if bead is None or not ground["has_origin"]:
        return
    completed = run_bd(repo, "dolt", "push")
    if completed is None or completed.returncode != 0:
        say(f"warning: bd dolt push failed: {bd_failure(completed)}; run it again")


def record_next(repo: Path) -> None:
    """Read before cleanup, because bd finds its database through this checkout."""
    completed = run_bd(repo, "ready", "-n", "1", "--json")
    if completed is None or completed.returncode != 0:
        say(f"next: lookup failed: bd ready -n 1 --json: {bd_failure(completed)}")
        return
    say(f"next: {completed.stdout.strip()}")


def clean_up(request: Request, ground: dict, landing: candidate.Landing) -> Path | None:
    """The `cd` target when cleanup removed the caller's directory, otherwise None."""
    if candidate.commit_or_none(request.repo, f"refs/heads/{ground['branch']}") is None:
        return None
    if outstanding(request.repo, ground, landing.parent):
        return None
    return remove_branch(request, ground)


def outstanding(repo: Path, ground: dict, base: str) -> bool:
    comparison = landed_check.Comparison(base, ground["branch"], ground["default_branch"])
    paths = landed_check.outstanding_paths(repo, comparison)
    if paths:
        say(f"kept {ground['branch']}: the default branch still differs in {', '.join(paths)}")
    return bool(paths)


def remove_branch(request: Request, ground: dict) -> Path | None:
    branch = ground["branch"]
    leave_branch(request.stable, branch, ground["default_branch"])
    worktrees = holders(request.stable, branch)
    cleanup = worktree_cleanup.remove_worktrees(worktrees, request.stable, request.start)
    emit(cleanup.lines)
    delete_branch(request.stable, branch, has_origin=ground["has_origin"])
    return cleanup.cd_target


def leave_branch(stable: Path, branch: str, default: str) -> None:
    """The main checkout is never removed, so when it holds the branch it switches off it."""
    if candidate.git_or_none(stable, "branch", "--show-current") != branch:
        return
    if candidate.git_or_none(stable, "switch", "--quiet", default) is None:
        say(f"could not switch {stable} from {branch} to {default}")


def holders(stable: Path, branch: str) -> list[Path]:
    """The linked worktrees on the branch; the first listed is the main checkout, never removed."""
    linked = resolve_ground.read_worktrees(stable)[1:]
    return [Path(worktree["path"]) for worktree in linked if worktree["branch"] == branch]


def delete_branch(stable: Path, branch: str, *, has_origin: bool) -> None:
    if candidate.git_or_none(stable, "branch", "-D", branch) is None:
        say(f"kept the branch {branch}: git branch -D refused, because a worktree still holds it")
        return
    say(f"deleted the branch {branch}")
    if has_origin:
        delete_remote_branch(stable, branch)


def delete_remote_branch(stable: Path, branch: str) -> None:
    listed = ("ls-remote", "--exit-code", "origin", f"refs/heads/{branch}")
    if candidate.run_git(stable, listed).returncode != 0:
        return
    if candidate.git_or_none(stable, "push", "--quiet", "origin", "--delete", branch) is None:
        say(f"warning: could not delete origin/{branch}")


def run_bd(directory: Path, *arguments: str) -> subprocess.CompletedProcess | None:
    """The finished `bd` call, or None when `bd` is not on PATH."""
    try:
        return subprocess.run(
            ["bd", *arguments], cwd=directory, capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return None


def bd_failure(completed: subprocess.CompletedProcess | None) -> str:
    if completed is None:
        return "bd is not on PATH"
    return completed.stderr.strip() or f"exit {completed.returncode}"


def say(line: str) -> None:
    print(f"tadw_ship: {line}", file=sys.stderr)


def emit(lines: Iterable[str]) -> None:
    for line in lines:
        print(line, file=sys.stderr)
