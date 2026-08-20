import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.simclock import SECONDS_PER_SIM_DAY, SimClock


def test_advance_not_running_does_nothing():
    clock = SimClock(speedup=1440, timeline_days=21)
    assert clock.advance(1000) == []
    assert clock.state.sim_day == 0


def test_advance_crosses_one_day():
    clock = SimClock(speedup=1440, timeline_days=21)  # 60 real seconds per sim day
    clock.start()
    crossed = clock.advance(60)
    assert crossed == [1]
    assert clock.state.sim_day == 1


def test_advance_crosses_multiple_days_in_one_call():
    clock = SimClock(speedup=1440, timeline_days=21)
    clock.start()
    crossed = clock.advance(185)  # 3 full days + partial
    assert crossed == [1, 2, 3]
    assert clock.state.sim_day == 3


def test_stops_at_timeline_end():
    clock = SimClock(speedup=1440, timeline_days=3)
    clock.start()
    crossed = clock.advance(600)  # far more than needed to finish
    assert crossed == [1, 2]
    assert clock.finished
    assert clock.state.running is False


def test_pause_stops_advancing():
    clock = SimClock(speedup=1440, timeline_days=21)
    clock.start()
    clock.advance(60)
    clock.pause()
    assert clock.advance(1000) == []
    assert clock.state.sim_day == 1


def test_reset_returns_to_day_zero():
    clock = SimClock(speedup=1440, timeline_days=21)
    clock.start()
    clock.advance(120)
    clock.reset()
    assert clock.state.sim_day == 0
    assert clock.state.running is False
    assert clock.advance(60) == []  # reset also stops running


def test_set_speedup_changes_seconds_per_day():
    clock = SimClock(speedup=1440, timeline_days=21)
    clock.set_speedup(2880)
    assert clock._real_seconds_per_day == SECONDS_PER_SIM_DAY / 2880


def test_set_speedup_rejects_non_positive():
    clock = SimClock()
    try:
        clock.set_speedup(0)
        assert False, "expected ValueError"
    except ValueError:
        pass
