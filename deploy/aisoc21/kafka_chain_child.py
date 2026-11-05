"""Actual Fusion worker in an isolated child process, real Kafka/PG/CH/Redis."""
import asyncio
import contextlib
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


async def execute(packet):
    # Separate package root prevents importing API's app as Fusion's app.
    root = Path(tempfile.mkdtemp(prefix="socai2-kafka-k1-"))
    for name, body in packet["files"].items():
        path = root / name
        assert path.resolve().is_relative_to(root) and name.endswith(".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    sys.path.insert(0, str(root))
    os.environ.update(packet["environment"])
    import redis.asyncio as redis
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from app.core.config import settings
    from app.core.kafka_security import kafka_client_kwargs
    from app.services.correlator import Correlator
    from app.services.deduplicator import Deduplicator
    from app.services.entity_risk import EntityRiskEngine
    from app.services.fusion_engine import FusionEngine
    from app.services.lake_writer import LakeWriter
    from app.services.socai2_sink import Socai2AlertSink
    from app.workers.consumer import FusionWorker

    topics = [settings.kafka_topic_alerts_raw, settings.kafka_topic_raw_events, settings.kafka_topic_alerts_fused]
    assert all(t.startswith(packet['topic_prefix'] + '.') for t in topics)
    common = {"bootstrap_servers": settings.kafka_bootstrap_servers, **kafka_client_kwargs()}
    admin = AIOKafkaAdminClient(**common)
    await admin.start()
    try:
        existing = await admin.list_topics()
        assert not set(topics) & set(existing), "fixed Kafka batch already exists; no replay"
        await admin.create_topics([NewTopic(t, 1, 1) for t in topics])
    finally:
        await admin.close()
    cache = redis.from_url(settings.redis_url)
    sink = Socai2AlertSink(settings.database_url)
    lake = LakeWriter(host=settings.clickhouse_host, port=settings.clickhouse_port,
        database=settings.clickhouse_database, user=settings.clickhouse_user,
        password=settings.clickhouse_password, batch_size=1)
    engine = FusionEngine(Deduplicator(cache), Correlator(cache), entity_risk=EntityRiskEngine(cache))
    # These optional vendor/detection/session integrations are explicitly out
    # of this fixture profile; the alert consumer, engine and writers are real.
    worker = FusionWorker(engine, sink=sink, lake=lake)
    producer = AIOKafkaProducer(**common, value_serializer=lambda x: json.dumps(x).encode())
    reader = AIOKafkaConsumer(topics[2], **common, auto_offset_reset="earliest",
        group_id=None, value_deserializer=lambda x: json.loads(x))
    task = asyncio.create_task(worker.start())
    receipts, fused = [], []
    try:
        await producer.start()
        await reader.start()
        for _ in range(120):
            if task.done():
                await task
                raise RuntimeError("worker exited before fixture dispatch")
            if worker.attached and worker._consumer.assignment():
                break
            await asyncio.sleep(.25)
        else:
            raise RuntimeError("isolated consumer not assigned")
        for case in packet["cases"]:
            for kind, topic, values in (("event", topics[1], case["events"]), ("alert", topics[0], case["alerts"])):
                for index, value in enumerate(values):
                    meta = await producer.send_and_wait(topic, value)
                    receipts.append({"case": case["key"], "kind": kind, "index": index, "topic": meta.topic,
                        "partition": meta.partition, "offset": meta.offset,
                        "sha256": hashlib.sha256(json.dumps(value).encode()).hexdigest()})
        # Optional exact replay exercises persisted-first-result recovery.
        if packet.get('replay_alert', True):
            replay = packet["cases"][0]["alerts"][0]
            meta = await producer.send_and_wait(topics[0], replay)
            receipts.append({"case": packet["cases"][0]["key"], "kind": "exact_replay", "index": 0,
                             "topic": meta.topic, "partition": meta.partition, "offset": meta.offset})
        expected_fused = packet.get('expected_fused', 13)
        deadline = asyncio.get_running_loop().time() + 100
        while len(fused) < expected_fused and asyncio.get_running_loop().time() < deadline:
            if task.done():
                await task
                raise RuntimeError("worker stopped before all fused outputs")
            batch = await reader.getmany(timeout_ms=1000)
            for messages in batch.values():
                for message in messages:
                    fused.append({"topic": message.topic, "partition": message.partition,
                        "offset": message.offset, "value": message.value})
        await lake.flush()
        committed = []
        for _ in range(30):
            committed = []
            for tp in worker._consumer.assignment():
                committed.append({"topic": tp.topic, "partition": tp.partition,
                    "committed": await worker._consumer.committed(tp), "end": (await worker._consumer.end_offsets([tp]))[tp]})
            if all((x['committed'] or 0) == x['end'] for x in committed):
                break
            await asyncio.sleep(.2)
        result = {"receipts": receipts, "fused": fused, "committed": committed, "metrics": worker.get_metrics(),
            "optional_integrations": "native/windowed detection, promotion, UEBA, sessions, AI assets, external enrichment disabled"}
        result["passed"] = (len(fused) == expected_fused and lake.rows_written == packet.get('expected_lake', 8)
            and all((x["committed"] or 0) == x["end"] for x in committed))
        print("K1_RESULT=" + json.dumps(result, default=str), flush=True)
    finally:
        await worker.stop()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await reader.stop()
        await producer.stop()
        await cache.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(execute(json.load(sys.stdin)))
    except Exception as exc:  # noqa: BLE001 -- sanitized failure receipt, no credentials
        import traceback
        print('K1_RESULT=' + json.dumps({'passed': False, 'error_type': type(exc).__name__,
            'frames': [{'file': Path(x.filename).name, 'line': x.lineno, 'name': x.name}
                       for x in traceback.extract_tb(exc.__traceback__)]}), flush=True)
