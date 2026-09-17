#!/usr/bin/env python3
"""Regression suite for landed_check.py.

Stdlib only, no install, mirroring test_check_worktree_occupants.py. Run with:
    python3 skills/ship/scripts/test_landed_check.py

Every case builds a real git repository in a temporary directory and runs real
commits through it, because the thing under test is what `git diff` reports for
a given pair of ranges. A stubbed git would pin this suite's idea of that answer
rather than git's.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-vds criterion                              Pinned by
  ------------------------------------------------------------------------------
  1. A landed branch that also wrote .beads       case_landed_branch_with_beads_is_silent
     passes with no output (tadw-0fo)
  2. An unlanded file is printed, exit 1          case_unlanded_file_is_reported

  tadw-0fo criterion
  ------------------------------------------------------------------------------
  1. .beads/issues.jsonl alone prints nothing     case_beads_only_difference_is_silent
  2. A missing non-.beads file still stops        case_unlanded_file_is_reported

  Design decisions in the script's docstring
  ------------------------------------------------------------------------------
  Paths never cross a shell word split            case_path_with_spaces_is_reported
  A target-only change is not this branch's       case_target_only_change_is_ignored
  A branch edit the target already holds is done  case_matching_content_is_silent
  Component matching, not string prefix           case_sibling_prefix_is_not_excluded
  --exclude adds to the built-in exclusion        case_extra_exclusion_is_honored
  Operator error is 2, never 1                    case_unknown_ref_exits_2,
                                                  case_missing_repo_exits_2
  Stdlib only                                     case_no_third_party_imports

Every repository here sets `core.excludesFile` to the null device. Without it the
developer's own `~/.gitignore` reaches in: it ignores `dist`, which made the
--exclude case pass against an empty diff and hold nothing at all.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "landed_check.py"

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


def git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def new_repo(directory: Path) -> Path:
    repo = directory / "repo"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main", "--quiet")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    # Without this the developer's own ~/.gitignore reaches in. It ignores
    # `dist`, so the --exclude case passed against an empty diff and held
    # nothing at all.
    git(repo, "config", "core.excludesFile", os.devnull)
    write(repo, "README.md", "start\n")
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "initial")
    return repo


def write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", message)


def run_check(repo: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--base",
            "main",
            "--branch",
            "feature",
            "--target",
            "main",
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def branch_and_edit(repo: Path, files: dict[str, str]) -> None:
    """Cut `feature` from main and commit one edit per named file."""
    git(repo, "switch", "--quiet", "-c", "feature")
    for relative, text in files.items():
        write(repo, relative, text)
    commit(repo, "feature work")
    git(repo, "switch", "--quiet", "main")


def case_unlanded_file_is_reported() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {"src/app.py": "branch\n"})
        result = run_check(repo)
        assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
        assert result.stdout.split() == ["src/app.py"], result.stdout


def case_matching_content_is_silent() -> None:
    """The branch edit landed: main now holds the same bytes."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {"src/app.py": "branch\n"})
        write(repo, "src/app.py", "branch\n")
        commit(repo, "same content by another route")
        result = run_check(repo)
        assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stdout}"
        assert result.stdout == "", result.stdout


def case_beads_only_difference_is_silent() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {".beads/issues.jsonl": '{"id":"a"}\n'})
        result = run_check(repo)
        assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stdout}"
        assert result.stdout == "", result.stdout


def case_landed_branch_with_beads_is_silent() -> None:
    """tadw-0fo: the deliverable landed, and only the tracker export differs."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(
            repo,
            {"src/app.py": "branch\n", ".beads/issues.jsonl": '{"id":"branch"}\n'},
        )
        write(repo, "src/app.py", "branch\n")
        write(repo, ".beads/issues.jsonl", '{"id":"main"}\n')
        commit(repo, "land the deliverable, re-export the tracker")
        result = run_check(repo)
        assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stdout}"
        assert result.stdout == "", result.stdout


def case_target_only_change_is_ignored() -> None:
    """A file only main touched is not this branch's outstanding work."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {"src/app.py": "branch\n"})
        write(repo, "docs/other.md", "main only\n")
        commit(repo, "unrelated work on main")
        result = run_check(repo)
        assert result.stdout.split() == ["src/app.py"], result.stdout


def case_path_with_spaces_is_reported() -> None:
    """The failure the shell pipeline had: a path list that word-splits."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {"docs/release notes.md": "branch\n"})
        result = run_check(repo)
        assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
        assert result.stdout.strip() == "docs/release notes.md", result.stdout


def case_sibling_prefix_is_not_excluded() -> None:
    """`.beads-archive` shares a string prefix with `.beads` and is not it."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {".beads-archive/old.jsonl": "branch\n"})
        result = run_check(repo)
        assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
        assert result.stdout.strip() == ".beads-archive/old.jsonl", result.stdout


def case_extra_exclusion_is_honored() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {"dist/bundle.js": "branch\n", "src/app.py": "branch\n"})
        result = run_check(repo, "--exclude", "dist")
        assert result.stdout.split() == ["src/app.py"], result.stdout


def case_dotfile_exclusion_is_honored() -> None:
    """`lstrip("./")` strips a character set, so it turned `.github` into `github`."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        branch_and_edit(repo, {".github/workflows/ci.yml": "branch\n", "src/app.py": "branch\n"})
        result = run_check(repo, "--exclude", ".github")
        assert result.stdout.split() == ["src/app.py"], result.stdout


def case_non_ascii_path_is_reported_raw() -> None:
    """core.quotePath defaults on, and a quoted path matches no --exclude prefix."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        git(repo, "config", "core.quotePath", "true")
        branch_and_edit(repo, {"dist/caf\u00e9.js": "branch\n", "src/app.py": "branch\n"})
        reported = run_check(repo).stdout.splitlines()
        assert len(reported) == 2, reported
        # Compared by shape, not by spelling: macOS stores the name decomposed,
        # so asserting the composed form would test the filesystem, not git.
        non_ascii = [path for path in reported if path != "src/app.py"]
        assert not non_ascii[0].startswith('"'), f"git quoted the path: {non_ascii}"
        excluded = run_check(repo, "--exclude", "dist").stdout.splitlines()
        assert excluded == ["src/app.py"], excluded


def case_unknown_ref_exits_2() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "--repo-root", str(repo),
                "--base", "main", "--branch", "no-such-branch", "--target", "main",
            ],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 2, f"expected exit 2, got {result.returncode}"
        assert result.stdout == "", f"a failed read must print no paths: {result.stdout!r}"


def case_missing_repo_exits_2() -> None:
    with tempfile.TemporaryDirectory() as directory:
        outside = Path(directory) / "not-a-repo"
        outside.mkdir()
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "--repo-root", str(outside),
                "--base", "main", "--branch", "feature", "--target", "main",
            ],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 2, f"expected exit 2, got {result.returncode}"


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__", "argparse", "dataclasses", "os", "re", "subprocess", "sys",
        "tempfile", "pathlib",
    }
    for path in (SCRIPT, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M))
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("an unlanded file is printed and exits 1", case_unlanded_file_is_reported),
    ("a branch edit main already holds is silent", case_matching_content_is_silent),
    ("a .beads-only difference is silent", case_beads_only_difference_is_silent),
    ("a landed branch that rewrote .beads is silent", case_landed_branch_with_beads_is_silent),
    ("a change only main made is ignored", case_target_only_change_is_ignored),
    ("a path containing a space is reported whole", case_path_with_spaces_is_reported),
    ("a sibling sharing the .beads prefix is not excluded", case_sibling_prefix_is_not_excluded),
    ("--exclude adds to the built-in exclusion", case_extra_exclusion_is_honored),
    ("--exclude works for a dotfile directory", case_dotfile_exclusion_is_honored),
    ("a non-ASCII path is reported and excluded raw", case_non_ascii_path_is_reported_raw),
    ("an unknown ref exits 2 and prints no paths", case_unknown_ref_exits_2),
    ("a directory that is not a repository exits 2", case_missing_repo_exits_2),
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
