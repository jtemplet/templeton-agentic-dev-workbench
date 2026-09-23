#!/usr/bin/env python3
"""Regression suite for read_gate_config.py.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_read_gate_config.py

  tadw-lc9 criterion                                Pinned by
  ------------------------------------------------------------------------------
  1. A valid gate fixture, when read, identifies    case_valid_fixture_names_commands_and_inputs
     the configured commands and their inputs
  Defaults are filled, so no reader guesses         case_absent_keys_take_their_defaults
  Reuse needs declared inputs                       case_reuse_without_inputs_is_off
  An invalid file exits 1 and names every problem   case_invalid_file_exits_1_and_prints_no_config,
                                                    case_invalid_file_names_every_problem_at_once,
                                                    case_unsupported_version_is_invalid,
                                                    case_dependency_on_unknown_gate_is_invalid,
                                                    case_parent_relative_cwd_is_invalid,
                                                    case_absolute_cwd_is_invalid
  A dependency loop would deadlock a scheduler      case_self_dependency_is_invalid,
                                                    case_dependency_cycle_is_invalid,
                                                    case_shared_dependency_is_not_a_cycle
  Operator error is 2, never 1                      case_missing_file_exits_2
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "read_gate_config.py"

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


def read(document: object) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory) / ".tadw" / "ship-gates.json"
        config.parent.mkdir()
        config.write_text(json.dumps(document), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", directory],
            capture_output=True, text=True, check=False,
        )


def valid_gate(**overrides: object) -> dict:
    return {"name": "markdown-format", "command": ["rumdl", "fmt", "--check", "."], **overrides}


def case_valid_fixture_names_commands_and_inputs() -> None:
    result = read({"version": 1, "gates": [
        valid_gate(inputs=["**/*.md", ".rumdl.toml"]),
        {"name": "hook-suite", "command": ["node", "hooks/test-hooks.js"],
         "inputs": ["hooks/**"], "depends_on": ["markdown-format"], "resources": ["tracker"]},
    ]})
    assert result.returncode == 0, result.stderr
    gates = json.loads(result.stdout)["gates"]
    assert [g["command"] for g in gates] == [["rumdl", "fmt", "--check", "."],
                                             ["node", "hooks/test-hooks.js"]]
    assert gates[0]["inputs"] == ["**/*.md", ".rumdl.toml"]
    assert gates[1]["inputs"] == ["hooks/**"]
    assert gates[1]["depends_on"] == ["markdown-format"]
    assert gates[1]["resources"] == ["tracker"]


def case_absent_keys_take_their_defaults() -> None:
    gate = json.loads(read({"version": 1, "gates": [valid_gate()]}).stdout)["gates"][0]
    assert gate["cwd"] == "." and gate["timeout"] == 900
    assert gate["inputs"] == [] and gate["depends_on"] == [] and gate["resources"] == []
    assert gate["reuse"] is False


def case_reuse_without_inputs_is_off() -> None:
    gates = json.loads(read({"version": 1, "gates": [
        valid_gate(reuse=True),
        valid_gate(name="with-inputs", reuse=True, inputs=["a"]),
    ]}).stdout)["gates"]
    assert gates[0]["reuse"] is False, "a gate with no declared inputs must never be reused"
    assert gates[1]["reuse"] is True


def invalid_file_result() -> subprocess.CompletedProcess:
    return read({"version": 1, "gates": [
        {"name": "", "command": []},
        valid_gate(name="twin"), valid_gate(name="twin", timeout=0, surprise=1),
    ]})


def case_invalid_file_exits_1_and_prints_no_config() -> None:
    result = invalid_file_result()
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    assert result.stdout == "", "an invalid file must print no configuration"


def case_invalid_file_names_every_problem_at_once() -> None:
    stderr = invalid_file_result().stderr
    for expected in ("gates[0].name", "gates[0].command", "appears more than once",
                     "gates[2].timeout", "unknown keys: surprise"):
        assert expected in stderr, f"missing problem {expected!r} in:\n{stderr}"


def case_unsupported_version_is_invalid() -> None:
    result = read({"version": 2, "gates": [valid_gate()]})
    assert result.returncode == 1 and "version must be 1" in result.stderr


def case_dependency_on_unknown_gate_is_invalid() -> None:
    result = read({"version": 1, "gates": [valid_gate(depends_on=["ghost"])]})
    assert result.returncode == 1 and "'ghost'" in result.stderr


def cwd_problem(cwd: str) -> subprocess.CompletedProcess:
    return read({"version": 1, "gates": [valid_gate(cwd=cwd)]})


def case_parent_relative_cwd_is_invalid() -> None:
    result = cwd_problem("../outside")
    assert result.returncode == 1 and "cwd" in result.stderr


def case_absolute_cwd_is_invalid() -> None:
    result = cwd_problem("/etc")
    assert result.returncode == 1 and "cwd" in result.stderr


def case_self_dependency_is_invalid() -> None:
    result = read({"version": 1, "gates": [valid_gate(depends_on=["markdown-format"])]})
    assert result.returncode == 1 and "the gate itself" in result.stderr


def case_dependency_cycle_is_invalid() -> None:
    result = read({"version": 1, "gates": [
        valid_gate(name="a", depends_on=["b"]), valid_gate(name="b", depends_on=["c"]),
        valid_gate(name="c", depends_on=["a"]),
    ]})
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    assert "cycle: a -> b -> c -> a" in result.stderr, result.stderr


def case_shared_dependency_is_not_a_cycle() -> None:
    result = read({"version": 1, "gates": [
        valid_gate(name="base"), valid_gate(name="left", depends_on=["base"]),
        valid_gate(name="right", depends_on=["base"]),
        valid_gate(name="top", depends_on=["left", "right"]),
    ]})
    assert result.returncode == 0, result.stderr


def case_missing_file_exits_2() -> None:
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo-root", directory],
                                capture_output=True, text=True, check=False)
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}"


for name, fn in [
    ("a valid fixture names its commands and inputs", case_valid_fixture_names_commands_and_inputs),
    ("absent keys take their documented defaults", case_absent_keys_take_their_defaults),
    ("reuse is off for a gate with no declared inputs", case_reuse_without_inputs_is_off),
    ("an invalid file exits 1 and prints no configuration",
     case_invalid_file_exits_1_and_prints_no_config),
    ("an invalid file names every problem at once", case_invalid_file_names_every_problem_at_once),
    ("an unsupported version is invalid", case_unsupported_version_is_invalid),
    ("a dependency on an unknown gate is invalid", case_dependency_on_unknown_gate_is_invalid),
    ("a parent-relative cwd is invalid", case_parent_relative_cwd_is_invalid),
    ("an absolute cwd is invalid", case_absolute_cwd_is_invalid),
    ("a gate depending on itself is invalid", case_self_dependency_is_invalid),
    ("a dependency cycle is invalid and named", case_dependency_cycle_is_invalid),
    ("a shared dependency is not a cycle", case_shared_dependency_is_not_a_cycle),
    ("a missing file exits 2", case_missing_file_exits_2),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
