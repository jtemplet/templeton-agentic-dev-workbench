#!/usr/bin/env python3
"""Regression suite for changed_set.py.

Stdlib only, no install. Run with:
    python3 skills/quality-gates/scripts/test_changed_set.py

Every case builds a throwaway origin repository plus a clone of it, so
`origin/HEAD` exists the way it does in a real checkout, then plants one kind of
change and asserts what the script says about it.

RULE-TO-TEST MAPPING. This block is what proves the port from the skill's Step 2
prose neither narrowed nor widened the scope. A rule with no test here is a rule
nothing holds.

  Step 2 rule (skills/quality-gates/SKILL.md)    Pinned by
  ------------------------------------------------------------------------------
  Committed changes are in scope                case_all_four_kinds_appear  (criterion 1)
  Staged changes are in scope                   case_all_four_kinds_appear  (criterion 1)
  Unstaged changes are in scope                 case_all_four_kinds_appear  (criterion 1)
  Untracked files are in scope                  case_all_four_kinds_appear  (criterion 1)
  Deletions are in scope                        case_deleted_file_appears
  An untouched file is out of scope             case_unchanged_file_absent
  Base is merge-base against `origin/HEAD`      case_non_main_default_branch_resolves
  Falling back to `origin/main`                 case_origin_head_missing_falls_back
  An unresolvable base is not an empty diff     case_clean_clone_prints_nothing
  No remote exits 3                             case_no_remote_exits_3  (criterion 2)
  An unfetched remote exits 3                   case_unfetched_remote_exits_3
  Unrelated history exits 3                     case_unrelated_history_exits_3
  An unborn HEAD exits 3                        case_unborn_head_exits_3
  The base SHA never reaches stdout             case_base_sha_on_stderr_only  (criterion 3)
  Every stdout line is a path                   case_stdout_is_only_paths  (criterion 3)
  `--exclude-standard` keeps ignored files out  case_gitignored_file_absent  (criterion 4)
  Ignored directories stay out                  case_gitignored_directory_absent

Beyond the prose, three failure modes the exit codes must keep apart, because the
caller does something different for each:

  A path with a newline is omitted, not split   case_newline_path_omitted_and_named
  Operator error exits 2                        case_bad_root_exits_2, case_not_a_git_repo_exits_2
  A missing git exits 2, never 3                case_git_missing_exits_2_not_3

Bare python3 with no third-party import is pinned by case_no_third_party_imports
plus the fact that this file runs at all.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "changed_set.py"

# A fixed identity and no global excludes file, so a case tests the script rather
# than the machine it runs on. A developer's global gitignore would otherwise
# decide whether a planted untracked file is visible to `ls-files --others`.
GIT = [
    "git",
    "-c",
    "core.excludesFile=/dev/null",
    "-c",
    "user.email=t@t",
    "-c",
    "user.name=t",
]

SHA = re.compile(r"\b[0-9a-f]{7,40}\b")

passed = 0
failed = 0


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*GIT, "-C", str(root), *args], capture_output=True, text=True, check=check
    )


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), *args],
        capture_output=True,
        text=True,
    )


def build(*, default_branch: str = "main", gitignore: str = "") -> Path:
    """An origin repository with one commit, and a clone of it. Returns the clone.

    A clone is what gives the fixture a real `refs/remotes/origin/HEAD`, which is
    the ref the base resolution reaches for first. Building the remote by hand
    with `git remote add` would test the fallback path in every case and leave the
    primary one unexercised.

    The base commit holds three files the cases mutate: one to modify without
    staging, one to delete, and one to leave alone.
    """
    workspace = Path(tempfile.mkdtemp())
    origin = workspace / "origin"
    origin.mkdir()
    git(origin, "init", "-q")
    for name in ("unstaged.txt", "doomed.txt", "unchanged.txt"):
        (origin / name).write_text("base\n", encoding="utf-8")
    if gitignore:
        (origin / ".gitignore").write_text(gitignore, encoding="utf-8")
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "base")
    git(origin, "branch", "-M", default_branch)

    clone = workspace / "clone"
    git(workspace, "clone", "-q", str(origin), str(clone))
    # Local config, not a one-shot `-c`: the script runs its own git commands, and
    # they must be as isolated from the developer's global config as these are.
    git(clone, "config", "core.excludesFile", "/dev/null")
    return clone


def plant_all_four_kinds(clone: Path) -> None:
    (clone / "committed.txt").write_text("new\n", encoding="utf-8")
    git(clone, "add", "committed.txt")
    git(clone, "commit", "-qm", "committed")
    (clone / "staged.txt").write_text("new\n", encoding="utf-8")
    git(clone, "add", "staged.txt")
    (clone / "unstaged.txt").write_text("edited\n", encoding="utf-8")
    (clone / "untracked.txt").write_text("new\n", encoding="utf-8")


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


print("\n  [the four kinds of change, and what stays out]")


def case_all_four_kinds_appear() -> None:
    """Criterion 1. The reason `git diff "$BASE"...HEAD` is the wrong basis.

    That form stops at the last commit, so staged, unstaged, and untracked work
    would all be missing here while the report claimed a scoped pass.
    """
    clone = build()
    plant_all_four_kinds(clone)
    r = run(clone)
    assert r.returncode == 0, f"a resolvable base must exit 0, got {r.returncode}: {r.stderr}"
    lines = r.stdout.splitlines()
    for expected in ("committed.txt", "staged.txt", "unstaged.txt", "untracked.txt"):
        assert expected in lines, f"{expected} must be in the changed set: {lines}"


def case_unchanged_file_absent() -> None:
    clone = build()
    plant_all_four_kinds(clone)
    r = run(clone)
    # The exit code and the positive control both matter: an absence assertion
    # alone passes when the script prints nothing at all, which is the regression
    # most worth catching here.
    assert r.returncode == 0, f"the fixture must resolve, got {r.returncode}: {r.stderr}"
    lines = r.stdout.splitlines()
    assert "committed.txt" in lines, f"the set must be built: {lines}"
    assert "unchanged.txt" not in lines, f"an untouched file must stay out of scope: {lines}"


def case_deleted_file_appears() -> None:
    """A removed file is a change. A caller deciding scope needs to know it left."""
    clone = build()
    git(clone, "rm", "-q", "doomed.txt")
    r = run(clone)
    assert r.returncode == 0, f"a deletion must not break resolution: {r.stderr}"
    assert "doomed.txt" in r.stdout.splitlines(), f"a deletion must appear: {r.stdout}"


def case_clean_clone_prints_nothing() -> None:
    """Exit 0 with empty stdout is 'nothing changed', which exit 3 is not.

    The pair of assertions is the whole reason exit 3 exists: this case and
    case_no_remote_exits_3 must never collapse into the same answer.
    """
    r = run(build())
    assert r.returncode == 0, f"a clean clone must exit 0, got {r.returncode}: {r.stderr}"
    assert r.stdout.strip() == "", f"a clean clone has no changed paths: {r.stdout!r}"


def case_no_duplicate_lines() -> None:
    clone = build()
    plant_all_four_kinds(clone)
    lines = run(clone).stdout.splitlines()
    assert lines, "an empty list has no duplicates, so this case needs paths to judge"
    assert len(lines) == len(set(lines)), f"a path must be printed once: {lines}"


for name, fn in [
    ("committed, staged, unstaged, and untracked all appear [criterion 1]", case_all_four_kinds_appear),
    ("an unchanged file does not appear", case_unchanged_file_absent),
    ("a deleted file appears", case_deleted_file_appears),
    ("a clean clone exits 0 and prints nothing", case_clean_clone_prints_nothing),
    ("no path is printed twice", case_no_duplicate_lines),
]:
    check(name, fn)


print("\n  [base resolution, and the exit 3 that says 'run at --all']")


def case_no_remote_exits_3() -> None:
    """Criterion 2. Exit 3, not 0, so the caller widens instead of covering nothing."""
    root = Path(tempfile.mkdtemp())
    git(root, "init", "-q")
    (root / "app.py").write_text("print('x')\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "only")
    r = run(root)
    assert r.returncode == 3, f"no remote must exit 3, got {r.returncode}: {r.stderr}"
    assert r.stdout.strip() == "", f"an unresolved base prints no paths: {r.stdout!r}"
    assert "--all" in r.stderr, f"stderr must name the fallback: {r.stderr!r}"


def case_unfetched_remote_exits_3() -> None:
    """A configured remote with no fetched refs resolves nothing, so exit 3."""
    clone = build()
    root = Path(tempfile.mkdtemp())
    git(root, "init", "-q")
    (root / "app.py").write_text("print('x')\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "only")
    git(root, "remote", "add", "origin", str(clone))
    r = run(root)
    assert r.returncode == 3, f"an unfetched remote must exit 3, got {r.returncode}"


def case_unrelated_history_exits_3() -> None:
    """HEAD sharing no ancestor with the remote has no merge base."""
    clone = build()
    git(clone, "checkout", "-q", "--orphan", "detached-work")
    git(clone, "commit", "-qm", "unrelated root")
    r = run(clone)
    assert r.returncode == 3, f"unrelated history must exit 3, got {r.returncode}: {r.stderr}"


def case_unborn_head_exits_3() -> None:
    """A fetched remote but no local commit: HEAD points at nothing yet."""
    origin = build()  # any repository with a `main` to fetch
    root = Path(tempfile.mkdtemp())
    git(root, "init", "-q")
    git(root, "remote", "add", "origin", str(origin))
    git(root, "fetch", "-q", "origin")
    r = run(root)
    assert r.returncode == 3, f"an unborn HEAD must exit 3, got {r.returncode}: {r.stderr}"


def case_origin_head_missing_falls_back() -> None:
    """The fallback the prose names. `git remote add` plus `fetch` leaves no origin/HEAD."""
    clone = build(default_branch="main")
    git(clone, "symbolic-ref", "-d", "refs/remotes/origin/HEAD")
    plant_all_four_kinds(clone)
    r = run(clone)
    assert r.returncode == 0, f"origin/main must still resolve, got {r.returncode}: {r.stderr}"
    assert "origin/main" in r.stderr, f"stderr must name the ref used: {r.stderr!r}"
    assert "committed.txt" in r.stdout.splitlines(), f"the set must be built: {r.stdout}"


def case_non_main_default_branch_resolves() -> None:
    """origin/HEAD is resolved, not assumed. A `trunk` default must work.

    Hardcoding `origin/main` would exit 3 here, and the caller would widen every
    gate to the whole repository on a perfectly ordinary checkout.
    """
    clone = build(default_branch="trunk")
    plant_all_four_kinds(clone)
    r = run(clone)
    assert r.returncode == 0, f"a trunk default must resolve, got {r.returncode}: {r.stderr}"
    assert "origin/trunk" in r.stderr, f"stderr must name origin/trunk: {r.stderr!r}"


for name, fn in [
    ("a repository with no remote exits 3 [criterion 2]", case_no_remote_exits_3),
    ("a remote with no fetched refs exits 3", case_unfetched_remote_exits_3),
    ("unrelated history exits 3", case_unrelated_history_exits_3),
    ("an unborn HEAD exits 3", case_unborn_head_exits_3),
    ("a missing origin/HEAD falls back to origin/main", case_origin_head_missing_falls_back),
    ("a non-main default branch resolves through origin/HEAD", case_non_main_default_branch_resolves),
]:
    check(name, fn)


print("\n  [stdout is a path list a caller can pipe]")


def case_base_sha_on_stderr_only() -> None:
    """Criterion 3, first half. The SHA is on stderr and nowhere else."""
    clone = build()
    plant_all_four_kinds(clone)
    base = git(clone, "merge-base", "HEAD", "origin/main").stdout.strip()
    r = run(clone)
    assert base, "the fixture must have a resolvable base"
    assert base in r.stderr, f"the base SHA must reach stderr: {r.stderr!r}"
    assert base not in r.stdout, f"the base SHA must not reach stdout: {r.stdout!r}"


def case_stdout_is_only_paths() -> None:
    """Criterion 3, second half. Every line is a path, with no SHA anywhere."""
    clone = build()
    plant_all_four_kinds(clone)
    r = run(clone)
    expected = {"committed.txt", "staged.txt", "unstaged.txt", "untracked.txt"}
    lines = r.stdout.splitlines()
    assert set(lines) == expected, f"stdout must be exactly the changed paths: {lines}"
    assert not SHA.search(r.stdout), f"stdout must hold no SHA: {r.stdout!r}"


def case_newline_path_omitted_and_named() -> None:
    """A name with a newline cannot sit on one line, so it is reported, not split.

    Printing it would hand every downstream reader two paths that do not exist,
    which is worse than one named omission.
    """
    clone = build()
    (clone / "we\nird.txt").write_text("new\n", encoding="utf-8")
    (clone / "plain.txt").write_text("new\n", encoding="utf-8")
    r = run(clone)
    assert r.returncode == 0, f"an odd name must not break the run: {r.stderr}"
    assert r.stdout.splitlines() == ["plain.txt"], f"only printable paths: {r.stdout!r}"
    assert "newline" in r.stderr, f"the omission must be named: {r.stderr!r}"


for name, fn in [
    ("the base SHA lands on stderr, never stdout [criterion 3]", case_base_sha_on_stderr_only),
    ("every stdout line is a path and no line is a SHA [criterion 3]", case_stdout_is_only_paths),
    ("a path containing a newline is omitted and named", case_newline_path_omitted_and_named),
]:
    check(name, fn)


print("\n  [ignored files stay out of scope]")


def case_gitignored_file_absent() -> None:
    """Criterion 4. Without --exclude-standard, build output widens every gate."""
    clone = build(gitignore="secret.log\n")
    (clone / "secret.log").write_text("noise\n", encoding="utf-8")
    (clone / "kept.txt").write_text("new\n", encoding="utf-8")
    r = run(clone)
    assert r.returncode == 0, f"an ignored file must not break the run: {r.stderr}"
    assert "secret.log" not in r.stdout, f"an ignored file must stay out: {r.stdout!r}"
    assert "kept.txt" in r.stdout.splitlines(), f"the unignored file must appear: {r.stdout!r}"


def case_gitignored_directory_absent() -> None:
    clone = build(gitignore="build/\n")
    (clone / "build").mkdir()
    (clone / "build" / "out.js").write_text("noise\n", encoding="utf-8")
    (clone / "kept.txt").write_text("new\n", encoding="utf-8")
    r = run(clone)
    assert r.returncode == 0, f"an ignored directory must not break the run: {r.stderr}"
    assert "kept.txt" in r.stdout.splitlines(), f"the unignored file must appear: {r.stdout!r}"
    assert "build/" not in r.stdout, f"an ignored directory must stay out: {r.stdout!r}"


for name, fn in [
    ("a gitignored file does not appear [criterion 4]", case_gitignored_file_absent),
    ("a gitignored directory does not appear", case_gitignored_directory_absent),
]:
    check(name, fn)


print("\n  [operator errors, kept apart from exit 3]")


def case_bad_root_exits_2() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", "/no/such/dir"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, f"a bad root must exit 2, got {r.returncode}"


def case_not_a_git_repo_exits_2() -> None:
    root = Path(tempfile.mkdtemp())
    (root / "app.py").write_text("print('x')\n", encoding="utf-8")
    r = run(root)
    assert r.returncode == 2, f"a non-repository must exit 2, got {r.returncode}"


def case_git_missing_exits_2_not_3() -> None:
    """Exit 3 tells the caller to widen the scope. A missing git has not earned that.

    Exit 3 here would send the caller off to run every gate over the whole
    repository with the same broken git, and the report would blame the scope.
    """
    clone = build()
    empty_bin = Path(tempfile.mkdtemp())
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(clone)],
        capture_output=True,
        text=True,
        env={"PATH": str(empty_bin)},
    )
    assert r.returncode == 2, f"a missing git must exit 2, got {r.returncode}"
    assert "ERROR" in r.stderr, f"it must say what went wrong: {r.stderr!r}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


for name, fn in [
    ("a repo root that does not exist exits 2", case_bad_root_exits_2),
    ("a directory that is not a git repository exits 2", case_not_a_git_repo_exits_2),
    ("git missing from PATH exits 2, not 3", case_git_missing_exits_2_not_3),
]:
    check(name, fn)


print("\n  [shipped artifact]")


def case_real_repo_stdout_is_clean() -> None:
    """The script runs against this repository and keeps stdout a path list.

    Both 0 and 3 are correct answers, since a clone with no `origin/main` and no
    `origin/HEAD` legitimately cannot resolve a base. What must hold either way:
    no crash, and the base SHA nowhere on stdout.

    The SHA is taken from the reported base line rather than matched by shape.
    A hex-shaped pattern would fail this case on a real path that happens to read
    as hex, and would miss a leaked sha256 object name, which is longer than the
    shape a 40-character pattern looks for.
    """
    repo = Path(__file__).resolve().parents[3]
    r = run(repo)
    assert r.returncode in (0, 3), f"expected 0 or 3, got {r.returncode}: {r.stderr}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"
    if r.returncode == 3:
        return
    reported = re.search(r"^base: (\S+)", r.stderr, re.M)
    assert reported, f"a successful run must report its base: {r.stderr!r}"
    assert reported.group(1) not in r.stdout, f"the base SHA reached stdout: {r.stdout!r}"
    for line in r.stdout.splitlines():
        assert not line.startswith("base:"), f"stdout must carry no base line: {line!r}"


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__", "argparse", "re", "subprocess", "sys", "tempfile", "pathlib",
    }
    for path in (SCRIPT, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M))
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("this repository runs clean, with a path-only stdout", case_real_repo_stdout_is_clean),
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
