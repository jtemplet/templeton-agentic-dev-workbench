#!/usr/bin/env python3
"""Count the TODO, FIXME, HACK, and XXX markers a diff adds.

This is Gate 6 of the quality-gates skill. It exists as a script because the
prose version was one shell recipe carrying a load-bearing `|| true`:

    git diff --unified=0 "$BASE" | grep -c '^+.*\\(TODO\\|FIXME\\|HACK\\|XXX\\)' || true

`grep -c` exits 1 when it counts zero, and zero is the clean result. Drop the
`|| true` while retyping the line and the cleanest possible hygiene gate reports
BLOCKED. The stakeholder is the reader of that report, who sees a broken
toolchain where the truth was good news.

THE `+++` HEADER TRAP. A unified diff opens each file section with `+++ b/path`,
which starts with `+` and carries a path that can itself contain a marker word.
The recipe above counts a file named `TODO.md` as a marker. Skipping every line
that starts with `+++` overcorrects: an added line whose content is itself a diff
(this repository's own documentation holds several) is real content, and `+`
plus `+++ b/x` is a line starting with `++++`. So the header is identified
structurally instead: a `+++` line is a header only OUTSIDE a hunk. Inside one,
every line starting with `+` is added content, whatever it looks like.

EXIT 0 AT ZERO. The skill maps 0 to PASS, 1 to WARN, and 2 to operator error,
which it reports as BLOCKED. A count of zero must exit 0 and nothing else; that
is the whole reason the recipe it replaces needed its `|| true`. An error must
never exit 1: a count nothing produced is worse than an honest failure.

TWO DELIBERATE DIVERGENCES from the recipe, both narrowings, both pinned by a
named test in `test_check_hygiene.py`:

  1. This counts MARKERS, not lines. `grep -c` counts matching lines, so a line
     holding both a TODO and a FIXME counted once. Two markers are two things to
     fix, and the report says "marker count".
  2. A marker needs a word boundary before it. The recipe matched a bare
     substring, so `AUTODOC` counted as a TODO. No boundary is required after
     it, because `TODOs` is a marker and `TODO` followed by `s` is the only way
     to write it.

KNOWN BOUNDARY. `git diff` never sees an untracked file, so a brand-new file's
markers are invisible here until it is added. That matches the recipe this
replaces, and closing it belongs to whoever wires the gate up, which can pass
`git ls-files --others --exclude-standard` alongside the diff.

This file and its suite necessarily contain all four markers, since they define
them. A diff that touches them reports them, and WARN is the right answer. The
alternative is an exemption by path, which would let a real marker hide in any
file that looks like this one.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MARKERS = ("TODO", "FIXME", "HACK", "XXX")

# The lookbehind is the word-boundary narrowing described above: it rejects
# `AUTODOC` while accepting `TODOs`, `#TODO`, and `b/TODO.md`.
MARKER_RE = re.compile(r"(?<![0-9A-Za-z_])(" + "|".join(MARKERS) + ")")

# `@@ -old,count +new,count @@`, where either count may be absent. Group 1 is the
# first line number of the hunk in the new file, which is what a finding cites.
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

# `--unified=0` because no context line can then be mistaken for content, and
# because it is what the recipe used. The rest defend the header shape this
# parser reads: an external diff driver, a textconv filter, or any of the four
# prefix keys in the caller's own git config would each rewrite it. A key an
# older git does not know is inert rather than an error, so pinning all four is
# safe. Only the reported path is at stake here, never the count.
DIFF_ARGS = ("diff", "--unified=0", "--no-color", "--no-ext-diff", "--no-textconv")
CONFIG_ARGS = (
    "-c",
    "core.quotePath=false",
    "-c",
    "diff.noprefix=false",
    "-c",
    "diff.mnemonicPrefix=false",
    "-c",
    "diff.srcPrefix=a/",
    "-c",
    "diff.dstPrefix=b/",
)

EXIT_CLEAN = 0
EXIT_MARKERS_FOUND = 1
EXIT_OPERATOR_ERROR = 2


class GitUnavailable(Exception):
    """git could not produce the diff, so the count is unknown.

    Raised rather than swallowed. Zero markers and no diff at all are the same
    number, and reporting the second as the first is this gate's worst outcome.
    """


class DiffUnparsed(Exception):
    """The diff held a shape this parser does not read.

    Its own exception so the reader learns the count was never taken, rather
    than receiving a silent undercount from the lines that did parse.
    """


@dataclass(frozen=True)
class Marker:
    """One marker on one added line, cited the way every other gate cites."""

    path: str
    line: int
    name: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.name}"


def git_diff(root: Path, base: str) -> str:
    """The unified diff of the working tree against `base`.

    `git diff <base>` with no `...HEAD`, so committed, staged, and unstaged
    changes all appear. The trailing `--` keeps git from reading a base that
    matches a filename as a path.
    """
    try:
        result = subprocess.run(
            ["git", *CONFIG_ARGS, "-C", str(root), *DIFF_ARGS, base, "--"],
            capture_output=True,
        )
    except OSError as exc:  # git absent from PATH, or not executable
        raise GitUnavailable(f"could not run git: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitUnavailable(f"git diff against {base!r} failed: {detail}")
    # Replacement rather than strict decoding: one file in a legacy encoding must
    # not take the gate down. A replaced byte cannot invent a marker, because
    # every marker is ASCII.
    return result.stdout.decode("utf-8", errors="replace")


def scan(diff: str) -> list[Marker]:
    """Every marker on an added line, in diff order.

    A small state machine, because the only reliable way to tell a `+++` header
    from added content that begins with `+++` is whether a hunk is open.
    """
    markers: list[Marker] = []
    path = "(unknown file)"
    line = 0
    in_hunk = False

    for raw in diff.splitlines():
        hunk = HUNK_RE.match(raw)
        if hunk:
            line = int(hunk.group(1))
            in_hunk = True
        elif raw.startswith("@@"):
            raise DiffUnparsed(f"unreadable hunk header: {raw!r}")
        elif not in_hunk:
            if raw.startswith("+++ "):
                path = header_path(raw[4:])
        elif raw.startswith("+"):
            markers.extend(
                Marker(path, line, match.group(1))
                for match in MARKER_RE.finditer(raw[1:])
            )
            line += 1
        elif raw.startswith(" "):
            line += 1
        elif raw.startswith(("-", "\\")):
            pass  # a removed line, or the "\ No newline at end of file" trailer
        else:
            in_hunk = False  # the hunk ended, so this is the next file's header

    return markers


def header_path(value: str) -> str:
    """The path from a `+++ ` header, without git's `b/` prefix.

    `/dev/null`, which git writes for a deleted file, is left as it is. So is a
    quoted path: `core.quotePath=false` leaves only a name holding a tab, a
    newline, or a quote in that form, and git accepts the quoted spelling back.
    """
    return value[2:] if value.startswith("b/") else value


def tally(markers: list[Marker]) -> str:
    """The per-name breakdown, in the order the gate documents its markers."""
    counted = [(name, sum(1 for m in markers if m.name == name)) for name in MARKERS]
    return ", ".join(f"{name} {count}" for name, count in counted if count)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base",
        required=True,
        metavar="REV",
        help="Revision to diff the working tree against",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    if not (root / ".git").exists():
        print(f"ERROR: {root} is not a git repository", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    if not args.base.strip():
        print("ERROR: --base must name a revision", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    try:
        markers = scan(git_diff(root, args.base))
    except (GitUnavailable, DiffUnparsed) as exc:
        # Exit 2, never 1 and never 0. Exit 1 reports a count nothing produced,
        # and exit 0 reports a clean gate that never ran.
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    if not markers:
        print("OK: 0 markers added (no TODO, FIXME, HACK, or XXX on an added line)")
        return EXIT_CLEAN

    for marker in markers:
        print(marker)
    plural = "" if len(markers) == 1 else "s"
    print(f"\n{len(markers)} marker{plural} added ({tally(markers)})")
    return EXIT_MARKERS_FOUND


if __name__ == "__main__":
    sys.exit(main())
