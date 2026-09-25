#!/usr/bin/env python3
"""Regression suite for write_acceptance_report.py.

Stdlib only, no install, and no git repository. Run with:
    python3 skills/verify-acceptance/scripts/test_write_acceptance_report.py

Nearly every case runs in-process: `build()` and the cap cases call the pure
functions with dicts, and `run_cli()` calls `main()` with an argument list, a
stdin buffer, and two output buffers. Every `--out` is a fresh path in its own
`tempfile.mkdtemp()` directory, so "writes nothing" means that directory stays
empty. The "[through a real subprocess]" group is the exception, on purpose: it
invokes `python3 write_acceptance_report.py ...` the way the verify-acceptance
skill will, so the CLI surface has a test that drives its real entry point. The
script may never import subprocess; this suite may, and does, for that group.

THE CONSUMER IS TESTED, NOT ASSUMED. `reconcile-acceptance` reads this file
through `load_findings.py`, and ADR 0011 calls that shape a contract between two
repositories. `case_written_report_satisfies_the_consumer` loads the real loader
and hands it the text this writer produced, so a field this writer renames fails
here rather than in outrigger.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-gky criterion                             Pinned by
  ------------------------------------------------------------------------------
  1. Valid input exits 0, and the file holds     the [with a valid report] group
     version 2, head, base, changed_files,
     criteria, gates, and the seven counts
  2. Counts that disagree with the rows exit 1   the [with a count the rows do not
     and write nothing                           give] group
  3. A `verdict` field exits 1 and writes        the [with a verdict field] group
     nothing
  4. Evidence over 20 lines or 2,000 characters  the [with evidence over the cap]
     is capped before a trimmed line             group
  5. No subprocess in the script                 case_script_never_names_subprocess
  6. AGENTS.md names this suite                  case_agents_md_lists_this_suite
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "write_acceptance_report.py"
REPO = HERE.parents[2]
CONSUMER = REPO / "skills" / "reconcile-acceptance" / "scripts" / "load_findings.py"


def load(name: str, path: Path):
    """The module at `path`, loaded under `name` without a package or an install."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


writer = load("write_acceptance_report", SCRIPT)
consumer = load("acceptance_load_findings", CONSUMER)

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


HEAD = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
BASE = {"ref": "origin/HEAD", "sha": "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"}
CHANGED = ["skills/ship/SKILL.md", "skills/ship/scripts/check_worktree_occupants.py"]
FACTS = writer.RunFacts(HEAD, tuple(CHANGED))

COUNT_FIELDS = writer.COUNT_FIELDS
STDIN_FIELDS = ("bead", "base", *COUNT_FIELDS, "criteria", "gates")
REPORT_FIELDS = (
    "version",
    "head",
    "bead",
    "base",
    "changed_files",
    *COUNT_FIELDS,
    "criteria",
    "gates",
)


def criterion(number: int = 1, verdict: str = "PASS", **overrides) -> dict:
    body = {
        "number": number,
        "text": f"Criterion {number}, as the bead states it.",
        "verdict": verdict,
        "evidence": "test_rejects_expired_token passed, 3 passed 0 failed",
        "command": "python3 -m pytest -k expired",
    }
    body.update(overrides)
    return body


def gate(name: str = "Tests", status: str = "PASS", **overrides) -> dict:
    body = {
        "name": name,
        "status": status,
        "command": "python3 -m pytest",
        "detail": f"{name}: 218 passed, 0 failed",
    }
    body.update(overrides)
    return body


def fields(**overrides) -> dict:
    """A stdin object that passes every check: three graded criteria over two gates."""
    body = {
        "bead": "tadw-gky",
        "base": BASE,
        "criteria_total": 3,
        "criteria_passed": 1,
        "criteria_failed": 1,
        "criteria_unverifiable": 1,
        "gates_total": 2,
        "gates_failed": 1,
        "gates_blocked": 0,
        "criteria": [criterion(1, "PASS"), criterion(2, "FAIL"), criterion(3, "UNVERIFIABLE")],
        "gates": [gate("Tests", "PASS"), gate("Lint", "FAIL")],
    }
    body.update(overrides)
    return body


def build(body: dict, facts=FACTS) -> dict:
    return writer.build_report(body, facts)


def fresh_out() -> Path:
    return Path(tempfile.mkdtemp()).resolve() / "acceptance-report.json"


WORKDIR = Path(tempfile.mkdtemp()).resolve()
CHANGED_FILE = WORKDIR / "acceptance-changed.txt"
CHANGED_FILE.write_text("\n".join(CHANGED) + "\n", encoding="utf-8")


def arguments(out: Path, **overrides: str | None) -> list[str]:
    """The argument list for a valid run, with any flag replaced or, given None, left out."""
    values = {"out": str(out), "head": HEAD, "changed_files": str(CHANGED_FILE)}
    values.update(overrides)
    argv: list[str] = []
    for name, value in values.items():
        if value is not None:
            argv += ["--" + name.replace("_", "-"), value]
    return argv


def run_cli(body: dict | list | str, argv: list[str]) -> tuple[int, str, str]:
    """The writer's process-boundary behavior: argv and stdin in, exit code and streams out."""
    text = body if isinstance(body, str) else json.dumps(body)
    out, err = io.StringIO(), io.StringIO()
    code = writer.main(argv, io.StringIO(text), out, err)
    return code, out.getvalue(), err.getvalue()


def written(out: Path) -> dict:
    return json.loads(out.read_text(encoding="utf-8"))


def nothing_written(out: Path) -> bool:
    return not out.parent.exists() or not any(out.parent.iterdir())


def refused(body: dict | list | str, **overrides: str | None) -> str:
    """stderr from a run that must exit 1 and leave its --out directory empty."""
    out = fresh_out()
    code, _, err = run_cli(body, arguments(out, **overrides))
    assert code == 1, f"must exit 1, got {code}: {err!r}"
    assert nothing_written(out), f"a refusal must write nothing: {list(out.parent.iterdir())}"
    return err


def usage_error(body: dict, out: Path | None = None, **overrides: str | None) -> str:
    """stderr from a run that must exit 2 and leave its --out directory empty."""
    out = out or fresh_out()
    code, _, err = run_cli(body, arguments(out, **overrides))
    assert code == 2, f"must exit 2, got {code}: {err!r}"
    assert nothing_written(out), "a usage error must write nothing"
    return err


print("\n  [with a valid report]")

VALID_OUT = fresh_out()
VALID_RUN = run_cli(fields(), arguments(VALID_OUT))


def case_valid_input_exits_0_and_prints_the_path() -> None:
    code, out, err = VALID_RUN
    assert code == 0, f"must exit 0, got {code}: {err!r}"
    assert out.strip() == str(VALID_OUT), f"stdout must name the written path: {out!r}"


def case_written_file_is_version_2() -> None:
    assert written(VALID_OUT)["version"] == 2


def case_written_file_holds_every_documented_field() -> None:
    missing = [name for name in REPORT_FIELDS if name not in written(VALID_OUT)]
    assert not missing, f"the file lacks version 2 fields: {missing}"


def case_injected_values_are_written() -> None:
    report = written(VALID_OUT)
    injected = {name: report[name] for name in ("head", "changed_files")}
    assert injected == {"head": HEAD, "changed_files": CHANGED}, f"got {injected}"


def case_stdin_values_are_written() -> None:
    report = written(VALID_OUT)
    assert (report["bead"], report["base"]) == ("tadw-gky", BASE)


def case_the_seven_counts_are_written() -> None:
    report = written(VALID_OUT)
    counts = {name: report[name] for name in COUNT_FIELDS}
    assert counts == {name: fields()[name] for name in COUNT_FIELDS}, f"got {counts}"


def case_criteria_keep_their_text_verdict_evidence_and_command() -> None:
    rows = written(VALID_OUT)["criteria"]
    assert [row["number"] for row in rows] == [1, 2, 3], rows
    assert rows[1] == criterion(2, "FAIL"), rows[1]


def case_gates_are_written_unchanged() -> None:
    assert written(VALID_OUT)["gates"] == [gate("Tests", "PASS"), gate("Lint", "FAIL")]


def case_fields_are_written_in_the_documented_order() -> None:
    assert list(written(VALID_OUT)) == list(REPORT_FIELDS)


def case_file_is_indented_json_ending_in_a_newline() -> None:
    text = VALID_OUT.read_text(encoding="utf-8")
    assert text == json.dumps(written(VALID_OUT), indent=2) + "\n"


def case_rename_leaves_no_temporary_file() -> None:
    assert [p.name for p in VALID_OUT.parent.iterdir()] == [VALID_OUT.name]


def case_written_report_satisfies_the_consumer() -> None:
    report = consumer.parse_report(VALID_OUT.read_text(encoding="utf-8"))
    assert report["criteria"][1]["verdict"] == "FAIL", report["criteria"][1]


def case_null_base_without_changed_files_writes_null() -> None:
    facts = writer.RunFacts(HEAD, None)
    report = build(fields(base=None), facts)
    assert (report["base"], report["changed_files"]) == (None, None)


def case_null_bead_is_written_as_null() -> None:
    assert build(fields(bead=None))["bead"] is None


def case_head_is_written_without_surrounding_space() -> None:
    out = fresh_out()
    run_cli(fields(), arguments(out, head=f"  {HEAD}\n"))
    assert written(out)["head"] == HEAD


def case_changed_files_skips_blank_lines_and_keeps_paths_verbatim() -> None:
    listing = WORKDIR / "spaced-changed.txt"
    listing.write_text("docs/a file.md\n\n  \nsrc/app.py\n", encoding="utf-8")
    out = fresh_out()
    run_cli(fields(), arguments(out, changed_files=str(listing)))
    assert written(out)["changed_files"] == ["docs/a file.md", "src/app.py"]


def case_empty_changed_files_writes_an_empty_list() -> None:
    listing = WORKDIR / "empty-changed.txt"
    listing.write_text("", encoding="utf-8")
    out = fresh_out()
    run_cli(fields(), arguments(out, changed_files=str(listing)))
    assert written(out)["changed_files"] == []


def case_a_report_grading_nothing_is_valid() -> None:
    body = fields(criteria=[], gates=[], **dict.fromkeys(COUNT_FIELDS, 0))
    report = build(body)
    assert (report["criteria"], report["gates"], report["criteria_total"]) == ([], [], 0)


def case_existing_report_is_replaced() -> None:
    out = fresh_out()
    out.write_text('{"version": 1, "bead": "tadw-old"}\n', encoding="utf-8")
    run_cli(fields(), arguments(out))
    assert written(out)["version"] == 2


for name, fn in [
    (
        "valid input exits 0 and prints the written path [criterion 1]",
        case_valid_input_exits_0_and_prints_the_path,
    ),
    ("the written file is version 2 [criterion 1]", case_written_file_is_version_2),
    (
        "the written file holds every version 2 field [criterion 1]",
        case_written_file_holds_every_documented_field,
    ),
    (
        "head and changed_files come from the arguments [criterion 1]",
        case_injected_values_are_written,
    ),
    ("bead and base come from stdin [criterion 1]", case_stdin_values_are_written),
    ("the seven counts are written [criterion 1]", case_the_seven_counts_are_written),
    (
        "each criterion keeps its text, verdict, evidence, and command [criterion 1]",
        case_criteria_keep_their_text_verdict_evidence_and_command,
    ),
    ("each gate row is written unchanged [criterion 1]", case_gates_are_written_unchanged),
    (
        "the fields are written in the documented order",
        case_fields_are_written_in_the_documented_order,
    ),
    (
        "the file is indented JSON ending in a newline",
        case_file_is_indented_json_ending_in_a_newline,
    ),
    ("the rename leaves no temporary file", case_rename_leaves_no_temporary_file),
    (
        "load_findings.py accepts the written report [ADR 0011 contract]",
        case_written_report_satisfies_the_consumer,
    ),
    (
        "a null base with no --changed-files writes both as null",
        case_null_base_without_changed_files_writes_null,
    ),
    ("a null bead is written as null", case_null_bead_is_written_as_null),
    (
        "--head is written without surrounding space",
        case_head_is_written_without_surrounding_space,
    ),
    (
        "--changed-files skips blank lines and keeps each path verbatim",
        case_changed_files_skips_blank_lines_and_keeps_paths_verbatim,
    ),
    (
        "an empty --changed-files file writes an empty list",
        case_empty_changed_files_writes_an_empty_list,
    ),
    ("empty criteria and gates with zero counts are valid", case_a_report_grading_nothing_is_valid),
    ("an existing report at --out is replaced", case_existing_report_is_replaced),
]:
    check(name, fn)

print("\n  [with a count the rows do not give]")


def count_case(count: str):
    """One case per count: raise that count alone, and the rows no longer give it."""

    def case() -> None:
        tally = fields()[count]
        err = refused(fields(**{count: tally + 1}))
        assert f"`{count}` is {tally + 1}, and the rows count {tally}." in err, err

    return case


def case_a_lowered_count_is_refused() -> None:
    err = refused(fields(criteria_total=2))
    assert "`criteria_total` is 2, and the rows count 3." in err, err


def case_counts_that_would_read_accepted_over_a_fail_are_refused() -> None:
    """The failure this check exists to prevent: an ACCEPTED-shaped count set."""
    body = fields(criteria_total=3, criteria_passed=3, criteria_failed=0, criteria_unverifiable=0)
    err = refused(dict(body, gates_failed=0))
    assert "`criteria_passed` is 3, and the rows count 1." in err, err


def case_a_blocked_gate_must_be_counted() -> None:
    body = fields(gates=[gate("Tests", "PASS"), gate("Type checking", "BLOCKED")], gates_failed=0)
    err = refused(body)
    assert "`gates_blocked` is 0, and the rows count 1." in err, err


cases = [
    (
        f"`{count}` one above the rows exits 1, names it, and writes nothing [criterion 2]",
        count_case(count),
    )
    for count in COUNT_FIELDS
]
cases += [
    (
        "a count below the rows exits 1 and names the tally [criterion 2]",
        case_a_lowered_count_is_refused,
    ),
    (
        "counts that would read ACCEPTED over a FAIL criterion exit 1 [criterion 2]",
        case_counts_that_would_read_accepted_over_a_fail_are_refused,
    ),
    ("an uncounted BLOCKED gate exits 1 [criterion 2]", case_a_blocked_gate_must_be_counted),
]
for name, fn in cases:
    check(name, fn)

print("\n  [with a verdict field]")


def case_verdict_field_is_refused() -> None:
    err = refused(fields(verdict="ACCEPTED"))
    assert "stdin holds a `verdict` field" in err, err


def case_verdict_refusal_names_the_self_grading_failure() -> None:
    err = refused(fields(verdict="ACCEPTED"))
    assert "labeling its own work" in err, f"the refusal must say why there is no verdict: {err!r}"
    assert "The counts decide" in err, err


def case_a_null_verdict_is_refused_too() -> None:
    """The field's presence is what is refused, so no value of it gets through."""
    assert "stdin holds a `verdict` field" in refused(fields(verdict=None))


def case_verdict_is_reported_before_a_missing_field() -> None:
    body = fields(verdict="NOT ACCEPTED")
    del body["gates"]
    err = refused(body)
    assert "`verdict` field" in err, f"the verdict must be reported first: {err!r}"


def case_verdict_is_reported_before_a_bad_count() -> None:
    err = refused(fields(verdict="ACCEPTED", criteria_total=99))
    assert "`verdict` field" in err, f"the verdict must be reported first: {err!r}"


def case_a_criterion_keeps_its_own_verdict() -> None:
    """Only the top-level field is refused; a row's verdict is the grade this run made."""
    assert build(fields())["criteria"][0]["verdict"] == "PASS"


for name, fn in [
    ("a `verdict` exits 1 and writes nothing [criterion 3]", case_verdict_field_is_refused),
    (
        "the refusal names the self-grading failure [criterion 3]",
        case_verdict_refusal_names_the_self_grading_failure,
    ),
    ("a null `verdict` exits 1 as well [criterion 3]", case_a_null_verdict_is_refused_too),
    (
        "the verdict is reported before a missing field [criterion 3]",
        case_verdict_is_reported_before_a_missing_field,
    ),
    (
        "the verdict is reported before a bad count [criterion 3]",
        case_verdict_is_reported_before_a_bad_count,
    ),
    ("a criterion keeps its own verdict", case_a_criterion_keeps_its_own_verdict),
]:
    check(name, fn)

print("\n  [with a field the report cannot hold]")


def missing_field_case(field_name: str):
    def case() -> None:
        body = fields()
        del body[field_name]
        err = refused(body)
        assert f"stdin lacks the field `{field_name}`" in err, err

    return case


def unexpected_field_case(field_name: str, value):
    """An argument sets this field, so stdin naming it must not compete with the argument."""

    def case() -> None:
        err = refused(dict(fields(), **{field_name: value}))
        assert f"stdin holds the unexpected field `{field_name}`" in err, err

    return case


def case_extra_top_level_field_is_refused() -> None:
    err = refused(dict(fields(), timestamp="2026-09-15T04:12:07Z"))
    assert "stdin holds the unexpected field `timestamp`" in err, err


def case_empty_bead_is_refused() -> None:
    err = refused(fields(bead=""))
    assert "stdin field `bead` holds ''" in err, err


def case_negative_count_is_refused() -> None:
    err = refused(fields(criteria_failed=-1))
    assert "stdin field `criteria_failed` holds -1" in err, err


def case_boolean_count_is_refused() -> None:
    err = refused(fields(gates_blocked=True))
    assert "stdin field `gates_blocked` holds True" in err, err


def case_criteria_that_are_not_a_list_are_refused() -> None:
    err = refused(fields(criteria={}))
    assert "stdin field `criteria` holds {}" in err, err


def case_base_without_a_sha_is_refused() -> None:
    err = refused(fields(base={"ref": "origin/HEAD"}))
    assert "`base` lacks the field `sha`" in err, err


def case_criterion_missing_a_field_is_refused() -> None:
    body = fields()
    del body["criteria"][1]["text"]
    err = refused(body)
    assert "`criteria[1]` lacks the field `text`" in err, err


def case_criterion_with_a_lowercase_verdict_is_refused() -> None:
    err = refused(fields(criteria=[criterion(1, "pass")], **passing_counts()))
    assert "`criteria[0]` field `verdict` holds 'pass'" in err, err


def case_criterion_with_a_gate_status_is_refused() -> None:
    """SKIP grades a gate, never a criterion, so the two vocabularies stay apart."""
    err = refused(fields(criteria=[criterion(1, "SKIP")], **passing_counts()))
    assert "`criteria[0]` field `verdict` holds 'SKIP'" in err, err


def case_criterion_number_of_zero_is_refused() -> None:
    err = refused(fields(criteria=[criterion(0)], **passing_counts()))
    assert "`criteria[0]` field `number` holds 0" in err, err


def case_repeated_criterion_number_is_refused() -> None:
    body = fields(
        criteria=[criterion(1), criterion(1)],
        criteria_total=2,
        criteria_passed=2,
        criteria_failed=0,
        criteria_unverifiable=0,
    )
    err = refused(body)
    assert "`criteria[1]` repeats the criterion number `1`" in err, err


def case_extra_field_in_a_criterion_is_refused() -> None:
    err = refused(fields(criteria=[criterion(1, file="src/app.py")], **passing_counts()))
    assert "`criteria[0]` holds the unexpected field `file`" in err, err


def case_gate_missing_a_field_is_refused() -> None:
    body = fields()
    del body["gates"][0]["detail"]
    err = refused(body)
    assert "`gates[0]` lacks the field `detail`" in err, err


def case_gate_status_warn_is_refused() -> None:
    """WARN grades a quality gate, and this report's statuses are its own smaller set."""
    err = refused(fields(gates=[gate("Doc freshness", "WARN")], gates_total=1, gates_failed=0))
    assert "`gates[0]` field `status` holds 'WARN'" in err, err


def case_gate_status_handoff_is_refused() -> None:
    err = refused(
        fields(gates=[gate("Handoff: browser-ui", "HANDOFF")], gates_total=1, gates_failed=0)
    )
    assert "`gates[0]` field `status` holds 'HANDOFF'" in err, err


def case_empty_gate_name_is_refused() -> None:
    err = refused(fields(gates=[gate("", "PASS")], gates_total=1, gates_failed=0))
    assert "`gates[0]` field `name` holds ''" in err, err


def case_repeated_gate_name_is_refused() -> None:
    err = refused(fields(gates=[gate("Lint", "FAIL"), gate("Lint", "PASS")]))
    assert "`gates[1]` repeats the gate name `Lint`" in err, err


def case_extra_field_in_a_gate_is_refused() -> None:
    err = refused(fields(gates=[dict(gate("Lint", "FAIL"), owner="ruff"), gate("Tests", "PASS")]))
    assert "`gates[0]` holds the unexpected field `owner`" in err, err


def case_non_object_stdin_is_refused() -> None:
    err = refused([fields()])
    assert "stdin holds [" in err and "it must be an object" in err, err


def case_unparseable_stdin_is_refused() -> None:
    err = refused("{not json")
    assert "stdin does not parse as JSON" in err, err


def case_base_without_changed_files_is_refused() -> None:
    err = refused(fields(), changed_files=None)
    assert "--changed-files is missing" in err, err


def case_changed_files_without_base_is_refused() -> None:
    err = refused(fields(base=None))
    assert "`base` is missing" in err, err


def case_shape_is_checked_before_the_counts() -> None:
    err = refused(fields(criteria_total=99, gates=[gate("Tests", "ERROR")]))
    assert "field `status` holds 'ERROR'" in err, f"the shape must be reported first: {err!r}"


def case_pairing_is_checked_before_the_counts() -> None:
    err = refused(fields(base=None, criteria_total=99))
    assert "`base` is missing" in err, f"the pairing must be reported first: {err!r}"


def passing_counts() -> dict:
    """The counts for one PASS criterion, so a shape case is not also a count case."""
    return {
        "criteria_total": 1,
        "criteria_passed": 1,
        "criteria_failed": 0,
        "criteria_unverifiable": 0,
    }


cases = [
    (
        f"a missing `{field_name}` exits 1, names it, and writes nothing",
        missing_field_case(field_name),
    )
    for field_name in STDIN_FIELDS
]
cases += [
    (
        f"`{field_name}` on stdin exits 1, because an argument sets it",
        unexpected_field_case(field_name, value),
    )
    for field_name, value in (("version", 2), ("head", HEAD), ("changed_files", CHANGED))
]
cases += [
    ("an extra top-level field exits 1 and names it", case_extra_top_level_field_is_refused),
    ("an empty `bead` exits 1", case_empty_bead_is_refused),
    ("a negative count exits 1", case_negative_count_is_refused),
    ("a boolean count exits 1", case_boolean_count_is_refused),
    ("`criteria` that is not a list exits 1", case_criteria_that_are_not_a_list_are_refused),
    ("a base with no sha exits 1", case_base_without_a_sha_is_refused),
    (
        "a criterion with no `text` exits 1 and names the row",
        case_criterion_missing_a_field_is_refused,
    ),
    ("a lowercase criterion verdict exits 1", case_criterion_with_a_lowercase_verdict_is_refused),
    ("a criterion graded SKIP exits 1", case_criterion_with_a_gate_status_is_refused),
    ("a criterion numbered 0 exits 1", case_criterion_number_of_zero_is_refused),
    ("a repeated criterion number exits 1", case_repeated_criterion_number_is_refused),
    ("an extra field in a criterion exits 1", case_extra_field_in_a_criterion_is_refused),
    ("a gate with no `detail` exits 1 and names the row", case_gate_missing_a_field_is_refused),
    ("the gate status WARN exits 1", case_gate_status_warn_is_refused),
    ("the gate status HANDOFF exits 1", case_gate_status_handoff_is_refused),
    ("an empty gate name exits 1", case_empty_gate_name_is_refused),
    ("a repeated gate name exits 1", case_repeated_gate_name_is_refused),
    ("an extra field in a gate row exits 1", case_extra_field_in_a_gate_is_refused),
    ("stdin that is not an object exits 1", case_non_object_stdin_is_refused),
    ("stdin that does not parse exits 1", case_unparseable_stdin_is_refused),
    (
        "a base with no --changed-files exits 1 and names the missing side",
        case_base_without_changed_files_is_refused,
    ),
    (
        "--changed-files with a null base exits 1 and names the missing side",
        case_changed_files_without_base_is_refused,
    ),
    ("the shape is checked before the counts", case_shape_is_checked_before_the_counts),
    ("the pairing is checked before the counts", case_pairing_is_checked_before_the_counts),
]
for name, fn in cases:
    check(name, fn)

print("\n  [with evidence over the cap]")

SHORT_LINES = [f"line {number}" for number in range(1, 26)]
WIDE_LINES = ["x" * 300 for _ in range(10)]


def case_25_short_lines_keep_20() -> None:
    capped = writer.cap_evidence("\n".join(SHORT_LINES))
    assert capped == "\n".join(SHORT_LINES[:20]) + "\n[trimmed: 5 more lines]", capped


def case_10_wide_lines_keep_whole_lines_within_2000_characters() -> None:
    capped = writer.cap_evidence("\n".join(WIDE_LINES))
    assert capped == "\n".join(WIDE_LINES[:6]) + "\n[trimmed: 4 more lines]", (
        f"got {len(capped.splitlines())} lines"
    )


def case_single_long_line_keeps_its_first_2000_characters() -> None:
    capped = writer.cap_evidence("y" * 5000)
    assert capped == "y" * 2000 + "\n[trimmed: 1 more lines]", capped[-40:]


def case_exactly_20_lines_and_2000_characters_is_unchanged() -> None:
    lines = ["z" * 99 for _ in range(19)] + ["z" * 100]
    text = "\n".join(lines)
    assert (len(text.splitlines()), len(text)) == (20, 2000), "fixture must sit on both limits"
    assert writer.cap_evidence(text) == text


def case_crlf_endings_over_2000_characters_lose_no_line() -> None:
    lines = ["w" * 99 for _ in range(19)] + ["w" * 100]
    text = "\r\n".join(lines)
    assert len(text) > 2000, "fixture must exceed the cap only through its line endings"
    assert writer.cap_evidence(text) == "\n".join(lines)


def case_null_evidence_stays_null() -> None:
    body = fields(criteria=[criterion(1, evidence=None)], **passing_counts())
    assert build(body)["criteria"][0]["evidence"] is None


def case_cap_applies_to_a_criterion_over_20_lines() -> None:
    out = fresh_out()
    body = fields(criteria=[criterion(1, evidence="\n".join(SHORT_LINES))], **passing_counts())
    run_cli(body, arguments(out))
    evidence = written(out)["criteria"][0]["evidence"]
    assert evidence.splitlines()[-1] == "[trimmed: 5 more lines]", evidence
    assert len(evidence.splitlines()) == 21, f"20 kept lines and the trimmed line: {evidence!r}"


def case_cap_applies_to_a_criterion_over_2000_characters() -> None:
    out = fresh_out()
    body = fields(criteria=[criterion(1, evidence="\n".join(WIDE_LINES))], **passing_counts())
    run_cli(body, arguments(out))
    evidence = written(out)["criteria"][0]["evidence"]
    assert len(evidence) <= 2000 + len("\n[trimmed: 4 more lines]"), len(evidence)
    assert evidence.splitlines()[-1] == "[trimmed: 4 more lines]", evidence.splitlines()[-1]


def case_gate_detail_is_not_capped() -> None:
    """A gate `detail` is a one-line result by the skill's own rule, so nothing trims it."""
    detail = "\n".join(SHORT_LINES)
    body = fields(gates=[gate("Tests", "PASS", detail=detail)], gates_total=1, gates_failed=0)
    assert build(body)["gates"][0]["detail"] == detail


for name, fn in [
    ("25 short lines keep 20 and trim 5 [criterion 4]", case_25_short_lines_keep_20),
    (
        "10 lines over 2,000 characters keep whole lines within 2,000 [criterion 4]",
        case_10_wide_lines_keep_whole_lines_within_2000_characters,
    ),
    (
        "a single 5,000-character line keeps its first 2,000 [criterion 4]",
        case_single_long_line_keeps_its_first_2000_characters,
    ),
    (
        "exactly 20 lines and 2,000 characters is unchanged",
        case_exactly_20_lines_and_2000_characters_is_unchanged,
    ),
    (
        "CRLF endings over 2,000 characters lose no line and get no trimmed line",
        case_crlf_endings_over_2000_characters_lose_no_line,
    ),
    ("null evidence stays null", case_null_evidence_stays_null),
    (
        "evidence over 20 lines is capped in the file main() writes [criterion 4]",
        case_cap_applies_to_a_criterion_over_20_lines,
    ),
    (
        "evidence over 2,000 characters is capped in the file main() writes [criterion 4]",
        case_cap_applies_to_a_criterion_over_2000_characters,
    ),
    ("a gate detail is never capped", case_gate_detail_is_not_capped),
]:
    check(name, fn)

print("\n  [with an argument that cannot be used]")


def case_short_head_exits_2() -> None:
    assert "--head" in usage_error(fields(), head="a1b2c3d")


def case_non_hex_head_exits_2() -> None:
    assert "--head" in usage_error(fields(), head="g" * 40)


def case_missing_head_exits_2() -> None:
    assert "--head" in usage_error(fields(), head=None)


def case_sha256_head_is_accepted() -> None:
    out = fresh_out()
    code, _, err = run_cli(fields(), arguments(out, head="b" * 64))
    assert code == 0, f"a 64-character head must be accepted, got {code}: {err!r}"


def case_unreadable_changed_files_exits_2() -> None:
    err = usage_error(fields(), changed_files=str(WORKDIR / "absent.txt"))
    assert "--changed-files could not be read" in err, err


def case_out_in_a_missing_directory_exits_2() -> None:
    out = Path(tempfile.mkdtemp()).resolve() / "absent" / "acceptance-report.json"
    assert "--out" in usage_error(fields(), out=out)


def case_out_naming_no_file_exits_2() -> None:
    for value in ("", ".", "/"):
        code, _, err = run_cli(fields(), arguments(Path(value)))
        assert code == 2, f"--out {value!r} must exit 2, got {code}: {err!r}"
        assert "--out" in err, err


def case_unwritable_out_exits_2_and_leaves_no_temporary_file() -> None:
    """`--out` names an existing directory, so the rename onto it cannot succeed."""
    out = Path(tempfile.mkdtemp()).resolve() / "acceptance-report.json"
    out.mkdir()
    code, _, err = run_cli(fields(), arguments(out))
    assert code == 2, f"must exit 2, got {code}: {err!r}"
    assert "--out could not be written" in err, err
    assert [p.name for p in out.parent.iterdir()] == [out.name], list(out.parent.iterdir())


def case_usage_error_beats_a_refusal() -> None:
    assert "--head" in usage_error({"not": "a report"}, head="nope")


for name, fn in [
    ("a short --head exits 2", case_short_head_exits_2),
    ("a non-hex --head exits 2", case_non_hex_head_exits_2),
    ("a missing --head exits 2", case_missing_head_exits_2),
    ("a 64-character --head is accepted", case_sha256_head_is_accepted),
    ("an unreadable --changed-files exits 2", case_unreadable_changed_files_exits_2),
    ("an --out in a missing directory exits 2", case_out_in_a_missing_directory_exits_2),
    ("an --out that names no file exits 2", case_out_naming_no_file_exits_2),
    (
        "an --out that cannot be written exits 2 and leaves no temporary file",
        case_unwritable_out_exits_2_and_leaves_no_temporary_file,
    ),
    ("a bad argument exits 2 even when stdin is also bad", case_usage_error_beats_a_refusal),
]:
    check(name, fn)

print("\n  [through a real subprocess]")


def run_subprocess(body: dict, argv: list[str]) -> subprocess.CompletedProcess[str]:
    """`python3 write_acceptance_report.py ...` with the object on stdin, as the skill will."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        input=json.dumps(body),
        capture_output=True,
        text=True,
        timeout=30,
    )


def case_subprocess_valid_input_exits_0_and_writes() -> None:
    out = fresh_out()
    result = run_subprocess(fields(), arguments(out))
    assert result.returncode == 0, f"must exit 0, got {result.returncode}: {result.stderr}"
    assert written(out)["version"] == 2


def case_subprocess_count_mismatch_exits_1_and_writes_nothing() -> None:
    out = fresh_out()
    result = run_subprocess(fields(criteria_passed=3), arguments(out))
    assert result.returncode == 1, f"must exit 1, got {result.returncode}"
    assert nothing_written(out), "a refusal must write nothing"


def case_subprocess_verdict_exits_1_and_writes_nothing() -> None:
    out = fresh_out()
    result = run_subprocess(fields(verdict="ACCEPTED"), arguments(out))
    assert result.returncode == 1, f"must exit 1, got {result.returncode}"
    assert nothing_written(out), "a refusal must write nothing"


for name, fn in [
    (
        "valid input exits 0 and writes the file, through a real process [criterion 1]",
        case_subprocess_valid_input_exits_0_and_writes,
    ),
    (
        "a count mismatch exits 1 and writes nothing, through a real process [criterion 2]",
        case_subprocess_count_mismatch_exits_1_and_writes_nothing,
    ),
    (
        "a verdict field exits 1 and writes nothing, through a real process [criterion 3]",
        case_subprocess_verdict_exits_1_and_writes_nothing,
    ),
]:
    check(name, fn)

print("\n  [the shape of the file itself]")


def case_script_never_names_subprocess() -> None:
    lines = [
        f"{number}: {line}"
        for number, line in enumerate(SCRIPT.read_text(encoding="utf-8").splitlines(), 1)
        if "subprocess" in line
    ]
    assert not lines, f"the writer must run no process: {lines}"


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__",
        "argparse",
        "collections",
        "contextlib",
        "dataclasses",
        "importlib",
        "io",
        "json",
        "os",
        "re",
        "subprocess",
        "sys",
        "tempfile",
        "pathlib",
        "typing",
    }
    for path in (SCRIPT, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M))
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


def case_agents_md_lists_this_suite() -> None:
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "python3 skills/verify-acceptance/scripts/test_write_acceptance_report.py" in agents


for name, fn in [
    ("the script never names subprocess [criterion 5]", case_script_never_names_subprocess),
    ("neither file imports outside the standard library", case_no_third_party_imports),
    ("AGENTS.md lists this suite [criterion 6]", case_agents_md_lists_this_suite),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
