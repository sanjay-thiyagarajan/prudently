"""Inventory Management Agent — specialist agent (invoked as an AgentTool by the Coordinator,
Day 5). Reasons over live Firestore inventory state through the par-levels tool below; the
underlying stock/par-level math lives in par_levels.py and is fully unit-tested independently
of the LLM."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.state import get_inventory

from .par_levels import category_summary, compute_par_levels

bootstrap_gemini_credentials()


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
        "category with no at-risk SKUs, say so plainly. Reordering itself (choosing a "
        "vendor, placing the order) is the Supply Chain Resiliency Agent's job — you flag "
        "what needs reordering, you don't place orders."
    ),
    tools=[FunctionTool(get_inventory_par_levels)],
)
