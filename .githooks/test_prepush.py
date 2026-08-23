#!/usr/bin/env python3
"""Regression suite for .githooks/pre-push.

Stdlib only, no install, mirroring the gate-script suites. Run with:
    python3 .githooks/test_prepush.py

Every behavioral case builds a throwaway repository from this repository's own
tracked tree, points `core.hooksPath` at the hook under test, and runs a real
`git push --dry-run` into a bare remote beside it. The hook is therefore driven
by git, with git's own stdin format and environment, rather than called directly.

WHY THE FIXTURE LIVES UNDER /tmp. `rumdl fmt --check .` discovers no markdown
files at all under macOS's per-user TMPDIR (`/var/folders/...`), which is what
`mktemp -d` returns by default. A fixture there would make the first check pass
over zero files, and criterion 1 would fail for a reason with nothing to do with
the hook. `/tmp` walks correctly on both macOS and Linux.
`case_fixture_is_walkable_by_rumdl` is the positive control that keeps this
honest: it fails loudly rather than letting the suite pass vacuously.

WHY SIX CHECKS ARE STUBBED IN THE FIXTURE. Measured 2026-08-15, the six stubbed
commands account for about 29 of the hook's 32 seconds, and each already owns a
regression suite. What this suite tests is the hook's ORCHESTRATION: run the
whole list, aggregate every failure, warn by name on a missing tool, honor the
off-switch, and leave the tree alone. Stubbing keeps the suite near a minute
instead of near ten. The part stubbing cannot cover, which commands the hook
actually runs, is pinned separately and statically by
`case_command_list_matches_agents_md`.

RULE-TO-TEST MAPPING. A rule with no test here is a rule nothing holds.

  Bead criterion                                  Pinned by
  ------------------------------------------------------------------------------
  1. Broken formatting refuses the push,        case_broken_markdown_refuses_push
     and the output names that file
  2. TADW_PREPUSH=off lets it through           case_off_switch_allows_a_failing_push
  3. A missing tool warns by name and allows    case_missing_rumdl_warns_and_allows
  4. Two failures both appear                   case_two_failures_both_reported
  5. The CI workflow is untouched               case_hook_leaves_the_tree_alone
  6. A delete-only push runs no checks          case_delete_only_push_runs_nothing

  Design rule (docs/plans/quality-gates-hardening.md M2)
  ------------------------------------------------------------------------------
  The hook runs the AGENTS.md block, minus       case_command_list_matches_agents_md
    three documented exclusions
  A clean tree pushes, with one summary line     case_clean_push_is_quiet
    carrying both the count and the elapsed time
  One warning per missing tool, not per check    case_missing_python3_warns_once
  A run that checked nothing is not a pass      case_no_check_ran_is_not_a_pass
  A push carrying code IS gated, even when it   case_mixed_delete_and_update_runs_checks
    also deletes a ref
  POSIX sh, executable                          case_hook_is_executable_posix_sh

STAGE 2, the recorded quality-gates verdict (M4). Same fixture, same real
`git push --dry-run`, with a report planted in the fixture's own git directory.

  Bead criterion                                  Pinned by
  ------------------------------------------------------------------------------
  1. A FAIL verdict refuses the push, naming    case_fail_verdict_refuses_the_push
     the verdict, the head, and the timestamp
  2. No report means one warning and a push     case_no_report_warns_once_and_allows
  3. A verdict recorded for a commit that is    case_verdict_off_the_pushed_line_warns
     not being pushed warns and allows          case_verdict_for_an_unknown_head_warns
  4. A current PASS verdict is silent           case_current_pass_verdict_is_silent

  Design rule (docs/plans/quality-gates-hardening.md M4)
  ------------------------------------------------------------------------------
  Current means an ancestor of the pushed       case_ancestor_verdict_is_current
    commit, not the tip of it
  Every ref in the push is considered, not      case_a_verdict_current_for_one_pushed_ref_is_not_stale
    only the first
  Both stages report, each under its own        case_both_stages_report_separately
    message, from one push
  TADW_PREPUSH=off covers stage 2 too           case_off_switch_allows_a_failed_verdict
  An unreadable report is not a FAIL            case_unparseable_report_warns_and_allows
  The verdict is matched case-insensitively,    case_a_lowercase_verdict_still_blocks
    because getting it wrong fails open
  The verdict is read from the git directory    case_verdict_is_read_from_the_git_dir
    the command resolves, not a literal .git/
  A deletion is gated by neither stage          case_delete_only_push_ignores_a_fail_verdict

Criterion 5 has a second reading this suite cannot cover: that
`.github/workflows/lint.yml` is byte-identical to its state before this
milestone. That is a property of the change rather than of the hook, so it is
verified with `git diff` at review time. What is pinned here is the runtime
half, and the sharper risk: a hook that rewrites the tree it was asked to check.
Dropping `--check` from the rumdl line would reformat every markdown file during
a push, and `case_hook_leaves_the_tree_alone` is what catches that.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".githooks" / "pre-push"
AGENTS = REPO / "AGENTS.md"

# See "WHY THE FIXTURE LIVES UNDER /tmp" above. Falls back to the default when
# /tmp is not writable, in which case the rumdl control case reports the problem
# rather than the suite passing over zero files.
FIXTURE_ROOT = "/tmp" if os.access("/tmp", os.W_OK) else None

# The commands in the AGENTS.md block that the hook deliberately does not run.
# Each value is the reason, and each key is asserted to still be in AGENTS.md, so
# a stale exclusion cannot sit here unnoticed.
NOT_IN_HOOK = {
    "python3 evals/run.py": "every case is a real model call, too slow and too costly for a push",
    "python3 .githooks/test_prepush.py": "this suite pushes into a fixture wired to the hook, so it would recurse",
    "claude plugin validate .": "reference-transaction already gates this at the tag, and it is the slowest check",
}

# Stubbed in the fixture, not in the repository. Keys are paths, values are a
# body that exits 0 in that file's language.
SLOW_CHECKS = {
    "hooks/test-hooks.js": "process.exit(0)\n",
    "skills/quality-gates/scripts/test_check_secrets.py": "raise SystemExit(0)\n",
    "skills/quality-gates/scripts/test_check_hygiene.py": "raise SystemExit(0)\n",
    "skills/quality-gates/scripts/test_changed_set.py": "raise SystemExit(0)\n",
    "skills/quality-gates/scripts/test_route_qa.py": "raise SystemExit(0)\n",
    # About 11 seconds on its own: it starts real HTTP servers and waits on real
    # sockets, which is the only way to pin which host it addresses and that it
    # leaks no process. Every push case here would pay for that again.
    "skills/quality-gates/scripts/test_probe_api.py": "raise SystemExit(0)\n",
    # Builds git repositories in temp directories, the same shape as
    # test_changed_set.py above, and every push case here would pay for it again.
    "evals/test_run.py": "raise SystemExit(0)\n",
    # The heaviest of the lot at about 14 seconds: it builds a repository, and
    # often a merge or a worktree, for each of its cases. Same reason as the two
    # above. `git archive` restores its executable bit and write_text keeps it,
    # so the stub stays runnable as ./hooks/test-claude-scripts.sh.
    "hooks/test-claude-scripts.sh": "#!/usr/bin/env bash\nexit 0\n",
}

# One of the stubbed suites, restored to the only behavior that matters for the
# leaked-GIT_DIR case: build a git repository in a temp directory, with the same
# `-c` settings test_changed_set.py inits with. That is the whole mechanism, and
# it runs in milliseconds instead of the twenty seconds the real suites cost.
#
# Written as its own check rather than by passing stub_slow=False, so the case
# pins the HOOK's contract (no leaked GIT_DIR reaches a check) rather than the
# suites' own defense against the same leak. Both layers exist; this tests one.
GIT_FIXTURE_CANARY = """\
import subprocess
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(
        ["git", "-c", "core.excludesFile=/dev/null", "-C", tmp, "init", "-q"],
        check=True,
    )
raise SystemExit(0)
"""
GIT_FIXTURE_CANARY_PATH = "skills/quality-gates/scripts/test_changed_set.py"

# A file the fixture breaks to make rumdl fail. Tracked markdown, so it is in the
# tree rumdl walks, and named in the assertion so a reader can see what failed.
BREAKABLE_DOC = "README.md"
BAD_MARKDOWN = "#  Badly   formatted   heading\n\n\n*   an   item\n"

# The check to break when a case needs EXACTLY ONE failure. A test suite rather
# than a checker: every checker in the list also has a suite that runs it, so
# breaking a checker fails two checks at once and every count assertion drifts by
# one. Nothing runs a test suite but the hook.
BREAKABLE_CHECK = "skills/quality-gates/scripts/test_check_doc_paths.py"
FAILING_BODY = "raise SystemExit(1)\n"

# The timestamp every planted verdict carries. A fixed value, because the FAIL
# message has to name it and a generated one could not be asserted against.
RECORDED_AT = "2026-08-11T04:12:07Z"

GIT = shutil.which("git") or "git"

workspaces: list[Path] = []
passed = 0
failed = 0


@atexit.register
def _cleanup() -> None:
    for path in workspaces:
        shutil.rmtree(path, ignore_errors=True)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """A git command that must succeed. Fixture setup has no recoverable failure.

    A fixed identity and no global excludes file, so a case tests the hook rather
    than the machine it runs on, matching the three suites under
    skills/quality-gates/scripts. The excludes half is not decoration: a developer
    whose global gitignore names `.docpaths-ignore` gets a fixture whose `git add
    -A` silently drops it, because the file is untracked here even though it is
    tracked upstream. The tar still puts it on disk, so a check reading it from
    disk passes and only a checkout from the commit, such as a linked worktree,
    reveals the gap.
    """
    return subprocess.run(
        [GIT, "-c", "core.excludesFile=/dev/null", "-c", "user.email=t@t",
         "-c", "user.name=t", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )


class Fixture:
    """A throwaway clone of this repository's tracked tree, wired to the hook."""

    def __init__(self, work: Path) -> None:
        self.work = work

    def write(self, relative: str, body: str) -> None:
        path = self.work / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def commit_all(self, message: str = "work") -> None:
        git(self.work, "add", "-A")
        git(self.work, "commit", "-qm", message)

    def push(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        """A real `git push --dry-run`, which runs the hook exactly as git does."""
        environment = dict(os.environ)
        environment.update(env or {})
        return subprocess.run(
            [GIT, "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(self.work),
             "push", "--dry-run", "origin", *(args or ("main",))],
            capture_output=True,
            text=True,
            env=environment,
        )

    def tree_digest(self) -> str:
        """A hash of every TRACKED file's bytes, for proving the hook rewrites nothing.

        Tracked only, deliberately. rumdl writes a `.rumdl_cache` directory as it
        runs, which the real checkout also carries untracked. A cache is not a
        rewrite of the tree, and hashing it would fail this case on every run.
        """
        digest = hashlib.sha256()
        listed = git(self.work, "ls-files", "-z").stdout
        for relative in sorted(entry for entry in listed.split("\0") if entry):
            digest.update(relative.encode())
            digest.update((self.work / relative).read_bytes())
        return digest.hexdigest()


def build(*, stub_slow: bool = True, extra_branch: str | None = None) -> Fixture:
    """A fixture repository plus a bare remote, with the working-tree hook in place.

    The tree comes from `git archive HEAD`, so it is the tracked tree and nothing
    else: no history to copy, and none of the untracked caches that make the real
    checkout ten times larger. The hook is then copied from the WORKING TREE
    rather than taken from the archive, so an uncommitted hook is what gets
    tested.
    """
    workspace = Path(tempfile.mkdtemp(prefix="tadw-prepush-", dir=FIXTURE_ROOT))
    workspaces.append(workspace)
    work = workspace / "work"
    remote = workspace / "remote.git"
    work.mkdir()
    remote.mkdir()

    git(remote, "init", "-q", "--bare")
    git(work, "init", "-q")

    archive = subprocess.run(
        [GIT, "-C", str(REPO), "archive", "HEAD"], capture_output=True, check=True
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(work)], input=archive, check=True)

    hook = work / ".githooks" / "pre-push"
    hook.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HOOK, hook)
    hook.chmod(0o755)

    fixture = Fixture(work)
    if stub_slow:
        for relative, body in SLOW_CHECKS.items():
            fixture.write(relative, body)

    fixture.commit_all("base")
    git(work, "branch", "-M", "main")
    git(work, "remote", "add", "origin", str(remote))
    # Pushed BEFORE core.hooksPath is set, so the setup push does not run the
    # hook under test and does not need to pass its checks.
    git(work, "push", "-q", "origin", "main")
    if extra_branch:
        git(work, "push", "-q", "origin", f"main:refs/heads/{extra_branch}")
    git(work, "config", "core.hooksPath", ".githooks")

    # One commit ahead of the remote, so every case has something to push. Git
    # runs no pre-push hook for an up-to-date push, and a case that pushed
    # nothing would assert against "Everything up-to-date" while looking green.
    # A `.txt` at the root, because no check in the list reads one: markdown
    # would reach rumdl, and a doc would reach the path checker.
    fixture.write("PENDING.txt", "a commit for the case to push\n")
    fixture.commit_all("pending work")
    return fixture


def git_dir(root: Path) -> Path:
    """The git directory the hook itself resolves, for a checkout or a worktree.

    `--absolute-git-dir` rather than `--git-dir`, because the hook resolves its
    path with the working directory git gives it and a case resolves the same
    path from wherever the suite happens to be running.
    """
    return Path(git(root, "rev-parse", "--absolute-git-dir").stdout.strip())


def head_of(root: Path) -> str:
    return git(root, "rev-parse", "HEAD").stdout.strip()


def record_verdict(root: Path, verdict: str, *, head: str | None = None) -> Path:
    """Plant a quality-gates report where the skill writes one, with the fields it writes.

    Written by hand rather than by running the gates: the hook's contract is the
    file, and a case that ran /quality-gates would test the skill instead and
    could not produce a FAIL on demand.
    """
    report = git_dir(root) / "quality-gates-report.json"
    report.write_text(
        json.dumps(
            {
                "version": 1,
                "head": head_of(root) if head is None else head,
                "timestamp": RECORDED_AT,
                "verdict": verdict,
            }
        ),
        encoding="utf-8",
    )
    return report


# Everything the hook reaches for: the checkers themselves, plus the four
# utilities it shells out to, plus `sh` for its own `#!/usr/bin/env sh` line.
HOOK_TOOLS = ("sh", "bash", "date", "mkdir", "cat", "rm", "git", "node", "python3", "rumdl")


def stub_path_without(*drop: str) -> str:
    """A PATH holding exactly what the hook needs, minus every tool in `drop`.

    A hermetic directory of symlinks rather than a filtered PATH, and this is not
    over-engineering: `/usr/bin/python3` ships with macOS, so keeping `/usr/bin`
    on PATH to supply `date` and `cat` also silently supplies python3, and a case
    that meant to remove it would prove nothing.
    """
    stub = Path(tempfile.mkdtemp(prefix="tadw-bin-", dir=FIXTURE_ROOT))
    workspaces.append(stub)
    for tool in HOOK_TOOLS:
        if tool in drop:
            continue
        real = shutil.which(tool)
        if real:
            (stub / tool).symlink_to(real)
    return str(stub)


def commands_in_agents_md() -> list[str]:
    """The command list from the AGENTS.md "Commands for This Repo" block."""
    text = AGENTS.read_text(encoding="utf-8")
    section = text.split("## Commands for This Repo", 1)[1]
    block = re.search(r"```bash\n(.*?)```", section, re.S)
    assert block, "AGENTS.md must carry a bash block under Commands for This Repo"
    commands = []
    for line in block.group(1).splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped:
            commands.append(stripped)
    return commands


def commands_in_hook() -> list[str]:
    """Every command the hook passes to its `check` helper."""
    commands = []
    for line in HOOK.read_text(encoding="utf-8").splitlines():
        if line.startswith("check "):
            commands.append(line[len("check "):].strip())
    return commands


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


print("\n  [the fixture is a repository the checks can actually read]")


def case_fixture_is_walkable_by_rumdl() -> None:
    """The positive control for every rumdl assertion below.

    Without this, a fixture in a directory rumdl declines to walk would report
    "No markdown files found to check", exit 0, and quietly turn criterion 1
    into a test of nothing.
    """
    if not shutil.which("rumdl"):
        return  # nothing to control for; case_missing_rumdl_warns_and_allows covers absence
    fixture = build()
    result = subprocess.run(
        ["rumdl", "fmt", "--check", "."],
        cwd=fixture.work,
        capture_output=True,
        text=True,
    )
    assert "No markdown files found" not in result.stdout, (
        f"rumdl walked no files in {fixture.work}, so the rumdl cases would be vacuous: "
        f"{result.stdout!r}"
    )
    assert result.returncode == 0, f"the unmodified tree must be clean: {result.stdout!r}"


def case_hook_is_executable_posix_sh() -> None:
    assert HOOK.exists(), f"{HOOK} must exist"
    assert os.access(HOOK, os.X_OK), "the hook must have its executable bit set"
    first = HOOK.read_text(encoding="utf-8").splitlines()[0]
    assert first == "#!/usr/bin/env sh", f"POSIX sh, matching the sibling hook: {first!r}"
    syntax = subprocess.run(["sh", "-n", str(HOOK)], capture_output=True, text=True)
    assert syntax.returncode == 0, f"sh -n must parse the hook: {syntax.stderr!r}"


for name, fn in [
    ("the fixture is a tree rumdl walks", case_fixture_is_walkable_by_rumdl),
    ("the hook is executable POSIX sh", case_hook_is_executable_posix_sh),
]:
    check(name, fn)


print("\n  [a failing check refuses the push]")


def case_broken_markdown_refuses_push() -> None:
    """Criterion 1. Break one file's formatting; the push is refused and names it."""
    if not shutil.which("rumdl"):
        return
    fixture = build()
    fixture.write(BREAKABLE_DOC, BAD_MARKDOWN)
    fixture.commit_all("break the formatting")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"a formatting failure must refuse the push: {output}"
    assert BREAKABLE_DOC in output, f"the output must name the broken file: {output}"
    assert "refusing to push" in output, f"it must say what it did: {output}"


def case_two_failures_both_reported() -> None:
    """Criterion 4. The hook does not stop at the first failure.

    Stopping early makes the author push, fail, fix, push, and fail again on the
    next one, which is the whole reason the design aggregates.
    """
    if not shutil.which("rumdl"):
        return
    fixture = build()
    fixture.write(BREAKABLE_DOC, BAD_MARKDOWN)
    fixture.write(BREAKABLE_CHECK, FAILING_BODY)
    fixture.commit_all("break two checks")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"two failures must refuse the push: {output}"
    assert BREAKABLE_DOC in output, f"the first failure must appear: {output}"
    assert "test_check_doc_paths.py" in output, f"the second failure must appear: {output}"
    assert "2 of" in output, f"the summary must count both failures: {output}"


def case_failure_report_names_the_command() -> None:
    """A reader needs the command to re-run, not just its output."""
    fixture = build()
    fixture.write(BREAKABLE_CHECK, FAILING_BODY)
    fixture.commit_all("break one check")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert f"FAILED: python3 {BREAKABLE_CHECK}" in output, (
        f"the failing command must be quoted verbatim: {output}"
    )


for name, fn in [
    ("broken markdown refuses the push and names the file [criterion 1]", case_broken_markdown_refuses_push),
    ("two failures both appear in one report [criterion 4]", case_two_failures_both_reported),
    ("the report names the failing command", case_failure_report_names_the_command),
]:
    check(name, fn)


print("\n  [the escapes, and what they must not swallow]")


def case_off_switch_allows_a_failing_push() -> None:
    """Criterion 2. TADW_PREPUSH=off wins over a real failure, or it is not an escape."""
    fixture = build()
    fixture.write(BREAKABLE_CHECK, FAILING_BODY)
    fixture.commit_all("break one check")
    refused = fixture.push()
    assert refused.returncode != 0, "the control: this push must fail without the off-switch"
    allowed = fixture.push(env={"TADW_PREPUSH": "off"})
    output = allowed.stdout + allowed.stderr
    assert allowed.returncode == 0, f"the off-switch must allow the push: {output}"
    assert "tadw:" not in output, f"off means silent, not merely permissive: {output!r}"


def case_off_switch_is_exact() -> None:
    """Only the documented value switches it off.

    An empty or unrelated value must not disable the gate, or a stray export
    would silence it for a whole shell session without anyone choosing that.
    """
    fixture = build()
    fixture.write(BREAKABLE_CHECK, FAILING_BODY)
    fixture.commit_all("break one check")
    for value in ("", "0", "false", "ON"):
        result = fixture.push(env={"TADW_PREPUSH": value})
        assert result.returncode != 0, f"TADW_PREPUSH={value!r} must not disable the hook"


def case_missing_rumdl_warns_and_allows() -> None:
    """Criterion 3. A missing tool is not evidence of broken code.

    An unpushable clone is a worse failure than an unchecked push, so the hook
    names the tool and continues. Named, because a silent skip would recreate the
    gap the hook exists to close.
    """
    fixture = build()
    result = fixture.push(env={"PATH": stub_path_without("rumdl")})
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a missing rumdl must still allow the push: {output}"
    assert "rumdl" in output, f"the skipped tool must be named: {output}"
    assert "WARNING" in output, f"the skip must be a warning, not silence: {output}"
    total = len(commands_in_hook())
    assert f"{total - 1} of {total}" in output, (
        f"every check but the rumdl one must still run: {output}"
    )


def case_missing_python3_warns_once() -> None:
    """python3 carries most of the checks, and one warning about it is the useful number.

    Scoped to the skipped-tool line rather than to every warning, because stage 2
    reads the recorded verdict in python3 as well and reports its own loss on the
    same push. That second line is the point of
    case_unparseable_report_warns_and_allows, and folding the two counts together
    here would make either one drift silently.
    """
    fixture = build()
    result = fixture.push(env={"PATH": stub_path_without("python3")})
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a missing python3 must still allow the push: {output}"
    warning = [line for line in output.splitlines() if "were skipped" in line]
    assert len(warning) == 1, f"exactly one warning line, not one per check: {warning}"
    assert warning[0].count("python3") == 1, f"python3 named once: {warning[0]!r}"
    assert "could not be read" in output, (
        f"and stage 2 must say what the absence cost it, rather than reading as a clean "
        f"verdict: {output}"
    )


def case_no_check_ran_is_not_a_pass() -> None:
    """Every tool missing still allows the push, and must never claim a pass.

    The missing-tool rule is deliberate, so the push proceeds. What it must not do
    is print "checks passed" having verified nothing: that is the
    all-skipped-reports-PASS shape the quality-gates skill refuses by name, and
    the reader would take it for a clean bill of health.
    """
    fixture = build()
    result = fixture.push(env={"PATH": stub_path_without("rumdl", "node", "python3", "bash")})
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a toolless clone must still push: {output}"
    assert "passed" not in output, f"nothing ran, so nothing passed: {output!r}"
    assert f"0 of {len(commands_in_hook())}" in output, (
        f"it must say how little ran: {output!r}"
    )
    assert "nothing was verified" in output, f"and say what that means: {output!r}"


for name, fn in [
    ("TADW_PREPUSH=off allows a push that would fail [criterion 2]", case_off_switch_allows_a_failing_push),
    ("only the documented off value disables the hook", case_off_switch_is_exact),
    ("a missing rumdl warns by name and allows [criterion 3]", case_missing_rumdl_warns_and_allows),
    ("a missing python3 warns once, not six times", case_missing_python3_warns_once),
    ("every tool missing allows the push but claims no pass", case_no_check_ran_is_not_a_pass),
]:
    check(name, fn)


print("\n  [what the hook must not do]")


def case_delete_only_push_runs_nothing() -> None:
    """Criterion 6. Deleting a remote ref pushes no code, so there is nothing to gate.

    Proven against a tree that WOULD fail, so the silence is the deletion rule
    rather than a tree that happens to be clean.
    """
    fixture = build(extra_branch="doomed")
    fixture.write(BREAKABLE_CHECK, FAILING_BODY)
    fixture.commit_all("break one check")
    result = fixture.push("--delete", "doomed")
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a delete-only push must be allowed: {output}"
    assert "tadw:" not in output, f"no check may run for a deletion: {output!r}"


def case_mixed_delete_and_update_runs_checks() -> None:
    """The complement of criterion 6, and the half a delete-only case cannot prove.

    `git push origin :doomed main` deletes one ref and updates another in one
    invocation, so git sends two stdin lines: one all-zero, one real. Code is
    being pushed, so the checks must run. A guard that skipped on seeing ANY
    deletion would wave this through, and the delete-only case would still pass.
    """
    fixture = build(extra_branch="doomed")
    fixture.write(BREAKABLE_CHECK, FAILING_BODY)
    fixture.commit_all("break one check")
    result = fixture.push(":doomed", "main")
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"a push carrying code must be gated: {output}"
    assert "refusing to push" in output, f"the failing check must refuse it: {output}"


def case_hook_leaves_the_tree_alone() -> None:
    """Criterion 5's runtime half, and the sharper risk it covers.

    `rumdl fmt --check .` reports; `rumdl fmt .` rewrites. Dropping `--check`
    would reformat every markdown file in the tree during a push, silently, and
    the push would then pass. The CI workflow is hashed alongside everything else
    rather than on its own, so any rewrite anywhere fails this case.
    """
    fixture = build()
    fixture.write(BREAKABLE_DOC, BAD_MARKDOWN)
    fixture.commit_all("break the formatting")
    workflow = fixture.work / ".github" / "workflows" / "lint.yml"
    before_workflow = workflow.read_bytes()
    before = fixture.tree_digest()
    fixture.push()
    assert fixture.tree_digest() == before, "the hook must not modify any file it checks"
    assert workflow.read_bytes() == before_workflow, "the CI workflow must be untouched"


def case_clean_push_is_quiet() -> None:
    """A passing run is one summary line, not ten. Noise trains people to ignore it.

    The whole hook, both stages, and one line out of it. The verdict is recorded
    as a current PASS so stage 2 has nothing to add, which is the state a session
    that followed "Landing the Plane" actually pushes in.
    """
    fixture = build()
    fixture.write("docs/NOTE.md", "# A note\n\nAdded so the push has a commit to carry.\n")
    fixture.commit_all("add a note")
    record_verdict(fixture.work, "PASS")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a clean tree must push: {output}"
    lines = [line for line in output.splitlines() if line.startswith("tadw:")]
    assert len(lines) == 1, f"exactly one tadw line on success: {lines}"
    assert "passed" in lines[0], f"and it says so: {lines[0]!r}"
    # Derived from the hook's own list, never hardcoded. Three of these
    # assertions carried a literal 12 and all three broke the day a check was
    # added, which is the same drift the hook's own comment warns about.
    total = len(commands_in_hook())
    assert f"{total} of {total}" in lines[0], f"with the count that ran: {lines[0]!r}"
    # The elapsed time is the only number a reader can use to judge whether the
    # hook is worth its place on every push, so it is asserted rather than assumed.
    assert re.search(r"\b\d+s\b", lines[0]), f"and how long it took: {lines[0]!r}"


def case_push_from_a_linked_worktree_spares_the_main_repository() -> None:
    """A push from a linked worktree must not reach into the repository it belongs to.

    git exports GIT_DIR into every hook. From the main checkout the value is the
    relative `.git`, which re-resolves under any directory a check moves into.
    From a LINKED WORKTREE it is an absolute path, and `git -C <tmpdir>` does not
    redirect it, so a check that inits a git fixture inits the repository GIT_DIR
    names instead. Four of the checks build such fixtures.

    Observed before the hook cleared it: a push from a linked worktree left the
    main checkout with core.bare=true and core.excludesFile=/dev/null, and every
    work-tree git command in both checkouts failed until it was repaired by hand.
    The main gitdir's config is therefore the evidence this case reads.

    A linked worktree is built rather than GIT_DIR being set on the push, because
    setting it there would redirect the push itself and never reach the hook.
    """
    fixture = build()
    fixture.write(GIT_FIXTURE_CANARY_PATH, GIT_FIXTURE_CANARY)
    fixture.commit_all("install the git-fixture canary")

    linked = fixture.work.parent / "linked"
    git(fixture.work, "worktree", "add", "-q", str(linked), "-b", "linked-work")

    config = fixture.work / ".git" / "config"
    before = config.read_text(encoding="utf-8")
    result = subprocess.run(
        [GIT, "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(linked),
         "push", "--dry-run", "origin", "linked-work"],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0, f"the push must still run and pass its checks: {output}"
    assert config.read_text(encoding="utf-8") == before, (
        f"the push rewrote the main repository's config:\n{config.read_text(encoding='utf-8')}"
    )
    bare = git(fixture.work, "rev-parse", "--is-bare-repository").stdout.strip()
    assert bare == "false", "the push turned the main repository bare"


for name, fn in [
    ("a delete-only push runs no checks [criterion 6]", case_delete_only_push_runs_nothing),
    ("a mixed delete-and-update push does run the checks", case_mixed_delete_and_update_runs_checks),
    ("the hook modifies nothing, including the CI workflow [criterion 5]", case_hook_leaves_the_tree_alone),
    ("a push from a linked worktree spares the main repository", case_push_from_a_linked_worktree_spares_the_main_repository),
    ("a clean push prints one summary line", case_clean_push_is_quiet),
]:
    check(name, fn)


print("\n  [stage 2: the verdict /quality-gates recorded]")


def case_fail_verdict_refuses_the_push() -> None:
    """Criterion 1. A recorded FAIL blocks, and the message names all three facts.

    The tree is clean, so the refusal can only have come from stage 2. Both exits
    are asserted too: a gate whose way out a reader has to guess gets bypassed
    with --no-verify instead, which skips stage 1 along with it.
    """
    fixture = build()
    recorded = head_of(fixture.work)
    record_verdict(fixture.work, "FAIL")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"a recorded FAIL must refuse the push: {output}"
    assert "verdict is FAIL" in output, f"it must name the verdict: {output}"
    assert recorded in output, f"and the head it was recorded for: {output}"
    assert RECORDED_AT in output, f"and when it was recorded: {output}"
    assert "/quality-gates" in output, f"and how to record a fresh one: {output}"
    assert "TADW_PREPUSH=off" in output, f"and the documented escape: {output}"


def case_no_report_warns_once_and_allows() -> None:
    """Criterion 2. Absence is not evidence of a problem.

    Blocking here would refuse every documentation push from a fresh clone and
    teach people to turn the hook off, which costs stage 1 as well.
    """
    fixture = build()
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"no recorded verdict must still allow the push: {output}"
    lines = [line for line in output.splitlines() if "quality-gates verdict" in line]
    assert len(lines) == 1, f"exactly one line about the missing verdict: {lines}"
    assert "WARNING" in lines[0], f"absence is a warning, not silence: {lines[0]!r}"
    # The wording, not merely the presence of a line. "No verdict recorded" and
    # "the verdict could not be read" send the author to different fixes: one
    # forgot to run the gates, the other has a broken artifact writer. Matching
    # only on "quality-gates verdict" would accept either message here.
    assert "no quality-gates verdict recorded" in lines[0], (
        f"absence must read as absence, not as a broken report: {lines[0]!r}"
    )
    assert "/quality-gates" in lines[0], f"and it names how to record one: {lines[0]!r}"


def case_verdict_off_the_pushed_line_warns() -> None:
    """Criterion 3. A verdict about a commit you are not pushing describes another tree.

    The recorded head is a real commit here, on a branch nobody is pushing, so
    the case pins the ancestry question rather than an unknown-object failure.
    """
    fixture = build()
    git(fixture.work, "checkout", "-q", "-b", "sidetrack", "HEAD~1")
    fixture.write("SIDETRACK.txt", "a commit on a branch nobody is pushing\n")
    fixture.commit_all("sidetrack")
    sidetrack = head_of(fixture.work)
    git(fixture.work, "checkout", "-q", "main")
    record_verdict(fixture.work, "PASS", head=sidetrack)
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a stale verdict warns rather than blocks: {output}"
    assert "stale" in output, f"and it says which way it is wrong: {output}"
    assert sidetrack in output, f"naming the head it describes: {output}"


def case_verdict_for_an_unknown_head_warns() -> None:
    """The same rule for a commit this clone has never seen.

    `merge-base --is-ancestor` fails on an unknown object, which is the answer
    this wants: a verdict about a commit that is not here describes another tree
    too. Pinned separately because it reaches the failure by a different route,
    and a hook that treated an erroring merge-base as "current" would pass the
    case above and silently trust this one.
    """
    fixture = build()
    record_verdict(fixture.work, "PASS", head="deadbeef" * 5)
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"an unknown head warns rather than blocks: {output}"
    assert "stale" in output, f"and it is reported as stale: {output}"


def case_current_pass_verdict_is_silent() -> None:
    """Criterion 4. A passing verdict about what you are pushing has nothing to say."""
    fixture = build()
    record_verdict(fixture.work, "PASS")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a current PASS must push: {output}"
    noise = [line for line in output.splitlines() if "verdict" in line or "stale" in line]
    assert not noise, f"stage 2 must add no line when the verdict is a current PASS: {noise}"


def case_ancestor_verdict_is_current() -> None:
    """Current means an ancestor of what is pushed, not the tip of it.

    A verdict recorded before one more commit still describes a commit inside the
    push, so it is not stale. The design chose ancestry over equality on purpose,
    and without this case the rule would read either way.
    """
    fixture = build()
    record_verdict(fixture.work, "PASS")
    fixture.write("LATER.txt", "one more commit after the verdict was recorded\n")
    fixture.commit_all("later work")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"an ancestor verdict must push: {output}"
    assert "stale" not in output, f"an ancestor of the pushed commit is not stale: {output}"


def case_a_verdict_current_for_one_pushed_ref_is_not_stale() -> None:
    """Stage 2 considers every ref in the push, not only the first line of stdin.

    The hook is run directly with a crafted stdin rather than through
    `fixture.push`, and that is the whole point of the case. Git decides the
    order it feeds those lines in, and it is not the order of the refspecs: a
    probe with a hook that echoed its stdin delivered `main` first for
    `git push origin aside main` even though `aside` sorts first. A case built on
    `fixture.push` therefore cannot put the non-matching ref first, and one that
    appeared to would be pinning a git version rather than this hook.

    Fed by hand, the order is ours: the first line is a ref the verdict does not
    describe, the second is one it does. A reader that stopped at the first line
    would warn here.
    """
    fixture = build()
    current = head_of(fixture.work)
    git(fixture.work, "checkout", "-q", "-b", "aside", "HEAD~1")
    fixture.write("ASIDE.txt", "a ref whose line the verdict does not describe\n")
    fixture.commit_all("aside")
    aside = head_of(fixture.work)
    git(fixture.work, "checkout", "-q", "main")
    record_verdict(fixture.work, "PASS", head=current)

    zeros = "0" * 40
    stdin = (
        f"refs/heads/aside {aside} refs/heads/aside {zeros}\n"
        f"refs/heads/main {current} refs/heads/main {zeros}\n"
    )
    result = subprocess.run(
        ["sh", str(fixture.work / ".githooks" / "pre-push"), "origin", "/dev/null"],
        cwd=fixture.work,
        input=stdin,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a current verdict must allow the push: {output}"
    assert "stale" not in output, (
        f"the verdict is current for the second ref on stdin, so it is not stale: {output}"
    )


def case_a_lowercase_verdict_still_blocks() -> None:
    """The verdict is matched case-insensitively, and the wrong answer here is an allow.

    The skill writes `FAIL` verbatim, so the reader's `.upper()` is a normalizer
    rather than a documented input. It is pinned anyway because dropping it fails
    open: a report saying `fail` would sail through as though it said nothing.
    """
    fixture = build()
    record_verdict(fixture.work, "fail")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"a lowercase fail must still refuse the push: {output}"
    assert "verdict is FAIL" in output, f"and be reported in one form: {output}"


def case_both_stages_report_separately() -> None:
    """One push, two questions, two answers.

    Stage 1 recording its failure rather than exiting on it is what makes this
    possible. A reader who fixes only the half they were shown pushes again and
    hits the other one, which is the same trap stage 1 avoids internally by
    running every check.
    """
    fixture = build()
    fixture.write(BREAKABLE_CHECK, FAILING_BODY)
    fixture.commit_all("break one check")
    record_verdict(fixture.work, "FAIL")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"either stage alone must refuse the push: {output}"
    assert "checks failed" in output, f"stage 1 must report its own failure: {output}"
    assert "verdict is FAIL" in output, f"and stage 2 must report its own: {output}"


def case_off_switch_allows_a_failed_verdict() -> None:
    """The escape covers the whole hook, or it is not the documented escape."""
    fixture = build()
    record_verdict(fixture.work, "FAIL")
    refused = fixture.push()
    assert refused.returncode != 0, "the control: this push must fail without the off-switch"
    allowed = fixture.push(env={"TADW_PREPUSH": "off"})
    output = allowed.stdout + allowed.stderr
    assert allowed.returncode == 0, f"the off-switch must allow the push: {output}"
    assert "tadw:" not in output, f"off means silent, not merely permissive: {output!r}"


def case_unparseable_report_warns_and_allows() -> None:
    """An unreadable report is not a FAIL, and the reader is not a grep for one.

    The planted body is truncated JSON that still contains the word FAIL, so a
    hook that matched text rather than parsing would block here. It must warn
    that it could not read the file, which is a different fix from a forgotten
    run, and allow the push.
    """
    fixture = build()
    report = git_dir(fixture.work) / "quality-gates-report.json"
    report.write_text('{"verdict": "FAIL", "head": "', encoding="utf-8")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"an unreadable report must allow the push: {output}"
    assert "could not be read" in output, f"and say what it could not do: {output}"
    assert "verdict is FAIL" not in output, f"text inside the file is not a verdict: {output}"


def case_verdict_is_read_from_the_git_dir() -> None:
    """The path is the one `git rev-parse --git-dir` resolves, never a literal `.git/`.

    Both halves are needed. A worktree's own verdict must gate its own push, and
    the main checkout's verdict must not: two worktrees on two branches produce
    two verdicts about two trees, and `--git-common-dir` would let whichever ran
    the gates last decide every push.
    """
    fixture = build()
    linked = fixture.work.parent / "linked"
    git(fixture.work, "worktree", "add", "-q", str(linked), "-b", "linked-work")

    def push_from_linked() -> str:
        result = subprocess.run(
            [GIT, "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(linked),
             "push", "--dry-run", "origin", "linked-work"],
            capture_output=True,
            text=True,
        )
        return f"{result.returncode}\n{result.stdout}{result.stderr}"

    record_verdict(linked, "FAIL")
    own = push_from_linked()
    assert not own.startswith("0\n"), f"a worktree's own FAIL must refuse its push: {own}"
    assert "verdict is FAIL" in own, f"and be the verdict it reports: {own}"

    (git_dir(linked) / "quality-gates-report.json").unlink()
    record_verdict(fixture.work, "FAIL")
    other = push_from_linked()
    assert other.startswith("0\n"), f"the main checkout's FAIL must not gate a worktree: {other}"
    assert "verdict is FAIL" not in other, f"nor be reported there: {other}"
    assert "worktrees" in other, f"the path it read must be the worktree's own: {other}"


def case_delete_only_push_ignores_a_fail_verdict() -> None:
    """Neither stage gates a deletion, because a deletion pushes no code.

    The complement of case_delete_only_push_runs_nothing, which proves the same
    rule for stage 1. Stage 2 needs its own: it reads a file rather than the
    tree, so a guard that skipped stage 1 could still let stage 2 block.
    """
    fixture = build(extra_branch="doomed")
    record_verdict(fixture.work, "FAIL")
    result = fixture.push("--delete", "doomed")
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a delete-only push must be allowed: {output}"
    assert "tadw:" not in output, f"neither stage may speak for a deletion: {output!r}"


for name, fn in [
    ("a recorded FAIL refuses the push, naming verdict, head and time [criterion 1]", case_fail_verdict_refuses_the_push),
    ("no recorded verdict is one warning and a push [criterion 2]", case_no_report_warns_once_and_allows),
    ("a verdict for a commit off the pushed line warns as stale [criterion 3]", case_verdict_off_the_pushed_line_warns),
    ("a verdict for a head this clone has never seen warns as stale", case_verdict_for_an_unknown_head_warns),
    ("a current PASS verdict says nothing [criterion 4]", case_current_pass_verdict_is_silent),
    ("a verdict recorded for an ancestor of the push is current", case_ancestor_verdict_is_current),
    ("a verdict current for one of several pushed refs is not stale", case_a_verdict_current_for_one_pushed_ref_is_not_stale),
    ("both stages report their own failure from one push", case_both_stages_report_separately),
    ("TADW_PREPUSH=off allows a recorded FAIL through", case_off_switch_allows_a_failed_verdict),
    ("an unreadable report warns and allows, and is not read as a FAIL", case_unparseable_report_warns_and_allows),
    ("a lowercase verdict still blocks", case_a_lowercase_verdict_still_blocks),
    ("the verdict is read from the resolved git directory", case_verdict_is_read_from_the_git_dir),
    ("a delete-only push ignores a recorded FAIL", case_delete_only_push_ignores_a_fail_verdict),
]:
    check(name, fn)


print("\n  [the hook runs the repository's own list, and stays in step with it]")


def case_command_list_matches_agents_md() -> None:
    """The identity of the commands, which stubbing cannot pin.

    Both directions matter. A command added to AGENTS.md and not to the hook is a
    check nothing enforces; a command in the hook and not in AGENTS.md is a check
    nobody documented.
    """
    documented = commands_in_agents_md()
    for excluded, reason in NOT_IN_HOOK.items():
        assert excluded in documented, (
            f"{excluded!r} is excluded from the hook for this reason, but is no longer in "
            f"AGENTS.md, so the exclusion is stale: {reason}"
        )
    actual = commands_in_hook()
    assert len(actual) == len(set(actual)), f"no command may run twice: {actual}"
    expected = [c for c in documented if c not in NOT_IN_HOOK]
    # Sorted, because execution order is the hook's business: it is free to put
    # the cheap checks first without AGENTS.md having to read in that order.
    assert sorted(actual) == sorted(expected), (
        f"the hook's list must be the AGENTS.md block minus the documented exclusions.\n"
        f"         only in hook:      {sorted(set(actual) - set(expected))}\n"
        f"         only in AGENTS.md: {sorted(set(expected) - set(actual))}"
    )


def case_every_hook_command_exists() -> None:
    """A path typo would report a failing check forever, blaming the wrong thing."""
    for command in commands_in_hook():
        parts = command.split()
        script = next((p for p in parts[1:] if "/" in p), None)
        if script:
            assert (REPO / script).exists(), f"{command!r} names a path that does not exist"


for name, fn in [
    ("the hook's list is the AGENTS.md block minus three exclusions", case_command_list_matches_agents_md),
    ("every command the hook runs names a real path", case_every_hook_command_exists),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
