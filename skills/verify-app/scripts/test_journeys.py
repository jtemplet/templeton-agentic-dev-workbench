#!/usr/bin/env python3
"""Regression suite for journeys.py.

Stdlib only, no install, mirroring test_check_drive_blocks.py. Run with:
    python3 skills/verify-app/scripts/test_journeys.py

Every case builds a throwaway repository and runs the script as a subprocess, the way
`verify-app` and the report writers call it. The fingerprint group carries most of the
value: a fingerprint that moves when nothing relevant changed re-runs every journey, and
one that holds still when a source file changed passes a journey nobody drove.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "journeys.py"
# Every throwaway repository lives under one directory, removed when the suite ends.
TEMP_ROOT = tempfile.TemporaryDirectory()

passed = 0
failed = 0


def leaf(*refs: str) -> str:
    """A leaf document whose frontmatter names these source_refs."""
    lines = "".join(f"  - {ref}\n" for ref in refs)
    return f"---\ntitle: A feature\nsource_refs:\n{lines}---\n\n# A feature\n"


DEALS_DOC = leaf("ui/src/Deals.vue", "server/api/deals.py")
EXPORT_DOC = leaf("server/jobs/")
SOURCES = {
    "ui/src/Deals.vue": "<template>deals</template>\n",
    "server/api/deals.py": "def deals(): ...\n",
    "server/jobs/export.py": "def export(): ...\n",
    "README.md": "# app\n",
}


def build(docs: dict[str, str], sources: dict[str, str] = SOURCES) -> Path:
    """A throwaway repository: source files at the root, documents under docs/products."""
    repo = Path(tempfile.mkdtemp(dir=TEMP_ROOT.name))
    for relative, body in sources.items():
        write(repo / relative, body)
    for relative, body in docs.items():
        write(repo / "docs" / "products" / relative, body)
    return repo


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def run(repo: Path, changed: list[str], *args: str) -> subprocess.CompletedProcess[str]:
    changed_file = repo / ".changed.txt"
    changed_file.write_text("".join(f"{path}\n" for path in changed), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--changed-files",
            str(changed_file),
            "--repo-root",
            str(repo),
            *args,
        ],
        capture_output=True,
        text=True,
    )


def needed(repo: Path, changed: list[str]) -> dict:
    result = run(repo, changed)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    return json.loads(result.stdout)


def journey(output: dict, name: str) -> dict:
    matches = [j for j in output["journeys"] if j["name"] == name]
    assert len(matches) == 1, f"expected one journey {name!r}, got {output['journeys']}"
    return matches[0]


def fingerprints(repo: Path, changed: list[str]) -> dict[str, str]:
    return {j["name"]: j["fingerprint"] for j in needed(repo, changed)["journeys"]}


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def two_journeys() -> Path:
    return build({"web/web.md": "# Web\n", "web/deals.md": DEALS_DOC, "jobs.md": EXPORT_DOC})


def deals_journey() -> dict:
    return journey(needed(two_journeys(), ["ui/src/Deals.vue"]), "deals")


ALL_SOURCES = ["ui/src/Deals.vue", "server/jobs/export.py"]


def fingerprints_after_edit(edited: str) -> tuple[dict[str, str], dict[str, str]]:
    repo = two_journeys()
    before = fingerprints(repo, ALL_SOURCES)
    write(repo / edited, "edited\n")
    return before, fingerprints(repo, ALL_SOURCES)


print("\n  when a leaf document's source_refs include a changed file")


def assert_names_the_journey() -> None:
    deals = deals_journey()
    assert deals["doc"] == "docs/products/web/deals.md", deals


def assert_lists_the_source_refs() -> None:
    deals = deals_journey()
    assert deals["source_refs"] == ["ui/src/Deals.vue", "server/api/deals.py"], deals


def assert_omits_an_untouched_journey() -> None:
    names = [j["name"] for j in needed(two_journeys(), ["ui/src/Deals.vue"])["journeys"]]
    assert names == ["deals"], names


def assert_directory_ref_covers_a_file_below_it() -> None:
    output = needed(two_journeys(), ["server/jobs/export.py"])
    assert journey(output, "jobs")["source_refs"] == ["server/jobs"], output


check("test_criterion_1_names_the_journey", assert_names_the_journey)
check("the journey carries its source_refs", assert_lists_the_source_refs)
check("a journey whose files did not change is not named", assert_omits_an_untouched_journey)
check("a directory ref covers a changed file below it", assert_directory_ref_covers_a_file_below_it)

print("\n  when a file is edited between two runs")


def assert_edit_in_refs_changes_fingerprint() -> None:
    before, after = fingerprints_after_edit("server/api/deals.py")
    assert before["deals"] != after["deals"], before


def assert_edit_in_refs_leaves_other_journey() -> None:
    before, after = fingerprints_after_edit("server/api/deals.py")
    assert before["jobs"] == after["jobs"], (before, after)


def assert_edit_outside_refs_changes_nothing() -> None:
    before, after = fingerprints_after_edit("README.md")
    assert before == after, (before, after)


def assert_edit_below_directory_ref_changes_fingerprint() -> None:
    before, after = fingerprints_after_edit("server/jobs/export.py")
    assert before["jobs"] != after["jobs"], before


def assert_new_file_below_directory_ref_changes_fingerprint() -> None:
    before, after = fingerprints_after_edit("server/jobs/cleanup.py")
    assert before["jobs"] != after["jobs"], before


check(
    "test_criterion_2_edit_to_a_source_ref_changes_the_fingerprint",
    assert_edit_in_refs_changes_fingerprint,
)
check(
    "the same edit leaves another journey's fingerprint alone",
    assert_edit_in_refs_leaves_other_journey,
)
check(
    "test_criterion_3_edit_outside_every_source_ref_changes_no_fingerprint",
    assert_edit_outside_refs_changes_nothing,
)
check(
    "an edit below a directory ref changes that journey's fingerprint",
    assert_edit_below_directory_ref_changes_fingerprint,
)
check(
    "a new file below a directory ref changes that journey's fingerprint",
    assert_new_file_below_directory_ref_changes_fingerprint,
)

print("\n  for the fingerprint rule itself")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expected(lines: list[str]) -> str:
    return sha("\n".join(sorted(lines)))


def assert_rule_is_sorted_path_hash_lines() -> None:
    deals = deals_journey()
    want = expected(
        [
            f"ui/src/Deals.vue {sha(SOURCES['ui/src/Deals.vue'])}",
            f"server/api/deals.py {sha(SOURCES['server/api/deals.py'])}",
        ]
    )
    assert deals["fingerprint"] == want, deals


def assert_missing_file_hashes_as_absent() -> None:
    repo = build({"gone.md": leaf("ui/src/Gone.vue")})
    gone = journey(needed(repo, ["ui/src/Gone.vue"]), "gone")
    assert gone["fingerprint"] == expected(["ui/src/Gone.vue absent"]), gone


check(
    "test_criterion_1_gives_the_journey_a_fingerprint: the sha256 of sorted '<path> <sha256>' lines",
    assert_rule_is_sorted_path_hash_lines,
)
check(
    "a source_ref that names no file hashes as the word absent",
    assert_missing_file_hashes_as_absent,
)

print("\n  when a changed file is named by no source_refs")


def assert_lists_uncovered() -> None:
    output = needed(two_journeys(), ["ui/src/Deals.vue", "README.md"])
    assert output["uncovered"] == ["README.md"], output


def assert_covered_file_is_not_uncovered() -> None:
    output = needed(two_journeys(), ["ui/src/Deals.vue"])
    assert output["uncovered"] == [], output


def assert_prefix_is_not_a_directory_match() -> None:
    output = needed(two_journeys(), ["server/jobs-archive/old.py"])
    assert output == {"journeys": [], "uncovered": ["server/jobs-archive/old.py"]}, output


check("test_criterion_4_lists_a_changed_file_no_source_ref_names", assert_lists_uncovered)
check("a covered changed file is not listed as uncovered", assert_covered_file_is_not_uncovered)
check(
    "a path that only shares a prefix with a directory ref is uncovered",
    assert_prefix_is_not_a_directory_match,
)

print("\n  which documents count as a journey")


def assert_owner_with_children_is_skipped() -> None:
    repo = build({"web/web.md": leaf("ui/src/Deals.vue"), "web/deals.md": "# Deals\n"})
    output = needed(repo, ["ui/src/Deals.vue"])
    assert output == {"journeys": [], "uncovered": ["ui/src/Deals.vue"]}, output


def assert_external_ref_is_ignored() -> None:
    doc = "---\nsource_refs:\n  - repo: atlas-ios\n    path: ui/src/Deals.vue\n---\n"
    output = needed(build({"ios.md": doc}), ["ui/src/Deals.vue"])
    assert output["journeys"] == [], output


def assert_doc_without_frontmatter_is_no_journey() -> None:
    output = needed(build({"plain.md": "# Plain\n"}), ["ui/src/Deals.vue"])
    assert output == {"journeys": [], "uncovered": ["ui/src/Deals.vue"]}, output


check(
    "a directory owner with children below it is not a journey",
    assert_owner_with_children_is_skipped,
)
check(
    "a mapping-form source_ref names another repository and covers nothing",
    assert_external_ref_is_ignored,
)
check(
    "a document with no frontmatter is not a journey", assert_doc_without_frontmatter_is_no_journey
)

print("\n  for the inputs the caller passes")


def assert_missing_changed_list_exits_2() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--changed-files", "/nonexistent/changed.txt"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (result.returncode, result.stderr)


def assert_missing_named_docs_root_exits_2() -> None:
    result = run(two_journeys(), ["README.md"], "--docs-root", "docs/nope")
    assert result.returncode == 2, (result.returncode, result.stderr)


def assert_absent_default_docs_root_leaves_all_uncovered() -> None:
    output = needed(build({}, sources={"app.py": "x\n"}), ["app.py"])
    assert output == {"journeys": [], "uncovered": ["app.py"]}, output


def assert_blank_and_repeated_lines_are_dropped() -> None:
    output = needed(two_journeys(), ["README.md", "", "README.md"])
    assert output["uncovered"] == ["README.md"], output


check("a changed-files list that does not exist exits 2", assert_missing_changed_list_exits_2)
check(
    "a docs root named on the command line that does not exist exits 2",
    assert_missing_named_docs_root_exits_2,
)
check(
    "a repository with no docs/products lists every changed file as uncovered",
    assert_absent_default_docs_root_leaves_all_uncovered,
)
check(
    "blank and repeated lines in the changed set are dropped",
    assert_blank_and_repeated_lines_are_dropped,
)

TEMP_ROOT.cleanup()
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
