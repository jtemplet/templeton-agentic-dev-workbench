#!/usr/bin/env python3
"""Run the response-style evals against this working tree.

Each case sends a fixed prompt to `claude -p` twice: once with this repository
loaded via --plugin-dir (so the SessionStart hook injects the style from the
working tree, not from the released copy in ~/.claude/plugins/cache), and once
with no plugin at all. The gap between the two arms is the measurement.

Graders are deterministic on purpose. Every rule these cases test is a pattern
you can match, so a script decides pass or fail: free, instant, never flaky.

A case may also name a `fixture`, which runs it against a throwaway repository
built under /tmp instead of this one. That is what lets a case plant a defect and
assert what a skill reports about it; see prepare_fixture for the layout.

Usage:
    python3 evals/run.py
    python3 evals/run.py --case decision-matrix-trigger --runs 3 --model opus
    python3 evals/run.py --no-baseline
    python3 evals/run.py --case gates-all-skip --keep-fixtures
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = Path(__file__).resolve().parent / "cases"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# The two halves of a fixture directory. Only `base` is required.
BASE_DIR = "base"
PLANT_DIR = "plant"

# A fixed identity, so a case builds the same commit on any machine. `gpgsign` is
# off because a machine that signs by default would block on a passphrase prompt
# inside a subprocess with no terminal.
GIT_IDENTITY = (
    "-c", "user.name=tadw evals",
    "-c", "user.email=evals@example.invalid",
    "-c", "commit.gpgsign=false",
)

FENCED_CODE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`]*`")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)
TABLE_DIVIDER = re.compile(r"^\s*\|[\s:|-]*-[\s:|-]*\|\s*$", re.M)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class RunResult:
    arm: str
    output: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


def load_cases(only: str | None) -> list[tuple[str, dict]]:
    cases = []
    for path in sorted(CASES_DIR.glob("*/case.json")):
        name = path.parent.name
        if only and name != only:
            continue
        with path.open() as handle:
            case = json.load(handle)
        # Checked here rather than at run time, because every run costs a real
        # model call and a typo in a fixture name should not be paid for.
        if case.get("fixture"):
            fixture_source(case["fixture"], case_name=name)
        cases.append((name, case))
    if not cases:
        raise SystemExit(f"no cases found (looked in {CASES_DIR}, filter={only!r})")
    return cases


def arms_for(case: dict, no_baseline: bool) -> list[tuple[str, bool]]:
    """The arms to run for one case, in order.

    `single_arm` drops the baseline for a case whose prompt invokes a slash
    command. The command does not exist without the plugin, so that arm would
    measure nothing and would double the cost of the case. Recorded as D7 in
    docs/plans/quality-gates-hardening.md.
    """
    arms = [("with-plugin", True)]
    if not no_baseline and not case.get("single_arm"):
        arms.append(("baseline", False))
    return arms


def fixture_source(name: str, case_name: str = "") -> Path:
    """The fixture directory a case names, verified to be usable."""
    path = FIXTURES_DIR / name
    if not (path / BASE_DIR).is_dir():
        owner = f"case {case_name!r} " if case_name else ""
        raise SystemExit(f"{owner}names fixture {name!r}, but {path / BASE_DIR} does not exist")
    return path


def git(repo: Path, *args: str) -> None:
    """One git command inside `repo`. Raises rather than returning a status.

    A fixture that half-built would send a paid model call at a repository whose
    state nobody knows, and the case would fail for a reason unrelated to the
    rule it tests.
    """
    completed = subprocess.run(
        ["git", *GIT_IDENTITY, "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {repo}: {completed.stderr.strip()[:200]}"
        )


def prepare_fixture(name: str, workdir: Path) -> Path:
    """Build a throwaway repository from a fixture, and return its root.

    A fixture directory holds up to two parts, and the split is what makes a
    planted defect visible to a skill that scopes itself to the change:

      base/   copied in, committed as the initial commit, and pushed to a bare
              origin so `origin/main` resolves the way it does in a real clone
      plant/  copied over the tree afterward and left UNCOMMITTED, so it reads as
              the working-tree change

    Committing the defect instead would put it in the base that a changed-scope
    run compares against, and the gate under test would correctly report nothing.
    The origin sits beside the checkout rather than inside it, so the gates never
    walk it.
    """
    source = fixture_source(name)
    repo = workdir / "repo"
    origin = workdir / "origin.git"

    shutil.copytree(source / BASE_DIR, repo)
    git(workdir, "init", "--quiet", "--bare", "-b", "main", origin.name)
    git(repo, "init", "--quiet", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "fixture base")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "--quiet", "-u", "origin", "main")

    plant = source / PLANT_DIR
    if plant.is_dir():
        shutil.copytree(plant, repo, dirs_exist_ok=True)
    return repo


@contextlib.contextmanager
def case_cwd(case: dict, keep: bool) -> Iterator[Path]:
    """The working directory for ONE run, torn down after it.

    A fresh fixture per run, not per case, because a skill under test can write
    into the tree it graded. The quality-gates skill records its verdict at
    `<git-dir>/quality-gates-report.json`, and a second run against the same
    tree could read the first run's answer instead of producing its own.
    """
    fixture = case.get("fixture")
    if not fixture:
        yield REPO_ROOT
        return

    workdir = Path(tempfile.mkdtemp(prefix=f"tadw-eval-{fixture}-"))
    try:
        yield prepare_fixture(fixture, workdir)
    finally:
        if keep:
            print(f"        kept fixture at {workdir}", flush=True)
        else:
            shutil.rmtree(workdir, ignore_errors=True)


def ask(prompt: str, model: str, with_plugin: bool, timeout: int, cwd: Path) -> str:
    """One model call. Returns the answer text, or raises on failure.

    `--plugin-dir` stays REPO_ROOT even when `cwd` is a fixture: the plugin under
    test is always this working tree, and only the repository the model looks at
    changes.
    """
    command = ["claude", "-p", prompt, "--model", model]
    if with_plugin:
        command += ["--plugin-dir", str(REPO_ROOT)]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd),
    )
    if completed.returncode != 0:
        raise RuntimeError(f"claude exited {completed.returncode}: {completed.stderr[:400]}")
    return completed.stdout.strip()


def prose_only(text: str) -> str:
    """Strip code and table rows so sentence-length checks see prose alone."""
    text = FENCED_CODE.sub(" ", text)
    text = INLINE_CODE.sub(" ", text)
    text = TABLE_ROW.sub(" ", text)
    return text


def has_markdown_table(text: str) -> bool:
    # A real table needs a divider row; a lone pipe character is not a table.
    return bool(TABLE_DIVIDER.search(text))


def grade(output: str, checks: dict) -> list[CheckResult]:
    results: list[CheckResult] = []

    for rule in checks.get("forbid_regex", []):
        hit = re.search(rule["pattern"], output, re.I)
        results.append(CheckResult(
            name=f"forbid /{rule['pattern']}/",
            passed=hit is None,
            detail="absent" if hit is None else f"found {hit.group(0)!r} ({rule['why']})",
        ))

    # A label is allowed only when the facts it stands for are present. The word
    # alone is the failure, not the word. Fails when the pattern appears and any
    # "unless" pattern is missing; passes when the pattern is absent entirely.
    for rule in checks.get("forbid_label_alone", []):
        hit = re.search(rule["pattern"], output, re.I)
        missing = [p for p in rule["unless_all"] if not re.search(p, output, re.I)]
        results.append(CheckResult(
            name=f"label /{rule['pattern']}/ only beside its facts",
            passed=hit is None or not missing,
            detail=(
                "label absent" if hit is None
                else "label present, and every supporting fact is there" if not missing
                else f"found {hit.group(0)!r} without {missing} ({rule['why']})"
            ),
        ))

    for rule in checks.get("require_regex", []):
        hit = re.search(rule["pattern"], output, re.I)
        results.append(CheckResult(
            name=f"require /{rule['pattern']}/",
            passed=hit is not None,
            detail=f"found {hit.group(0)!r}" if hit else f"missing ({rule['why']})",
        ))

    if checks.get("require_markdown_table"):
        present = has_markdown_table(output)
        results.append(CheckResult(
            name="require markdown table",
            passed=present,
            detail="table present" if present else "no table; the matrix rule did not fire",
        ))

    if checks.get("forbid_markdown_table"):
        present = has_markdown_table(output)
        results.append(CheckResult(
            name="forbid markdown table",
            passed=not present,
            detail="no table, correct" if not present else "table drawn for an obvious call",
        ))

    limit = checks.get("max_sentence_words")
    if limit:
        worst, worst_text = 0, ""
        for sentence in SENTENCE_SPLIT.split(prose_only(output)):
            count = len(sentence.split())
            if count > worst:
                worst, worst_text = count, sentence.strip()
        results.append(CheckResult(
            name=f"max sentence <= {limit} words",
            passed=worst <= limit,
            detail=f"longest was {worst}" + ("" if worst <= limit else f": {worst_text[:90]!r}"),
        ))

    return results


def describe_run(cases: list[tuple[str, dict]], model: str, runs: int, no_baseline: bool) -> str:
    """The header line, spelled out rather than assumed from the flags alone.

    A single-arm case runs one arm whatever `--no-baseline` says, so a header
    claiming both arms for a run that skipped one is the report lying about its
    own scope. Its own function so a test can read it without a model call.
    """
    arms = "with-plugin only" if no_baseline else "with-plugin + baseline"
    single = sum(1 for _, case in cases if case.get("single_arm"))
    if single and not no_baseline:
        arms += f", {single} of them single-arm"
    header = f"{len(cases)} case(s), model={model}, runs={runs}, arms={arms}"
    fixtures = sum(1 for _, case in cases if case.get("fixture"))
    if fixtures:
        header += f"; {fixtures} run in a fixture repository"
    return header


def run_case(name: str, case: dict, args) -> list[RunResult]:
    results: list[RunResult] = []
    for arm, with_plugin in arms_for(case, args.no_baseline):
        for attempt in range(args.runs):
            label = f"{name} [{arm}]" + (f" run {attempt + 1}" if args.runs > 1 else "")
            print(f"  running {label} ...", flush=True)
            try:
                with case_cwd(case, args.keep_fixtures) as cwd:
                    output = ask(case["prompt"], args.model, with_plugin, args.timeout, cwd)
            except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
                results.append(RunResult(arm, "", [CheckResult("invocation", False, str(error)[:200])]))
                continue
            results.append(RunResult(arm, output, grade(output, case.get("checks", {}))))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", help="run only this case directory name")
    parser.add_argument("--model", default="sonnet", help="model for the answer (default: sonnet)")
    parser.add_argument("--runs", type=int, default=1, help="runs per arm (default: 1; use 3 before trusting a result)")
    parser.add_argument("--no-baseline", action="store_true", help="skip the no-plugin arm")
    parser.add_argument("--keep-fixtures", action="store_true",
                        help="leave each fixture repository on disk, and print where")
    parser.add_argument("--timeout", type=int, default=300, help="per-call timeout in seconds")
    parser.add_argument("--show-output", action="store_true", help="print each full answer")
    parser.add_argument("--json", metavar="PATH", help="write full results to this JSON file")
    args = parser.parse_args()

    cases = load_cases(args.case)
    print(describe_run(cases, args.model, args.runs, args.no_baseline) + "\n")

    report, tally = {}, {}
    for name, case in cases:
        print(f"{name}: {case['why'][:100]}")
        results = run_case(name, case, args)
        report[name] = {"why": case["why"], "prompt": case["prompt"], "runs": []}

        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"    {status}  {result.arm}")
            for check in result.checks:
                mark = "ok  " if check.passed else "FAIL"
                print(f"        {mark} {check.name}: {check.detail}")
            if args.show_output and result.output:
                body = "\n".join("        | " + line for line in result.output.splitlines())
                print(body)
            report[name]["runs"].append({
                "arm": result.arm,
                "passed": result.passed,
                "output": result.output,
                "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in result.checks],
            })
            bucket = tally.setdefault(result.arm, [0, 0])
            bucket[1] += 1
            if result.passed:
                bucket[0] += 1
        print()

    print("Summary")
    for arm, (passed, total) in tally.items():
        print(f"  {arm:<12} {passed}/{total} runs passed")
    if "with-plugin" in tally and "baseline" in tally:
        with_rate = tally["with-plugin"][0] / tally["with-plugin"][1]
        base_rate = tally["baseline"][0] / tally["baseline"][1]
        print(f"  delta        {with_rate - base_rate:+.0%} (with-plugin minus baseline)")
        if with_rate == base_rate:
            print("  note: no gap. The model already behaved this way; these rules changed nothing here.")

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
        print(f"\nwrote {args.json}")

    failed = tally.get("with-plugin", [0, 0])
    return 0 if failed[0] == failed[1] else 1


if __name__ == "__main__":
    sys.exit(main())
