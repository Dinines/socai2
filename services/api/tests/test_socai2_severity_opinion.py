"""Direct independent-unit and update guard checks with synthetic values."""
import copy
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.socai2 import ai_stage_delivery, case_c6_delivery, incident_output_adapter
from app.socai2.baseline_context import reference
from app.socai2.severity_opinion import PATH, VERSION
from app.socai2.subject_risk_opinions import decision, manual_stamp
from jsonschema import Draft202012Validator
from socai2_test_severity import opinion


@pytest.fixture
def incident():
    aid, material = str(uuid4()), uuid4()
    prepared = {"severity_opinion_version": VERSION, "member_aliases": {aid: "M1"},
        "source_map": {"S1": {"ref": reference("alert_material", material, "observation", "$.raw_text"), "alert_ids": [aid]}},
        "data": {"omissions": {}, "members": [{"alert_id": aid, "included": 1, "triage_eligible": True}]}}
    body = {"severity_opinion": opinion(["S1"]),
        "diagnosis": {"summary": "Synthetic observation.", "conclusion": "Synthetic review required.",
            "source_ids": ["S1"], "limitations": []},
        "members": [{"alert_ref": "M1", "state": "unresolved", "assessment": "Synthetic member.",
            "source_ids": ["S1"], "limitations": []}], "findings": [], "open_questions": []}
    return prepared, body


def test_generated_schema_and_received_source_span(incident):
    prepared, body = incident
    body["business_verdict"] = "needs_review"
    schema = incident_output_adapter.candidate_schema(prepared)
    Draft202012Validator(schema).validate(body)
    raw = json.dumps(body)
    result = ai_stage_delivery.receive("I", raw, prepared, uuid4())
    assert result["result"] is not None and result["delivery"]["state"] == "complete"
    unit = next(u for u in result["retained_units"] if u["path"] == PATH)
    start, end = unit["value_span"]
    assert json.loads(raw[start:end]) == body["severity_opinion"]
    assert hashlib.sha256(raw[start:end].encode()).hexdigest() == unit["value_sha256"]
    assert unit["resolved_refs"][0]["ref"] == prepared["source_map"]["S1"]["ref"]


@pytest.mark.parametrize("invalid", [None, "invalid_level", "blank_reason", "incomplete_impact"])
def test_missing_or_invalid_unit_keeps_independent_incident_analysis(incident, invalid):
    prepared, body = incident
    if invalid is None:
        body.pop("severity_opinion")
    elif invalid == "invalid_level":
        body["severity_opinion"]["level"] = "unknown"
    elif invalid == "blank_reason":
        body["severity_opinion"]["reason"] = " "
    else:
        body["severity_opinion"]["impact_basis"].pop("potential")
    result = ai_stage_delivery.receive("I", json.dumps(body), prepared, uuid4())
    assert result["result"] is not None
    assert result["delivery"]["state"] == "partial"
    assert not any(u["path"] == PATH for u in result["retained_units"])


def test_incident_truncation_and_bad_citation_keep_complete_unit(incident):
    prepared, body = incident
    body["severity_opinion"]["source_refs"] = ["not_bound"]
    raw = '{"severity_opinion":' + json.dumps(body["severity_opinion"]) + ',"diagnosis":{"summary":"unfinished'
    received = ai_stage_delivery.receive("I", raw, prepared, uuid4(), finish_reason="length")
    unit = next(u for u in received["retained_units"] if u["path"] == PATH)
    assert unit["value"] == body["severity_opinion"]
    assert unit["resolved_refs"] == [] and unit["quality_issues"]
    assert received["result"] is None and received["delivery"]["state"] == "partial"


@pytest.mark.parametrize("ending", ["}", ',"conclusion":{"text":"unfinished'])
def test_c6_independent_grade_does_not_manufacture_result_core(incident, ending):
    prepared, body = incident
    aid = next(iter(prepared["member_aliases"]))
    prepared["case_boundary"] = {"member_aliases": prepared["member_aliases"], "object_aliases": {}}
    context = SimpleNamespace(alerts={aid: {}}, questions=[], scope=SimpleNamespace(object_keys=[]))
    raw = '{"severity_opinion":' + json.dumps(body["severity_opinion"]) + ending
    received = case_c6_delivery.receive(raw, prepared, context, {"state": "initial", "result_id": None}, uuid4(), finish_reason="length")
    assert received["full_delivery"] is None
    assert not received["use"]["adoption_eligible"]
    assert received["retained_output"]["fields"]["severity_opinion"] == body["severity_opinion"]
    assert any(u["path"] == PATH for u in received["retained_units"])


@pytest.fixture
def guard():
    row = {"risk_metadata": {"manual_severity_revision": 0}, "severity": "medium", "severity_source": "member_max"}
    members = {str(uuid4()): str(uuid4())}
    frozen = {"manual_severity_revision": 0, "manual_stamp": manual_stamp(row), "current_level": "medium",
        "scope_revision": 1, "scope_kind": "whole_case", "subject_type": "case", "members": members,
        "selected_members": members.copy()}
    options = {"run_state": "completed", "current_members": members.copy(), "current_scope_revision": 1, "fresh": True, "newer": False}
    return row, frozen, {"unit": {"value": opinion()}}, options


@pytest.mark.parametrize("level,expected", [("high", "raised"), ("low", "lower_not_applied"), ("medium", "unchanged")])
def test_fresh_opinions_compare_impact_not_strings(guard, level, expected):
    row, frozen, candidate, options = guard
    candidate["unit"]["value"]["level"] = level
    assert decision(row, frozen, candidate, **options) == expected


@pytest.mark.parametrize("change,expected", [
    ("unknown", "execution_unconfirmed"), ("missing", "opinion_missing_or_invalid"),
    ("human", "manual_revision_changed"), ("material", "frozen_scope_changed"),
    ("local", "local_scope_only"), ("stale", "input_changed"), ("late", "newer_round_exists")])
def test_inapplicable_complete_units_do_not_raise(guard, change, expected):
    row, frozen, candidate, options = copy.deepcopy(guard)
    if change == "unknown": options["run_state"] = "unknown"
    if change == "missing": candidate["unit"] = None
    if change == "human": row["risk_metadata"]["manual_severity_revision"] = 1
    if change == "material": options["current_members"][next(iter(frozen["members"]))] = str(uuid4())
    if change == "local": frozen["scope_kind"] = "selected_alerts"
    if change == "stale": options["fresh"] = False
    if change == "late": options["newer"] = True
    assert decision(row, frozen, candidate, **options) == expected


def test_new_round_can_raise_previously_manual_value(guard):
    row, frozen, candidate, options = guard
    row["severity_source"] = "manual"
    row["risk_metadata"]["manual_severity_revision"] = frozen["manual_severity_revision"] = 1
    assert decision(row, frozen, candidate, **options) == "raised"


def test_new_incident_fingerprint_excludes_only_own_risk_outputs():
    from app.socai2.stage_inputs import RISK_INPUT_VERSION, comparison_source
    old = {"parent": {"title": "Synthetic input", "severity": "medium", "risk_metadata": {},
        "priority_value": 50, "severity_override": None}, "members": [{"material": {"id": str(uuid4())}}]}
    frozen = {**copy.deepcopy(old), "risk_input_version": RISK_INPUT_VERSION}
    current = copy.deepcopy(old)
    current["parent"].update(severity="high", risk_metadata={"latest_opinion": {}}, priority_value=75)
    assert comparison_source(frozen) == comparison_source(current, risk_version=RISK_INPUT_VERSION)
    assert comparison_source(old) != comparison_source(current)  # No retroactive rewrite of legacy equality.
    for key, value in [("title", "Changed input"), ("severity_override", "low")]:
        changed = copy.deepcopy(current)
        changed["parent"][key] = value
        assert comparison_source(frozen) != comparison_source(changed, risk_version=RISK_INPUT_VERSION)
    current["members"][0]["material"]["id"] = str(uuid4())
    assert comparison_source(frozen) != comparison_source(current, risk_version=RISK_INPUT_VERSION)
