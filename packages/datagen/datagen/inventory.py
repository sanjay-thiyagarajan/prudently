"""Synthetic supply catalog + vendors for the Supply Chain Resiliency Agent's reorder
recommendation logic (see apps/api/agents/supply/reorder.py).

The item master below carries the field set a real hospital materials-management system
(Cerner/Oracle Health Supply Chain, Infor CloudSuite, GHX) actually tracks per SKU — not just
enough to compute a reorder point. Manufacturer/vendor identifiers, UNSPSC classification,
storage/handling, lot + expiration, and hazard/criticality flags are all real fields those
systems carry; only the *values* here are synthetic, same honesty framing as roster.py's
HOURLY_RATE_BASE and this module's own base_unit_cost. Manufacturer and distributor names are
invented (e.g. "Meridian Medical"), not real companies — same convention as VENDORS below,
which has never named a real distributor."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Literal

StorageCondition = Literal[
    "room_temperature", "refrigerated", "controlled_substance_safe", "compressed_gas"
]

# One catalog entry per SKU. A dict, not a positional tuple — the field count here (16) makes a
# tuple unreadable and error-prone to reorder; a dict is self-labeling at every call site.
# `unspsc_code` is a real UN classification scheme hospital procurement systems use to group
# purchases across vendors regardless of a vendor's own SKU naming.
CATALOG: list[dict] = [
    {
        "sku": "N95-001",
        "name": "N95 respirator masks",
        "category": "PPE",
        "unit": "box-of-20",
        "baseline_daily_consumption": 12,
        "base_unit_cost": 28.00,
        "manufacturer": "Meridian Medical",
        "manufacturer_part_number": "MM-N95-20",
        "gtin": "10812345600014",
        "unspsc_code": "42131601",
        "storage_location": "Central Supply — PPE Bay",
        "storage_condition": "room_temperature",
        "package_quantity": 20,
        "shelf_life_days": 1825,  # 5 years, typical for NIOSH-rated respirators
        "is_hazardous": False,
        "is_controlled_substance": False,
        "is_critical_item": True,
    },
    {
        "sku": "GLV-002",
        "name": "Nitrile exam gloves",
        "category": "PPE",
        "unit": "box-of-100",
        "baseline_daily_consumption": 8,
        "base_unit_cost": 9.50,
        "manufacturer": "Coastal Health Supply",
        "manufacturer_part_number": "CHS-GLV-100M",
        "gtin": "10812345600021",
        "unspsc_code": "42132203",
        "storage_location": "Central Supply — PPE Bay",
        "storage_condition": "room_temperature",
        "package_quantity": 100,
        "shelf_life_days": 1825,
        "is_hazardous": False,
        "is_controlled_substance": False,
        "is_critical_item": True,
    },
    {
        "sku": "IVF-003",
        "name": "IV saline fluid bags",
        "category": "fluids",
        "unit": "bag",
        "baseline_daily_consumption": 40,
        "base_unit_cost": 3.75,
        "manufacturer": "Apex Fluid Systems",
        "manufacturer_part_number": "AFS-NS-1000",
        "gtin": "10812345600038",
        "unspsc_code": "51141701",
        "storage_location": "Central Supply — Fluids Bay",
        "storage_condition": "room_temperature",
        "package_quantity": 1,
        "shelf_life_days": 730,
        "is_hazardous": False,
        "is_controlled_substance": False,
        "is_critical_item": True,
    },
    {
        "sku": "OSE-004",
        "name": "Oseltamivir (antiviral)",
        "category": "pharmacy",
        "unit": "course",
        "baseline_daily_consumption": 3,
        "base_unit_cost": 65.00,
        "manufacturer": "Northgate Pharma",
        "manufacturer_part_number": "NGP-OSE-75",
        "gtin": "10812345600045",
        "unspsc_code": "51142108",
        "storage_location": "Pharmacy — Secure Storage",
        "storage_condition": "room_temperature",
        "package_quantity": 1,
        "shelf_life_days": 730,
        "is_hazardous": False,
        "is_controlled_substance": False,
        "is_critical_item": False,
    },
    {
        "sku": "ABX-005",
        "name": "Broad-spectrum antibiotics",
        "category": "pharmacy",
        "unit": "course",
        "baseline_daily_consumption": 6,
        "base_unit_cost": 40.00,
        "manufacturer": "Northgate Pharma",
        "manufacturer_part_number": "NGP-ABX-500",
        "gtin": "10812345600052",
        "unspsc_code": "51141543",
        "storage_location": "Pharmacy — Secure Storage",
        "storage_condition": "room_temperature",
        "package_quantity": 1,
        "shelf_life_days": 545,
        "is_hazardous": False,
        "is_controlled_substance": False,
        "is_critical_item": True,
    },
    {
        "sku": "O2-006",
        "name": "Oxygen cylinders",
        "category": "respiratory",
        "unit": "cylinder",
        "baseline_daily_consumption": 5,
        "base_unit_cost": 55.00,
        "manufacturer": "Summit Gas & Medical",
        "manufacturer_part_number": "SGM-O2-E",
        "gtin": "10812345600069",
        "unspsc_code": "42131811",
        "storage_location": "Respiratory Therapy — Cylinder Cage",
        "storage_condition": "compressed_gas",
        "package_quantity": 1,
        "shelf_life_days": None,  # compressed medical gas doesn't expire
        "is_hazardous": True,
        "is_controlled_substance": False,
        "is_critical_item": True,
    },
    {
        "sku": "SYR-007",
        "name": "Syringes",
        "category": "consumables",
        "unit": "box-of-100",
        "baseline_daily_consumption": 6,
        "base_unit_cost": 12.00,
        "manufacturer": "Coastal Health Supply",
        "manufacturer_part_number": "CHS-SYR-100",
        "gtin": "10812345600076",
        "unspsc_code": "42142502",
        "storage_location": "Central Supply — Consumables Bay",
        "storage_condition": "room_temperature",
        "package_quantity": 100,
        "shelf_life_days": 1825,
        "is_hazardous": False,
        "is_controlled_substance": False,
        "is_critical_item": False,
    },
    {
        "sku": "GWN-008",
        "name": "Isolation gowns",
        "category": "PPE",
        "unit": "box-of-10",
        "baseline_daily_consumption": 5,
        "base_unit_cost": 18.00,
        "manufacturer": "Meridian Medical",
        "manufacturer_part_number": "MM-GWN-10",
        "gtin": "10812345600083",
        "unspsc_code": "42131606",
        "storage_location": "Central Supply — PPE Bay",
        "storage_condition": "room_temperature",
        "package_quantity": 10,
        "shelf_life_days": 1095,
        "is_hazardous": False,
        "is_controlled_substance": False,
        "is_critical_item": True,
    },
]

VENDORS = [
    # (vendor_id, name, lead_time_days, reliability)
    ("ven-primary", "MedSupply Primary", 3, 0.95),
    ("ven-backup", "Regional Backup Distributors", 6, 0.85),
]


@dataclass(frozen=True)
class InventoryItem:
    # pylint: disable=too-many-instance-attributes
    # A real hospital item master carries exactly this many fields per SKU — see this module's
    # own docstring for which system's field set this mirrors.
    sku: str
    name: str
    category: str
    unit: str
    current_stock: int
    reorder_point: int
    baseline_daily_consumption: int
    primary_vendor_id: str
    unit_cost: float
    manufacturer: str
    manufacturer_part_number: str
    gtin: str
    unspsc_code: str
    storage_location: str
    storage_condition: StorageCondition
    package_quantity: int
    par_level_min: int
    par_level_max: int
    is_hazardous: bool
    is_controlled_substance: bool
    is_critical_item: bool
    lot_number: str
    expiration_date: str | None


@dataclass(frozen=True)
class Vendor:
    vendor_id: str
    name: str
    lead_time_days: int
    reliability: float


# SKUs seeded with deliberately tight stock so Supply Chain has real, organic material to act
# on the moment the fleet watch's first cycle runs — no scripted depletion required. Mirrors
# how staff fatigue/credential status already land under pressure at plain seed time (see
# AGENTS.md's autonomous fleet watch section): N95-001 seeds already `critical`, O2-006 already
# `low` (agents/inventory/par_levels.py's CRITICAL_RATIO=0.5 against a 5-day reorder point).
_TIGHT_STOCK_DAYS_ON_HAND = {
    "N95-001": (1, 2),  # ratio <= 0.4 -> critical
    "O2-006": (3, 4),  # ratio in (0.6, 0.8] -> low
}

# A reference "today" for expiration-date generation — deliberately not date.today(): the whole
# fleet already runs on a simulated clock (services/state.py's sim day), and a real seed run
# should be reproducible byte-for-byte given the same SIM_SEED, which date.today() would break.
_CATALOG_EPOCH = date(2026, 1, 1)


def generate_inventory(seed: int) -> tuple[list[InventoryItem], list[Vendor]]:
    rng = random.Random(seed)
    # Own rng stream (seed+1), same "isolated stream per concern" discipline as roster.py's
    # hourly_rate — added later than current_stock's draws, must never perturb them.
    cost_rng = random.Random(seed + 1)
    # A third stream (seed+2) for lot/expiration — added later still, for the same reason.
    lot_rng = random.Random(seed + 2)
    vendors = [Vendor(*v) for v in VENDORS]

    items: list[InventoryItem] = []
    for entry in CATALOG:
        sku = entry["sku"]
        daily = entry["baseline_daily_consumption"]
        # Stock on hand is normally 8-20 days of baseline consumption — enough headroom that
        # most SKUs are calm at seed time. A couple of SKUs (_TIGHT_STOCK_DAYS_ON_HAND) seed
        # deliberately tight instead, so Supply Chain has genuine reorder material immediately.
        low, high = _TIGHT_STOCK_DAYS_ON_HAND.get(sku, (8, 20))
        days_on_hand = rng.randint(low, high)
        stock = daily * days_on_hand
        reorder_point = daily * 5  # reorder when < 5 days of baseline supply remain
        unit_cost = round(entry["base_unit_cost"] * cost_rng.uniform(0.9, 1.1), 2)

        shelf_life = entry["shelf_life_days"]
        if shelf_life is None:
            expiration_date = None
        else:
            # The lot on hand is at a random point in its shelf life, not freshly received —
            # some runway left (at least 30 days) so most items don't seed already expired.
            remaining = rng.randint(30, shelf_life)
            expiration_date = (_CATALOG_EPOCH + timedelta(days=remaining)).isoformat()
        lot_number = f"L{lot_rng.randint(100000, 999999)}"

        items.append(
            InventoryItem(
                sku=sku,
                name=entry["name"],
                category=entry["category"],
                unit=entry["unit"],
                current_stock=stock,
                reorder_point=reorder_point,
                baseline_daily_consumption=daily,
                primary_vendor_id=vendors[0].vendor_id,
                unit_cost=unit_cost,
                manufacturer=entry["manufacturer"],
                manufacturer_part_number=entry["manufacturer_part_number"],
                gtin=entry["gtin"],
                unspsc_code=entry["unspsc_code"],
                storage_location=entry["storage_location"],
                storage_condition=entry["storage_condition"],
                package_quantity=entry["package_quantity"],
                # The par range a real materials-management system restocks against: the floor
                # is the same reorder_point (below it, an order must already be in flight), the
                # ceiling is 15 days of baseline consumption (the level a standard reorder
                # brings the SKU back up to).
                par_level_min=reorder_point,
                par_level_max=daily * 15,
                is_hazardous=entry["is_hazardous"],
                is_controlled_substance=entry["is_controlled_substance"],
                is_critical_item=entry["is_critical_item"],
                lot_number=lot_number,
                expiration_date=expiration_date,
            )
        )

    return items, vendors


def as_dicts(items: list[InventoryItem], vendors: list[Vendor]) -> tuple[list[dict], list[dict]]:
    return [asdict(i) for i in items], [asdict(v) for v in vendors]
