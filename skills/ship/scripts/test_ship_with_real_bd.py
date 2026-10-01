#!/usr/bin/env python3
"""Check the full ship workflow against a real bd installation.

Run locally with:
    python3 skills/ship/scripts/test_ship_with_real_bd.py

This test is intentionally absent from CI because CI does not install bd. It
skips with a clear message when bd is not on PATH.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SHIP = REPO / "bin" / "tadw-ship"
EXPORT = ".beads/issues.jsonl"
BEAD_ID = "shiptest-1"
BRANCH = f"feat/{BEAD_ID}"
SESSION_ACTOR = "Ship integration test (session abc)"


def isolated_environment(home: Path) -> dict[str, str]:
    """Keep the fixture's bd and Git settings out of the user's home config."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("BD_", "BEADS_", "TADW_SHIP_"))
    }
    environment.update(
        {
            "HOME": str(home),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Ship integration test",
            "GIT_AUTHOR_EMAIL": "ship-test@example.test",
            "GIT_COMMITTER_NAME": "Ship integration test",
            "GIT_COMMITTER_EMAIL": "ship-test@example.test",
        }
    )
    return environment


def command(
    directory: Path, *arguments: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run a command in the fixture and retain its output for a useful failure."""
    return subprocess.run(
        arguments,
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=120,
    )


def checked(
    directory: Path, *arguments: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    completed = command(directory, *arguments, env=env)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{shlex.join(arguments)} exited {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def git(directory: Path, *arguments: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return checked(directory, "git", *arguments, env=env)


def make_repository(main: Path, worktree: Path, env: dict[str, str]) -> None:
    """Create a bead on main, claimed by a session, and a feature commit in its linked worktree.

    Git ignores the tracker export, and the main checkout holds one on disk.
    """
    main.mkdir()
    git(main, "init", "--quiet", "--initial-branch=main", env=env)
    git(main, "config", "user.name", "Ship integration test", env=env)
    git(main, "config", "user.email", "ship-test@example.test", env=env)
    git(main, "config", "core.hooksPath", os.devnull, env=env)

    checked(
        main,
        "bd",
        "init",
        "--non-interactive",
        "--agents-profile",
        "minimal",
        "--prefix",
        "shiptest",
        env=env,
    )
    checked(main, "bd", "config", "set", "export.auto", "true", env=env)
    checked(main, "bd", "config", "set", "export.interval", "1s", env=env)
    checked(
        main,
        "bd",
        "create",
        "Ship integration test",
        "--id",
        BEAD_ID,
        "--type",
        "task",
        "--description",
        "A scratch bead for the real-bd ship test.",
        env=env,
    )
    # `/build` claims a bead under a session actor, and `bd` refuses a close by anyone else.
    checked(main, "bd", "update", BEAD_ID, "--claim", "--actor", SESSION_ACTOR, env=env)
    checked(main, "bd", "export", "-o", EXPORT, env=env)

    with (main / ".gitignore").open("a", encoding="utf-8") as ignored:
        ignored.write(f"\n{EXPORT}\n")

    # bd init creates local integrations that are not needed by the fixture.
    # Stage the generated repository state so the main checkout starts clean.
    git(main, "add", "--all", env=env)
    git(main, "commit", "--quiet", "-m", "Fixture base", env=env)

    git(
        main,
        "worktree",
        "add",
        "--quiet",
        "-b",
        BRANCH,
        str(worktree),
        "main",
        env=env,
    )
    (worktree / "feature.txt").write_text("shipped\n", encoding="utf-8")
    git(worktree, "add", "feature.txt", env=env)
    git(worktree, "commit", "--quiet", "-m", "Add feature", env=env)


def ship(env: dict[str, str], worktree: Path) -> subprocess.CompletedProcess[str]:
    """Run the user-facing executable with a trivial, explicit gate."""
    return subprocess.run(
        [str(SHIP), BEAD_ID, "--repo-root", str(worktree)],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
        env={**env, "TADW_SHIP_CHECK": "true"},
        timeout=120,
    )


def porcelain_paths(output: str) -> list[str]:
    return sorted(line[3:] for line in output.splitlines() if len(line) >= 4)


def exported_status(main: Path) -> str | None:
    """The bead's status in the main checkout's export file."""
    for line in (main / EXPORT).read_text(encoding="utf-8").splitlines():
        issue = json.loads(line)
        if issue.get("id") == BEAD_ID:
            return issue.get("status")
    return None


def tracks_export(commit: str, main: Path, env: dict[str, str]) -> bool:
    listed = git(main, "ls-tree", "-r", "--name-only", commit, "--", EXPORT, env=env).stdout
    return bool(listed.strip())


def run_real_bd_check(bd_path: str) -> int:
    with tempfile.TemporaryDirectory(prefix="tadw-ship-real-bd-") as directory:
        scratch = Path(directory)
        home = scratch / "home"
        home.mkdir()
        main = scratch / "main"
        worktree = scratch / "worktree"
        env = isolated_environment(home)
        env["PATH"] = f"{Path(bd_path).parent}{os.pathsep}{env['PATH']}"
        make_repository(main, worktree, env)

        # The auto-export throttle is measured from bd create. Let its one-second
        # interval expire so it cannot hide the close that ship performs late.
        time.sleep(1.1)
        result = ship(env, worktree)
        lines = result.stdout.splitlines()
        machine_line = next((line for line in reversed(lines) if line.startswith("SHIP_")), None)
        if (
            result.returncode != 0
            or machine_line is None
            or not machine_line.startswith("SHIP_DONE ")
        ):
            print(
                "FAIL - ship did not finish successfully: "
                f"exit={result.returncode}, last machine line={machine_line!r}; "
                f"stdout={result.stdout!r}; stderr={result.stderr!r}"
            )
            return 1

        landing = machine_line.removeprefix("SHIP_DONE ")
        dirty = porcelain_paths(
            git(main, "status", "--porcelain", "--untracked-files=all", env=env).stdout
        )
        status = exported_status(main)
        export_tracked = tracks_export(landing, main, env)

    print(f"bd: {bd_path}")
    checks = [
        (
            not dirty,
            "SHIP_DONE leaves the default checkout clean"
            if not dirty
            else f"SHIP_DONE leaves the default checkout dirty: {', '.join(dirty)}",
        ),
        (
            status == "closed",
            f"the main checkout's {EXPORT} holds the bead as {status!r}"
            if status == "closed"
            else f"the main checkout's {EXPORT} holds the bead as {status!r}; expected 'closed'",
        ),
        (
            not export_tracked,
            f"the landing commit does not carry {EXPORT}"
            if not export_tracked
            else f"the landing commit carries {EXPORT}",
        ),
    ]
    for passed, message in checks:
        print(f"{'PASS' if passed else 'FAIL'} - {message}")
    return 0 if all(passed for passed, _ in checks) else 1


def main() -> int:
    bd_path = shutil.which("bd")
    if bd_path is None:
        print("SKIP - real-bd ship test: bd is not on PATH")
        return 0
    try:
        return run_real_bd_check(bd_path)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL - could not complete the real-bd ship test: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
