"""Minimal Cloud KMS field-encryption helper, used only by seed.py's write_firestore when
writing the `patients` collection to real Firestore — DRY_RUN's local JSON output
(.local_output/patients.json) is left plaintext on purpose, for inspectability, since nothing
written there ever reaches a real datastore.

Deliberately a small, intentional duplicate of apps/api/services/platform/crypto_kms.py's
KmsCryptoService.encrypt_field rather than a cross-package import: packages/datagen and
apps/api are two independent uv projects with no shared workspace (confirmed — neither
pyproject.toml references the other), and services/triggers.py already establishes this
codebase's own precedent for exactly this shape of duplication (a tiny derivation duplicated
across a boundary it deliberately keeps clean, rather than reached across). Same KMS key
(prudently-patient-data/patient-pii, us-central1, project prudently-hackathon) as apps/api's
config.py — a value encrypted here decrypts correctly through the real app's crypto_kms.py at
read time, since both are the same Cloud KMS resource."""

from __future__ import annotations

import base64
from functools import lru_cache

PROJECT_ID = "prudently-hackathon"
KMS_LOCATION = "us-central1"
KMS_KEY_RING = "prudently-patient-data"
KMS_KEY_ID = "patient-pii"

PATIENT_PII_FIELDS = ("name", "date_of_birth", "contact_email", "contact_phone")


@lru_cache
def _client():
    from google.cloud import kms  # pylint: disable=import-outside-toplevel

    return kms.KeyManagementServiceClient()


@lru_cache
def _key_path() -> str:
    return _client().crypto_key_path(PROJECT_ID, KMS_LOCATION, KMS_KEY_RING, KMS_KEY_ID)


def encrypt_field(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    response = _client().encrypt(
        request={"name": _key_path(), "plaintext": plaintext.encode("utf-8")}
    )
    return base64.b64encode(response.ciphertext).decode("ascii")


def encrypt_patient_record(record: dict) -> dict:
    encrypted = dict(record)
    for field in PATIENT_PII_FIELDS:
        if encrypted.get(field):
            encrypted[field] = encrypt_field(encrypted[field])
    return encrypted
