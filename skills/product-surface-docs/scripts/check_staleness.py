#!/usr/bin/env python3
"""Detect stale product-surface docs by diffing each doc's source_refs in git.

Walks a docs/products tree, reads the YAML frontmatter of every .md doc, and for
each doc decides whether the code it documents has changed since the doc was last
reviewed. This is the executable form of the "Keeping Current" mechanism: it turns
staleness from prose into a command.

Per-doc decision:
  - stub          : no source_refs declared yet (needs first-pass authoring)
  - stale         : at least one in-repo source_ref changed since the baseline
  - external-stale: an external source_ref advanced past its pinned SHA
  - unverifiable  : an external source_ref has no reachable probe checkout
  - current       : nothing changed

Baseline date (the "since" for in-repo refs):
  - the doc's `last_reviewed` frontmatter date, if present
  - else the doc file's own last git-commit date (the bootstrap rule, so a
    frontmatter-less tree still gets a real baseline on its first refresh)

Frontmatter schema (see references/frontmatter-schema.md):
  source_refs:
    - ui/src/views/SleepView.vue            # in-repo, string form
    - repo: atlas-ios                        # external, mapping form
      path: Sources/Recovery/
      pin: <commit-sha>                      # last reconciled SHA in that repo
      probe: ../atlas-ios                    # optional local checkout to diff against

Usage:
  python3 check_staleness.py [docs_dir]     # default: docs/products
  python3 check_staleness.py --json         # machine-readable output

No third-party dependencies. Frontmatter is parsed with a small tolerant reader
scoped to this schema (no PyYAML required).
"""

import json
import subprocess
import sys
from pathlib import Path


def run_git(args, cwd=None):
    """Run a git command, returning (ok, stdout). Never raises."""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return out.returncode == 0, out.stdout.strip()
    except FileNotFoundError:
        return False, ""


def parse_frontmatter(text):
    """Extract the leading --- ... --- block into a dict for our known schema.

    Handles top-level scalars and a `source_refs:` list whose items are either
    bare strings (`- path`) or mappings (`- repo: x` then indented `path:`/`pin:`/
    `probe:` lines). Returns {} when there is no frontmatter.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}

    data = {}
    refs = []
    in_refs = False
    current = None  # the mapping item currently being built
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        stripped = raw.strip()

        if not in_refs and stripped == "source_refs:":
            in_refs = True
            continue

        if in_refs:
            # Any indent-0 line that is not a dash item ends the source_refs list
            # (covers both `key:` block openers and `key: value` scalars).
            if indent == 0 and not stripped.startswith("- "):
                if current:
                    refs.append(current)
                    current = None
                in_refs = False
                # fall through to scalar handling below
            elif stripped.startswith("- "):
                if current:
                    refs.append(current)
                    current = None
                item = stripped[2:].strip()
                if ":" in item and not item.startswith("/"):
                    # mapping item, first key on the dash line (e.g. "- repo: x")
                    k, v = item.split(":", 1)
                    current = {k.strip(): v.strip()}
                else:
                    refs.append(item)  # bare string ref
                continue
            elif current is not None and ":" in stripped:
                k, v = stripped.split(":", 1)
                current[k.strip()] = v.strip()
                continue
            else:
                continue

        if ":" in stripped:
            k, v = stripped.split(":", 1)
            data[k.strip()] = v.strip()

    if current:
        refs.append(current)
    if refs:
        data["source_refs"] = refs
    return data


def doc_commit_baseline(repo_root, doc_path):
    """The doc file's own last commit timestamp (full ISO 8601), for the bootstrap rule.

    A full timestamp (not just the date) is deliberate: it prevents a source commit
    made earlier on the same day as the doc's commit from being falsely flagged as a
    change-since-review.
    """
    ok, out = run_git(
        ["log", "-1", "--format=%cI", "--", str(doc_path)],
        cwd=repo_root,
    )
    return out if ok and out else None


def in_repo_changed(repo_root, path, since):
    """True if any commit touched `path` strictly after `since`.

    `since` may be a date (`2026-06-12`, from an explicit `last_reviewed`) or a full
    ISO timestamp (from the bootstrap baseline); git's --since accepts both.
    """
    ok, out = run_git(
        ["log", f"--since={since}", "--format=%h", "--", path],
        cwd=repo_root,
    )
    return bool(ok and out)


def external_status(ref):
    """Return one of 'changed' | 'current' | 'unverifiable' for an external ref."""
    probe = ref.get("probe")
    pin = ref.get("pin")
    path = ref.get("path", "")
    if not probe or not Path(probe).expanduser().exists():
        return "unverifiable"
    if not pin:
        return "unverifiable"
    ok, out = run_git(
        ["log", "--format=%h", f"{pin}..HEAD", "--", path],
        cwd=str(Path(probe).expanduser()),
    )
    if not ok:
        return "unverifiable"
    return "changed" if out else "current"


def evaluate_doc(repo_root, doc_path):
    fm = parse_frontmatter(doc_path.read_text(encoding="utf-8", errors="replace"))
    refs = fm.get("source_refs") or []
    if not refs:
        return {"status": "stub", "changed": [], "baseline": None}

    baseline = fm.get("last_reviewed") or doc_commit_baseline(repo_root, doc_path)
    if not baseline:
        return {"status": "unverifiable", "changed": [], "baseline": None,
                "note": "no last_reviewed and no commit history"}

    changed = []
    external_unverifiable = []
    for ref in refs:
        if isinstance(ref, str):
            if in_repo_changed(repo_root, ref, baseline):
                changed.append(ref)
        else:
            st = external_status(ref)
            label = f"{ref.get('repo', '?')}:{ref.get('path', '')}"
            if st == "changed":
                changed.append(label + " (external)")
            elif st == "unverifiable":
                external_unverifiable.append(label)

    if changed:
        status = "stale"
    elif external_unverifiable:
        status = "unverifiable"
    else:
        status = "current"
    return {
        "status": status,
        "changed": changed,
        "baseline": baseline,
        "unverifiable_external": external_unverifiable,
    }


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    docs_dir = Path(args[0]) if args else Path("docs/products")
    if not docs_dir.exists():
        print(f"docs dir not found: {docs_dir}", file=sys.stderr)
        return 2

    ok, repo_root = run_git(["rev-parse", "--show-toplevel"])
    repo_root = repo_root if ok and repo_root else "."

    # Accept either a directory (scan it) or a single .md file (check just that doc).
    if docs_dir.is_file():
        docs = [docs_dir]
    else:
        docs = [d for d in sorted(docs_dir.rglob("*.md"))
                if not d.name.startswith("_")]  # skip ledger / coverage artifacts

    results = []
    for doc in docs:
        res = evaluate_doc(repo_root, doc)
        res["doc"] = str(doc)
        results.append(res)

    if as_json:
        print(json.dumps(results, indent=2))
        return 0

    order = ["stale", "unverifiable", "stub", "current"]
    by_status = {k: [r for r in results if r["status"] == k] for k in order}
    labels = {
        "stale": "STALE (code changed since last_reviewed)",
        "unverifiable": "UNVERIFIABLE (external ref, no reachable probe)",
        "stub": "STUB (no source_refs; needs authoring)",
        "current": "CURRENT",
    }
    for k in order:
        rows = by_status[k]
        if not rows:
            continue
        print(f"\n== {labels[k]}: {len(rows)} ==")
        for r in rows:
            base = f"  (baseline {r['baseline']})" if r.get("baseline") else ""
            print(f"  {r['doc']}{base}")
            for c in r.get("changed", []):
                print(f"      changed: {c}")
            for u in r.get("unverifiable_external", []):
                print(f"      unverifiable external: {u}")
    total = len(results)
    stale_n = len(by_status["stale"]) + len(by_status["unverifiable"])
    print(f"\n{stale_n} of {total} docs need attention "
          f"({len(by_status['stub'])} stubs, {len(by_status['current'])} current).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
