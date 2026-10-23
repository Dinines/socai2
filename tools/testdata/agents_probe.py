#!/usr/bin/env python3
"""Bounded local original Agents worker + API probe; never publishes fixtures.

Only the explicit private config/environment is used. Start this process first,
wait for consumer-ready.json, then publish each new fused message serially and
wait for progress.json committed_count before publishing the next. The original
worker owns business processing and Kafka commits. No main-app migrations run.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_COUNT = 2
REQUEST_LIMIT = 14
READERS = ("AISOC_ORG_MEMORY_KEYS_FILE", "AISOC_TENANT_SKILLS_KEYS_FILE",
           "AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE", "AISOC_TRIAGE_KB_KEYS_FILE",
           "AISOC_TRIAGE_IDENTITY_KEYS_FILE", "AISOC_INVESTIGATION_CONTEXT_KEYS_FILE")
ROUTERS = ("graph", "feedback", "tenant_skills", "knowledge_base", "alerts",
           "lake", "agent_tools", "threat_intel", "identity_graph")
CURRENT_ALERT: ContextVar[dict | None] = ContextVar("testdata_probe_alert", default=None)


class ProbeStopped(RuntimeError):
    """The driving process asked this temporary probe to clean up."""


def save(path: Path, value, *, replace: bool = False) -> None:
    """Private, complete JSON receipts; old evidence is never overwritten by default."""
    data = json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
    target = path.with_suffix(path.suffix + ".tmp") if replace else path
    with target.open("x", encoding="utf-8") as stream:
        os.chmod(target, 0o600)
        stream.write(data)
    if replace:
        os.replace(target, path)


def private_file(path: Path) -> Path:
    path = path.resolve()
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError("Configuration files must exist and have private permissions")
    return path


def read_configuration(path: Path) -> dict:
    path = private_file(path)
    config = json.loads(path.read_text(encoding="utf-8"))
    batch = config.get("run_id", "")
    if not isinstance(batch, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", batch):
        raise ValueError("An explicit bounded batch run_id is required")
    config["tenant_id"] = str(UUID(config["tenant_id"]))
    names = [config.get(key) for key in ("fused_topic", "group", "dlq")]
    prefix = f"socai2.testdata.{batch}."
    if any(not isinstance(name, str) or not name.startswith(prefix) or
           not re.fullmatch(r"[A-Za-z0-9._-]{1,249}", name) for name in names) or len(set(names)) != 3:
        raise ValueError("Topic, group and DLQ must be distinct and belong to this test batch")
    if type(config.get("api_port")) is not int or not 1024 <= config["api_port"] <= 65535:
        raise ValueError("An explicit unprivileged local API port is required")
    for key in ("env_file", "reader_keys_file", "writer_keys_file", "neo4j_config"):
        value = Path(config[key])
        config[key] = str(private_file(value if value.is_absolute() else path.parent / value))
    if config.get("expected_count", EXPECTED_COUNT) != EXPECTED_COUNT or config.get("request_limit", REQUEST_LIMIT) != REQUEST_LIMIT:
        raise ValueError("This probe accepts exactly two inputs and at most fourteen HTTP model requests")
    deadline = config.get("max_seconds", 600)
    if type(deadline) is not int or not 60 <= deadline <= 900:
        raise ValueError("Probe deadline must be between 60 and 900 seconds")
    config["max_seconds"] = deadline
    graph = json.loads(Path(config["neo4j_config"]).read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or set(graph) != {"uri", "username", "password", "database"} or graph["database"] != "neo4j":
        raise ValueError("Neo4j config must use the existing identity graph file contract")
    if any(not isinstance(value, str) or not value for value in graph.values()):
        raise ValueError("Neo4j config contains an empty field")
    return config


def configure_process(config: dict, service: str) -> None:
    """No inherited production routing or implicit repository .env settings."""
    if "app" in sys.modules:
        raise RuntimeError("API and Agents require separate probe processes")
    from dotenv import dotenv_values
    values = dotenv_values(config["env_file"], interpolate=False)
    if any(value is None or "${" in value for value in values.values()):
        raise ValueError("The explicit environment must have resolved values")
    for key in ("DATABASE_URL", "KAFKA_BOOTSTRAP_SERVERS"):
        if not values.get(key):
            raise ValueError("Explicit database and Kafka configuration is required")
    if not values.get("LLM_GATEWAY_URL") and not values.get("OPENAI_BASE_URL"):
        raise ValueError("An explicit model endpoint is required")
    if values.get("AISOC_AGENT_ESCALATE_TO_GRAPH") != "1":
        raise ValueError("The supplied environment must explicitly enable original escalation")
    for name in ("AISOC_SIEM_WRITEBACK_ENABLED", "AISOC_ALERT_PLAYBOOKS_ENABLED"):
        if str(values.get(name, "")).lower() not in {"0", "false", "off"}:
            raise ValueError("The supplied environment must explicitly disable external action paths")
    # Preserve process essentials only; all service routing/authentication must
    # be supplied in this batch's environment, never inherited from a shell.
    system_env = {key: value for key, value in os.environ.items()
                  if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT"}}
    os.environ.clear()
    os.environ.update(system_env)
    os.environ.update(values)
    local_api = f"http://127.0.0.1:{config['api_port']}"
    os.environ.update({key: config["reader_keys_file"] for key in READERS})
    os.environ.update({"AISOC_INVESTIGATION_PREPARE_KEYS_FILE": config["writer_keys_file"],
                       "AISOC_IDENTITY_GRAPH_CONFIG_FILE": config["neo4j_config"],
                       "API_SERVICE_URL": local_api, "AISOC_API_URL": local_api,
                       "KAFKA_TOPIC_ALERTS_FUSED": config["fused_topic"],
                       "KAFKA_TOPIC_ALERTS_FUSED_DLQ": config["dlq"],
                       "OTEL_SDK_DISABLED": "true", "PYTHONDONTWRITEBYTECODE": "1"})
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "services" / service))
    # Exception strings can carry connection credentials. Explicit receipts
    # retain types and observed statuses, without logging environment values.
    logging.disable(logging.CRITICAL)
    import structlog
    def discard_log(logger, method, event_dict):
        raise structlog.DropEvent
    structlog.configure(processors=[discard_log])
    if service == "api":
        from app.core import config as api_config
        api_config.settings = api_config.Settings(_env_file=None)
        api_config.get_settings = lambda: api_config.settings


def api_app(config: dict, out: Path):
    from fastapi import FastAPI, Request
    from neo4j import AsyncGraphDatabase
    from app.db import neo4j as graph_db
    from app.db.database import engine
    from app.db.clickhouse import close_clickhouse
    graph_config = json.loads(Path(config["neo4j_config"]).read_text(encoding="utf-8"))

    @asynccontextmanager
    async def lifespan(app):
        graph_db._driver = AsyncGraphDatabase.driver(graph_config["uri"],
            auth=(graph_config["username"], graph_config["password"]),
            connection_timeout=5, max_transaction_retry_time=0)
        try:
            await graph_db._driver.verify_connectivity()
            yield
        finally:
            await graph_db._driver.close()
            await close_clickhouse()
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    for name in ROUTERS:
        router = importlib.import_module(f"app.api.v1.endpoints.{name}").router
        app.include_router(router, prefix="/api/v1")

    @app.get("/probe-ready")
    async def ready():
        return {"ready": True, "batch_run_id": config["run_id"]}

    @app.middleware("http")
    async def record(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/"):
            with (out / "api-requests.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"method": request.method, "path": request.url.path,
                                         "status": response.status_code}) + "\n")
        return response
    return app


def visible_response(body: dict) -> dict:
    """Visible assistant output and usage, excluding provider reasoning metadata."""
    output = {key: body[key] for key in ("id", "model", "created", "usage") if key in body}
    output["choices"] = []
    for choice in body.get("choices", []):
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = [block for block in content if isinstance(block, dict) and block.get("type") in {"text", "output_text"}]
        output["choices"].append({"index": choice.get("index"), "finish_reason": choice.get("finish_reason"),
            "message": {**{key: message[key] for key in ("role", "tool_calls", "refusal") if key in message}, "content": content}})
    if "error" in body:
        output["error"] = body["error"]
    return output


class ModelObserver:
    def __init__(self, out: Path):
        self.out, self.requests, self.responses, self.tools, self.factories = out, [], [], [], []
        self.cap_reached = False

    async def request(self, request):
        if len(self.requests) >= REQUEST_LIMIT:
            self.cap_reached = True
            raise RuntimeError("Test observation HTTP request cap reached")
        item = {"index": len(self.requests) + 1, "method": request.method, "path": request.url.path,
                "alert": CURRENT_ALERT.get(), "started_at": datetime.now(timezone.utc).isoformat()}
        self.requests.append(item)  # Reserve the request slot before the first await.
        request.extensions["testdata_request_index"] = item["index"]
        item["body"] = json.loads(await request.aread())
        save(self.out / f"model-request-{item['index']:02d}.json", item)

    async def response(self, response):
        await response.aread()
        try:
            body = visible_response(response.json())
        except (ValueError, TypeError, AttributeError):
            body = {"non_json_response": True}
        item = {"index": response.request.extensions["testdata_request_index"],
                "status_code": response.status_code, "body": body}
        self.responses.append(item)
        save(self.out / f"model-response-{item['index']:02d}.json", item)

    def factory(self, original, client):
        def observed(role, **kwargs):
            self.factories.append({"role": role, **{key: kwargs[key] for key in
                                   ("temperature", "max_tokens", "json_output") if key in kwargs}})
            return original(role, **{**kwargs, "max_retries": 0, "timeout": 45.0, "http_async_client": client})
        return observed

    def execute(self, original, render):
        async def observed(registry, name, arguments):
            item = {"index": len(self.tools) + 1, "alert": CURRENT_ALERT.get(), "tool": name, "args": arguments}
            self.tools.append(item)
            save(self.out / f"tool-request-{item['index']:02d}.json", item)
            started = time.monotonic()
            try:
                result = await original(registry, name, arguments)
                item.update({"result": result, "model_tool_content": render(result)})
                return result
            except BaseException as exc:
                item["interrupted_by"] = type(exc).__name__
                raise
            finally:
                item["duration_ms"] = round((time.monotonic() - started) * 1000)
                save(self.out / f"tool-result-{item['index']:02d}.json", item)
        return observed

    def summary(self):
        responded = {item["index"] for item in self.responses}
        return {"http_requests": len(self.requests), "http_responses": len(self.responses),
                "requests_without_response": [item["index"] for item in self.requests if item["index"] not in responded],
                "cap_reached": self.cap_reached, "factory_calls": self.factories, "tool_calls": len(self.tools),
                "sdk_max_retries": 0, "sdk_timeout_seconds": 45, "trust_env": False,
                "request_limit": REQUEST_LIMIT, "gateway_internal_attempts": "not_observed"}


async def consumer_offsets(consumer, *, require_empty=False) -> list[dict]:
    partitions = sorted(consumer.assignment(), key=lambda part: (part.topic, part.partition))
    if not partitions:
        raise ValueError("Consumer is not assigned")
    starts, ends = await consumer.beginning_offsets(partitions), await consumer.end_offsets(partitions)
    rows = []
    for part in partitions:
        position, committed = await consumer.position(part), await consumer.committed(part)
        row = {"topic": part.topic, "partition": part.partition, "beginning": starts[part],
               "end": ends[part], "position": position, "committed": committed}
        if require_empty and (starts[part] != 0 or ends[part] != 0 or position != 0 or committed not in (None, 0)):
            raise ValueError("The probe requires a new empty topic and zero consumer start")
        rows.append(row)
    return rows


def committed_count(rows: list[dict]) -> int:
    return sum(row["committed"] or 0 for row in rows)


async def consume(config: dict, out: Path, observer: ModelObserver) -> dict:
    import httpx
    from app.llm import factory
    # Patch before importing the worker and its graph, so original bound imports
    # receive the observation factory without altering role/model selection.
    original_factory = factory.make_chat_model
    worker = task = None
    processed = []
    admitted = set()
    ready = False
    result = {"status": "started", "processed": processed, "cleanup_errors": []}
    async with httpx.AsyncClient(trust_env=False, timeout=45,
            event_hooks={"request": [observer.request], "response": [observer.response]}) as client:
        observed_factory = observer.factory(original_factory, client)
        factory.make_chat_model = observed_factory
        from app.agents import auto_triage_agent
        from app.investigator import deep_investigation, ledger
        from app.prompting.tool_results import render_tool_message
        from app.tools.registry import ToolRegistry
        from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state
        auto_triage_agent.make_chat_model = deep_investigation.make_chat_model = observed_factory
        original_execute = ToolRegistry.execute
        ToolRegistry.execute = observer.execute(original_execute, render_tool_message)
        try:
            worker = FusedAlertTriageWorker(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
                topic=config["fused_topic"], group_id=config["group"], dlq_topic=config["dlq"],
                max_attempts=1, entity_concurrency=1)
            process, triage = worker._process_with_retry, worker.triage

            async def observed_triage(message):
                adopted = await triage(message)
                identity = CURRENT_ALERT.get()
                save(out / f"triage-result-{identity['index']:02d}.json", {"alert": identity, "adopted": adopted})
                return adopted

            async def observed_process(message):
                state = build_state(message)
                aid = str((state.raw_alert or {}).get("id")) if state is not None else None
                if (not ready or state is None or str(state.tenant_id) != config["tenant_id"] or
                        aid in admitted or len(admitted) >= EXPECTED_COUNT):
                    raise RuntimeError("Message outside the ready bounded test batch")
                admitted.add(aid)
                identity = {"index": len(admitted), "canonical_alert_id": aid,
                            "run_id": str(state.run_id), "tenant_id": str(state.tenant_id)}
                token = CURRENT_ALERT.set(identity)
                save(out / f"fused-input-{identity['index']:02d}.json", {"identity": identity, "message": message})
                record = {**identity, "outcome": "running"}
                processed.append(record)
                try:
                    ok = await process(message)
                    record["outcome"] = "durable_success" if ok else "dead_lettered"
                    return ok
                except BaseException as exc:
                    record.update({"outcome": "interrupted", "error_type": type(exc).__name__})
                    raise
                finally:
                    save(out / f"processed-{identity['index']:02d}.json", record)
                    CURRENT_ALERT.reset(token)

            worker.triage, worker._process_with_retry = observed_triage, observed_process
            task = asyncio.create_task(worker.start())
            async with asyncio.timeout(config["max_seconds"]):
                async with asyncio.timeout(30):
                    while not worker.attached or not worker._consumer.assignment():
                        if task.done():
                            await task
                            raise RuntimeError("Worker exited before readiness")
                        await asyncio.sleep(0.1)
                    result["start_offsets"] = await consumer_offsets(worker._consumer, require_empty=True)
                ready = True
                save(out / "consumer-ready.json", {"batch_run_id": config["run_id"], "tenant_id": config["tenant_id"],
                    "topic": config["fused_topic"], "group": config["group"], "dlq": config["dlq"],
                    "expected_count": EXPECTED_COUNT, "offsets": result["start_offsets"]})
                last_progress = None
                while True:
                    if (out / "stop-request.json").exists():
                        raise ProbeStopped("Driver requested cleanup")
                    if task.done():
                        await task
                        raise RuntimeError("Worker exited before batch completion")
                    rows = await consumer_offsets(worker._consumer)
                    count = committed_count(rows)
                    outcomes = [record["outcome"] for record in processed]
                    progress = {"committed_count": count, "processed": processed, "offsets": rows}
                    encoded = json.dumps(progress, sort_keys=True)
                    if encoded != last_progress:
                        save(out / "progress.json", progress, replace=True)
                        last_progress = encoded
                    if any(value in {"dead_lettered", "interrupted"} for value in outcomes):
                        raise RuntimeError("Batch processing did not yield durable success")
                    if sum(row["end"] for row in rows) > EXPECTED_COUNT or count > EXPECTED_COUNT:
                        raise RuntimeError("Additional messages appeared in the bounded topic")
                    if len(outcomes) == EXPECTED_COUNT and all(value == "durable_success" for value in outcomes) and count == EXPECTED_COUNT:
                        if any(row["end"] != row["position"] or row["position"] != row["committed"] for row in rows):
                            raise RuntimeError("Final consumer positions do not match committed delivery")
                        result.update({"status": "processed_and_committed", "final_offsets": rows})
                        break
                    await asyncio.sleep(0.2)
        except BaseException as exc:
            result.update({"status": "incomplete", "error_type": type(exc).__name__})
        finally:
            ready = False
            if worker is not None:
                try:
                    await worker.stop()
                except BaseException as exc:
                    result["cleanup_errors"].append({"stage": "worker", "error_type": type(exc).__name__})
            if task is not None:
                if not task.done():
                    task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except BaseException as exc:
                    result["worker_exit_error"] = type(exc).__name__
            try:
                await ledger.close_pool()
            except BaseException as exc:
                result["cleanup_errors"].append({"stage": "ledger", "error_type": type(exc).__name__})
            for module_name, attribute, method in (("app.core.cost_telemetry", "_POOL", "close"),
                    ("app.memory.institutional", "_POOL", "close"), ("app.memory.working", "_redis", "aclose")):
                module = sys.modules.get(module_name)
                resource = getattr(module, attribute, None)
                if resource is not None:
                    try:
                        async with asyncio.timeout(10):
                            await getattr(resource, method)()
                        setattr(module, attribute, None)
                    except BaseException as exc:
                        result["cleanup_errors"].append({"stage": module_name, "error_type": type(exc).__name__})
            ToolRegistry.execute = original_execute
            factory.make_chat_model = auto_triage_agent.make_chat_model = deep_investigation.make_chat_model = original_factory
    return result


async def run(config_path: Path, config: dict, out: Path) -> dict:
    import httpx
    observer = ModelObserver(out)
    api_process = None
    result = {"status": "incomplete", "cleanup_errors": []}
    try:
        with (out / "api-process.log").open("x", encoding="utf-8") as log:
            api_process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                "--config", str(config_path.resolve()), "--out", str(out), "--mode", "api"],
                stdout=log, stderr=subprocess.STDOUT, cwd=out)
        async with httpx.AsyncClient(trust_env=False, timeout=1) as http:
            async with asyncio.timeout(30):
                while True:
                    if api_process.poll() is not None:
                        raise RuntimeError("Temporary API exited before readiness")
                    try:
                        response = await http.get(f"http://127.0.0.1:{config['api_port']}/probe-ready")
                        if response.status_code == 200 and response.json().get("batch_run_id") == config["run_id"]:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.2)
        result = await consume(config, out, observer)
    except BaseException as exc:
        result.update({"status": "incomplete", "error_type": type(exc).__name__})
    finally:
        if api_process is not None and api_process.poll() is None:
            api_process.terminate()
            try:
                await asyncio.to_thread(api_process.wait, timeout=10)
            except subprocess.TimeoutExpired:
                api_process.kill()
                await asyncio.to_thread(api_process.wait, timeout=5)
                result["cleanup_errors"].append({"stage": "api", "error_type": "ForcedKill"})
        result.update({"schema_version": "socai2-agents-probe/v1", "batch_run_id": config["run_id"],
                       "tenant_id": config["tenant_id"], "topic": config["fused_topic"], "group": config["group"],
                       "dlq": config["dlq"], "models": observer.summary(), "expected_count": EXPECTED_COUNT,
                       "api_exit_code": api_process.returncode if api_process else None,
                       "content_assessment": "not_reviewed", "runtime": "local_source_not_production"})
        source_paths = [Path(__file__), *(ROOT / "services/agents/app" / name for name in
            ("workers/fused_alert_consumer.py", "agents/auto_triage_agent.py", "graph/runner.py",
             "investigator/deep_investigation.py", "investigator/ledger.py", "llm/factory.py", "tools/registry.py"))]
        result["source_sha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
        save(out / "summary.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("run", "api"), default="run", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        args.config = args.config.resolve()
        config = read_configuration(args.config)
        out = args.out.resolve()
        if not out.is_relative_to(ROOT / ".local"):
            raise ValueError("Private evidence output must be inside the repository .local directory")
        if args.mode == "run":
            out.mkdir(mode=0o700, parents=True, exist_ok=False)
        elif not out.is_dir() or out.stat().st_mode & 0o077:
            raise ValueError("The internal API process requires the parent's private output directory")
        os.umask(0o077)
        os.chdir(out)  # The service Settings default .env must not be loaded.
        configure_process(config, "api" if args.mode == "api" else "agents")
        if args.mode == "api":
            import uvicorn
            uvicorn.run(api_app(config, out), host="127.0.0.1", port=config["api_port"], access_log=False, log_level="error")
            return 0
        result = asyncio.run(run(args.config, config, out))
        print(json.dumps({"status": result["status"], "http_requests": result["models"]["http_requests"]}))
        return 0 if result["status"] == "processed_and_committed" and not result["cleanup_errors"] else 1
    except Exception as exc:
        print(json.dumps({"status": "probe_failed", "error_type": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
