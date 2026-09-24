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
  3. Squash the feature branch into it, run `bd export`, and commit. The
     pre-commit hook may fold a refreshed export into the same commit.
  4. Require the tree to be clean after the hook, then run the gate on it.
  5. Reject the candidate when the gate changed a tracked file, or when a fresh
     tracker export differs from the export the candidate commit carries.
  6. Advance the default branch only while it still names the candidate's parent,
     and only through a checkout that holds no unrelated tracked changes.

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


resolve_ground = load_sibling("resolve_ground")

EXPORT_PATH = ".beads/issues.jsonl"
AUDIT_LOG_PATH = ".beads/interactions.jsonl"
WORKTREE_PREFIX = "tadw-ship-candidate-"

# Runs the gate in a directory; True when every gate passed.
Gate = Callable[[Path], bool]
# Runs `bd export` from a directory into a file path; True when the file was written.
# A bead-free ship passes None, so no export is written, staged, or compared.
ExportRunner = Callable[[Path, Path], bool] | None


class CandidateStop(Exception):
    """The landing must stop here; `reason` is one word for the report."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class Plan:
    """What to land: the feature branch, where it lands, and the candidate's commit subject."""

    branch: str
    default_branch: str
    subject: str


@dataclass(frozen=True)
class Landing:
    """What a landing checked and moved, recorded once for the report."""

    parent: str
    commit: str
    local_commits: tuple[str, ...]

    def report_lines(self) -> list[str]:
        lines = [f"tadw_ship: checked candidate {self.commit[:12]} on {self.parent[:12]}"]
        lines += [
            f"tadw_ship: local commit in the checked tree: {sha[:12]}" for sha in self.local_commits
        ]
        return lines


def land_candidate(repo: Path, plan: Plan, gate: Gate, export: ExportRunner) -> Landing:
    """Build, check, and land the candidate; raise `CandidateStop` instead of half-landing."""
    refuse_unsafe_checkout(repo)
    parent = resolve_commit(repo, f"refs/heads/{plan.default_branch}")
    local_commits = local_commits_beyond_remote(repo, plan.default_branch, parent)
    worktree = Path(tempfile.mkdtemp(prefix=WORKTREE_PREFIX)) / "tree"
    try:
        git(repo, "worktree", "add", "--detach", str(worktree), parent)
        commit = commit_candidate(worktree, plan, export)
        verify_checked_tree(worktree, commit, gate, export)
        advance_default_branch(repo, plan.default_branch, parent, commit)
    finally:
        preserve_audit_log(worktree, repo)
        remove_worktree(repo, worktree)
    return Landing(parent=parent, commit=commit, local_commits=local_commits)


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
    """Squash the feature branch, export the tracker, and commit; the hook may add to the commit."""
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
    git(worktree, "commit", "--quiet", "-m", plan.subject)
    return resolve_commit(worktree, "HEAD")


def squash_merge(worktree: Path, branch: str) -> bool:
    return run_git(worktree, ("merge", "--squash", f"refs/heads/{branch}")).returncode == 0


def stage_export(worktree: Path) -> None:
    """Stage the export alone; the audit log is untracked and is never staged."""
    git(worktree, "add", "--", EXPORT_PATH)


def verify_checked_tree(worktree: Path, commit: str, gate: Gate, export: ExportRunner) -> None:
    require_untracked_audit_log(worktree, commit)
    require_clean_tree(worktree, "the pre-commit hook left the candidate dirty")
    if not gate(worktree):
        raise CandidateStop("gate", "the gate failed on the candidate commit")
    require_clean_tree(worktree, "the gate changed a tracked file")
    if export is not None:
        require_matching_export(worktree, export)


def require_untracked_audit_log(worktree: Path, commit: str) -> None:
    if git(worktree, "ls-tree", "--name-only", commit, "--", AUDIT_LOG_PATH):
        raise CandidateStop("audit-log", f"{AUDIT_LOG_PATH} must stay untracked")


def require_clean_tree(worktree: Path, detail: str) -> None:
    stop = resolve_ground.mutation_guard(worktree)
    if stop is not None:
        raise CandidateStop(stop, detail)


def require_matching_export(worktree: Path, export: Callable[[Path, Path], bool]) -> None:
    """A fresh export must match the committed one byte for byte, or the check is stale."""
    with tempfile.TemporaryDirectory(prefix="tadw-ship-export-") as directory:
        fresh = Path(directory) / "issues.jsonl"
        if not export(worktree, fresh):
            raise CandidateStop("export", "bd export failed after the gate")
        committed = worktree / EXPORT_PATH
        if not committed.is_file() or committed.read_bytes() != fresh.read_bytes():
            raise CandidateStop("export-drift", "the tracker export changed while the gate ran")


def advance_default_branch(repo: Path, default_branch: str, parent: str, commit: str) -> None:
    """Fast-forward only while the branch still names the candidate's parent."""
    reference = f"refs/heads/{default_branch}"
    if resolve_commit(repo, reference) != parent:
        raise CandidateStop("base-moved", f"{default_branch} moved after the candidate was built")
    holder = resolve_ground.worktree_holding(resolve_ground.read_worktrees(repo), default_branch)
    if holder is None:
        git(repo, "update-ref", reference, commit, parent)
        return
    if resolve_ground.mutation_guard(Path(holder)) is not None:
        raise CandidateStop(
            "default-checkout-dirty",
            f"{holder} holds {default_branch} with changed tracked files; nothing was moved",
        )
    git(Path(holder), "merge", "--ff-only", "--quiet", commit)


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
    stdout = git_or_none(directory, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if stdout is None:
        raise CandidateStop("revision", f"{revision} does not name a commit in {directory}")
    return stdout


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
