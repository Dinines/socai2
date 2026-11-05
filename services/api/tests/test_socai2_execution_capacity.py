"""Local v2 dispatch/capacity checks; historical exports are read-only inputs."""
import asyncio
import copy
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.socai2 import baseline_analysis_contract as contract
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.baseline_analysis import budget_reason, messages, reserved_calls
from app.socai2.baseline_capacity import (
    final_reservation,
    final_wire_reason,
    remaining_seconds,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import FULL_EXECUTOR_VERSION, Limits
from app.socai2.baseline_dispatch import dispatch_followups, offered_bindings
from app.socai2.baseline_evidence_tools import catalog
from app.socai2.baseline_execution_schema import (
    compact_execution_wire,
    execution_format,
)
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_store import encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format
from test_socai2_followup_scope import frozen


def fixture():
    packet, answer = frozen()
    context = Context.model_validate(packet["context"])
    limits = Limits(max_model_calls=4, max_tokens=48000, max_tool_calls=4, max_rows_per_query=50,
        deadline_at=context.captured_at + timedelta(seconds=120), policy_version="local-v2-fixture")
    lake = SimpleNamespace(configured=lambda: True)
    options, bindings, _ = offered_bindings(catalog(context, "00000000-0000-0000-0000-000000000001"), limits, context.captured_at, [], lake)
    return packet, answer, context, limits, options, bindings


def execution_answer():
    packet, answer, context, _limits, options, bindings = fixture()
    for item in answer["followups"]:
        item.update(binding_id=None, priority="supporting")
        item["mode"] = "human"
    chosen = options[0]
    item = answer["followups"][0]
    item.update(mode="query", binding_id=chosen["binding_id"], priority="decision_critical",
        alert_ids=chosen["alert_ids"], object_keys=[], source_ids=[])
    return packet, answer, context, bindings


def test_execution_binding_is_visible_fixed_and_member_scoped():
    packet, answer, context, bindings = execution_answer()
    accepted = contract.parse(json.dumps(answer), packet["source_map"], context, packet["coverage"], bindings=bindings)
    assert accepted.followups[0].priority == "decision_critical"
    for field, value, reason in [("binding_id", "unoffered", "followup_binding_not_offered"),
            ("binding_id", None, "followup_binding_not_offered"),
            ("mode", "deep", "followup_binding_requires_query"),
            ("alert_ids", list(context.alerts)[:1], "followup_binding_member_mismatch")]:
        invalid = copy.deepcopy(answer)
        invalid["followups"][0][field] = value
        with pytest.raises(contract.AnalysisRejected, match=reason):
            contract.parse(json.dumps(invalid), packet["source_map"], context, packet["coverage"], bindings=bindings)
    # Future C6 proposals and historical C3 outputs retain their original shape.
    packet, original = frozen()
    contract.parse(json.dumps(original), packet["source_map"], context, packet["coverage"])
    assert "binding_id" not in delivery.Delivery.model_json_schema()["$defs"]["Followup"]["required"]


def test_direct_queries_never_call_deep_and_modes_do_not_shadow_each_other():
    _, answer, _, bindings = execution_answer()
    query = answer["followups"][0]
    deep = {**query, "mode": "deep", "binding_id": None}
    second = next(k for k in bindings if k != query["binding_id"])
    followups = [{**deep, "priority": "supporting"}, query, copy.deepcopy(query),
        {**query, "binding_id": second}, deep]
    service = SimpleNamespace(query_evidence=AsyncMock(return_value={"result": {"state": "completed"},
        "projection": {"reason": None}, "artifact_id": "query", "projection_id": "projection", "reused": False}),
        deepen=AsyncMock(return_value={"state": "completed", "stop_reason": "handoff",
            "deep_artifact_id": "deep", "answer": None}))
    routes = asyncio.run(dispatch_followups(service, "tenant", "case", "run", followups, bindings, gateway=None, lake=None))
    assert [r["followup_index"] for r in routes] == [1, 2, 3, 4, 0]
    assert service.query_evidence.await_count == 2 and service.deepen.await_count == 1
    assert routes[1]["reused"] and routes[-1]["reused"]
    assert all("deep_artifact_id" not in r for r in routes if r["mode"] == "query")
    service.deepen.reset_mock()
    service.query_evidence.reset_mock()
    asyncio.run(dispatch_followups(service, "tenant", "case", "run", [query], bindings, gateway=None, lake=None))
    service.query_evidence.assert_awaited_once()
    service.deepen.assert_not_awaited()


def test_supporting_query_preserves_deep_reuse_and_distinct_plan_projection_links():
    _, answer, _, bindings = execution_answer()
    query = {**answer["followups"][0], "priority": "supporting"}
    deep = {**query, "mode": "deep", "binding_id": None, "priority": "decision_critical"}
    second = next(k for k in bindings if k != query["binding_id"])
    followups = [deep, query, {**query, "binding_id": second}, copy.deepcopy(query)]
    service = SimpleNamespace(query_evidence=AsyncMock(side_effect=[
        {"result": {"state": "completed"}, "projection": {"reason": None},
            "artifact_id": "deep-query-receipt", "projection_id": "deep-query-projection", "reused": True},
        {"result": {"state": "completed"}, "projection": {"reason": None},
            "artifact_id": "new-query-receipt", "projection_id": "new-query-projection", "reused": False}]),
        deepen=AsyncMock(return_value={"state": "completed", "stop_reason": "handoff",
            "deep_artifact_id": "deep", "answer": None}))
    routes = asyncio.run(dispatch_followups(service, "tenant", "case", "run", followups, bindings, gateway=None, lake=None))
    assert [r["followup_index"] for r in routes] == [0, 1, 2, 3]
    assert [r["reused"] for r in routes] == [False, True, False, True]
    assert service.query_evidence.await_count == 2 and service.deepen.await_count == 1
    visible, planned = delivery_followups({"initial_analysis_artifact_id": "initial-plan", "routes": routes},
        {"analysis": {"followups": followups}})
    assert {r["followup_index"]: r["projection_id"] for r in visible["routes"] if "projection_id" in r} == {
        1: "deep-query-projection", 2: "new-query-projection", 3: "deep-query-projection"}
    assert len(planned) == 4 and all(c["required"] for c in planned)


@pytest.mark.parametrize("condition", ["disabled", "time", "tools", "hostless", "adapter", "window"])
def test_unavailable_bindings_cannot_be_selected(condition):
    _, _, context, limits, _, _ = fixture()
    source_catalog = catalog(context, "00000000-0000-0000-0000-000000000001")
    lake = SimpleNamespace(configured=lambda: condition != "disabled")
    if condition == "time":
        limits = limits.model_copy(update={"deadline_at": context.captured_at + timedelta(seconds=30)})
    elif condition == "tools":
        limits = limits.model_copy(update={"max_tool_calls": 0})
    elif condition == "hostless":
        source_catalog["bindings"] = {}
    elif condition == "adapter":
        lake.unavailable_reason = lambda _: "not_connected"
    elif condition == "window":
        for binding in source_catalog["bindings"].values():
            binding["scope"]["window_end"] = binding["scope"]["window_start"]
    options, mapping, _ = offered_bindings(source_catalog, limits, context.captured_at, [], lake)
    assert options == [] and mapping == {}


@pytest.mark.parametrize("protocol", ["chat_completions", "deepseek_responses"])
@pytest.mark.parametrize("run_index", range(3))
def test_frozen_two_member_candidates_admit_c3_and_final_without_losing_required_values(protocol, run_index):
    from diagnose_socai2_kafka_inputs_20261105 import DIRECTORY, one
    db = json.loads(max(DIRECTORY.glob("database-*.json")).read_text())
    run = [r for r in db["runs"] if r["stop_reason"] == "required_model_input_unavailable"][run_index]
    before = copy.deepcopy(run)
    rows = [a for a in db["artifacts"] if a["run_id"] == run["id"] and isinstance(a["content_json"], dict)]
    context = Context.model_validate(next(a["content_json"] for a in rows if a["schema_version"] == "socai2.baseline-context.v1"))
    rebuilt = asyncio.run(one(db, run))
    assert rebuilt["prepared"]["ready"] and not any(r["omitted"] for r in rebuilt["required"])
    gateway = SimpleNamespace(provider=protocol, schema_profile="standard", model="deepseek-flash")
    reservation = final_reservation(gateway, context)
    limits = Limits.model_validate(run["limits"]).model_copy(update={"max_tokens": 48000,
        "deadline_at": context.captured_at + timedelta(seconds=120)})
    prepared = next(a["content_json"] for a in rows if a["schema_version"] == "socai2.baseline-model-view.v4")
    tools = {a["id"]: a["content_json"] for a in rows if a["kind"] == "tool_response"}
    options, _bindings, _ = offered_bindings(catalog(context, "00000000-0000-0000-0000-000000000001"), limits, context.captured_at, [], SimpleNamespace(configured=lambda: True))
    prompt, sources = messages(prepared, context, tools, options)
    assert options and len(prompt[1]["content"].encode()) <= 8192 and len(encoded(prompt)) <= 12288
    canonical = {"model": gateway.model, "messages": prompt, "max_tokens": 3000, "temperature": 0,
        "response_format": response_format(contract.ExecutionAnalysis, sources, members=context.alerts,
            questions=[q.id for q in context.questions], objects=context.scope.object_keys,
            bindings=[o["binding_id"] for o in options])}
    canonical["response_format"] = execution_format(canonical["response_format"],
        {o["binding_id"]: _bindings[o["binding_id"]] for o in options})
    c3 = compact_execution_wire(prepare_request(gateway, canonical))
    assert budget_reason([], limits, len(encoded(c3)), context.captured_at, reserve_calls=1, reservation=reservation) is None
    p = rebuilt["prepared"]
    c6 = prepare_request(gateway, {**canonical, "messages": p["messages"], "response_format": response_format(
        delivery.Delivery, p["source_map"], members=context.alerts, questions=[q.id for q in context.questions], objects=context.scope.object_keys)})
    assert final_wire_reason(c6, reservation) is None
    # Even a maximal provider-reported first-call charge leaves the entire
    # reserved C6 request affordable. Actual usage is never replaced by bytes.
    actual = len(encoded(c3)) + 3000 + 256
    previous = [{"kind": "model", "state": "completed", "usage": {"usage_state": "reported", "total_tokens": actual}}]
    assert budget_reason(previous, limits, len(encoded(c6)), context.captured_at) is None
    assert run == before and run["limits"]["max_tokens"] == 24000


def test_reservation_protects_tokens_time_and_unknown_usage_without_changing_old_run():
    _, _, context, limits, _, _ = fixture()
    reservation = final_reservation(SimpleNamespace(provider="chat_completions", model="local"), context)
    previous = [{"kind": "model", "state": "completed", "usage": {"usage_state": "reported", "total_tokens": 15000}}]
    assert budget_reason(previous, limits, 14000, context.captured_at, reserve_calls=1, reservation=reservation) == "final_model_tokens_reserved"
    previous[0]["usage"] = {"usage_state": "unavailable", "total_tokens": None}
    assert budget_reason(previous, limits, 1, context.captured_at, reserve_calls=1, reservation=reservation) == "prior_model_usage_unknown"
    now = limits.deadline_at - timedelta(seconds=30)
    assert budget_reason([], limits, 1, now, reservation=reservation) == "final_model_time_reserved"
    assert remaining_seconds(limits, context.captured_at, reservation, "C3") == 90
    assert remaining_seconds(limits, context.captured_at, reservation, "C6") == 120
    assert reserved_calls({"executor_version": FULL_EXECUTOR_VERSION}, "C3") == 1
    assert reserved_calls({"executor_version": "socai2.baseline-executor.v1"}, "C3") == 1
    assert budget_reason([], limits.model_copy(update={"max_tokens": 24000}), 1000, context.captured_at) is None
