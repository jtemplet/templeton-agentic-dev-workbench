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
    """Create an open bead on main and a feature commit in its linked worktree."""
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
    checked(main, "bd", "export", "-o", EXPORT, env=env)

    # bd init creates local integrations that are not needed by the fixture.
    # Stage the generated repository state so the main checkout starts clean.
    git(main, "add", "--all", env=env)
    git(main, "add", "--force", "--", EXPORT, env=env)
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


def issue_status_in(commit: str, main: Path, env: dict[str, str]) -> str | None:
    exported = git(main, "show", f"{commit}:{EXPORT}", env=env).stdout
    for line in exported.splitlines():
        issue = json.loads(line)
        if issue.get("id") == BEAD_ID:
            return issue.get("status")
    return None


def export_only_commits(landing: str, main: Path, env: dict[str, str]) -> list[str]:
    commits = git(
        main,
        "log",
        "--format=%H",
        f"{landing}..refs/heads/main",
        env=env,
    ).stdout.splitlines()
    export_only = []
    for commit in commits:
        paths = git(
            main,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
            env=env,
        ).stdout.splitlines()
        if paths == [EXPORT]:
            export_only.append(commit)
    return export_only


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
        status = issue_status_in(landing, main, env)
        later_export_commits = export_only_commits(landing, main, env)

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
            f"landing commit carries the bead as {status!r} in {EXPORT}"
            if status == "closed"
            else f"landing commit has bead status {status!r} in {EXPORT}; expected 'closed'",
        ),
        (
            not later_export_commits,
            f"no later commit changes only {EXPORT}"
            if not later_export_commits
            else "later commits change only "
            f"{EXPORT}: {', '.join(commit[:12] for commit in later_export_commits)}",
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
