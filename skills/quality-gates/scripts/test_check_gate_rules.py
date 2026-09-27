#!/usr/bin/env python3
"""Regression suite for check_gate_rules.py.

Stdlib only, no install, mirroring the other suites in this repository. Run with:
    python3 skills/quality-gates/scripts/test_check_gate_rules.py

Each group pins one rule from tadw-6pyo that lets two runs on one tree agree:

  PROJECT CHECKS EXAMPLES   no test suite sits under Project checks
  PROJECT CHECKS ROWS       one report row per command, never one row for all
  UNSELECTED SUITES         Gate 1 says what the report shows for a suite not run
  NARROWING                 lint with nothing to read is SKIP; doc freshness never narrows
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_gate_rules.py"
REAL_SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"

PASS, FAIL, ERROR = 0, 1, 2

WRITER_START = "<!-- quality-gates-writer:start -->"
WRITER_END = "<!-- quality-gates-writer:end -->"
REPORT_START = "<!-- quality-gates-report:start -->"
REPORT_END = "<!-- quality-gates-report:end -->"
PROJECT_START = "<!-- quality-gates-project-checks:start -->"
PROJECT_END = "<!-- quality-gates-project-checks:end -->"
GATE1_START = "<!-- quality-gates-gate1:start -->"
GATE1_END = "<!-- quality-gates-gate1:end -->"
SCOPE_START = "<!-- quality-gates-narrowing:start -->"
SCOPE_END = "<!-- quality-gates-narrowing:end -->"

VALIDATE = "claude plugin validate ."
ONE_ROW_PER_COMMAND = (
    "Each command gets its own report row, named by Naming Each Row in Step 4."
)

UNSELECTED_RULE = (
    "A suite that Step 2 did not select gets no report row. The Scope line counts it."
)
NARROWING_TABLE = "\n".join(
    [
        "| Gate | At `--changed` (default) | At `--all` |",
        "|---|---|---|",
        "| Lint | The changed files the tool reads. SKIP when there is no changed file it reads "
        "| Whole tree |",
        "| Doc freshness | The default document set, unchanged | The default document set |",
    ]
)


def json_gate(name: str, command: str) -> str:
    return f'    {{"name": "{name}", "status": "PASS", "command": "{command}", "detail": "ok"}}'


def table_gate(name: str, command: str) -> str:
    return f"| {name} | PASS | `{command}` | ok |"


def document(
    project_command: str = VALIDATE,
    project_prose: str = ONE_ROW_PER_COMMAND,
    gate1_prose: str = UNSELECTED_RULE,
    narrowing_table: str = NARROWING_TABLE,
) -> str:
    """Assemble a minimal document that satisfies every rule unless told not to."""
    return "\n".join(
        [
            SCOPE_START,
            "",
            narrowing_table,
            "",
            SCOPE_END,
            "",
            GATE1_START,
            "",
            gate1_prose,
            "",
            GATE1_END,
            "",
            PROJECT_START,
            "",
            project_prose,
            "",
            PROJECT_END,
            "",
            WRITER_START,
            "",
            "```bash",
            json_gate("Lint", "ruff check ."),
            json_gate("Project checks", project_command),
            "```",
            "",
            WRITER_END,
            "",
            REPORT_START,
            "",
            "```markdown",
            "| Gate | Status | Command | Result |",
            "|---|---|---|---|",
            table_gate("Lint", "ruff check ."),
            table_gate("Project checks", project_command),
            "```",
            "",
            REPORT_END,
            "",
        ]
    )


def run(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "SKILL.md"
        path.write_text(text, encoding="utf-8")
        return run_on(path)


def run_on(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)], capture_output=True, text=True, check=False
    )


# --- PROJECT CHECKS EXAMPLES ------------------------------------------------


def test_a_document_that_follows_every_rule_passes():
    assert run(document()).returncode == PASS


def test_a_test_suite_under_project_checks_fails():
    result = run(document(project_command="node hooks/test-hooks.js"))
    assert result.returncode == FAIL
    assert "node hooks/test-hooks.js" in result.stdout


def test_a_python_test_script_under_project_checks_fails():
    command = "python3 skills/ship/scripts/test_tadw_ship.py"
    assert run(document(project_command=command)).returncode == FAIL


def test_a_named_test_runner_under_project_checks_fails():
    assert run(document(project_command="pytest -q")).returncode == FAIL


# --- PROJECT CHECKS ROWS -----------------------------------------------------


def test_two_commands_in_one_project_checks_row_fails():
    result = run(document(project_command=f"{VALIDATE} && rumdl check ."))
    assert result.returncode == FAIL
    assert "one command" in result.stdout


def test_prose_that_gives_project_checks_a_single_row_fails():
    prose = "A command that fits no gate runs under a single **Project checks** row."
    result = run(document(project_prose=prose))
    assert result.returncode == FAIL
    assert "single" in result.stdout


def test_prose_that_never_says_one_row_per_command_fails():
    assert run(document(project_prose="The orchestrator owns it.")).returncode == FAIL


# --- UNSELECTED SUITES --------------------------------------------------------


def test_gate1_that_never_says_what_an_unselected_suite_shows_fails():
    result = run(document(gate1_prose="Every discovered suite gets its own row."))
    assert result.returncode == FAIL
    assert "did not select" in result.stdout


# --- NARROWING ----------------------------------------------------------------


def test_lint_that_never_says_what_happens_with_nothing_to_read_fails():
    table = NARROWING_TABLE.replace(
        "The changed files the tool reads. SKIP when there is no changed file it reads",
        "Changed files only",
    )
    result = run(document(narrowing_table=table))
    assert result.returncode == FAIL
    assert "no changed file it reads" in result.stdout


def test_doc_freshness_narrowed_to_changed_files_fails():
    table = NARROWING_TABLE.replace(
        "| Doc freshness | The default document set, unchanged |",
        "| Doc freshness | Changed files only |",
    )
    result = run(document(narrowing_table=table))
    assert result.returncode == FAIL
    assert "Doc freshness" in result.stdout


# --- THE SHIPPED SKILL --------------------------------------------------------


def test_the_shipped_skill_passes():
    result = run_on(REAL_SKILL)
    assert result.returncode == PASS, result.stdout + result.stderr


def main() -> int:
    tests = [(name, test) for name, test in globals().items() if name.startswith("test_")]
    failures = 0
    for name, test in tests:
        try:
            test()
        except AssertionError as error:
            failures += 1
            print(f"FAIL {name}: {error}")
        else:
            print(f"ok   {name}")
    print(f"\n{len(tests) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
