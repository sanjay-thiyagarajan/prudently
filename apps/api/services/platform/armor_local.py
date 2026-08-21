"""Local-emulated Model Armor fallback: keyword/pattern-based screening for offline dev
without GCP credentials — architecturally honest defense-in-depth behind the same
`ArmorService` interface `armor_vertex.py` satisfies, not a stub (see AGENTS.md's platform
adapter layer + Memory Bank docs' own "memory poisoning" mitigation guidance re: defense in
depth). Deliberately conservative (a handful of high-signal phrases, not exhaustive) — the
real filter is `armor_vertex.py`; this only needs to keep local dev/tests functional when
`ARMOR_BACKEND=local`, not match Model Armor's actual detection quality."""

from __future__ import annotations

import re

from .armor import ArmorResult  # pylint: disable=cyclic-import

# Prompt-injection / jailbreak signal phrases — mirrors the class of attack Model Armor's
# pi_and_jailbreak filter targets, not an attempt to replicate its ML detection.
_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore (all )?previous instructions",
        r"disregard (all )?(previous|prior) instructions",
        r"you are now in (developer|admin|unrestricted) mode",
        r"do not mention this (instruction|to the user)",
        r"system prompt",
        r"jailbreak",
    ]
]

_MALICIOUS_URI_PATTERN = re.compile(
    r"https?://[^\s]*\.(?:zip|exe|apk|ru|tk)(?:[/\s]|$)", re.IGNORECASE
)


class LocalArmorService:  # pylint: disable=too-few-public-methods
    def screen(self, text: str) -> ArmorResult:
        matched: list[str] = []

        if any(pattern.search(text) for pattern in _INJECTION_PATTERNS):
            matched.append("pi_and_jailbreak")
        if _MALICIOUS_URI_PATTERN.search(text):
            matched.append("malicious_uris")

        reason = f"Local armor flagged: {', '.join(matched)}" if matched else None
        return ArmorResult(blocked=bool(matched), matched_filters=tuple(matched), reason=reason)
