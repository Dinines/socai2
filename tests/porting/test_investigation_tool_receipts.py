"""Completed tool material is atomic, tenant-bound and never overwritten."""
import hashlib
import json
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.investigator import ledger
from app.investigator import deep_investigation as deep
from app.graph import runner
from app.llm import tool_loop
from app.models.state import InvestigationState
from app.tools.registry import Tool, ToolRegistry
from langchain_core.messages import AIMessage
from test_graph_triage_usage_integrity import database, seed


def tool_entry():
    return {"tool": "authentication_events", "args": {"user_name": "unit-user"},
            "call_id": "read-1", "iteration": 1, "status": "success", "available": True,
            "result_text": '{"rows":[{"message":"合成记录"}]}', "result_preview": "preview",
            "result_truncated": False, "duration_ms": 3}


@pytest.mark.asyncio
async def test_tool_receipt_roundtrip_and_conflict_preserve_first(database):
    run, tenant, _, first = await seed(database)
    entry = tool_entry()
    receipt = await ledger.record_tool_result(run_id=run, tenant_id=tenant, seq=10000,
                                             entry={**entry, "ledger_status": "pending"})
    assert receipt
    row = await database.fetchrow("SELECT * FROM investigation_artifacts WHERE kind='tool_result'")
    event = await database.fetchrow("SELECT * FROM investigation_events WHERE seq=10000")
    assert str(row["event_id"]) == receipt["event_id"] == str(event["id"])
    assert str(row["id"]) == receipt["artifact_id"]
    assert json.loads(row["content"]) == entry
    assert row["size_bytes"] == len(row["content"].encode("utf-8"))
    assert row["sha256"] == hashlib.sha256(row["content"].encode()).hexdigest()
    assert event["output_hash"] == hashlib.sha256(entry["result_text"].encode()).hexdigest()
    assert "result_text" not in json.loads(event["payload"])
    assert "ledger_status" not in json.loads(event["payload"])
    assert await ledger.record_tool_result(run_id=run, tenant_id=tenant, seq=10000,
                                          entry={**entry, "result_text": "changed"}) is None
    assert await database.fetchval("SELECT count(*) FROM investigation_artifacts") == 1
    assert json.loads(await database.fetchval("SELECT payload FROM investigation_events WHERE seq=1")) == first


@pytest.mark.asyncio
async def test_tool_receipt_failure_rolls_back_and_foreign_tenant_cannot_write(database):
    run, tenant, _, _ = await seed(database)
    assert await ledger.record_tool_result(run_id=run, tenant_id=uuid4(), seq=10000, entry=tool_entry()) is None
    await database.execute("""
        CREATE FUNCTION pg_temp.reject_tool_artifact() RETURNS trigger LANGUAGE plpgsql AS
        $$ BEGIN RAISE EXCEPTION 'isolated artifact failure'; END $$;
        CREATE TRIGGER reject_tool_artifact BEFORE INSERT ON investigation_artifacts
        FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_tool_artifact()
    """)
    assert await ledger.record_tool_result(run_id=run, tenant_id=tenant, seq=10000, entry=tool_entry()) is None
    assert await database.fetchval("SELECT count(*) FROM investigation_events WHERE seq=10000") == 0
    assert await database.fetchval("SELECT count(*) FROM investigation_artifacts") == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("stop", ["timeout", "model_error"])
async def test_outer_graph_stop_retains_completed_deep_material_and_markdown(database, monkeypatch, stop):
    run, tenant, _, first = await seed(database)
    state = InvestigationState(run_id=run, tenant_id=tenant, incident_id=uuid4(),
                               alert_summary="Isolated handoff fixture",
                               findings=["first triage finding"], verdict="confirmed_incident", status="completed")
    monkeypatch.setattr(deep, "ENABLED", True)
    monkeypatch.setattr(deep, "_resolve_tenant_skill", AsyncMock(return_value=None))
    monkeypatch.setattr(deep, "scoped_customer_tools", AsyncMock(return_value=([], [])))
    monkeypatch.setattr(deep, "build_mcp_toolset", AsyncMock(return_value=SimpleNamespace(tools=[], refusals=[])))
    monkeypatch.setattr(deep, "investigation_tools", lambda _: [])
    monkeypatch.setattr(deep, "default_registry", lambda _: ToolRegistry([
        Tool(name="read", description="read isolated fixture", parameters={"type": "object"},
             fn=lambda: {"available": True, "rows": [{"message": "已完成的合成查询"}]})]))
    calls = []

    async def invoke(*_args):
        calls.append(1)
        if len(calls) == 1:
            return AIMessage(content="", tool_calls=[{"name": "read", "args": {}, "id": "read-1"}])
        if stop == "model_error":
            raise ValueError("isolated model failure")
        await asyncio.Event().wait()

    monkeypatch.setattr(tool_loop, "safe_ainvoke", invoke)

    class Graph:
        async def astream(self, _):
            result = await deep.run_deep_investigation(state, llm=SimpleNamespace(bind_tools=lambda _: object()))
            yield {"investigation": {"investigation_depth": result.as_dict(), "findings": state.findings + result.findings()}}

    result = await runner._run(Graph(), state, budget=runner.InvestigationBudget(max_seconds=.5), persist=True, seq_start=1)
    assert len(calls) == 2 and result.verdict == "needs_review"
    assert "first triage finding" in result.findings
    trace = result.investigation_depth["tool_trace"]
    assert len(trace) == 1 and trace[0]["ledger_status"] == "recorded"
    assert trace[0]["status"] == "success"
    assert json.loads(trace[0]["result_text"])["rows"][0]["message"] == "已完成的合成查询"
    report = await database.fetchval("SELECT content FROM investigation_artifacts WHERE kind='report_md'")
    assert "Completion: partial" in report and trace[0]["ledger_artifact_id"] in report
    assert "已完成的合成查询" not in report  # Material is linked, not copied into the report.
    assert await database.fetchval("SELECT count(*) FROM investigation_artifacts WHERE kind='tool_result'") == 1
    completion = json.loads(await database.fetchval("SELECT payload FROM investigation_events WHERE kind='graph_result'"))
    assert completion["completion"] == "partial"
    assert json.loads(await database.fetchval("SELECT payload FROM investigation_events WHERE seq=1")) == first
    assert runner.current_investigation_budget() is None
    assert runner._ACTIVE_PROGRESS.get() is None
