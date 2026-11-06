"""Mirror new, durable production Fusion deliveries by ID. Never start an investigation."""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from uuid import UUID

import asyncpg
from aiokafka import AIOKafkaConsumer, TopicPartition
from production_ingress import IngressError, check_identity, database_url, project

TOPIC = "socai2.alerts.fused"
GROUP = "socai2-investigation-projection-v1"
BOUNDARY = Path("/var/lib/socai2-projection/activation.json")
READY = Path("/tmp/production-projection-ready")


def notification_ids(body):
    try:
        packet = json.loads(body)
        tenant = UUID(packet["tenant_id"])
        alert = UUID(packet["id"])
        incident = UUID(packet["incident_id"])
        if UUID(packet["alert_row_id"]) != alert or packet["persist_outcome"] not in ("inserted", "duplicate"):
            raise ValueError("unconfirmed")
    except (AttributeError, ValueError, KeyError, TypeError) as exc:
        raise IngressError("invalid_fusion_notification") from exc
    return tenant, alert, incident


async def handle(consumer, message):
    tenant, alert, incident = notification_ids(message.value)
    await project(tenant, [alert], [], expected_incident=incident)
    # An interrupted commit causes a redelivery of the same immutable material.
    await consumer.commit({TopicPartition(TOPIC, message.partition): message.offset + 1})


async def positions(consumer):
    # Fetch only broker metadata; never subscribe or auto-create the topic here.
    cluster = await consumer._client.fetch_all_metadata()
    partitions = [TopicPartition(TOPIC, i) for i in sorted(cluster.partitions_for_topic(TOPIC) or [])]
    if not partitions:
        raise IngressError("fused_topic_unavailable")
    starts, ends = await asyncio.gather(consumer.beginning_offsets(partitions), consumer.end_offsets(partitions))
    return {str(p.partition): {"begin": starts[p], "end": ends[p], "committed": await consumer.committed(p)}
            for p in partitions}


def validate_offsets(offsets, activation, *, allow_missing=False):
    if activation.get("topic") != TOPIC or activation.get("group") != GROUP or set(activation["start"]) != set(offsets):
        raise IngressError("activation_scope_mismatch")
    for part, pos in offsets.items():
        committed = pos["committed"]
        if committed is None and not allow_missing:
            raise IngressError("projection_offset_missing")
        floor = activation["start"][part]
        target = floor if committed is None else committed
        if target < floor or not pos["begin"] <= target <= pos["end"]:
            raise IngressError("projection_offset_out_of_range")


def activation_record(offsets):
    if not BOUNDARY.exists():
        if any(p["committed"] is not None for p in offsets.values()):
            raise IngressError("existing_group_without_activation")
        initial = {"topic": TOPIC, "group": GROUP, "start": {k: v["end"] for k, v in offsets.items()}}
        # Create the boundary before mutating Kafka; a retry uses precisely these offsets.
        with BOUNDARY.open("x", encoding="utf-8") as output:
            json.dump(initial, output)
            output.flush()
            os.fsync(output.fileno())
    activation = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    validate_offsets(offsets, activation, allow_missing=True)
    return activation


async def activate(consumer, offsets):
    activation = activation_record(offsets)
    missing = {TopicPartition(TOPIC, int(k)): activation["start"][k] for k, v in offsets.items()
               if v["committed"] is None}
    if missing:
        consumer.assign(list(missing))
        consumer.pause(*missing)
        await consumer.commit(missing)
    return activation


async def database_ready():
    conn = await asyncpg.connect(database_url(), timeout=10, command_timeout=10)
    try:
        async with conn.transaction(readonly=True):
            # Schema, role, function and RLS only; no business subject is queried.
            await check_identity(conn, UUID(int=0))
    finally:
        await conn.close()


async def serve(consumer, partitions):
    consumer.subscribe([TOPIC])
    while True:
        messages = await consumer.getmany(timeout_ms=2500, max_records=1)
        for records in messages.values():
            for record in records:
                try:
                    await handle(consumer, record)
                except Exception as exc:
                    code = exc.receipt["error"] if isinstance(exc, IngressError) else type(exc).__name__
                    print(json.dumps({"status": "held", "partition": record.partition,
                                      "offset": record.offset, "error": code}), flush=True)
                    raise
        if {str(p.partition) for p in consumer.assignment()} == set(partitions):
            READY.touch()


async def run(mode):
    from app.core.kafka_security import kafka_client_kwargs

    await database_ready()
    security = kafka_client_kwargs(environment="production")
    if security["security_protocol"] not in ("SSL", "SASL_SSL"):
        raise IngressError("kafka_tls_required")
    consumer = AIOKafkaConsumer(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
                                group_id=GROUP, client_id=GROUP, auto_offset_reset="none", enable_auto_commit=False,
                                request_timeout_ms=20000, max_partition_fetch_bytes=2 * 1024 * 1024, **security)
    await consumer.start()
    try:
        offsets = await positions(consumer)
        if mode == "activate":
            print(json.dumps(await activate(consumer, offsets)), flush=True)
        else:
            activation = json.loads(BOUNDARY.read_text(encoding="utf-8"))
            validate_offsets(offsets, activation)
            if mode == "status":
                print(json.dumps({"group": GROUP, "topic": TOPIC, "partitions": offsets,
                                  "activation": activation["start"], "database": "aisoc", "schema": "socai2"}))
            else:
                await serve(consumer, offsets)
    finally:
        await consumer.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("activate", "serve", "status", "health"))
    args = parser.parse_args()
    if args.mode == "health":
        return int(not READY.exists() or time.time() - READY.stat().st_mtime > 75)
    if Path("/opt/processor/smoke-fusion").is_dir():
        sys.path.insert(0, "/opt/processor/smoke-fusion")
    if args.mode == "serve":
        READY.unlink(missing_ok=True)
    try:
        asyncio.run(run(args.mode))
    except Exception as exc:  # noqa: BLE001 -- report a bounded error code without credentials or record contents
        code = exc.receipt["error"] if isinstance(exc, IngressError) else type(exc).__name__
        print(json.dumps({"status": "unavailable", "error": code}), flush=True)
        return 1
    finally:
        if args.mode == "serve":
            READY.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
