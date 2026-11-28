"""A/I closed units and existing result contract, without manufactured answers."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.socai2 import ai_delivery_store, ai_stage_delivery
from app.socai2.baseline_store import digest, encoded
from app.socai2.stage_delivery import validate_sources


@pytest.fixture
def prepared():
    a, b, mid = map(str, (uuid4(), uuid4(), uuid4()))
    sources = {"N1_S1": {"ref": {"type": "alert_material", "id": mid, "external": None,
        "source_path": "$.raw_json.process.pid", "row_keys": [], "role": "observation"}, "alert_ids": [a]},
        "N1_S2": {"ref": {"type": "alert_material", "id": mid, "external": None,
        "source_path": "$.raw_json.process.name", "row_keys": [], "role": "observation"}, "alert_ids": [b]}}
    return {"source_map": sources, "member_aliases": {a: "A1", b: "A2"}, "data": {
        "citations": "structured_v3", "prose_alias_format": "namespaced_v1", "items": [],
        "omissions": {}, "source_statuses": [], "material_state": "complete", "members": [
            {"alert_id": aid, "included": 2, "triage_eligible": False, "triage_freshness": "unavailable"} for aid in (a, b)]},
        "fact_refs": [], "fact_text": "原始行为：进程已启动。"}


def answer(stage):
    if stage == "A":
        return {"verdict": "needs_review", "confidence": None, "rationale": "需核实登录的授权。",
                "evidence_ids": ["N1_S1"], "recommendations": [{"reason": "核实授权。", "source_ids": ["N1_S1"]}]}
    return {"diagnosis": {"summary": "记录中存在登录及外联。", "conclusion": "需核实行为关联。",
                         "source_ids": ["N1_S1", "N1_S2"], "limitations": []},
        "members": [{"alert_ref": alias, "state": "unresolved", "assessment": "已阅读本成员记录。",
                     "source_ids": [sid], "limitations": []} for alias, sid in (("A1", "N1_S1"), ("A2", "N1_S2"))],
        "findings": [{"statement": text, "state": "inferred", "alert_refs": ["A1"], "source_ids": ["N1_S1"], "limitations": []}
                     for text in ("发现一。", "发现二。")], "open_questions": []}


def receive(stage, content, prepared, **kwargs):
    text = json.dumps(content, ensure_ascii=False) if not isinstance(content, str) else content
    return ai_stage_delivery.receive(stage, text, prepared, uuid4(), **kwargs)


@pytest.mark.parametrize("verdict", ["malicious", "benign", "false_positive", "needs_review", None, "invalid", "duplicate"])
def test_incident_verdict_is_independent_of_the_diagnosis(prepared, verdict):
    from app.socai2.business_verdict import PATH, VERSION

    prepared["business_verdict_version"] = VERSION
    body = answer("I")
    if verdict == "duplicate":
        body["business_verdict"] = "needs_review"
        content = json.dumps(body)[:-1] + ', "business_verdict": "benign"}'
    else:
        if verdict is not None:
            body["business_verdict"] = verdict
        content = json.dumps(body)
    got = receive("I", content, prepared)
    valid = verdict not in {None, "invalid", "duplicate"}
    assert got["result"].conclusion == body["diagnosis"]["conclusion"]
    assert got["result"].business_verdict == (verdict if valid else None)
    assert got["delivery"]["state"] == ("complete" if valid else "partial")
    if valid:
        unit, = [u for u in got["retained_units"] if u["path"] == PATH]
        start, end = unit["value_span"]
        assert json.loads(content[start:end]) == verdict
    else:
        assert any(gap["path"] == PATH for gap in got["missing_units"] + got["invalid_units"])


@pytest.mark.parametrize("stage", ["A", "I"])
@pytest.mark.parametrize("finish", ["stop", "length"])
def test_full_answer_keeps_result_and_every_original_value(stage, finish, prepared):
    raw = answer(stage)
    text = json.dumps(raw, ensure_ascii=False)
    result = receive(stage, text, prepared, finish_reason=finish)
    assert result["result"] is not None and result["delivery"]["state"] == "complete"
    assert result["parse"]["state"] == "complete_json" and result["parse"]["truncated"] == (finish == "length")
    for unit in result["retained_units"]:
        start, end = unit["value_span"]
        assert json.loads(text[start:end]) == unit["value"]
        assert hashlib.sha256(text[start:end].encode()).hexdigest() == unit["value_sha256"]
    if stage == "A":
        assert result["result"].rationale == raw["rationale"] and result["result"].confidence is None
    else:
        assert result["result"].conclusion == raw["diagnosis"]["conclusion"]
        assert len(result["validated_members"]) == 2


def test_alert_rationale_alone_does_not_manufacture_verdict_or_confidence(prepared):
    result = receive("A", '{"rationale":"保留这段说明。","confidence":0.', prepared)
    assert result["analysis"] == {"rationale": "保留这段说明。"}
    assert result["result"] is None and not result["use"]["conclusion_available"]


def test_alert_partial_advice_keeps_core_without_claiming_explicit_empty(prepared):
    raw = answer("A")
    text = json.dumps(raw, ensure_ascii=False)
    cut = text.index('"recommendations"')
    result = receive("A", text[:cut] + '"recommendations":[{"reason":"半', prepared)
    assert result["result"].verdict == raw["verdict"]
    assert "recommendations" not in result["analysis"]
    assert result["delivery"]["state"] == "partial" and result["missing_units"]
    assert "stage_output_incomplete_see_stage_delivery" in result["result"].limitations


def test_incident_closed_finding_survives_half_next_item(prepared):
    text = json.dumps(answer("I"), ensure_ascii=False)
    cut = text.index("发现二") + 1
    result = receive("I", text[:cut], prepared, finish_reason="length")
    assert result["result"].conclusion == answer("I")["diagnosis"]["conclusion"]
    assert [f.id for f in result["result"].findings if f.id.startswith("F")] == ["F1"]
    assert "open_questions" not in result["analysis"] and result["delivery"]["state"] == "partial"
    assert result["parse"]["truncated"]


def test_incident_diagnosis_without_members_is_unscoped_partial_text(prepared):
    result = receive("I", {"diagnosis": answer("I")["diagnosis"]}, prepared)
    assert result["result"] is None
    assert result["analysis"]["diagnosis"]["conclusion"] == answer("I")["diagnosis"]["conclusion"]
    assert all(u["declared_scope"] is None for u in result["retained_units"])
    assert "members" not in result["analysis"]


def test_invalid_scope_and_duplicate_member_are_local_not_silent_relabel(prepared):
    raw = answer("I")
    raw["members"].append(copy.deepcopy(raw["members"][0]))
    raw["findings"][0]["alert_refs"] = ["unknown"]
    result = receive("I", raw, prepared)
    assert result["result"] is None and len(result["analysis"]["members"]) == 1
    assert [u["path"] for u in result["retained_units"] if u["kind"] == "findings"] == ["$.findings[1]"]
    assert {u["path"] for u in result["invalid_units"]} == {"$.members[0]", "$.members[2]", "$.findings[0]"}


def test_finding_original_index_kept_after_invalid_item(prepared):
    raw = answer("I")
    raw["findings"][0]["alert_refs"] = ["unknown"]
    result = receive("I", raw, prepared)
    assert [f.id for f in result["result"].findings if f.id.startswith("F")] == ["F2"]
    assert result["delivery"]["state"] == "partial"


def test_quality_does_not_delete_claim_or_widen_declared_scope(prepared):
    raw = answer("I")
    raw["findings"][0]["source_ids"] = ["N1_S2", "N1_S2", "unknown"]
    result = receive("I", raw, prepared)
    assert result["result"] is not None and result["quality"]["state"] == "issues_recorded"
    unit = next(u for u in result["retained_units"] if u["path"] == "$.findings[0]")
    assert unit["value"] == raw["findings"][0] and unit["declared_scope"] == {"alert_refs": ["A1"]}
    assert [r["source_id"] for r in unit["resolved_refs"]] == ["N1_S2"]


@pytest.mark.parametrize("text", ['', '  ', '{"confidence":0.', '{"rationale":"未闭合\\u4'])
def test_no_complete_unit_yields_none(text, prepared):
    result = receive("A", text, prepared)
    assert result["delivery"]["state"] == "none" and result["result"] is None


def test_duplicate_nested_key_excludes_conflicting_diagnosis(prepared):
    text = '{"diagnosis":{"summary":"原说明","summary":"冲突"},"members":[]}'
    result = receive("I", text, prepared)
    assert result["retained_units"] == [] and result["result"] is None
    assert any(g["reason_code"] == "duplicate_json_key" for g in result["invalid_units"])


@pytest.mark.asyncio
async def test_save_strict_receipt_from_unchanged_artifacts(prepared):
    from unittest.mock import AsyncMock
    request_id, original_id, run_id, input_id, stage_id = (uuid4() for _ in range(5))
    text = json.dumps(answer("I"), ensure_ascii=False)
    request = {"body": {"messages": []}}
    original = {"raw": {"choices": [{"message": {"content": text}, "finish_reason": "length"}]}}
    source = {str(request_id): request, str(original_id): original}
    store = AsyncMock()
    store.tenant_id = uuid4()
    store.where = lambda table, *args: args
    store.now.return_value = datetime.now(timezone.utc)
    store.one.side_effect = [{"content_json": v, "material_state": "complete", "sha256": digest(v), "size_bytes": len(encoded(v))}
                             for v in source.values()]
    received = ai_stage_delivery.receive("I", text, prepared, original_id, finish_reason="length")
    received["finish_reason"] = "length"
    _, value = await ai_delivery_store.save(store,
        {"id": run_id, "kind": "incident_diagnosis", "incident_id": uuid4(), "input_artifact_id": input_id},
        stage_id, request_id, original_id, received)
    assert validate_sources(value, source).delivery.state == "complete"
    assert value["execution"]["local_state"] == "ended"
    insert_values = store.db.execute.call_args_list[0].args[0].compile().params
    assert insert_values["incident_id"] is not None and insert_values["run_id"] == run_id
    assert insert_values["step_id"] == stage_id and insert_values["schema_version"] == value["schema_version"]
    assert insert_values["content_json"] == value


@pytest.mark.parametrize('stage', ['A', 'I'])
@pytest.mark.parametrize('failure', ['choices', 'tool_calls', 'refusal', 'usage_unknown', 'usage_exceeds'])
def test_receiving_units_does_not_bypass_existing_protocol_or_budget(stage, failure, prepared):
    from app.socai2.baseline_analysis_model import usage
    payload = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(answer(stage))}}],
               'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}}
    if failure == 'choices':
        payload['choices'].append(copy.deepcopy(payload['choices'][0]))
    elif failure in {'tool_calls', 'refusal'}:
        payload['choices'][0]['message'][failure] = ['unexpected'] if failure == 'tool_calls' else 'refused'
    elif failure == 'usage_unknown':
        payload.pop('usage')
    received = ai_delivery_store.receive_payload(stage, payload, prepared, uuid4(), usage(payload),
        {'reserved_token_upper_bound': 20 if failure == 'usage_exceeds' else 100})
    assert received['result'] is None and received['delivery']['state'] == 'none'
    assert received['rejection'] and received['retained_units'] == []


@pytest.mark.parametrize('stage', ['A', 'I'])
def test_existing_responses_protocol_locates_actual_original_text(stage, prepared):
    from app.socai2.baseline_analysis_model import usage
    payload = {'object': 'response', 'status': 'completed', 'output': [
        {'type': 'reasoning'}, {'type': 'message', 'role': 'assistant', 'status': 'completed',
            'content': [{'type': 'output_text', 'text': json.dumps(answer(stage))}]}],
        'usage': {'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30}}
    received = ai_delivery_store.receive_payload(stage, payload, prepared, uuid4(), usage(payload),
        {'reserved_token_upper_bound': 100})
    assert received['result'] is not None and received['delivery']['state'] == 'complete'
    assert all(u['original_content_path'] == '$.raw.output[1].content[0].text' for u in received['retained_units'])
