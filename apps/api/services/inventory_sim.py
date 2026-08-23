"""Pure logic for the sim clock's daily inventory depletion — kept separate from
routes/sim.py so the decrement math is independently unit-tested, matching this project's
services/payroll.py / agents/*/*.py pure-logic-module convention."""

from __future__ import annotations

import random


def compute_daily_consumption_delta(
    baseline_daily_consumption: int, sim_seed: int, sku: str, day: int
) -> int:
    """Deterministic (sim_seed, sku, day)-seeded consumption for one sim-day tick — never
    plain `random`, so `/sim/reset` followed by a replay reproduces identical numbers (this
    project's existing "deterministic replay for the demo video" discipline). Returns a
    negative delta (stock going down), +-15% noise around the SKU's baseline."""
    rng = random.Random(f"{sim_seed}-{sku}-{day}")
    noise = rng.uniform(0.85, 1.15)
    return -round(baseline_daily_consumption * noise)
