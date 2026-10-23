"""Wave 4a — LLM tool-calling: the registry exposes real tools and the loop
executes the model's selected calls, feeds results back, and terminates."""

from __future__ import annotations

from types import SimpleNamespace
import hashlib
import json

import pytest
from app.agents.tool_loop import run_with_tools
from app.tools.registry import Tool, ToolRegistry, default_registry


class _FakeLLM:
    """Scripted chat model exposing bind_tools + ainvoke."""

    def __init__(self, script: list) -> None:
        self._script = script
        self.calls = 0
        self.bound_tools = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    async def ainvoke(self, _messages):
        resp = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        return resp


def _tool_call(name, args, cid="c1"):
    return SimpleNamespace(content="", tool_calls=[{"name": name, "args": args, "id": cid}])


def _final(text):
    return SimpleNamespace(content=text, tool_calls=[])


def test_registry_exposes_openai_schemas():
    reg = default_registry()
    schemas = reg.openai_schemas()
    names = {s["function"]["name"] for s in schemas}
    assert {"extract_iocs", "map_to_mitre", "lookup_technique", "enrich_ioc"} <= names
    assert all(s["type"] == "function" for s in schemas)


@pytest.mark.asyncio
async def test_registry_execute_runs_real_tool_and_handles_unknown():
    reg = default_registry()
    iocs = await reg.execute("extract_iocs", {"text": "beacon to evil.example and 45.9.148.99"})
    assert isinstance(iocs, list)
    # Unknown tool fails soft.
    err = await reg.execute("nope", {})
    assert "error" in err


@pytest.mark.asyncio
async def test_tool_loop_executes_selected_tool_then_answers():
    reg = default_registry()
    llm = _FakeLLM([_tool_call("extract_iocs", {"text": "45.9.148.99 and evil.example"}), _final("Two IOCs found.")])
    out = await run_with_tools(llm, system="You are an analyst.", user="Find IOCs.", registry=reg)
    assert out["truncated"] is False
    assert out["content"] == "Two IOCs found."
    assert out["iterations"] == 2
    assert any(t["tool"] == "extract_iocs" for t in out["tool_trace"])
    assert llm.bound_tools is not None  # tools were bound to the model


@pytest.mark.asyncio
async def test_tool_loop_is_bounded_by_max_iters():
    # A model that always asks for a tool must not loop forever.
    reg = ToolRegistry([Tool(name="noop", description="noop", parameters={"type": "object", "properties": {}}, fn=lambda: {"ok": True})])
    llm = _FakeLLM([_tool_call("noop", {})])  # always returns a tool call
    out = await run_with_tools(llm, system="s", user="u", registry=reg, max_iters=3)
    assert out["truncated"] is True
    assert out["iterations"] == 3
    assert len(out["tool_trace"]) == 3


@pytest.mark.asyncio
async def test_completed_tool_callback_precedes_next_model_and_keeps_actual_bounded_text(monkeypatch):
    from app.llm import tool_loop

    result = {"rows": [{"error": "ordinary event field", "body": "界" * 5000}], "available": True}
    observed = []
    turns = 0

    async def invoke(_, messages):
        nonlocal turns
        turns += 1
        if turns == 1:
            return _tool_call("read", {"hostname": "host-1"})
        assert len(observed) == 1
        assert messages[-1].content == observed[0]["result_text"]
        raise RuntimeError("next model failed")

    async def retain(entry):
        observed.append(entry)

    monkeypatch.setattr(tool_loop, "safe_ainvoke", invoke)
    registry = ToolRegistry([Tool("read", "read", {"type": "object"}, lambda **_: result)])
    with pytest.raises(RuntimeError, match="next model failed"):
        await run_with_tools(_FakeLLM([]), system="s", user="u", registry=registry, on_tool_complete=retain)
    entry = observed[0]
    serialized = json.dumps(result, default=str)
    assert entry["status"] == "success" and entry["available"] is True
    assert entry["result_text"] == serialized[:4000] and entry["result_truncated"]
    assert entry["result_size_bytes"] == len(serialized.encode("utf-8"))
    assert entry["result_sha256"] == hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    assert entry["args"] == {"hostname": "host-1"} and entry["call_id"] == "c1"


@pytest.mark.parametrize(("result", "status"), [
    ({"rows": [{"error": "telemetry field"}], "available": True}, "success"),
    ({"padding": "x" * 300, "available": False}, "unavailable"),
    ({"padding": "x" * 300, "error": "lookup failed"}, "error"),
    ({"available": True, "rows": []}, "empty"),
    ({"message": "error: unavailable"}, "unknown"),
    ([], "empty"),
])
def test_tool_state_uses_explicit_top_level_fields(result, status):
    from app.llm.tool_loop import _tool_status

    assert _tool_status(result) == status
