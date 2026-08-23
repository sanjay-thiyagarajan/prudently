"""Simulation clock control — start/pause/reset/status, plus everything that happens at a
simulated-day boundary: stock depletion, the Memory Bank writes that give agents a narrative
timeline to reason over (services/memory.py), and the autonomous fleet watch that lets the
fleet act on what changed without being asked (services/triggers.py + services/autonomy.py)."""

import asyncio
from datetime import date

from fastapi import APIRouter

from agents.inventory.par_levels import compute_par_levels
from agents.shift.burndown import compute_burndown, unit_summary
from config import get_settings
from services.autonomy import run_triggers
from services.inventory_sim import compute_daily_consumption_delta
from services.memory import write_fact
from services.simclock import SimClock, SimClockRunner
from services.state import (
    adjust_inventory_stock,
    clear_watch_state,
    get_inventory,
    get_shift_history,
    get_staff_roster,
    get_watch_state,
    write_inventory_transaction,
    write_watch_state,
)
from services.triggers import detect_all

router = APIRouter(prefix="/sim", tags=["simulation"])


def _on_sim_tick(day: int) -> None:
    # SimClockRunner._run() calls on_tick synchronously from within its own coroutine, which
    # is already on the running event loop — asyncio.create_task is the correct way to fire
    # off the async day-boundary work without blocking the tick loop on it.
    asyncio.create_task(_advance_day(day))


async def _advance_day(day: int) -> None:
    """Everything a simulated-day boundary means, in strict order.

    The ordering is load-bearing and was previously wrong: depletion and the memory write used
    to be two concurrent tasks, so the fleet watch (added later) could observe either the old
    or the new stock depending on which coroutine won. Deplete first, then observe, then act.
    """
    await _deplete_inventory_for_day(day)
    await _write_sim_day_memory(day)
    await _run_fleet_watch(day)


async def _run_fleet_watch(day: int) -> None:
    """The fleet notices what changed and acts on it, with nobody in the room.

    Wrapped whole in a try/except for the same reason every audit write in this codebase is:
    a watch failure must never stop the clock. A stopped clock is a dead demo; a missed
    trigger is one quiet day.
    """
    try:
        par_records = compute_par_levels(get_inventory())
        burndown = compute_burndown(get_staff_roster(), get_shift_history(), as_of=date.today())
        triggers, next_state = detect_all(
            par_records, unit_summary(burndown), get_watch_state(), day
        )
        write_watch_state(next_state)
        if triggers:
            await run_triggers(triggers, day)
    except Exception:  # pylint: disable=broad-exception-caught
        pass


async def _deplete_inventory_for_day(day: int) -> None:
    """Real stock depletion tied to the sim clock — until this, `current_stock` was a value
    assigned once at seed time and never actually moved during a demo (a SKU's stock was just
    "already low" from a random days-of-supply draw, not genuinely falling). Decrement noise
    is deterministically seeded from sim_seed + sku + day (not plain `random`) so `/sim/reset`
    followed by a replay reproduces identical numbers — the same "deterministic replay for the
    demo video" discipline services/simclock.py's own docstring already establishes for
    `/sim/reset`. Iterates SKUs in a fixed (sorted) order so the sequence of transaction writes
    is reproducible too, not just each SKU's individual delta."""
    sim_seed = get_settings().sim_seed
    items = sorted(get_inventory(), key=lambda item: item["sku"])
    for item in items:
        delta = compute_daily_consumption_delta(
            item["baseline_daily_consumption"], sim_seed, item["sku"], day
        )
        if delta == 0:
            continue
        before, after = adjust_inventory_stock(item["sku"], delta)
        write_inventory_transaction(
            sku=item["sku"],
            item_name=item["name"],
            tx_type="consumption",
            quantity_delta=delta,
            stock_before=before,
            stock_after=after,
            sim_day=day,
        )


async def _write_sim_day_memory(day: int) -> None:
    """Writes the day's facts into each agent's own Memory Bank store, scoped the way that
    agent's recall tool reads them back: Shift per unit, Inventory per SKU.

    Only SKUs that are actually under pressure get a fact. Writing all of them every day would
    make a recall query return 21 near-identical "still fine" lines for a SKU nobody cares
    about, which is worse than no history at all — similarity search would surface those ahead
    of the one day that mattered.
    """
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

    for item in compute_par_levels(get_inventory()):
        if item["stock_status"] == "ok":
            continue
        days_left = item["days_of_supply"]
        fact = (
            f"sim_day {day}: {item['name']} ({item['sku']}) is {item['stock_status']} at "
            f"{item['current_stock']} units against a reorder point of {item['reorder_point']}"
            + (f", ~{days_left} days of supply left." if days_left is not None else ".")
        )
        await write_fact(
            app_name="inventory_management_agent",
            user_id=item["sku"],
            fact=fact,
            author="sim_clock",
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
    # Without this the fleet watch stays silent on a replay: every SKU is already recorded at
    # its breached status, so nothing reads as a *new* crossing and no trigger fires. Resetting
    # the clock has to reset what the fleet remembers seeing, or the demo only works once.
    clear_watch_state()
    return status()


@router.post("/advance")
async def advance() -> dict:
    """Advances exactly one simulated day, immediately, without waiting on the clock.

    Exists for demo recording: at the default speedup a day boundary lands once a minute,
    which is fine for an ambient dashboard and useless when the shot needs the surge to happen
    *now*. Runs the same `_advance_day` the clock would have run, so nothing about the
    resulting state or the triggers it fires is special-cased for the demo path.

    Fires and returns rather than awaiting, exactly like the clock's own tick. Measured, not
    assumed: the first version awaited the day, and a boundary that trips three fatigue
    triggers runs three real agent turns back to back — the request took over two minutes and
    the dashboard's "Next day" button would have sat spinning through all of it. The dashboard
    polls, so the autonomous feed fills in as each turn lands, which is also the better thing
    to watch on camera.
    """
    day = _clock.state.sim_day + 1
    _clock.state.sim_day = day
    asyncio.create_task(_advance_day(day))
    return status()
