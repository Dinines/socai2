"""One local, real Deep investigation through the configured SSH tunnels.

Run with the Agents dependencies installed; no service process is started::

    python deploy/aisoc21/probe_investigation_deep.py \
      --input .local/aisoc21/investigation-functional-20261021/deep-input.json \
      --output-dir .local/aisoc21/investigation-functional-20261021/deep-run

The input supplies tenant_id, alert_summary, raw_alert and optional
mitre_mappings/tenant_skill/context_bundle/source. New local run/incident UUIDs
are generated unless explicitly supplied. The operator supplies gateway/API
URLs and credentials through the environment. HTTP, model replies and tools
are real: the wrappers only observe the original calls and bound SDK retries.
Evidence stays local; this does not create a persisted Case/Run or report.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from uuid import UUID, uuid4


REPO = Path(__file__).resolve().parents[2]


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def visible_response(body: dict[str, Any]) -> dict[str, Any]:
    """Keep public assistant fields/usage, never provider reasoning metadata."""
    output = {key: body[key] for key in ("id", "model", "created", "usage") if key in body}
    output["choices"] = []
    for choice in body.get("choices", []):
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = [block for block in content if isinstance(block, dict)
                       and block.get("type") in {"text", "output_text"}]
        output["choices"].append({
            "index": choice.get("index"), "finish_reason": choice.get("finish_reason"),
            "message": {**{key: message[key] for key in ("role", "tool_calls", "refusal") if key in message},
                        "content": content},
        })
    if "error" in body:
        output["error"] = body["error"]
    return output


async def observe(args: argparse.Namespace) -> dict[str, Any]:
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    tenant_id = str(UUID(str(args.tenant_id or payload["tenant_id"])))
    run_id = args.run_id or UUID(str(payload["run_id"])) if payload.get("run_id") else args.run_id or uuid4()
    incident_id = args.incident_id or UUID(str(payload["case_id"])) if payload.get("case_id") else args.incident_id or uuid4()
    output = args.output_dir.resolve()
    if not output.is_relative_to(REPO / ".local"):
        raise ValueError("Evidence output must be under this repository's .local directory")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)

    # Local observation only. Remove ambient DB access before importing any
    # production modules; the original ledger then reports unavailable.
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("DATABASE_DSN", None)
    os.environ["AISOC_DEEP_INVESTIGATION"] = "true"
    os.environ["AISOC_DEEP_INVESTIGATION_MAX_ITERS"] = "6"
    os.environ["AISOC_DEEP_INVESTIGATION_BUDGET_SECONDS"] = "120"
    os.environ["AISOC_LLM_RESPONSE_CACHE"] = "0"
    if not os.getenv("LLM_GATEWAY_URL") and not os.getenv("OPENAI_BASE_URL"):
        raise ValueError("An explicit tunneled model endpoint is required")
    if not os.getenv("AISOC_API_URL"):
        raise ValueError("AISOC_API_URL must name the tunneled API")
    sys.path.insert(0, str(REPO / "services/agents"))

    import httpx
    from app.core.cost_telemetry import CostTracker
    from app.investigator import deep_investigation as deep
    from app.llm.factory import make_chat_model
    from app.models.state import InvestigationState
    from app.prompting.tool_results import render_tool_message
    from app.tools.registry import ToolRegistry

    requests: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    exchanges: list[dict[str, Any]] = []
    tools: list[dict[str, Any]] = []
    tracker: CostTracker | None = None

    class ObservedState(InvestigationState):
        def record_llm_exchange(self, **exchange: Any) -> dict[str, Any]:
            original = super().record_llm_exchange(**exchange)
            item = {"index": len(exchanges) + 1, **exchange,
                    "usage": asdict(tracker._records[-1]) if tracker and tracker._records else None}
            exchanges.append(item)
            write_json(output / f"exchange-{item['index']:02d}.json", item)
            return original

    state = ObservedState(
        run_id=run_id, incident_id=incident_id, tenant_id=tenant_id,
        alert_summary=payload.get("alert_summary", ""), raw_alert=payload["raw_alert"],
        mitre_mappings=payload.get("mitre_mappings", []),
        tenant_skill=payload.get("tenant_skill"), context_bundle=payload.get("context_bundle"),
    )
    write_json(output / "input.json", {"input": payload, "state": state.to_dict(),
               "scope": "local Deep component observation; not a persisted Case/Run",
               "limits": {"max_model_requests": 6, "deep_loop_seconds": 120,
                          "sdk_timeout_seconds": 45, "sdk_max_retries": 0,
                          "deep_token_ceiling": deep.MAX_TOKENS_PER_INVESTIGATION},
               "database_enabled": False, "cost_tracker_persist": False})

    async def request_hook(request: httpx.Request) -> None:
        if len(requests) >= 6:
            raise RuntimeError("The six-request observation cap was reached")
        body = json.loads(await request.aread())
        item = {"index": len(requests) + 1, "method": request.method,
                "path": request.url.path, "body": body}
        requests.append(item)
        # Authorization and other request headers are deliberately excluded.
        write_json(output / f"model-request-{item['index']:02d}.json", item)

    async def response_hook(response: httpx.Response) -> None:
        await response.aread()
        try:
            body = visible_response(response.json())
        except (ValueError, TypeError):
            body = {"non_json_response": True}
        item = {"index": len(responses) + 1, "status_code": response.status_code, "body": body}
        responses.append(item)
        write_json(output / f"model-response-{item['index']:02d}.json", item)

    original_execute, original_factory = ToolRegistry.execute, deep.make_chat_model

    async def observed_execute(registry: ToolRegistry, name: str, arguments: dict[str, Any]) -> Any:
        item = {"index": len(tools) + 1, "after_exchange": len(exchanges),
                "tool": name, "args": arguments}
        tools.append(item)
        started = time.monotonic()
        try:
            result = await original_execute(registry, name, arguments)
            item.update({"result": result, "model_tool_content": render_tool_message(result)})
            return result
        except BaseException as exc:
            item["interrupted_by"] = type(exc).__name__
            raise
        finally:
            item["duration_ms"] = round((time.monotonic() - started) * 1000)
            write_json(output / f"tool-{item['index']:02d}.json", item)

    async with httpx.AsyncClient(event_hooks={"request": [request_hook], "response": [response_hook]}) as client:
        def observed_factory(role: str, **kwargs: Any) -> Any:
            return make_chat_model(role, **{**kwargs, "max_retries": 0, "timeout": 45.0,
                                           "http_async_client": client})

        ToolRegistry.execute, deep.make_chat_model = observed_execute, observed_factory
        try:
            async with CostTracker(run_id=str(run_id), tenant_id=tenant_id, persist=False) as tracker:
                result = await deep.run_deep_investigation(state)
        finally:
            ToolRegistry.execute, deep.make_chat_model = original_execute, original_factory

    # Adopt exactly the Deep findings/depth fields that investigation_agent
    # consumes. Do not run triage, response execution or a report-writer model.
    for finding in result.findings():
        state.add_finding(finding)
    state.investigation_depth = result.as_dict()
    write_json(output / "state.json", state.to_dict())
    write_json(output / "result.json", {**asdict(result), "reached_depth": result.reached_depth})
    write_json(output / "trace.json", {"tools": tools, "loop_trace": result.tool_trace,
                                       "unverified_tool_claims": result.unverified_tool_claims})
    write_json(output / "usage.json", {"summary": tracker.summary(),
                                       "calls": [asdict(record) for record in tracker._records]})
    with (output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(f"# Deep investigation observation\n\nLocal Run: `{run_id}`\n\n")
        stream.write("This is the Deep component's findings, not a full Case report.\n\n")
        stream.write("\n\n".join(result.findings()) + "\n")
    summary = {"run_id": str(run_id), "tenant_id": tenant_id,
               "observed_at": datetime.now(timezone.utc).isoformat(),
               "model_requests": len(requests), "model_http_responses": len(responses),
               "model_exchanges": len(exchanges), "tool_executions": len(tools),
               "usage": tracker.summary(), "strategy_id": result.strategy_id,
               "distinct_pivots": result.distinct_pivots, "truncated": result.truncated,
               "error": result.error, "stop_reason": result.stop_reason,
               "database_enabled": False, "cost_tracker_persist": False,
               "provenance": payload.get("provenance", payload.get("source")), "output_dir": str(output)}
    write_json(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory under .local; never overwritten")
    parser.add_argument("--tenant-id", type=UUID)
    parser.add_argument("--run-id", type=UUID, help="New local-only Run UUID")
    parser.add_argument("--incident-id", type=UUID, help="New local-only incident UUID")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        summary = asyncio.run(observe(args))
        print(json.dumps(summary, ensure_ascii=False))
        return 1 if summary["error"] else 0
    except BaseException as exc:
        # Existing receipts remain even if a call is interrupted; no automatic retry.
        output = args.output_dir.resolve()
        if output.is_dir() and not (output / "failure.json").exists():
            write_json(output / "failure.json", {"exception_type": type(exc).__name__,
                       "retry_performed": False, "action": "Preserve receipts and inspect before any new input"})
        print(json.dumps({"failed": True, "exception_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
