#!/usr/bin/env python3
"""Regression suite for tadw_ship.py, the ship runner.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_tadw_ship.py

  tadw-8j8 criterion                                Pinned by
  ------------------------------------------------------------------------------
  1. This repository's configured gate matches      case_configured_gate_matches_agents_md,
     AGENTS.md                                      case_configured_gates_run_from_the_root,
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

  tadw-0jz2 criterion                               Pinned by, all through bin/tadw-ship
  ------------------------------------------------------------------------------
  1. Exit 0 with `SHIP_DONE <hash>` or 1 with       case_ship_exits_0_with_ship_done_last,
     `SHIP_BLOCKED <slug>` as the last line         case_stop_exits_1_with_ship_blocked_last
  2. The default branch carries the landing commit;  case_default_branch_carries_the_shipped_commit,
     the report names its checked code commit,      case_gated_commit_is_the_shipped_commit,
     and the bead closes and is pushed              case_shipped_commit_is_pushed,
                                                    case_ship_closes_the_bead,
                                                    case_ship_removes_the_worktree_and_branch
  3. A caller inside the removed worktree gets      case_caller_in_removed_worktree_gets_cd_line,
     `cd <stable-path>` before the machine line     case_cd_line_sits_above_the_machine_line
  4. A caller outside it gets no `cd` line          case_caller_outside_removed_worktree_gets_no_cd_line
  5. A failing gate ends `SHIP_BLOCKED gate` and    case_failing_gate_ends_with_ship_blocked_gate,
     leaves the default branch unchanged            case_failing_gate_leaves_the_default_branch_unchanged,
                                                    case_failing_gate_leaves_the_bead_open

  tadw-awsr criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. With no override and no file, an executable    case_pre_push_hook_is_selected,
     pre-push hook is the gate                      case_ship_gates_on_the_pre_push_hook,
                                                    case_configuration_outranks_the_hooks
  2. The gate checks code and the push carries the   case_pre_push_gate_checks_code_and_push_carries_landing_commit,
     landing commit                                  case_run_gate_feeds_the_pre_push_hook_a_push_of_head
  3. A failing hook ends `SHIP_BLOCKED gate` with   case_failing_pre_push_hook_ends_with_ship_blocked_gate,
     the default branch unchanged                   case_run_gate_stops_on_a_failing_pre_push_hook
  4. core.hooksPath is honored                      case_hooks_path_is_honored
  5. Without a pre-push hook, the pre-commit hook   case_pre_commit_hook_is_selected_without_a_pre_push_hook,
     is the gate, and a refused commit stops        case_pre_commit_hook_is_the_gate_without_a_pre_push_hook,
                                                    case_refused_candidate_commit_ends_with_ship_blocked_gate
  6. With no hook, the run stops, names adding a    case_no_hook_names_adding_a_pre_push_hook,
     pre-push hook, and changes nothing             case_non_executable_hook_is_not_a_gate,
                                                    case_missing_configuration_changes_nothing

  tadw-lndi criterion                               Pinned by, all through bin/tadw-ship
  ------------------------------------------------------------------------------
  1. A main checkout dirty only in the export       case_rewritten_export_in_main_still_ships
     ends SHIP_DONE with the candidate landed
  2. Any other changed tracked file ends            case_another_changed_file_in_main_stops_with_git_state
     SHIP_BLOCKED git-state, main unchanged
  3. The output says the export was restored        test_candidate.py: git ignores the export,
                                                    so no run through the executable restores it

  tadw-8tax criterion                               Pinned by, all through bin/tadw-ship
  ------------------------------------------------------------------------------
  1. Staged and unstaged changes in main are        case_dirty_main_ships_and_gets_its_changes_back
     stashed, the ship lands, and the changes
     come back with the staged state kept
  2. The tracker export is never stashed           case_stale_export_stays_out_of_the_stash
  3. A failed ship restores them too                case_blocked_ship_still_restores_main_changes
  4. A restore that conflicts warns, keeps the      case_conflicting_restore_keeps_the_stash
     stash, and does not undo the landing

  tadw-8vnh criterion                               Pinned by, all through bin/tadw-ship
  ------------------------------------------------------------------------------
  1. Superseded by tadw-o3ar criterion 3
  2. A failed gate leaves the bead open; a moved     case_failing_gate_leaves_the_bead_open,
     default branch reopens it                       case_default_branch_moves_after_close_reopens_the_bead
  3. The pre-commit hook runs once                   case_pre_commit_hook_is_the_gate_without_a_pre_push_hook
  4. The real-bd test leaves a clean checkout        test_ship_with_real_bd.py

  tadw-o3ar criterion                               Pinned by, all through bin/tadw-ship
  ------------------------------------------------------------------------------
  1. A bead ships from a repository that ignores    case_ship_exits_0_with_ship_done_last
     the export                                     (every fixture here ignores it)
  3. The gated commit is the shipped commit          case_gated_commit_is_the_shipped_commit,
                                                    case_pre_push_gate_checks_code_and_push_carries_landing_commit
  7. A failed export after the close warns, and     case_failed_export_still_ships,
     the run still ends SHIP_DONE                   case_failed_export_warns
  9. The `tracker` stop slug does not name          case_tracker_slug_does_not_name_the_export
     `bd export`

  A ship with no bead runs no export, pinned by case_bead_free_ship_runs_no_export.

  Criteria 2, 4, and 5 are pinned in test_candidate.py, and 6 in test_ship_recovery.py.
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

READ_ONLY_CALL = re.compile(r"git -C \S+ rev-parse ")

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
        """Finding the hooks reads with `git rev-parse`; nothing else may run before the gate."""
        other = [call for call in self.calls.splitlines() if not READ_ONLY_CALL.match(call)]
        assert not other, f"no git or bd call may run before the gate:\n{other}"
        assert not self.state_changed, "the refs or the working tree changed"


def case_configured_gate_matches_agents_md() -> None:
    result = run(REPO, "--check-gate")
    assert result.returncode == 0, result.stderr
    selected = json.loads(result.stdout)
    assert selected["source"] == str(CONFIG), f"expected the file, got {selected['source']}"
    documented = commands_in_agents_md()
    configured = [shlex.join(gate["command"]) for gate in selected["gates"]]
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
    selected = json.loads(result.stdout)
    assert selected["source"] == "TADW_SHIP_CHECK", selected
    assert [gate["command"] for gate in selected["gates"]] == [["sh", "-c", "make check"]]
    assert selected["gates"][0]["timeout"] == 900, selected


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
    assert json.loads(result.stdout)["gates"][0]["timeout"] == 60, result.stdout


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


def rejected_override_timeout(value: str) -> None:
    result = run_in_empty_repo(
        "--check-gate", env={"TADW_SHIP_CHECK": "make check", "TADW_SHIP_CHECK_TIMEOUT": value}
    )
    assert_ship_stopped(result)
    assert "positive whole number" in result.stderr, result.stderr


def case_zero_override_timeout_is_rejected() -> None:
    rejected_override_timeout("0")


def case_negative_override_timeout_is_rejected() -> None:
    rejected_override_timeout("-5")


def case_signed_override_timeout_is_rejected() -> None:
    rejected_override_timeout("+60")


def case_missing_repository_is_operator_error() -> None:
    with tempfile.TemporaryDirectory() as directory:
        result = run(Path(directory) / "absent", "--check-gate")
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}"


def case_start_on_the_default_branch_stops_with_git_state() -> None:
    with tempfile.TemporaryDirectory() as directory:
        fixture = Fixture(Path(directory))
        write_config(fixture.repo, valid_config())
        result = fixture.start()
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    assert result.stdout.splitlines()[-1] == "SHIP_BLOCKED git-state", result.stdout


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


BEAD = "tadw-e2e"
BRANCH = f"feature/{BEAD}/add-thing"
# A tracker holding one bead, whose status lives in a file beside the script.
FAKE_BD = """#!/bin/sh
status="$(dirname "$0")/status"
root="$(cd "$(dirname "$0")/.." && pwd)"
case "$1" in
  show)
    if [ "$2" = "BEAD" ]; then
      printf '[{"id":"BEAD","title":"Add the thing","issue_type":"feature","status":"%s"}]' "$(cat "$status")"
    else
      printf '{"error":"no issue found"}'
    fi ;;
  close)
    echo closed > "$status"
    printf '{"id":"BEAD","status":"%s"}\\n' "$(cat "$status")" > "$root/main/.beads/issues.jsonl"
    if [ -f "$(dirname "$0")/move-main" ]; then
      printf 'concurrent\\n' > "$root/main/concurrent.txt"
      git -C "$root/main" add concurrent.txt
      git -C "$root/main" commit -q -m "concurrent landing"
    fi
    ;;
  reopen)
    echo open > "$status"
    printf '{"id":"BEAD","status":"%s"}\\n' "$(cat "$status")" > "$root/main/.beads/issues.jsonl"
    ;;
  export)
    echo "$3" >> "$(dirname "$0")/exports.log"
    if [ -f "$(dirname "$0")/export-fails" ]; then
      echo "export refused" >&2; exit 1
    fi
    mkdir -p "$(dirname "$3")"
    printf '{"id":"BEAD","status":"%s"}\\n' "$(cat "$status")" > "$3"
    ;;
  ready) printf '[]' ;;
esac
""".replace("BEAD", BEAD)


class ShipRun(NamedTuple):
    """One `tadw-ship <bead-id>` run through the executable, and the state it left."""

    result: subprocess.CompletedProcess
    main: Path
    default_before: str
    default_after: str
    origin_after: str
    bead_status: str
    worktree_removed: bool
    branch_deleted: bool
    pushes: str = ""
    pre_commit_calls: str = ""

    def last_line(self) -> str:
        return self.result.stdout.splitlines()[-1]

    def shipped_hash(self) -> str:
        return self.last_line().removeprefix("SHIP_DONE ")

    def cd_lines(self) -> list[str]:
        return [line for line in self.result.stdout.splitlines() if line.startswith("cd ")]


class ShipRepository:
    """A main checkout with an origin, and a linked worktree whose branch adds one file.

    Git ignores the tracker export, and the main checkout holds one on disk.
    """

    def __init__(self, root: Path, branch: str = BRANCH) -> None:
        self.main = root / "main"
        self.worktree = root / "worktrees" / "add-thing"
        self.shims = root / "shims"
        self.create_main(root / "origin.git")
        self.git("worktree", "add", "-q", "-b", branch, str(self.worktree), "main")
        (self.worktree / "thing.txt").write_text("the thing\n")
        self.git("-C", str(self.worktree), "add", "thing.txt")
        self.git("-C", str(self.worktree), "commit", "-q", "-m", "Add the thing")
        self.install_bd()

    def create_main(self, origin: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.main)], check=True)
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@t")
        (self.main / ".beads").mkdir()
        (self.main / ".beads" / "issues.jsonl").write_text("{}\n")
        (self.main / ".gitignore").write_text(".beads/issues.jsonl\n")
        (self.main / "base.txt").write_text("base\n")
        self.git("add", ".gitignore", "base.txt")
        self.git("commit", "-q", "-m", "base")
        self.git("remote", "add", "origin", str(origin))
        self.git("push", "-q", "-u", "origin", "main")

    def install_bd(self) -> None:
        self.shims.mkdir()
        (self.shims / "status").write_text("open\n")
        (self.shims / "bd").write_text(FAKE_BD)
        (self.shims / "bd").chmod(0o755)

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.main), *args], capture_output=True, text=True, check=True
        )
        return completed.stdout.strip()

    def install_hook(self, name: str, body: str) -> None:
        hook = self.main / ".git" / "hooks" / name
        hook.write_text(f"#!/bin/sh\n{body}\n")
        hook.chmod(0o755)

    def ship(
        self, gate: str | None, cwd: Path, bead: str | None = BEAD
    ) -> subprocess.CompletedProcess:
        """A `gate` of None leaves TADW_SHIP_CHECK unset, so the hooks are the gate.

        A `bead` of None names no bead, so the runner takes one from the branch name.
        """
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith("TADW_SHIP")
        }
        environment["PATH"] = f"{self.shims}{os.pathsep}{os.environ['PATH']}"
        if gate is not None:
            environment["TADW_SHIP_CHECK"] = gate
        return subprocess.run(
            [str(EXECUTABLE), *([] if bead is None else [bead]), "--repo-root", str(self.worktree)],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            env=environment,
        )

    def exports(self) -> str:
        """Each path the fake `bd` was asked to export to, one per line."""
        return read_if_present(self.shims / "exports.log")


@functools.cache
def ship_run(
    gate: str | None,
    start_in_worktree: bool,
    hooks: tuple[tuple[str, str], ...] = (),
    bd_flags: tuple[str, ...] = (),
) -> ShipRun:
    """Each name in `bd_flags` is a file the fake `bd` reads: `move-main` or `export-fails`."""
    with tempfile.TemporaryDirectory() as directory:
        repository = ShipRepository(Path(directory).resolve())
        for flag in bd_flags:
            (repository.shims / flag).touch()
        for name, body in hooks:
            repository.install_hook(name, body.replace("{root}", directory))
        before = repository.git("rev-parse", "main")
        start = repository.worktree if start_in_worktree else repository.main
        result = repository.ship(gate, start)
        remove_kept_gate_logs(result.stderr)
        return ShipRun(
            result=result,
            main=repository.main,
            default_before=before,
            default_after=repository.git("rev-parse", "main"),
            origin_after=repository.git("rev-parse", "origin/main"),
            bead_status=(repository.shims / "status").read_text().strip(),
            worktree_removed=not repository.worktree.exists(),
            branch_deleted=not repository.git("branch", "--list", BRANCH),
            pushes=read_if_present(Path(directory) / "pushes.log"),
            pre_commit_calls=read_if_present(Path(directory) / "pre-commit.log"),
        )


def read_if_present(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def remove_kept_gate_logs(stderr: str) -> None:
    """A failed gate keeps its logs for the operator; a test has no operator to read them."""
    for log in re.findall(r"\(log: (.+)\)", stderr):
        shutil.rmtree(Path(log).parent, ignore_errors=True)


def shipped_from_worktree() -> ShipRun:
    return ship_run("true", start_in_worktree=True)


def shipped_from_main() -> ShipRun:
    return ship_run("true", start_in_worktree=False)


def blocked_by_gate() -> ShipRun:
    return ship_run("false", start_in_worktree=True)


def case_ship_exits_0_with_ship_done_last() -> None:
    run = shipped_from_worktree()
    assert run.result.returncode == 0, f"expected exit 0:\n{run.result.stderr}"
    assert re.fullmatch(r"SHIP_DONE [0-9a-f]{40}", run.last_line()), run.result.stdout


def case_stop_exits_1_with_ship_blocked_last() -> None:
    run = blocked_by_gate()
    assert run.result.returncode == 1, f"expected exit 1:\n{run.result.stderr}"
    assert re.fullmatch(r"SHIP_BLOCKED [a-z-]+", run.last_line()), run.result.stdout


def case_default_branch_carries_the_shipped_commit() -> None:
    run = shipped_from_worktree()
    assert run.default_after == run.shipped_hash(), run.result.stdout


def case_gated_commit_is_the_shipped_commit() -> None:
    run = shipped_from_worktree()
    checked = re.search(r"checked candidate ([0-9a-f]{12})", run.result.stderr)
    assert checked, run.result.stderr
    assert checked.group(1) == run.shipped_hash()[:12], run.result.stderr


def case_shipped_commit_is_pushed() -> None:
    run = shipped_from_worktree()
    assert run.origin_after == run.shipped_hash(), "origin/main must carry the landed commit"


def case_ship_closes_the_bead() -> None:
    assert shipped_from_worktree().bead_status == "closed"


def case_ship_removes_the_worktree_and_branch() -> None:
    run = shipped_from_worktree()
    assert (run.worktree_removed, run.branch_deleted) == (True, True), run.result.stderr


def case_caller_in_removed_worktree_gets_cd_line() -> None:
    run = shipped_from_worktree()
    assert run.cd_lines() == [f"cd {shlex.quote(str(run.main))}"], run.result.stdout


def case_cd_line_sits_above_the_machine_line() -> None:
    lines = shipped_from_worktree().result.stdout.splitlines()
    assert lines[-2].startswith("cd "), lines


def case_caller_outside_removed_worktree_gets_no_cd_line() -> None:
    run = shipped_from_main()
    assert run.result.returncode == 0, run.result.stderr
    assert run.cd_lines() == [], run.result.stdout


def case_failing_gate_ends_with_ship_blocked_gate() -> None:
    assert blocked_by_gate().last_line() == "SHIP_BLOCKED gate"


def case_failing_gate_leaves_the_default_branch_unchanged() -> None:
    run = blocked_by_gate()
    assert run.default_after == run.default_before, "the default branch moved on a failed gate"


def case_failing_gate_leaves_the_bead_open() -> None:
    assert blocked_by_gate().bead_status == "open"


def case_default_branch_moves_after_close_reopens_the_bead() -> None:
    run = ship_run("true", True, bd_flags=("move-main",))
    assert run.last_line() == "SHIP_BLOCKED git-state", run.result.stdout
    assert run.bead_status == "open", run.bead_status
    assert run.default_after != run.default_before, "the fixture did not move main"
    assert run.origin_after == run.default_before, "ship pushed the concurrent landing"


def shipped_with_a_failing_export() -> ShipRun:
    return ship_run("true", True, bd_flags=("export-fails",))


BEAD_FREE_BRANCH = "chore/tidy-up"


@functools.cache
def bead_free_ship() -> tuple[subprocess.CompletedProcess, str]:
    """Ship a branch that names no bead; return the result and the exports the fake `bd` ran."""
    with tempfile.TemporaryDirectory() as directory:
        repository = ShipRepository(Path(directory).resolve(), BEAD_FREE_BRANCH)
        result = repository.ship("true", repository.worktree, bead=None)
        return result, repository.exports()


def case_bead_free_ship_runs_no_export() -> None:
    result, exports = bead_free_ship()
    assert result.returncode == 0 and "bead-free ship" in result.stderr, result.stderr
    assert exports == "", exports


def case_failed_export_still_ships() -> None:
    run = shipped_with_a_failing_export()
    assert re.fullmatch(r"SHIP_DONE [0-9a-f]{40}", run.last_line()), run.result.stderr


def case_failed_export_warns() -> None:
    stderr = shipped_with_a_failing_export().result.stderr
    assert "warning: bd export could not regenerate" in stderr, stderr


# tadw-awsr: with no override and no configuration file, the repository's own
# hooks are the gate. Each hook body may write to {root}, the fixture's directory.
LOGGING_PRE_PUSH = 'printf "%s " "$1" >> "{root}/pushes.log"; cat >> "{root}/pushes.log"'
PASSING_PRE_PUSH = (("pre-push", LOGGING_PRE_PUSH),)
FAILING_PRE_PUSH = (("pre-push", f"{LOGGING_PRE_PUSH}; exit 1"),)
FAILING_PRE_COMMIT = (("pre-commit", "echo 'lint failed' >&2; exit 1"),)


def shipped_through_pre_push() -> ShipRun:
    return ship_run(None, True, PASSING_PRE_PUSH)


# tadw-lndi: `bd` auto-export rewrites the main checkout's export from any worktree.
# Git ignores the export, so only the other file the hook edits dirties the checkout.
REWRITE_MAIN_EXPORT = "printf 'rewritten by bd\\n' > {root}/main/.beads/issues.jsonl"
EXPORT_REWRITTEN_IN_MAIN = (("pre-commit", REWRITE_MAIN_EXPORT),)
EXPORT_AND_SOURCE_DIRTY_IN_MAIN = (
    ("pre-commit", f"{REWRITE_MAIN_EXPORT}; printf 'edit\\n' > {{root}}/main/base.txt"),
)


def shipped_over_a_rewritten_export() -> ShipRun:
    return ship_run("true", True, EXPORT_REWRITTEN_IN_MAIN)


def case_rewritten_export_in_main_still_ships() -> None:
    run = shipped_over_a_rewritten_export()
    assert run.result.returncode == 0, run.result.stderr
    assert re.fullmatch(r"SHIP_DONE [0-9a-f]{40}", run.last_line()), run.result.stdout
    assert run.default_after == run.shipped_hash(), "the default branch lacks the candidate"


def case_another_changed_file_in_main_stops_with_git_state() -> None:
    run = ship_run("true", True, EXPORT_AND_SOURCE_DIRTY_IN_MAIN)
    assert run.last_line() == "SHIP_BLOCKED git-state", run.result.stdout
    assert run.default_after == run.default_before, "the default branch moved"


# tadw-8tax: changes the operator left in the main checkout are stashed for the ship.
def dirty_main_ship(gate: str, prepare) -> tuple[ShipRepository, subprocess.CompletedProcess]:
    """Ship from the worktree after `prepare` changed the main checkout; the repository is kept."""
    directory = tempfile.mkdtemp()
    repository = ShipRepository(Path(directory).resolve())
    prepare(repository.main)
    result = repository.ship(gate, repository.worktree)
    remove_kept_gate_logs(result.stderr)
    return repository, result


def stage_and_edit(main: Path) -> None:
    (main / "base.txt").write_text("edited\n")
    (main / "staged.txt").write_text("staged\n")
    subprocess.run(["git", "-C", str(main), "add", "staged.txt"], check=True)


def porcelain(repository: ShipRepository) -> str:
    return repository.git("status", "--porcelain")


# tadw-d1nf: a tracked audit log is named, with its fix, before any tree-state stop.
def case_tracked_audit_log_is_named_before_a_dirty_tree() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = ShipRepository(Path(directory).resolve())
        worktree = repository.worktree
        (worktree / ".beads").mkdir(exist_ok=True)
        (worktree / ".beads" / "interactions.jsonl").write_text("{}\n")
        subprocess.run(["git", "-C", str(worktree), "add", ".beads/interactions.jsonl"], check=True)
        subprocess.run(["git", "-C", str(worktree), "commit", "-q", "-m", "track it"], check=True)
        (worktree / "thing.txt").write_text("edited\n")
        result = repository.ship("true", worktree)
        assert result.returncode != 0, result.stderr
        assert "git rm --cached .beads/interactions.jsonl" in result.stderr, result.stderr
        assert "dirty-tracked" not in result.stderr, result.stderr


def case_dirty_main_ships_and_gets_its_changes_back() -> None:
    repository, result = dirty_main_ship("true", stage_and_edit)
    try:
        assert result.returncode == 0, result.stderr
        assert (repository.main / "base.txt").read_text() == "edited\n"
        assert (repository.main / "thing.txt").exists(), "main lacks the landed file"
        assert porcelain(repository) == "M base.txt\nA  staged.txt", porcelain(repository)
        assert not repository.git("stash", "list"), "the stash was left behind"
    finally:
        shutil.rmtree(repository.main.parent, ignore_errors=True)


def edit_export_and_a_source_file(main: Path) -> None:
    (main / ".beads" / "issues.jsonl").write_text("stale\n")
    (main / "base.txt").write_text("edited\n")


def case_stale_export_stays_out_of_the_stash() -> None:
    repository, result = dirty_main_ship("true", edit_export_and_a_source_file)
    try:
        assert result.returncode == 0, result.stderr
        assert porcelain(repository) == "M base.txt", porcelain(repository)
        assert "stashed 1 changed file(s)" in result.stderr, result.stderr
    finally:
        shutil.rmtree(repository.main.parent, ignore_errors=True)


def case_blocked_ship_still_restores_main_changes() -> None:
    repository, result = dirty_main_ship("false", stage_and_edit)
    try:
        assert result.stdout.splitlines()[-1] == "SHIP_BLOCKED gate", result.stdout
        assert porcelain(repository) == "M base.txt\nA  staged.txt", porcelain(repository)
        assert not repository.git("stash", "list"), "the stash was left behind"
    finally:
        shutil.rmtree(repository.main.parent, ignore_errors=True)


def stage_the_file_the_ship_adds(main: Path) -> None:
    (main / "thing.txt").write_text("mine\n")
    subprocess.run(["git", "-C", str(main), "add", "thing.txt"], check=True)


def case_conflicting_restore_keeps_the_stash() -> None:
    repository, result = dirty_main_ship("true", stage_the_file_the_ship_adds)
    try:
        assert re.fullmatch(r"SHIP_DONE [0-9a-f]{40}", result.stdout.splitlines()[-1]), (
            result.stdout
        )
        assert "warning: could not restore the changes stashed" in result.stderr, result.stderr
        assert repository.git("stash", "list"), "the stash was dropped"
        assert repository.git("rev-parse", "main") == repository.git("rev-parse", "origin/main")
    finally:
        shutil.rmtree(repository.main.parent, ignore_errors=True)


def case_ship_gates_on_the_pre_push_hook() -> None:
    run = shipped_through_pre_push()
    assert run.result.returncode == 0, run.result.stderr
    assert run.pushes, "the pre-push hook never ran"


def case_pre_push_gate_checks_code_and_push_carries_landing_commit() -> None:
    run = shipped_through_pre_push()
    runs = run.pushes.splitlines()
    assert len(runs) == 2, f"expected one gate run and one real push: {runs}"
    checked = re.search(r"checked candidate ([0-9a-f]{12})", run.result.stderr)
    assert checked, run.result.stderr
    for line in runs:
        remote, local_ref, local_sha, remote_ref = line.split()[:4]
        assert (remote, local_ref, remote_ref) == (
            "origin",
            "refs/heads/main",
            "refs/heads/main",
        )
        if line == runs[0]:
            assert local_sha.startswith(checked.group(1)), line
        else:
            assert local_sha == run.shipped_hash(), line


def case_failing_pre_push_hook_ends_with_ship_blocked_gate() -> None:
    run = ship_run(None, True, FAILING_PRE_PUSH)
    assert run.last_line() == "SHIP_BLOCKED gate", run.result.stdout
    assert run.default_after == run.default_before, "the default branch moved on a failed hook"


def case_pre_commit_hook_is_the_gate_without_a_pre_push_hook() -> None:
    hook = 'echo called >> "{root}/pre-commit.log"'
    run = ship_run(None, True, (("pre-commit", hook),))
    assert run.result.returncode == 0, run.result.stderr
    assert run.pre_commit_calls.splitlines() == ["called"], run.pre_commit_calls


def case_refused_candidate_commit_ends_with_ship_blocked_gate() -> None:
    run = ship_run(None, True, FAILING_PRE_COMMIT)
    assert run.last_line() == "SHIP_BLOCKED gate", run.result.stdout
    assert run.default_after == run.default_before, "the default branch moved on a refused commit"
    assert "lint failed" in run.result.stderr, run.result.stderr


def install_hook(directory: Path, name: str, body: str, mode: int = 0o755) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(f"#!/bin/sh\n{body}\n")
    (directory / name).chmod(mode)


def selected_source(prepare) -> str:
    with tempfile.TemporaryDirectory() as directory:
        fixture = Fixture(Path(directory))
        prepare(fixture.repo)
        result = fixture.start("--check-gate")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["source"]


def case_pre_push_hook_is_selected() -> None:
    source = selected_source(lambda repo: install_hook(repo / ".git" / "hooks", "pre-push", ""))
    assert source == "pre-push hook", source


def case_hooks_path_is_honored() -> None:
    def prepare(repo: Path) -> None:
        install_hook(repo / ".githooks", "pre-push", "")
        subprocess.run(
            ["git", "-C", str(repo), "config", "core.hooksPath", ".githooks"], check=True
        )

    assert selected_source(prepare) == "pre-push hook"


def case_pre_commit_hook_is_selected_without_a_pre_push_hook() -> None:
    source = selected_source(lambda repo: install_hook(repo / ".git" / "hooks", "pre-commit", ""))
    assert source == "pre-commit hook", source


def case_configuration_outranks_the_hooks() -> None:
    def prepare(repo: Path) -> None:
        install_hook(repo / ".git" / "hooks", "pre-push", "")
        write_config(repo, valid_config())

    assert selected_source(prepare) == str(CONFIG)


def non_executable_hook(repo: Path) -> None:
    install_hook(repo / ".git" / "hooks", "pre-push", "", mode=0o644)


def case_non_executable_hook_is_not_a_gate() -> None:
    Stop(non_executable_hook).assert_blocked()


def case_no_hook_names_adding_a_pre_push_hook() -> None:
    Stop(no_configuration).assert_said("pre-push hook")


def run_gate_with_pre_push(body: str) -> tuple[subprocess.CompletedProcess, str, str]:
    """Run --run-gate in a fixture whose pre-push hook runs `body`; return what it logged."""
    with tempfile.TemporaryDirectory() as directory:
        fixture = Fixture(Path(directory))
        log = Path(directory) / "pushes.log"
        install_hook(fixture.repo / ".git" / "hooks", "pre-push", body.replace("{root}", directory))
        result = fixture.start("--run-gate")
        head = fixture.git("rev-parse", "HEAD").strip()
        return result, read_if_present(log), head


def case_run_gate_feeds_the_pre_push_hook_a_push_of_head() -> None:
    result, pushes, head = run_gate_with_pre_push(LOGGING_PRE_PUSH)
    assert result.returncode == 0, result.stderr
    assert pushes.split() == ["origin", "refs/heads/main", head, "refs/heads/main", "0" * 40]


def case_run_gate_stops_on_a_failing_pre_push_hook() -> None:
    result, _, _ = run_gate_with_pre_push("exit 1")
    assert result.stdout.splitlines()[-1] == "SHIP_BLOCKED gate", result.stdout


SKILL = REPO / "skills" / "ship" / "SKILL.md"
SETUP_INSTRUCTIONS = REPO / "docs" / "ship-gate-contract.md"
# The categories the skill promised before it called the runner.
EXISTING_STOP_SLUGS = {"gate", "conflict", "tracker", "git-state", "internal"}
MAX_SKILL_WORDS = 500


def fenced_lines(text: str) -> list[str]:
    lines, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif fenced:
            lines.append(line)
    return lines


def marked_region(text: str, name: str) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    assert start in text and end in text, f"the document must mark its {name} region"
    return text.split(start, 1)[1].split(end, 1)[0]


def skill_stop_slugs() -> set[str]:
    return set(
        re.findall(r"^\| `([a-z-]+)` \|", marked_region(SKILL.read_text(), "stop-slugs"), re.M)
    )


def runner_stop_slugs() -> set[str]:
    """Every slug the runner's own code names, plus each helper stop it translates."""
    sources = "".join(
        (SCRIPT.parent / name).read_text() for name in ("tadw_ship.py", "ship_workflow.py")
    )
    literal = set(re.findall(r"(?:ShipStop|stop)\(\s*\"([a-z-]+)\"", sources))
    table = re.search(r"CANDIDATE_SLUGS = \{(.*?)\}", sources, re.S)
    assert table, "ship_workflow.py must keep its CANDIDATE_SLUGS table"
    translated = set(re.findall(r"\"[a-z-]+\": \"([a-z-]+)\"", table.group(1)))
    # resolve_rebase_conflict.py reports its own stop, and the workflow passes it through.
    return literal | translated | {"conflict", "tracker"}


def case_skill_ends_with_the_runner_machine_line() -> None:
    text = SKILL.read_text()
    for required in ("SHIP_DONE <hash>", "SHIP_BLOCKED <slug>", "machine line, copied exactly"):
        assert required in text, f"the skill must say {required!r}"


def case_skill_invokes_the_runner_once() -> None:
    commands = [line for line in fenced_lines(SKILL.read_text()) if line.strip()]
    runner = [line for line in commands if "bin/tadw-ship" in line]
    assert len(runner) == 1, f"expected one runner command, found {runner}"
    helpers = [line for line in commands if "skills/ship/scripts/" in line]
    assert not helpers, f"the skill must not run a helper itself: {helpers}"


def case_skill_has_at_most_500_words() -> None:
    words = len(SKILL.read_text().split())  # the count `wc -w` prints
    assert words <= MAX_SKILL_WORDS, f"the skill has {words} words"


def case_skill_lists_every_existing_stop_category() -> None:
    assert skill_stop_slugs() == EXISTING_STOP_SLUGS, skill_stop_slugs()


def case_runner_emits_only_existing_stop_categories() -> None:
    unknown = runner_stop_slugs() - EXISTING_STOP_SLUGS
    assert not unknown, f"the skill does not know these categories: {unknown}"


def case_tracker_slug_does_not_name_the_export() -> None:
    rows = marked_region(SKILL.read_text(), "stop-slugs").splitlines()
    tracker = next(row for row in rows if row.startswith("| `tracker` |"))
    assert "bd export" not in tracker, tracker


def case_setup_instructions_name_the_setup_action() -> None:
    migration = marked_region(SETUP_INSTRUCTIONS.read_text(), "ship-setup")
    for action in ("TADW_SHIP_CHECK", ".tadw/ship-gates.json"):
        assert action in migration, f"the setup instructions must name {action}"


def case_skill_links_the_setup_instructions() -> None:
    assert "docs/ship-gate-contract.md" in SKILL.read_text()


for name, fn in [
    ("the gates are the AGENTS.md list, in order",
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
    ("a zero override timeout is rejected", case_zero_override_timeout_is_rejected),
    ("a negative override timeout is rejected", case_negative_override_timeout_is_rejected),
    ("a signed override timeout is rejected", case_signed_override_timeout_is_rejected),
    ("a missing repository is operator error, not a ship stop",
     case_missing_repository_is_operator_error),
    ("a start on the default branch stops with git-state",
     case_start_on_the_default_branch_stops_with_git_state),
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
    ("a ship exits 0 with SHIP_DONE <hash> last", case_ship_exits_0_with_ship_done_last),
    ("a stop exits 1 with SHIP_BLOCKED <slug> last", case_stop_exits_1_with_ship_blocked_last),
    ("the default branch carries the shipped commit",
     case_default_branch_carries_the_shipped_commit),
    ("the gated commit is the shipped commit", case_gated_commit_is_the_shipped_commit),
    ("the shipped commit is pushed", case_shipped_commit_is_pushed),
    ("a ship closes the bead", case_ship_closes_the_bead),
    ("a ship removes the worktree and the branch", case_ship_removes_the_worktree_and_branch),
    ("a caller in the removed worktree gets the exact cd line",
     case_caller_in_removed_worktree_gets_cd_line),
    ("the cd line sits right above the machine line", case_cd_line_sits_above_the_machine_line),
    ("a caller outside every removed worktree gets no cd line",
     case_caller_outside_removed_worktree_gets_no_cd_line),
    ("a failing gate ends with SHIP_BLOCKED gate", case_failing_gate_ends_with_ship_blocked_gate),
    ("a failing gate leaves the default branch unchanged",
     case_failing_gate_leaves_the_default_branch_unchanged),
    ("a failing gate leaves the bead open", case_failing_gate_leaves_the_bead_open),
    ("a moved default branch reopens the bead", case_default_branch_moves_after_close_reopens_the_bead),
    ("a ship with no bead runs no export", case_bead_free_ship_runs_no_export),
    ("a failed export after the close still ships", case_failed_export_still_ships),
    ("a failed export after the close warns", case_failed_export_warns),
    ("a rewritten export in main still ships", case_rewritten_export_in_main_still_ships),
    ("another changed file in main stops with git-state",
     case_another_changed_file_in_main_stops_with_git_state),
    ("a tracked audit log is named before a dirty tree",
     case_tracked_audit_log_is_named_before_a_dirty_tree),
    ("a dirty main is stashed for the ship and restored after",
     case_dirty_main_ships_and_gets_its_changes_back),
    ("the tracker export stays out of the stash", case_stale_export_stays_out_of_the_stash),
    ("a blocked ship still restores the changes in main",
     case_blocked_ship_still_restores_main_changes),
    ("a conflicting restore keeps the stash and warns",
     case_conflicting_restore_keeps_the_stash),
    ("ship gates on the pre-push hook", case_ship_gates_on_the_pre_push_hook),
    ("the pre-push gate checks code and the push carries the landing commit",
     case_pre_push_gate_checks_code_and_push_carries_landing_commit),
    ("a failing pre-push hook ends with SHIP_BLOCKED gate",
     case_failing_pre_push_hook_ends_with_ship_blocked_gate),
    ("the pre-commit hook is the gate without a pre-push hook",
     case_pre_commit_hook_is_the_gate_without_a_pre_push_hook),
    ("a refused candidate commit ends with SHIP_BLOCKED gate",
     case_refused_candidate_commit_ends_with_ship_blocked_gate),
    ("a pre-push hook is selected", case_pre_push_hook_is_selected),
    ("core.hooksPath is honored", case_hooks_path_is_honored),
    ("a pre-commit hook is selected without a pre-push hook",
     case_pre_commit_hook_is_selected_without_a_pre_push_hook),
    ("the configuration outranks the hooks", case_configuration_outranks_the_hooks),
    ("a non-executable hook is not a gate", case_non_executable_hook_is_not_a_gate),
    ("no hook names adding a pre-push hook", case_no_hook_names_adding_a_pre_push_hook),
    ("--run-gate feeds the pre-push hook a push of HEAD",
     case_run_gate_feeds_the_pre_push_hook_a_push_of_head),
    ("--run-gate stops on a failing pre-push hook",
     case_run_gate_stops_on_a_failing_pre_push_hook),
    ("the skill ends with the runner's machine line", case_skill_ends_with_the_runner_machine_line),
    ("the skill invokes the runner once", case_skill_invokes_the_runner_once),
    ("the skill has at most 500 words", case_skill_has_at_most_500_words),
    ("the skill lists every existing stop category",
     case_skill_lists_every_existing_stop_category),
    ("the runner emits only existing stop categories",
     case_runner_emits_only_existing_stop_categories),
    ("the tracker stop slug does not name bd export",
     case_tracker_slug_does_not_name_the_export),
    ("the setup instructions name the setup action", case_setup_instructions_name_the_setup_action),
    ("the skill links the setup instructions", case_skill_links_the_setup_instructions),
]:  # fmt: skip
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
