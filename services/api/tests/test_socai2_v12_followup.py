"""Conditional decisions and receipt-derived query facts for the 1.2 followup."""
import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import jsonschema
import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2.model_protocol import prepare_request
from app.socai2.program_facts import query_statuses
from test_socai2_stage_quality import source


KINDS = {"needs_review": None, "true_positive": "malicious_behavior",
         "false_positive": "refuted_detection", "benign": "authorized_or_expected_behavior"}


@pytest.mark.parametrize("protocol,profile", [("chat_completions", "standard"),
    ("chat_completions", "vllm_grammar_v1"), ("deepseek_responses", "standard")])
def test_actual_wire_rejects_every_conflicting_verdict_basis_and_unknown_source(protocol, profile):
    fmt = alert.constrained_response_format({"N1_S1": {}})
    body = prepare_request(SimpleNamespace(provider=protocol, schema_profile=profile),
        {"model": "test", "messages": [{"role": "user", "content": "test"}],
         "max_tokens": 3000, "temperature": 0, "response_format": fmt})
    schema = body["text"]["format"]["schema"] if protocol == "deepseek_responses" else body["response_format"]["json_schema"]["schema"]
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    for verdict, expected in KINDS.items():
        for kind in KINDS.values():
            value = {"verdict": verdict, "confidence": None, "rationale": "判断理由", "explanation": "行为解释",
                "evidence_ids": ["N1_S1"], "recommendations": [], "limitations": [],
                "decision_basis": None if kind is None else {"kind": kind, "claim": "明确主张", "source_ids": ["N1_S1"]}}
            assert validator.is_valid(value) == (kind == expected)
            if kind == expected:
                value["evidence_ids"] = ["N1_S99"]
                assert not validator.is_valid(value)


@pytest.mark.parametrize("state,count,truncated,outcome", [
    ("skipped", None, False, "not_queried"), ("failed", None, False, "failed"),
    ("timeout", None, False, "failed"), ("unknown", None, False, "unknown"),
    ("completed", 0, False, "empty"), ("completed", 0, True, "unknown"),
    ("completed", 2, True, "data"), ("completed", None, False, "unknown")])
def test_query_statuses_do_not_promote_missing_failed_or_truncated_receipts(state, count, truncated, outcome):
    identity = uuid4()
    payload = {"tool_name": "threat_intel", "state": state, "reason": "actual_reason",
        "returned_rows": count, "truncated": truncated}
    before = copy.deepcopy(payload)
    value = query_statuses([(identity, payload)])[0]
    assert value["outcome"] == outcome and value["returned_rows"] == count
    assert value["receipt"]["id"] == str(identity) and value["receipt"]["role"] == "execution_receipt"
    assert value["state"] == state and value["reason"] == "actual_reason" and payload == before


def test_skipped_ti_is_explicit_in_actual_model_input_without_changing_fusion_label():
    original = source()
    original["members"][0]["material"]["detection"]["reason"] = "no TI match"
    before = copy.deepcopy(original)
    receipt = {"tool_name": "threat_intel", "state": "skipped", "reason": "no_supported_frozen_objects",
        "returned_rows": None, "truncated": False, "limitations": [], "rows": None}
    messages, _, data = alert.build(original, uuid4(), [(uuid4(), receipt)])
    visible = json.loads(messages[1]["content"])
    facts = visible["program_facts"]["query_statuses"]
    assert facts == data["program_facts"]["query_statuses"]
    assert facts[0]["outcome"] == "not_queried" and facts[0]["returned_rows"] is None
    assert "本次未执行查询" in facts[0]["statement"] and original == before
