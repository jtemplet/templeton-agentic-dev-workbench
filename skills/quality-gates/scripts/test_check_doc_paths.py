#!/usr/bin/env python3
"""Regression suite for check_doc_paths.py.

Stdlib only, no install, mirroring test_check_framework_leak.py. Run with:
    python3 skills/quality-gates/scripts/test_check_doc_paths.py

The cases come from the checker's contract, and the first group comes from the
run that made this script necessary. The prose version of this gate reported 194
misses on a repository with no broken links, so every shape that produced a false
positive there has a case here. A checker that cries wolf is worse than no
checker: it gets ignored, and then the real miss is ignored with it.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_doc_paths.py"

passed = 0
failed = 0


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(root), *args],
        capture_output=True,
        text=True,
    )


def build(doc_body: str, tree: tuple[str, ...] = ()) -> Path:
    """A throwaway repository: one README plus whatever directories a case needs."""
    root = Path(tempfile.mkdtemp())
    for entry in tree:
        target = root / entry
        if entry.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x", encoding="utf-8")
    (root / "README.md").write_text(doc_body, encoding="utf-8")
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


def misses(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln for ln in result.stdout.splitlines() if " -> " in ln]


print("\n  [no false positives: every shape that broke the prose version]")


def case_slash_command() -> None:
    r = run(build("Run `/code-review` to review.", ("commands/",)))
    assert not misses(r), f"a slash command is not a path: {r.stdout}"


def case_placeholder() -> None:
    r = run(build("Edit `skills/<name>/SKILL.md`.", ("skills/",)))
    assert not misses(r), f"an angle-bracket placeholder is not a path: {r.stdout}"


def case_unanchored_example() -> None:
    r = run(build("For example `src/export.py` fails.", ("skills/",)))
    assert not misses(r), f"a path under no real directory is an example: {r.stdout}"


def case_fenced_block() -> None:
    body = "Text.\n\n```bash\ncat docs/nope.md\n```\n"
    r = run(build(body, ("docs/",)))
    assert not misses(r), f"fenced samples describe other machines: {r.stdout}"


def case_file_line() -> None:
    r = run(build("See `hooks/test.js:378` for the rule.", ("hooks/",)))
    assert not misses(r), f"file:line is a reference, not a path: {r.stdout}"


def case_url_and_glob() -> None:
    body = "See `https://example.com/a.md` and `docs/*.md`."
    r = run(build(body, ("docs/",)))
    assert not misses(r), f"URLs and globs are not path claims: {r.stdout}"


for name, fn in [
    ("a slash command is not reported", case_slash_command),
    ("an angle-bracket placeholder is not reported", case_placeholder),
    ("a path outside every real directory is not reported", case_unanchored_example),
    ("a path inside a fenced block is not reported", case_fenced_block),
    ("a file:line reference is not reported", case_file_line),
    ("a URL and a glob are not reported", case_url_and_glob),
]:
    check(name, fn)


print("\n  [true positives: the misses the gate exists to find]")


def case_backtick_miss() -> None:
    r = run(build("Read `docs/gone.md` for detail.", ("docs/",)))
    assert len(misses(r)) == 1, f"an anchored missing path must be reported: {r.stdout}"
    assert r.returncode == 1, f"misses must exit 1, got {r.returncode}"


def case_link_miss() -> None:
    r = run(build("See [the guide](docs/gone.md).", ("docs/",)))
    assert len(misses(r)) == 1, f"a broken link must be reported: {r.stdout}"


def case_link_needs_no_anchor() -> None:
    """A link is an unambiguous claim, so it is checked without rule 1."""
    r = run(build("See [it](nowhere/gone.md)."))
    assert len(misses(r)) == 1, f"a broken link is a finding anywhere: {r.stdout}"


def case_link_anchor_is_stripped() -> None:
    """A link to a heading inside a real file is not a broken link."""
    r = run(build("See [the rule](docs/real.md#test).", ("docs/real.md",)))
    assert not misses(r), f"an anchor fragment must be stripped: {r.stdout}"


def case_existing_path_is_clean() -> None:
    r = run(build("Read `docs/real.md`.", ("docs/real.md",)))
    assert not misses(r), f"a path that exists is not a miss: {r.stdout}"
    assert r.returncode == 0, f"a clean run must exit 0, got {r.returncode}"


def case_plugin_root_variable() -> None:
    body = "Read `${CLAUDE_PLUGIN_ROOT}/skills/gone/SKILL.md`."
    r = run(build(body, ("skills/",)))
    assert len(misses(r)) == 1, f"the plugin-root prefix must be stripped: {r.stdout}"


for name, fn in [
    ("a missing anchored path is reported, exit 1", case_backtick_miss),
    ("a broken markdown link is reported", case_link_miss),
    ("a broken link needs no directory anchor", case_link_needs_no_anchor),
    ("a link's #fragment is stripped before resolving", case_link_anchor_is_stripped),
    ("a path that exists is clean, exit 0", case_existing_path_is_clean),
    ("${CLAUDE_PLUGIN_ROOT} is stripped before resolving", case_plugin_root_variable),
]:
    check(name, fn)


print("\n  [runtime outputs: paths a documented tool creates]")


def case_ignore_flag() -> None:
    root = build("Writes `docs/roadmap.html`.", ("docs/",))
    assert misses(run(root)), "without an ignore, the output path is a miss"
    r = run(root, "--ignore", "docs/roadmap.html")
    assert not misses(r), f"--ignore must silence it: {r.stdout}"
    assert r.returncode == 0, f"an ignored miss must exit 0, got {r.returncode}"


def case_ignore_file() -> None:
    root = build("Writes `docs/roadmap-v2.1.html`.", ("docs/",))
    (root / ".docpaths-ignore").write_text(
        "# outputs\ndocs/roadmap-v*.html\n", encoding="utf-8"
    )
    r = run(root)
    assert not misses(r), f".docpaths-ignore globs must apply: {r.stdout}"


def case_doc_prefix_skips_a_document() -> None:
    """A plan names the tree it wants to create, so every path in it is a miss."""
    root = build("x", ("docs/plans/",))
    (root / "docs" / "plans" / "p.md").write_text(
        "Create `skills/not-yet/SKILL.md`.", encoding="utf-8"
    )
    (root / "skills").mkdir()
    assert misses(run(root)), "without the skip, a plan's future paths are misses"
    (root / ".docpaths-ignore").write_text("doc:docs/plans/*\n", encoding="utf-8")
    r = run(root)
    assert not misses(r), f"doc: must skip the whole document: {r.stdout}"


for name, fn in [
    ("--ignore silences a runtime output", case_ignore_flag),
    (".docpaths-ignore is read, comments and globs honored", case_ignore_file),
    ("a doc: glob skips a whole document", case_doc_prefix_skips_a_document),
]:
    check(name, fn)


print("\n  [operator errors are loud, never a silent pass]")


def case_missing_document() -> None:
    r = run(build("x"), "no-such-doc.md")
    assert r.returncode == 2, f"a named document that is absent must exit 2, got {r.returncode}"


def case_bad_root() -> None:
    r = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", "/no/such/dir"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, f"a bad root must exit 2, got {r.returncode}"


for name, fn in [
    ("a named document that does not exist exits 2", case_missing_document),
    ("a repo root that does not exist exits 2", case_bad_root),
]:
    check(name, fn)


print("\n  [shipped artifact]")


def case_real_repo() -> None:
    repo = Path(__file__).resolve().parents[3]
    r = run(repo)
    assert r.returncode == 0, f"this repository must be clean:\n{r.stdout}"


check("this repository's own documents all resolve", case_real_repo)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
