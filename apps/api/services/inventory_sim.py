"""Pure logic for the watch loop's ongoing inventory consumption noise — kept separate from
services/fleet_watch.py so the decrement math is independently unit-tested, matching this
project's services/payroll.py / agents/*/*.py pure-logic-module convention."""

from __future__ import annotations

import random

# A "consumption day" here is an ambient-noise pacing knob, not a sim-clock day: it's how much
# real wall-clock time the noise generator takes to work through one SKU's full
# baseline_daily_consumption. 1 hour keeps a multi-minute demo/judging session showing genuine
# movement without flooding a fast watch-loop interval. This constant replaces a real bug: the
# first version applied a full day's consumption on *every* watch cycle (no scaling at all), so
# at a 90s interval every SKU crashed to critical/zero stock — and `contact_vendor_for_reorder`
# sent a real approval email per SKU — within about five minutes of a fresh deploy, confirmed
# live against the actual deployed service (26 real emails, `email_log` collection).
REAL_SECONDS_PER_CONSUMPTION_DAY = 3600


def compute_consumption_delta(
    baseline_daily_consumption: int,
    sim_seed: int,
    sku: str,
    cycle: int,
    *,
    interval_seconds: int,
) -> int:
    """Deterministic (sim_seed, sku, cycle)-seeded consumption for one watch-loop cycle — never
    plain `random`, so a reset watch state followed by a replay reproduces identical numbers
    (this project's existing "deterministic replay for the demo video" discipline). `cycle` is a
    monotonic counter incremented once per real watch cycle, not a scripted day number — there
    is no fixed-length timeline behind it. Returns a negative delta (stock going down): the
    SKU's baseline daily consumption scaled to `interval_seconds` /
    REAL_SECONDS_PER_CONSUMPTION_DAY of a day, +-15% noise. A low-baseline SKU rounding to a
    0 delta on a given cycle is expected, not a bug — real movement should be occasional and
    granular, not guaranteed every single cycle."""
    rng = random.Random(f"{sim_seed}-{sku}-{cycle}")
    noise = rng.uniform(0.85, 1.15)
    fraction = interval_seconds / REAL_SECONDS_PER_CONSUMPTION_DAY
    return -round(baseline_daily_consumption * noise * fraction)
