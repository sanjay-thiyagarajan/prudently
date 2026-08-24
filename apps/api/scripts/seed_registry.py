"""Seeds the `agent_registry` Firestore collection read by services/platform/registry.py (and,
through it, the Gateway's `before_tool_callback`). Run via `uv run python -m scripts.
seed_registry` from apps/api, or `make seed-registry`. Reasoning Engine IDs are copied from
config.py by hand after each agent's first `adk deploy agent_engine` — this script does not
call GCP to discover them, matching the manual "fill in config.py" step already documented in
AGENTS.md's deploy notes. Safe to re-run: every write is a full `set()` on a fixed doc ID
(the agent name), not an incremental update."""

from __future__ import annotations

from config import AGENT_ENGINE_SETTING, get_settings
from services.state import get_client

REGISTRY: list[dict] = [
    {
        "agent_name": "coordinator",
        "role": "root ADK agent, sole user-facing entry point",
        "status": "active",
        "reasoning_engine_id": None,
        "firestore_collections": ["agent_registry"],
    },
    {
        "agent_name": "shift_allocation_agent",
        "role": "fatigue/overtime burndown -> reallocation recommendations",
        "status": "active",
        "reasoning_engine_id": None,  # filled from config.py below
        "firestore_collections": ["staff_roster", "shift_history"],
    },
    {
        "agent_name": "inventory_management_agent",
        "role": "tactical stock/par-level tracking",
        "status": "active",
        "reasoning_engine_id": None,
        "firestore_collections": ["inventory"],
    },
    {
        "agent_name": "supply_chain_resiliency_agent",
        "role": "strategic vendor/reorder decisions",
        "status": "active",
        "reasoning_engine_id": None,
        "firestore_collections": ["vendors"],
    },
    {
        "agent_name": "hr_agent",
        "role": "credentialing + per-diem escalation target",
        "status": "active",
        "reasoning_engine_id": None,
        "firestore_collections": ["staff_roster"],
    },
    {
        "agent_name": "medical_representative_agent",
        "role": "external-facing vendor/pharma liaison, Model Armor ingestion boundary",
        "status": "active",
        "reasoning_engine_id": None,
        "firestore_collections": [],
    },
    {
        "agent_name": "chaos_continuity_agent",
        "role": "hospital what-if + fleet fault injection",
        "status": "active",
        "reasoning_engine_id": None,
        "firestore_collections": ["chaos_experiments"],
    },
    {
        "agent_name": "surgical_scheduling_agent",
        "role": "OR/surgeon double-booking detection + patient status notifications",
        "status": "active",
        "reasoning_engine_id": None,
        "firestore_collections": ["patients", "surgical_cases", "patient_notification_log"],
    },
]


def main() -> None:
    settings = get_settings()
    client = get_client()
    batch = client.batch()

    for entry in REGISTRY:
        settings_field = AGENT_ENGINE_SETTING.get(entry["agent_name"])
        if settings_field:
            entry["reasoning_engine_id"] = getattr(settings, settings_field) or None
        batch.set(client.collection("agent_registry").document(entry["agent_name"]), entry)

    batch.commit()
    print(f"wrote {len(REGISTRY)} agent_registry docs")


if __name__ == "__main__":
    main()
