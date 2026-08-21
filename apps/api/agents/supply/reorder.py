"""Vendor/reorder decisions: given raw inventory items (services.state.get_inventory shape)
and the vendor catalog, decides which SKUs need reordering, how much to reorder, which
vendor to place it with, and whether the primary vendor's lead time is too slow to avoid a
stockout — in which case an alternate vendor is flagged for parallel outreach. Pure functions
over plain dicts (matching the Firestore document shape from
packages/datagen/datagen/inventory.py and services/state.py) — no I/O, no ADK, so this is
cheap to unit-test exhaustively.

Stock-status math is intentionally re-derived here rather than imported from
agents.inventory.par_levels: each agent folder is deployed to its own Reasoning Engine as a
self-contained unit (see AGENTS.md's `adk deploy agent_engine` notes), so a cross-agent-folder
import would need extra deploy staging just to avoid a ~10-line duplication — not worth the
deploy fragility. If the two ever drift, agents.inventory.par_levels is the source of truth
for what counts as 'low' vs 'critical'."""

from __future__ import annotations

from typing import Literal

StockStatus = Literal["ok", "low", "critical"]
Urgency = Literal["routine", "expedited"]

# Mirrors agents.inventory.par_levels.CRITICAL_RATIO — see module docstring for why this is
# duplicated rather than imported.
CRITICAL_RATIO = 0.5

# Reorder brings stock up to this many days of baseline consumption, not just back to the
# reorder point — matches the datagen headroom (8-20 days on hand at baseline) so a routine
# reorder covers a full restock cycle rather than triggering again almost immediately.
TARGET_DAYS_OF_SUPPLY = 14


# pylint: disable=duplicate-code
# Deliberately mirrors agents.inventory.par_levels._stock_status / _days_of_supply — see
# module docstring above for why this is duplicated rather than imported.
def _stock_status(current_stock: int, reorder_point: int) -> StockStatus:
    if reorder_point <= 0:
        return "ok"
    ratio = current_stock / reorder_point
    if ratio <= CRITICAL_RATIO:
        return "critical"
    if ratio <= 1.0:
        return "low"
    return "ok"


def _days_of_supply(current_stock: int, baseline_daily_consumption: int) -> float | None:
    if baseline_daily_consumption <= 0:
        return None
    return round(current_stock / baseline_daily_consumption, 1)


# pylint: enable=duplicate-code


def _vendor_by_id(vendors: list[dict], vendor_id: str | None) -> dict | None:
    return next((v for v in vendors if v["vendor_id"] == vendor_id), None)


def _alternate_vendor(vendors: list[dict], primary_vendor_id: str | None) -> dict | None:
    return next((v for v in vendors if v["vendor_id"] != primary_vendor_id), None)


def _reorder_quantity(
    current_stock: int, baseline_daily_consumption: int, target_days_of_supply: int
) -> int:
    target = baseline_daily_consumption * target_days_of_supply
    return max(0, target - current_stock)


def _recommendation(decision: dict) -> str:
    """Expects the in-progress decision dict built by compute_reorders (all keys except
    'recommendation' itself already set) — keeps this helper to one argument instead of
    threading every field through individually."""
    vendor_name = decision["vendor_name"] or "an alternate vendor (no primary vendor on file)"
    base = (
        f"Reorder {decision['reorder_quantity']} {decision['name']} "
        f"({decision['sku']}) from {vendor_name}."
    )
    if decision["urgency"] == "expedited":
        base = f"URGENT — {base}"
    if decision["will_stock_out_before_delivery"] and decision["alternate_vendor_name"]:
        base += (
            f" Primary vendor's lead time won't beat the stockout — contact "
            f"{decision['alternate_vendor_name']} in parallel."
        )
    return base


def compute_reorders(
    items: list[dict],
    vendors: list[dict],
    target_days_of_supply: int = TARGET_DAYS_OF_SUPPLY,
) -> list[dict]:
    """Returns one reorder decision per SKU that is 'low' or 'critical' on stock, sorted
    most-urgent first. Expects raw inventory items shaped like
    packages/datagen/datagen/inventory.py / services.state.get_inventory (sku, name,
    category, current_stock, reorder_point, baseline_daily_consumption, primary_vendor_id)."""
    decisions: list[dict] = []

    for item in items:
        current_stock = item["current_stock"]
        baseline_daily_consumption = item.get("baseline_daily_consumption", 0)
        status = _stock_status(current_stock, item["reorder_point"])
        if status == "ok":
            continue

        days_left = _days_of_supply(current_stock, baseline_daily_consumption)
        vendor = _vendor_by_id(vendors, item.get("primary_vendor_id"))
        alternate = _alternate_vendor(vendors, item.get("primary_vendor_id"))
        urgency: Urgency = "expedited" if status == "critical" else "routine"

        will_stock_out_before_delivery = (
            vendor is not None and days_left is not None and days_left < vendor["lead_time_days"]
        )

        quantity = _reorder_quantity(
            current_stock, baseline_daily_consumption, target_days_of_supply
        )

        decision = {
            "sku": item["sku"],
            "name": item["name"],
            "category": item["category"],
            "stock_status": status,
            "days_of_supply": days_left,
            "reorder_quantity": quantity,
            "vendor_id": vendor["vendor_id"] if vendor else None,
            "vendor_name": vendor["name"] if vendor else None,
            "vendor_lead_time_days": vendor["lead_time_days"] if vendor else None,
            "vendor_reliability": vendor["reliability"] if vendor else None,
            "urgency": urgency,
            "will_stock_out_before_delivery": will_stock_out_before_delivery,
            "alternate_vendor_id": (
                alternate["vendor_id"] if (will_stock_out_before_delivery and alternate) else None
            ),
            "alternate_vendor_name": (
                alternate["name"] if (will_stock_out_before_delivery and alternate) else None
            ),
        }
        decision["recommendation"] = _recommendation(decision)
        decisions.append(decision)

    decisions.sort(
        key=lambda d: (
            d["urgency"] != "expedited",
            d["days_of_supply"] is None,
            d["days_of_supply"],
        )
    )
    return decisions


def vendor_summary(reorder_decisions: list[dict]) -> dict[str, dict]:
    """Aggregate per-vendor order counts and total reorder quantity — what the Coordinator/
    dashboard actually wants to show for vendor load rather than the full per-SKU list."""
    summary: dict[str, dict] = {}
    for decision in reorder_decisions:
        vendor_id = decision["vendor_id"] or "unassigned"
        bucket = summary.setdefault(vendor_id, {"order_count": 0, "total_quantity": 0})
        bucket["order_count"] += 1
        bucket["total_quantity"] += decision["reorder_quantity"]
    return summary
