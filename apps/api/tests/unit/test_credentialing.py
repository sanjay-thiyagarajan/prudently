import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.hr.credentialing import (
    compliance_summary,
    compute_credential_status,
    guest_doctor_hours_summary,
    perdiem_coverage_for_unit,
)

TODAY = date(2026, 8, 21)


def staff_member(
    staff_id: str,
    credential_expiry: str,
    unit: str = "ER",
    role: str = "nurse",
    is_per_diem: bool = False,
    name: str | None = None,
) -> dict:
    return {
        "staff_id": staff_id,
        "name": name or f"Staff {staff_id}",
        "role": role,
        "unit": unit,
        "safe_weekly_hours": 40.0,
        "credential_expiry": credential_expiry,
        "is_per_diem": is_per_diem,
    }


def test_credential_far_in_future_is_valid():
    records = compute_credential_status([staff_member("a", "2027-01-01")], TODAY)
    assert records[0]["credential_status"] == "valid"


def test_credential_within_30_days_is_expiring_soon():
    records = compute_credential_status([staff_member("a", "2026-09-10")], TODAY)
    assert records[0]["credential_status"] == "expiring_soon"
    assert records[0]["days_until_expiry"] == 20


def test_credential_exactly_30_days_out_is_expiring_soon():
    records = compute_credential_status([staff_member("a", "2026-09-20")], TODAY)
    assert records[0]["days_until_expiry"] == 30
    assert records[0]["credential_status"] == "expiring_soon"


def test_credential_31_days_out_is_valid():
    records = compute_credential_status([staff_member("a", "2026-09-21")], TODAY)
    assert records[0]["days_until_expiry"] == 31
    assert records[0]["credential_status"] == "valid"


def test_credential_in_past_is_expired():
    records = compute_credential_status([staff_member("a", "2026-08-01")], TODAY)
    assert records[0]["credential_status"] == "expired"
    assert records[0]["days_until_expiry"] == -20


def test_credential_expiring_today_is_expiring_soon_not_expired():
    records = compute_credential_status([staff_member("a", "2026-08-21")], TODAY)
    assert records[0]["days_until_expiry"] == 0
    assert records[0]["credential_status"] == "expiring_soon"


def test_records_sorted_most_urgent_first():
    records = compute_credential_status(
        [
            staff_member("valid", "2027-01-01"),
            staff_member("expired", "2026-01-01"),
            staff_member("soon", "2026-09-01"),
        ],
        TODAY,
    )
    assert [r["staff_id"] for r in records] == ["expired", "soon", "valid"]


def test_compliance_summary_aggregates_by_unit():
    records = compute_credential_status(
        [
            staff_member("a", "2027-01-01", unit="ER"),
            staff_member("b", "2026-01-01", unit="ER"),
            staff_member("c", "2027-01-01", unit="ICU"),
        ],
        TODAY,
    )
    summary = compliance_summary(records)
    assert summary["ER"]["valid"] == 1
    assert summary["ER"]["expired"] == 1
    assert summary["ICU"]["valid"] == 1


def test_perdiem_coverage_excludes_non_perdiem_staff():
    staff = [staff_member("a", "2027-01-01", unit="ER", is_per_diem=False)]
    assert perdiem_coverage_for_unit(staff, "ER", TODAY) == []


def test_perdiem_coverage_excludes_other_units():
    staff = [staff_member("pd-a", "2027-01-01", unit="ICU", is_per_diem=True)]
    assert perdiem_coverage_for_unit(staff, "ER", TODAY) == []


def test_perdiem_coverage_excludes_expired_credentials():
    staff = [staff_member("pd-a", "2026-01-01", unit="ER", is_per_diem=True)]
    assert perdiem_coverage_for_unit(staff, "ER", TODAY) == []


def test_perdiem_coverage_includes_expiring_soon_as_eligible():
    staff = [staff_member("pd-a", "2026-09-01", unit="ER", is_per_diem=True)]
    eligible = perdiem_coverage_for_unit(staff, "ER", TODAY)
    assert len(eligible) == 1
    assert eligible[0]["credential_status"] == "expiring_soon"


def test_perdiem_coverage_returns_eligible_compliant_staff():
    staff = [
        staff_member("pd-a", "2027-01-01", unit="ER", is_per_diem=True, name="Per-Diem A"),
        staff_member("pd-b", "2026-01-01", unit="ER", is_per_diem=True, name="Per-Diem B"),
        staff_member("er-00", "2027-01-01", unit="ER", is_per_diem=False),
    ]
    eligible = perdiem_coverage_for_unit(staff, "ER", TODAY)
    assert [e["staff_id"] for e in eligible] == ["pd-a"]


def shift(staff_id: str, shift_date: str, hours: float, unit: str = "ER") -> dict:
    return {"staff_id": staff_id, "shift_date": shift_date, "hours": hours, "unit": unit}


def test_guest_doctor_hours_excludes_non_perdiem_staff():
    staff = [staff_member("er-00", "2027-01-01", is_per_diem=False)]
    shifts = [shift("er-00", "2026-08-15", 8)]
    assert guest_doctor_hours_summary(staff, shifts, as_of=TODAY) == []


def test_guest_doctor_hours_sums_within_trailing_window():
    staff = [staff_member("pd-a", "2027-01-01", is_per_diem=True, name="Per-Diem A")]
    shifts = [
        shift("pd-a", "2026-08-15", 8),  # 6 days ago, in window
        shift("pd-a", "2026-08-10", 8),  # 11 days ago, in window
        shift("pd-a", "2026-07-01", 8),  # >28 days ago, excluded
    ]
    summary = guest_doctor_hours_summary(staff, shifts, as_of=TODAY, window_days=28)
    assert summary == [
        {"staff_id": "pd-a", "name": "Per-Diem A", "unit": "ER", "role": "nurse", "hours": 16}
    ]


def test_guest_doctor_hours_zero_when_no_shifts():
    staff = [staff_member("pd-a", "2027-01-01", is_per_diem=True)]
    summary = guest_doctor_hours_summary(staff, [], as_of=TODAY)
    assert summary[0]["hours"] == 0


def test_guest_doctor_hours_ignores_other_staff_shifts():
    staff = [
        staff_member("pd-a", "2027-01-01", is_per_diem=True),
        staff_member("er-00", "2027-01-01", is_per_diem=False),
    ]
    shifts = [shift("er-00", "2026-08-15", 8)]
    summary = guest_doctor_hours_summary(staff, shifts, as_of=TODAY)
    assert summary[0]["hours"] == 0
