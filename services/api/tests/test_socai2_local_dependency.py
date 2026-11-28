"""Optional graph failures preserve final content without weakening provenance."""
import asyncio
import copy
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import test_socai2_c6_units as c6
from app.socai2 import baseline_graph_projection as graph
from app.socai2.baseline_delivery import BaselineDelivery
from app.socai2.baseline_delivery_projection import make_publication
from app.socai2.baseline_store import StoreError
from app.socai2.case_followup_loader import graph_candidates

mother = c6.mother


def bases():
    material, old_graph, new_graph = (str(uuid4()) for _ in range(3))
    rows = [{"id": material, "content_json": {"type": "materials"}},
        {"id": old_graph, "content_json": {"type": "graph_snapshot", "state": "completed",
            "captured_at": "2026-11-18T00:00:00+00:00", "input_artifact_ids": [material],
            "graph_artifact_id": str(uuid4()), "delivery_state": "partial"}},
        {"id": new_graph, "content_json": {"type": "graph_snapshot", "state": "failed",
            "captured_at": "2026-11-18T00:01:00+00:00", "input_artifact_ids": [material],
            "graph_artifact_id": None, "delivery_state": "none", "reason": graph.CAPACITY_FAILURE}}]
    return rows


@pytest.mark.parametrize("kind", ["failed", "stale", "not_built"])
def test_unavailable_graph_never_reads_or_reuses_earlier_graph(kind):
    rows = bases()
    if kind == "stale":
        rows.append({"id": str(uuid4()), "content_json": {"type": "query_projection"}})
    elif kind == "not_built":
        rows = rows[:1]
    # An empty artifact map makes any attempt to use the old graph fail.
    assert graph_candidates(rows, {}) == (kind, [])
    selected = BaselineDelivery(None).current_graph(rows)
    assert selected["state"] == kind and selected["graph_artifact_id"] is None


@pytest.mark.parametrize("mutation", [{"reason": "unclassified_failure"}, {"graph_artifact_id": str(uuid4())},
                                      {"state": "completed"}, {"delivery_state": "partial"}])
def test_untrusted_failure_shape_is_a_hard_error(mutation):
    rows = bases()
    rows[-1]["content_json"].update(mutation)
    with pytest.raises(StoreError, match="graph_snapshot_invalid"):
        graph_candidates(rows, {})


def test_qualified_final_conclusion_survives_absent_graph(mother):
    received = c6.receive(mother)
    _, prepared, context, comparison = mother
    prepared = copy.deepcopy(prepared)
    prepared["c6_delivery"] = received
    final = c6.Delivery.model_validate(received["full_delivery"])
    members = {UUID(a): {"read_state": "read", "analysis_state": "analyzed"} for a in context.alerts}
    result, limitations = make_publication(final, context, members, prepared, comparison,
        BaselineDelivery(None).current_graph(bases()), uuid4(), None)
    assert result.conclusion == final.conclusion.text
    assert result.terminal_state == "completed" and result.validation_state == "accepted"
    assert result.graph_artifact_id is None and result.delivery_state == "partial"
    assert {m.alert_id for m in result.members} == set(members)
    assert "source_graph_unavailable" in limitations


def test_known_failed_query_is_reused_and_missing_dependency_never_dispatches():
    from app.socai2.baseline_dispatch import dispatch_followups
    attempted = []

    async def query(*args, **kwargs):
        attempted.append(args[3])
        return {"reused": False, "artifact_id": str(uuid4()), "projection_id": str(uuid4()),
            "result": {"state": "failed", "tool_name": "process_activity", "returned_rows": None, "truncated": False},
            "projection": {"reason": "source_unavailable"}}

    item = {"question_id": "detection_facts", "mode": "query", "priority": "supporting", "binding_id": "B1"}
    routes = asyncio.run(dispatch_followups(SimpleNamespace(query_evidence=query), uuid4(), uuid4(), uuid4(),
        [item, {**item, "question_id": "member_relationships"}, {**item, "binding_id": "missing"}],
        {"B1": {"binding_id": "frozen-binding"}}, gateway=None, lake=None, allowed_indices={0, 1}))
    assert attempted == ["frozen-binding"]
    assert [r["state"] for r in routes] == ["failed", "failed", "skipped"]
    assert routes[1]["reused"] and routes[1]["query_artifact_id"] == routes[0]["query_artifact_id"]
    assert routes[2]["reason"] == "c3_followup_dependency_unavailable"


def test_executor_records_failed_graph_route_then_finalizes(monkeypatch):
    from app.socai2 import (
        baseline_analysis,
        baseline_executor,
        case_model_boundary,
        runtime_policy,
    )
    from app.socai2.baseline_contracts import FULL_EXECUTOR_VERSION

    # Isolate orchestration: the actual C5 capacity branch and real PG writes
    # are verified separately; this checks that its failure reaches routing.
    monkeypatch.setattr(runtime_policy, "execution_policy", lambda *_: None)
    monkeypatch.setattr(case_model_boundary, "selected_profile", lambda _: None)
    monkeypatch.setattr(baseline_executor, "offered_bindings", lambda *_: ([], {}, []))
    monkeypatch.setattr(baseline_executor, "final_reservation", lambda *_: {})
    monkeypatch.setattr(baseline_analysis, "reserved_calls", lambda *_: 0)
    from app.socai2 import baseline_evidence_tools
    monkeypatch.setattr(baseline_evidence_tools, "catalog", lambda *_: {"bindings": {}, "unsupported": []})
    run_id, case_id, c3_id, graph_receipt = (uuid4() for _ in range(4))
    run = {"id": run_id, "case_id": case_id, "state": "running", "executor_version": FULL_EXECUTOR_VERSION,
        "limits": {"max_model_calls": None, "max_tokens": None, "max_tool_calls": None,
            "max_rows_per_query": None, "deadline_at": None, "policy_version": "test"}, "input_artifact_id": uuid4()}
    store = SimpleNamespace(where=lambda table, *clauses: clauses, read_context=AsyncMock(return_value=object()),
        one=AsyncMock(side_effect=[None, {"output_artifact_id": c3_id}]), now=AsyncMock(return_value=datetime.now(UTC)))

    @asynccontextmanager
    async def transaction(*args, **kwargs):
        yield store

    followup = {"mode": "graph", "priority": "supporting", "question_id": "member_relationships", "binding_id": None}
    service = SimpleNamespace(transaction=transaction, enrich=AsyncMock(), prepare_evidence=AsyncMock(),
        analyze=AsyncMock(return_value={"state": "completed", "analysis": {"followups": [followup]},
            "basis": {"binding_map": {}, "stage_delivery": {"followup_unit_paths": ["$.followups[0]"],
                "dispatch_paths": ["$.followups[0]"]}}}),
        build_graph=AsyncMock(return_value={"state": "failed", "reason": graph.CAPACITY_FAILURE,
            "graph_artifact_id": None, "artifact_id": str(graph_receipt)}), finalize=AsyncMock(return_value="finalized"))
    gateway = SimpleNamespace(configure=AsyncMock(return_value=True))
    executor = baseline_executor.BaselineExecutor(service, uuid4(), gateway=gateway, lake=object())
    executor.locked = AsyncMock(return_value=run)
    executor.idle = AsyncMock()
    executor.record = AsyncMock(return_value=uuid4())
    assert asyncio.run(executor.execute(SimpleNamespace(case_id=case_id, run_id=run_id))) == "finalized"
    route = executor.record.call_args.args[3]["routes"][0]
    assert route["state"] == "failed" and route["reason"] == graph.CAPACITY_FAILURE
    assert route["graph_artifact_id"] is None
    assert executor.record.call_args.args[4][-1]["id"] == str(graph_receipt)
    service.build_graph.assert_awaited_once()
    service.finalize.assert_awaited_once()
