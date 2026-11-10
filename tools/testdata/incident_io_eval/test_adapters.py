"""Offline contract tests; altered packets are synthetic copies, never DB rows."""
import copy
import json
import os
from pathlib import Path

import pytest
from app.socai2 import incident_diagnosis_contract as legacy
from app.socai2.baseline_store import StoreError
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError

from .fixtures import load
from .input_adapter import encoded, prepare, rows
from .output_adapter import candidate_schema, parse, replay_candidate, review

ROOT = Path(__file__).resolve().parents[3]
CONFIG = json.loads(Path(__file__).with_name("config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / CONFIG["policy"])


@pytest.fixture
def sample():
    return load(ROOT, CONFIG)


def extra(sample, field, value, *, role="observation", member=0):
    sid = "N1_S" + str(max(int(s.rsplit("S", 1)[1]) for s in sample["source_map"]) + 1)
    aid = sample["data"]["members"][member]["alert_id"]
    reference = copy.deepcopy(next(s["ref"] for s in sample["source_map"].values() if aid in s["alert_ids"]))
    reference.update(source_path=field, role=role)
    sample["source_map"][sid] = {"ref": reference, "alert_ids": [aid]}
    sample["data"]["source_groups"].append({"role": role, "alert_ids": [aid],
                                           "items": [{"id": sid, "field": field, "value": value}]})
    return sid


def fixture_answer(prepared):
    sources = {aid: next(s for s, v in prepared["source_map"].items()
                        if v["alert_ids"] == [aid] and v["ref"]["role"] == "observation")
               for aid in prepared["member_aliases"]}
    return {"diagnosis": {"summary": "离线结构夹具，不是模型原答。", "conclusion": "仅验证字段装配。",
                           "source_ids": list(sources.values()), "limitations": []},
            "members": [{"alert_ref": alias, "state": "unresolved", "assessment": "合成的成员评述夹具。",
                         "source_ids": [sources[aid]], "limitations": []}
                        for aid, alias in prepared["member_aliases"].items()],
            "findings": [], "open_questions": []}


def test_original_packet_is_immutable_and_all_observations_remain_addressable(sample):
    before = copy.deepcopy(sample)
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert sample == before
    for item in rows(sample["data"]):
        if item["role"] in {"observation", "prior_analysis", "human_statement"}:
            assert item["id"] in projected["source_map"]
            if item["role"] == "prior_analysis":
                assert item["value"]["rationale"] in projected["user"]
    for sid, source in projected["source_map"].items():
        assert source["ref"] == sample["source_map"][sid]["ref"]
        assert source["alert_ids"] == sample["source_map"][sid]["alert_ids"]


def test_only_identical_same_member_copies_are_grouped(sample):
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    merged = [r for r in projected["records"] if len(r["source_ids"]) > 1]
    assert merged
    for row in merged:
        originals = [x for x in rows(sample["data"]) if x["id"] in row["source_ids"]]
        assert len({encoded(x["value"]) for x in originals}) == 1
        assert len({tuple(x["alert_ids"]) for x in originals}) == 1
    conflict = next(x for x in rows(sample["data"]) if x["field"] == "$.raw_json.raw_event.ocsf_event.activity.outcome")
    for group in sample["data"]["source_groups"]:
        for item in group["items"]:
            if item["id"] == conflict["id"]:
                item["value"] = "failure"
    changed = prepare(sample["data"], sample["source_map"], CONFIG)
    assert '该动作结果：成功' in changed["user"] and '该动作结果：失败' in changed["user"]


def test_unknown_business_fields_zero_false_and_meaningful_empty_lists_survive(sample):
    values = [("vendor.account.id", "business-account-id"), ("traffic.bytes_out", 0),
              ("cloud.mfa_enabled", False), ("cloud.permissions_after", []),
              ("email.vendor_extension", {"id": "message-business-id", "description": "邮件正文\n保持原文"})]
    for field, value in values:
        extra(sample, "$.ocsf_json." + field, value)
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    for _, value in values:
        assert (value if isinstance(value, str) else encoded(value)) in projected["user"]


def test_nonempty_description_and_human_text_are_not_rewritten(sample):
    description = "合成采集端说明：登录成功，但尚未核实业务用途。\n保留第二行。"
    for group in sample["data"]["source_groups"]:
        for item in group["items"]:
            if item["field"] == "$.members.0.alert":
                item["value"]["description"] = description
    extra(sample, "$.members.0.feedback", {"rationale": "只批准这一项；旧编号N9_S1保持原样。"}, role="human_statement")
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert description in projected["user"]
    assert "只批准这一项；旧编号N9_S1保持原样。" in projected["user"]


def test_stale_or_unavailable_states_are_not_changed_to_current(sample):
    sample["data"]["members"][0].update(triage_freshness="stale", triage_eligible=False, triage_visibility="unavailable")
    sample["data"]["members"][1].update(stored_material_state="unavailable", view_coverage="partial")
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert 'A1：已有分诊与本轮材料未确认匹配' in projected["user"]
    assert 'A2：缺少可用的原始材料' in projected["user"]
    assert projected["data"]["members"] == sample["data"]["members"]


def test_internal_states_scores_and_uuid_maps_stay_only_in_backend_ledger(sample):
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    text = projected["user"]
    for key in ("included", "omitted", "stored_material_state", "triage_eligible", "triage_freshness",
                "triage_visibility", "view_coverage", "member_severities", "material_received_at",
                "confidence_rationale", "contribution", "score_state", "connector_type", "original_vendor"):
        assert key not in text
    assert all(aid not in text for aid in projected["member_aliases"])
    assert projected["program_facts"] == sample["data"]["program_facts"]
    assert "部分原始内容未进入本次输入" in text


def test_business_fields_named_like_backend_scores_are_preserved_by_path(sample):
    extra(sample, "$.ocsf_json.vendor.confidence_value", 0)
    extra(sample, "$.ocsf_json.vendor.connector_type", "business-record-origin")
    extra(sample, "$.ocsf_json.vendor.schema_version", {"id": "business-doc", "content": False})
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "vendor.confidence_value：0" in projected["user"]
    assert "vendor.connector_type：business-record-origin" in projected["user"]
    assert 'vendor.schema_version：{"content":false,"id":"business-doc"}' in projected["user"]


def test_detection_business_rule_and_unknown_extensions_survive_score_removal(sample):
    for group in sample["data"]["source_groups"]:
        for item in group["items"]:
            if item["field"] == "$.detection":
                item["value"].update(rule_name="合成规则：敏感权限变更", rule_id="RULE-X-UNKNOWN",
                                     techniques=["T-UNMAPPED"], vendor_condition={"authorized": False},
                                     confidence_value=99.9)
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "合成规则：敏感权限变更" in projected["user"] and "RULE-X-UNKNOWN" in projected["user"]
    assert "T-UNMAPPED" in projected["user"] and 'vendor_condition：{"authorized":false}' in projected["user"]
    assert "confidence_value" not in projected["user"]


def test_class_dictionary_does_not_guess_unknown_or_wrongly_typed_codes(sample):
    extra(sample, "$.ocsf_json.class_uid", 99991, role="source_label")
    extra(sample, "$.ocsf_json.class_uid", "3002", role="source_label")
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "记录类别：身份认证" in projected["user"]
    assert "记录类别：99991" in projected["user"] and "记录类别：3002" in projected["user"]


def test_unique_objects_normalization_differences_and_program_only_facts_survive(sample):
    for group in sample["data"]["source_groups"]:
        for item in group["items"]:
            if item["field"] == "$.members.0.objects":
                item["value"].append({"object_type": "domain", "object_role": "target",
                                      "raw_value": "Example.INTERNAL", "normalized_value": "example.internal"})
    facts = sample["data"]["program_facts"]["members"][0]
    facts["detection_labels"]["entries"] = [{"received": "CUSTOM-T", "mapping_state": "mapped", "name": "合成标签释义"}]
    facts["activity_times"].append({"kind": "activity_start_time", "unit": "unix_milliseconds", "value": 1, "source": None})
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "Example.INTERNAL" in projected["user"] and "example.internal" in projected["user"]
    assert "合成标签释义" in projected["user"] and "unix_milliseconds" in projected["user"]


def test_variable_member_count_and_new_business_values_need_no_case_specific_rules(sample):
    aid = sample["data"]["members"][0]["alert_id"]
    sample["data"]["members"] = sample["data"]["members"][:1]
    sample["data"]["program_facts"]["members"] = sample["data"]["program_facts"]["members"][:1]
    sample["data"]["source_groups"] = [g for g in sample["data"]["source_groups"] if not g["alert_ids"] or g["alert_ids"] == [aid]]
    sample["source_map"] = {s: v for s, v in sample["source_map"].items() if not v["alert_ids"] or v["alert_ids"] == [aid]}
    extra(sample, "$.ocsf_json.cloud.target.resource", "synthetic-unseen-resource")
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "本轮成员：A1。" in projected["user"]
    assert "synthetic-unseen-resource" in projected["user"]
    output, members = parse(encoded(fixture_answer(projected)), projected)
    assert len(members) == len(output.findings) == 1


def test_query_receipts_are_inventoried_but_not_silently_added_to_i(sample):
    assert len(sample["queries"]) == 3
    assert all(len(q["receipts"]) == 3 for q in sample["queries"])
    assert all(not q["included_in_current_i_model_view"] for q in sample["queries"])
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "query_statuses" not in projected["program_facts"]


def test_old_answer_structure_replay_matches_every_existing_output_field(sample):
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    # Isolate OUTPUT adaptation: keep the OLD input's complete reference set.
    replay_context = {**projected, "source_map": sample["source_map"]}
    candidate = replay_candidate(sample["answer"], projected["member_aliases"])
    Draft202012Validator(candidate_schema(replay_context)).validate(candidate)
    expected, expected_members = legacy.parse(sample["raw_answer"], sample["source_map"], sample["data"])
    actual, actual_members = parse(encoded(candidate), replay_context)
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    assert actual_members == expected_members
    assert len(actual.findings) == 8 and len(actual.open_questions) == 2


def test_new_input_accepts_only_visible_sources_without_fabricating_member_analysis(sample):
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    candidate = fixture_answer(projected)
    Draft202012Validator(candidate_schema(projected)).validate(candidate)
    actual, members = parse(encoded(candidate), projected)
    assert [f.statement for f in actual.findings] == [m["assessment"] for m in candidate["members"]]
    assert [m["alert_id"] for m in members] == list(projected["member_aliases"])
    assert actual.summary == candidate["diagnosis"]["summary"]


@pytest.mark.parametrize("mutation", ["missing_member", "duplicate_member", "foreign_member", "foreign_source", "cross_member", "extra_field", "duplicate_json_key"])
def test_invalid_scopes_and_shapes_are_not_silently_repaired(sample, mutation):
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    answer = fixture_answer(projected)
    if mutation == "missing_member":
        answer["members"].pop()
    elif mutation == "duplicate_member":
        answer["members"][1]["alert_ref"] = answer["members"][0]["alert_ref"]
    elif mutation == "foreign_member":
        answer["members"][0]["alert_ref"] = "A999"
    elif mutation == "foreign_source":
        answer["members"][0]["source_ids"] = ["N999_S999"]
    elif mutation == "cross_member":
        answer["members"][0]["source_ids"] = answer["members"][1]["source_ids"]
    elif mutation == "extra_field":
        answer["severity"] = "critical"
    content = encoded(answer)
    if mutation == "duplicate_json_key":
        content = content[:-1] + ',"findings":[]}'
    with pytest.raises((StoreError, SchemaError)):
        parse(content, projected)


def test_one_bad_member_reference_retains_other_valid_members_in_existing_review(sample):
    projected = prepare(sample["data"], sample["source_map"], CONFIG)
    candidate = fixture_answer(projected)
    candidate["members"][0]["source_ids"] = ["N999_S999"]
    with pytest.raises(StoreError):
        parse(encoded(candidate), projected)
    partial = review(encoded(candidate), projected)
    assert partial is not None and len(partial["retained_analysis"]["members"]) == 2
