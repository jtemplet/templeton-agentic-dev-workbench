#!/usr/bin/env python3
"""Regression suite for git_process.py.

Stdlib only, no install, mirroring test_landed_check.py. Run with:
    python3 skills/ship/scripts/test_git_process.py

Every case that needs git runs it against a real repository in a temporary directory, because
the thing under test is how real git's exit codes and output reach the caller.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-vror criterion                                   Pinned by
  ------------------------------------------------------------------------------
  3. read raises GitFailed with the return code and     case_read_raises_git_failed_with_code_and_stderr
     stderr on a non-zero exit
  3. ask returns None for the same command              case_ask_returns_none_on_nonzero_exit
  4. run, read, and ask raise GitUnavailable with       case_run_raises_git_unavailable,
     no git on PATH                                     case_read_raises_git_unavailable,
                                                        case_ask_raises_git_unavailable

  tadw-aj6x criterion                                   Pinned by
  ------------------------------------------------------------------------------
  2. GitFailed and GitUnavailable share one base,       case_both_errors_share_one_base
     so one except clause names every git failure
  2. Every ship script catches the same classes         case_ship_scripts_share_one_error_module
  3. No stop-reason text changes: GitFailed keeps       case_git_failed_message_names_arguments_and_stderr
     the old `git <args>: <stderr>` message

  Design decisions in the module docstring
  ------------------------------------------------------------------------------
  run never raises on a non-zero exit                   case_run_returns_nonzero_without_raising
  Output comes back verbatim                            case_output_is_verbatim
  GitFailed carries the arguments and stdout            case_git_failed_carries_arguments_and_stdout
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "git_process.py"

spec = importlib.util.spec_from_file_location("git_process", SCRIPT)
git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(git_process)

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


@contextmanager
def repository():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        subprocess.run(["git", "-C", str(root), "init", "--quiet"], check=True)
        yield root


@contextmanager
def empty_path():
    saved = os.environ["PATH"]
    with tempfile.TemporaryDirectory() as empty:
        os.environ["PATH"] = empty
        try:
            yield Path(empty)
        finally:
            os.environ["PATH"] = saved


def raises(error_type, call) -> BaseException:
    try:
        call()
    except error_type as error:
        return error
    raise AssertionError(f"expected {error_type.__name__}, nothing was raised")


MISSING_REF = ("rev-parse", "--verify", "--quiet", "refs/heads/nope")
UNKNOWN_REVISION = ("rev-parse", "--verify", "no-such-revision")


def case_run_returns_nonzero_without_raising():
    with repository() as root:
        completed = git_process.run(root, *MISSING_REF)
    assert completed.returncode != 0, completed.returncode


def case_output_is_verbatim():
    with repository() as root:
        stdout = git_process.read(root, "rev-parse", "--show-toplevel")
    assert stdout.endswith("\n"), repr(stdout)


def case_read_raises_git_failed_with_code_and_stderr():
    with repository() as root:
        error = raises(git_process.GitFailed, lambda: git_process.read(root, *UNKNOWN_REVISION))
    assert error.returncode != 0, error.returncode
    assert error.stderr.startswith("fatal:"), repr(error.stderr)


def case_git_failed_carries_arguments_and_stdout():
    with repository() as root:
        error = raises(git_process.GitFailed, lambda: git_process.read(root, *UNKNOWN_REVISION))
    assert error.arguments == UNKNOWN_REVISION, error.arguments
    assert isinstance(error.stdout, str), type(error.stdout)


def case_git_failed_message_names_arguments_and_stderr():
    with repository() as root:
        error = raises(git_process.GitFailed, lambda: git_process.read(root, *UNKNOWN_REVISION))
    expected = f"git {' '.join(UNKNOWN_REVISION)}: {error.stderr.strip()}"
    assert str(error) == expected, str(error)


def case_both_errors_share_one_base():
    assert issubclass(git_process.GitFailed, git_process.GitProcessError)
    assert issubclass(git_process.GitUnavailable, git_process.GitProcessError)


SHARED_MODULE_PROBE = """
import importlib.util, sys
path = sys.argv[1]
spec = importlib.util.spec_from_file_location("tadw_ship", path)
tadw_ship = importlib.util.module_from_spec(spec)
sys.modules["tadw_ship"] = tadw_ship
spec.loader.exec_module(tadw_ship)
shared = tadw_ship.git_process
for name in ("resolve_ground", "candidate", "landed_check", "resolve_rebase_conflict"):
    module = sys.modules.get(name)
    assert module is not None and module.git_process is shared, name
assert tadw_ship.ship_workflow.git_process is shared
"""


def case_ship_scripts_share_one_error_module():
    script = SCRIPT.parent / "tadw_ship.py"
    completed = subprocess.run(
        [sys.executable, "-I", "-c", SHARED_MODULE_PROBE, str(script)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def case_ask_returns_none_on_nonzero_exit():
    with repository() as root:
        assert git_process.ask(root, *UNKNOWN_REVISION) is None


def case_ask_returns_stdout_on_success():
    with repository() as root:
        assert git_process.ask(root, "rev-parse", "--is-inside-work-tree") == "true\n"


def case_run_raises_git_unavailable():
    with empty_path() as root:
        raises(git_process.GitUnavailable, lambda: git_process.run(root, "status"))


def case_read_raises_git_unavailable():
    with empty_path() as root:
        raises(git_process.GitUnavailable, lambda: git_process.read(root, "status"))


def case_ask_raises_git_unavailable():
    with empty_path() as root:
        raises(git_process.GitUnavailable, lambda: git_process.ask(root, "status"))


def main() -> int:
    cases = {name: fn for name, fn in globals().items() if name.startswith("case_")}
    for name, fn in cases.items():
        check(name, fn)
    print(f"{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
