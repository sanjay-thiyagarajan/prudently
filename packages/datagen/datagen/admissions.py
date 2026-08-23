"""Scripted flu-outbreak surge: a deterministic daily admissions time series, generated once at
seed time and displayed as static history on the Admissions page — not replayed or advanced by
anything at runtime. (Earlier versions of this project had a "simulation clock" that replayed
this series at compressed speed to fit weeks of activity into a short demo; that clock has since
been removed in favor of the fleet watch acting on live state directly — see AGENTS.md's
"De-simulation" section. This admissions curve is the one piece of that scripted-timeline
design left as-is: reframing it as live ingestion is out of scope for that change.)"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta

TIMELINE_DAYS = 21  # simulated days: baseline -> surge onset -> peak -> decline
SURGE_START_DAY = 8
SURGE_PEAK_DAY = 14
SURGE_END_DAY = 20
SURGE_PEAK_MULTIPLIER = 3.2  # admissions at peak vs. baseline

BASELINE_DAILY_ADMISSIONS = {
    "ER": 18,
    "ICU": 4,
    "General Ward": 9,
}


@dataclass(frozen=True)
class AdmissionsDay:
    sim_day: int
    calendar_date: str
    unit: str
    admissions: int
    surge_multiplier: float


def _surge_multiplier(sim_day: int) -> float:
    """Bell-curve-shaped ramp: 1.0 outside the surge window, peaking at
    SURGE_PEAK_MULTIPLIER on SURGE_PEAK_DAY."""
    if sim_day < SURGE_START_DAY or sim_day > SURGE_END_DAY:
        return 1.0
    spread = (SURGE_END_DAY - SURGE_START_DAY) / 2
    center = SURGE_PEAK_DAY
    bell = math.exp(-((sim_day - center) ** 2) / (2 * (spread / 2) ** 2))
    return 1.0 + (SURGE_PEAK_MULTIPLIER - 1.0) * bell


def generate_admissions(seed: int, start_date: date | None = None) -> list[AdmissionsDay]:
    rng = random.Random(seed)
    start_date = start_date or date.today()

    records: list[AdmissionsDay] = []
    for sim_day in range(TIMELINE_DAYS):
        calendar_date = start_date + timedelta(days=sim_day)
        multiplier = _surge_multiplier(sim_day)
        for unit, baseline in BASELINE_DAILY_ADMISSIONS.items():
            # ER/ICU absorb more of the surge than General Ward, matching a real flu wave.
            unit_multiplier = multiplier if unit != "General Ward" else 1.0 + (multiplier - 1.0) * 0.4
            noise = rng.uniform(0.85, 1.15)
            admissions = max(0, round(baseline * unit_multiplier * noise))
            records.append(
                AdmissionsDay(
                    sim_day=sim_day,
                    calendar_date=calendar_date.isoformat(),
                    unit=unit,
                    admissions=admissions,
                    surge_multiplier=round(unit_multiplier, 3),
                )
            )

    return records


def as_dicts(records: list[AdmissionsDay]) -> list[dict]:
    return [asdict(r) for r in records]
