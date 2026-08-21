"""Model Armor capability port: screens inbound text (vendor communications, Day 4's
Medical Representative ingestion path) for prompt injection, jailbreak attempts, malicious
URIs, and other unsafe content *before* it reaches LLM context, Memory Bank, or an A2A hop.
`armor_vertex.py` is the real implementation (`google-cloud-modelarmor` against a live
template — confirmed real product, see docs/day1-probe-results.md #6); `armor_local.py` is a
keyword-based emulated fallback for offline dev. Selected by `ARMOR_BACKEND` via
`get_armor_service()` below, matching the adapter pattern described in AGENTS.md's "Platform
adapter layer" section."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from config import get_settings


@dataclass(frozen=True)
class ArmorResult:
    blocked: bool
    matched_filters: tuple[str, ...]
    reason: str | None
    # True only when Model Armor itself couldn't be reached (fail-closed path in
    # armor_vertex.py) — distinct from a genuine content match. Callers (dashboard,
    # armor_events) must not render this the same as a real block: an outage rendered as a
    # successful security demo is a wrong narration, not a security win.
    service_error: bool = False


class ArmorService(Protocol):  # pylint: disable=too-few-public-methods
    def screen(self, text: str) -> ArmorResult: ...  # noqa: E704


@lru_cache
def get_armor_service() -> ArmorService:
    # Imports are local (not top-level) on purpose, for two reasons: (1) armor_vertex and
    # armor_local both import ArmorResult from this module, so a top-level import here would
    # be a real circular import, not just a pylint false positive; (2) it keeps
    # google-cloud-modelarmor out of the import graph entirely when ARMOR_BACKEND=local.
    # pylint: disable=import-outside-toplevel,cyclic-import
    if get_settings().armor_backend == "vertex":
        from .armor_vertex import VertexArmorService

        return VertexArmorService()

    from .armor_local import LocalArmorService

    return LocalArmorService()
