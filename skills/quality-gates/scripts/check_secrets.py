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

# Default size above which the content scan skips a file. 2 MiB is far above any
# source file and far below a data dump, and reading a dump stalls the gate.
# Skipping is a default, not a rule: `--no-skip-large-files` scans everything,
# because a key CAN sit in a generated config dump even though nobody typed it
# there. Whatever is skipped gets named in the report, since a gate that prints
# OK without saying what it did not read has overstated its own result.
MAX_SCAN_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Finding:
    """One secret found. Carries no matched value, by construction."""

    path: str
    line: int
    pattern: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}  [{self.pattern}]"


@dataclass(frozen=True)
class Skipped:
    """One file the content scan did not read, and why.

    Reported rather than counted silently. "OK" after an unexamined file is a
    claim the gate has not earned, and the reader cannot see the gap otherwise.
    """

    path: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}  ({self.reason})"


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


def content_findings(
    root: Path,
    path: str,
    *,
    skip_large_files: bool,
    max_scan_bytes: int,
) -> tuple[list[Finding], Skipped | None]:
    """Scan one file for prefixed key formats.

    Returns the findings, plus a Skipped when the file was never read. An
    unreadable or undecodable file yields no exception: a gate that dies on a
    stray binary reports neither that file nor the ones after it. It does yield a
    Skipped, so the omission reaches the report instead of vanishing.
    """
    full = root / path
    try:
        if skip_large_files and full.stat().st_size > max_scan_bytes:
            return [], Skipped(path, f"over {max_scan_bytes} bytes")
        text = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], Skipped(path, "not valid UTF-8")
    except OSError as exc:
        return [], Skipped(path, exc.strerror or "unreadable")

    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, pattern in CONTENT_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path, lineno, name))
    return findings, None


def check(
    root: Path,
    extra_excludes: list[str],
    *,
    skip_large_files: bool = True,
    max_scan_bytes: int = MAX_SCAN_BYTES,
) -> tuple[list[Finding], list[Skipped]]:
    findings: list[Finding] = []
    skipped: list[Skipped] = []
    for path in candidate_files(root):
        if is_excluded(path):
            continue
        if any(fnmatch.fnmatch(path, glob) for glob in extra_excludes):
            continue
        if has_secret_name(path):
            findings.append(Finding(path, 0, "secret-file-name"))
        file_findings, missed = content_findings(
            root,
            path,
            skip_large_files=skip_large_files,
            max_scan_bytes=max_scan_bytes,
        )
        findings.extend(file_findings)
        if missed is not None:
            skipped.append(missed)
    return findings, skipped


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
    parser.add_argument(
        "--no-skip-large-files",
        dest="skip_large_files",
        action="store_false",
        help="Scan large files too, instead of skipping them",
    )
    parser.add_argument(
        "--max-scan-bytes",
        type=int,
        default=MAX_SCAN_BYTES,
        metavar="N",
        help=f"Skip files larger than N bytes (default {MAX_SCAN_BYTES})",
    )
    parser.set_defaults(skip_large_files=True)
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return 2
    if not (root / ".git").exists():
        print(f"ERROR: {root} is not a git repository", file=sys.stderr)
        return 2
    if args.max_scan_bytes < 1:
        print("ERROR: --max-scan-bytes must be 1 or more", file=sys.stderr)
        return 2

    try:
        findings, skipped = check(
            root,
            args.exclude,
            skip_large_files=args.skip_large_files,
            max_scan_bytes=args.max_scan_bytes,
        )
    except GitUnavailable as exc:
        # Exit 2, never 1. Exit 1 means "secrets found", and reporting a finding
        # the gate never looked for is as wrong as missing a real one.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for finding in findings:
        print(finding)

    # Printed before the verdict, so the reader sees the gap before the word OK.
    # A skip is not a finding and does not change the exit status: a repository
    # holding one undecodable file would otherwise fail this gate forever.
    if skipped:
        print(f"\n{len(skipped)} files not scanned for key formats:")
        for missed in skipped:
            print(f"  {missed}")

    if findings:
        print(f"\n{len(findings)} secret findings")
        return 1
    if skipped:
        print("OK: no secret files, and no prefixed key formats in what was scanned")
        return 0
    print("OK: no secret files and no prefixed key formats found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
