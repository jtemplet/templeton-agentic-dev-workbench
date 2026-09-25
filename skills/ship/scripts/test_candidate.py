#!/usr/bin/env python3
"""Regression suite for candidate.py, which builds and checks the commit ship lands.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_candidate.py

Every case uses real git repositories in a temporary directory: a bare origin, a
checkout holding `main`, and a linked worktree holding the feature branch.

  tadw-9ed criterion                                   Pinned by
  ------------------------------------------------------------------------------
  1. A failing gate leaves the default branch          case_failing_gate_leaves_main_unchanged
     unchanged
  2. Local default-branch commits appear in the        case_local_commits_are_in_the_checked_tree,
     checked tree and the report                       case_local_commits_are_reported
  3. A gate that changes a tracked file, or the        case_gate_changing_a_tracked_file_is_rejected,
     tracker export, rejects the candidate before      case_export_drift_is_rejected,
     the fast-forward; untracked gate output does      case_untracked_gate_output_does_not_reject_the_candidate
     not
  4. A source conflict or dirty worktree stops         case_conflict_stops_and_keeps_work,
     without deleting unrelated work                   case_dirty_feature_checkout_stops
  5. bd export writes the export and the commit        case_export_rides_the_candidate_commit,
     carries it; a bead-free ship writes none          case_bead_free_landing_writes_no_export
  6. Cleanup leaves a default-branch worktree with     case_dirty_default_checkout_is_left_alone,
     unrelated work unchanged                          case_cleanup_removes_only_the_temporary_worktree
  7. A later local commit is named unpushed and        case_later_commit_is_reported_unpushed
     unchecked
  8. The interactions log stays untracked, and         case_audit_log_stays_untracked,
     lines bd wrote in the temporary worktree are      case_audit_lines_written_in_the_temporary_worktree_are_kept,
                                                       case_appended_audit_lines_never_join_an_unterminated_line
     kept, each on its own line

  tadw-lndi criterion                                  Pinned by
  ------------------------------------------------------------------------------
  1. A default checkout whose only changed tracked     case_export_only_dirty_default_checkout_lands
     file is the export takes the landing
  2. Any other changed tracked file stops it           case_export_and_another_change_stop_the_landing,
                                                       case_dirty_default_checkout_is_left_alone
  3. A restored export is reported                     case_restored_export_is_reported,
                                                       case_clean_landing_reports_no_restore

  The same three run end to end through bin/tadw-ship in test_tadw_ship.py.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("candidate", SCRIPTS / "candidate.py")
candidate = importlib.util.module_from_spec(spec)
sys.modules["candidate"] = candidate
spec.loader.exec_module(candidate)

ENVIRONMENT = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}
USE_FAKE_EXPORT = object()
TRACKER_EXPORT = '{"id":"tadw-x"}\n'

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


def git(directory: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        capture_output=True,
        text=True,
        check=True,
        env=ENVIRONMENT,
    )
    return completed.stdout.strip()


class Fixture:
    """A bare origin, the `main` checkout, and a feature worktree with one commit on it."""

    def __init__(self, root: Path) -> None:
        self.origin = root / "origin.git"
        self.main = root / "main"
        self.feature = root / "feature"
        subprocess.run(
            ["git", "init", "--bare", "-b", "main", str(self.origin)],
            check=True,
            capture_output=True,
            env=ENVIRONMENT,
        )
        subprocess.run(
            ["git", "clone", str(self.origin), str(self.main)],
            check=True,
            capture_output=True,
            env=ENVIRONMENT,
        )
        git(self.main, "checkout", "-b", "main")
        self.commit_on_main("base.txt", "base\n", "base")
        git(self.main, "push", "-u", "origin", "main")
        git(self.main, "worktree", "add", "-b", "feature", str(self.feature))
        self.commit_on_feature("feature.txt", "feature\n", "feature work")

    def commit_on_main(self, name: str, text: str, message: str) -> None:
        commit(self.main, name, text, message)

    def commit_on_feature(self, name: str, text: str, message: str) -> None:
        commit(self.feature, name, text, message)

    def main_tip(self) -> str:
        return git(self.main, "rev-parse", "main")

    def land(self, gate=None, export=USE_FAKE_EXPORT):
        return candidate.land_candidate(
            self.feature,
            candidate.Plan("feature", "main", "feat: land"),
            gate or passing_gate,
            write_export if export is USE_FAKE_EXPORT else export,
        )


def commit(directory: Path, name: str, text: str, message: str) -> None:
    (directory / name).write_text(text, encoding="utf-8")
    git(directory, "add", name)
    git(directory, "commit", "--quiet", "-m", message)


def passing_gate(worktree: Path) -> bool:
    return True


def failing_gate(worktree: Path) -> bool:
    return False


def write_export(worktree: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(TRACKER_EXPORT, encoding="utf-8")
    return True


def stopped(fixture: Fixture, **kwargs) -> candidate.CandidateStop:
    try:
        fixture.land(**kwargs)
    except candidate.CandidateStop as stop:
        return stop
    raise AssertionError("the landing did not stop")


def with_fixture(test) -> None:
    with tempfile.TemporaryDirectory() as directory:
        test(Fixture(Path(directory)))


def case_failing_gate_leaves_main_unchanged() -> None:
    def test(fixture: Fixture) -> None:
        before, feature_tip = fixture.main_tip(), git(fixture.feature, "rev-parse", "feature")
        stop = stopped(fixture, gate=failing_gate)
        assert stop.reason == "gate", stop
        assert fixture.main_tip() == before, "main moved after a failing gate"
        assert git(fixture.feature, "rev-parse", "feature") == feature_tip

    with_fixture(test)


def case_local_commits_are_in_the_checked_tree() -> None:
    def test(fixture: Fixture) -> None:
        fixture.commit_on_main("local.txt", "local\n", "local only")
        seen: list[bool] = []

        def gate(worktree: Path) -> bool:
            seen.append((worktree / "local.txt").is_file() and (worktree / "feature.txt").is_file())
            return True

        fixture.land(gate=gate)
        assert seen == [True], "the gate did not run on a tree holding the local commit"

    with_fixture(test)


def case_local_commits_are_reported() -> None:
    def test(fixture: Fixture) -> None:
        fixture.commit_on_main("local.txt", "local\n", "local only")
        local = fixture.main_tip()
        landing = fixture.land()
        assert landing.local_commits == (local,), landing
        assert any(local[:12] in line for line in landing.report_lines()), landing.report_lines()

    with_fixture(test)


def case_gate_changing_a_tracked_file_is_rejected() -> None:
    def test(fixture: Fixture) -> None:
        before = fixture.main_tip()

        def gate(worktree: Path) -> bool:
            (worktree / "base.txt").write_text("changed by the gate\n", encoding="utf-8")
            return True

        assert stopped(fixture, gate=gate).reason == "dirty-tracked"
        assert fixture.main_tip() == before

    with_fixture(test)


def case_export_drift_is_rejected() -> None:
    def test(fixture: Fixture) -> None:
        before, calls = fixture.main_tip(), []

        def export(worktree: Path, target: Path) -> bool:
            calls.append(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(TRACKER_EXPORT * len(calls), encoding="utf-8")
            return True

        assert stopped(fixture, export=export).reason == "export-drift"
        assert fixture.main_tip() == before

    with_fixture(test)


def case_conflict_stops_and_keeps_work() -> None:
    def test(fixture: Fixture) -> None:
        fixture.commit_on_main("feature.txt", "main wrote this first\n", "conflicting")
        (fixture.main / "notes.txt").write_text("unrelated, untracked\n", encoding="utf-8")
        before = fixture.main_tip()
        assert stopped(fixture).reason == "conflict"
        assert fixture.main_tip() == before
        assert (fixture.main / "notes.txt").read_text(encoding="utf-8") == "unrelated, untracked\n"

    with_fixture(test)


def case_dirty_feature_checkout_stops() -> None:
    def test(fixture: Fixture) -> None:
        (fixture.feature / "feature.txt").write_text("edited\n", encoding="utf-8")
        before = fixture.main_tip()
        assert stopped(fixture).reason == "dirty-tracked"
        assert fixture.main_tip() == before
        assert (fixture.feature / "feature.txt").read_text(encoding="utf-8") == "edited\n"

    with_fixture(test)


def case_export_rides_the_candidate_commit() -> None:
    def test(fixture: Fixture) -> None:
        landing = fixture.land()
        carried = git(fixture.main, "show", f"{landing.commit}:{candidate.EXPORT_PATH}")
        assert carried == TRACKER_EXPORT.strip(), carried
        assert git(fixture.main, "rev-parse", "main") == landing.commit

    with_fixture(test)


def case_dirty_default_checkout_is_left_alone() -> None:
    def test(fixture: Fixture) -> None:
        (fixture.main / "base.txt").write_text("unrelated edit\n", encoding="utf-8")
        before = fixture.main_tip()
        assert stopped(fixture).reason == "default-checkout-dirty"
        assert fixture.main_tip() == before
        assert (fixture.main / "base.txt").read_text(encoding="utf-8") == "unrelated edit\n"

    with_fixture(test)


def track_stale_export(fixture: Fixture) -> Path:
    """Commit an export on main, then rewrite it in the main checkout, as `bd` auto-export does."""
    (fixture.main / ".beads").mkdir()
    fixture.commit_on_main(candidate.EXPORT_PATH, '{"id":"old"}\n', "chore: export")
    stale = fixture.main / candidate.EXPORT_PATH
    stale.write_text('{"id":"rewritten by bd"}\n', encoding="utf-8")
    return stale


def case_export_only_dirty_default_checkout_lands() -> None:
    def test(fixture: Fixture) -> None:
        exported = track_stale_export(fixture)
        landing = fixture.land()
        assert fixture.main_tip() == landing.commit, "main did not move"
        assert exported.read_text(encoding="utf-8") == TRACKER_EXPORT, "main holds a stale export"
        assert git(fixture.main, "status", "--porcelain", "--untracked-files=no") == ""
        assert landing.restored_export_in == fixture.main.resolve(), landing

    with_fixture(test)


def case_staged_export_in_default_checkout_lands() -> None:
    def test(fixture: Fixture) -> None:
        exported = track_stale_export(fixture)
        git(fixture.main, "add", candidate.EXPORT_PATH)
        landing = fixture.land()
        assert fixture.main_tip() == landing.commit, "main did not move"
        assert exported.read_text(encoding="utf-8") == TRACKER_EXPORT, "main holds a stale export"
        assert git(fixture.main, "status", "--porcelain", "--untracked-files=no") == ""

    with_fixture(test)


def case_export_and_another_change_stop_the_landing() -> None:
    def test(fixture: Fixture) -> None:
        exported = track_stale_export(fixture)
        (fixture.main / "base.txt").write_text("unrelated edit\n", encoding="utf-8")
        before = fixture.main_tip()
        assert stopped(fixture).reason == "default-checkout-dirty"
        assert fixture.main_tip() == before
        assert exported.read_text(encoding="utf-8") == '{"id":"rewritten by bd"}\n', "restored"
        assert (fixture.main / "base.txt").read_text(encoding="utf-8") == "unrelated edit\n"

    with_fixture(test)


def case_restored_export_is_reported() -> None:
    def test(fixture: Fixture) -> None:
        track_stale_export(fixture)
        lines = fixture.land().report_lines()
        restored = [line for line in lines if f"restored {candidate.EXPORT_PATH}" in line]
        assert len(restored) == 1 and str(fixture.main.resolve()) in restored[0], lines

    with_fixture(test)


def case_clean_landing_reports_no_restore() -> None:
    def test(fixture: Fixture) -> None:
        landing = fixture.land()
        assert landing.restored_export_in is None, landing
        assert not any("restored" in line for line in landing.report_lines())

    with_fixture(test)


def case_cleanup_removes_only_the_temporary_worktree() -> None:
    def test(fixture: Fixture) -> None:
        fixture.land()
        listed = git(fixture.main, "worktree", "list", "--porcelain")
        assert candidate.WORKTREE_PREFIX not in listed, listed
        assert str(fixture.feature) in listed, "the feature worktree was removed"
        assert (fixture.feature / "feature.txt").is_file()

    with_fixture(test)


def case_later_commit_is_reported_unpushed() -> None:
    def test(fixture: Fixture) -> None:
        landing = fixture.land()
        fixture.commit_on_main("hook.txt", "made by pre-push\n", "chore: export")
        later = candidate.later_local_commits(fixture.main, "main", landing.commit)
        assert later == [fixture.main_tip()], later
        lines = candidate.unpushed_report_lines(later)
        assert len(lines) == 1 and "unpushed" in lines[0] and "did not check" in lines[0], lines
        assert candidate.later_local_commits(fixture.main, "main", fixture.main_tip()) == []

    with_fixture(test)


def case_audit_log_stays_untracked() -> None:
    def test(fixture: Fixture) -> None:
        def export(worktree: Path, target: Path) -> bool:
            write_export(worktree, target)
            (worktree / candidate.AUDIT_LOG_PATH).write_text("{}\n", encoding="utf-8")
            return True

        landing = fixture.land(export=export)
        tracked = git(fixture.main, "ls-tree", "-r", "--name-only", landing.commit)
        assert candidate.AUDIT_LOG_PATH not in tracked.splitlines(), tracked

    with_fixture(test)


def case_bead_free_landing_writes_no_export() -> None:
    def test(fixture: Fixture) -> None:
        landing = fixture.land(export=None)
        tracked = git(fixture.main, "ls-tree", "-r", "--name-only", landing.commit)
        assert candidate.EXPORT_PATH not in tracked.splitlines(), tracked
        assert fixture.main_tip() == landing.commit

    with_fixture(test)


def case_audit_lines_written_in_the_temporary_worktree_are_kept() -> None:
    def test(fixture: Fixture) -> None:
        def export(worktree: Path, target: Path) -> bool:
            write_export(worktree, target)
            (worktree / candidate.AUDIT_LOG_PATH).write_text('{"event":"x"}\n', encoding="utf-8")
            return True

        landing = fixture.land(export=export)
        kept = (fixture.feature / candidate.AUDIT_LOG_PATH).read_text(encoding="utf-8")
        assert kept == '{"event":"x"}\n', kept
        tracked = git(fixture.main, "ls-tree", "-r", "--name-only", landing.commit)
        assert candidate.AUDIT_LOG_PATH not in tracked.splitlines(), tracked

    with_fixture(test)


def case_appended_audit_lines_never_join_an_unterminated_line() -> None:
    def test(fixture: Fixture) -> None:
        kept = fixture.feature / candidate.AUDIT_LOG_PATH
        kept.parent.mkdir(exist_ok=True)
        kept.write_text('{"event":"old"}', encoding="utf-8")

        def export(worktree: Path, target: Path) -> bool:
            write_export(worktree, target)
            (worktree / candidate.AUDIT_LOG_PATH).write_text('{"event":"new"}\n', encoding="utf-8")
            return True

        fixture.land(export=export)
        lines = kept.read_text(encoding="utf-8").splitlines()
        assert lines == ['{"event":"old"}', '{"event":"new"}'], lines

    with_fixture(test)


def case_untracked_gate_output_does_not_reject_the_candidate() -> None:
    def test(fixture: Fixture) -> None:
        def gate(worktree: Path) -> bool:
            (worktree / "build-output.log").write_text("noise\n", encoding="utf-8")
            return True

        landing = fixture.land(gate=gate)
        assert fixture.main_tip() == landing.commit
        assert candidate.WORKTREE_PREFIX not in git(fixture.main, "worktree", "list")

    with_fixture(test)


for name, fn in [
    ("a failing gate leaves main unchanged", case_failing_gate_leaves_main_unchanged),
    ("local commits are in the checked tree", case_local_commits_are_in_the_checked_tree),
    ("local commits are named in the report", case_local_commits_are_reported),
    ("a gate that changes a tracked file is rejected",
     case_gate_changing_a_tracked_file_is_rejected),
    ("a drifting tracker export is rejected", case_export_drift_is_rejected),
    ("a source conflict stops and keeps unrelated work", case_conflict_stops_and_keeps_work),
    ("a dirty feature checkout stops", case_dirty_feature_checkout_stops),
    ("the export rides the candidate commit", case_export_rides_the_candidate_commit),
    ("a dirty default checkout is left alone", case_dirty_default_checkout_is_left_alone),
    ("a default checkout dirty only in the export lands",
     case_export_only_dirty_default_checkout_lands),
    ("a default checkout with the export staged lands",
     case_staged_export_in_default_checkout_lands),
    ("the export and another change stop the landing",
     case_export_and_another_change_stop_the_landing),
    ("a restored export is reported", case_restored_export_is_reported),
    ("a clean landing reports no restore", case_clean_landing_reports_no_restore),
    ("cleanup removes only the temporary worktree",
     case_cleanup_removes_only_the_temporary_worktree),
    ("a later local commit is reported unpushed", case_later_commit_is_reported_unpushed),
    ("the interactions log stays untracked", case_audit_log_stays_untracked),
    ("a bead-free landing writes no export", case_bead_free_landing_writes_no_export),
    ("audit lines from the temporary worktree are kept",
     case_audit_lines_written_in_the_temporary_worktree_are_kept),
    ("appended audit lines never join an unterminated line",
     case_appended_audit_lines_never_join_an_unterminated_line),
    ("untracked gate output does not reject the candidate",
     case_untracked_gate_output_does_not_reject_the_candidate),
]:  # fmt: skip
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
