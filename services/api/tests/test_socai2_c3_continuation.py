"""D3b: bounded supplement, sparse downstream inputs and exact routing indices."""
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import test_socai2_c3_units as fixtures
import test_socai2_case_model_boundary as base
from app.socai2 import case_c3_completion_flow as flow
from app.socai2 import case_c3_delivery as units
from app.socai2 import case_followup_input as followup
from app.socai2 import case_output_adapter as output
from app.socai2.baseline_dispatch import dispatch_followups
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.case_citation_quality import VALIDATION
from app.socai2.citation_quality import new_review
from app.socai2.stage_delivery import VERSION

configured, sample = base.configured, base.sample
FIXTURES, mother = fixtures.FIXTURES, fixtures.mother


def first_reply(prepared, context, original_id=None):
    content = (FIXTURES / "f1-closed-f2-partial.txt").read_text()
    return units.receive(content, prepared, context, prepared["binding_map"], original_id or uuid4(), finish_reason="length")


def remainder(text, first):
    raw = json.loads(text)
    missing = units.completion_fields(first)
    reply = {key: raw[key] for key in missing}
    reply["findings"] = reply["findings"][1:]
    return reply


def test_supplement_completes_only_missing_units_without_rewriting_initial(mother):
    text, prepared, context = mother
    first = first_reply(prepared, context)
    before = copy.deepcopy(first)
    reply = remainder(text, first)
    second = units.receive(json.dumps(reply), prepared, context, prepared["binding_map"], uuid4(),
        prefix="$.supplement", prior_analysis=first["analysis"])
    actual = units.combine(first, second, units.completion_fields(first), prepared, context, prepared["binding_map"])
    assert actual["delivery"]["state"] == "complete" and actual["invalid_units"] == []
    assert first == before
    assert actual["retained_units"][:6] == first["retained_units"]
    assert [f["id"] for f in actual["analysis"]["findings"]] == ["F1", "F2", "F3", "F4", "F5"]
    assert actual["retained_units"][6]["path"] == "$.supplement.findings[0]"
    assert len(actual["analysis"]["questions"]) == 6
    assert not any(i["code"] == "unknown_domain_finding" for i in second["quality"]["issues"])


@pytest.mark.parametrize("reply", ["", "  ", '{"findings":[{"id":', '{"findings":[false]}'])
def test_unusable_supplement_keeps_all_initial_units(mother, reply):
    _, prepared, context = mother
    first = first_reply(prepared, context)
    second = units.receive(reply, prepared, context, prepared["binding_map"], uuid4(), prefix="$.supplement")
    result = units.combine(first, second, units.completion_fields(first), prepared, context, prepared["binding_map"])
    assert result["retained_units"] == first["retained_units"]
    assert result["analysis"] == first["analysis"] and result["delivery"]["state"] == "partial"
    assert "followups" not in result["analysis"] and result["use"]["dispatch_paths"] == []


def test_supplement_conflict_does_not_replace_first_finding(mother):
    text, prepared, context = mother
    first = first_reply(prepared, context)
    raw = json.loads(text)
    second = units.receive(json.dumps({"findings": raw["findings"][:2]}), prepared, context,
        prepared["binding_map"], uuid4(), prefix="$.supplement")
    result = units.combine(first, second, ["findings"], prepared, context, prepared["binding_map"])
    assert {"path": "$.supplement.findings[0]", "reason_code": "supplement_retained_unit_conflict"} in result["invalid_units"]
    assert result["analysis"]["findings"][0] == first["analysis"]["findings"][0]
    assert [f["id"] for f in result["analysis"]["findings"]] == ["F1", "F2"]


@pytest.mark.parametrize("mode", ["disabled", "budget_skip", "invalid_reply", "second_truncation", "complete"])
def test_live_completion_controller_is_bounded_and_saves_receipt(mother, configured, monkeypatch, mode):
    text, prepared, context = mother
    prepared = copy.deepcopy(prepared)
    ids = [uuid4() for _ in range(8)]
    tenant, case_id, run_id, stage_id, model_id, response_id, request_id, original_id = ids
    initial_text = (FIXTURES / "f1-closed-f2-partial.txt").read_text()
    prepared.update(ready=True, messages=prepared["body"]["messages"], citation_review=new_review(),
        unit_delivery=first_reply(prepared, context, original_id), received_finish_reason="length")
    if mode == "disabled":
        prepared["case_boundary"]["c3_completion"]["max_attempts"] = 0
    request = copy.deepcopy(prepared)
    original = {"type": "model_original_response", "request_artifact_id": str(request_id),
                "raw": {"choices": [{"message": {"content": initial_text}}]}}
    originals = {str(request_id): {"payload": request}, str(original_id): original}
    first = {"state": "completed", "id": model_id, "input_artifact_id": request_id}
    saved, calls, more = {}, [], {}

    class Store:
        async def now(self):
            return datetime.now(timezone.utc)

        async def save_input_artifact(self, case, run, identity, payload, **kwargs):
            saved[str(identity)] = {"payload": copy.deepcopy(payload), **kwargs}

    store = Store()

    class Service:
        @asynccontextmanager
        async def transaction(self, _tenant):
            yield store

    class Steps:
        def __init__(self, *_):
            pass

        async def locked(self, *_):
            return {"requested_by": uuid4()}

        async def save(self, store, run, step, payload, kind, refs=()):
            identity = uuid4()
            saved[str(identity)] = {"payload": copy.deepcopy(payload), "kind": kind, "refs": refs}
            return identity

        async def call(self, tenant, case, run, stage, code, extra, gateway, parser, **kwargs):
            calls.append(copy.deepcopy(extra))
            if mode == "budget_skip":
                return None, "final_model_call_reserved", None, None
            sid, rid, oid = uuid4(), uuid4(), uuid4()
            body = json.dumps(remainder(text, prepared["unit_delivery"])) if mode == "complete" else (
                '{"findings":[{"id":' if mode == "second_truncation" else " ")
            extra["citation_review"].update(original_response_artifact_id=str(oid))
            extra["received_finish_reason"] = "length" if mode == "second_truncation" else "stop"
            more.update({str(rid): {"payload": copy.deepcopy(extra)}, str(oid): {
                "type": "model_original_response", "request_artifact_id": str(rid),
                "raw": {"choices": [{"message": {"content": body}}]}}})
            parsed = parser(body)
            return parsed, None, sid, uuid4()

    async def read_originals(service, steps, tenant, case, run, mid, rid):
        return (first, originals, request) if mid == model_id else (None, more, None)

    monkeypatch.setattr(flow, "ModelSteps", Steps)
    monkeypatch.setattr(flow, "originals_for", read_originals)
    result = asyncio.run(flow.complete_sections(Service(), tenant, case_id, run_id, stage_id,
        prepared, context, prepared["binding_map"], output.output_format(prepared, context, prepared["binding_map"]),
        None, (None, None, model_id, response_id), schema="socai2.baseline-analysis.v3"))
    assert len(calls) == (0 if mode == "disabled" else 1)
    receipt = saved[str(result[3])]
    assert receipt["schema"] == VERSION
    value = receipt["payload"]
    assert value["delivery"]["state"] == ("complete" if mode == "complete" else "partial")
    assert value["retained_units"][:6] == prepared["unit_delivery"]["retained_units"]
    assert result[0].model_dump()["findings"][0]["id"] == "F1"
    assert prepared["stage_delivery_result"]["artifact_id"] == str(result[3])
    record = prepared["section_completion_result"]
    assert record["attempts"] == (0 if mode in {"disabled", "budget_skip"} else 1)
    if mode == "budget_skip":
        assert record["reason"] == "final_model_call_reserved" and record["state"] == "skipped"


@pytest.mark.parametrize("none", [False, True])
def test_sparse_or_absent_initial_analysis_reaches_current_c6(sample, none):
    context, prepared = base.prepared_sample(sample)
    answer = base.answer_for(prepared, context)
    aid = answer["members"][0]["alert_id"]
    answer["findings"] = [{"id": "F1", "state": "inferred", "statement": "  唯一保留的发现原文。\n",
        "alert_ids": [aid], "support_ids": answer["members"][0]["evidence_ids"],
        "counter_ids": [], "alternatives": [], "limitations": ["需核实。"]}]
    text = "" if none else json.dumps({k: answer[k] for k in ("summary", "members", "findings")}, ensure_ascii=False)
    received = units.receive(text, prepared, context, {}, uuid4())
    previous = {"analysis": received["analysis"] if not none else None,
        "source_map": prepared["source_map"], "validation": VALIDATION if not none else "not_accepted",
        "basis": {"stage_delivery": units.summary(received, uuid4()), "citation_review": received["quality"]}}
    before = copy.deepcopy(previous)
    built = followup.build("C6", context, prepared, {}, previous=previous, prior_id=uuid4(),
        extra={"comparison": {"state": "initial", "result_id": None}})
    assert built["ready"] and previous == before
    if none:
        assert "C3没有可用的模型分析内容" in built["messages"][1]["content"]
        assert not any(row["block"] == "C3" for row in built["followup_boundary"]["records"])
    else:
        row = next(row for row in built["followup_boundary"]["records"] if row["block"] == "C3")
        assert row["ref"]["role"] == "prior_analysis" and row["ref"]["source_path"] == "$.analysis"
        assert "唯一保留的发现原文。" in built["messages"][1]["content"]
        assert "C3仅完成已列出的部分" in built["messages"][1]["content"]
        assert "questions" not in row["value"] and "followups" not in row["value"]


def test_non_dispatchable_plan_keeps_its_original_index_and_does_not_call_tools():
    plans = [{"question_id": "detection_facts", "mode": "query", "priority": "decision_critical",
        "binding_id": "not-executable", "alert_ids": [str(uuid4())]},
        {"question_id": "authorization", "mode": "human", "priority": "supporting", "binding_id": None,
         "alert_ids": [str(uuid4())]}]
    routes = asyncio.run(dispatch_followups(SimpleNamespace(), None, None, None, plans, {},
        gateway=None, lake=None, allowed_indices={1}))
    assert [(r["followup_index"], r["state"]) for r in routes] == [(0, "skipped"), (1, "handoff")]
    assert routes[0]["reason"] == "c3_followup_dependency_unavailable"
    execution, selected = delivery_followups({"initial_analysis_artifact_id": str(uuid4()), "routes": routes},
                                            {"analysis": {"followups": plans}})
    assert [p["entry"]["value"]["execution_plan_index"] for p in selected] == [0, 1]
    assert execution["routes"][0]["state"] == "skipped"
