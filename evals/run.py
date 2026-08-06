#!/usr/bin/env python3
"""Run the response-style evals against this working tree.

Each case sends a fixed prompt to `claude -p` twice: once with this repository
loaded via --plugin-dir (so the SessionStart hook injects the style from the
working tree, not from the released copy in ~/.claude/plugins/cache), and once
with no plugin at all. The gap between the two arms is the measurement.

Graders are deterministic on purpose. Every rule these cases test is a pattern
you can match, so a script decides pass or fail: free, instant, never flaky.

Usage:
    python3 evals/run.py
    python3 evals/run.py --case decision-matrix-trigger --runs 3 --model opus
    python3 evals/run.py --no-baseline
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = Path(__file__).resolve().parent / "cases"

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
            cases.append((name, json.load(handle)))
    if not cases:
        raise SystemExit(f"no cases found (looked in {CASES_DIR}, filter={only!r})")
    return cases


def ask(prompt: str, model: str, with_plugin: bool, timeout: int) -> str:
    """One model call. Returns the answer text, or raises on failure."""
    command = ["claude", "-p", prompt, "--model", model]
    if with_plugin:
        command += ["--plugin-dir", str(REPO_ROOT)]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
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


def run_case(name: str, case: dict, args) -> list[RunResult]:
    arms = [("with-plugin", True)]
    if not args.no_baseline:
        arms.append(("baseline", False))

    results: list[RunResult] = []
    for arm, with_plugin in arms:
        for attempt in range(args.runs):
            label = f"{name} [{arm}]" + (f" run {attempt + 1}" if args.runs > 1 else "")
            print(f"  running {label} ...", flush=True)
            try:
                output = ask(case["prompt"], args.model, with_plugin, args.timeout)
            except (RuntimeError, subprocess.TimeoutExpired) as error:
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
    parser.add_argument("--timeout", type=int, default=300, help="per-call timeout in seconds")
    parser.add_argument("--show-output", action="store_true", help="print each full answer")
    parser.add_argument("--json", metavar="PATH", help="write full results to this JSON file")
    args = parser.parse_args()

    cases = load_cases(args.case)
    print(f"{len(cases)} case(s), model={args.model}, runs={args.runs}, "
          f"arms={'with-plugin only' if args.no_baseline else 'with-plugin + baseline'}\n")

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
