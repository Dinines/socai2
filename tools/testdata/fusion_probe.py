#!/usr/bin/env python3
"""A fresh wire batch -> isolated Kafka -> original Fusion method -> PostgreSQL.

No API, Agents, models, consumer loop or offset commits. This is an explicit
real-infrastructure probe; local validation alone does not execute it.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys
from uuid import UUID

from alert_kafka import ROOT, _save_receipt, kafka_config, load_wire, send_kafka
from alert_scenarios import RUN_ID, sha256

REQUIRED_ENV = {"DATABASE_URL", "REDIS_URL", "KAFKA_BOOTSTRAP_SERVERS", "KAFKA_SECURITY_PROTOCOL",
                "KAFKA_TOPIC_ALERTS_RAW", "KAFKA_TOPIC_ALERTS_FUSED", "SOCAI_TESTDATA_REDIS_PREFIX"}
OPTIONAL_ENV = {"PGSSLROOTCERT", "PGSSLMODE", "KAFKA_SSL_CAFILE", "KAFKA_SSL_CERTFILE",
                "KAFKA_SSL_KEYFILE", "KAFKA_SASL_MECHANISM", "KAFKA_SASL_USERNAME", "KAFKA_SASL_PASSWORD"}
DISABLED = ("AISOC_EVENT_PROMOTION_ENABLED", "AISOC_LAKE_WRITER_ENABLED", "AISOC_DETECTION_ENGINE_ENABLED",
            "AISOC_WINDOWED_DETECTION_ENABLED", "AISOC_FEATURE_RBA", "AISOC_ATTACK_CHAIN_GROUPING_ENABLED",
            "AISOC_UEBA_FUSION_ENABLED", "AISOC_FUSION_MEMORY_NUDGE", "AISOC_FUSE_ENRICHMENT",
            "AISOC_VULN_BOOST", "AISOC_TENANT_IOC_MATCH")


def read_configuration(env_file: Path, run_id: str) -> dict[str, str]:
    """No ambient defaults or credential interpolation; only explicit transports."""
    from dotenv import dotenv_values

    if not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid wire run ID")
    if not env_file.is_file():
        raise ValueError("Explicit environment file required")
    values = dotenv_values(env_file, interpolate=False)
    if set(values) - REQUIRED_ENV - OPTIONAL_ENV or any(not values.get(key) for key in REQUIRED_ENV):
        raise ValueError("Environment file has missing or unsupported keys")
    if any(value is None or "${" in value for value in values.values()):
        raise ValueError("Environment values must be explicit")
    expected = {"KAFKA_TOPIC_ALERTS_RAW": f"socai2.testdata.{run_id}.raw",
                "KAFKA_TOPIC_ALERTS_FUSED": f"socai2.testdata.{run_id}.fused",
                "SOCAI_TESTDATA_REDIS_PREFIX": f"socai2:testdata:{run_id}:"}
    if any(values[key] != value for key, value in expected.items()):
        raise ValueError("Topics and Redis prefix must belong to this wire batch")
    if values["KAFKA_SECURITY_PROTOCOL"].strip().upper() in {"SSL", "SASL_SSL"} and not values.get("KAFKA_SSL_CAFILE"):
        raise ValueError("Kafka TLS requires an explicit CA file")
    if values.get("PGSSLMODE") == "verify-full" and not values.get("PGSSLROOTCERT"):
        raise ValueError("PostgreSQL verify-full requires an explicit CA file")
    return dict(values)


def configure_process(values: dict[str, str], run_id: str) -> None:
    """Configure only this probe process before importing the Fusion package."""
    if "app" in sys.modules:
        raise RuntimeError("Run the Fusion probe in a separate process")
    for key in list(os.environ):
        if key.startswith(("AISOC_", "KAFKA_", "OPENAI_", "LLM_", "LITELLM_", "PG", "DATABASE_", "REDIS_")):
            os.environ.pop(key)
    os.environ.update({key: value for key, value in values.items() if key != "SOCAI_TESTDATA_REDIS_PREFIX"})
    os.environ.update({key: "false" for key in DISABLED})
    os.environ.update({"ENVIRONMENT": "test", "ENV": "test", "AISOC_ALERT_SINK_ENABLED": "true",
                       "KAFKA_TOPIC_RAW_EVENTS": f"socai2.testdata.{run_id}.unused-events",
                       "KAFKA_CONSUMER_GROUP": f"socai2.testdata.{run_id}.unused-no-consumer",
                       "OTEL_SDK_DISABLED": "true", "PYTHONDONTWRITEBYTECODE": "1"})
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "services/fusion"))
    # Avoid the service Settings default .env file and suppress connection
    # exceptions that may include credentials. Receipts use exception types.
    from app.core import config
    config.settings = config.Settings(_env_file=None)
    logging.disable(logging.CRITICAL)
    import structlog
    def discard_log(logger, method, event_dict):
        raise structlog.DropEvent
    structlog.configure(processors=[discard_log])


class IsolatedRedis:
    """Original commands with a new prefix; no delete/flush operations."""
    ALLOWED = ("aisoc:fusion:dedup:", "aisoc:fusion:correlation:",
               "aisoc:fusion:incident:", "aisoc:fusion:delivery:v1:")

    def __init__(self, client, prefix: str):
        self.client, self.prefix = client, prefix
        self.keys: set[str] = set()

    def key(self, key: str) -> str:
        if not isinstance(key, str) or not key.startswith(self.ALLOWED):
            raise ValueError("Redis key outside the bounded Fusion path")
        result = self.prefix + key
        self.keys.add(result)
        return result

    async def get(self, key: str):
        return await self.client.get(self.key(key))

    async def set(self, key: str, value, **kwargs):
        return await self.client.set(self.key(key), value, **kwargs)


def coordinate(message) -> dict:
    return {key: getattr(message, key) for key in ("topic", "partition", "offset")}


async def consume_exact(consumer, count: int) -> list:
    messages = []
    async with asyncio.timeout(25):
        while len(messages) < count:
            for batch in (await consumer.getmany(timeout_ms=500, max_records=count + 1)).values():
                messages.extend(batch)
            if len(messages) > count:
                raise ValueError("Unexpected additional message in isolated topic")
    return sorted(messages, key=lambda message: (message.partition, message.offset))


def check_material(raw, envelope: dict, pg: dict) -> None:
    """Compare original material, allowing only the original identity/provenance adoption."""
    expected = raw.model_dump(mode="json")
    expected["id"] = str(raw.deterministic_id())
    source_ids = list(expected["source_event_ids"])
    if str(raw.id) not in source_ids:
        source_ids.append(str(raw.id))
    expected["source_event_ids"] = source_ids
    observed_alert = dict(envelope.get("alert") or {})
    if "created_at" not in raw.model_fields_set:
        # RawAlert supplies ingestion time independently on each parse. It is
        # not source event time and was not part of this wire's material.
        expected.pop("created_at", None)
        observed_alert.pop("created_at", None)
    if observed_alert != expected:
        raise ValueError("Fused alert material differs from normalized wire input")
    for key in ("title", "description", "severity", "raw_event", "mitre_tactics", "mitre_techniques", "source_event_ids"):
        observed = pg[key]
        if key in {"raw_event", "mitre_tactics", "mitre_techniques", "source_event_ids"} and isinstance(observed, str):
            observed = json.loads(observed)
        wanted = expected[key]
        if key == "title":
            wanted = wanted[:500]  # Original AlertSink schema adaptation.
        if key == "description":
            wanted = wanted or None
        if observed != wanted:
            raise ValueError("PostgreSQL alert material differs from fused material")
    if pg["event_time"] != datetime.fromisoformat(expected["event_time"].replace("Z", "+00:00")):
        raise ValueError("PostgreSQL event time differs from wire input")


async def run(*, wire_dir: Path, env_file: Path, out: Path, manifest: dict,
              wire_values: list[bytes], values: dict[str, str], receipt: dict) -> dict:
    cache = sink = admin = producer = raw_consumer = fused_consumer = None
    isolated = None
    def phase(label: str):
        receipt["phase"] = label
        _save_receipt(out / "receipt.json", receipt)
        print(json.dumps({"run_id": manifest["run_id"], "phase": label}), flush=True)

    try:
        import redis.asyncio as redis
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
        from aiokafka.admin import AIOKafkaAdminClient, NewTopic
        from aiokafka.structs import TopicPartition
        from app.core.config import settings
        from app.models.alert import RawAlert
        from app.services.alert_sink import AlertSink
        from app.services.correlator import Correlator
        from app.services.deduplicator import Deduplicator
        from app.services.delivery_recovery import restore_snapshot
        from app.services.dlq_sink import PostgresDLQ
        from app.services.fusion_engine import FusionEngine
        from app.services.ml_scorer import MLScorer
        from app.workers.consumer import FusionWorker

        tenant = UUID(manifest["tenant_id"])
        proposed = [RawAlert.model_validate_json(data) for data in wire_values]
        canonical_ids = [alert.deterministic_id() for alert in proposed]
        transport = kafka_config(env_file)
        raw_topic, fused_topic = values["KAFKA_TOPIC_ALERTS_RAW"], values["KAFKA_TOPIC_ALERTS_FUSED"]
        sink = AlertSink(settings.database_url)
        cache = redis.from_url(settings.redis_url, socket_connect_timeout=8, socket_timeout=8)
        isolated = IsolatedRedis(cache, values["SOCAI_TESTDATA_REDIS_PREFIX"])
        phase("read-only preflight before topic creation or publishing")
        await sink.start()
        if sink._pool is None:
            raise RuntimeError("PostgreSQL unavailable")
        async with sink._pool.acquire() as conn, conn.transaction(readonly=True):
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            if not await conn.fetchval("SELECT is_active FROM tenants WHERE id=$1", tenant):
                raise ValueError("Wire tenant must exist and be active")
            if await conn.fetchval("SELECT count(*) FROM alerts WHERE id=ANY($1::uuid[])", canonical_ids):
                raise ValueError("Canonical alert already exists; do not replay")
        if not await cache.ping():
            raise RuntimeError("Redis unavailable")
        async with asyncio.timeout(20):
            async for _ in cache.scan_iter(match=isolated.prefix + "*", count=100):
                raise ValueError("Redis prefix already exists; do not reuse")
        admin = AIOKafkaAdminClient(**transport)
        await admin.start()
        topics = [raw_topic, fused_topic]
        if set(await admin.list_topics()).intersection(topics):
            raise ValueError("Test topic already exists; do not replay")
        receipt["preflight"] = {"tenant_exists_active": True, "new_canonical_rows_absent": len(proposed),
                                "redis_prefix_absent": True, "topics_absent": topics}
        phase("creating two isolated topics and assigning observers at offset zero")
        await admin.create_topics([NewTopic(topic, 1, 1, topic_configs={"retention.ms": "86400000"}) for topic in topics])
        for topic in topics:
            client = AIOKafkaConsumer(**transport, group_id=None, enable_auto_commit=False)
            if topic == raw_topic:
                raw_consumer = client
            else:
                fused_consumer = client
            await client.start()
            partition = TopicPartition(topic, 0)
            client.assign([partition])
            if (await client.end_offsets([partition]))[partition] != 0:
                raise ValueError("Test topic is not empty")
            client.seek(partition, 0)
        producer = AIOKafkaProducer(**transport, value_serializer=lambda item: json.dumps(item).encode(),
                                    acks="all", enable_idempotence=True, request_timeout_ms=10000)
        await producer.start()
        scorer = MLScorer()
        worker = FusionWorker(FusionEngine(Deduplicator(isolated), Correlator(isolated), ml_scorer=scorer),
                              sink=sink, dlq=PostgresDLQ(lambda: sink._pool))
        worker._producer = producer
        phase("sending wire batch once using the Kafka sender")
        sent = await send_kafka(wire_dir=wire_dir, tenant=str(tenant), topic=raw_topic,
                                receipt=out / "send-receipt.json", config=transport)
        if sent["status"] != "accepted_only" or sent["cleanup_errors"]:
            raise RuntimeError("Kafka send did not complete cleanly; do not retry")
        raw_messages = await consume_exact(raw_consumer, len(proposed))
        _save_receipt(out / "raw-observed.json", [{"coordinate": coordinate(m), "payload": json.loads(m.value)} for m in raw_messages])
        accepted = {row["alert_id"]: row for row in sent["records"]}
        inputs = {str(raw.id): (raw, data) for raw, data in zip(proposed, wire_values)}
        seen = set()
        phase("processing original Fusion method without a consumer loop")
        for message in raw_messages:
            payload = json.loads(message.value)
            input_id = payload["id"]
            if input_id in seen or input_id not in inputs:
                raise ValueError("Unexpected or duplicate raw identity")
            seen.add(input_id)
            raw, original = inputs[input_id]
            canonical = raw.deterministic_id()
            if message.value != original or accepted[input_id]["message"] != coordinate(message):
                raise ValueError("Observed raw bytes or coordinate differ from send receipt")
            await worker._process_message(payload, **coordinate(message))
            fused_message = (await consume_exact(fused_consumer, 1))[0]
            envelope = json.loads(fused_message.value)
            _save_receipt(out / f"fused-{input_id}.json", {"coordinate": coordinate(fused_message), "payload": envelope})
            lookup = await sink.lookup_delivery(raw)
            if not lookup.exists or lookup.snapshot is None:
                raise ValueError("PostgreSQL delivery snapshot missing")
            _save_receipt(out / f"snapshot-{input_id}.json", lookup.snapshot)
            restored = restore_snapshot(lookup.snapshot, raw).model_dump(mode="json")
            if restored != {key: value for key, value in envelope.items() if key not in {"alert_row_id", "persist_outcome"}}:
                raise ValueError("PostgreSQL snapshot differs from fused message")
            if (envelope["alert_row_id"] != str(canonical) or envelope["id"] != str(canonical)
                    or envelope["tenant_id"] != str(tenant) or envelope["persist_outcome"] != "inserted"
                    or envelope["fusion_decision"] not in {"new_incident", "correlated"} or not envelope["incident_id"]):
                raise ValueError("Unexpected Fusion identity or persistence result")
            pg = await sink._pool.fetchrow("SELECT id,status,case_id,title,description,severity,raw_event,event_time,"
                "mitre_tactics,mitre_techniques,source_event_ids FROM alerts WHERE id=$1 AND tenant_id=$2", canonical, tenant)
            if not pg or pg["status"] != "new" or pg["case_id"] is not None:
                raise ValueError("Unexpected PostgreSQL alert state")
            check_material(raw, envelope, dict(pg))
            receipt["records"].append({"input_alert_id": input_id, "canonical_alert_id": str(canonical),
                "raw": coordinate(message), "fused": coordinate(fused_message), "snapshot_equals_fused": True,
                "material_matches": True, "pg_exists_same_tenant": True, "pg_status": pg["status"], "case_id": None,
                "persist_outcome": envelope["persist_outcome"], "incident_id": envelope["incident_id"],
                "fusion_decision": envelope["fusion_decision"], "confidence_score": envelope["confidence_score"],
                "anomaly_score": envelope["anomaly_score"], "priority_score": envelope["priority_score"]})
            phase("one Fusion result persisted and verified")
        ids = [str(item) for item in canonical_ids] + list(inputs)
        runs = await sink._pool.fetchval("SELECT count(*) FROM investigation_runs WHERE tenant_id=$1 AND "
            "(case_id=ANY($2::text[]) OR raw_alert->>'id'=ANY($2::text[]) OR raw_alert->'alert'->>'id'=ANY($2::text[]) "
            "OR raw_alert->'raw_event'->>'run_id'=$3 OR raw_alert->'alert'->'raw_event'->>'run_id'=$3)",
            tenant, ids, manifest["run_id"])
        dlq_count = await sink._pool.fetchval("SELECT count(*) FROM aisoc_dead_letters WHERE topic=$1", raw_topic)
        if runs or dlq_count or scorer._iso_trained or scorer._lgbm_trained:
            raise ValueError("Unexpected Run, dead letter or trained scorer")
        for client, topic in ((raw_consumer, raw_topic), (fused_consumer, fused_topic)):
            partition = TopicPartition(topic, 0)
            if (await client.end_offsets([partition]))[partition] != len(proposed):
                raise ValueError("Unexpected isolated topic end offset")
        receipt.update(status="passed", linked_investigation_runs=runs, fusion_dead_letters=dlq_count,
                       real_messages_published=2 * len(proposed), scoring="original untrained heuristic fallback")
        phase("bounded Kafka and Fusion verification passed")
    except BaseException as exc:
        receipt.update(status="failed", error_type=type(exc).__name__)
        phase("stopped without replay; partial evidence retained")
        raise
    finally:
        for client in (raw_consumer, fused_consumer, producer, admin, cache, sink):
            if client is None:
                continue
            try:
                close = client.close if client is admin else client.aclose if client is cache else client.stop
                await asyncio.wait_for(close(), 10)
            except BaseException as exc:
                receipt["cleanup_errors"].append(type(exc).__name__)
        receipt["redis_keys"] = sorted(isolated.keys) if isolated else []
        if receipt["cleanup_errors"] and receipt["status"] == "passed":
            receipt["status"] = "failed_cleanup"
        _save_receipt(out / "receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wire-dir", required=True, type=Path)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    receipt = None
    try:
        wire_dir, env_file, out = args.wire_dir.resolve(), args.env_file.resolve(), args.out.resolve()
        draft = json.loads((wire_dir / "manifest.json").read_text())
        manifest, wire_values = load_wire(wire_dir, draft["tenant_id"])
        values = read_configuration(env_file, manifest["run_id"])
        out.mkdir(parents=True, exist_ok=False, mode=0o700)
        receipt = {"schema_version": "socai2-fusion-probe/v1", "run_id": manifest["run_id"],
            "tenant_id": manifest["tenant_id"], "count": len(wire_values), "status": "starting",
            "wire_manifest_sha256": sha256((wire_dir / "manifest.json").read_bytes()),
            "raw_topic": values["KAFKA_TOPIC_ALERTS_RAW"], "fused_topic": values["KAFKA_TOPIC_ALERTS_FUSED"],
            "redis_prefix": values["SOCAI_TESTDATA_REDIS_PREFIX"], "fusion_dlq": "PostgreSQL aisoc_dead_letters",
            "consumer_loop_started": False, "offset_commits": 0, "api_started": False, "agents_started": False,
            "model_calls": 0, "deployment": False, "production_topics_used": False, "records": [], "cleanup_errors": [],
            "cleanup_policy": "retain test evidence and topics; isolated Redis keys expire by original TTL"}
        _save_receipt(out / "receipt.json", receipt)
        configure_process(values, manifest["run_id"])
        result = asyncio.run(run(wire_dir=wire_dir, env_file=env_file, out=out, manifest=manifest,
                                 wire_values=wire_values, values=values, receipt=receipt))
        return 0 if result["status"] == "passed" else 1
    except BaseException as exc:
        if receipt is not None:
            receipt.update(status="failed", error_type=type(exc).__name__)
            _save_receipt(out / "receipt.json", receipt)
        print(json.dumps({"status": "stopped", "error_type": type(exc).__name__}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
