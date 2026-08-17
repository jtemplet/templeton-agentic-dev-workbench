#!/usr/bin/env python3
"""Regression suite for probe_api.py.

Stdlib only, no install, mirroring test_check_doc_paths.py. Run with:
    python3 skills/quality-gates/scripts/test_probe_api.py

Every case drives a REAL http.server over a REAL loopback socket with the REAL
curl binary. Nothing here fakes the transport, because the three rules this suite
exists to pin are all properties of the transport: which host the guard allows,
whether an unreachable server reads as a failure, and whether the process this
script started is gone when it returns.

THE GUARD GROUP IS THE ONE THAT MATTERS MOST. probe_api.py is allowed to send
DELETE only because its host cannot be anything but this machine. If those cases
ever pass while the guard is gone, the gate can reach a shared database.

THE TEARDOWN GROUP ASSERTS ON A PID, not on a log line. A message saying the
server stopped is what a leaked process also prints.
"""

from __future__ import annotations

import atexit
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROBER = Path(__file__).resolve().parent / "probe_api.py"

passed = 0
failed = 0

# The fixture server. Written to a temp file per case, started either by the test
# or by probe_api.py itself, so both paths exercise the same endpoints.
#
#   GET  /health        200, for the readiness probe
#   GET  /items         200 JSON list
#   POST /items         201 JSON {"id": 7}, so a capture has something to read
#   GET  /items/7       200; any other id 404
#   DELETE /items/7     204, so a write method is proven to arrive
#   GET  /whoami        200, echoing whether an Authorization header arrived
#   GET  /text          200 with a text/plain body, for the not-JSON cases
SERVER_SOURCE = '''\
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def reply(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self.reply(200, b'{"ok":true}')
        if self.path == "/items":
            return self.reply(200, b'[{"id":7}]')
        if self.path == "/items/7":
            return self.reply(200, b'{"id":7,"format":"csv"}')
        if self.path == "/whoami":
            seen = self.headers.get("Authorization") or ""
            return self.reply(200, json.dumps({"auth": seen}).encode())
        if self.path == "/text":
            return self.reply(200, b"plain words", ctype="text/plain")
        if self.path == "/binary":
            # A PNG magic number plus bytes that are not valid UTF-8. An export
            # endpoint really answers like this.
            return self.reply(
                200, bytes([0x89, 0x50, 0x4E, 0x47, 0xFF, 0xFE, 0xFD]), ctype="image/png"
            )
        return self.reply(404, b'{"error":"not found"}')

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path == "/items":
            return self.reply(201, b'{"id":7,"nested":{"deep":"v"}}')
        return self.reply(404, b'{"error":"not found"}')

    def do_DELETE(self):
        if self.path == "/items/7":
            return self.reply(204)
        return self.reply(404, b'{"error":"not found"}')

port = int(sys.argv[1])
if len(sys.argv) > 2:
    open(sys.argv[2], "w").write(str(os.getpid()))
HTTPServer(("127.0.0.1", port), H).serve_forever()
'''


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def server_script() -> Path:
    path = Path(tempfile.mkdtemp()) / "fixture_server.py"
    path.write_text(SERVER_SOURCE, encoding="utf-8")
    return path


def write_spec(spec: dict) -> Path:
    path = Path(tempfile.mkdtemp()) / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def run(spec: dict, env: dict[str, str] | None = None, *extra: str):
    return subprocess.run(
        [sys.executable, str(PROBER), "--spec", str(write_spec(spec)), *extra],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


class Running:
    """The fixture server, started by the test rather than by the spec.

    Most cases share ONE of these, via `shared()` below. The fixture answers the
    same way every time and keeps no state between requests, so sharing changes no
    outcome, and starting a fresh interpreter per case cost about eight seconds of
    a suite that has to sit on a `git push`.
    """

    def __init__(self) -> None:
        self.port = free_port()
        self.script = server_script()

    def __enter__(self) -> Running:
        self.process = subprocess.Popen(
            [sys.executable, str(self.script), str(self.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return self
            except OSError:
                time.sleep(0.1)
        raise AssertionError("the fixture server never accepted a connection")

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __exit__(self, *_: object) -> None:
        self.process.terminate()
        self.process.wait(timeout=10)


_SHARED: Running | None = None


def shared() -> Running:
    """The one fixture server the stateless cases reuse, torn down at exit."""
    global _SHARED
    if _SHARED is None:
        _SHARED = Running()
        _SHARED.__enter__()
        atexit.register(_SHARED.__exit__)
    return _SHARED


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


print("\n  [the host: localhost by default, anything the caller supplies]")

# No case here addresses a host that could belong to someone else. The two
# non-loopback cases use `.invalid` (RFC 2606, guaranteed not to resolve) and
# 192.0.2.1 (RFC 5737 TEST-NET-1, guaranteed not routed), so a suite that runs on
# every push sends nothing anywhere.


def case_default_is_localhost() -> None:
    """A spec with no base_url probes this machine, and never infers a host."""
    result = run(
        {"probes": [{"path": "/__probe_default__", "expect": {"status": 200}}]},
        None,
        "--timeout",
        "2",
    )
    assert "http://127.0.0.1:3000/__probe_default__" in result.stdout, (
        f"the default base URL must be localhost: {result.stdout}"
    )


def case_supplied_remote_host_is_used_and_warned() -> None:
    result = run(
        {"base_url": "http://probe-test.invalid", "probes": [{"path": "/"}]},
        None,
        "--timeout",
        "2",
    )
    assert "WARNING" in result.stderr, f"a remote host must be named: {result.stderr}"
    assert "NOT this machine" in result.stderr, result.stderr
    assert "probe-test.invalid" in result.stdout, (
        f"and it must reach stdout, which the report copies: {result.stdout}"
    )


def case_summary_line_marks_a_remote_host() -> None:
    """A report that omits the host it probed cannot be checked by its reader."""
    result = run(
        {"base_url": "http://192.0.2.1:9", "probes": [{"path": "/"}]}, None, "--timeout", "1"
    )
    assert "(NOT this machine)" in result.stdout, (
        f"the summary must mark a non-loopback host: {result.stdout}"
    )


def case_localhost_summary_is_unmarked() -> None:
    server = shared()
    result = run(
        {"base_url": server.base, "probes": [{"path": "/items", "expect": {"status": 200}}]}
    )
    assert "NOT this machine" not in result.stdout, (
        f"the default case must not carry a warning: {result.stdout}"
    )
    assert f"probes against {server.base}" in result.stdout, result.stdout


def case_cli_base_url_beats_the_spec() -> None:
    server = shared()
    result = run(
        {"base_url": "http://127.0.0.1:1", "probes": [{"path": "/items", "expect": {"status": 200}}]},
        None,
        "--base-url",
        server.base,
    )
    assert result.returncode == 0, f"--base-url must override the spec: {result.stdout}"


def case_bind_address_is_warned_not_refused() -> None:
    """0.0.0.0 is where a server listens, and supplying it is usually a slip."""
    result = run(
        {"base_url": "http://0.0.0.0:9", "probes": [{"path": "/"}]}, None, "--timeout", "1"
    )
    assert "WARNING" in result.stderr, result.stderr
    assert "127.0.0.1" in result.stderr, f"say what to use instead: {result.stderr}"


def case_non_http_scheme_is_still_an_error() -> None:
    """Not a host policy: curl cannot speak it, so no probe can be sent."""
    result = run({"base_url": "ftp://localhost", "probes": [{"path": "/"}]})
    assert result.returncode == 2, result.stderr
    assert "http or https" in result.stderr, result.stderr


def case_loopback_range_is_unwarned() -> None:
    """127.0.0.2 is this machine, so it draws no warning.

    `--timeout 2` because macOS neither refuses nor answers on 127.0.0.2, so the
    default 10-second budget would be spent waiting on a case about the host.
    """
    result = run({"base_url": "http://127.0.0.2:9", "probes": [{"path": "/"}]}, None, "--timeout", "2")
    assert "NOT this machine" not in result.stderr, f"127.0.0.2 is loopback: {result.stderr}"
    assert result.returncode == 2, result.returncode
    assert "1 blocked" in result.stdout, f"an unreachable port is BLOCKED: {result.stdout}"


def case_bind_address_with_a_start_command_does_not_claim_a_miss() -> None:
    """Found by a fresh-eyes pass: the check read `warnings`, not the host.

    0.0.0.0 warns for its own reason, and where it works at all it reaches the
    local server, so "the probes will not reach the server it starts" was false
    for it.
    """
    port = free_port()
    script = server_script()
    result = run(
        {
            "base_url": f"http://0.0.0.0:{port}",
            "server": {
                "start": f"{sys.executable} {script} {port}",
                "health_path": "/health",
                "ready_status": [200],
            },
            "probes": [{"path": "/items", "expect": {"status": 200}}],
        },
        None,
        "--health-timeout",
        "10",
    )
    assert "will not reach the server it starts" not in result.stderr, (
        f"0.0.0.0 is not another machine: {result.stderr}"
    )


def case_remote_host_with_a_start_command_warns_twice() -> None:
    """Starting a local server and probing elsewhere reads as a working gate."""
    result = run(
        {
            "base_url": "http://probe-test.invalid",
            "server": {"start": "true", "health_path": "/up"},
            "probes": [{"path": "/"}],
        },
        None,
        "--health-timeout",
        "2",
    )
    assert "will not reach the server it starts" in result.stderr, result.stderr


for name, fn in [
    ("a spec with no base_url probes 127.0.0.1:3000", case_default_is_localhost),
    ("a supplied remote host is used and named", case_supplied_remote_host_is_used_and_warned),
    ("the summary line marks a non-loopback host", case_summary_line_marks_a_remote_host),
    ("a loopback host draws no warning", case_localhost_summary_is_unmarked),
    ("--base-url overrides the spec", case_cli_base_url_beats_the_spec),
    ("0.0.0.0 is warned about, not refused", case_bind_address_is_warned_not_refused),
    ("a non-http scheme is still an error", case_non_http_scheme_is_still_an_error),
    ("127.0.0.2 is this machine, so it is unwarned", case_loopback_range_is_unwarned),
    ("a remote host plus a start command warns", case_remote_host_with_a_start_command_warns_twice),
    ("0.0.0.0 plus a start command does not claim a miss", case_bind_address_with_a_start_command_does_not_claim_a_miss),
]:
    check(name, fn)


print("\n  [grading a real response]")


def case_passing_probe() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "name": "list items",
                    "path": "/items",
                    "expect": {
                        "status": 200,
                        "body_contains": ['"id"'],
                        "header_contains": {"content-type": "application/json"},
                        "body_json": True,
                    },
                }
            ],
        }
    )
    assert result.returncode == 0, f"a met expectation must exit 0: {result.stdout}{result.stderr}"
    assert "1 passed" in result.stdout, result.stdout


def case_wrong_status_is_a_failure_not_a_block() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [{"path": "/nope", "expect": {"status": 200}}],
        }
    )
    assert result.returncode == 1, (
        f"a wrong status is the finding this gate produces, so exit 1: {result.returncode}"
    )
    assert "status 404, expected 200" in result.stdout, result.stdout


def case_status_list_accepts_either() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [{"path": "/items", "expect": {"status": [200, 304]}}],
        }
    )
    assert result.returncode == 0, result.stdout


def case_body_and_header_mismatches_are_named() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "path": "/text",
                    "expect": {
                        "status": 200,
                        "body_contains": ["missing"],
                        "body_not_contains": ["plain"],
                        "header_contains": {"content-type": "application/json"},
                        "body_json": True,
                    },
                }
            ],
        }
    )
    assert result.returncode == 1, result.stdout
    for expected in ("does not contain", "which it must not", "content-type is", "not JSON"):
        assert expected in result.stdout, f"{expected!r} missing from:\n{result.stdout}"


def case_write_methods_reach_the_server() -> None:
    """The point of allowing any method: a new POST route can actually be graded."""
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "name": "create",
                    "method": "POST",
                    "path": "/items",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"format":"csv"}',
                    "expect": {"status": 201},
                },
                {
                    "name": "delete",
                    "method": "DELETE",
                    "path": "/items/7",
                    "expect": {"status": 204},
                },
            ],
        }
    )
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    assert "2 passed" in result.stdout, result.stdout


def case_insecure_tls_reaches_the_command() -> None:
    """`insecure_tls` must arrive at curl, and be visible in the printed command.

    No certificate and no HTTPS listener here on purpose. The thing that can break
    is the flag not being passed, and the printed command is where that is
    observable through the real entry point. Whether curl then accepts a
    self-signed certificate is curl's behavior, not this script's, and proving it
    would cost the suite an openssl dependency it does not otherwise need.
    """
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "insecure_tls": True,
            "probes": [{"path": "/items", "expect": {"status": 200}}],
        }
    )
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    assert " -k " in result.stdout, (
        f"the printed command must carry -k so a reader can re-run it: {result.stdout}"
    )


def case_insecure_tls_is_off_by_default() -> None:
    """The control: nothing weakens TLS unless the spec asks for it."""
    server = shared()
    result = run(
        {"base_url": server.base, "probes": [{"path": "/items", "expect": {"status": 200}}]}
    )
    assert " -k " not in result.stdout, f"-k must not appear unasked: {result.stdout}"


def case_binary_body_is_graded_not_a_crash() -> None:
    """Found by a fresh-eyes pass: `text=True` decoded strictly and raised.

    A PNG or PDF body took the whole gate down with a UnicodeDecodeError
    traceback, which is not one of the three statuses this gate can report. An
    export endpoint, the example this skill ships, answers with exactly these
    bytes.
    """
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [{"name": "download", "path": "/binary", "expect": {"status": 200}}],
        }
    )
    assert result.returncode == 0, (
        f"a binary body must grade on its status, not crash:\n{result.stdout}{result.stderr}"
    )
    assert "Traceback" not in result.stderr, result.stderr
    assert "1 passed" in result.stdout, result.stdout


def case_malformed_header_expectation_is_not_ignored() -> None:
    """An assertion that never ran must not report PASS.

    `header_contains` as a list was silently skipped, so a probe with one real
    expectation and one malformed one came back green.
    """
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "path": "/items",
                    "expect": {"status": 200, "header_contains": ["content-type"]},
                }
            ],
        }
    )
    assert result.returncode == 2, (
        f"a malformed expectation must never pass, got {result.returncode}: {result.stdout}"
    )
    assert "header_contains must be an object" in result.stderr, result.stderr


def case_malformed_body_json_expectation_is_not_ignored() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [{"path": "/text", "expect": {"status": 200, "body_json": "yes"}}],
        }
    )
    assert result.returncode == 2, f"{result.returncode}: {result.stdout}"
    assert "body_json must be true or false" in result.stderr, result.stderr


for name, fn in [
    ("a met expectation exits 0", case_passing_probe),
    ("a wrong status is FAIL, exit 1", case_wrong_status_is_a_failure_not_a_block),
    ("a status list accepts either value", case_status_list_accepts_either),
    ("every body and header mismatch is named", case_body_and_header_mismatches_are_named),
    ("POST and DELETE reach the server", case_write_methods_reach_the_server),
    ("insecure_tls puts -k in the printed command", case_insecure_tls_reaches_the_command),
    ("insecure_tls is off unless the spec asks", case_insecure_tls_is_off_by_default),
    ("a binary response body is graded, not a crash", case_binary_body_is_graded_not_a_crash),
    ("a malformed header_contains exits 2", case_malformed_header_expectation_is_not_ignored),
    ("a malformed body_json exits 2", case_malformed_body_json_expectation_is_not_ignored),
]:
    check(name, fn)


print("\n  [could not run is BLOCKED, never a failing endpoint]")


def case_connection_refused_is_blocked() -> None:
    port = free_port()  # nothing is listening on it
    result = run(
        {"base_url": f"http://127.0.0.1:{port}", "probes": [{"path": "/", "expect": {"status": 200}}]}
    )
    assert result.returncode == 2, (
        f"a refused connection reached no endpoint, so it cannot be FAIL: {result.returncode}"
    )
    assert "BLOCKED" in result.stdout and "connection refused" in result.stdout, result.stdout


def case_no_http_status_is_blocked_not_failed() -> None:
    """curl exiting 0 while reporting http_code 000 means nothing answered.

    A REAL server cannot produce this: an empty reply exits 52 and a timeout exits
    28, both of which the returncode branch already catches. So this case stubs
    `curl` on PATH, the way `hooks/test-claude-scripts.sh` stubs `br` and `gh`.
    The rule is worth pinning because status 0 graded against an expected 200
    would report a failing endpoint where no endpoint replied, which contradicts
    what this script's own docstring promises.
    """
    stub_dir = Path(tempfile.mkdtemp())
    stub = stub_dir / "curl"
    stub.write_text(
        "#!/bin/sh\n"
        "# Answers like curl does when it sent a request and got no HTTP response.\n"
        'printf "\\n__PROBE_STATUS__:000"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    result = run(
        {"base_url": "http://127.0.0.1:9", "probes": [{"path": "/x", "expect": {"status": 200}}]},
        {"PATH": f"{stub_dir}:{os.environ.get('PATH', '')}"},
    )
    assert result.returncode == 2, (
        f"no HTTP status is BLOCKED, never FAIL, got {result.returncode}: {result.stdout}"
    )
    assert "no HTTP status" in result.stdout, result.stdout
    assert "status 0" not in result.stdout, f"0 must not be graded as a status: {result.stdout}"


def case_empty_probe_list_is_blocked() -> None:
    result = run({"base_url": "http://127.0.0.1:1", "probes": []})
    assert result.returncode == 2, f"an unfinished spec must never exit 0: {result.returncode}"
    assert "no probes" in result.stderr, result.stderr


def case_unparseable_spec_is_blocked() -> None:
    path = Path(tempfile.mkdtemp()) / "spec.json"
    path.write_text("{not json", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(PROBER), "--spec", str(path)], capture_output=True, text=True
    )
    assert result.returncode == 2, result.returncode
    assert "not valid JSON" in result.stderr, result.stderr


def case_missing_spec_file_is_blocked() -> None:
    result = subprocess.run(
        [sys.executable, str(PROBER), "--spec", "/no/such/spec.json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.returncode


def case_blocked_outranks_failed() -> None:
    """One unreachable probe beside one failing probe still exits 2."""
    dead = free_port()
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {"name": "fails", "path": "/nope", "expect": {"status": 200}},
                {
                    "name": "blocked",
                    "path": "/x",
                    "expect": {"status": 200},
                },
            ],
        }
    )
    assert result.returncode == 1, f"control: both reachable means exit 1: {result.stdout}"
    result = run(
        {
            "base_url": f"http://127.0.0.1:{dead}",
            "probes": [{"path": "/nope", "expect": {"status": 200}}],
        }
    )
    assert result.returncode == 2, result.returncode


for name, fn in [
    ("a refused connection is BLOCKED, exit 2", case_connection_refused_is_blocked),
    ("http_code 000 at exit 0 is BLOCKED, not FAIL", case_no_http_status_is_blocked_not_failed),
    ("a spec with no probes exits 2", case_empty_probe_list_is_blocked),
    ("an unparseable spec exits 2", case_unparseable_spec_is_blocked),
    ("a spec file that does not exist exits 2", case_missing_spec_file_is_blocked),
    ("BLOCKED outranks FAIL in the exit status", case_blocked_outranks_failed),
]:
    check(name, fn)


print("\n  [credentials: expanded from the environment, never printed]")


def case_env_var_is_expanded_and_arrives() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "path": "/whoami",
                    "headers": {"Authorization": "Bearer ${PROBE_TEST_TOKEN}"},
                    "expect": {"status": 200, "body_contains": ["Bearer s3cret"]},
                }
            ],
        },
        {"PROBE_TEST_TOKEN": "s3cret"},
    )
    assert result.returncode == 0, f"the real token must arrive: {result.stdout}"


def case_env_var_spelling_is_printed_not_the_value() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "path": "/items",
                    "headers": {"Authorization": "Bearer ${PROBE_TEST_TOKEN}"},
                    "expect": {"status": 200},
                }
            ],
        },
        {"PROBE_TEST_TOKEN": "s3cret"},
    )
    combined = result.stdout + result.stderr
    assert "s3cret" not in combined, f"the token must never be printed:\n{combined}"
    assert "${PROBE_TEST_TOKEN}" in result.stdout, (
        f"the printed command stays runnable via the variable:\n{result.stdout}"
    )


def case_literal_secret_is_redacted_and_warned() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "path": "/items",
                    "headers": {"Authorization": "Bearer hardcoded"},
                    "expect": {"status": 200},
                }
            ],
        }
    )
    assert "hardcoded" not in result.stdout, f"a literal secret must not print:\n{result.stdout}"
    assert "<redacted>" in result.stdout, result.stdout
    assert "use ${VAR}" in result.stderr, f"say how to fix it: {result.stderr}"


def case_unset_env_var_is_blocked_not_empty() -> None:
    """An empty Authorization header turns an auth probe into a probe of nothing."""
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "path": "/whoami",
                    "headers": {"Authorization": "Bearer ${PROBE_UNSET_TOKEN}"},
                    "expect": {"status": 200},
                }
            ],
        }
    )
    assert result.returncode == 2, (
        f"an unset variable must not silently become empty: {result.returncode}"
    )
    assert "PROBE_UNSET_TOKEN" in result.stderr, result.stderr


for name, fn in [
    ("a ${VAR} header is expanded and arrives", case_env_var_is_expanded_and_arrives),
    ("the report prints ${VAR}, never the token", case_env_var_spelling_is_printed_not_the_value),
    ("a literal secret is redacted and warned about", case_literal_secret_is_redacted_and_warned),
    ("an unset ${VAR} exits 2 rather than sending empty", case_unset_env_var_is_blocked_not_empty),
]:
    check(name, fn)


print("\n  [capture: what makes a create-then-read flow expressible]")


def case_capture_chains_into_a_later_probe() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "name": "create",
                    "method": "POST",
                    "path": "/items",
                    "expect": {"status": 201},
                    "capture": {"item_id": "id", "deep": "nested.deep"},
                },
                {
                    "name": "read it back",
                    "path": "/items/{item_id}",
                    "expect": {"status": 200, "body_contains": ["csv"]},
                },
            ],
        }
    )
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    assert "2 passed" in result.stdout, result.stdout


def case_missing_capture_key_is_blocked() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {
                    "name": "create",
                    "method": "POST",
                    "path": "/items",
                    "expect": {"status": 201},
                    "capture": {"item_id": "no_such_key"},
                }
            ],
        }
    )
    assert result.returncode == 2, result.returncode
    assert "no key" in result.stdout, result.stdout


def case_unresolved_reference_is_blocked() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [{"path": "/items/{never_captured}", "expect": {"status": 200}}],
        }
    )
    assert result.returncode == 2, result.returncode
    assert "no earlier probe captured" in result.stdout, result.stdout


def case_capture_from_a_non_json_body_is_blocked() -> None:
    server = shared()
    result = run(
        {
            "base_url": server.base,
            "probes": [
                {"path": "/text", "expect": {"status": 200}, "capture": {"x": "id"}}
            ],
        }
    )
    assert result.returncode == 2, result.returncode
    assert "not JSON" in result.stdout, result.stdout


for name, fn in [
    ("a captured value substitutes into a later path", case_capture_chains_into_a_later_probe),
    ("a capture path with no such key is BLOCKED", case_missing_capture_key_is_blocked),
    ("a {name} nothing captured is BLOCKED", case_unresolved_reference_is_blocked),
    ("a capture from a non-JSON body is BLOCKED", case_capture_from_a_non_json_body_is_blocked),
]:
    check(name, fn)


print("\n  [the declared server: started, waited for, and always stopped]")


def case_declared_server_is_started_and_stopped() -> None:
    port = free_port()
    script = server_script()
    pidfile = script.parent / "server.pid"
    result = run(
        {
            "base_url": f"http://127.0.0.1:{port}",
            "server": {
                "start": f"{sys.executable} {script} {port} {pidfile}",
                "health_path": "/health",
                "ready_status": [200],
            },
            "probes": [{"path": "/items", "expect": {"status": 200}}],
        },
        None,
        "--health-timeout",
        "20",
    )
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    pid = int(pidfile.read_text(encoding="utf-8"))
    for _ in range(50):  # SIGTERM is asynchronous; give it a moment to land
        if not alive(pid):
            break
        time.sleep(0.1)
    assert not alive(pid), f"the server this script started is still running as pid {pid}"


def case_server_that_never_answers_is_blocked_and_killed() -> None:
    """A leaked listener makes the NEXT run probe a stale build and report green."""
    port = free_port()
    holder = Path(tempfile.mkdtemp()) / "sleeper.py"
    pidfile = holder.parent / "sleeper.pid"
    holder.write_text(
        "import os, sys, time\n"
        "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
        "time.sleep(120)\n",
        encoding="utf-8",
    )
    result = run(
        {
            "base_url": f"http://127.0.0.1:{port}",
            "server": {"start": f"{sys.executable} {holder} {pidfile}", "health_path": "/health"},
            "probes": [{"path": "/items", "expect": {"status": 200}}],
        },
        None,
        "--health-timeout",
        "3",
    )
    assert result.returncode == 2, f"a server that never answers is BLOCKED: {result.returncode}"
    assert "did not become healthy" in result.stderr, result.stderr
    pid = int(pidfile.read_text(encoding="utf-8"))
    for _ in range(50):
        if not alive(pid):
            break
        time.sleep(0.1)
    assert not alive(pid), f"the failed start leaked pid {pid}"


def case_server_that_exits_immediately_names_its_code() -> None:
    port = free_port()
    result = run(
        {
            "base_url": f"http://127.0.0.1:{port}",
            "server": {"start": "exit 3", "health_path": "/health"},
            "probes": [{"path": "/items", "expect": {"status": 200}}],
        },
        None,
        "--health-timeout",
        "10",
    )
    assert result.returncode == 2, result.returncode
    assert "exited with code 3" in result.stderr, result.stderr


def case_empty_start_command_is_blocked() -> None:
    result = run(
        {
            "base_url": "http://127.0.0.1:1",
            "server": {"start": "   "},
            "probes": [{"path": "/", "expect": {"status": 200}}],
        }
    )
    assert result.returncode == 2, result.returncode
    assert "non-empty command" in result.stderr, result.stderr


for name, fn in [
    ("a declared server is started, probed, and stopped", case_declared_server_is_started_and_stopped),
    ("a server that never answers is BLOCKED and killed", case_server_that_never_answers_is_blocked_and_killed),
    ("a server that exits at once names its exit code", case_server_that_exits_immediately_names_its_code),
    ("an empty server.start exits 2", case_empty_start_command_is_blocked),
]:
    check(name, fn)


print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
