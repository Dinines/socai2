"""Field roles, strict shape and source alias boundaries; no model or network."""
import copy
import json
from uuid import uuid4

import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_semantics import material_projection
from app.socai2.baseline_store import StoreError


def source():
    aid, mid = str(uuid4()), str(uuid4())
    member = {"alert": {"id": aid, "title": "Recorded activity", "event_time": None},
        "material": {"id": mid, "material_state": "complete", "raw_text": None,
            "ocsf_json": {"process": {"pid": 42}, "metadata": {"product": {"name": "InternalProbe"}}},
            "raw_json": {"raw_event": {"original_vendor": "VendorClaim", "custom_annotation": "Validation run",
                "process": {"pid": 42, "metadata": {"label": "Preapproved"}}, "user": {"name": "S1"}}},
            "detection": {}, "source_scope": {}}, "objects": [], "feedback": None, "membership": {}, "triage": None}
    return {"parent": {"id": str(uuid4())}, "members": [member], "triage_validation": {aid: {"usable": False}}}


def test_omission_details_are_bounded_with_explicit_count():
    data = {}
    details = [{"source": {"id": str(uuid4()), "source_path": "$." + "x" * 100}, "reason": "view_size"} for _ in range(300)]
    alert.retain_omission_details(data, details)
    assert len(json.dumps(data["omission_details"], separators=(",", ":")).encode()) <= 16384
    assert data["omission_details_truncated"] and data["omission_detail_count"] == 300


def test_typed_projection_keeps_conflicting_names_and_original_paths():
    mat = {"id": uuid4(), "alert_id": uuid4(), "material_state": "complete", "ocsf_json": {
        "class_uid": 1007, "actor": {"user": {"name": "actor-one"}}, "user": {"name": "user-two"},
        "device": {"hostname": "device-three"}, "network": {"protocol_name": "tcp"},
        "process": {"pid": 5, "cmd_line": "x" * 3000}}}
    output = material_projection(mat)
    names = [v for v in output["fields"] if v["name"] == "user_name"]
    assert {(v["source_path"], v["value"]) for v in names} == {
        ("$.ocsf_json.actor.user.name", "actor-one"), ("$.ocsf_json.user.name", "user-two")}
    assert all(v["conflict"] for v in names)
    assert any(v["source_path"] == "$.ocsf_json.process.cmd_line" and v["reason"] == "whole_field_exceeds_budget"
               for v in output["omissions"])


def test_incident_projection_round_robins_facts_before_metadata():
    frozen = source()
    first = frozen["members"][0]
    second = copy.deepcopy(first)
    second["alert"]["id"], second["material"]["id"] = str(uuid4()), str(uuid4())
    first["material"]["ocsf_json"] = {"metadata": {"notes": "received annotation " * 250},
        "class_uid": 1007, "process": {"pid": 7, "cmd_line": "task --read"}, "user": {"name": "first-only"}}
    second["material"]["ocsf_json"] = {"metadata": {"notes": "received annotation " * 250},
        "class_uid": 4001, "dst_endpoint": {"ip": "198.51.100.44", "port": 443},
        "src_endpoint": {"ip": "192.0.2.44", "port": 50100}, "network": {"protocol_name": "tcp"}}
    frozen["members"].append(second)
    messages, mapping, data = incident.build(frozen, uuid4())
    assert [v["alert_ids"] for v in data["items"][:2]] == [[m["alert"]["id"]] for m in frozen["members"]]
    visible = {v["field"]: v for v in data["items"]}
    assert visible["$.ocsf_json.process.cmd_line"]["value"] == "task --read"
    assert visible["$.ocsf_json.user.name"]["alert_ids"] == [first["alert"]["id"]]
    assert visible["$.ocsf_json.dst_endpoint.port"]["alert_ids"] == [second["alert"]["id"]]
    assert len([o for o in data["omission_details"] if o["source"]["source_path"] == "$.ocsf_json.metadata.notes"]) == 2
    assert "omission_details" not in json.loads(messages[1]["content"])
    assert len(messages[1]["content"].encode()) <= 8192
    assert all(mapping[x["id"]]["ref"]["type"] == "alert_material" for x in data["items"][:2])


def answer(data):
    return {"verdict": "needs_review", "confidence": None, "rationale": "Authorization is unresolved",
        "explanation": "A process record is present", "evidence_ids": [data["items"][0]["id"]],
        "recommendations": [], "limitations": ["source declarations do not establish authorization"], "decision_basis": None}


def incident_answer(data):
    ids = {m["alert_id"]: [i["id"] for i in data["items"] if m["alert_id"] in i["alert_ids"]]
        for m in data["members"]}
    return {"summary": "Related source records", "conclusion": "Authorization remains unresolved",
        "evidence_ids": [v[0] for v in ids.values()], "members": [{"alert_id": k, "state": "unresolved",
            "assessment": "Needs confirmation", "source_ids": v[:1], "limitations": []} for k,v in ids.items()],
        "findings": [], "open_questions": [], "limitations": []}


def test_a_i_annotations_keep_values_paths_and_label_roles():
    frozen = source()
    before = copy.deepcopy(frozen)
    for build in (lambda: alert.build(frozen, uuid4(), []), lambda: incident.build(frozen, uuid4())):
        messages, mapping, data = build()
        by_path = {i["field"]: i for i in data["items"]}
        for path in ("$.raw_json.raw_event.original_vendor", "$.raw_json.raw_event.custom_annotation",
                "$.raw_json.raw_event.process.metadata.label", "$.ocsf_json.metadata.product.name"):
            assert by_path[path]["role"] == "source_label"
            assert mapping[by_path[path]["id"]]["ref"]["role"] == "source_label"
        for path in ("$.ocsf_json.process.pid", "$.raw_json.raw_event.process.pid", "$.raw_json.raw_event.user.name"):
            assert by_path[path]["role"] == "observation"
        assert by_path["$.raw_json.raw_event.custom_annotation"]["value"] == "Validation run"
        assert len(json.dumps(messages, ensure_ascii=False).encode()) <= 12288
    assert frozen == before


def test_label_only_decisive_verdict_is_rejected():
    _, mapping, data = alert.build(source(), uuid4(), [])
    value = answer(data)
    value["evidence_ids"] = [i["id"] for i in data["items"] if i["role"] == "source_label"]
    for verdict in ("true_positive", "false_positive", "benign"):
        value["verdict"] = verdict
        with pytest.raises(StoreError, match="alert_answer_requires_direct_source"):
            alert.parse(json.dumps(value), mapping, data)
    value["verdict"] = "needs_review"
    assert alert.parse(json.dumps(value), mapping, data).verdict == "needs_review"


def test_unbound_alias_rejected_but_literal_source_name_allowed():
    _, mapping, data = alert.build(source(), uuid4(), [])
    value = answer(data)
    value["explanation"] = "The received account is S1."
    assert alert.parse(json.dumps(value), mapping, data).explanation == value["explanation"]
    sid = "N999_S1"
    value["explanation"] = "According to (" + sid + "), authorization is unknown."
    with pytest.raises(StoreError, match="alert_answer_prose_source_unbound"):
        alert.parse(json.dumps(value), mapping, data)
    value["explanation"] = "The account name is prefix" + sid + "suffix."
    assert alert.parse(json.dumps(value), mapping, data).explanation == value["explanation"]


def test_i_arrays_remain_strict_and_member_aliases_not_in_prose():
    _, mapping, data = incident.build(source(), uuid4())
    value = incident_answer(data)
    assert incident.parse(json.dumps(value), mapping, data)[0].summary == value["summary"]
    for path in (None, "member"):
        for invalid in (None, "not provided"):
            bad = copy.deepcopy(value)
            target = bad if path is None else bad["members"][0]
            target["limitations"] = invalid
            with pytest.raises(StoreError, match="incident_answer_shape_invalid"):
                incident.parse(json.dumps(bad), mapping, data)
    bad = copy.deepcopy(value)
    sid = "N999_S1"
    bad["summary"] += " (" + sid + ")"
    with pytest.raises(StoreError, match="incident_answer_prose_source_unbound"):
        incident.parse(json.dumps(bad), mapping, data)


def test_i_cannot_attach_one_members_field_to_another():
    frozen = source()
    second = source()["members"][0]
    frozen["members"].append(second)
    frozen["triage_validation"][second["alert"]["id"]] = {"usable": False}
    _, mapping, data = incident.build(frozen, uuid4())
    value = incident_answer(data)
    value["members"][1]["source_ids"] = value["members"][0]["source_ids"]
    with pytest.raises(StoreError, match="incident_source_wrong_member"):
        incident.parse(json.dumps(value), mapping, data)
