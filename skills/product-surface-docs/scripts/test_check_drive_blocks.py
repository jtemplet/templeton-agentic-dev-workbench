#!/usr/bin/env python3
"""Regression suite for check_drive_blocks.py.

Stdlib only, no install, mirroring test_check_doc_paths.py. Run with:
    python3 skills/product-surface-docs/scripts/test_check_drive_blocks.py

Two groups carry most of the value. The leaf-detection group pins which documents the
checker asks for a block at all, because a checker that demanded one from a surface
document would fail every real tree on its first run. The block-shape group pins what
counts as a usable block, including the not-drivable form, because a feature with no
user interface must be able to pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_drive_blocks.py"

passed = 0
failed = 0

FULL_BLOCK = """<!-- drive:start -->
## How to drive this

- **Route:** /deals
- **Precondition:** signed in as a lender whose workspace holds at least one deal
- **Selector:** `[data-testid="deal-row"]`
- **Action:** click the first row, then read the page header
- **Success signal:** the header shows the deal name from that row
<!-- drive:end -->
"""

NOT_DRIVABLE_BLOCK = """<!-- drive:start -->
## How to drive this

**Not drivable:** this feature has no user interface. It runs as the nightly export job.
<!-- drive:end -->
"""

NO_BLOCK = """> A leaf document with prose and no drive block.

- **Customer:** a lender
"""


def run(tree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(tree), *args],
        capture_output=True,
        text=True,
    )


def build(docs: dict[str, str]) -> Path:
    """A throwaway docs/products tree. Keys are paths relative to it."""
    root = Path(tempfile.mkdtemp()) / "products"
    root.mkdir(parents=True, exist_ok=True)
    for relative, body in docs.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def graded(result: subprocess.CompletedProcess[str]) -> dict[str, str]:
    """The JSON result, as a mapping of document base name to outcome."""
    rows = json.loads(result.stdout)
    return {Path(row["doc"]).name: row["outcome"] for row in rows}


def assert_exit(tree: Path, expected: int) -> None:
    result = run(tree)
    assert result.returncode == expected, (
        f"expected exit {expected}, got {result.returncode}\n{result.stdout}{result.stderr}"
    )


def run_default(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run with no directory argument, so the checker uses its default path."""
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def assert_absent_default_passes(as_json: bool) -> None:
    """A repository with no docs/products is not a failing repository."""
    empty_repo = Path(tempfile.mkdtemp())
    result = run_default(empty_repo, "--json") if as_json else run_default(empty_repo)
    assert result.returncode == 0, (
        f"expected exit 0 on a repository with no tree, got {result.returncode}\n{result.stderr}"
    )
    if as_json:
        assert json.loads(result.stdout) == [], f"expected an empty list, got {result.stdout!r}"
    else:
        assert "nothing to check" in result.stdout, f"unexpected output: {result.stdout!r}"


def assert_absent(docs: dict[str, str], name: str) -> None:
    outcomes = graded(run(build(docs), "--json"))
    assert name not in outcomes, f"{name} was graded as a leaf: {outcomes}"


def assert_outcome(docs: dict[str, str], name: str, expected: str) -> None:
    outcomes = graded(run(build(docs), "--json"))
    assert outcomes.get(name) == expected, (
        f"expected {name} to grade {expected}, got {outcomes}"
    )


def assert_missing_line(body: str, expected: str) -> None:
    rows = json.loads(run(build({"web/web.md": body}), "--json").stdout)
    missing = rows[0]["missing_lines"]
    assert missing == [expected], f"expected [{expected!r}], got {missing}"


def assert_in_stdout(docs: dict[str, str], needle: str) -> None:
    out = run(build(docs)).stdout
    assert needle in out, f"expected {needle!r} in output:\n{out}"


def assert_json_exit(docs: dict[str, str], expected: int) -> None:
    result = run(build(docs), "--json")
    assert result.returncode == expected, (
        f"expected exit {expected}, got {result.returncode}"
    )
    json.loads(result.stdout)


def assert_shipped_example_passes() -> None:
    skill = CHECKER.parent.parent / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.find("<!-- drive:start -->")
    end = text.find("<!-- drive:end -->", start) + len("<!-- drive:end -->")
    assert start != -1 and end > start, "SKILL.md carries no drive block example"
    outcomes = graded(run(build({"web/web.md": text[start:end]}), "--json"))
    assert outcomes.get("web.md") == "ok", (
        f"the example in SKILL.md does not pass its own checker: {outcomes}"
    )


print("\ncheck_drive_blocks.py")

print("\n  exit status")

check(
    "a tree whose every leaf carries a block exits 0",
    lambda: assert_exit(build({"web/web.md": NO_BLOCK, "web/deals.md": FULL_BLOCK}), 0),
)
check(
    "a tree with one leaf missing its block exits 1",
    lambda: assert_exit(build({"web/web.md": NO_BLOCK, "web/deals.md": NO_BLOCK}), 1),
)
check(
    "a directory named on the command line that does not exist exits 2",
    lambda: assert_exit(Path("/nonexistent/products"), 2),
)
check(
    "an empty tree exits 0, because it has no leaf to fail",
    lambda: assert_exit(build({}), 0),
)
check(
    "a repository with no docs/products exits 0, not 2",
    lambda: assert_absent_default_passes(False),
)
check(
    "the same repository under --json prints an empty list and exits 0",
    lambda: assert_absent_default_passes(True),
)

print("\n  which documents count as a leaf")

check(
    "a directory owner with children below it is not a leaf",
    lambda: assert_absent({"web/web.md": NO_BLOCK, "web/deals.md": FULL_BLOCK}, "web.md"),
)
check(
    "a directory owner with no children is a leaf",
    lambda: assert_outcome({"web/web.md": NO_BLOCK}, "web.md", "missing"),
)
check(
    "a plain file beside an owner is a leaf",
    lambda: assert_outcome(
        {"web/web.md": NO_BLOCK, "web/deals.md": NO_BLOCK}, "deals.md", "missing"
    ),
)
check(
    "a deep owner with a child below it is not a leaf",
    lambda: assert_absent(
        {
            "web/web.md": NO_BLOCK,
            "web/dashboard/dashboard.md": NO_BLOCK,
            "web/dashboard/sleep.md": FULL_BLOCK,
        },
        "dashboard.md",
    ),
)
check(
    "a deep owner with no child is a leaf",
    lambda: assert_outcome(
        {"web/web.md": NO_BLOCK, "web/dashboard/dashboard.md": NO_BLOCK},
        "dashboard.md",
        "missing",
    ),
)
check(
    "product_overview.md is never a leaf, even alone in the tree",
    lambda: assert_absent({"product_overview.md": NO_BLOCK}, "product_overview.md"),
)
check(
    "_findings.md is never a leaf",
    lambda: assert_absent(
        {"_findings.md": NO_BLOCK, "web/web.md": FULL_BLOCK}, "_findings.md"
    ),
)

print("\n  what counts as a usable block")

check(
    "a complete block grades ok",
    lambda: assert_outcome({"web/web.md": FULL_BLOCK}, "web.md", "ok"),
)
check(
    "the not-drivable form grades not-drivable",
    lambda: assert_outcome({"web/web.md": NOT_DRIVABLE_BLOCK}, "web.md", "not-drivable"),
)
check(
    "a tree whose only leaf is not drivable exits 0",
    lambda: assert_exit(build({"web/web.md": NOT_DRIVABLE_BLOCK}), 0),
)
check(
    "a block missing one of the five lines grades incomplete",
    lambda: assert_outcome(
        {"web/web.md": FULL_BLOCK.replace('- **Selector:** `[data-testid="deal-row"]`\n', "")},
        "web.md",
        "incomplete",
    ),
)
check(
    "an incomplete block names the line it is missing",
    lambda: assert_missing_line(
        FULL_BLOCK.replace("- **Action:** click the first row, then read the page header\n", ""),
        "Action:",
    ),
)
check(
    "a block that opens and never closes grades unterminated",
    lambda: assert_outcome(
        {"web/web.md": FULL_BLOCK.replace("<!-- drive:end -->", "")},
        "web.md",
        "unterminated",
    ),
)
check(
    "the five lines are read from inside the block, not from the whole document",
    lambda: assert_outcome(
        {
            "web/web.md": "- **Route:** /deals\n- **Precondition:** x\n- **Selector:** y\n"
            "- **Action:** z\n- **Success signal:** w\n\n"
            + FULL_BLOCK.replace("- **Route:** /deals\n", "")
        },
        "web.md",
        "incomplete",
    ),
)
check(
    "the heading is not what finds the block",
    lambda: assert_outcome(
        {"web/web.md": FULL_BLOCK.replace("## How to drive this", "## Driving it")},
        "web.md",
        "ok",
    ),
)

print("\n  the report")

check(
    "the human report names the failing document",
    lambda: assert_in_stdout({"web/web.md": NO_BLOCK}, "web.md"),
)
check(
    "the human report counts the leaves it checked",
    lambda: assert_in_stdout({"web/web.md": FULL_BLOCK}, "1 leaf,"),
)
check(
    "the count reads as a plural when the tree holds more than one leaf",
    lambda: assert_in_stdout(
        {"web/web.md": FULL_BLOCK, "ios/ios.md": FULL_BLOCK}, "2 leaves,"
    ),
)
check(
    "one failing leaf reads as a singular",
    lambda: assert_in_stdout({"web/web.md": NO_BLOCK}, "1 of 1 leaf document carries"),
)
check(
    "two failing leaves read as a plural",
    lambda: assert_in_stdout(
        {"web/web.md": NO_BLOCK, "ios/ios.md": NO_BLOCK}, "2 of 2 leaf documents carry"
    ),
)
check(
    "the human report counts the not-drivable leaves separately",
    lambda: assert_in_stdout({"web/web.md": NOT_DRIVABLE_BLOCK}, "1 marked not drivable"),
)
check(
    "--json on a failing tree still exits 1",
    lambda: assert_json_exit({"web/web.md": NO_BLOCK}, 1),
)
check(
    "--json on a passing tree exits 0",
    lambda: assert_json_exit({"web/web.md": FULL_BLOCK}, 0),
)

print("\n  the shipped template")

check(
    "the example block in SKILL.md passes this checker",
    assert_shipped_example_passes,
)

print(
    f"\nAll {passed} checks passed."
    if not failed
    else f"\n{failed} of {passed + failed} checks FAILED."
)
sys.exit(1 if failed else 0)
