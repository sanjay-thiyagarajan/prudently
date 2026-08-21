import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.supply.reorder import compute_reorders, vendor_summary

VENDORS = [
    {
        "vendor_id": "ven-primary",
        "name": "MedSupply Primary",
        "lead_time_days": 3,
        "reliability": 0.95,
    },
    {
        "vendor_id": "ven-backup",
        "name": "Regional Backup Distributors",
        "lead_time_days": 6,
        "reliability": 0.85,
    },
]


def inv_item(
    sku: str,
    current_stock: int,
    reorder_point: int = 50,
    baseline_daily_consumption: int = 5,
    primary_vendor_id: str | None = "ven-primary",
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
        "primary_vendor_id": primary_vendor_id,
    }


def test_ok_status_items_are_excluded():
    records = compute_reorders([inv_item("A", current_stock=100, reorder_point=50)], VENDORS)
    assert records == []


def test_low_status_is_routine_urgency():
    # ratio 50/50=1.0 -> low; days_of_supply = 50/5 = 10.0
    records = compute_reorders([inv_item("A", current_stock=50, reorder_point=50)], VENDORS)
    assert records[0]["stock_status"] == "low"
    assert records[0]["urgency"] == "routine"
    assert "URGENT" not in records[0]["recommendation"]


def test_critical_status_is_expedited_urgency():
    # ratio 5/50=0.1 -> critical; days_of_supply = 5/5 = 1.0
    records = compute_reorders([inv_item("A", current_stock=5, reorder_point=50)], VENDORS)
    assert records[0]["stock_status"] == "critical"
    assert records[0]["urgency"] == "expedited"
    assert "URGENT" in records[0]["recommendation"]


def test_reorder_quantity_targets_configured_days_of_supply():
    records = compute_reorders(
        [inv_item("A", current_stock=10, reorder_point=50, baseline_daily_consumption=5)],
        VENDORS,
        target_days_of_supply=14,
    )
    assert records[0]["reorder_quantity"] == 5 * 14 - 10


def test_reorder_quantity_never_negative():
    # current stock already above the 14-day target, but still under reorder_point -> "low"
    # with nothing extra needed
    records = compute_reorders(
        [inv_item("A", current_stock=1000, reorder_point=2000, baseline_daily_consumption=5)],
        VENDORS,
    )
    assert records[0]["reorder_quantity"] == 0


def test_primary_vendor_used_when_lead_time_beats_stockout():
    # current_stock=50, reorder_point=50 -> low; baseline=5 -> days_of_supply=10 > lead_time=3
    records = compute_reorders(
        [inv_item("A", current_stock=50, reorder_point=50, baseline_daily_consumption=5)], VENDORS
    )
    record = records[0]
    assert record["vendor_id"] == "ven-primary"
    assert record["will_stock_out_before_delivery"] is False
    assert record["alternate_vendor_id"] is None
    assert "contact" not in record["recommendation"]


def test_alternate_vendor_flagged_when_primary_lead_time_too_slow():
    # current_stock=10, baseline=5 -> days_of_supply=2 < primary lead_time_days=3
    records = compute_reorders(
        [inv_item("A", current_stock=10, reorder_point=50, baseline_daily_consumption=5)], VENDORS
    )
    record = records[0]
    assert record["days_of_supply"] == 2.0
    assert record["will_stock_out_before_delivery"] is True
    assert record["alternate_vendor_id"] == "ven-backup"
    assert "Regional Backup Distributors" in record["recommendation"]


def test_no_alternate_flagged_when_only_one_vendor_exists():
    records = compute_reorders(
        [inv_item("A", current_stock=5, reorder_point=50, baseline_daily_consumption=5)],
        [VENDORS[0]],
    )
    record = records[0]
    assert record["will_stock_out_before_delivery"] is True
    assert record["alternate_vendor_id"] is None


def test_unknown_vendor_id_yields_no_vendor_fields():
    records = compute_reorders(
        [inv_item("A", current_stock=50, reorder_point=50, primary_vendor_id="ven-ghost")], VENDORS
    )
    record = records[0]
    assert record["vendor_id"] is None
    assert record["vendor_name"] is None
    assert record["will_stock_out_before_delivery"] is False


def test_missing_baseline_consumption_never_triggers_stockout_flag():
    records = compute_reorders(
        [inv_item("A", current_stock=5, reorder_point=50, baseline_daily_consumption=0)], VENDORS
    )
    assert records[0]["days_of_supply"] is None
    assert records[0]["will_stock_out_before_delivery"] is False


def test_zero_reorder_point_is_always_ok_and_excluded():
    records = compute_reorders([inv_item("A", current_stock=0, reorder_point=0)], VENDORS)
    assert records == []


def test_records_sorted_expedited_first_then_by_days_of_supply():
    records = compute_reorders(
        [
            inv_item("ROUTINE", current_stock=45, reorder_point=50, baseline_daily_consumption=5),
            inv_item("EXPEDITED", current_stock=5, reorder_point=50, baseline_daily_consumption=5),
        ],
        VENDORS,
    )
    assert records[0]["sku"] == "EXPEDITED"
    assert records[1]["sku"] == "ROUTINE"


def test_vendor_summary_aggregates_order_counts_and_quantity():
    records = compute_reorders(
        [
            inv_item("A", current_stock=0, reorder_point=50, baseline_daily_consumption=1),
            inv_item("B", current_stock=0, reorder_point=50, baseline_daily_consumption=1),
        ],
        VENDORS,
        target_days_of_supply=14,
    )
    summary = vendor_summary(records)
    assert summary["ven-primary"]["order_count"] == 2
    assert summary["ven-primary"]["total_quantity"] == 28
