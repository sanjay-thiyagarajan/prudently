import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.inventory_sim import compute_consumption_delta

# 90s watch cycle against the module's 3600s (1hr) "consumption day" pacing knob: each cycle
# moves ~1/40th of a SKU's baseline daily consumption.
INTERVAL = 90


def test_compute_consumption_delta_is_never_positive():
    delta = compute_consumption_delta(
        baseline_daily_consumption=12,
        sim_seed=42,
        sku="N95-001",
        cycle=3,
        interval_seconds=INTERVAL,
    )
    assert delta <= 0


def test_compute_consumption_delta_is_deterministic():
    args = dict(
        baseline_daily_consumption=12,
        sim_seed=42,
        sku="N95-001",
        cycle=3,
        interval_seconds=INTERVAL,
    )
    assert compute_consumption_delta(**args) == compute_consumption_delta(**args)


def test_compute_consumption_delta_varies_by_sku_and_cycle():
    base = compute_consumption_delta(
        baseline_daily_consumption=1200,
        sim_seed=42,
        sku="N95-001",
        cycle=3,
        interval_seconds=INTERVAL,
    )
    other_sku = compute_consumption_delta(
        baseline_daily_consumption=1200,
        sim_seed=42,
        sku="GLV-002",
        cycle=3,
        interval_seconds=INTERVAL,
    )
    other_cycle = compute_consumption_delta(
        baseline_daily_consumption=1200,
        sim_seed=42,
        sku="N95-001",
        cycle=4,
        interval_seconds=INTERVAL,
    )
    assert base != other_sku or base != other_cycle


def test_compute_consumption_delta_is_scaled_by_interval_not_full_daily_baseline():
    # The bug this test guards against: applying a full day's consumption on every watch
    # cycle crashed every SKU to zero stock (and fired a real approval email per SKU) within
    # minutes of a fresh deploy. At a 90s interval against a 3600s "consumption day," one
    # cycle must move only a small fraction of the baseline, never the whole thing.
    delta = compute_consumption_delta(
        baseline_daily_consumption=40,
        sim_seed=42,
        sku="IVF-003",
        cycle=10,
        interval_seconds=INTERVAL,
    )
    assert -3 <= delta <= 0


def test_compute_consumption_delta_scales_up_with_a_longer_interval():
    short = compute_consumption_delta(
        baseline_daily_consumption=1200, sim_seed=42, sku="IVF-003", cycle=10, interval_seconds=90
    )
    long_ = compute_consumption_delta(
        baseline_daily_consumption=1200, sim_seed=42, sku="IVF-003", cycle=10, interval_seconds=3600
    )
    assert abs(long_) > abs(short)
