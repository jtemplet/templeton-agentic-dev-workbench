#!/usr/bin/env python3
"""Decide whether /build may claim a bead, and carry out that decision.

label_bead_on_skill_invocation.sh calls this once per /build, with the hook
payload on stdin:

    python3 label_bead_hook.py claim <bead-id> <status> <assignee>

<status> and <assignee> come from the `bd show` the hook already made while
resolving the bead, so the decision itself costs no tracker call. Stdout is one
JSON object, {"outcome": <text for the log>, "hook_output": <hook JSON or null>},
and the exit status is the one the bash claim_bead always returned:

    0  this session holds the bead, or its status was left alone
    1  bd failed, so the skill runs without a claim
    2  another holder means /build must not run

Usage errors exit 1, never 2, so a broken call can never refuse a build.

WHY THE CLAIM IS PER SESSION. Every session used to claim as git user.name, so
a bead held by a second window read as "yours", and outrigger claims with no
assignee at all, which read as "nobody's". Both let /build start duplicate work
on 2026-09-28. So the claim is made under `<user.name> (session <id>)`, and an
in_progress bead is refused unless its assignee is this session's actor, an
empty assignee included.

A payload with no session_id keeps the old behavior: bd claims as git user.name
and no in_progress bead is refused, since one session cannot be told from
another.

Stdlib only, and Python 3.9, since /usr/bin/python3 is what a consumer
repository is guaranteed to have.
"""

from __future__ import annotations

import enum
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Sequence

EXIT_HELD = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2

# bd's exit status for a failed --if-assignee precondition: another session
# adopted the claim between the read and the write.
BD_PRECONDITION_MISMATCH = 13

# Eight characters tell concurrent sessions apart and keep `bd show` readable.
SESSION_PART_LENGTH = 8

# The session part lands in the tracker as an assignee, so anything but
# letters, digits and hyphens is dropped.
UNSAFE_SESSION_CHARACTERS = re.compile(r"[^A-Za-z0-9-]")


class Decision(enum.Enum):
    CLAIM = "claim"
    ADOPT = "adopt"
    ALREADY_HELD = "already held"
    REFUSE = "refuse"
    LEAVE_ALONE = "leave alone"


@dataclass(frozen=True)
class ClaimResult:
    code: int
    outcome: str

    @property
    def holds_bead(self) -> bool:
        return self.outcome.startswith(("claimed", "already held"))


def decide_claim(status: str, assignee: str, actor: str, owner: str) -> Decision:
    """Pick what /build does with a bead, from its status and assignee.

    `owner` is the bare git user.name. `bd update <id> --claim`, the start
    /triage-beads prints, records exactly that, so it is the person's own claim
    and this session adopts it rather than refusing it.
    """
    if actor and assignee and assignee == owner and status in ("open", "in_progress"):
        return Decision.ADOPT
    if status == "in_progress" and actor:
        return Decision.ALREADY_HELD if assignee == actor else Decision.REFUSE
    # A closed bead must not silently reopen because someone ran /build to
    # re-read a spec.
    if status != "open":
        return Decision.LEAVE_ALONE
    return Decision.CLAIM


def session_part(session_id: object) -> str:
    if isinstance(session_id, bool) or not isinstance(session_id, (str, int)):
        return ""
    return UNSAFE_SESSION_CHARACTERS.sub("", str(session_id))[:SESSION_PART_LENGTH]


def claim_actor(session: str, owner: str, user: str) -> str:
    """The per-session actor, or "" when the payload carried no session_id.

    The user name stays in front so a person reading `bd show` still sees whose
    machine holds the bead; the session suffix tells two windows apart.
    """
    if not session:
        return ""
    return f"{owner or user or 'agent'} (session {session})"


class BdTracker:
    """The two writes and one read the claim needs, through the bd CLI."""

    def claim(self, bead_id: str, actor: str) -> bool:
        # --claim is atomic, so of two sessions racing for one open bead exactly
        # one wins. It is idempotent when the claim is already this actor's, so
        # two events firing for one /build is safe.
        return self._run(["update", bead_id, "--claim", *(["--actor", actor] if actor else [])]) == 0

    def adopt(self, bead_id: str, owner: str, actor: str) -> int:
        # --if-assignee makes the takeover a compare-and-set: of two sessions
        # adopting one claim, exactly one wins.
        return self._run([
            "update", bead_id, "--if-assignee", owner, "--assignee", actor,
            "--status", "in_progress", "--actor", actor,
        ])

    def assignee(self, bead_id: str) -> str:
        try:
            completed = subprocess.run(
                ["bd", "show", bead_id, "--json"], capture_output=True, text=True, check=False
            )
        except OSError:
            return ""
        return bead_field(completed.stdout, "assignee")

    @staticmethod
    def _run(arguments: Sequence[str]) -> int:
        try:
            return subprocess.run(
                ["bd", *arguments], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
            ).returncode
        except OSError:
            return 127


def run_claim(bead_id: str, status: str, assignee: str, actor: str, owner: str, tracker) -> ClaimResult:
    decision = decide_claim(status, assignee, actor, owner)
    if decision is Decision.ADOPT:
        return _adopt(bead_id, owner, actor, tracker)
    if decision is Decision.ALREADY_HELD:
        log(f"{bead_id} is already held by this session ({actor})")
        return ClaimResult(EXIT_HELD, "already held by this session")
    if decision is Decision.REFUSE:
        log(f"{bead_id} is in_progress under {assignee or 'no assignee'}; refusing /build")
        return ClaimResult(EXIT_REFUSED, f"REFUSED, in_progress under {assignee or 'no assignee'}")
    if decision is Decision.LEAVE_ALONE:
        log(f"{bead_id} is {status or 'of no readable status'}, not open; leaving its status alone")
        return ClaimResult(EXIT_HELD, f"left status {status or 'unreadable'} alone")
    return _claim(bead_id, actor, tracker)


def _claim(bead_id: str, actor: str, tracker) -> ClaimResult:
    as_actor = f" as {actor}" if actor else ""
    if tracker.claim(bead_id, actor):
        log(f"claimed {bead_id}{as_actor}, now in_progress")
        return ClaimResult(EXIT_HELD, f"claimed in_progress{as_actor}")

    # A lost race and a broken bd both fail here. Only the first is a refusal,
    # and a fresh read tells them apart: a lost race leaves another assignee.
    holder = tracker.assignee(bead_id)
    if actor and holder and holder != actor:
        log(f"{bead_id} was claimed by {holder} first; refusing /build")
        return ClaimResult(EXIT_REFUSED, f"REFUSED, claimed first by {holder}")
    log(f"bd update {bead_id} --claim failed")
    return ClaimResult(EXIT_FAILED, "FAILED to claim in_progress")


def _adopt(bead_id: str, owner: str, actor: str, tracker) -> ClaimResult:
    rc = tracker.adopt(bead_id, owner, actor)
    if rc == 0:
        log(f"adopted {bead_id} from {owner} as {actor}, now in_progress")
        return ClaimResult(EXIT_HELD, f"claimed in_progress as {actor}, adopted from {owner}")
    if rc == BD_PRECONDITION_MISMATCH:
        holder = tracker.assignee(bead_id) or "another session"
        log(f"{bead_id} was adopted by {holder} first; refusing /build")
        return ClaimResult(EXIT_REFUSED, f"REFUSED, claimed first by {holder}")
    log(f"bd update {bead_id} --if-assignee failed")
    return ClaimResult(EXIT_FAILED, f"FAILED to adopt the claim under {owner}")


def refusal_output(event: str, bead_id: str, outcome: str) -> Optional[dict]:
    """Stop /build before it starts, in the shape each event accepts.

    A UserPromptSubmit block discards the prompt and shows the reason to the
    person; a PreToolUse deny shows it to Claude instead of running the skill.
    Codex's runner discards this stdout, so there the refusal is the unmade
    claim plus the feature-development skill's own guard.
    """
    detail = outcome[len("REFUSED, "):] if outcome.startswith("REFUSED, ") else outcome
    reason = (
        f"/build refused: {bead_id} is already being worked ({detail}). Another session or "
        "outrigger may be building it right now. If that work is abandoned, release it with "
        f"`bd unclaim {bead_id} --force`, then run /build again."
    )
    if event == "UserPromptSubmit":
        return {"decision": "block", "reason": reason}
    if event == "PreToolUse":
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
        }}
    return None


def announcement_output(event: str, bead_id: str, actor: str) -> Optional[dict]:
    """Tell the run which bead this session holds.

    The feature-development guard reads this line: without it, an in_progress
    bead is one the run must not assume is its own.
    """
    if not actor:
        return None
    context = (
        f'bead-claim: this session holds {bead_id} as "{actor}" (in_progress). '
        "The claim was made for this run, so building it duplicates no one."
    )
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}


def hook_output(event: str, bead_id: str, actor: str, result: ClaimResult) -> Optional[dict]:
    if result.code == EXIT_REFUSED:
        return refusal_output(event, bead_id, result.outcome)
    if result.holds_bead:
        return announcement_output(event, bead_id, actor)
    return None


def bead_field(show_json: str, field: str) -> str:
    try:
        parsed = json.loads(show_json)
    except ValueError:
        return ""
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    value = parsed.get(field) if isinstance(parsed, dict) else None
    return value if isinstance(value, str) else ""


def git_user_name() -> str:
    try:
        completed = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return completed.stdout.strip()


def read_payload(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def log(message: str) -> None:
    print(f"[bead-label] {message}", file=sys.stderr)


def main(argv: Sequence[str]) -> int:
    if len(argv) != 4 or argv[0] != "claim":
        log("usage: label_bead_hook.py claim <bead-id> <status> <assignee> (payload on stdin)")
        return EXIT_FAILED
    bead_id, status, assignee = argv[1:]
    payload = read_payload(sys.stdin.read())
    owner = git_user_name()
    actor = claim_actor(session_part(payload.get("session_id")), owner, os.environ.get("USER", ""))

    result = run_claim(bead_id, status, assignee, actor, owner, BdTracker())
    event = payload.get("hook_event_name")
    output = hook_output(event if isinstance(event, str) else "", bead_id, actor, result)
    print(json.dumps({"outcome": result.outcome, "hook_output": output}))
    return result.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
