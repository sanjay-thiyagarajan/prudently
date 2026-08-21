"""Supply Chain Resiliency Agent — specialist agent (invoked as an AgentTool by the
Coordinator, Day 5). Strategic vendor/reorder decisions over live Firestore inventory +
vendor state; the underlying reorder-quantity, stock-status, and alternate-vendor math lives
in reorder.py and is fully unit-tested independently of the LLM. Escalates to the Medical
Representative agent via genuine Agent2Agent (Day 5) when a vendor needs to be contacted
directly — that wiring lands with the A2A day, not here."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.state import get_inventory, get_vendors

from .reorder import compute_reorders, vendor_summary

bootstrap_gemini_credentials()


def get_reorder_recommendations() -> dict:
    """Returns reorder decisions for every SKU that is 'low' or 'critical' on stock, plus a
    per-vendor order-load summary. Use this before recommending any reorder or vendor
    contact — it tells you the quantity to order, which vendor to use, whether the primary
    vendor's lead time is fast enough to beat a stockout, and which alternate vendor to
    contact in parallel if not."""
    items = get_inventory()
    vendors = get_vendors()
    decisions = compute_reorders(items, vendors)
    return {
        "reorder_decisions": decisions,
        "vendor_summary": vendor_summary(decisions),
    }


root_agent = Agent(
    model=get_settings().model_fast,
    name="supply_chain_resiliency_agent",
    description=(
        "Decides hospital supply reorder quantities and vendor selection, flagging when "
        "the primary vendor's lead time won't beat an impending stockout."
    ),
    instruction=(
        "You are the Supply Chain Resiliency Agent for a hospital's Fortified Enterprise "
        "Fleet. Call get_reorder_recommendations to see current reorder decisions across all "
        "SKUs needing action. Prioritize 'expedited' urgency over 'routine'. Be concrete: "
        "name the SKU, the quantity to order, and the vendor. If will_stock_out_before_"
        "delivery is true, explicitly call out the alternate vendor to contact in parallel. "
        "Never invent a reorder for a SKU not returned by the tool — if nothing needs "
        "reordering, say so plainly. Flagging which SKUs need reordering in the first place "
        "is the Inventory Management Agent's job — you decide quantity and vendor, you don't "
        "re-derive stock status."
    ),
    tools=[FunctionTool(get_reorder_recommendations)],
)
