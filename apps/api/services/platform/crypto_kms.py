"""Real field-encryption adapter — Cloud KMS symmetric encrypt/decrypt against a dedicated key
(`infra/terraform/modules/kms`). Credential path is the caller's own IAM identity, same pattern
as every other real GCP adapter in this codebase (Model Armor, Cloud Trace): no key material is
ever fetched into this process — Cloud KMS does the actual cryptographic operation and returns
only ciphertext/plaintext bytes, never the key itself, over the API call."""

from __future__ import annotations

import base64
from functools import lru_cache

from config import GCP_PROJECT_ID, get_settings


@lru_cache
def _client():
    from google.cloud import kms  # pylint: disable=import-outside-toplevel

    return kms.KeyManagementServiceClient()


@lru_cache
def _key_path() -> str:
    settings = get_settings()
    return _client().crypto_key_path(
        GCP_PROJECT_ID, settings.kms_location, settings.kms_key_ring, settings.kms_key_id
    )


class KmsCryptoService:
    def encrypt_field(self, plaintext: str) -> str:
        """Returns base64 ciphertext safe to store directly as a Firestore string field. Empty/
        None input passes through unchanged — patient records legitimately have optional fields
        (no phone on file, for instance), and encrypting an empty string is a pointless KMS
        call that would still need special-casing on the read side anyway."""
        if not plaintext:
            return plaintext
        response = _client().encrypt(
            request={"name": _key_path(), "plaintext": plaintext.encode("utf-8")}
        )
        return base64.b64encode(response.ciphertext).decode("ascii")

    def decrypt_field(self, ciphertext: str) -> str:
        """The inverse of encrypt_field. Every call site is already gated by
        services/auth.py's require_role("admin", "clinician") before this ever runs — see
        routes/surgical_scheduling.py — so reaching this function at all implies the caller was
        already authorized to see the plaintext."""
        if not ciphertext:
            return ciphertext
        response = _client().decrypt(
            request={"name": _key_path(), "ciphertext": base64.b64decode(ciphertext)}
        )
        return response.plaintext.decode("utf-8")
