"""Autonomous fleet-watch trigger detection. The behaviour that actually matters here is
edge- vs level-triggering: a watch that re-fires on unchanged state would spend a long-running
demo emailing the manager about the same SKU on every single check."""

from __future__ import annotations

import pytest

from services.triggers import (
    detect_all,
    detect_credential_triggers,
    detect_fatigue_triggers,
    detect_schedule_conflict_triggers,
    detect_stock_triggers,
    next_watch_state,
)

AS_OF = "2026-08-23"


def par(sku: str, status: str, *, name: str | None = None, days: float | None = 3.0) -> dict:
    return {
        "sku": sku,
        "name": name or f"Item {sku}",
        "stock_status": status,
        "current_stock": 10,
        "reorder_point": 20,
        "days_of_supply": days,
    }


def summary(**units: dict) -> dict:
    return units


def credential(
    staff_id: str, status: str, *, name: str | None = None, unit: str = "ICU", role: str = "Nurse"
) -> dict:
    return {
        "staff_id": staff_id,
        "name": name or f"Staff {staff_id}",
        "role": role,
        "unit": unit,
        "credential_status": status,
        "days_until_expiry": -3 if status == "expired" else 10,
    }


class TestStockTriggers:
    def test_fires_on_transition_into_low(self):
        triggers = detect_stock_triggers([par("GLV-002", "low")], {"GLV-002": "ok"}, AS_OF)
        assert len(triggers) == 1
        assert triggers[0].kind == "stock_breach"
        assert triggers[0].subject == "GLV-002"
        assert triggers[0].agent == "supply_chain_resiliency_agent"

    def test_does_not_refire_on_unchanged_status(self):
        assert detect_stock_triggers([par("GLV-002", "low")], {"GLV-002": "low"}, AS_OF) == []

    def test_escalates_low_to_critical(self):
        triggers = detect_stock_triggers([par("GLV-002", "critical")], {"GLV-002": "low"}, AS_OF)
        assert len(triggers) == 1
        assert triggers[0].severity == "critical"
        assert "expedited" in triggers[0].summary

    def test_does_not_fire_on_recovery(self):
        # critical -> low is an improvement; the fleet already acted on the way down.
        assert detect_stock_triggers([par("GLV-002", "low")], {"GLV-002": "critical"}, AS_OF) == []

    def test_ok_status_never_fires(self):
        assert detect_stock_triggers([par("GLV-002", "ok")], {}, AS_OF) == []

    def test_unseen_sku_already_breached_fires(self):
        # A fleet started mid-surge should still notice, even with no prior snapshot.
        triggers = detect_stock_triggers([par("NEW-001", "critical")], {}, AS_OF)
        assert len(triggers) == 1

    def test_prompt_forbids_asking_a_follow_up(self):
        # Nobody is in the room to answer one, so a clarifying question is a dead turn.
        trigger = detect_stock_triggers([par("GLV-002", "low")], {}, AS_OF)[0]
        assert "do not ask a follow-up question" in trigger.prompt

    def test_memory_fact_carries_the_timestamp_and_transition(self):
        trigger = detect_stock_triggers([par("GLV-002", "critical")], {"GLV-002": "low"}, AS_OF)[0]
        assert AS_OF in trigger.memory_fact
        assert "low -> critical" in trigger.memory_fact

    def test_missing_days_of_supply_is_described_not_crashed(self):
        trigger = detect_stock_triggers([par("X", "low", days=None)], {}, AS_OF)[0]
        assert "runway unknown" in trigger.prompt

    def test_dedupe_key_is_stable_per_subject(self):
        trigger = detect_stock_triggers([par("GLV-002", "low")], {}, AS_OF)[0]
        assert trigger.dedupe_key == "stock_breach:GLV-002"


class TestFatigueTriggers:
    def test_fires_when_critical_count_rises(self):
        triggers = detect_fatigue_triggers(summary(ICU={"critical": 3}), {"ICU": 1}, AS_OF)
        assert len(triggers) == 1
        assert triggers[0].subject == "ICU"
        assert triggers[0].agent == "shift_allocation_agent"

    def test_does_not_fire_when_flat(self):
        assert detect_fatigue_triggers(summary(ICU={"critical": 3}), {"ICU": 3}, AS_OF) == []

    def test_does_not_fire_when_improving(self):
        assert detect_fatigue_triggers(summary(ICU={"critical": 1}), {"ICU": 4}, AS_OF) == []

    def test_first_observation_of_a_nonzero_count_fires(self):
        triggers = detect_fatigue_triggers(summary(ER={"critical": 2}), {}, AS_OF)
        assert len(triggers) == 1

    def test_zero_critical_never_fires(self):
        assert detect_fatigue_triggers(summary(ER={"critical": 0}), {}, AS_OF) == []

    def test_units_are_processed_in_stable_order(self):
        triggers = detect_fatigue_triggers(
            summary(ICU={"critical": 1}, ER={"critical": 1}, GEN={"critical": 1}), {}, AS_OF
        )
        assert [t.subject for t in triggers] == ["ER", "GEN", "ICU"]


class TestCredentialTriggers:
    def test_fires_on_transition_into_expired(self):
        triggers = detect_credential_triggers([credential("hr-01", "expired")], set(), AS_OF)
        assert len(triggers) == 1
        assert triggers[0].kind == "credential_breach"
        assert triggers[0].subject == "hr-01"
        assert triggers[0].agent == "hr_agent"

    def test_does_not_refire_on_already_expired(self):
        triggers = detect_credential_triggers([credential("hr-01", "expired")], {"hr-01"}, AS_OF)
        assert triggers == []

    def test_valid_and_expiring_soon_never_fire(self):
        records = [credential("hr-01", "valid"), credential("hr-02", "expiring_soon")]
        assert detect_credential_triggers(records, set(), AS_OF) == []

    def test_prompt_forbids_asking_a_follow_up(self):
        trigger = detect_credential_triggers([credential("hr-01", "expired")], set(), AS_OF)[0]
        assert "do not ask a follow-up question" in trigger.prompt

    def test_dedupe_key_is_stable_per_subject(self):
        trigger = detect_credential_triggers([credential("hr-01", "expired")], set(), AS_OF)[0]
        assert trigger.dedupe_key == "credential_breach:hr-01"


def conflict(case_a="A", case_b="B", reason="both scheduled in OR-1"):
    return {"case_id_a": case_a, "case_id_b": case_b, "reason": reason}


class TestScheduleConflictTriggers:
    def test_fires_on_a_new_conflict(self):
        triggers = detect_schedule_conflict_triggers([conflict()], set(), AS_OF)
        assert len(triggers) == 1
        assert triggers[0].kind == "schedule_conflict"
        assert triggers[0].agent == "surgical_scheduling_agent"

    def test_does_not_refire_on_an_already_seen_conflict(self):
        triggers = detect_schedule_conflict_triggers([conflict()], {"A::B"}, AS_OF)
        assert triggers == []

    def test_key_is_order_independent_with_previous_state(self):
        # A::B and B::A must be treated as the same conflict regardless of which case a given
        # detect_conflicts() run happened to list first.
        triggers = detect_schedule_conflict_triggers(
            [conflict(case_a="B", case_b="A")], {"A::B"}, AS_OF
        )
        assert triggers == []

    def test_prompt_forbids_asking_a_follow_up(self):
        trigger = detect_schedule_conflict_triggers([conflict()], set(), AS_OF)[0]
        assert "do not ask a follow-up question" in trigger.prompt

    def test_no_patient_identity_anywhere_in_the_trigger(self):
        # conflicts carry only case_id/room/surgeon/time — asserting this the way
        # test_redaction.py asserts no staff name leaks onto the public payload.
        trigger = detect_schedule_conflict_triggers([conflict()], set(), AS_OF)[0]
        assert "patient" not in repr(trigger).lower()


class TestWatchState:
    def test_next_state_captures_every_sku_including_ok(self):
        # "ok" must be recorded, or a SKU recovering then re-breaching would look unchanged.
        state = next_watch_state(
            [par("A", "ok"), par("B", "low")], summary(ICU={"critical": 2}), []
        )
        assert state["sku_status"] == {"A": "ok", "B": "low"}
        assert state["unit_critical"] == {"ICU": 2}
        assert state["expired_staff"] == []

    def test_next_state_captures_expired_staff(self):
        state = next_watch_state(
            [], {}, [credential("hr-01", "expired"), credential("hr-02", "valid")]
        )
        assert state["expired_staff"] == ["hr-01"]

    def test_detect_all_returns_all_three_kinds_and_the_next_state(self):
        triggers, state = detect_all(
            [par("A", "critical")],
            summary(ICU={"critical": 2}),
            [credential("hr-01", "expired")],
            None,
            AS_OF,
        )
        assert {t.kind for t in triggers} == {"stock_breach", "fatigue_breach", "credential_breach"}
        assert state["expired_staff"] == ["hr-01"]
        assert state["conflict_keys"] == []  # additive axis, defaults to empty

    def test_detect_all_includes_schedule_conflicts_when_given(self):
        triggers, state = detect_all([], {}, [], None, AS_OF, conflicts=[conflict()])
        assert {t.kind for t in triggers} == {"schedule_conflict"}
        assert state["conflict_keys"] == ["A::B"]

    def test_detect_all_with_no_prior_state_treats_everything_as_new(self):
        triggers, _ = detect_all([par("A", "low")], {}, [], None, AS_OF)
        assert len(triggers) == 1

    def test_round_trip_is_quiet_on_the_second_check(self):
        # The property the whole design rests on: feeding a check's own output back in as the
        # previous state must produce no triggers at all.
        records = [par("A", "critical"), par("B", "low")]
        units = summary(ICU={"critical": 2})
        credentials = [credential("hr-01", "expired")]
        _, state = detect_all(records, units, credentials, None, AS_OF)
        triggers, _ = detect_all(records, units, credentials, state, AS_OF)
        assert triggers == []


@pytest.mark.parametrize(
    "was,now,should_fire",
    [
        ("ok", "low", True),
        ("ok", "critical", True),
        ("low", "critical", True),
        ("low", "low", False),
        ("critical", "critical", False),
        ("critical", "low", False),
    ],
)
def test_stock_severity_transition_matrix(was, now, should_fire):
    triggers = detect_stock_triggers([par("S", now)], {"S": was}, AS_OF)
    assert bool(triggers) is should_fire
