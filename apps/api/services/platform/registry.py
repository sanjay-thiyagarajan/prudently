"""Agent Registry capability port — local-emulated only (Day-1 probe found no distinct
`registries`/`catalogs` resource in the `aiplatform` v1 discovery doc; see
docs/day1-probe-results.md #3). A Firestore-backed catalog of the fleet, `agent_registry`
collection, one doc per agent — seeded by scripts/seed_registry.py, read by the Gateway
(services/platform/gateway.py) before routing any Coordinator → specialist call. No write API:
the registry is operational metadata about a fixed roster, not something agents update at
runtime."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from config import get_settings


@dataclass(frozen=True)
class RegistryEntry:
    agent_name: str
    role: str
    status: str
    reasoning_engine_id: str | None
    firestore_collections: tuple[str, ...]


class RegistryService(Protocol):  # pylint: disable=too-few-public-methods
    def get_agent(self, agent_name: str) -> RegistryEntry | None: ...  # noqa: E704


@lru_cache
def get_registry_service() -> RegistryService:
    if get_settings().registry_backend != "local":
        raise NotImplementedError(
            "REGISTRY_BACKEND=vertex has no real implementation — Day-1 probe found no "
            "distinct Agent Registry GCP product (docs/day1-probe-results.md #3)."
        )

    # pylint: disable-next=import-outside-toplevel,cyclic-import
    from .registry_local import LocalRegistryService

    return LocalRegistryService()
