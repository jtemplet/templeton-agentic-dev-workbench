#!/usr/bin/env python3
"""Regression suite for claim_bead_for_build.py, the /build claim decision.

Stdlib only, and Python 3.9, like the module. Run with:
    python3 scripts/test_claim_bead_for_build.py

The decision is tested by calling decide_claim directly. run_claim gets a fake
tracker, so each bd outcome (a lost race, a broken bd, a lost adoption) is one
constructor argument rather than a stub script. Two cases run the module as the
hook does, with a stub bd on PATH, to pin the stdin and stdout contract.

bead_candidates is pure, so its cases pass every input and compare the whole
ordered list. The expected lists were captured from the shell pipeline the
function replaced, run under LC_ALL=C.

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
import claim_bead_for_build as hook  # noqa: E402
from claim_bead_for_build import Decision, decide_claim  # noqa: E402

MODULE = Path(__file__).resolve().parent / "claim_bead_for_build.py"
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
    return claim_of(hook.Bead("tadw-1", status, assignee), actor, tracker)


def claim_of(bead, actor: str = ACTOR, tracker: FakeTracker = None):
    return hook.run_claim(bead, hook.Claimant(actor, OWNER), tracker or FakeTracker())


def bead_of_type(issue_type: str, status: str = "open", assignee: str = ""):
    return hook.Bead("tadw-1", status, assignee, issue_type)


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


# --- containers ---------------------------------------------------------------

CONTAINER_TYPES = ("epic", "milestone")
LEAF_TYPES = ("task", "bug", "feature", "chore", "")


def case_container_is_refused_before_any_tracker_write():
    # Every status and assignee here would otherwise claim, adopt, or be left alone.
    for issue_type in CONTAINER_TYPES:
        for status, assignee in (("open", ""), ("open", OWNER), ("in_progress", ACTOR), ("closed", "")):
            tracker = FakeTracker()
            result = claim_of(bead_of_type(issue_type, status, assignee), tracker=tracker)
            assert_eq(
                (result.code, result.outcome, tracker.calls),
                (2, f"REFUSED, type {issue_type} is a container", []),
            )


def case_container_is_refused_without_a_session():
    for issue_type in CONTAINER_TYPES:
        tracker = FakeTracker()
        result = claim_of(bead_of_type(issue_type), actor="", tracker=tracker)
        assert_eq((result.code, tracker.calls), (2, []))


def case_refused_container_is_not_held():
    assert_eq(claim_of(bead_of_type("epic")).holds_bead, False)


def case_leaf_types_are_still_claimed():
    for issue_type in LEAF_TYPES:
        tracker = FakeTracker()
        result = claim_of(bead_of_type(issue_type), tracker=tracker)
        assert_eq((result.code, tracker.calls), (0, [("claim", "tadw-1", ACTOR)]))


def case_leaf_adoption_survives_a_named_type():
    tracker = FakeTracker()
    result = claim_of(bead_of_type("task", "in_progress", OWNER), tracker=tracker)
    assert_eq((result.code, tracker.calls), (0, [("adopt", "tadw-1", OWNER, ACTOR)]))


def case_container_diagnostic_names_the_type_and_the_next_command():
    for issue_type in CONTAINER_TYPES:
        refused = claim_of(bead_of_type(issue_type))
        blocked = hook.hook_output("UserPromptSubmit", "tadw-1", ACTOR, refused)
        assert_eq(blocked["decision"], "block")
        denied = hook.hook_output("PreToolUse", "tadw-1", ACTOR, refused)
        assert_eq(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        for reason in (blocked["reason"], denied["hookSpecificOutput"]["permissionDecisionReason"]):
            assert f"tadw-1 is of type {issue_type}, a container" in reason, reason
            assert "bd list --parent tadw-1" in reason, reason
            # Releasing a claim is the wrong advice: nothing holds a container.
            assert "bd unclaim" not in reason, reason


# --- hook output ----------------------------------------------------------------


def case_refusal_takes_each_events_shape():
    refused = claim("in_progress", OTHER)
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


def case_container_refusal_exits_2_and_runs_no_bd_command():
    for issue_type in CONTAINER_TYPES:
        for payload in ({"hook_event_name": "PreToolUse", "session_id": "aaaa1111"}, {"hook_event_name": "PreToolUse"}):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                completed = run_module(directory, json.dumps(payload), "claim", "tadw-1", "open", "", issue_type)
                assert_eq(completed.returncode, 2)
                assert_eq((directory / "bd.log").exists(), False)
                output = json.loads(completed.stdout)["hook_output"]
                assert_eq(output["hookSpecificOutput"]["permissionDecision"], "deny")


def case_leaf_type_argument_still_claims():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        payload = json.dumps({"hook_event_name": "PreToolUse", "session_id": "aaaa1111"})
        completed = run_module(directory, payload, "claim", "tadw-1", "open", "", "task")
        assert_eq(completed.returncode, 0)
        logged = (directory / "bd.log").read_text(encoding="utf-8")
        assert_eq(logged, f"update tadw-1 --claim --actor {ACTOR}\n")


def case_bad_usage_never_refuses():
    with tempfile.TemporaryDirectory() as tmp:
        completed = run_module(Path(tmp), "{}", "claim", "tadw-1")
        assert_eq(completed.returncode, 1)
        assert_eq(completed.stdout, "")


# --- bead candidates ------------------------------------------------------------

LONG_BRANCH = "tadw-b14-a1-b2-c3-d4-e5-f6-g7-h8-i9-j1-k2-l3-m4-n5"


def candidates(text: str = "", branch: str = "main", prefixes=("tadw",)) -> list:
    return hook.bead_candidates(text, branch, prefixes)


def case_outrigger_branch_offers_its_hyphen_free_short_id():
    assert_eq(candidates(branch="outrigger/zkc.5/some-slug"), ["zkc.5"])


def case_positional_segment_beats_a_longer_slug():
    assert_eq(
        candidates(branch="outrigger/e12/tadw-beta-two-and-then-some"),
        [
            "e12",
            "tadw-beta-two-and-then-some",
            "tadw-beta-two-and-then",
            "tadw-beta-two-and",
            "tadw-beta-two",
            "tadw-beta",
        ],
    )


def case_id_slug_branch_offers_the_id_inside_it():
    assert "tadw-b14" in candidates(branch="tadw-b14-hook-resolution-and-clean-tree")


def case_slug_id_is_tried_whole_before_its_own_prefix():
    assert_eq(
        candidates(branch="tadw-qg-prepush-verdict-gate-tug"),
        [
            "tadw-qg-prepush-verdict-gate-tug",
            "tadw-qg-prepush-verdict-gate",
            "tadw-qg-prepush-verdict",
            "tadw-qg-prepush",
            "tadw-qg",
        ],
    )


def case_dotted_child_does_not_offer_its_parent():
    assert_eq(candidates(branch="feature/hdw-3fe4.3", prefixes=("hdw",)), ["hdw-3fe4.3"])


def case_hyphenated_token_needs_a_known_prefix():
    assert_eq(candidates("run pre-commit and code-review on tadw-9ma"), ["tadw-9ma"])


def case_no_known_prefixes_disables_the_prefix_filter():
    assert_eq(
        candidates("run pre-commit and code-review on tadw-9ma", prefixes=()),
        ["code-review", "pre-commit", "tadw-9ma"],
    )


def case_bare_word_without_a_digit_is_dropped():
    assert_eq(candidates("needs human review"), [])


def case_bare_id_is_kept_up_to_the_length_bound():
    at_bound = "a1" + "b" * (hook.MAX_BARE_ID_LENGTH - 2)
    assert_eq(candidates(f"{at_bound} {at_bound}b"), [at_bound])


def case_dotted_id_without_a_hyphen_takes_the_bare_filter():
    # abcd.12 is seven characters, one past the bound, and the dot counts.
    assert_eq(candidates("zkc.5 abcd.12"), ["zkc.5"])


def case_positional_segment_is_exempt_from_the_bare_filter():
    assert_eq(candidates(branch="outrigger/averyverylongword/x"), ["averyverylongword"])


def case_positional_segment_is_exempt_from_the_prefix_filter():
    assert_eq(candidates(branch="outrigger/pre-commit/x"), ["pre-commit"])


def case_blank_positional_segment_is_skipped():
    assert_eq(candidates(branch="x//tadw-b1"), ["tadw-b1"])


def case_two_segment_branch_has_no_positional():
    assert_eq(candidates(branch="needs/tadw-alpha-one"), ["tadw-alpha-one", "tadw-alpha"])


def case_duplicates_collapse_to_the_first():
    assert_eq(candidates("tadw-a1 tadw-a1 e12 e12", branch="feature/tadw-a1"), ["tadw-a1", "e12"])


def case_list_is_capped_at_the_probe_budget():
    assert_eq(len(candidates(branch=LONG_BRANCH)), hook.MAX_BEAD_PROBES)


def case_cap_falls_on_the_shortest_candidates():
    # Fifteen survive the filters; the three shortest, tadw-b14 among them, are cut.
    assert_eq(candidates(branch=LONG_BRANCH)[-1], "tadw-b14-a1-b2-c3")


def case_id_named_in_the_arguments_is_offered():
    assert_eq(candidates("fix tadw-b14 today"), ["tadw-b14"])


def case_id_shaped_token_ranks_ahead_of_a_longer_bare_id():
    assert_eq(candidates("abc123 a-1", prefixes=("a",)), ["a-1", "abc123"])


def case_equal_lengths_are_ordered_by_codepoint():
    assert_eq(candidates("tadw-b2 tadw-a2 b12 a12"), ["tadw-a2", "tadw-b2", "a12", "b12"])


def case_nothing_to_offer_is_an_empty_list():
    assert_eq(candidates("just some prose here"), [])


def case_candidate_functions_run_no_command():
    def refuse(*_args, **_kwargs):
        raise AssertionError("a candidate function ran a command")

    real = (hook.run_command, subprocess.run)
    hook.run_command, subprocess.run = refuse, refuse
    try:
        candidates("see #12 and tadw-b14", branch="outrigger/e12/tadw-beta-two")
    finally:
        hook.run_command, subprocess.run = real


def run_candidates(directory: Path, text: str, *arguments: str) -> subprocess.CompletedProcess:
    return run_module(directory, text, "candidates", *arguments)


def case_candidates_subcommand_prints_one_per_line():
    with tempfile.TemporaryDirectory() as tmp:
        completed = run_candidates(Path(tmp), "fix e12 and tadw-b14", "outrigger/zkc.5/slug", "tadw|life")
        assert_eq((completed.returncode, completed.stdout), (0, "zkc.5\ntadw-b14\ne12\n"))


def case_candidates_subcommand_takes_an_empty_prefix_list():
    with tempfile.TemporaryDirectory() as tmp:
        completed = run_candidates(Path(tmp), "pre-commit", "main", "")
        assert_eq((completed.returncode, completed.stdout), (0, "pre-commit\n"))


def case_candidates_subcommand_prints_nothing_when_there_is_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        completed = run_candidates(Path(tmp), "", "main", "tadw")
        assert_eq((completed.returncode, completed.stdout), (0, ""))


def case_candidates_subcommand_runs_no_bd_command():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        run_candidates(directory, "tadw-b14", "outrigger/e12/slug", "tadw")
        assert_eq((directory / "bd.log").exists(), False)


def case_candidates_bad_usage_exits_1():
    with tempfile.TemporaryDirectory() as tmp:
        completed = run_candidates(Path(tmp), "tadw-b14", "main")
        assert_eq((completed.returncode, completed.stdout), (1, ""))


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
    ("an epic or milestone is refused before any tracker write", case_container_is_refused_before_any_tracker_write),
    ("an epic or milestone is refused without a session", case_container_is_refused_without_a_session),
    ("a refused container is not held", case_refused_container_is_not_held),
    ("every leaf type is still claimed", case_leaf_types_are_still_claimed),
    ("a leaf that names its type is still adopted", case_leaf_adoption_survives_a_named_type),
    ("the container diagnostic names the type and the next command", case_container_diagnostic_names_the_type_and_the_next_command),
    ("a refusal takes the shape each event accepts", case_refusal_takes_each_events_shape),
    ("a held bead is announced to the run", case_held_bead_is_announced),
    ("no actor means no announcement", case_no_actor_announces_nothing),
    ("bead_field reads bd show JSON", case_bead_field_reads_bd_show_json),
    ("a hostile session_id reaches bd sanitized", case_hostile_session_id_reaches_bd_sanitized),
    ("a refusal exits 2 with hook JSON on stdout", case_refusal_exits_2_with_hook_json),
    ("a container refusal exits 2 and runs no bd command", case_container_refusal_exits_2_and_runs_no_bd_command),
    ("a leaf type on the command line still claims", case_leaf_type_argument_still_claims),
    ("bad usage exits 1 and never refuses", case_bad_usage_never_refuses),
    ("an outrigger branch offers its hyphen-free short id", case_outrigger_branch_offers_its_hyphen_free_short_id),
    ("the positional segment beats a longer slug", case_positional_segment_beats_a_longer_slug),
    ("an id-slug branch offers the id inside it", case_id_slug_branch_offers_the_id_inside_it),
    ("a slug id is tried whole before its own prefix", case_slug_id_is_tried_whole_before_its_own_prefix),
    ("a dotted child does not offer its parent", case_dotted_child_does_not_offer_its_parent),
    ("a hyphenated token needs a known prefix", case_hyphenated_token_needs_a_known_prefix),
    ("no known prefixes disables the prefix filter", case_no_known_prefixes_disables_the_prefix_filter),
    ("a bare word without a digit is dropped", case_bare_word_without_a_digit_is_dropped),
    ("a bare id is kept up to MAX_BARE_ID_LENGTH and dropped past it", case_bare_id_is_kept_up_to_the_length_bound),
    ("a dotted id without a hyphen takes the bare filter", case_dotted_id_without_a_hyphen_takes_the_bare_filter),
    ("the positional segment is exempt from the bare filter", case_positional_segment_is_exempt_from_the_bare_filter),
    ("the positional segment is exempt from the prefix filter", case_positional_segment_is_exempt_from_the_prefix_filter),
    ("a blank positional segment is skipped", case_blank_positional_segment_is_skipped),
    ("a two-segment branch has no positional segment", case_two_segment_branch_has_no_positional),
    ("duplicate candidates collapse to the first", case_duplicates_collapse_to_the_first),
    ("the list is capped at MAX_BEAD_PROBES", case_list_is_capped_at_the_probe_budget),
    ("the cap falls on the shortest candidates", case_cap_falls_on_the_shortest_candidates),
    ("an id named in the arguments is offered", case_id_named_in_the_arguments_is_offered),
    ("an id-shaped token ranks ahead of a longer bare id", case_id_shaped_token_ranks_ahead_of_a_longer_bare_id),
    ("equal lengths are ordered by codepoint", case_equal_lengths_are_ordered_by_codepoint),
    ("nothing to offer is an empty list", case_nothing_to_offer_is_an_empty_list),
    ("the candidate functions run no command", case_candidate_functions_run_no_command),
    ("the candidates subcommand prints one candidate per line", case_candidates_subcommand_prints_one_per_line),
    ("the candidates subcommand takes an empty prefix list", case_candidates_subcommand_takes_an_empty_prefix_list),
    ("the candidates subcommand prints nothing when there is nothing", case_candidates_subcommand_prints_nothing_when_there_is_nothing),
    ("the candidates subcommand runs no bd command", case_candidates_subcommand_runs_no_bd_command),
    ("candidates bad usage exits 1", case_candidates_bad_usage_exits_1),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
