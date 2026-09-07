#!/usr/bin/env python3
"""Report paths a document claims exist that are not on disk.

This is Gate 5 of the quality-gates skill. It exists as a script because the
prose version did not survive its first real repository: told to extract "tokens
that look like a path", it reported 194 misses here, of which zero were stale
references. Slash commands (`/code-review`), placeholders (`skills/<name>/`),
and a worked example in the skill's own text all look like paths.

Three rules cut that to a usable signal, and each one is load-bearing:

  1. ANCHOR TO A REAL DIRECTORY. A backticked token counts only when its first
     segment is a directory that exists in the repository. `docs/ROUTING.md` is
     a claim about this tree; `src/export.py` in a worked example is not. One
     shape anchors elsewhere: a token under `references/` is measured against
     the directory of the document that names it, because that is where a skill
     keeps its own reference prose and no such directory sits at the root.
  2. SKIP WHAT IS NOT A PATH. Slash commands, URLs, placeholders in angle
     brackets, globs, variables, and `file:line` references are all excluded by
     shape, before any disk access.
  3. SKIP FENCED BLOCKS. Sample commands inside ``` fences describe other
     machines and other repositories.

Markdown link targets are checked without rule 1. A link is an unambiguous
claim that the target is reachable, so a broken one is a finding wherever it points.

Paths a documented tool CREATES at runtime are not broken references. `docs/roadmap.html`
does not exist until someone runs the dashboard. List those in `.docpaths-ignore`
at the repository root, one glob per line, or pass `--ignore`.

Exit status is 1 when misses are found. The skill maps that to WARN, never to a
gate failure: a doc pointing at a path that does not exist yet is worth reporting
and is not a reason to block a commit.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKTICK = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*```")

# A token shaped like any of these is not a claim about a file in this tree.
NOT_A_PATH_PREFIX = ("/", "http://", "https://", "@", "#", "~", "mailto:")
NOT_A_PATH_CHARS = frozenset("<>*$? ")

DEFAULT_DOCS = ("README.md", "AGENTS.md", "CLAUDE.md")
# Prompt assets: documents an agent reads and acts on. A `references/` file
# under a skill is deliberately absent from this list; those are prose the skill
# quotes, not paths a command depends on. A SKILL.md that POINTS at one is still
# checked, which is what DOC_RELATIVE_ROOT below resolves.
DEFAULT_ASSET_GLOBS = ("skills/*/SKILL.md", "commands/*.md", "agents/*.md")
# A skill keeps its reference prose beside itself, so `references/schema.md`
# names a file under that skill's own directory and nothing at the repository
# root. A bare `references/` names the directory as a concept, which is how the
# prose here discusses it, so a pointer needs a segment after the slash.
DOC_RELATIVE_ROOT = "references"
IGNORE_FILE = ".docpaths-ignore"
DOC_PREFIX = "doc:"


@dataclass(frozen=True)
class Miss:
    """One path a document claims exists, that does not."""

    doc: str
    line: int
    target: str
    kind: str

    def __str__(self) -> str:
        return f"{self.doc}:{self.line} -> {self.target}  [{self.kind}]"


def load_ignores(root: Path, extra: list[str]) -> tuple[list[str], list[str]]:
    """Return (target globs, document globs).

    A `doc:` prefix skips a whole document. Some documents name paths that do not
    exist on purpose: a plan describes the tree it wants to create, so every path
    in it is a miss until the work lands. Listing their targets one by one would
    turn the ignore file into a second copy of the plan.
    """
    targets: list[str] = list(extra)
    documents: list[str] = []
    ignore_file = root / IGNORE_FILE
    if ignore_file.is_file():
        for raw in ignore_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(DOC_PREFIX):
                documents.append(line[len(DOC_PREFIX) :].strip())
            else:
                targets.append(line)
    return targets, documents


def top_level_dirs(root: Path) -> frozenset[str]:
    return frozenset(p.name for p in root.iterdir() if p.is_dir())


def is_shaped_like_a_path(token: str) -> bool:
    if token.startswith(NOT_A_PATH_PREFIX):
        return False
    if NOT_A_PATH_CHARS & set(token):
        return False
    return ":" not in token


def normalize(token: str) -> str:
    """Strip the plugin-root variable, any anchor fragment, and a trailing slash.

    The fragment matters: `[the rule](docs/HOOKS.md#test)` points at a real file,
    and resolving the whole token would report it missing.
    """
    without_root = token.replace("${CLAUDE_PLUGIN_ROOT}/", "")
    return without_root.split("#", 1)[0].rstrip("/")


def ignored(target: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(target, pattern) for pattern in patterns)


def targets_in(text: str, anchors: frozenset[str]) -> list[tuple[int, str, str]]:
    """Yield (line number, target, kind) for every path claim in one document."""
    found: list[tuple[int, str, str]] = []
    fenced = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        for target in LINK.findall(line):
            if is_shaped_like_a_path(normalize(target)):
                found.append((lineno, target, "link"))
        if fenced:
            continue
        for token in BACKTICK.findall(line):
            # Normalize before the shape test, not after. `${CLAUDE_PLUGIN_ROOT}/...`
            # carries a `$` that the shape test rejects, and those Read-delegation
            # paths are the ones worth checking most: a broken one silently breaks
            # the command that reads it.
            candidate = normalize(token)
            if not is_shaped_like_a_path(candidate):
                continue
            head, _, rest = candidate.partition("/")
            if head == DOC_RELATIVE_ROOT and rest:
                found.append((lineno, token, "reference"))
            elif head in anchors:
                found.append((lineno, token, "backtick"))
    return found


def owning_skill_dir(doc: Path) -> Path:
    """The directory a `references/` pointer is written from.

    A SKILL.md names `references/x.md` from the skill's own directory. A document
    already inside that `references/` directory names its siblings with the same
    wording, copied from the skill, so it is writing from one level up. Reading
    it from the document's own directory instead doubles the segment and reports
    a live sibling as missing.
    """
    if doc.parent.name == DOC_RELATIVE_ROOT:
        return doc.parent.parent
    return doc.parent


def reachable(root: Path, doc: Path, resolved: str, kind: str) -> bool:
    """Whether a normalized target names something that exists.

    Two ways, because this tree uses both and neither is wrong. A markdown link
    is relative to the document that carries it, which is what a renderer
    follows: `verification.md` beside `protocol_contract.md`, or
    `../cli/run/run.md` from a sibling directory. A backticked path is written
    from the repository root, the way a reader would type it into an editor.

    Trying only the root form reported 65 live links as broken in one run, every
    one of which a renderer resolves. Trying both reports a miss only when the
    target resolves NEITHER way, so a genuinely dead link is still a finding.

    A `reference` kind takes neither, and resolves against the skill that owns
    the pointer. Trying the root too would let an unrelated `references/` file
    there silence a skill's dead pointer.
    """
    if kind == "reference":
        return (owning_skill_dir(doc) / resolved).exists()
    if (doc.parent / resolved).exists():
        return True
    return (root / resolved).exists()


def check(
    root: Path, docs: list[Path], patterns: list[str], skip_docs: list[str]
) -> list[Miss]:
    anchors = top_level_dirs(root)
    misses: list[Miss] = []
    for doc in docs:
        label = doc.relative_to(root).as_posix()
        if ignored(label, skip_docs):
            continue
        text = doc.read_text(encoding="utf-8")
        for lineno, target, kind in targets_in(text, anchors):
            resolved = normalize(target)
            if ignored(resolved, patterns) or reachable(root, doc, resolved, kind):
                continue
            misses.append(Miss(label, lineno, target, kind))
    return misses


def resolve_docs(root: Path, given: list[str]) -> list[Path]:
    """The documents checked when the caller names none.

    The three named files, everything under `docs/`, and every prompt asset: a
    skill, a command, or an agent. The prompt assets are here because they carry
    the delegation path each command reads its skill from. A typo in one breaks
    that command with no error message, so leaving them out made this gate
    report a clean run over the paths that fail most quietly.
    """
    if given:
        return [Path(g) if Path(g).is_absolute() else root / g for g in given]
    docs = [root / name for name in DEFAULT_DOCS]
    docs.extend(sorted((root / "docs").rglob("*.md")))
    for pattern in DEFAULT_ASSET_GLOBS:
        docs.extend(sorted(root.glob(pattern)))
    return [d for d in docs if d.is_file()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docs", nargs="*", help="Documents to check")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="GLOB",
        help="Path a tool creates at runtime; repeatable",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return 2

    docs = resolve_docs(root, args.docs)
    missing_docs = [d for d in docs if not d.is_file()]
    if missing_docs:
        for doc in missing_docs:
            print(f"ERROR: no such document: {doc}", file=sys.stderr)
        return 2
    if not docs:
        print("OK: no documents to check")
        return 0

    target_globs, doc_globs = load_ignores(root, args.ignore)
    misses = check(root, docs, target_globs, doc_globs)
    for miss in misses:
        print(miss)

    if misses:
        print(f"\n{len(misses)} missing paths across {len(docs)} documents")
        return 1
    print(f"OK: every path claim in {len(docs)} documents resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
