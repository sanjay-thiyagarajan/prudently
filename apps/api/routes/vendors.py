"""Vendor directory — auth-gated (docs/threat-model.md finding 2), same rationale as
routes/inventory.py: was public with no reason beyond precedent drift from the judge-facing
overview, which already shows vendor names via reorder decisions without needing this route
open too."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from services.auth import require_firebase_auth
from services.state import get_vendors

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/")
def list_vendors(_uid: str = Depends(require_firebase_auth)) -> list[dict]:
    return get_vendors()
