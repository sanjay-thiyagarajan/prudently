"""Background driver for services/fleet_watch.py's run_watch_cycle — the real-time watch loop
that replaces the old sim clock's tick (services/simclock.py, removed). Started from app.py's
lifespan the moment the API process starts; runs fully unprompted, no button required.
POST /watch/check-now (routes/watch.py) fires one extra cycle on demand without disturbing this
loop's own schedule — same "fire and return" shape the old POST /sim/advance used, for the same
reason: a multi-trigger cycle can run several real agent turns back to back and must not make a
caller wait minutes for a response.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from services.fleet_watch import run_watch_cycle

logger = logging.getLogger(__name__)


class WatchLoop:
    def __init__(self, interval_seconds: int):
        self.interval_seconds = interval_seconds
        self.last_checked_at: datetime | None = None
        self.checks_run = 0
        # Cumulative since process start (not reset daily) — a live status strip context, not
        # an audit record; get_autonomous_actions() is the real audit trail.
        self.triggers_fired_total = 0
        self.vendor_messages_screened_total = 0
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Idempotent: safe to call more than once (e.g. across a hot-reload)."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            await self.check_now()
            await asyncio.sleep(self.interval_seconds)

    async def check_now(self) -> dict:
        """Runs one watch cycle immediately, outside the loop's own sleep schedule — used both
        by the loop itself and by POST /watch/check-now."""
        try:
            result = await run_watch_cycle()
        except Exception:  # pylint: disable=broad-exception-caught
            # run_watch_cycle already isolates its own stages; this is a last-resort guard so a
            # truly unexpected failure can't kill the background loop's `while True`.
            logger.exception("Watch cycle failed outright.")
            result = {"triggers_fired": 0}
        self.last_checked_at = datetime.now(timezone.utc)
        self.checks_run += 1
        self.triggers_fired_total += result.get("triggers_fired", 0)
        self.vendor_messages_screened_total += result.get("vendor_messages_screened", 0)
        return result

    @property
    def next_check_at(self) -> datetime | None:
        if self.last_checked_at is None:
            return None
        return self.last_checked_at + timedelta(seconds=self.interval_seconds)


@lru_cache
def get_watch_loop() -> WatchLoop:
    from config import get_settings  # pylint: disable=import-outside-toplevel

    return WatchLoop(interval_seconds=get_settings().watch_interval_seconds)
