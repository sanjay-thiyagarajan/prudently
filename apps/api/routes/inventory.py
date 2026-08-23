"""Inventory movement history + purchase-order lifecycle — public reads (same treatment as
the existing Inventory/Supply Chain panels via /dashboard/overview, operational data, not
compensation or manager-config data), auth-gated writes for the two consequential state
transitions (receive, invoice), mirroring routes/policy.py's write-gating pattern."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from google.cloud import firestore

from services.auth import require_firebase_auth
from services.state import (
    adjust_inventory_stock,
    get_inventory_transactions,
    get_purchase_order,
    get_purchase_orders,
    update_purchase_order,
    write_inventory_transaction,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/transactions")
def list_transactions(sku: str | None = None) -> list[dict]:
    return get_inventory_transactions(sku=sku)


@router.get("/purchase-orders")
def list_purchase_orders(vendor_id: str | None = None) -> list[dict]:
    orders = get_purchase_orders()
    if vendor_id is not None:
        orders = [po for po in orders if po.get("vendor_id") == vendor_id]
    return orders


@router.get("/purchase-orders/{po_id}")
def get_purchase_order_detail(po_id: str) -> dict:
    po = get_purchase_order(po_id)
    return po if po is not None else {"error": "not_found"}


@router.post("/purchase-orders/{po_id}/receive")
def receive_purchase_order(po_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """Adds the ordered quantity back onto the SKU's current_stock via the same transactional
    helper the sim clock's consumption tick uses, and writes a real 'receipt' transaction —
    the counterpart entry to the daily 'consumption' entries in the movement audit trail."""
    po = get_purchase_order(po_id)
    if po is None:
        return {"error": "not_found"}
    if po.get("status") != "ordered":
        return {"error": "not_ordered", **po}

    before, after = adjust_inventory_stock(po["sku"], po["quantity"])
    write_inventory_transaction(
        sku=po["sku"],
        item_name=po["item_name"],
        tx_type="receipt",
        quantity_delta=po["quantity"],
        stock_before=before,
        stock_after=after,
        source="purchase_order_received",
    )
    update_purchase_order(po_id, {"status": "received", "received_at": firestore.SERVER_TIMESTAMP})
    return get_purchase_order(po_id)


@router.post("/purchase-orders/{po_id}/invoice")
def invoice_purchase_order(po_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """Idempotent, same "already decided" shape as routes/payroll.py's mark_paid."""
    po = get_purchase_order(po_id)
    if po is None:
        return {"error": "not_found"}
    if po.get("status") == "invoiced":
        return po
    if po.get("status") != "received":
        return {"error": "must_be_received_first", **po}

    update_purchase_order(po_id, {"status": "invoiced", "invoiced_at": firestore.SERVER_TIMESTAMP})
    return get_purchase_order(po_id)
