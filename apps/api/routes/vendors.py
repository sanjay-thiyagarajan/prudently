"""Vendor directory — public, same rationale as routes/inventory.py: vendor names are
already shown on the public Supply Chain panel via reorder decisions, this just gives the
raw vendor list its own page."""

from __future__ import annotations

from fastapi import APIRouter

from services.state import get_vendors

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/")
def list_vendors() -> list[dict]:
    return get_vendors()
