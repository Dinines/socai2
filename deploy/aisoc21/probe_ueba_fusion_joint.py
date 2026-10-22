"""Local UEBA/Fusion processes, real project-21 PG/Redis/Kafka, unique test data.

Run with the prepared local Python environment. No deployment, source upload,
model call, production topic, existing entity, or existing consumer group is used.
Connection secrets remain in the ignored local configuration, never in receipts.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from uuid import UUID, uuid4


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / ".local/aisoc21/ueba-fusion-joint-20261021"
RUN = uuid4().hex[:12]
OUT = PRIVATE / RUN
OUT.mkdir(parents=True, exist_ok=False)
OUT.chmod(0o700)
TENANT = "b282f186-3e35-5cbd-93e9-14100108da5d"
BASE = {}
for line in (ROOT / ".local/aisoc21/private/fusion-1f.env").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        name, value = line.split("=", 1)
        BASE[name] = value
CA = str((PRIVATE / "ca.crt").resolve())
BASE.update(KAFKA_SSL_CAFILE=CA, PGSSLROOTCERT=CA, PGSSLMODE="verify-full")
TOPICS = {name: f"socai2.jointueba.{RUN}.{name}" for name in ["events", "anomalies", "alerts-on", "alerts-off", "fused"]}
GROUPS = {name: f"socai2.jointueba.{RUN}.{name}" for name in ["ueba", "fusion-on", "fusion-off"]}
BASE.update(
    KAFKA_TOPIC_ALERTS_RAW=TOPICS["alerts-on"], KAFKA_TOPIC_ALERTS_FUSED=TOPICS["fused"],
    KAFKA_TOPIC_UEBA_ANOMALIES=TOPICS["anomalies"], KAFKA_CONSUMER_GROUP=GROUPS["fusion-on"],
    AISOC_UEBA_FUSION_ENABLED="true", AISOC_EVENT_PROMOTION_ENABLED="false",
    AISOC_LAKE_WRITER_ENABLED="false", AISOC_DETECTION_ENGINE_ENABLED="false",
    AISOC_WINDOWED_DETECTION_ENABLED="false", AISOC_FEATURE_RBA="false",
    AISOC_ATTACK_CHAIN_GROUPING_ENABLED="false", AISOC_FUSION_MEMORY_NUDGE="0",
    AISOC_FUSE_ENRICHMENT="false", AISOC_VULN_BOOST="false",
)
os.environ.update(BASE)
sys.path.insert(0, str(ROOT / "services/fusion"))

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.structs import OffsetAndMetadata, TopicPartition
import redis.asyncio as redis
from app.core.config import settings
from app.core.kafka_security import kafka_client_kwargs
from app.models.alert import RawAlert
from app.services.alert_sink import AlertSink
from app.services.ueba_signal import UebaSignalCache


RECEIPT = {"run_id": RUN, "date": "2026-10-21", "tenant_id": TENANT,
           "execution": "local source processes with real infrastructure on 21",
           "topics": TOPICS, "groups": GROUPS, "cases": [], "status": "started",
           "deployment": False, "model_calls": 0, "production_topics_used": False}
PROCESSES = []


def save(phase):
    RECEIPT["phase"] = phase
    (OUT / "receipt.json").write_text(json.dumps(RECEIPT, ensure_ascii=False, indent=2, default=str) + "\n")
    print(json.dumps({"run_id": RUN, "phase": phase}), flush=True)


def environment(service, enabled=True):
    env = dict(os.environ, **BASE)
    env.update(PYTHONPATH=str(ROOT / f"services/{service}"), PYTHONDONTWRITEBYTECODE="1")
    if service == "ueba":
        env.update(DATABASE_URL=BASE["DATABASE_URL"].replace("sslmode=", "ssl="),
                   KAFKA_INPUT_TOPIC=TOPICS["events"], KAFKA_OUTPUT_TOPIC=TOPICS["anomalies"],
                   KAFKA_CONSUMER_GROUP=GROUPS["ueba"])
    else:
        env.update(AISOC_UEBA_FUSION_ENABLED="true" if enabled else "false",
                   KAFKA_TOPIC_ALERTS_RAW=TOPICS["alerts-on" if enabled else "alerts-off"],
                   KAFKA_CONSUMER_GROUP=GROUPS["fusion-on" if enabled else "fusion-off"])
    return env


async def start(service, port, enabled=True):
    label = service + ("-on" if enabled else "-off")
    log = (OUT / (label + ".log")).open("w")
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                         cwd=ROOT / f"services/{service}", env=environment(service, enabled), stdout=log, stderr=log)
    PROCESSES.append((p, log))
    for _ in range(60):
        if p.poll() is not None:
            raise RuntimeError(label + " exited; local private log retained")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=0.5) as response:
                if response.status == 200:
                    save(label + " ready")
                    return p
        except Exception:
            pass
        await asyncio.sleep(0.5)
    raise TimeoutError(label + " did not become ready")


async def read_message(topic, predicate):
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=settings.kafka_bootstrap_servers,
                               group_id=None, enable_auto_commit=False, auto_offset_reset="earliest", **kafka_client_kwargs())
    await consumer.start()
    try:
        end = time.monotonic() + 20
        while time.monotonic() < end:
            batches = await consumer.getmany(timeout_ms=500, max_records=30)
            for messages in batches.values():
                for message in messages:
                    value = json.loads(message.value)
                    if predicate(value):
                        return value, {"topic": topic, "partition": message.partition, "offset": message.offset}
        raise TimeoutError("no matching message in " + topic)
    finally:
        await consumer.stop()


async def main():
    sink = AlertSink(settings.database_url)
    cache_redis = redis.from_url(settings.redis_url)
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers, **kafka_client_kwargs())
    admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers, **kafka_client_kwargs())
    try:
        await sink.start()
        assert sink._pool is not None, "PG connection unavailable"
        assert await sink._pool.fetchval("SELECT EXISTS(SELECT 1 FROM tenants WHERE id=$1)", UUID(TENANT))
        assert await cache_redis.ping()
        await admin.start()
        await producer.start()
        await admin.create_topics([NewTopic(name, 1, 1, topic_configs={"retention.ms": "86400000"}) for name in TOPICS.values()])
        # Initialise ONLY this run's new groups at zero before starting latest consumers.
        for group, topics in [(GROUPS["ueba"], [TOPICS["events"]]),
                              (GROUPS["fusion-on"], [TOPICS["alerts-on"], TOPICS["anomalies"]]),
                              (GROUPS["fusion-off"], [TOPICS["alerts-off"]])]:
            c = AIOKafkaConsumer(bootstrap_servers=settings.kafka_bootstrap_servers, group_id=group,
                                enable_auto_commit=False, **kafka_client_kwargs())
            await c.start()
            try:
                partitions = [TopicPartition(t, 0) for t in topics]
                c.assign(partitions)
                await c.commit({tp: OffsetAndMetadata(0, "joint-new-group") for tp in partitions})
            finally:
                await c.stop()
        save("real infrastructure and private topics ready")

        entities = {level: f"joint-ueba-{RUN}-{level}" for level in ["medium", "high", "critical"]}
        preparation = '''import asyncio,json,os,uuid
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.services.baseline import BaselineService
from app.core.config import settings
async def main():
 assert settings.min_baseline_samples==30 and settings.anomaly_threshold==3
 engine=create_async_engine(settings.database_url)
 factory=async_sessionmaker(engine,expire_on_commit=False)
 rows=[]
 try:
  for entity in json.loads(os.environ["JOINT_ENTITIES"]).values():
   async with factory() as session:
    async with session.begin():
     svc=BaselineService(session)
     for i in range(30):
      row=await svc.update(uuid.UUID(os.environ["JOINT_TENANT"]),"user",entity,{"bytes_sent":80 if i%2==0 else 120})
     assert row.feature_stats["bytes_sent"]["count"]==30
     rows.append({"entity_id":entity,"baseline_id":str(row.id),"feature_stats":row.feature_stats})
  print(json.dumps(rows))
 finally:await engine.dispose()
asyncio.run(main())'''
        prep_env = environment("ueba")
        prep_env.update(JOINT_TENANT=TENANT, JOINT_ENTITIES=json.dumps(entities))
        prep = subprocess.run([sys.executable, "-c", preparation], env=prep_env, capture_output=True, text=True, timeout=40)
        (OUT / "baseline-preparation.log").write_text(prep.stdout + prep.stderr)
        if prep.returncode:
            raise RuntimeError("baseline preparation failed; private log retained")
        RECEIPT["baselines"] = json.loads(prep.stdout.splitlines()[-1])
        save("three original 30-sample PG baselines prepared")
        await start("ueba", 24906)
        fusion_on = await start("fusion", 24903)
        cache = UebaSignalCache(cache_redis)

        async def alert_case(label, entity, enabled, expected_confidence, expected_anomaly):
            source = uuid4()
            alert = RawAlert(id=source, tenant_id=TENANT, identity_version="source-v1", source_alert_id=source,
                             source="joint-ueba-" + RUN, title="UEBA joint verification " + label,
                             severity="high", username=entity, hostname="JUEBA-" + entity,
                             src_ip=f"2001:db8:{RUN[:4]}:{RUN[4:8]}::{list(entities.values()).index(entity)+1}",
                             mitre_tactics=["execution"], mitre_techniques=["T1059.001"], risk_score=0.5,
                             source_event_ids=["joint-control-" + str(source)])
            metadata = await producer.send_and_wait(TOPICS["alerts-on" if enabled else "alerts-off"], alert.model_dump_json().encode())
            value, coordinate = await read_message(TOPICS["fused"], lambda v: v.get("alert", {}).get("source_alert_id") == str(source))
            saved = await sink.lookup_delivery(alert)
            assert saved.exists and saved.snapshot
            persisted = saved.snapshot["fused"]
            for result in [value, persisted]:
                assert abs(result["confidence_score"] - expected_confidence) < 0.00001, (label, result["confidence_score"])
                assert abs(result["anomaly_score"] - expected_anomaly) < 0.00001
                assert abs(result["priority_score"] - 1) < 0.00001
                assert result["alert"]["risk_score"] == 0.5
            factors = [f for f in value["confidence_rationale"] if f["factor"] == "ueba_anomaly"]
            assert len(factors) == (1 if label in entities else 0)
            row = {"case": label, "source_alert_id": str(source), "alert_id": value["id"], "entity_id": entity,
                   "enabled": enabled, "input": {"topic": metadata.topic, "partition": metadata.partition, "offset": metadata.offset},
                   "output": coordinate, "confidence_score": value["confidence_score"], "confidence_label": value["confidence_label"],
                   "anomaly_score": value["anomaly_score"], "priority_score": value["priority_score"],
                   "ueba_factor": factors, "real_pg_snapshot_matches": True}
            RECEIPT["cases"].append(row)
            save(label + " real fused result verified")

        await alert_case("no_signal", entities["medium"], True, 0.656, 0.15)
        for level, feature, confidence, anomaly in [("medium", 171, 0.726, 0.45), ("high", 192, 0.796, 0.75), ("critical", 232, 0.856, 1.0)]:
            event_id = str(uuid4())
            event = {"schema_version": "v1", "event_id": event_id, "tenant_id": TENANT,
                     "entity_type": "user", "entity_id": entities[level], "event_type": "joint-verification",
                     "features": {"bytes_sent": feature}}
            sent = await producer.send_and_wait(TOPICS["events"], json.dumps(event).encode())
            message, coordinate = await read_message(TOPICS["anomalies"], lambda v: v.get("entity_id") == entities[level])
            assert message["risk_level"] == level
            pg = await sink._pool.fetchrow("SELECT id, source_event_id, anomaly_score, risk_level, features FROM ueba_anomalies WHERE id=$1 AND tenant_id=$2", UUID(message["anomaly_id"]), UUID(TENANT))
            assert pg and pg["source_event_id"] == event_id and pg["risk_level"] == level
            assert abs(pg["anomaly_score"] - message["anomaly_score"]) < 0.00001
            for _ in range(40):
                signal = await cache.lookup(TENANT, [("user", entities[level])])
                if signal and signal.risk_level == level:
                    break
                await asyncio.sleep(0.25)
            else:
                raise TimeoutError("Fusion did not cache the real " + level + " anomaly")
            RECEIPT.setdefault("actual_anomalies", []).append({"entity_id": entities[level], "source_event_id": event_id,
                "input": {"topic": sent.topic, "partition": sent.partition, "offset": sent.offset},
                "anomaly_id": message["anomaly_id"], "anomaly_score": message["anomaly_score"], "risk_level": level,
                "kafka_output": coordinate, "pg_features": json.loads(pg["features"]) if isinstance(pg["features"], str) else pg["features"],
                "fusion_cached_risk": signal.risk_level})
            await alert_case(level, entities[level], True, confidence, anomaly)

        fusion_on.terminate()
        await asyncio.to_thread(fusion_on.wait, 15)
        await start("fusion", 24903, enabled=False)
        await alert_case("disabled_with_cached_critical", entities["critical"], False, 0.656, 0.15)
        rows = await sink._pool.fetch("SELECT entity_id, feature_stats FROM ueba_entity_baselines WHERE tenant_id=$1 AND entity_id=ANY($2::text[])", UUID(TENANT), list(entities.values()))
        RECEIPT["final_baseline_counts"] = {r["entity_id"]: (json.loads(r["feature_stats"]) if isinstance(r["feature_stats"], str) else r["feature_stats"])["bytes_sent"]["count"] for r in rows}
        assert set(RECEIPT["final_baseline_counts"].values()) == {31}
        RECEIPT["status"] = "passed"
        save("joint validation passed; no deployment")
    except Exception as exc:
        RECEIPT["status"] = "failed"
        RECEIPT["error_type"] = type(exc).__name__
        # Error descriptions omit DSNs, credentials and complete process logs.
        RECEIPT["error"] = str(exc) if isinstance(exc, (AssertionError, TimeoutError)) else "see retained private execution log"
        save("stopped after failure; no input replay")
        raise
    finally:
        for p, log in PROCESSES:
            if p.poll() is None:
                p.terminate()
                try:
                    await asyncio.to_thread(p.wait, 15)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
            log.close()
        await producer.stop()
        await admin.close()
        await cache_redis.aclose()
        await sink.stop()
        RECEIPT["local_processes_stopped"] = all(p.poll() is not None for p, _ in PROCESSES)
        save("local processes stopped; test data retained")


if __name__ == "__main__":
    asyncio.run(main())
