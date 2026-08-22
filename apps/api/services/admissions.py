"""Admissions/discharge pure aggregation — projects the raw admissions_timeseries records
(packages/datagen/datagen/admissions.py) into the shapes the dashboard's Admissions panel
renders. Pure, no I/O, matching this project's agents/*/*.py pure-logic-module convention so
the math is independently unit-tested."""

from __future__ import annotations


def unit_totals(records: list[dict]) -> list[dict]:
    """Total admissions per unit across every record passed in."""
    totals: dict[str, int] = {}
    for record in records:
        totals[record["unit"]] = totals.get(record["unit"], 0) + record["admissions"]
    return [{"unit": unit, "total_admissions": total} for unit, total in sorted(totals.items())]


def recent_daily_trend(records: list[dict], days: int = 14) -> list[dict]:
    """The most recent `days` sim-days, one row per (day, unit), sorted oldest to newest so a
    chart can render it directly."""
    sim_days = sorted({record["sim_day"] for record in records})
    cutoff = set(sim_days[-days:] if len(sim_days) > days else sim_days)
    trend = [
        {
            "sim_day": record["sim_day"],
            "calendar_date": record["calendar_date"],
            "unit": record["unit"],
            "admissions": record["admissions"],
        }
        for record in records
        if record["sim_day"] in cutoff
    ]
    trend.sort(key=lambda record: (record["sim_day"], record["unit"]))
    return trend
