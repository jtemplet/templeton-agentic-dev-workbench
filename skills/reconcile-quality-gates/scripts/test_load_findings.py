#!/usr/bin/env python3
"""Regression suite for load_findings.py.

Stdlib only, no install, and no git repository. Run with:
    python3 skills/reconcile-quality-gates/scripts/test_load_findings.py

Nearly every case calls the loader in-process with injected values, so most of
the suite starts no process (`load()` for the pure function, `run_cli()` for
`main()` with an argument list and two string buffers). The
"[through a real subprocess]" group is the exception, on purpose: it invokes
`python3 load_findings.py ...` the way the reconcile-quality-gates skill does,
so the CLI surface has a test that drives its real entry point.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-gni criterion                             Pinned by
  ------------------------------------------------------------------------------
  1. Each loader reason 1 to 8, in order         the [each reason] and [first
                                                 reason wins] groups
  2. PASS or NO GATES RAN exits 3                case_pass_verdict_exits_3,
                                                 case_no_gates_ran_verdict_exits_3
  3. Inside the change in scope, outside not     case_fail_in_changed_file_is_in_scope,
                                                 case_fail_outside_change_is_out_of_scope
  4. Out of scope carries no evidence            case_out_of_scope_entry_has_no_evidence
  5. No subprocess in the script                 case_script_never_names_subprocess
  6. AGENTS.md names this suite                  case_agents_md_lists_this_suite

  tadw-1v7 criterion                             Pinned by
  ------------------------------------------------------------------------------
  1. SKILL.md names all ten reasons and both     case_skill_names_every_reason_and_machine_line
     machine lines
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
OTHER_HEAD = "f" * 40
BASE = {"ref": "origin/HEAD", "sha": "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"}
CHANGED = ["src/api/exports.py", "tests/test_exports.py"]
CHANGED_FILE = "src/api/exports.py"
OUTSIDE_FILE = "src/legacy/report.py"


def gate(name: str, status: str) -> dict:
    return {"name": name, "status": status, "command": f"run {name.lower()}", "detail": status}


def finding(gate_name: str, file: str | None, problem: str = "F841 unused variable") -> dict:
    return {
        "gate": gate_name,
        "file": file,
        "line": None if file is None else 88,
        "problem": problem,
        "evidence": f"{file}:88:5: {problem}",
    }


def report(gates: list[dict], findings: list[dict], verdict: str = "FAIL", **overrides) -> dict:
    """A version 2 quality-gates report, with every field the writer writes."""
    body = {
        "version": 2,
        "head": HEAD,
        "dirty": False,
        "timestamp": "2026-09-14T12:00:00Z",
        "scope": "changed",
        "gate_source": "AGENTS.md",
        "routing": {},
        "bead": "tadw-abc",
        "base": BASE,
        "changed_files": CHANGED,
        "verdict": verdict,
        "gates": gates,
        "findings": findings,
    }
    body.update(overrides)
    return body


LINT_FAIL = [gate("Lint", "FAIL"), gate("Tests", "PASS")]
IN_CHANGE = report(LINT_FAIL, [finding("Lint", CHANGED_FILE)])
OUTSIDE_CHANGE = report(LINT_FAIL, [finding("Lint", OUTSIDE_FILE)])
MIXED = report(
    [gate("Lint", "FAIL"), gate("Tests", "FAIL"), gate("Types", "WARN"), gate("Docs", "BLOCKED")],
    [
        finding("Lint", CHANGED_FILE, "F841 unused variable"),
        finding("Lint", OUTSIDE_FILE, "E711 comparison to None"),
        finding("Tests", None, "test_export_csv failed"),
        finding("Types", CHANGED_FILE, "missing return type"),
    ],
)
ONLY_BLOCKED = report([gate("Tests", "PASS"), gate("Docs", "BLOCKED")], [])
ONLY_HANDOFF = report([gate("Tests", "PASS"), gate("QA", "HANDOFF")], [], verdict="INCOMPLETE")
PASSING = report([gate("Lint", "PASS"), gate("Tests", "PASS")], [], verdict="PASS")


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


def with_field(body: dict, **fields) -> dict:
    return {**body, **fields}


def without_field(body: dict, name: str) -> dict:
    return {key: value for key, value in body.items() if key != name}


print("\n  [each reason, when its condition holds]")


def case_no_report_is_report_missing() -> None:
    assert reason_of(load(None)) == "report-missing"


def case_invalid_json_is_report_unreadable() -> None:
    assert reason_of(load("{not json")) == "report-unreadable"


def case_version_1_is_report_unreadable_and_names_it() -> None:
    outcome = load(with_field(IN_CHANGE, version=1))
    assert reason_of(outcome) == "report-unreadable", f"got {outcome!r}"
    assert "version is 1" in outcome.detail, f"must name the version: {outcome.detail!r}"


def case_missing_findings_field_is_report_unreadable() -> None:
    assert reason_of(load(without_field(IN_CHANGE, "findings"))) == "report-unreadable"


def case_status_outside_the_six_is_report_unreadable() -> None:
    body = report([gate("Lint", "ERROR")], [])
    assert reason_of(load(body)) == "report-unreadable"


def case_finding_naming_no_gate_row_is_report_unreadable() -> None:
    body = report(LINT_FAIL, [finding("Security", CHANGED_FILE)])
    assert reason_of(load(body)) == "report-unreadable"


def case_repeated_gate_name_is_report_unreadable() -> None:
    body = report([gate("Tests", "FAIL"), gate("Tests", "PASS")], [finding("Tests", None)])
    assert reason_of(load(body)) == "report-unreadable"


def case_base_without_changed_files_is_report_unreadable() -> None:
    assert reason_of(load(with_field(IN_CHANGE, changed_files=None))) == "report-unreadable"


def case_other_head_is_report_stale() -> None:
    assert reason_of(load(IN_CHANGE, head=OTHER_HEAD)) == "report-stale"


def case_other_bead_is_bead_mismatch() -> None:
    assert reason_of(load(IN_CHANGE, bead="tadw-xyz")) == "bead-mismatch"


def case_null_report_bead_is_bead_mismatch() -> None:
    assert reason_of(load(with_field(IN_CHANGE, bead=None), bead="tadw-abc")) == "bead-mismatch"


def case_dirty_in_scope_file_is_uncommitted_changes() -> None:
    outcome = load(IN_CHANGE, dirty={CHANGED_FILE})
    assert reason_of(outcome) == "uncommitted-changes", f"got {outcome!r}"
    assert CHANGED_FILE in outcome.detail, f"must name the file: {outcome.detail!r}"


def case_every_fail_outside_change_is_failures_outside_change() -> None:
    assert reason_of(load(OUTSIDE_CHANGE)) == "failures-outside-change"


def case_only_blocked_gate_is_needs_environment() -> None:
    assert reason_of(load(ONLY_BLOCKED)) == "needs-environment"


def case_only_handoff_gate_prints_needs_human_check() -> None:
    outcome = load(ONLY_HANDOFF)
    assert outcome.exit_code == 1, f"must exit 1, got {outcome.exit_code}"
    assert stdout_of(outcome) == "RECONCILE_QUALITY_GATES_BLOCKED needs-human-check\n"


def case_fail_gate_with_no_finding_is_needs_human_check() -> None:
    assert reason_of(load(report(LINT_FAIL, []))) == "needs-human-check"


for name, fn in [
    ("no report is report-missing [criterion 1]", case_no_report_is_report_missing),
    ("invalid JSON is report-unreadable [criterion 1]", case_invalid_json_is_report_unreadable),
    (
        "version 1 is report-unreadable, and the detail names it [criterion 1]",
        case_version_1_is_report_unreadable_and_names_it,
    ),
    (
        "a missing `findings` field is report-unreadable [criterion 1]",
        case_missing_findings_field_is_report_unreadable,
    ),
    (
        "a gate status outside the six is report-unreadable",
        case_status_outside_the_six_is_report_unreadable,
    ),
    (
        "a finding that names no gate row is report-unreadable",
        case_finding_naming_no_gate_row_is_report_unreadable,
    ),
    ("a repeated gate name is report-unreadable", case_repeated_gate_name_is_report_unreadable),
    (
        "a base with a null changed_files is report-unreadable",
        case_base_without_changed_files_is_report_unreadable,
    ),
    ("another head is report-stale [criterion 1]", case_other_head_is_report_stale),
    ("another bead is bead-mismatch [criterion 1]", case_other_bead_is_bead_mismatch),
    ("a null report bead is bead-mismatch [criterion 1]", case_null_report_bead_is_bead_mismatch),
    (
        "a dirty file an in-scope finding names is uncommitted-changes [criterion 1]",
        case_dirty_in_scope_file_is_uncommitted_changes,
    ),
    (
        "every FAIL finding outside the change is failures-outside-change [criterion 1]",
        case_every_fail_outside_change_is_failures_outside_change,
    ),
    (
        "only a BLOCKED gate is needs-environment [criterion 1]",
        case_only_blocked_gate_is_needs_environment,
    ),
    (
        "only a HANDOFF gate prints needs-human-check on exit 1 [criterion 1]",
        case_only_handoff_gate_prints_needs_human_check,
    ),
    (
        "a FAIL gate with no finding is needs-human-check",
        case_fail_gate_with_no_finding_is_needs_human_check,
    ),
]:
    check(name, fn)

print("\n  [when several reasons hold, the first wins]")


def case_unreadable_beats_stale() -> None:
    assert reason_of(load(with_field(IN_CHANGE, version=1), head=OTHER_HEAD)) == "report-unreadable"


def case_stale_beats_bead_mismatch() -> None:
    assert reason_of(load(IN_CHANGE, head=OTHER_HEAD, bead="tadw-xyz")) == "report-stale"


def case_bead_mismatch_beats_uncommitted_changes() -> None:
    outcome = load(IN_CHANGE, dirty={CHANGED_FILE}, bead="tadw-xyz")
    assert reason_of(outcome) == "bead-mismatch"


def case_failures_outside_change_beats_needs_environment() -> None:
    body = report([*LINT_FAIL, gate("Docs", "BLOCKED")], [finding("Lint", OUTSIDE_FILE)])
    assert reason_of(load(body)) == "failures-outside-change"


def case_needs_environment_beats_needs_human_check() -> None:
    body = report([gate("Docs", "BLOCKED"), gate("QA", "HANDOFF")], [])
    assert reason_of(load(body)) == "needs-environment"


def case_stale_pass_report_is_report_stale() -> None:
    assert reason_of(load(PASSING, head=OTHER_HEAD)) == "report-stale"


for name, fn in [
    ("report-unreadable beats report-stale [criterion 1]", case_unreadable_beats_stale),
    ("report-stale beats bead-mismatch [criterion 1]", case_stale_beats_bead_mismatch),
    (
        "bead-mismatch beats uncommitted-changes [criterion 1]",
        case_bead_mismatch_beats_uncommitted_changes,
    ),
    (
        "failures-outside-change beats needs-environment [criterion 1]",
        case_failures_outside_change_beats_needs_environment,
    ),
    (
        "needs-environment beats needs-human-check [criterion 1]",
        case_needs_environment_beats_needs_human_check,
    ),
    ("a stale PASS report is report-stale, not exit 3", case_stale_pass_report_is_report_stale),
]:
    check(name, fn)

print("\n  [when the verdict leaves nothing to fix]")


def case_pass_verdict_exits_3() -> None:
    assert load(PASSING).exit_code == 3


def case_no_gates_ran_verdict_exits_3() -> None:
    body = report([gate("Tests", "SKIP")], [], verdict="NO GATES RAN")
    assert load(body).exit_code == 3


def case_nothing_to_fix_prints_nothing_on_stdout() -> None:
    assert stdout_of(load(PASSING)) == ""


for name, fn in [
    ("a PASS verdict exits 3 [criterion 2]", case_pass_verdict_exits_3),
    ("a NO GATES RAN verdict exits 3 [criterion 2]", case_no_gates_ran_verdict_exits_3),
    ("exit 3 prints nothing on stdout", case_nothing_to_fix_prints_nothing_on_stdout),
]:
    check(name, fn)

print("\n  [what does not block]")


def case_no_bead_argument_skips_the_bead_check() -> None:
    assert load(with_field(IN_CHANGE, bead=None)).exit_code == 0


def case_dirty_file_of_out_of_scope_finding_does_not_block() -> None:
    assert load(MIXED, dirty={OUTSIDE_FILE, "README.md"}).exit_code == 0


def case_null_file_finding_on_fail_gate_stays_in_scope() -> None:
    body = report([gate("Tests", "FAIL")], [finding("Tests", None)], changed_files=[])
    assert len(findings_of(load(body))["in_scope"]) == 1


for name, fn in [
    ("no --bead skips the bead check", case_no_bead_argument_skips_the_bead_check),
    (
        "a dirty file that no in-scope finding names does not block",
        case_dirty_file_of_out_of_scope_finding_does_not_block,
    ),
    (
        "a FAIL finding with a null file stays in scope, never failures-outside-change",
        case_null_file_finding_on_fail_gate_stays_in_scope,
    ),
]:
    check(name, fn)

print("\n  [how the findings split]")


def mixed_findings() -> dict:
    return findings_of(load(MIXED))


def by_problem(entries: list[dict], problem: str) -> dict | None:
    return next((entry for entry in entries if entry["problem"] == problem), None)


def case_fail_in_changed_file_is_in_scope() -> None:
    assert by_problem(mixed_findings()["in_scope"], "F841 unused variable") is not None


def case_fail_outside_change_is_out_of_scope() -> None:
    findings = mixed_findings()
    assert by_problem(findings["out_of_scope"], "E711 comparison to None") is not None
    assert by_problem(findings["in_scope"], "E711 comparison to None") is None


def case_out_of_scope_entry_has_no_evidence() -> None:
    entry = by_problem(mixed_findings()["out_of_scope"], "E711 comparison to None")
    assert entry == {"gate": "Lint", "file": OUTSIDE_FILE, "problem": "E711 comparison to None"}, (
        f"out of scope must hold only gate, file, and problem: {entry!r}"
    )


def case_in_scope_entry_keeps_evidence_and_gate_command() -> None:
    entry = by_problem(mixed_findings()["in_scope"], "F841 unused variable")
    assert entry["evidence"] == f"{CHANGED_FILE}:88:5: F841 unused variable", entry
    assert entry["line"] == 88, entry
    assert entry["command"] == "run lint", entry


def case_finding_on_warn_gate_is_out_of_scope() -> None:
    assert by_problem(mixed_findings()["out_of_scope"], "missing return type") is not None


def case_null_base_puts_every_fail_finding_in_scope() -> None:
    findings = findings_of(load(with_field(OUTSIDE_CHANGE, base=None, changed_files=None)))
    assert len(findings["in_scope"]) == 1, findings
    assert findings["scope_known"] is False


def case_known_base_is_echoed_with_scope_known() -> None:
    findings = mixed_findings()
    assert (findings["base"], findings["bead"], findings["scope_known"]) == (BASE, "tadw-abc", True)


for name, fn in [
    (
        "a FAIL finding in a changed file is in scope [criterion 3]",
        case_fail_in_changed_file_is_in_scope,
    ),
    (
        "a FAIL finding outside changed_files is out of scope [criterion 3]",
        case_fail_outside_change_is_out_of_scope,
    ),
    (
        "an out-of-scope entry has no evidence key [criterion 4]",
        case_out_of_scope_entry_has_no_evidence,
    ),
    (
        "an in-scope entry keeps its evidence and line, and gains its gate's command",
        case_in_scope_entry_keeps_evidence_and_gate_command,
    ),
    ("a finding on a WARN gate is out of scope", case_finding_on_warn_gate_is_out_of_scope),
    (
        "a null base puts every FAIL finding in scope, with scope_known false",
        case_null_base_puts_every_fail_finding_in_scope,
    ),
    (
        "a known base prints base, bead, and scope_known true",
        case_known_base_is_echoed_with_scope_known,
    ),
]:
    check(name, fn)

print("\n  [from the command line]")

WORKDIR = Path(tempfile.mkdtemp()).resolve()
REPORT_FILE = WORKDIR / "quality-gates-report.json"
REPORT_FILE.write_text(json.dumps(MIXED), encoding="utf-8")
PASSING_FILE = WORKDIR / "passing-report.json"
PASSING_FILE.write_text(json.dumps(PASSING), encoding="utf-8")
CLEAN_STATUS = WORKDIR / "clean-status"
CLEAN_STATUS.write_bytes(b"")
RENAME_STATUS = WORKDIR / "rename-status"
RENAME_STATUS.write_bytes(f"R  src/api/csv.py\0{CHANGED_FILE}\0?? notes.txt\0".encode())


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
    assert out.splitlines()[-1] == "RECONCILE_QUALITY_GATES_BLOCKED report-missing", out


def case_findings_print_as_json() -> None:
    code, out, _ = run_cli()
    assert code == 0, f"must exit 0, got {code}"
    assert len(json.loads(out)["in_scope"]) == 2


def case_renamed_from_path_counts_as_dirty() -> None:
    code, out, _ = run_cli(dirty_files=RENAME_STATUS)
    assert code == 1, f"the rename's original path is an in-scope file, got {code}: {out!r}"
    assert out.strip() == "RECONCILE_QUALITY_GATES_BLOCKED uncommitted-changes", out


def case_report_that_will_not_open_is_report_unreadable_with_its_cause() -> None:
    code, out, err = run_cli(report=WORKDIR)
    assert (code, out.strip()) == (1, "RECONCILE_QUALITY_GATES_BLOCKED report-unreadable"), out
    assert "could not be read" in err, f"stderr must give the cause: {err!r}"


def case_report_path_that_names_no_file_is_a_usage_error() -> None:
    codes = [run_cli(report=Path(value))[0] for value in ("", ".", "/")]
    assert codes == [2, 2, 2], f"each must exit 2, got {codes}"


def case_unreadable_dirty_files_is_a_usage_error() -> None:
    code, _, _ = run_cli(dirty_files=WORKDIR / "absent")
    assert code == 2, f"must exit 2, got {code}"


def case_head_that_is_not_a_commit_id_is_a_usage_error() -> None:
    code, _, _ = run_cli(head="HEAD")
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
    ("a rename's original path counts as dirty", case_renamed_from_path_counts_as_dirty),
    (
        "a report path that will not open is report-unreadable, with its cause on stderr",
        case_report_that_will_not_open_is_report_unreadable_with_its_cause,
    ),
    (
        "a --report that names no file exits 2",
        case_report_path_that_names_no_file_is_a_usage_error,
    ),
    ("an unreadable --dirty-files exits 2", case_unreadable_dirty_files_is_a_usage_error),
    (
        "a --head that is not a commit id exits 2",
        case_head_that_is_not_a_commit_id_is_a_usage_error,
    ),
    ("a blank --bead exits 2", case_blank_bead_is_a_usage_error),
]:
    check(name, fn)

print("\n  [through a real subprocess]")


def run_subprocess(report: Path, head: str = HEAD) -> subprocess.CompletedProcess[str]:
    """`python3 load_findings.py ...`, the way the reconcile-quality-gates skill

    calls it: a real process, real argv, and the interpreter's own exit code.
    """
    argv = ["--report", str(report), "--head", head, "--dirty-files", str(CLEAN_STATUS)]
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def case_subprocess_missing_report_ends_on_the_machine_line() -> None:
    result = run_subprocess(WORKDIR / "absent.json")
    assert result.returncode == 1, f"must exit 1, got {result.returncode}"
    assert result.stdout.splitlines()[-1] == "RECONCILE_QUALITY_GATES_BLOCKED report-missing", (
        result.stdout
    )


def case_subprocess_findings_print_as_json_on_exit_0() -> None:
    result = run_subprocess(REPORT_FILE)
    assert result.returncode == 0, f"must exit 0, got {result.returncode}: {result.stderr}"
    assert len(json.loads(result.stdout)["in_scope"]) == 2


def case_subprocess_pass_verdict_exits_3() -> None:
    result = run_subprocess(PASSING_FILE)
    assert result.returncode == 3, f"must exit 3, got {result.returncode}: {result.stderr}"


def case_subprocess_bad_head_exits_2() -> None:
    result = run_subprocess(REPORT_FILE, head="  ")
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
    ("a PASS verdict exits 3, through a real process", case_subprocess_pass_verdict_exits_3),
    ("a blank --head exits 2, through a real process", case_subprocess_bad_head_exits_2),
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


def case_machine_lines_name_this_skill() -> None:
    assert (loader.DONE_LINE, loader.BLOCKED_LINE) == (
        "RECONCILE_QUALITY_GATES_DONE",
        "RECONCILE_QUALITY_GATES_BLOCKED",
    )


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
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.MULTILINE))
        outside = {module for module in imported if module.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


def case_agents_md_lists_this_suite() -> None:
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "python3 skills/reconcile-quality-gates/scripts/test_load_findings.py" in agents


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
    ("the script never names subprocess [criterion 5]", case_script_never_names_subprocess),
    ("the ten reasons keep the plan's order", case_reasons_keep_the_plan_order),
    ("the machine lines name reconcile-quality-gates", case_machine_lines_name_this_skill),
    ("neither file imports outside the standard library", case_no_third_party_imports),
    ("AGENTS.md lists this suite [criterion 6]", case_agents_md_lists_this_suite),
    (
        "SKILL.md names all ten reason tokens and both machine lines [tadw-1v7 criterion 1]",
        case_skill_names_every_reason_and_machine_line,
    ),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
