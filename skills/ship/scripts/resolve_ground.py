#!/usr/bin/env python3
"""Answer Step 1 of the ship skill in one JSON object: is this repository fit to
ship from, and what are the names the rest of the run needs.

Six questions, all deterministic, each of which the skill used to spend a
paragraph telling the reader how to ask correctly:

  * Is this a git repository, and where is its common directory?
  * What is the default branch, and does an origin exist?
  * What branch is HEAD on, and is HEAD detached?
  * Which tracked files changed, and which files are merely untracked?
  * Is a rebase, merge, or cherry-pick already in progress?
  * Which worktree holds which branch?

And one that is not a question about git at all: which tokens in the branch name
could be a bead id. The script only proposes them; `bd show` is what decides,
and the skill says outright never to trust the shape alone.

THE IN-PROGRESS CHECK IS A PATH TEST, NEVER AN EXIT CODE. `git rev-parse
--git-path rebase-merge` exits 0 in every clean repository, because the question
it answers is "where would that live", not "is it there". Reading its exit code
reports a rebase in progress everywhere. The test is whether the path exists.

AN UNTRACKED FILE DOES NOT STOP THE RUN. A CHANGED TRACKED FILE DOES. `git
rebase` refuses to start with a modified tracked file, so that is a real stop.
An untracked file is usually build output, and a gate that writes one is normal,
so refusing over it would make the ship skill unusable in those repositories.
Both lists are reported; only one sets `stop`.

A STATUS THAT COULD NOT BE READ IS NOT A CLEAN TREE. `git status` fails on a
corrupt index, and reading that failure as "no changed files" would let a
mutation run over work nobody could see. It is its own stop,
`status-unreadable`, and `mutation_guard` asks the same question for every later
boundary that is about to change the repository.

THE STOP CONDITIONS ARE ORDERED, and the first one found is the one named, so a
report never has to choose between two true answers. In order: no repository, no
resolvable default branch, an operation already in progress, HEAD already on the
default branch, a detached HEAD, an unreadable status, a changed tracked file.

AN OPERATION IN PROGRESS OUTRANKS THE TWO CONDITIONS IT CAUSES. A rebase stopped
on a conflict detaches HEAD and leaves the conflicted file modified, so both
`detached-head` and `dirty-tracked` are also true of it. Naming either one sends
the operator to a symptom. The skill's prose listed the five conditions in the
order a reader thinks of them, which put `detached-head` first and made
`operation-in-progress` unreachable in the only state that produces it.

`no-default-branch` is the one condition the prose never covered. A repository
with no `origin/HEAD`, no `main`, and no `master` has nothing to ship onto, and
guessing there would land work on whatever branch happened to sort first.

Exit status: 0 when the repository is fit to ship from, 1 when a stop condition
was found (`stop` names it, and the rest of the object is still filled in as far
as it could be read), 2 on operator error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

EXIT_FIT = 0
EXIT_STOP = 1
EXIT_OPERATOR_ERROR = 2

# Where git records an operation that is already running. Each is a path under
# the git directory; its existence is the answer. See the module docstring.
IN_PROGRESS_PATHS = ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD")

# A single branch-name segment that is a git convention rather than a bead id.
# Only an exact match is dropped: `fix-the-retry-budget` is a slug, not a type.
BRANCH_TYPE_WORDS = frozenset([
    "outrigger", "feat", "feature", "fix", "bug", "bugfix", "chore", "docs", "doc",
    "refactor", "test", "tests", "ci", "build", "perf", "style", "revert", "hotfix",
    "release", "wip", "main", "master", "dev", "develop",
])

# Enough candidates to cover a long hyphenated slug, few enough that verifying
# them is a handful of `bd show` calls rather than a scan of the tracker.
MAX_BEAD_CANDIDATES = 25


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    try:
        ground = resolve_ground(args.directory)
    except GitError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    print(json.dumps(ground, indent=2, sort_keys=True))
    return EXIT_STOP if ground["stop"] else EXIT_FIT


def resolve_ground(directory: Path) -> dict:
    """Read every fact Step 1 needs, and name the first stop condition found."""
    ground = blank_ground()

    toplevel = read_git(directory, "rev-parse", "--show-toplevel")
    if toplevel is None:
        ground["stop"] = "no-repository"
        return ground
    ground["repo_root"] = toplevel
    root = Path(toplevel)

    ground["git_common_dir"] = absolute_git_path(root, "rev-parse", "--git-common-dir")
    ground["git_dir"] = absolute_git_path(root, "rev-parse", "--git-dir")
    ground["is_linked_worktree"] = ground["git_dir"] != ground["git_common_dir"]
    ground["origin_url"] = read_git(root, "remote", "get-url", "origin")
    ground["has_origin"] = ground["origin_url"] is not None
    ground["worktrees"] = read_worktrees(root)

    tracked = read_status(root, untracked=False)
    untracked = read_status(root, untracked=True, only_untracked=True)
    ground["status_unreadable"] = tracked is None or untracked is None
    ground["dirty_tracked"] = tracked or []
    ground["untracked"] = untracked or []
    ground["in_progress"] = first_in_progress_operation(root, ground["git_dir"])

    branch = read_git(root, "branch", "--show-current")
    ground["branch"] = branch or None
    ground["bead_candidates"] = bead_candidates(branch or "")

    default_branch, source = resolve_default_branch(root)
    ground["default_branch"] = default_branch
    ground["default_branch_source"] = source
    ground["default_branch_worktree"] = worktree_holding(ground["worktrees"], default_branch)

    ground["stop"] = first_stop_condition(ground)
    return ground


def first_stop_condition(ground: dict) -> str | None:
    """The first condition that makes this repository unfit to ship from.

    The order is the report's contract, not an implementation detail. See the
    module docstring for why an operation in progress is named before the
    detached HEAD and the modified file it causes.
    """
    if ground["default_branch"] is None:
        return "no-default-branch"
    if ground["in_progress"]:
        return "operation-in-progress"
    if ground["branch"] == ground["default_branch"]:
        return "on-default-branch"
    if ground["branch"] is None:
        return "detached-head"
    if ground["status_unreadable"]:
        return "status-unreadable"
    if ground["dirty_tracked"]:
        return "dirty-tracked"
    return None


def mutation_guard(directory: Path) -> str | None:
    """The stop that forbids changing this checkout now, or None when it may change.

    Every boundary that is about to mutate asks this, so each one applies the
    same rule: untracked files never block, changed tracked files do, and a
    status that could not be read blocks as well.
    """
    tracked = read_status(directory, untracked=False)
    if tracked is None:
        return "status-unreadable"
    if tracked:
        return "dirty-tracked"
    return None


def blank_ground() -> dict:
    return {
        "stop": None,
        "repo_root": None,
        "git_dir": None,
        "git_common_dir": None,
        "is_linked_worktree": False,
        "branch": None,
        "default_branch": None,
        "default_branch_source": None,
        "default_branch_worktree": None,
        "has_origin": False,
        "origin_url": None,
        "status_unreadable": False,
        "dirty_tracked": [],
        "untracked": [],
        "in_progress": None,
        "worktrees": [],
        "bead_candidates": [],
    }


def resolve_default_branch(root: Path) -> tuple[str | None, str | None]:
    """origin/HEAD, then a local main, then a local master. Never a guess."""
    symbolic = read_git(root, "symbolic-ref", "refs/remotes/origin/HEAD")
    if symbolic and symbolic.startswith("refs/remotes/origin/"):
        return symbolic[len("refs/remotes/origin/") :], "origin/HEAD"
    for candidate in ("main", "master"):
        if read_git(root, "rev-parse", "--verify", f"refs/heads/{candidate}") is not None:
            return candidate, f"local {candidate}"
    return None, None


def first_in_progress_operation(root: Path, git_dir: str | None) -> str | None:
    """The first operation git has state on disk for, or None.

    `git_dir` is a string or None rather than a Path, because `--git-dir` can
    fail and `Path(None)` raises a TypeError that no caller here catches. A
    crash where the answer is "I could not tell" is the worst of both.
    """
    fallback = Path(git_dir) if git_dir else Path(root) / ".git"
    for name in IN_PROGRESS_PATHS:
        located = read_git(root, "rev-parse", "--git-path", name)
        path = Path(located) if located else fallback / name
        if not path.is_absolute():
            path = root / path
        if path.exists():
            return name
    return None


def read_worktrees(root: Path) -> list[dict]:
    """Parse `git worktree list --porcelain` into one record per worktree."""
    stdout = read_git(root, "worktree", "list", "--porcelain") or ""
    worktrees: list[dict] = []
    current: dict | None = None
    for line in stdout.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[len("worktree ") :], "branch": None, "detached": False,
                       "bare": False}
            worktrees.append(current)
        elif current is None:
            continue
        elif line.startswith("branch refs/heads/"):
            current["branch"] = line[len("branch refs/heads/") :]
        elif line == "detached":
            current["detached"] = True
        elif line == "bare":
            current["bare"] = True
    return worktrees


def worktree_holding(worktrees: list[dict], branch: str | None) -> str | None:
    if branch is None:
        return None
    for worktree in worktrees:
        if worktree["branch"] == branch:
            return worktree["path"]
    return None


def read_status(root: Path, *, untracked: bool, only_untracked: bool = False) -> list[str] | None:
    """Paths from `git status --porcelain -z`, split on NUL rather than on space,
    or None when git could not report a status at all.

    A rename emits its original path as a second NUL-separated field, which a
    line-oriented parser reads as a second changed file. Only the new path is
    kept, because that is the path a later command has to act on.
    """
    mode = "all" if untracked else "no"
    stdout = read_git_raw(root, "status", "--porcelain=v1", "-z", f"--untracked-files={mode}")
    if stdout is None:
        return None
    fields = stdout.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if code[0] in "RC":
            index += 1  # skip the original path that follows a rename or copy
        if only_untracked and code != "??":
            continue
        if not only_untracked and code == "??":
            continue
        paths.append(path)
    return sorted(paths)


def bead_candidates(branch: str) -> list[str]:
    """Tokens in a branch name that could be a bead id, best guess first.

    `outrigger/<short-id>/<slug>` puts the id in the second segment, and that id
    is the SHORTEST candidate the name yields, so it goes first by rule rather
    than by length. Everything after it is longest first, because a long id
    contains shorter accidental matches and the long one is the real bead.

    This proposes; it never decides. `bd show` is the filter, and a candidate
    that is not a bead costs one failed lookup.
    """
    segments = [segment for segment in branch.split("/") if segment]
    if not segments:
        return []

    ordered: list[str] = []
    if len(segments) >= 3 and segments[0] == "outrigger":
        ordered.append(segments[1])

    anchored: set[str] = set()
    interior: set[str] = set()
    for segment in segments:
        segment_anchored, segment_interior = hyphen_runs(segment)
        anchored |= segment_anchored
        interior |= segment_interior

    for group in (anchored, interior - anchored):
        group -= set(ordered)
        group -= {word for word in group if word.lower() in BRANCH_TYPE_WORDS}
        ordered.extend(sorted(group, key=lambda run: (-len(run), run)))
    return ordered[:MAX_BEAD_CANDIDATES]


def hyphen_runs(segment: str) -> tuple[set[str], set[str]]:
    """(runs anchored to an end of the segment, runs floating inside it).

    `tadw-0fo-exclude` yields `tadw`, `tadw-0fo`, and the whole segment as
    prefixes, plus `exclude` and `0fo-exclude` as suffixes; `0fo` alone floats.
    One of them is the bead id whether the slug was appended to it or prepended.

    THE SPLIT IS WHAT KEEPS THE CAP FROM LOSING THE ID. A segment of n tokens has
    n(n+1)/2 runs but only 2n-1 anchored ones, so a nine-token branch name yields
    45 runs against a cap of 25. Ranked by length alone, `tadw-0fo` sits below
    thirty longer interior runs like `exclude-the-beads-directory` and falls off
    the end, the lookup finds no bead, and the ship goes bead-free and leaves the
    bead open. An interior run is never a tracker id, so it is the right thing to
    drop.
    """
    tokens = [token for token in segment.split("-") if token]
    anchored: set[str] = set()
    interior: set[str] = set()
    for start in range(len(tokens)):
        for end in range(start + 1, len(tokens) + 1):
            run = "-".join(tokens[start:end])
            at_an_end = start == 0 or end == len(tokens)
            (anchored if at_an_end else interior).add(run)
    return anchored, interior


def absolute_git_path(root: Path, *arguments: str) -> str | None:
    """A git directory path, always absolute and always symlink-resolved.

    `--git-dir` answers `.git` in an ordinary checkout and an absolute path in a
    linked worktree, and a worktree under `/tmp` on macOS answers to
    `/private/tmp` through one of the two. Resolving both sides is what lets
    `is_linked_worktree` compare them.
    """
    located = read_git(root, *arguments)
    if located is None:
        return None
    path = Path(located)
    return str((path if path.is_absolute() else root / path).resolve())


class GitError(RuntimeError):
    """git could not be run at all."""


def read_git(directory: Path, *arguments: str) -> str | None:
    """The command's stdout with surrounding whitespace removed, or None when it
    exited non-zero. A non-zero exit here is an answer, not a failure: it is how
    git says a ref does not exist or a remote is not configured."""
    stdout = read_git_raw(directory, *arguments)
    return None if stdout is None else stdout.strip()


def read_git_raw(directory: Path, *arguments: str) -> str | None:
    """The command's stdout verbatim, for output whose separator is NUL."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise GitError("git is not on PATH") from error
    return None if completed.returncode != 0 else completed.stdout


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report whether a repository is fit to ship from, as JSON.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path.cwd(),
        help="where to look for the repository; defaults to the working directory",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
