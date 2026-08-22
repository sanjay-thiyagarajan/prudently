"""One-off, additive backfill for the payroll/guest-doctor-hours milestone (Aug 22, 2026):
adds `hourly_rate` to existing staff_roster docs and per-diem/guest-doctor shift history to
shift_history — both new fields/records `generate_roster` now produces, per its own
docstring. Deliberately not a full `make seed` rerun: `generate_roster` defaults to
`today=date.today()`, so a full reseed would also re-anchor every credential_expiry date to
today, disturbing HR's already-demo-relevant flagged-staff set for no reason (see
resync_shift_history.py's docstring for the same reasoning applied to shift_history's own
repair). This script only ever adds:

- `staff_roster`: `.update({"hourly_rate": ...})` per doc — a targeted field merge, every
  other field (credential_expiry, is_per_diem, etc.) untouched.
- `shift_history`: `.set()` for per-diem staff_ids' shifts only — brand-new doc IDs (per-diem
  staff currently have zero shift_history docs), never touches a regular staff member's
  already-corrected history.

Usage: `SIM_SEED=42 GOOGLE_CLOUD_PROJECT=prudently-hackathon uv run python -m
datagen.backfill_payroll_data` (run from packages/datagen). No DRY_RUN mode, same rationale as
resync_shift_history.py."""

from __future__ import annotations

import os

from datagen.roster import as_dicts as roster_as_dicts
from datagen.roster import generate_roster
from datagen.seed import _BATCH_CHUNK_SIZE, _doc_id_for


def main() -> None:
    from google.cloud import firestore  # imported lazily, matches seed.py's convention

    seed = int(os.environ.get("SIM_SEED", "42"))
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "prudently-hackathon")
    print(f"Backfilling payroll data (SIM_SEED={seed}, project={project})")

    staff, shifts = generate_roster(seed)
    staff_dicts, shift_dicts = roster_as_dicts(staff, shifts)
    rate_by_staff_id = {s["staff_id"]: s["hourly_rate"] for s in staff_dicts}
    perdiem_ids = {s["staff_id"] for s in staff_dicts if s["is_per_diem"]}
    perdiem_shift_dicts = [r for r in shift_dicts if r["staff_id"] in perdiem_ids]
    print(
        f"  {len(rate_by_staff_id)} staff hourly rates, {len(perdiem_shift_dicts)} guest-doctor shifts"
    )

    client = firestore.Client(project=project)

    staff_coll = client.collection("staff_roster")
    live_staff_ids = [d.id for d in staff_coll.stream()]
    updated = 0
    for chunk_start in range(0, len(live_staff_ids), _BATCH_CHUNK_SIZE):
        chunk = live_staff_ids[chunk_start : chunk_start + _BATCH_CHUNK_SIZE]
        batch = client.batch()
        for staff_id in chunk:
            if staff_id not in rate_by_staff_id:
                continue
            batch.update(staff_coll.document(staff_id), {"hourly_rate": rate_by_staff_id[staff_id]})
            updated += 1
        batch.commit()
    print(f"  updated hourly_rate on {updated} staff_roster docs")

    shift_coll = client.collection("shift_history")
    written = 0
    for chunk_start in range(0, len(perdiem_shift_dicts), _BATCH_CHUNK_SIZE):
        chunk = perdiem_shift_dicts[chunk_start : chunk_start + _BATCH_CHUNK_SIZE]
        batch = client.batch()
        for offset, record in enumerate(chunk):
            doc_id = _doc_id_for("shift_history", record, chunk_start + offset)
            batch.set(shift_coll.document(doc_id), record)
            written += 1
        batch.commit()
    print(f"  added {written} guest-doctor shift_history docs")
    print("Done.")


if __name__ == "__main__":
    main()
