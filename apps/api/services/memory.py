"""Memory Bank wrapper — persistent, cross-session narrative memory, a real Vertex AI
capability (docs/day1-probe-results.md #2). Memories are scoped per (app_name, user_id): by
convention here app_name is the specialist agent's name (e.g. "shift_allocation_agent") and
user_id is the narrowest sensible scope for that agent (a unit, SKU, or scenario id — see
AGENTS.md's agent roster table), matching the Memory Bank docs' isolation guidance.

Requires a deployed Reasoning Engine — memories are a sub-resource of one
(reasoningEngines/{engine_id}/memories). The service's `location` must match that engine's
own deployment region (us-central1 here), not a separate multi-region — location="us" 404s
with "ReasoningEngine does not exist" even though the engine is real.

**Per-agent engine scoping (added Aug 23; this used to be hardcoded to Shift's engine).**
Every agent's memories previously landed in Shift's Reasoning Engine regardless of the
app_name they were written under, which made the per-agent scopes in AGENTS.md's roster table
aspirational rather than real, and was the stated reason Medical Representative could not be
wired to Memory Bank at all (an adversarial-input agent writing into Shift's store inverts the
trust boundary that agent exists to demonstrate). `_engine_id_for` now resolves each agent to
its own deployed engine, so an agent's memories live in the engine it actually runs on and one
agent's store is not reachable through another's.

Note that changing an agent's engine id changes where its memories live — facts written before
this change are readable only under the engine they were written to. Everything written under
`shift_allocation_agent` (the sim clock's per-unit burndown timeline, which is all that
mattered) was already going to Shift's engine, so that history carries over intact.
"""

from __future__ import annotations

from functools import lru_cache

from google.adk.memory.memory_entry import MemoryEntry
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.genai import types as genai_types

from config import AGENT_ENGINE_SETTING, GCP_PROJECT_ID, get_settings


def _engine_id_for(app_name: str) -> str:
    try:
        field = AGENT_ENGINE_SETTING[app_name]
    except KeyError as exc:
        raise ValueError(
            f"No Reasoning Engine is registered for agent '{app_name}'. Memory Bank memories "
            "are a sub-resource of a specific deployed engine, so an agent without one cannot "
            "read or write memory. Add it to config.AGENT_ENGINE_SETTING (and to Settings) "
            "if it has been deployed."
        ) from exc
    return getattr(get_settings(), field)


@lru_cache
def get_memory_service(app_name: str) -> VertexAiMemoryBankService:
    """One cached client per agent — each bound to that agent's own Reasoning Engine."""
    settings = get_settings()
    return VertexAiMemoryBankService(
        project=GCP_PROJECT_ID,
        location=settings.memory_bank_location,
        agent_engine_id=_engine_id_for(app_name),
    )


async def write_fact(app_name: str, user_id: str, fact: str, author: str = "system") -> None:
    """Direct write (CreateMemory-equivalent) — use for facts that should persist verbatim,
    e.g. "2026-08-23: ER burndown — 2 safe, 1 elevated, 5 critical.", not summarized/
    reinterpreted.
    `role="user"` regardless of `author`: Memory Bank normalizes/expects this rather than an
    arbitrary role string — `author` still carries provenance separately."""
    entry = MemoryEntry(
        content=genai_types.Content(role="user", parts=[genai_types.Part(text=fact)]),
        author=author,
    )
    await get_memory_service(app_name).add_memory(
        app_name=app_name, user_id=user_id, memories=[entry]
    )


async def search(app_name: str, user_id: str, query: str) -> list[str]:
    """Similarity search scoped to (app_name, user_id) — returns fact text only."""
    response = await get_memory_service(app_name).search_memory(
        app_name=app_name, user_id=user_id, query=query
    )
    return [m.content.parts[0].text for m in response.memories if m.content.parts]
