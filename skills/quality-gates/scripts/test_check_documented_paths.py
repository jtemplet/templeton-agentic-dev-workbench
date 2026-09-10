#!/usr/bin/env python3
"""Regression suite for check_documented_paths.py.

Stdlib only, no install, mirroring test_check_worktree_occupants.py. Run with:
    python3 skills/quality-gates/scripts/test_check_documented_paths.py

Every case builds a throwaway tree holding its own documents and its own
`skills/` layout, so a case asserts against the checker rather than against
this repository's current contents. The one exception is
`case_this_repository_passes`, which runs the shipped checker over the shipped
tree, because criterion 4 is a claim about this repository and nothing smaller
can prove it.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-1rm criterion                              Pinned by
  ------------------------------------------------------------------------------
  3. A path that does not resolve fails, naming   case_missing_path_fails_naming_it
     the document and the line
  1. A runnable command with no default fallback  case_fenced_command_without_fallback_fails
     fails, naming the document and the line
  3. A path that resolves passes                  case_resolving_path_passes
  4. Every reference in this repository is        case_this_repository_passes
     prose or a path proven to resolve

  Design decisions in the script's docstring:
  A placeholder names no single file              case_angle_placeholder_is_skipped,
                                                  case_brace_placeholder_is_skipped,
                                                  case_elision_is_skipped
  A bare mention is prose                         case_bare_mention_is_skipped
  Every skip is named, never just counted         case_skipped_references_are_named
  Prose counts, not only fenced blocks            case_inline_backtick_prose_is_checked
  Only a fenced line needs a fallback             case_prose_reference_needs_no_marker
  The marker and default satisfy the rule          case_fenced_command_with_fallback_passes
  An escaped quote closes the path                case_json_sample_is_checked
  A closing bracket closes the path               case_bracket_closes_the_path
  The bare form is the same reference             case_unbraced_variable_is_checked
  Sentence punctuation is not part of the path    case_trailing_period_is_stripped
  History is excluded, never rewritten            case_changelog_is_excluded,
                                                  case_plans_are_excluded
  One read per real file                          case_symlinked_document_is_read_once
  A document outside the root is labelled, not    case_out_of_tree_document_does_not_crash
     a crash
  Operator error is 2, never 1                    case_missing_repo_root_exits_2,
                                                  case_named_document_missing_exits_2
  Stdlib only                                     case_no_third_party_imports
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_documented_paths.py"
REPO = Path(__file__).resolve().parents[3]

MARKER = "<!-- plugin-root-fallback -->"

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


def run(root: Path, *docs: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), *docs],
        capture_output=True,
        text=True,
    )


def tree(documents: dict[str, str]) -> Path:
    """A throwaway plugin root holding `skills/real/SKILL.md` and the documents given.

    The real skill exists so a case can name a path that resolves and a path
    that does not, and have the difference be the only variable. Each key is
    the document's path under the root, written out in full.
    """
    root = Path(tempfile.mkdtemp(prefix="tadw-docpaths-"))
    (root / "skills" / "real").mkdir(parents=True)
    (root / "skills" / "real" / "SKILL.md").write_text("# real\n", encoding="utf-8")
    for relative, body in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


def fenced(command: str) -> str:
    return f"# A note\n\n```bash\n{command}\n```\n"


print("\n  [criterion 3: a path that does not resolve fails, and names where]")


def case_missing_path_fails_naming_it() -> None:
    root = tree({"doc.md": "Read `${CLAUDE_PLUGIN_ROOT}/skills/gone/SKILL.md` now.\n"})
    result = run(root)
    assert result.returncode == 1, f"a missing path must exit 1: {result.stdout}"
    assert "doc.md:1" in result.stdout, (
        f"the document and line must be named: {result.stdout}"
    )
    assert "/skills/gone/SKILL.md" in result.stdout, (
        f"the path must be named: {result.stdout}"
    )


def case_resolving_path_passes() -> None:
    root = tree({"doc.md": "Read `${CLAUDE_PLUGIN_ROOT}/skills/real/SKILL.md` now.\n"})
    result = run(root)
    assert result.returncode == 0, f"a resolving path must exit 0: {result.stdout}"
    assert "1 documented" in result.stdout, (
        f"and be counted as checked: {result.stdout}"
    )


for name, fn in [
    ("a path that does not resolve exits 1, naming document and line [criterion 3]", case_missing_path_fails_naming_it),
    ("a path that resolves exits 0 and is counted", case_resolving_path_passes),
]:
    check(name, fn)


print("\n  [criterion 1: a runnable command finds its script when the variable is unset]")


def case_fenced_command_without_fallback_fails() -> None:
    """The half that catches a new command that expands an unset variable.

    The marker is present and the path resolves, so only the missing default can
    fail it.
    """
    root = tree(
        {
            "doc.md": fenced('python3 "${CLAUDE_PLUGIN_ROOT}/skills/real/SKILL.md"')
            + f"\n{MARKER}\nThe command has a fallback note, but no default.\n"
        }
    )
    result = run(root)
    assert result.returncode == 1, f"a command without a fallback must exit 1: {result.stdout}"
    assert "doc.md:4" in result.stdout, (
        f"the document and line must be named: {result.stdout}"
    )
    assert MARKER in result.stdout, f"the marker must be named: {result.stdout}"


def case_fenced_command_with_fallback_passes() -> None:
    root = tree(
        {
            "doc.md": fenced(
                'python3 "$(find "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}" '
                "-path '*/skills/real/SKILL.md' -print -quit)\""
            )
            + f"\n{MARKER}\nThe command searches for the installed script.\n"
        }
    )
    result = run(root)
    assert result.returncode == 0, (
        f"the marker and default must satisfy the rule: {result.stdout}"
    )


def case_prose_reference_needs_no_marker() -> None:
    """Only a fenced line is a command somebody runs."""
    root = tree({"doc.md": "Read `${CLAUDE_PLUGIN_ROOT}/skills/real/SKILL.md` now.\n"})
    result = run(root)
    assert result.returncode == 0, (
        f"prose is not a command, so it needs no fallback statement: {result.stdout}"
    )


for name, fn in [
    ("a fenced command without a default exits 1 [criterion 1]", case_fenced_command_without_fallback_fails),
    ("the marker and default satisfy the rule", case_fenced_command_with_fallback_passes),
    ("a prose reference needs no marker", case_prose_reference_needs_no_marker),
]:
    check(name, fn)


print("\n  [what names no single file is skipped, and named]")


def case_angle_placeholder_is_skipped() -> None:
    root = tree({"doc.md": "The template is `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`.\n"})
    result = run(root)
    assert result.returncode == 0, f"a <name> template must not fail: {result.stdout}"
    assert "1 skipped" in result.stdout, f"and must be counted skipped: {result.stdout}"


def case_brace_placeholder_is_skipped() -> None:
    root = tree({"doc.md": "The template is `${CLAUDE_PLUGIN_ROOT}/skills/{id}/SKILL.md`.\n"})
    result = run(root)
    assert result.returncode == 0, f"a {{id}} template must not fail: {result.stdout}"
    assert "1 skipped" in result.stdout, f"and must be counted skipped: {result.stdout}"


def case_elision_is_skipped() -> None:
    root = tree({"doc.md": 'Run `python3 "${CLAUDE_PLUGIN_ROOT}/..."` somehow.\n'})
    result = run(root)
    assert result.returncode == 0, f"an elision must not fail: {result.stdout}"
    assert "1 skipped" in result.stdout, f"and must be counted skipped: {result.stdout}"


def case_bare_mention_is_skipped() -> None:
    root = tree({"doc.md": "The variable `${CLAUDE_PLUGIN_ROOT}` is set by Claude Code.\n"})
    result = run(root)
    assert result.returncode == 0, f"a bare mention must not fail: {result.stdout}"
    assert "1 skipped" in result.stdout, f"and must be counted skipped: {result.stdout}"


def case_skipped_references_are_named() -> None:
    """A count alone hides what went unchecked."""
    root = tree({"doc.md": "The template is `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`.\n"})
    result = run(root)
    assert "skipped doc.md:1" in result.stdout, (
        f"the skipped reference must be named, not just counted: {result.stdout}"
    )
    assert "placeholder" in result.stdout, (
        f"and the reason it was skipped: {result.stdout}"
    )


for name, fn in [
    ("a <name> placeholder is skipped, not failed", case_angle_placeholder_is_skipped),
    ("a {id} placeholder is skipped, not failed", case_brace_placeholder_is_skipped),
    ("an elision is skipped, not failed", case_elision_is_skipped),
    ("a bare mention with no path is skipped", case_bare_mention_is_skipped),
    ("every skipped reference is named, with its reason", case_skipped_references_are_named),
]:
    check(name, fn)


print("\n  [every shape a reference is written in]")


def case_inline_backtick_prose_is_checked() -> None:
    """The commands/ and agents/ shape: prose, inline backticks, no fence."""
    root = tree({"doc.md": "**Read** `${CLAUDE_PLUGIN_ROOT}/skills/gone/SKILL.md` and follow it.\n"})
    result = run(root)
    assert result.returncode == 1, (
        f"prose with inline backticks must be checked, not skipped: {result.stdout}"
    )


def case_json_sample_is_checked() -> None:
    """An escaped quote closes the path, as in the report samples in quality-gates."""
    root = tree(
        {
            "doc.md": '{"command": "python3 \\"${CLAUDE_PLUGIN_ROOT}/skills/gone/x.py\\" --repo-root ."}\n'
        }
    )
    result = run(root)
    assert result.returncode == 1, f"a JSON sample must be checked: {result.stdout}"
    assert "/skills/gone/x.py" in result.stdout, (
        f"the escaped quote must close the path, not join it: {result.stdout}"
    )


def case_bracket_closes_the_path() -> None:
    """A markdown link label closes the path, so the `]` is not absorbed into it."""
    root = tree({"doc.md": "See [${CLAUDE_PLUGIN_ROOT}/skills/real/SKILL.md](x.md).\n"})
    result = run(root)
    assert result.returncode == 0, (
        f"a closing bracket must not become part of the path: {result.stdout}"
    )


def case_unbraced_variable_is_checked() -> None:
    root = tree({"doc.md": "Read $CLAUDE_PLUGIN_ROOT/skills/gone/SKILL.md now.\n"})
    result = run(root)
    assert result.returncode == 1, (
        f"the unbraced form is the same reference: {result.stdout}"
    )


def case_trailing_period_is_stripped() -> None:
    """A sentence ending straight after a path must not make the path unresolvable."""
    root = tree({"doc.md": "Read ${CLAUDE_PLUGIN_ROOT}/skills/real/SKILL.md.\n"})
    result = run(root)
    assert result.returncode == 0, (
        f"a trailing period is punctuation, not part of the path: {result.stdout}"
    )


for name, fn in [
    ("prose with inline backticks is checked", case_inline_backtick_prose_is_checked),
    ("an escaped quote inside JSON closes the path", case_json_sample_is_checked),
    ("a closing bracket closes the path", case_bracket_closes_the_path),
    ("the unbraced $CLAUDE_PLUGIN_ROOT is checked too", case_unbraced_variable_is_checked),
    ("a trailing sentence period is not part of the path", case_trailing_period_is_stripped),
]:
    check(name, fn)


print("\n  [history is excluded, never rewritten to match the tree]")


def case_changelog_is_excluded() -> None:
    root = tree({"CHANGELOG.md": "Added `${CLAUDE_PLUGIN_ROOT}/skills/gone/x.py`.\n"})
    result = run(root)
    assert result.returncode == 0, (
        f"CHANGELOG.md records what shipped on a date, so it is excluded: {result.stdout}"
    )


def case_plans_are_excluded() -> None:
    root = tree({"docs/plans/old.md": "Proposed `${CLAUDE_PLUGIN_ROOT}/skills/gone/x.py`.\n"})
    result = run(root)
    assert result.returncode == 0, (
        f"a plan records what was proposed, so it is excluded: {result.stdout}"
    )


for name, fn in [
    ("CHANGELOG.md is excluded", case_changelog_is_excluded),
    ("docs/plans/ is excluded", case_plans_are_excluded),
]:
    check(name, fn)


print("\n  [reading the tree]")


def case_symlinked_document_is_read_once() -> None:
    """CLAUDE.md is a symlink to AGENTS.md, and one miss must be reported once."""
    root = tree({"AGENTS.md": "Read `${CLAUDE_PLUGIN_ROOT}/skills/gone/SKILL.md`.\n"})
    (root / "CLAUDE.md").symlink_to(root / "AGENTS.md")
    result = run(root)
    assert result.returncode == 1, f"the miss must still be reported: {result.stdout}"
    assert result.stdout.count("/skills/gone/SKILL.md") == 1, (
        f"a symlink is the same real file, so it is read once: {result.stdout}"
    )


def case_out_of_tree_document_does_not_crash() -> None:
    """`resolve_docs` accepts an absolute path, so `scan` must survive one that
    is not under the root."""
    root = tree({"doc.md": "nothing here\n"})
    outside = Path(tempfile.mkdtemp(prefix="tadw-docpaths-outside-")) / "outside.md"
    outside.write_text(
        "Read `${CLAUDE_PLUGIN_ROOT}/skills/gone/SKILL.md`.\n", encoding="utf-8"
    )
    result = run(root, str(outside))
    assert "Traceback" not in result.stderr, (
        f"a document outside the root must not raise: {result.stderr}"
    )
    assert result.returncode == 1, (
        f"it must report the miss, not crash: {result.stdout} {result.stderr}"
    )
    assert "outside.md" in result.stdout, (
        f"and label it by its full path: {result.stdout}"
    )


def case_missing_repo_root_exits_2() -> None:
    result = run(Path("/no/such/directory"))
    assert result.returncode == 2, f"operator error is 2, never 1: {result.stderr}"


def case_named_document_missing_exits_2() -> None:
    root = tree({"doc.md": "nothing here\n"})
    result = run(root, "no-such-document.md")
    assert result.returncode == 2, f"operator error is 2, never 1: {result.stderr}"


for name, fn in [
    ("a symlinked document is read once, not twice", case_symlinked_document_is_read_once),
    ("a document outside the root is labelled, not a crash", case_out_of_tree_document_does_not_crash),
    ("a repo root that does not exist exits 2", case_missing_repo_root_exits_2),
    ("a named document that does not exist exits 2", case_named_document_missing_exits_2),
]:
    check(name, fn)


print("\n  [the shipped artifact]")


def case_this_repository_passes() -> None:
    """Criterion 4, as a claim about this repository rather than a fixture."""
    result = run(REPO)
    assert result.returncode == 0, (
        f"every CLAUDE_PLUGIN_ROOT reference in this repository must resolve, and "
        f"every document that runs one must state its fallback: {result.stdout}"
    )


def case_no_third_party_imports() -> None:
    stdlib = {
        "__future__",
        "argparse",
        "dataclasses",
        "re",
        "subprocess",
        "sys",
        "tempfile",
        "pathlib",
    }
    for path in (SCRIPT, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(
            re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M)
        )
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("this repository's own documented references all hold [criterion 4]", case_this_repository_passes),
    ("neither file imports outside the standard library", case_no_third_party_imports),
]:
    check(name, fn)


print(
    f"\nAll {passed} checks passed."
    if not failed
    else f"\n{failed} FAILED, {passed} passed."
)
sys.exit(1 if failed else 0)
