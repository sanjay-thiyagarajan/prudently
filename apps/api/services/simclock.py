"""Simulation clock: advances a simulated hospital timeline (see packages/datagen —
TIMELINE_DAYS=21, scripted flu surge) at a compressed real-time rate, so "weeks of
asynchronous operation" fit inside a demo. Pure tick-advancement logic (SimClock) is kept
separate from the Pub/Sub publish side effect so it's cheaply unit-testable.

SIM_SPEEDUP is simulated-seconds-per-real-second: one simulated day (86400s) advances every
`86400 / SIM_SPEEDUP` real seconds. Default 1440 -> 60 real seconds per simulated day.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Callable

SECONDS_PER_SIM_DAY = 86_400


@dataclass
class ClockState:
    sim_day: int = 0
    running: bool = False
    speedup: int = 1440
    timeline_days: int = 21


class SimClock:
    """Pure, deterministic tick-advancement — no I/O, no asyncio, easy to unit test."""

    def __init__(self, speedup: int = 1440, timeline_days: int = 21):
        self.state = ClockState(speedup=speedup, timeline_days=timeline_days)
        self._real_seconds_per_day = SECONDS_PER_SIM_DAY / speedup
        self._elapsed_real_seconds = 0.0

    @property
    def finished(self) -> bool:
        return self.state.sim_day >= self.state.timeline_days - 1

    def start(self) -> None:
        self.state.running = True

    def pause(self) -> None:
        self.state.running = False

    def reset(self) -> None:
        self.state.sim_day = 0
        self.state.running = False
        self._elapsed_real_seconds = 0.0

    def set_speedup(self, speedup: int) -> None:
        if speedup <= 0:
            raise ValueError("speedup must be positive")
        self.state.speedup = speedup
        self._real_seconds_per_day = SECONDS_PER_SIM_DAY / speedup

    def advance(self, real_seconds_elapsed: float) -> list[int]:
        """Advance the clock by `real_seconds_elapsed` of wall-clock time. Returns the list
        of new sim_day values crossed (usually 0 or 1 entries, more if speedup is extreme
        relative to the poll interval)."""
        if not self.state.running or self.finished:
            return []

        self._elapsed_real_seconds += real_seconds_elapsed
        crossed: list[int] = []
        while self._elapsed_real_seconds >= self._real_seconds_per_day and not self.finished:
            self._elapsed_real_seconds -= self._real_seconds_per_day
            self.state.sim_day += 1
            crossed.append(self.state.sim_day)
            if self.finished:
                self.state.running = False
                break

        return crossed


class SimClockRunner:
    """Wires SimClock to a wall-clock poll loop and a tick-published side effect
    (Pub/Sub in production, a no-op/log in DRY_RUN or tests)."""

    def __init__(self, clock: SimClock, on_tick: Callable[[int], None], poll_interval: float = 1.0):
        self.clock = clock
        self.on_tick = on_tick
        self.poll_interval = poll_interval
        self._task: asyncio.Task | None = None

    async def _run(self) -> None:  # pragma: no cover — asyncio poll loop, thin glue over
        last = time.monotonic()  # the fully-tested SimClock.advance(); see test_simclock.py
        while True:
            await asyncio.sleep(self.poll_interval)
            now = time.monotonic()
            elapsed = now - last
            last = now
            for sim_day in self.clock.advance(elapsed):
                self.on_tick(sim_day)
            if self.clock.finished:
                break

    def start(self) -> None:  # pragma: no cover — asyncio.create_task glue
        self.clock.start()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    def pause(self) -> None:
        self.clock.pause()

    def reset(self) -> None:  # pragma: no cover — asyncio.Task cancellation glue
        self.clock.reset()
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
