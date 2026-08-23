#!/usr/bin/env python3
"""Regression suite for run.py's fixture and single-arm support.

Stdlib only, no install, mirroring test_changed_set.py. Run with:
    python3 evals/test_run.py

WHY THIS SUITE EXISTS WITHOUT CALLING A MODEL. Every eval case is a paid call to
`claude -p`, so the suite that guards the harness cannot be the suite that runs
the cases. What is testable for free is everything around the call: which arms a
case runs, which directory the call is made from, and what that directory
contains. This file imports run.py and exercises exactly that, so a regression in
the harness fails in seconds rather than after a paid run reports a confusing
result.

CRITERION-TO-TEST MAPPING, from bead tadw-qg-eval-fixture-harness-e4i.

  Criterion                                        Pinned by
  ------------------------------------------------------------------------------
  1. The six existing cases behave as before       case_shipped_cases_are_untouched
                                                   case_case_without_fixture_runs_in_repo_root
                                                   case_case_without_single_arm_runs_both_arms
  2. A fixture case runs in a temp git repository,  case_model_call_happens_in_the_fixture
     not the repository root                       case_fixture_is_a_temp_repo_not_the_root
                                                   case_fixture_base_is_committed
                                                   case_fixture_plant_is_left_uncommitted
                                                   case_fixture_origin_resolves_a_base
  3. `single_arm` runs only the with-plugin arm     case_single_arm_runs_one_arm
  4. README documents both keys and the reason      case_readme_documents_both_keys

THE FIRST TEST UNDER CRITERION 2 IS THE ONE THAT PROVES THE BEAD. The four below
it check the directory the harness BUILDS; only that one checks the directory the
call is MADE FROM, using a fake `claude` on PATH that reports its own working
directory. Measured: with it absent, changing `ask` to `cwd=str(REPO_ROOT)`, which
is the exact defect this bead was filed to fix, passed all fourteen other checks.

Four more failure modes carry their own test, each a way the harness could waste a
paid run, corrupt a result, or misreport its own scope:

  A misnamed fixture fails before any call        case_missing_fixture_fails_fast
  Each run gets its own copy of the fixture       case_two_runs_get_independent_trees
  --keep-fixtures leaves the tree, and says where case_keep_fixtures_leaves_the_tree
  The header states a skipped arm                 case_header_counts_single_arm_and_fixture_cases

The CLI is also exercised through its real entry point, by argv and exit code
rather than by import, in case_cli_help_exits_zero and
case_cli_unknown_case_exits_one. Neither costs a model call.
"""

from __future__ import annotations

import argparse
import atexit
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run as harness  # noqa: E402  (the path insert above has to come first)

EVALS = Path(__file__).resolve().parent
README = EVALS / "README.md"

# The cases that shipped before fixture support existed. Named rather than
# counted, so adding a seventh case does not silently satisfy criterion 1.
SHIPPED_CASES = {
    "decision-matrix-suppress",
    "decision-matrix-trigger",
    "exact-names",
    "jargon-tombstone",
    "plain-sentences",
    "self-report-plainly",
}

# Every directory built outside a `with` block, removed at exit the way
# .githooks/test_prepush.py does it. Measured before this existed: each run left
# three `tadw-test-work-*` trees behind, two git repositories each, and the suite
# runs on every push.
workspaces: list[Path] = []

passed = 0
failed = 0


@atexit.register
def _cleanup() -> None:
    for path in workspaces:
        shutil.rmtree(path, ignore_errors=True)


def check(name: str, fn) -> None:
    """Run one case. Any exception is a failure, and no case stops the next one.

    Catching Exception rather than AssertionError alone is deliberate: a case that
    shells out to git can raise CalledProcessError, and an uncaught one would abort
    the suite so the cases after it never run. Measured while mutation-testing this
    file, that is exactly what happened, and the run reported nothing at all.
    """
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1
    except Exception as exc:  # noqa: BLE001  (see the docstring)
        print(f"  FAIL - {name}\n         raised {type(exc).__name__}: {exc}")
        failed += 1


@contextlib.contextmanager
def fixture_named(name: str, base: dict[str, str], plant: dict[str, str] | None = None) -> Iterator[None]:
    """Write a fixture, and point the harness at it for the duration of the block.

    Nothing here reads `evals/fixtures/`, so a fixture a later bead adds cannot
    change what these cases measure, and none of them has to exist yet.
    """
    root = Path(tempfile.mkdtemp(prefix="tadw-test-fixtures-"))
    for directory, files in ((harness.BASE_DIR, base), (harness.PLANT_DIR, plant or {})):
        for relative, body in files.items():
            path = root / name / directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

    original = harness.FIXTURES_DIR
    harness.FIXTURES_DIR = root
    try:
        yield
    finally:
        harness.FIXTURES_DIR = original
        shutil.rmtree(root, ignore_errors=True)


def build_fixture(name: str, base: dict[str, str], plant: dict[str, str] | None = None) -> Path:
    """The built repository for a fixture, for a case that asserts on its contents.

    The repository outlives the `with` block, since the caller reads it, so its
    directory is registered for cleanup at exit rather than removed here.
    """
    workdir = Path(tempfile.mkdtemp(prefix="tadw-test-work-"))
    workspaces.append(workdir)
    with fixture_named(name, base, plant):
        return harness.prepare_fixture(name, workdir)


def git_out(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def worktree_status(repo: Path) -> dict[str, str]:
    """`git status --porcelain` as {path: two-character code}.

    Read unstripped, because the first column is a space for a file modified in
    the worktree but not staged, and that space is the difference between the
    plant landing as the change and the plant landing in the index.
    """
    completed = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    return {line[3:]: line[:2] for line in completed.stdout.splitlines() if line}


print("\n  [criterion 1: the six shipped cases behave exactly as before]")


def case_shipped_cases_are_untouched() -> None:
    """None of the six carries either new key, so neither can change their behavior."""
    found = set()
    for path in sorted(harness.CASES_DIR.glob("*/case.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        found.add(path.parent.name)
        if path.parent.name in SHIPPED_CASES:
            assert "fixture" not in case, f"{path.parent.name} gained a fixture key"
            assert "single_arm" not in case, f"{path.parent.name} gained a single_arm key"
    missing = SHIPPED_CASES - found
    assert not missing, f"a shipped case disappeared: {sorted(missing)}"


def case_case_without_fixture_runs_in_repo_root() -> None:
    with harness.case_cwd({"prompt": "x"}, keep=False) as cwd:
        assert cwd == harness.REPO_ROOT, f"expected the repository root, got {cwd}"


def case_case_without_single_arm_runs_both_arms() -> None:
    arms = harness.arms_for({"prompt": "x"}, no_baseline=False)
    assert arms == [("with-plugin", True), ("baseline", False)], arms


def case_no_baseline_flag_still_drops_the_baseline() -> None:
    arms = harness.arms_for({"prompt": "x"}, no_baseline=True)
    assert arms == [("with-plugin", True)], arms


print("\n  [criterion 2: a fixture case runs in a temp repository of its own]")


def case_fixture_is_a_temp_repo_not_the_root() -> None:
    """Asserted through case_cwd, the path a run actually takes.

    Calling prepare_fixture alone would leave the wiring from the `fixture` key to
    the working directory untested, which is the half criterion 2 is about.
    """
    with fixture_named("demo", {"README.md": "# demo\n"}):
        with harness.case_cwd({"fixture": "demo"}, keep=False) as repo:
            assert repo != harness.REPO_ROOT, "the fixture must not be this repository"
            assert harness.REPO_ROOT not in repo.parents, f"it sits inside the repo: {repo}"
            assert (repo / ".git").exists(), f"no git directory in {repo}"
            assert (repo / "README.md").read_text(encoding="utf-8") == "# demo\n"
            top = git_out(repo, "rev-parse", "--show-toplevel")
            assert Path(top).resolve() == repo.resolve(), f"git disagrees about the root: {top}"


def case_fixture_base_is_committed() -> None:
    repo = build_fixture("demo", {"src/app.py": "def hello():\n    return 1\n"})
    tracked = git_out(repo, "ls-files").splitlines()
    assert tracked == ["src/app.py"], f"the base must be the initial commit: {tracked}"
    count = git_out(repo, "rev-list", "--count", "HEAD")
    assert count == "1", f"exactly one commit, got {count}"


def case_fixture_plant_is_left_uncommitted() -> None:
    """The planted defect has to read as the working-tree change, not as history."""
    repo = build_fixture(
        "demo",
        {"src/app.py": "def hello():\n    return 1\n"},
        {"src/app.py": "def hello():\n    return 1\n\n\ndef added():\n    return 2\n",
         "src/new.py": "def fresh():\n    return 3\n"},
    )
    dirty = worktree_status(repo)
    assert dirty.get("src/app.py") == " M", f"the overwritten file must be modified, unstaged: {dirty}"
    assert dirty.get("src/new.py") == "??", f"the added file must be untracked: {dirty}"
    committed = git_out(repo, "show", "HEAD:src/app.py")
    assert "def added" not in committed, "the plant leaked into the initial commit"


def case_fixture_origin_resolves_a_base() -> None:
    """Without origin/main, changed_set.py exits 3 and every gate widens to --all."""
    repo = build_fixture(
        "demo",
        {"src/app.py": "x = 1\n"},
        {"src/new.py": "y = 2\n"},
    )
    assert git_out(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    # Asserted on the return code rather than through git_out, whose check=True
    # would raise CalledProcessError and describe a crash instead of this rule.
    resolved = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "origin/main"],
        capture_output=True, text=True,
    )
    assert resolved.returncode == 0, "origin/main must resolve, or every gate widens to --all"

    script = harness.REPO_ROOT / "skills/quality-gates/scripts/changed_set.py"
    result = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(repo)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"the base must resolve: {result.returncode}, {result.stderr!r}"
    listed = result.stdout.split()
    assert listed == ["src/new.py"], f"only the plant is the change: {listed}"


def case_two_runs_get_independent_trees() -> None:
    """One run must not be able to hand its verdict artifact to the next."""
    with fixture_named("demo", {"README.md": "# demo\n"}):
        seen = []
        for _ in range(2):
            with harness.case_cwd({"fixture": "demo"}, keep=False) as cwd:
                seen.append(cwd)
                (cwd / ".git" / "quality-gates-report.json").write_text("{}", encoding="utf-8")
                assert cwd.exists()
        assert seen[0] != seen[1], f"both runs shared one tree: {seen}"
        for cwd in seen:
            assert not cwd.exists(), f"the fixture outlived its run: {cwd}"


print("\n  [criterion 3: single_arm runs the with-plugin arm alone]")


def case_single_arm_runs_one_arm() -> None:
    arms = harness.arms_for({"prompt": "x", "single_arm": True}, no_baseline=False)
    assert arms == [("with-plugin", True)], arms


def case_single_arm_false_keeps_both_arms() -> None:
    """The key is opt-in, so the falsy value must behave like an absent key."""
    arms = harness.arms_for({"prompt": "x", "single_arm": False}, no_baseline=False)
    assert arms == [("with-plugin", True), ("baseline", False)], arms


print("\n  [criterion 4, plus the two ways a paid run could be wasted]")


def case_readme_documents_both_keys() -> None:
    """Criterion 4 asks for the reason, not a spelling, so the reason is what is pinned."""
    text = README.read_text(encoding="utf-8")
    for key in ("`fixture`", "`single_arm`"):
        assert key in text, f"README.md must document {key}"
    assert "baseline" in text.lower(), "README.md must name the arm a fixture case skips"
    assert re.search(r"does not exist without the plugin", text, re.I), \
        "README.md must give the reason fixture cases skip the baseline arm"
    assert "base/" in text and "plant/" in text, \
        "README.md must document the base/ and plant/ layout"


def case_missing_fixture_fails_fast() -> None:
    """A typo costs an error, never a paid call against the wrong directory."""
    try:
        harness.fixture_source("no-such-fixture", case_name="demo")
    except SystemExit as exc:
        message = str(exc)
        assert "no-such-fixture" in message, f"name the fixture: {message!r}"
        assert "demo" in message, f"name the case that asked for it: {message!r}"
        return
    raise AssertionError("a missing fixture must raise SystemExit")


def case_model_call_happens_in_the_fixture() -> None:
    """The one case that proves the whole bead, driven through run_case.

    Every other case here checks the directory the harness BUILDS. This checks the
    directory the call is MADE FROM, by putting a fake `claude` on PATH that
    reports its own working directory and its argv. Without it, changing `ask` to
    `cwd=str(REPO_ROOT)` passes every other check in this file, and every fixture
    case would silently grade this repository instead of its fixture.
    """
    stub_dir = Path(tempfile.mkdtemp(prefix="tadw-test-bin-"))
    workspaces.append(stub_dir)
    stub = stub_dir / "claude"
    # Two lines: where it ran, then how it was called.
    stub.write_text('#!/bin/sh\npwd\necho "ARGV: $*"\n', encoding="utf-8")
    stub.chmod(0o755)

    original_path = os.environ["PATH"]
    os.environ["PATH"] = f"{stub_dir}{os.pathsep}{original_path}"
    try:
        with fixture_named("demo", {"README.md": "# demo\n"}):
            args = argparse.Namespace(
                model="fake", runs=1, no_baseline=True, keep_fixtures=False, timeout=30
            )
            with contextlib.redirect_stdout(io.StringIO()):
                results = harness.run_case("demo", {"prompt": "x", "fixture": "demo"}, args)
    finally:
        os.environ["PATH"] = original_path

    assert len(results) == 1, f"one arm, one run: {results}"
    output = results[0].output
    assert output, f"the stub produced no output: {results[0].checks}"
    where, argv = output.splitlines()[0], output.splitlines()[1]

    assert Path(where).resolve() != harness.REPO_ROOT.resolve(), (
        f"the call was made from the repository root, so the fixture was ignored: {where}"
    )
    assert "tadw-eval-demo-" in where, f"the call must run inside the fixture: {where}"
    # The other half of ask()'s contract: the plugin still comes from this tree.
    assert f"--plugin-dir {harness.REPO_ROOT}" in argv, f"--plugin-dir must stay the repo: {argv}"


def case_keep_fixtures_leaves_the_tree() -> None:
    kept: list[Path] = []
    with fixture_named("demo", {"README.md": "# demo\n"}):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            with harness.case_cwd({"fixture": "demo"}, keep=True) as cwd:
                kept.append(cwd)
        assert cwd.exists(), f"--keep-fixtures must leave the tree: {cwd}"
        assert str(cwd.parent) in printed.getvalue(), (
            f"and name where it left it: {printed.getvalue()!r}"
        )
    for path in kept:
        workspaces.append(path.parent)


def case_header_counts_single_arm_and_fixture_cases() -> None:
    cases = [
        ("plain", {"prompt": "x"}),
        ("gated", {"prompt": "y", "fixture": "f", "single_arm": True}),
    ]
    header = harness.describe_run(cases, "sonnet", 3, no_baseline=False)
    assert "2 case(s)" in header and "model=sonnet" in header and "runs=3" in header, header
    assert "1 of them single-arm" in header, f"a skipped arm must be stated: {header}"
    assert "1 run in a fixture repository" in header, header

    plain = harness.describe_run([("plain", {"prompt": "x"})], "sonnet", 1, no_baseline=False)
    assert "single-arm" not in plain and "fixture" not in plain, (
        f"a run with neither key must claim neither: {plain}"
    )


print("\n  [the account under measurement is the caller\'s, not the shell\'s]")


def spawned_env(exported: dict) -> dict:
    """The environment a real `ask()` hands to `claude`, with `exported` set first.

    A stub `claude` on PATH prints its own environment, so this drives the real
    spawn rather than reading REDIRECTING_VARS back. A change to `ask()` that
    dropped `env=` would pass any assertion made against the constant, and every
    run would silently measure whichever account the shell was switched to.
    """
    stub_dir = Path(tempfile.mkdtemp(prefix="tadw-test-env-"))
    workspaces.append(stub_dir)
    stub = stub_dir / "claude"
    stub.write_text("#!/bin/sh\nenv\n", encoding="utf-8")
    stub.chmod(0o755)

    original = {name: os.environ.get(name) for name in exported}
    original_path = os.environ["PATH"]
    os.environ["PATH"] = f"{stub_dir}{os.pathsep}{original_path}"
    os.environ.update(exported)
    try:
        output = harness.ask(
            "x", model="fake", with_plugin=False, timeout=30, cwd=harness.REPO_ROOT
        )
    finally:
        os.environ["PATH"] = original_path
        for name, value in original.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    seen = {}
    for line in output.splitlines():
        name, _, value = line.partition("=")
        if _:
            seen[name] = value
    return seen


def case_an_api_key_never_reaches_the_model_call() -> None:
    """Criterion 1. The variable that made every case fail at invocation.

    A set ANTHROPIC_API_KEY takes precedence over the stored claude.ai login, and
    `claude -p` then exits 1 with a connectors warning. Measured 2026-08-22 before
    this was fixed: 12 of 12 runs died there, reported as 0/6 in both arms, which
    reads like a total style regression.
    """
    seen = spawned_env({"ANTHROPIC_API_KEY": "sk-ant-not-a-real-key"})
    assert "ANTHROPIC_API_KEY" not in seen, "the key must not reach the model call"


def case_bedrock_routing_never_reaches_the_model_call() -> None:
    """Criterion 2, and the quieter half of the rule.

    Bedrock routing does not fail the run. It completes and measures a different
    account, so nothing in the output says the number is about somewhere else.
    """
    seen = spawned_env(
        {"CLAUDE_CODE_USE_BEDROCK": "1", "AWS_BEARER_TOKEN_BEDROCK": "not-a-real-token"}
    )
    assert "CLAUDE_CODE_USE_BEDROCK" not in seen, "Bedrock routing must not reach the call"
    assert "AWS_BEARER_TOKEN_BEDROCK" not in seen, "nor its token"


def case_a_model_override_never_reaches_the_model_call() -> None:
    """The run header reports what `--model` names, so nothing else may decide it."""
    seen = spawned_env({"ANTHROPIC_MODEL": "some-other-model"})
    assert "ANTHROPIC_MODEL" not in seen, (
        "an env model override would answer as a model the header does not name"
    )


def case_the_rest_of_the_environment_is_passed_through() -> None:
    """Criterion 3. Stripping five names, not building an environment from scratch.

    The child is a real `claude` invocation: without PATH it cannot find its own
    dependencies, and without HOME it cannot read the login this harness exists to
    measure. An empty env passes all three cases above and runs nothing.
    """
    seen = spawned_env({"ANTHROPIC_API_KEY": "sk-ant-not-a-real-key"})
    assert seen.get("PATH"), f"PATH must survive: {sorted(seen)[:12]}"
    for name in ("HOME", "USER"):
        if name in os.environ:
            assert name in seen, f"{name} must survive"


def case_every_redirecting_var_is_covered_by_a_case() -> None:
    """The list and the cases move together, or a sixth entry ships untested."""
    tested = {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "AWS_BEARER_TOKEN_BEDROCK",
        "CLAUDE_CODE_USE_BEDROCK",
        "ANTHROPIC_MODEL",
    }
    declared = set(harness.REDIRECTING_VARS)
    assert declared == tested, (
        f"REDIRECTING_VARS and the cases above disagree.\n"
        f"         stripped but untested: {sorted(declared - tested)}\n"
        f"         tested but not stripped: {sorted(tested - declared)}"
    )


def case_readme_states_the_behavior_not_a_workaround() -> None:
    """Criterion 5. The README told readers to strip the variable by hand."""
    text = README.read_text(encoding="utf-8")
    assert "env -u ANTHROPIC_API_KEY" not in text, (
        "the harness strips it now, so the manual workaround must not still be prescribed"
    )
    assert "ANTHROPIC_API_KEY" in text, (
        "the behavior is still worth stating; a reader with a key set should know it is ignored"
    )


for name, fn in [
    ("an API key never reaches the model call [criterion 1]", case_an_api_key_never_reaches_the_model_call),
    ("Bedrock routing never reaches the model call [criterion 2]", case_bedrock_routing_never_reaches_the_model_call),
    ("an env model override never reaches the model call", case_a_model_override_never_reaches_the_model_call),
    ("the rest of the environment is passed through [criterion 3]", case_the_rest_of_the_environment_is_passed_through),
    ("every stripped variable has a case [criterion 4]", case_every_redirecting_var_is_covered_by_a_case),
    ("README states the behavior, not the workaround [criterion 5]", case_readme_states_the_behavior_not_a_workaround),
]:
    check(name, fn)


print("\n  [the CLI, through its real entry point]")


def case_cli_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, str(EVALS / "run.py"), "--help"],
        capture_output=True, text=True, cwd=str(harness.REPO_ROOT),
    )
    assert result.returncode == 0, f"--help must exit 0: {result.returncode}, {result.stderr[:200]}"
    for flag in ("--keep-fixtures", "--no-baseline", "--runs"):
        # \b, not `in`: a renamed --keep-fixturez CONTAINS --keep-fixtures, and a
        # substring match called that a pass while the flag no longer existed.
        assert re.search(rf"{re.escape(flag)}\b", result.stdout), f"--help must list {flag}"


def case_cli_unknown_case_exits_one() -> None:
    """The load-time failure path, through argv, with no model call behind it."""
    result = subprocess.run(
        [sys.executable, str(EVALS / "run.py"), "--case", "no-such-case"],
        capture_output=True, text=True, cwd=str(harness.REPO_ROOT),
    )
    assert result.returncode == 1, f"an unknown case must exit 1: {result.returncode}"
    assert "no cases found" in result.stderr, f"and say so: {result.stderr[:200]!r}"

    # The same path with --keep-fixtures, which proves argparse ACCEPTS the flag
    # rather than merely printing something like it. A renamed flag exits 2 here.
    with_flag = subprocess.run(
        [sys.executable, str(EVALS / "run.py"), "--keep-fixtures", "--case", "no-such-case"],
        capture_output=True, text=True, cwd=str(harness.REPO_ROOT),
    )
    assert with_flag.returncode == 1, (
        f"--keep-fixtures must be a real flag, not an argparse error: "
        f"exit {with_flag.returncode}, {with_flag.stderr[:160]!r}"
    )


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__", "argparse", "contextlib", "collections", "dataclasses", "json",
        "pathlib", "re", "shutil", "subprocess", "sys", "tempfile", "atexit",
        "argparse", "io", "os",
    }
    # Not stdlib: the harness under test, imported by path above.
    stdlib = stdlib | {"run"}
    for path in (EVALS / "run.py", Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M))
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("the six shipped cases carry neither new key [criterion 1]", case_shipped_cases_are_untouched),
    ("a case with no fixture runs in the repository root [criterion 1]", case_case_without_fixture_runs_in_repo_root),
    ("a case with no single_arm runs both arms [criterion 1]", case_case_without_single_arm_runs_both_arms),
    ("--no-baseline still drops the baseline arm [criterion 1]", case_no_baseline_flag_still_drops_the_baseline),
    ("a fixture is a temp git repository, not this one [criterion 2]", case_fixture_is_a_temp_repo_not_the_root),
    ("base/ becomes the one initial commit [criterion 2]", case_fixture_base_is_committed),
    ("plant/ is left uncommitted, as the change [criterion 2]", case_fixture_plant_is_left_uncommitted),
    ("origin/main resolves, so a scoped run sees the plant [criterion 2]", case_fixture_origin_resolves_a_base),
    ("each run gets its own tree, and it is cleaned up", case_two_runs_get_independent_trees),
    ("single_arm runs the with-plugin arm alone [criterion 3]", case_single_arm_runs_one_arm),
    ("single_arm false behaves like an absent key [criterion 3]", case_single_arm_false_keeps_both_arms),
    ("README.md documents both keys and the layout [criterion 4]", case_readme_documents_both_keys),
    ("the model call is made inside the fixture [criterion 2]", case_model_call_happens_in_the_fixture),
    ("--keep-fixtures leaves the tree and names it", case_keep_fixtures_leaves_the_tree),
    ("the header states a skipped arm and a fixture run", case_header_counts_single_arm_and_fixture_cases),
    ("run.py --help exits 0 through real argv", case_cli_help_exits_zero),
    ("run.py --case no-such-case exits 1 through real argv", case_cli_unknown_case_exits_one),
    ("a misnamed fixture fails before any model call", case_missing_fixture_fails_fast),
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
