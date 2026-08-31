#!/usr/bin/env python3
"""Run every bd command a document puts in a fenced block, and report the ones bd rejects.

A skill can document a bd command that bd rejects, and nothing notices. An agent
following the skill hits the error mid-run and has no documented recovery. That
happened twice before this script existed: tadw-pdi fixed three such commands in
skills/triage-beads/SKILL.md, and both times a person found them by reading.
This is check_doc_paths.py's job done for commands instead of paths.

Three rules keep the signal usable, and each one is measured, not assumed:

  1. FENCED BLOCKS ONLY. Measured on 2026-08-31: fenced plus inline backticks
     produced 29 candidates and 3 failures, all three prose fragments rather
     than commands (`bd show`, `bd list --status`, `bd search`). Fenced blocks
     alone produced 17 candidates and 0 failures. A command in a fenced block
     is meant to be run; a name in backticks is prose.
  2. SKIP WHAT CANNOT RUN VERBATIM. A placeholder (`<id>`, `{id}`, `$VAR`,
     `$(...)`), a pipe, a line continuation, or an unbalanced quote makes a
     line an illustration. The skipped count is reported, so a reader can see
     what was not checked.
  3. RUN ONLY A READ-ONLY SAFELIST: list, show, ready, blocked, stats, search,
     epic, prime, where, doctor. The commands run against the real tracker, so
     a write here would make a check that mutates what it checks. A verb off
     the safelist is counted as skipped, never run.

A missing `bd` warns by name and exits 0, matching the pre-push hook's policy
for a missing tool: CI has no bd and no tracker database, and blocking there
would refuse every push from CI.

Exit status: 0 when every extracted command exits 0 (or nothing could be
verified), 1 when at least one failed, 2 on operator error. The failure exit is
mapped to FAIL rather than WARN by the caller, because a documented command
that errors stops an agent's run.
"""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FENCE = re.compile(r"^\s*```")
PROMPT_PREFIX = "$ "

# Verbs that read the tracker and change nothing. Everything else is skipped:
# create, update, close, delete, import, export, and dolt all mutate state.
SAFE_VERBS = frozenset(
    ("list", "show", "ready", "blocked", "stats", "search", "epic", "prime", "where", "doctor")
)

# A line carrying any of these cannot run verbatim: `<` and `{` open
# placeholders, `$` opens a variable or a substitution, `|` is a pipe.
UNRUNNABLE_CHARS = frozenset("<{$|")

# Directories whose markdown describes other machines or is not this
# repository's to fix.
EXCLUDED_DIRS = frozenset((".git", "node_modules", ".worktrees"))

TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Candidate:
    """One runnable bd command, with every fenced line that documents it."""

    argv: tuple[str, ...]
    locations: tuple[str, ...]


@dataclass(frozen=True)
class Failure:
    """One documented command that bd rejected."""

    location: str
    command: str
    error: str

    def __str__(self) -> str:
        return f"{self.location}\n  $ {self.command}\n  {self.error}"


def markdown_files(root: Path) -> list[Path]:
    """Every markdown file in the tree, one per real file.

    Deduplicated by resolved path because CLAUDE.md here is a symlink to
    AGENTS.md, and running the same block twice would double every count.
    """
    seen: set[Path] = set()
    files: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if EXCLUDED_DIRS & set(path.relative_to(root).parts):
            continue
        real = path.resolve()
        if real in seen:
            continue
        seen.add(real)
        files.append(path)
    return files


def runnable_argv(line: str) -> tuple[str, ...] | None:
    """The argv for a fenced line that is a verbatim, read-only bd command.

    None means the line is not such a command: not bd at all, carrying a
    placeholder or pipe, a continuation, an unbalanced quote, or a verb off
    the safelist. The caller counts those as skipped when they do start with
    `bd`, because a reader deserves to know what was not checked.
    """
    text = line.strip()
    if text.startswith(PROMPT_PREFIX):
        text = text[len(PROMPT_PREFIX) :]
    if not (text == "bd" or text.startswith("bd ")):
        return None
    if UNRUNNABLE_CHARS & set(text) or text.endswith("\\"):
        return None
    try:
        # comments=True strips a trailing `# explanation`, which the doc blocks
        # here carry on most lines.
        argv = shlex.split(text, comments=True)
    except ValueError:
        return None
    if len(argv) < 2 or argv[1] not in SAFE_VERBS:
        return None
    return tuple(argv)


def is_bd_line(line: str) -> bool:
    text = line.strip()
    if text.startswith(PROMPT_PREFIX):
        text = text[len(PROMPT_PREFIX) :]
    return text == "bd" or text.startswith("bd ")


def extract(root: Path, docs: list[Path]) -> tuple[list[Candidate], int]:
    """(runnable candidates, skipped line count) across every document.

    A command documented in several places runs once and is reported for each
    place, so a shared mistake costs one execution and names every copy.
    """
    by_argv: dict[tuple[str, ...], list[str]] = {}
    skipped = 0
    for doc in docs:
        label = doc.relative_to(root).as_posix()
        fenced = False
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if not fenced or not is_bd_line(line):
                continue
            argv = runnable_argv(line)
            if argv is None:
                skipped += 1
                continue
            by_argv.setdefault(argv, []).append(f"{label}:{lineno}")
    candidates = [
        Candidate(argv, tuple(locations)) for argv, locations in by_argv.items()
    ]
    return candidates, skipped


def first_error_line(result: subprocess.CompletedProcess[str]) -> str:
    for stream in (result.stderr, result.stdout):
        for line in stream.splitlines():
            if line.strip():
                return line.strip()
    return f"(no output, exit {result.returncode})"


def run_all(root: Path, candidates: list[Candidate]) -> list[Failure]:
    failures: list[Failure] = []
    for candidate in candidates:
        command = " ".join(candidate.argv)
        try:
            result = subprocess.run(
                candidate.argv,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            failures.extend(
                Failure(loc, command, f"timed out after {TIMEOUT_SECONDS}s")
                for loc in candidate.locations
            )
            continue
        if result.returncode != 0:
            error = first_error_line(result)
            failures.extend(
                Failure(loc, command, error) for loc in candidate.locations
            )
    return failures


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
        return 2

    docs = resolve_docs(root, args.docs)
    missing = [d for d in docs if not d.is_file()]
    if missing:
        for doc in missing:
            print(f"ERROR: no such document: {doc}", file=sys.stderr)
        return 2

    candidates, skipped = extract(root, docs)
    if not candidates:
        print(f"OK: no runnable bd commands documented ({skipped} lines skipped)")
        return 0

    if shutil.which("bd") is None:
        print(
            "WARNING: bd is not on PATH, so no documented command was verified",
            file=sys.stderr,
        )
        return 0

    failures = run_all(root, candidates)
    for failure in failures:
        print(failure)

    total = len(candidates)
    if failures:
        print(f"\n{len(failures)} documented bd commands fail ({total} unique commands ran, {skipped} lines skipped)")
        return 1
    print(f"OK: {total} unique documented bd commands all exit 0 ({skipped} lines skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
