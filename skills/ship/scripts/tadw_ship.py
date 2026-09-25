#!/usr/bin/env python3
"""Ship a bead's branch without a model: the executable the ship skill will call.

Run it from any shell as `tadw-ship [bead-id]`, through `bin/tadw-ship`, or as
this file. It resolves the gate, then the stable checkout, before any step that
changes Git or tracker state. A repository with no gate stops with
`SHIP_BLOCKED gate`, and one with no stable checkout stops with
`SHIP_BLOCKED git-state`, both having touched nothing. The landing steps come
later (tadw-0jz2); until then only `--check-gate` and `--run-gate` run to
completion.

The gate comes from the first of these sources that is set:

1. `TADW_SHIP_CHECK`, one shell command, bounded by `TADW_SHIP_CHECK_TIMEOUT`
   (seconds, default 900). A blank value counts as unset, because an empty
   command would pass every ship.
2. `.tadw/ship-gates.json`, the versioned file docs/ship-gate-contract.md
   specifies. Each gate there carries its own `timeout`, and
   `TADW_SHIP_CHECK_TIMEOUT` does not apply to it.

No other source is read. Markdown is never parsed for a gate.

`--run-gate` runs the gate through run_checks.py, the executor the pre-push
hook shares, and holds it to ship's policy: every gate must pass. A gate that
fails, times out, cannot start, or is interrupted stops the run. Nothing is
skipped for a missing tool, which is the pre-push hook's policy and not ship's.

Exit status: 0 when `--check-gate` found a gate (printed as JSON on stdout) or
every gate `--run-gate` ran passed, 1 on a ship stop (the last stdout line is
the machine line), 2 on operator error, such as a repository path that does not
exist.
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

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_OPERATOR_ERROR = 2

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
    """No usable gate: the run must stop with `SHIP_BLOCKED gate` before any mutation."""

    def __init__(self, problems: list[str], action: str = SETUP_ACTION) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems
        self.action = action


@dataclass(frozen=True)
class OverrideGate:
    """One shell command from `TADW_SHIP_CHECK`, bounded by one timeout."""

    command: str
    timeout: int

    def as_json(self) -> dict:
        return {"source": OVERRIDE_VARIABLE, "command": self.command, "timeout": self.timeout}

    def checks(self, repo: Path, log_dir: Path) -> list[run_checks.Check]:
        """The override is the one documented shell string, so a shell runs it."""
        return [
            run_checks.Check(
                name=OVERRIDE_VARIABLE,
                command=("sh", "-c", self.command),
                log=log_dir / f"{OVERRIDE_VARIABLE}.log",
                cwd=repo,
                timeout=self.timeout,
            )
        ]


@dataclass(frozen=True)
class ConfiguredGate:
    """The normalized gates from `.tadw/ship-gates.json`, each carrying its own timeout."""

    gates: tuple[read_gate_config.NormalizedGate, ...]

    def as_json(self) -> dict:
        return {"source": str(read_gate_config.CONFIG_PATH), "gates": list(self.gates)}

    def checks(self, repo: Path, log_dir: Path) -> list[run_checks.Check]:
        return [check_for(gate, repo, log_dir) for gate in self.gates]


def check_for(gate: read_gate_config.NormalizedGate, repo: Path, log_dir: Path) -> run_checks.Check:
    return run_checks.Check(
        name=gate["name"],
        command=tuple(gate["command"]),
        log=log_dir / f"{gate['name']}.log",
        cwd=repo / gate["cwd"],
        timeout=gate["timeout"],
        depends_on=tuple(gate["depends_on"]),
        resources=tuple(gate["resources"]),
    )


Gate = OverrideGate | ConfiguredGate


def main(argv: list[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo_root)
    if not repo.is_dir():
        return refuse_missing_repository(repo)
    try:
        gate = resolve_gate(repo, os.environ if environ is None else environ)
    except GateBlocked as blocked:
        return stop_on_gate(blocked)
    return run_requested_mode(args, gate, repo)


def run_requested_mode(args: argparse.Namespace, gate: Gate, repo: Path) -> int:
    if args.run_gate:
        return run_gate_with_kept_failure_logs(gate, repo)
    if args.check_gate:
        return print_gate(gate)
    return start_workflow(repo)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    reject_bead_with_gate_flag(parser, args)
    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "bead_id",
        nargs="?",
        metavar="bead-id",
        help="the bead to ship; when omitted, the bead is derived from the branch name",
    )
    parser.add_argument("--repo-root", default=".", help="the repository to ship from")
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument(
        "--check-gate", action="store_true", help="select and validate the gate, print it, and stop"
    )
    flags.add_argument(
        "--run-gate", action="store_true", help="select the gate, run it, and stop on any failure"
    )
    return parser


def reject_bead_with_gate_flag(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.bead_id and (args.check_gate or args.run_gate):
        parser.error("bead-id ships a bead; --check-gate and --run-gate only test the gate")


def resolve_gate(repo: Path, environ: Mapping[str, str]) -> Gate:
    override = environ.get(OVERRIDE_VARIABLE, "")
    if override.strip():
        return OverrideGate(override, override_timeout(environ.get(TIMEOUT_VARIABLE)))
    return configured_gate(repo)


def override_timeout(value: str | None) -> int:
    if value is None or not value.strip():
        return read_gate_config.DEFAULT_TIMEOUT_SECONDS
    return positive_seconds(value)


def positive_seconds(value: str) -> int:
    problem = [f"{TIMEOUT_VARIABLE} must be a positive whole number of seconds, found {value!r}"]
    try:
        seconds = int(value)
    except ValueError as error:
        raise GateBlocked(problem, TIMEOUT_ACTION) from error
    if seconds <= 0:
        raise GateBlocked(problem, TIMEOUT_ACTION)
    return seconds


def configured_gate(repo: Path) -> ConfiguredGate:
    path = repo / read_gate_config.CONFIG_PATH
    require_gate_config_file(path)
    document = read_gate_document(path)
    require_valid_gate_document(path, document)
    return ConfiguredGate(tuple(read_gate_config.normalize(document)["gates"]))


def require_gate_config_file(path: Path) -> None:
    if not path.is_file():
        raise GateBlocked([f"no {OVERRIDE_VARIABLE} and no gate configuration at {path}"])


def read_gate_document(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateBlocked([f"{path} could not be read as JSON: {error}"]) from error


def require_valid_gate_document(path: Path, document: object) -> None:
    problems = read_gate_config.validate(document)
    if problems:
        raise GateBlocked([f"{path}: {problem}" for problem in problems])


def print_gate(gate: Gate) -> int:
    print(json.dumps(gate.as_json(), indent=2))
    return EXIT_OK


def run_gate_with_kept_failure_logs(gate: Gate, repo: Path) -> int:
    log_dir = Path(tempfile.mkdtemp(prefix="tadw-ship-gate-"))
    code = run_gate(gate.checks(repo, log_dir), workers=os.cpu_count() or 1)
    discard_logs_when_passed(log_dir, code)
    return code


def discard_logs_when_passed(log_dir: Path, code: int) -> None:
    if code == EXIT_OK:
        shutil.rmtree(log_dir, ignore_errors=True)


def run_gate(checks: list[run_checks.Check], workers: int) -> int:
    outcome = run_checks.run_checks(checks, workers)
    print_check_lines(outcome)
    return report_gate_verdict(outcome)


def print_check_lines(outcome: run_checks.Outcome) -> None:
    for line in ship_report.check_lines(check_reports(outcome)):
        print(line, file=sys.stderr)


def check_reports(outcome: run_checks.Outcome) -> list[ship_report.CheckReport]:
    return [
        ship_report.report_check(result.name, result.status.value, result.log)
        for result in outcome.results
    ]


def report_gate_verdict(outcome: run_checks.Outcome) -> int:
    if gate_passed(outcome):
        return report_gate_passed(outcome)
    return stop_on_failed_gate(outcome)


def gate_passed(outcome: run_checks.Outcome) -> bool:
    """Ship's policy: every gate ran to its end and passed; anything else stops the ship."""
    return outcome.stopped_by is None and all(
        result.status is run_checks.Status.PASSED for result in outcome.results
    )


def report_gate_passed(outcome: run_checks.Outcome) -> int:
    count = len(outcome.results)
    print(f"tadw_ship: every gate passed, {count} of {count}")
    return EXIT_OK


def stop_on_failed_gate(outcome: run_checks.Outcome) -> int:
    if outcome.stopped_by is not None:
        print(f"tadw_ship: the gate was interrupted by {outcome.stopped_by.name}", file=sys.stderr)
    print("SHIP_BLOCKED gate")
    return EXIT_BLOCKED


def start_workflow(repo: Path) -> int:
    try:
        worktree_cleanup.stable_checkout(repo)
    except worktree_cleanup.NoStableCheckout as missing:
        return stop_without_stable_checkout(missing)
    return refuse_unbuilt_landing()


def refuse_missing_repository(repo: Path) -> int:
    print(f"tadw_ship: not a directory: {repo}", file=sys.stderr)
    return EXIT_OPERATOR_ERROR


def refuse_unbuilt_landing() -> int:
    print(
        "tadw_ship: the landing steps are not built yet (tadw-0jz2); "
        "only --check-gate and --run-gate run",
        file=sys.stderr,
    )
    return EXIT_OPERATOR_ERROR


def stop_without_stable_checkout(missing: worktree_cleanup.NoStableCheckout) -> int:
    print(f"tadw_ship: {missing}", file=sys.stderr)
    print(
        "tadw_ship: nothing was changed. Ship from a repository with a main checkout, "
        "because ship moves there before it removes any worktree.",
        file=sys.stderr,
    )
    print("SHIP_BLOCKED git-state")
    return EXIT_BLOCKED


def stop_on_gate(blocked: GateBlocked) -> int:
    for problem in blocked.problems:
        print(f"tadw_ship: {problem}", file=sys.stderr)
    print(f"tadw_ship: nothing was changed. {blocked.action}", file=sys.stderr)
    print("SHIP_BLOCKED gate")
    return EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
