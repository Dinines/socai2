"""Direct routing and receipt checks; no generation or external query calls."""
import asyncio
import copy
from types import SimpleNamespace

import pytest
import test_socai2_case_model_boundary as base
from app.socai2.baseline_dispatch import dispatch_followups
from app.socai2.case_followup_input import build
from app.socai2.case_followup_output import deep_format
from app.socai2.followup_activity import activity, query_record

configured, sample = base.configured, base.sample


def test_frozen_goals_allow_material_analysis_without_a_query(sample):
    context, prepared = base.prepared_sample(sample)
    policy = prepared["case_boundary"]["followup_routing"]
    assert policy["version"] == "socai2.followup-routing.v1"
    assert policy["C3"] in prepared["messages"][0]["content"]
    assert policy["C3"] in prepared["case_boundary"]["c3_completion"]["system"]
    deep = build("Deep", context, prepared, {}, question_id="detection_facts")
    assert policy["Deep"] in deep["messages"][0]["content"]
    variants = deep_format(deep)["json_schema"]["schema"]["anyOf"]
    assert {row["properties"]["action"]["enum"][0] for row in variants} == {"answer", "handoff"}
    assert deep["binding_map"] == {} and deep["ready"]


@pytest.mark.parametrize("state,count,truncated,outcome", [
    ("completed", 2, False, "data"), ("completed", 0, False, "empty"),
    ("skipped", None, False, "not_queried"), ("failed", None, False, "failed"),
    ("unknown", None, False, "unknown"), ("completed", 0, True, "unknown")])
def test_activity_preserves_actual_receipt_and_distinguishes_results(state, count, truncated, outcome):
    result = {"artifact_id": "raw", "projection_id": "view", "reused": False,
        "result": {"tool_name": "process_activity", "state": state, "returned_rows": count, "truncated": truncated}}
    original = copy.deepcopy(result)
    record = query_record(result)
    assert record["outcome"] == outcome and record["returned_rows"] == count and result == original
    report = activity("analysis_with_queries", [record], disposition="handoff")
    assert report["disposition"] == "handoff" and report["queries"][0]["query_artifact_id"] == "raw"
    assert report["new_query_attempt_count"] == int(state != "skipped")
    # A completed answer or handoff alone contributes no query receipt.
    assert activity("material_analysis", disposition="answer")["new_query_attempt_count"] == 0


def test_dispatch_keeps_original_plan_and_does_not_count_reuse_twice():
    calls = []
    async def query(*args, **kwargs):
        calls.append(args)
        return {"artifact_id": "raw", "projection_id": "view", "reused": False,
            "projection": {"reason": None},
            "result": {"tool_name": "process_activity", "state": "completed", "returned_rows": 1, "truncated": False}}
    plan = [{"question_id": q, "mode": "query", "priority": "decision_critical", "binding_id": "B1"}
            for q in ("detection_facts", "member_relationships")]
    original = copy.deepcopy(plan)
    routes = asyncio.run(dispatch_followups(SimpleNamespace(query_evidence=query), None, None, None,
        plan, {"B1": {"binding_id": "frozen"}}, gateway=None, lake=None))
    assert len(calls) == 1 and plan == original
    assert [row["activity"]["new_query_attempt_count"] for row in routes] == [1, 0]
    assert all(row["query_artifact_id"] == "raw" for row in routes)
    assert routes[1]["activity"]["queries"][0]["reused"]


def test_handoff_and_graph_have_no_implicit_source_or_task_call():
    plan = [{"question_id": "authorization", "mode": mode, "priority": "supporting", "binding_id": None}
            for mode in ("human", "graph")]
    routes = asyncio.run(dispatch_followups(object(), None, None, None, plan, {}, gateway=None, lake=None))
    assert [row["state"] for row in routes] == ["handoff", "scheduled"]
    assert [row["activity"]["kind"] for row in routes] == ["material_handoff", "retained_graph"]
    assert all(row["activity"]["queries"] == [] for row in routes)
