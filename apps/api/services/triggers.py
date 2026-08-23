"""Autonomous trigger detection — the pure half of the fleet watch (services/autonomy.py is
the impure half that actually invokes an agent).

The fleet was query-driven until this module existed: every agent action began with a human
typing a question, which made "agent-monitored hospital operations" true only in the sense
that an agent would answer if asked. These functions turn a state snapshot plus the previous
snapshot into a list of things the fleet should act on *without being asked*.

Everything here is edge-triggered, never level-triggered. A SKU that is still low today
because it was low yesterday is not a new event, and firing on it every tick would mean the
sim clock spending a demo emailing the manager about the same box of gloves 21 times. A
trigger fires only on a transition into a worse state — and `next_watch_state` produces the
snapshot the next tick compares against.

Pure functions over plain dicts: no Firestore, no ADK, no clock. Fully unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TriggerKind = Literal["stock_breach", "fatigue_breach"]

# Severity ordering for stock status, so "was low, is now critical" reads as an escalation
# while "was critical, is now low" does not re-fire.
_STOCK_SEVERITY = {"ok": 0, "low": 1, "critical": 2}


@dataclass(frozen=True)
class Trigger:
    """One thing the fleet noticed on its own and should act on.

    Eight fields rather than the default limit of seven: `prompt` and `memory_fact` are
    pre-rendered here rather than assembled at the call site, so everything a trigger *means*
    lives in one pure, testable place and services/autonomy.py never composes agent-facing
    text of its own.
    """

    # pylint: disable=too-many-instance-attributes

    kind: TriggerKind
    subject: str  # the SKU or unit this is about
    agent: str  # which specialist should handle it
    severity: str
    summary: str  # human-readable, shown in the dashboard's autonomous feed
    prompt: str  # what the watcher actually asks the agent
    memory_fact: str  # what gets written to Memory Bank for later recall
    context: dict = field(default_factory=dict)

    @property
    def dedupe_key(self) -> str:
        return f"{self.kind}:{self.subject}"


def detect_stock_triggers(
    par_records: list[dict], previous_status: dict[str, str], sim_day: int
) -> list[Trigger]:
    """Fires when a SKU crosses *into* a worse stock status than it held at the last tick.

    A SKU with no previous status recorded is treated as newly observed: it fires only if it
    is already low or critical, so a fleet started mid-surge still notices, but a fleet
    started at calm baseline stays quiet until something actually moves.
    """
    triggers: list[Trigger] = []
    for record in par_records:
        sku = record["sku"]
        status = record["stock_status"]
        if status == "ok":
            continue

        was = previous_status.get(sku, "ok")
        if _STOCK_SEVERITY[status] <= _STOCK_SEVERITY.get(was, 0):
            continue  # unchanged, or recovering — not a new event

        days_left = record.get("days_of_supply")
        runway = f"~{days_left} days of supply left" if days_left is not None else "runway unknown"
        urgency = "expedited" if status == "critical" else "standard"
        triggers.append(
            Trigger(
                kind="stock_breach",
                subject=sku,
                agent="supply_chain_resiliency_agent",
                severity=status,
                summary=(
                    f"{record['name']} ({sku}) crossed from {was} to {status} — {runway}. "
                    f"Supply Chain Resiliency was asked to decide an {urgency} reorder."
                ),
                prompt=(
                    f"Automated stock watch: {record['name']} (SKU {sku}) has just crossed "
                    f"from '{was}' to '{status}' stock status — current stock "
                    f"{record['current_stock']} against a reorder point of "
                    f"{record['reorder_point']}, {runway}. Decide whether this needs a reorder "
                    "and, if it does, act on it by contacting the right vendor for the right "
                    "quantity. Nobody is watching this conversation, so do not ask a follow-up "
                    "question — make the call and report what you did."
                ),
                memory_fact=(
                    f"sim_day {sim_day}: {record['name']} ({sku}) stock went {was} -> {status} "
                    f"at {record['current_stock']} units, {runway}."
                ),
                context={
                    "sku": sku,
                    "item_name": record["name"],
                    "previous_status": was,
                    "current_stock": record["current_stock"],
                    "days_of_supply": days_left,
                },
            )
        )
    return triggers


def detect_fatigue_triggers(
    unit_summary: dict[str, dict], previous_critical: dict[str, int], sim_day: int
) -> list[Trigger]:
    """Fires when a unit's count of critical-fatigue staff *increases* over the last tick.

    Deliberately keyed on the critical count rather than any individual's burndown ratio: an
    individual crossing the threshold is Shift's own recommendation to make when asked, while
    a unit accumulating critical staff is a staffing failure the fleet should escalate on its
    own initiative.
    """
    triggers: list[Trigger] = []
    for unit, counts in sorted(unit_summary.items()):
        critical = counts.get("critical", 0)
        was = previous_critical.get(unit, 0)
        if critical <= was:
            continue

        triggers.append(
            Trigger(
                kind="fatigue_breach",
                subject=unit,
                agent="shift_allocation_agent",
                severity="critical",
                summary=(
                    f"{unit} critical-fatigue staff rose from {was} to {critical}. "
                    "Shift Allocation was asked to find coverage."
                ),
                prompt=(
                    f"Automated fatigue watch: the {unit} unit's count of staff at critical "
                    f"fatigue risk has just risen from {was} to {critical}. Identify who is "
                    "over their safe weekly hours, find the best available coverage — check "
                    "this unit's history first to see whether this has been building — and "
                    "act on the single most urgent reallocation. Nobody is watching this "
                    "conversation, so do not ask a follow-up question; make the call and "
                    "report what you did."
                ),
                memory_fact=(
                    f"sim_day {sim_day}: {unit} critical-fatigue count rose {was} -> {critical}, "
                    "triggering an autonomous coverage check."
                ),
                context={"unit": unit, "previous_critical": was, "critical": critical},
            )
        )
    return triggers


def next_watch_state(par_records: list[dict], unit_summary: dict[str, dict], sim_day: int) -> dict:
    """The snapshot the next tick compares against. Stored as one Firestore document."""
    return {
        "sim_day": sim_day,
        "sku_status": {r["sku"]: r["stock_status"] for r in par_records},
        "unit_critical": {unit: counts.get("critical", 0) for unit, counts in unit_summary.items()},
    }


def detect_all(
    par_records: list[dict],
    unit_summary: dict[str, dict],
    watch_state: dict | None,
    sim_day: int,
) -> tuple[list[Trigger], dict]:
    """Convenience entry point: everything the fleet should notice this tick, plus the state
    to persist for the next one."""
    state = watch_state or {}
    triggers = detect_stock_triggers(par_records, state.get("sku_status", {}), sim_day)
    triggers += detect_fatigue_triggers(unit_summary, state.get("unit_critical", {}), sim_day)
    return triggers, next_watch_state(par_records, unit_summary, sim_day)
