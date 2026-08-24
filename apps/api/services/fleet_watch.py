"""Real-time fleet watch — the fleet notices what changed and acts on it, with nobody in the
room. Runs on a background loop (started from app.py's lifespan, once every
WATCH_INTERVAL_SECONDS) plus on demand via POST /watch/check-now (routes/watch.py).

This replaces the old sim-clock day-boundary mechanism (previously routes/sim.py's
_advance_day/_run_fleet_watch/_write_sim_day_memory/_deplete_inventory_for_day). The trigger
detection itself (services/triggers.py) was always a pure state-diff against a persisted
snapshot — it never actually needed a "day number," only *something* to invoke it periodically
with fresh state. This module is that something, running on real wall-clock time instead of a
scripted 21-day timeline.

Four stages, in strict order, each independently isolated (a failure in one is logged and does
not stop the rest) — carried over from a real production incident on the old sim-clock version,
where an unhandled Memory Bank write failure silently killed the entire day-boundary pipeline,
including trigger detection, and no autonomous action ever appeared with no error visible
anywhere an operator would look:

  1. `_load_watch_state`   — read the last-seen snapshot + advance the consumption-noise cycle.
  2. `_apply_consumption_noise` — a little real-time inventory movement (services/inventory_sim
     .py), so a long-running demo keeps seeing new activity instead of a static baseline. Not a
     scripted depletion curve: no day index, no fixed end date.
  3. `_compute_snapshot`   — read live state (par levels, burndown, credential status) *after*
     the noise above, so the fleet reacts to genuinely current numbers.
  4. `_write_memory_facts` and `_detect_and_act` — both depend only on the snapshot from stage 3,
     not on each other, so a Memory Bank outage cannot prevent trigger detection/action (the
     exact failure mode the old version suffered from).
"""

from __future__ import annotations

import logging
from datetime import date

from agents.hr.credentialing import compute_credential_status
from agents.inventory.par_levels import compute_par_levels
from agents.shift.burndown import compute_burndown, unit_summary
from agents.surgical_scheduling.conflicts import detect_conflicts
from config import get_settings
from services.autonomy import run_triggers
from services.inventory_sim import compute_consumption_delta
from services.memory import write_fact
from services.state import (
    adjust_inventory_stock,
    get_inventory,
    get_shift_history,
    get_staff_roster,
    get_surgical_cases,
    get_watch_state,
    write_inventory_transaction,
    write_watch_state,
)
from services.triggers import detect_all

logger = logging.getLogger(__name__)


async def run_watch_cycle() -> dict:
    """One real-time watch cycle. Returns a small status dict the background loop and
    POST /watch/check-now both report back to the caller."""
    ctx: dict = {"triggers_fired": 0}
    for stage in (
        _load_watch_state,
        _apply_consumption_noise,
        _compute_snapshot,
        _write_memory_facts,
        _detect_and_act,
    ):
        try:
            await stage(ctx)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Watch cycle: stage %s failed; continuing.", stage.__name__)
    return {"triggers_fired": ctx["triggers_fired"], "checked_at": ctx.get("as_of")}


async def _load_watch_state(ctx: dict) -> None:
    ctx["watch_state"] = get_watch_state() or {}
    ctx["cycle"] = ctx["watch_state"].get("cycle", 0) + 1
    ctx["as_of"] = date.today().isoformat()


async def _apply_consumption_noise(ctx: dict) -> None:
    """Ongoing, real-time inventory movement — deterministic per (sim_seed, sku, cycle) so it
    stays reproducible for tests, but `cycle` is a monotonic counter advanced once per real
    watch cycle, not a day index into a fixed-length timeline."""
    settings = get_settings()
    items = sorted(get_inventory(), key=lambda item: item["sku"])
    for item in items:
        delta = compute_consumption_delta(
            item["baseline_daily_consumption"],
            settings.sim_seed,
            item["sku"],
            ctx["cycle"],
            interval_seconds=settings.watch_interval_seconds,
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
        )


async def _compute_snapshot(ctx: dict) -> None:
    """Reads live state *after* this cycle's consumption noise, so everything downstream reacts
    to genuinely current numbers rather than what the world looked like before this tick."""
    staff = get_staff_roster()
    shifts = get_shift_history()
    ctx["par_records"] = compute_par_levels(get_inventory())
    burndown = compute_burndown(staff, shifts, as_of=date.today())
    ctx["unit_summary"] = unit_summary(burndown)
    ctx["credential_records"] = compute_credential_status(staff, as_of=date.today())
    ctx["conflicts"] = detect_conflicts(get_surgical_cases(caller="fleet_watch"))


async def _write_memory_facts(ctx: dict) -> None:
    """Writes the current state into each agent's own Memory Bank store, scoped the way that
    agent's recall tool reads it back: Shift per unit, Inventory per SKU.

    Only SKUs actually under pressure get a fact — writing all of them every cycle would make a
    recall query return a wall of near-identical "still fine" lines for a SKU nobody cares
    about, which is worse than no history at all.
    """
    as_of = ctx["as_of"]
    for unit, counts in ctx["unit_summary"].items():
        fact = (
            f"{as_of}: {unit} burndown — "
            f"{counts['safe']} safe, {counts['elevated']} elevated, {counts['critical']} critical."
        )
        await _write_fact_best_effort("shift_allocation_agent", unit, fact)

    for item in ctx["par_records"]:
        if item["stock_status"] == "ok":
            continue
        days_left = item["days_of_supply"]
        fact = (
            f"{as_of}: {item['name']} ({item['sku']}) is {item['stock_status']} at "
            f"{item['current_stock']} units against a reorder point of {item['reorder_point']}"
            + (f", ~{days_left} days of supply left." if days_left is not None else ".")
        )
        await _write_fact_best_effort("inventory_management_agent", item["sku"], fact)


async def _write_fact_best_effort(app_name: str, user_id: str, fact: str) -> None:
    """One failing write must not cost the rest of the cycle's facts."""
    try:
        await write_fact(app_name=app_name, user_id=user_id, fact=fact, author="fleet_watch")
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning("Memory Bank write failed for %s/%s; timeline gap.", app_name, user_id)


async def _detect_and_act(ctx: dict) -> None:
    """No blanket try/except of its own beyond the one run_watch_cycle already wraps every
    stage in: this must not be gated on `_write_memory_facts` succeeding, which is exactly the
    isolation this module's docstring calls out as load-bearing."""
    triggers, next_state = detect_all(
        ctx["par_records"],
        ctx["unit_summary"],
        ctx["credential_records"],
        ctx["watch_state"],
        ctx["as_of"],
        conflicts=ctx["conflicts"],
    )
    next_state["cycle"] = ctx["cycle"]
    write_watch_state(next_state)
    ctx["triggers_fired"] = len(triggers)
    if triggers:
        await run_triggers(triggers)
