"""What an anonymous caller may see on the public feeds. These tests are the enforcement
mechanism for the rule in services/redaction.py's docstring: aggregates stay, per-employee
rows go."""

from __future__ import annotations

from services.redaction import redact_agent_detail, redact_overview


def overview_payload() -> dict:
    return {
        "as_of": "2026-08-23",
        "fleet": [{"agent_name": "hr_agent", "status": "active"}],
        "shift": {
            "records": [
                {"staff_id": "ic-01", "name": "Nurse IC-01", "risk_level": "critical"},
                {"staff_id": "ic-02", "name": "Nurse IC-02", "risk_level": "safe"},
            ],
            "unit_summary": {"ICU": {"safe": 1, "elevated": 0, "critical": 1}},
        },
        "hr": {
            "records": [
                {"staff_id": "ge-03", "name": "Nurse GE-03", "credential_status": "expired"}
            ],
            "unit_summary": {"General Ward": {"expired": 1}},
        },
        "guest_doctor_hours": [{"staff_id": "pd-er-00", "name": "Per-Diem ER-00", "hours": 40.0}],
        "inventory": {"records": [{"sku": "GLV-002"}], "category_summary": {"PPE": {"low": 1}}},
        "supply": {"decisions": [{"sku": "GLV-002", "quantity": 100}]},
        "armor_events": [{"matched_filters": ["pi_and_jailbreak"]}],
        # Both of these carry staff identity in ways the structured-list redaction misses, and
        # the fixture omitted them entirely — which made the repr() scan below pass vacuously
        # while named staff were live on the public feed. That is the bug this module exists to
        # prevent, one layer down.
        "autonomous_actions": [
            {
                "id": "a1",
                "trigger_kind": "fatigue_breach",
                "subject": "ICU",
                "agent_name": "shift_allocation_agent",
                "status": "completed",
                "summary": "ICU critical-fatigue staff rose from 0 to 4.",
                "prompt": "Automated fatigue watch: the ICU unit's count has risen from 0 to 4.",
                "response": "Nurse IC-01 is at 48 trailing hours; reassign to Per-Diem ER-00.",
            }
        ],
        "approvals": [
            {
                "task_type": "contact_vendor_for_reorder",
                "status": "pending",
                "recipient_label": "MedSupply Primary",
                "subject": "Reorder request: 400 units of Nitrile exam gloves",
            },
            {
                "task_type": "notify_staff_reallocation",
                "status": "pending",
                "recipient_label": "Nurse IC-01 (ICU)",
                "subject": "Shift reallocation: Nurse IC-01 to ER on 2026-08-24",
            },
        ],
        "chaos_experiments": [
            {
                "experiment_type": "hospital_whatif",
                "summary": "5 additional patients into ICU over 2 days",
                "result": {
                    "unit": "ICU",
                    "additional_patients": 5,
                    "would_need_expedited_reorder": False,
                    "staffing_projection": [
                        {"name": "Nurse IC-01", "projected_burndown": 1.4},
                        {"name": "Nurse IC-02", "projected_burndown": 1.2},
                    ],
                    "staff_needing_escalation": ["Nurse IC-01"],
                },
            }
        ],
    }


class TestAuthenticatedView:
    def test_authenticated_payload_is_returned_untouched(self):
        payload = overview_payload()
        assert redact_overview(payload, authenticated=True) is payload

    def test_authenticated_agent_detail_is_returned_untouched(self):
        payload = {"live_state": {"shift": {"records": [{"name": "Nurse"}]}}}
        assert redact_agent_detail(payload, authenticated=True) is payload


class TestPublicView:
    def test_staff_rows_are_withheld(self):
        public = redact_overview(overview_payload(), authenticated=False)
        assert public["shift"]["records"] == []
        assert public["hr"]["records"] == []
        assert public["guest_doctor_hours"] == []

    def test_no_staff_name_survives_anywhere_in_the_payload(self):
        # The blunt check that matters: serialize the whole public payload and confirm no
        # individual's name appears in it, however nested — including inside free text an
        # agent wrote and inside an approval's recipient label.
        public = redact_overview(overview_payload(), authenticated=False)
        blob = repr(public)
        for name in ("Nurse IC-01", "Nurse IC-02", "Nurse GE-03", "Per-Diem ER-00"):
            assert name not in blob, f"{name} leaked onto the public payload"

    def test_agent_prose_is_withheld_but_the_summary_survives(self):
        # The summary is generated from aggregates, never from a roster row, so the autonomous
        # feed still reads correctly when signed out — that is the whole point of redacting
        # the prose rather than dropping the action.
        public = redact_overview(overview_payload(), authenticated=False)
        action = public["autonomous_actions"][0]
        assert action["response"] == ""
        assert action["prompt"] == ""
        assert action["summary"] == "ICU critical-fatigue staff rose from 0 to 4."
        assert action["_redacted"]["fields"] == ["response", "prompt"]

    def test_staff_recipient_is_generic_but_vendor_recipient_is_kept(self):
        public = redact_overview(overview_payload(), authenticated=False)
        by_task = {a["task_type"]: a for a in public["approvals"]}
        assert by_task["notify_staff_reallocation"]["recipient_label"] == "A staff member"
        assert by_task["contact_vendor_for_reorder"]["recipient_label"] == "MedSupply Primary"

    def test_staff_approval_subject_is_genericised(self):
        # Redacting recipient_label and leaving subject would look complete and would not be —
        # the subject line names the person too.
        public = redact_overview(overview_payload(), authenticated=False)
        by_task = {a["task_type"]: a for a in public["approvals"]}
        assert by_task["notify_staff_reallocation"]["subject"] == (
            "Shift reallocation for a staff member"
        )
        # The vendor one describes goods, not a person, and stays intact.
        assert "Nitrile" in by_task["contact_vendor_for_reorder"]["subject"]

    def test_chaos_results_drop_staff_rows_but_keep_the_projection(self):
        public = redact_overview(overview_payload(), authenticated=False)
        result = public["chaos_experiments"][0]["result"]
        assert result["staffing_projection"] == []
        assert result["staff_needing_escalation"] == []
        assert result["_redacted"]["staffing_projection"]["withheld_count"] == 2
        # The aggregate half of the experiment is what the replay panel renders.
        assert result["unit"] == "ICU"
        assert result["additional_patients"] == 5

    def test_aggregates_are_preserved(self):
        # The fleet story is told with aggregates — redaction must not cost the demo anything.
        public = redact_overview(overview_payload(), authenticated=False)
        assert public["shift"]["unit_summary"]["ICU"]["critical"] == 1
        assert public["hr"]["unit_summary"]["General Ward"]["expired"] == 1
        assert public["inventory"]["category_summary"]["PPE"]["low"] == 1

    def test_non_staff_sections_are_untouched(self):
        public = redact_overview(overview_payload(), authenticated=False)
        assert public["supply"]["decisions"][0]["sku"] == "GLV-002"
        assert public["armor_events"][0]["matched_filters"] == ["pi_and_jailbreak"]
        assert public["fleet"][0]["agent_name"] == "hr_agent"

    def test_withheld_count_is_reported(self):
        public = redact_overview(overview_payload(), authenticated=False)
        assert public["shift"]["_redacted"]["records"]["withheld_count"] == 2
        assert public["hr"]["_redacted"]["records"]["withheld_count"] == 1

    def test_public_view_is_flagged(self):
        public = redact_overview(overview_payload(), authenticated=False)
        assert public["_public_view"] is True

    def test_agent_detail_also_redacts_prose_and_recipients(self):
        payload = {
            "agent": {"agent_name": "shift_allocation_agent"},
            "live_state": {"shift": {"records": [{"name": "Nurse IC-01"}]}},
            "autonomous_actions": [{"response": "Nurse IC-01 is over hours.", "summary": "ok"}],
            "approvals": [
                {"task_type": "notify_staff_reallocation", "recipient_label": "Nurse IC-01 (ICU)"}
            ],
        }
        public = redact_agent_detail(payload, authenticated=False)
        assert "Nurse IC-01" not in repr(public)

    def test_original_payload_is_not_mutated(self):
        # The deep-copy guarantee: an anonymous request must not poison a cached payload for
        # the next authenticated one.
        payload = overview_payload()
        redact_overview(payload, authenticated=False)
        assert len(payload["shift"]["records"]) == 2
        assert len(payload["guest_doctor_hours"]) == 1
        assert payload["autonomous_actions"][0]["response"].startswith("Nurse IC-01")
        assert payload["approvals"][1]["recipient_label"] == "Nurse IC-01 (ICU)"


class TestAgentDetailPublicView:
    def test_nested_live_state_is_redacted(self):
        payload = {
            "agent": {"agent_name": "shift_allocation_agent"},
            "live_state": {
                "shift": {
                    "records": [{"name": "Nurse IC-01"}],
                    "unit_summary": {"ICU": {"critical": 1}},
                }
            },
        }
        public = redact_agent_detail(payload, authenticated=False)
        assert public["live_state"]["shift"]["records"] == []
        assert public["live_state"]["shift"]["unit_summary"]["ICU"]["critical"] == 1

    def test_agent_without_staff_state_is_unaffected(self):
        payload = {
            "agent": {"agent_name": "medical_representative_agent"},
            "live_state": {"armor_events": [{"matched_filters": ["pi_and_jailbreak"]}]},
        }
        public = redact_agent_detail(payload, authenticated=False)
        assert public["live_state"]["armor_events"][0]["matched_filters"] == ["pi_and_jailbreak"]

    def test_missing_live_state_does_not_crash(self):
        assert redact_agent_detail({"agent": {}}, authenticated=False)["_public_view"] is True

    def test_activity_log_summary_is_genericised_for_staff_directed_tool_calls(self):
        # The gap this closes: activity_log entries carry the identical subject string as the
        # approvals list (both come from services/platform/approvals.py's `subject`), but only
        # `approvals[].subject` was ever redacted — a signed-out caller could read the staff
        # member's name straight off activity_log instead.
        payload = {
            "agent": {"agent_name": "hr_agent"},
            "activity_log": [
                {
                    "id": "e1",
                    "tool_name": "notify_staff_credential_escalation",
                    "summary": "Credential/escalation notice for Nurse IC-01",
                },
                {
                    "id": "e2",
                    "tool_name": "contact_vendor_for_reorder",
                    "summary": "Reorder request: 400 units of Nitrile exam gloves",
                },
            ],
        }
        public = redact_agent_detail(payload, authenticated=False)
        by_id = {e["id"]: e for e in public["activity_log"]}
        assert by_id["e1"]["summary"] == "Credential escalation for a staff member"
        assert "Nitrile" in by_id["e2"]["summary"]
        assert public["_redacted"]["activity_log"]["withheld_count"] == 1
        assert "Nurse IC-01" not in repr(public)

    def test_activity_log_authenticated_is_untouched(self):
        payload = {
            "activity_log": [
                {"tool_name": "notify_staff_credential_escalation", "summary": "Nurse IC-01"}
            ]
        }
        assert redact_agent_detail(payload, authenticated=True) is payload


class TestMalformedPayloads:
    def test_missing_section_is_skipped(self):
        assert redact_overview({"as_of": "2026-08-23"}, authenticated=False)["_public_view"]

    def test_non_list_at_a_redacted_path_is_left_alone(self):
        payload = {"shift": {"records": "unexpected"}}
        assert redact_overview(payload, authenticated=False)["shift"]["records"] == "unexpected"

    def test_non_dict_parent_is_skipped(self):
        payload = {"shift": "unexpected"}
        assert redact_overview(payload, authenticated=False)["shift"] == "unexpected"
