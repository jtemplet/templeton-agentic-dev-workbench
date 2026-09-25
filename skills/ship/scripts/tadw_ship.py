#!/usr/bin/env python3
"""Ship a bead's branch without a model: the executable the ship skill will call.

Run it from any shell as `tadw-ship [bead-id]`. The gate comes from the first of
these that is set, and no other source is read:

1. `TADW_SHIP_CHECK`, one shell command, bounded by `TADW_SHIP_CHECK_TIMEOUT`
   (seconds, default 900). A blank value counts as unset, because an empty
   command would pass every ship.
2. `.tadw/ship-gates.json`, as docs/ship-gate-contract.md specifies. Each gate
   there carries its own `timeout`.

`--check-gate` prints the selected gate as JSON. `--run-gate` runs it through
run_checks.py, the executor the pre-push hook shares, and every gate must pass:
a missing tool stops the ship rather than being skipped. With neither flag the
runner ships the bead end to end through ship_workflow.py, running the same
gate on the candidate commit it lands.

Exit status: 0 on success (the last stdout line is `SHIP_DONE <hash>`), 1 on a
ship stop (the last stdout line is `SHIP_BLOCKED <slug>`), 2 on operator error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
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
run_checks = load_sibling("run_checks")
ship_report = load_sibling("ship_report")
worktree_cleanup = load_sibling("worktree_cleanup")
ship_workflow = load_sibling("ship_workflow")

EXIT_OK = 0
EXIT_BLOCKED = 1

OVERRIDE_VARIABLE = "TADW_SHIP_CHECK"
TIMEOUT_VARIABLE = "TADW_SHIP_CHECK_TIMEOUT"

SETUP_ACTION = (
    f"Set {OVERRIDE_VARIABLE} to one command that runs the whole gate, or write "
    f"{read_gate_config.CONFIG_PATH} as docs/ship-gate-contract.md describes, then re-run."
)
TIMEOUT_ACTION = (
    f"Set {TIMEOUT_VARIABLE} to a positive whole number of seconds, or unset it for the "
    f"default of {read_gate_config.DEFAULT_TIMEOUT_SECONDS}, then re-run."
)


class GateBlocked(Exception):
    """No usable gate: the run stops with `SHIP_BLOCKED gate` before any mutation."""

    def __init__(self, problems: list[str], action: str = SETUP_ACTION) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems
        self.action = action


@dataclass(frozen=True)
class ShipGate:
    """The checks a ship must pass, and where they were configured."""

    source: str
    gates: tuple[read_gate_config.NormalizedGate, ...]

    def as_json(self) -> dict:
        return {"source": self.source, "gates": list(self.gates)}

    def checks(self, repo: Path, log_dir: Path) -> list[run_checks.Check]:
        return [
            run_checks.Check(
                name=gate["name"],
                command=tuple(gate["command"]),
                log=log_dir / f"{gate['name']}.log",
                cwd=repo / gate["cwd"],
                timeout=gate["timeout"],
                depends_on=tuple(gate["depends_on"]),
                resources=tuple(gate["resources"]),
            )
            for gate in self.gates
        ]


class CandidateGate:
    """The gate a landing runs on its candidate tree; it keeps each check's report."""

    def __init__(self, gate: ShipGate) -> None:
        self.gate = gate
        self.outcome: run_checks.Outcome | None = None
        self.reports: tuple[ship_report.CheckReport, ...] = ()

    def __call__(self, directory: Path) -> bool:
        """Logs go to a fresh temporary directory, kept only when a gate did not pass."""
        log_dir = Path(tempfile.mkdtemp(prefix="tadw-ship-gate-"))
        self.outcome = run_checks.run_checks(
            self.gate.checks(directory, log_dir), os.cpu_count() or 1
        )
        self.reports = check_reports(self.outcome)
        if self.passed():
            shutil.rmtree(log_dir, ignore_errors=True)
        return self.passed()

    def passed(self) -> bool:
        return self.outcome is not None and gate_passed(self.outcome)


def main(argv: list[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    # First, before anything can chdir: the caller's directory decides the `cd` line.
    start = Path.cwd()
    args = parse_args(argv)
    try:
        gate = select_gate(args.repo_root, os.environ if environ is None else environ)
    except GateBlocked as blocked:
        return stop("gate", *blocked.problems, f"nothing was changed. {blocked.action}")
    return dispatch(args, gate, start)


def dispatch(args: argparse.Namespace, gate: ShipGate, start: Path) -> int:
    if args.run_gate:
        return run_gate(gate, args.repo_root)
    if args.check_gate:
        return show_gate(gate)
    return start_workflow(args, gate, start)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.bead_id and (args.check_gate or args.run_gate):
        parser.error("bead-id ships a bead; --check-gate and --run-gate only test the gate")
    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "bead_id",
        nargs="?",
        metavar="bead-id",
        help="the bead to ship; when omitted, the bead is derived from the branch name",
    )
    parser.add_argument(
        "--repo-root", default=".", type=existing_directory, help="the repository to ship from"
    )
    add_gate_flags(parser)
    return parser


def add_gate_flags(parser: argparse.ArgumentParser) -> None:
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument(
        "--check-gate", action="store_true", help="select and validate the gate, print it, and stop"
    )
    flags.add_argument(
        "--run-gate", action="store_true", help="select the gate, run it, and stop on any failure"
    )


def existing_directory(value: str) -> Path:
    path = Path(value)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"not a directory: {path}")
    return path


def select_gate(repo: Path, environ: Mapping[str, str]) -> ShipGate:
    command = environ.get(OVERRIDE_VARIABLE, "")
    if command.strip():
        return override_gate(command, override_timeout(environ.get(TIMEOUT_VARIABLE)))
    return configured_gate(repo)


def override_timeout(value: str | None) -> int:
    if value is None or not value.strip():
        return read_gate_config.DEFAULT_TIMEOUT_SECONDS
    if not value.strip().isdecimal() or int(value) <= 0:
        problem = f"{TIMEOUT_VARIABLE} must be a positive whole number of seconds, found {value!r}"
        raise GateBlocked([problem], TIMEOUT_ACTION)
    return int(value)


def override_gate(command: str, timeout: int) -> ShipGate:
    """The override is one documented shell string, so a shell runs it."""
    gate = read_gate_config.NormalizedGate(
        name=OVERRIDE_VARIABLE,
        command=["sh", "-c", command],
        inputs=[],
        cwd=".",
        timeout=timeout,
        depends_on=[],
        resources=[],
        reuse=False,
    )
    return ShipGate(OVERRIDE_VARIABLE, (gate,))


def configured_gate(repo: Path) -> ShipGate:
    try:
        gates = read_gate_config.load_gates(repo)
    except read_gate_config.GateConfigError as error:
        raise GateBlocked(error.problems) from error
    return ShipGate(str(read_gate_config.CONFIG_PATH), tuple(gates))


def show_gate(gate: ShipGate) -> int:
    print(json.dumps(gate.as_json(), indent=2))
    return EXIT_OK


def run_gate(gate: ShipGate, repo: Path) -> int:
    run = CandidateGate(gate)
    passed = run(repo)
    print_check_lines(run.reports)
    if not passed:
        return stop("gate", *interruption(run.outcome))
    return report_gate_passed(len(run.reports))


def check_reports(outcome: run_checks.Outcome) -> tuple[ship_report.CheckReport, ...]:
    return tuple(
        ship_report.report_check(result.name, result.status.value, result.log)
        for result in outcome.results
    )


def print_check_lines(reports: tuple[ship_report.CheckReport, ...]) -> None:
    for line in ship_report.check_lines(reports):
        print(line, file=sys.stderr)


def gate_passed(outcome: run_checks.Outcome) -> bool:
    """Ship's policy: every gate ran to its end and passed; anything else stops the ship."""
    return outcome.stopped_by is None and all(
        result.status is run_checks.Status.PASSED for result in outcome.results
    )


def interruption(outcome: run_checks.Outcome) -> list[str]:
    if outcome.stopped_by is None:
        return []
    return [f"the gate was interrupted by {outcome.stopped_by.name}"]


def report_gate_passed(count: int) -> int:
    print(f"tadw_ship: every gate passed, {count} of {count}")
    return EXIT_OK


def start_workflow(args: argparse.Namespace, gate: ShipGate, start: Path) -> int:
    """Resolve the stable checkout before the first mutation, and keep that one path."""
    try:
        stable = worktree_cleanup.stable_checkout(args.repo_root)
    except worktree_cleanup.NoStableCheckout as missing:
        return stop(
            "git-state",
            str(missing),
            "nothing was changed. Ship from a repository with a main checkout, "
            "because ship moves there before it removes any worktree.",
        )
    request = ship_workflow.Request(args.repo_root.resolve(), start, stable, args.bead_id)
    return ship(request, CandidateGate(gate))


def ship(request: ship_workflow.Request, gate: CandidateGate) -> int:
    try:
        shipped = ship_workflow.ship(request, gate)
    except ship_workflow.ShipStop as stopped:
        print_check_lines(gate.reports)
        return stop(stopped.slug, *stopped.explanation)
    return report_shipped(shipped, gate.reports)


def report_shipped(
    shipped: ship_workflow.Shipped, checks: tuple[ship_report.CheckReport, ...]
) -> int:
    """One result, rendered once, so the `cd` line always sits right above the machine line."""
    machine_line = f"SHIP_DONE {shipped.commit}"
    result = ship_report.ShipResult(shipped.bead_id, checks, machine_line, shipped.cd_target)
    print("\n".join(ship_report.render(result)))
    return EXIT_OK


def stop(reason: str, *explanation: str) -> int:
    """Explain on stderr, then print the machine line last, where callers read it."""
    for line in explanation:
        print(f"tadw_ship: {line}", file=sys.stderr)
    print(f"SHIP_BLOCKED {reason}")
    return EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
