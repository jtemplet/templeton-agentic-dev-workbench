#!/usr/bin/env python3
"""Report secret files and prefixed key formats in the working tree.

This is Gate 6 of the quality-gates skill. It exists as a script because the
prose version asked the model to reassemble a pattern set, an exclusion list, and
a two-command file scan on every run, so two runs could disagree about what
"clean" means. Gate 5 already proved that failure mode: its prose version
reported 194 misses on a repository with no broken links.

The stakeholder is anyone trusting a PASS here. A quietly narrowed pattern list
reports clean while a key sits in the tree, and nothing about the report says
which patterns actually ran.

Two checks, both from the skill's prose:

  1. SECRET FILE NAMES, across tracked files AND untracked-but-unignored ones.
     The untracked half is the case this gate exists to catch: an untracked
     `.env` that git does not ignore is one `git add -A` away from a commit.
  2. PREFIXED KEY FORMATS in file content. Prefixed only. Generic long hex or
     base64 matching fires on lockfile hashes, fixtures, and minified assets, and
     a gate that cries wolf gets ignored along with the real finding.

THE MATCHED VALUE NEVER REACHES OUTPUT. A finding carries `file:line` and the
pattern name, nothing else. A report that quotes the secret copies it into one
more place, which is the opposite of the point.

Each content pattern requires the key's BODY, not just its prefix. `ghp_` and
`sk-ant-` appear as bare strings in this repository's own gate documentation, so
matching the prefix alone would report the file that defines the pattern. That is
not a narrowing: a prefix with no body is a mention, and a prefix with a body is
a key. The skill's prose already writes `AKIA[0-9A-Z]{16}` this way; the other
patterns now match it. Deliberately absent: any rule that exempts a path for
being documentation. An exemption by location would let a real key hide in any
file that happens to look like a doc.

Exit status is 1 when findings exist, 2 on operator error. The skill maps a
finding to FAIL, because unlike a stale doc reference, a key in the tree is not
something to note and move past.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Check 1: file names that carry secrets by convention.
SECRET_NAME_GLOBS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.p12",
    "id_rsa",
    "*.keystore",
    "*credential*",
)

# Sample files are meant to be committed; they hold placeholders, not keys.
SECRET_NAME_ALLOWED = (".env.example", ".env.sample", ".env.template")

# Check 2: prefixed key formats, each anchored to a body. See the module
# docstring for why the body is required rather than the prefix alone.
CONTENT_PATTERNS = (
    ("aws-access-key-id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("anthropic-api-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

# Excluded from both checks. Vendored, generated, and minified trees are not
# where a developer puts a key, and they are where false positives live.
EXCLUDED_DIRS = ("vendor", "node_modules", "dist", "build", ".git")
EXCLUDED_GLOBS = (
    "*.min.*",
    "*.lock",  # covers Gemfile.lock, Cargo.lock, poetry.lock, uv.lock
    "*lock.json",  # package-lock.json, composer.lock.json
    "*.lockb",  # bun
)
FIXTURE_DIR_NAMES = ("fixtures", "__fixtures__", "testdata")

# A key cannot hide in a file too large to be hand-written, and reading one
# stalls the gate. 2 MiB is far above any source file and far below a data dump.
MAX_SCAN_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Finding:
    """One secret found. Carries no matched value, by construction."""

    path: str
    line: int
    pattern: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}  [{self.pattern}]"


class GitUnavailable(Exception):
    """git could not be run, so the candidate file list is unknown.

    Raised rather than swallowed, because an empty file list is indistinguishable
    from a clean tree. Silently scanning nothing and printing OK is the one
    outcome this gate must never produce.
    """


def git_files(root: Path, *args: str) -> list[str]:
    """Run one `git ls-files` variant and return its paths.

    `-z` because a path may contain a newline, and splitting on one would turn a
    single file into two bogus paths.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", *args],
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # git absent from PATH, or not executable
        raise GitUnavailable(f"could not run git: {exc}") from exc
    if result.returncode != 0:
        raise GitUnavailable(
            f"git ls-files failed ({result.returncode}): {result.stderr.strip()}"
        )
    return [entry for entry in result.stdout.split("\0") if entry]


def candidate_files(root: Path) -> list[str]:
    """Tracked files plus untracked ones git does not ignore, deduplicated.

    Both halves matter. Tracked catches what is already committed; untracked
    catches the `.env` sitting in the tree right now, which is the finding this
    gate was written for.

    `--exclude-standard` honors the caller's real git config, including a global
    excludes file. That is deliberate: the gate asks whether a file is one
    `git add -A` from a commit, and a globally ignored file is not. The cost is
    that a repository relying on one developer's global ignore to hide a `.env`
    reads clean for that developer and dirty for everyone else. Reporting it
    anyway would be the louder gate and the wrong answer to the question asked.
    """
    tracked = git_files(root)
    untracked = git_files(root, "--others", "--exclude-standard")
    return sorted(set(tracked) | set(untracked))


def is_excluded(path: str) -> bool:
    """True when a path sits somewhere a key would not be hand-written.

    Both directory rules test `parts[:-1]`, the DIRECTORY components only. Testing
    every part would match a plain file named `build`, `dist`, or `vendor`, and a
    real key inside it would be skipped in silence. An extensionless `build` file
    is an ordinary thing for a repository to hold.
    """
    directories = Path(path).parts[:-1]
    if any(part in EXCLUDED_DIRS for part in directories):
        return True
    if any(part in FIXTURE_DIR_NAMES for part in directories):
        return True
    name = Path(path).name
    return any(fnmatch.fnmatch(name, glob) for glob in EXCLUDED_GLOBS)


def has_secret_name(path: str) -> bool:
    name = Path(path).name
    if name in SECRET_NAME_ALLOWED:
        return False
    return any(fnmatch.fnmatch(name, glob) for glob in SECRET_NAME_GLOBS)


def content_findings(root: Path, path: str) -> list[Finding]:
    """Scan one file for prefixed key formats.

    An unreadable or binary file yields nothing rather than raising: a gate that
    dies on a stray binary reports neither that file nor the ones after it.
    """
    full = root / path
    try:
        if full.stat().st_size > MAX_SCAN_BYTES:
            return []
        text = full.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, pattern in CONTENT_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path, lineno, name))
    return findings


def check(root: Path, extra_excludes: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in candidate_files(root):
        if is_excluded(path):
            continue
        if any(fnmatch.fnmatch(path, glob) for glob in extra_excludes):
            continue
        if has_secret_name(path):
            findings.append(Finding(path, 0, "secret-file-name"))
        findings.extend(content_findings(root, path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Path glob to skip; repeatable",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return 2
    if not (root / ".git").exists():
        print(f"ERROR: {root} is not a git repository", file=sys.stderr)
        return 2

    try:
        findings = check(root, args.exclude)
    except GitUnavailable as exc:
        # Exit 2, never 1. Exit 1 means "secrets found", and reporting a finding
        # the gate never looked for is as wrong as missing a real one.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for finding in findings:
        print(finding)

    if findings:
        print(f"\n{len(findings)} secret findings")
        return 1
    print("OK: no secret files and no prefixed key formats found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
