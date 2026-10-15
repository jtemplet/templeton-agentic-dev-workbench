#!/usr/bin/env python3
"""Regression suite for commit_left_work.py.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_commit_left_work.py

Every case builds a real repository in a temporary directory, because the
behavior under test is what git stages and commits. The end-to-end cases, where
a full ship lands the committed work and removes the worktree, are in
test_ship_recovery.py, which already holds a repository with an origin.

  tadw-aqp6 criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. A modified tracked file and a new untracked    case_modified_and_untracked_paths_are_committed,
     file are both committed                        case_deleted_tracked_file_is_committed
  2. A secret-shaped path stops the run, names      case_secret_shaped_path_stops_and_stages_nothing,
     the path, and stages nothing                   case_template_env_file_is_committed
  3. A refused commit leaves nothing staged or      case_refused_commit_leaves_nothing_staged
     committed, and says why
  4. The default branch, a detached HEAD, and an    case_default_branch_commits_nothing,
     operation in progress commit nothing           case_detached_head_commits_nothing,
                                                    case_operation_in_progress_commits_nothing
  5. An ignored file is never committed             case_ignored_file_is_not_committed
  6. The committed paths are returned               case_modified_and_untracked_paths_are_committed,
                                                    case_clean_branch_commits_nothing
"""

from __future__ import annotations

import contextlib
import importlib.util
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


commit_left_work = load("commit_left_work")

passed = 0
failed = 0


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


@contextlib.contextmanager
def feature_branch() -> Iterator[Path]:
    """A repository on a feature branch, with one tracked file and an ignore rule."""
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory).resolve()
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.name", "t")
        git(repo, "config", "user.email", "t@t")
        (repo / ".gitignore").write_text("*.log\n")
        (repo / "tracked.txt").write_text("one\n")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "base")
        git(repo, "switch", "-q", "-c", "feature/x/thing")
        yield repo


def head_files(repo: Path) -> list[str]:
    return git(repo, "show", "--name-only", "--format=", "HEAD").splitlines()


def staged(repo: Path) -> str:
    return git(repo, "diff", "--cached", "--name-only")


def case_modified_and_untracked_paths_are_committed() -> None:
    with feature_branch() as repo:
        (repo / "tracked.txt").write_text("two\n")
        (repo / "new.txt").write_text("new\n")
        committed = commit_left_work.commit_left_work(repo)
        assert committed == ["new.txt", "tracked.txt"], committed
        assert head_files(repo) == ["new.txt", "tracked.txt"], head_files(repo)
        assert git(repo, "status", "--porcelain") == "", git(repo, "status", "--porcelain")


def case_deleted_tracked_file_is_committed() -> None:
    with feature_branch() as repo:
        (repo / "tracked.txt").unlink()
        commit_left_work.commit_left_work(repo)
        assert git(repo, "ls-files", "tracked.txt") == "", "the deletion was not committed"


def case_secret_shaped_path_stops_and_stages_nothing() -> None:
    for name in (".env", ".env.production", "server.pem", "AuthKey_X.p8", "cert.p12", "id.key"):
        with feature_branch() as repo:
            (repo / "tracked.txt").write_text("two\n")
            (repo / name).write_text("secret\n")
            try:
                commit_left_work.commit_left_work(repo)
            except commit_left_work.LeftWorkStop as stopped:
                assert name in str(stopped), stopped
            else:
                raise AssertionError(f"{name} did not stop the run")
            assert staged(repo) == "", staged(repo)
            assert git(repo, "rev-list", "--count", "HEAD") == "1", f"{name} was committed"


def case_template_env_file_is_committed() -> None:
    with feature_branch() as repo:
        (repo / ".env.example").write_text("KEY=\n")
        assert commit_left_work.commit_left_work(repo) == [".env.example"]


def case_refused_commit_leaves_nothing_staged() -> None:
    with feature_branch() as repo:
        hook = repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'lint found 3 errors' >&2\nexit 1\n")
        hook.chmod(0o755)
        (repo / "tracked.txt").write_text("two\n")
        (repo / "new.txt").write_text("new\n")
        try:
            commit_left_work.commit_left_work(repo)
        except commit_left_work.LeftWorkStop as stopped:
            assert "lint found 3 errors" in str(stopped), stopped
        else:
            raise AssertionError("a refused commit did not stop the run")
        assert staged(repo) == "", staged(repo)
        assert git(repo, "rev-list", "--count", "HEAD") == "1", "something was committed"


def case_default_branch_commits_nothing() -> None:
    with feature_branch() as repo:
        git(repo, "switch", "-q", "main")
        (repo / "tracked.txt").write_text("two\n")
        assert commit_left_work.commit_left_work(repo) == []
        assert git(repo, "rev-list", "--count", "HEAD") == "1"


def case_detached_head_commits_nothing() -> None:
    with feature_branch() as repo:
        git(repo, "switch", "-q", "--detach")
        (repo / "tracked.txt").write_text("two\n")
        assert commit_left_work.commit_left_work(repo) == []


def case_operation_in_progress_commits_nothing() -> None:
    with feature_branch() as repo:
        (repo / ".git" / "MERGE_HEAD").write_text(git(repo, "rev-parse", "HEAD") + "\n")
        (repo / "tracked.txt").write_text("two\n")
        assert commit_left_work.commit_left_work(repo) == []


def case_ignored_file_is_not_committed() -> None:
    with feature_branch() as repo:
        (repo / "build.log").write_text("noise\n")
        (repo / "new.txt").write_text("new\n")
        assert commit_left_work.commit_left_work(repo) == ["new.txt"]
        assert "build.log" not in head_files(repo), head_files(repo)


def case_clean_branch_commits_nothing() -> None:
    with feature_branch() as repo:
        assert commit_left_work.commit_left_work(repo) == []
        assert git(repo, "rev-list", "--count", "HEAD") == "1"


for name, fn in [
    ("1. modified and untracked paths are committed", case_modified_and_untracked_paths_are_committed),
    ("1. a deleted tracked file is committed", case_deleted_tracked_file_is_committed),
    ("2. a secret-shaped path stops and stages nothing",
     case_secret_shaped_path_stops_and_stages_nothing),
    ("2. a template env file is committed", case_template_env_file_is_committed),
    ("3. a refused commit leaves nothing staged", case_refused_commit_leaves_nothing_staged),
    ("4. the default branch commits nothing", case_default_branch_commits_nothing),
    ("4. a detached HEAD commits nothing", case_detached_head_commits_nothing),
    ("4. an operation in progress commits nothing", case_operation_in_progress_commits_nothing),
    ("5. an ignored file is not committed", case_ignored_file_is_not_committed),
    ("6. a clean branch commits nothing", case_clean_branch_commits_nothing),
]:  # fmt: skip
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
