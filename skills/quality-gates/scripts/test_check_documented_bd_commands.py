#!/usr/bin/env python3
"""Regression suite for check_documented_bd_commands.py.

Stdlib only, no install, mirroring test_check_doc_paths.py. Run with:
    python3 skills/quality-gates/scripts/test_check_documented_bd_commands.py

Every case runs the checker against a throwaway repository and a stub `bd`
placed first on PATH, so the suite never touches the real tracker and never
depends on which bd version is installed. The stub records every invocation,
which is what lets a case assert that a line was skipped rather than run:
"skipped" is a claim about what did NOT happen, and only a recording proves it.

Each acceptance criterion of tadw-epi has a case here, named in its check line.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_documented_bd_commands.py"
REPO = Path(__file__).resolve().parents[3]

passed = 0
failed = 0


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


# A bd that exits 0 on everything and appends each invocation's arguments to
# invocations.log beside itself.
RECORDING_BD = """\
#!/usr/bin/env sh
echo "$@" >> "$(dirname "$0")/invocations.log"
exit 0
"""

# A bd that rejects --limit the way the real one rejected it on `bd blocked`,
# which is the defect that motivated this checker (tadw-pdi).
REJECTING_BD = """\
#!/usr/bin/env sh
for arg in "$@"; do
  if [ "$arg" = "--limit" ]; then
    echo "Error: unknown flag: --limit" >&2
    exit 1
  fi
done
exit 0
"""


def build(doc_body: str, bd_body: str | None = RECORDING_BD) -> tuple[Path, dict[str, str]]:
    """A throwaway repository plus the environment that runs it.

    Returns (root, env). The stub bd lives outside the repository so the doc
    walk never sees it, and it is first on PATH so it shadows any real bd.
    bd_body=None builds an environment with no bd at all.
    """
    root = Path(tempfile.mkdtemp())
    (root / "README.md").write_text(doc_body, encoding="utf-8")
    env = dict(os.environ)
    bin_dir = Path(tempfile.mkdtemp())
    if bd_body is not None:
        stub = bin_dir / "bd"
        stub.write_text(bd_body, encoding="utf-8")
        stub.chmod(0o755)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    else:
        env["PATH"] = str(bin_dir)
    env["TADW_BD_BIN"] = str(bin_dir)
    return root, env


def run(root: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(root), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def invocations(env: dict[str, str]) -> list[str]:
    log = Path(env["TADW_BD_BIN"]) / "invocations.log"
    if not log.is_file():
        return []
    return log.read_text(encoding="utf-8").splitlines()


def fenced(*lines: str) -> str:
    return "Text.\n\n```bash\n" + "\n".join(lines) + "\n```\n"


print("\n  [criterion 1: a documented command bd rejects is a named failure]")


def case_rejected_command_fails() -> None:
    root, env = build(fenced("bd blocked --json --limit 0"), REJECTING_BD)
    r = run(root, env)
    assert r.returncode == 1, f"a rejected command must exit 1, got {r.returncode}: {r.stdout}"
    assert "README.md:4" in r.stdout, f"the failure must name file and line: {r.stdout}"
    assert "bd blocked --json --limit 0" in r.stdout, f"the failure must show the command: {r.stdout}"
    assert "unknown flag: --limit" in r.stdout, f"the failure must carry bd's own error: {r.stdout}"


check("a fenced command bd rejects exits 1 with file, line, and bd's error", case_rejected_command_fails)


print("\n  [criterion 2: prose is not a command]")


def case_inline_backtick_is_prose() -> None:
    root, env = build("Run `bd show` to inspect an issue.\n")
    r = run(root, env)
    assert r.returncode == 0, f"inline backticks are prose, got exit {r.returncode}: {r.stdout}"
    assert not invocations(env), f"prose must run nothing: {invocations(env)}"


check("a bd mention in inline backticks runs nothing, exit 0", case_inline_backtick_is_prose)


print("\n  [criterion 3: what cannot run verbatim is skipped, and writes never run]")


def case_placeholder_write_is_skipped() -> None:
    root, env = build(fenced("bd update <id> --claim"))
    r = run(root, env)
    assert r.returncode == 0, f"a skipped line is not a failure, got {r.returncode}: {r.stdout}"
    assert not invocations(env), f"a placeholder write must never run: {invocations(env)}"
    assert "1 lines skipped" in r.stdout, f"the skipped count must be reported: {r.stdout}"


def case_safelisted_verb_with_placeholder_is_skipped() -> None:
    root, env = build(fenced("bd show <id> --json"))
    r = run(root, env)
    assert not invocations(env), f"a placeholder must skip even a read verb: {invocations(env)}"
    assert "1 lines skipped" in r.stdout, f"the skipped count must be reported: {r.stdout}"


def case_write_verb_without_placeholder_is_skipped() -> None:
    root, env = build(fenced("bd dolt push"))
    r = run(root, env)
    assert not invocations(env), f"a verb off the safelist must never run: {invocations(env)}"
    assert r.returncode == 0, f"a skipped write is not a failure: {r.stdout}"


def case_pipe_is_skipped() -> None:
    root, env = build(fenced("bd list --json | head -3"))
    r = run(root, env)
    assert not invocations(env), f"a pipe cannot run verbatim: {invocations(env)}"


def case_unbalanced_quote_is_skipped() -> None:
    root, env = build(fenced('bd search "unfinished'))
    r = run(root, env)
    assert r.returncode == 0, f"an unparsable line is skipped, not a crash: {r.stderr}"
    assert not invocations(env), f"an unparsable line must never run: {invocations(env)}"


for name, fn in [
    ("a placeholder write is skipped and counted [criterion 3]", case_placeholder_write_is_skipped),
    ("a placeholder skips even a safelisted verb", case_safelisted_verb_with_placeholder_is_skipped),
    ("a verb off the safelist never runs", case_write_verb_without_placeholder_is_skipped),
    ("a piped command never runs", case_pipe_is_skipped),
    ("an unbalanced quote is skipped, never a crash", case_unbalanced_quote_is_skipped),
]:
    check(name, fn)


print("\n  [what does run, runs the way the block wrote it]")


def case_safelisted_command_runs() -> None:
    root, env = build(fenced("bd list --status=open --json"))
    r = run(root, env)
    assert invocations(env) == ["list --status=open --json"], (
        f"the command must run with its documented arguments: {invocations(env)}"
    )
    assert r.returncode == 0, f"a passing command exits 0: {r.stdout}"


def case_prompt_prefix_and_comment() -> None:
    root, env = build(fenced("$ bd ready --json   # find available work"))
    r = run(root, env)
    assert invocations(env) == ["ready --json"], (
        f"the $ prompt and the trailing comment must be stripped: {invocations(env)}"
    )
    assert r.returncode == 0, r.stdout


def case_duplicate_command_runs_once_reports_each() -> None:
    body = fenced("bd blocked --json --limit 0") + "\nMore.\n" + fenced("bd blocked --json --limit 0")
    root, env = build(body, REJECTING_BD)
    r = run(root, env)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("README.md:")]
    assert len(lines) == 2, f"both documented locations must be named: {r.stdout}"
    assert "1 unique commands ran" in r.stdout, f"one unique command, run once: {r.stdout}"


for name, fn in [
    ("a safelisted fenced command runs verbatim", case_safelisted_command_runs),
    ("a $-prompt prefix and a trailing comment are stripped", case_prompt_prefix_and_comment),
    ("a command documented twice runs once and is reported at each line", case_duplicate_command_runs_once_reports_each),
]:
    check(name, fn)


print("\n  [criterion 5: a missing bd warns and allows]")


def case_missing_bd_warns() -> None:
    root, env = build(fenced("bd list --json"), bd_body=None)
    r = run(root, env)
    assert r.returncode == 0, f"a missing bd must exit 0, got {r.returncode}: {r.stderr}"
    assert "bd is not on PATH" in r.stderr, f"the warning must name bd: {r.stderr}"
    assert "no documented command was verified" in r.stderr, (
        f"the warning must say nothing was verified: {r.stderr}"
    )


check("no bd on PATH warns that nothing was verified, exit 0", case_missing_bd_warns)


print("\n  [operator errors are loud, never a silent pass]")


def case_missing_document() -> None:
    root, env = build("x")
    r = run(root, env, "no-such-doc.md")
    assert r.returncode == 2, f"a named document that is absent must exit 2, got {r.returncode}"


def case_bad_root() -> None:
    r = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", "/no/such/dir"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, f"a bad root must exit 2, got {r.returncode}"


for name, fn in [
    ("a named document that does not exist exits 2", case_missing_document),
    ("a repo root that does not exist exits 2", case_bad_root),
]:
    check(name, fn)


print("\n  [the shipped artifact]")


def case_symlinked_doc_counts_once() -> None:
    """CLAUDE.md in this repository is a symlink to AGENTS.md; the same block
    must not run and count twice."""
    root, env = build(fenced("bd list --json"))
    (root / "CLAUDE.md").symlink_to(root / "README.md")
    r = run(root, env)
    assert len(invocations(env)) == 1, (
        f"a symlinked document is the same document: {invocations(env)}"
    )
    assert r.returncode == 0, r.stdout


def case_real_repo() -> None:
    """Criterion 4: the repository as it stands passes. Real PATH, so this uses
    the real bd where installed and the missing-bd path where not; both exit 0
    when the documents are sound."""
    r = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(REPO)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"this repository must be clean:\n{r.stdout}\n{r.stderr}"


def case_registered_in_gate_and_hook() -> None:
    """Criterion 7: both the check list and the pre-push hook name the script
    and this suite."""
    claude_md = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    hook = (REPO / ".githooks" / "pre-push").read_text(encoding="utf-8")
    for text, where in ((claude_md, "CLAUDE.md"), (hook, ".githooks/pre-push")):
        assert "check_documented_bd_commands.py" in text, f"{where} must name the checker"
        assert "test_check_documented_bd_commands.py" in text, f"{where} must name this suite"


for name, fn in [
    ("a symlinked document runs its block once", case_symlinked_doc_counts_once),
    ("this repository's own documented bd commands all pass [criterion 4]", case_real_repo),
    ("CLAUDE.md and .githooks/pre-push both register the check [criterion 7]", case_registered_in_gate_and_hook),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
