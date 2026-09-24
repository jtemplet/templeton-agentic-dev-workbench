#!/usr/bin/env python3
"""Regression suite for run_checks.py, the check executor ship and pre-push share.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_run_checks.py

  tadw-7raw criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. Independent checks overlap within the          case_independent_checks_overlap,
     configured worker limit                        case_workers_bound_the_overlap
  2. Checks sharing a tracker resource run in       case_shared_resource_runs_in_list_order,
     order                                          case_other_checks_run_beside_a_resource,
                                                    case_dependent_of_a_failed_check_runs,
                                                    case_dependent_waits_for_its_dependency,
                                                    case_a_plan_that_cannot_progress_ends
  3. A timeout or interruption never reports an     case_timed_out_check_has_no_exit_status,
     incomplete check as successful                 case_timeout_stops_the_checks_children,
                                                    case_a_timeout_does_not_pause_other_checks,
                                                    case_dependent_of_a_timed_out_check_never_runs,
                                                    case_check_ended_by_a_signal_is_interrupted,
                                                    case_interrupted_run_lets_a_check_clean_up,
                                                    case_interrupted_run_writes_no_exit_status
  Criterion 4 belongs to the hook: .githooks/test_prepush.py.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parent / "run_checks.py"

# How long a "slow" check holds its worker. Long enough that two checks started
# together overlap by a wide margin, short enough to keep the suite quick.
HOLD_SECONDS = 0.4
DEADLINE_SECONDS = 15
GRACE_SECONDS = 1.0

passed = 0
failed = 0
workspaces: list[Path] = []


def load_executor() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_checks", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_checks"] = module
    spec.loader.exec_module(module)
    return module


run_checks = load_executor()


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def workspace() -> Path:
    path = Path(tempfile.mkdtemp(prefix="tadw-run-checks-"))
    workspaces.append(path)
    return path


def python_check(work: Path, name: str, body: str, **options) -> run_checks.Check:
    return run_checks.Check(
        name=name,
        command=(sys.executable, "-c", body),
        log=work / f"{name}.out",
        cwd=work,
        **options,
    )


def sleeper(work: Path, name: str, **options) -> run_checks.Check:
    return python_check(work, name, f"import time; time.sleep({HOLD_SECONDS})", **options)


def run(checks: list[run_checks.Check], workers: int) -> dict[str, run_checks.CheckResult]:
    outcome = run_checks.run_checks(checks, workers, grace=GRACE_SECONDS)
    return {result.name: result for result in outcome.results}


def overlaps(first: run_checks.CheckResult, second: run_checks.CheckResult) -> bool:
    return first.started < second.ended and second.started < first.ended


def most_at_once(results: list[run_checks.CheckResult]) -> int:
    edges = sorted(
        [(result.started, 1) for result in results] + [(result.ended, -1) for result in results]
    )
    level = peak = 0
    for _, step in edges:
        level += step
        peak = max(peak, level)
    return peak


def process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError, PermissionError:
        return False
    return True


def wait_until(condition, what: str) -> None:
    deadline = time.monotonic() + DEADLINE_SECONDS
    while not condition():
        assert time.monotonic() < deadline, f"timed out waiting until {what}"
        time.sleep(0.05)


print("\n  [criterion 1: independent checks run at the same time]")


def case_independent_checks_overlap() -> None:
    work = workspace()
    results = run([sleeper(work, name) for name in ("a", "b", "c")], workers=3)
    assert overlaps(results["a"], results["b"]) and overlaps(results["b"], results["c"]), (
        f"three independent checks under three workers must overlap: {results}"
    )


def case_workers_bound_the_overlap() -> None:
    work = workspace()
    results = run([sleeper(work, name) for name in ("a", "b", "c", "d")], workers=2)
    assert most_at_once(list(results.values())) == 2, (
        f"two workers run two checks at once, never more: {results}"
    )


for name, fn in [
    ("independent checks overlap", case_independent_checks_overlap),
    ("the worker limit bounds the overlap", case_workers_bound_the_overlap),
]:
    check(name, fn)


print("\n  [criterion 2: checks sharing a resource take turns]")


def tracker_pair_beside_an_unrelated_check() -> dict[str, run_checks.CheckResult]:
    work = workspace()
    checks = [
        sleeper(work, "first", resources=("tracker",)),
        sleeper(work, "unrelated"),
        sleeper(work, "second", resources=("tracker",)),
    ]
    return run(checks, workers=3)


def failing_dependency_and_its_dependent() -> dict[str, run_checks.CheckResult]:
    work = workspace()
    failing = f"import time; time.sleep({HOLD_SECONDS}); raise SystemExit(1)"
    checks = [
        python_check(work, "first", failing),
        sleeper(work, "second", depends_on=("first",)),
    ]
    return run(checks, workers=2)


def case_shared_resource_runs_in_list_order() -> None:
    results = tracker_pair_beside_an_unrelated_check()
    assert results["first"].ended <= results["second"].started, (
        f"the second tracker check must start after the first ends: {results}"
    )


def case_other_checks_run_beside_a_resource() -> None:
    results = tracker_pair_beside_an_unrelated_check()
    assert overlaps(results["first"], results["unrelated"]), (
        f"a check without the resource still runs beside the tracker checks: {results}"
    )


def case_dependent_of_a_failed_check_runs() -> None:
    results = failing_dependency_and_its_dependent()
    assert results["second"].status is run_checks.Status.PASSED, (
        f"a dependency that failed still finished, so its dependent runs: {results}"
    )


def case_dependent_waits_for_its_dependency() -> None:
    results = failing_dependency_and_its_dependent()
    assert results["first"].ended <= results["second"].started, (
        f"the dependent must start after its dependency ends: {results}"
    )


def case_a_plan_that_cannot_progress_ends() -> None:
    """The earlier check waits for the later one, which waits for the tracker the earlier holds.

    The configuration validator accepts this plan, because it holds no dependency
    cycle. The executor must end it rather than wait forever. It runs in a child
    process with a deadline, so a hang fails this case instead of the whole suite.
    """
    probe = (
        "import sys\n"
        f"sys.path.insert(0, {str(SCRIPT.parent)!r})\n"
        "import run_checks, pathlib, tempfile\n"
        "work = pathlib.Path(tempfile.mkdtemp())\n"
        "def check(name, **options):\n"
        "    return run_checks.Check(name, (sys.executable, '-c', 'pass'), work / name, **options)\n"
        "outcome = run_checks.run_checks([\n"
        "    check('early', depends_on=('late',), resources=('tracker',)),\n"
        "    check('late', resources=('tracker',)),\n"
        "], workers=2)\n"
        "print(' '.join(result.status.value for result in outcome.results))\n"
    )
    try:
        finished = subprocess.run(
            [sys.executable, "-c", probe], capture_output=True, text=True, timeout=DEADLINE_SECONDS
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            "the executor waited forever on a plan that cannot progress"
        ) from error
    assert finished.stdout.split() == ["not_run", "not_run"], (
        f"neither check can ever start, so both are not run: {finished.stdout!r} {finished.stderr!r}"
    )


for name, fn in [
    ("checks sharing a resource run in list order", case_shared_resource_runs_in_list_order),
    ("other checks run beside a resource", case_other_checks_run_beside_a_resource),
    ("a dependent of a failed check still runs", case_dependent_of_a_failed_check_runs),
    ("a dependent waits for its dependency to end", case_dependent_waits_for_its_dependency),
    ("a plan that cannot progress ends instead of hanging", case_a_plan_that_cannot_progress_ends),
]:
    check(name, fn)


print("\n  [criterion 3: no incomplete check reads as a success]")


def case_timed_out_check_has_no_exit_status() -> None:
    work = workspace()
    result = run([python_check(work, "slow", "import time; time.sleep(60)", timeout=0.3)], 1)[
        "slow"
    ]
    assert (result.status, result.exit_code) == (run_checks.Status.TIMED_OUT, None), (
        f"a check stopped at its timeout has no exit status: {result}"
    )


def case_timeout_stops_the_checks_children() -> None:
    work = workspace()
    pid_file = work / "child.pid"
    body = (
        "import pathlib, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    # Long enough for the child to start while the whole gate loads the machine.
    run([python_check(work, "slow", body, timeout=3)], workers=1)
    assert pid_file.exists(), "the check timed out before it started its child"
    child = int(pid_file.read_text())
    wait_until(lambda: not process_is_alive(child), "the timed-out check's child stopped")


def case_a_timeout_does_not_pause_other_checks() -> None:
    """A check that ignores SIGTERM holds its grace period; the check beside it still finishes."""
    work = workspace()
    stubborn = (
        "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n"
    )
    checks = [
        python_check(work, "stubborn", stubborn, timeout=0.2),
        python_check(work, "quick", "import time; time.sleep(0.6)"),
    ]
    outcome = run_checks.run_checks(checks, workers=2, grace=3)
    stubborn_result, quick_result = outcome.results
    assert quick_result.ended < stubborn_result.ended, (
        f"the quick check must finish during the stubborn check's grace period: {outcome}"
    )


def case_dependent_of_a_timed_out_check_never_runs() -> None:
    work = workspace()
    mark = work / "dependent-ran"
    checks = [
        python_check(work, "slow", "import time; time.sleep(60)", timeout=0.3),
        python_check(
            work,
            "after",
            f"import pathlib; pathlib.Path({str(mark)!r}).touch()",
            depends_on=("slow",),
        ),
    ]
    results = run(checks, workers=2)
    assert results["after"].status is run_checks.Status.NOT_RUN, f"it must not run: {results}"
    assert not mark.exists(), "the dependent left its mark, so it ran"


def case_check_ended_by_a_signal_is_interrupted() -> None:
    work = workspace()
    body = "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"
    result = run([python_check(work, "killed", body)], workers=1)["killed"]
    assert (result.status, result.exit_code) == (run_checks.Status.INTERRUPTED, None), (
        f"a check a signal ended did not finish: {result}"
    )


def start_interruptible_run(work: Path) -> tuple[subprocess.Popen, Path]:
    """The executor as the hook runs it, over one check that cleans up on SIGINT."""
    cleaned = work / "cleaned"
    started = work / "started"
    check_body = (
        "import pathlib, time\n"
        f"pathlib.Path({str(started)!r}).touch()\n"
        "try:\n"
        "    time.sleep(60)\n"
        "finally:\n"
        f"    pathlib.Path({str(cleaned)!r}).touch()\n"
    )
    script = work / "slow_check.py"
    script.write_text(check_body, encoding="utf-8")
    (work / "1.cmd").write_text(f"{sys.executable} {script}\n", encoding="utf-8")
    executor = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--plan-dir", str(work), "--workers", "2", "--grace", "2"]
    )
    wait_until(started.exists, "the check started")
    return executor, cleaned


def case_interrupted_run_lets_a_check_clean_up() -> None:
    executor, cleaned = start_interruptible_run(workspace())
    executor.send_signal(signal.SIGTERM)
    assert executor.wait(timeout=DEADLINE_SECONDS) == 128 + signal.SIGTERM, (
        "an interrupted run exits 128 plus the signal"
    )
    assert cleaned.exists(), "the check got SIGINT and ran its cleanup before the run ended"


def case_interrupted_run_writes_no_exit_status() -> None:
    work = workspace()
    executor, _ = start_interruptible_run(work)
    executor.send_signal(signal.SIGINT)
    executor.wait(timeout=DEADLINE_SECONDS)
    assert not (work / "1.rc").exists(), "an interrupted check must have no exit status file"


for name, fn in [
    ("a timed-out check has no exit status", case_timed_out_check_has_no_exit_status),
    ("a timeout stops the check's children too", case_timeout_stops_the_checks_children),
    ("a timeout does not pause the other checks", case_a_timeout_does_not_pause_other_checks),
    (
        "a dependent of a timed-out check never runs",
        case_dependent_of_a_timed_out_check_never_runs,
    ),
    ("a check ended by a signal is interrupted", case_check_ended_by_a_signal_is_interrupted),
    ("an interrupted run lets a check clean up", case_interrupted_run_lets_a_check_clean_up),
    ("an interrupted run writes no exit status", case_interrupted_run_writes_no_exit_status),
]:
    check(name, fn)


print("\n  [a plan the executor cannot run is refused]")


def case_unknown_dependency_is_refused() -> None:
    work = workspace()
    try:
        run([sleeper(work, "a", depends_on=("missing",))], workers=1)
    except ValueError as error:
        assert "missing" in str(error), f"the error must name the unknown check: {error}"
        return
    raise AssertionError("a dependency on an unknown check must be refused")


def case_missing_command_fails() -> None:
    work = workspace()
    missing = run_checks.Check("gone", ("tadw-no-such-tool",), work / "gone.out", cwd=work)
    result = run([missing], workers=1)["gone"]
    assert result.status is run_checks.Status.FAILED, f"a command that cannot start fails: {result}"


for name, fn in [
    ("a dependency on an unknown check is refused", case_unknown_dependency_is_refused),
    ("a command that cannot start fails", case_missing_command_fails),
]:
    check(name, fn)


for path in workspaces:
    shutil.rmtree(path, ignore_errors=True)

print(f"\n  {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
