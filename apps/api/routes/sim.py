"""Simulation clock control — start/pause/reset/status, plus the sim-day-boundary memory
writes that give agents a narrative timeline to reason over (see services/memory.py)."""

import asyncio
from datetime import date

from fastapi import APIRouter

from agents.shift.burndown import compute_burndown, unit_summary
from services.memory import write_fact
from services.simclock import SimClock, SimClockRunner
from services.state import get_shift_history, get_staff_roster

router = APIRouter(prefix="/sim", tags=["simulation"])


def _on_sim_tick(day: int) -> None:
    # SimClockRunner._run() calls on_tick synchronously from within its own coroutine, which
    # is already on the running event loop — asyncio.create_task is the correct way to fire
    # off the async memory write without blocking the tick loop on it.
    asyncio.create_task(_write_sim_day_memory(day))


async def _write_sim_day_memory(day: int) -> None:
    staff = get_staff_roster()
    shifts = get_shift_history()
    records = compute_burndown(staff, shifts, as_of=date.today())
    summary = unit_summary(records)
    for unit, counts in summary.items():
        fact = (
            f"sim_day {day}: {unit} burndown — "
            f"{counts['safe']} safe, {counts['elevated']} elevated, {counts['critical']} critical."
        )
        await write_fact(
            app_name="shift_allocation_agent", user_id=unit, fact=fact, author="sim_clock"
        )


_clock = SimClock()
_runner = SimClockRunner(clock=_clock, on_tick=_on_sim_tick)


@router.get("/status")
def status() -> dict:
    return {
        "sim_day": _clock.state.sim_day,
        "running": _clock.state.running,
        "speedup": _clock.state.speedup,
        "timeline_days": _clock.state.timeline_days,
        "finished": _clock.finished,
    }


@router.post("/start")
async def start() -> dict:
    # async def, not def: SimClockRunner.start() calls asyncio.create_task(), which
    # requires a running event loop. FastAPI runs `def` handlers in a worker thread pool
    # (no loop there) but runs `async def` handlers directly on the event loop.
    _runner.start()
    return status()


@router.post("/pause")
async def pause() -> dict:
    _runner.pause()
    return status()


@router.post("/reset")
async def reset() -> dict:
    _runner.reset()
    return status()
