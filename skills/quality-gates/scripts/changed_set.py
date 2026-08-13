#!/usr/bin/env python3
"""Print every path the quality gates should look at, one per line.

This is Step 2 of the quality-gates skill. It exists as a script because the
prose version was two git commands plus a base-resolution fallback that the model
retyped on every run, and getting it wrong narrows every gate in silence. Gate 5
already proved that failure mode: its prose version reported 194 misses on a
repository with no broken links.

The stakeholder is anyone reading a scoped report that quietly covered nothing.

THE TRAP THIS SCRIPT CLOSES. `git diff "$BASE"...HEAD` stops at the last commit,
and this skill runs before a commit more often than after one, so the very work
being checked drops out of scope. The diff here is `git diff "$BASE"`, with no
`...HEAD`, which compares the base against the WORKING TREE: committed, staged,
and unstaged changes all land in the set. Untracked files need the second
command, because `git diff` never sees them.

EXIT 3 IS THE POINT. An unresolvable base and an empty diff are different
answers, and the prose conflated them. Exit 3 says "the base will not resolve,
run at --all"; exit 0 with no output says "the base resolved and nothing
changed". Treating the first as the second narrows every gate to nothing while
reporting confidently. Exit 2 is operator error, which is neither.

STDOUT IS PATHS AND NOTHING ELSE. The resolved base SHA, the ref it came from,
the count, and any skipped path all go to stderr, so a caller can pipe stdout
without filtering it first.

Deletions appear, because `git diff --name-only` reports them and a caller
deciding what to check needs to know a file left the tree. A path that cannot
sit on one line, because its name contains a newline, is named on stderr and
left out of stdout: emitting it would split one file into two bogus paths for
every downstream reader.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# The default branch of the remote, as git records it. Resolved rather than
# assumed, because a repository whose default branch is `master` or `trunk`
# answers here and would fail against a hardcoded name.
ORIGIN_HEAD = "refs/remotes/origin/HEAD"

# Used when `origin/HEAD` is absent, which is ordinary: a repository set up with
# `git remote add` plus `git fetch` never gets that symbolic ref.
FALLBACK_BASE_REF = "origin/main"

EXIT_OK = 0
EXIT_OPERATOR_ERROR = 2
EXIT_BASE_UNRESOLVED = 3


class GitUnavailable(Exception):
    """git could not be run, so the changed set is unknown.

    Raised rather than swallowed. An empty path list is indistinguishable from a
    clean tree, and printing nothing at exit 0 is the one outcome this script
    must never produce.
    """


class BaseUnresolved(Exception):
    """No candidate ref produced a merge base with HEAD.

    Its own exception, and its own exit status, because the caller's next move
    differs: fall back to a whole-repository run rather than trust an empty set.
    """


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # git absent from PATH, or not executable
        raise GitUnavailable(f"could not run git: {exc}") from exc


def git_paths(root: Path, *args: str) -> list[str]:
    """Run one path-listing git command and return its paths.

    `-z` because a path may contain a newline, and git would otherwise quote it
    into a shape no reader parses back.
    """
    result = git(root, *args, "-z")
    if result.returncode != 0:
        raise GitUnavailable(
            f"git {args[0]} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return [entry for entry in result.stdout.split("\0") if entry]


def base_candidates(root: Path) -> list[str]:
    """The refs to try as the base, in order, deduplicated.

    `origin/HEAD` first because it names the remote's actual default branch.
    `origin/main` second, per the skill's prose, for the common repository that
    has a remote but no symbolic ref for its head.
    """
    result = git(root, "symbolic-ref", "--quiet", "--short", ORIGIN_HEAD)
    resolved = result.stdout.strip() if result.returncode == 0 else ""
    candidates = [ref for ref in (resolved, FALLBACK_BASE_REF) if ref]
    return list(dict.fromkeys(candidates))


def resolve_base(root: Path) -> tuple[str, str]:
    """Return the base SHA and the ref it came from.

    Raises BaseUnresolved when no candidate works, which covers a repository with
    no remote, an unfetched remote, a shallow clone with no shared history, and
    an unborn HEAD.
    """
    candidates = base_candidates(root)
    for ref in candidates:
        result = git(root, "merge-base", "HEAD", ref)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), ref
    raise BaseUnresolved("no merge base with " + " or ".join(candidates))


def changed_set(root: Path, base: str) -> tuple[list[str], list[str]]:
    """Return the changed paths, plus the paths that cannot be printed.

    The diff carries committed, staged, and unstaged changes; `ls-files --others`
    carries new files. `--exclude-standard` keeps ignored files out, so build
    output and local scratch files do not widen the scope of every gate.
    """
    tracked = git_paths(root, "diff", "--name-only", base)
    untracked = git_paths(root, "ls-files", "--others", "--exclude-standard")
    paths = sorted(set(tracked) | set(untracked))
    printable = [path for path in paths if "\n" not in path]
    unprintable = [path for path in paths if "\n" in path]
    return printable, unprintable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    if not (root / ".git").exists():
        print(f"ERROR: {root} is not a git repository", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    try:
        base, ref = resolve_base(root)
        paths, unprintable = changed_set(root, base)
    except BaseUnresolved as exc:
        print(f"ERROR: {exc}; run the gates at --all", file=sys.stderr)
        return EXIT_BASE_UNRESOLVED
    except GitUnavailable as exc:
        # Exit 2, never 3. Exit 3 tells the caller to widen the scope, and a
        # machine without git has not earned that instruction.
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    print(f"base: {base} (merge-base of HEAD and {ref})", file=sys.stderr)
    for path in paths:
        print(path)

    # Named, never dropped in silence. A caller that narrowed its gates to this
    # list needs to see what the list could not carry.
    for path in unprintable:
        print(
            f"WARNING: omitted a path whose name contains a newline: {path!r}",
            file=sys.stderr,
        )
    print(f"{len(paths)} changed paths", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
