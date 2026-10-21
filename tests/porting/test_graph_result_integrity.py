"""Normal graph output, first triage separation and visible model receipts."""
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.cost_telemetry import CostTracker, current_cost_tracker
from app.graph import runner
from app.investigator import ledger
from app.llm import tool_loop
from app.models.state import AgentStatus, InvestigationState
from app.tools.registry import Tool, ToolRegistry
from app.workers import fused_alert_consumer as consumer

# Reuse the explicitly disposable PostgreSQL fixture and first-result seed.
from test_graph_triage_usage_integrity import database, seed


@pytest.mark.asyncio
async def test_graph_result_and_reports_are_queryable_without_changing_triage(database):
    run, tenant, alert, first = await seed(database)
    state = InvestigationState(run_id=run, tenant_id=tenant, incident_id=uuid4(),
                               alert_summary="bounded graph result", findings=["first finding"])
    state.record_llm_exchange(agent="triage", purpose="triage", model="first", prompt="first prompt",
                              response="first response", duration_ms=1)

    class Graph:
        async def astream(self, mapping):
            result = InvestigationState.model_validate(mapping)
            result.findings.append("new investigation finding")
            result.status = AgentStatus.COMPLETED
            result.record_llm_exchange(agent="deep-investigator", purpose="tool_loop:1", model="unit",
                                      prompt="actual graph prompt", response="actual graph answer", duration_ms=2)
            current_cost_tracker().record(model="unit", prompt_tokens=9, completion_tokens=4, latency_ms=2)
            yield {"investigation": result.to_dict()}

    async with CostTracker(run_id=str(run), tenant_id=str(tenant), persist=False):
        result = await runner._run(Graph(), state, budget=runner.InvestigationBudget(max_seconds=5),
                                   persist=True, seq_start=1)
    assert result.findings[-1] == "new investigation finding"
    event = await database.fetchrow("SELECT * FROM investigation_events WHERE kind='graph_result'")
    assert json.loads(event["payload"])["completion"] == "completed"
    rows = await database.fetch("SELECT * FROM investigation_artifacts WHERE event_id=$1", event["id"])
    artifacts = {row["kind"]: row["content"] for row in rows}
    assert set(artifacts) == {"graph_result", "report_md", "report_html", "graph_llm_exchanges"}
    assert json.loads(artifacts["graph_result"])["findings"][-1] == "new investigation finding"
    assert "new investigation finding" in artifacts["report_md"] and "new investigation finding" in artifacts["report_html"]
    exchanges = json.loads(artifacts["graph_llm_exchanges"])
    assert len(exchanges) == 1 and exchanges[0]["prompt"] == "actual graph prompt"
    assert exchanges[0]["response"] == "actual graph answer"
    assert all(row["sha256"] == hashlib.sha256(row["content"].encode()).hexdigest() for row in rows)
    confirmation = dict(run_id=run, tenant_id=tenant, seq=event["seq"],
        state=json.loads(artifacts["graph_result"]), exchanges=exchanges,
        report_md=artifacts["report_md"], report_html=artifacts["report_html"], completion="completed")
    assert await ledger.persist_graph_result(**confirmation) == event["id"]
    with pytest.raises(ledger.LedgerPersistError, match="conflicts"):
        await ledger.persist_graph_result(**{**confirmation, "report_md": "different report"})
    assert await database.fetchval("SELECT count(*) FROM investigation_artifacts WHERE event_id=$1", event["id"]) == 4
    assert json.loads(await database.fetchval("SELECT payload FROM investigation_events WHERE run_id=$1 AND seq=1", run)) == first
    assert await database.fetchval("SELECT total_tokens FROM investigation_runs WHERE id=$1", run) == 50


@pytest.mark.asyncio
async def test_graph_result_artifacts_and_receipt_rollback_together(database):
    run, tenant, _, _ = await seed(database)
    state = InvestigationState(run_id=run, tenant_id=tenant, incident_id=uuid4()).to_dict()
    await database.execute("""
        CREATE FUNCTION pg_temp.reject_graph_artifact() RETURNS trigger LANGUAGE plpgsql AS
        $$ BEGIN RAISE EXCEPTION 'isolated graph artifact failure'; END $$;
        CREATE TRIGGER reject_graph_artifact BEFORE INSERT ON investigation_artifacts
        FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_graph_artifact()
    """)
    with pytest.raises(ledger.LedgerPersistError, match="transaction failed"):
        await ledger.persist_graph_result(run_id=run, tenant_id=tenant, seq=2, state=state,
            exchanges=[], report_md="report", report_html="<p>report</p>", completion="partial")
    assert await database.fetchval("SELECT count(*) FROM investigation_events WHERE kind='graph_result'") == 0
    assert await database.fetchval("SELECT count(*) FROM investigation_artifacts") == 0
    foreign = uuid4()
    with pytest.raises(ledger.LedgerPersistError, match="ownership"):
        await ledger.persist_graph_result(run_id=run, tenant_id=foreign, seq=2,
            state={**state, "tenant_id": str(foreign)}, exchanges=[],
            report_md="report", report_html="<p>report</p>", completion="completed")


@pytest.mark.asyncio
async def test_graph_node_failure_retains_readable_partial_result(database):
    run, tenant, alert, _ = await seed(database)
    state = InvestigationState(run_id=run, tenant_id=tenant, incident_id=uuid4())
    class Graph:
        async def astream(self, _):
            yield {"triage": {"findings": ["observed before failure"], "status": "running"}}
            raise RuntimeError("synthetic node error")
    result = await runner._run(Graph(), state, budget=runner.InvestigationBudget(max_seconds=5),
                               persist=True, seq_start=1)
    assert result.status is AgentStatus.FAILED and result.verdict == "needs_review"
    event = await database.fetchrow("SELECT payload FROM investigation_events WHERE kind='graph_result'")
    assert json.loads(event["payload"])["completion"] == "partial"
    report = await database.fetchval("SELECT content FROM investigation_artifacts WHERE kind='report_md'")
    assert "observed before failure" in report and "partial results" in report
    row = await database.fetchrow("SELECT status,total_tokens FROM investigation_runs WHERE id=$1", run)
    assert row["status"] == "completed" and row["total_tokens"] == 37
    from app.workers import triage_delivery
    first = await triage_delivery.lookup(run_id=run, tenant_id=tenant, alert_id=str(alert), workflow_version="unit-v1")
    assert first["verdict"] == "needs_review" and first["cost"]["tokens"] == 37


@pytest.mark.asyncio
async def test_tool_loop_receipt_records_visible_messages_and_tool_results_only(monkeypatch):
    state = InvestigationState(incident_id=uuid4(), tenant_id=uuid4())
    turns = 0

    class Model:
        model = "unit:visible"
        def bind_tools(self, _):
            return self

    async def safe(_, messages):
        nonlocal turns
        turns += 1
        if turns == 1:
            return SimpleNamespace(type="ai", content="", tool_calls=[{"id": "read-1", "name": "read", "args": {}}])
        return SimpleNamespace(type="ai", content=[{"type": "text", "text": "visible answer"},
            {"type": "reasoning", "text": "HIDDEN_REASONING_SENTINEL"}],
            additional_kwargs={"reasoning_content": "HIDDEN_PROVIDER_SENTINEL"}, tool_calls=[])

    monkeypatch.setattr(tool_loop, "safe_ainvoke", safe)
    out = await tool_loop.run_with_tools(Model(), system="visible system", user="visible user",
        registry=ToolRegistry([Tool(name="read", description="bounded read", parameters={"type": "object"},
                                   fn=lambda: {"observation": "actual tool result"})]),
        on_exchange=state.record_llm_exchange)
    assert turns == 2 and out["content"] == "visible answer"
    receipt = state.llm_exchanges[1]
    assert "visible user" in receipt["prompt"] and "actual tool result" in receipt["prompt"]
    assert "visible answer" in receipt["response"]
    assert json.loads(state.llm_exchanges[0]["response"])["tool_calls"][0]["name"] == "read"
    assert "HIDDEN" not in json.dumps(state.llm_exchanges)
    assert receipt["input_hash"] == hashlib.sha256(receipt["prompt"].encode()).hexdigest()


@pytest.mark.asyncio
async def test_deep_driver_attaches_the_actual_state_exchange_recorder(monkeypatch):
    from unittest.mock import AsyncMock
    from app.investigator import deep_investigation as deep
    state = InvestigationState(incident_id=uuid4(), tenant_id=uuid4(), alert_summary="bounded investigation")
    monkeypatch.setattr(deep, "ENABLED", True)
    monkeypatch.setattr(deep, "_resolve_tenant_skill", AsyncMock(return_value=None))
    monkeypatch.setattr(deep, "scoped_customer_tools", AsyncMock(return_value=([], [])))
    monkeypatch.setattr(deep, "build_mcp_toolset", AsyncMock(return_value=SimpleNamespace(tools=[], refusals=[])))
    monkeypatch.setattr(deep, "default_registry", lambda _: ToolRegistry())
    monkeypatch.setattr(deep, "investigation_tools", lambda _: [])
    async def loop(_, **kwargs):
        kwargs["on_exchange"](agent="deep-investigator", purpose="tool_loop:1", model="unit",
            prompt="visible driver prompt", response="visible driver answer", duration_ms=1)
        return {"content": "visible driver answer", "tool_trace": [], "iterations": 1, "truncated": False}
    monkeypatch.setattr(deep, "run_with_tools", loop)
    result = await deep.run_deep_investigation(state, llm=object())
    assert result.narrative == "visible driver answer"
    assert state.llm_exchanges[0]["prompt"] == "visible driver prompt"


@pytest.mark.asyncio
async def test_escalation_retains_returned_graph_state_without_mutating_first_triage(monkeypatch):
    state = InvestigationState(incident_id=uuid4(), tenant_id=uuid4(), status=AgentStatus.RUNNING,
                               verdict="needs_review", findings=["first triage"])
    before = state.to_dict()
    async def prefetch(**_):
        return {"sources_called": ["unit"]}
    async def graph(candidate, **_):
        candidate.findings.append("graph finding")
        candidate.status = AgentStatus.COMPLETED
        candidate.verdict = "true_positive"
        return candidate
    monkeypatch.setenv("AISOC_AGENT_ESCALATE_TO_GRAPH", "1")
    monkeypatch.setattr(consumer, "prefetch_context_bundle_dict", prefetch)
    monkeypatch.setattr(consumer, "run_escalation", graph)
    worker = consumer.FusedAlertTriageWorker(bootstrap_servers="unused")
    monkeypatch.setattr(worker, "_review_only", lambda: False)
    result = await worker._maybe_escalate(state, writer=SimpleNamespace(escalation_allowed=True, persists_cost=False))
    assert result is not state and result.findings[-1] == "graph finding"
    assert result.status is AgentStatus.COMPLETED
    assert state.to_dict() == before
