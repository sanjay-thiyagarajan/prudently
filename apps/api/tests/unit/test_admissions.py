import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.admissions import recent_daily_trend, unit_totals


def admission(sim_day: int, unit: str, admissions: int) -> dict:
    return {
        "sim_day": sim_day,
        "calendar_date": f"2026-08-{sim_day + 1:02d}",
        "unit": unit,
        "admissions": admissions,
        "surge_multiplier": 1.0,
    }


def test_unit_totals_sums_per_unit_across_all_records():
    records = [
        admission(0, "ER", 10),
        admission(1, "ER", 12),
        admission(0, "ICU", 3),
    ]
    assert unit_totals(records) == [
        {"unit": "ER", "total_admissions": 22},
        {"unit": "ICU", "total_admissions": 3},
    ]


def test_unit_totals_empty_input():
    assert unit_totals([]) == []


def test_recent_daily_trend_keeps_only_the_last_n_days():
    records = [admission(day, "ER", 5) for day in range(20)]
    trend = recent_daily_trend(records, days=3)
    assert sorted({r["sim_day"] for r in trend}) == [17, 18, 19]


def test_recent_daily_trend_sorted_oldest_to_newest():
    records = [admission(2, "ER", 1), admission(0, "ER", 1), admission(1, "ER", 1)]
    trend = recent_daily_trend(records, days=10)
    assert [r["sim_day"] for r in trend] == [0, 1, 2]


def test_recent_daily_trend_fewer_records_than_window():
    records = [admission(0, "ER", 5), admission(1, "ICU", 2)]
    trend = recent_daily_trend(records, days=14)
    assert len(trend) == 2


def test_recent_daily_trend_explicit_fields_only():
    records = [{**admission(0, "ER", 5), "extra_internal_field": "should not leak"}]
    trend = recent_daily_trend(records, days=14)
    assert set(trend[0].keys()) == {"sim_day", "calendar_date", "unit", "admissions"}
