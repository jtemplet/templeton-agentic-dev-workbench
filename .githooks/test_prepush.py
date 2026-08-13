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

WHY FOUR CHECKS ARE STUBBED IN THE FIXTURE. The four slowest commands in the
hook's list account for about 16 of its 19 seconds, and each already owns a
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
  One warning per missing tool, not per check    case_missing_python3_warns_once
  POSIX sh, executable                          case_hook_is_executable_posix_sh

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
}

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

GIT = shutil.which("git") or "git"

workspaces: list[Path] = []
passed = 0
failed = 0


@atexit.register
def _cleanup() -> None:
    for path in workspaces:
        shutil.rmtree(path, ignore_errors=True)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """A git command that must succeed. Fixture setup has no recoverable failure."""
    return subprocess.run(
        [GIT, "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(root), *args],
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


# Everything the hook reaches for: the checkers themselves, plus the four
# utilities it shells out to, plus `sh` for its own `#!/usr/bin/env sh` line.
HOOK_TOOLS = ("sh", "date", "mkdir", "cat", "rm", "git", "node", "python3", "rumdl")


def stub_path_without(*, drop: str) -> str:
    """A PATH holding exactly what the hook needs, minus `drop`.

    A hermetic directory of symlinks rather than a filtered PATH, and this is not
    over-engineering: `/usr/bin/python3` ships with macOS, so keeping `/usr/bin`
    on PATH to supply `date` and `cat` also silently supplies python3, and a case
    that meant to remove it would prove nothing.
    """
    stub = Path(tempfile.mkdtemp(prefix="tadw-bin-", dir=FIXTURE_ROOT))
    workspaces.append(stub)
    for tool in HOOK_TOOLS:
        if tool == drop:
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
    result = fixture.push(env={"PATH": stub_path_without(drop="rumdl")})
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a missing rumdl must still allow the push: {output}"
    assert "rumdl" in output, f"the skipped tool must be named: {output}"
    assert "WARNING" in output, f"the skip must be a warning, not silence: {output}"
    assert "9 ran" in output, f"the other nine checks must still run: {output}"


def case_missing_python3_warns_once() -> None:
    """python3 carries six checks, and one warning about it is the useful number."""
    fixture = build()
    result = fixture.push(env={"PATH": stub_path_without(drop="python3")})
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a missing python3 must still allow the push: {output}"
    warning = [line for line in output.splitlines() if "WARNING" in line]
    assert len(warning) == 1, f"exactly one warning line, not one per check: {warning}"
    assert warning[0].count("python3") == 1, f"python3 named once: {warning[0]!r}"


for name, fn in [
    ("TADW_PREPUSH=off allows a push that would fail [criterion 2]", case_off_switch_allows_a_failing_push),
    ("only the documented off value disables the hook", case_off_switch_is_exact),
    ("a missing rumdl warns by name and allows [criterion 3]", case_missing_rumdl_warns_and_allows),
    ("a missing python3 warns once, not six times", case_missing_python3_warns_once),
]:
    check(name, fn)


print("\n  [what the hook must not do]")


def case_delete_only_push_runs_nothing() -> None:
    """Criterion 6. Deleting a remote ref pushes no code, so there is nothing to gate."""
    fixture = build(extra_branch="doomed")
    result = fixture.push("--delete", "doomed")
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a delete-only push must be allowed: {output}"
    assert "tadw:" not in output, f"no check may run for a deletion: {output!r}"


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
    """A passing run is one summary line, not ten. Noise trains people to ignore it."""
    fixture = build()
    fixture.write("docs/NOTE.md", "# A note\n\nAdded so the push has a commit to carry.\n")
    fixture.commit_all("add a note")
    result = fixture.push()
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"a clean tree must push: {output}"
    lines = [line for line in output.splitlines() if line.startswith("tadw:")]
    assert len(lines) == 1, f"exactly one tadw line on success: {lines}"
    assert "passed" in lines[0], f"and it says so: {lines[0]!r}"
    assert "10 ran" in lines[0], f"with the count it ran: {lines[0]!r}"


for name, fn in [
    ("a delete-only push runs no checks [criterion 6]", case_delete_only_push_runs_nothing),
    ("the hook modifies nothing, including the CI workflow [criterion 5]", case_hook_leaves_the_tree_alone),
    ("a clean push prints one summary line", case_clean_push_is_quiet),
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
