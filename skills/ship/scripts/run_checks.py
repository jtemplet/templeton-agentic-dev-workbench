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

Run as a script, it reads a plan directory the pre-push hook writes: one
`<n>.cmd` file per check, holding the command as space-separated words, and an
optional `<n>.after` file holding the number of the check it waits for. It
writes each check's output to `<n>.out`, and writes `<n>.rc` the moment a check
finishes, and only then. Exit status: 0 when the run was not interrupted, 128
plus the signal number when it was, and 2 on operator error.
"""

from __future__ import annotations

import argparse
import contextlib
import enum
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OPERATOR_ERROR = 2
DEFAULT_GRACE_SECONDS = 5.0
POLL_SECONDS = 0.05
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
# The exit status a shell gives a command it could not run.
EXIT_COULD_NOT_START = 127


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


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    exit_code: int | None
    log: Path
    started: float | None = None
    ended: float | None = None


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
        outcome = run_checks(read_plan(plan), args.workers, args.grace, write_exit_status(plan))
    except ValueError as error:
        print(f"run_checks: {error}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    return 0 if outcome.stopped_by is None else 128 + outcome.stopped_by


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan-dir", required=True, help="directory holding the <n>.cmd files")
    parser.add_argument("--workers", type=int, required=True, help="most checks to run at once")
    parser.add_argument("--grace", type=float, default=DEFAULT_GRACE_SECONDS, help="seconds")
    return parser.parse_args(argv)


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
    """Write `<n>.rc` as each check finishes, so a run that dies later keeps what it knew."""

    def write(result: CheckResult) -> None:
        if result.status.finished:
            (plan / f"{result.name}.rc").write_text(f"{result.exit_code}\n", encoding="utf-8")

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


@dataclass
class _Running:
    check: Check
    process: subprocess.Popen
    started: float
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
        self.running.append(_Running(check, process, started))

    def kill(self, entry: _Running, status: Status) -> None:
        """End every process left in the check's group, and record it as unfinished."""
        signal_group(entry.process, signal.SIGKILL)
        entry.process.wait()
        self.finish(entry, status, None)

    def finish(self, entry: _Running, status: Status, code: int | None) -> None:
        self.running.remove(entry)
        self.record(
            CheckResult(
                entry.check.name, status, code, entry.check.log, entry.started, time.monotonic()
            )
        )

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
