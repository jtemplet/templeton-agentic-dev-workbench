#!/usr/bin/env python3
"""Regression suite for ship_report.py.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_ship_report.py

Every case feeds the module the exact text a runner prints, or a log file in a
temporary directory, because the behavior under test is what the report says
about that text.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-a7r criterion                               Pinned by
  ------------------------------------------------------------------------------
  4. Unknown counts are marked unavailable          case_unknown_counts_are_unavailable
  4. ... and the canonical bead id is kept          case_report_names_the_bead
  5. A failed check's full output stays in its log  case_failed_check_names_its_log
  5. ... and the report carries a bounded excerpt   case_long_failure_is_bounded_in_lines,
                                                    case_long_failure_is_bounded_in_characters
  6. A known parser supplies the counts             case_pytest_counts_are_parsed,
                                                    case_unittest_counts_are_parsed,
                                                    case_house_suite_counts_are_parsed
  6. No known parser: counts unavailable            case_unrecognized_output_has_no_counts
  6. pytest errors count as failures                case_pytest_errors_count_as_failed

  Design decisions in the module docstring
  ------------------------------------------------------------------------------
  The machine line is the last line                 case_machine_line_is_last
  A passed check carries no excerpt                 case_passed_check_has_no_excerpt
  A short failure is quoted whole                   case_short_failure_is_quoted_whole
  A short subject is left alone                     case_short_subject_is_unchanged
  A long subject keeps its bead id                  case_long_subject_keeps_the_bead_id
  A long subject fits the limit                     case_long_subject_fits_the_limit
  A long subject is cut at a word boundary          case_long_subject_cuts_at_a_word
  A bead id longer than the limit is still kept     case_oversized_bead_id_is_kept

  tadw-kgql criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. The `cd` line comes before the machine line    case_cd_line_precedes_the_machine_line,
                                                    case_cd_line_quotes_a_path_with_spaces
  2. No removed start directory, no `cd` line       case_no_cd_target_prints_no_cd_line
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "ship_report.py"
spec = importlib.util.spec_from_file_location("ship_report", SCRIPT)
ship_report = importlib.util.module_from_spec(spec)
sys.modules["ship_report"] = ship_report
spec.loader.exec_module(ship_report)

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


PYTEST_OUTPUT = "collected 4 items\n\n===== 3 passed, 1 failed in 0.12s =====\n"
UNITTEST_OUTPUT = "..F.E\n------\nRan 5 tests in 0.004s\n\nFAILED (failures=1, errors=1)\n"
HOUSE_OUTPUT = "  ok   - one\n  FAIL - two\n\n1 FAILED, 12 passed.\n"
UNKNOWN_OUTPUT = "compiling...\nerror: something broke\n"
LONG_TITLE = "Resolve bead selection and workflow guards across every boundary the runner has"
BLOCKED = "SHIP_BLOCKED gate"


LOGS = tempfile.TemporaryDirectory()


def check_report_for(output: str, status: str = "failed"):
    """Write `output` to a fresh log, then report on it as a check with `status`."""
    log = Path(tempfile.mkstemp(suffix=".log", dir=LOGS.name)[1])
    log.write_text(output, encoding="utf-8")
    return ship_report.report_check("suite", status, log)


def rendered(bead_id, output: str) -> list[str]:
    result = ship_report.ShipResult(bead_id, (check_report_for(output),), BLOCKED)
    return ship_report.render(result)


def case_unknown_counts_are_unavailable():
    lines = rendered("tadw-a7r", UNKNOWN_OUTPUT)
    assert ship_report.COUNTS_UNAVAILABLE in lines[1], lines


def case_report_names_the_bead():
    lines = rendered("tadw-a7r", UNKNOWN_OUTPUT)
    assert lines[0] == "tadw_ship: bead tadw-a7r", lines


def case_failed_check_names_its_log():
    report = check_report_for(UNKNOWN_OUTPUT)
    line = ship_report.render(ship_report.ShipResult(None, (report,), BLOCKED))[1]
    assert f"log: {report.log}" in line, line


def case_long_failure_is_bounded_in_lines():
    output = "\n".join(f"line {number}" for number in range(500))
    excerpt = check_report_for(output).excerpt
    assert len(excerpt.splitlines()) == ship_report.EXCERPT_MAX_LINES + 1, len(excerpt.splitlines())


def case_long_failure_is_bounded_in_characters():
    output = "x" * 50_000
    excerpt = check_report_for(output).excerpt
    body = excerpt.splitlines()[-1]
    assert len(body) == ship_report.EXCERPT_MAX_CHARACTERS, len(body)


def case_short_failure_is_quoted_whole():
    assert check_report_for(UNKNOWN_OUTPUT).excerpt == UNKNOWN_OUTPUT.rstrip("\n")


def case_passed_check_has_no_excerpt():
    assert check_report_for(PYTEST_OUTPUT, status="passed").excerpt is None


def case_pytest_counts_are_parsed():
    assert ship_report.parse_counts(PYTEST_OUTPUT) == ship_report.Counts(3, 1)


def case_unittest_counts_are_parsed():
    assert ship_report.parse_counts(UNITTEST_OUTPUT) == ship_report.Counts(3, 2)


def case_house_suite_counts_are_parsed():
    assert ship_report.parse_counts(HOUSE_OUTPUT) == ship_report.Counts(12, 1)


def case_pytest_errors_count_as_failed():
    output = "===== 1 passed, 2 errors in 0.30s =====\n"
    assert ship_report.parse_counts(output) == ship_report.Counts(1, 2)


def case_unrecognized_output_has_no_counts():
    assert ship_report.parse_counts(UNKNOWN_OUTPUT) is None


def case_machine_line_is_last():
    assert rendered(None, UNKNOWN_OUTPUT)[-1] == BLOCKED


def rendered_with_cd(target: Path | None) -> list[str]:
    return ship_report.render(ship_report.ShipResult("tadw-kgql", (), BLOCKED, target))


def case_cd_line_precedes_the_machine_line():
    lines = rendered_with_cd(Path("/work/repo"))
    assert lines[-2:] == ["cd /work/repo", BLOCKED], lines


def case_cd_line_quotes_a_path_with_spaces():
    lines = rendered_with_cd(Path("/work/my repo"))
    assert lines[-2] == "cd '/work/my repo'", lines


def case_no_cd_target_prints_no_cd_line():
    lines = rendered_with_cd(None)
    assert not [line for line in lines if line.startswith("cd ")], lines


def case_short_subject_is_unchanged():
    subject = ship_report.commit_subject("feat", "Add a flag", "tadw-a7r")
    assert subject == "feat: Add a flag (tadw-a7r)", subject


def case_long_subject_keeps_the_bead_id():
    subject = ship_report.commit_subject("feat", LONG_TITLE, "tadw-a7r")
    assert subject.endswith("... (tadw-a7r)"), subject


def case_long_subject_fits_the_limit():
    subject = ship_report.commit_subject("feat", LONG_TITLE, "tadw-a7r")
    assert len(subject) <= ship_report.SUBJECT_MAX_CHARACTERS, len(subject)


def case_long_subject_cuts_at_a_word():
    subject = ship_report.commit_subject("feat", LONG_TITLE, "tadw-a7r")
    kept = subject.removeprefix("feat: ").removesuffix("... (tadw-a7r)")
    assert LONG_TITLE.startswith(kept + " "), subject


def case_oversized_bead_id_is_kept():
    bead_id = "tadw-" + "x" * 80
    subject = ship_report.commit_subject("feat", LONG_TITLE, bead_id)
    assert subject == f"feat: ... ({bead_id})", subject


for name, fn in [
    ("unknown counts are marked unavailable", case_unknown_counts_are_unavailable),
    ("the report names the canonical bead id", case_report_names_the_bead),
    ("a failed check names the log holding its output", case_failed_check_names_its_log),
    ("a long failure is bounded in lines", case_long_failure_is_bounded_in_lines),
    ("a long failure is bounded in characters", case_long_failure_is_bounded_in_characters),
    ("a short failure is quoted whole", case_short_failure_is_quoted_whole),
    ("a passed check carries no excerpt", case_passed_check_has_no_excerpt),
    ("pytest's summary supplies the counts", case_pytest_counts_are_parsed),
    ("unittest's summary supplies the counts", case_unittest_counts_are_parsed),
    ("this repository's suite summary supplies the counts", case_house_suite_counts_are_parsed),
    ("output no parser knows has no counts", case_unrecognized_output_has_no_counts),
    ("pytest errors count as failures", case_pytest_errors_count_as_failed),
    ("a bead id longer than the limit is still kept", case_oversized_bead_id_is_kept),
    ("the machine line is the last line", case_machine_line_is_last),
    ("the cd line comes right before the machine line", case_cd_line_precedes_the_machine_line),
    ("the cd line quotes a path with spaces", case_cd_line_quotes_a_path_with_spaces),
    ("no cd target prints no cd line", case_no_cd_target_prints_no_cd_line),
    ("a short subject is left alone", case_short_subject_is_unchanged),
    ("a long subject keeps its bead id", case_long_subject_keeps_the_bead_id),
    ("a long subject fits the limit", case_long_subject_fits_the_limit),
    ("a long subject is cut at a word boundary", case_long_subject_cuts_at_a_word),
]:
    check(name, fn)

LOGS.cleanup()
print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
