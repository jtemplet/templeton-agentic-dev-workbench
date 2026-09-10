#!/usr/bin/env python3
"""Check every documented `${CLAUDE_PLUGIN_ROOT}` reference: the path exists, and
a command that runs one finds its script when the variable is unset.

A document can name a plugin script that has moved, been renamed, or was never
built, and nothing notices. `check_doc_paths.py` does not: it reads a path a
document claims, and `${CLAUDE_PLUGIN_ROOT}/skills/ship/scripts/x.py` is a shell
expansion rather than a claim it can resolve. `check_documented_bd_commands.py`
does not either: it filters to `bd` commands on a read-only safelist, so a
`python3` line never reaches it. That gap is what tadw-1rm found.

THE VARIABLE RESOLVES TO THE REPOSITORY ROOT HERE, because this repository IS
the plugin. So substituting `--repo-root` for the variable and asking whether
the path exists is the same question a consumer's Claude Code answers when it
expands the variable against the installed plugin directory.

TWO FAILURES, NOT ONE. A path that does not exist is the obvious one. The
second is a command that interpolates `${CLAUDE_PLUGIN_ROOT}` without a
default. Claude Code expands the variable when it loads a skill, but the Bash
tool does not receive it. A runnable command must use `${CLAUDE_PLUGIN_ROOT:-...}`
to find an installed copy when Bash has no value.

THE FALLBACK HAS TWO PARTS. `${CLAUDE_PLUGIN_ROOT:-...}` makes the command run
when Bash has no value. `<!-- plugin-root-fallback -->` marks the explanation.
Matching the explanation by wording would break when somebody rephrases it.

PROSE COUNTS, NOT ONLY FENCED BLOCKS, for the path half. The 25 highest-value
references are `**Read** `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`` lines in
`commands/` and `agents/`, written as prose with inline backticks, and each is
the only route from a command to its skill. A path that does not resolve breaks
the command whether or not a fence surrounds it. The runnable-command half is
narrower on purpose: only a fenced line is a command somebody runs.

TWO KINDS OF REFERENCE ARE SKIPPED, and each one is named in the report so a
reader can see what was not checked:

  1. A PLACEHOLDER. `/skills/<name>/SKILL.md` is a template, and `/...` is an
     elision. Neither names one file.
  2. A BARE MENTION. The variable named with no path after it is prose about
     the variable.

HISTORICAL RECORDS ARE EXCLUDED: `CHANGELOG.md` and `docs/plans/`. Both say what
was proposed or done on a date. `docs/plans/quality-gates-hardening.md` quotes a
proposed `check_secrets.py` that was never built, and that record is correct as
history. Editing it to match the tree as it stands today would destroy the thing
it exists to hold. `.rumdl.toml` already excludes `CHANGELOG.md` for this same
reason.

Exit status: 0 when every reference resolves and every runnable command has a
fallback, 1 when either fails, 2 on operator error.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The variable, braced or bare, plus the path that follows it. The path ends at
# whitespace or at any character that closes a quoting context: a quote, a
# backtick, a closing parenthesis or bracket, a comma, a pipe, or the backslash
# that escapes a quote inside a JSON sample.
REFERENCE = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT(?!:)\}?(?P<path>[^\s\"'`)\]\\,|]*)")

# `<name>` and `{id}` open a template; `...` is an elision. A path carrying any
# of them names no single file.
PLACEHOLDER = re.compile(r"[<{]|\.\.\.")

FENCE = re.compile(r"^\s*```")

# What a document must carry when it puts a reference in a fenced block.
FALLBACK_MARKER = "<!-- plugin-root-fallback -->"
FALLBACK_EXPRESSION = "${CLAUDE_PLUGIN_ROOT:-"
RUNNABLE_COMMAND = re.compile(r"^\s*(?:python3|bash|sh)\b")

# Trailing sentence punctuation, stripped because no shipped filename ends in
# it and prose routinely closes a sentence straight after a path.
SENTENCE_PUNCTUATION = ".,;:"

EXCLUDED_DIRS = frozenset((".git", "node_modules", ".worktrees"))
EXCLUDED_PATHS = frozenset(("CHANGELOG.md", "docs/plans"))

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_OPERATOR_ERROR = 2


@dataclass(frozen=True)
class Miss:
    """One documented path that does not exist under the plugin root."""

    location: str
    path: str

    def __str__(self) -> str:
        return f"{self.location}\n  ${{CLAUDE_PLUGIN_ROOT}}{self.path}\n  no such path"


@dataclass(frozen=True)
class Unstated:
    """One command that cannot find its script when the variable is unset."""

    location: str

    def __str__(self) -> str:
        return (
            f"{self.location}\n  a fenced ${{CLAUDE_PLUGIN_ROOT}} command without "
            f"{FALLBACK_EXPRESSION}... or {FALLBACK_MARKER}\n  give the command a "
            "default plugin-root search"
        )


@dataclass(frozen=True)
class Skipped:
    """One reference that names no single file, and why."""

    location: str
    reason: str


def label_for(root: Path, doc: Path) -> str:
    """The document's path relative to the root, or its full path when it is
    outside the root.

    `resolve_docs` accepts an absolute path, so a caller can name a document
    anywhere. `Path.relative_to` raises on one that is not under the root, and
    an uncaught raise here would read as a failing check rather than as the
    operator naming an outside file.
    """
    try:
        return doc.relative_to(root).as_posix()
    except ValueError:
        return doc.as_posix()


def is_excluded(root: Path, doc: Path) -> bool:
    posix = label_for(root, doc)
    if EXCLUDED_DIRS & set(Path(posix).parts):
        return True
    return any(
        posix == excluded or posix.startswith(f"{excluded}/")
        for excluded in EXCLUDED_PATHS
    )


def markdown_files(root: Path) -> list[Path]:
    """Every markdown file worth checking, one per real file.

    Deduplicated by resolved path because CLAUDE.md is a symlink to AGENTS.md,
    and reading both would report every finding in it twice.
    """
    seen: set[Path] = set()
    files: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if is_excluded(root, path):
            continue
        real = path.resolve()
        if real in seen:
            continue
        seen.add(real)
        files.append(path)
    return files


def referenced_path(match: re.Match[str]) -> tuple[str | None, str]:
    """(the path a reference names, why it names none).

    The path is None when the reference names no single file, and the reason is
    what the report prints beside it.
    """
    raw = match.group("path")
    if not raw:
        return None, "a bare mention, with no path"
    if PLACEHOLDER.search(raw):
        return None, f"a placeholder: {raw}"
    path = raw.rstrip(SENTENCE_PUNCTUATION)
    if not path:
        return None, "punctuation only, with no path"
    return path, ""


def scan(
    root: Path, docs: list[Path]
) -> tuple[list[Miss], list[Unstated], list[Skipped], int]:
    """(misses, unstated documents, skipped references, checked count)."""
    misses: list[Miss] = []
    unstated: list[Unstated] = []
    skipped: list[Skipped] = []
    checked = 0

    for doc in docs:
        label = label_for(root, doc)
        text = doc.read_text(encoding="utf-8")
        fenced = False
        first_unresolved_command = ""
        first_fallback_command = ""

        for lineno, line in enumerate(text.splitlines(), 1):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if (
                fenced
                and RUNNABLE_COMMAND.match(line)
                and "CLAUDE_PLUGIN_ROOT" in line
            ):
                if FALLBACK_EXPRESSION in line:
                    if not first_fallback_command:
                        first_fallback_command = f"{label}:{lineno}"
                elif not first_unresolved_command:
                    first_unresolved_command = f"{label}:{lineno}"
            for match in REFERENCE.finditer(line):
                path, reason = referenced_path(match)
                if path is None:
                    skipped.append(Skipped(f"{label}:{lineno}", reason))
                    continue
                checked += 1
                if not (root / path.lstrip("/")).exists():
                    misses.append(Miss(f"{label}:{lineno}", path))

        if first_unresolved_command or (
            first_fallback_command and FALLBACK_MARKER not in text
        ):
            unstated.append(Unstated(first_unresolved_command or first_fallback_command))

    return misses, unstated, skipped, checked


def resolve_docs(root: Path, given: list[str]) -> list[Path]:
    if given:
        return [Path(g) if Path(g).is_absolute() else root / g for g in given]
    return markdown_files(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docs", nargs="*", help="Documents to check")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    docs = resolve_docs(root, args.docs)
    missing_docs = [doc for doc in docs if not doc.is_file()]
    if missing_docs:
        for doc in missing_docs:
            print(f"ERROR: no such document: {doc}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    misses, unstated, skipped, checked = scan(root, docs)
    for finding in (*misses, *unstated):
        print(finding)

    for skip in skipped:
        print(f"skipped {skip.location}: {skip.reason}")

    if misses or unstated:
        print(
            f"\n{len(misses)} documented CLAUDE_PLUGIN_ROOT paths do not exist, "
            f"and {len(unstated)} documented commands lack a working fallback "
            f"({checked} checked, {len(skipped)} skipped)"
        )
        return EXIT_FAILED
    print(
        f"OK: {checked} documented CLAUDE_PLUGIN_ROOT paths all resolve, and every "
        f"runnable command has a working fallback ({len(skipped)} skipped)"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
