#!/usr/bin/env python3
"""Regression suite for measure_gate_baseline.py.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_measure_gate_baseline.py

  tadw-lc9 criterion                                Pinned by
  ------------------------------------------------------------------------------
  2. The baseline procedure records check-process   case_records_process_counts_and_elapsed_time
     counts and elapsed time
  Warmup runs are discarded                         case_warmup_runs_are_not_recorded
  A failing command is reported, not hidden         case_failing_command_exits_1
  Operator error is 2, never 1                      case_bad_run_count_exits_2
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "measure_gate_baseline.py"

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


def measure(command: str, *extra: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as directory:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", directory, "--tool", "python3",
             "--command", command, *extra],
            capture_output=True, text=True, check=False,
        )


def case_records_process_counts_and_elapsed_time() -> None:
    result = measure("python3 -c 'pass'; python3 -c 'pass'", "--runs", "2")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert len(report["runs"]) == 2
    for run in report["runs"]:
        assert run["processes"] == 2, f"expected 2 python3 starts, got {run['processes']}"
        assert run["by_tool"] == {"python3": 2}
        assert run["seconds"] > 0
    assert report["median_processes"] == 2 and report["median_seconds"] > 0


def case_warmup_runs_are_not_recorded() -> None:
    report = json.loads(measure("python3 -c 'pass'", "--runs", "1", "--warmup", "2").stdout)
    assert len(report["runs"]) == 1 and report["warmup"] == 2
    assert report["runs"][0]["processes"] == 1, "a warmup start leaked into the measured run"


def case_failing_command_exits_1() -> None:
    result = measure("python3 -c 'raise SystemExit(3)'", "--runs", "1")
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    assert json.loads(result.stdout)["runs"][0]["exit_code"] == 3


def case_bad_run_count_exits_2() -> None:
    result = measure("true", "--runs", "0")
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}"


for name, fn in [
    ("process counts and elapsed time are recorded", case_records_process_counts_and_elapsed_time),
    ("warmup runs are not recorded", case_warmup_runs_are_not_recorded),
    ("a failing command exits 1 with its exit code recorded", case_failing_command_exits_1),
    ("a run count of zero exits 2", case_bad_run_count_exits_2),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
