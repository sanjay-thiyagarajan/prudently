import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.inventory.par_levels import category_summary, compute_par_levels


def item(
    sku: str,
    current_stock: int,
    reorder_point: int,
    baseline_daily_consumption: int = 10,
    category: str = "PPE",
    name: str | None = None,
) -> dict:
    return {
        "sku": sku,
        "name": name or f"Item {sku}",
        "category": category,
        "unit": "box",
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "baseline_daily_consumption": baseline_daily_consumption,
        "primary_vendor_id": "ven-primary",
    }


def test_stock_well_above_reorder_point_is_ok():
    records = compute_par_levels([item("A", current_stock=100, reorder_point=50)])
    assert records[0]["stock_status"] == "ok"
    assert records[0]["recommendation"] is None


def test_stock_at_reorder_point_is_low():
    records = compute_par_levels([item("A", current_stock=50, reorder_point=50)])
    assert records[0]["stock_status"] == "low"
    assert "reorder point" in records[0]["recommendation"]


def test_stock_below_half_reorder_point_is_critical():
    records = compute_par_levels([item("A", current_stock=20, reorder_point=50)])
    assert records[0]["stock_status"] == "critical"
    assert "critically low" in records[0]["recommendation"]


def test_stock_exactly_at_critical_boundary_is_critical():
    records = compute_par_levels([item("A", current_stock=25, reorder_point=50)])
    assert records[0]["stock_status"] == "critical"


def test_days_of_supply_computed_from_baseline_consumption():
    records = compute_par_levels(
        [item("A", current_stock=30, reorder_point=50, baseline_daily_consumption=10)]
    )
    assert records[0]["days_of_supply"] == 3.0


def test_zero_baseline_consumption_yields_no_days_of_supply():
    records = compute_par_levels(
        [item("A", current_stock=20, reorder_point=50, baseline_daily_consumption=0)]
    )
    assert records[0]["days_of_supply"] is None
    assert records[0]["stock_status"] == "critical"  # status math is unaffected


def test_zero_reorder_point_is_always_ok():
    records = compute_par_levels([item("A", current_stock=0, reorder_point=0)])
    assert records[0]["stock_status"] == "ok"


def test_records_sorted_by_lowest_days_of_supply_first():
    records = compute_par_levels(
        [
            item("HIGH", current_stock=200, reorder_point=50, baseline_daily_consumption=10),
            item("LOW", current_stock=5, reorder_point=50, baseline_daily_consumption=10),
        ]
    )
    assert records[0]["sku"] == "LOW"
    assert records[1]["sku"] == "HIGH"


def test_records_with_no_days_of_supply_sort_last():
    records = compute_par_levels(
        [
            item("NODATA", current_stock=5, reorder_point=50, baseline_daily_consumption=0),
            item("LOW", current_stock=5, reorder_point=50, baseline_daily_consumption=10),
        ]
    )
    assert records[0]["sku"] == "LOW"
    assert records[1]["sku"] == "NODATA"


def test_category_summary_aggregates_status_counts():
    records = compute_par_levels(
        [
            item("A", current_stock=100, reorder_point=50, category="PPE"),
            item("B", current_stock=50, reorder_point=50, category="PPE"),
            item("C", current_stock=5, reorder_point=50, category="pharmacy"),
        ]
    )
    summary = category_summary(records)
    assert summary["PPE"]["ok"] == 1
    assert summary["PPE"]["low"] == 1
    assert summary["pharmacy"]["critical"] == 1
