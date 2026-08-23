"""Real-time fleet watch status + on-demand check — replaces the old sim clock's
start/pause/reset/status/advance surface (routes/sim.py, removed). The watch runs unprompted on
a background loop (services/watch_loop.py, started from app.py's lifespan) the moment the API
process starts; nothing here starts or stops that loop — POST /watch/check-now only fires one
extra cycle immediately, for demo/judging control, without disturbing the loop's own schedule.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from services.state import clear_watch_state
from services.watch_loop import get_watch_loop

router = APIRouter(prefix="/watch", tags=["fleet-watch"])


@router.get("/status")
def status() -> dict:
    loop = get_watch_loop()
    return {
        "last_checked_at": loop.last_checked_at.isoformat() if loop.last_checked_at else None,
        "next_check_at": loop.next_check_at.isoformat() if loop.next_check_at else None,
        "interval_seconds": loop.interval_seconds,
        "checks_run": loop.checks_run,
        "triggers_fired_total": loop.triggers_fired_total,
    }


@router.post("/check-now")
async def check_now() -> dict:
    """Fires one watch cycle immediately, fire-and-return exactly like the old POST /sim/advance
    — a multi-trigger cycle can run several real agent turns back to back and must not make the
    dashboard's "Run fleet check now" button sit spinning through all of it. The dashboard polls
    GET /watch/status and the activity feed, which fill in as each turn lands."""
    loop = get_watch_loop()
    asyncio.create_task(loop.check_now())
    return {"status": "checking"}


@router.post("/reset")
def reset() -> dict:
    """Internal ops utility, not a dashboard button: clears fleet_watch/state so a freshly
    reseeded baseline re-fires the same triggers instead of finding every SKU/unit/credential
    already recorded at its breached status and staying silent."""
    clear_watch_state()
    return {"status": "reset"}
