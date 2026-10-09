#!/usr/bin/env python3
"""Build the exact commit ship will land, check it, and only then advance the default branch.

The older order ran the gate before the squash, so the tree that passed was not
the tree that was published. Here the candidate is committed first, in a
temporary worktree cut from the local default-branch tip, and the gate runs
against that clean commit. The default branch and the feature branch are never
moved until the gate has passed on the committed tree.

The steps, each of which stops the run with a `CandidateStop` and leaves the
default branch, the feature branch, and every checkout it did not create as they
were:

  1. Refuse a feature checkout with changed tracked files, or an unreadable status.
  2. Cut a detached worktree at the local default-branch tip. That tip includes
     local commits beyond the remote base, so they are in the checked tree.
  3. Squash the feature branch into it and make the gated commit. A pre-commit
     hook can run here.
  4. Require a clean tree after the hook, then run the gate on that commit.
  5. After the gate passes, close the bead. The gated commit is the landing
     commit: git ignores the tracker export, so a close changes no tracked file.
  6. Advance the default branch only while it still names the candidate's parent,
     and only through a checkout that holds no changed tracked files.

Each step is recorded before and after it runs through the `record` the caller
passes (ship_progress.py), so an interrupted landing can be resumed (tadw-dur4).
A bead the run already closed is not closed again.

`.beads/interactions.jsonl` is an untracked audit log (ADR 0010). A candidate
that carries it is rejected.

The temporary worktree is the only directory removed, and it is removed on
every path, so a default-branch checkout holding unrelated work is never touched
by cleanup.
"""

from __future__ import annotations

import contextlib
import importlib.util
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Protocol


def load_sibling(name: str) -> ModuleType:
    """Load a helper from this file's own directory, never from another installed copy.

    A helper already registered from that file is returned as it is, so every script shares one
    set of classes."""
    path = Path(__file__).resolve().parent / f"{name}.py"
    loaded = sys.modules.get(name)
    if loaded is not None and Path(getattr(loaded, "__file__", "")).resolve() == path:
        return loaded
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


git_process = load_sibling("git_process")
resolve_ground = load_sibling("resolve_ground")
ship_progress = load_sibling("ship_progress")

EXPORT_PATH = ".beads/issues.jsonl"
AUDIT_LOG_PATH = resolve_ground.AUDIT_LOG_PATH
WORKTREE_PREFIX = "tadw-ship-candidate-"

# Runs the gate in a directory; True when every gate passed.
Gate = Callable[[Path], bool]


@dataclass(frozen=True)
class BeadActions:
    """Tracker actions that must travel together when shipping a bead."""

    close: Callable[[Path], None]
    reopen: Callable[[Path], None]
    already_closed: bool = False


class CandidateStop(Exception):
    """The landing must stop here; `reason` is one word for the report."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class Recorder(Protocol):
    def mark(self, state: str, **facts: object) -> None: ...


class NoRecord:
    """For a caller that keeps no progress record."""

    def mark(self, state: str, **facts: object) -> None:
        pass


@dataclass(frozen=True)
class Plan:
    """What to land: the feature branch, where it lands, the commit subject, and where each
    step is recorded."""

    branch: str
    default_branch: str
    subject: str
    record: Recorder = field(default_factory=NoRecord)


@dataclass(frozen=True)
class Landing:
    """The commit that passed the gate, which is the commit the default branch carries."""

    parent: str
    commit: str
    checked_commit: str
    local_commits: tuple[str, ...]

    def report_lines(self) -> list[str]:
        return [
            f"tadw_ship: checked candidate {self.checked_commit[:12]} on {self.parent[:12]}",
            *(
                f"tadw_ship: local commit in the checked tree: {sha[:12]}"
                for sha in self.local_commits
            ),
        ]


def land_candidate(
    repo: Path,
    plan: Plan,
    gate: Gate,
    bead: BeadActions | None = None,
) -> Landing:
    """Build, check, and land the candidate; raise `CandidateStop` instead of half-landing."""
    refuse_unsafe_checkout(repo)
    parent = resolve_commit(repo, f"refs/heads/{plan.default_branch}")
    branch_tip = resolve_commit(repo, f"refs/heads/{plan.branch}")
    local_commits = local_commits_beyond_remote(repo, plan.default_branch, parent)
    worktree = Path(tempfile.mkdtemp(prefix=WORKTREE_PREFIX)) / "tree"
    bead_closed = bead is not None and bead.already_closed
    branch_advance_started = False
    branch_advanced = False
    record = plan.record
    try:
        record.mark(ship_progress.STARTED, parent=parent, candidate_worktree=str(worktree))
        git(repo, "worktree", "add", "--detach", str(worktree), parent)
        commit = commit_candidate(worktree, plan)
        record.mark(ship_progress.CANDIDATE, checked_commit=commit, branch_tip=branch_tip)
        verify_checked_tree(worktree, commit, gate)

        if bead is not None and not bead.already_closed:
            bead_closed = True
            bead.close(worktree)

        record.mark(ship_progress.LANDING, landing_commit=commit)
        branch_advance_started = True
        advance_default_branch(repo, plan.default_branch, parent, commit)
        branch_advanced = True
        record.mark(ship_progress.LANDED)
    # A user interrupt must reopen a bead before the temporary worktree is removed.
    except BaseException as failure:
        landing_reached_default = branch_advanced
        if bead_closed and branch_advance_started and not landing_reached_default:
            landing_reached_default = default_branch_contains(repo, plan.default_branch, commit)
        if bead_closed and not landing_reached_default:
            try:
                bead.reopen(worktree)
            except Exception as reopen_failure:
                raise CandidateStop(
                    "export",
                    f"landing stopped ({failure}); bd could not reopen the bead: {reopen_failure}",
                ) from reopen_failure
        raise
    finally:
        preserve_audit_log(worktree, repo)
        remove_worktree(repo, worktree)
    return Landing(parent, commit, commit, local_commits)


def later_local_commits(repo: Path, default_branch: str, checked_commit: str) -> list[str]:
    """Commits on the default branch after the checked one, for example a pre-push export commit."""
    return git(repo, "rev-list", f"{checked_commit}..refs/heads/{default_branch}").split()


def unpushed_report_lines(later_commits: list[str]) -> list[str]:
    """Name each later commit as unpushed and unchecked, never as part of this landing."""
    return [
        f"tadw_ship: unpushed local commit {sha[:12]}, created after the check; "
        "this run did not check or publish it"
        for sha in later_commits
    ]


def refuse_unsafe_checkout(repo: Path) -> None:
    stop = resolve_ground.mutation_guard(repo)
    if stop is not None:
        raise CandidateStop(stop, f"{repo} must have no changed tracked files before landing")


def local_commits_beyond_remote(repo: Path, default_branch: str, tip: str) -> tuple[str, ...]:
    remote = f"refs/remotes/origin/{default_branch}"
    if git_or_none(repo, "rev-parse", "--verify", "--quiet", remote) is None:
        return ()
    return tuple(reversed(git(repo, "rev-list", f"{remote}..{tip}").split()))


def commit_candidate(worktree: Path, plan: Plan) -> str:
    """Squash the feature branch and commit the tree the gate will check."""
    if not squash_merge(worktree, plan.branch):
        raise CandidateStop(
            "conflict", f"squashing {plan.branch} conflicts with the default branch"
        )
    if not git(worktree, "diff", "--cached", "--name-only"):
        raise CandidateStop("empty", f"{plan.branch} adds nothing to the default branch")
    commit_through_hook(worktree, plan.subject)
    return resolve_commit(worktree, "HEAD")


def commit_through_hook(worktree: Path, subject: str) -> None:
    """The pre-commit hook runs here, so a commit it refuses is a failed gate."""
    completed = run_git(worktree, ("commit", "--quiet", "-m", subject))
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise CandidateStop("gate", f"the candidate commit was refused: {detail}")


def squash_merge(worktree: Path, branch: str) -> bool:
    return run_git(worktree, ("merge", "--squash", f"refs/heads/{branch}")).returncode == 0


def verify_checked_tree(worktree: Path, commit: str, gate: Gate) -> None:
    require_untracked_audit_log(worktree, commit)
    require_clean_tree(worktree, "the pre-commit hook left the candidate dirty")
    if not gate(worktree):
        raise CandidateStop("gate", "the gate failed on the candidate commit")
    require_clean_tree(worktree, "the gate changed a tracked file")


def require_untracked_audit_log(worktree: Path, commit: str) -> None:
    if git(worktree, "ls-tree", "--name-only", commit, "--", AUDIT_LOG_PATH):
        raise CandidateStop("audit-log", untrack_audit_log_message())


def untrack_audit_log_message() -> str:
    return (
        f"{AUDIT_LOG_PATH} must stay untracked (ADR 0010). Fix it on the branch: run "
        f"`git rm --cached {AUDIT_LOG_PATH}`, add `interactions.jsonl` to `.beads/.gitignore`, "
        "and commit both"
    )


def require_clean_tree(worktree: Path, detail: str) -> None:
    stop = resolve_ground.mutation_guard(worktree)
    if stop is not None:
        raise CandidateStop(stop, detail)


def advance_default_branch(repo: Path, default_branch: str, parent: str, commit: str) -> None:
    """Fast-forward only while the branch still names the candidate's parent."""
    reference = f"refs/heads/{default_branch}"
    if resolve_commit(repo, reference) != parent:
        raise CandidateStop("base-moved", f"{default_branch} moved after the candidate was built")
    holder = resolve_ground.worktree_holding(resolve_ground.read_worktrees(repo), default_branch)
    if holder is None:
        git(repo, "update-ref", reference, commit, parent)
        return
    require_clean_holder(Path(holder), default_branch)
    git(Path(holder), "merge", "--ff-only", "--quiet", commit)


def default_branch_contains(repo: Path, default_branch: str, commit: str) -> bool:
    """Check whether a failed branch advance nevertheless made the landing reachable."""
    result = run_git(
        repo,
        ("merge-base", "--is-ancestor", commit, f"refs/heads/{default_branch}"),
    )
    if result.returncode not in (0, 1):
        detail = (result.stderr or result.stdout).strip()
        raise CandidateStop(
            "git",
            f"cannot tell whether {default_branch} contains {commit[:12]}: {detail}",
        )
    return result.returncode == 0


def require_clean_holder(holder: Path, default_branch: str) -> None:
    """Stop on any changed tracked file in the checkout that holds the default branch.

    A status git could not read stops as well: it is not a clean tree.
    """
    changed = resolve_ground.read_status(holder, untracked=False)
    if changed is None or changed:
        raise CandidateStop(
            "default-checkout-dirty",
            f"{holder} holds {default_branch} with changed tracked files; nothing was moved",
        )


def preserve_audit_log(worktree: Path, repo: Path) -> None:
    """Append audit lines `bd` wrote inside the temporary worktree to the caller's own log.

    Removing the worktree would otherwise delete them. The log stays untracked (ADR 0010).
    """
    written = worktree / AUDIT_LOG_PATH
    if not written.is_file():
        return
    kept = repo / AUDIT_LOG_PATH
    with contextlib.suppress(OSError):
        kept.parent.mkdir(parents=True, exist_ok=True)
        separator = b"\n" if ends_mid_line(kept) else b""
        with kept.open("ab") as log:
            log.write(separator + written.read_bytes())


def ends_mid_line(path: Path) -> bool:
    """True when the file has content and its last byte is not a newline."""
    if not path.is_file():
        return False
    data = path.read_bytes()
    return bool(data) and not data.endswith(b"\n")


def remove_worktree(repo: Path, worktree: Path) -> None:
    """Remove only the worktree this run created; a failure here never hides the landing result."""
    git_or_none(repo, "worktree", "remove", "--force", str(worktree))
    git_or_none(repo, "worktree", "prune")
    with contextlib.suppress(OSError):
        worktree.parent.rmdir()


def resolve_commit(directory: Path, revision: str) -> str:
    stdout = commit_or_none(directory, revision)
    if stdout is None:
        raise CandidateStop("revision", f"{revision} does not name a commit in {directory}")
    return stdout


def commit_or_none(directory: Path, revision: str) -> str | None:
    """The commit `revision` names, or None when it names none."""
    return git_or_none(directory, "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}")


def git(directory: Path, *arguments: str) -> str:
    """Stdout with surrounding whitespace removed; a non-zero exit stops the landing."""
    try:
        return git_process.read(directory, *arguments).strip()
    except git_process.GitFailed as error:
        detail = (error.stderr or error.stdout).strip()
        raise CandidateStop("git", f"git {' '.join(arguments)} failed: {detail}") from error
    except git_process.GitUnavailable as error:
        raise CandidateStop("git", str(error)) from error


def git_or_none(directory: Path, *arguments: str) -> str | None:
    try:
        stdout = git_process.ask(directory, *arguments)
    except git_process.GitUnavailable as error:
        raise CandidateStop("git", str(error)) from error
    return None if stdout is None else stdout.strip()


def run_git(directory: Path, arguments: tuple[str, ...]) -> subprocess.CompletedProcess:
    try:
        return git_process.run(directory, *arguments)
    except git_process.GitUnavailable as error:
        raise CandidateStop("git", str(error)) from error
