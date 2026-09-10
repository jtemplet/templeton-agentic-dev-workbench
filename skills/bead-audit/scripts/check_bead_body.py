#!/usr/bin/env python3
"""Check a bead description against the two rules a reader meets first.

`docs/bead-body-contract.md` says every bead description opens with an `**Ask:**` line of 20
words or fewer, and that its prose reads at a fourteen-year-old level. A rule nobody checks stops
being followed: the plain-English instruction in `skills/bead-refine/SKILL.md` was already written
when its owner reported that it did not bind. This script is the check.

THREE MODES

    check_bead_body.py DESCRIPTION_FILE     one description, held in a file ("-" reads stdin)
    check_bead_body.py --bd-json FILE       every bead in `bd list --json` output ("-" reads stdin)
    check_bead_body.py --compare OLD NEW    whether NEW only prepends an Ask line to OLD

The compare mode exists for the one-off pass that prepends an Ask line to every bead in the
backlog. `bd update -d` replaces the whole description, so a pass that changes anything below the
new line has lost content, and nothing else would notice.

HOW THE READING LEVEL IS SCORED

The score is the Flesch-Kincaid grade level:

    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

Grade 9 is the reading level of a fourteen-year-old, so a score above 9 fails. The score is
compared as printed, to one decimal, so a reader who sees 9.0 sees a pass.

Code is removed before scoring: fenced blocks, backticked spans, and any bare token shaped like a
path or a file name. A reader does not read `skills/quality-gates/SKILL.md` as prose. Counted as
one word, it carries a dozen syllables, and a bead would fail for naming the file it changes.
Headings are removed too, because a heading has no full stop and would join the sentence below
it. A list item and a table row each count as their own sentence, for the same reason.

Syllables are counted by vowel groups, less a silent final "e". That is the usual approximation,
and it needs no dictionary. The grade is a floor, not the whole test: it cannot see jargon, so
the contract still carries the rules that catch it.

Exit: 0 clean, 1 with a report naming each failure, 2 on operator error.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

ASK_PREFIX = "**Ask:**"
ASK_WORD_LIMIT = 20
# Grade 9 is the reading level of a fourteen-year-old.
GRADE_LIMIT = 9.0
STDIN = "-"
# How much of a wrong first line a failure quotes, so a long one stays on one terminal line.
SHOWN_CHARACTERS = 60

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s*#{1,6}\s")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
TABLE_ROW = re.compile(r"^\s*\|")
TABLE_DIVIDER = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
CODE_SPAN = re.compile(r"(`+).*?\1")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# A dotted file name (`plugin.json`, `.githooks`) is code even with no slash in it.
FILE_NAME = re.compile(r"\.?[\w-]+(?:\.[\w-]+)+|\.[\w-]+")
SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")
ENDS_SENTENCE = re.compile(r"([.!?])[\"')\]]*$")
HAS_WORD_CHARACTER = re.compile(r"[A-Za-z0-9]")
VOWEL_GROUP = re.compile(r"[aeiouy]+")
# Silent in "file" and "make", sounded in "table" and "agree".
SILENT_FINAL_E = re.compile(r"(?<!e)(?<![^aeiouy]l)e$")


def check_body(description: str) -> tuple[float, list[str]]:
    """Return the description's grade and every rule it breaks."""
    grade = reading_grade(description)
    return grade, ask_line_problems(description) + grade_problems(grade)


def ask_line_problems(description: str) -> list[str]:
    first_line = description.split("\n", 1)[0]
    if not first_line.startswith(ASK_PREFIX):
        shown = f'"{first_line[:SHOWN_CHARACTERS]}"' if first_line.strip() else "empty"
        return [f"missing the `{ASK_PREFIX}` first line. The first line is {shown}"]

    words = len(first_line[len(ASK_PREFIX) :].split())
    if words == 0:
        return [f"the `{ASK_PREFIX}` line holds no sentence"]
    if words > ASK_WORD_LIMIT:
        return [f"the `{ASK_PREFIX}` line is {words} words, the limit is {ASK_WORD_LIMIT}"]
    return []


def grade_problems(grade: float) -> list[str]:
    if grade > GRADE_LIMIT:
        return [
            f"the prose reads at Flesch-Kincaid grade {grade:.1f}, the limit is {GRADE_LIMIT:.0f}"
        ]
    return []


def prepend_problems(old: str, new: str) -> list[str]:
    """Return why `new` is more than `old` with an Ask line and one blank line prepended."""
    first_line, _, rest = new.partition("\n")
    if not first_line.startswith(ASK_PREFIX):
        return [f"the new description does not open with an `{ASK_PREFIX}` line"]
    if not rest.startswith("\n"):
        return [f"no blank line follows the `{ASK_PREFIX}` line"]

    body = rest[1:]
    if body != old:
        line = first_difference(old, body)
        return [
            f"the text below the `{ASK_PREFIX}` line changes the old description at its line {line}"
        ]
    return []


def first_difference(old: str, new: str) -> int:
    """The 1-based line of `old` where `new` first departs from it. The two must differ."""
    pairs = itertools.zip_longest(old.split("\n"), new.split("\n"))
    return next(number for number, (before, after) in enumerate(pairs, 1) if before != after)


def reading_grade(description: str) -> float:
    """The Flesch-Kincaid grade of the description's prose, rounded to one decimal."""
    sentences = [words for words in prose_sentences(description) if words]
    words = [word for sentence in sentences for word in sentence]
    if not words:
        return 0.0
    syllables = sum(count_syllables(word) for word in words)
    grade = 0.39 * len(words) / len(sentences) + 11.8 * syllables / len(words) - 15.59
    return round(grade, 1)


def prose_sentences(description: str) -> list[list[str]]:
    """Every sentence of prose as its list of words, once code and paths are removed."""
    return [
        [token for token in sentence.split() if HAS_WORD_CHARACTER.search(token)]
        for block in prose_blocks(description)
        for sentence in SENTENCE_END.split(without_code(block))
    ]


def prose_blocks(description: str) -> list[str]:
    """Split the description into runs of prose: a paragraph, a list item, or a table row.

    Headings and fenced code are not prose, so neither reaches a block.
    """
    blocks: list[list[str]] = [[]]
    fenced = False
    for line in description.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            blocks.append([])
        elif fenced:
            continue
        elif not line.strip() or HEADING.match(line) or TABLE_DIVIDER.match(line):
            blocks.append([])
        elif LIST_ITEM.match(line) or TABLE_ROW.match(line):
            blocks.append([line])
        else:
            blocks[-1].append(line)
    return [" ".join(lines) for lines in blocks if lines]


def without_code(block: str) -> str:
    """The block's text with code spans, link targets, paths, and Markdown markup removed."""
    text = CODE_SPAN.sub(" ", block)
    text = LINK.sub(r"\1", text)
    text = LIST_ITEM.sub("", text, count=1)
    text = text.replace(ASK_PREFIX, " ").replace("*", "").replace("|", " ")
    return " ".join(without_path(token) for token in text.split())


def without_path(token: str) -> str:
    """The token, or only its sentence-ending mark when the token is a path or a file name."""
    core = token.lstrip("\"'([<").rstrip("\"')]>,;:!?.")
    if "/" not in core and not FILE_NAME.fullmatch(core):
        return token
    ending = ENDS_SENTENCE.search(token)
    return ending.group(1) if ending else ""


def count_syllables(word: str) -> int:
    letters = re.sub(r"[^a-z]", "", word.lower())
    groups = len(VOWEL_GROUP.findall(letters))
    if groups > 1 and SILENT_FINAL_E.search(letters):
        groups -= 1
    return max(groups, 1)


def report_description(label: str, description: str) -> int:
    grade, problems = check_body(description)
    if problems:
        print(failure_report(label, grade, problems))
        return 1
    print(f"OK: {label} opens with an `{ASK_PREFIX}` line and reads at grade {grade:.1f}")
    return 0


def report_beads(beads: list[dict]) -> int:
    failures = 0
    for bead in beads:
        grade, problems = check_body(bead.get("description") or "")
        if problems:
            failures += 1
            print(failure_report(bead.get("id", "(no id)"), grade, problems))

    if failures:
        print(f"\n{failures} of {len(beads)} bead(s) fail")
        return 1
    print(
        f"OK: all {len(beads)} bead(s) open with an `{ASK_PREFIX}` line "
        f"and read at grade {GRADE_LIMIT:.0f} or below"
    )
    return 0


def report_compare(old: str, new: str) -> int:
    problems = prepend_problems(old, new)
    if problems:
        print("FAIL: the edit is not prepend-only")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"OK: the edit is prepend-only: one `{ASK_PREFIX}` line and one blank line, nothing else")
    return 0


def failure_report(label: str, grade: float, problems: list[str]) -> str:
    lines = [f"FAIL: {label}, grade {grade:.1f}"]
    lines.extend(f"  {problem}" for problem in problems)
    return "\n".join(lines)


def load_beads(text: str) -> list[dict]:
    beads = json.loads(text)
    if not isinstance(beads, list) or not all(isinstance(bead, dict) for bead in beads):
        raise ValueError("expected the JSON list of beads that `bd list --json` prints")
    for bead in beads:
        if not isinstance(bead.get("description") or "", str):
            raise ValueError(f"bead {bead.get('id', '(no id)')} has a description that is not text")
    return beads


def read_input(path: str) -> str:
    if path == STDIN:
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("description", nargs="?", help='a file holding one description, or "-"')
    mode.add_argument("--bd-json", metavar="FILE", help='`bd list --json` output, or "-"')
    mode.add_argument(
        "--compare", nargs=2, metavar=("OLD", "NEW"), help="two files holding descriptions"
    )
    args = parser.parse_args(argv)
    if args.compare and args.compare.count(STDIN) > 1:
        parser.error("--compare can read stdin for one of its two files, not both")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.compare:
            old_path, new_path = args.compare
            return report_compare(read_input(old_path), read_input(new_path))
        if args.bd_json is not None:
            return report_beads(load_beads(read_input(args.bd_json)))
        label = "stdin" if args.description == STDIN else args.description
        return report_description(label, read_input(args.description))
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
