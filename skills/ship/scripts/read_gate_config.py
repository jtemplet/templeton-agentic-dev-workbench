#!/usr/bin/env python3
"""Read and validate a repository's ship gate configuration, and print it as JSON.

The configuration is `.tadw/ship-gates.json`. Its format is versioned and
specified in docs/ship-gate-contract.md. It is plain JSON so that no reader
needs a third-party parser, and it never depends on Markdown: the gate is what
the file says, not what a document is read to mean.

Each gate names one command as an argument list (never a shell string, so no
quoting rule applies) and the inputs that command's result depends on. The
inputs are what a later result-reuse rule will compare, so a gate that leaves
them empty declares "I cannot say", and its result is never reused.

Exit status: 0 when the file is valid, 1 when it is invalid (each problem is
printed to stderr, all of them at once), 2 when there is no configuration file,
including when the repository path does not exist.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict

EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_OPERATOR_ERROR = 2

SUPPORTED_VERSION = 1
CONFIG_PATH = Path(".tadw") / "ship-gates.json"
DEFAULT_TIMEOUT_SECONDS = 900

GATE_KEYS = frozenset(
    ["name", "command", "inputs", "cwd", "timeout", "depends_on", "resources", "reuse"]
)


class NormalizedGate(TypedDict):
    """One gate with every default filled in, as `normalize` returns it."""

    name: str
    command: list[str]
    inputs: list[str]
    cwd: str
    timeout: int
    depends_on: list[str]
    resources: list[str]
    reuse: bool


class GateConfigError(Exception):
    """The configuration is invalid; `problems` names every one of them."""

    exit_code = EXIT_INVALID

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class MissingGateConfig(GateConfigError):
    exit_code = EXIT_OPERATOR_ERROR


def main(argv: list[str] | None = None) -> int:
    try:
        gates = load_gates(Path(parse_args(argv).repo_root))
    except GateConfigError as error:
        return report_problems(error)
    print(json.dumps({"version": SUPPORTED_VERSION, "gates": gates}, indent=2))
    return EXIT_VALID


def load_gates(repo: Path) -> list[NormalizedGate]:
    """The configured gates with every default filled in, or a `GateConfigError`."""
    path = repo / CONFIG_PATH
    document = read_document(path)
    require_valid(path, document)
    return normalize(document)["gates"]


def read_document(path: Path) -> object:
    if not path.is_file():
        raise MissingGateConfig([f"no gate configuration at {path}"])
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateConfigError([f"{path} could not be read as JSON: {error}"]) from error


def require_valid(path: Path, document: object) -> None:
    problems = validate(document)
    if problems:
        raise GateConfigError([f"{path}: {problem}" for problem in problems])


def report_problems(error: GateConfigError) -> int:
    for problem in error.problems:
        print(f"read_gate_config: {problem}", file=sys.stderr)
    return error.exit_code


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".", help="repository holding .tadw/ship-gates.json")
    return parser.parse_args(argv)


def validate(document: object) -> list[str]:
    if not isinstance(document, dict):
        return ["the top level must be an object"]
    problems: list[str] = []
    if document.get("version") != SUPPORTED_VERSION:
        problems.append(f"version must be {SUPPORTED_VERSION}, found {document.get('version')!r}")
    gates = document.get("gates")
    if not isinstance(gates, list) or not gates:
        return problems + ["gates must be a non-empty list"]

    names = [gate.get("name") for gate in gates if isinstance(gate, dict)]
    for index, gate in enumerate(gates):
        problems += validate_gate(index, gate, names)
    duplicated = sorted({name for name in names if names.count(name) > 1})
    problems += [f"gate name {name!r} appears more than once" for name in duplicated]
    if not problems:
        cycle = find_cycle(normalize(document)["gates"])
        if cycle:
            problems.append(f"depends_on forms a cycle: {' -> '.join(cycle)}")
    return problems


def validate_gate(index: int, gate: object, names: list[object]) -> list[str]:
    where = f"gates[{index}]"
    if not isinstance(gate, dict):
        return [f"{where} must be an object"]
    problems: list[str] = []
    unknown = sorted(set(gate) - GATE_KEYS)
    if unknown:
        problems.append(f"{where} has unknown keys: {', '.join(unknown)}")
    if not is_text(gate.get("name")):
        problems.append(f"{where}.name must be a non-empty string")
    if not is_text_list(gate.get("command")) or not gate.get("command"):
        problems.append(f"{where}.command must be a non-empty list of strings")
    for key in ("inputs", "resources", "depends_on"):
        if key in gate and not is_text_list(gate[key]):
            problems.append(f"{where}.{key} must be a list of strings")
    problems += validate_dependencies(where, gate, names)
    if "cwd" in gate and not is_relative_inside(gate["cwd"]):
        problems.append(f"{where}.cwd must be a relative path that stays inside the repository")
    timeout = gate.get("timeout", DEFAULT_TIMEOUT_SECONDS)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        problems.append(f"{where}.timeout must be a positive whole number of seconds")
    if "reuse" in gate and not isinstance(gate["reuse"], bool):
        problems.append(f"{where}.reuse must be true or false")
    return problems


def validate_dependencies(where: str, gate: dict, names: list[object]) -> list[str]:
    dependencies = gate.get("depends_on", [])
    if not is_text_list(dependencies):
        return []
    problems = []
    for dependency in dependencies:
        if dependency == gate.get("name"):
            problems.append(f"{where}.depends_on names the gate itself")
        elif dependency not in names:
            problems.append(f"{where}.depends_on names {dependency!r}, which is not a gate")
    return problems


def find_cycle(gates: list[NormalizedGate]) -> list[str]:
    """Return the names on one dependency cycle, or an empty list when there is none."""
    graph = {g["name"]: g["depends_on"] for g in gates}
    finished: set[str] = set()

    def visit(name: str, path: list[str]) -> list[str]:
        if name in path:
            return path[path.index(name) :] + [name]
        if name in finished:
            return []
        for dependency in graph.get(name, []):
            cycle = visit(dependency, path + [name])
            if cycle:
                return cycle
        finished.add(name)
        return []

    for name in graph:
        cycle = visit(name, [])
        if cycle:
            return cycle
    return []


def normalize(document: dict) -> dict:
    """Fill each default, so a reader never has to know what an absent key means."""
    return {
        "version": document["version"],
        "gates": [
            NormalizedGate(
                name=gate["name"],
                command=gate["command"],
                inputs=gate.get("inputs", []),
                cwd=gate.get("cwd", "."),
                timeout=gate.get("timeout", DEFAULT_TIMEOUT_SECONDS),
                depends_on=gate.get("depends_on", []),
                resources=gate.get("resources", []),
                reuse=gate.get("reuse", False) and bool(gate.get("inputs")),
            )
            for gate in document["gates"]
        ],
    }


def is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_text_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def is_relative_inside(value: object) -> bool:
    if not is_text(value):
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


if __name__ == "__main__":
    sys.exit(main())
