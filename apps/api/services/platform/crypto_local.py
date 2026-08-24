"""Local-emulated field-encryption fallback: reversible but explicitly NOT real encryption —
same "architecturally honest no-op/stand-in, not real protection" framing as
`armor_local.py`/`email_local.py`. Used for offline dev/tests so importing services/state.py's
patient accessors never requires live Cloud KMS credentials. A ciphertext produced here is
tagged `local:` specifically so nobody mistakes a value round-tripped through this backend for
one that was ever actually protected."""

from __future__ import annotations

import base64

_PREFIX = "local:"


class LocalCryptoService:
    def encrypt_field(self, plaintext: str) -> str:
        if not plaintext:
            return plaintext
        return _PREFIX + base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    def decrypt_field(self, ciphertext: str) -> str:
        if not ciphertext:
            return ciphertext
        if not ciphertext.startswith(_PREFIX):
            # Never silently "decrypt" a value that was never actually encrypted through this
            # backend — that would hide a real backend mismatch (e.g. data written under
            # CRYPTO_BACKEND=vertex, read back under =local) as a plausible-looking string.
            raise ValueError("Not a value this local backend encrypted.")
        return base64.b64decode(ciphertext[len(_PREFIX) :]).decode("utf-8")
