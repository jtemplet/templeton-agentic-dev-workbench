#!/usr/bin/env python3
"""Regression suite for check_secrets.py.

Stdlib only, no install, mirroring test_check_doc_paths.py. Run with:
    python3 skills/quality-gates/scripts/test_check_secrets.py

Every case builds a throwaway git repository, plants one thing, and asserts what
the script says about it. Planted keys are fabricated: the AKIA body is `A` times
16, which is the right shape and belongs to nobody.

RULE-TO-TEST MAPPING. This block is what proves the port from the skill's prose
neither narrowed nor widened detection. Each Gate 6 rule names the test pinning
it; a rule with no test here is a rule nothing holds.

  Gate 6 rule (skills/quality-gates/SKILL.md)   Pinned by
  ------------------------------------------------------------------------------
  Name `.env`                                   case_tracked_env
  Name `.env.*`                                 case_env_suffix_variant
  Name `*.pem`                                  case_pem_file
  Name `*.p12`                                  case_p12_file
  Name `id_rsa`                                 case_id_rsa
  Name `*.keystore`                             case_keystore
  Name `*credential*`                           case_credential_substring
  Exclude `.env.example`                        case_env_example_allowed
  Exclude `.env.sample`                         case_env_sample_allowed
  Exclude `.env.template`                       case_env_template_allowed
  Scan `git ls-files`                           case_tracked_env
  Scan `--others --exclude-standard`            case_untracked_env  (criterion 1)
  Ignored files are not scanned                 case_gitignored_env_is_not_a_finding
  Content `AKIA[0-9A-Z]{16}`                    case_akia_in_source
  Content `ghp_`                                case_github_token
  Content `xox[baprs]-`                         case_slack_token
  Content `sk-ant-`                             case_anthropic_key
  Content `-----BEGIN ... PRIVATE KEY-----`     case_private_key_block
  Exclude `node_modules/`                       case_node_modules_excluded  (criterion 2)
  Exclude `vendor/`                             case_vendor_excluded
  Exclude `dist/`, `build/`                     case_dist_and_build_excluded
  Exclude `*.min.*`                             case_minified_excluded
  Exclude lockfiles                             case_lockfile_excluded
  Exclude fixture directories                   case_fixture_dir_excluded
  No generic hex/base64 matching                case_long_hex_is_not_a_finding
  Report file:line and the pattern name         case_report_shape  (criterion 3)
  Never report the matched value                case_value_never_printed  (criterion 3)
  Clean tree passes                             case_clean_tree
  This repository passes                        case_real_repo  (criterion 4)

Beyond the prose, the large-file policy. Skipping is configurable and never
silent, because "OK" after an unexamined file claims more than the gate checked:

  Large files skipped by default                case_large_file_is_skipped
  A skip is named in the report                 case_skip_is_reported
  --no-skip-large-files scans them              case_no_skip_large_files_finds_it
  A skip does not change the exit status        case_skip_alone_still_exits_0
  A skip report carries no value                case_skip_report_never_prints_the_value
  An undecodable file is a skip, not a crash    case_undecodable_file_is_reported
  --max-scan-bytes must be positive             case_max_scan_bytes_must_be_positive

Criterion 5 (bare python3, no third-party import) is pinned by
case_no_third_party_imports plus the fact that this file runs at all.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# git exports GIT_DIR into any hook it runs, and from a linked worktree the value
# is an absolute path to the main repository's gitdir. `git -C <tmpdir>` does not
# redirect it, so every `git init` below would initialize that repository instead
# of the fixture. .githooks/pre-push clears these before it runs any check;
# repeating it here makes the suite safe to run by hand under a stray GIT_DIR too.
for _leaked in (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
):
    os.environ.pop(_leaked, None)

CHECKER = Path(__file__).resolve().parent / "check_secrets.py"

# Fabricated, shape-valid, owned by nobody. Kept in one place so the
# value-never-printed assertion and the planting code cannot drift apart.
#
# Every one is BUILT, never written as a literal, and that is required rather
# than stylistic: a literal here would be a real match in a tracked file, so the
# checker would report its own test suite and criterion 4 would fail. The first
# run of this suite proved it, on the private-key marker below. Concatenation is
# the fix that needs no location-based exemption, and a location-based exemption
# is exactly what would let a real key hide in a file named like a test.
FAKE_AKIA = "AKIA" + "A" * 16
FAKE_GITHUB = "ghp_" + "b" * 36
FAKE_SLACK = "xoxb-" + "1" * 12
FAKE_ANTHROPIC = "sk-ant-" + "c" * 24
PRIVATE_KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY" + "-----"
PRIVATE_KEY_FOOTER = "-----END " + "RSA PRIVATE KEY" + "-----"

passed = 0
failed = 0


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(root), *args],
        capture_output=True,
        text=True,
    )


def build(files: dict[str, str], *, track: bool = True, gitignore: str = "") -> Path:
    """A throwaway git repository holding exactly the planted files.

    Committing is what makes `git ls-files` return them, which is the tracked
    half of check 1. Pass track=False to leave them untracked, which is the half
    that catches an uncommitted `.env`.

    `core.excludesFile=/dev/null` is load-bearing, not tidiness. A developer's
    global gitignore commonly lists `dist` and `build`, so without it those
    fixtures are never staged, `git add -A` records nothing, the commit fails,
    and the exclusion tests that do run pass for the wrong reason: the file was
    invisible to git rather than excluded by this script. This suite must test
    the script, not the machine it runs on.
    """
    root = Path(tempfile.mkdtemp())
    git = ["git", "-c", "core.excludesFile=/dev/null"]
    subprocess.run([*git, "init", "-q"], cwd=root, check=True)
    if gitignore:
        (root / ".gitignore").write_text(gitignore, encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    if track:
        subprocess.run([*git, "add", "-A"], cwd=root, check=True)
        subprocess.run(
            [*git, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
            cwd=root,
            check=True,
        )
    return root


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def findings(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln for ln in result.stdout.splitlines() if re.search(r":\d+\s+\[", ln)]


print("\n  [check 1: secret file names]")


def case_tracked_env() -> None:
    r = run(build({".env": "TOKEN=x\n"}))
    assert r.returncode == 1, f"a tracked .env must exit 1, got {r.returncode}"
    assert any(".env" in f for f in findings(r)), f"must name .env: {r.stdout}"


def case_untracked_env() -> None:
    """Criterion 1: untracked and unignored is the case the gate exists for."""
    r = run(build({".env": "TOKEN=x\n"}, track=False))
    assert r.returncode == 1, f"an untracked .env must exit 1, got {r.returncode}"
    assert any(".env" in f for f in findings(r)), f"must name .env: {r.stdout}"


def case_env_suffix_variant() -> None:
    r = run(build({".env.production": "TOKEN=x\n"}))
    assert r.returncode == 1, f".env.* must be a finding: {r.stdout}"


def case_pem_file() -> None:
    r = run(build({"server.pem": "x\n"}))
    assert r.returncode == 1, f"*.pem must be a finding: {r.stdout}"


def case_p12_file() -> None:
    r = run(build({"cert.p12": "x\n"}))
    assert r.returncode == 1, f"*.p12 must be a finding: {r.stdout}"


def case_id_rsa() -> None:
    r = run(build({"id_rsa": "x\n"}))
    assert r.returncode == 1, f"id_rsa must be a finding: {r.stdout}"


def case_keystore() -> None:
    r = run(build({"app.keystore": "x\n"}))
    assert r.returncode == 1, f"*.keystore must be a finding: {r.stdout}"


def case_credential_substring() -> None:
    r = run(build({"aws_credentials.json": "{}\n"}))
    assert r.returncode == 1, f"*credential* must be a finding: {r.stdout}"


for name, fn in [
    ("a tracked .env is a finding", case_tracked_env),
    ("an untracked, unignored .env is a finding [criterion 1]", case_untracked_env),
    ("a .env.<suffix> variant is a finding", case_env_suffix_variant),
    ("a .pem file is a finding", case_pem_file),
    ("a .p12 file is a finding", case_p12_file),
    ("an id_rsa file is a finding", case_id_rsa),
    ("a .keystore file is a finding", case_keystore),
    ("a name containing 'credential' is a finding", case_credential_substring),
]:
    check(name, fn)


print("\n  [check 1: sample files are meant to be committed]")


def case_env_example_allowed() -> None:
    r = run(build({".env.example": "TOKEN=replace-me\n"}))
    assert r.returncode == 0, f".env.example must be allowed: {r.stdout}"


def case_env_sample_allowed() -> None:
    r = run(build({".env.sample": "TOKEN=replace-me\n"}))
    assert r.returncode == 0, f".env.sample must be allowed: {r.stdout}"


def case_env_template_allowed() -> None:
    r = run(build({".env.template": "TOKEN=replace-me\n"}))
    assert r.returncode == 0, f".env.template must be allowed: {r.stdout}"


def case_gitignored_env_is_not_a_finding() -> None:
    """An ignored .env cannot reach a commit, so it is not this gate's finding.

    --exclude-standard is what draws that line, and without this case a change
    dropping the flag would still pass every other name test.
    """
    root = build({}, gitignore=".env\n")
    (root / ".env").write_text("TOKEN=x\n", encoding="utf-8")
    r = run(root)
    assert r.returncode == 0, f"a gitignored .env must not be a finding: {r.stdout}"


for name, fn in [
    (".env.example is allowed", case_env_example_allowed),
    (".env.sample is allowed", case_env_sample_allowed),
    (".env.template is allowed", case_env_template_allowed),
    ("a gitignored .env is not a finding", case_gitignored_env_is_not_a_finding),
]:
    check(name, fn)


print("\n  [check 2: prefixed key formats in content]")


def case_akia_in_source() -> None:
    r = run(build({"src/app.py": f'KEY = "{FAKE_AKIA}"\n'}))
    assert r.returncode == 1, f"an AKIA key must exit 1: {r.stdout}"
    assert any("aws-access-key-id" in f for f in findings(r)), r.stdout


def case_github_token() -> None:
    r = run(build({"src/app.py": f'T = "{FAKE_GITHUB}"\n'}))
    assert r.returncode == 1, f"a github token must be a finding: {r.stdout}"
    assert any("github-token" in f for f in findings(r)), r.stdout


def case_slack_token() -> None:
    r = run(build({"src/app.py": f'T = "{FAKE_SLACK}"\n'}))
    assert r.returncode == 1, f"a slack token must be a finding: {r.stdout}"
    assert any("slack-token" in f for f in findings(r)), r.stdout


def case_anthropic_key() -> None:
    r = run(build({"src/app.py": f'T = "{FAKE_ANTHROPIC}"\n'}))
    assert r.returncode == 1, f"an anthropic key must be a finding: {r.stdout}"
    assert any("anthropic-api-key" in f for f in findings(r)), r.stdout


def case_private_key_block() -> None:
    body = f"{PRIVATE_KEY_HEADER}\nMII...\n{PRIVATE_KEY_FOOTER}\n"
    r = run(build({"src/key.txt": body}))
    assert r.returncode == 1, f"a private key block must be a finding: {r.stdout}"
    assert any("private-key-block" in f for f in findings(r)), r.stdout


def case_bare_prefix_is_a_mention_not_a_key() -> None:
    """A prefix with no body is documentation, and this repository has three.

    `skills/quality-gates/SKILL.md` writes `ghp_` and `sk-ant-` to DEFINE the
    patterns. Matching a bare prefix would report the file that specifies the
    gate, which is why each pattern requires a body. Criterion 4 depends on this.
    """
    r = run(build({"docs/gate.md": "Match `ghp_`, `sk-ant-`, and `xox[baprs]-`.\n"}))
    assert r.returncode == 0, f"a bare prefix is a mention, not a key: {r.stdout}"


def case_long_hex_is_not_a_finding() -> None:
    """No generic hex or base64 rule. It fires on every lockfile hash."""
    r = run(build({"src/data.py": f'H = "{"a1b2c3d4" * 8}"\n'}))
    assert r.returncode == 0, f"long hex must not be a finding: {r.stdout}"


for name, fn in [
    ("an AKIA key in source is a finding", case_akia_in_source),
    ("a github token is a finding", case_github_token),
    ("a slack token is a finding", case_slack_token),
    ("an anthropic key is a finding", case_anthropic_key),
    ("a private key block is a finding", case_private_key_block),
    ("a bare prefix with no body is not a finding", case_bare_prefix_is_a_mention_not_a_key),
    ("a long hex string is not a finding", case_long_hex_is_not_a_finding),
]:
    check(name, fn)


print("\n  [exclusions: where false positives live]")


def case_node_modules_excluded() -> None:
    """Criterion 2: the same key in src/ and node_modules/, only src/ reported."""
    r = run(
        build(
            {
                "src/app.py": f'KEY = "{FAKE_AKIA}"\n',
                "node_modules/pkg/index.js": f'var k = "{FAKE_AKIA}";\n',
            }
        )
    )
    assert r.returncode == 1, f"the src/ hit must still fail: {r.stdout}"
    hits = findings(r)
    assert any(h.startswith("src/") for h in hits), f"src/ must be reported: {hits}"
    assert not any("node_modules" in h for h in hits), f"node_modules must not be: {hits}"


def case_vendor_excluded() -> None:
    r = run(build({"vendor/lib.go": f'k := "{FAKE_AKIA}"\n'}))
    assert r.returncode == 0, f"vendor/ must be excluded: {r.stdout}"


def case_dist_and_build_excluded() -> None:
    r = run(
        build(
            {
                "dist/bundle.js": f'var k="{FAKE_AKIA}";\n',
                "build/out.js": f'var k="{FAKE_AKIA}";\n',
            }
        )
    )
    assert r.returncode == 0, f"dist/ and build/ must be excluded: {r.stdout}"


def case_minified_excluded() -> None:
    r = run(build({"assets/app.min.js": f'var k="{FAKE_AKIA}";\n'}))
    assert r.returncode == 0, f"*.min.* must be excluded: {r.stdout}"


def case_lockfile_excluded() -> None:
    r = run(build({"package-lock.json": f'{{"h":"{FAKE_AKIA}"}}\n'}))
    assert r.returncode == 0, f"a lockfile must be excluded: {r.stdout}"


def case_fixture_dir_excluded() -> None:
    r = run(build({"tests/fixtures/sample.txt": f"{FAKE_AKIA}\n"}))
    assert r.returncode == 0, f"a fixture directory must be excluded: {r.stdout}"


def case_file_named_like_an_excluded_dir_is_still_scanned() -> None:
    """A FILE named `build` is not the `build/` directory.

    The first version tested every path part against EXCLUDED_DIRS, including the
    filename, so an extensionless file called `build`, `dist`, or `vendor` was
    skipped and a real key inside it went unreported. Found by a fresh-eyes pass.
    """
    for name in ("build", "dist", "vendor"):
        r = run(build({name: f'K = "{FAKE_AKIA}"\n'}))
        assert r.returncode == 1, f"a file named {name!r} must still be scanned: {r.stdout}"
        assert any(name in h for h in findings(r)), f"{name} must be reported: {r.stdout}"


def case_file_named_like_a_fixture_dir_is_still_scanned() -> None:
    r = run(build({"testdata": f'K = "{FAKE_AKIA}"\n'}))
    assert r.returncode == 1, f"a file named 'testdata' must be scanned: {r.stdout}"


def case_extra_exclude_flag() -> None:
    root = build({"src/app.py": f'KEY = "{FAKE_AKIA}"\n'})
    assert run(root).returncode == 1, "the finding must exist without --exclude"
    r = run(root, "--exclude", "src/*")
    assert r.returncode == 0, f"--exclude must suppress it: {r.stdout}"


for name, fn in [
    ("the same key in node_modules/ is not reported, src/ is [criterion 2]", case_node_modules_excluded),
    ("vendor/ is excluded", case_vendor_excluded),
    ("dist/ and build/ are excluded", case_dist_and_build_excluded),
    ("a minified file is excluded", case_minified_excluded),
    ("a lockfile is excluded", case_lockfile_excluded),
    ("a fixture directory is excluded", case_fixture_dir_excluded),
    ("a FILE named build/dist/vendor is still scanned", case_file_named_like_an_excluded_dir_is_still_scanned),
    ("a FILE named testdata is still scanned", case_file_named_like_a_fixture_dir_is_still_scanned),
    ("--exclude suppresses a real finding", case_extra_exclude_flag),
]:
    check(name, fn)


print("\n  [the report never copies the secret]")


def case_report_shape() -> None:
    """Criterion 3, first half: file:line and the pattern name are both present."""
    r = run(build({"src/app.py": f'\n\nKEY = "{FAKE_AKIA}"\n'}))
    hits = findings(r)
    assert hits, f"expected a finding: {r.stdout}"
    assert re.search(r"^src/app\.py:3\s+\[aws-access-key-id\]$", hits[0]), (
        f"the report must be file:line plus the pattern name, got {hits[0]!r}"
    )


def case_value_never_printed() -> None:
    """Criterion 3, second half. The load-bearing one.

    Checks stdout AND stderr, and checks for the key body as well as the whole
    key: printing `AAAAAAAAAAAAAAAA` without the `AKIA` prefix is still a leak.
    """
    r = run(build({"src/app.py": f'KEY = "{FAKE_AKIA}"\n'}))
    combined = r.stdout + r.stderr
    assert FAKE_AKIA not in combined, "the matched value reached the report"
    assert "A" * 16 not in combined, "the key body reached the report"


def case_secret_file_content_is_not_quoted() -> None:
    """A .env is reported by name, and no value inside it reaches the report.

    Its contents ARE read: check() runs content_findings on every candidate,
    secret-named or not. What this pins is that nothing read gets quoted.
    """
    r = run(build({".env": "SUPER_SECRET_VALUE=hunter2\n"}))
    combined = r.stdout + r.stderr
    assert "hunter2" not in combined, "a secret file's contents reached the report"


for name, fn in [
    ("a finding is file:line plus the pattern name [criterion 3]", case_report_shape),
    ("the matched value never reaches stdout or stderr [criterion 3]", case_value_never_printed),
    ("a secret file's contents are never quoted", case_secret_file_content_is_not_quoted),
]:
    check(name, fn)


print("\n  [large files: skipped by default, never in silence]")

# Padding to push a file over a deliberately tiny --max-scan-bytes. Tests set the
# cap rather than writing 2 MiB, so the policy is exercised without the bytes.
TINY_CAP = "64"


def large_file_repo() -> Path:
    """A repo whose only key sits in a file bigger than TINY_CAP bytes."""
    return build({"src/dump.json": f'{{"k": "{FAKE_AKIA}", "pad": "{"x" * 200}"}}\n'})


def case_large_file_is_skipped() -> None:
    r = run(large_file_repo(), "--max-scan-bytes", TINY_CAP)
    assert r.returncode == 0, f"an oversized file must be skipped: {r.stdout}"
    assert not findings(r), f"a skipped file yields no findings: {r.stdout}"


def case_skip_is_reported() -> None:
    """The load-bearing half. A silent skip is what made the old cap wrong."""
    r = run(large_file_repo(), "--max-scan-bytes", TINY_CAP)
    assert "src/dump.json" in r.stdout, f"the skip must name the file: {r.stdout}"
    assert "not scanned" in r.stdout, f"the skip must say what happened: {r.stdout}"
    assert "in what was scanned" in r.stdout, (
        f"the verdict must not claim more than it checked: {r.stdout}"
    )


def case_no_skip_large_files_finds_it() -> None:
    r = run(large_file_repo(), "--max-scan-bytes", TINY_CAP, "--no-skip-large-files")
    assert r.returncode == 1, f"--no-skip-large-files must find the key: {r.stdout}"
    assert any("aws-access-key-id" in f for f in findings(r)), r.stdout


def case_skip_alone_still_exits_0() -> None:
    """A skip is not a finding. A repo with one huge clean file must still pass."""
    root = build({"src/big.txt": "y" * 300 + "\n"})
    r = run(root, "--max-scan-bytes", TINY_CAP)
    assert r.returncode == 0, f"a skip alone must not fail the gate: {r.stdout}"
    assert "not scanned" in r.stdout, f"and must still be reported: {r.stdout}"


def case_skip_report_never_prints_the_value() -> None:
    r = run(large_file_repo(), "--max-scan-bytes", TINY_CAP)
    combined = r.stdout + r.stderr
    assert FAKE_AKIA not in combined, "the skip report leaked the value"
    assert "A" * 16 not in combined, "the skip report leaked the key body"


def case_undecodable_file_is_reported() -> None:
    """A binary file is a skip with a reason, not a crash and not a silent pass."""
    root = build({"src/app.py": "print('x')\n"})
    (root / "blob.bin").write_bytes(b"\xff\xfe\x00\x01not utf8")
    r = run(root)
    assert r.returncode == 0, f"a binary file must not fail the gate: {r.stdout}"
    assert "blob.bin" in r.stdout, f"the skip must name it: {r.stdout}"
    assert "UTF-8" in r.stdout, f"and give the reason: {r.stdout}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


def case_max_scan_bytes_must_be_positive() -> None:
    r = run(build({"src/app.py": "print('x')\n"}), "--max-scan-bytes", "0")
    assert r.returncode == 2, f"a nonsense cap is operator error, got {r.returncode}"


for name, fn in [
    ("a file over the cap is skipped", case_large_file_is_skipped),
    ("a skipped file is named in the report", case_skip_is_reported),
    ("--no-skip-large-files scans it and finds the key", case_no_skip_large_files_finds_it),
    ("a skip alone still exits 0", case_skip_alone_still_exits_0),
    ("the skip report never prints the value", case_skip_report_never_prints_the_value),
    ("an undecodable file is reported, not a crash", case_undecodable_file_is_reported),
    ("--max-scan-bytes 0 exits 2", case_max_scan_bytes_must_be_positive),
]:
    check(name, fn)


print("\n  [clean trees and operator errors]")


def case_clean_tree() -> None:
    r = run(build({"src/app.py": "print('hello')\n", "README.md": "# x\n"}))
    assert r.returncode == 0, f"a clean tree must exit 0: {r.stdout}"
    assert "OK:" in r.stdout, f"a clean run must say so: {r.stdout}"


def case_bad_root() -> None:
    r = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", "/no/such/dir"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, f"a bad root must exit 2, got {r.returncode}"


def case_not_a_git_repo() -> None:
    """Exit 2, not 0. A silent pass on a non-repository is a false clean bill."""
    root = Path(tempfile.mkdtemp())
    (root / "src.py").write_text("x\n", encoding="utf-8")
    r = run(root)
    assert r.returncode == 2, f"a non-repository must exit 2, got {r.returncode}"


def case_git_missing_exits_2_not_1() -> None:
    """A missing git must exit 2 with a message, never crash and never exit 1.

    The first version claimed git_files "returns empty on any git failure", but a
    git absent from PATH raises FileNotFoundError from subprocess, so the script
    died with a traceback and exit 1. Exit 1 means "secrets found", so a machine
    without git reported a FAIL for a scan it never ran. Found by a fresh-eyes pass.
    """
    root = build({"src/app.py": "print('x')\n"})
    empty_bin = Path(tempfile.mkdtemp())
    r = subprocess.run(
        [sys.executable, str(CHECKER), "--repo-root", str(root)],
        capture_output=True,
        text=True,
        env={"PATH": str(empty_bin)},
    )
    assert r.returncode == 2, f"a missing git must exit 2, got {r.returncode}"
    assert "ERROR" in r.stderr, f"it must say what went wrong: {r.stderr!r}"
    assert "Traceback" not in r.stderr, f"it must not crash: {r.stderr}"


for name, fn in [
    ("a clean tree exits 0", case_clean_tree),
    ("a repo root that does not exist exits 2", case_bad_root),
    ("a directory that is not a git repository exits 2", case_not_a_git_repo),
    ("git missing from PATH exits 2, not 1", case_git_missing_exits_2_not_1),
]:
    check(name, fn)


print("\n  [shipped artifact]")


def case_real_repo() -> None:
    """Criterion 4. This repository documents these very patterns in its prose."""
    repo = Path(__file__).resolve().parents[3]
    r = run(repo)
    assert r.returncode == 0, f"this repository must be clean:\n{r.stdout}"


def case_no_third_party_imports() -> None:
    """Criterion 5: stdlib only, in the script and in this suite."""
    stdlib = {
        "__future__", "argparse", "fnmatch", "os", "re", "subprocess", "sys",
        "tempfile", "dataclasses", "pathlib",
    }
    for path in (CHECKER, Path(__file__).resolve()):
        source = path.read_text(encoding="utf-8")
        imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M))
        outside = {m for m in imported if m.split(".")[0] not in stdlib}
        assert not outside, f"{path.name} imports outside the stdlib: {outside}"


for name, fn in [
    ("this repository's own tree is clean [criterion 4]", case_real_repo),
    ("neither file imports outside the standard library [criterion 5]", case_no_third_party_imports),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
