#!/usr/bin/env python3
"""Ship one bead end to end: ground, rebase, land the checked candidate, close, push, clean up.

The order is the ship skill's (skills/ship/SKILL.md). Every step is a helper
that already exists; this module runs them in order, and turns the stop each
helper raises into one of the report's slugs: gate, conflict, tracker,
git-state, or internal.

ONLY THE LANDING MOVES THE DEFAULT BRANCH. `candidate.land_candidate` moves it
after the gate passed on the exact commit it moves it to, so every stop before
the landing leaves the default branch as it was.

THE BEAD CLOSES AFTER THE LANDING, NEVER BEFORE. A bead closed ahead of a gate
that then fails reads as shipped when nothing landed. The export inside the
landing commit therefore still shows the bead open, and the next tracker export
carries the close.

CLEANUP WAITS FOR THE LANDED CHECK. Deleting the branch is safe only once the
default branch holds every file the branch authored, so a branch with
outstanding files keeps its worktree and its name.

Resuming an interrupted run is tadw-dur4.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import NoReturn


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
    bead = choose_bead(request, ground)
    holder = ground["default_branch_worktree"]
    with default_checkout_stash.default_checkout_set_aside(holder, ground["default_branch"], say):
        return land_and_publish(request, ground, bead, gate)


def land_and_publish(
    request: Request, ground: dict, bead: select_bead.Bead | None, gate: candidate.Gate
) -> Shipped:
    bring_current(request.repo, ground)
    landing = land(request.repo, ground, bead, gate)
    publish(request.repo, ground, bead, landing.commit)
    bead_id = None if bead is None else bead.id
    return Shipped(bead_id, landing.commit, clean_up(request, ground, landing))


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


def bring_current(repo: Path, ground: dict) -> None:
    """Catch the local default branch up to origin, then rebase the branch onto it."""
    if ground["has_origin"]:
        catch_up(repo, ground["default_branch"])
    rebase(repo, ground["default_branch"])


def catch_up(repo: Path, default: str) -> None:
    candidate.git(repo, "fetch", "--quiet", "origin")
    local = candidate.resolve_commit(repo, f"refs/heads/{default}")
    remote = candidate.git_or_none(
        repo, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{default}^{{commit}}"
    )
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


def land(
    repo: Path, ground: dict, bead: select_bead.Bead | None, gate: candidate.Gate
) -> candidate.Landing:
    subject = commit_subject(bead, ground["branch"])
    plan = candidate.Plan(ground["branch"], ground["default_branch"], subject)
    landing = candidate.land_candidate(repo, plan, gate, None if bead is None else bd_export)
    emit(landing.report_lines())
    return landing


def commit_subject(bead: select_bead.Bead | None, branch: str) -> str:
    if bead is None:
        return f"chore: Land {branch}"
    return ship_report.commit_subject(COMMIT_KINDS.get(bead.type, "chore"), bead.title, bead.id)


def bd_export(directory: Path, target: Path) -> bool:
    completed = run_bd(directory, "export", "-o", str(target))
    return completed is not None and completed.returncode == 0 and target.is_file()


def publish(repo: Path, ground: dict, bead: select_bead.Bead | None, commit: str) -> None:
    """Close the bead, push, and record what comes next; only a failed close or push stops."""
    if bead is not None:
        close_bead(repo, bead, commit)
    push(repo, ground, commit)
    sync_tracker(repo, ground, bead)
    record_next(repo)


def close_bead(repo: Path, bead: select_bead.Bead, commit: str) -> None:
    completed = run_bd(
        repo, "close", bead.id, "--reason", f"shipped: {bead.title}", "--suggest-next"
    )
    if completed is None or completed.returncode != 0:
        raise ShipStop(
            "tracker",
            f"bd close {bead.id} failed: {bd_failure(completed)}",
            f"the default branch already carries {commit}, and {bead.id} is still open",
        )
    emit(f"tadw_ship: {line}" for line in completed.stdout.splitlines() if line.strip())


def push(repo: Path, ground: dict, commit: str) -> None:
    """With no origin the land is complete locally, and nothing is pushed."""
    if ground["has_origin"]:
        push_default(repo, ground["default_branch"], commit)


def push_default(repo: Path, default: str, commit: str) -> None:
    reference = f"refs/heads/{default}"
    completed = candidate.run_git(repo, ("push", "--quiet", "origin", f"{reference}:{reference}"))
    if completed.returncode != 0:
        raise ShipStop(
            "git-state",
            f"git push origin {default} failed: {completed.stderr.strip()}",
            f"{default} carries {commit} locally, unpushed; never force the push",
        )
    report_unpushed(repo, default, commit)


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
