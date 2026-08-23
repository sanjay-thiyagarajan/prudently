"""Synthetic supply catalog + vendors for the Supply Chain Resiliency Agent's reorder
recommendation logic (see apps/api/agents/supply/reorder.py, Day 4)."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

CATALOG = [
    # (sku, name, category, unit, baseline_daily_consumption, base_unit_cost)
    # base_unit_cost is a plausible-looking synthetic figure, not sourced from real pricing —
    # same honesty framing as roster.py's HOURLY_RATE_BASE.
    ("N95-001", "N95 respirator masks", "PPE", "box-of-20", 12, 28.00),
    ("GLV-002", "Nitrile exam gloves", "PPE", "box-of-100", 8, 9.50),
    ("IVF-003", "IV saline fluid bags", "fluids", "bag", 40, 3.75),
    ("OSE-004", "Oseltamivir (antiviral)", "pharmacy", "course", 3, 65.00),
    ("ABX-005", "Broad-spectrum antibiotics", "pharmacy", "course", 6, 40.00),
    ("O2-006", "Oxygen cylinders", "respiratory", "cylinder", 5, 55.00),
    ("SYR-007", "Syringes", "consumables", "box-of-100", 6, 12.00),
    ("GWN-008", "Isolation gowns", "PPE", "box-of-10", 5, 18.00),
]

VENDORS = [
    # (vendor_id, name, lead_time_days, reliability)
    ("ven-primary", "MedSupply Primary", 3, 0.95),
    ("ven-backup", "Regional Backup Distributors", 6, 0.85),
]


@dataclass(frozen=True)
class InventoryItem:
    sku: str
    name: str
    category: str
    unit: str
    current_stock: int
    reorder_point: int
    baseline_daily_consumption: int
    primary_vendor_id: str
    unit_cost: float = 0.0


@dataclass(frozen=True)
class Vendor:
    vendor_id: str
    name: str
    lead_time_days: int
    reliability: float


def generate_inventory(seed: int) -> tuple[list[InventoryItem], list[Vendor]]:
    rng = random.Random(seed)
    # Own rng stream (seed+1), same "isolated stream per concern" discipline as roster.py's
    # hourly_rate — added later than current_stock's draws, must never perturb them.
    cost_rng = random.Random(seed + 1)
    vendors = [Vendor(*v) for v in VENDORS]

    items: list[InventoryItem] = []
    for sku, name, category, unit, daily, base_cost in CATALOG:
        # Stock on hand is 8-20 days of baseline consumption — enough headroom that the
        # baseline scenario is calm, but tight enough that a surge (Day 8+) forces a real
        # reorder recommendation instead of nothing happening.
        days_on_hand = rng.randint(8, 20)
        stock = daily * days_on_hand
        reorder_point = daily * 5  # reorder when < 5 days of baseline supply remain
        unit_cost = round(base_cost * cost_rng.uniform(0.9, 1.1), 2)
        items.append(
            InventoryItem(
                sku=sku,
                name=name,
                category=category,
                unit=unit,
                current_stock=stock,
                reorder_point=reorder_point,
                baseline_daily_consumption=daily,
                primary_vendor_id=vendors[0].vendor_id,
                unit_cost=unit_cost,
            )
        )

    return items, vendors


def as_dicts(items: list[InventoryItem], vendors: list[Vendor]) -> tuple[list[dict], list[dict]]:
    return [asdict(i) for i in items], [asdict(v) for v in vendors]
