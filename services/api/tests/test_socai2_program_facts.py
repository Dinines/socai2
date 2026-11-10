"""Frozen known fields remain separate from model prose and risk judgments."""
import copy
import json
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import jsonschema
import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_context import Context
from app.socai2.baseline_model_view import build
from app.socai2.baseline_semantics import project
from app.socai2.model_input_view import frozen_items
from app.socai2.program_facts import case_facts, incident_level, labels
from test_socai2_followup_scope import frozen
from test_socai2_stage_quality import source


def test_diagnosis_contract_keeps_partial_content_separate_from_a_global_conclusion():
    root = Path(__file__).resolve().parents[3]
    document = json.loads((root / "services/api/app/socai2/contracts.schema.json").read_text())
    schema = {"$defs": document["$defs"], "$ref": "#/$defs/diagnosis"}
    legacy = {"conclusion": "prior valid diagnosis", "validation_state": "accepted",
        "findings": [], "source_refs": [], "limitations": []}
    jsonschema.validate(legacy, schema)
    partial = {"conclusion": None, "validation_state": "partial", "findings": [],
        "partial_review_artifact_id": str(uuid4()), "limitations": ["global conclusion unavailable"]}
    jsonschema.validate(partial, schema)
    invalid = [dict(partial, conclusion="unsupported global conclusion"),
        {k: v for k, v in partial.items() if k != "partial_review_artifact_id"},
        {k: v for k, v in legacy.items() if k != "source_refs"},
        dict(partial, validation_state="accepted", source_refs=[])]
    for value in invalid:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(value, schema)
@pytest.mark.parametrize("builder", [alert, incident])
def test_all_four_clocks_and_severity_roles_are_explicit_without_raw_mutation(builder):
    original = source()
    member = original["members"][0]
    aid = member["alert"]["id"]
    member["alert"].update(event_time="2026-11-06T12:50:10+00:00", event_time_source="source",
        ingested_at="2026-11-06T12:50:11+00:00", severity="medium", original_vendor="Received Vendor")
    stamp = "2026-11-06T12:49:45+00:00"
    member["material"]["ocsf_json"] = {"class_uid": 3002, "time": stamp, "severity_id": 1,
        "activity": {"action": "logon", "outcome": "success"}}
    member["material"]["detection"] = {"tactics": ["TA0009"], "techniques": ["T1005", "T9999"]}
    original["parent"]["severity_override"] = "high"
    before = copy.deepcopy(original)
    args = (original, uuid4(), []) if builder is alert else (original, uuid4())
    messages, refs, data = builder.build(*args, execution_time="2026-11-07T00:00:00+00:00")
    known = json.loads(messages[1]["content"])["program_facts"]
    record = known["members"][0]
    assert record["alert"]["event_time"] != record["activity_times"][0]["value"] == stamp
    assert record["alert"]["severity"] == "medium" and record["log_severity"][0]["value"] == 1
    assert record["alert"]["ingested_at"] != known["execution_started_at"]
    assert record["detection_labels"]["entries"][0]["name"] == "Collection"
    assert record["detection_labels"]["entries"][2]["mapping_state"] == "unknown"
    times = [item for item in data["items"] if item["field"] == "$.ocsf_json.time"]
    assert len(times) == 1 and times[0]["value"] == stamp
    assert refs[times[0]["id"]]["ref"]["role"] == "observation"
    if builder is incident:
        assert known["incident_severity"]["severity_effective"] == "high"
        assert known["incident_severity"]["severity_source"] == "manual_override"
        assert known["incident_severity"]["member_severities"] == {aid: "medium"}
    assert original == before


@pytest.mark.parametrize("value,unit", [(1793969385000, "unix_milliseconds"),
    ("2026-11-06T20:49:45+08:00", "iso8601_with_offset")])
def test_activity_time_preserves_original_value_and_explicit_unit(value, unit):
    field = next(f for f in project({"class_uid": 3002, "time": value})["fields"] if f["name"] == "activity_time")
    assert field["value"] == value and field["unit"] == unit and field["source_path"] == "$.ocsf_json.time"
    unknown = project({"time": 1793969385})
    assert next(f for f in unknown["fields"] if f["name"] == "activity_time")["unit"] == "unspecified_numeric_time"


@pytest.mark.parametrize("bad", [True, -1, 1.5, "2026-11-06T12:49:45", "unknown"])
def test_invalid_time_is_not_substituted_or_inferred(bad):
    result = project({"class_uid": 3002, "time": bad})
    assert not any(f["name"] == "activity_time" for f in result["fields"])
    assert any(o["source_path"] == "$.ocsf_json.time" for o in result["omissions"])


def test_complete_incident_max_unknown_members_and_partial_scope_are_distinct():
    alerts = {"a": {"severity": "low"}, "b": {"severity": "medium"}, "c": {"severity": None}}
    result = incident_level({}, alerts, alerts)
    assert result["severity_effective"] == "medium" and result["unknown_severity_count"] == 1
    result = incident_level({}, alerts, [*alerts, "unfrozen-member"])
    assert result["severity_auto"] is None and result["missing_member_ids"] == ["unfrozen-member"]
    result = incident_level({"severity_override": "high"}, alerts, [*alerts, "unfrozen-member"])
    assert result["severity_effective"] == "high" and result["state"] == "partial_member_scope"
    assert incident_level({}, {"a": {"severity": None}}, ["a"])["severity_effective"] is None


def test_case_frozen_names_and_times_have_sources_and_no_new_case_severity():
    stored, _ = frozen()
    context = Context.model_validate(stored["context"])
    aid = next(iter(context.alerts))
    material = {"id": UUID(context.alerts[aid].material["id"]), "alert_id": aid,
        "received_at": datetime.fromisoformat("2026-11-06T12:49:46+00:00"),
        "material_state": "complete", "ocsf_json": {"class_uid": 3002, "time": 1793969385000}, "detection": {}}
    artifact = uuid4()
    facts = case_facts(context, artifact, {aid: material})
    root = Path(__file__).resolve().parents[3]
    schema = json.loads((root / "services/api/app/socai2/contracts.schema.json").read_text())
    jsonschema.validate(facts, {"$defs": schema["$defs"], "$ref": "#/$defs/program_facts"})
    design = json.loads((root / "docs/design/socai2-json-contracts-20261103.schema.json").read_text())
    dictionary = json.loads((root / "docs/design/socai2-data-contract-20261103.json").read_text())
    assert design["$defs"]["program_facts"] == schema["$defs"]["program_facts"] == dictionary["contracts"]["program_facts"]["schema"]
    for name in ("diagnosis", "alert_explanation", "report_result"):
        assert design["$defs"][name] == schema["$defs"][name] == dictionary["contracts"][name]["schema"]
    assert facts["case_severity"] == context.case.get("severity")
    record = next(m for m in facts["members"] if m["alert"]["id"] == aid)
    assert record["activity_times"][0]["source"]["id"] == str(material["id"])
    started = datetime.fromisoformat("2026-11-07T01:00:00+00:00")
    run_id = uuid4()
    view = build(context, artifact, [], [], {aid: material}, execution_time=started, run_id=run_id)
    assert view["ready"], view.get("reason")
    data = json.loads(view["messages"][1]["content"])
    assert data["program_facts"]["execution_started_at"] == started.isoformat()
    assert data["program_facts"]["execution_time_source"]["id"] == str(run_id)
    assert data["program_facts"]["snapshot_captured_at"] != started.isoformat()
    entries = frozen_items(data)
    actual = next(item for item in entries if item["source"]["source_path"] == "$.ocsf_json.time")
    assert actual["required"] and actual["value"] == {"activity_time": 1793969385000, "unit": "unix_milliseconds"}


def test_unknown_detection_identifier_is_not_guessed_or_promoted_to_observation():
    output = labels({"tactics": ["TA0009", "Collection", "TA9999"], "techniques": ["T1005"]})
    assert output["role"] == "source_label" and output["does_not_establish_observed_attack"]
    assert [e["mapping_state"] for e in output["entries"]] == ["mapped", "unknown", "unknown", "mapped"]
    assert output["entries"][-1]["name"] == "Data from Local System"
    assert datetime.fromisoformat(output["entries"][-1]["verified_on"]).year == 2026
