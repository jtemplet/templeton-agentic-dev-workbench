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

  tadw-n8xh criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. A changed input file runs the check again      case_changed_input_file_runs_the_check_again
  2. A changed command, tool identity, or           case_changed_command_runs_the_check_again,
     declared environment runs the check again      case_changed_tool_version_runs_the_check_again,
                                                    case_tool_changed_during_the_run_runs_the_check_again,
                                                    case_changed_declared_variable_runs_the_check_again
  3. Incomplete or unverifiable inputs run the      case_input_matching_no_file_runs_the_check_again,
     check again                                    case_undeclared_tools_run_the_check_again,
                                                    case_tools_omitting_the_commands_program_run_the_check_again,
                                                    case_tool_missing_from_path_runs_the_check_again,
                                                    case_tool_without_a_version_runs_the_check_again,
                                                    case_files_git_cannot_list_run_the_check_again,
                                                    case_unreadable_saved_result_runs_the_check_again,
                                                    case_failed_result_runs_the_check_again,
                                                    case_input_changed_during_the_run_runs_the_check_again
  4. Matching inputs start fewer check processes    case_matching_inputs_start_fewer_processes_than_a_cold_run,
     than a cold run                                case_reused_result_is_a_pass_marked_reused,
                                                    case_planned_check_reuses_its_gates_saved_result,
                                                    case_reused_planned_check_records_exit_status_0
"""

from __future__ import annotations

import importlib.util
import json
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


print("\n  [tadw-n8xh: a saved result stands in only when everything declared matches]")

FAKE_TOOL = "tadw-fake-tool"
SETTING = "TADW_REUSE_SETTING"


class ReuseFixture:
    """A repository with one input file, one tool on PATH, and a check that counts its own runs.

    The counter, the tool, and the store live outside the repository, so none of
    them is ever an input.
    """

    def __init__(self, in_repository: bool = True) -> None:
        self.root = workspace()
        self.outside = workspace()
        if in_repository:
            subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "input.txt").write_text("one\n", encoding="utf-8")
        self.write_tool("echo 1.0")
        self.environ = {"PATH": f"{self.outside}{os.pathsep}{os.environ['PATH']}", SETTING: "a"}
        self.body = f"open({str(self.outside / 'runs')!r}, 'a').write('x')"
        tools = (sys.executable, FAKE_TOOL)
        self.declared = {"inputs": ("input.txt",), "tools": tools, "env": (SETTING,)}

    def write_tool(self, script: str) -> None:
        tool = self.outside / FAKE_TOOL
        tool.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
        tool.chmod(0o755)

    def run(self) -> run_checks.CheckResult:
        """One run, as a caller makes it: a fresh `SavedResults` over the same store."""
        results = run_checks.SavedResults(self.root, self.outside / "saved", self.environ)
        check = run_checks.Check(
            name="counted",
            command=(sys.executable, "-c", self.body),
            log=self.outside / "counted.out",
            cwd=self.root,
            reuse=run_checks.Reuse(**self.declared, results=results),
        )
        return run([check], workers=1)["counted"]

    def processes_started(self) -> int:
        runs = self.outside / "runs"
        return len(runs.read_text(encoding="utf-8")) if runs.exists() else 0


def started_by_second_run(change=lambda fixture: None, **fixture_options) -> int:
    """How many processes the second run starts, after `change` alters the fixture."""
    fixture = ReuseFixture(**fixture_options)
    fixture.run()
    change(fixture)
    fixture.run()
    return fixture.processes_started() - 1


def started_by_two_runs(prepare) -> int:
    """How many processes two runs start, when `prepare` alters the fixture before the first."""
    fixture = ReuseFixture()
    prepare(fixture)
    fixture.run()
    fixture.run()
    return fixture.processes_started()


def case_changed_input_file_runs_the_check_again() -> None:
    def change(fixture: ReuseFixture) -> None:
        (fixture.root / "input.txt").write_text("two\n", encoding="utf-8")

    assert started_by_second_run(change) == 1, "a changed input file must run the check again"


def case_changed_command_runs_the_check_again() -> None:
    def change(fixture: ReuseFixture) -> None:
        fixture.body += "  # a changed command"

    assert started_by_second_run(change) == 1, "a changed command must run the check again"


def case_changed_tool_version_runs_the_check_again() -> None:
    assert started_by_second_run(lambda fixture: fixture.write_tool("echo 2.0")) == 1, (
        "a tool that reports another version must run the check again"
    )


def case_changed_declared_variable_runs_the_check_again() -> None:
    def change(fixture: ReuseFixture) -> None:
        fixture.environ[SETTING] = "b"

    assert started_by_second_run(change) == 1, (
        "a changed declared variable must run the check again"
    )


def case_input_matching_no_file_runs_the_check_again() -> None:
    def prepare(fixture: ReuseFixture) -> None:
        fixture.declared["inputs"] = ("input.txt", "absent.txt")

    assert started_by_two_runs(prepare) == 2, "an input that matches no file cannot be verified"


def case_undeclared_tools_run_the_check_again() -> None:
    def prepare(fixture: ReuseFixture) -> None:
        fixture.declared["tools"] = ()

    assert started_by_two_runs(prepare) == 2, "a check that names no tool is never reused"


def case_tools_omitting_the_commands_program_run_the_check_again() -> None:
    def prepare(fixture: ReuseFixture) -> None:
        fixture.declared["tools"] = (FAKE_TOOL,)

    assert started_by_two_runs(prepare) == 2, (
        "a check that does not declare the program its command runs is never reused"
    )


def case_tool_changed_during_the_run_runs_the_check_again() -> None:
    """The check rewrites its tool, and the tool is put back before the second run.

    The tool read before the first run then matches the second run's reading, so
    only a fresh reading after the run keeps that pass out of the store.
    """
    fixture = ReuseFixture()
    changed = "#!/bin/sh\necho 2.0\n"
    fixture.body += f"; open({str(fixture.outside / FAKE_TOOL)!r}, 'w').write({changed!r})"
    fixture.run()
    fixture.write_tool("echo 1.0")
    fixture.run()
    assert fixture.processes_started() == 2, (
        "a pass whose tool changed while it ran describes no state, so it is not saved"
    )


def case_tool_missing_from_path_runs_the_check_again() -> None:
    def change(fixture: ReuseFixture) -> None:
        (fixture.outside / FAKE_TOOL).unlink()

    assert started_by_second_run(change) == 1, "a tool that is not on PATH cannot be verified"


def case_tool_without_a_version_runs_the_check_again() -> None:
    assert started_by_two_runs(lambda fixture: fixture.write_tool("exit 1")) == 2, (
        "a tool whose --version fails cannot be verified"
    )


def case_files_git_cannot_list_run_the_check_again() -> None:
    assert started_by_second_run(in_repository=False) == 1, (
        "inputs outside a git repository cannot be listed, so they cannot be verified"
    )


def case_unreadable_saved_result_runs_the_check_again() -> None:
    def change(fixture: ReuseFixture) -> None:
        for saved in (fixture.outside / "saved").iterdir():
            saved.write_text("{not json", encoding="utf-8")

    assert started_by_second_run(change) == 1, "a saved result that cannot be read is no result"


def case_failed_result_runs_the_check_again() -> None:
    def prepare(fixture: ReuseFixture) -> None:
        fixture.body += "; raise SystemExit(1)"

    assert started_by_two_runs(prepare) == 2, "a failed result must never stand in for a check"


def case_input_changed_during_the_run_runs_the_check_again() -> None:
    """The check rewrites its input, and the input is put back before the second run.

    The state read before the first run then matches the second run's state, so
    only the comparison made after the run keeps that pass out of the store.
    """
    fixture = ReuseFixture()
    fixture.body += f"; open({str(fixture.root / 'input.txt')!r}, 'w').write('changed')"
    fixture.run()
    (fixture.root / "input.txt").write_text("one\n", encoding="utf-8")
    fixture.run()
    assert fixture.processes_started() == 2, (
        "a pass whose input changed while it ran describes no state, so it is not saved"
    )


def case_matching_inputs_start_fewer_processes_than_a_cold_run() -> None:
    cold_run_started = 1
    assert started_by_second_run() < cold_run_started, (
        "with every declared value unchanged, the second run must start no process"
    )


def case_reused_result_is_a_pass_marked_reused() -> None:
    fixture = ReuseFixture()
    fixture.run()
    result = fixture.run()
    assert (result.status, result.exit_code, result.reused) == (
        run_checks.Status.PASSED,
        0,
        True,
    ), f"a reused result reads as a pass and says it was reused: {result}"


class PlannedReuseFixture:
    """The executor as the hook runs it: a plan directory, and a gate file that declares reuse."""

    def __init__(self) -> None:
        self.root = workspace()
        self.plan = workspace()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        counter = f"open({str(self.plan / 'runs')!r}, 'a').write('x')\n"
        (self.root / "count.py").write_text(counter, encoding="utf-8")
        self.write_gate([sys.executable, "count.py"])
        (self.plan / "1.cmd").write_text(f"{sys.executable} count.py\n", encoding="utf-8")

    def write_gate(self, command: list[str]) -> None:
        declared = {"inputs": ["count.py"], "tools": [command[0]]}
        gate = {"name": "counted", "command": command} | declared
        config = self.root / ".tadw" / "ship-gates.json"
        config.parent.mkdir()
        config.write_text(json.dumps({"version": 1, "gates": [gate | {"reuse": True}]}))

    def run_twice(self) -> PlannedReuseFixture:
        for _ in range(2):
            subprocess.run(
                [sys.executable, str(SCRIPT), "--plan-dir", str(self.plan), "--workers", "1"]
                + ["--repo-root", "."],
                cwd=self.root,
                capture_output=True,
                check=True,
            )
        return self


def case_planned_check_reuses_its_gates_saved_result() -> None:
    fixture = PlannedReuseFixture().run_twice()
    assert (fixture.plan / "runs").read_text(encoding="utf-8") == "x", (
        "a planned check whose command is a reusable gate must run once in two runs"
    )


def case_reused_planned_check_records_exit_status_0() -> None:
    fixture = PlannedReuseFixture().run_twice()
    assert (fixture.plan / "1.rc").read_text(encoding="utf-8") == "0\n", (
        "the hook reads the status file, so a reused check must record exit status 0"
    )


for name, fn in [
    ("a changed input file runs the check again", case_changed_input_file_runs_the_check_again),
    ("a changed command runs the check again", case_changed_command_runs_the_check_again),
    ("a changed tool version runs the check again", case_changed_tool_version_runs_the_check_again),
    (
        "a changed declared variable runs the check again",
        case_changed_declared_variable_runs_the_check_again,
    ),
    (
        "an input that matches no file runs the check again",
        case_input_matching_no_file_runs_the_check_again,
    ),
    ("undeclared tools run the check again", case_undeclared_tools_run_the_check_again),
    (
        "tools that omit the command's own program run the check again",
        case_tools_omitting_the_commands_program_run_the_check_again,
    ),
    (
        "a tool changed during the run runs the check again",
        case_tool_changed_during_the_run_runs_the_check_again,
    ),
    (
        "a tool missing from PATH runs the check again",
        case_tool_missing_from_path_runs_the_check_again,
    ),
    (
        "a tool without a version runs the check again",
        case_tool_without_a_version_runs_the_check_again,
    ),
    ("files git cannot list run the check again", case_files_git_cannot_list_run_the_check_again),
    (
        "an unreadable saved result runs the check again",
        case_unreadable_saved_result_runs_the_check_again,
    ),
    ("a failed result runs the check again", case_failed_result_runs_the_check_again),
    (
        "an input changed during the run runs the check again",
        case_input_changed_during_the_run_runs_the_check_again,
    ),
    (
        "matching inputs start fewer processes than a cold run",
        case_matching_inputs_start_fewer_processes_than_a_cold_run,
    ),
    ("a reused result is a pass marked reused", case_reused_result_is_a_pass_marked_reused),
    (
        "a planned check reuses its gate's saved result",
        case_planned_check_reuses_its_gates_saved_result,
    ),
    (
        "a reused planned check records exit status 0",
        case_reused_planned_check_records_exit_status_0,
    ),
]:
    check(name, fn)


for path in workspaces:
    shutil.rmtree(path, ignore_errors=True)

print(f"\n  {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
