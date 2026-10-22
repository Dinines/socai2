#!/usr/bin/env python3
"""Observe one original local investigation against real configured services.

This is a test-only entry point, not a worker or an API endpoint. It delegates
to the original Router/manual streams and keeps their preprocessing, prompts,
parsers and decisions. It never supplies a model reply or an HTTP response.

Input JSON: case_id, tenant_id, alert_summary, raw_alert (object), optional
run_id (UUID) and provenance. Configure gateway and read-only dependency URLs /
credentials in the environment before running. Each mode is run separately.
DATABASE_URL/DATABASE_DSN are removed before application imports, so no ledger
or cost rows are written. Raw local evidence includes prompts and source data;
authentication headers and environment credential values are never recorded.
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import functools
import hashlib
import importlib
import json
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
STAGE: contextvars.ContextVar[str] = contextvars.ContextVar("probe_stage", default="preprocessing")
MODEL_CALL: contextvars.ContextVar[int | None] = contextvars.ContextVar("probe_model_call", default=None)
PURPOSE = {
    "auto_triage": "Classify disposition/confidence and apply the original close/escalate policy",
    "phishing": "Analyse phishing-specific evidence once and return a domain verdict",
    "identity": "Analyse identity/authentication evidence once and return a domain verdict",
    "cloud": "Analyse cloud-specific evidence once and return a domain verdict",
    "insider": "Analyse insider/data-movement evidence once and return a domain verdict",
    "recon": "Extract IOCs, MITRE techniques and threat actors before fixed IOC enrichment",
    "forensic": "Form an evidence-scoped root-cause hypothesis, timeline and blast-radius assessment",
    "responder": "Propose containment, eradication and recovery steps as a dry-run plan",
    "report_writer": "Write the Markdown report from the preceding investigation state",
}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def serialise(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return serialise(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(k): serialise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialise(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def without_private_reasoning(value: Any) -> Any:
    """Keep visible replies and usage; omit provider-only reasoning channels."""
    private = {"reasoning", "reasoning_content", "analysis"}
    if isinstance(value, dict):
        return {key: without_private_reasoning(item) for key, item in value.items()
                if str(key).lower() not in private}
    if isinstance(value, list):
        return [without_private_reasoning(item) for item in value
                if not (isinstance(item, dict) and str(item.get("type", "")).lower() in private)]
    return value


def visible_http_body(body: bytes) -> dict[str, Any]:
    # The hash elsewhere refers to the original bytes. Never persist a raw
    # side-channel reasoning string, including in an unexpected non-JSON body.
    try:
        visible = without_private_reasoning(json.loads(body))
    except (ValueError, UnicodeDecodeError):
        return {"body_utf8": None, "non_json_body_omitted": True, "body_bytes": len(body)}
    return {"body_utf8": json.dumps(visible, ensure_ascii=False),
            "body_visibility": "JSON with provider private reasoning fields omitted"}


def safe_url(value: Any) -> str:
    parts = urlsplit(str(value))
    hostname = parts.hostname or ""
    if ":" in hostname:
        hostname = f"[{hostname}]"
    authority = hostname + (f":{parts.port}" if parts.port else "")
    sensitive = {"key", "api_key", "apikey", "token", "access_token", "password", "secret"}
    query = urlencode([(k, "[REDACTED]" if k.lower() in sensitive else v) for k, v in parse_qsl(parts.query, keep_blank_values=True)])
    return urlunsplit((parts.scheme, authority, parts.path, query, parts.fragment))


def safe_headers(headers: Any) -> dict[str, str]:
    # Preserve transport/usage provenance, never request or response credentials.
    sensitive = {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "api-key"}
    return {str(k): str(v) for k, v in headers.items()
            if str(k).lower() not in sensitive
            and not any(marker in str(k).lower() for marker in ("api-key", "api_key", "service-token", "secret"))}


class ObservationLimitReached(BaseException):
    """Stop without falling through an agent's normal Exception fallback."""


class Observation:
    def __init__(self, output: Path, max_calls: int):
        self.output = output
        self.max_calls = max_calls
        self.calls_started = 0
        self.replies_received = 0
        self.http_count = 0
        self.node_count = 0
        self.model_records: list[dict[str, Any]] = []
        self.exception_redactions: dict[str, str] = {}

    def scrub_record(self, value: Any) -> Any:
        value = serialise(value)
        if isinstance(value, dict):
            return {key: self.scrub_record(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.scrub_record(item) for item in value]
        if isinstance(value, str):
            for text, replacement in self.exception_redactions.items():
                value = value.replace(text, replacement)
        return value

    def error_record(self, exc: BaseException) -> dict[str, Any]:
        text = str(exc)
        # SDK exceptions can embed the entire provider body. Keep the
        # exception object untouched for original business handling, while
        # suppressing that same text in this probe's files and console logs.
        if text and (hasattr(exc, "body") or any(key in text.lower() for key in ("reasoning", "analysis"))):
            self.exception_redactions[text] = f"[Provider exception text omitted: {type(exc).__name__}; see filtered HTTP response]"
        return {"type": type(exc).__name__, "status_code": getattr(exc, "status_code", None),
                "http_requests_observed": self.http_count}

    def write(self, filename: str, value: Any) -> None:
        target = self.output / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            json.dump(self.scrub_record(value), handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def append(self, filename: str, value: Any) -> None:
        with (self.output / filename).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self.scrub_record(value), ensure_ascii=False) + "\n")

    def wrap_node(self, fn: Any, stage: str) -> Any:
        @functools.wraps(fn)
        async def observed(*args: Any, **kwargs: Any) -> Any:
            self.node_count += 1
            prefix = f"nodes/{self.node_count:02d}-{stage}"
            token = STAGE.set(stage)
            self.write(prefix + "-input.json", {"args": args, "kwargs": kwargs})
            try:
                result = await fn(*args, **kwargs)
                self.write(prefix + "-output.json", result)
                return result
            except BaseException as exc:
                self.write(prefix + "-error.json", self.error_record(exc))
                raise
            finally:
                STAGE.reset(token)
        return observed

    def observe_http(self) -> None:
        import httpx

        original_send = httpx.AsyncClient.send

        async def observed_send(client: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
            self.http_count += 1
            number = self.http_count
            prefix = f"http/{number:03d}"
            body = await request.aread()
            self.write(prefix + "-request.json", {
                "at": timestamp(), "stage": STAGE.get(), "model_call": MODEL_CALL.get(),
                "method": request.method, "url": safe_url(request.url),
                "headers": safe_headers(request.headers),
                **visible_http_body(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
            })
            start = time.monotonic()
            try:
                response = await original_send(client, request, *args, **kwargs)
                # Selected original paths use non-streaming calls. Reading here
                # preserves the bytes httpx will return to the original caller.
                content = await response.aread()
                self.write(prefix + "-response.json", {
                    "at": timestamp(), "stage": STAGE.get(), "model_call": MODEL_CALL.get(),
                    "status_code": response.status_code, "headers": safe_headers(response.headers),
                    "elapsed_ms": round((time.monotonic() - start) * 1000, 2),
                    **visible_http_body(content),
                    "body_sha256": hashlib.sha256(content).hexdigest(),
                })
                return response
            except BaseException as exc:
                self.write(prefix + "-error.json", {
                    "at": timestamp(), "stage": STAGE.get(), "model_call": MODEL_CALL.get(),
                    **self.error_record(exc),
                })
                raise

        httpx.AsyncClient.send = observed_send

    def observe_factory(self) -> None:
        from app.llm import factory

        original_factory = factory.make_chat_model
        owner = self

        class ObservedModel:
            def __init__(self, inner: Any, role: str, requested: dict[str, Any]):
                self.inner, self.role, self.requested = inner, role, requested

            def __getattr__(self, name: str) -> Any:
                return getattr(self.inner, name)

            def bind_tools(self, *args: Any, **kwargs: Any) -> Any:
                # Delegation only: no tool is invented, executed or answered.
                return ObservedModel(self.inner.bind_tools(*args, **kwargs), self.role,
                                     {**self.requested, "bind_tools_args": serialise(args), "bind_tools_kwargs": serialise(kwargs)})

            async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
                if owner.calls_started >= owner.max_calls:
                    raise ObservationLimitReached(f"Model invocation cap {owner.max_calls} reached; no further request sent")
                owner.calls_started += 1  # No await before reservation; safe for Router fan-out.
                number = owner.calls_started
                prefix = f"models/{number:02d}-{self.role}"
                token = MODEL_CALL.set(number)
                materialised = list(messages)
                request = {
                    "at": timestamp(), "stage": STAGE.get(), "role": self.role,
                    "purpose": PURPOSE.get(STAGE.get(), "See the original system prompt and node state"),
                    "model": getattr(self.inner, "model_name", None),
                    "base_url": safe_url(getattr(self.inner, "openai_api_base", "") or ""),
                    "factory_arguments": self.requested,
                    "actual_outbound_messages_after_contract_and_privacy": without_private_reasoning(serialise(materialised)),
                    "invocation_kwargs": without_private_reasoning(serialise(kwargs)),
                    "boundary": "Real model ainvoke; request is recorded after safe_ainvoke egress transformation",
                }
                owner.write(prefix + "-request.json", request)
                start = time.monotonic()
                try:
                    async with asyncio.timeout(45.0):
                        response = await self.inner.ainvoke(materialised, **kwargs)
                    owner.replies_received += 1
                    metadata = without_private_reasoning(dict(getattr(response, "response_metadata", {}) or {}))
                    if "headers" in metadata:
                        metadata["headers"] = safe_headers(metadata["headers"])
                    result = without_private_reasoning(serialise(response))
                    if isinstance(result, dict):
                        result["response_metadata"] = metadata
                    record = {
                        "at": timestamp(), "stage": STAGE.get(), "role": self.role,
                        "elapsed_ms": round((time.monotonic() - start) * 1000, 2),
                        "raw_model_message_before_privacy_restore": result,
                        "response_visibility": "Visible assistant message only; provider private reasoning fields omitted",
                        "usage_metadata": serialise(getattr(response, "usage_metadata", None)),
                        "token_usage": serialise(metadata.get("token_usage")),
                        "finish_reason": metadata.get("finish_reason"),
                        "tool_calls": serialise(getattr(response, "tool_calls", None)),
                        "invalid_tool_calls": serialise(getattr(response, "invalid_tool_calls", None)),
                    }
                    owner.write(prefix + "-response.json", record)
                    owner.model_records.append({"number": number, "stage": STAGE.get(), "role": self.role,
                                                "finish_reason": record["finish_reason"], "usage_metadata": record["usage_metadata"],
                                                "token_usage": record["token_usage"], "response_file": prefix + "-response.json"})
                    return response
                except BaseException as exc:
                    owner.write(prefix + "-error.json", {"at": timestamp(), **owner.error_record(exc)})
                    raise
                finally:
                    MODEL_CALL.reset(token)

        def observed_factory(role: str, **kwargs: Any) -> Any:
            kwargs.update(max_retries=0, timeout=45.0)
            inner = original_factory(role, **kwargs)
            return ObservedModel(inner, role, serialise(kwargs))

        # Patch only this process's factory references. All calls still reach
        # the original factory and real transport; no business file is edited.
        factory.make_chat_model = observed_factory
        for name, module in list(sys.modules.items()):
            if name.startswith("app.") and getattr(module, "make_chat_model", None) is original_factory:
                setattr(module, "make_chat_model", observed_factory)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("router", "manual"))
    parser.add_argument("--input", required=True, type=Path, help="JSON input, preserved without field flattening")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-replies", type=int, help="Also caps model invocations; maximum 5 router / 4 manual")
    return parser.parse_args()


async def run(args: argparse.Namespace) -> int:
    ceiling = 5 if args.mode == "router" else 4
    cap = args.max_replies if args.max_replies is not None else ceiling
    if cap < 1 or cap > ceiling:
        raise ValueError(f"--max-replies must be between 1 and {ceiling}")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    for key in ("case_id", "tenant_id", "alert_summary", "raw_alert"):
        if key not in payload:
            raise ValueError(f"Input is missing {key}")
    if not isinstance(payload["raw_alert"], dict):
        raise ValueError("raw_alert must be an object; no transformation is applied")
    run_id = uuid.UUID(str(payload["run_id"])) if payload.get("run_id") else uuid.uuid4()
    if not (os.getenv("OPENAI_BASE_URL", "").strip() or os.getenv("LLM_GATEWAY_URL", "").strip()):
        raise ValueError("Configure OPENAI_BASE_URL or LLM_GATEWAY_URL; the probe does not default to a public provider")

    os.umask(0o077)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any((args.output_dir / name).exists() for name in ("plan.json", "summary.json", "events.jsonl", "models", "http", "nodes")):
        raise ValueError("Output already contains a probe record; choose a fresh directory")
    observation = Observation(args.output_dir, cap)
    removed_database_names = [name for name in ("DATABASE_URL", "DATABASE_DSN") if os.environ.pop(name, None) is not None]
    os.environ["AISOC_LLM_RESPONSE_CACHE"] = "0"  # Every observed model call must be real.
    # The original manual pipeline defaults to 2048. Refuse an accidental
    # inherited unlimited/different value instead of silently changing it.
    if os.getenv("AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS", "2048").strip() not in ("", "2048"):
        raise ValueError("This observation requires the original manual completion bound of 2048")
    observation.write("plan.json", {
        "at": timestamp(), "mode": args.mode, "run_id": str(run_id), "input": payload,
        "python": platform.python_version(), "max_model_invocations": cap,
        "test_only_adjustments": {"sdk_max_retries": 0, "sdk_and_whole_await_timeout_seconds": 45,
                                  "response_cache": "disabled", "removed_database_env_names": removed_database_names},
        "boundaries": ["Real configured model/services only; no mocked outputs or HTTP", "No worker/HTTP API starts",
                       "Ledger/cost persistence disabled by absent database DSNs", "Original native fallbacks, if reached, remain visible in node state"],
        "dependency_urls": {name: safe_url(os.getenv(name, "")) for name in
                            ("OPENAI_BASE_URL", "LLM_GATEWAY_URL", "API_SERVICE_URL", "ENRICHMENT_SERVICE_URL", "AISOC_UEBA_URL")},
        "nonsecret_runtime_flags": {name: os.getenv(name) for name in
                                    ("AISOC_TRIAGE_ADMISSION_PROFILE", "AISOC_AGENT_PARALLEL_TOPOLOGY",
                                     "AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS", "AISOC_AGENTS_LLM_CONTRACT_ENFORCED",
                                     "AISOC_PSEUDONYMIZE_EGRESS")},
    })
    sys.path.insert(0, str(ROOT / "services/agents"))
    observation.observe_http()
    observation.observe_factory()
    import structlog
    structlog.configure(processors=[lambda _logger, _method, event: observation.scrub_record(event),
                                    structlog.processors.JSONRenderer()])
    from app.llm import contract
    contract._RESPONSE_CACHE_ENABLED = False
    contract._RESPONSE_CACHE.clear()

    if args.mode == "router":
        agents = importlib.import_module("app.agents")
        for stage, function in (("auto_triage", "run_auto_triage"), ("phishing", "run_phishing"),
                                ("identity", "run_identity"), ("cloud", "run_cloud"), ("insider", "run_insider_threat")):
            setattr(agents, function, observation.wrap_node(getattr(agents, function), stage))
        module = importlib.import_module("app.orchestrator.router")
        original_done = module._build_done_event

        def observed_done(state: Any, **kwargs: Any) -> Any:
            result = original_done(state, **kwargs)
            observation.write("final-internal-state.json", state)
            return result

        module._build_done_event = observed_done
        stream = module.RouterOrchestrator().stream_kwargs
    else:
        module = importlib.import_module("app.investigator.orchestrator")
        for stage in ("recon", "forensic", "responder", "report_writer"):
            function = "run_" + stage
            setattr(module, function, observation.wrap_node(getattr(module, function), stage))
        original_groundedness = module._apply_groundedness

        def observed_groundedness(state: Any) -> None:
            original_groundedness(state)
            observation.write("final-internal-state.json", state.to_dict())

        module._apply_groundedness = observed_groundedness
        stream = module.InvestigatorOrchestrator().stream

    terminal = None
    error = None
    start = time.monotonic()
    try:
        async for event in stream(case_id=str(payload["case_id"]), tenant_id=str(payload["tenant_id"]),
                                  alert_summary=str(payload["alert_summary"]), raw_alert=payload["raw_alert"], run_id=run_id):
            observation.append("events.jsonl", event)
            if event.get("type") in ("done", "error"):
                terminal = serialise(event)
        if terminal is not None:
            observation.write("terminal.json", terminal)
            state = terminal.get("state") or {}
            observation.write("state.json", state)
            if state.get("report_md"):
                with (args.output_dir / "report.md").open("x", encoding="utf-8") as handle:
                    handle.write(state["report_md"])
    except BaseException as exc:
        error = observation.error_record(exc)
        observation.write("error.json", error)
    summary = {
        "at": timestamp(), "mode": args.mode, "run_id": str(run_id),
        "elapsed_seconds": round(time.monotonic() - start, 2), "calls_started": observation.calls_started,
        "replies_received": observation.replies_received, "http_requests": observation.http_count,
        "nodes_started": observation.node_count, "model_calls": observation.model_records,
        "terminal_type": (terminal or {}).get("type"), "status": ((terminal or {}).get("state") or {}).get("status"),
        "report_markdown_saved": (args.output_dir / "report.md").exists(), "probe_error": error,
        "ledger_persistence": "disabled; only local evidence written",
    }
    observation.write("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if error is None and summary["terminal_type"] == "done" and summary["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
