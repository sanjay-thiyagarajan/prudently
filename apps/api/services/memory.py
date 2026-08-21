"""Memory Bank wrapper — persistent, cross-session narrative memory, confirmed a real Vertex
AI capability (docs/day1-probe-results.md #2) and confirmed working end-to-end Day 3 via a
live write+search round trip. Memories are scoped per (app_name, user_id); by convention
here app_name is the specialist agent's name (e.g. "shift_allocation_agent") and user_id is
the narrowest sensible scope for that agent (a unit, SKU, or scenario id — see AGENTS.md's
agent roster table), matching the Memory Bank docs' isolation guidance.

Requires a deployed Reasoning Engine — memories are a sub-resource of one
(reasoningEngines/{engine_id}/memories). The service's `location` must match that engine's
own deployment region (us-central1 here), not a separate multi-region — confirmed Day 3:
location="us" 404s with "ReasoningEngine does not exist" even though the engine is real.
"""

from __future__ import annotations

from functools import lru_cache

from google.adk.memory.memory_entry import MemoryEntry
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.genai import types as genai_types

from config import GCP_PROJECT_ID, get_settings


@lru_cache
def get_memory_service() -> VertexAiMemoryBankService:
    settings = get_settings()
    return VertexAiMemoryBankService(
        project=GCP_PROJECT_ID,
        location=settings.memory_bank_location,
        agent_engine_id=settings.shift_agent_engine_id,
    )


async def write_fact(app_name: str, user_id: str, fact: str, author: str = "system") -> None:
    """Direct write (CreateMemory-equivalent) — use for facts that should persist verbatim,
    e.g. "sim_day 8: flu surge onset, ER admissions +30%", not summarized/reinterpreted.
    `role="user"` regardless of `author`: confirmed Day 3 that Memory Bank normalizes/expects
    this rather than an arbitrary role string — `author` still carries provenance separately."""
    entry = MemoryEntry(
        content=genai_types.Content(role="user", parts=[genai_types.Part(text=fact)]),
        author=author,
    )
    await get_memory_service().add_memory(app_name=app_name, user_id=user_id, memories=[entry])


async def search(app_name: str, user_id: str, query: str) -> list[str]:
    """Similarity search scoped to (app_name, user_id) — returns fact text only."""
    response = await get_memory_service().search_memory(
        app_name=app_name, user_id=user_id, query=query
    )
    return [m.content.parts[0].text for m in response.memories if m.content.parts]
