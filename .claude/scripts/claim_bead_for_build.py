#!/usr/bin/env python3
"""Decide whether /build may claim a bead, and carry out that decision.

Also list the bead ids a skill invocation might be acting on, for the label
script to probe (the `candidates` subcommand, at the foot of this docstring).

label_bead_on_skill_invocation.sh calls this once per /build, with the hook
payload on stdin:

    python3 claim_bead_for_build.py claim <bead-id> <status> <assignee> [<issue-type>]

<status>, <assignee> and <issue-type> come from the `bd show` the hook already
made while resolving the bead, so the decision itself costs no tracker call. A
label script older than the container refusal passes no <issue-type>, and its
bead is then treated as a leaf, as it always was. Stdout is one
JSON object, {"outcome": <text for the log>, "hook_output": <hook JSON or null>},
and the exit status is the one the bash claim_bead always returned:

    0  this session holds the bead, or its status was left alone
    1  bd failed, so the skill runs without a claim
    2  /build must not run: another holder has the bead, or it is a container

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

WHY A CONTAINER IS REFUSED HERE. An epic or a milestone groups other beads and
holds no work of its own. The hook claims before the feature-development skill
reads the bead, so a guard in the skill alone runs after the container's status
and assignee have already changed. The refusal needs no session, so it holds
for every payload.

THE CANDIDATES SUBCOMMAND. The label script calls this once per labeled skill,
with the skill arguments and any pull request text on stdin:

    python3 claim_bead_for_build.py candidates <branch> <prefixes>

<prefixes> is the `a|b|c` alternation of the id prefixes the repository uses,
and an empty one disables the prefix filter. Stdout is one candidate per line,
most likely first, and the exit status is 0. The candidate functions are pure:
they run no tracker and no git command and read no file, so the label script
stays the only prober and bd still decides which candidate is a bead.

Stdlib only, and Python 3.9, since /usr/bin/python3 is what a consumer
repository is guaranteed to have.
"""

from __future__ import annotations

import enum
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

EXIT_HELD = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2

# bd's exit status for a failed --if-assignee precondition: another session
# adopted the claim between the read and the write.
BD_PRECONDITION_MISMATCH = 13

# The shell's own status for a program it cannot find.
EXIT_COMMAND_NOT_FOUND = 127

# The bd issue types that group other beads and hold no work of their own.
CONTAINER_TYPES = frozenset({"epic", "milestone"})

# Eight characters tell concurrent sessions apart and keep `bd show` readable.
SESSION_PART_LENGTH = 8

# The session part lands in the tracker as an assignee, so anything but
# letters, digits and hyphens is dropped.
UNSAFE_SESSION_CHARACTERS = re.compile(r"[^A-Za-z0-9-]")

# How many candidates the label script may probe. Each one is a `bd show`
# subprocess on the critical path of every skill start, and the token pattern
# offers far more than any branch really carries. Twelve sits well above the
# real branches measured and still bounds the cost of a prose-heavy PR body.
#
# The cap falls on the SHORTEST candidates, since the list is longest-first. A
# branch of more than twelve hyphen segments therefore spends the budget on
# prefixes longer than the id and resolves nothing, which is the same answer it
# gave before prefixes were offered at all.
MAX_BEAD_PROBES = 12

# A candidate with no hyphen that is longer than this is not a bead id. Every
# bare id in this ecosystem is of the `e12` / `9ma` / `zkc.5` shape, and the
# length bound plus a required digit is what stops the token pattern from
# offering every lowercase word in a prompt.
MAX_BARE_ID_LENGTH = 6

# A maximal run: the hyphen is optional and a leading digit is allowed, so the
# hyphen-free short ids outrigger puts in a branch (zkc.5, e12, 9ma) are offered
# at all. Shape cannot tell such an id from an ordinary word, which is why the
# filters below narrow the list and bd verifies what is left.
CANDIDATE_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[0-9]+)*")


class Decision(enum.Enum):
    CLAIM = "claim"
    ADOPT = "adopt"
    ALREADY_HELD = "already held"
    REFUSE = "refuse"
    LEAVE_ALONE = "leave alone"


@dataclass(frozen=True)
class Bead:
    """What `bd show` reported about the bead /build was asked to start."""

    id: str
    status: str
    assignee: str
    issue_type: str = ""

    @property
    def is_container(self) -> bool:
        return self.issue_type in CONTAINER_TYPES


@dataclass(frozen=True)
class Claimant:
    """Who is asking: the per-session actor, and the bare git user.name."""

    actor: str
    owner: str


@dataclass(frozen=True)
class ClaimResult:
    code: int
    outcome: str
    # What the person is told when the run is refused; empty for every other result.
    reason: str = ""

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
        actor_flags = ["--actor", actor] if actor else []
        return self._run(["update", bead_id, "--claim", *actor_flags]) == 0

    def adopt(self, bead_id: str, owner: str, actor: str) -> int:
        # --if-assignee makes the takeover a compare-and-set: of two sessions
        # adopting one claim, exactly one wins.
        return self._run(
            [
                "update",
                bead_id,
                "--if-assignee",
                owner,
                "--assignee",
                actor,
                "--status",
                "in_progress",
                "--actor",
                actor,
            ]
        )

    def assignee(self, bead_id: str) -> str:
        completed = run_command(["bd", "show", bead_id, "--json"])
        return bead_field(completed.stdout, "assignee") if completed else ""

    @staticmethod
    def _run(arguments: Sequence[str]) -> int:
        completed = run_command(["bd", *arguments])
        return completed.returncode if completed else EXIT_COMMAND_NOT_FOUND


def run_command(argv: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
    """Run one fixed command, or None when its program is missing.

    Every argument is either a literal or an id and a name this module read from
    the hook payload and `bd show`, and no shell is involved, so the call takes
    no untrusted command line. The program is resolved to a path first.
    """
    program = shutil.which(argv[0])
    if program is None:
        return None
    try:
        return subprocess.run(  # noqa: S603
            [program, *argv[1:]], capture_output=True, text=True, check=False
        )
    except OSError:
        return None


def run_claim(bead: Bead, claimant: Claimant, tracker) -> ClaimResult:
    if bead.is_container:
        return _refuse_container(bead)
    decision = decide_claim(bead.status, bead.assignee, claimant.actor, claimant.owner)
    if decision is Decision.ADOPT:
        return _adopt(bead.id, claimant, tracker)
    if decision is Decision.CLAIM:
        return _claim(bead.id, claimant.actor, tracker)
    return _without_writing(decision, bead, claimant.actor)


def _refuse_container(bead: Bead) -> ClaimResult:
    log(f"{bead.id} is of type {bead.issue_type}, a container; refusing /build")
    reason = (
        f"/build refused: {bead.id} is of type {bead.issue_type}, a container that "
        "groups other beads and holds no work of its own. Nothing was claimed or changed. "
        f"Run `bd list --parent {bead.id}` and build one of its children instead."
    )
    return ClaimResult(EXIT_REFUSED, f"REFUSED, type {bead.issue_type} is a container", reason)


def _refuse_holder(bead_id: str, detail: str) -> ClaimResult:
    reason = (
        f"/build refused: {bead_id} is already being worked ({detail}). Another session or "
        "outrigger may be building it right now. If that work is abandoned, release it with "
        f"`bd unclaim {bead_id} --force`, then run /build again."
    )
    return ClaimResult(EXIT_REFUSED, f"REFUSED, {detail}", reason)


def _without_writing(decision: Decision, bead: Bead, actor: str) -> ClaimResult:
    if decision is Decision.ALREADY_HELD:
        log(f"{bead.id} is already held by this session ({actor})")
        return ClaimResult(EXIT_HELD, "already held by this session")
    if decision is Decision.REFUSE:
        return _refuse_in_progress(bead)
    return _leave_alone(bead)


def _refuse_in_progress(bead: Bead) -> ClaimResult:
    holder = bead.assignee or "no assignee"
    log(f"{bead.id} is in_progress under {holder}; refusing /build")
    return _refuse_holder(bead.id, f"in_progress under {holder}")


def _leave_alone(bead: Bead) -> ClaimResult:
    status = bead.status or "of no readable status"
    log(f"{bead.id} is {status}, not open; leaving its status alone")
    return ClaimResult(EXIT_HELD, f"left status {bead.status or 'unreadable'} alone")


def _claim(bead_id: str, actor: str, tracker) -> ClaimResult:
    as_actor = f" as {actor}" if actor else ""
    if tracker.claim(bead_id, actor):
        log(f"claimed {bead_id}{as_actor}, now in_progress")
        return ClaimResult(EXIT_HELD, f"claimed in_progress{as_actor}")
    return _failed_claim(bead_id, actor, tracker)


def _failed_claim(bead_id: str, actor: str, tracker) -> ClaimResult:
    # A lost race and a broken bd both fail here. Only the first is a refusal,
    # and a fresh read tells them apart: a lost race leaves another assignee.
    holder = tracker.assignee(bead_id)
    if actor and holder and holder != actor:
        log(f"{bead_id} was claimed by {holder} first; refusing /build")
        return _refuse_holder(bead_id, f"claimed first by {holder}")
    log(f"bd update {bead_id} --claim failed")
    return ClaimResult(EXIT_FAILED, "FAILED to claim in_progress")


def _adopt(bead_id: str, claimant: Claimant, tracker) -> ClaimResult:
    owner, actor = claimant.owner, claimant.actor
    rc = tracker.adopt(bead_id, owner, actor)
    if rc == 0:
        log(f"adopted {bead_id} from {owner} as {actor}, now in_progress")
        return ClaimResult(EXIT_HELD, f"claimed in_progress as {actor}, adopted from {owner}")
    if rc == BD_PRECONDITION_MISMATCH:
        return _lost_adoption(bead_id, tracker)
    log(f"bd update {bead_id} --if-assignee failed")
    return ClaimResult(EXIT_FAILED, f"FAILED to adopt the claim under {owner}")


def _lost_adoption(bead_id: str, tracker) -> ClaimResult:
    holder = tracker.assignee(bead_id) or "another session"
    log(f"{bead_id} was adopted by {holder} first; refusing /build")
    return _refuse_holder(bead_id, f"claimed first by {holder}")


def refusal_output(event: str, reason: str) -> dict | None:
    """Stop /build before it starts, in the shape each event accepts.

    A UserPromptSubmit block discards the prompt and shows the reason to the
    person; a PreToolUse deny shows it to Claude instead of running the skill.
    Codex's runner discards this stdout, so there the refusal is the unmade
    claim plus the feature-development skill's own guard.
    """
    if event == "UserPromptSubmit":
        return {"decision": "block", "reason": reason}
    if event == "PreToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    return None


def announcement_output(event: str, bead_id: str, actor: str) -> dict | None:
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


def hook_output(event: str, bead_id: str, actor: str, result: ClaimResult) -> dict | None:
    if result.code == EXIT_REFUSED:
        return refusal_output(event, result.reason)
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
    completed = run_command(["git", "config", "user.name"])
    return completed.stdout.strip() if completed else ""


def read_payload(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def log(message: str) -> None:
    print(f"[bead-label] {message}", file=sys.stderr)


def main(argv: Sequence[str]) -> int:
    if len(argv) in (4, 5) and argv[0] == "claim":
        return claim_and_report(Bead(*argv[1:]), read_payload(sys.stdin.read()))
    if len(argv) == 3 and argv[0] == "candidates":
        return print_candidates(read_text(sys.stdin.buffer.read()), argv[1], argv[2])
    log(
        "usage: claim_bead_for_build.py claim <bead-id> <status> <assignee> [<issue-type>] "
        "(payload on stdin), or claim_bead_for_build.py candidates <branch> <prefixes> "
        "(text on stdin)"
    )
    return EXIT_FAILED


def claim_and_report(bead: Bead, payload: dict) -> int:
    claimant = claimant_for(payload)
    result = run_claim(bead, claimant, BdTracker())
    print(
        json.dumps(
            {"outcome": result.outcome, "hook_output": output_for(payload, bead, claimant, result)}
        )
    )
    return result.code


def claimant_for(payload: dict) -> Claimant:
    owner = git_user_name()
    actor = claim_actor(session_part(payload.get("session_id")), owner, os.environ.get("USER", ""))
    return Claimant(actor, owner)


def output_for(payload: dict, bead: Bead, claimant: Claimant, result: ClaimResult) -> dict | None:
    event = payload.get("hook_event_name")
    return hook_output(event if isinstance(event, str) else "", bead.id, claimant.actor, result)


def read_text(raw: bytes) -> str:
    # Decoded here rather than by sys.stdin, so a PR body with a stray byte
    # cannot fail the lookup under whatever locale the hook was started in.
    return raw.decode("utf-8", errors="replace")


def print_candidates(text: str, branch: str, prefix_alternation: str) -> int:
    prefixes = frozenset(filter(None, prefix_alternation.split("|")))
    lines = "".join(f"{candidate}\n" for candidate in bead_candidates(text, branch, prefixes))
    # Bytes, encoded the way argv was decoded, so the branch segment comes back
    # out exactly as it went in.
    sys.stdout.buffer.write(os.fsencode(lines))
    return EXIT_HELD


def bead_candidates(text: str, branch: str, prefixes: Collection[str]) -> list[str]:
    """The ids worth probing, most likely first, at most MAX_BEAD_PROBES.

    `text` is the skill arguments plus any pull request text. `prefixes` is the
    id prefixes this repository uses; an empty one disables the prefix filter.
    Nothing here is an authority: the list only narrows the search.
    """
    sources = f"{text}\n{branch.replace('/', ' ')}"
    ranked = most_specific_first(with_hyphen_prefixes(CANDIDATE_TOKEN.findall(sources)))
    plausible = (token for token in ranked if is_plausible_id(token, prefixes))
    # The positional segment is added after the filters and is exempt from both.
    # It is not a guess about shape: outrigger put the id in that position.
    return unique_nonblank([positional_segment(branch), *plausible])[:MAX_BEAD_PROBES]


def positional_segment(branch: str) -> str:
    """Segment two of outrigger/<short-id>/<slug>, verbatim, or ""."""
    segments = branch.split("/")
    return segments[1] if len(segments) >= 3 else ""


def with_hyphen_prefixes(tokens: Iterable[str]) -> list[str]:
    """Each token, followed by its own hyphen-separated prefixes.

    A branch named <bead-id>-<slug> arrives as one token, so without this
    tadw-b14-hook-resolution offers only itself and the tadw-b14 inside it is
    never probed. The single-segment prefix is offered too, and is_plausible_id
    is what keeps `tadw` out.

    A dotted child suffix sits in the last hyphen field and is never split off:
    hdw-3fe4.3 must not offer hdw-3fe4, which is a different bead.
    """
    offered = []
    for token in tokens:
        fields = token.split("-")
        offered.append(token)
        offered.extend("-".join(fields[:count]) for count in range(1, len(fields)))
    return offered


def most_specific_first(tokens: Iterable[str]) -> list[str]:
    """Id-shaped tokens ahead of bare words, and longest first within each.

    Longest first is what tries a whole slug id (tadw-qg-prepush-verdict-gate-tug)
    before any prefix of it, and that is the reason offering prefixes is safe:
    tadw-qg resolves to nothing. The two tiers are what keeps the pattern
    affordable: it matches every lowercase word, and a PR body of prose would
    otherwise spend the whole probe budget on words longer than the id.

    Equal lengths fall back to codepoint order, which is what `LC_ALL=C sort`
    gave. The shell left that tie to the locale; this is the deterministic choice.
    """
    return sorted(tokens, key=lambda token: (is_bare_word(token), -len(token), token))


def is_bare_word(token: str) -> bool:
    return "-" not in token and "." not in token


def is_plausible_id(token: str, prefixes: Collection[str]) -> bool:
    """Two cheap local filters, because every survivor costs a `bd show`.

    A hyphenated token must carry a prefix this repository uses, which is what
    removes `pre-commit` and `code-review`. A token with no hyphen carries no
    prefix at all, so it must instead be short and hold a digit, which every
    real one does and no English word does.
    """
    prefix, hyphen, _ = token.partition("-")
    if not hyphen:
        return len(token) <= MAX_BARE_ID_LENGTH and any(c in "0123456789" for c in token)
    return not prefixes or prefix in prefixes


def unique_nonblank(candidates: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(candidate for candidate in candidates if candidate.strip()))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
