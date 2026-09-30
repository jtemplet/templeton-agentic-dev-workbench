#!/usr/bin/env python3
"""Regression suite for label_bead_hook.py, the /build claim decision.

Stdlib only, and Python 3.9, like the module. Run with:
    python3 scripts/test_label_bead_hook.py

The decision is tested by calling decide_claim directly. run_claim gets a fake
tracker, so each bd outcome (a lost race, a broken bd, a lost adoption) is one
constructor argument rather than a stub script. Two cases run the module as the
hook does, with a stub bd on PATH, to pin the stdin and stdout contract.

hooks/test-claude-scripts.sh still drives the whole bash hook end to end.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

sys.dont_write_bytecode = True
import label_bead_hook as hook  # noqa: E402
from label_bead_hook import Decision, decide_claim  # noqa: E402

MODULE = Path(__file__).resolve().parent / "label_bead_hook.py"
OWNER = "Hook Suite"
ACTOR = "Hook Suite (session aaaa1111)"
OTHER = "Hook Suite (session bbbb2222)"

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


def assert_eq(actual, expected) -> None:
    assert actual == expected, f"expected {expected!r}, saw {actual!r}"


class FakeTracker:
    def __init__(self, claim_ok: bool = True, adopt_rc: int = 0, holder: str = "") -> None:
        self.claim_ok = claim_ok
        self.adopt_rc = adopt_rc
        self.holder = holder
        self.calls: list = []

    def claim(self, bead_id: str, actor: str) -> bool:
        self.calls.append(("claim", bead_id, actor))
        return self.claim_ok

    def adopt(self, bead_id: str, owner: str, actor: str) -> int:
        self.calls.append(("adopt", bead_id, owner, actor))
        return self.adopt_rc

    def assignee(self, bead_id: str) -> str:
        return self.holder


def claim(status: str, assignee: str = "", actor: str = ACTOR, tracker: FakeTracker = None):
    return hook.run_claim("tadw-1", status, assignee, actor, OWNER, tracker or FakeTracker())


# --- decide_claim ------------------------------------------------------------


def case_open_unassigned_bead_is_claimed():
    assert_eq(decide_claim("open", "", ACTOR, OWNER), Decision.CLAIM)


def case_own_session_holds_its_bead():
    assert_eq(decide_claim("in_progress", ACTOR, ACTOR, OWNER), Decision.ALREADY_HELD)


def case_other_session_refuses():
    assert_eq(decide_claim("in_progress", OTHER, ACTOR, OWNER), Decision.REFUSE)


def case_unassigned_in_progress_refuses():
    # outrigger claims with no assignee at all.
    assert_eq(decide_claim("in_progress", "", ACTOR, OWNER), Decision.REFUSE)


def case_bare_owner_claim_is_adopted():
    for status in ("open", "in_progress"):
        assert_eq(decide_claim(status, OWNER, ACTOR, OWNER), Decision.ADOPT)


def case_closed_bead_is_left_alone():
    assert_eq(decide_claim("closed", "", ACTOR, OWNER), Decision.LEAVE_ALONE)
    assert_eq(decide_claim("closed", OWNER, ACTOR, OWNER), Decision.LEAVE_ALONE)


def case_no_session_refuses_nothing():
    assert_eq(decide_claim("in_progress", "Somebody Else", "", OWNER), Decision.LEAVE_ALONE)
    assert_eq(decide_claim("in_progress", OWNER, "", OWNER), Decision.LEAVE_ALONE)
    assert_eq(decide_claim("open", "", "", OWNER), Decision.CLAIM)


# --- the actor ----------------------------------------------------------------


def case_session_part_keeps_eight_safe_characters():
    assert_eq(hook.session_part("a b;$(rm -rf x)`id`|c-1234567"), "abrm-rfx")
    assert_eq(hook.session_part("aaaa1111-2222-3333"), "aaaa1111")


def case_session_part_rejects_non_text():
    for value in (None, True, {"x": 1}, ["a"]):
        assert_eq(hook.session_part(value), "")


def case_actor_falls_back_from_owner_to_user():
    assert_eq(hook.claim_actor("aaaa1111", OWNER, "jt"), ACTOR)
    assert_eq(hook.claim_actor("aaaa1111", "", "jt"), "jt (session aaaa1111)")
    assert_eq(hook.claim_actor("aaaa1111", "", ""), "agent (session aaaa1111)")
    assert_eq(hook.claim_actor("", OWNER, "jt"), "")


# --- run_claim ----------------------------------------------------------------


def case_claim_succeeds_under_the_actor():
    tracker = FakeTracker()
    result = claim("open", tracker=tracker)
    assert_eq((result.code, result.outcome), (0, f"claimed in_progress as {ACTOR}"))
    assert_eq(tracker.calls, [("claim", "tadw-1", ACTOR)])


def case_lost_claim_race_refuses():
    result = claim("open", tracker=FakeTracker(claim_ok=False, holder=OTHER))
    assert_eq((result.code, result.outcome), (2, f"REFUSED, claimed first by {OTHER}"))


def case_broken_bd_is_a_failure_not_a_refusal():
    result = claim("open", tracker=FakeTracker(claim_ok=False))
    assert_eq((result.code, result.outcome), (1, "FAILED to claim in_progress"))


def case_adoption_is_a_compare_and_set():
    tracker = FakeTracker()
    result = claim("in_progress", OWNER, tracker=tracker)
    assert_eq(result.code, 0)
    assert_eq(result.outcome, f"claimed in_progress as {ACTOR}, adopted from {OWNER}")
    assert_eq(tracker.calls, [("adopt", "tadw-1", OWNER, ACTOR)])


def case_lost_adoption_race_refuses():
    result = claim("in_progress", OWNER, tracker=FakeTracker(adopt_rc=13, holder=OTHER))
    assert_eq((result.code, result.outcome), (2, f"REFUSED, claimed first by {OTHER}"))


def case_failed_adoption_runs_without_a_claim():
    result = claim("open", OWNER, tracker=FakeTracker(adopt_rc=1))
    assert_eq((result.code, result.outcome), (1, f"FAILED to adopt the claim under {OWNER}"))


def case_refusal_writes_nothing():
    tracker = FakeTracker()
    result = claim("in_progress", OTHER, tracker=tracker)
    assert_eq((result.code, result.outcome), (2, f"REFUSED, in_progress under {OTHER}"))
    assert_eq(tracker.calls, [])


def case_left_alone_bead_is_not_held():
    result = claim("closed")
    assert_eq((result.code, result.outcome, result.holds_bead), (0, "left status closed alone", False))


# --- hook output ----------------------------------------------------------------


def case_refusal_takes_each_events_shape():
    refused = hook.ClaimResult(2, f"REFUSED, in_progress under {OTHER}")
    blocked = hook.hook_output("UserPromptSubmit", "tadw-1", ACTOR, refused)
    assert_eq(blocked["decision"], "block")
    assert "bd unclaim tadw-1 --force" in blocked["reason"], blocked["reason"]
    assert f"({'in_progress under ' + OTHER})" in blocked["reason"], blocked["reason"]
    denied = hook.hook_output("PreToolUse", "tadw-1", ACTOR, refused)
    assert_eq(denied["hookSpecificOutput"]["permissionDecision"], "deny")
    assert_eq(hook.hook_output("Stop", "tadw-1", ACTOR, refused), None)


def case_held_bead_is_announced():
    held = hook.ClaimResult(0, "already held by this session")
    output = hook.hook_output("PreToolUse", "tadw-1", ACTOR, held)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("bead-claim: this session holds tadw-1"), context


def case_no_actor_announces_nothing():
    held = hook.ClaimResult(0, "claimed in_progress")
    assert_eq(hook.hook_output("PreToolUse", "tadw-1", "", held), None)


def case_bead_field_reads_bd_show_json():
    assert_eq(hook.bead_field('[{"assignee": "x"}]', "assignee"), "x")
    assert_eq(hook.bead_field('[{"status": "open"}]', "assignee"), "")
    assert_eq(hook.bead_field("", "assignee"), "")
    assert_eq(hook.bead_field("[]", "assignee"), "")


# --- the command-line contract --------------------------------------------------


def run_module(directory: Path, payload: str, *arguments: str) -> subprocess.CompletedProcess:
    bindir = directory / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "bd"
    stub.write_text(f'#!/bin/sh\necho "$*" >> "{directory}/bd.log"\nexit 0\n', encoding="utf-8")
    stub.chmod(0o755)
    gitconfig = directory / "gitconfig"
    gitconfig.write_text(f"[user]\n\tname = {OWNER}\n", encoding="utf-8")
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}",
               GIT_CONFIG_GLOBAL=str(gitconfig), GIT_CONFIG_NOSYSTEM="1")
    return subprocess.run(
        [sys.executable, str(MODULE), *arguments],
        input=payload, capture_output=True, text=True, cwd=directory, env=env, check=False,
    )


def case_hostile_session_id_reaches_bd_sanitized():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        payload = json.dumps({"hook_event_name": "PreToolUse", "session_id": "a b;$(rm -rf x)`id`|c-1234567"})
        completed = run_module(directory, payload, "claim", "tadw-1", "open", "")
        assert_eq(completed.returncode, 0)
        logged = (directory / "bd.log").read_text(encoding="utf-8")
        assert_eq(logged, f"update tadw-1 --claim --actor {OWNER} (session abrm-rfx)\n")
        result = json.loads(completed.stdout)
        assert_eq(result["outcome"], f"claimed in_progress as {OWNER} (session abrm-rfx)")
        assert_eq(result["hook_output"]["hookSpecificOutput"]["hookEventName"], "PreToolUse")


def case_refusal_exits_2_with_hook_json():
    with tempfile.TemporaryDirectory() as tmp:
        payload = json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "aaaa1111"})
        completed = run_module(Path(tmp), payload, "claim", "tadw-1", "in_progress", OTHER)
        assert_eq(completed.returncode, 2)
        assert_eq(json.loads(completed.stdout)["hook_output"]["decision"], "block")


def case_bad_usage_never_refuses():
    with tempfile.TemporaryDirectory() as tmp:
        completed = run_module(Path(tmp), "{}", "claim", "tadw-1")
        assert_eq(completed.returncode, 1)
        assert_eq(completed.stdout, "")


for name, fn in [
    ("an open, unassigned bead is claimed", case_open_unassigned_bead_is_claimed),
    ("this session's own claim is already held", case_own_session_holds_its_bead),
    ("another session's claim refuses", case_other_session_refuses),
    ("an in_progress bead with no assignee refuses", case_unassigned_in_progress_refuses),
    ("the person's bare-name claim is adopted", case_bare_owner_claim_is_adopted),
    ("a closed bead is left alone", case_closed_bead_is_left_alone),
    ("without a session nothing is refused", case_no_session_refuses_nothing),
    ("the session part keeps at most 8 safe characters", case_session_part_keeps_eight_safe_characters),
    ("a session_id that is not text yields no session", case_session_part_rejects_non_text),
    ("the actor falls back from user.name to USER to agent", case_actor_falls_back_from_owner_to_user),
    ("a claim is made under the session's actor", case_claim_succeeds_under_the_actor),
    ("losing the claim race refuses", case_lost_claim_race_refuses),
    ("a broken bd fails without refusing", case_broken_bd_is_a_failure_not_a_refusal),
    ("adoption takes the claim over as a compare-and-set", case_adoption_is_a_compare_and_set),
    ("losing the adoption race refuses", case_lost_adoption_race_refuses),
    ("a failed adoption runs without a claim", case_failed_adoption_runs_without_a_claim),
    ("a refusal writes nothing to the tracker", case_refusal_writes_nothing),
    ("a bead left alone is not held", case_left_alone_bead_is_not_held),
    ("a refusal takes the shape each event accepts", case_refusal_takes_each_events_shape),
    ("a held bead is announced to the run", case_held_bead_is_announced),
    ("no actor means no announcement", case_no_actor_announces_nothing),
    ("bead_field reads bd show JSON", case_bead_field_reads_bd_show_json),
    ("a hostile session_id reaches bd sanitized", case_hostile_session_id_reaches_bd_sanitized),
    ("a refusal exits 2 with hook JSON on stdout", case_refusal_exits_2_with_hook_json),
    ("bad usage exits 1 and never refuses", case_bad_usage_never_refuses),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
