#!/usr/bin/env python3
"""Regression suite for resolve_rebase_conflict.py.

Stdlib only, no install, mirroring test_check_worktree_occupants.py. Run with:
    python3 skills/ship/scripts/test_resolve_rebase_conflict.py

Every conflict here is produced by a real `git rebase` that really conflicts, so
the markers under test are git's own rather than a fixture's idea of them. The
tracker cases put a stub `bd` first on PATH instead of a real beads database: the
contract being tested is that the script runs `bd export -o .beads/issues.jsonl`
and then refuses whatever comes back unless it is marker-free JSON, and a stub
can fail in the exact ways a real export fails.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-vds criterion 3                            Pinned by
  ------------------------------------------------------------------------------
  One foreign path resolves nothing at all        case_source_conflict_resolves_nothing,
                                                  case_one_foreign_path_spares_the_changelog

  Design decisions in the script's docstring
  ------------------------------------------------------------------------------
  An empty conflicted set is exit 0               case_no_conflict_is_exit_zero
  Both changelog sides survive, ours first        case_changelog_keeps_both_sides
  Every hunk in the file, not just the first      case_changelog_resolves_two_hunks
  A diff3 base section is dropped                 case_diff3_base_section_is_dropped
  The export is regenerated, not chosen           case_tracker_export_is_regenerated
  A failed export stops with `tracker`            case_failed_export_stops_with_tracker
  A missing bd stops with `tracker`               case_missing_bd_stops_with_tracker
  An export that is not JSON stops                case_invalid_json_export_stops
  Markers surviving the export stop               case_markered_export_stops
  Both paths at once are both resolved            case_both_paths_resolve_together
  An unterminated hunk loses no content           case_unterminated_hunk_stops
  Markers are counted, never grepped              case_changelog_keeps_both_sides
  Operator error is 2, never 1                    case_missing_repo_exits_2
  Stdlib only                                     case_no_third_party_imports
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "resolve_rebase_conflict.py"

BASE_CHANGELOG = "# Changelog\n\n## 1.0.0\n\n- the first release\n"
MAIN_CHANGELOG = "# Changelog\n\n## 1.2.0\n\n- MAIN ENTRY\n\n## 1.0.0\n\n- the first release\n"
BRANCH_CHANGELOG = "# Changelog\n\n## 1.1.0\n\n- BRANCH ENTRY\n\n## 1.0.0\n\n- the first release\n"

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


def git(repo: Path, *arguments: str, check_exit: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
        check=check_exit,
    )


def write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read(repo: Path, relative: str) -> str:
    return (repo / relative).read_text(encoding="utf-8")


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", message)


def conflicting_repo(
    directory: Path,
    sides: dict[str, tuple[str, str, str]],
    conflict_style: str = "merge",
) -> Path:
    """A repository stopped mid-rebase, conflicted on every file in `sides`.

    Each value is (base, main's version, the branch's version). The rebase
    replays the branch onto main, so main's version is the `<<<<<<<` side.
    """
    repo = directory / "repo"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main", "--quiet")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "core.excludesFile", os.devnull)
    git(repo, "config", "merge.conflictStyle", conflict_style)

    for relative, (base, _, _) in sides.items():
        write(repo, relative, base)
    commit(repo, "base")

    for relative, (_, main_side, _) in sides.items():
        write(repo, relative, main_side)
    commit(repo, "main edits")

    git(repo, "switch", "--quiet", "-c", "feature", "HEAD~1")
    for relative, (_, _, branch_side) in sides.items():
        write(repo, relative, branch_side)
    commit(repo, "branch edits")

    rebase = git(repo, "rebase", "main", check_exit=False)
    assert rebase.returncode != 0, "the fixture was supposed to conflict"
    return repo


def stub_bd(directory: Path, body: str) -> dict:
    """An environment whose PATH finds a `bd` that does exactly what `body` says."""
    bin_directory = directory / "stub-bin"
    bin_directory.mkdir(exist_ok=True)
    script = bin_directory / "bd"
    script.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    script.chmod(0o755)
    return dict(os.environ, PATH=f"{bin_directory}{os.pathsep}{os.environ['PATH']}")


def resolve(repo: Path, environment: dict | None = None) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo)],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    if result.returncode == 2:
        return result.returncode, {}
    assert result.stdout.strip(), f"no JSON on stdout: {result.stderr}"
    return result.returncode, json.loads(result.stdout)


def staged_paths(repo: Path) -> set[str]:
    stdout = git(repo, "diff", "--name-only", "--cached").stdout
    return {line for line in stdout.splitlines() if line}


def unmerged_paths(repo: Path) -> set[str]:
    stdout = git(repo, "diff", "--name-only", "--diff-filter=U").stdout
    return {line for line in stdout.splitlines() if line}


def case_no_conflict_is_exit_zero() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory) / "repo"
        repo.mkdir()
        git(repo, "init", "--initial-branch=main", "--quiet")
        git(repo, "config", "user.email", "test@example.invalid")
        git(repo, "config", "user.name", "Test")
        write(repo, "README.md", "start\n")
        commit(repo, "initial")
        code, outcome = resolve(repo)
        assert code == 0, f"expected exit 0, got {code}: {outcome}"
        assert outcome["stop"] is None, outcome
        assert outcome["resolved"] == [], outcome


def case_changelog_keeps_both_sides() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(
            Path(directory),
            {"CHANGELOG.md": (BASE_CHANGELOG, MAIN_CHANGELOG, BRANCH_CHANGELOG)},
        )
        code, outcome = resolve(repo)
        assert code == 0, f"expected exit 0, got {code}: {outcome}"
        assert outcome["resolved"] == ["CHANGELOG.md"], outcome
        merged = read(repo, "CHANGELOG.md")
        assert "MAIN ENTRY" in merged, merged
        assert "BRANCH ENTRY" in merged, merged
        assert merged.index("MAIN ENTRY") < merged.index("BRANCH ENTRY"), merged
        assert "<<<<<<<" not in merged and ">>>>>>>" not in merged, merged
        assert "=======" not in merged, merged
        assert staged_paths(repo) >= {"CHANGELOG.md"}, staged_paths(repo)
        assert unmerged_paths(repo) == set(), unmerged_paths(repo)


def case_changelog_resolves_two_hunks() -> None:
    """A file can conflict in more than one place; the first hunk is not the file."""
    base = "# Changelog\n\n## top\n\n- base top\n\n## bottom\n\n- base bottom\n"
    main_side = "# Changelog\n\n## top\n\n- MAIN TOP\n\n## bottom\n\n- MAIN BOTTOM\n"
    branch_side = "# Changelog\n\n## top\n\n- BRANCH TOP\n\n## bottom\n\n- BRANCH BOTTOM\n"
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(Path(directory), {"CHANGELOG.md": (base, main_side, branch_side)})
        code, outcome = resolve(repo)
        assert code == 0, f"expected exit 0, got {code}: {outcome}"
        merged = read(repo, "CHANGELOG.md")
        for entry in ("MAIN TOP", "BRANCH TOP", "MAIN BOTTOM", "BRANCH BOTTOM"):
            assert entry in merged, f"{entry} missing from:\n{merged}"
        assert "<<<<<<<" not in merged, merged


def case_diff3_base_section_is_dropped() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(
            Path(directory),
            {"CHANGELOG.md": (BASE_CHANGELOG, MAIN_CHANGELOG, BRANCH_CHANGELOG)},
            conflict_style="diff3",
        )
        raw = read(repo, "CHANGELOG.md")
        assert "|||||||" in raw, f"the fixture did not produce a diff3 hunk:\n{raw}"
        code, outcome = resolve(repo)
        assert code == 0, f"expected exit 0, got {code}: {outcome}"
        merged = read(repo, "CHANGELOG.md")
        assert "MAIN ENTRY" in merged and "BRANCH ENTRY" in merged, merged
        assert "|||||||" not in merged, merged


def case_source_conflict_resolves_nothing() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(
            Path(directory),
            {"src/app.py": ("base\n", "main\n", "branch\n")},
        )
        code, outcome = resolve(repo)
        assert code == 1, f"expected exit 1, got {code}: {outcome}"
        assert outcome["stop"] == "conflict", outcome
        assert "src/app.py" in outcome["detail"], outcome["detail"]
        assert outcome["resolved"] == [], outcome
        assert unmerged_paths(repo) == {"src/app.py"}, unmerged_paths(repo)


def case_one_foreign_path_spares_the_changelog() -> None:
    """The refusal is the whole set, so a resolvable path is left conflicted too."""
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(
            Path(directory),
            {
                "CHANGELOG.md": (BASE_CHANGELOG, MAIN_CHANGELOG, BRANCH_CHANGELOG),
                "src/app.py": ("base\n", "main\n", "branch\n"),
            },
        )
        code, outcome = resolve(repo)
        assert code == 1, f"expected exit 1, got {code}: {outcome}"
        assert outcome["stop"] == "conflict", outcome
        assert outcome["resolved"] == [], outcome
        assert "<<<<<<<" in read(repo, "CHANGELOG.md"), "the changelog was touched anyway"
        assert unmerged_paths(repo) == {"CHANGELOG.md", "src/app.py"}, unmerged_paths(repo)


def case_unterminated_hunk_stops() -> None:
    """A hunk with no `>>>>>>>` must stop, never write.

    Its lines are held aside until the closing marker, so an unterminated hunk
    contributes nothing to the output and its `<<<<<<<` was already consumed.
    One closed hunk earlier in the file gets past the `hunks == 0` test, and the
    caller then writes a changelog that silently lost both sides of the second.
    """
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(
            Path(directory),
            {"CHANGELOG.md": (BASE_CHANGELOG, MAIN_CHANGELOG, BRANCH_CHANGELOG)},
        )
        conflicted = read(repo, "CHANGELOG.md")
        write(repo, "CHANGELOG.md", conflicted + "<<<<<<< HEAD\n- SECOND HUNK\n")
        code, outcome = resolve(repo)
        assert code == 1, f"expected exit 1, got {code}: {outcome}"
        assert outcome["stop"] == "conflict", outcome
        assert "no closing marker" in outcome["detail"], outcome["detail"]
        assert "SECOND HUNK" in read(repo, "CHANGELOG.md"), "content was written away"


def tracker_sides() -> dict[str, tuple[str, str, str]]:
    return {
        ".beads/issues.jsonl": (
            '{"id":"base"}\n',
            '{"id":"main"}\n',
            '{"id":"branch"}\n',
        )
    }


def case_tracker_export_is_regenerated() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(Path(directory), tracker_sides())
        environment = stub_bd(Path(directory), 'printf \'{"id":"from-the-database"}\\n\' > "$3"\n')
        code, outcome = resolve(repo, environment)
        assert code == 0, f"expected exit 0, got {code}: {outcome}"
        assert outcome["resolved"] == [".beads/issues.jsonl"], outcome
        exported = read(repo, ".beads/issues.jsonl")
        assert exported.strip() == '{"id":"from-the-database"}', exported
        assert "main" not in exported and "branch" not in exported, exported
        assert staged_paths(repo) >= {".beads/issues.jsonl"}, staged_paths(repo)
        assert unmerged_paths(repo) == set(), unmerged_paths(repo)


def case_failed_export_stops_with_tracker() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(Path(directory), tracker_sides())
        environment = stub_bd(Path(directory), 'echo "database is locked" >&2\nexit 1\n')
        code, outcome = resolve(repo, environment)
        assert code == 1, f"expected exit 1, got {code}: {outcome}"
        assert outcome["stop"] == "tracker", outcome
        assert "database is locked" in outcome["detail"], outcome["detail"]


def case_missing_bd_stops_with_tracker() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(Path(directory), tracker_sides())
        empty = Path(directory) / "empty-bin"
        empty.mkdir()
        git_directory = subprocess.run(
            ["sh", "-c", "command -v git"], capture_output=True, text=True, check=True,
        ).stdout.strip()
        (empty / "git").symlink_to(git_directory)
        environment = dict(os.environ, PATH=str(empty))
        code, outcome = resolve(repo, environment)
        assert code == 1, f"expected exit 1, got {code}: {outcome}"
        assert outcome["stop"] == "tracker", outcome
        assert "bd is not on PATH" in outcome["detail"], outcome["detail"]


def case_invalid_json_export_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(Path(directory), tracker_sides())
        environment = stub_bd(Path(directory), 'printf \'{"id":"tru\\n\' > "$3"\n')
        code, outcome = resolve(repo, environment)
        assert code == 1, f"expected exit 1, got {code}: {outcome}"
        assert outcome["stop"] == "tracker", outcome
        assert "is not JSON" in outcome["detail"], outcome["detail"]


def case_markered_export_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = conflicting_repo(Path(directory), tracker_sides())
        environment = stub_bd(Path(directory), 'printf \'<<<<<<< HEAD\\n\' > "$3"\n')
        code, outcome = resolve(repo, environment)
        assert code == 1, f"expected exit 1, got {code}: {outcome}"
        assert outcome["stop"] == "tracker", outcome
        assert "markers survived" in outcome["detail"], outcome["detail"]


def case_both_paths_resolve_together() -> None:
    with tempfile.TemporaryDirectory() as directory:
        sides = dict(tracker_sides())
        sides["CHANGELOG.md"] = (BASE_CHANGELOG, MAIN_CHANGELOG, BRANCH_CHANGELOG)
        repo = conflicting_repo(Path(directory), sides)
        environment = stub_bd(Path(directory), 'printf \'{"id":"fresh"}\\n\' > "$3"\n')
        code, outcome = resolve(repo, environment)
        assert code == 0, f"expected exit 0, got {code}: {outcome}"
        assert set(outcome["resolved"]) == {".beads/issues.jsonl", "CHANGELOG.md"}, outcome
        assert unmerged_paths(repo) == set(), unmerged_paths(repo)


def case_missing_repo_exits_2() -> None:
    with tempfile.TemporaryDirectory() as directory:
        outside = Path(directory) / "plain"
        outside.mkdir()
        code, _ = resolve(outside)
        assert code == 2, f"expected exit 2, got {code}"


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__", "argparse", "json", "os", "re", "subprocess", "sys",
        "tempfile", "pathlib",
    }
    for path in (SCRIPT, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M))
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("an empty conflicted set exits 0", case_no_conflict_is_exit_zero),
    ("the changelog keeps both sides, main's first", case_changelog_keeps_both_sides),
    ("every changelog hunk is resolved, not just the first", case_changelog_resolves_two_hunks),
    ("a diff3 base section is dropped", case_diff3_base_section_is_dropped),
    ("a source conflict resolves nothing", case_source_conflict_resolves_nothing),
    ("one foreign path leaves the changelog conflicted", case_one_foreign_path_spares_the_changelog),
    ("the tracker export is regenerated, not chosen", case_tracker_export_is_regenerated),
    ("a failed bd export stops with tracker", case_failed_export_stops_with_tracker),
    ("a missing bd stops with tracker", case_missing_bd_stops_with_tracker),
    ("an export that is not JSON stops with tracker", case_invalid_json_export_stops),
    ("markers surviving the export stop with tracker", case_markered_export_stops),
    ("both resolvable paths resolve in one run", case_both_paths_resolve_together),
    ("an unterminated hunk stops and writes nothing", case_unterminated_hunk_stops),
    ("a directory that is not a repository exits 2", case_missing_repo_exits_2),
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
