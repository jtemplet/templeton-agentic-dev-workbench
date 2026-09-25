#!/usr/bin/env python3
"""Regression suite for select_bead.py.

Stdlib only, no install. Run with:
    python3 skills/ship/scripts/test_select_bead.py

Selection is tested in process against a lookup built from a dictionary, the
lightest fixture that proves the rules. `bd`'s output shapes are tested through
parse_show with the exact stdout and stderr a real `bd` printed, and one case
runs the command line against a shim `bd` on PATH.

RULE-TO-TEST MAPPING. A criterion with no test here is a criterion nothing holds.

  tadw-a7r criterion                               Pinned by
  ------------------------------------------------------------------------------
  1. Aliases of one canonical id are not ambiguous  case_aliases_of_one_bead_select_it
  2. Two distinct fallback ids stop                 case_two_distinct_beads_stop
  2. An invalid explicit id stops                   case_unknown_explicit_id_stops
  2. ... and never becomes bead-free                case_explicit_id_without_tracker_stops

  Design decisions in the module docstring
  ------------------------------------------------------------------------------
  An explicit id is the only lookup                 case_explicit_id_is_the_only_lookup
  No candidate resolves: bead-free                  case_no_candidate_ships_bead_free
  No tracker: bead-free                             case_no_tracker_ships_bead_free
  A failing tracker stops, never bead-free          case_failing_tracker_stops
  A closed bead stops                               case_closed_bead_stops
  bd's "not found" JSON means no bead               case_not_found_output_is_no_bead
  bd's missing database means no tracker            case_missing_database_is_no_tracker
  Unparsable output is a tracker failure            case_unparsable_output_is_a_failure
  A record missing a field is a tracker failure     case_record_missing_a_field_is_a_failure
  The command line prints the choice                case_command_line_prints_the_choice
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "select_bead.py"
spec = importlib.util.spec_from_file_location("select_bead", SCRIPT)
select_bead = importlib.util.module_from_spec(spec)
sys.modules["select_bead"] = select_bead
spec.loader.exec_module(select_bead)
ground_spec = importlib.util.spec_from_file_location(
    "resolve_ground", SCRIPT.parent / "resolve_ground.py"
)
resolve_ground = importlib.util.module_from_spec(ground_spec)
ground_spec.loader.exec_module(resolve_ground)

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


OPEN = select_bead.Bead("tadw-a7r", "Resolve bead selection", "feature", "open")
OTHER = select_bead.Bead("tadw-9ed", "Check the candidate", "feature", "open")
CLOSED = select_bead.Bead("tadw-8j8", "Build the runner", "feature", "closed")

# bd resolves a short id to its bead, so both spellings name one record.
TRACKER = {"tadw-a7r": OPEN, "a7r": OPEN, "tadw-9ed": OTHER, "tadw-8j8": CLOSED}

NOT_FOUND_STDOUT = (
    '{\n  "error": "no issues found matching the provided IDs",\n  "schema_version": 1\n}\n'
)
NO_DATABASE_STDERR = "Error: no beads database found\nHint: run 'bd where' to inspect\n"


class RecordingLookup:
    """A lookup over a dictionary that records every id it was asked for."""

    def __init__(self, beads: dict) -> None:
        self.beads = beads
        self.asked: list[str] = []

    def __call__(self, candidate: str):
        self.asked.append(candidate)
        return self.beads.get(candidate)


def raising(error: Exception):
    def lookup(candidate: str):
        raise error

    return lookup


def stop_reason(explicit, candidates, lookup) -> str | None:
    try:
        select_bead.select_bead(explicit, candidates, lookup)
    except select_bead.SelectionStopped as stopped:
        return stopped.reason
    return None


def completed(stdout: str = "", stderr: str = "", code: int = 1):
    return subprocess.CompletedProcess(["bd"], code, stdout=stdout, stderr=stderr)


def case_aliases_of_one_bead_select_it():
    selection = select_bead.select_bead(None, ["a7r", "tadw-a7r"], RecordingLookup(TRACKER))
    assert selection.bead == OPEN, selection


def case_two_distinct_beads_stop():
    reason = stop_reason(None, ["tadw-a7r", "tadw-9ed"], RecordingLookup(TRACKER))
    assert reason == "ambiguous", reason


def case_unknown_explicit_id_stops():
    reason = stop_reason("tadw-typo", ["tadw-a7r"], RecordingLookup(TRACKER))
    assert reason == "explicit-unresolved", reason


def case_explicit_id_without_tracker_stops():
    reason = stop_reason("tadw-a7r", [], raising(select_bead.TrackerMissing("no db")))
    assert reason == "explicit-unresolved", reason


def case_explicit_id_is_the_only_lookup():
    lookup = RecordingLookup(TRACKER)
    select_bead.select_bead("tadw-a7r", ["tadw-9ed"], lookup)
    assert lookup.asked == ["tadw-a7r"], lookup.asked


def case_no_candidate_ships_bead_free():
    selection = select_bead.select_bead(None, ["nothing"], RecordingLookup(TRACKER))
    assert selection.bead_free_reason == "no-candidate", selection


# tadw-7lxr: `bd show` resolves a partial id, so `bd show ios` returned
# hdw-ios-send-birth-year-wynj and a branch naming no bead closed it.
UNRELATED = select_bead.Bead("hdw-ios-send-birth-year-wynj", "Send birth year", "feature", "open")


def partial_match_lookup(beads: list) -> RecordingLookup:
    """Every substring of an id resolves to its bead, the way `bd show` resolves one."""
    tracker = {}
    for bead in beads:
        for start in range(len(bead.id)):
            for end in range(start + 1, len(bead.id) + 1):
                tracker.setdefault(bead.id[start:end], bead)
    return RecordingLookup(tracker)


def case_a_branch_word_inside_an_id_ships_bead_free():
    branch = "fix/ios/wrap-snapshot-stat-label"
    candidates = resolve_ground.bead_candidates(branch)
    selection = select_bead.select_bead(None, candidates, partial_match_lookup([UNRELATED]))
    assert selection.bead is None, f"{branch} selected {selection.bead}"


def case_a_full_id_on_the_branch_selects_its_bead():
    candidates = ["fix", "hdw-ios-send-birth-year-wynj"]
    selection = select_bead.select_bead(None, candidates, partial_match_lookup([UNRELATED]))
    assert selection.bead == UNRELATED, selection


def case_a_hash_alone_on_the_branch_selects_its_bead():
    selection = select_bead.select_bead(None, ["a7r"], partial_match_lookup([OPEN]))
    assert selection.bead == OPEN, selection


def case_a_prefix_of_a_hash_is_not_a_bead():
    awsr = select_bead.Bead("tadw-awsr", "Gate on the hooks", "bug", "open")
    selection = select_bead.select_bead(None, ["aws"], partial_match_lookup([awsr]))
    assert selection.bead is None, selection


def case_no_tracker_ships_bead_free():
    lookup = raising(select_bead.TrackerMissing("no db"))
    selection = select_bead.select_bead(None, ["tadw-a7r"], lookup)
    assert selection.bead_free_reason == "no-tracker", selection


def case_failing_tracker_stops():
    reason = stop_reason(None, ["tadw-a7r"], raising(select_bead.TrackerFailed("crashed")))
    assert reason == "tracker-failed", reason


def case_closed_bead_stops():
    reason = stop_reason(None, ["tadw-8j8"], RecordingLookup(TRACKER))
    assert reason == "already-closed", reason


def case_not_found_output_is_no_bead():
    bead = select_bead.parse_show("nope", completed(stdout=NOT_FOUND_STDOUT))
    assert bead is None, bead


def case_missing_database_is_no_tracker():
    try:
        select_bead.parse_show("tadw-a7r", completed(stderr=NO_DATABASE_STDERR))
    except select_bead.TrackerMissing:
        return
    raise AssertionError("a missing database was not reported as TrackerMissing")


def case_unparsable_output_is_a_failure():
    try:
        select_bead.parse_show("tadw-a7r", completed(stderr="panic: dolt"))
    except select_bead.TrackerFailed:
        return
    raise AssertionError("unparsable output was not reported as TrackerFailed")


def case_record_missing_a_field_is_a_failure():
    try:
        select_bead.parse_show("tadw-a7r", completed(stdout='[{"id": "tadw-a7r"}]', code=0))
    except select_bead.TrackerFailed:
        return
    raise AssertionError("a record missing a field was not reported as TrackerFailed")


def case_command_line_prints_the_choice():
    record = [{"id": "tadw-a7r", "title": "Resolve", "issue_type": "feature", "status": "open"}]
    with tempfile.TemporaryDirectory() as directory:
        shims = Path(directory)
        shim = shims / "bd"
        shim.write_text(f"#!/bin/sh\necho '{json.dumps(record)}'\n")
        shim.chmod(0o755)
        environment = {**os.environ, "PATH": f"{shims}{os.pathsep}{os.environ['PATH']}"}
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", directory, "a7r"],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
    assert json.loads(result.stdout)["bead"]["id"] == "tadw-a7r", result.stdout + result.stderr


for name, fn in [
    ("aliases of one canonical id select that bead", case_aliases_of_one_bead_select_it),
    ("two distinct beads from the branch stop the run", case_two_distinct_beads_stop),
    ("an unknown explicit id stops the run", case_unknown_explicit_id_stops),
    (
        "an explicit id with no tracker stops, never bead-free",
        case_explicit_id_without_tracker_stops,
    ),
    ("an explicit id is the only lookup made", case_explicit_id_is_the_only_lookup),
    ("a branch naming no bead ships bead-free", case_no_candidate_ships_bead_free),
    ("a branch word inside an id ships bead-free", case_a_branch_word_inside_an_id_ships_bead_free),
    ("a full id on the branch selects its bead", case_a_full_id_on_the_branch_selects_its_bead),
    (
        "a hash alone on the branch selects its bead",
        case_a_hash_alone_on_the_branch_selects_its_bead,
    ),
    ("a prefix of a hash is not a bead", case_a_prefix_of_a_hash_is_not_a_bead),
    ("no tracker at all ships bead-free", case_no_tracker_ships_bead_free),
    ("a tracker that fails stops the run", case_failing_tracker_stops),
    ("a closed bead stops the run", case_closed_bead_stops),
    ("bd's not-found JSON means no bead", case_not_found_output_is_no_bead),
    ("bd's missing database means no tracker", case_missing_database_is_no_tracker),
    ("unparsable bd output is a tracker failure", case_unparsable_output_is_a_failure),
    ("a bd record missing a field is a tracker failure", case_record_missing_a_field_is_a_failure),
    ("the command line prints the chosen bead", case_command_line_prints_the_choice),
]:
    check(name, fn)

print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
