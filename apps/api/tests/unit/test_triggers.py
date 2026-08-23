"""Autonomous fleet-watch trigger detection. The behaviour that actually matters here is
edge- vs level-triggering: a watch that re-fires on unchanged state would spend a 21-day demo
emailing the manager about the same SKU every single day."""

from __future__ import annotations

import pytest

from services.triggers import (
    detect_all,
    detect_fatigue_triggers,
    detect_stock_triggers,
    next_watch_state,
)


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


class TestStockTriggers:
    def test_fires_on_transition_into_low(self):
        triggers = detect_stock_triggers([par("GLV-002", "low")], {"GLV-002": "ok"}, sim_day=4)
        assert len(triggers) == 1
        assert triggers[0].kind == "stock_breach"
        assert triggers[0].subject == "GLV-002"
        assert triggers[0].agent == "supply_chain_resiliency_agent"

    def test_does_not_refire_on_unchanged_status(self):
        assert detect_stock_triggers([par("GLV-002", "low")], {"GLV-002": "low"}, sim_day=5) == []

    def test_escalates_low_to_critical(self):
        triggers = detect_stock_triggers([par("GLV-002", "critical")], {"GLV-002": "low"}, 6)
        assert len(triggers) == 1
        assert triggers[0].severity == "critical"
        assert "expedited" in triggers[0].summary

    def test_does_not_fire_on_recovery(self):
        # critical -> low is an improvement; the fleet already acted on the way down.
        assert detect_stock_triggers([par("GLV-002", "low")], {"GLV-002": "critical"}, 7) == []

    def test_ok_status_never_fires(self):
        assert detect_stock_triggers([par("GLV-002", "ok")], {}, sim_day=1) == []

    def test_unseen_sku_already_breached_fires(self):
        # A fleet started mid-surge should still notice, even with no prior snapshot.
        triggers = detect_stock_triggers([par("NEW-001", "critical")], {}, sim_day=1)
        assert len(triggers) == 1

    def test_prompt_forbids_asking_a_follow_up(self):
        # Nobody is in the room to answer one, so a clarifying question is a dead turn.
        trigger = detect_stock_triggers([par("GLV-002", "low")], {}, sim_day=2)[0]
        assert "do not ask a follow-up question" in trigger.prompt

    def test_memory_fact_carries_the_day_and_transition(self):
        trigger = detect_stock_triggers([par("GLV-002", "critical")], {"GLV-002": "low"}, 9)[0]
        assert "sim_day 9" in trigger.memory_fact
        assert "low -> critical" in trigger.memory_fact

    def test_missing_days_of_supply_is_described_not_crashed(self):
        trigger = detect_stock_triggers([par("X", "low", days=None)], {}, sim_day=1)[0]
        assert "runway unknown" in trigger.prompt

    def test_dedupe_key_is_stable_per_subject(self):
        trigger = detect_stock_triggers([par("GLV-002", "low")], {}, sim_day=1)[0]
        assert trigger.dedupe_key == "stock_breach:GLV-002"


class TestFatigueTriggers:
    def test_fires_when_critical_count_rises(self):
        triggers = detect_fatigue_triggers(summary(ICU={"critical": 3}), {"ICU": 1}, sim_day=8)
        assert len(triggers) == 1
        assert triggers[0].subject == "ICU"
        assert triggers[0].agent == "shift_allocation_agent"

    def test_does_not_fire_when_flat(self):
        assert detect_fatigue_triggers(summary(ICU={"critical": 3}), {"ICU": 3}, 9) == []

    def test_does_not_fire_when_improving(self):
        assert detect_fatigue_triggers(summary(ICU={"critical": 1}), {"ICU": 4}, 10) == []

    def test_first_observation_of_a_nonzero_count_fires(self):
        triggers = detect_fatigue_triggers(summary(ER={"critical": 2}), {}, sim_day=1)
        assert len(triggers) == 1

    def test_zero_critical_never_fires(self):
        assert detect_fatigue_triggers(summary(ER={"critical": 0}), {}, sim_day=1) == []

    def test_units_are_processed_in_stable_order(self):
        triggers = detect_fatigue_triggers(
            summary(ICU={"critical": 1}, ER={"critical": 1}, GEN={"critical": 1}), {}, 3
        )
        assert [t.subject for t in triggers] == ["ER", "GEN", "ICU"]


class TestWatchState:
    def test_next_state_captures_every_sku_including_ok(self):
        # "ok" must be recorded, or a SKU recovering then re-breaching would look unchanged.
        state = next_watch_state([par("A", "ok"), par("B", "low")], summary(ICU={"critical": 2}), 5)
        assert state["sku_status"] == {"A": "ok", "B": "low"}
        assert state["unit_critical"] == {"ICU": 2}
        assert state["sim_day"] == 5

    def test_detect_all_returns_both_kinds_and_the_next_state(self):
        triggers, state = detect_all(
            [par("A", "critical")], summary(ICU={"critical": 2}), None, sim_day=6
        )
        assert {t.kind for t in triggers} == {"stock_breach", "fatigue_breach"}
        assert state["sim_day"] == 6

    def test_detect_all_with_no_prior_state_treats_everything_as_new(self):
        triggers, _ = detect_all([par("A", "low")], {}, None, sim_day=1)
        assert len(triggers) == 1

    def test_round_trip_is_quiet_on_the_second_tick(self):
        # The property the whole design rests on: feeding a tick's own output back in as the
        # previous state must produce no triggers at all.
        records = [par("A", "critical"), par("B", "low")]
        units = summary(ICU={"critical": 2})
        _, state = detect_all(records, units, None, sim_day=1)
        triggers, _ = detect_all(records, units, state, sim_day=2)
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
    triggers = detect_stock_triggers([par("S", now)], {"S": was}, sim_day=1)
    assert bool(triggers) is should_fire
