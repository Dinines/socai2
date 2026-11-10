"""Offline coverage and identifier contracts; no model or database fixtures."""
import copy
import json
from pathlib import Path

import pytest
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import StoreError, digest, encoded
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError

from .fixtures import load
from .input_adapter import material_entries, prepare
from .output_adapter import canonical, convert, parse, schema, tool_catalog

ROOT = Path(__file__).resolve().parents[3]
CONFIG = json.loads(Path(__file__).with_name("config.json").read_text())
BUSINESS = json.loads((ROOT / CONFIG["business_render_config"]).read_text())


@pytest.fixture
def sample():
    return load(ROOT, CONFIG)


def test_frozen_sources_not_mutated_and_every_record_has_exact_provenance(sample):
    before = copy.deepcopy(sample)
    result = prepare(sample, CONFIG, BUSINESS)
    assert before == sample
    for row in result["records"]:
        ref = result["source_map"][row["id"]]
        assert ref["ref"] == row["ref"]
        assert ref["visible_value_sha256"] == digest(row["value"])
        assert row["id"] in result["user"]
    Context.model_validate(sample["context"])


def test_incident_findings_and_questions_preserve_prose_scope_and_role(sample):
    result = prepare(sample, CONFIG, BUSINESS)
    findings = [r for r in result["records"] if r["block"] == "finding"]
    questions = [r for r in result["records"] if r["block"] == "question"]
    assert len(findings) == 8 and len(questions) == 2
    for row in [*findings, *questions]:
        assert row["ref"]["role"] == "prior_analysis"
        assert row["original_scope"] == row["original_value"]["scope"]
        assert row["alert_ids"] == sorted(row["original_scope"]["alert_ids"])
        key = "statement" if row["block"] == "finding" else "text"
        assert row["value"][key] == row["original_value"][key]
        assert row["value"][key] in result["user"]


def test_cross_member_finding_keeps_external_scope_without_new_case_member(sample):
    incident = next(iter(sample["context"]["incidents"].values()))
    finding = incident["diagnosis"]["diagnosis"]["findings"][0]
    outside = "00000000-0000-0000-0000-000000999999"
    finding["scope"]["alert_ids"] = [*sample["context"]["alerts"], outside]
    result = prepare(sample, CONFIG, BUSINESS)
    row = next(r for r in result["records"] if r["block"] == "finding")
    assert row["original_scope"]["alert_ids"] == finding["scope"]["alert_ids"]
    assert len(row["alert_ids"]) == 3
    assert row["value"]["outside_case_members"] == ["X1"]
    assert outside not in result["member_aliases"]


def test_invalid_incident_never_promoted_to_usable(sample):
    for incident in sample["context"]["incidents"].values():
        incident["diagnosis_usable"] = False
    result = prepare(sample, CONFIG, BUSINESS)
    assert not any(r["block"] in {"finding", "question", "incident"} for r in result["records"])
    assert "诊断不可" in result["user"]


def test_receipts_are_separate_from_original_triage_claims(sample):
    result = prepare(sample, CONFIG, BUSINESS)
    assert result["query_supplement_was_in_original_c1"] is False
    actual = [r for r in result["records"] if r["ref"]["role"] == "execution_receipt" and r["block"] == "query"]
    assert len(actual) == 9
    for row in result["records"]:
        if row["block"] == "triage":
            assert row["value"]["rationale"] == row["original_value"]["rationale"]
    assert any(r["original_value"]["state"] == "skipped" for r in actual)
    assert all(r["value"]["outcome"] != "empty" for r in actual if r["original_value"]["state"] == "skipped")


@pytest.mark.parametrize("field,value", [("run_id", "00000000-0000-0000-0000-000000000000"), ("sha256", "bad"), ("tenant_id", "wrong")])
def test_mispaired_or_modified_receipt_is_rejected(sample, field, value):
    first = next(iter(sample["query_source"]["triage_queries"].values()))[0]
    first[field] = value
    with pytest.raises(StoreError):
        prepare(sample, CONFIG, BUSINESS)


def test_stale_triage_cannot_lend_its_receipts(sample):
    next(iter(sample["context"]["alerts"].values()))["triage_freshness"] = "stale"
    with pytest.raises(StoreError):
        prepare(sample, CONFIG, BUSINESS)


def test_missing_receipt_is_not_an_empty_result(sample):
    aid = next(iter(sample["query_source"]["triage_queries"]))
    sample["query_source"]["triage_queries"][aid] = []
    result = prepare(sample, CONFIG, BUSINESS)
    assert result["member_aliases"][aid] + "：未提供同次分诊" in result["user"]


@pytest.mark.parametrize("relative", CONFIG["material_snapshots"])
def test_cloud_and_email_full_structures_are_present(relative):
    data = json.loads((ROOT / relative).read_text())
    for material in data["alert_materials"]:
        original = copy.deepcopy(material)
        rows = material_entries(material["alert_id"], material, BUSINESS, [])
        assert material == original
        assert rows
        assert any(r["ref"]["source_path"].startswith("$.raw_json") for r in rows)
        assert any(r["ref"]["source_path"] == "$.raw_text" and r["value"] == material["raw_text"] for r in rows)


def test_unknown_nested_fields_zero_false_empty_and_business_id_survive(sample):
    aid, material = next(iter(sample["materials"].items()))
    material["raw_json"]["future_business"] = {"actor_id": "real-business-id", "zero": 0, "enabled": False, "result": [],
                                                  "odd.key": {"nested": "kept intact"}}
    rows = material_entries(aid, material, BUSINESS, [])
    row = next(r for r in rows if r["ref"]["source_path"] == "$.raw_json.future_business")
    assert row["value"] == material["raw_json"]["future_business"]
    assert row["ref"]["role"] == "source_label"


def test_nonempty_description_and_old_numbers_are_not_rewritten(sample):
    member = next(iter(sample["context"]["alerts"].values()))
    original = "原文 N1_S3，业务用户 A1 不能改名，登录成功。"
    member["alert"]["description"] = original
    result = prepare(sample, CONFIG, BUSINESS)
    assert original in result["user"]
    assert all(sid != "N1_S3" for sid in result["source_map"])


def test_short_id_roundtrip_restores_original_analysis_without_changes(sample):
    result = prepare(sample, CONFIG, BUSINESS)
    original = {**result, "source_map": sample["request"]["source_map"], "coverage": sample["data"]["members"]}
    converted = convert(sample["answer"], result["member_aliases"], result["object_aliases"])
    restored = canonical(json.dumps(converted), original, sample["context"], sample["request"]["binding_map"])
    assert restored == sample["answer"]
    # This historical raw answer is still rejected; a lossless adapter must
    # preserve the failure, not silently repair it to make a test pass.
    with pytest.raises(AnalysisRejected, match="domain_finding_scope_mismatch"):
        parse(json.dumps(converted), original, sample["context"], sample["request"]["binding_map"])


def test_historical_citations_cannot_be_reused_as_new_current_citations(sample):
    result = prepare(sample, CONFIG, BUSINESS)
    assert not set(result["source_map"]) & set(sample["request"]["source_map"])
    converted = convert(sample["answer"], result["member_aliases"], result["object_aliases"])
    with pytest.raises(SchemaError):
        parse(json.dumps(converted), result, sample["context"], sample["request"]["binding_map"])


def test_schema_and_tool_directory_use_only_frozen_aliases(sample):
    result = prepare(sample, CONFIG, BUSINESS)
    candidate = schema(result, sample["context"], sample["request"]["binding_map"])
    Draft202012Validator.check_schema(candidate)
    catalog = tool_catalog(json.loads(sample["request"]["body"]["messages"][2]["content"]), result)
    rendered = encoded(catalog).decode()
    assert not any(aid in rendered for aid in result["member_aliases"])
    assert catalog["capabilities"] == json.loads(sample["request"]["body"]["messages"][2]["content"])["capabilities"]


def test_synthetic_valid_contract_restores_scope_and_sources(sample):
    result = prepare(sample, CONFIG, BUSINESS)
    answer = {"summary": "离线合同夹具，仅核字段装配。", "members": [], "findings": [], "questions": [],
              "domains": [], "conflicts": [], "followups": []}
    for aid, alias in result["member_aliases"].items():
        sid = next(s for s, ref in result["source_map"].items() if ref["alert_ids"] == [aid] and ref["ref"]["role"] == "observation")
        answer["members"].append({"alert_id": alias, "state": "unresolved", "summary": "仅核字段装配。",
                                  "evidence_ids": [sid], "limitations": ["合成检查，不是模型判断"]})
    for q in sample["context"]["questions"]:
        answer["questions"].append({"id": q["id"], "state": "unresolved", "answer": "本例不执行业务分析。",
                                    "evidence_ids": [], "limitations": ["合成检查"]})
    for name in ("identity", "cloud", "phishing", "insider"):
        answer["domains"].append({"name": name, "applicability": "undetermined", "reason": "本例不执行业务分析。",
                                  "alert_ids": [], "finding_ids": [], "limitations": ["合成检查"]})
    parsed = parse(json.dumps(answer), result, sample["context"], sample["request"]["binding_map"])
    assert {str(m.alert_id) for m in parsed.members} == set(sample["context"]["alerts"])
    assert len(parsed.questions) == 6 and len(parsed.domains) == 4


def test_known_backend_fields_omitted_but_unknown_business_values_preserved(sample):
    member = next(iter(sample["context"]["alerts"].values()))
    member["alert"].update(owner_id="backend-owner", row_version=19, future_business_flag=False)
    result = prepare(sample, CONFIG, BUSINESS)
    row = next(r for r in result["records"] if r["block"] == "alert")
    assert "owner_id" not in row["value"] and "row_version" not in row["value"]
    assert row["value"]["future_business_flag"] is False


def test_prior_recommendation_text_and_direct_support_survive_short_mapping(sample):
    result = prepare(sample, CONFIG, BUSINESS)
    for row in result["records"]:
        if row["block"] != "triage":
            continue
        for old, new in zip(row["original_value"]["recommendations"], row["value"]["recommendations"], strict=True):
            assert old["reason"] == new["reason"]
            for sid in new["source_refs"]:
                assert result["source_map"][sid]["ref"] in old["source_refs"]
