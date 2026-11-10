"""Original-input regressions: compactness never substitutes for meaning or scope."""
import copy
import json
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_store import StoreError, encoded
from app.socai2.model_input_view import compact, items
from app.socai2.runtime_policy import draft_limit, field_limit
from app.socai2.structured_output import response_format
from test_socai2_stage_quality import answer, incident_answer, source

ROOT = Path(__file__).resolve().parents[3]


def snapshot(batch):
    directory = {"r4": "20261104T074438-r4-export", "r5": "20261104T075920-r5-export",
        "r6": "20261104T092702-r6-export"}[batch]
    path = max((ROOT / "docs/operations/evidence/socai2-next-acceptance-20261104" / directory).glob("database-*.json"))
    return json.loads(path.read_text("utf-8"))


@pytest.mark.parametrize("batch", ["r4", "r5"])
def test_frozen_incident_preserves_original_visible_values_and_restores_paired_triage(batch):
    db = snapshot(batch)
    run = next(r for r in db["runs"] if r["kind"] == "incident_diagnosis")
    arts = {a["id"]: a for a in db["artifacts"]}
    original = arts[run["input_artifact_id"]]["content_json"]
    before = copy.deepcopy(original)
    old = next(a["content_json"] for a in arts.values() if a["run_id"] == run["id"] and a["kind"] == "model_request")
    old_data = json.loads(old["body"]["input"][1]["content"])
    messages, refs, data = incident.build(original, run["input_artifact_id"])
    wire = json.loads(messages[1]["content"])
    assert "items" not in wire and len(encoded(wire)) <= draft_limit()
    assert items(wire) == data["items"]
    by_source = {(tuple(i["alert_ids"]), i["field"]): i for i in items(wire)}
    for item in old_data["items"]:
        actual = by_source[(tuple(item["alert_ids"]), item["field"])]
        assert actual["value"] == item["value"] and actual["role"] == item["role"]
    for index, member in enumerate(original["members"]):
        aid = member["alert"]["id"]
        value = by_source[((aid,), f"$.members.{index}.triage")]
        assert value["value"] == {k: member["triage"].get(k) for k in (
            "verdict", "rationale", "confidence", "score_state", "assessed_at")}
        coverage = next(m for m in wire["members"] if m["alert_id"] == aid)
        assert coverage["triage_eligible"] and coverage["triage_visibility"] == "included"
        assert refs[value["id"]]["ref"]["role"] == "prior_analysis"
    assert original == before


def test_grouping_preserves_types_and_separates_roles_members_and_origins():
    data = {"items": [{"id": f"S{i+1}", "alert_ids": [str(i % 2)], "role": role,
        "origin": "input", "field": "$.value", "value": value} for i, (role, value) in enumerate([
            ("observation", 0), ("source_label", "0"), ("prior_analysis", {"confidence": None}),
            ("human_statement", [False, "line\nline"]), ("observation", {"a": [1, 2]})])]}
    before = copy.deepcopy(data)
    assert items(compact(data)) == data["items"] and data == before


def test_m2_incident_keeps_both_detection_bundles_before_optional_raw_leaves():
    db = snapshot("r6")
    run = next(r for r in db["runs"] if r["kind"] == "incident_diagnosis")
    original = next(a["content_json"] for a in db["artifacts"] if a["id"] == run["input_artifact_id"])
    before = copy.deepcopy(original)
    messages, refs, data = incident.build(original, run["input_artifact_id"])
    visible = {(tuple(i["alert_ids"]), i["field"]): i for i in items(json.loads(messages[1]["content"]))}
    for index, member in enumerate(original["members"]):
        aid = member["alert"]["id"]
        detection = visible[((aid,), "$.detection")]
        assert detection["value"] == member["material"]["detection"]
        assert detection["role"] == refs[detection["id"]]["ref"]["role"] == "source_label"
        assert refs[detection["id"]]["ref"]["id"] == member["material"]["id"]
        assert visible[((aid,), f"$.members.{index}.triage")]["value"] == {
            k: member["triage"].get(k) for k in ("verdict", "rationale", "confidence", "score_state", "assessed_at")}
        for path, value in incident.semantic_fields(member["material"], aid):
            assert visible[((aid,), path)]["value"] == value
    assert original == before and len(messages[1]["content"].encode()) <= draft_limit()
    assert len(encoded(messages)) <= draft_limit()
    # Any optional item dropped to make room is explicitly accounted for.
    old = json.loads((ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m2/plan-and-packets.json").read_text("utf-8"))
    old_i = next(p for p in old["packets"] if p["id"] == "I-current")
    for item in old_i["data"]["items"]:
        if (tuple(item["alert_ids"]), item["field"]) not in visible:
            assert any(d["alert_ids"] == item["alert_ids"] and d["source"]["source_path"] == item["field"]
                       for d in data["omission_details"])


@pytest.mark.parametrize("value,reason", [({"rule_name": "x" * 2200}, "field_size"),
    ({"rule_name": '{"class_uid":4001,"activity_id":1}'}, "input_guard")])
def test_detection_priority_keeps_guard_and_explicit_omissions(value, reason, monkeypatch):
    monkeypatch.setattr(incident, "field_limit", lambda: 2048)
    frozen = source()
    frozen["members"][0]["material"]["detection"] = value
    _, _, data = incident.build(frozen, uuid4())
    assert not any(i["field"] == "$.detection" for i in data["items"])
    assert any(d["source"]["source_path"] == "$.detection" and d["reason"] == reason
               for d in data["omission_details"])


@pytest.mark.parametrize("reason", ["large_fact", "large_triage", "guard_triage"])
def test_required_values_never_silently_disappear(reason):
    frozen = source()
    member = frozen["members"][0]
    if reason == "large_fact":
        member["material"]["ocsf_json"]["process"]["cmd_line"] = "x" * (field_limit() + 1)
        with pytest.raises(StoreError, match="required_semantic_input_unavailable"):
            alert.build(frozen, uuid4(), [])
        expected = "required_semantic_input_unavailable"
    else:
        paired = {"id": str(uuid4()), "source_run_id": str(uuid4()), "verdict": "needs_review",
            "rationale": "x" * (field_limit() + 1) if reason == "large_triage" else '{"class_uid":4001,"activity_id":1}',
            "confidence": None, "score_state": "not_computed"}
        member["triage"] = paired
        frozen["triage_validation"][member["alert"]["id"]] = {"usable": True, "freshness": "current",
            "triage_id": paired["id"], "source_run_id": paired["source_run_id"]}
        expected = "incident_required_input_"
    with pytest.raises(StoreError, match=expected):
        incident.build(frozen, uuid4())


def test_bound_prose_is_warning_but_unknown_reference_still_blocks():
    _, mapping, data = alert.build(source(), uuid4(), [])
    value = answer(data)
    sid = next(s for s in mapping if s not in value["evidence_ids"])
    value["evidence_ids"].append(sid)
    value["rationale"] = f"Source {sid} needs confirmation."
    diagnostics = []
    assert alert.parse(json.dumps(value), mapping, data, diagnostics=diagnostics).rationale == value["rationale"]
    assert diagnostics == [{"code": "source_alias_in_prose", "path": "$.rationale", "category": "presentation",
        "severity": "warning", "check_state": "observed"}]
    value["rationale"] = "Source S999 needs confirmation."
    with pytest.raises(StoreError, match="prose_source_unbound"):
        alert.parse(json.dumps(value), mapping, data)


def test_background_schema_and_parser_agree_and_report_multiple_issues():
    _, refs, data = incident.build(source(), uuid4())
    value = incident_answer(data)
    background = next(s for s, v in refs.items() if not v["alert_ids"])
    fmt = response_format(incident.Answer, refs, members=[m["alert_id"] for m in data["members"]],
        member_sources=[s for s, v in refs.items() if v["alert_ids"]])["json_schema"]["schema"]
    value["evidence_ids"].append(background)
    jsonschema.validate(value, fmt)
    incident.parse(json.dumps(value), refs, data)
    value["members"][0]["source_ids"].append(background)
    value["members"][0]["assessment"] += f" ({background})"
    value["open_questions"] = [{"text": "Verify relation", "alert_ids": [data["members"][0]["alert_id"]],
        "source_ids": ["S999"], "evidence_requirements": ["direct record"]}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, fmt)
    diagnostics = []
    with pytest.raises(StoreError, match="incident_source_wrong_member"):
        incident.parse(json.dumps(value), refs, data, diagnostics=diagnostics)
    codes = {d["code"] for d in diagnostics}
    assert {"incident_source_wrong_member", "incident_answer_source_invalid", "incident_answer_prose_source_wrong_member"} <= codes


def test_bad_json_cannot_report_source_checks_as_passed():
    diagnostics = []
    with pytest.raises(StoreError, match="shape_invalid"):
        incident.parse("{", {}, {}, diagnostics=diagnostics)
    assert any(d["check_state"] == "not_checked" for d in diagnostics)


@pytest.mark.parametrize("batch", ["r4", "r6"])
def test_case_frozen_material_and_triage_survive_initial_model_view(batch):
    from app.socai2 import baseline_analysis, baseline_enrichment, baseline_model_view
    from app.socai2.baseline_context import Context
    from app.socai2.model_input_view import frozen_items
    db = snapshot(batch)
    rid = next(r["id"] for r in db["runs"] if r["kind"] == "baseline")
    arts = [a for a in db["artifacts"] if a["run_id"] == rid]
    context_art = next(a for a in arts if a["schema_version"] == "socai2.baseline-context.v1")
    context = Context.model_validate(context_art["content_json"])
    tools = {a["id"]: a["content_json"] for a in arts if a["kind"] == "tool_response"}
    c2 = next(a["content_json"] for a in arts if a["kind"] == "source_snapshot" and a["schema_version"] == baseline_enrichment.SCHEMA)
    enrichment = [(s["artifact_id"], tools[s["artifact_id"]], baseline_enrichment.citation_roles(tools[s["artifact_id"]])) for s in c2["sources"]]
    states = [{k: s[k] for k in ("source", "outcome", "truncated", "reason", "limitations")} for s in c2["sources"]]
    materials = {m["alert_id"]: m for m in db["alert_materials"] if m["alert_id"] in context.alerts}
    prepared = baseline_model_view.build(context, context_art["id"], enrichment, states, materials)
    assert prepared["ready"], prepared
    assert prepared["schema_version"] == "socai2.baseline-model-view.v4"
    frozen = frozen_items(json.loads(prepared["messages"][1]["content"]))
    assert all(m["triage_visibility"] == "included" for m in prepared["coverage"].values() if m["triage_eligible"])
    messages, refs = baseline_analysis.messages(prepared, context, tools)
    assert len(messages[1]["content"].encode()) == prepared["bytes"] <= draft_limit()
    assert len(prepared["messages"][1]["content"].encode()) == prepared["prepared_ledger_bytes"]
    visible = items(json.loads(messages[1]["content"]))
    assert len(frozen) == len(visible) == len(refs)
    for item in visible:
        ref = refs[item["id"]]["ref"]
        original = next(v for v in frozen if v["source"] == ref)
        assert item["value"] == original["value"]
    assert "selected_fields_not_full_raw_review" in messages[1]["content"]
    if batch == "r6":
        from unittest.mock import patch
        with patch.object(baseline_model_view, "draft_limit", lambda: 1000):
            denied = baseline_model_view.build(context, context_art["id"], enrichment, states, materials)
        assert not denied["ready"] and all(m["view_coverage"] == "unavailable" for m in denied["coverage"].values())
        assert prepared["prepared_ledger_bytes"] > 8192  # off-wire provenance is not model input
        for aid in context.alerts:
            assert any(r["ref"]["source_path"] == f"$.alerts.{aid}.alert.event_time" for r in refs.values())
        for iid, incident_input in context.incidents.items():
            if incident_input.diagnosis_usable:
                value = next(i["value"] for i in visible if refs[i["id"]]["ref"]["source_path"] == f"$.incidents.{iid}.diagnosis")
                original = incident_input.diagnosis
                assert value == {"summary": original["summary"], "conclusion": original["diagnosis"]["conclusion"],
                    "limitations": original["diagnosis"]["limitations"]}
    legacy = copy.deepcopy(prepared)
    legacy_data = json.loads(legacy["messages"][1]["content"])
    legacy_data.pop("frozen_source_groups")
    legacy_data["items"] = frozen
    legacy_data["schema_version"] = "socai2.baseline-model-view.v1"
    legacy["messages"][1]["content"] = encoded(legacy_data).decode()
    legacy_messages, legacy_refs = baseline_analysis.messages(legacy, context, tools)
    assert legacy_refs == refs
    assert items(json.loads(legacy_messages[1]["content"])) == visible


def test_final_budget_never_discards_required_feedback_or_paired_judgment():
    from app.socai2.baseline_reasoning import fit_final_request
    data = {"members": {"a": {"included": 2}}, "items": [
        {"id": "S1", "role": "human_statement", "alert_ids": ["a"], "value": "approval only applies to script A"},
        {"id": "S2", "role": "source_label", "alert_ids": ["a"], "value": "optional metadata" * 100}]}
    body = {"messages": [{"role": "system", "content": "rules"}, {"role": "user", "content": encoded(compact(data)).decode()}],
        "response_format": response_format(alert.Answer, ["S1", "S2"])}
    prepared = {"source_map": {sid: {"ref": {"id": sid}, "alert_ids": ["a"], "required": sid == "S1"}
        for sid in ("S1", "S2")}, "omissions": []}
    fit_final_request(body, prepared, 1)
    assert list(prepared["source_map"]) == ["S1"]
    assert items(json.loads(body["messages"][1]["content"]))[0]["value"] == data["items"][0]["value"]
    assert len(encoded(body)) > 1  # caller must reject capacity; never pretend fit


def test_required_clock_survives_omission_of_large_alert_metadata(monkeypatch):
    monkeypatch.setattr(alert, "field_limit", lambda: 2048)
    monkeypatch.setattr(incident, "field_limit", lambda: 2048)
    from app.socai2.stage_results import validate_refs
    frozen = source()
    member = frozen["members"][0]
    member["alert"].update(title="x" * 2500, event_time="2026-11-04T01:00:00Z")
    for contract, args in ((alert, (frozen, uuid4(), [])), (incident, (frozen, uuid4()))):
        messages, refs, data = contract.build(*args)
        clock = next(i for i in items(json.loads(messages[1]["content"])) if i["field"].endswith(".alert.event_time"))
        assert clock["value"] == member["alert"]["event_time"] and clock["role"] == "source_label"
        assert refs[clock["id"]]["ref"]["source_path"].endswith(".alert.event_time")
        assert data["omissions"]["field_size"] >= 1
        ref = refs[clock["id"]]["ref"]
        validate_refs({"source_refs": [ref]}, frozen, args[1])
        with pytest.raises(StoreError, match="stage_input_reference_role_or_path_invalid"):
            validate_refs({"source_refs": [{**ref, "role": "observation"}]}, frozen, args[1])
        with pytest.raises(StoreError, match="stage_input_reference_role_or_path_invalid"):
            validate_refs({"source_refs": [{**ref, "source_path": ref["source_path"] + ".extra"}]}, frozen, args[1])


def test_late_required_feedback_precedes_large_optional_background():
    from app.socai2.baseline_reasoning import bounded_input
    candidates = [{"original": "x" * 1600, "entry": {"id": f"S{i+1}", "role": "source_label",
        "alert_ids": ["a"], "value": "x" * 1600}, "source": {"ref": {"id": str(i)}, "alert_ids": ["a"]}}
        for i in range(8)]
    candidates.append({"original": "authorization applies only to the script", "required": True,
        "entry": {"id": "S9", "role": "human_statement", "alert_ids": ["a"], "value": "authorization applies only to the script"},
        "source": {"ref": {"id": "human"}, "alert_ids": ["a"]}})
    from unittest.mock import patch
    with patch("app.socai2.baseline_reasoning.draft_limit", return_value=8192):
        prepared = bounded_input({"members": {"a": {"included": 0}}}, candidates, "Analyze the evidence.")
    assert prepared["ready"] and "N1_S9" in prepared["source_map"]
    assert prepared["omissions"] and prepared["source_map"]["N1_S9"]["required"]


def test_only_unchanged_server_question_rules_are_deduplicated():
    from app.socai2.baseline_context import QUESTIONS
    identity, question, requirement = QUESTIONS[0]
    original = {"items": [], "questions": [
        {"id": identity, "text": question, "evidence_requirements": [requirement]},
        {"id": "custom", "text": question, "evidence_requirements": [requirement]},
        {"id": identity, "text": question, "evidence_requirements": ["custom required source"]}]}
    before = copy.deepcopy(original)
    result = compact(original)
    assert result["questions"][0] == {"id": identity, "text": question}
    assert result["questions"][1:] == before["questions"][1:] and original == before
