"""Surgical schedule conflict detection — the behaviour that matters is the same class as
services/triggers.py's edge-triggering: a conflict already flagged must produce a stable key so
the fleet watch doesn't re-fire on it every cycle."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.surgical_scheduling.conflicts import conflict_dedupe_keys, detect_conflicts


def case(
    case_id,
    room="OR-1",
    surgeon="doc-01",
    start="2026-08-23T08:00:00",
    end="2026-08-23T09:30:00",
    status="scheduled",
):
    return {
        "case_id": case_id,
        "operating_room": room,
        "surgeon_staff_id": surgeon,
        "scheduled_start": start,
        "scheduled_end": end,
        "status": status,
    }


class TestRoomConflicts:
    def test_overlapping_same_room_conflicts(self):
        cases = [
            case("A", room="OR-1", surgeon="doc-01"),
            case("B", room="OR-1", surgeon="doc-02", start="2026-08-23T08:30:00"),
        ]
        conflicts = detect_conflicts(cases)
        assert len(conflicts) == 1
        assert {conflicts[0]["case_id_a"], conflicts[0]["case_id_b"]} == {"A", "B"}
        assert "OR-1" in conflicts[0]["reason"]

    def test_non_overlapping_same_room_does_not_conflict(self):
        cases = [
            case(
                "A",
                room="OR-1",
                surgeon="doc-01",
                start="2026-08-23T08:00:00",
                end="2026-08-23T09:00:00",
            ),
            case(
                "B",
                room="OR-1",
                surgeon="doc-02",
                start="2026-08-23T09:00:00",
                end="2026-08-23T10:00:00",
            ),
        ]
        assert detect_conflicts(cases) == []

    def test_different_room_same_time_does_not_conflict(self):
        cases = [
            case("A", room="OR-1", surgeon="doc-01"),
            case("B", room="OR-2", surgeon="doc-02", start="2026-08-23T08:30:00"),
        ]
        assert detect_conflicts(cases) == []


class TestSurgeonConflicts:
    def test_overlapping_same_surgeon_different_room_conflicts(self):
        cases = [
            case("A", room="OR-1", surgeon="doc-01"),
            case("B", room="OR-2", surgeon="doc-01", start="2026-08-23T08:30:00"),
        ]
        conflicts = detect_conflicts(cases)
        assert len(conflicts) == 1
        assert "doc-01" in conflicts[0]["reason"]

    def test_no_surgeon_assigned_never_conflicts_on_surgeon(self):
        cases = [
            case("A", room="OR-1", surgeon=None),
            case("B", room="OR-2", surgeon=None, start="2026-08-23T08:30:00"),
        ]
        assert detect_conflicts(cases) == []


class TestStatusFiltering:
    def test_completed_case_never_conflicts(self):
        cases = [
            case("A", room="OR-1", surgeon="doc-01", status="completed"),
            case("B", room="OR-1", surgeon="doc-02", start="2026-08-23T08:30:00"),
        ]
        assert detect_conflicts(cases) == []

    def test_cancelled_case_never_conflicts(self):
        cases = [
            case("A", room="OR-1", surgeon="doc-01", status="cancelled"),
            case("B", room="OR-1", surgeon="doc-02", start="2026-08-23T08:30:00"),
        ]
        assert detect_conflicts(cases) == []

    def test_confirmed_case_still_conflicts(self):
        cases = [
            case("A", room="OR-1", surgeon="doc-01", status="confirmed"),
            case("B", room="OR-1", surgeon="doc-02", start="2026-08-23T08:30:00"),
        ]
        assert len(detect_conflicts(cases)) == 1


class TestDedupeKeys:
    def test_key_is_order_independent(self):
        conflicts_ab = detect_conflicts(
            [case("A", room="OR-1"), case("B", room="OR-1", start="2026-08-23T08:30:00")]
        )
        conflicts_ba = detect_conflicts(
            [case("B", room="OR-1", start="2026-08-23T08:30:00"), case("A", room="OR-1")]
        )
        assert conflict_dedupe_keys(conflicts_ab) == conflict_dedupe_keys(conflicts_ba)

    def test_round_trip_is_quiet_on_the_second_check(self):
        # Same property as services/triggers.py's own edge-triggering test: feeding a check's
        # own output back in as "already seen" must not re-fire.
        cases = [case("A", room="OR-1"), case("B", room="OR-1", start="2026-08-23T08:30:00")]
        conflicts = detect_conflicts(cases)
        previous_keys = conflict_dedupe_keys(conflicts)
        # A "new" detection run against the identical schedule produces the identical key set —
        # the caller (services/triggers.py) is what actually skips already-seen keys.
        assert conflict_dedupe_keys(detect_conflicts(cases)) == previous_keys


class TestMultipleConflicts:
    def test_sorted_by_earliest_start_time(self):
        cases = [
            case(
                "late",
                room="OR-2",
                surgeon="doc-09",
                start="2026-08-23T14:00:00",
                end="2026-08-23T15:00:00",
            ),
            case(
                "late2",
                room="OR-2",
                surgeon="doc-10",
                start="2026-08-23T14:30:00",
                end="2026-08-23T15:30:00",
            ),
            case(
                "early",
                room="OR-1",
                surgeon="doc-01",
                start="2026-08-23T08:00:00",
                end="2026-08-23T09:00:00",
            ),
            case(
                "early2",
                room="OR-1",
                surgeon="doc-02",
                start="2026-08-23T08:30:00",
                end="2026-08-23T09:30:00",
            ),
        ]
        conflicts = detect_conflicts(cases)
        assert len(conflicts) == 2
        assert conflicts[0]["scheduled_start"] == "2026-08-23T08:00:00"
