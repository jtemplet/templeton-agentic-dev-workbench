#!/usr/bin/env python3
"""Answer one question: which files this branch touched still differ from the target.

The ship skill asks it twice. Step 2 asks before the rebase, where an empty
answer means the work already landed and the run must close the bead and stop
rather than merge again. Step 5 asks after the squash-merge, where an empty
answer is what makes `git branch -D` safe: main holds the branch's version of
every file the branch authored.

WHY A SCRIPT AND NOT THE SHELL PIPELINE IT REPLACES. The skill used to document
`comm -12 <(git diff --name-only ...) <(git diff --name-only ...)`, with eight
lines of prose warning the reader never to rewrite it as a shell variable
holding the file list. That warning was earned: measured on 2026-08-24, a
newline-separated list expands to ONE pathspec wherever `IFS` excludes newline,
that pathspec matches no file, `git diff` prints nothing and exits 0, and the
caller reads the silence as "already landed" and deletes a branch it never
merged. `set -- $FILES` reported `args=1` for a four-file branch, and the
documented pipeline printed 0 lines where listing the four paths printed 918.
Here the paths are a Python list and never cross a shell word split, so the
trap cannot be re-entered and the warning does not need to be re-read.

TWO RANGES, INTERSECTED.

  touched   `git diff --name-only <base>...<branch>`  three-dot: what this
            branch changed since it forked, and nothing the target changed.
  differing `git diff --name-only <branch> <target>`  two-dot: what still
            differs between the two trees, in either direction.

The intersection is the branch's own outstanding work. A file the target changed
alone is not this branch's business, and a file the branch changed to a value
the target already holds is done.

`.beads/` IS EXCLUDED, ALWAYS. The ship writes it: Step 4 closes the bead and
folds the fresh export into the landing commit, so that path differs between the
branch tip and the target on every ship with a bead, not on some. Without the
exclusion the Step 5 check fires every time and the documented response is to
keep the branch and ask a human, which makes the check noise rather than a
guard. Reproduced on 2026-09-08 shipping tadw-w87: the check printed exactly
`.beads/issues.jsonl` while the deliverable was byte-identical on both sides.
That is tadw-0fo. Do not make this exclusion a flag somebody can forget; extra
exclusions go through `--exclude`.

Exit status: 0 when nothing is outstanding, 1 when something is (the paths go to
stdout, one per line), 2 on operator error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# The ship's own commit writes this on every run that has a bead. See the
# module docstring; this is tadw-0fo.
ALWAYS_EXCLUDED = (".beads/",)

EXIT_NOTHING_OUTSTANDING = 0
EXIT_OUTSTANDING = 1
EXIT_OPERATOR_ERROR = 2


@dataclass(frozen=True)
class Comparison:
    """The three refs that together pose one landed-check question.

    They travel as a unit because no two of them mean anything apart: the
    answer is a property of the triple. Step 2 asks it with the default branch
    as both `base` and `target`, and Step 5 with the pre-landing base.
    """

    base: str
    branch: str
    target: str


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    comparison = Comparison(base=args.base, branch=args.branch, target=args.target)
    try:
        outstanding = outstanding_paths(args.repo_root, comparison, tuple(args.exclude))
    except GitError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    for path in outstanding:
        print(path)
    return EXIT_OUTSTANDING if outstanding else EXIT_NOTHING_OUTSTANDING


def outstanding_paths(
    repo_root: Path,
    comparison: Comparison,
    excluded: tuple[str, ...] = (),
) -> list[str]:
    """The files the branch authored since the base that still differ from the target."""
    touched = changed_paths(repo_root, f"{comparison.base}...{comparison.branch}")
    differing = changed_paths(repo_root, comparison.branch, comparison.target)
    prefixes = ALWAYS_EXCLUDED + tuple(normalize_prefix(p) for p in excluded)
    return sorted(
        path
        for path in touched & differing
        if not any(is_under(path, prefix) for prefix in prefixes)
    )


def changed_paths(repo_root: Path, *revision_arguments: str) -> set[str]:
    """The paths in one diff range, read NUL-separated so none is transformed.

    `-z` is not a convenience here. Without it git applies `core.quotePath`,
    which defaults to true, so `dist/café.js` prints as `"dist/caf\\303\\251.js"`
    with the quotes in the string. The intersection still works, because both
    ranges quote alike, but the leading quote makes the path fail every
    `--exclude` prefix test, and an excluded file is then reported as
    outstanding. A path holding a newline is the same story, one range apart.
    """
    stdout = run_git(repo_root, "diff", "--name-only", "-z", *revision_arguments)
    return {path for path in stdout.split("\0") if path}


def is_under(path: str, prefix: str) -> bool:
    """True when `path` is `prefix` itself or sits beneath it.

    Compares whole path components. `.beads` and `.beads-archive` share a string
    prefix and are different directories, so a bare `startswith` would exclude a
    file this check exists to report.
    """
    if not prefix:
        return False
    stripped = prefix.rstrip("/")
    return path == stripped or path.startswith(stripped + "/")


def normalize_prefix(prefix: str) -> str:
    """Drop a leading `./`, and nothing else.

    `lstrip("./")` strips a character SET, so it turns `.github` into `github`
    and the exclusion then matches no file. Every dotfile directory a caller
    might exclude hits that, and it fails silently: the path is reported as
    outstanding, and the ship keeps a branch it should have deleted.
    """
    prefix = prefix.strip()
    while prefix.startswith("./"):
        prefix = prefix[2:]
    return prefix


class GitError(RuntimeError):
    """git refused a command, or there was no repository to run it in."""


def run_git(repo_root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise GitError("git is not on PATH") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"exit {completed.returncode}"
        raise GitError(f"git {' '.join(arguments)}: {detail}")
    return completed.stdout


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report the files a branch authored that still differ from a target.",
    )
    parser.add_argument("--base", required=True, help="the ref the branch forked from")
    parser.add_argument("--branch", required=True, help="the branch, or a ref naming its tip")
    parser.add_argument("--target", required=True, help="the ref the work should have landed on")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="the repository to read; defaults to the working directory",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATH",
        help="a path or directory to ignore, repeatable; .beads/ is always ignored",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
