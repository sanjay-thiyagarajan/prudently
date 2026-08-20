"""Entry point: `python -m datagen.seed` (invoked via `make seed`).

Generates the synthetic roster, inventory, and admissions timeline and loads it into
Firestore's live-state collections (staff_roster, shift_history, inventory, vendors,
admissions_timeseries) — see AGENTS.md for the collection ownership table. In DRY_RUN mode
(default, matches .env.example) it writes local JSON under .local_output/ instead, so the
data can be inspected without a Firestore emulator running.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from datagen.admissions import as_dicts as admissions_as_dicts
from datagen.admissions import generate_admissions
from datagen.inventory import as_dicts as inventory_as_dicts
from datagen.inventory import generate_inventory
from datagen.roster import as_dicts as roster_as_dicts
from datagen.roster import generate_roster

LOCAL_OUTPUT_DIR = Path(__file__).resolve().parent.parent / ".local_output"


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    return default if val is None else val.strip().lower() in ("1", "true", "yes")


def build_dataset(seed: int) -> dict[str, list[dict]]:
    staff, shifts = generate_roster(seed)
    staff_dicts, shift_dicts = roster_as_dicts(staff, shifts)

    items, vendors = generate_inventory(seed)
    item_dicts, vendor_dicts = inventory_as_dicts(items, vendors)

    admissions = generate_admissions(seed)
    admissions_dicts = admissions_as_dicts(admissions)

    return {
        "staff_roster": staff_dicts,
        "shift_history": shift_dicts,
        "inventory": item_dicts,
        "vendors": vendor_dicts,
        "admissions_timeseries": admissions_dicts,
    }


def write_local(dataset: dict[str, list[dict]]) -> None:
    LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for collection, records in dataset.items():
        path = LOCAL_OUTPUT_DIR / f"{collection}.json"
        path.write_text(json.dumps(records, indent=2))
        print(f"  wrote {len(records):>4} records -> {path.relative_to(Path.cwd())}")


def write_firestore(dataset: dict[str, list[dict]], project: str) -> None:
    from google.cloud import firestore  # imported lazily — not needed in DRY_RUN

    client = firestore.Client(project=project)
    for collection, records in dataset.items():
        batch = client.batch()
        for i, record in enumerate(records):
            doc_id = record.get("staff_id") or record.get("sku") or record.get("vendor_id") or str(i)
            # admissions_timeseries has no natural key; disambiguate by day+unit
            if collection == "admissions_timeseries":
                doc_id = f"{record['sim_day']:02d}-{record['unit'].replace(' ', '_')}"
            batch.set(client.collection(collection).document(doc_id), record)
        batch.commit()
        print(f"  wrote {len(records):>4} records -> Firestore/{collection}")


def main() -> None:
    seed = int(os.environ.get("SIM_SEED", "42"))
    dry_run = _env_bool("DRY_RUN", True)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "prudently-hackathon")

    print(f"Generating synthetic dataset (SIM_SEED={seed}, DRY_RUN={dry_run})")
    dataset = build_dataset(seed)

    if dry_run:
        print(f"DRY_RUN=true -> writing local JSON under {LOCAL_OUTPUT_DIR}")
        write_local(dataset)
    else:
        print(f"DRY_RUN=false -> writing to Firestore project {project}")
        write_firestore(dataset, project)

    print("Done.")


if __name__ == "__main__":
    main()
