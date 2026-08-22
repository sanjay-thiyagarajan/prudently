"""One-off repair for the shift_history doc-ID collision bug fixed in seed.py (Aug 22, 2026)
— `write_firestore` used to key every shift_history doc by staff_id alone, so each day's
`batch.set()` for the same staff member overwrote the previous one; only the last of 28
trailing days survived per person (confirmed live: 24 staff -> 24 docs, not ~600).

Deliberately scoped to shift_history alone, not a full `make seed` rerun: `generate_roster`/
`generate_admissions` default to `today=date.today()`, so a full reseed would also re-anchor
every staff_roster credential_expiry and admissions_timeseries calendar_date to today's date —
a real, avoidable side effect on collections that aren't broken (see AGENTS.md's Aug 22 note on
this repair for the full reasoning). This script only deletes and rewrites shift_history.

Usage: `SIM_SEED=42 GOOGLE_CLOUD_PROJECT=prudently-hackathon uv run python -m
datagen.resync_shift_history` (run from packages/datagen). No DRY_RUN mode — this always
targets real Firestore, since a local-JSON dry run can't exhibit or verify a Firestore-only
bug; read the diff below before running against a project that matters."""

from __future__ import annotations

import os

from datagen.roster import as_dicts as roster_as_dicts
from datagen.roster import generate_roster
from datagen.seed import _BATCH_CHUNK_SIZE, _doc_id_for


def main() -> None:
    from google.cloud import firestore  # imported lazily, matches seed.py's convention

    seed = int(os.environ.get("SIM_SEED", "42"))
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "prudently-hackathon")
    print(f"Resyncing shift_history only (SIM_SEED={seed}, project={project})")

    _, shifts = generate_roster(seed)
    _, shift_dicts = roster_as_dicts([], shifts)
    print(f"  regenerated {len(shift_dicts)} shift records (was 24 live docs, one per staff)")

    client = firestore.Client(project=project)
    coll_ref = client.collection("shift_history")

    existing = list(coll_ref.stream())
    for chunk_start in range(0, len(existing), _BATCH_CHUNK_SIZE):
        chunk = existing[chunk_start : chunk_start + _BATCH_CHUNK_SIZE]
        batch = client.batch()
        for doc in chunk:
            batch.delete(doc.reference)
        batch.commit()
    print(f"  deleted {len(existing)} stale docs")

    for chunk_start in range(0, len(shift_dicts), _BATCH_CHUNK_SIZE):
        chunk = shift_dicts[chunk_start : chunk_start + _BATCH_CHUNK_SIZE]
        batch = client.batch()
        for offset, record in enumerate(chunk):
            doc_id = _doc_id_for("shift_history", record, chunk_start + offset)
            batch.set(coll_ref.document(doc_id), record)
        batch.commit()
    print(f"  wrote {len(shift_dicts)} corrected docs -> Firestore/shift_history")
    print("Done.")


if __name__ == "__main__":
    main()
