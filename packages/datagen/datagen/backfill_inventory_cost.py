"""One-off, additive backfill: adds `unit_cost` to existing `inventory` docs — the new field
`generate_inventory` now produces, per its own
docstring. Deliberately not a full `make seed` rerun, same reasoning as
`backfill_payroll_data.py`: `generate_inventory`'s `current_stock` draw must stay untouched, so
this only ever does a targeted `.update({"unit_cost": ...})` per doc, every other field left
alone.

Usage: `SIM_SEED=42 GOOGLE_CLOUD_PROJECT=prudently-hackathon uv run python -m
datagen.backfill_inventory_cost` (run from packages/datagen). No DRY_RUN mode, same rationale
as `backfill_payroll_data.py`."""

from __future__ import annotations

import os

from datagen.inventory import as_dicts as inventory_as_dicts
from datagen.inventory import generate_inventory


def main() -> None:
    from google.cloud import firestore  # imported lazily, matches seed.py's convention

    seed = int(os.environ.get("SIM_SEED", "42"))
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "prudently-hackathon")
    print(f"Backfilling inventory unit_cost (SIM_SEED={seed}, project={project})")

    items, _vendors = generate_inventory(seed)
    item_dicts, _vendor_dicts = inventory_as_dicts(items, _vendors)
    cost_by_sku = {i["sku"]: i["unit_cost"] for i in item_dicts}

    client = firestore.Client(project=project)
    inv_coll = client.collection("inventory")
    live_skus = [d.id for d in inv_coll.stream()]

    batch = client.batch()
    updated = 0
    for sku in live_skus:
        if sku not in cost_by_sku:
            continue
        batch.update(inv_coll.document(sku), {"unit_cost": cost_by_sku[sku]})
        updated += 1
    batch.commit()
    print(f"  updated unit_cost on {updated} inventory docs")
    print("Done.")


if __name__ == "__main__":
    main()
