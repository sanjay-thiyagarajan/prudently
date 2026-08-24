"""Surgical schedule conflict detection: flags cases that double-book the same operating room
or the same surgeon at an overlapping time. Pure functions over plain dicts (matching the
Firestore document shape from packages/datagen/datagen/patients.py and services/state.py) — no
I/O, no ADK, no patient PII (only case_id/room/surgeon_id/time — see agent.py's docstring for
why decrypted patient identity never reaches this module), so this is cheap to unit-test
exhaustively, matching this project's agents/*/*.py pure-logic-module convention."""

from __future__ import annotations

from datetime import datetime


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    return _parse(a_start) < _parse(b_end) and _parse(b_start) < _parse(a_end)


def detect_conflicts(cases: list[dict]) -> list[dict]:
    """Returns one record per conflicting *pair* of cases, sorted by earliest start time.
    Only `status in {"scheduled", "confirmed"}` cases are considered — a case already
    `completed`/`cancelled` can't meaningfully conflict with anything."""
    active = [c for c in cases if c.get("status") in ("scheduled", "confirmed")]
    conflicts: list[dict] = []

    for i, case_a in enumerate(active):
        for case_b in active[i + 1 :]:
            if not _overlaps(
                case_a["scheduled_start"],
                case_a["scheduled_end"],
                case_b["scheduled_start"],
                case_b["scheduled_end"],
            ):
                continue

            same_room = case_a["operating_room"] == case_b["operating_room"]
            same_surgeon = case_a.get("surgeon_staff_id") is not None and case_a.get(
                "surgeon_staff_id"
            ) == case_b.get("surgeon_staff_id")
            if not (same_room or same_surgeon):
                continue

            reasons = []
            if same_room:
                reasons.append(f"both scheduled in {case_a['operating_room']}")
            if same_surgeon:
                reasons.append(f"both assigned to surgeon {case_a['surgeon_staff_id']}")

            conflicts.append(
                {
                    "case_id_a": case_a["case_id"],
                    "case_id_b": case_b["case_id"],
                    "reason": " and ".join(reasons),
                    "operating_room": case_a["operating_room"] if same_room else None,
                    "surgeon_staff_id": case_a["surgeon_staff_id"] if same_surgeon else None,
                    "scheduled_start": min(case_a["scheduled_start"], case_b["scheduled_start"]),
                }
            )

    conflicts.sort(key=lambda c: c["scheduled_start"])
    return conflicts


def conflict_dedupe_keys(conflicts: list[dict]) -> set[str]:
    """A stable, order-independent key per conflicting pair — used by services/triggers.py to
    compare this cycle's conflicts against the last-seen set (edge-triggered, same pattern as
    stock/fatigue/credential breaches: a conflict that was already flagged last cycle is not a
    new event)."""
    keys = set()
    for conflict in conflicts:
        pair = tuple(sorted((conflict["case_id_a"], conflict["case_id_b"])))
        keys.add(f"{pair[0]}::{pair[1]}")
    return keys
