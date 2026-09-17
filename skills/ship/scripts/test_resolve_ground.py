#!/usr/bin/env python3
"""Regression suite for resolve_ground.py.

Stdlib only, no install, mirroring test_check_worktree_occupants.py. Run with:
    python3 skills/ship/scripts/test_resolve_ground.py

Every case builds a real git repository in a temporary directory, and the
in-progress cases start a real conflicting rebase, because the fact under test
is where git puts its state and what its commands exit with. A stubbed git would
pin this suite's idea of that rather than git's.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-vds criterion 4                            Pinned by
  ------------------------------------------------------------------------------
  A detached HEAD is named                        case_detached_head_stops
  A dirty tracked file is named                   case_dirty_tracked_stops
  An in-progress rebase is named                  case_rebase_in_progress_stops

  Design decisions in the script's docstring
  ------------------------------------------------------------------------------
  A clean repository is fit, exit 0               case_clean_branch_is_fit
  An untracked file never stops the run           case_untracked_alone_is_fit
  origin/HEAD outranks a local main               case_default_branch_from_branch_name
  A local main is used with no origin             case_default_branch_falls_back_to_local
  No default branch at all is a stop              case_no_default_branch_stops
  HEAD on the default branch is a stop            case_on_default_branch_stops
  Not a repository is a stop, not an error        case_not_a_repository_stops
  In progress outranks its own symptoms           case_in_progress_outranks_its_own_symptoms
  The worktree map names who holds what           case_worktree_map_reports_branches
  A rename is one path, not two                   case_rename_is_one_dirty_path
  outrigger puts the short id first               case_outrigger_short_id_leads
  Anchored runs rank above interior ones          case_candidates_are_anchored_then_longest_first
  A branch-type word is not a candidate           case_branch_type_word_is_dropped
  A long name keeps the id inside the cap         case_long_branch_name_keeps_the_id
  git-dir unreadable does not crash               case_git_missing_exits_2
  git missing is operator error, exit 2           case_git_missing_exits_2
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

SCRIPT = Path(__file__).resolve().parent / "resolve_ground.py"

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


def new_repo(directory: Path) -> Path:
    repo = directory / "repo"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main", "--quiet")
    configure(repo)
    write(repo, "README.md", "start\n")
    commit(repo, "initial")
    return repo


def configure(repo: Path) -> None:
    """Identity, plus isolation from whatever the developer's home directory says.

    A global `~/.gitignore` that ignores `build` made the untracked-file case
    pass against an empty list, which is the shape of a test that holds nothing.
    """
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "core.excludesFile", os.devnull)


def write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", message)


def resolve(repo: Path, environment: dict | None = None) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--directory", str(repo)],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    if result.returncode == 2:
        return result.returncode, {}
    assert result.stdout.strip(), f"no JSON on stdout: {result.stderr}"
    return result.returncode, json.loads(result.stdout)


def on_feature_branch(repo: Path, name: str = "feature") -> None:
    git(repo, "switch", "--quiet", "-c", name)


def case_clean_branch_is_fit() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo)
        code, ground = resolve(repo)
        assert code == 0, f"expected exit 0, got {code}: {ground.get('stop')}"
        assert ground["stop"] is None, ground["stop"]
        assert ground["branch"] == "feature", ground["branch"]
        assert ground["default_branch"] == "main", ground["default_branch"]
        assert ground["has_origin"] is False, ground["origin_url"]


def case_untracked_alone_is_fit() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo)
        write(repo, "artifacts/output.js", "generated\n")
        code, ground = resolve(repo)
        assert code == 0, f"an untracked file must not stop the run: {ground.get('stop')}"
        assert ground["untracked"] == ["artifacts/output.js"], ground["untracked"]
        assert ground["dirty_tracked"] == [], ground["dirty_tracked"]


def case_dirty_tracked_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo)
        write(repo, "README.md", "modified\n")
        code, ground = resolve(repo)
        assert code == 1, f"expected exit 1, got {code}"
        assert ground["stop"] == "dirty-tracked", ground["stop"]
        assert ground["dirty_tracked"] == ["README.md"], ground["dirty_tracked"]


def case_detached_head_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        head = git(repo, "rev-parse", "HEAD").stdout.strip()
        git(repo, "checkout", "--quiet", "--detach", head)
        code, ground = resolve(repo)
        assert code == 1, f"expected exit 1, got {code}"
        assert ground["stop"] == "detached-head", ground["stop"]
        assert ground["branch"] is None, ground["branch"]


def case_on_default_branch_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        code, ground = resolve(repo)
        assert code == 1, f"expected exit 1, got {code}"
        assert ground["stop"] == "on-default-branch", ground["stop"]


def case_rebase_in_progress_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        write(repo, "shared.txt", "main side\n")
        commit(repo, "main edits shared")
        git(repo, "switch", "--quiet", "-c", "feature", "HEAD~1")
        write(repo, "shared.txt", "branch side\n")
        commit(repo, "branch edits shared")
        git(repo, "rebase", "main", check_exit=False)  # conflicts on purpose
        code, ground = resolve(repo)
        git(repo, "rebase", "--abort", check_exit=False)
        assert code == 1, f"expected exit 1, got {code}"
        assert ground["stop"] == "operation-in-progress", ground["stop"]
        assert ground["in_progress"] in {"rebase-merge", "rebase-apply"}, ground["in_progress"]


def case_in_progress_outranks_its_own_symptoms() -> None:
    """Three true conditions, one named. A conflicted rebase detaches HEAD and
    leaves the conflicted file modified, so naming either sends the operator to a
    symptom rather than to `git rebase --abort`."""
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        write(repo, "shared.txt", "main side\n")
        commit(repo, "main edits shared")
        git(repo, "switch", "--quiet", "-c", "feature", "HEAD~1")
        write(repo, "shared.txt", "branch side\n")
        commit(repo, "branch edits shared")
        git(repo, "rebase", "main", check_exit=False)
        code, ground = resolve(repo)
        git(repo, "rebase", "--abort", check_exit=False)
        assert code == 1, f"expected exit 1, got {code}"
        assert ground["stop"] == "operation-in-progress", f"order changed: {ground['stop']}"
        assert ground["branch"] is None, "a conflicted rebase detaches HEAD"
        assert ground["dirty_tracked"], "a conflicted rebase leaves the file modified"


def case_not_a_repository_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        outside = Path(directory) / "plain"
        outside.mkdir()
        code, ground = resolve(outside)
        assert code == 1, f"expected exit 1, got {code}"
        assert ground["stop"] == "no-repository", ground["stop"]


def case_default_branch_falls_back_to_local() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo)
        _, ground = resolve(repo)
        assert ground["default_branch"] == "main", ground["default_branch"]
        assert ground["default_branch_source"] == "local main", ground["default_branch_source"]


def case_default_branch_from_branch_name() -> None:
    """origin/HEAD wins even when a local main exists and names something else."""
    with tempfile.TemporaryDirectory() as directory:
        upstream = new_repo(Path(directory))
        git(upstream, "switch", "--quiet", "-c", "trunk")
        clone = Path(directory) / "clone"
        subprocess.run(
            ["git", "clone", "--quiet", str(upstream), str(clone)],
            capture_output=True, text=True, check=True,
        )
        configure(clone)
        git(clone, "branch", "main", "HEAD")
        on_feature_branch(clone)
        _, ground = resolve(clone)
        assert ground["default_branch"] == "trunk", ground["default_branch"]
        assert ground["default_branch_source"] == "origin/HEAD", ground["default_branch_source"]
        assert ground["has_origin"] is True, ground["origin_url"]


def case_no_default_branch_stops() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory) / "repo"
        repo.mkdir()
        git(repo, "init", "--initial-branch=trunk", "--quiet")
        configure(repo)
        write(repo, "README.md", "start\n")
        commit(repo, "initial")
        on_feature_branch(repo)
        code, ground = resolve(repo)
        assert code == 1, f"expected exit 1, got {code}"
        assert ground["stop"] == "no-default-branch", ground["stop"]


def case_worktree_map_reports_branches() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo)
        elsewhere = Path(directory) / "held"
        git(repo, "worktree", "add", "--quiet", str(elsewhere), "main")
        _, ground = resolve(repo)
        holders = {w["branch"]: w["path"] for w in ground["worktrees"]}
        assert Path(holders["feature"]).resolve() == repo.resolve(), holders
        assert Path(holders["main"]).name == "held", holders
        assert Path(ground["default_branch_worktree"]).name == "held", ground


def case_rename_is_one_dirty_path() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo)
        git(repo, "mv", "README.md", "READINGS.md")
        _, ground = resolve(repo)
        assert ground["dirty_tracked"] == ["READINGS.md"], ground["dirty_tracked"]


def case_outrigger_short_id_leads() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo, "outrigger/4kx/create-ship-command")
        _, ground = resolve(repo)
        candidates = ground["bead_candidates"]
        assert candidates[0] == "4kx", candidates
        assert "create-ship-command" in candidates, candidates


def case_candidates_are_anchored_then_longest_first() -> None:
    """Anchored runs first as a group, longest first inside it, interior after.

    `0fo-exclude` touches neither end of `tadw-0fo-exclude-beads`, so it ranks
    below every prefix and suffix however long it is. No tracker id is an
    interior run, and ranking by length alone is what pushed the real id past
    the cap on a longer name.
    """
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo, "fix/tadw-0fo-exclude-beads")
        _, ground = resolve(repo)
        candidates = ground["bead_candidates"]
        assert "tadw-0fo" in candidates, candidates
        anchored = ["tadw-0fo-exclude-beads", "tadw-0fo-exclude", "tadw-0fo", "tadw",
                    "0fo-exclude-beads", "exclude-beads", "beads"]
        interior = ["0fo-exclude", "exclude", "0fo"]
        assert candidates[: len(anchored)] == sorted(anchored, key=lambda r: (-len(r), r)), candidates
        assert candidates[len(anchored) :] == sorted(interior, key=lambda r: (-len(r), r)), candidates


def case_branch_type_word_is_dropped() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo, "chore/simplify-ship")
        _, ground = resolve(repo)
        assert "chore" not in ground["bead_candidates"], ground["bead_candidates"]
        assert "simplify-ship" in ground["bead_candidates"], ground["bead_candidates"]


def case_long_branch_name_keeps_the_id() -> None:
    """The cap must drop interior runs, never an anchored one.

    Ranked by length alone, `tadw-0fo` sits below thirty longer interior runs
    like `exclude-the-beads-directory` and falls off the end of a 25-item list.
    The lookup then finds no bead and the ship goes bead-free, leaving it open.
    """
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        on_feature_branch(repo, "fix/tadw-0fo-exclude-the-beads-directory-from-the-check")
        _, ground = resolve(repo)
        candidates = ground["bead_candidates"]
        assert "tadw-0fo" in candidates, f"the id fell off the end: {candidates}"
        assert "check" in candidates, f"the trailing token fell off the end: {candidates}"
        assert "beads-directory" not in candidates, f"an interior run survived: {candidates}"


def case_git_missing_exits_2() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = new_repo(Path(directory))
        empty_path = Path(directory) / "empty-bin"
        empty_path.mkdir()
        environment = dict(os.environ, PATH=str(empty_path))
        code, _ = resolve(repo, environment=environment)
        assert code == 2, f"expected operator error 2, got {code}"


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
    ("a clean feature branch is fit to ship from", case_clean_branch_is_fit),
    ("an untracked file alone does not stop the run", case_untracked_alone_is_fit),
    ("a changed tracked file stops the run", case_dirty_tracked_stops),
    ("a detached HEAD stops the run", case_detached_head_stops),
    ("HEAD on the default branch stops the run", case_on_default_branch_stops),
    ("a rebase already in progress stops the run", case_rebase_in_progress_stops),
    ("the rebase is named before its own symptoms", case_in_progress_outranks_its_own_symptoms),
    ("a directory that is not a repository stops the run", case_not_a_repository_stops),
    ("a local main is the default with no origin", case_default_branch_falls_back_to_local),
    ("origin/HEAD outranks a local main", case_default_branch_from_branch_name),
    ("no origin/HEAD, main, or master stops the run", case_no_default_branch_stops),
    ("the worktree map names who holds each branch", case_worktree_map_reports_branches),
    ("a rename reports one path, not two", case_rename_is_one_dirty_path),
    ("an outrigger branch puts the short id first", case_outrigger_short_id_leads),
    ("anchored runs rank above interior ones", case_candidates_are_anchored_then_longest_first),
    ("a branch-type word is not a bead candidate", case_branch_type_word_is_dropped),
    ("a long branch name keeps the id inside the cap", case_long_branch_name_keeps_the_id),
    ("git missing from PATH exits 2", case_git_missing_exits_2),
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
