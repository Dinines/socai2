"""Frozen m2 scope and original-plan retention; no model or database calls."""
import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from app.socai2 import baseline_analysis_contract as contract
from app.socai2.baseline_context import Context
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_reasoning import bounded_input, fit_final_request
from app.socai2.baseline_store import StoreError, encoded
from app.socai2.model_input_view import items

ROOT = Path(__file__).resolve().parents[3]
M2 = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m2"


def frozen():
    packet = next(p for p in json.loads((M2 / "plan-and-packets.json").read_text("utf-8"))["packets"] if p["id"] == "C3-current")
    answer = next(p["answer"] for p in json.loads((M2 / "parsed-results.json").read_text("utf-8"))["cells"]
        if p["cell"] == "C3-current-deepseek")
    return packet, answer


def test_original_answer_preserved_but_cross_member_object_rejected():
    packet, answer = frozen()
    context = Context.model_validate(packet["context"])
    original = copy.deepcopy(answer)
    contract.parse(json.dumps(answer), packet["source_map"], context, packet["coverage"])
    human = answer["followups"][1]
    human["object_keys"] = ['["ip","198.51.100.20"]']
    with pytest.raises(contract.AnalysisRejected, match="followup_objects_outside_members"):
        contract.parse(json.dumps(answer), packet["source_map"], context, packet["coverage"])
    # A relation between both declared members legitimately uses their union.
    human["alert_ids"] = list(context.alerts)
    contract.parse(json.dumps(answer), packet["source_map"], context, packet["coverage"])
    _, saved = frozen()
    assert saved == original


def test_no_objects_does_not_fabricate_ownership_or_block_object_free_followup():
    packet, answer = frozen()
    for alert in packet["context"]["alerts"].values():
        alert["objects"] = []
    context = Context.model_validate(packet["context"])
    with pytest.raises(contract.AnalysisRejected, match="followup_objects_outside_members"):
        contract.parse(json.dumps(answer), packet["source_map"], context, packet["coverage"])
    for followup in answer["followups"]:
        followup["object_keys"] = []
    contract.parse(json.dumps(answer), packet["source_map"], context, packet["coverage"])


def plan():
    _, answer = frozen()
    original = copy.deepcopy(answer["followups"][1])
    answer["followups"] = [original, {**copy.deepcopy(original), "objective": "Confirm a different scoped maintenance change."}]
    dispatch = {"initial_analysis_artifact_id": str(uuid4()), "routes": [
        {"followup_index": i, "question_id": item["question_id"], "mode": item["mode"],
            "state": "handoff", "reason": "human_confirmation_required_no_task_created"}
        for i, item in enumerate(answer["followups"])]}
    return dispatch, {"analysis": answer, "validation": "structure_scope_sources_checked"}


def test_same_question_routes_bind_to_original_item_and_citable_path():
    dispatch, initial = plan()
    before = copy.deepcopy([dispatch, initial])
    dispatch["routes"].reverse()
    meta, candidates = delivery_followups(dispatch, initial)
    assert [r["followup_index"] for r in meta["routes"]] == [0, 1]
    assert meta["role"] == "execution_receipt" and meta["initial_analysis_artifact_id"] == dispatch["initial_analysis_artifact_id"]
    for i, candidate in enumerate(candidates):
        assert candidate["entry"]["value"]["execution_plan_index"] == i
        assert candidate["entry"]["value"]["followup"]["objective"] == initial["analysis"]["followups"][i]["objective"]
        ref = candidate["source"]["ref"]
        assert ref["id"] == dispatch["initial_analysis_artifact_id"]
        assert contract.citation_roles(initial)[ref["source_path"]] == "prior_analysis"
        assert "source_ids" not in candidate["entry"]["value"]["followup"]
    assert initial == before[1]


@pytest.mark.parametrize("failure", ["duplicate", "missing", "out_of_bounds", "bool_index", "changed_mode", "changed_question"])
def test_invalid_receipt_cannot_attach_to_another_proposal(failure):
    dispatch, initial = plan()
    if failure == "duplicate":
        dispatch["routes"][1]["followup_index"] = 0
    elif failure == "missing":
        dispatch["routes"].pop()
    elif failure == "out_of_bounds":
        dispatch["routes"][1]["followup_index"] = 2
    elif failure == "bool_index":
        dispatch["routes"][0]["followup_index"] = False
    elif failure == "changed_mode":
        dispatch["routes"][0]["mode"] = "deep"
    else:
        dispatch["routes"][0]["question_id"] = "member_relationships"
    with pytest.raises(StoreError, match="followup_dispatch_plan_mismatch"):
        delivery_followups(dispatch, initial)


def test_required_plan_survives_optional_wire_trimming_and_rejects_oversize():
    dispatch, initial = plan()
    meta, candidates = delivery_followups(dispatch, initial)
    for i, candidate in enumerate(candidates):
        candidate["entry"]["id"] = f"S{i}"
    optional = copy.deepcopy(candidates[0])
    optional.update(required=False)
    optional["entry"] = {**optional["entry"], "id": "S99", "value": {"old_summary": "x" * 1000}}
    prepared = bounded_input({"followup_execution": meta}, [*candidates, optional], "Keep original plan and actual receipt distinct.")
    assert prepared["ready"]
    assert len(prepared["messages"][1]["content"].encode()) <= 8192
    body = {"messages": prepared["messages"], "response_format": {"json_schema": {"schema": {
        "$defs": {"SourceId": {"enum": sorted(prepared["source_map"])}}}}}}
    fit_final_request(body, prepared, len(encoded(body)) - 500)
    visible = items(json.loads(body["messages"][1]["content"]))
    assert {v["value"]["execution_plan_index"] for v in visible} == {0, 1}
    assert all(s["required"] for s in prepared["source_map"].values())
    assert prepared["omissions"][-1]["reason"] == "remaining_final_token_budget"
    # No silent cutting of required plan text to keep a misleading status visible.
    candidates[0]["entry"]["value"]["followup"]["objective"] = "中" * 1000
    candidates[0]["original"] = candidates[0]["entry"]["value"]["followup"]
    stopped = bounded_input({"followup_execution": meta}, candidates, "same limits")
    assert not stopped["ready"] and stopped["reason"] == "required_model_input_unavailable"
    assert stopped["messages"] == [] and stopped["omissions"][0]["reason"] == "whole_field_exceeds_budget"


def test_unanswered_deep_and_human_handoff_remain_execution_receipts():
    dispatch, initial = plan()
    initial["analysis"]["followups"][0]["mode"] = "deep"
    dispatch["routes"][0].update(mode="deep", state="completed", reason="handoff", answer_available=False)
    meta, _ = delivery_followups(dispatch, initial)
    assert meta["routes"][0]["answer_available"] is False
    assert meta["routes"][1]["state"] == "handoff"
    assert delivery_followups(None, None) == (None, [])
    dispatch["routes"] = []
    initial["analysis"]["followups"] = []
    assert delivery_followups(dispatch, initial)[1] == []


@pytest.mark.parametrize("failure,reason", [("guard", "source_guard_blocked"), ("total_budget", "model_view_budget_exhausted")])
def test_required_plan_never_bypasses_guard_or_total_input_limit(failure, reason):
    dispatch, initial = plan()
    if failure == "guard":
        initial["analysis"]["followups"][0]["objective"] = '{"class_uid":4001,"activity_id":1}'
    else:
        item = initial["analysis"]["followups"][0]
        initial["analysis"]["followups"] = [{**item, "objective": f"Plan {i}: " + "x" * 800} for i in range(12)]
        dispatch["routes"] = [{**dispatch["routes"][0], "followup_index": i} for i in range(12)]
    meta, candidates = delivery_followups(dispatch, initial)
    for i, candidate in enumerate(candidates):
        candidate["entry"]["id"] = f"S{i}"
    prepared = bounded_input({"followup_execution": meta}, candidates, "unchanged budget")
    assert prepared["reason"] == "required_model_input_unavailable" and prepared["messages"] == []
    assert reason in {o["reason"] for o in prepared["omissions"]}
