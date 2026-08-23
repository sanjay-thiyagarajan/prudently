import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.inventory_sim import compute_daily_consumption_delta


def test_compute_daily_consumption_delta_is_negative():
    delta = compute_daily_consumption_delta(
        baseline_daily_consumption=12, sim_seed=42, sku="N95-001", day=3
    )
    assert delta < 0


def test_compute_daily_consumption_delta_is_deterministic():
    args = dict(baseline_daily_consumption=12, sim_seed=42, sku="N95-001", day=3)
    assert compute_daily_consumption_delta(**args) == compute_daily_consumption_delta(**args)


def test_compute_daily_consumption_delta_varies_by_sku_and_day():
    base = compute_daily_consumption_delta(
        baseline_daily_consumption=12, sim_seed=42, sku="N95-001", day=3
    )
    other_sku = compute_daily_consumption_delta(
        baseline_daily_consumption=12, sim_seed=42, sku="GLV-002", day=3
    )
    other_day = compute_daily_consumption_delta(
        baseline_daily_consumption=12, sim_seed=42, sku="N95-001", day=4
    )
    assert base != other_sku or base != other_day


def test_compute_daily_consumption_delta_stays_within_noise_band():
    delta = compute_daily_consumption_delta(
        baseline_daily_consumption=40, sim_seed=42, sku="IVF-003", day=10
    )
    assert -46 <= delta <= -34  # baseline 40 +-15%
