"""Inventory Management Agent — specialist agent (invoked as an AgentTool by the Coordinator).
Reasons over live Firestore inventory state through the par-levels tool below; the underlying
stock/par-level math lives in par_levels.py and is fully unit-tested independently of the
LLM."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.memory import search as search_memory
from services.platform.observability import get_observability_service
from services.state import get_inventory

from .par_levels import category_summary, compute_par_levels

bootstrap_gemini_credentials()

AGENT_NAME = "inventory_management_agent"


async def recall_sku_history(sku: str, question: str) -> dict:
    """Recalls how a SKU's stock has moved on *earlier days* of this operation — Memory Bank
    holds a fact per SKU per simulated day whenever its status changed (written by the sim
    clock as the timeline advances). Use this for any question about a burn rate, a trend, how
    fast something is falling, or when a SKU first went low. get_inventory_par_levels tells
    you about *now*; this tells you about *before*."""
    with get_observability_service().span("inventory.recall_sku_history", {"sku": sku}) as span:
        try:
            facts = await search_memory(app_name=AGENT_NAME, user_id=sku, query=question)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            span.set_attribute("inventory.recall.error", type(exc).__name__)
            return {
                "sku": sku,
                "recalled_facts": [],
                "note": "Memory Bank is unavailable right now; answer from current state only.",
            }
        span.set_attribute("inventory.recall.fact_count", len(facts))
        return {
            "sku": sku,
            "recalled_facts": facts,
            "note": (
                "No history recorded for this SKU yet — its status has not changed since the "
                "timeline started."
                if not facts
                else f"{len(facts)} fact(s) recalled from earlier days of this operation."
            ),
        }


def get_inventory_par_levels() -> dict:
    """Returns current stock/par-level status for every inventory SKU, plus a per-category
    status summary. Use this before recommending any reorder — it tells you which SKUs are
    ok, low (at or below reorder point), or critical (under half of reorder point), and the
    estimated days of supply remaining at baseline consumption."""
    items = get_inventory()
    records = compute_par_levels(items)
    return {
        "sku_par_levels": records,
        "category_summary": category_summary(records),
    }


root_agent = Agent(
    model=get_settings().model_fast,
    name="inventory_management_agent",
    description=(
        "Tracks hospital supply stock against par (reorder point) levels and flags SKUs "
        "that need reordering, with estimated days of supply remaining."
    ),
    instruction=(
        "You are the Inventory Management Agent for a hospital's Fortified Enterprise "
        "Fleet. Call get_inventory_par_levels to see current stock status across all SKUs. "
        "When asked for a recommendation, prioritize SKUs flagged 'critical', then 'low'. "
        "Be concrete: name the SKU, its category, current stock, and days of supply "
        "remaining. Never recommend anything for SKUs at 'ok' status. If asked about a "
        "category with no at-risk SKUs, say so plainly. If the question is about a burn "
        "rate, a trend, or when something started falling, call recall_sku_history for that "
        "SKU first — you have a persistent per-SKU memory of every earlier day in this "
        "operation, and answering a 'how fast is this dropping' question from today's "
        "snapshot alone is wrong. Cite the recalled days explicitly when you use them. "
        "Reordering itself (choosing a vendor, placing the order) is the Supply Chain "
        "Resiliency Agent's job — you flag what needs reordering, you don't place orders."
    ),
    tools=[FunctionTool(get_inventory_par_levels), FunctionTool(recall_sku_history)],
)
