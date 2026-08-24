"""One-off, additive backfill for the Part D surgical-scheduling milestone: adds `patients` and
`surgical_cases` to an already-seeded Firestore project. Deliberately not a full `make seed`
rerun — `seed.py`'s `write_firestore` iterates over every collection `build_dataset()` produces
(`staff_roster`, `shift_history`, `inventory`, `vendors`, `admissions_timeseries`, `patients`,
`surgical_cases`), and a live re-seed would overwrite whatever the fleet watch and manager
actions have accumulated in every one of those since the project was first seeded — the same
"targeted addition, not a full reseed" reasoning as `backfill_payroll_data.py`. `scheduled_start`/
`scheduled_end` anchor to `date.today()` (see `datagen.patients.generate_surgical_cases`), so
this is meant to be run once, at Part D launch, not repeatedly — re-running it re-anchors every
case to whatever "today" is at run time, which is fine for a fresh backfill but would silently
move an already-demoed schedule if run again later.

`patients` is written through the real Cloud KMS encryption path (`datagen.crypto.
encrypt_patient_record`) — this is the one collection in this backfill that carries PII-shaped
fields, and it must never land in Firestore as plaintext.

Usage: `SIM_SEED=42 GOOGLE_CLOUD_PROJECT=prudently-hackathon uv run python -m
datagen.backfill_patients` (run from packages/datagen). No DRY_RUN mode, same rationale as
backfill_payroll_data.py."""

from __future__ import annotations

import os

from datagen.crypto import encrypt_patient_record
from datagen.patients import as_dicts as patients_as_dicts
from datagen.patients import generate_patients, generate_surgical_cases
from datagen.seed import _BATCH_CHUNK_SIZE, _doc_id_for


def main() -> None:
    from google.cloud import firestore  # imported lazily, matches seed.py's convention

    seed = int(os.environ.get("SIM_SEED", "42"))
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "prudently-hackathon")
    print(f"Backfilling surgical-scheduling data (SIM_SEED={seed}, project={project})")

    client = firestore.Client(project=project)

    live_staff = [doc.to_dict() for doc in client.collection("staff_roster").stream()]
    surgeon_ids = [s["staff_id"] for s in live_staff if s.get("role") == "physician"]
    print(f"  {len(surgeon_ids)} physician-role staff available as surgeons")

    patients = generate_patients(seed)
    surgical_cases = generate_surgical_cases(patients, surgeon_ids, seed)
    patient_dicts, case_dicts = patients_as_dicts(patients, surgical_cases)
    print(f"  generated {len(patient_dicts)} patients, {len(case_dicts)} surgical cases")

    patients_coll = client.collection("patients")
    written = 0
    for chunk_start in range(0, len(patient_dicts), _BATCH_CHUNK_SIZE):
        chunk = patient_dicts[chunk_start : chunk_start + _BATCH_CHUNK_SIZE]
        batch = client.batch()
        for offset, record in enumerate(chunk):
            doc_id = _doc_id_for("patients", record, chunk_start + offset)
            batch.set(patients_coll.document(doc_id), encrypt_patient_record(record))
            written += 1
        batch.commit()
    print(f"  wrote {written} patients (KMS-encrypted PII fields)")

    cases_coll = client.collection("surgical_cases")
    written = 0
    for chunk_start in range(0, len(case_dicts), _BATCH_CHUNK_SIZE):
        chunk = case_dicts[chunk_start : chunk_start + _BATCH_CHUNK_SIZE]
        batch = client.batch()
        for offset, record in enumerate(chunk):
            doc_id = _doc_id_for("surgical_cases", record, chunk_start + offset)
            batch.set(cases_coll.document(doc_id), record)
            written += 1
        batch.commit()
    print(f"  wrote {written} surgical_cases")
    print("Done.")


if __name__ == "__main__":
    main()
