#!/usr/bin/env python3
"""Regression suite for the container rules in the bead body contract and its audit.

Stdlib only, no install, mirroring the other suites in this repository. Run with:
    python3 skills/bead-audit/scripts/test_container_contract.py

A container is a bead of type `epic` or `milestone`. It holds other beads and produces no diff of
its own. `docs/bead-body-contract.md` says what a container body carries, and
`skills/bead-audit/SKILL.md` says how the audit grades and scores it. Both are prose an agent
executes, so this suite reads the tables in the two real files and the two milestone fixtures. It
fails when the files stop agreeing with each other.

The groups follow the bead's acceptance criteria (tadw-5n2s.2), so a grader can cite a group by its
criterion number:

  criterion 1   a complete milestone passes with native design and notes, and needs no
                acceptance field and no diff estimate
  criterion 2   a milestone with no Success Criteria fails, and a missing size alone does not
  criterion 3   the score denominator leaves out the size weight for both container types
  criterion 4   task, feature, and bug keep native acceptance criteria and their estimates
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
CONTRACT = REPOSITORY / "docs" / "bead-body-contract.md"
AUDIT = REPOSITORY / "skills" / "bead-audit" / "SKILL.md"
FIXTURES = REPOSITORY / "skills" / "bead-audit" / "references" / "fixtures"
COMPLETE_MILESTONE = FIXTURES / "milestone-complete.md"
MILESTONE_WITHOUT_SUCCESS_CRITERIA = FIXTURES / "milestone-without-success-criteria.md"

CONTAINER_TYPES = ("epic", "milestone")
LEAF_TYPES = ("task", "feature", "bug")
ALL_TYPES = "all types"
CONTAINER_SECTIONS = {"Ask", "Why", "Success Criteria", "How", "Done when"}
LEAF_SECTIONS = {"Ask", "Why", "Estimated size", "How", "Done when", "Acceptance Criteria"}

TABLE_DIVIDER = re.compile(r"^\|[\s:|-]+\|$")
BACKTICKED = re.compile(r"`([^`]+)`")
EXPECTED_BLOCK = re.compile(r"<!--(.*?)-->", re.DOTALL)


def region(path: Path, name: str) -> str:
    """The text between the paired `<!-- name:start -->` and `<!-- name:end -->` comments."""
    text = path.read_text(encoding="utf-8")
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise AssertionError(f"{path.name} must hold exactly one {start} and one {end}")
    return text.split(start, 1)[1].split(end, 1)[0]


def table_rows(path: Path, name: str) -> list[list[str]]:
    """Every body row of the one table in the named region, as its list of cells."""
    lines = [line.strip() for line in region(path, name).splitlines()]
    rows = [line for line in lines if line.startswith("|") and not TABLE_DIVIDER.match(line)]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows[1:]]


def required_sections(bead_type: str) -> set[str]:
    """The sections the contract requires for the type."""
    return {
        section
        for section, _field, _heading, required_for in table_rows(CONTRACT, "section-table")
        if required_for == ALL_TYPES or bead_type in required_for.split(", ")
    }


def field_of(section: str) -> str:
    """The `bd` field the contract puts the section in."""
    fields = {row[0]: row[1] for row in table_rows(CONTRACT, "section-table")}
    return fields[section].strip("`")


def audited_sections(bead_type: str) -> str:
    """The audit's own cell naming the type-specific sections it requires for the type."""
    cells = {row[0].strip("`"): row[1] for row in table_rows(AUDIT, "type-sections")}
    return cells[bead_type]


def score_denominator(bead_type: str) -> int:
    """The sum of the audit's score weights that apply to the type."""
    return sum(
        int(weight)
        for _dimension, weight, applies_to in table_rows(AUDIT, "score-weights")
        if applies_to == ALL_TYPES or bead_type in BACKTICKED.findall(applies_to)
    )


def expected_block(fixture: Path) -> str:
    """The comment at the top of a fixture that records the verdict the audit must reach."""
    return EXPECTED_BLOCK.search(fixture.read_text(encoding="utf-8")).group(1)


def body_of(fixture: Path) -> str:
    """The fixture's bead, without the comment that records the expected verdict."""
    return EXPECTED_BLOCK.sub("", fixture.read_text(encoding="utf-8"), count=1)


def same(actual: object, expected: object) -> str:
    """Why the two differ, or an empty string when they are equal."""
    return "" if actual == expected else f"expected {expected!r}, got {actual!r}"


def holds(text: str, *needles: str) -> str:
    """Which needle the text is missing, or an empty string when it holds them all."""
    missing = [needle for needle in needles if needle not in text]
    return f"expected to find {missing!r}" if missing else ""


def leaves_out(text: str, *needles: str) -> str:
    """Which needle the text wrongly holds, or an empty string when it holds none."""
    found = [needle for needle in needles if needle in text]
    return f"expected to leave out {found!r}" if found else ""


def first_failure(*failures: str) -> str:
    return next((failure for failure in failures if failure), "")


def complete_container_requires_the_five_container_sections() -> str:
    return first_failure(
        *(same(required_sections(kind), CONTAINER_SECTIONS) for kind in CONTAINER_TYPES)
    )


def container_how_and_done_when_sit_in_native_design_and_notes() -> str:
    return first_failure(same(field_of("How"), "design"), same(field_of("Done when"), "notes"))


def complete_milestone_fixture_passes_with_no_acceptance_field_and_no_size() -> str:
    body = body_of(COMPLETE_MILESTONE)
    return first_failure(
        holds(expected_block(COMPLETE_MILESTONE), "overall PASS", "band Excellent"),
        holds(body, "Type: milestone", "design:", "notes:", "## Success Criteria"),
        leaves_out(body, "acceptance_criteria:", "## Estimated size"),
    )


def audit_requires_success_criteria_for_both_container_types() -> str:
    return first_failure(
        *(same(audited_sections(kind), "Success Criteria") for kind in CONTAINER_TYPES)
    )


def milestone_without_success_criteria_fixture_fails_on_that_section_alone() -> str:
    expected = expected_block(MILESTONE_WITHOUT_SUCCESS_CRITERIA)
    body = body_of(MILESTONE_WITHOUT_SUCCESS_CRITERIA)
    return first_failure(
        holds(expected, "overall NEEDS WORK", "Success Criteria: content fail", "size N/A"),
        holds(body, "Type: milestone"),
        leaves_out(body, "## Success Criteria", "## Estimated size"),
    )


def size_audit_marks_both_container_types_not_applicable() -> str:
    container_rule = region(AUDIT, "container-size")
    return holds(container_rule, "`epic`", "`milestone`", "N/A (umbrella)", "not a finding")


def container_denominator_leaves_out_the_size_weight() -> str:
    return first_failure(*(same(score_denominator(kind), 90) for kind in CONTAINER_TYPES))


def container_fixtures_record_the_denominator_of_90() -> str:
    return first_failure(
        holds(expected_block(COMPLETE_MILESTONE), "Denominator: 90"),
        holds(expected_block(MILESTONE_WITHOUT_SUCCESS_CRITERIA), "Denominator: 90"),
    )


def leaf_types_require_acceptance_criteria_and_an_estimate() -> str:
    return first_failure(
        same(required_sections("task"), LEAF_SECTIONS),
        same(required_sections("feature"), LEAF_SECTIONS),
        same(required_sections("bug"), LEAF_SECTIONS | {"Steps to Reproduce"}),
    )


def leaf_acceptance_criteria_sit_in_the_native_field() -> str:
    return first_failure(
        same(field_of("Acceptance Criteria"), "acceptance_criteria"),
        *(holds(audited_sections(kind), "Acceptance Criteria") for kind in LEAF_TYPES),
    )


def leaf_denominators_keep_the_size_weight() -> str:
    return first_failure(
        same(score_denominator("task"), 100),
        same(score_denominator("feature"), 100),
        same(score_denominator("bug"), 110),
    )


CRITERION_1 = "criterion 1: a complete milestone passes with native design and notes"
CRITERION_2 = "criterion 2: a missing Success Criteria fails, a missing size alone does not"
CRITERION_3 = "criterion 3: the denominator leaves out the size weight for both container types"
CRITERION_4 = "criterion 4: task, feature, and bug keep acceptance criteria and estimates"

CASES: list[tuple[str, Callable[[], str]]] = [
    (CRITERION_1, complete_container_requires_the_five_container_sections),
    (CRITERION_1, container_how_and_done_when_sit_in_native_design_and_notes),
    (CRITERION_1, complete_milestone_fixture_passes_with_no_acceptance_field_and_no_size),
    (CRITERION_2, audit_requires_success_criteria_for_both_container_types),
    (CRITERION_2, milestone_without_success_criteria_fixture_fails_on_that_section_alone),
    (CRITERION_2, size_audit_marks_both_container_types_not_applicable),
    (CRITERION_3, container_denominator_leaves_out_the_size_weight),
    (CRITERION_3, container_fixtures_record_the_denominator_of_90),
    (CRITERION_4, leaf_types_require_acceptance_criteria_and_an_estimate),
    (CRITERION_4, leaf_acceptance_criteria_sit_in_the_native_field),
    (CRITERION_4, leaf_denominators_keep_the_size_weight),
]


def failure_of(check: Callable[[], str]) -> str:
    """Why the check fails, or an empty string. A file the check cannot read is a failure."""
    try:
        return check()
    except (AssertionError, AttributeError, KeyError, OSError, ValueError) as error:
        return f"{type(error).__name__}: {error}"


def main() -> int:
    print("container contract tests:")
    failures = 0
    group = None

    for case_group, check in CASES:
        if case_group != group:
            group = case_group
            print(f"\n  [{group}]")
        failure = failure_of(check)
        if failure:
            failures += 1
            print(f"    NOT OK - {check.__name__}\n        {failure}")
        else:
            print(f"    ok - {check.__name__}")

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1

    print(f"\nAll {len(CASES)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
