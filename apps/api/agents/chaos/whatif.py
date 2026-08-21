"""Hospital-domain what-if: projects the staffing and inventory impact of a hypothetical
mass-casualty patient surge, without mutating any live state — a "what would happen if"
projection, not a simulation tick. Pure functions over plain dicts (matching the Firestore
document shapes from packages/datagen and services/state.py), same discipline as every other
specialist's pure-logic module (see agents/shift/burndown.py, agents/inventory/par_levels.py).

Deliberately reimplements the risk-threshold math from burndown.py and par_levels.py rather
than importing those agents' modules — cross-agent-folder imports don't survive `adk deploy`'s
per-folder staging cleanly (see agents/supply/reorder.py's docstring for the same call made
there first)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

RiskLevel = Literal["safe", "elevated", "critical"]
StockStatus = Literal["ok", "low", "critical"]

TRAILING_WINDOW_DAYS = 7
ELEVATED_THRESHOLD = 0.85
CRITICAL_THRESHOLD = 1.10

# Assumption: a unit absorbing a mass-casualty surge runs its staff this many extra hours per
# day, every day of the surge window, on top of their actual trailing-week hours — a rough
# stand-in for "all hands, extended shifts" during acute response, not a claim about any real
# hospital's actual surge staffing policy.
OVERTIME_HOURS_PER_SURGE_DAY = 4.0

CRITICAL_RATIO = 0.5

# Assumption: each additional patient hospital-wide raises daily consumption of every
# catalogued item (PPE, fluids, meds, O2, consumables) by this fraction — a single blunt
# multiplier standing in for item-specific per-patient usage rates the synthetic catalog
# doesn't model. Documented here, not hidden in the math, because it's the projection's
# single biggest simplifying assumption.
CONSUMPTION_INCREASE_PER_PATIENT = 0.02


# pylint: disable=duplicate-code
# _parse_date/_staffing_risk_level deliberately mirror agents.shift.burndown's
# _parse_date/_risk_level — see this module's docstring for why they're duplicated, not
# imported.
def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _staffing_risk_level(ratio: float) -> RiskLevel:
    if ratio >= CRITICAL_THRESHOLD:
        return "critical"
    if ratio >= ELEVATED_THRESHOLD:
        return "elevated"
    return "safe"


# pylint: enable=duplicate-code


def _stock_status(current_stock: float, reorder_point: int) -> StockStatus:
    if reorder_point <= 0:
        return "ok"
    ratio = current_stock / reorder_point
    if ratio <= CRITICAL_RATIO:
        return "critical"
    if ratio <= 1.0:
        return "low"
    return "ok"


# pylint: disable-next=too-many-arguments,too-many-positional-arguments,too-many-locals
def project_staffing_impact(
    staff: list[dict],
    shifts: list[dict],
    unit: str,
    surge_days: int,
    as_of: date,
    window_days: int = TRAILING_WINDOW_DAYS,
) -> list[dict]:
    """Projects burndown risk for every staff member in `unit` if they each pick up
    `OVERTIME_HOURS_PER_SURGE_DAY` extra hours/day for `surge_days`, on top of their actual
    trailing `window_days` hours. Non-`unit` staff are excluded — a surge concentrated in one
    unit doesn't project extra hours onto staff who aren't absorbing it. Sorted highest
    projected risk first."""
    # pylint: disable=duplicate-code
    # Mirrors agents.shift.burndown's trailing-hours accumulation — deliberately duplicated,
    # not imported, per the cross-agent-folder staging rationale in this module's docstring.
    trailing_hours: dict[str, float] = {}
    for shift in shifts:
        shift_date = _parse_date(shift["shift_date"])
        age_days = (as_of - shift_date).days
        if 0 <= age_days < window_days:
            staff_id = shift["staff_id"]
            trailing_hours[staff_id] = trailing_hours.get(staff_id, 0.0) + shift["hours"]
    # pylint: enable=duplicate-code

    records: list[dict] = []
    for member in staff:
        if member["unit"] != unit:
            continue
        staff_id = member["staff_id"]
        current_hours = trailing_hours.get(staff_id, 0.0)
        projected_hours = current_hours + OVERTIME_HOURS_PER_SURGE_DAY * surge_days
        safe_hours = member.get("safe_weekly_hours", 40.0)
        ratio = projected_hours / safe_hours if safe_hours else 0.0

        records.append(
            {
                "staff_id": staff_id,
                "name": member["name"],
                "unit": unit,
                "current_trailing_hours": current_hours,
                "projected_hours": round(projected_hours, 1),
                "safe_weekly_hours": safe_hours,
                "projected_burndown_ratio": round(ratio, 3),
                "projected_risk_level": _staffing_risk_level(ratio),
            }
        )

    records.sort(key=lambda r: r["projected_burndown_ratio"], reverse=True)
    return records


def project_inventory_impact(
    items: list[dict], additional_patients: int, surge_days: int
) -> list[dict]:
    """Projects stock status for every catalogued item under the surge's inflated
    consumption rate over `surge_days`, using `CONSUMPTION_INCREASE_PER_PATIENT` — see module
    docstring for that assumption's caveat. Sorted lowest projected runway first."""
    multiplier = 1.0 + CONSUMPTION_INCREASE_PER_PATIENT * additional_patients

    records: list[dict] = []
    for item in items:
        baseline = item.get("baseline_daily_consumption", 0)
        surged_daily = baseline * multiplier
        projected_consumed = surged_daily * surge_days
        projected_remaining = item["current_stock"] - projected_consumed
        status = _stock_status(projected_remaining, item["reorder_point"])

        records.append(
            {
                "sku": item["sku"],
                "name": item["name"],
                "category": item["category"],
                "current_stock": item["current_stock"],
                "surged_daily_consumption": round(surged_daily, 1),
                "projected_remaining_after_surge": round(projected_remaining, 1),
                "projected_stock_status": status,
            }
        )

    records.sort(key=lambda r: r["projected_remaining_after_surge"])
    return records


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def project_mass_casualty_surge(
    staff: list[dict],
    shifts: list[dict],
    items: list[dict],
    additional_patients: int,
    unit: str,
    surge_days: int,
    as_of: date | None = None,
) -> dict:
    """Top-level what-if: `additional_patients` arriving over `surge_days`, absorbed by
    `unit`. Combines the staffing and inventory projections and flags whether each would
    need real escalation (Shift -> HR per-diem activation; Inventory -> Supply Chain
    expedited reorder) if the surge actually happened — read-only, nothing here writes to
    live state or triggers a real escalation."""
    as_of = as_of or date.today()
    staffing = project_staffing_impact(staff, shifts, unit, surge_days, as_of)
    inventory = project_inventory_impact(items, additional_patients, surge_days)

    critical_staff = [r for r in staffing if r["projected_risk_level"] == "critical"]
    critical_items = [r for r in inventory if r["projected_stock_status"] == "critical"]

    return {
        "additional_patients": additional_patients,
        "unit": unit,
        "surge_days": surge_days,
        "as_of": as_of.isoformat(),
        "staffing_projection": staffing,
        "inventory_projection": inventory,
        "would_need_hr_escalation": len(critical_staff) > 0,
        "staff_needing_escalation": [r["name"] for r in critical_staff],
        "would_need_expedited_reorder": len(critical_items) > 0,
        "items_needing_reorder": [r["sku"] for r in critical_items],
    }
