#!/usr/bin/env python3
"""Run a list of checks at the same time, and record how each one ended.

Ship and this repository's pre-push hook both run a list of checks. The
running is shared here; the policy is not. Ship requires every gate to pass.
Pre-push skips a check whose tool is missing and reports every failure
together. Each caller decides what a result means, and this module only
reports results.

Four rules decide when a check starts:

1. No more than `workers` checks run at once.
2. A check waits until every check it `depends_on` has finished, passed or
   failed. A check whose dependency did not finish (it timed out, was
   interrupted, or never ran) never runs either.
3. Checks that name the same resource, such as `tracker`, run one at a time
   and in list order.
4. Otherwise, the earliest check in the list starts first.

When no check is running and none can start, the plan cannot make progress,
for example when a check depends on a later check that shares its resource.
Every check left is then recorded as not run, rather than waiting forever.

Each check runs in a process group of its own, so stopping it also stops
every process it started inside that group. A check past its timeout gets
SIGTERM, then SIGKILL after a grace period, and the other checks keep running
and starting while it winds down. On SIGINT, SIGTERM, or SIGHUP,
every running check gets SIGINT first, so a Python check can run its own
cleanup, then SIGKILL after the grace period. A check that did not finish is
never given an exit status, so no caller can read it as a pass.

A check that carries a `Reuse` can be satisfied by a saved result instead of a
process. Its gate declares what the result depends on: input files, tools, and
environment variables. When the check is due to start, the executor reads all
of them, and the command, and compares them with the saved pass. A full match
records a pass and starts nothing. Anything else runs the check: no saved
result, a saved result that is not a pass, one changed value, or one value
that cannot be read. A pass is saved only when the same values read the same
after the run as before it. docs/ship-gate-contract.md states the rule.

Run as a script, it reads a plan directory the pre-push hook writes: one
`<n>.cmd` file per check, holding the command as space-separated words, and an
optional `<n>.after` file holding the number of the check it waits for. It
writes each check's output to `<n>.out`, and writes `<n>.rc` the moment a check
finishes, and only then. With `--repo-root`, a planned check whose command is
the command of a reusable gate in that repository takes the gate's
declarations, and a check a saved result satisfies also gets an empty
`<n>.reused`. Exit status: 0 when the run was not interrupted, 128 plus the
signal number when it was, and 2 on operator error.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import enum
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import ModuleType


# Each ship script carries this loader: a shared one would itself have to be loaded by path.
def load_sibling(name: str) -> ModuleType:
    """Load a helper from this file's own directory, never from another installed copy."""
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    # A dataclass resolves its string annotations through sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


read_gate_config = load_sibling("read_gate_config")

EXIT_OPERATOR_ERROR = 2
DEFAULT_GRACE_SECONDS = 5.0
POLL_SECONDS = 0.05
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
# The exit status a shell gives a command it could not run.
EXIT_COULD_NOT_START = 127
SAVED_RESULT_VERSION = 1
SAVED_RESULTS_DIRECTORY = "tadw-check-results"
TOOL_VERSION_TIMEOUT_SECONDS = 10
# Tracked files, and untracked files git does not ignore.
LIST_FILES = ("ls-files", "-z", "--cached", "--others", "--exclude-standard")
REUSED_LOG = "reused a saved result: every declared input, tool, and variable matches\n"


class Status(enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INTERRUPTED = "interrupted"
    NOT_RUN = "not_run"

    @property
    def finished(self) -> bool:
        """Whether the check ran to its own end, so its exit status means something."""
        return self in (Status.PASSED, Status.FAILED)


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]
    log: Path
    cwd: Path = Path()
    timeout: float | None = None
    depends_on: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    # Without one, the check always runs.
    reuse: Reuse | None = None

    def declared_state(self) -> dict | None:
        """Everything the result depends on, read now; None when no saved result may stand in."""
        return self.reuse.state_of(self) if self.reuse else None


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    exit_code: int | None
    log: Path
    started: float | None = None
    ended: float | None = None
    # True when a saved pass stood in for the check, so no process started.
    reused: bool = False


@dataclass(frozen=True)
class Outcome:
    """Every check's result in list order, and the signal that stopped the run, if any."""

    results: tuple[CheckResult, ...]
    stopped_by: signal.Signals | None = None


def run_checks(
    checks: Sequence[Check],
    workers: int,
    grace: float = DEFAULT_GRACE_SECONDS,
    on_result: Callable[[CheckResult], None] = lambda result: None,
) -> Outcome:
    """Run every check under the rules above; `on_result` hears each result as it lands."""
    validate_plan(checks, workers)
    with contextlib.ExitStack() as logs:
        run = _Run(list(checks), workers, grace, on_result, logs)
        with _StopSignalsRecorded(run):
            run.drive()
        return run.outcome()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = Path(args.plan_dir)
    if not plan.is_dir():
        print(f"run_checks: not a plan directory: {plan}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    try:
        checks = planned_checks(plan, args.repo_root)
        outcome = run_checks(checks, args.workers, args.grace, write_exit_status(plan))
    except ValueError as error:
        print(f"run_checks: {error}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    return 0 if outcome.stopped_by is None else 128 + outcome.stopped_by


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan-dir", required=True, help="directory holding the <n>.cmd files")
    parser.add_argument("--workers", type=int, required=True, help="most checks to run at once")
    parser.add_argument("--grace", type=float, default=DEFAULT_GRACE_SECONDS, help="seconds")
    parser.add_argument(
        "--repo-root", help="reuse saved results for the reusable gates this repository configures"
    )
    return parser.parse_args(argv)


def planned_checks(plan: Path, repo_root: str | None) -> list[Check]:
    checks = read_plan(plan)
    return checks if repo_root is None else with_gate_reuse(checks, Path(repo_root))


def with_gate_reuse(checks: list[Check], repo: Path) -> list[Check]:
    """A planned check has no gate name, so its command finds the gate that declares its inputs."""
    results = saved_results(repo)
    rules = {tuple(gate["command"]): reuse_for(gate, results) for gate in root_gates(repo)}
    return [dataclasses.replace(check, reuse=rules.get(check.command)) for check in checks]


def root_gates(repo: Path) -> list[read_gate_config.NormalizedGate]:
    """The gates that run at the repository root, where every planned check runs."""
    try:
        gates = read_gate_config.load_gates(repo)
    except read_gate_config.GateConfigError:
        return []
    return [gate for gate in gates if gate["cwd"] == "."]


def reuse_line(outcome: Outcome) -> str | None:
    """How many checks a saved result satisfied, for a caller to report; None when none did."""
    reused = sum(result.reused for result in outcome.results)
    if not reused:
        return None
    return f"{reused} of {len(outcome.results)} checks reused a saved result and started no process"


def read_plan(plan: Path) -> list[Check]:
    """One check per `<n>.cmd`, in numeric order, named by its number."""
    numbers = sorted(int(path.stem) for path in plan.glob("*.cmd") if path.stem.isdigit())
    return [read_check(plan, str(number)) for number in numbers]


def read_check(plan: Path, name: str) -> Check:
    after = plan / f"{name}.after"
    return Check(
        name=name,
        command=tuple((plan / f"{name}.cmd").read_text(encoding="utf-8").split()),
        log=plan / f"{name}.out",
        depends_on=tuple(after.read_text(encoding="utf-8").split()) if after.exists() else (),
    )


def write_exit_status(plan: Path) -> Callable[[CheckResult], None]:
    """Write `<n>.rc` as each check finishes, so a run that dies later keeps what it knew.

    A check a saved result satisfied also gets an empty `<n>.reused`, so the hook can count them.
    """

    def write(result: CheckResult) -> None:
        if result.status.finished:
            (plan / f"{result.name}.rc").write_text(f"{result.exit_code}\n", encoding="utf-8")
        if result.reused:
            (plan / f"{result.name}.reused").touch()

    return write


def validate_plan(checks: Sequence[Check], workers: int) -> None:
    if workers < 1:
        raise ValueError(f"workers must be at least 1, found {workers}")
    names = [check.name for check in checks]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        raise ValueError(f"check names appear more than once: {', '.join(duplicated)}")
    for check in checks:
        unknown = [name for name in check.depends_on if name not in names]
        if unknown:
            raise ValueError(f"{check.name} depends on unknown checks: {', '.join(unknown)}")


class Unverifiable(Exception):
    """Something a check declares could not be read, so no saved result can be trusted."""


@dataclass
class SavedResults:
    """The passes saved for one repository, and the readers that decide whether one still holds.

    One instance serves one run. Every worktree of the repository shares the
    store, which is safe because a saved pass is matched on content, never on
    which worktree or commit wrote it.
    """

    root: Path
    store: Path
    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)
    tools: dict[str, dict[str, str]] = field(default_factory=dict)

    def holds(self, state: dict) -> bool:
        """Whether the saved result for this command is a pass recorded for exactly this state."""
        try:
            saved = json.loads(self.path_for(state).read_text(encoding="utf-8"))
        except OSError, UnicodeDecodeError, json.JSONDecodeError:
            return False
        return (
            isinstance(saved, dict)
            and saved.get("status") == Status.PASSED.value
            and saved.get("state") == state
        )

    def save(self, state: dict, result: CheckResult) -> None:
        """A result that cannot be saved costs a rerun next time, never this run's pass."""
        record = {
            "state": state,
            "status": result.status.value,
            "exit_code": result.exit_code,
            "seconds": result.ended - result.started,
            "log": str(result.log),
        }
        try:
            self.write(self.path_for(state), json.dumps(record, indent=2))
        except OSError as error:
            print(
                f"run_checks: could not save the result of {result.name}: {error}", file=sys.stderr
            )

    def write(self, path: Path, text: str) -> None:
        """Through a temporary file, so a reader never sees half a record."""
        self.store.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.store, suffix=".tmp", delete=False
        ) as handle:
            handle.write(text)
        Path(handle.name).replace(path)

    def path_for(self, state: dict) -> Path:
        """One file per command and working directory, so each run replaces the last result."""
        return self.store / f"{digest(json.dumps([state['command'], state['cwd']]).encode())}.json"

    def relative(self, directory: Path) -> str:
        return os.path.relpath(directory.resolve(), self.root.resolve())

    def input_hashes(self, patterns: Sequence[str]) -> dict[str, str]:
        files = self.listed_files()
        return {
            name: self.file_hash(name) for pattern in patterns for name in matching(files, pattern)
        }

    def listed_files(self) -> list[str]:
        """Every file a declared input can match, as git lists them."""
        try:
            # surrogateescape, so a file name that is not UTF-8 still names its file.
            listed = subprocess.run(
                ["git", "-C", str(self.root), *LIST_FILES],
                capture_output=True,
                encoding="utf-8",
                errors="surrogateescape",
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise Unverifiable(f"git could not list the files in {self.root}") from error
        return sorted(set(filter(None, listed.stdout.split("\0"))))

    def file_hash(self, name: str) -> str:
        try:
            return digest((self.root / name).read_bytes())
        except OSError as error:
            raise Unverifiable(f"input {name} could not be read") from error

    def tool_identity(self, tool: str) -> dict[str, str]:
        """Where the tool resolves and what it prints for `--version`, kept until forgotten."""
        if tool not in self.tools:
            self.tools[tool] = read_tool_identity(tool, self.environ.get("PATH"))
        return self.tools[tool]

    def forget_tools(self, tools: Sequence[str]) -> None:
        """The next reading of each tool is a fresh one."""
        for tool in tools:
            self.tools.pop(tool, None)

    def env_hash(self, name: str) -> str | None:
        """A hash, so a secret a gate declares is never written to the store; None when unset."""
        value = self.environ.get(name)
        return None if value is None else digest(value.encode())


@dataclass(frozen=True)
class Reuse:
    """What a check's result depends on, as its gate declares it, and where passes are saved."""

    inputs: tuple[str, ...]
    tools: tuple[str, ...]
    env: tuple[str, ...]
    results: SavedResults

    def state_of(self, check: Check) -> dict | None:
        """None when the declarations are incomplete, or when any declared value cannot be read."""
        if not self.names_what_runs(check):
            return None
        try:
            return self.read_state(check)
        except Unverifiable:
            return None

    def state_after_run(self, check: Check) -> dict | None:
        """Read with fresh tool identities: the check that just ran may have changed a tool."""
        self.results.forget_tools(self.tools)
        return self.state_of(check)

    def names_what_runs(self, check: Check) -> bool:
        """Inputs, and at least the program the command itself starts, must be declared."""
        return bool(self.inputs) and check.command[0] in self.tools

    def read_state(self, check: Check) -> dict:
        return {
            "version": SAVED_RESULT_VERSION,
            "command": list(check.command),
            "cwd": self.results.relative(check.cwd),
            "inputs": self.results.input_hashes(self.inputs),
            "tools": {tool: self.results.tool_identity(tool) for tool in self.tools},
            "env": {name: self.results.env_hash(name) for name in self.env},
        }

    def satisfied_by_saved(self, state: dict) -> bool:
        return self.results.holds(state)

    def save(self, state: dict, result: CheckResult) -> None:
        self.results.save(state, result)


def saved_results(root: Path) -> SavedResults | None:
    """The store under the repository's common git directory; None when `root` is in no repository.

    The common directory, never the per-worktree one: ship gates a temporary
    worktree it then removes, and the push that follows runs in another checkout.
    """
    try:
        common = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
    except OSError, subprocess.CalledProcessError:
        return None
    return SavedResults(root, root / common.stdout.strip() / SAVED_RESULTS_DIRECTORY)


def reuse_for(gate: Mapping, results: SavedResults | None) -> Reuse | None:
    """The gate's declarations as a `Reuse`; None when the gate is not reusable or has no store."""
    if results is None or not gate["reuse"]:
        return None
    return Reuse(tuple(gate["inputs"]), tuple(gate["tools"]), tuple(gate["env"]), results)


def matching(files: Sequence[str], pattern: str) -> list[str]:
    """A declared input that matches no file is a missing input, so nothing can be verified."""
    matched = [name for name in files if PurePosixPath(name).full_match(pattern)]
    if not matched:
        raise Unverifiable(f"input {pattern} matches no file")
    return matched


def read_tool_identity(tool: str, search_path: str | None) -> dict[str, str]:
    location = shutil.which(tool, path=search_path)
    if location is None:
        raise Unverifiable(f"tool {tool} is not on PATH")
    return {"path": os.path.realpath(location), "version": read_tool_version(location)}


def read_tool_version(location: str) -> str:
    try:
        shown = subprocess.run(
            [location, "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=TOOL_VERSION_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise Unverifiable(f"{location} --version did not run to a clean exit") from error
    return (shown.stdout + shown.stderr).strip()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class _Running:
    check: Check
    process: subprocess.Popen
    started: float
    # What the check declared it depends on, read just before it started.
    state: dict | None = None
    # Set once the check passes its timeout and gets SIGTERM: when SIGKILL follows.
    kill_at: float | None = None

    def past_timeout(self, now: float) -> bool:
        return self.check.timeout is not None and now - self.started > self.check.timeout


@dataclass
class _Run:
    checks: list[Check]
    workers: int
    grace: float
    on_result: Callable[[CheckResult], None]
    logs: contextlib.ExitStack
    results: dict[str, CheckResult] = field(default_factory=dict)
    running: list[_Running] = field(default_factory=list)
    stopped_by: signal.Signals | None = None

    def drive(self) -> None:
        while self.stopped_by is None and len(self.results) < len(self.checks):
            recorded = len(self.results)
            self.collect_finished()
            self.skip_blocked()
            self.start_ready()
            if self.running:
                time.sleep(POLL_SECONDS)
            elif len(self.results) == recorded:
                self.skip_stalled()
        if self.stopped_by is not None:
            self.stop_all()

    def stop(self, signum: int) -> None:
        """Ask the run to stop; only the first signal counts."""
        if self.stopped_by is None:
            self.stopped_by = signal.Signals(signum)

    def outcome(self) -> Outcome:
        self.skip_stalled()
        return Outcome(tuple(self.results[check.name] for check in self.checks), self.stopped_by)

    def collect_finished(self) -> None:
        now = time.monotonic()
        for entry in list(self.running):
            code = entry.process.poll()
            if entry.kill_at is not None:
                if code is not None or now >= entry.kill_at:
                    self.kill(entry, Status.TIMED_OUT)
            elif code is not None:
                status = status_of_exit(code)
                self.finish(entry, status, code if status.finished else None)
            elif entry.past_timeout(now):
                signal_group(entry.process, signal.SIGTERM)
                entry.kill_at = now + self.grace

    def skip_blocked(self) -> None:
        for check in self.pending():
            if any(self.ended_unfinished(name) for name in check.depends_on):
                self.record_not_run(check)

    def start_ready(self) -> None:
        for check in self.pending():
            if len(self.running) >= self.workers:
                return
            if self.is_ready(check):
                self.start(check)

    def skip_stalled(self) -> None:
        """Nothing is running and nothing can start, so no check left will ever run."""
        for check in self.pending():
            self.record_not_run(check)

    def stop_all(self) -> None:
        for entry in self.running:
            signal_group(entry.process, signal.SIGINT)
        deadline = time.monotonic() + self.grace
        while time.monotonic() < deadline and any(e.process.poll() is None for e in self.running):
            time.sleep(POLL_SECONDS)
        for entry in list(self.running):
            self.kill(entry, Status.INTERRUPTED)

    def start(self, check: Check) -> None:
        state = check.declared_state()
        if state is not None and check.reuse.satisfied_by_saved(state):
            self.record_reused(check)
        else:
            self.start_process(check, state)

    def record_reused(self, check: Check) -> None:
        check.log.write_text(REUSED_LOG, encoding="utf-8")
        self.record(CheckResult(check.name, Status.PASSED, 0, check.log, reused=True))

    def start_process(self, check: Check, state: dict | None) -> None:
        log = self.logs.enter_context(check.log.open("wb"))
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                check.command,
                cwd=check.cwd,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as error:
            log.write(f"could not start {check.command[0]}: {error}\n".encode())
            log.flush()
            self.record(
                CheckResult(
                    check.name, Status.FAILED, EXIT_COULD_NOT_START, check.log, started, started
                )
            )
            return
        self.running.append(_Running(check, process, started, state=state))

    def kill(self, entry: _Running, status: Status) -> None:
        """End every process left in the check's group, and record it as unfinished."""
        signal_group(entry.process, signal.SIGKILL)
        entry.process.wait()
        self.finish(entry, status, None)

    def finish(self, entry: _Running, status: Status, code: int | None) -> None:
        self.running.remove(entry)
        result = CheckResult(
            entry.check.name, status, code, entry.check.log, entry.started, time.monotonic()
        )
        self.save_pass(entry, result)
        self.record(result)

    def save_pass(self, entry: _Running, result: CheckResult) -> None:
        """Only a pass is saved, and only when nothing it depends on changed while it ran."""
        if result.status is not Status.PASSED or entry.state is None:
            return
        if entry.check.reuse.state_after_run(entry.check) == entry.state:
            entry.check.reuse.save(entry.state, result)

    def record_not_run(self, check: Check) -> None:
        self.record(CheckResult(check.name, Status.NOT_RUN, None, check.log))

    def record(self, result: CheckResult) -> None:
        self.results[result.name] = result
        self.on_result(result)

    def pending(self) -> list[Check]:
        started = {entry.check.name for entry in self.running}
        return [c for c in self.checks if c.name not in self.results and c.name not in started]

    def is_ready(self, check: Check) -> bool:
        if not all(name in self.results for name in check.depends_on):
            return False
        earlier = self.checks[: self.checks.index(check)]
        return not any(self.holds_a_resource_of(other, check) for other in earlier)

    def holds_a_resource_of(self, other: Check, check: Check) -> bool:
        """Whether `other` names one of `check`'s resources and has yet to finish."""
        return other.name not in self.results and bool(set(other.resources) & set(check.resources))

    def ended_unfinished(self, name: str) -> bool:
        result = self.results.get(name)
        return result is not None and not result.status.finished


def status_of_exit(code: int) -> Status:
    """A negative code is a signal: something outside ended the check, so it did not finish."""
    if code < 0:
        return Status.INTERRUPTED
    return Status.PASSED if code == 0 else Status.FAILED


def signal_group(process: subprocess.Popen, signum: signal.Signals) -> None:
    """Signal the check's whole process group, which stays reachable while any member lives."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signum)


class _StopSignalsRecorded:
    """Tell the run to stop on a stop signal instead of dying on it, then restore the handlers.

    Replacing the handler also matters for the hook: sh starts a background job
    with SIGINT ignored, and a check would inherit that through exec. A handled
    signal is reset to its default on exec, so each check can be interrupted.
    """

    def __init__(self, run: _Run) -> None:
        self.run = run
        self.previous: dict[signal.Signals, object] = {}

    def __enter__(self) -> None:
        for signum in STOP_SIGNALS:
            self.previous[signum] = signal.signal(signum, self.handle)

    def __exit__(self, *exc_info: object) -> None:
        for signum, handler in self.previous.items():
            signal.signal(signum, handler)

    def handle(self, signum: int, frame: object) -> None:
        self.run.stop(signum)


if __name__ == "__main__":
    sys.exit(main())
