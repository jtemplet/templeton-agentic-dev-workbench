#!/usr/bin/env python3
"""Regression suite for check_hygiene.py.

Stdlib only, no install, mirroring test_changed_set.py. Run with:
    python3 skills/quality-gates/scripts/test_check_hygiene.py

Every case builds a throwaway repository with one commit, plants one kind of
change against it, and asserts the count and the exit status.

RULE-TO-TEST MAPPING. This block is what proves the port from the Gate 7 shell
recipe neither narrowed nor widened the count by accident. A rule with no test
here is a rule nothing holds.

  Gate 7 rule (skills/quality-gates/SKILL.md)     Pinned by
  ------------------------------------------------------------------------------
  Added lines are counted                        case_two_added_markers  (criterion 1)
  All four marker names count                   case_all_four_names_count
  A removed marker is not added                 case_removed_marker  (criterion 3)
  An unchanged marker is not added              case_untouched_marker_absent
  A clean diff counts zero                     case_clean_diff  (criterion 4)
  Zero exits 0, never a BLOCKED code            case_clean_diff, case_removed_marker
  Above zero exits 1                           case_two_added_markers  (criterion 1)
  Staged work counts                            case_staged_and_unstaged_both_count
  Unstaged work counts                          case_staged_and_unstaged_both_count
  Committed work counts                         case_committed_marker_counts
  An untracked file is not in a diff            case_untracked_marker_is_invisible

The `+++` header, which is criterion 2 and the one real decision in the design:

  A marker in a `+++ b/TODO.md` header is not   case_header_path_marker  (criterion 2)
  A `rename to TODO.md` path is not             case_rename_to_marker_path
  Added content that starts with `+++` IS       case_quoted_diff_content_counts

The two deliberate narrowings, each stated in the script's docstring:

  Markers are counted, not matching lines       case_two_markers_on_one_line
  A marker needs a word boundary before it      case_marker_inside_a_word
  It needs none after it, so `TODOs` counts     case_plural_marker_counts
  Matching stays case-sensitive                 case_lowercase_marker

Operator error is exit 2 and never 1, because exit 1 is a count:

  A base that will not resolve                  case_unresolvable_base_exits_2
  A repo root that is not one                   case_bad_root_exits_2, case_not_a_git_repo_exits_2
  An absent --base                              case_missing_base_argument_exits_2
  git missing from PATH                         case_git_missing_exits_2

Bare python3 with no third-party import is pinned by case_no_third_party_imports
plus the fact that this file runs at all.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_hygiene.py"

# A fixed identity and no global excludes file, so a case tests the script rather
# than the machine it runs on.
GIT = [
    "git",
    "-c",
    "core.excludesFile=/dev/null",
    "-c",
    "user.email=t@t",
    "-c",
    "user.name=t",
]

passed = 0
failed = 0


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*GIT, "-C", str(root), *args], capture_output=True, text=True, check=check
    )


def run(root: Path, base: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), "--base", base],
        capture_output=True,
        text=True,
    )


def build(files: dict[str, str] | None = None) -> tuple[Path, str]:
    """A repository holding `files` in one commit. Returns the root and that SHA.

    The base is the commit SHA rather than a branch name, so a case can commit
    freely on top of it without moving the point of comparison.
    """
    root = Path(tempfile.mkdtemp())
    git(root, "init", "-q")
    git(root, "config", "core.excludesFile", "/dev/null")
    for name, body in (files or {"app.py": "print('x')\n"}).items():
        write(root / name, body)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    return root, git(root, "rev-parse", "HEAD").stdout.strip()


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def count_line(result: subprocess.CompletedProcess[str]) -> str:
    """The summary line, which is the number the skill reports."""
    lines = [line for line in result.stdout.splitlines() if "marker" in line]
    assert lines, f"the run must report a count: {result.stdout!r} {result.stderr!r}"
    return lines[-1]


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


print("\n  [what an added marker costs]")


def case_two_added_markers() -> None:
    """Criterion 1. Two added marker lines exit 1 and report 2."""
    root, base = build()
    write(root / "app.py", "print('x')\n# TODO: later\n# FIXME: broken\n")
    r = run(root, base)
    assert r.returncode == 1, f"added markers must exit 1, got {r.returncode}: {r.stderr}"
    assert "2 markers added" in count_line(r), f"the count must be 2: {r.stdout!r}"
    assert "app.py:2: TODO" in r.stdout, f"the TODO must be cited: {r.stdout!r}"
    assert "app.py:3: FIXME" in r.stdout, f"the FIXME must be cited: {r.stdout!r}"


def case_all_four_names_count() -> None:
    root, base = build()
    write(root / "app.py", "# TODO\n# FIXME\n# HACK\n# XXX\n")
    r = run(root, base)
    assert r.returncode == 1, f"four markers must exit 1, got {r.returncode}: {r.stderr}"
    assert "4 markers added" in count_line(r), f"all four names must count: {r.stdout!r}"


def case_single_marker_reads_as_singular() -> None:
    root, base = build()
    write(root / "app.py", "print('x')\n# HACK: works for now\n")
    r = run(root, base)
    assert "1 marker added" in count_line(r), f"one marker, not markers: {r.stdout!r}"


def case_committed_marker_counts() -> None:
    """A commit made after the base is still part of the change under review."""
    root, base = build()
    write(root / "app.py", "print('x')\n# TODO: later\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "work")
    r = run(root, base)
    assert r.returncode == 1, f"a committed marker must count: {r.stderr}"
    assert "1 marker added" in count_line(r), f"the count must be 1: {r.stdout!r}"


def case_staged_and_unstaged_both_count() -> None:
    """`git diff <base>` with no `...HEAD`, so uncommitted work is in scope.

    This gate runs before a commit more often than after one. `git diff
    "$BASE"...HEAD` would report zero here while two markers sat in the tree.
    """
    root, base = build()
    write(root / "staged.py", "# TODO: staged\n")
    git(root, "add", "staged.py")
    write(root / "app.py", "print('x')\n# FIXME: unstaged\n")
    r = run(root, base)
    assert r.returncode == 1, f"uncommitted markers must count: {r.stderr}"
    assert "2 markers added" in count_line(r), f"both must count: {r.stdout!r}"


for name, fn in [
    ("two added markers exit 1 and report 2 [criterion 1]", case_two_added_markers),
    ("TODO, FIXME, HACK, and XXX all count", case_all_four_names_count),
    ("a single marker reads as singular", case_single_marker_reads_as_singular),
    ("a marker committed after the base counts", case_committed_marker_counts),
    ("staged and unstaged markers both count", case_staged_and_unstaged_both_count),
]:
    check(name, fn)


print("\n  [zero is the clean answer, and it exits 0]")


def case_clean_diff() -> None:
    """Criterion 4, and the trap the `|| true` in the old recipe papered over.

    `grep -c` exits 1 at zero. Any non-zero code here is read as BLOCKED, so a
    clean gate would report a broken toolchain.
    """
    root, base = build()
    r = run(root, base)
    assert r.returncode == 0, f"a clean diff must exit 0, got {r.returncode}: {r.stderr}"
    assert "0 markers added" in r.stdout, f"the count must be 0: {r.stdout!r}"


def case_removed_marker() -> None:
    """Criterion 3. Deleting a TODO adds nothing, so the count is 0 and exit is 0."""
    root, base = build({"app.py": "# TODO: later\nprint('x')\n"})
    write(root / "app.py", "print('x')\n")
    r = run(root, base)
    assert r.returncode == 0, f"a removal must exit 0, got {r.returncode}: {r.stderr}"
    assert "0 markers added" in r.stdout, f"a removal adds nothing: {r.stdout!r}"


def case_untouched_marker_absent() -> None:
    """A marker someone else left years ago changes nothing the reader can act on."""
    root, base = build({"app.py": "# TODO: ancient\nprint('x')\n"})
    write(root / "app.py", "# TODO: ancient\nprint('y')\n")
    r = run(root, base)
    assert r.returncode == 0, f"an untouched marker must exit 0: {r.stderr}"
    assert "0 markers added" in r.stdout, f"it is not added by this diff: {r.stdout!r}"


def case_untracked_marker_is_invisible() -> None:
    """The documented boundary: `git diff` never sees an untracked file.

    Pinned rather than left implicit, because it is the one case where a real
    marker goes unreported, and whoever wires this gate up needs to know it is
    the script's behavior rather than an accident. Closing it means passing the
    untracked list in alongside the diff.
    """
    root, base = build()
    write(root / "brand_new.py", "# TODO: never committed\n")
    r = run(root, base)
    assert r.returncode == 0, f"an untracked file is not in a diff: {r.stdout!r}"
    git(root, "add", "brand_new.py")
    r = run(root, base)
    assert r.returncode == 1, f"adding it makes the marker visible: {r.stdout!r}"


for name, fn in [
    ("a clean diff exits 0 and reports 0 [criterion 4]", case_clean_diff),
    ("a removed marker exits 0 and reports 0 [criterion 3]", case_removed_marker),
    ("an untouched marker does not count", case_untouched_marker_absent),
    ("an untracked file's marker is invisible until it is added", case_untracked_marker_is_invisible),
]:
    check(name, fn)


print("\n  [the +++ header, which is not content]")


def case_header_path_marker() -> None:
    """Criterion 2. `+++ b/TODO.md` starts with `+` and holds a marker word.

    The old recipe counted this file's own name as a TODO. The file's content
    holds no marker, so the only correct answer is 0.
    """
    root, base = build()
    write(root / "TODO.md", "nothing to see\n")
    git(root, "add", "TODO.md")
    r = run(root, base)
    assert r.returncode == 0, f"a header path must exit 0, got {r.returncode}: {r.stderr}"
    assert "0 markers added" in r.stdout, f"a header is not content: {r.stdout!r}"
    assert "TODO.md:" not in r.stdout, f"no finding may cite the header: {r.stdout!r}"


def case_header_path_marker_with_real_content_marker() -> None:
    """The header stays out while the file's own marker still counts.

    An absence assertion alone would pass if the script counted nothing at all,
    which is the regression most worth catching here.
    """
    root, base = build()
    write(root / "TODO.md", "# FIXME: this one is real\n")
    git(root, "add", "TODO.md")
    r = run(root, base)
    assert r.returncode == 1, f"the content marker must count: {r.stderr}"
    assert "1 marker added" in count_line(r), f"exactly one, not two: {r.stdout!r}"
    assert "TODO.md:1: FIXME" in r.stdout, f"cited at its line: {r.stdout!r}"


def case_rename_to_marker_path() -> None:
    """Renaming a file INTO a marker path, with an edit, still counts 0.

    The edit is what makes this case bite. A pure `git mv` emits `rename from`
    and `rename to` with no `+++` header and no hunk at all, so it would pass
    even with the header rule deleted. Renaming plus modifying emits
    `+++ b/TODO.md` over a real hunk, which is the shape that exercises the rule.
    """
    root, base = build({"app.py": "print('x')\n"})
    git(root, "mv", "app.py", "TODO.md")
    write(root / "TODO.md", "print('x')\nprint('y')\n")
    r = run(root, base)
    assert r.returncode == 0, f"a rename adds no marker, got {r.returncode}: {r.stderr}"
    assert "0 markers added" in r.stdout, f"a rename is not an addition: {r.stdout!r}"
    assert "TODO.md:" not in r.stdout, f"no finding may cite the new path: {r.stdout!r}"


def case_quoted_diff_content_counts() -> None:
    """Skipping every `+++` line overcorrects, and this is the case that proves it.

    An added line whose content is itself a diff header arrives as `++++ b/...`.
    It is content: this repository's own documentation quotes diffs, and a marker
    inside one is as real as any other.
    """
    root, base = build()
    write(root / "docs/x.md", "```diff\n+++ b/TODO.md\n+# TODO: real\n```\n")
    git(root, "add", "docs/x.md")
    r = run(root, base)
    assert r.returncode == 1, f"quoted diff content must count: {r.stderr}"
    assert "2 markers added" in count_line(r), f"both quoted markers count: {r.stdout!r}"
    for line in r.stdout.splitlines():
        if ": TODO" in line:
            assert line.startswith("docs/x.md:"), f"cited in the real file: {line!r}"


for name, fn in [
    ("a marker in a `+++ b/TODO.md` header does not count [criterion 2]", case_header_path_marker),
    ("a header path is skipped while the file's own marker counts", case_header_path_marker_with_real_content_marker),
    ("a `rename to TODO.md` path does not count", case_rename_to_marker_path),
    ("an added line that begins with `+++` is content, and counts", case_quoted_diff_content_counts),
]:
    check(name, fn)


print("\n  [the two narrowings, versus what grep -c did]")


def case_two_markers_on_one_line() -> None:
    """Markers are counted, not matching lines. `grep -c` reported 1 here."""
    root, base = build()
    write(root / "app.py", "print('x')  # TODO: rename, FIXME: and validate\n")
    r = run(root, base)
    assert r.returncode == 1, f"one line with two markers must exit 1: {r.stderr}"
    assert "2 markers added" in count_line(r), f"two markers, one line: {r.stdout!r}"


def case_marker_inside_a_word() -> None:
    """A word boundary is required before a marker. `AUTODOC` contains `TODO`.

    This is the false positive the substring match produced, and the reason the
    lookbehind is there rather than a bare alternation.
    """
    root, base = build()
    write(root / "app.py", "AUTODOC = True\nUNFIXMEABLE = False\n")
    r = run(root, base)
    assert r.returncode == 0, f"a marker inside a word must not count: {r.stdout!r}"
    assert "0 markers added" in r.stdout, f"no boundary, no marker: {r.stdout!r}"


def case_plural_marker_counts() -> None:
    """No boundary is required after a marker, so `TODOs` still counts."""
    root, base = build()
    write(root / "app.py", "# TODOs: two things here\n")
    r = run(root, base)
    assert r.returncode == 1, f"a plural marker must count: {r.stdout!r}"
    assert "1 marker added" in count_line(r), f"the count must be 1: {r.stdout!r}"


def case_lowercase_marker() -> None:
    """Case-sensitive, as the recipe was. `todo` in prose is not a marker."""
    root, base = build()
    write(root / "app.py", "# todo: this is a sentence about a todo list\n")
    r = run(root, base)
    assert r.returncode == 0, f"lowercase must not count: {r.stdout!r}"
    assert "0 markers added" in r.stdout, f"matching stays case-sensitive: {r.stdout!r}"


def case_tally_names_each_marker() -> None:
    root, base = build()
    write(root / "app.py", "# TODO\n# TODO\n# XXX\n")
    r = run(root, base)
    summary = count_line(r)
    assert "TODO 2" in summary, f"the breakdown must count TODO twice: {summary!r}"
    assert "XXX 1" in summary, f"the breakdown must name XXX: {summary!r}"
    assert "FIXME" not in summary, f"an absent name stays out: {summary!r}"


for name, fn in [
    ("two markers on one line count 2, where grep -c counted 1", case_two_markers_on_one_line),
    ("a marker inside a word does not count", case_marker_inside_a_word),
    ("a plural marker counts", case_plural_marker_counts),
    ("a lowercase marker does not count", case_lowercase_marker),
    ("the summary breaks the count down by name", case_tally_names_each_marker),
]:
    check(name, fn)


print("\n  [content this parser must survive]")


def case_binary_file_does_not_crash() -> None:
    """git reports a binary file as one summary line, which holds no marker."""
    root, base = build()
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01\x02TODO\xff\xfe")
    git(root, "add", "logo.png")
    r = run(root, base)
    assert r.returncode == 0, f"a binary file must not count, got {r.returncode}: {r.stderr}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


def case_undecodable_text_does_not_crash() -> None:
    """One file in a legacy encoding must not take the gate down."""
    root, base = build()
    (root / "legacy.txt").write_bytes(b"caf\xe9\n# TODO: still counted\n")
    git(root, "add", "legacy.txt")
    r = run(root, base)
    assert r.returncode == 1, f"the marker must survive decoding: {r.stdout!r} {r.stderr!r}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


def case_deleted_file_reports_no_marker() -> None:
    root, base = build({"app.py": "print('x')\n", "gone.py": "# TODO: leaving\n"})
    git(root, "rm", "-q", "gone.py")
    r = run(root, base)
    assert r.returncode == 0, f"a deletion adds nothing, got {r.returncode}: {r.stderr}"
    assert "0 markers added" in r.stdout, f"a deletion is not an addition: {r.stdout!r}"


for name, fn in [
    ("a binary file does not crash the parser", case_binary_file_does_not_crash),
    ("undecodable bytes do not crash the parser", case_undecodable_text_does_not_crash),
    ("deleting a file holding a marker reports 0", case_deleted_file_reports_no_marker),
]:
    check(name, fn)


print("\n  [operator error is exit 2, never exit 1]")


def case_unresolvable_base_exits_2() -> None:
    """Exit 1 is a count. A base that does not exist produced no count at all."""
    root, _ = build()
    r = run(root, "no-such-ref")
    assert r.returncode == 2, f"a bad base must exit 2, got {r.returncode}: {r.stderr}"
    assert "ERROR" in r.stderr, f"it must say what went wrong: {r.stderr!r}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


def case_bad_root_exits_2() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", "/no/such/dir", "--base", "HEAD"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, f"a bad root must exit 2, got {r.returncode}"


def case_not_a_git_repo_exits_2() -> None:
    root = Path(tempfile.mkdtemp())
    write(root / "app.py", "print('x')\n")
    r = run(root, "HEAD")
    assert r.returncode == 2, f"a non-repository must exit 2, got {r.returncode}"


def case_missing_base_argument_exits_2() -> None:
    """`--base` is required, and argparse's own refusal already exits 2."""
    root, _ = build()
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, f"an absent --base must exit 2, got {r.returncode}"
    assert "--base" in r.stderr, f"it must name the missing argument: {r.stderr!r}"


def case_blank_base_exits_2() -> None:
    root, _ = build()
    r = run(root, "   ")
    assert r.returncode == 2, f"a blank base must exit 2, got {r.returncode}: {r.stderr}"


def case_git_missing_exits_2() -> None:
    root, base = build()
    empty_bin = Path(tempfile.mkdtemp())
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), "--base", base],
        capture_output=True,
        text=True,
        env={"PATH": str(empty_bin)},
    )
    assert r.returncode == 2, f"a missing git must exit 2, got {r.returncode}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


for name, fn in [
    ("a base that will not resolve exits 2", case_unresolvable_base_exits_2),
    ("a repo root that does not exist exits 2", case_bad_root_exits_2),
    ("a directory that is not a git repository exits 2", case_not_a_git_repo_exits_2),
    ("an absent --base exits 2", case_missing_base_argument_exits_2),
    ("a blank --base exits 2", case_blank_base_exits_2),
    ("git missing from PATH exits 2", case_git_missing_exits_2),
]:
    check(name, fn)


print("\n  [shipped artifact]")


def case_real_repo_runs_clean() -> None:
    """The script runs against this repository without crashing.

    `--base HEAD` rather than a remote branch, because a clone with no fetched
    `origin/main` would exit 2 here for a reason that has nothing to do with the
    script. Both 0 and 1 are correct answers: this file and the script it tests
    hold all four markers by necessity, so a diff that touches them reports them.
    """
    repo = Path(__file__).resolve().parents[3]
    r = run(repo, "HEAD")
    assert r.returncode in (0, 1), f"expected 0 or 1, got {r.returncode}: {r.stderr}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__", "argparse", "dataclasses", "re", "subprocess", "sys",
        "tempfile", "pathlib",
    }
    for path in (SCRIPT, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M))
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("this repository runs without a crash", case_real_repo_runs_clean),
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
