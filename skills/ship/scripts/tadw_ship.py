#!/usr/bin/env python3
"""Ship a bead's branch without a model: the executable the ship skill will call.

This first stage selects the gate and stops. It resolves the gate before any
step that changes Git or tracker state, so a repository with no gate stops
with `SHIP_BLOCKED gate` having touched nothing. The landing steps come later
(tadw-9ed); until then only `--check-gate` runs to completion.

The gate comes from the first of these sources that is set:

1. `TADW_SHIP_CHECK`, one shell command, bounded by `TADW_SHIP_CHECK_TIMEOUT`
   (seconds, default 900). A blank value counts as unset, because an empty
   command would pass every ship.
2. `.tadw/ship-gates.json`, the versioned file docs/ship-gate-contract.md
   specifies. Each gate there carries its own `timeout`, and
   `TADW_SHIP_CHECK_TIMEOUT` does not apply to it.

No other source is read. Markdown is never parsed for a gate.

`--check-gate` is provisional: tadw-kgql settles the terminal flags.

Exit status: 0 when `--check-gate` found a gate (printed as JSON on stdout),
1 on a ship stop (the last stdout line is the machine line), 2 on operator
error, such as a repository path that does not exist.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


def load_sibling(name: str) -> ModuleType:
    """Load a helper from this file's own directory, never from another installed copy."""
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


read_gate_config = load_sibling("read_gate_config")

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


@dataclass(frozen=True)
class ConfiguredGate:
    """The normalized gates from `.tadw/ship-gates.json`, each carrying its own timeout."""

    gates: tuple[read_gate_config.NormalizedGate, ...]

    def as_json(self) -> dict:
        return {"source": str(read_gate_config.CONFIG_PATH), "gates": list(self.gates)}


def main(argv: list[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo_root)
    if not repo.is_dir():
        print(f"tadw_ship: not a directory: {repo}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    try:
        gate = resolve_gate(repo, os.environ if environ is None else environ)
    except GateBlocked as blocked:
        return stop_on_gate(blocked)

    if not args.check_gate:
        print(
            "tadw_ship: the landing steps are not built yet (tadw-9ed); only --check-gate runs",
            file=sys.stderr,
        )
        return EXIT_OPERATOR_ERROR
    print(json.dumps(gate.as_json(), indent=2))
    return EXIT_OK


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".", help="the repository to ship from")
    parser.add_argument(
        "--check-gate", action="store_true", help="select and validate the gate, print it, and stop"
    )
    return parser.parse_args(argv)


def resolve_gate(repo: Path, environ: Mapping[str, str]) -> OverrideGate | ConfiguredGate:
    override = environ.get(OVERRIDE_VARIABLE, "")
    if override.strip():
        return OverrideGate(override, override_timeout(environ.get(TIMEOUT_VARIABLE)))
    return configured_gate(repo)


def override_timeout(value: str | None) -> int:
    if value is None or not value.strip():
        return read_gate_config.DEFAULT_TIMEOUT_SECONDS
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
    if not path.is_file():
        raise GateBlocked([f"no {OVERRIDE_VARIABLE} and no gate configuration at {path}"])
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateBlocked([f"{path} could not be read as JSON: {error}"]) from error
    problems = read_gate_config.validate(document)
    if problems:
        raise GateBlocked([f"{path}: {problem}" for problem in problems])
    return ConfiguredGate(tuple(read_gate_config.normalize(document)["gates"]))


def stop_on_gate(blocked: GateBlocked) -> int:
    for problem in blocked.problems:
        print(f"tadw_ship: {problem}", file=sys.stderr)
    print(f"tadw_ship: nothing was changed. {blocked.action}", file=sys.stderr)
    print("SHIP_BLOCKED gate")
    return EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
