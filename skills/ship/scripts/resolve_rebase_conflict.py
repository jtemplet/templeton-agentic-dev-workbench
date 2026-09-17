#!/usr/bin/env python3
"""Resolve the two rebase conflicts that need no judgment, and refuse every other.

Step 2 of the ship skill rebases a feature branch onto the default branch. Two
paths conflict there for reasons that have nothing to do with the code, and both
have one correct resolution that a person adds nothing to:

  `.beads/issues.jsonl`  A passive export of the tracker database. The database
                         is the source of truth, so neither side is worth
                         reading: regenerate the file with `bd export`.
  `CHANGELOG.md`         An append-only section conflicts whenever the default
                         branch gains an entry first. Both entries are correct.
                         Keep both, with the default branch's side first so that
                         two runs of this script produce the same bytes.

ANY OTHER CONFLICTED PATH RESOLVES NOTHING AT ALL. A source conflict belongs to
whoever wrote the branch. When the conflicted set holds even one path outside
the two above, this script touches no file, names every conflicted path, and
leaves the rebase exactly as it found it so the caller can abort cleanly.

THE VERIFICATIONS THE PROSE USED TO CARRY ARE NOW STRUCTURAL.

  * "Both sides must survive" in `CHANGELOG.md` is true by construction here,
    because the hunk parser concatenates the two sides rather than choosing.
  * "Do not rewrite the marker check as `grep -c`" was a real trap: `grep -c`
    exits 1 when it counts zero, so the cleanest possible file stopped the run.
    Counting in Python has no exit code to misread.
  * The tracker export is parsed as JSON line by line before it is staged,
    because a truncated export is a file that looks fine and imports nothing.

WHICH SIDE IS THE DEFAULT BRANCH'S. During `git rebase <upstream>`, git replays
the branch's commits onto the upstream, so "ours" is the upstream and "theirs"
is the branch commit being replayed. The `<<<<<<<` side is therefore the default
branch's, which is the side that goes first. This script is for that rebase and
says so; a `git merge` conflict has the two sides the other way round.

Exit status: 0 when the conflicted set is now empty (or was empty to begin
with), 1 when the caller must stop (`stop` names the skill's slug: `conflict`
for a path this script will not touch, `tracker` for an export that could not be
regenerated or verified), 2 on operator error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TRACKER_EXPORT = ".beads/issues.jsonl"
CHANGELOG = "CHANGELOG.md"
RESOLVABLE = (TRACKER_EXPORT, CHANGELOG)

OURS_MARKER = "<<<<<<<"
SPLIT_MARKER = "======="
THEIRS_MARKER = ">>>>>>>"
BASE_MARKER = "|||||||"

EXIT_RESOLVED = 0
EXIT_STOP = 1
EXIT_OPERATOR_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    try:
        outcome = resolve_conflicts(args.repo_root)
    except GitError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    print(json.dumps(outcome, indent=2, sort_keys=True))
    return EXIT_STOP if outcome["stop"] else EXIT_RESOLVED


def resolve_conflicts(repo_root: Path) -> dict:
    """Resolve what is mechanical, or refuse the whole set and change nothing."""
    conflicted = conflicted_paths(repo_root)
    outcome = {"conflicted": conflicted, "resolved": [], "stop": None, "detail": None}
    if not conflicted:
        outcome["detail"] = "no conflicted paths"
        return outcome

    refused = [path for path in conflicted if path not in RESOLVABLE]
    if refused:
        outcome["stop"] = "conflict"
        outcome["detail"] = (
            "resolved nothing; these paths need the person who wrote the branch: "
            + ", ".join(refused)
        )
        return outcome

    for path in conflicted:
        resolver = resolve_tracker_export if path == TRACKER_EXPORT else resolve_changelog
        failure = resolver(repo_root, repo_root / path)
        if failure:
            outcome["stop"], outcome["detail"] = failure
            return outcome
        run_git(repo_root, "add", "--", path)
        outcome["resolved"].append(path)

    remaining = conflicted_paths(repo_root)
    if remaining:
        outcome["stop"] = "conflict"
        outcome["detail"] = "still conflicted after resolving: " + ", ".join(remaining)
    return outcome


def resolve_tracker_export(repo_root: Path, path: Path) -> tuple[str, str] | None:
    """Overwrite the conflicted export from the database, then prove it imports.

    No `git checkout --ours` first: `bd export` truncates and rewrites the whole
    file, so picking a side only to discard it is a step with no effect.
    """
    exported = run_bd(repo_root, "export", "-o", TRACKER_EXPORT)
    if exported is not None:
        return ("tracker", f"bd export failed: {exported}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return ("tracker", f"the export is unreadable after bd export: {error}")

    markers = marker_lines(text)
    if markers:
        return ("tracker", f"conflict markers survived bd export at lines {markers}")

    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError as error:
            return ("tracker", f"{TRACKER_EXPORT} line {number} is not JSON: {error}")
    return None


def resolve_changelog(repo_root: Path, path: Path) -> tuple[str, str] | None:
    """Keep both sides of every conflict hunk, the default branch's side first."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return ("conflict", f"{CHANGELOG} is unreadable: {error}")

    merged, hunks, unterminated = keep_both_sides(text)
    if unterminated:
        return ("conflict", f"{CHANGELOG} holds a conflict hunk with no closing marker")
    if hunks == 0:
        return ("conflict", f"{CHANGELOG} is staged as conflicted but holds no hunk")

    markers = marker_lines(merged)
    if markers:
        return ("conflict", f"conflict markers survived the merge at lines {markers}")

    path.write_text(merged, encoding="utf-8")
    return None


def keep_both_sides(text: str) -> tuple[str, int, bool]:
    """(the merged text, how many hunks closed, whether one never closed).

    Concatenate each hunk's two sides, ours first, dropping the marker lines. A
    diff3-style hunk also carries a `|||||||` base section between the two sides.
    That section is the common ancestor rather than an entry either side wrote,
    so it is dropped; keeping it would resurrect deleted text.

    THE UNTERMINATED FLAG IS THE DATA-LOSS GUARD. A hunk's lines are held aside
    until its `>>>>>>>` arrives, and only then joined onto the output. A hunk
    that never closes therefore contributes nothing, and its `<<<<<<<` was
    consumed, so the marker check downstream sees a clean file and the caller
    writes content that silently lost both sides. One closed hunk earlier in the
    file is enough to get past the `hunks == 0` test, which is what makes this
    reachable rather than theoretical.
    """
    kept: list[str] = []
    ours: list[str] = []
    theirs: list[str] = []
    section = "outside"
    hunks = 0

    for line in text.splitlines(keepends=True):
        marker = line.split(" ", 1)[0].rstrip("\r\n")
        if marker == OURS_MARKER:
            section, ours, theirs = "ours", [], []
        elif marker == BASE_MARKER and section in {"ours", "base"}:
            section = "base"
        elif line.rstrip("\r\n") == SPLIT_MARKER and section in {"ours", "base"}:
            section = "theirs"
        elif marker == THEIRS_MARKER and section == "theirs":
            kept.extend(ours)
            kept.extend(theirs)
            section = "outside"
            hunks += 1
        elif section == "ours":
            ours.append(line)
        elif section == "theirs":
            theirs.append(line)
        elif section == "base":
            continue
        else:
            kept.append(line)

    return "".join(kept), hunks, section != "outside"


def marker_lines(text: str) -> list[int]:
    """The 1-indexed lines holding a conflict marker, counted rather than grepped.

    `grep -c` exits 1 when it counts zero, so a clean file read as a failure.
    """
    return [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if line.startswith((OURS_MARKER, SPLIT_MARKER, THEIRS_MARKER, BASE_MARKER))
    ]


def conflicted_paths(repo_root: Path) -> list[str]:
    stdout = run_git(repo_root, "diff", "--name-only", "--diff-filter=U")
    return sorted({line for line in stdout.splitlines() if line})


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


def run_bd(repo_root: Path, *arguments: str) -> str | None:
    """None when `bd` succeeded, otherwise the reason it did not.

    A missing `bd` is reported rather than raised, because the caller's answer to
    both is the same: stop with `tracker` and let a person look.
    """
    try:
        completed = subprocess.run(
            ["bd", *arguments],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "bd is not on PATH"
    if completed.returncode != 0:
        return completed.stderr.strip() or f"exit {completed.returncode}"
    return None


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a rebase's tracker-export and changelog conflicts, as JSON.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="the repository whose rebase is stopped; defaults to the working directory",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
