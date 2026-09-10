#!/usr/bin/env python3
"""Regression suite for check_bead_body.py.

Stdlib only, no install, mirroring the other suites in this repository. Run with:
    python3 skills/bead-audit/scripts/test_check_bead_body.py

Every case drives the script as a command, the way a hook or a person runs it, and asserts the
exit status plus the line of output that names the failure.

The groups follow the bead's acceptance criteria (tadw-vio), so a grader can cite a group by its
criterion number:

  criterion 1   a description with no `**Ask:**` first line fails, naming the line
  criterion 2   prose above Flesch-Kincaid grade 9 fails, and the score is printed
  criterion 3   code spans, fenced code, and paths do not raise the score
  criterion 4   an edit that only prepends an Ask line and a blank line is prepend-only
  scoring       list items, table rows, link text, and final e are counted as a reader reads them
  bd list       the script reads `bd list --json` output as well as a file

Each removal case in criterion 3 is paired with its exposed twin, the same text with the code
shown as prose. The twin must fail. Without it, a fixture too short to raise the score would pass
whether or not the script removed anything. The scoring cases carry twins for the same reason: a
twin shows the verdict would flip if the rule under test stopped holding.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_bead_body.py"

PASS, FAIL, ERROR = 0, 1, 2

ASK = "**Ask:** Fix the cat."
PLAIN = f"{ASK}\n\nThe cat sat on the mat. The dog ran to the door."
NO_ASK = "## Why (Computational)\n\nThe cat sat on the mat."
LONG_WORD = "internationalization_configuration_serialization"
OLD = "## Why (Computational)\n\nThe cat sat on the mat.\n\n## Estimated size\n\n1 file."


def sentence(words: int, syllables: int) -> str:
    """A sentence of exactly `words` words and `syllables` syllables.

    It is built from "cat" (one syllable) and "open" (two), so the count does not lean on how the
    script splits a hard word.
    """
    opens = syllables - words
    assert 0 <= opens <= words, "syllables must lie between words and twice words"
    return " ".join(["open"] * opens + ["cat"] * (words - opens)).capitalize() + "."


def ask_line(words: int) -> str:
    return f"**Ask:** {' '.join(['cat'] * words)}.\n\nThe cat sat."


def exposed_paths(text: str) -> str:
    """Glue each path into one long word, so nothing marks it as a path any more."""
    return re.sub(r"(?<=\w)[/.](?=\w)", "", text)


# With ASK in front, each description holds 2 sentences. Grade 9.0 is 48 words and 62 syllables:
# 0.39 * 48 / 2 + 11.8 * 62 / 48 - 15.59 = 9.01. Grade 9.1 is 52 words and 64 syllables: 9.07.
# Grade 10.1 is 20 words and 37 syllables: 10.14.
AT_GRADE_9 = f"{ASK}\n\n{sentence(45, 59)}"
AT_GRADE_9_1 = f"{ASK}\n\n{sentence(49, 61)}"
AT_GRADE_10_1 = f"{ASK}\n\n{sentence(17, 34)}"

CODE_SPANS = f"{ASK}\n\nRun `{LONG_WORD}` now. Then run `{LONG_WORD}` again."
FENCED_CODE = f"{ASK}\n\nRun this.\n\n```bash\n{LONG_WORD} {LONG_WORD} {LONG_WORD}\n```\n"
PATHS = (
    f"{ASK}\n\nRead skills/quality-gates/scripts/check_documented_bd_commands.py first. "
    "Then edit docs/bead-body-contract.md and CHANGELOG.md."
)
HEADING = f"{ASK}\n\n## {LONG_WORD}\n\nThe cat sat on the mat."
LINK_TARGET = f"{ASK}\n\nRead [the rule](#{LONG_WORD}) now."
LINK_TEXT = f"{ASK}\n\nRead [{LONG_WORD}](#rule) now."

# Twenty short lines with no full stop. Read as one run-on sentence they score above grade 9,
# even beside the table's one-word header row; read one sentence per line they score below 0.
ITEM = "the cat sat on the mat"
LINES = 20
LIST_ITEMS = f"{ASK}\n\n" + "\n".join(f"- {ITEM}" for _ in range(LINES))
TABLE_ROWS = f"{ASK}\n\n| Note |\n|---|\n" + "\n".join(f"| {ITEM} |" for _ in range(LINES))
RUN_ON = f"{ASK}\n\n" + "\n".join(ITEM for _ in range(LINES))

# "make" has one syllable, so swapping it for "cat" keeps the grade at 9.0. Counted as two, the
# five swaps add five syllables, which is sentence(45, 64): grade 10.2.
SILENT_E = f"{ASK}\n\n{sentence(45, 59).replace('cat', 'make', 5)}"
SILENT_E_SOUNDED = f"{ASK}\n\n{sentence(45, 64)}"
# "table" has two syllables, like "open", so the grade stays at 9.1. Counted as one, the five
# swaps drop five syllables, which is sentence(49, 56): grade 7.9.
SOUNDED_LE = f"{ASK}\n\n{sentence(49, 61).replace('open', 'table', 5)}"
SOUNDED_LE_SILENT = f"{ASK}\n\n{sentence(49, 56)}"

# Two sentences of 40 words, the first ending on a path. Kept apart they score 7.0; merged into
# one 80-word sentence, because the path took its full stop with it, they score 12.4.
FORTY_WORDS = " ".join(["cat"] * 40)
PATH_ENDS_SENTENCE = f"{ASK}\n\n{FORTY_WORDS} docs/cat.md. {FORTY_WORDS}."
PATH_WITHOUT_FULL_STOP = f"{ASK}\n\n{FORTY_WORDS} docs/cat.md {FORTY_WORDS}."


def check_description(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "description.md"
        path.write_text(text, encoding="utf-8")
        return run(str(path))


def compare(old: str, new: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as root:
        old_path, new_path = Path(root) / "old.md", Path(root) / "new.md"
        old_path.write_text(old, encoding="utf-8")
        new_path.write_text(new, encoding="utf-8")
        return run("--compare", str(old_path), str(new_path))


def check_bd_json(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "beads.json"
        path.write_text(text, encoding="utf-8")
        return run("--bd-json", str(path))


def run(*args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True, text=True
    )


def beads(*pairs: tuple[str, str]) -> str:
    """`bd list --json` output holding one bead per (id, description) pair."""
    return json.dumps(
        [{"id": bead_id, "description": text, "status": "open"} for bead_id, text in pairs]
    )


@dataclass(frozen=True)
class Case:
    group: str
    name: str
    action: Callable[[], subprocess.CompletedProcess[str]]
    exit: int
    shows: str = ""
    hides: str = ""


CASES = (
    # ---- criterion 1: the Ask line ----
    Case(
        "criterion 1: the Ask line",
        "a description with no Ask first line fails, naming the missing line",
        lambda: check_description(NO_ASK),
        FAIL,
        shows="missing the `**Ask:**` first line",
    ),
    Case(
        "criterion 1: the Ask line",
        "an Ask line below the first line fails",
        lambda: check_description(f"The cat sat on the mat.\n\n{ASK}"),
        FAIL,
        shows="missing the `**Ask:**` first line",
    ),
    Case(
        "criterion 1: the Ask line",
        "an Ask line of 20 words passes",
        lambda: check_description(ask_line(20)),
        PASS,
    ),
    Case(
        "criterion 1: the Ask line",
        "an Ask line over 20 words fails, and prints its word count",
        lambda: check_description(ask_line(21)),
        FAIL,
        shows="is 21 words, the limit is 20",
    ),
    Case(
        "criterion 1: the Ask line",
        "an Ask line holding no sentence fails",
        lambda: check_description("**Ask:**\n\nThe cat sat."),
        FAIL,
        shows="holds no sentence",
    ),
    Case(
        "criterion 1: the Ask line",
        "a plain description with an Ask line passes",
        lambda: check_description(PLAIN),
        PASS,
    ),
    # ---- criterion 2: the reading level ----
    Case(
        "criterion 2: the reading level",
        "a grade above 9 fails, and prints the score",
        lambda: check_description(AT_GRADE_10_1),
        FAIL,
        shows="grade 10.1, the limit is 9",
    ),
    Case(
        "criterion 2: the reading level",
        "a grade of 9.1 fails",
        lambda: check_description(AT_GRADE_9_1),
        FAIL,
        shows="grade 9.1",
    ),
    Case(
        "criterion 2: the reading level",
        "a grade of 9.0 passes",
        lambda: check_description(AT_GRADE_9),
        PASS,
        shows="grade 9.0",
    ),
    # ---- criterion 3: code and paths are removed before scoring ----
    Case(
        "criterion 3: what is removed before scoring",
        "exposed twin: the code span text, read as prose, fails",
        lambda: check_description(CODE_SPANS.replace("`", "")),
        FAIL,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "code spans do not raise the score",
        lambda: check_description(CODE_SPANS),
        PASS,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "exposed twin: the fenced code, read as prose, fails",
        lambda: check_description(FENCED_CODE.replace("```bash\n", "").replace("```\n", "")),
        FAIL,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "a fenced code block does not raise the score",
        lambda: check_description(FENCED_CODE),
        PASS,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "exposed twin: the paths, glued into words, fail",
        lambda: check_description(exposed_paths(PATHS)),
        FAIL,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "long file paths and file names do not raise the score",
        lambda: check_description(PATHS),
        PASS,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "exposed twin: the heading, read as a paragraph, fails",
        lambda: check_description(HEADING.replace("## ", "")),
        FAIL,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "a heading does not raise the score",
        lambda: check_description(HEADING),
        PASS,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "exposed twin: the link target, read as prose, fails",
        lambda: check_description(LINK_TARGET.replace("](", "] (")),
        FAIL,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "a link target does not raise the score",
        lambda: check_description(LINK_TARGET),
        PASS,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "exposed twin: a path that drops its full stop merges two sentences, and fails",
        lambda: check_description(PATH_WITHOUT_FULL_STOP),
        FAIL,
    ),
    Case(
        "criterion 3: what is removed before scoring",
        "a path at the end of a sentence keeps the full stop that ends it",
        lambda: check_description(PATH_ENDS_SENTENCE),
        PASS,
    ),
    # ---- scoring: sentences and syllables ----
    Case(
        "scoring: sentences and syllables",
        "exposed twin: twenty lines with no full stop read as one sentence, and fail",
        lambda: check_description(RUN_ON),
        FAIL,
    ),
    Case(
        "scoring: sentences and syllables",
        "each list item counts as its own sentence",
        lambda: check_description(LIST_ITEMS),
        PASS,
    ),
    Case(
        "scoring: sentences and syllables",
        "each table row counts as its own sentence",
        lambda: check_description(TABLE_ROWS),
        PASS,
    ),
    Case(
        "scoring: sentences and syllables",
        "link text is scored as prose",
        lambda: check_description(LINK_TEXT),
        FAIL,
        shows="Flesch-Kincaid grade",
    ),
    Case(
        "scoring: sentences and syllables",
        "exposed twin: the same words with each silent e sounded, fail",
        lambda: check_description(SILENT_E_SOUNDED),
        FAIL,
    ),
    Case(
        "scoring: sentences and syllables",
        "a silent final e is not counted as a syllable",
        lambda: check_description(SILENT_E),
        PASS,
        shows="grade 9.0",
    ),
    Case(
        "scoring: sentences and syllables",
        "exposed twin: the same words with each final le silent, pass",
        lambda: check_description(SOUNDED_LE_SILENT),
        PASS,
    ),
    Case(
        "scoring: sentences and syllables",
        "a final le after a consonant keeps its syllable",
        lambda: check_description(SOUNDED_LE),
        FAIL,
        shows="grade 9.1",
    ),
    # ---- criterion 4: a prepend-only edit ----
    Case(
        "criterion 4: a prepend-only edit",
        "a prepended Ask line and blank line is reported prepend-only",
        lambda: compare(OLD, f"{ASK}\n\n{OLD}"),
        PASS,
        shows="prepend-only",
    ),
    Case(
        "criterion 4: a prepend-only edit",
        "an edit that also changed a later line fails, naming that line",
        lambda: compare(OLD, f"{ASK}\n\n{OLD.replace('1 file.', '2 files.')}"),
        FAIL,
        shows="at its line 7",
    ),
    Case(
        "criterion 4: a prepend-only edit",
        "a prepended Ask line with no blank line after it fails",
        lambda: compare(OLD, f"{ASK}\n{OLD}"),
        FAIL,
        shows="no blank line follows",
    ),
    Case(
        "criterion 4: a prepend-only edit",
        "a prepended line that is not an Ask line fails",
        lambda: compare(OLD, f"Fix the cat.\n\n{OLD}"),
        FAIL,
        shows="does not open with an `**Ask:**` line",
    ),
    Case(
        "criterion 4: a prepend-only edit",
        "an edit that only added a trailing newline fails",
        lambda: compare(OLD, f"{ASK}\n\n{OLD}\n"),
        FAIL,
        shows="at its line 8",
    ),
    # ---- bd list --json ----
    Case(
        "bd list --json",
        "a failing bead is named by its id, and a passing one is not",
        lambda: check_bd_json(beads(("acme-good", PLAIN), ("acme-bad", NO_ASK))),
        FAIL,
        shows="FAIL: acme-bad",
        hides="acme-good",
    ),
    Case(
        "bd list --json",
        "a list of passing beads passes, and counts them",
        lambda: check_bd_json(beads(("acme-one", PLAIN), ("acme-two", PLAIN))),
        PASS,
        shows="all 2 bead(s)",
    ),
    Case(
        "bd list --json",
        "an empty list passes, and says it checked 0 beads",
        lambda: check_bd_json("[]"),
        PASS,
        shows="all 0 bead(s)",
    ),
    Case(
        "bd list --json",
        "a list holding something other than a bead exits 2",
        lambda: check_bd_json(json.dumps(["acme-one"])),
        ERROR,
    ),
    Case(
        "bd list --json",
        "a bead with no description fails rather than being skipped",
        lambda: check_bd_json(json.dumps([{"id": "acme-empty"}])),
        FAIL,
        shows="FAIL: acme-empty",
    ),
    Case(
        "bd list --json",
        "the output is read from stdin when the file is -",
        lambda: run("--bd-json", "-", stdin=beads(("acme-bad", NO_ASK))),
        FAIL,
        shows="FAIL: acme-bad",
    ),
    Case(
        "bd list --json",
        "a JSON object that is not a list exits 2",
        lambda: check_bd_json(json.dumps({"id": "acme-one"})),
        ERROR,
    ),
    Case(
        "bd list --json",
        "text that is not JSON exits 2",
        lambda: check_bd_json("not json"),
        ERROR,
    ),
    Case(
        "bd list --json",
        "a description that is not text exits 2, not 1",
        lambda: check_bd_json(json.dumps([{"id": "acme-one", "description": 42}])),
        ERROR,
    ),
    Case(
        "bd list --json",
        "an empty --bd-json path exits 2, not 1",
        lambda: run("--bd-json", ""),
        ERROR,
    ),
    # ---- operator error ----
    Case(
        "operator error",
        "a missing file exits 2",
        lambda: run("/nonexistent/description.md"),
        ERROR,
    ),
    Case("operator error", "no argument exits 2", lambda: run(), ERROR),
    Case(
        "operator error",
        "one description is read from stdin when the file is -",
        lambda: run("-", stdin=PLAIN),
        PASS,
        shows="OK: stdin",
    ),
    Case(
        "operator error",
        "--compare reading stdin twice exits 2",
        lambda: run("--compare", "-", "-"),
        ERROR,
    ),
)


def failure_of(case: Case, result: subprocess.CompletedProcess[str]) -> str:
    """Why the result breaks the case, or an empty string when it holds."""
    if result.returncode != case.exit:
        return f"expected exit {case.exit}, got {result.returncode}"
    if case.shows not in result.stdout:
        return f"expected the output to show {case.shows!r}"
    if case.hides and case.hides in result.stdout:
        return f"expected the output to leave out {case.hides!r}"
    return ""


def main() -> int:
    print("check_bead_body tests:")
    failures = 0
    group = None

    for case in CASES:
        if case.group != group:
            group = case.group
            print(f"\n  [{group}]")
        result = case.action()
        failure = failure_of(case, result)
        if failure:
            failures += 1
            print(f"    NOT OK - {case.name}\n        {failure}\n{result.stdout}{result.stderr}")
        else:
            print(f"    ok - {case.name}")

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1

    print(f"\nAll {len(CASES)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
