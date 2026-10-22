"""The real orchestration must hand off and persist its prefetched context.

Only model runners, the workflow executor and storage transport are doubled.
No model, HTTP service or database is contacted by these contracts.
"""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.context.bundle import ContextBundle
from app.investigator import ledger, orchestrator as manual
from app.models.state import AgentStatus, InvestigationState
from app.orchestrator import router


@pytest.fixture
def material(monkeypatch):
    for key in ("DATABASE_URL", "DATABASE_DSN"):
        monkeypatch.delenv(key, raising=False)
    async def no_http(*_args, **_kwargs):
        pytest.fail("orchestration contract unexpectedly attempted HTTP")
    monkeypatch.setattr(httpx.AsyncClient, "send", no_http)
    tenant, case, run, alert = uuid4(), uuid4(), uuid4(), uuid4()
    context = {
        "tenant_id": str(tenant), "case_id": str(case), "alert_id": str(alert), "scope": "case",
        "queried_at": "2026-10-21T12:00:00Z",
        "model_summary": "Candidate linked-alert-2 shares HOST-A; source=postgres. Association is not confirmed attack causality.",
        "attack_chain": {"status": "success", "source": "postgres", "query": {"window": "24h"},
                         "data": {"chain": [{"alert_id": "linked-alert-2", "shared_entities": [{"kind": "host", "value": "HOST-A"}]}]}, "error": None},
        "attack_path": {"status": "success", "source": "neo4j", "fallback": False,
                        "data": {"nodes": [{"id": str(case), "label": "Case"}], "edges": []}, "error": None},
        "alert_graph": {"status": "empty", "source": "neo4j", "data": {"neighbors": {}, "blast_radius": {}}, "error": None},
    }
    bundle = ContextBundle(incident_id=case, tenant_id=str(tenant), attack_context=context).model_dump(mode="json")
    return SimpleNamespace(tenant=tenant, case=case, run=run, alert=alert, context=context, bundle=bundle)


def _ledger_spy(monkeypatch, tenant):
    for name in ("record_event", "complete_run", "record_artifact"):
        monkeypatch.setattr(ledger, name, AsyncMock())
    monkeypatch.setattr(ledger, "start_run", AsyncMock(return_value=tenant))
    return ledger.record_artifact


def _assert_context_artifacts(spy, material):
    calls = [call.kwargs for call in spy.await_args_list if call.kwargs.get("kind") in {"attack_chain", "attack_path", "alert_graph"}]
    assert len(calls) == 3
    assert {call["kind"] for call in calls} == {"attack_chain", "attack_path", "alert_graph"}
    for call in calls:
        assert call["run_id"] == material.run and call["tenant_id"] == material.tenant
        saved = json.loads(call["content"])
        assert saved["case_id"] == str(material.case)
        assert saved["model_summary"] == material.context["model_summary"]
        assert saved[call["kind"]] == material.context[call["kind"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["run", "stream"])
@pytest.mark.parametrize("topology", ["sequential", "parallel"])
async def test_router_domain_receives_same_prefetched_bundle(material, monkeypatch, surface, topology):
    seen = []
    async def triage(state):
        state.verdict, state.confidence, state.status = "needs_review", 0.5, AgentStatus.RUNNING
        return state
    async def identity(state, *, bundle=None):
        seen.append(bundle)
        state.verdict, state.confidence = "true_positive", 0.7
        state.add_finding("Domain received candidate context")
        return state
    monkeypatch.setattr(router, "_run_auto_triage_step", triage)
    monkeypatch.setattr(router, "_resolve_runner", lambda _signal: identity)
    artifacts = _ledger_spy(monkeypatch, material.tenant)
    state = InvestigationState(run_id=material.run, incident_id=material.case, tenant_id=material.tenant,
        alert_summary="identity authentication", raw_alert={"username": "alice"}, context_bundle=material.bundle)
    orchestrator = router.RouterOrchestrator()
    if surface == "run":
        final, _ = await orchestrator.run(state, topology=topology)
        assert final.status == AgentStatus.COMPLETED
    else:
        events = [event async for event in orchestrator.stream(state, topology=topology)]
        assert events[-1]["type"] == "done"
        assert "linked-alert-2" in events[-1]["state"]["report_md"]
        _assert_context_artifacts(artifacts, material)
    assert seen
    assert all(isinstance(bundle, ContextBundle) for bundle in seen)
    assert all(bundle.attack_context == material.context for bundle in seen)


class _Tracker:
    def __init__(self, **_kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *_args):
        pass
    def summary(self):
        return {"total_tokens": 0, "measured_call_count": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["run", "stream"])
async def test_default_orchestrator_persists_three_context_artifacts_on_the_run(material, monkeypatch, surface):
    monkeypatch.setattr(manual, "prefetch_context_bundle_dict", AsyncMock(return_value=material.bundle))
    monkeypatch.setattr(manual, "CostTracker", _Tracker)
    artifacts = _ledger_spy(monkeypatch, material.tenant)
    class Workflow:
        async def ainvoke(self, state):
            assert state["context_bundle"] == material.bundle
            return {**state, "status": "completed", "report_md": "# Bounded local report"}
        async def astream(self, state):
            yield {"report_writer": await self.ainvoke(state)}
    orchestrator = object.__new__(manual.InvestigatorOrchestrator)
    orchestrator._graph = Workflow()
    args = dict(case_id=str(material.case), tenant_id=str(material.tenant), run_id=material.run,
                alert_summary="supplied alert", raw_alert={"case_id": str(material.case)})
    if surface == "run":
        final = await orchestrator.run(**args)
        assert final.status == "completed"
    else:
        events = [event async for event in orchestrator.stream(**args)]
        assert events[-1]["type"] == "done"
    _assert_context_artifacts(artifacts, material)


class _ContextManager:
    def __init__(self, value):
        self.value = value
    async def __aenter__(self):
        return self.value
    async def __aexit__(self, *_args):
        pass


@pytest.mark.asyncio
async def test_graph_result_transaction_includes_run_context_artifacts_and_matching_receipt(material, monkeypatch):
    conn = SimpleNamespace(execute=AsyncMock(), fetchrow=AsyncMock(side_effect=[{"id": material.run}, {"id": uuid4()}]))
    conn.transaction = lambda: _ContextManager(conn)
    pool = SimpleNamespace(acquire=lambda: _ContextManager(conn))
    monkeypatch.setattr(ledger, "get_pool", AsyncMock(return_value=pool))
    monkeypatch.setattr(ledger, "_set_rls_context", AsyncMock())
    await ledger.persist_graph_result(run_id=material.run, tenant_id=material.tenant, seq=10,
        state={"run_id": str(material.run), "tenant_id": str(material.tenant), "context_bundle": material.bundle},
        exchanges=[], report_md="# Report", report_html="<p>Report</p>", completion="completed")
    saved = {call.args[5]: call.args for call in conn.execute.await_args_list if "INSERT INTO investigation_artifacts" in call.args[0]}
    # call.args[0] is SQL, followed by id/run/event/tenant/kind/content/hash/size.
    for kind in ("attack_chain", "attack_path", "alert_graph"):
        args = saved[kind]
        assert args[2] == material.run and args[4] == material.tenant
        content = json.loads(args[6])
        assert content["case_id"] == str(material.case) and content[kind] == material.context[kind]
        assert args[7] == hashlib.sha256(args[6].encode()).hexdigest()
    event = conn.fetchrow.await_args_list[1]
    receipt = json.loads(event.args[6])
    assert {row["kind"] for row in receipt["artifacts"]} >= {"attack_chain", "attack_path", "alert_graph"}
