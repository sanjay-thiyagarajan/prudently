"""Simulation clock control — start/pause/reset/status. Agent reactions to ticks
(Shift/Supply/Chaos recommendations) land Day 3+; this just exposes the clock itself."""

from fastapi import APIRouter

from services.simclock import SimClock, SimClockRunner

router = APIRouter(prefix="/sim", tags=["simulation"])

_clock = SimClock()
_runner = SimClockRunner(clock=_clock, on_tick=lambda day: print(f"[sim] tick -> sim_day={day}"))


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
