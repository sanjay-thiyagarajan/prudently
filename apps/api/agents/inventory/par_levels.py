"""Stock/par-level tracking: flags SKUs whose current stock has fallen to or below their
reorder point, and estimates days-of-supply remaining against baseline daily consumption.
Pure functions over plain dicts (matching the Firestore document shape from
packages/datagen/datagen/inventory.py and services/state.py) — no I/O, no ADK, so this is
cheap to unit-test exhaustively."""

from __future__ import annotations

from typing import Literal

StockStatus = Literal["ok", "low", "critical"]

# Ratio of current_stock to reorder_point at which stock status changes. At or below the
# reorder point itself (ratio <= 1.0) stock is "low"; once it drops under half the reorder
# point there's not enough runway left to trust a normal-lead-time reorder, so "critical".
CRITICAL_RATIO = 0.5


# pylint: disable=duplicate-code
# agents.supply.reorder deliberately mirrors this pair of functions — see that module's
# docstring for why (cross-agent-folder imports don't survive `adk deploy`'s per-folder
# staging cleanly).
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


def _recommendation(
    status: StockStatus, item_name: str, sku: str, days_left: float | None
) -> str | None:
    if status == "critical":
        return (
            f"{item_name} ({sku}) is critically low"
            + (f" — ~{days_left} days of supply left" if days_left is not None else "")
            + " — place an expedited reorder now."
        )
    if status == "low":
        return (
            f"{item_name} ({sku}) has fallen to its reorder point"
            + (f" — ~{days_left} days of supply left" if days_left is not None else "")
            + " — place a standard reorder."
        )
    return None


def compute_par_levels(items: list[dict]) -> list[dict]:
    """Returns one stock record per inventory item, sorted lowest-runway (most urgent) first."""
    records: list[dict] = []
    for item in items:
        current_stock = item["current_stock"]
        reorder_point = item["reorder_point"]
        baseline_daily_consumption = item.get("baseline_daily_consumption", 0)
        status = _stock_status(current_stock, reorder_point)
        days_left = _days_of_supply(current_stock, baseline_daily_consumption)

        records.append(
            {
                "sku": item["sku"],
                "name": item["name"],
                "category": item["category"],
                "unit": item["unit"],
                "current_stock": current_stock,
                "reorder_point": reorder_point,
                "baseline_daily_consumption": baseline_daily_consumption,
                "days_of_supply": days_left,
                "stock_status": status,
                "primary_vendor_id": item.get("primary_vendor_id"),
                "recommendation": _recommendation(status, item["name"], item["sku"], days_left),
            }
        )

    records.sort(key=lambda r: (r["days_of_supply"] is None, r["days_of_supply"]))
    return records


def category_summary(par_level_records: list[dict]) -> dict[str, dict]:
    """Aggregate per-category counts of stock status — what the Coordinator/dashboard
    actually wants to show at a glance rather than the full per-SKU list."""
    summary: dict[str, dict] = {}
    for record in par_level_records:
        category = record["category"]
        bucket = summary.setdefault(category, {"ok": 0, "low": 0, "critical": 0})
        bucket[record["stock_status"]] += 1
    return summary
