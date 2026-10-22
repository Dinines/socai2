#!/usr/bin/env python3
"""Bounded generated alerts -> local ingress -> real Kafka/Fusion/Postgres.

Uses a fresh run directory, topics and Redis prefix. The original Fusion
message method is called explicitly; its consumer loop/offset commits and all
Agents/model paths are outside this probe. Never retry a failed publish.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import importlib.util
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / ".local/aisoc21/private"
PORT = 24930
API_URL = f"http://127.0.0.1:{PORT}"
MODEL_PREFIXES = ("OPENAI_", "OPENROUTER_", "ANTHROPIC_", "AZURE_OPENAI_", "LLM_", "LITELLM_", "OLLAMA_",
                  "GEMINI_", "GOOGLE_API_", "GOOGLE_GENERATIVE_", "MISTRAL_", "COHERE_",
                  "GROQ_", "TOGETHER_", "DEEPSEEK_", "LANGCHAIN_", "LANGSMITH_", "BEDROCK_")


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    path.chmod(0o600)


def read_env(name: str) -> dict[str, str]:
    from dotenv import dotenv_values
    return {key: value for key, value in dotenv_values(PRIVATE / name).items() if value is not None}


def initialize(out: Path, count: int) -> dict:
    if not out.is_relative_to(ROOT / ".local/aisoc21"):
        raise ValueError("Output must be in the ignored project local directory")
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    actor = json.loads((ROOT / ".local/aisoc21/attack-context-20261021/case-three-alerts.draft.json").read_text())
    run = uuid.uuid4().hex[:12]
    config = {"run_id": run, "count": count, "tenant_id": actor["tenant_id"],
              "actor_user_id": actor["actor_user_id"], "jwt_secret": secrets.token_urlsafe(48),
              "raw_topic": f"socai2.testdata.{run}.raw", "fused_topic": f"socai2.testdata.{run}.fused",
              "redis_prefix": f"socai2:testdata:{run}:", "event_time": datetime.now(UTC).isoformat()}
    save(out / "private.json", config)
    return config


def configure(out: Path, mode: str) -> dict:
    config = json.loads((out / "private.json").read_text())
    fusion, runtime = read_env("fusion-1f.env"), read_env("runtime.env")
    for name in list(os.environ):
        if name.startswith(MODEL_PREFIXES) or "MODEL" in name or name in {"AISOC_API_SERVICE_TOKEN", "AISOC_SERVICE_TOKEN"}:
            os.environ.pop(name, None)
    # Copy only the infrastructure values needed by these two local processes.
    os.environ.update({key: value for key, value in fusion.items() if key.startswith("KAFKA_")})
    ca = str(ROOT / ".local/aisoc21/ueba-fusion-joint-20261021/ca.crt")
    os.environ.update({
        "DATABASE_URL": runtime["DATABASE_URL"], "REDIS_URL": fusion["REDIS_URL"],
        "PGSSLROOTCERT": ca, "PGSSLMODE": "verify-full", "KAFKA_SSL_CAFILE": ca,
        "KAFKA_TOPIC_ALERTS_RAW": config["raw_topic"], "KAFKA_TOPIC_ALERTS_FUSED": config["fused_topic"],
        "KAFKA_TOPIC_RAW_EVENTS": f"socai2.testdata.{config['run_id']}.unused-events",
        "KAFKA_CONSUMER_GROUP": f"socai2.testdata.{config['run_id']}.unused-no-consumer",
        "SECRET_KEY": config["jwt_secret"], "ENVIRONMENT": "test", "ENV": "test", "DEBUG": "false",
        "AISOC_ALERT_IDENTITY_VERSION": "source-v1", "AISOC_DEV_AUTH_BYPASS": "false",
        "AISOC_DEV_MODE": "0", "AISOC_TRIAGE_WORKER_ENABLED": "false",
        "AISOC_EVENT_PROMOTION_ENABLED": "false", "AISOC_LAKE_WRITER_ENABLED": "false",
        "AISOC_DETECTION_ENGINE_ENABLED": "false", "AISOC_WINDOWED_DETECTION_ENABLED": "false",
        "AISOC_FEATURE_RBA": "false", "AISOC_ATTACK_CHAIN_GROUPING_ENABLED": "false",
        "AISOC_UEBA_FUSION_ENABLED": "false", "AISOC_FUSION_MEMORY_NUDGE": "0",
        "AISOC_FUSE_ENRICHMENT": "false", "AISOC_VULN_BOOST": "false",
        "AISOC_AGENT_ESCALATE_TO_GRAPH": "0", "AISOC_PLAYBOOK_EXECUTION_ENABLED": "false",
        "OTEL_SDK_DISABLED": "true", "PYTHONDONTWRITEBYTECODE": "1",
    })
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "services" / ("api" if mode == "api" else "fusion")))
    # Service exception logs can contain connection details. Receipt errors are
    # type-only, and this bounded probe suppresses third-party logging entirely.
    logging.disable(logging.CRITICAL)
    import structlog
    def discard_log(logger, method, event_dict):
        raise structlog.DropEvent
    structlog.configure(processors=[discard_log])
    return config


def api_app(out: Path, config: dict):
    from fastapi import FastAPI, Request
    from app.api.v1.endpoints import alert_ingress
    from app.db.database import engine

    @asynccontextmanager
    async def lifespan(app):
        # No migrations, DDL, API main lifespan, background workers or seeding.
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.include_router(alert_ingress.router, prefix="/api/v1")

    @app.get("/probe-ready")
    async def ready():
        return {"ready": True, "run_id": config["run_id"]}

    @app.middleware("http")
    async def record(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/api/v1/alert-ingress":
            with (out / "api-requests.jsonl").open("a") as stream:
                stream.write(json.dumps({"method": request.method, "path": request.url.path,
                                         "status": response.status_code}) + "\n")
        return response

    return app


class IsolatedRedis:
    """Original Redis commands, with a fresh prefix and no delete/flush API."""
    ALLOWED = ("aisoc:fusion:dedup:", "aisoc:fusion:correlation:",
               "aisoc:fusion:incident:", "aisoc:fusion:delivery:v1:")

    def __init__(self, client, prefix: str):
        self.client, self.prefix = client, prefix
        self.keys: set[str] = set()

    def key(self, key: str) -> str:
        if not isinstance(key, str) or not key.startswith(self.ALLOWED):
            raise ValueError("Unexpected Redis key outside the bounded Fusion path")
        result = self.prefix + key
        self.keys.add(result)
        return result

    async def get(self, key: str):
        return await self.client.get(self.key(key))

    async def set(self, key: str, value, **kwargs):
        return await self.client.set(self.key(key), value, **kwargs)


def testdata_tool():
    path = ROOT / "tools/testdata/alert_scenarios.py"
    spec = importlib.util.spec_from_file_location("socai2_probe_alert_scenarios", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Test data generator unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def coordinate(message) -> dict:
    return {"topic": message.topic, "partition": message.partition, "offset": message.offset}


async def consume_exact(consumer, count: int) -> list:
    messages = []
    async with asyncio.timeout(25):
        while len(messages) < count:
            batches = await consumer.getmany(timeout_ms=500, max_records=count + 1)
            for batch in batches.values():
                messages.extend(batch)
            if len(messages) > count:
                raise AssertionError("Unexpected additional message in isolated topic")
    return sorted(messages, key=lambda message: (message.partition, message.offset))


async def run(out: Path, config: dict) -> None:
    import httpx
    import jwt
    import redis.asyncio as redis
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from aiokafka.structs import TopicPartition
    from app.core.config import settings
    from app.core.kafka_security import kafka_client_kwargs
    from app.models.alert import RawAlert
    from app.services.alert_sink import AlertSink
    from app.services.correlator import Correlator
    from app.services.deduplicator import Deduplicator
    from app.services.delivery_recovery import restore_snapshot
    from app.services.fusion_engine import FusionEngine
    from app.services.ml_scorer import MLScorer
    from app.workers.consumer import FusionWorker

    tenant = uuid.UUID(config["tenant_id"])
    receipt = {key: value for key, value in config.items() if key not in {"jwt_secret", "actor_user_id"}}
    receipt.update(status="started", scope="generated existing alerts through real ingress/Kafka/Fusion/PG",
                   model_calls=0, agents_started=False, offset_commit_tested=False, consumer_loop_started=False,
                   deployment=False, production_topics_used=False, records=[])
    sink = AlertSink(settings.database_url)
    cache = redis.from_url(settings.redis_url, socket_connect_timeout=8, socket_timeout=8)
    isolated = IsolatedRedis(cache, config["redis_prefix"])
    admin = producer = raw_consumer = fused_consumer = api_process = api_log = None

    def phase(label: str):
        receipt["phase"] = label
        save(out / "receipt.json", receipt)
        print(json.dumps({"run_id": config["run_id"], "phase": label}), flush=True)

    try:
        phase("generating new bounded local fixtures")
        tool = testdata_tool()
        batch_dir = out / "batch"
        manifest = tool.generate_batch(run_id=config["run_id"], tenant=str(tenant),
                                       event_time=config["event_time"], count=config["count"], out=batch_dir)
        records = manifest["records"]
        assert len(records) == config["count"]
        inputs = [json.loads((batch_dir / record["payload"]).read_text()) for record in records]
        proposed = [RawAlert.model_validate({**payload, "tenant_id": str(tenant),
                     "identity_version": "source-v1", "source_alert_id": payload["id"]}) for payload in inputs]
        canonical_ids = [alert.deterministic_id() for alert in proposed]
        assert len(set(canonical_ids)) == config["count"]
        phase("read-only infrastructure and identity preflight before publishing")
        # Refuse to attach to any existing process on the fixed local port.
        with socket.socket() as port_check:
            port_check.bind(("127.0.0.1", PORT))
        await sink.start()
        assert sink._pool is not None
        actor = await sink._pool.fetchrow("SELECT tenant_id,is_active FROM users WHERE id=$1", uuid.UUID(config["actor_user_id"]))
        assert actor and actor["is_active"] and actor["tenant_id"] == tenant
        for alert in proposed:
            assert not (await sink.lookup_delivery(alert)).exists
        assert await cache.ping()
        admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers, **kafka_client_kwargs())
        await admin.start()
        topics = [config["raw_topic"], config["fused_topic"]]
        existing = set(await admin.list_topics())
        assert not existing.intersection(topics)
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers,
                    value_serializer=lambda value: json.dumps(value).encode(), acks="all", enable_idempotence=True,
                    request_timeout_ms=10000, **kafka_client_kwargs())
        await producer.start()
        receipt["preflight"] = {"postgres": True, "redis": True, "kafka": True,
                                "actor_active_same_tenant": True, "new_canonical_rows_absent": len(canonical_ids)}
        await admin.create_topics([NewTopic(topic, 1, 1, topic_configs={"retention.ms": "86400000"}) for topic in topics])
        for topic in topics:
            client = AIOKafkaConsumer(bootstrap_servers=settings.kafka_bootstrap_servers,
                     group_id=None, enable_auto_commit=False, **kafka_client_kwargs())
            if topic == config["raw_topic"]:
                raw_consumer = client
            else:
                fused_consumer = client
            await client.start()
            partition = TopicPartition(topic, 0)
            client.assign([partition])
            assert (await client.end_offsets([partition]))[partition] == 0
            client.seek(partition, 0)
        now = datetime.now(UTC)
        token = jwt.encode({"sub": config["actor_user_id"], "type": "access", "iat": int(now.timestamp()),
                            "exp": int(now.timestamp()) + 300}, config["jwt_secret"], algorithm="HS256")
        api_log = (out / "api.log").open("w")
        api_process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "api", "--out", str(out)],
                                       cwd=ROOT, stdout=api_log, stderr=api_log)
        async with httpx.AsyncClient(timeout=2) as http:
            async with asyncio.timeout(30):
                while True:
                    assert api_process.poll() is None
                    try:
                        response = await http.get(API_URL + "/probe-ready")
                        if response.status_code == 200 and response.json().get("run_id") == config["run_id"]:
                            break
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(0.2)
        phase("sending each new alert exactly once through authenticated ingress")
        os.environ["SOCAI_TESTDATA_PROBE_TOKEN"] = token
        try:
            sent = await asyncio.to_thread(tool.send_batch, input_dir=batch_dir,
                         url=API_URL + "/api/v1/alert-ingress", token_env="SOCAI_TESTDATA_PROBE_TOKEN",
                         receipt=out / "send-receipt.json", timeout=35)
        finally:
            os.environ.pop("SOCAI_TESTDATA_PROBE_TOKEN", None)
        assert sent["status"] == "accepted_only"
        accepted = {record["alert_id"]: record for record in sent["records"]}
        raw_messages = await consume_exact(raw_consumer, config["count"])
        save(out / "raw-observed.json", [{"coordinate": coordinate(message), "payload": json.loads(message.value)} for message in raw_messages])
        scorer = MLScorer()
        engine = FusionEngine(Deduplicator(isolated), Correlator(isolated), ml_scorer=scorer)
        worker = FusionWorker(engine, sink=sink)
        worker._producer = producer
        assert worker._consumer is None and not worker._running
        phase("processing original Fusion message method without consumer offset commits")
        received_ids: set[str] = set()
        for message in raw_messages:
            payload = json.loads(message.value)
            input_id = str(payload["id"])
            assert input_id not in received_ids and input_id in accepted
            received_ids.add(input_id)
            result = accepted[input_id]
            assert result["http_status"] == 202
            assert result["response"]["processing_confirmed"] is False
            assert result["response"]["message"] == coordinate(message)
            raw = RawAlert.model_validate(payload)
            canonical = raw.deterministic_id()
            assert raw.tenant_id == tenant and raw.identity_version == "source-v1"
            assert str(canonical) == result["response"]["canonical_alert_id"]
            await worker._process_message(payload, topic=message.topic, partition=message.partition, offset=message.offset)
            fused_message = (await consume_exact(fused_consumer, 1))[0]
            envelope = json.loads(fused_message.value)
            lookup = await sink.lookup_delivery(raw)
            assert lookup.exists and lookup.snapshot is not None
            restored = restore_snapshot(lookup.snapshot, raw).model_dump(mode="json")
            observed = {key: value for key, value in envelope.items() if key not in {"alert_row_id", "persist_outcome"}}
            assert restored == observed
            assert envelope["alert_row_id"] == str(canonical) and envelope["persist_outcome"] == "inserted"
            pg = await sink._pool.fetchrow("SELECT id,tenant_id,status,case_id,source_event_ids FROM alerts WHERE id=$1 AND tenant_id=$2", canonical, tenant)
            assert pg and pg["status"] == "new" and pg["case_id"] is None
            assert envelope["tenant_id"] == str(tenant) and envelope["id"] == str(canonical)
            assert envelope["fusion_decision"] in {"new_incident", "correlated"} and envelope["incident_id"]
            save(out / f"fused-{input_id}.json", {"coordinate": coordinate(fused_message), "payload": envelope})
            save(out / f"snapshot-{input_id}.json", lookup.snapshot)
            receipt["records"].append({"input_id": input_id, "canonical_alert_id": str(canonical),
                "api_status": 202, "api_processing_confirmed": False, "raw": coordinate(message),
                "fused": coordinate(fused_message), "pg_exists_same_tenant": True, "pg_status": pg["status"],
                "case_id": None, "persist_outcome": envelope["persist_outcome"],
                "incident_id": envelope["incident_id"], "fusion_decision": envelope["fusion_decision"],
                "snapshot_equals_fused": True, "confidence_score": envelope["confidence_score"],
                "anomaly_score": envelope["anomaly_score"], "priority_score": envelope["priority_score"]})
            phase("one original Fusion result persisted and observed")
        assert len(received_ids) == config["count"]
        assert not scorer._iso_trained and not scorer._lgbm_trained
        ids = [str(value) for value in canonical_ids] + [payload["id"] for payload in inputs]
        run_count = await sink._pool.fetchval(
            "SELECT count(*) FROM investigation_runs WHERE tenant_id=$1 AND "
            "(case_id=ANY($2::text[]) OR raw_alert->>'id'=ANY($2::text[]) OR raw_alert->'alert'->>'id'=ANY($2::text[]) "
            "OR raw_alert->'raw_event'->>'run_id'=$3 OR raw_alert->'alert'->'raw_event'->>'run_id'=$3)",
            tenant, ids, config["run_id"])
        assert run_count == 0
        for client, topic in [(raw_consumer, config["raw_topic"]), (fused_consumer, config["fused_topic"])]:
            partition = TopicPartition(topic, 0)
            assert (await client.end_offsets([partition]))[partition] == config["count"]
        receipt.update(status="passed", linked_investigation_runs=run_count, scoring="original untrained heuristic fallback",
                       redis_keys=sorted(isolated.keys), real_messages_published=config["count"] * 2,
                       offset_commits=0, cleanup_policy="retain new test evidence/topics and let isolated Redis TTL expire")
        phase("bounded ingress and Fusion verification passed")
    except BaseException as exc:
        receipt.update(status="failed", error_type=type(exc).__name__)
        phase("stopped without replay; partial evidence retained")
        raise
    finally:
        cleanup_errors = []
        if api_process is not None and api_process.poll() is None:
            api_process.terminate()
            try:
                await asyncio.to_thread(api_process.wait, 10)
            except subprocess.TimeoutExpired:
                api_process.kill()
                await asyncio.to_thread(api_process.wait, 5)
        if api_log is not None:
            api_log.close()
        for client in (raw_consumer, fused_consumer, producer, admin):
            if client is not None:
                try:
                    await client.close() if client is admin else await client.stop()
                except Exception as exc:
                    cleanup_errors.append(type(exc).__name__)
        for close in (cache.aclose, sink.stop):
            try:
                await close()
            except Exception as exc:
                cleanup_errors.append(type(exc).__name__)
        receipt["local_processes_stopped"] = api_process is None or api_process.poll() is not None
        receipt["cleanup_errors"] = cleanup_errors
        save(out / "receipt.json", receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "api"])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--count", type=int, choices=[1, 2, 3], default=3)
    args = parser.parse_args()
    os.umask(0o077)
    out = args.out.resolve()
    try:
        if args.mode == "run":
            initialize(out, args.count)
        configuration = configure(out, args.mode)
        if args.mode == "api":
            import uvicorn
            uvicorn.run(api_app(out, configuration), host="127.0.0.1", port=PORT,
                        log_config=None, log_level="critical", access_log=False)
        else:
            asyncio.run(run(out, configuration))
        return 0
    except BaseException as exc:
        print(json.dumps({"status": "stopped", "error_type": type(exc).__name__}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
