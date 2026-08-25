"""One-off, additive backfill: pushes the enriched item-master fields `generate_inventory` now
produces (manufacturer, GTIN, UNSPSC code, storage location/condition, package quantity, par
range, hazard/controlled/critical flags, lot number, expiration date — see datagen/inventory.py's
module docstring) onto existing `inventory` docs. Deliberately not a full `make seed` rerun,
same reasoning as backfill_inventory_cost.py and backfill_payroll_data.py: `current_stock` has
been live-mutated by the sim clock's consumption ticks and any reorders received since this
project was first seeded, so this only ever does a targeted per-field `.update()`, leaving
`current_stock`/`reorder_point`/`unit_cost` and anything else already live untouched.

Usage: `SIM_SEED=42 GOOGLE_CLOUD_PROJECT=prudently-hackathon uv run python -m
datagen.backfill_inventory_fields` (run from packages/datagen). No DRY_RUN mode, same rationale
as backfill_inventory_cost.py."""

from __future__ import annotations

import os

from datagen.inventory import as_dicts as inventory_as_dicts
from datagen.inventory import generate_inventory

# Everything generate_inventory now produces beyond the fields already live in Firestore —
# current_stock, reorder_point, baseline_daily_consumption, primary_vendor_id, unit_cost are
# deliberately absent here, they're each already backfilled or live-mutated by another path.
_NEW_FIELDS = (
    "manufacturer",
    "manufacturer_part_number",
    "gtin",
    "unspsc_code",
    "storage_location",
    "storage_condition",
    "package_quantity",
    "par_level_min",
    "par_level_max",
    "is_hazardous",
    "is_controlled_substance",
    "is_critical_item",
    "lot_number",
    "expiration_date",
)


def main() -> None:
    from google.cloud import firestore  # imported lazily, matches seed.py's convention

    seed = int(os.environ.get("SIM_SEED", "42"))
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "prudently-hackathon")
    print(f"Backfilling inventory item-master fields (SIM_SEED={seed}, project={project})")

    items, _vendors = generate_inventory(seed)
    item_dicts, _vendor_dicts = inventory_as_dicts(items, _vendors)
    by_sku = {i["sku"]: i for i in item_dicts}

    client = firestore.Client(project=project)
    inv_coll = client.collection("inventory")
    live_skus = [d.id for d in inv_coll.stream()]

    batch = client.batch()
    updated = 0
    for sku in live_skus:
        generated = by_sku.get(sku)
        if generated is None:
            continue
        patch = {field: generated[field] for field in _NEW_FIELDS}
        batch.update(inv_coll.document(sku), patch)
        updated += 1
    batch.commit()
    print(f"  updated {len(_NEW_FIELDS)} fields on {updated} inventory docs")
    print("Done.")


if __name__ == "__main__":
    main()
