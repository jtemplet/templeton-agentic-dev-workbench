#!/usr/bin/env python3
"""Measure a gate command: how many check processes it starts and how long it takes.

This is the repeatable baseline method for the deterministic ship plan. Run the
current workflow's gate command through it, keep the JSON, and run the new
command the same way later. The two files are then comparable line for line.

HOW A CHECK PROCESS IS COUNTED. The script puts a directory of shims first on
`PATH`, one per tool name. A shim appends one line to a log and then runs the
real tool, so every start of a named tool counts once, whichever process starts
it. A process that names its tool by absolute path, or through `sys.executable`,
does not pass a shim and is not counted. `--tool` chooses the names; the default
covers the tools the AGENTS.md check list starts.

WARM AND COLD. `--warmup N` runs the command N times first and discards those
runs. Use `--warmup 0` for a cold measurement, taken after the operator clears
whatever caches matter, and `--warmup 1` for a warm one. Report them separately.

Exit status: 0 when every measured run of the command exited 0, 1 when any did
not (the measurements are still printed), 2 on operator error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXIT_OK = 0
EXIT_COMMAND_FAILED = 1
EXIT_OPERATOR_ERROR = 2

DEFAULT_TOOLS = ("rumdl", "node", "python3", "bash", "claude")
LOG_VARIABLE = "TADW_BASELINE_LOG"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.runs < 1 or args.warmup < 0:
        print("measure_gate_baseline: --runs must be at least 1 and --warmup at least 0",
              file=sys.stderr)
        return EXIT_OPERATOR_ERROR
    if not Path(args.repo_root).is_dir():
        print(f"measure_gate_baseline: not a directory: {args.repo_root}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    with tempfile.TemporaryDirectory() as scratch:
        shim_dir = Path(scratch) / "shims"
        shim_dir.mkdir()
        missing = write_shims(shim_dir, args.tool)
        for _ in range(args.warmup):
            time_command(args, scratch, shim_dir)
        runs = [time_command(args, scratch, shim_dir) for _ in range(args.runs)]

    report = {
        "command": args.command,
        "tools": sorted(set(args.tool) - set(missing)),
        "tools_not_found": missing,
        "warmup": args.warmup,
        "runs": runs,
        "median_seconds": round(statistics.median(run["seconds"] for run in runs), 3),
        "median_processes": statistics.median(run["processes"] for run in runs),
    }
    print(json.dumps(report, indent=2))
    return EXIT_OK if all(run["exit_code"] == 0 for run in runs) else EXIT_COMMAND_FAILED


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".", help="directory the command runs in")
    parser.add_argument("--runs", type=int, default=3, help="measured runs (default 3)")
    parser.add_argument("--warmup", type=int, default=0, help="discarded runs before measuring")
    parser.add_argument("--tool", action="append", default=None,
                        help="tool name to count; repeatable (default: the AGENTS.md tools)")
    parser.add_argument("--command", required=True, help="gate command, run through the shell")
    args = parser.parse_args(argv)
    args.tool = args.tool or list(DEFAULT_TOOLS)
    return args


def write_shims(shim_dir: Path, tools: list[str]) -> list[str]:
    """Write one counting shim per tool found on PATH; return the names not found."""
    missing = []
    for tool in tools:
        real = shutil.which(tool)
        if real is None:
            missing.append(tool)
            continue
        shim = shim_dir / tool
        body = f'#!/bin/sh\nprintf \'%s\\n\' "{tool}" >> "${LOG_VARIABLE}"\nexec "{real}" "$@"\n'
        shim.write_text(body, encoding="utf-8")
        shim.chmod(0o755)
    return missing


def time_command(args: argparse.Namespace, scratch: str, shim_dir: Path) -> dict:
    log = Path(scratch) / "processes.log"
    log.write_text("", encoding="utf-8")
    environment = {**os.environ, "PATH": f"{shim_dir}{os.pathsep}{os.environ['PATH']}",
                   LOG_VARIABLE: str(log)}
    started = time.monotonic()
    completed = subprocess.run(args.command, shell=True, cwd=args.repo_root, env=environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    seconds = time.monotonic() - started
    started_tools = log.read_text(encoding="utf-8").split()
    return {
        "seconds": round(seconds, 3),
        "processes": len(started_tools),
        "by_tool": {tool: started_tools.count(tool) for tool in sorted(set(started_tools))},
        "exit_code": completed.returncode,
    }


if __name__ == "__main__":
    sys.exit(main())
