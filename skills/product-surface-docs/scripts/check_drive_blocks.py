#!/usr/bin/env python3
"""Report which leaf documents in a docs/products tree carry no drive block.

A drive block is the "How to drive this" section that tells an agent how to reach one
feature: its route, its precondition, its selector, its action, and its success signal.
`skills/product-surface-docs/SKILL.md` defines the shape. The `verify-app` skill reads
it. This script is what keeps the two in step, so a template nobody enforces cannot
quietly decay.

Only a leaf document needs one. A leaf is a document with no document below it, which
is the same rule the skill states from the other side: every document except a leaf
ends with a list of links to the documents below it. So an overview, a surface, and any
directory owner that has children are all exempt, and no depth count is needed.

The block is found by its paired comments, never by its heading:

    <!-- drive:start -->
    ## How to drive this

    - **Route:** /deals
    - **Precondition:** signed in as a lender whose workspace holds at least one deal
    - **Selector:** `[data-testid="deal-row"]`
    - **Action:** click the first row, then read the page header
    - **Success signal:** the header shows the deal name from that row
    <!-- drive:end -->

Renaming the heading would otherwise break this script without a word. A feature with no
user interface writes the same block carrying a reason, and that passes:

    <!-- drive:start -->
    ## How to drive this

    **Not drivable:** this feature has no user interface. It runs as the nightly export job.
    <!-- drive:end -->

Per-document outcome:
  - ok            : the block is present and complete
  - not-drivable  : the block is present and says why the feature cannot be driven
  - missing       : no drive block at all
  - incomplete    : the block is present and one or more of the five lines is absent
  - unterminated  : the block opens and never closes

Usage:
  python3 check_drive_blocks.py [docs_dir]     # default: docs/products
  python3 check_drive_blocks.py --json         # machine-readable output

Exit status:
  0  every leaf document carries a usable block, or the repository has no tree to check
  1  at least one leaf document does not
  2  operator error: a directory named on the command line does not exist

A repository with no `docs/products` is not a failing repository. Most are not documented
this way, and this check runs in a push hook, so treating an absent default as operator
error would refuse every push from every such repository. A directory named on the command
line is different: the operator asserted it exists, and a typo there deserves an error.

No third-party dependencies.
"""

import json
import sys
from pathlib import Path

START = "<!-- drive:start -->"
END = "<!-- drive:end -->"
NOT_DRIVABLE = "**Not drivable:**"
REQUIRED_LINES = ("Route:", "Precondition:", "Selector:", "Action:", "Success signal:")

# Documents that are never leaves whatever the directory shape says. The overview owns
# the whole tree, and the ledger is a table of findings rather than a document about a
# feature.
NEVER_A_LEAF = ("product_overview.md", "_findings.md")


def collect_docs(docs_dir):
    """Every markdown document in the tree, sorted, minus the two that are never leaves."""
    return [
        path
        for path in sorted(docs_dir.rglob("*.md"))
        if path.name not in NEVER_A_LEAF
    ]


def domain_of(doc):
    """The directory a document owns, or None when it owns none.

    A document owns a directory when it is named after it, such as `web/web.md` owning
    `web/`. Every other document owns nothing and therefore has nothing below it.
    """
    if doc.stem == doc.parent.name:
        return doc.parent
    return None


def is_leaf(doc, docs):
    """True when no document in the tree sits below this one.

    This is the skill's own rule, read from the other side: a document that links down
    to other documents is not a leaf. A document owning no directory has nothing below
    it by construction.
    """
    domain = domain_of(doc)
    if domain is None:
        return True
    return not any(other != doc and domain in other.parents for other in docs)


def read_block(text):
    """Extract the drive block's body, or say why there is none.

    Returns (body, problem). Exactly one of the two is None.
    """
    start = text.find(START)
    if start == -1:
        return None, "missing"
    end = text.find(END, start)
    if end == -1:
        return None, "unterminated"
    return text[start + len(START) : end], None


def grade_block(body):
    """Grade a drive block's body. Returns (outcome, missing_lines)."""
    if NOT_DRIVABLE in body:
        return "not-drivable", []
    missing = [name for name in REQUIRED_LINES if name not in body]
    if missing:
        return "incomplete", missing
    return "ok", []


def evaluate_doc(doc):
    """Grade one leaf document. Returns a result mapping."""
    body, problem = read_block(doc.read_text(encoding="utf-8", errors="replace"))
    if problem:
        return {"doc": str(doc), "outcome": problem, "missing_lines": []}
    outcome, missing = grade_block(body)
    return {"doc": str(doc), "outcome": outcome, "missing_lines": missing}


def evaluate_tree(docs_dir):
    """Grade every leaf document in the tree, in path order."""
    docs = collect_docs(docs_dir)
    return [evaluate_doc(doc) for doc in docs if is_leaf(doc, docs)]


PASSING = ("ok", "not-drivable")

LABELS = {
    "missing": "MISSING (no drive block)",
    "unterminated": "UNTERMINATED (the block opens and never closes)",
    "incomplete": "INCOMPLETE (the block is missing a required line)",
}


def report(results):
    """Print the human-readable report. Returns the count of failing documents."""
    failing = [r for r in results if r["outcome"] not in PASSING]
    for outcome in ("missing", "unterminated", "incomplete"):
        rows = [r for r in failing if r["outcome"] == outcome]
        if not rows:
            continue
        print(f"\n== {LABELS[outcome]}: {len(rows)} ==")
        for row in rows:
            print(f"  {row['doc']}")
            for name in row["missing_lines"]:
                print(f"      missing line: {name}")
    return len(failing)


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    named = bool(args)
    docs_dir = Path(args[0]) if named else Path("docs/products")
    if not docs_dir.exists():
        if named:
            print(f"docs dir not found: {docs_dir}", file=sys.stderr)
            return 2
        if as_json:
            print(json.dumps([], indent=2))
        else:
            print(f"OK: no {docs_dir} tree in this repository, so there is nothing to check")
        return 0

    results = evaluate_tree(docs_dir)

    if as_json:
        print(json.dumps(results, indent=2))
        return 1 if any(r["outcome"] not in PASSING for r in results) else 0

    failing = report(results)
    if failing:
        carry = "leaf document carries" if failing == 1 else "leaf documents carry"
        print(f"\n{failing} of {len(results)} {carry} no usable drive block.")
        return 1
    not_drivable = sum(1 for r in results if r["outcome"] == "not-drivable")
    leaves = "leaf" if len(results) == 1 else "leaves"
    print(
        f"OK: every leaf document carries a drive block "
        f"({len(results)} {leaves}, {not_drivable} marked not drivable)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
