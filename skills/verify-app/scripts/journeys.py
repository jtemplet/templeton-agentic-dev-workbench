#!/usr/bin/env python3
"""Name the journeys a changed set needs, and fingerprint each one's source files.

A journey is one path through the app that `verify-app` drives, described by the drive
block of a leaf document under `docs/products/`. A leaf document needs a journey run
when its `source_refs` frontmatter names a file in the changed set. This script makes
that match a command, so two runs on one tree always give one answer.

The fingerprint is how a saved journey result is judged fresh. A commit hash is never
compared (`docs/ship-gate-contract.md`), because two trees at one commit can differ.
The fingerprint of a journey is the sha256 of these lines, sorted and joined by newlines:

    <path> <sha256 of the file's bytes>

with one line per file its `source_refs` name. A directory ref contributes one line per
file below it. A ref that names nothing on disk contributes `<ref> absent`. So the
fingerprint changes when one of the journey's files changes, and at no other time.

This script is the one place that rule lives. The report writers read its output and
never compute a fingerprint themselves.

It runs no git, per ADR 0011 rule 4: the caller passes the changed set as a file with
one repository-relative path per line.

Output, one JSON object on stdout:

    {
      "journeys": [
        {"name": "deals", "doc": "docs/products/web/deals.md",
         "source_refs": ["ui/src/views/Deals.vue"], "fingerprint": "<64 hex>"}
      ],
      "uncovered": ["server/jobs/export.py"]
    }

Usage:
  python3 journeys.py --changed-files PATH [--docs-root DIR] [--repo-root DIR]

Exit status:
  0  the object was printed, including when no journey matched
  2  operator error: the changed-files list, the repository root, or a docs root named
     on the command line does not exist

No third-party dependencies.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

PRODUCT_DOCS_SCRIPTS = Path(__file__).resolve().parents[2] / "product-surface-docs" / "scripts"


# The frontmatter parser and the leaf rule live beside the product-surface-docs checks.
# Loading them by path keeps one definition of each without putting that directory on
# sys.path, where its modules could shadow ours.
def load_product_docs_module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, PRODUCT_DOCS_SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_drive_blocks = load_product_docs_module("check_drive_blocks")
check_staleness = load_product_docs_module("check_staleness")

EXIT_OPERATOR_ERROR = 2
DEFAULT_DOCS_ROOT = "docs/products"


def needed_journeys(changed: list[str], docs_root: Path, repo_root: Path) -> dict:
    """The journeys the changed set needs, and the changed files no journey covers."""
    leaves = leaf_refs(docs_root)
    journeys = [
        describe_journey(doc, refs, repo_root)
        for doc, refs in leaves
        if any(covers(ref, path) for ref in refs for path in changed)
    ]
    all_refs = [ref for _, refs in leaves for ref in refs]
    uncovered = [path for path in changed if not any(covers(ref, path) for ref in all_refs)]
    return {"journeys": journeys, "uncovered": uncovered}


def leaf_refs(docs_root: Path) -> list[tuple[Path, list[str]]]:
    """Each leaf document with its in-repository source_refs, in path order."""
    if not docs_root.is_dir():
        return []
    docs = check_drive_blocks.collect_docs(docs_root)
    return [(doc, in_repo_refs(doc)) for doc in docs if check_drive_blocks.is_leaf(doc, docs)]


def in_repo_refs(doc: Path) -> list[str]:
    """The string-form source_refs. A mapping-form ref names another repository."""
    frontmatter = check_staleness.parse_frontmatter(
        doc.read_text(encoding="utf-8", errors="replace")
    )
    refs = frontmatter.get("source_refs", [])
    return [ref.rstrip("/") for ref in refs if isinstance(ref, str) and ref.strip("/")]


def covers(ref: str, path: str) -> bool:
    """True when the ref names the path itself, or a directory above it."""
    return path == ref or path.startswith(ref + "/")


def describe_journey(doc: Path, refs: list[str], repo_root: Path) -> dict:
    return {
        "name": doc.stem,
        "doc": display_path(doc, repo_root),
        "source_refs": refs,
        "fingerprint": fingerprint(refs, repo_root),
    }


def fingerprint(refs: list[str], repo_root: Path) -> str:
    """The sha256 over the sorted `<path> <file sha256>` lines of every file the refs name."""
    lines = sorted(line for ref in refs for line in ref_lines(ref, repo_root))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def ref_lines(ref: str, repo_root: Path) -> list[str]:
    target = repo_root / ref
    if target.is_file():
        return [f"{ref} {file_sha256(target)}"]
    if target.is_dir():
        files = sorted(path for path in target.rglob("*") if path.is_file())
        return [f"{path.relative_to(repo_root).as_posix()} {file_sha256(path)}" for path in files]
    return [f"{ref} absent"]


# Two journeys can name one file, so each file is read once per run.
@functools.cache
def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(doc: Path, repo_root: Path) -> str:
    try:
        return doc.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(doc)


def read_changed(path: Path) -> list[str]:
    """One repository-relative path per line. Blank lines and repeats are dropped."""
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return list(dict.fromkeys(line for line in lines if line))


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    docs_root = resolve_docs_root(args.docs_root, args.repo_root)
    problem = input_problem(args, docs_root)
    if problem:
        return operator_error(problem)
    result = needed_journeys(read_changed(args.changed_files), docs_root, args.repo_root)
    print(json.dumps(result, indent=2))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--changed-files", required=True, type=Path, help="One path per line")
    parser.add_argument("--docs-root", type=Path, help=f"Default: {DEFAULT_DOCS_ROOT}")
    parser.add_argument("--repo-root", default=".", type=Path, help="Repository root")
    return parser.parse_args(argv)


def input_problem(args: argparse.Namespace, docs_root: Path) -> str | None:
    """Why the inputs cannot be used, or None. An absent default docs root is no problem."""
    if not args.repo_root.is_dir():
        return f"--repo-root {args.repo_root} is not a directory"
    if not args.changed_files.is_file():
        return f"--changed-files {args.changed_files} does not exist"
    if args.docs_root is not None and not docs_root.is_dir():
        return f"--docs-root {docs_root} is not a directory"
    return None


def resolve_docs_root(named: Path | None, repo_root: Path) -> Path:
    """A relative docs root is read from the repository root; an absolute one stands alone."""
    return repo_root / (named or DEFAULT_DOCS_ROOT)


def operator_error(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return EXIT_OPERATOR_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
