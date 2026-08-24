"""Autonomous trigger detection — the pure half of the fleet watch (services/fleet_watch.py and
services/autonomy.py are the impure half that actually invokes an agent).

The fleet was query-driven until this module existed: every agent action began with a human
typing a question, which made "agent-monitored hospital operations" true only in the sense
that an agent would answer if asked. These functions turn a state snapshot plus the previous
snapshot into a list of things the fleet should act on *without being asked*.

Everything here is edge-triggered, never level-triggered. A SKU that is still low today
because it was low at the last check is not a new event, and firing on it every check would
mean the watch loop spending a long-running demo emailing the manager about the same box of
gloves on every cycle. A trigger fires only on a transition into a worse state — and
`next_watch_state` produces the snapshot the next check compares against.

Pure functions over plain dicts: no Firestore, no ADK, no clock. Fully unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TriggerKind = Literal["stock_breach", "fatigue_breach", "credential_breach", "schedule_conflict"]

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
    subject: str  # the SKU, unit, or staff_id this is about
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
    par_records: list[dict], previous_status: dict[str, str], as_of: str
) -> list[Trigger]:
    """Fires when a SKU crosses *into* a worse stock status than it held at the last check.

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
                    f"{as_of}: {record['name']} ({sku}) stock went {was} -> {status} "
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
    unit_summary: dict[str, dict], previous_critical: dict[str, int], as_of: str
) -> list[Trigger]:
    """Fires when a unit's count of critical-fatigue staff *increases* over the last check.

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
                    f"{as_of}: {unit} critical-fatigue count rose {was} -> {critical}, "
                    "triggering an autonomous coverage check."
                ),
                context={"unit": unit, "previous_critical": was, "critical": critical},
            )
        )
    return triggers


def detect_credential_triggers(
    credential_records: list[dict], previous_expired: set[str], as_of: str
) -> list[Trigger]:
    """Fires when a staff member's credential crosses *into* expired since the last check.

    Same edge-triggered shape as the other two: a staff member who was already expired last
    check is not a new event, or HR would be re-escalated about the same license every cycle.
    Targets HR's existing `notify_staff_credential_escalation` tool — this is the third
    autonomy axis (alongside stock and fatigue), closing the gap where HR was autonomy-capable
    (services/autonomy.py's _AGENT_MODULES) but had no trigger kind that ever reached it.
    """
    triggers: list[Trigger] = []
    for record in credential_records:
        if record["credential_status"] != "expired":
            continue
        staff_id = record["staff_id"]
        if staff_id in previous_expired:
            continue

        triggers.append(
            Trigger(
                kind="credential_breach",
                subject=staff_id,
                agent="hr_agent",
                severity="critical",
                summary=(
                    f"{record['name']} ({record['role']}, {record['unit']})'s credential "
                    "expired. HR was asked to escalate."
                ),
                prompt=(
                    f"Automated credential watch: {record['name']} ({record['role']}, "
                    f"{record['unit']})'s credential/license has just expired "
                    f"({record['days_until_expiry']} days past expiry). Escalate this to the "
                    "staff member and flag it for compliance follow-up. Nobody is watching "
                    "this conversation, so do not ask a follow-up question — make the call and "
                    "report what you did."
                ),
                memory_fact=(
                    f"{as_of}: {record['name']} ({staff_id})'s credential expired, "
                    "triggering an autonomous HR escalation."
                ),
                context={
                    "staff_id": staff_id,
                    "name": record["name"],
                    "role": record["role"],
                    "unit": record["unit"],
                },
            )
        )
    return triggers


def _conflict_key(conflict: dict) -> str:
    # Deliberately duplicated rather than importing agents/surgical_scheduling/conflicts.py's
    # near-identical conflict_dedupe_keys — same rationale as agents/supply/reorder.py's own
    # duplicated stock-status derivation: keeps this module agent-logic-free (it has never
    # imported an agents.* module, and a schedule-conflict trigger isn't worth being the first
    # exception) and avoids the adk-deploy per-folder staging fragility a cross-folder import
    # would risk if this module is ever staged independently.
    pair = tuple(sorted((conflict["case_id_a"], conflict["case_id_b"])))
    return f"{pair[0]}::{pair[1]}"


def detect_schedule_conflict_triggers(
    conflicts: list[dict], previous_conflict_keys: set[str], as_of: str
) -> list[Trigger]:
    """Fires when a surgical-schedule conflict (agents/surgical_scheduling/conflicts.py's
    `detect_conflicts`) is new since the last check — same edge-triggered shape as the other
    three: a conflict already flagged last cycle is not a new event, or the fleet would
    re-escalate the same OR double-booking on every check. `conflicts` carries no patient PII
    (case_id/room/surgeon_id/time only — see conflicts.py's own docstring), so this function
    never touches encrypted fields."""
    triggers: list[Trigger] = []
    for conflict in conflicts:
        key = _conflict_key(conflict)
        if key in previous_conflict_keys:
            continue

        triggers.append(
            Trigger(
                kind="schedule_conflict",
                subject=key,
                agent="surgical_scheduling_agent",
                severity="critical",
                summary=(
                    f"Cases {conflict['case_id_a']} and {conflict['case_id_b']} conflict — "
                    f"{conflict['reason']}. Surgical Scheduling was asked to recommend a fix."
                ),
                prompt=(
                    f"Automated schedule watch: cases {conflict['case_id_a']} and "
                    f"{conflict['case_id_b']} now conflict ({conflict['reason']}). Recommend "
                    "which case should be rescheduled and to what slot. Nobody is watching this "
                    "conversation, so do not ask a follow-up question — make the call and "
                    "report what you did."
                ),
                memory_fact=(
                    f"{as_of}: cases {conflict['case_id_a']} and {conflict['case_id_b']} "
                    f"conflicted ({conflict['reason']}), triggering an autonomous review."
                ),
                context={
                    "case_id_a": conflict["case_id_a"],
                    "case_id_b": conflict["case_id_b"],
                    "reason": conflict["reason"],
                },
            )
        )
    return triggers


def next_watch_state(
    par_records: list[dict],
    unit_summary: dict[str, dict],
    credential_records: list[dict],
    conflicts: list[dict] | None = None,
) -> dict:
    """The snapshot the next check compares against. Stored as one Firestore document."""
    return {
        "sku_status": {r["sku"]: r["stock_status"] for r in par_records},
        "unit_critical": {unit: counts.get("critical", 0) for unit, counts in unit_summary.items()},
        "expired_staff": sorted(
            r["staff_id"] for r in credential_records if r["credential_status"] == "expired"
        ),
        "conflict_keys": sorted({_conflict_key(c) for c in (conflicts or [])}),
    }


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def detect_all(
    par_records: list[dict],
    unit_summary: dict[str, dict],
    credential_records: list[dict],
    watch_state: dict | None,
    as_of: str,
    conflicts: list[dict] | None = None,
) -> tuple[list[Trigger], dict]:
    """Convenience entry point: everything the fleet should notice this check, plus the state
    to persist for the next one. `conflicts` defaults to None/empty so every existing caller
    (and every existing test) keeps working unchanged — the schedule-conflict axis is additive."""
    state = watch_state or {}
    conflicts = conflicts or []
    triggers = detect_stock_triggers(par_records, state.get("sku_status", {}), as_of)
    triggers += detect_fatigue_triggers(unit_summary, state.get("unit_critical", {}), as_of)
    triggers += detect_credential_triggers(
        credential_records, set(state.get("expired_staff", [])), as_of
    )
    triggers += detect_schedule_conflict_triggers(
        conflicts, set(state.get("conflict_keys", [])), as_of
    )
    return triggers, next_watch_state(par_records, unit_summary, credential_records, conflicts)
