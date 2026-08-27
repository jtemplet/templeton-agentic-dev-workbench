#!/usr/bin/env python3
"""Report the live processes whose working directory sits inside a worktree.

Step 5 of the ship skill removes the worktree holding the branch it just landed,
and that skill says outright it "often runs inside the worktree it deletes". The
directory goes away; the session standing in it does not. What follows is quiet
rather than loud: `$CLAUDE_PROJECT_DIR` names a path that no longer exists, the
bead-label hook guards on `test -x <script>` and no-ops, and the session labels
nothing and writes no log line, because the script that writes the log is the
file that vanished. Nobody is told. That is tadw-t1u, and tadw-1rf is the guard
that made it quiet.

So this reports, and does nothing else. It never kills a process, never removes
a directory, and never refuses: `/tadw:ship` runs unattended, and the session it
would refuse for is usually its own caller. The operator decides.

EXIT CODES. 0 means nobody occupies the worktree, and the caller removes it with
no warning printed. 1 means somebody does, and the caller prints the report and
still removes it. 2 is operator error, and never 1: a "nobody is there" answer
that no measurement produced is the failure this whole script exists to prevent.

WHY ONE `lsof` AND NOT `pgrep`. The bead's design recorded what worked by hand:
`pgrep -f 'dangerously-skip-permissions'`, then `lsof -a -p <pid> -d cwd -Fn` for
each hit. That narrows to Claude sessions started with one flag, and the harm is
not specific to Claude: any shell, editor, or test runner left in the directory
is equally stranded. `lsof -d cwd -Fpn` dumps every visible process's working
directory in one call, about 0.4 seconds for 550 processes on the machine this
was written against, so the pre-filter buys nothing and costs coverage.

KNOWN BOUNDARY. `lsof` shows only the processes the invoking user may see.
Another user's session inside the worktree is invisible here without root, and
this does not escalate to find one. The operator this serves is the one running
the ship, and their own sessions are the ones that go quiet.

PATH MATCHING IS BY COMPONENT, NEVER BY PREFIX STRING. `/w/feature` and
`/w/feature-2` share a string prefix and are different worktrees; reporting the
second when removing the first is a false warning, which criterion 4 forbids.
Both sides are resolved first, because a worktree under `/tmp` on macOS answers
to `/private/tmp` in `lsof` output and a string compare would miss every hit.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_UNOCCUPIED = 0
EXIT_OCCUPIED = 1
EXIT_OPERATOR_ERROR = 2

LSOF_TIMEOUT_SECONDS = 30


class LsofUnavailable(RuntimeError):
    """`lsof` is missing, unrunnable, or took too long to answer."""


def process_cwds() -> dict[int, str]:
    """Every visible process id mapped to its working directory.

    `lsof -F` writes one field per line, tagged by its first character: `p` opens
    a process record, and `n` carries the path of the file that record's later
    fields describe. `-d cwd` keeps only the working-directory entry, so each
    process contributes at most one path.
    """
    if shutil.which("lsof") is None:
        raise LsofUnavailable("lsof is not on PATH, so no process could be checked")
    try:
        result = subprocess.run(
            ["lsof", "-d", "cwd", "-Fpn"],
            capture_output=True,
            text=True,
            timeout=LSOF_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise LsofUnavailable(
            f"lsof did not answer within {LSOF_TIMEOUT_SECONDS} seconds"
        ) from exc
    except OSError as exc:
        raise LsofUnavailable(f"lsof could not be run: {exc}") from exc

    # A non-zero exit is normal here. lsof reports 1 when it could not read some
    # process it saw, which happens on any machine with processes owned by root,
    # and it still prints every record it did read. Empty output is the real
    # failure, because that is the answer nothing produced.
    if not result.stdout.strip():
        raise LsofUnavailable(
            f"lsof reported no process at all (exit {result.returncode})"
        )

    cwds: dict[int, str] = {}
    pid: int | None = None
    for line in result.stdout.splitlines():
        if not line:
            continue
        tag, value = line[0], line[1:]
        if tag == "p":
            pid = int(value) if value.isdigit() else None
        elif tag == "n" and pid is not None:
            cwds.setdefault(pid, value)
    return cwds


def occupants(worktree: Path, cwds: dict[int, str]) -> list[tuple[int, str]]:
    """The (pid, cwd) pairs standing in `worktree` or below it, lowest pid first.

    The worktree itself counts, and so does any directory under it. A path that
    merely starts with the same characters does not.
    """
    found = []
    for pid, raw in sorted(cwds.items()):
        try:
            candidate = Path(raw).resolve()
        except OSError:
            continue
        if candidate == worktree or worktree in candidate.parents:
            found.append((pid, raw))
    return found


def command_name(pid: int) -> str:
    """The process's command, or "unknown" when it exits before we ask."""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--worktree",
        required=True,
        metavar="PATH",
        help="Worktree about to be removed",
    )
    args = parser.parse_args()

    raw = args.worktree.strip()
    if not raw:
        print("ERROR: --worktree must name a path", file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    worktree = Path(raw).resolve()
    if not worktree.is_dir():
        print(f"ERROR: --worktree {worktree} is not a directory", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    try:
        found = occupants(worktree, process_cwds())
    except LsofUnavailable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    if not found:
        print(f"OK: no live process has {worktree} as its working directory")
        return EXIT_UNOCCUPIED

    subject = (
        "1 live process stands"
        if len(found) == 1
        else f"{len(found)} live processes stand"
    )
    print(f"WARNING: {subject} in {worktree}:")
    for pid, raw_cwd in found:
        print(f"  pid {pid} ({command_name(pid)}) cwd {raw_cwd}")
    print(
        "\nRemoving the worktree does not stop them. A Claude session left open "
        "there keeps running, labels no bead, and writes no log line, because "
        "the hook script it calls is inside the directory being removed. End "
        "those sessions, or restart them somewhere that still exists."
    )
    return EXIT_OCCUPIED


if __name__ == "__main__":
    sys.exit(main())
