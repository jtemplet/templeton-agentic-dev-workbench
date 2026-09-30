#!/usr/bin/env python3
"""Build the exact commit ship will land, check it, and only then advance the default branch.

The older order ran the gate before the squash and the tracker export, so the tree
that passed was not the tree that was published. Here the candidate is committed
first, in a temporary worktree cut from the local default-branch tip, and the
gate runs against that clean commit. The default branch and the feature branch
are never moved until the gate has passed on the committed tree.

The steps, each of which stops the run with a `CandidateStop` and leaves the
default branch, the feature branch, and every checkout it did not create as they
were:

  1. Refuse a feature checkout with changed tracked files, or an unreadable status.
  2. Cut a detached worktree at the local default-branch tip. That tip includes
     local commits beyond the remote base, so they are in the checked tree.
  3. Squash the feature branch into it, export the tracker, and make the gated
     commit. A pre-commit hook can run here.
  4. Require a clean tree after the hook, then run the gate on the code tree.
  5. After the gate passes, close the bead and export the tracker again. Make a
     landing commit whose only change from the gated commit is the export.
  6. Advance the default branch only while it still names the candidate's parent,
     and only through a checkout that holds no unrelated tracked changes. A
     checkout whose only change is the tracker export has that one file restored
     first: `bd` auto-export rewrites it from any worktree, the candidate carries
     a fresher copy, and `bd export` regenerates it from the database.

Each step is recorded before and after it runs through the `record` the caller
passes (ship_progress.py), so an interrupted landing can be resumed (tadw-dur4).
A bead the run already closed is not closed again: the candidate's first export
carries that close, so the gated commit is the landing commit.

`.beads/interactions.jsonl` is an untracked audit log (ADR 0010). It is never
staged, and a candidate that carries it is rejected.

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
    """Load a helper from this file's own directory, never from another installed copy."""
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resolve_ground = load_sibling("resolve_ground")
ship_progress = load_sibling("ship_progress")

EXPORT_PATH = ".beads/issues.jsonl"
AUDIT_LOG_PATH = resolve_ground.AUDIT_LOG_PATH
WORKTREE_PREFIX = "tadw-ship-candidate-"

# Runs the gate in a directory; True when every gate passed.
Gate = Callable[[Path], bool]
# Runs `bd export` from a directory into a file path; True when the file was written.
# A bead-free ship passes None, so no export is written, staged, or compared.
ExportRunner = Callable[[Path, Path], bool] | None


@dataclass(frozen=True)
class BeadActions:
    """Tracker actions that must travel together when shipping a bead."""

    close: Callable[[Path], None]
    reopen: Callable[[Path], None]
    already_closed: bool = False


@dataclass(frozen=True)
class TrackerActions:
    """Tracker operations that keep the landing export in sync with a bead close."""

    export: ExportRunner
    bead: BeadActions | None = None


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
    """The code commit that passed the gate and the commit the default branch carries."""

    parent: str
    commit: str
    checked_commit: str
    local_commits: tuple[str, ...]
    restored_export_in: Path | None = None

    def report_lines(self) -> list[str]:
        lines = [f"tadw_ship: checked candidate {self.checked_commit[:12]} on {self.parent[:12]}"]
        if self.commit != self.checked_commit:
            lines.append(f"tadw_ship: landing commit {self.commit[:12]} adds {EXPORT_PATH} only")
        lines += [
            f"tadw_ship: local commit in the checked tree: {sha[:12]}" for sha in self.local_commits
        ]
        if self.restored_export_in is not None:
            lines.append(restored_export_line(self.restored_export_in))
        return lines


def restored_export_line(holder: Path) -> str:
    return (
        f"tadw_ship: restored {EXPORT_PATH} in {holder} before the fast-forward; "
        "bd export regenerates it"
    )


def land_candidate(
    repo: Path,
    plan: Plan,
    gate: Gate,
    tracker: TrackerActions | None = None,
) -> Landing:
    """Build, check, and land the candidate; raise `CandidateStop` instead of half-landing."""
    refuse_unsafe_checkout(repo)
    parent = resolve_commit(repo, f"refs/heads/{plan.default_branch}")
    branch_tip = resolve_commit(repo, f"refs/heads/{plan.branch}")
    local_commits = local_commits_beyond_remote(repo, plan.default_branch, parent)
    worktree = Path(tempfile.mkdtemp(prefix=WORKTREE_PREFIX)) / "tree"
    bead = None if tracker is None else tracker.bead
    bead_closed = bead is not None and bead.already_closed
    branch_advance_started = False
    branch_advanced = False
    record = plan.record
    try:
        record.mark(ship_progress.STARTED, parent=parent, candidate_worktree=str(worktree))
        git(repo, "worktree", "add", "--detach", str(worktree), parent)
        export = None if tracker is None else tracker.export
        checked_commit = commit_candidate(worktree, plan, export)
        record.mark(ship_progress.CANDIDATE, checked_commit=checked_commit, branch_tip=branch_tip)
        verify_checked_tree(worktree, checked_commit, gate)

        commit = checked_commit
        if bead is not None and not bead.already_closed:
            bead_closed = True
            bead.close(worktree)
            commit = commit_landing_tree(worktree, plan.subject, checked_commit, tracker.export)

        record.mark(ship_progress.LANDING, landing_commit=commit)
        branch_advance_started = True
        restored_export_in = advance_default_branch(repo, plan.default_branch, parent, commit)
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
    return Landing(parent, commit, checked_commit, local_commits, restored_export_in)


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


def commit_candidate(worktree: Path, plan: Plan, export: ExportRunner) -> str:
    """Squash the feature branch, export the tracker, and commit the tree the gate will check."""
    if not squash_merge(worktree, plan.branch):
        raise CandidateStop(
            "conflict", f"squashing {plan.branch} conflicts with the default branch"
        )
    if export is not None:
        if not export(worktree, worktree / EXPORT_PATH):
            raise CandidateStop("export", "bd export did not write the tracker export")
        stage_export(worktree)
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


def stage_export(worktree: Path) -> None:
    """Stage the export alone; the audit log is untracked and is never staged."""
    git(worktree, "add", "--", EXPORT_PATH)


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


def commit_landing_tree(
    worktree: Path, subject: str, checked_commit: str, export: ExportRunner
) -> str:
    """Commit the post-close export on the checked tree without running hooks twice."""
    if export is None or not export(worktree, worktree / EXPORT_PATH):
        raise CandidateStop("export", "bd export did not write the tracker after closing the bead")

    stage_export(worktree)
    staged = git(worktree, "diff", "--cached", "--name-only").splitlines()
    unstaged = git(worktree, "diff", "--name-only").splitlines()
    if staged != [EXPORT_PATH] or unstaged:
        raise CandidateStop(
            "export-drift",
            f"the landing tree must change only {EXPORT_PATH}; staged={staged}, unstaged={unstaged}",
        )

    tree = git(worktree, "write-tree")
    commit = git(worktree, "commit-tree", tree, "-p", checked_commit, "-m", subject)
    changed = git(worktree, "diff", "--name-only", checked_commit, commit).splitlines()
    if changed != [EXPORT_PATH]:
        raise CandidateStop(
            "export-drift",
            f"the landing commit must change only {EXPORT_PATH}; changed={changed}",
        )

    git(worktree, "reset", "--hard", commit)
    require_clean_tree(worktree, "the landing commit left the candidate dirty")
    return commit


def advance_default_branch(
    repo: Path, default_branch: str, parent: str, commit: str
) -> Path | None:
    """Fast-forward only while the branch still names the candidate's parent.

    Returns the checkout whose tracker export was restored first, or None.
    """
    reference = f"refs/heads/{default_branch}"
    if resolve_commit(repo, reference) != parent:
        raise CandidateStop("base-moved", f"{default_branch} moved after the candidate was built")
    holder = resolve_ground.worktree_holding(resolve_ground.read_worktrees(repo), default_branch)
    if holder is None:
        git(repo, "update-ref", reference, commit, parent)
        return None
    restored = restore_stale_export(Path(holder), default_branch)
    git(Path(holder), "merge", "--ff-only", "--quiet", commit)
    return Path(holder) if restored else None


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


def restore_stale_export(holder: Path, default_branch: str) -> bool:
    """Restore the export when it is the holder's only changed tracked file; stop on anything else."""
    changed = resolve_ground.read_status(holder, untracked=False)
    if changed == []:
        return False
    if changed == [EXPORT_PATH]:
        git(holder, "checkout", "HEAD", "--", EXPORT_PATH)  # HEAD also resets a staged copy
        return True
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
    completed = run_git(directory, arguments)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise CandidateStop("git", f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def git_or_none(directory: Path, *arguments: str) -> str | None:
    completed = run_git(directory, arguments)
    return None if completed.returncode != 0 else completed.stdout.strip()


def run_git(directory: Path, arguments: tuple[str, ...]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *arguments], capture_output=True, text=True, check=False
        )
    except FileNotFoundError as error:
        raise CandidateStop("git", "git is not on PATH") from error
