#!/usr/bin/env python3
"""Drive a change's REST endpoints with real curl requests and grade the answers.

This is Gate 8 of the quality-gates skill, and the `curl` method route_qa.py
picks. It takes a probe spec, sends each request through `curl`, and compares the
real status, headers, and body against what the spec expects.

It exists as a script because three of its rules cannot survive as prose.

LOCALHOST IS THE DEFAULT, AND ONLY THE CALLER CHANGES IT. With no `base_url` in
the spec and no `--base-url` on the command line, this probes
`http://127.0.0.1:3000`. It never infers a host from a config file, an
environment variable, or a URL it read somewhere in the repository: a host that
arrives by inference is a host nobody chose, and this script sends DELETE.

A supplied host outside `localhost`, `127.0.0.0/8`, and `::1` is USED, because
supplying it is the caller saying so, and warned about by name on every run.
Author direction, and it replaces an earlier hard refusal. Two consequences worth
stating plainly, since the refusal was what used to answer for them:

  1. The write methods are no longer fenced by the address. A spec pointed at a
     shared host will create and delete records on it, and the only thing between
     that and a bad afternoon is the person who typed the URL.
  2. So the warning is loud and the base URL appears in the run's summary line,
     which is what the skill copies into its report. A remote host that was
     probed cannot end up unmentioned.

THE SERVER TEARDOWN IS THE SECOND. When the spec declares a start command, the
server runs in its own process group and is killed in a `finally`, so an
exception, a failed health probe, or a Ctrl-C still stops it. A prose instruction
to "stop the server afterward" leaks one listener per aborted run, and the next
run then probes a stale build and reports a green gate.

THE COULD-NOT-RUN SPLIT IS THE THIRD. curl exit 7 is a refused connection and
exit 28 is a timeout. Neither is a failing endpoint, and reporting either as FAIL
tells the author to fix code that was never reached. Those exits are BLOCKED, and
BLOCKED is exit 2 here, matching the skill's status model: a gate that could not
run has not passed and has not failed.

NO SECRET REACHES THE OUTPUT. A header value that came from `${VAR}` prints as
`${VAR}`, so the printed curl command stays runnable without carrying the token.
A literal value under a sensitive header name prints as `<redacted>`, and the run
says the spec should use an environment variable instead. This is Gate 6's rule
about never quoting a matched secret, applied to the gate that handles live
credentials.

EXIT CODES, in the skill's own vocabulary:

    0  every probe met its expectation                        PASS
    1  at least one probe's response differed, none errored   FAIL
    2  the gate could not run as specified                    BLOCKED

Exit 2 covers a missing spec, a spec with no probes, a `base_url` whose scheme
curl cannot speak, an unexpanded `${VAR}`, a server that never became healthy, an
absent curl, a refused connection, and an unresolved `{capture}`. It never covers
a wrong status code, which is the finding this gate exists to produce.

SPEC FORMAT

`base_url` is optional and defaults to `http://127.0.0.1:3000`.

    {
      "base_url": "http://127.0.0.1:3000",
      "insecure_tls": false,
      "server": {
        "start": "bin/rails server -p 3000",
        "health_path": "/up",
        "ready_status": [200, 204, 404]
      },
      "probes": [
        {
          "name": "create an export",
          "method": "POST",
          "path": "/api/v1/exports",
          "headers": {"Content-Type": "application/json",
                      "Authorization": "Bearer ${API_TOKEN}"},
          "body": "{\\"format\\": \\"csv\\"}",
          "expect": {
            "status": 201,
            "body_contains": ["\\"id\\""],
            "body_not_contains": ["error"],
            "header_contains": {"content-type": "application/json"}
          },
          "capture": {"export_id": "id"}
        },
        {
          "name": "fetch it back",
          "method": "GET",
          "path": "/api/v1/exports/{export_id}",
          "expect": {"status": 200}
        }
      ]
    }

`capture` reads a dot path out of the JSON response (`data.id` walks two levels,
and a number indexes a list), and `{name}` substitutes it into any later probe's
path, headers, or body. Probes run in the order written, which is what lets a
write flow read as create, fetch, delete.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

EXIT_OK = 0
EXIT_EXPECTATION_FAILED = 1
EXIT_BLOCKED = 2

# Where this gate probes when the caller names no host. See the default-host note
# in the docstring: a host that arrives by inference is a host nobody chose.
DEFAULT_BASE_URL = "http://127.0.0.1:3000"

# The hosts that mean this machine, so everything else can be warned about.
LOOPBACK_NAMES = ("localhost", "ip6-localhost", "localhost.localdomain")

# curl's own exits for "never reached the server". Separated from every other
# non-zero exit only in the message; all of them are BLOCKED.
CURL_UNREACHED = {6: "host not resolved", 7: "connection refused", 28: "timed out"}

# A header whose value must never be printed. Matched on the NAME, because the
# value is exactly what must not be inspected or echoed.
SENSITIVE_HEADER_RE = re.compile(
    r"authoriz|cookie|token|secret|password|api[-_]?key|x-csrf", re.IGNORECASE
)

# `${VAR}` in a spec string. Expanded from the environment, so a spec file
# committed to a repository never has to carry a credential.
ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# `{name}` from a previous probe's `capture`. Distinct syntax from `${VAR}` on
# purpose: one comes from the environment before the run, the other from a
# response during it, and a single syntax for both hides which failed.
#
# The lookbehind is not cosmetic. `${API_TOKEN}` ENDS in `{API_TOKEN}`, so
# without it every environment variable reads as a capture nothing captured, and
# an authenticated probe is BLOCKED before it is ever sent. test_probe_api.py
# caught exactly that.
CAPTURE_RE = re.compile(r"(?<!\$)\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Written by curl into one file, then read back. `-w` appends the status after
# the body so a single request yields both without a second call.
STATUS_MARKER = "\n__PROBE_STATUS__:"


class SpecError(Exception):
    """The spec cannot be executed as written, so nothing ran. Always exit 2."""


class ProbeBlocked(Exception):
    """One probe could not reach a verdict. BLOCKED, never FAIL."""


@dataclass
class Result:
    """One probe's outcome, in the vocabulary the skill's report uses."""

    name: str
    command: str
    status: str  # "PASS", "FAIL", or "BLOCKED"
    detail: str


def load_spec(path: Path) -> dict[str, object]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpecError(f"could not read the spec: {exc}") from exc
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SpecError(f"the spec is not valid JSON: {exc}") from exc
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a JSON object")
    probes = spec.get("probes")
    if not isinstance(probes, list) or not probes:
        # Never exit 0 here. A spec with no probes is a spec someone forgot to
        # finish, and reporting it as a clean gate is this script's worst outcome.
        raise SpecError("the spec declares no probes, so nothing would be checked")
    return spec


def is_loopback(host: str) -> bool:
    """Whether this host is this machine. See the default-host note up top."""
    if host.lower() in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False  # a DNS name that is not one of the localhost spellings


def addresses_another_machine(base_url: str) -> bool:
    """Whether this URL leaves this machine.

    `0.0.0.0` answers False. It is a bind address rather than a target, and where
    it works at all it reaches the local server, so it is warned about separately
    and never counted as remote.
    """
    host = urllib.parse.urlsplit(base_url).hostname or ""
    return host != "0.0.0.0" and not is_loopback(host)


def resolve_base_url(supplied: str | None) -> tuple[str, list[str]]:
    """The base URL to probe, plus the warnings the run must carry.

    A scheme curl cannot speak is still an error, because no host answers it. The
    host itself is the caller's call.
    """
    if not supplied:
        return DEFAULT_BASE_URL, []

    parsed = urllib.parse.urlsplit(supplied)
    if parsed.scheme not in ("http", "https"):
        raise SpecError(
            f"base_url {supplied!r} must use http or https, not {parsed.scheme or 'no scheme'}"
        )
    host = parsed.hostname
    if not host:
        raise SpecError(f"base_url {supplied!r} names no host")

    warnings: list[str] = []
    if host == "0.0.0.0":
        # Allowed, because it was supplied, but it is almost always a mistake:
        # 0.0.0.0 is where a server LISTENS. macOS does not route it as a target.
        warnings.append(
            "base_url addresses 0.0.0.0, which is a bind address rather than a "
            "target. Use 127.0.0.1 if you meant this machine."
        )
    elif not is_loopback(host):
        warnings.append(
            f"base_url addresses {host}, which is NOT this machine. Every probe "
            f"below, including any POST, PUT, PATCH, or DELETE, runs against it. "
            f"Say so in the report."
        )
    return supplied.rstrip("/"), warnings


def expand_env(value: str, where: str) -> str:
    """Substitute every `${VAR}`, and refuse an absent one.

    An unset variable must not become an empty string. An empty `Authorization`
    header turns a probe that proves auth works into a probe that proves nothing,
    and it passes.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in os.environ:
            raise SpecError(f"{where} references ${{{name}}}, which is not set")
        return os.environ[name]

    return ENV_RE.sub(replace, value)


def expand_captures(value: str, captured: dict[str, str], where: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in captured:
            raise ProbeBlocked(
                f"{where} references {{{name}}}, which no earlier probe captured"
            )
        return captured[name]

    return CAPTURE_RE.sub(replace, value)


def redact(name: str, value: str, raw: str) -> str:
    """The printable form of one header value.

    `raw` is the value before `${VAR}` expansion. When it held a variable, that
    spelling prints: the command stays runnable and the secret stays out of the
    report. A literal secret prints as `<redacted>`, and the caller is told to
    move it into a variable.
    """
    if not SENSITIVE_HEADER_RE.search(name):
        return value
    if ENV_RE.search(raw):
        return raw
    return "<redacted>"


def dig(payload: object, dotted: str) -> str:
    """Follow a dot path into a decoded JSON body, or raise ProbeBlocked."""
    current = payload
    for key in dotted.split("."):
        if isinstance(current, list):
            try:
                current = current[int(key)]
            except (ValueError, IndexError):
                raise ProbeBlocked(f"capture path {dotted!r} has no index {key!r}") from None
        elif isinstance(current, dict):
            if key not in current:
                raise ProbeBlocked(f"capture path {dotted!r} has no key {key!r}")
            current = current[key]
        else:
            raise ProbeBlocked(f"capture path {dotted!r} ran past a scalar at {key!r}")
    if isinstance(current, (dict, list)):
        raise ProbeBlocked(f"capture path {dotted!r} names a structure, not a value")
    return "" if current is None else str(current)


@dataclass
class Request:
    """One built request: what curl will send, and what may be printed."""

    method: str
    url: str
    headers: dict[str, str]
    printable_headers: dict[str, str]
    body: str | None
    literal_secrets: list[str]


def build_request(
    probe: dict[str, object], base_url: str, captured: dict[str, str]
) -> Request:
    name = str(probe.get("name") or probe.get("path") or "unnamed probe")
    method = str(probe.get("method", "GET")).upper()
    raw_path = probe.get("path")
    if not isinstance(raw_path, str) or not raw_path.startswith("/"):
        raise SpecError(f"{name}: path must be a string starting with /")

    def prepare(value: str, where: str) -> str:
        return expand_env(expand_captures(value, captured, where), where)

    url = base_url + prepare(raw_path, f"{name} path")

    headers: dict[str, str] = {}
    printable: dict[str, str] = {}
    literal_secrets: list[str] = []
    raw_headers = probe.get("headers") or {}
    if not isinstance(raw_headers, dict):
        raise SpecError(f"{name}: headers must be an object")
    for key, raw_value in raw_headers.items():
        if not isinstance(raw_value, str):
            raise SpecError(f"{name}: header {key!r} must be a string")
        resolved = prepare(raw_value, f"{name} header {key}")
        headers[str(key)] = resolved
        printable[str(key)] = redact(str(key), resolved, raw_value)
        if SENSITIVE_HEADER_RE.search(str(key)) and not ENV_RE.search(raw_value):
            literal_secrets.append(str(key))

    body = probe.get("body")
    if body is not None and not isinstance(body, str):
        body = json.dumps(body)
    if isinstance(body, str):
        body = prepare(body, f"{name} body")

    return Request(method, url, headers, printable, body, literal_secrets)


def curl_argv(request: Request, timeout: int, insecure_tls: bool) -> list[str]:
    argv = [
        "curl",
        "--silent",
        "--show-error",
        "--no-progress-meter",
        "--max-time",
        str(timeout),
        "--request",
        request.method,
        "--dump-header",
        "-",
        "--write-out",
        f"{STATUS_MARKER}%{{http_code}}",
    ]
    if insecure_tls:
        argv.append("--insecure")
    for key, value in request.headers.items():
        argv += ["--header", f"{key}: {value}"]
    if request.body is not None:
        argv += ["--data-binary", request.body]
    argv.append(request.url)
    return argv


def printable_command(request: Request, timeout: int, insecure_tls: bool) -> str:
    """The same request as a command a reader can paste, with secrets redacted."""
    parts = ["curl", "-sS", "-i", "--max-time", str(timeout), "-X", request.method]
    if insecure_tls:
        parts.append("-k")
    for key, value in request.printable_headers.items():
        parts += ["-H", shell_quote(f"{key}: {value}")]
    if request.body is not None:
        parts += ["--data-binary", shell_quote(request.body)]
    parts.append(shell_quote(request.url))
    return " ".join(parts)


def shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]*", value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: str


def send(request: Request, timeout: int, insecure_tls: bool) -> Response:
    """Send one request and decode the answer, whatever bytes it carries.

    BYTES, THEN DECODE WITH REPLACEMENT. `subprocess.run(text=True)` decodes
    strictly, so an endpoint answering with a PNG, a PDF, or a gzip body raised
    UnicodeDecodeError out of this function and took the whole gate down with a
    traceback. An export endpoint is the example this skill ships, and a real one
    returns exactly those bytes. A replaced byte cannot invent a status code, and
    a body assertion against binary content was never going to be meaningful.
    """
    argv = curl_argv(request, timeout, insecure_tls)
    try:
        completed = subprocess.run(argv, capture_output=True, timeout=timeout + 15)
    except FileNotFoundError:
        raise ProbeBlocked("curl is not on PATH, so no probe can be sent") from None
    except subprocess.TimeoutExpired:
        raise ProbeBlocked(f"curl did not return within {timeout + 15}s") from None
    if completed.returncode != 0:
        reason = CURL_UNREACHED.get(completed.returncode, "curl failed")
        detail = completed.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise ProbeBlocked(
            f"{reason} (curl exit {completed.returncode})"
            + (f": {detail[-1]}" if detail else "")
        )
    return parse_response(completed.stdout.decode("utf-8", errors="replace"))


def parse_response(raw: str) -> Response:
    """Split curl's output into the status, the headers, and the body."""
    body_and_status = raw
    status = -1
    marker = raw.rfind(STATUS_MARKER)
    if marker != -1:
        body_and_status = raw[:marker]
        tail = raw[marker + len(STATUS_MARKER) :].strip()
        status = int(tail) if tail.isdigit() else -1
    if status <= 0:
        # `<= 0`, not `== -1`. curl writes http_code 000 when it sent a request
        # and got no HTTP response back, and grading 0 against an expected 200
        # reports a failing endpoint where nothing answered. BLOCKED is the honest
        # status, per this script's own could-not-run rule.
        raise ProbeBlocked("curl reported no HTTP status, so nothing answered")

    # `--dump-header -` writes the header block to stdout ahead of the body, and a
    # redirect chain writes one block per hop. The last block is the response
    # that answered.
    headers: dict[str, str] = {}
    body = body_and_status
    while True:
        match = re.match(r"HTTP/[\d.]+ \d+[^\n]*\n", body)
        if not match:
            break
        rest = body[match.end() :]
        block_end = rest.find("\n\n")
        alt_end = rest.find("\r\n\r\n")
        if alt_end != -1 and (block_end == -1 or alt_end < block_end):
            block_end, width = alt_end, 4
        else:
            width = 2
        if block_end == -1:
            headers = parse_header_block(rest)
            body = ""
            break
        headers = parse_header_block(rest[:block_end])
        body = rest[block_end + width :]
    return Response(status, headers, body)


def parse_header_block(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    return headers


def grade(expect: dict[str, object], response: Response) -> list[str]:
    """Every way this response differed from the expectation. Empty means PASS."""
    problems: list[str] = []

    wanted = expect.get("status")
    if wanted is not None:
        allowed = wanted if isinstance(wanted, list) else [wanted]
        if response.status not in allowed:
            problems.append(
                f"status {response.status}, expected {' or '.join(str(a) for a in allowed)}"
            )

    for needle in as_list(expect.get("body_contains")):
        if needle not in response.body:
            problems.append(f"body does not contain {needle!r}")
    for needle in as_list(expect.get("body_not_contains")):
        if needle in response.body:
            problems.append(f"body contains {needle!r}, which it must not")

    # A malformed expectation raises rather than being skipped. Silently ignoring
    # `"header_contains": ["content-type"]` leaves an assertion that never ran,
    # and a probe with one real expectation and one ignored one reports PASS. That
    # is the gate-that-never-ran-reads-as-green failure this skill exists to
    # refuse, one level down.
    header_expect = expect.get("header_contains")
    if header_expect is not None:
        if not isinstance(header_expect, dict):
            raise SpecError(
                f"header_contains must be an object of header name to expected "
                f"substring, not {type(header_expect).__name__}"
            )
        for key, needle in header_expect.items():
            actual = response.headers.get(str(key).lower())
            if actual is None:
                problems.append(f"no {key} header")
            elif str(needle).lower() not in actual.lower():
                problems.append(f"{key} is {actual!r}, expected to contain {needle!r}")

    body_json = expect.get("body_json")
    if body_json is not None:
        if not isinstance(body_json, bool):
            raise SpecError(f"body_json must be true or false, not {body_json!r}")
        if body_json:
            try:
                json.loads(response.body)
            except json.JSONDecodeError as exc:
                problems.append(f"body is not JSON: {exc}")

    return problems


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


# --- the optional server ----------------------------------------------------


class Server:
    """The declared server, started in its own process group and always stopped.

    A context manager rather than a start and a stop call, because the stop has
    to survive an exception on any path between them. See the teardown note in
    the module docstring.
    """

    def __init__(self, config: dict[str, object], root: Path, base_url: str, timeout: int):
        command = config.get("start")
        if not isinstance(command, str) or not command.strip():
            raise SpecError("server.start must be a non-empty command string")
        self.command = command
        self.root = root
        self.health_url = base_url + str(config.get("health_path", "/"))
        ready = config.get("ready_status", [200, 204, 301, 302, 401, 404])
        self.ready_status = ready if isinstance(ready, list) else [ready]
        self.timeout = timeout
        self.process: subprocess.Popen[bytes] | None = None
        # mkstemp hands back an OPEN descriptor, and `[1]` alone dropped it on the
        # floor: one leaked fd per run. The path is what __enter__ reopens.
        handle, log_path = tempfile.mkstemp(prefix="probe-api-server-", suffix=".log")
        os.close(handle)
        self.log_path = Path(log_path)

    def __enter__(self) -> Server:
        # A FILE, not a pipe. Nothing here reads the server's output while the
        # probes run, and a chatty server fills a 64 KB pipe buffer and then
        # blocks on its next write, which reads as a hung gate. A file also means
        # the log survives to be quoted when the health probe never succeeds.
        try:
            self.handle = self.log_path.open("wb")
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                cwd=str(self.root),
                stdout=self.handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # its own group, so the kill reaches children
            )
        except OSError as exc:
            raise SpecError(f"could not start the server: {exc}") from exc
        try:
            self.wait_for_health()
        except SpecError:
            self.__exit__()
            raise
        return self

    def tail(self, lines: int = 5) -> str:
        """The end of the server's own output, which usually says why it failed."""
        try:
            text = self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        recent = [line for line in text.splitlines() if line.strip()][-lines:]
        return "\n  ".join(recent)

    def wait_for_health(self) -> None:
        deadline = time.monotonic() + self.timeout
        last = "no attempt completed"
        while time.monotonic() < deadline:
            if self.process and self.process.poll() is not None:
                raise SpecError(
                    f"the server exited with code {self.process.returncode} before "
                    f"becoming healthy; command was {self.command!r}\n  {self.tail()}"
                )
            probe = subprocess.run(
                [
                    "curl", "--silent", "--output", os.devnull,
                    "--max-time", "3",
                    "--write-out", "%{http_code}",
                    self.health_url,
                ],
                capture_output=True,
                text=True,
            )
            code = probe.stdout.strip()
            if code.isdigit() and int(code) in self.ready_status:
                return
            last = f"health probe of {self.health_url} returned {code or 'nothing'}"
            time.sleep(0.5)
        raise SpecError(
            f"the server did not become healthy within {self.timeout}s: {last}. "
            f"Expected one of {self.ready_status} from server.health_path\n  {self.tail()}"
        )

    def __exit__(self, *_: object) -> None:
        """Stop the server on every path out. See the teardown note up top."""
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait(timeout=5)
                except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
                    pass
            except (ProcessLookupError, PermissionError):
                pass
        handle = getattr(self, "handle", None)
        if handle:
            handle.close()
        print(f"server log: {self.log_path}", file=sys.stderr)


# --- the run ----------------------------------------------------------------


def run_probes(spec: dict[str, object], base_url: str, timeout: int) -> list[Result]:
    insecure = bool(spec.get("insecure_tls"))
    captured: dict[str, str] = {}
    results: list[Result] = []
    probes = spec["probes"]
    assert isinstance(probes, list)

    for entry in probes:
        if not isinstance(entry, dict):
            raise SpecError("every probe must be a JSON object")
        name = str(entry.get("name") or entry.get("path") or "unnamed probe")
        try:
            request = build_request(entry, base_url, captured)
        except ProbeBlocked as exc:
            results.append(Result(name, "-", "BLOCKED", str(exc)))
            continue
        command = printable_command(request, timeout, insecure)

        if request.literal_secrets:
            print(
                "WARNING: probe {} sets {} to a literal value; use ${{VAR}} so the "
                "report can print a runnable command".format(
                    name, ", ".join(request.literal_secrets)
                ),
                file=sys.stderr,
            )

        try:
            response = send(request, timeout, insecure)
        except ProbeBlocked as exc:
            results.append(Result(name, command, "BLOCKED", str(exc)))
            continue

        expect = entry.get("expect") or {}
        if not isinstance(expect, dict):
            raise SpecError(f"{name}: expect must be an object")
        problems = grade(expect, response)

        capture_spec = entry.get("capture") or {}
        if isinstance(capture_spec, dict) and capture_spec:
            try:
                payload = json.loads(response.body)
            except json.JSONDecodeError:
                results.append(
                    Result(
                        name,
                        command,
                        "BLOCKED",
                        f"status {response.status}, but the body is not JSON so "
                        f"capture {sorted(capture_spec)} cannot be read",
                    )
                )
                continue
            try:
                for key, dotted in capture_spec.items():
                    captured[str(key)] = dig(payload, str(dotted))
            except ProbeBlocked as exc:
                results.append(Result(name, command, "BLOCKED", f"status {response.status}, {exc}"))
                continue

        if problems:
            results.append(Result(name, command, "FAIL", "; ".join(problems)))
        else:
            results.append(Result(name, command, "PASS", f"status {response.status}"))

    return results


def report(results: list[Result], base_url: str) -> int:
    for result in results:
        print(f"{result.status:<8} {result.name}")
        print(f"         {result.command}")
        print(f"         {result.detail}")
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    blocked = sum(1 for r in results if r.status == "BLOCKED")
    # The base URL rides the summary line, on stdout, because stdout is what the
    # skill copies into its report. A stderr-only warning about a remote host is
    # one a report can omit without looking incomplete.
    where = f"{base_url} (NOT this machine)" if addresses_another_machine(base_url) else base_url
    print(f"\n{len(results)} probes against {where}: {passed} passed, {failed} failed, {blocked} blocked")
    if blocked:
        # BLOCKED outranks FAIL for the exit status, because "the gate could not
        # run as specified" is the more urgent fact and both fail the run anyway.
        return EXIT_BLOCKED
    return EXIT_EXPECTATION_FAILED if failed else EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", required=True, metavar="FILE", help="Probe spec, JSON")
    parser.add_argument("--repo-root", default=".", help="Directory to start the server in")
    parser.add_argument(
        "--base-url",
        metavar="URL",
        help=(
            "Probe this URL instead of the spec's base_url. "
            f"With neither, {DEFAULT_BASE_URL}. A host that is not this machine is "
            "used as given and warned about."
        ),
    )
    parser.add_argument(
        "--timeout", type=int, default=10, metavar="SECONDS", help="Per-request timeout"
    )
    parser.add_argument(
        "--health-timeout",
        type=int,
        default=60,
        metavar="SECONDS",
        help="How long to wait for a declared server to answer its health path",
    )
    args = parser.parse_args()

    if not shutil.which("curl"):
        print("ERROR: curl is not on PATH, so this gate cannot run", file=sys.stderr)
        return EXIT_BLOCKED

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return EXIT_BLOCKED

    try:
        spec = load_spec(Path(args.spec))
        # The command line beats the spec, so one spec can be pointed somewhere
        # else without editing it.
        supplied = args.base_url or spec.get("base_url")
        if supplied is not None and not isinstance(supplied, str):
            raise SpecError("base_url must be a string")
        base_url, warnings = resolve_base_url(
            expand_env(supplied, "base_url") if supplied else None
        )
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)

        server_config = spec.get("server")
        if server_config:
            if not isinstance(server_config, dict):
                raise SpecError("server must be an object")
            if addresses_another_machine(base_url):
                # Tested on the URL, not on `warnings`: 0.0.0.0 also warns, and it
                # reaches the local server where it works at all, so this message
                # would have been false for it.
                #
                # Starting a local server and then probing somewhere else is a
                # spec bug that reads as a working gate: the local server answers
                # nothing, and the remote one answers everything.
                print(
                    "WARNING: the spec starts a local server but base_url is not "
                    "this machine, so the probes will not reach the server it "
                    "starts",
                    file=sys.stderr,
                )
            with Server(server_config, root, base_url, args.health_timeout):
                results = run_probes(spec, base_url, args.timeout)
        else:
            results = run_probes(spec, base_url, args.timeout)
    except SpecError as exc:
        # Exit 2, never 1. Every failure here means no verdict was reached about
        # any endpoint, and exit 1 would report one.
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_BLOCKED

    return report(results, base_url)


if __name__ == "__main__":
    sys.exit(main())
