#!/usr/bin/env python3
"""Regression suite for load_findings.py.

Stdlib only, no install, and no git repository. Run with:
    python3 skills/reconcile-acceptance/scripts/test_load_findings.py

Nearly every case calls the loader in-process with injected values, so most of
the suite starts no process (`load()` for the pure function, `run_cli()` for
`main()` with an argument list and two string buffers). The
"[through a real subprocess]" group is the exception, on purpose: it invokes
`python3 load_findings.py ...` the way the reconcile-acceptance skill does, so
the CLI surface has a test that drives its real entry point, not just its
argument-parsing and dispatch logic.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-3vp criterion                             Pinned by
  ------------------------------------------------------------------------------
  1. Each loader reason, in order               the [reasons] and [first reason
                                                wins] groups
  1. failures-outside-change never prints       case_fail_in_no_changed_file_stays_in_scope
  2. ACCEPTED counts exit 3                     case_accepted_counts_exit_3
  3. Only UNVERIFIABLE prints needs-human-check case_only_unverifiable_prints_needs_human_check
  4. Out of scope carries no evidence           case_unverifiable_criterion_has_no_evidence
  5. No subprocess in the script                case_script_never_names_subprocess
  6. AGENTS.md names this suite                 case_agents_md_lists_this_suite
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
SCRIPT = HERE / "load_findings.py"
REPO = HERE.parents[2]

_spec = importlib.util.spec_from_file_location("load_findings", SCRIPT)
loader = importlib.util.module_from_spec(_spec)
sys.modules["load_findings"] = loader
_spec.loader.exec_module(loader)

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
CHANGED = ["src/auth.py", "tests/test_auth.py"]


def criterion(number: int, verdict: str, command: str | None = None) -> dict:
    return {
        "number": number,
        "text": f"criterion {number}",
        "verdict": verdict,
        "evidence": f"evidence for criterion {number}",
        "command": command,
    }


def gate(name: str, status: str) -> dict:
    return {
        "name": name,
        "status": status,
        "command": "pytest -q",
        "detail": f"{name} {status}",
    }


PASSING_GATES = [
    gate("Tests", "PASS"),
    gate("Lint", "PASS"),
    gate("Type checking", "SKIP"),
]


def report(criteria: list[dict], gates: list[dict] = PASSING_GATES, **overrides) -> dict:
    """A version 2 acceptance report whose counts agree with its rows."""
    body = {
        "version": 2,
        "bead": "tadw-abc",
        "head": HEAD,
        "base": BASE,
        "changed_files": CHANGED,
        "criteria": criteria,
        "gates": gates,
        "criteria_total": len(criteria),
        "criteria_passed": sum(c["verdict"] == "PASS" for c in criteria),
        "criteria_failed": sum(c["verdict"] == "FAIL" for c in criteria),
        "criteria_unverifiable": sum(c["verdict"] == "UNVERIFIABLE" for c in criteria),
        "gates_total": len(gates),
        "gates_failed": sum(g["status"] == "FAIL" for g in gates),
        "gates_blocked": sum(g["status"] == "BLOCKED" for g in gates),
    }
    body.update(overrides)
    return body


ACCEPTED = report([criterion(1, "PASS"), criterion(2, "PASS")])
FAILING = report(
    [
        criterion(1, "PASS"),
        criterion(2, "FAIL", command="pytest tests/test_auth.py::test_rejects_expired"),
        criterion(3, "UNVERIFIABLE"),
    ],
    gates=[
        gate("Tests", "FAIL"),
        gate("Lint", "BLOCKED"),
        gate("Type checking", "SKIP"),
    ],
)
ONLY_UNVERIFIABLE = report([criterion(1, "PASS"), criterion(2, "UNVERIFIABLE")])
ONLY_BLOCKED = report(
    [criterion(1, "PASS"), criterion(2, "UNVERIFIABLE")],
    gates=[gate("Tests", "BLOCKED"), gate("Lint", "PASS")],
)


def load(body: dict | str | None, head: str = HEAD, dirty=(), bead: str | None = None):
    text = body if body is None or isinstance(body, str) else json.dumps(body)
    return loader.load_findings(loader.LoaderInputs(text, head, frozenset(dirty), bead))


def reason_of(outcome) -> str | None:
    return getattr(outcome, "reason", None)


def stdout_of(outcome) -> str:
    out, err = io.StringIO(), io.StringIO()
    outcome.emit(out, err)
    return out.getvalue()


def findings_of(outcome) -> dict:
    assert outcome.exit_code == 0, f"expected findings, got {outcome!r}"
    return json.loads(stdout_of(outcome))


print("\n  [each reason, when its condition holds]")


def case_no_report_is_report_missing() -> None:
    assert reason_of(load(None)) == "report-missing"


def case_invalid_json_is_report_unreadable() -> None:
    assert reason_of(load("{not json")) == "report-unreadable"


def case_version_1_is_report_unreadable_and_names_it() -> None:
    outcome = load(report([criterion(1, "PASS")], version=1))
    assert reason_of(outcome) == "report-unreadable", f"got {outcome!r}"
    assert "version is 1" in outcome.detail, f"must name the version: {outcome.detail!r}"


def case_missing_version_2_field_is_report_unreadable() -> None:
    body = report([criterion(1, "FAIL")])
    del body["changed_files"]
    assert reason_of(load(body)) == "report-unreadable"


def case_counts_disagreeing_with_rows_is_report_unreadable() -> None:
    body = report([criterion(1, "FAIL")], criteria_failed=0, criteria_passed=1)
    assert reason_of(load(body)) == "report-unreadable"


def case_other_head_is_report_stale() -> None:
    assert reason_of(load(FAILING, head="f" * 40)) == "report-stale"


def case_other_bead_is_bead_mismatch() -> None:
    assert reason_of(load(FAILING, bead="tadw-xyz")) == "bead-mismatch"


def case_null_report_bead_is_bead_mismatch() -> None:
    body = report(FAILING["criteria"], FAILING["gates"], bead=None)
    assert reason_of(load(body, bead="tadw-abc")) == "bead-mismatch"


def case_dirty_changed_file_is_uncommitted_changes() -> None:
    outcome = load(FAILING, dirty={"src/auth.py"})
    assert reason_of(outcome) == "uncommitted-changes", f"got {outcome!r}"
    assert "src/auth.py" in outcome.detail, f"must name the file: {outcome.detail!r}"


def case_only_blocked_gates_is_needs_environment() -> None:
    body = report([criterion(1, "PASS")], gates=[gate("Tests", "BLOCKED")])
    assert reason_of(load(body)) == "needs-environment"


def case_only_unverifiable_prints_needs_human_check() -> None:
    outcome = load(ONLY_UNVERIFIABLE)
    assert outcome.exit_code == 1, f"must exit 1, got {outcome.exit_code}"
    assert stdout_of(outcome) == "RECONCILE_ACCEPTANCE_BLOCKED needs-human-check\n"


def case_no_criteria_is_needs_human_check() -> None:
    assert reason_of(load(report([]))) == "needs-human-check"


for name, fn in [
    ("no report is report-missing [criterion 1]", case_no_report_is_report_missing),
    (
        "invalid JSON is report-unreadable [criterion 1]",
        case_invalid_json_is_report_unreadable,
    ),
    (
        "version 1 is report-unreadable, and the detail names it [criterion 1]",
        case_version_1_is_report_unreadable_and_names_it,
    ),
    (
        "a missing version 2 field is report-unreadable [criterion 1]",
        case_missing_version_2_field_is_report_unreadable,
    ),
    (
        "counts that disagree with the rows are report-unreadable",
        case_counts_disagreeing_with_rows_is_report_unreadable,
    ),
    ("another head is report-stale [criterion 1]", case_other_head_is_report_stale),
    ("another bead is bead-mismatch [criterion 1]", case_other_bead_is_bead_mismatch),
    (
        "a null report bead is bead-mismatch [criterion 1]",
        case_null_report_bead_is_bead_mismatch,
    ),
    (
        "a dirty changed file is uncommitted-changes [criterion 1]",
        case_dirty_changed_file_is_uncommitted_changes,
    ),
    (
        "only blocked gates is needs-environment [criterion 1]",
        case_only_blocked_gates_is_needs_environment,
    ),
    (
        "only UNVERIFIABLE criteria prints needs-human-check [criteria 1, 3]",
        case_only_unverifiable_prints_needs_human_check,
    ),
    (
        "a report with no criteria is needs-human-check",
        case_no_criteria_is_needs_human_check,
    ),
]:
    check(name, fn)

print("\n  [what does not block]")


def case_no_bead_argument_skips_the_bead_check() -> None:
    body = report(FAILING["criteria"], FAILING["gates"], bead=None)
    assert load(body).exit_code == 0


def case_dirty_file_outside_the_change_does_not_block() -> None:
    assert load(FAILING, dirty={"README.md"}).exit_code == 0


def case_null_base_leaves_dirty_files_to_the_skill() -> None:
    body = report(FAILING["criteria"], FAILING["gates"], base=None, changed_files=None)
    outcome = load(body, dirty={"src/auth.py"})
    assert findings_of(outcome)["scope_known"] is False


def case_fail_in_no_changed_file_stays_in_scope() -> None:
    body = report(FAILING["criteria"], FAILING["gates"], changed_files=[])
    outcome = load(body)
    assert reason_of(outcome) != "failures-outside-change", f"got {outcome!r}"
    assert len(findings_of(outcome)["in_scope"]) == 2


for name, fn in [
    ("no --bead skips the bead check", case_no_bead_argument_skips_the_bead_check),
    (
        "a dirty file outside the change does not block",
        case_dirty_file_outside_the_change_does_not_block,
    ),
    (
        "a null base leaves dirty files to the skill",
        case_null_base_leaves_dirty_files_to_the_skill,
    ),
    (
        "a FAIL with no changed file stays in scope, never failures-outside-change [criterion 1]",
        case_fail_in_no_changed_file_stays_in_scope,
    ),
]:
    check(name, fn)

print("\n  [when several reasons hold, the first wins]")


def case_unreadable_beats_stale() -> None:
    body = report([criterion(1, "FAIL")], version=1)
    assert reason_of(load(body, head="f" * 40)) == "report-unreadable"


def case_stale_beats_bead_mismatch() -> None:
    assert reason_of(load(FAILING, head="f" * 40, bead="tadw-xyz")) == "report-stale"


def case_bead_mismatch_beats_uncommitted_changes() -> None:
    outcome = load(FAILING, dirty={"src/auth.py"}, bead="tadw-xyz")
    assert reason_of(outcome) == "bead-mismatch"


def case_needs_environment_beats_needs_human_check() -> None:
    assert reason_of(load(ONLY_BLOCKED)) == "needs-environment"


def case_stale_beats_nothing_to_fix() -> None:
    assert reason_of(load(ACCEPTED, head="f" * 40)) == "report-stale"


for name, fn in [
    ("report-unreadable beats report-stale [criterion 1]", case_unreadable_beats_stale),
    ("report-stale beats bead-mismatch [criterion 1]", case_stale_beats_bead_mismatch),
    (
        "bead-mismatch beats uncommitted-changes [criterion 1]",
        case_bead_mismatch_beats_uncommitted_changes,
    ),
    (
        "needs-environment beats needs-human-check [criterion 1]",
        case_needs_environment_beats_needs_human_check,
    ),
    (
        "a stale ACCEPTED report is report-stale, not exit 3",
        case_stale_beats_nothing_to_fix,
    ),
]:
    check(name, fn)

print("\n  [with counts that make the report ACCEPTED]")


def case_accepted_counts_exit_3() -> None:
    assert load(ACCEPTED).exit_code == 3


def case_accepted_prints_nothing_on_stdout() -> None:
    assert stdout_of(load(ACCEPTED)) == ""


def case_no_gates_is_not_accepted() -> None:
    assert load(report([criterion(1, "PASS")], gates=[])).exit_code == 1


for name, fn in [
    ("ACCEPTED counts exit 3 [criterion 2]", case_accepted_counts_exit_3),
    ("ACCEPTED prints nothing on stdout", case_accepted_prints_nothing_on_stdout),
    (
        "a report with no gates is not ACCEPTED, as the label hook reads it",
        case_no_gates_is_not_accepted,
    ),
]:
    check(name, fn)

print("\n  [how the findings split]")


def failing_findings() -> dict:
    return findings_of(load(FAILING))


def by_key(entries: list[dict], key: str, value) -> dict | None:
    return next((e for e in entries if e.get(key) == value), None)


def case_fail_criterion_is_in_scope_with_its_command() -> None:
    entry = by_key(failing_findings()["in_scope"], "criterion", 2)
    assert entry is not None, "criterion 2 must be in scope"
    assert entry["command"] == "pytest tests/test_auth.py::test_rejects_expired"


def case_fail_gate_is_in_scope() -> None:
    assert by_key(failing_findings()["in_scope"], "gate", "Tests") is not None


def case_unverifiable_criterion_has_no_evidence() -> None:
    entry = by_key(failing_findings()["out_of_scope"], "criterion", 3)
    assert entry is not None, "criterion 3 must be out of scope"
    assert "evidence" not in entry, f"out of scope must drop evidence: {entry!r}"


def case_blocked_gate_is_out_of_scope() -> None:
    assert by_key(failing_findings()["out_of_scope"], "gate", "Lint") is not None


def case_pass_and_skip_rows_are_not_findings() -> None:
    findings = failing_findings()
    every = findings["in_scope"] + findings["out_of_scope"]
    assert by_key(every, "criterion", 1) is None, "a PASS criterion is not a finding"
    assert by_key(every, "gate", "Type checking") is None, "a SKIP gate is not a finding"


def case_known_base_marks_scope_known() -> None:
    findings = failing_findings()
    assert findings["scope_known"] is True
    assert findings["base"] == BASE


for name, fn in [
    (
        "a FAIL criterion is in scope with its command",
        case_fail_criterion_is_in_scope_with_its_command,
    ),
    ("a FAIL gate is in scope", case_fail_gate_is_in_scope),
    (
        "an out-of-scope criterion carries no evidence [criterion 4]",
        case_unverifiable_criterion_has_no_evidence,
    ),
    ("a BLOCKED gate is out of scope", case_blocked_gate_is_out_of_scope),
    ("PASS and SKIP rows are not findings", case_pass_and_skip_rows_are_not_findings),
    ("a known base marks scope_known true", case_known_base_marks_scope_known),
]:
    check(name, fn)

print("\n  [from the command line]")

WORKDIR = Path(tempfile.mkdtemp()).resolve()
REPORT_FILE = WORKDIR / "acceptance-report.json"
REPORT_FILE.write_text(json.dumps(FAILING), encoding="utf-8")
CLEAN_STATUS = WORKDIR / "clean-status"
CLEAN_STATUS.write_bytes(b"")
RENAME_STATUS = WORKDIR / "rename-status"
RENAME_STATUS.write_bytes(b"R  src/session.py\0src/auth.py\0?? notes.txt\0")


def run_cli(
    report: Path = REPORT_FILE,
    head: str = HEAD,
    dirty_files: Path = CLEAN_STATUS,
    bead: str | None = None,
) -> tuple[int, str, str]:
    """The loader's process-boundary behavior: argv in, exit code and streams out."""
    argv = ["--report", str(report), "--head", head, "--dirty-files", str(dirty_files)]
    if bead is not None:
        argv += ["--bead", bead]
    out, err = io.StringIO(), io.StringIO()
    code = loader.main(argv, out, err)
    return code, out.getvalue(), err.getvalue()


def case_missing_report_path_ends_on_the_machine_line() -> None:
    code, out, _ = run_cli(report=WORKDIR / "absent.json")
    assert code == 1, f"must exit 1, got {code}"
    assert out.splitlines()[-1] == "RECONCILE_ACCEPTANCE_BLOCKED report-missing", out


def case_findings_print_as_json() -> None:
    code, out, _ = run_cli()
    assert code == 0, f"must exit 0, got {code}"
    assert len(json.loads(out)["in_scope"]) == 2


def case_renamed_from_path_counts_as_dirty() -> None:
    code, out, _ = run_cli(dirty_files=RENAME_STATUS)
    assert code == 1, f"the rename's original path is a changed file, got {code}: {out!r}"
    assert out.strip() == "RECONCILE_ACCEPTANCE_BLOCKED uncommitted-changes", out


def case_unreadable_report_stops_with_its_own_cause() -> None:
    old = WORKDIR / "old-report.json"
    old.write_text(json.dumps({"version": 1}), encoding="utf-8")
    code, out, _ = run_cli(report=old)
    assert code == 1 and "report-unreadable" in out, out


def case_unreadable_detail_goes_to_stderr() -> None:
    old = WORKDIR / "old-report.json"
    old.write_text(json.dumps({"version": 1}), encoding="utf-8")
    _, _, err = run_cli(report=old)
    assert "version is 1" in err, f"stderr must name the version: {err!r}"


def case_unreadable_dirty_files_is_a_usage_error() -> None:
    code, _, _ = run_cli(dirty_files=WORKDIR / "absent")
    assert code == 2, f"must exit 2, got {code}"


def case_blank_head_is_a_usage_error() -> None:
    code, _, _ = run_cli(head="  ")
    assert code == 2, f"must exit 2, got {code}"


def case_blank_bead_is_a_usage_error() -> None:
    code, _, _ = run_cli(bead="  ")
    assert code == 2, f"a blank --bead must exit 2, got {code}"


for name, fn in [
    (
        "a missing report path ends on the BLOCKED machine line",
        case_missing_report_path_ends_on_the_machine_line,
    ),
    ("findings print as JSON on exit 0", case_findings_print_as_json),
    (
        "a rename's original path counts as dirty",
        case_renamed_from_path_counts_as_dirty,
    ),
    (
        "an unreadable report stops with report-unreadable",
        case_unreadable_report_stops_with_its_own_cause,
    ),
    (
        "an unreadable report's detail goes to stderr",
        case_unreadable_detail_goes_to_stderr,
    ),
    (
        "an unreadable --dirty-files exits 2",
        case_unreadable_dirty_files_is_a_usage_error,
    ),
    ("a blank --head exits 2", case_blank_head_is_a_usage_error),
    ("a blank --bead exits 2", case_blank_bead_is_a_usage_error),
]:
    check(name, fn)

print("\n  [through a real subprocess]")


def run_subprocess(*args: str) -> subprocess.CompletedProcess[str]:
    """`python3 load_findings.py ...`, the way the reconcile-acceptance skill

    calls it: a real process, real argv, and the interpreter's own exit code.
    """
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def case_subprocess_missing_report_ends_on_the_machine_line() -> None:
    result = run_subprocess(
        "--report",
        str(WORKDIR / "absent.json"),
        "--head",
        HEAD,
        "--dirty-files",
        str(CLEAN_STATUS),
    )
    assert result.returncode == 1, f"must exit 1, got {result.returncode}"
    assert result.stdout.splitlines()[-1] == "RECONCILE_ACCEPTANCE_BLOCKED report-missing", (
        result.stdout
    )


def case_subprocess_findings_print_as_json_on_exit_0() -> None:
    result = run_subprocess(
        "--report", str(REPORT_FILE), "--head", HEAD, "--dirty-files", str(CLEAN_STATUS)
    )
    assert result.returncode == 0, f"must exit 0, got {result.returncode}: {result.stderr}"
    assert len(json.loads(result.stdout)["in_scope"]) == 2


def case_subprocess_blank_head_exits_2() -> None:
    result = run_subprocess(
        "--report", str(REPORT_FILE), "--head", "  ", "--dirty-files", str(CLEAN_STATUS)
    )
    assert result.returncode == 2, f"must exit 2, got {result.returncode}"


for name, fn in [
    (
        "a missing report path ends on the BLOCKED machine line, through a real process",
        case_subprocess_missing_report_ends_on_the_machine_line,
    ),
    (
        "findings print as JSON on exit 0, through a real process",
        case_subprocess_findings_print_as_json_on_exit_0,
    ),
    (
        "a blank --head exits 2, through a real process",
        case_subprocess_blank_head_exits_2,
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
    assert not lines, f"the loader must run no process: {lines}"


def case_reasons_keep_the_plan_order() -> None:
    assert loader.REASONS == (
        "report-missing",
        "report-unreadable",
        "report-stale",
        "bead-mismatch",
        "uncommitted-changes",
        "failures-outside-change",
        "needs-environment",
        "needs-human-check",
        "finding-not-fixed",
        "commit-failed",
    ), f"got {loader.REASONS}"


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__",
        "argparse",
        "collections",
        "dataclasses",
        "importlib",
        "io",
        "json",
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
    assert "python3 skills/reconcile-acceptance/scripts/test_load_findings.py" in agents


def case_skill_names_every_reason_and_machine_line() -> None:
    skill_path = HERE.parent / "SKILL.md"
    skill = skill_path.read_text(encoding="utf-8")
    # A word boundary, not backticks: rewording SKILL.md's formatting must not fail this case.
    missing_reasons = [
        r for r in loader.REASONS if not re.search(rf"(?<![\w-]){re.escape(r)}(?![\w-])", skill)
    ]
    assert not missing_reasons, f"SKILL.md never names: {missing_reasons}"
    for line_name in (loader.DONE_LINE, loader.BLOCKED_LINE):
        assert line_name in skill, f"SKILL.md never names the machine line {line_name}"


for name, fn in [
    (
        "the script never names subprocess [criterion 5]",
        case_script_never_names_subprocess,
    ),
    ("the ten reasons keep the plan's order", case_reasons_keep_the_plan_order),
    ("neither file imports outside the standard library", case_no_third_party_imports),
    ("AGENTS.md lists this suite [criterion 6]", case_agents_md_lists_this_suite),
    (
        "SKILL.md names all ten reason tokens and both machine lines [tadw-568 criterion 1]",
        case_skill_names_every_reason_and_machine_line,
    ),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
