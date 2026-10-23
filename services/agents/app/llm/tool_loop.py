"""LLM tool-calling loop (Wave 4a).

Lives under ``app.llm`` rather than ``app.agents``: it is a
provider-agnostic loop over ``safe_ainvoke`` and the tool registry, and
nothing about it is agent-specific. The original home created a cycle —
importing ``app.agents.tool_loop`` executes ``app/agents/__init__.py``,
which imports every agent module, so any agent wanting the loop imported
itself. ``app.agents.tool_loop`` re-exports this for existing callers.

A minimal, provider-agnostic ReAct loop: bind the registry's tools to the model,
let the model choose which to call, execute the calls, feed results back, and
repeat until the model answers without a tool call (or a cap is hit). This is
the primitive that lets specialist agents *use tools* instead of reasoning over
a single pre-serialised blob.

Bounded + fail-soft: at most ``max_iters`` round-trips; tool errors come back to
the model as structured results (via ToolRegistry.execute) rather than aborting.
"""

from __future__ import annotations

import json
import hashlib
import time
from typing import Any, Awaitable, Callable

import structlog
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.llm.contract import safe_ainvoke
from app.core.cost_telemetry import current_cost_tracker
from app.prompting.tool_results import render_tool_message
from app.tools.registry import ToolRegistry

logger = structlog.get_logger()


async def run_with_tools(
    llm: Any,
    *,
    system: str,
    user: str,
    registry: ToolRegistry,
    max_iters: int = 4,
    on_exchange: Callable[..., Any] | None = None,
    max_tokens: int | None = None,
    max_model_calls: int | None = None,
    on_tool_complete: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """Run a tool-calling conversation and return the final content + tool trace.

    Returns ``{"content": str, "tool_trace": [...], "iterations": int,
    "truncated": bool}``.
    """
    bound = llm.bind_tools(registry.openai_schemas())
    messages: list[Any] = [SystemMessage(content=system), HumanMessage(content=user)]
    trace: list[dict[str, Any]] = []
    tracker = current_cost_tracker()

    def exhausted() -> str | None:
        if tracker is None:
            return None
        if current_cost_tracker() is not tracker:
            raise RuntimeError("Tool-loop usage tracker identity changed")
        if max_tokens and tracker.tokens_used >= max_tokens:
            return f"token budget exhausted ({tracker.tokens_used} of {max_tokens})"
        if max_model_calls and tracker.calls_made >= max_model_calls:
            return f"model-call budget exhausted ({tracker.calls_made} of {max_model_calls})"
        return None

    def partial(iterations: int, reason: str) -> dict[str, Any]:
        return {"content": "", "tool_trace": trace, "iterations": iterations,
                "truncated": True, "stop_reason": reason}

    for iteration in range(1, max_iters + 1):
        reason = exhausted()
        if reason:
            return partial(iteration - 1, reason)
        # Routed through safe_ainvoke rather than calling bound.ainvoke
        # directly. This loop feeds tool output straight back into the prompt,
        # and that output is untrusted: a SIEM row, a graph property or a
        # threat-intel record can carry text that reads as an instruction.
        # Skipping the contract here skipped injection validation on precisely
        # the highest-risk content in the system, and lost the token/cost
        # telemetry for every tool-calling turn.
        started = time.monotonic()
        response = await safe_ainvoke(bound, messages)
        if on_exchange is not None:
            # Explicit visible fields only: provider reasoning metadata and
            # non-text/reasoning content blocks never enter this receipt.
            on_exchange(
                agent="deep-investigator", purpose=f"tool_loop:{iteration}",
                model=str(getattr(llm, "model", None) or getattr(llm, "model_name", None) or "") or None,
                prompt=[_visible_message(message) for message in messages],
                response=json.dumps(_visible_message(response), sort_keys=True, ensure_ascii=False),
                duration_ms=round((time.monotonic() - started) * 1000),
            )
        messages.append(response)
        # Usage is known only after the reply. One reply may cross the
        # remaining allowance; retain its receipt, mark partial immediately,
        # and issue no further model/tool call.
        reason = exhausted()
        if reason:
            return partial(iteration, reason)
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            return {
                "content": _content(response),
                "tool_trace": trace,
                "iterations": iteration,
                "truncated": False,
            }
        for call in tool_calls:
            name = call.get("name", "")
            args = call.get("args", {}) or {}
            call_id = call.get("id", "") or ""
            tool_started = time.monotonic()
            result = await registry.execute(name, args)
            # The only place in this service where a tool result becomes text
            # a model reads. Depth plan 1.3 turned that from an accident of
            # layout into an invariant: `render_tool_message` is the single
            # renderer and this is its single call site, both enforced by
            # `test_tool_result_channel.py` walking the syntax tree. The guard
            # rule `fabricated_tool_result` is sound only while that holds —
            # it reports a tool result inside the evidence fence as fabricated
            # by construction, which is a claim about this loop.
            result_text = render_tool_message(result)
            serialized = json.dumps(result, default=str)
            entry = {
                "tool": name, "args": args, "call_id": call_id, "iteration": iteration,
                "status": _tool_status(result),
                "available": result.get("available") if isinstance(result, dict)
                    and isinstance(result.get("available"), bool) else None,
                "result_preview": str(result)[:200], "result_text": result_text,
                "result_size_bytes": len(serialized.encode("utf-8")),
                "result_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                "result_truncated": result_text != serialized,
                "duration_ms": round((time.monotonic() - tool_started) * 1000),
            }
            trace.append(entry)
            # Retain the completed call before another tool/model can fail.
            # The callback persists the same bounded text sent to the model;
            # it must not re-render or enlarge the prompt's tool channel.
            if on_tool_complete is not None:
                await on_tool_complete(entry)
            messages.append(ToolMessage(content=result_text, tool_call_id=call_id))

    logger.info("tool_loop.truncated", iterations=max_iters, tools_called=len(trace))
    # The last item is a ToolMessage, not an analyst's final answer. Keep
    # its evidence in the trace/messages; a cap must not promote it into a
    # completed investigation narrative or spend another model call.
    return partial(max_iters, f"iteration cap ({max_iters})")


def _tool_status(result: Any) -> str:
    """Classify only explicit top-level execution fields, never preview prose.

    Empty means a successful empty response, not evidence of safety. A plain
    mapping with no known envelope remains unknown; nested telemetry fields
    named ``error`` cannot turn a successful lookup into a failed call.
    """
    if isinstance(result, list):
        return "success" if result else "empty"
    if not isinstance(result, dict):
        return "unknown"
    if result.get("error"):
        return "error"
    if result.get("available") is False:
        return "unavailable"
    if result.get("available") is True or result.get("ok") is True:
        rows = result.get("rows")
        return "empty" if isinstance(rows, list) and not rows else "success"
    return "unknown"


def _content(message: Any) -> str:
    return _visible_message(message)["content"]


def _visible_message(message: Any) -> dict[str, Any]:
    content = getattr(message, "content", "")
    if isinstance(content, list):
        content = "\n".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") in {"text", "input_text", "output_text"}
            and isinstance(block.get("text"), str)
        )
    if not isinstance(content, str):
        content = ""
    result: dict[str, Any] = {"role": str(getattr(message, "type", "assistant")), "content": content}
    calls = getattr(message, "tool_calls", None) or []
    if calls:
        result["tool_calls"] = [{key: call[key] for key in ("id", "name", "args") if key in call}
                                for call in calls if isinstance(call, dict)]
    call_id = getattr(message, "tool_call_id", None)
    if call_id:
        result["tool_call_id"] = str(call_id)
    return result
