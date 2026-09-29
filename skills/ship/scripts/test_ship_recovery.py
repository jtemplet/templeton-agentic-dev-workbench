#!/usr/bin/env python3
"""Regression suite for resuming interrupted ship runs: ship_progress.py, ship_recovery.py,
and the recovery paths through bin/tadw-ship.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_ship_recovery.py

An interruption is a real SIGKILL: a fake `bd` or a git hook kills the running
tadw-ship process at the named point, and a second run resumes from the record.

  tadw-dur4 criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. After an interruption past the close or        case_1_resume_after_close_ships_the_bead,
     the candidate commit, resume validates the     case_1_resume_after_close_validates_the_bead,
     bead and recorded Git state first              case_1_close_without_landing_is_rebuilt
  2. A bead closed by another run or changed        case_2_bead_closed_by_another_run_is_not_reopened,
     concurrently is never taken for this run's     case_2_close_interrupted_midway_is_not_claimed,
     close, nor reopened                            case_2_changed_close_is_not_this_runs
  3. A gate failure after this run's close          case_3_gate_failure_after_close_reopens_the_bead,
     reopens a matching bead and regenerates        case_3_reopen_regenerates_the_export,
     its export; otherwise it reports the status    case_3_changed_bead_reports_its_status,
     and keeps the candidate                        case_3_changed_bead_keeps_the_candidate
  4. A moved destination rebuilds and rechecks      case_4_moved_destination_rebuilds_on_it,
                                                    case_4_moved_destination_reruns_the_gate
  5. An authentication failure or a hook            case_5_auth_failure_keeps_the_candidate,
     refusal keeps the candidate, reports the       case_5_auth_failure_is_not_rebuilt,
     cause, and is not rebuilt                      case_5_hook_refusal_reports_the_cause,
                                                    case_5_refusals_are_classified
  6. An uncertain push result inspects the          case_6_uncertain_push_inspects_the_destination,
     destination before retry or cleanup            case_6_uncertain_push_decisions
  7. Resume neither duplicates a landing nor        case_7_resume_after_close_lands_once,
     deletes unrelated work                         case_7_resume_after_advance_lands_once,
                                                    case_7_resume_after_refused_push_publishes,
                                                    case_7_resume_keeps_unrelated_work
  8. Two concurrent ship runs in one repository:    case_8_second_run_stops_while_one_holds_the_lock,
     only one mutates                               case_8_second_run_changes_nothing
  9. A branch already landed closes its bead and    case_9_landed_branch_ends_with_ship_done_default_tip,
     exits SHIP_DONE <default tip>, no gate, no     case_9_landed_branch_closes_the_bead,
     rebase                                         case_9_landed_branch_runs_no_gate,
                                                    case_9_landed_branch_is_not_rebased
"""

from __future__ import annotations

import fcntl
import functools
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
EXECUTABLE = HERE.parents[2] / "bin" / "tadw-ship"
BEAD = "tadw-rec"
BRANCH = f"feature/{BEAD}/add-thing"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ship_progress = load("ship_progress")
ship_recovery = load("ship_recovery")

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


# A one-bead tracker. Each close and edit stamps closed_at/updated_at from a counter,
# so a later change is visible. `on-<event>` scripts in the state directory run after it.
FAKE_BD = """#!/bin/sh
state="$(dirname "$0")"
tick() { n=$(( $(cat "$state/clock") + 1 )); echo "$n" > "$state/clock"; echo "t$n"; }
after() { if [ -x "$state/on-$1" ]; then "$state/on-$1"; fi; }
case "$1" in
  show)
    if [ "$2" = "BEAD" ]; then
      printf '[{"id":"BEAD","title":"Add the thing","issue_type":"feature","status":"%s","closed_at":%s,"updated_at":"%s"}]' \\
        "$(cat "$state/status")" "$(cat "$state/closed_at")" "$(cat "$state/updated_at")"
    else
      printf '{"error":"no issue found"}'
    fi ;;
  close)
    echo closed > "$state/status"; t=$(tick); printf '"%s"' "$t" > "$state/closed_at"
    echo "$t" > "$state/updated_at"; after close ;;
  reopen)
    echo open > "$state/status"; echo null > "$state/closed_at"; tick > "$state/updated_at"
    after reopen ;;
  export)
    mkdir -p "$(dirname "$3")"
    printf '{"id":"BEAD","status":"%s","updated_at":"%s"}\\n' \\
      "$(cat "$state/status")" "$(cat "$state/updated_at")" > "$3"
    after export ;;
  ready) printf '[]' ;;
esac
""".replace("BEAD", BEAD)

# Kills the tadw-ship process this script runs under, as a power cut would.
KILL_SHIP = """#!/bin/sh
pid=$$
while [ "$pid" -gt 1 ]; do
  pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
  case "$(ps -o command= -p "$pid")" in *bin/tadw-ship*) kill -9 "$pid"; exit 0 ;; esac
done
"""

# Wraps git so a test can make one push fail in a chosen way.
GIT_SHIM = """#!/bin/sh
state="$(dirname "$0")"
case " $* " in
  *" push "*)
    if [ -f "$state/push-auth-fails" ]; then
      echo "fatal: Authentication failed for 'origin'" >&2; exit 128
    fi
    if [ -f "$state/push-hangs-up" ]; then
      rm "$state/push-hangs-up"; "REAL_GIT" "$@"
      echo "fatal: the remote end hung up unexpectedly" >&2; exit 128
    fi ;;
esac
exec "REAL_GIT" "$@"
""".replace("REAL_GIT", shutil.which("git"))


class Repository:
    """A main checkout with an origin, a worktree whose branch adds a file, and a second clone."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.main = root / "main"
        self.worktree = root / "worktrees" / "add-thing"
        self.state = root / "shims"
        self.origin = root / "origin.git"
        self.gate_log = root / "gate.log"
        self.create()

    def create(self) -> None:
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.main)], check=True)
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@t")
        (self.main / ".beads").mkdir()
        (self.main / ".beads" / "issues.jsonl").write_text("{}\n")
        (self.main / "base.txt").write_text("base\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "base")
        self.git("remote", "add", "origin", str(self.origin))
        self.git("push", "-q", "-u", "origin", "main")
        self.git("worktree", "add", "-q", "-b", BRANCH, str(self.worktree), "main")
        (self.worktree / "thing.txt").write_text("the thing\n")
        self.git("-C", str(self.worktree), "add", "thing.txt")
        self.git("-C", str(self.worktree), "commit", "-q", "-m", "Add the thing")
        self.install_tools()

    def install_tools(self) -> None:
        self.state.mkdir()
        for name, value in (("status", "open"), ("closed_at", "null"), ("updated_at", "t0"),
                            ("clock", "0")):  # fmt: skip
            (self.state / name).write_text(f"{value}\n")
        for name, body in (("bd", FAKE_BD), ("kill-ship", KILL_SHIP), ("git", GIT_SHIM)):
            self.executable(self.state / name, body)
        self.gate("true")

    def executable(self, path: Path, body: str) -> None:
        path.write_text(body if body.startswith("#!") else f"#!/bin/sh\n{body}\n")
        path.chmod(0o755)

    def gate(self, body: str) -> None:
        self.executable(self.root / "gate.sh", f'echo run >> "{self.gate_log}"\n{body}')

    def on(self, event: str, body: str) -> None:
        """Run `body` once, after the fake bd's next `event` whose condition holds."""
        self.executable(self.state / f"on-{event}", body)

    def hook(self, name: str, body: str) -> None:
        self.executable(self.main / ".git" / "hooks" / name, body)

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.main), *args], capture_output=True, text=True, check=True
        )
        return completed.stdout.strip()

    def ship(self, cwd: Path | None = None) -> subprocess.CompletedProcess:
        environment = {k: v for k, v in os.environ.items() if not k.startswith("TADW_SHIP")}
        environment["PATH"] = f"{self.state}{os.pathsep}{os.environ['PATH']}"
        environment["TADW_SHIP_CHECK"] = f"sh {self.root / 'gate.sh'}"
        return subprocess.run(
            [str(EXECUTABLE), BEAD, "--repo-root", str(self.worktree)],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd or self.main,
            env=environment,
        )


class Outcome(NamedTuple):
    """What each run printed, and the repository and tracker afterwards."""

    runs: tuple[subprocess.CompletedProcess, ...]
    main_tip: str
    origin_tip: str
    bead_status: str
    gate_runs: int
    landings: int
    record_kept: bool
    candidate_ref_kept: bool
    main_export: str
    branch_tip: str
    noted: str
    unrelated_file_kept: bool
    stale_worktrees: int

    def last(self, index: int = -1) -> str:
        return self.runs[index].stdout.splitlines()[-1]

    def stderr(self, index: int = -1) -> str:
        return self.runs[index].stderr


def scenario(prepare, runs: int = 2, between=None) -> Outcome:
    """Prepare the repository, ship `runs` times, and read back the state.

    `prepare` may return a string to keep, such as a commit it read before the runs.
    """
    with tempfile.TemporaryDirectory() as directory:
        repository = Repository(Path(directory).resolve())
        (repository.main / "notes.local").write_text("mine\n")
        noted = prepare(repository) or ""
        results = []
        for index in range(runs):
            results.append(repository.ship())
            if between is not None and index == 0:
                between(repository)
        return read_outcome(repository, tuple(results), noted)


def read_outcome(repository: Repository, runs: tuple, noted: str) -> Outcome:
    git = repository.git
    common = repository.main / ".git"
    worktrees = git("worktree", "list", "--porcelain")
    return Outcome(
        runs=runs,
        main_tip=git("rev-parse", "main"),
        origin_tip=subprocess.run(
            ["git", "--git-dir", str(repository.origin), "rev-parse", "main"],
            capture_output=True,
            text=True,
        ).stdout.strip(),  # fmt: skip
        bead_status=(repository.state / "status").read_text().strip(),
        gate_runs=len(repository.gate_log.read_text().splitlines())
        if repository.gate_log.exists()
        else 0,
        # A second landing of the same branch would be a second commit adding thing.txt.
        landings=int(git("rev-list", "--count", "main", "--", "thing.txt")),
        record_kept=(common / "tadw-ship" / "progress.json").exists(),
        candidate_ref_kept=bool(git("for-each-ref", ship_progress.CANDIDATE_REF)),
        main_export=(repository.main / ".beads" / "issues.jsonl").read_text(),
        branch_tip=subprocess.run(
            ["git", "-C", str(repository.main), "rev-parse", "--verify", "--quiet", BRANCH],
            capture_output=True,
            text=True,
        ).stdout.strip(),  # fmt: skip
        noted=noted,
        unrelated_file_kept=read_if_present(repository.main / "notes.local") == "mine\n",
        stale_worktrees=worktrees.count("tadw-ship-candidate-"),
    )


def read_if_present(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def kill_on_closed_export(repository: Repository) -> None:
    """Die right after the landing export, once this run's close is recorded."""
    repository.on("export", f'[ "$(cat "{repository.state}/status")" = closed ] || exit 0\n'
                  f'rm "$0"; "{repository.state}/kill-ship"')  # fmt: skip


def kill_after_advance(repository: Repository) -> None:
    """Die in main's post-merge: the default branch has moved, and the record says `landing`.

    The candidate's squash merge runs the same hook, from its own worktree, so it is skipped.
    """
    repository.hook("post-merge", f'[ "$(pwd -P)" = "{repository.main}" ] || exit 0\n'
                    f'rm "$0"; "{repository.state}/kill-ship"')  # fmt: skip


def moved_on_close(repository: Repository) -> None:
    repository.on("close", f'rm "$0"; "{repository.state}/move-origin"')
    script = (
        f'cd "{repository.root}/other" && echo moved > moved.txt && git add moved.txt && '
        "git -c user.name=o -c user.email=o@o commit -q -m moved && git push -q origin main"
    )
    subprocess.run(["git", "clone", "-q", str(repository.origin), str(repository.root / "other")],
                   check=True)  # fmt: skip
    repository.executable(repository.state / "move-origin", script)


# ---- unit: the recovery decisions -------------------------------------------------------

CLOSE = ship_progress.BeadClose("closed", "t3", "t3")


Resume = ship_recovery.Resume
PushNext = ship_recovery.PushNext


def recorded(state: str, **facts) -> ship_progress.Progress:
    base = {"bead_id": BEAD, "bead_title": "Add the thing", "bead_type": "feature",
            "parent": "p", "branch_tip": "b", "landing_commit": "l", "close": CLOSE}  # fmt: skip
    return ship_progress.Progress("run", state, BRANCH, "main", **{**base, **facts})


def observed(bead=CLOSE, **facts) -> ship_recovery.Observed:
    base = {"default_tip": "p", "branch_tip": "b", "landing_exists": True,
            "landing_on_default": False}  # fmt: skip
    return ship_recovery.Observed(bead=bead, **{**base, **facts})


def action(progress, seen) -> ship_recovery.Resume:
    return ship_recovery.resume_action(progress, seen).action


def case_1_resume_after_close_validates_the_bead() -> None:
    changed = ship_progress.BeadClose("closed", "t3", "t9")
    assert action(recorded("landing"), observed()) is Resume.ADVANCE
    assert action(recorded("landing"), observed(bead=changed)) is Resume.STOP_TRACKER


def case_2_bead_closed_by_another_run_is_not_reopened() -> None:
    assert action(recorded("candidate", close=None), observed()) is Resume.STOP_TRACKER


def case_2_close_interrupted_midway_is_not_claimed() -> None:
    assert action(recorded("closing", close=None), observed()) is Resume.STOP_TRACKER


def case_2_changed_close_is_not_this_runs() -> None:
    other = ship_progress.BeadClose("closed", "t7", "t7")
    assert action(recorded("closed"), observed(bead=other)) is Resume.STOP_TRACKER


def case_1_moved_base_rebuilds_rather_than_advances() -> None:
    assert action(recorded("landing"), observed(default_tip="q")) is Resume.REBUILD


def case_7_landing_on_default_is_never_rebuilt() -> None:
    assert action(recorded("landing"), observed(landing_on_default=True)) is Resume.PUBLISH
    assert action(recorded("pushed"), observed(landing_on_default=True)) is Resume.CLEAN_UP


def case_5_refusals_are_classified() -> None:
    classify = ship_recovery.classify_push_failure
    assert classify("fatal: Authentication failed for 'x'") is ship_recovery.PushFailure.AUTH
    assert classify(" ! [remote rejected] main (pre-receive hook declined)") is (
        ship_recovery.PushFailure.HOOK
    )
    assert classify("error: failed to push some refs to 'x'") is ship_recovery.PushFailure.HOOK
    assert classify(" ! [rejected] main -> main (fetch first)") is ship_recovery.PushFailure.MOVED


def case_5_hook_output_cannot_pass_for_a_network_failure() -> None:
    quoted = "test_pool: connection timed out\nerror: failed to push some refs to 'x'"
    assert ship_recovery.classify_push_failure(quoted) is ship_recovery.PushFailure.HOOK


def case_6_uncertain_push_decisions() -> None:
    uncertain = ship_recovery.PushFailure.UNCERTAIN
    view = ship_recovery.RemoteView
    decide = ship_recovery.after_push_failure
    assert decide(uncertain, view(True, carries_landing=True), retried=False) is PushNext.DONE
    assert decide(uncertain, view(True, behind_landing=True), retried=False) is PushNext.RETRY
    assert decide(uncertain, view(True, behind_landing=True), retried=True) is PushNext.REPORT
    assert decide(uncertain, view(False), retried=False) is PushNext.REPORT
    assert decide(uncertain, view(True), retried=False) is PushNext.REBUILD


def case_progress_record_round_trips() -> None:
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run(["git", "init", "-q", directory], check=True)
        store = ship_progress.ProgressStore(Path(directory) / ".git")
        store.save(recorded("closed", landing_commit=None, checked_commit=None))
        assert ship_progress.ProgressStore(Path(directory) / ".git").load() == store.current


# ---- end to end: interruptions and refusals ---------------------------------------------


@functools.cache
def resumed_after_close() -> Outcome:
    return scenario(kill_on_closed_export)


@functools.cache
def resumed_after_advance() -> Outcome:
    return scenario(kill_after_advance)


@functools.cache
def changed_while_stopped() -> Outcome:
    def edit_the_bead(repository: Repository) -> None:
        (repository.state / "updated_at").write_text("t99\n")

    return scenario(kill_on_closed_export, between=edit_the_bead)


@functools.cache
def closed_by_another_run() -> Outcome:
    def kill_in_gate(repository: Repository) -> None:
        killed = repository.root / "killed"
        repository.gate(
            f'[ -f "{killed}" ] || {{ touch "{killed}"; "{repository.state}/kill-ship"; }}'
        )

    def close_elsewhere(repository: Repository) -> None:
        for name, value in (("status", "closed"), ("closed_at", '"t50"'), ("updated_at", "t50")):
            (repository.state / name).write_text(f"{value}\n")

    return scenario(kill_in_gate, between=close_elsewhere)


@functools.cache
def moved_destination() -> Outcome:
    return scenario(moved_on_close, runs=1)


@functools.cache
def killed_during_rebuild() -> Outcome:
    """Origin moves after the close; the run dies in the rebuilt candidate's gate."""

    def prepare(repository: Repository) -> None:
        moved_on_close(repository)
        killed = repository.root / "killed"
        repository.gate(
            f'[ "$(wc -l < "{repository.gate_log}")" -lt 2 ] || [ -f "{killed}" ] || '
            f'{{ touch "{killed}"; "{repository.state}/kill-ship"; }}'
        )

    return scenario(prepare)


@functools.cache
def moved_then_gate_fails() -> Outcome:
    def prepare(repository: Repository) -> None:
        moved_on_close(repository)
        repository.gate(f'[ "$(wc -l < "{repository.gate_log}")" -lt 2 ]')

    return scenario(prepare, runs=1)


@functools.cache
def auth_failure_then_resume() -> Outcome:
    def prepare(repository: Repository) -> None:
        (repository.state / "push-auth-fails").touch()

    def restore_credentials(repository: Repository) -> None:
        (repository.state / "push-auth-fails").unlink()

    return scenario(prepare, between=restore_credentials)


@functools.cache
def hook_refusal() -> Outcome:
    def prepare(repository: Repository) -> None:
        repository.hook("pre-push", 'echo "pre-push: refused by policy" >&2; exit 1')

    return scenario(prepare, runs=1)


@functools.cache
def uncertain_push() -> Outcome:
    def prepare(repository: Repository) -> None:
        (repository.state / "push-hangs-up").touch()

    return scenario(prepare, runs=1)


@functools.cache
def already_landed() -> Outcome:
    def prepare(repository: Repository) -> None:
        (repository.main / "thing.txt").write_text("the thing\n")
        repository.git("add", "thing.txt")
        repository.git("commit", "-q", "-m", "Add the thing by hand")
        repository.git("push", "-q", "origin", "main")
        return repository.git("rev-parse", BRANCH)

    return scenario(prepare, runs=1)


@functools.cache
def lock_held() -> tuple[Outcome, str]:
    with tempfile.TemporaryDirectory() as directory:
        repository = Repository(Path(directory).resolve())
        before = repository.git("rev-parse", "main")
        lock_dir = repository.main / ".git" / ship_progress.STATE_DIRECTORY
        lock_dir.mkdir()
        with (lock_dir / ship_progress.LOCK_NAME).open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            result = repository.ship()
        return read_outcome(repository, (result,), ""), before


def shipped(outcome: Outcome, index: int = -1) -> str:
    return outcome.last(index).removeprefix("SHIP_DONE ")


def case_1_resume_after_close_ships_the_bead() -> None:
    outcome = resumed_after_close()
    assert outcome.runs[0].returncode == -9, outcome.runs[0]
    assert outcome.last().startswith("SHIP_DONE "), outcome.stderr()
    assert outcome.origin_tip == shipped(outcome), outcome.stderr()
    assert outcome.bead_status == "closed"


def case_1_close_without_landing_is_rebuilt() -> None:
    assert "the recorded landing is verified" not in resumed_after_close().stderr()
    assert "build a new candidate" in resumed_after_close().stderr()


def case_2_bead_closed_by_another_run_stops_the_resume() -> None:
    outcome = closed_by_another_run()
    assert outcome.last() == "SHIP_BLOCKED tracker", outcome.stderr()
    assert "this run never closed it" in outcome.stderr(), outcome.stderr()


def case_2_bead_closed_by_another_run_stays_closed() -> None:
    assert closed_by_another_run().bead_status == "closed"


def case_3_gate_failure_after_close_reopens_the_bead() -> None:
    outcome = moved_then_gate_fails()
    assert outcome.last() == "SHIP_BLOCKED gate", outcome.stderr()
    assert outcome.bead_status == "open", outcome.stderr()


def case_3_reopen_regenerates_the_export() -> None:
    assert '"status":"open"' in moved_then_gate_fails().main_export


def case_3_gate_failure_leaves_origin_as_moved() -> None:
    outcome = moved_then_gate_fails()
    assert outcome.origin_tip == outcome.main_tip, "the default branch kept an unchecked landing"
    assert not outcome.record_kept, "a reversed close needs no recovery record"


def case_3_changed_bead_reports_its_status() -> None:
    outcome = changed_while_stopped()
    assert outcome.last() == "SHIP_BLOCKED tracker", outcome.stderr()
    assert "updated_at t99" in outcome.stderr(), outcome.stderr()
    assert outcome.bead_status == "closed", "a changed bead must not be reopened"


def case_3_changed_bead_keeps_the_candidate() -> None:
    outcome = changed_while_stopped()
    assert (outcome.record_kept, outcome.candidate_ref_kept) == (True, True), outcome.stderr()


def case_4_moved_destination_rebuilds_on_it() -> None:
    outcome = moved_destination()
    assert outcome.last().startswith("SHIP_DONE "), outcome.stderr()
    assert outcome.origin_tip == shipped(outcome)
    assert "origin/main moved; rebuilding" in outcome.stderr(), outcome.stderr()
    assert outcome.landings == 1, f"{outcome.landings} landing commits on main"


def case_4_moved_destination_reruns_the_gate() -> None:
    assert moved_destination().gate_runs == 2


def case_5_auth_failure_keeps_the_candidate() -> None:
    outcome = auth_failure_then_resume()
    first = outcome.runs[0]
    assert first.stdout.splitlines()[-1] == "SHIP_BLOCKED git-state", first.stderr
    assert "authentication failed" in first.stderr, first.stderr


def case_5_auth_failure_is_not_rebuilt() -> None:
    assert auth_failure_then_resume().gate_runs == 1


def case_5_hook_refusal_reports_the_cause() -> None:
    outcome = hook_refusal()
    assert outcome.last() == "SHIP_BLOCKED git-state", outcome.stderr()
    assert "a hook refused the push" in outcome.stderr(), outcome.stderr()
    assert (outcome.gate_runs, outcome.record_kept) == (1, True), outcome.stderr()
    assert outcome.main_tip != outcome.origin_tip, "the landing was not kept on main"


def case_6_uncertain_push_inspects_the_destination() -> None:
    outcome = uncertain_push()
    assert outcome.last().startswith("SHIP_DONE "), outcome.stderr()
    assert "reported a failure, but origin/main carries" in outcome.stderr(), outcome.stderr()
    assert outcome.origin_tip == shipped(outcome)


def case_7_resume_after_close_lands_once() -> None:
    outcome = resumed_after_close()
    assert outcome.landings == 1, outcome.stderr()
    assert outcome.stale_worktrees == 0, "the killed run's candidate worktree was left behind"


def case_7_resume_after_advance_lands_once() -> None:
    outcome = resumed_after_advance()
    assert outcome.runs[0].returncode == -9, outcome.runs[0]
    assert outcome.last().startswith("SHIP_DONE "), outcome.stderr()
    assert outcome.landings == 1, outcome.stderr()
    assert (outcome.gate_runs, outcome.origin_tip) == (1, outcome.main_tip), outcome.stderr()


def case_7_resume_after_refused_push_publishes() -> None:
    outcome = auth_failure_then_resume()
    assert outcome.last().startswith("SHIP_DONE "), outcome.stderr()
    assert (outcome.origin_tip, outcome.landings) == (shipped(outcome), 1)
    assert not outcome.record_kept


def case_1_kill_during_rebuild_resumes_this_runs_close() -> None:
    outcome = killed_during_rebuild()
    assert outcome.runs[0].returncode == -9, outcome.runs[0]
    assert outcome.last().startswith("SHIP_DONE "), outcome.stderr()
    assert (outcome.bead_status, outcome.landings) == ("closed", 1), outcome.stderr()


def case_1_close_recorded_before_the_candidate_is_rebuilt() -> None:
    assert action(recorded("candidate", landing_commit=None), observed()) is Resume.REBUILD


def case_7_resume_keeps_unrelated_work() -> None:
    for outcome in (resumed_after_close(), resumed_after_advance(), auth_failure_then_resume()):
        assert outcome.unrelated_file_kept, "an untracked file in main was lost"


def case_8_second_run_stops_while_one_holds_the_lock() -> None:
    outcome, _ = lock_held()
    assert outcome.last() == "SHIP_BLOCKED git-state", outcome.stderr()
    assert "another tadw-ship run holds" in outcome.stderr(), outcome.stderr()


def case_8_second_run_changes_nothing() -> None:
    outcome, before = lock_held()
    assert (outcome.main_tip, outcome.bead_status, outcome.gate_runs) == (before, "open", 0)


def case_9_landed_branch_ends_with_ship_done_default_tip() -> None:
    outcome = already_landed()
    assert outcome.runs[0].returncode == 0, outcome.stderr()
    assert outcome.last() == f"SHIP_DONE {outcome.main_tip}", outcome.stdout


def case_9_landed_branch_closes_the_bead() -> None:
    assert already_landed().bead_status == "closed"


def case_9_landed_branch_runs_no_gate() -> None:
    assert already_landed().gate_runs == 0


def case_9_landed_branch_is_not_rebased() -> None:
    outcome = already_landed()
    assert outcome.branch_tip == outcome.noted, "the branch was rebased"


for name, fn in [
    ("the progress record round-trips", case_progress_record_round_trips),
    ("1. resume after a close validates the bead", case_1_resume_after_close_validates_the_bead),
    ("1. a moved base rebuilds rather than advances",
     case_1_moved_base_rebuilds_rather_than_advances),
    ("1. a close recorded before the candidate is rebuilt",
     case_1_close_recorded_before_the_candidate_is_rebuilt),
    ("1. a kill during a rebuild resumes this run's close",
     case_1_kill_during_rebuild_resumes_this_runs_close),
    ("1. a run killed after its close resumes and ships",
     case_1_resume_after_close_ships_the_bead),
    ("1. a close with no recorded landing is rebuilt", case_1_close_without_landing_is_rebuilt),
    ("2. a bead closed by another run is not reopened",
     case_2_bead_closed_by_another_run_is_not_reopened),
    ("2. a close interrupted midway is not claimed", case_2_close_interrupted_midway_is_not_claimed),
    ("2. a changed close is not this run's", case_2_changed_close_is_not_this_runs),
    ("2. a bead closed elsewhere stops the resume",
     case_2_bead_closed_by_another_run_stops_the_resume),
    ("2. a bead closed elsewhere stays closed", case_2_bead_closed_by_another_run_stays_closed),
    ("3. a gate failure after the close reopens the bead",
     case_3_gate_failure_after_close_reopens_the_bead),
    ("3. the reopen regenerates the export", case_3_reopen_regenerates_the_export),
    ("3. the failed rebuild leaves main at the moved origin",
     case_3_gate_failure_leaves_origin_as_moved),
    ("3. a changed bead reports its actual status", case_3_changed_bead_reports_its_status),
    ("3. a changed bead keeps the candidate", case_3_changed_bead_keeps_the_candidate),
    ("4. a moved destination rebuilds on it", case_4_moved_destination_rebuilds_on_it),
    ("4. a moved destination reruns the gate", case_4_moved_destination_reruns_the_gate),
    ("5. push refusals are classified", case_5_refusals_are_classified),
    ("5. hook output cannot pass for a network failure",
     case_5_hook_output_cannot_pass_for_a_network_failure),
    ("5. an auth failure keeps the candidate and names the cause",
     case_5_auth_failure_keeps_the_candidate),
    ("5. an auth failure is not rebuilt", case_5_auth_failure_is_not_rebuilt),
    ("5. a hook refusal reports the cause and keeps the landing",
     case_5_hook_refusal_reports_the_cause),
    ("6. uncertain push decisions follow the destination", case_6_uncertain_push_decisions),
    ("6. an uncertain push inspects the destination",
     case_6_uncertain_push_inspects_the_destination),
    ("7. a landing on the default branch is never rebuilt",
     case_7_landing_on_default_is_never_rebuilt),
    ("7. resume after the close lands once", case_7_resume_after_close_lands_once),
    ("7. resume after the advance lands once", case_7_resume_after_advance_lands_once),
    ("7. resume after a refused push publishes", case_7_resume_after_refused_push_publishes),
    ("7. resume keeps unrelated work", case_7_resume_keeps_unrelated_work),
    ("8. a second run stops while one holds the lock",
     case_8_second_run_stops_while_one_holds_the_lock),
    ("8. the second run changes nothing", case_8_second_run_changes_nothing),
    ("9. a landed branch ends with SHIP_DONE <default tip>",
     case_9_landed_branch_ends_with_ship_done_default_tip),
    ("9. a landed branch closes the bead", case_9_landed_branch_closes_the_bead),
    ("9. a landed branch runs no gate", case_9_landed_branch_runs_no_gate),
    ("9. a landed branch is not rebased", case_9_landed_branch_is_not_rebased),
]:  # fmt: skip
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
