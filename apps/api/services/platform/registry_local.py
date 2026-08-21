"""Local-emulated Agent Registry: reads the `agent_registry` Firestore collection (seeded by
scripts/seed_registry.py) — architecturally honest defense-in-depth behind the same
`RegistryService` interface a real product would satisfy, not a stub, matching the framing in
AGENTS.md's platform adapter layer."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import firestore

from config import GCP_PROJECT_ID

from .registry import RegistryEntry  # pylint: disable=cyclic-import


@lru_cache
def _client() -> firestore.Client:
    return firestore.Client(project=GCP_PROJECT_ID, database="(default)")


def _to_entry(doc: dict) -> RegistryEntry:
    return RegistryEntry(
        agent_name=doc["agent_name"],
        role=doc["role"],
        status=doc["status"],
        reasoning_engine_id=doc.get("reasoning_engine_id") or None,
        firestore_collections=tuple(doc.get("firestore_collections", [])),
    )


class LocalRegistryService:  # pylint: disable=too-few-public-methods
    def get_agent(self, agent_name: str) -> RegistryEntry | None:
        doc = _client().collection("agent_registry").document(agent_name).get()
        if not doc.exists:
            return None
        return _to_entry(doc.to_dict())
