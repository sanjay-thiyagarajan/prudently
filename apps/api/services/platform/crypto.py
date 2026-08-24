"""Field-level encryption capability port for patient PII (Part D) — the piece that makes this
codebase's "architected for real PII" claim true rather than aspirational. Firestore's own
encryption-at-rest protects the whole database uniformly, which is real but doesn't answer
"what happens if the application layer itself is compromised" (docs/threat-model.md finding 9's
shared-identity blast-radius concern): a field encrypted with a key the application only reaches
through `decrypt_field` stays opaque even to a caller that can read Firestore directly but never
goes through this module. `crypto_kms.py` is the real implementation (Cloud KMS, confirmed real
product — same "adapter with a real GCP backend" shape as `armor.py`/`observability.py`);
`crypto_local.py` is an emulated fallback for offline dev/tests, matching `armor_local.py`'s own
"architecturally honest no-op/stand-in, not real protection" framing. Selected by
`CRYPTO_BACKEND` via `get_crypto_service()` below.

Direct per-field encrypt/decrypt, not envelope encryption with a locally-generated data
encryption key: every value protected here (a name, a date, an email, a phone number) is a few
dozen bytes, comfortably inside Cloud KMS's ~64KiB payload limit for a symmetric key, so
generating/wrapping/managing a local DEK would buy nothing a direct KMS call doesn't already
provide. Envelope encryption earns its complexity at bulk-data scale, which patient contact
fields aren't."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from config import get_settings


class CryptoService(Protocol):  # pylint: disable=too-few-public-methods
    def encrypt_field(self, plaintext: str) -> str: ...  # noqa: E704
    def decrypt_field(self, ciphertext: str) -> str: ...  # noqa: E704


@lru_cache
def get_crypto_service() -> CryptoService:
    # Local imports for the same reason as armor.py's get_armor_service: keeps google-cloud-kms
    # out of the import graph entirely when CRYPTO_BACKEND=local, and avoids a real circular
    # import between this module and its two backends.
    # pylint: disable=import-outside-toplevel,cyclic-import
    if get_settings().crypto_backend == "vertex":
        from .crypto_kms import KmsCryptoService

        return KmsCryptoService()

    from .crypto_local import LocalCryptoService

    return LocalCryptoService()
