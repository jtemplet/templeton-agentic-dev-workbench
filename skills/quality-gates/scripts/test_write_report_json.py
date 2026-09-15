#!/usr/bin/env python3
"""Regression suite for write_report_json.py.

Stdlib only, no install, and no git repository. Run with:
    python3 skills/quality-gates/scripts/test_write_report_json.py

Nearly every case runs in-process: `build()` and the cap cases call the pure
functions with dicts, and `run_cli()` calls `main()` with an argument list, a
stdin buffer, and two output buffers. Every `--out` is a fresh path in its own
`tempfile.mkdtemp()` directory, so "writes nothing" means that directory stays
empty. The "[through a real subprocess]" group is the exception, on purpose: it
invokes `python3 write_report_json.py ...` the way the quality-gates skill will,
so the CLI surface has a test that drives its real entry point.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-6qd criterion                             Pinned by
  ------------------------------------------------------------------------------
  1. Valid input exits 0 and writes version 2    the [with a valid report] group
     with every version 1 and version 2 field
  2. A verdict that breaks the Verdict Rules     the [with a verdict the Verdict
     exits 1, names it, and writes nothing       Rules do not give] group
  3. A bad status, a missing field, or a         the [with a status, field, or
     finding naming no gate row exits 1          reference the report cannot hold]
                                                 group
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
SCRIPT = HERE / "write_report_json.py"
REPO = HERE.parents[2]

_spec = importlib.util.spec_from_file_location("write_report_json", SCRIPT)
writer = importlib.util.module_from_spec(_spec)
sys.modules["write_report_json"] = writer
_spec.loader.exec_module(writer)

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
TIMESTAMP = "2026-08-11T04:12:07Z"
BASE = {"ref": "origin/HEAD", "sha": "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"}
CHANGED = ["src/api/exports.py", "tests/test_exports.py"]
FACTS = writer.RunFacts(HEAD, True, TIMESTAMP, tuple(CHANGED))

VERSION_1_FIELDS = (
    "version",
    "head",
    "dirty",
    "timestamp",
    "scope",
    "gate_source",
    "routing",
    "verdict",
    "gates",
)
VERSION_2_FIELDS = ("bead", "base", "changed_files", "findings")
STDIN_FIELDS = ("scope", "gate_source", "routing", "bead", "base", "verdict", "gates", "findings")


def gate(name: str, status: str) -> dict:
    return {"name": name, "status": status, "command": None, "detail": f"{name} {status}"}


def finding(gate_name: str = "Lint", **overrides) -> dict:
    body = {
        "gate": gate_name,
        "file": "src/api/exports.py",
        "line": 88,
        "problem": "F841 local variable 'rows' is assigned to but never used",
        "evidence": "src/api/exports.py:88:5: F841 local variable 'rows' is assigned to but never used",
    }
    body.update(overrides)
    return body


def fields(**overrides) -> dict:
    """A stdin object that passes every check: a FAIL verdict over a FAIL Lint row."""
    body = {
        "scope": "changed",
        "gate_source": "AGENTS.md",
        "routing": {"http-api": {"method": "curl", "owner": None, "files": 2, "endpoints": 3}},
        "bead": "tadw-abc",
        "base": BASE,
        "verdict": "FAIL",
        "gates": [
            gate("Tests", "PASS"),
            gate("Lint", "FAIL"),
            gate("Doc freshness", "WARN"),
            gate("Type checking", "SKIP"),
        ],
        "findings": [finding()],
    }
    body.update(overrides)
    return body


def build(body: dict, facts=FACTS) -> dict:
    return writer.build_report(body, facts)


def fresh_out() -> Path:
    return Path(tempfile.mkdtemp()).resolve() / "quality-gates-report.json"


WORKDIR = Path(tempfile.mkdtemp()).resolve()
CHANGED_FILE = WORKDIR / "quality-gates-changed.txt"
CHANGED_FILE.write_text("\n".join(CHANGED) + "\n", encoding="utf-8")


def arguments(out: Path, **overrides: str | None) -> list[str]:
    """The argument list for a valid run, with any flag replaced or, given None, left out."""
    values = {
        "out": str(out),
        "head": HEAD,
        "dirty": "true",
        "timestamp": TIMESTAMP,
        "changed_files": str(CHANGED_FILE),
    }
    values.update(overrides)
    argv: list[str] = []
    for name, value in values.items():
        if value is not None:
            argv += ["--" + name.replace("_", "-"), value]
    return argv


def run_cli(body: dict | str, argv: list[str]) -> tuple[int, str, str]:
    """The writer's process-boundary behavior: argv and stdin in, exit code and streams out."""
    text = body if isinstance(body, str) else json.dumps(body)
    out, err = io.StringIO(), io.StringIO()
    code = writer.main(argv, io.StringIO(text), out, err)
    return code, out.getvalue(), err.getvalue()


def written(out: Path) -> dict:
    return json.loads(out.read_text(encoding="utf-8"))


def nothing_written(out: Path) -> bool:
    return not out.parent.exists() or not any(out.parent.iterdir())


def refused(body: dict | str, **overrides: str | None) -> str:
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


def case_written_file_holds_every_version_1_field() -> None:
    missing = [name for name in VERSION_1_FIELDS if name not in written(VALID_OUT)]
    assert not missing, f"the file lacks version 1 fields: {missing}"


def case_written_file_holds_every_version_2_field() -> None:
    missing = [name for name in VERSION_2_FIELDS if name not in written(VALID_OUT)]
    assert not missing, f"the file lacks version 2 fields: {missing}"


def case_injected_values_are_written() -> None:
    report = written(VALID_OUT)
    injected = {k: report[k] for k in ("head", "dirty", "timestamp", "changed_files")}
    assert injected == {
        "head": HEAD,
        "dirty": True,
        "timestamp": TIMESTAMP,
        "changed_files": CHANGED,
    }, f"got {injected}"


def case_fields_are_written_in_the_documented_order() -> None:
    assert list(written(VALID_OUT)) == [
        "version",
        "head",
        "dirty",
        "timestamp",
        "scope",
        "gate_source",
        "routing",
        "bead",
        "base",
        "changed_files",
        "verdict",
        "gates",
        "findings",
    ]


def case_file_is_indented_json_ending_in_a_newline() -> None:
    text = VALID_OUT.read_text(encoding="utf-8")
    assert text == json.dumps(written(VALID_OUT), indent=2) + "\n"


def case_rename_leaves_no_temporary_file() -> None:
    assert [p.name for p in VALID_OUT.parent.iterdir()] == [VALID_OUT.name]


def case_null_base_without_changed_files_writes_null() -> None:
    facts = writer.RunFacts(HEAD, True, TIMESTAMP, None)
    assert build(fields(base=None), facts)["changed_files"] is None


def case_dirty_false_writes_false() -> None:
    out = fresh_out()
    run_cli(fields(), arguments(out, dirty="false"))
    assert written(out)["dirty"] is False


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


def case_empty_routing_and_findings_are_valid() -> None:
    report = build(fields(routing={}, findings=[]))
    assert (report["routing"], report["findings"]) == ({}, [])


def case_existing_report_is_replaced() -> None:
    out = fresh_out()
    out.write_text('{"version": 1}\n', encoding="utf-8")
    run_cli(fields(), arguments(out))
    assert written(out)["version"] == 2


for name, fn in [
    (
        "valid input exits 0 and prints the written path [criterion 1]",
        case_valid_input_exits_0_and_prints_the_path,
    ),
    ("the written file is version 2 [criterion 1]", case_written_file_is_version_2),
    (
        "the written file holds every version 1 field [criterion 1]",
        case_written_file_holds_every_version_1_field,
    ),
    (
        "the written file holds bead, base, changed_files, and findings [criterion 1]",
        case_written_file_holds_every_version_2_field,
    ),
    (
        "head, dirty, timestamp, and changed_files come from the arguments [criterion 1]",
        case_injected_values_are_written,
    ),
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
        "a null base with no --changed-files writes changed_files null",
        case_null_base_without_changed_files_writes_null,
    ),
    ("--dirty false writes false", case_dirty_false_writes_false),
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
    ("empty routing and empty findings are valid", case_empty_routing_and_findings_are_valid),
    ("an existing report at --out is replaced", case_existing_report_is_replaced),
]:
    check(name, fn)

print("\n  [with a verdict the Verdict Rules do not give]")


def case_pass_with_a_fail_gate_is_refused() -> None:
    err = refused(fields(verdict="PASS", gates=[gate("Tests", "PASS"), gate("Lint", "FAIL")]))
    assert "The verdict is PASS, and the Verdict Rules give FAIL: gate `Lint` is FAIL." in err, err


def case_pass_with_a_blocked_gate_is_refused() -> None:
    body = fields(verdict="PASS", gates=[gate("Lint", "PASS"), gate("Type checking", "BLOCKED")])
    err = refused(body)
    assert "The verdict is PASS, and the Verdict Rules give FAIL" in err, err
    assert "gate `Type checking` is BLOCKED" in err, f"must name the deciding gate: {err!r}"


def case_fail_with_every_gate_passing_is_refused() -> None:
    err = refused(fields(verdict="FAIL", gates=[gate("Tests", "PASS"), gate("Lint", "PASS")]))
    assert "The verdict is FAIL, and the Verdict Rules give PASS" in err, err


def case_pass_with_a_handoff_gate_is_refused() -> None:
    body = fields(
        verdict="PASS",
        gates=[gate("Lint", "PASS"), gate("Handoff: browser-ui", "HANDOFF")],
        findings=[],
    )
    err = refused(body)
    assert "The verdict is PASS, and the Verdict Rules give INCOMPLETE" in err, err
    assert "gate `Handoff: browser-ui` is HANDOFF" in err, f"must name the deciding gate: {err!r}"


def case_pass_with_every_gate_skipped_is_refused() -> None:
    body = fields(verdict="PASS", gates=[gate("Tests", "SKIP"), gate("Lint", "SKIP")], findings=[])
    err = refused(body)
    assert "The verdict is PASS, and the Verdict Rules give NO GATES RAN" in err, err


def case_no_gates_ran_with_a_warn_gate_is_refused() -> None:
    body = fields(
        verdict="NO GATES RAN",
        gates=[gate("Doc freshness", "WARN"), gate("Tests", "SKIP")],
        findings=[],
    )
    err = refused(body)
    assert "The verdict is NO GATES RAN, and the Verdict Rules give PASS" in err, err


for name, fn in [
    (
        "PASS over a FAIL gate exits 1, names both verdicts and the gate [criterion 2]",
        case_pass_with_a_fail_gate_is_refused,
    ),
    (
        "PASS over a BLOCKED gate exits 1 and names FAIL [criterion 2]",
        case_pass_with_a_blocked_gate_is_refused,
    ),
    (
        "FAIL over every gate passing exits 1 and names PASS [criterion 2]",
        case_fail_with_every_gate_passing_is_refused,
    ),
    (
        "PASS over a HANDOFF gate exits 1 and names INCOMPLETE [criterion 2]",
        case_pass_with_a_handoff_gate_is_refused,
    ),
    (
        "PASS over every gate skipped exits 1 and names NO GATES RAN [criterion 2]",
        case_pass_with_every_gate_skipped_is_refused,
    ),
    (
        "NO GATES RAN over a WARN gate exits 1 and names PASS [criterion 2]",
        case_no_gates_ran_with_a_warn_gate_is_refused,
    ),
]:
    check(name, fn)

print("\n  [for the order of the Verdict Rules]")


def verdict_for(*statuses: str) -> str:
    gates = [gate(f"gate {index}", status) for index, status in enumerate(statuses)]
    return writer.derive_verdict(gates).verdict


def case_all_blocked_is_fail() -> None:
    assert verdict_for("BLOCKED", "BLOCKED") == "FAIL"


def case_fail_beats_handoff() -> None:
    assert verdict_for("HANDOFF", "FAIL", "PASS") == "FAIL"


def case_all_warn_and_skip_is_pass() -> None:
    assert verdict_for("WARN", "SKIP", "WARN") == "PASS"


def case_no_gates_is_no_gates_ran() -> None:
    assert verdict_for() == "NO GATES RAN"


def case_handoff_beats_no_gates_ran() -> None:
    assert verdict_for("HANDOFF", "SKIP") == "INCOMPLETE"


for name, fn in [
    ("all BLOCKED is FAIL, never NO GATES RAN", case_all_blocked_is_fail),
    ("FAIL beats HANDOFF", case_fail_beats_handoff),
    ("all WARN and SKIP is PASS", case_all_warn_and_skip_is_pass),
    ("no gates at all is NO GATES RAN", case_no_gates_is_no_gates_ran),
    ("HANDOFF over SKIP is INCOMPLETE, never NO GATES RAN", case_handoff_beats_no_gates_ran),
]:
    check(name, fn)

print("\n  [with a status, field, or reference the report cannot hold]")


def case_lowercase_status_is_refused() -> None:
    err = refused(fields(gates=[gate("Tests", "pass"), gate("Lint", "FAIL")]))
    assert "`gates[0]` field `status` holds 'pass'" in err, err


def case_unknown_status_is_refused() -> None:
    err = refused(fields(gates=[gate("Tests", "ERROR"), gate("Lint", "FAIL")]))
    assert "`gates[0]` field `status` holds 'ERROR'" in err, err


def missing_field_case(field_name: str):
    def case() -> None:
        body = fields()
        del body[field_name]
        err = refused(body)
        assert f"stdin lacks the field `{field_name}`" in err, err

    return case


def case_finding_naming_no_gate_row_is_refused() -> None:
    err = refused(fields(findings=[finding("Lnt")]))
    assert "names the gate `Lnt`, and no row in `gates` has that name" in err, err


def case_unknown_verdict_is_refused() -> None:
    err = refused(fields(verdict="PASSED"))
    assert "field `verdict` holds 'PASSED'" in err, err


def case_extra_top_level_field_is_refused() -> None:
    err = refused(dict(fields(), head=HEAD))
    assert "stdin holds the unexpected field `head`" in err, err


def case_bad_scope_is_refused() -> None:
    err = refused(fields(scope="partial"))
    assert "field `scope` holds 'partial'" in err, err


def case_base_without_a_sha_is_refused() -> None:
    err = refused(fields(base={"ref": "origin/HEAD"}))
    assert "`base` lacks the field `sha`" in err, err


def case_routing_entry_with_a_negative_count_is_refused() -> None:
    routing = {"http-api": {"method": "curl", "owner": None, "files": -1, "endpoints": 3}}
    err = refused(fields(routing=routing))
    assert "`routing.http-api` field `files` holds -1" in err, err


def case_routing_entry_with_a_boolean_count_is_refused() -> None:
    routing = {"http-api": {"method": "curl", "owner": None, "files": 2, "endpoints": True}}
    err = refused(fields(routing=routing))
    assert "`routing.http-api` field `endpoints` holds True" in err, err


def case_duplicate_gate_names_are_refused() -> None:
    err = refused(fields(gates=[gate("Lint", "FAIL"), gate("Lint", "PASS")]))
    assert "`gates[1]` repeats the gate name `Lint`" in err, err


def case_line_without_a_file_is_refused() -> None:
    err = refused(fields(findings=[finding(file=None, line=12)]))
    assert "`findings[0]` names line 12 and no `file`" in err, err


def case_line_of_zero_is_refused() -> None:
    err = refused(fields(findings=[finding(line=0)]))
    assert "`findings[0]` field `line` holds 0" in err, err


def case_extra_field_in_a_gate_is_refused() -> None:
    err = refused(fields(gates=[dict(gate("Lint", "FAIL"), owner="ruff")]))
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


def case_shape_is_checked_before_the_verdict() -> None:
    err = refused(fields(verdict="PASS", gates=[gate("Lint", "ERROR"), gate("Tests", "FAIL")]))
    assert "field `status` holds 'ERROR'" in err, f"the shape must be reported first: {err!r}"


def case_pairing_is_checked_before_the_verdict() -> None:
    err = refused(fields(base=None, verdict="PASS"))
    assert "`base` is missing" in err, f"the pairing must be reported first: {err!r}"


def case_verdict_is_checked_before_finding_gates() -> None:
    err = refused(fields(verdict="PASS", findings=[finding("Lnt")]))
    assert "The verdict is PASS" in err, f"the verdict must be reported first: {err!r}"


cases = [
    (
        "a lowercase status exits 1 and writes nothing [criterion 3]",
        case_lowercase_status_is_refused,
    ),
    ("the status ERROR exits 1 and writes nothing [criterion 3]", case_unknown_status_is_refused),
]
cases += [
    (
        f"a missing `{field_name}` exits 1, names it, and writes nothing [criterion 3]",
        missing_field_case(field_name),
    )
    for field_name in STDIN_FIELDS
]
cases += [
    (
        "a finding whose gate names no row exits 1 and names the gate [criterion 3]",
        case_finding_naming_no_gate_row_is_refused,
    ),
    ("an unknown verdict string exits 1", case_unknown_verdict_is_refused),
    ("an extra top-level field exits 1 and names it", case_extra_top_level_field_is_refused),
    ("a scope other than changed or all exits 1", case_bad_scope_is_refused),
    ("a base with no sha exits 1", case_base_without_a_sha_is_refused),
    (
        "a routing entry with a negative count exits 1",
        case_routing_entry_with_a_negative_count_is_refused,
    ),
    (
        "a routing entry with a boolean count exits 1",
        case_routing_entry_with_a_boolean_count_is_refused,
    ),
    ("duplicate gate names exit 1", case_duplicate_gate_names_are_refused),
    ("a line with no file exits 1", case_line_without_a_file_is_refused),
    ("a line of 0 exits 1", case_line_of_zero_is_refused),
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
    ("the shape is checked before the verdict", case_shape_is_checked_before_the_verdict),
    ("the pairing is checked before the verdict", case_pairing_is_checked_before_the_verdict),
    (
        "the verdict is checked before the gates findings name",
        case_verdict_is_checked_before_finding_gates,
    ),
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
    report = build(fields(findings=[finding(evidence=None)]))
    assert report["findings"][0]["evidence"] is None


def case_cap_applies_in_the_written_file() -> None:
    out = fresh_out()
    run_cli(fields(findings=[finding(evidence="\n".join(SHORT_LINES))]), arguments(out))
    evidence = written(out)["findings"][0]["evidence"]
    assert evidence.splitlines()[-1] == "[trimmed: 5 more lines]", evidence
    assert len(evidence.splitlines()) == 21, f"20 kept lines and the trimmed line: {evidence!r}"


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
        "the cap applies in the file main() writes [criterion 4]",
        case_cap_applies_in_the_written_file,
    ),
]:
    check(name, fn)

print("\n  [with an argument that cannot be used]")


def case_bad_dirty_exits_2() -> None:
    assert "--dirty" in usage_error(fields(), dirty="yes")


def case_timestamp_with_a_space_exits_2() -> None:
    assert "--timestamp" in usage_error(fields(), timestamp="2026-08-11 04:12:07")


def case_unpadded_timestamp_exits_2() -> None:
    assert "--timestamp" in usage_error(fields(), timestamp="2026-8-11T4:12:07Z")


def case_short_head_exits_2() -> None:
    assert "--head" in usage_error(fields(), head="a1b2c3d")


def case_non_hex_head_exits_2() -> None:
    assert "--head" in usage_error(fields(), head="g" * 40)


def case_missing_head_exits_2() -> None:
    assert "--head" in usage_error(fields(), head=None)


def case_unreadable_changed_files_exits_2() -> None:
    err = usage_error(fields(), changed_files=str(WORKDIR / "absent.txt"))
    assert "--changed-files could not be read" in err, err


def case_out_in_a_missing_directory_exits_2() -> None:
    out = Path(tempfile.mkdtemp()).resolve() / "absent" / "quality-gates-report.json"
    assert "--out" in usage_error(fields(), out=out)


def case_out_naming_no_file_exits_2() -> None:
    for value in ("", ".", "/"):
        code, _, err = run_cli(fields(), arguments(Path(value)))
        assert code == 2, f"--out {value!r} must exit 2, got {code}: {err!r}"
        assert "--out" in err, err


def case_usage_error_beats_a_refusal() -> None:
    assert "--dirty" in usage_error({"not": "a report"}, dirty="maybe")


for name, fn in [
    ("a --dirty other than true or false exits 2", case_bad_dirty_exits_2),
    ("a --timestamp with a space exits 2", case_timestamp_with_a_space_exits_2),
    ("an unpadded --timestamp exits 2", case_unpadded_timestamp_exits_2),
    ("a short --head exits 2", case_short_head_exits_2),
    ("a non-hex --head exits 2", case_non_hex_head_exits_2),
    ("a missing --head exits 2", case_missing_head_exits_2),
    ("an unreadable --changed-files exits 2", case_unreadable_changed_files_exits_2),
    ("an --out in a missing directory exits 2", case_out_in_a_missing_directory_exits_2),
    ("an --out that names no file exits 2", case_out_naming_no_file_exits_2),
    ("a bad argument exits 2 even when stdin is also bad", case_usage_error_beats_a_refusal),
]:
    check(name, fn)

print("\n  [through a real subprocess]")


def run_subprocess(body: dict, argv: list[str]) -> subprocess.CompletedProcess[str]:
    """`python3 write_report_json.py ...` with the object on stdin, as the skill will call it."""
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


def case_subprocess_verdict_mismatch_exits_1_and_writes_nothing() -> None:
    out = fresh_out()
    result = run_subprocess(fields(verdict="PASS"), arguments(out))
    assert result.returncode == 1, f"must exit 1, got {result.returncode}"
    assert nothing_written(out), "a refusal must write nothing"


for name, fn in [
    (
        "valid input exits 0 and writes the file, through a real process [criterion 1]",
        case_subprocess_valid_input_exits_0_and_writes,
    ),
    (
        "a verdict mismatch exits 1 and writes nothing, through a real process [criterion 2]",
        case_subprocess_verdict_mismatch_exits_1_and_writes_nothing,
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
        "dataclasses",
        "datetime",
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
    assert "python3 skills/quality-gates/scripts/test_write_report_json.py" in agents


for name, fn in [
    (
        "the script never names subprocess [criterion 5]",
        case_script_never_names_subprocess,
    ),
    ("neither file imports outside the standard library", case_no_third_party_imports),
    ("AGENTS.md lists this suite [criterion 6]", case_agents_md_lists_this_suite),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
