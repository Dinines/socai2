"""Project durable Fusion deliveries and register A tasks; never call a model here."""
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
from projection_config import load_profile


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


async def handle(consumer, message, config):
    tenant, alert, incident = notification_ids(message.value)
    await project(tenant, [alert], [], config=config, expected_incident=incident)
    # An interrupted commit causes a redelivery of the same immutable material.
    await consumer.commit({TopicPartition(config["topic"], message.partition): message.offset + 1})


async def positions(consumer, config):
    # Fetch only broker metadata; never subscribe or auto-create the topic here.
    cluster = await consumer._client.fetch_all_metadata()
    partitions = [TopicPartition(config["topic"], i) for i in sorted(cluster.partitions_for_topic(config["topic"]) or [])]
    if not partitions:
        raise IngressError("fused_topic_unavailable")
    starts, ends = await asyncio.gather(consumer.beginning_offsets(partitions), consumer.end_offsets(partitions))
    return {str(p.partition): {"begin": starts[p], "end": ends[p], "committed": await consumer.committed(p)}
            for p in partitions}


def validate_offsets(offsets, activation, config, *, allow_missing=False):
    if activation.get("topic") != config["topic"] or activation.get("group") != config["group"] or set(activation["start"]) != set(offsets):
        raise IngressError("activation_scope_mismatch")
    for part, pos in offsets.items():
        committed = pos["committed"]
        if committed is None and not allow_missing:
            raise IngressError("projection_offset_missing")
        floor = activation["start"][part]
        target = floor if committed is None else committed
        if target < floor or not pos["begin"] <= target <= pos["end"]:
            raise IngressError("projection_offset_out_of_range")


def activation_record(offsets, config):
    boundary = Path(config["activation_file"])
    if not boundary.exists():
        if any(p["committed"] is not None for p in offsets.values()):
            raise IngressError("existing_group_without_activation")
        initial = {"topic": config["topic"], "group": config["group"], "start": {k: v["end"] for k, v in offsets.items()}}
        # Create the boundary before mutating Kafka; a retry uses precisely these offsets.
        with boundary.open("x", encoding="utf-8") as output:
            json.dump(initial, output)
            output.flush()
            os.fsync(output.fileno())
    activation = json.loads(boundary.read_text(encoding="utf-8"))
    validate_offsets(offsets, activation, config, allow_missing=True)
    return activation


async def activate(consumer, offsets, config):
    activation = activation_record(offsets, config)
    missing = {TopicPartition(config["topic"], int(k)): activation["start"][k] for k, v in offsets.items()
               if v["committed"] is None}
    if missing:
        consumer.assign(list(missing))
        consumer.pause(*missing)
        await consumer.commit(missing)
    return activation


async def database_ready(config):
    conn = await asyncpg.connect(database_url(), timeout=config["connect_timeout_seconds"], command_timeout=config["command_timeout_seconds"])
    try:
        async with conn.transaction(readonly=True):
            # Schema, role, function and RLS only; no business subject is queried.
            await check_identity(conn, UUID(int=0))
            ready = await conn.fetchval("""SELECT bool_and(has_table_privilege(current_user,t,p))
                FROM unnest(ARRAY['socai2.analysis_tasks','socai2.analysis_subject_state']) t
                CROSS JOIN unnest(ARRAY['SELECT','INSERT']) p""")
            if ready is not True:
                raise IngressError("analysis_task_registration_unavailable")
    finally:
        await conn.close()


async def serve(consumer, partitions, config):
    consumer.subscribe([config["topic"]])
    while True:
        messages = await consumer.getmany(timeout_ms=config["poll_timeout_ms"], max_records=config["max_records"])
        for records in messages.values():
            for record in records:
                try:
                    await handle(consumer, record, config)
                except Exception as exc:
                    code = exc.receipt["error"] if isinstance(exc, IngressError) else type(exc).__name__
                    print(json.dumps({"status": "held", "topic": config["topic"], "group": config["group"], "partition": record.partition,
                                      "offset": record.offset, "error": code}), flush=True)
                    raise
        if {str(p.partition) for p in consumer.assignment()} == set(partitions):
            Path(config["ready_file"]).touch()


async def run(mode, config):
    from app.core.kafka_security import kafka_client_kwargs

    await database_ready(config)
    security = kafka_client_kwargs(environment=config["environment"])
    if security["security_protocol"] not in ("SSL", "SASL_SSL"):
        raise IngressError("kafka_tls_required")
    consumer = AIOKafkaConsumer(bootstrap_servers=config["bootstrap_servers"],
        group_id=config["group"], client_id=config["client_id"], auto_offset_reset="none", enable_auto_commit=False,
        request_timeout_ms=config["request_timeout_ms"], max_partition_fetch_bytes=config["max_partition_fetch_bytes"], **security)
    await consumer.start()
    try:
        offsets = await positions(consumer, config)
        if mode == "activate":
            print(json.dumps(await activate(consumer, offsets, config)), flush=True)
        else:
            activation = json.loads(Path(config["activation_file"]).read_text(encoding="utf-8"))
            validate_offsets(offsets, activation, config)
            if mode == "status":
                print(json.dumps({"group": config["group"], "topic": config["topic"], "partitions": offsets,
                    "activation": activation["start"], "database": os.environ["SOCAI2_SERVICE_DATABASE_NAME"], "schema": "socai2"}))
            else:
                await serve(consumer, offsets, config)
    finally:
        await consumer.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("activate", "serve", "status", "health"))
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    config = load_profile(args.profile)
    ready = Path(config["ready_file"])
    if args.mode == "health":
        return int(not ready.exists() or time.time() - ready.stat().st_mtime > config["health_max_age_seconds"])
    if not Path(config["source_pythonpath"]).is_dir():
        raise IngressError("source_runtime_unavailable")
    sys.path.insert(0, config["source_pythonpath"])
    if args.mode == "serve":
        ready.unlink(missing_ok=True)
    try:
        asyncio.run(run(args.mode, config))
    except Exception as exc:  # noqa: BLE001 -- report a bounded error code without credentials or record contents
        code = exc.receipt["error"] if isinstance(exc, IngressError) else type(exc).__name__
        print(json.dumps({"status": "unavailable", "error": code}), flush=True)
        return 1
    finally:
        if args.mode == "serve":
            ready.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
