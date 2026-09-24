#!/usr/bin/env python3
"""Regression suite for tadw_ship.py, the ship runner.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_tadw_ship.py

  tadw-8j8 criterion                                Pinned by
  ------------------------------------------------------------------------------
  1. This repository's configured gate matches      case_configured_gate_matches_agents_md,
     AGENTS.md, except python3 evals/run.py         case_configured_gates_run_from_the_root,
                                                    case_repository_gate_is_valid
  2. A command override is selected                 case_override_is_selected,
                                                    case_override_outranks_configuration,
                                                    case_override_timeout_is_read
  3. Missing or invalid configuration and no        case_missing_configuration_stops,
     override stops before changing Git or          case_missing_configuration_names_the_setup,
     tracker state, and names the setup             case_missing_configuration_changes_nothing,
                                                    case_invalid_configuration_names_each_problem,
                                                    case_invalid_configuration_changes_nothing,
                                                    case_unreadable_configuration_stops,
                                                    case_blank_override_counts_as_unset,
                                                    case_invalid_override_timeout_names_its_own_fix

  tadw-7raw: ship runs its gate through the executor pre-push shares, and keeps
  its own strict policy, pinned by case_run_gate_passes_when_every_gate_passes,
  case_run_gate_stops_on_one_failed_gate, case_run_gate_stops_on_a_missing_tool,
  case_run_gate_stops_on_a_timeout, case_run_gate_runs_the_override, and
  case_run_gate_keeps_the_log_of_a_failed_gate.

  tadw-a7r criterion 5: a failed gate's full output stays in its log, and the
  runner prints only a bounded excerpt, pinned by
  case_run_gate_prints_a_bounded_excerpt and case_run_gate_log_keeps_every_line.

  tadw-kgql criterion                               Pinned by
  ------------------------------------------------------------------------------
  3. No stable checkout stops with                  case_no_stable_checkout_stops_with_git_state,
     `SHIP_BLOCKED git-state` before any Git or     case_no_stable_checkout_names_the_reason,
     tracker mutation, and names the reason         case_no_stable_checkout_changes_nothing
  4. Each installed copy loads its own helpers      case_each_copy_loads_its_own_helpers,
                                                    case_linked_executable_loads_its_own_copy
  5. `tadw-ship --help` runs with no shell, lists   case_help_runs_without_a_shell,
     every terminal flag, and no flag is called     case_help_lists_every_flag,
     provisional                                    case_no_flag_is_called_provisional

  Criteria 1 and 2 are pinned in test_worktree_cleanup.py and test_ship_report.py.
"""

from __future__ import annotations

import functools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

SCRIPT = Path(__file__).resolve().parent / "tadw_ship.py"
REPO = Path(__file__).resolve().parents[3]
EXECUTABLE = REPO / "bin" / "tadw-ship"
TERMINAL_FLAGS = ("bead-id", "--repo-root", "--check-gate", "--run-gate")
AGENTS = REPO / "AGENTS.md"
CONFIG = Path(".tadw") / "ship-gates.json"

# The one AGENTS.md command that is deliberately not a gate: ADR 0005.
NOT_A_GATE = "python3 evals/run.py"

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


def commands_in_agents_md() -> list[str]:
    """The command list from the AGENTS.md "Commands for This Repo" block."""
    section = AGENTS.read_text(encoding="utf-8").split("## Commands for This Repo", 1)[1]
    block = re.search(r"```bash\n(.*?)```", section, re.S)
    assert block, "AGENTS.md must carry a bash block under Commands for This Repo"
    lines = (line.split("#", 1)[0].strip() for line in block.group(1).splitlines())
    return [line for line in lines if line]


def run(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("TADW_SHIP_CHECK")
    }
    environment.update(env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def run_in_empty_repo(
    *args: str, env: dict[str, str] | None = None, config: object = None
) -> subprocess.CompletedProcess:
    """Run the runner in a fresh directory, holding `config` as its gate file when given."""
    with tempfile.TemporaryDirectory() as directory:
        if config is not None:
            write_config(Path(directory), config)
        return run(Path(directory), *args, env=env)


def write_config(repo: Path, document: object) -> None:
    (repo / CONFIG).parent.mkdir(exist_ok=True)
    (repo / CONFIG).write_text(json.dumps(document), encoding="utf-8")


def valid_config() -> dict:
    return {"version": 1, "gates": [{"name": "suite", "command": ["python3", "-c", "pass"]}]}


def no_configuration(repo: Path) -> None:
    pass


def invalid_configuration(repo: Path) -> None:
    write_config(repo, {"version": 2, "gates": []})


def unreadable_configuration(repo: Path) -> None:
    (repo / CONFIG).parent.mkdir()
    (repo / CONFIG).write_text("{not json", encoding="utf-8")


class Fixture:
    """A git repository, with `git` and `bd` on PATH wrapped to log every call."""

    def __init__(self, root: Path) -> None:
        self.repo = root / "repo"
        self.log = root / "calls.log"
        self.shims = root / "shims"
        self.shims.mkdir()
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
                 "-m", "base")  # fmt: skip
        self.shim("git", shutil.which("git"))
        self.shim("bd", None)

    def shim(self, tool: str, real: str | None) -> None:
        target = f'exec "{real}" "$@"' if real else "exit 0"
        path = self.shims / tool
        path.write_text(f'#!/bin/sh\necho "{tool} $*" >> "{self.log}"\n{target}\n')
        path.chmod(0o755)

    def state(self) -> str:
        """The refs and the working-tree status, read with the real git, not the shim."""
        refs = self.git("for-each-ref", "--format=%(refname) %(objectname)")
        return refs + self.git("status", "--porcelain")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=True
        ).stdout

    def start(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        path = {"PATH": f"{self.shims}{os.pathsep}{os.environ['PATH']}"}
        return run(self.repo, *args, env={**path, **(env or {})})

    def calls(self) -> str:
        return self.log.read_text() if self.log.exists() else ""


class Stop:
    """Both entry points, the real start and --check-gate, run once in one fixture."""

    def __init__(self, prepare, env: dict[str, str] | None = None) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            prepare(fixture.repo)
            before = fixture.state()
            self.results = [fixture.start(*args, env=env) for args in ((), ("--check-gate",))]
            self.calls = fixture.calls()
            self.state_changed = fixture.state() != before

    def assert_blocked(self) -> None:
        for result in self.results:
            assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
            assert result.stdout.splitlines()[-1] == "SHIP_BLOCKED gate", result.stdout

    def assert_said(self, text: str) -> None:
        for result in self.results:
            assert text in result.stderr, f"expected {text!r} in:\n{result.stderr}"

    def assert_changed_nothing(self) -> None:
        assert self.calls == "", f"no git or bd call may run before the gate:\n{self.calls}"
        assert not self.state_changed, "the refs or the working tree changed"


def case_configured_gate_matches_agents_md() -> None:
    result = run(REPO, "--check-gate")
    assert result.returncode == 0, result.stderr
    selected = json.loads(result.stdout)
    assert selected["source"] == str(CONFIG), f"expected the file, got {selected['source']}"
    listed = commands_in_agents_md()
    assert NOT_A_GATE in listed, "the eval exclusion is stale"
    configured = [shlex.join(gate["command"]) for gate in selected["gates"]]
    documented = [command for command in listed if command != NOT_A_GATE]
    assert configured == documented, (
        "the gates must be the AGENTS.md list, one for one and in its order\n"
        f"         only in the configuration: {sorted(set(configured) - set(documented))}\n"
        f"         only in AGENTS.md: {sorted(set(documented) - set(configured))}"
    )


def case_configured_gates_run_from_the_root() -> None:
    gates = json.loads(run(REPO, "--check-gate").stdout)["gates"]
    elsewhere = [gate["name"] for gate in gates if gate["cwd"] != "."]
    assert not elsewhere, f"AGENTS.md runs every command from the root, but not: {elsewhere}"


def case_repository_gate_is_valid() -> None:
    reader = SCRIPT.parent / "read_gate_config.py"
    result = subprocess.run(
        [sys.executable, str(reader), "--repo-root", str(REPO)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def case_override_is_selected() -> None:
    result = run_in_empty_repo("--check-gate", env={"TADW_SHIP_CHECK": "make check"})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "source": "TADW_SHIP_CHECK",
        "command": "make check",
        "timeout": 900,
    }


def case_override_outranks_configuration() -> None:
    result = run_in_empty_repo(
        "--check-gate", env={"TADW_SHIP_CHECK": "make check"}, config=valid_config()
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["source"] == "TADW_SHIP_CHECK"


def case_override_timeout_is_read() -> None:
    result = run_in_empty_repo(
        "--check-gate", env={"TADW_SHIP_CHECK": "make check", "TADW_SHIP_CHECK_TIMEOUT": "60"}
    )
    assert json.loads(result.stdout)["timeout"] == 60, result.stdout


def case_missing_configuration_stops() -> None:
    Stop(no_configuration).assert_blocked()


def case_missing_configuration_names_the_setup() -> None:
    stop = Stop(no_configuration)
    for setup in ("TADW_SHIP_CHECK", ".tadw/ship-gates.json"):
        stop.assert_said(setup)


def case_missing_configuration_changes_nothing() -> None:
    Stop(no_configuration).assert_changed_nothing()


def case_invalid_configuration_names_each_problem() -> None:
    stop = Stop(invalid_configuration)
    stop.assert_blocked()
    for problem in ("version must be 1", "gates must be a non-empty list"):
        stop.assert_said(problem)


def case_invalid_configuration_changes_nothing() -> None:
    Stop(invalid_configuration).assert_changed_nothing()


def case_unreadable_configuration_stops() -> None:
    stop = Stop(unreadable_configuration)
    stop.assert_blocked()
    stop.assert_said("could not be read as JSON")


def case_blank_override_counts_as_unset() -> None:
    stop = Stop(no_configuration, env={"TADW_SHIP_CHECK": "  "})
    stop.assert_blocked()
    stop.assert_said("no gate configuration")


def case_invalid_override_timeout_names_its_own_fix() -> None:
    stop = Stop(
        no_configuration,
        env={"TADW_SHIP_CHECK": "make check", "TADW_SHIP_CHECK_TIMEOUT": "soon"},
    )
    stop.assert_blocked()
    stop.assert_said("Set TADW_SHIP_CHECK_TIMEOUT to a positive whole number")
    for result in stop.results:
        assert ".tadw/ship-gates.json" not in result.stderr, "the override is set already"


def case_missing_repository_is_operator_error() -> None:
    with tempfile.TemporaryDirectory() as directory:
        result = run(Path(directory) / "absent", "--check-gate")
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}"


def case_start_without_check_gate_does_not_claim_a_ship() -> None:
    with tempfile.TemporaryDirectory() as directory:
        fixture = Fixture(Path(directory))
        write_config(fixture.repo, valid_config())
        result = fixture.start()
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}"
    assert "SHIP_DONE" not in result.stdout, result.stdout


def case_bead_with_a_gate_flag_is_operator_error() -> None:
    result = run_in_empty_repo("tadw-kgql", "--check-gate", config=valid_config())
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}"


@functools.cache
def bare_start() -> StartFromBareLinkedWorktree:
    return StartFromBareLinkedWorktree()


class StartFromBareLinkedWorktree:
    """A start from a linked worktree of a bare repository, which has no main checkout."""

    def __init__(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            bare = Path(directory) / "bare.git"
            subprocess.run(["git", "clone", "-q", "--bare", str(fixture.repo), str(bare)],
                           check=True)  # fmt: skip
            fixture.repo = Path(directory) / "linked"
            subprocess.run(
                ["git", "-C", str(bare), "worktree", "add", "-q", str(fixture.repo), "main"],
                check=True,
            )
            before = fixture.state()
            self.result = fixture.start(env={"TADW_SHIP_CHECK": "true"})
            self.state_changed = fixture.state() != before
            self.bd_calls = [
                line for line in fixture.calls().splitlines() if line.startswith("bd ")
            ]


def case_no_stable_checkout_stops_with_git_state() -> None:
    result = bare_start().result
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    assert result.stdout.splitlines()[-1] == "SHIP_BLOCKED git-state", result.stdout


def case_no_stable_checkout_names_the_reason() -> None:
    result = bare_start().result
    assert "is bare" in result.stderr, result.stderr


def case_no_stable_checkout_changes_nothing() -> None:
    stop = bare_start()
    assert not stop.state_changed, "the refs or the working tree changed"
    assert not stop.bd_calls, (
        f"no bd call may run before the stable checkout is known: {stop.bd_calls}"
    )


@functools.cache
def help_run() -> subprocess.CompletedProcess:
    """Run the executable file itself, with no shell and no interpreter named."""
    return subprocess.run([str(EXECUTABLE), "--help"], capture_output=True, text=True, check=False)


def case_help_runs_without_a_shell() -> None:
    result = help_run()
    assert result.returncode == 0, result.stderr


def case_help_lists_every_flag() -> None:
    usage = help_run().stdout
    missing = [flag for flag in TERMINAL_FLAGS if flag not in usage]
    assert not missing, f"--help does not list {missing}:\n{usage}"


def case_no_flag_is_called_provisional() -> None:
    assert "provisional" not in SCRIPT.read_text(encoding="utf-8").lower()


class PluginCopy(NamedTuple):
    """One installed copy of the plugin, laid out as the plugin lays itself out."""

    executable: Path
    scripts: Path


def install_copy(root: Path) -> PluginCopy:
    copy = PluginCopy(root / "bin" / "tadw-ship", root / "skills" / "ship" / "scripts")
    copy.executable.parent.mkdir(parents=True)
    shutil.copy2(EXECUTABLE, copy.executable)
    copy.scripts.mkdir(parents=True)
    for helper in SCRIPT.parent.glob("*.py"):
        shutil.copy2(helper, copy.scripts / helper.name)
    return copy


def poison(copy: PluginCopy) -> None:
    """Make every script in `copy` stop the process the moment it is loaded."""
    for helper in copy.scripts.glob("*.py"):
        helper.write_text('raise SystemExit("loaded from the poisoned copy")\n')


class CopyRuns(NamedTuple):
    """`--check-gate` run through copy A, copy B, and a link to copy A."""

    sound: subprocess.CompletedProcess
    poisoned: subprocess.CompletedProcess
    linked: subprocess.CompletedProcess


@functools.cache
def copy_runs() -> CopyRuns:
    """Copy A is sound; copy B is poisoned and sits on PYTHONPATH and in the working directory."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        sound = install_copy(root / "a")
        poisoned = install_copy(root / "b")
        poison(poisoned)
        link = poisoned.executable.parent / "tadw-ship-link"
        link.symlink_to(sound.executable)
        repo = root / "repo"
        repo.mkdir()
        write_config(repo, valid_config())

        def check_gate(executable: Path) -> subprocess.CompletedProcess:
            return subprocess.run(
                [str(executable), "--repo-root", str(repo), "--check-gate"],
                capture_output=True,
                text=True,
                check=False,
                cwd=poisoned.scripts,
                env={**os.environ, "PYTHONPATH": str(poisoned.scripts)},
            )

        return CopyRuns(
            *(check_gate(path) for path in (sound.executable, poisoned.executable, link))
        )


def case_each_copy_loads_its_own_helpers() -> None:
    runs = copy_runs()
    assert "poisoned" in runs.poisoned.stderr, "the poisoned copy must fail, or this proves nothing"
    assert runs.sound.returncode == 0, f"copy A loaded a helper from copy B:\n{runs.sound.stderr}"


def case_linked_executable_loads_its_own_copy() -> None:
    result = copy_runs().linked
    assert result.returncode == 0, f"the link did not run copy A's helpers:\n{result.stderr}"


def gate_config(*gates: dict) -> dict:
    return {"version": 1, "gates": list(gates)}


def python_gate(name: str, body: str, **options) -> dict:
    return {"name": name, "command": [sys.executable, "-c", body], **options}


def assert_ship_stopped(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}: {result.stderr}"
    assert result.stdout.splitlines()[-1] == "SHIP_BLOCKED gate", result.stdout


def case_run_gate_passes_when_every_gate_passes() -> None:
    config = gate_config(python_gate("one", "pass"), python_gate("two", "pass"))
    result = run_in_empty_repo("--run-gate", config=config)
    assert result.returncode == 0, f"every gate passed, so the run continues: {result.stderr}"
    assert "2 of 2" in result.stdout, result.stdout


def case_run_gate_stops_on_one_failed_gate() -> None:
    config = gate_config(python_gate("good", "pass"), python_gate("bad", "raise SystemExit(3)"))
    result = run_in_empty_repo("--run-gate", config=config)
    assert_ship_stopped(result)
    assert "failed bad" in result.stderr, f"the failed gate must be named: {result.stderr}"


def case_run_gate_stops_on_a_missing_tool() -> None:
    config = gate_config({"name": "absent", "command": ["tadw-no-such-tool"]})
    result = run_in_empty_repo("--run-gate", config=config)
    assert_ship_stopped(result)


def case_run_gate_stops_on_a_timeout() -> None:
    config = gate_config(python_gate("slow", "import time; time.sleep(60)", timeout=1))
    result = run_in_empty_repo("--run-gate", config=config)
    assert_ship_stopped(result)
    assert "timed_out slow" in result.stderr, f"the timeout must be named: {result.stderr}"


def case_run_gate_keeps_the_log_of_a_failed_gate() -> None:
    config = gate_config(python_gate("bad", "print('the gate said why'); raise SystemExit(1)"))
    result = run_in_empty_repo("--run-gate", config=config)
    logged = re.search(r"\(log: (.+)\)", result.stderr)
    assert logged, f"the failed gate must name its log: {result.stderr}"
    log = Path(logged.group(1))
    assert "the gate said why" in log.read_text(), f"the log must hold the gate's output: {log}"
    shutil.rmtree(log.parent, ignore_errors=True)


NOISY_GATE = "for n in range(500): print(f'noise {n}')\nraise SystemExit(1)"


def case_run_gate_prints_a_bounded_excerpt() -> None:
    result = run_in_empty_repo("--run-gate", config=gate_config(python_gate("noisy", NOISY_GATE)))
    shutil.rmtree(Path(re.search(r"\(log: (.+)\)", result.stderr).group(1)).parent)
    shown = ("noise 0\n" in result.stderr, "noise 499" in result.stderr)
    assert shown == (False, True), f"expected only the tail of the output: {shown}"


def case_run_gate_log_keeps_every_line() -> None:
    result = run_in_empty_repo("--run-gate", config=gate_config(python_gate("noisy", NOISY_GATE)))
    log = Path(re.search(r"\(log: (.+)\)", result.stderr).group(1))
    assert "noise 0\n" in log.read_text(), f"the log must keep every line: {log}"
    shutil.rmtree(log.parent, ignore_errors=True)


def case_run_gate_runs_the_override() -> None:
    result = run_in_empty_repo("--run-gate", env={"TADW_SHIP_CHECK": "exit 4"})
    assert_ship_stopped(result)
    assert "failed TADW_SHIP_CHECK" in result.stderr, result.stderr


for name, fn in [
    ("the gates are the AGENTS.md list, in order, except the model eval",
     case_configured_gate_matches_agents_md),
    ("every configured gate runs from the repository root",
     case_configured_gates_run_from_the_root),
    ("this repository's gate configuration is valid", case_repository_gate_is_valid),
    ("a command override is selected", case_override_is_selected),
    ("the override outranks the configuration file", case_override_outranks_configuration),
    ("the override timeout is read", case_override_timeout_is_read),
    ("missing configuration stops the run", case_missing_configuration_stops),
    ("missing configuration names the setup", case_missing_configuration_names_the_setup),
    ("missing configuration changes nothing", case_missing_configuration_changes_nothing),
    ("invalid configuration names each problem", case_invalid_configuration_names_each_problem),
    ("invalid configuration changes nothing", case_invalid_configuration_changes_nothing),
    ("unreadable configuration stops", case_unreadable_configuration_stops),
    ("a blank override counts as unset", case_blank_override_counts_as_unset),
    ("an invalid override timeout names its own fix",
     case_invalid_override_timeout_names_its_own_fix),
    ("a missing repository is operator error, not a ship stop",
     case_missing_repository_is_operator_error),
    ("a start without --check-gate does not claim a ship",
     case_start_without_check_gate_does_not_claim_a_ship),
    ("a bead-id with a gate flag is operator error", case_bead_with_a_gate_flag_is_operator_error),
    ("no stable checkout stops with git-state", case_no_stable_checkout_stops_with_git_state),
    ("no stable checkout names the reason", case_no_stable_checkout_names_the_reason),
    ("no stable checkout changes nothing", case_no_stable_checkout_changes_nothing),
    ("--help runs without a shell", case_help_runs_without_a_shell),
    ("--help lists every terminal flag", case_help_lists_every_flag),
    ("no flag is called provisional", case_no_flag_is_called_provisional),
    ("each installed copy loads its own helpers", case_each_copy_loads_its_own_helpers),
    ("a linked executable loads its own copy", case_linked_executable_loads_its_own_copy),
    ("--run-gate passes when every gate passes", case_run_gate_passes_when_every_gate_passes),
    ("--run-gate stops on one failed gate", case_run_gate_stops_on_one_failed_gate),
    ("--run-gate stops on a missing tool, never skips it", case_run_gate_stops_on_a_missing_tool),
    ("--run-gate stops on a timeout", case_run_gate_stops_on_a_timeout),
    ("--run-gate runs the override through a shell", case_run_gate_runs_the_override),
    ("--run-gate keeps the log of a failed gate", case_run_gate_keeps_the_log_of_a_failed_gate),
    ("--run-gate prints a bounded excerpt of a failure", case_run_gate_prints_a_bounded_excerpt),
    ("--run-gate keeps every line of a failure in its log", case_run_gate_log_keeps_every_line),
]:  # fmt: skip
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
