import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.chaos.whatif import (  # noqa: E402
    project_inventory_impact,
    project_mass_casualty_surge,
    project_staffing_impact,
)

TODAY = date(2026, 8, 21)

STAFF = [
    {"staff_id": "er-00", "name": "Nurse ER-00", "unit": "ER", "safe_weekly_hours": 40.0},
    {"staff_id": "er-01", "name": "Nurse ER-01", "unit": "ER", "safe_weekly_hours": 40.0},
    {"staff_id": "icu-00", "name": "Nurse ICU-00", "unit": "ICU", "safe_weekly_hours": 40.0},
]


def shift(staff_id: str, days_ago: int, hours: float) -> dict:
    shift_date = date(2026, 8, 21 - days_ago)
    return {"staff_id": staff_id, "shift_date": shift_date.isoformat(), "hours": hours}


def test_staffing_projection_excludes_other_units():
    records = project_staffing_impact(STAFF, [], unit="ER", surge_days=3, as_of=TODAY)
    assert {r["staff_id"] for r in records} == {"er-00", "er-01"}


def test_staffing_projection_adds_overtime_on_top_of_trailing_hours():
    # er-00: 8 actual trailing hours + (4 hrs/day * 3 surge days) = 20 projected -> ratio 0.5
    shifts = [shift("er-00", 0, 8)]
    records = project_staffing_impact(STAFF, shifts, unit="ER", surge_days=3, as_of=TODAY)
    er00 = next(r for r in records if r["staff_id"] == "er-00")
    assert er00["projected_hours"] == 20.0
    assert er00["projected_burndown_ratio"] == 0.5
    assert er00["projected_risk_level"] == "safe"


def test_staffing_projection_crosses_into_critical():
    # er-00: 20 trailing hours + (4 * 6) = 44 projected -> ratio 1.1 -> critical
    shifts = [shift("er-00", d, 4) for d in range(5)]  # 20 hours
    records = project_staffing_impact(STAFF, shifts, unit="ER", surge_days=6, as_of=TODAY)
    er00 = next(r for r in records if r["staff_id"] == "er-00")
    assert er00["projected_risk_level"] == "critical"


def test_staffing_projection_sorted_highest_risk_first():
    shifts = [shift("er-00", 0, 30), shift("er-01", 0, 2)]
    records = project_staffing_impact(STAFF, shifts, unit="ER", surge_days=1, as_of=TODAY)
    assert records[0]["staff_id"] == "er-00"


ITEM = {
    "sku": "IVF-003",
    "name": "IV saline fluid bags",
    "category": "fluids",
    "current_stock": 320,
    "reorder_point": 200,
    "baseline_daily_consumption": 40,
}


def test_inventory_projection_no_surge_is_baseline_only():
    records = project_inventory_impact([ITEM], additional_patients=0, surge_days=1)
    assert records[0]["surged_daily_consumption"] == 40.0
    assert records[0]["projected_remaining_after_surge"] == 280.0
    assert records[0]["projected_stock_status"] == "ok"


def test_inventory_projection_scales_with_additional_patients():
    # multiplier = 1 + 0.02*10 = 1.2 -> surged_daily = 48, consumed over 3 days = 144
    records = project_inventory_impact([ITEM], additional_patients=10, surge_days=3)
    record = records[0]
    assert record["surged_daily_consumption"] == 48.0
    assert record["projected_remaining_after_surge"] == 176.0
    assert record["projected_stock_status"] == "low"  # ratio 176/200 = 0.88


def test_inventory_projection_can_flip_to_critical():
    low_stock_item = {**ITEM, "current_stock": 100}
    records = project_inventory_impact([low_stock_item], additional_patients=0, surge_days=1)
    # remaining = 100 - 40 = 60, ratio 60/200 = 0.3 <= 0.5 -> critical
    assert records[0]["projected_stock_status"] == "critical"


def test_inventory_projection_sorted_lowest_runway_first():
    plentiful = {**ITEM, "sku": "PLENTY", "current_stock": 10000}
    scarce = {**ITEM, "sku": "SCARCE", "current_stock": 50}
    records = project_inventory_impact([plentiful, scarce], additional_patients=0, surge_days=1)
    assert records[0]["sku"] == "SCARCE"


def test_mass_casualty_surge_flags_escalations_when_needed():
    shifts = [shift("er-00", d, 4) for d in range(5)]  # pushes er-00 toward critical
    scarce_item = {**ITEM, "current_stock": 100}
    result = project_mass_casualty_surge(
        STAFF, shifts, [scarce_item], additional_patients=5, unit="ER", surge_days=6, as_of=TODAY
    )
    assert result["would_need_hr_escalation"] is True
    assert "Nurse ER-00" in result["staff_needing_escalation"]
    assert result["would_need_expedited_reorder"] is True
    assert "IVF-003" in result["items_needing_reorder"]


def test_mass_casualty_surge_no_escalation_when_calm():
    plentiful_item = {**ITEM, "current_stock": 100000}
    result = project_mass_casualty_surge(
        STAFF, [], [plentiful_item], additional_patients=1, unit="ER", surge_days=1, as_of=TODAY
    )
    assert result["would_need_hr_escalation"] is False
    assert result["staff_needing_escalation"] == []
    assert result["would_need_expedited_reorder"] is False
    assert result["items_needing_reorder"] == []
