"""Deep's retained answer is independent of executable control fields."""
import hashlib
import json
from uuid import uuid4

import pytest
import test_socai2_case_followup_boundary as base
from app.socai2 import case_deep_delivery as deep
from app.socai2 import case_followup_input as inputs
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import reference
from app.socai2.citation_quality import new_review

configured, sample = base.configured, base.sample


@pytest.fixture
def prepared():
    return {"source_map": {"E1": {"ref": reference("artifact", uuid4(), "observation"),
            "alert_ids": [str(uuid4())]}}, "binding_map": {"B1": "frozen-binding"},
        "case_boundary": {"question_id": "authorization"}, "citation_review": new_review()}


def answer():
    return {"state": "unresolved", "text": "原始结论：授权仍待核实。", "support_ids": ["E1"],
        "counter_ids": [], "alternatives": [], "limitations": ["尚无授权证明"]}


def content(**updates):
    return json.dumps({"action": "answer", "binding_id": None, "reason": "已分析当前材料", "answer": answer(),
        **updates}, ensure_ascii=False)


@pytest.mark.parametrize("finish_reason", ["stop", "length"])
def test_complete_reply_uses_same_receiver(prepared, finish_reason):
    text = content()
    out = deep.receive(text, prepared, uuid4(), finish_reason=finish_reason)
    assert out["decision"].answer.text == answer()["text"]
    assert out["delivery"]["state"] == "complete"
    assert out["parse"]["truncated"] == (finish_reason == "length")
    for unit in out["retained_units"]:
        start, end = unit["value_span"]
        assert json.loads(text[start:end]) == unit["value"]
        assert hashlib.sha256(text[start:end].encode()).hexdigest() == unit["value_sha256"]


def test_answer_survives_incomplete_control_without_inventing_action(prepared):
    text = '{"answer":' + json.dumps(answer(), ensure_ascii=False) + ',"action":"que'
    out = deep.receive(text, prepared, uuid4(), finish_reason="length")
    assert out["answer"] == answer() and out["decision"] is None
    assert out["delivery"]["state"] == "partial" and out["use"]["dispatch_paths"] == []
    assert [u["path"] for u in out["retained_units"]] == ["$.answer"]
    assert out["missing_units"]


@pytest.mark.parametrize("text", ["", " ", '{"answer":{"state":"unresolved","text":"半个',
    '{"answer":{"state":"unresolved","text":"\\u4'])
def test_no_complete_answer_is_not_filled(prepared, text):
    out = deep.receive(text, prepared, uuid4(), finish_reason="length")
    assert out["answer"] is None and out["decision"] is None
    assert out["delivery"]["state"] == "none" and out["use"]["dispatch_paths"] == []


@pytest.mark.parametrize("changes", [
    {"action": "query", "binding_id": "unoffered", "answer": None},
    {"action": "query", "binding_id": "B1"},
    {"action": "query", "binding_id": None, "answer": None},
    {"reason": ""}, {"reason": "x" * 1201}, {"action": "unsupported"},
])
def test_invalid_controls_never_dispatch_query(prepared, changes):
    out = deep.receive(content(**changes), prepared, uuid4())
    assert out["decision"] is None and out["use"]["dispatch_paths"] == [] and out["invalid_units"]
    if changes.get("answer", answer()) is not None:
        assert out["answer"] == answer()


def test_query_needs_complete_frozen_fields(prepared):
    out = deep.receive(content(action="query", binding_id="B1", answer=None), prepared, uuid4(), finish_reason="length")
    assert out["decision"].action == "query" and out["answer"] is None
    assert set(out["use"]["dispatch_paths"]) == {"$." + k for k in deep.FIELDS}
    text = '{"action":"query","binding_id":"B1","reason":"查询","answer":n'
    out = deep.receive(text, prepared, uuid4())
    assert out["decision"] is None and out["use"]["dispatch_paths"] == []


def test_duplicate_control_does_not_destroy_independent_answer(prepared):
    text = '{"answer":' + json.dumps(answer()) + ',"action":"answer","action":"query"}'
    out = deep.receive(text, prepared, uuid4())
    assert out["answer"] == answer() and out["decision"] is None
    assert all(u["path"] != "$.action" for u in out["retained_units"])
    assert any(g["reason_code"] == "duplicate_json_key" for g in out["invalid_units"])


def test_quality_is_recorded_but_answer_text_and_state_remain(prepared):
    raw = answer()
    raw.update(support_ids=["E1", "E1", "missing"], limitations=[])
    out = deep.receive(content(answer=raw), prepared, uuid4())
    assert out["decision"].answer.text == raw["text"] and out["decision"].answer.state == raw["state"]
    assert out["quality"]["state"] == "issues_recorded"
    unit = next(u for u in out["retained_units"] if u["path"] == "$.answer")
    assert unit["value"] == raw and [r["source_id"] for r in unit["resolved_refs"]] == ["E1"]


def test_live_parser_keeps_partial_answer_before_raising_control_error(prepared):
    prepared["citation_review"]["original_response_artifact_id"] = str(uuid4())
    text = '{"answer":' + json.dumps(answer()) + ','
    with pytest.raises(AnalysisRejected, match="deep_decision_incomplete_or_invalid"):
        deep.parser(prepared)(text)
    assert prepared["unit_delivery"]["answer"] == answer()


def test_c6_actual_builder_uses_retained_answer_as_prior_analysis(sample):
    context, prior, initial = base.fixture(sample)
    frozen = inputs.build("Deep", context, prior, {}, previous=initial, prior_id=uuid4(),
        question_id=context.questions[0].id)
    raw = answer()
    raw["support_ids"] = [next(sid for sid, row in frozen["source_map"].items() if row["ref"]["role"] != "execution_receipt")]
    text = '{"answer":' + json.dumps(raw) + ',"action":"a'
    out = deep.receive(text, frozen, uuid4(), finish_reason="length")
    aid = str(uuid4())
    summary = {"type": "deep_summary", "question_id": context.questions[0].id,
        "answer": out["answer"], "source_map": frozen["source_map"], "citation_review": out["quality"]}
    artifacts = {aid: {"content_json": summary}}
    actual = inputs.build("C6", context, prior, artifacts, previous=initial, prior_id=uuid4())
    rows = [r for r in actual["followup_boundary"]["records"] if r["block"] == "Deep"]
    assert len(rows) == 1 and rows[0]["value"]["text"] == raw["text"]
    assert rows[0]["ref"] == reference("artifact", aid, "prior_analysis", "$.answer")
    assert raw["text"] in actual["messages"][1]["content"]
    assert "value_span" not in actual["messages"][1]["content"]
    assert summary["answer"] == out["answer"]
