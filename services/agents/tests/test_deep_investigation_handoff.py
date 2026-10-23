"""Completed tool material survives a later failure without another model call."""
from __future__ import annotations

import asyncio
import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from app.graph import runner
from app.investigator import deep_investigation as deep
from app.llm import tool_loop
from app.models.state import InvestigationState
from app.tools.registry import Tool, ToolRegistry


@pytest.fixture
def isolated(monkeypatch):
    state = InvestigationState(incident_id=uuid4(), tenant_id=uuid4(), alert_summary="bounded investigation")
    monkeypatch.setattr(deep, "ENABLED", True)
    monkeypatch.setattr(deep, "_resolve_tenant_skill", AsyncMock(return_value=None))
    monkeypatch.setattr(deep, "scoped_customer_tools", AsyncMock(return_value=([], [])))
    monkeypatch.setattr(deep, "build_mcp_toolset", AsyncMock(return_value=SimpleNamespace(tools=[], refusals=[])))
    monkeypatch.setattr(deep, "investigation_tools", lambda _: [])
    monkeypatch.setattr(deep.ledger, "resolve_tenant", AsyncMock(return_value=state.tenant_id))
    published = []
    monkeypatch.setattr(runner, "publish_investigation_progress", lambda payload: published.append(copy.deepcopy(payload)))
    return state, published


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["model_error", "model_timeout", "tool_timeout"])
async def test_completed_material_is_recorded_before_later_failure(monkeypatch, isolated, failure):
    state, published = isolated
    writes = []
    turns = 0

    async def persist(**kwargs):
        writes.append(copy.deepcopy(kwargs))
        return {"event_id": "event-1", "artifact_id": "artifact-1"}

    async def slow_tool():
        await asyncio.sleep(2)

    registry = ToolRegistry([
        Tool("read", "read", {"type": "object"}, lambda: {"available": True, "rows": [{"event_id": "source-1"}]}),
        Tool("slow", "slow", {"type": "object"}, slow_tool),
    ])
    monkeypatch.setattr(deep, "default_registry", lambda _: registry)
    monkeypatch.setattr(deep.ledger, "record_tool_result", persist)
    monkeypatch.setattr(deep, "BUDGET_SECONDS", 0.03)

    async def invoke(*_):
        nonlocal turns
        turns += 1
        if turns == 1:
            calls = [{"name": "read", "args": {}, "id": "read-1"}]
            if failure == "tool_timeout":
                calls.append({"name": "slow", "args": {}, "id": "slow-1"})
            return AIMessage(content="", tool_calls=calls)
        assert len(writes) == 1, "next model started before the completed tool was retained"
        if failure == "model_error":
            raise RuntimeError("next request failed")
        await asyncio.sleep(2)

    monkeypatch.setattr(tool_loop, "safe_ainvoke", invoke)
    result = await deep.run_deep_investigation(state, llm=SimpleNamespace(bind_tools=lambda _: object()))
    assert result.error and result.truncated and result.narrative == ""
    assert result.ledger_rows == 1 and result.ledger_gaps == []
    assert len(result.tool_trace) == len(writes) == 1
    assert writes[0]["seq"] == 10000
    assert result.tool_trace[0]["ledger_artifact_id"] == "artifact-1"
    assert "source-1" in result.as_dict()["tool_trace"][0]["result_text"]
    assert result.pivots == ["read"] and turns <= 2
    assert published[-1]["investigation_depth"]["stop_reason"] == result.stop_reason
    text = " ".join(result.findings())
    assert "Completed tool calls retained" in text and "Unresolved" in text
    assert "deterministic path only" not in text


@pytest.mark.asyncio
async def test_storage_failure_is_a_gap_and_does_not_repeat_query(monkeypatch, isolated):
    state, _ = isolated
    tool_calls = []
    writes = AsyncMock(return_value=None)
    monkeypatch.setattr(deep.ledger, "record_tool_result", writes)
    registry = ToolRegistry([Tool("read", "read", {"type": "object"},
        lambda: tool_calls.append(1) or {"available": True, "rows": []})])
    monkeypatch.setattr(deep, "default_registry", lambda _: registry)
    replies = iter([AIMessage(content="", tool_calls=[{"name": "read", "args": {}, "id": "read-1"}]),
                    AIMessage(content="Further verification is needed.")])
    monkeypatch.setattr(tool_loop, "safe_ainvoke", AsyncMock(side_effect=lambda *_: next(replies)))
    result = await deep.run_deep_investigation(state, llm=SimpleNamespace(bind_tools=lambda _: object()))
    assert len(tool_calls) == writes.await_count == 1
    assert result.ledger_rows == 0 and len(result.ledger_gaps) == 1
    assert result.tool_trace[0]["status"] == "empty"
    assert result.tool_trace[0]["ledger_status"] == "not_recorded"
    assert "Tool-material storage gaps" in " ".join(result.findings())


@pytest.mark.asyncio
async def test_cancellation_during_retention_publishes_gap_and_propagates(monkeypatch, isolated):
    state, published = isolated
    writing = asyncio.Event()

    async def persist(**_):
        writing.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(deep.ledger, "record_tool_result", persist)
    monkeypatch.setattr(deep, "default_registry", lambda _: ToolRegistry([
        Tool("read", "read", {"type": "object"}, lambda: {"available": True, "rows": [{"id": "retained"}]})]))
    monkeypatch.setattr(tool_loop, "safe_ainvoke", AsyncMock(return_value=AIMessage(content="", tool_calls=[
        {"name": "read", "args": {}, "id": "read-1"} ])))
    task = asyncio.create_task(deep.run_deep_investigation(state, llm=SimpleNamespace(bind_tools=lambda _: object())))
    await asyncio.wait_for(writing.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    depth = published[-1]["investigation_depth"]
    assert depth["truncated"] and "cancelled" in depth["stop_reason"]
    assert depth["ledger_rows"] == 0 and depth["ledger_gaps"]
    assert depth["tool_trace"][0]["ledger_status"] == "retention_interrupted"
    assert "retained" in depth["tool_trace"][0]["result_text"]


def test_pivot_status_never_reinterprets_preview():
    pivots, unavailable = deep._classify_pivots([
        {"tool": "read", "status": "success", "result_preview": "{'rows': [{'error': 'ordinary event'}]}"},
        {"tool": "empty", "status": "empty", "result_preview": "error unavailable"},
        {"tool": "legacy", "result_preview": "{'available': True}"},
        {"tool": "missing", "status": "unavailable", "result_preview": "x" * 200},
    ])
    assert pivots == ["read", "empty"] and unavailable == ["missing"]
