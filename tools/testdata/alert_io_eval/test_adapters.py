import copy
import json
import os
from pathlib import Path

import pytest

from app.socai2.baseline_store import StoreError
from .fixtures import packets
from .input_adapter import prepare, rows
from .output_adapter import parse

ROOT = Path(__file__).resolve().parents[3]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / "deploy/local-investigation/investigation-policy.toml")
CONFIG = json.loads(Path(__file__).with_name("config.json").read_text())


@pytest.fixture(scope="module")
def samples():
    return packets(ROOT, CONFIG)[0]


def test_all_nine_inputs_are_immutable_and_narratives_preserved(samples):
    for sample in samples:
        before = copy.deepcopy(sample)
        projected = prepare(sample["data"], sample["source_map"], CONFIG)
        assert sample == before
        for item in rows(sample["data"]):
            if item["role"] == "prior_analysis":
                assert json.dumps(item["value"]["rationale"], ensure_ascii=False) in projected["user"]
        assert projected["source_map"]
        assert len(projected["user"].encode()) < len(sample["body"]["messages"][1]["content"].encode())


def test_history_typos_and_query_state_are_not_rewritten(samples):
    p = prepare(samples[1]["data"], samples[1]["source_map"], CONFIG)
    assert "socai2-flow-20261908-01" in p["user"]  # Original historical typo, not silently repaired.
    assert "租户内部威胁情报：没有查询" in p["user"]
    assert "历史分析原文" in p["user"]
    assert p["user"].count("关联历史记录]") == 1
    assert '"matched_by"' in p["user"]


def test_unknown_business_ids_zero_false_and_empty_business_containers_survive(samples):
    sample = copy.deepcopy(samples[0])
    sample["data"]["source_groups"].append({"role": "observation", "origin": "input", "items": []})
    for i, (field, value) in enumerate((("process.uid", "business-uid"), ("traffic.bytes_out", 0),
                                        ("vendor.mfa", False), ("vendor.change", {"permissions_after": []})), 90):
        sid = f"N1_S{i}"
        sample["data"]["source_groups"][-1]["items"].append({"id": sid, "field": "$.ocsf_json."+field, "value": value})
        sample["source_map"][sid] = {"ref": {"type": "alert_material", "id": "m1", "role": "observation", "source_path": "$.ocsf_json."+field}}
    p = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "business-uid" in p["user"] and "traffic.bytes_out=0" in p["user"]
    assert "vendor.mfa=false" in p["user"] and '"permissions_after":[]' in p["user"]


def test_nonempty_background_and_human_text_preserved(samples):
    sample = copy.deepcopy(samples[0])
    items = [
        ("source_label", "assets", "$.rows.0", {"record_id": "asset", "record": {"name": "db-owner-host", "owner_email": "owner@example.com", "criticality": "high"}}),
        ("source_label", "threat_intel", "$.rows.0", {"record_id": "ioc", "record": {"value": "example.net", "confidence": 0, "source": "internal"}}),
        ("human_statement", "input", "$.members.0.feedback", {"id": "feedback", "rationale": "仅批准这条命令；不批准其他命令。", "verdict": "benign"})]
    for i, (role, origin, field, value) in enumerate(items, 80):
        sid = f"N1_S{i}"
        sample["data"]["source_groups"].append({"role": role, "origin": origin, "items": [{"id": sid, "field": field, "value": value}]})
        sample["source_map"][sid] = {"ref": {"type": "artifact", "id": origin, "role": role, "source_path": field}}
    p = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "owner@example.com" in p["user"] and '"confidence":0' in p["user"]
    assert "仅批准这条命令；不批准其他命令。" in p["user"]


def test_conflicting_normalized_raw_values_remain_distinct(samples):
    sample = copy.deepcopy(samples[0])
    altered = next(x for x in rows(sample["data"]) if x["field"] == "$.raw_json.raw_event.ocsf_event.activity.outcome")
    for group in sample["data"]["source_groups"]:
        for x in group["items"]:
            if x["id"] == altered["id"]:
                x["value"] = "failure"
    p = prepare(sample["data"], sample["source_map"], CONFIG)
    assert "成功（success）" in p["user"] and "失败（failure）" in p["user"]


def answer(p, **changes):
    direct = next(s for s, v in p["source_map"].items() if v["ref"]["role"] == "observation")
    return {"verdict": "needs_review", "confidence": None, "rationale": "材料不足以确定性质。", "evidence_ids": [direct], "recommendations": [], **changes}


def test_five_field_adapter_preserves_judgment_and_existing_output_contract(samples):
    p = prepare(samples[0]["data"], samples[0]["source_map"], CONFIG)
    body = answer(p)
    result = parse(json.dumps(body), p)
    assert result.verdict == body["verdict"] and result.rationale == body["rationale"]
    assert result.generation_method == "template" and result.confidence is None
    assert result.score_state == "not_computed" and result.source_refs


@pytest.mark.parametrize("alter", [{"evidence_ids": []}, {"evidence_ids": ["N99_S999"]}, {"confidence": 1.2}, {"tenant_id": "extra"}])
def test_invalid_core_is_not_repaired(samples, alter):
    p = prepare(samples[0]["data"], samples[0]["source_map"], CONFIG)
    with pytest.raises(Exception):
        parse(json.dumps(answer(p, **alter)), p)


def test_five_field_definitive_basis_cannot_be_labels_only(samples):
    p = prepare(samples[0]["data"], samples[0]["source_map"], CONFIG)
    label = next(s for s, v in p["source_map"].items() if v["ref"]["role"] == "source_label")
    with pytest.raises(StoreError):
        parse(json.dumps(answer(p, verdict="benign", evidence_ids=[label])), p)


def test_output_duplicate_json_key_rejected(samples):
    p = prepare(samples[0]["data"], samples[0]["source_map"], CONFIG)
    raw = json.dumps(answer(p))[:-1] + ', "verdict":"benign"}'
    with pytest.raises(StoreError):
        parse(raw, p)
