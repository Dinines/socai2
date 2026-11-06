"""Ingest exactly one frozen, isolated two-alert Kafka/Fusion card on 21. No model calls."""
import argparse
import asyncio
import contextlib
import hashlib
import ipaddress
import json
import os
import secrets
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import UUID

ROOT = Path("/opt/sting-aisoc-socai2/evidence/deployed-pilot-20261106-01")
DB = "socai2_pilot_20261106_01"
LAKE = "socai2_next_validation"
PREFIX = "socai2.validation.deployed-pilot-20261106-01"
GROUP = "socai2-validation-deployed-pilot-20261106-01"
TOPICS = [PREFIX + suffix for suffix in (".alerts.raw", ".raw_events", ".alerts.fused")]
PLAN_SHA = "df836637137521839990723e8969fa209d280c579518e00675f0761627902f1b"
API = "socai2-next-api"
CH = "sting-infra21-clickhouse-1"
PG = "spirithub-postgres-1"
WRITER = "socai2_pilot_20261106_01_writer"
IMAGE = "socai2-next-api:20261104-n15"


def require(valid, code):
    if not valid:
        raise RuntimeError(code)


def failure(exc):
    return {"passed": False, "error_type": type(exc).__name__, "frames": [
        {"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
        for f in traceback.extract_tb(exc.__traceback__)
    ]}


def write(name, value):
    with (ROOT / (name + ".json")).open("x", encoding="utf8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def command(args, data=None, timeout=35):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout, check=False)
    require(result.returncode == 0, "server_command_failed:" + args[0])
    return result.stdout.decode().strip()


def env(container):
    rows = json.loads(command(["docker", "inspect", container]))[0]["Config"]["Env"]
    return dict(row.split("=", 1) for row in rows if "=" in row)


def pg(sql):
    return command(["docker", "exec", "-i", PG, "psql", "-XAtq", "-v", "ON_ERROR_STOP=1",
                    "-U", "spirithub", "-d", DB], sql.encode())


def lake_query(sql):
    cfg = env(CH)
    return command(["docker", "exec", "-i", CH, "clickhouse-client", "--user", cfg.get("CLICKHOUSE_USER", "default"),
                    "--password", cfg.get("CLICKHOUSE_PASSWORD", ""), "--multiquery"], sql.encode())


def plan():
    contents = (ROOT / "plan.json").read_bytes()
    require(hashlib.sha256(contents).hexdigest() == PLAN_SHA, "plan_sha_mismatch")
    p = json.loads(contents)
    require(p["topic_prefix"] == PREFIX and p["group"] == GROUP, "incorrect_kafka_route")
    require(len(p["case"]["events"]) == len(p["case"]["alerts"]) == 2, "incorrect_card_size")
    require(len(set(p["canonical_alert_ids"])) == 2, "duplicate_alert")
    uuid = str(UUID(p["tenant_id"]))
    require(all(v["tenant_id"] == uuid for v in p["case"]["events"] + p["case"]["alerts"]), "tenant_mismatch")
    return p


def event_filter(p):
    ids = [str(UUID(v["event_id"])) for v in p["case"]["events"]]
    require(len(set(ids)) == 2, "duplicate_event")
    return f"tenant_id='{UUID(p['tenant_id'])}' AND event_id IN ('{ids[0]}','{ids[1]}')"


async def child(packet):
    os.environ.update(packet["environment"])
    root = Path(tempfile.mkdtemp(prefix="pilot-fusion-"))
    for name, content in packet["fusion_sources"].items():
        target = root / name
        require(target.resolve().is_relative_to(root / "app"), "invalid_source_path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes.fromhex(content))
    sys.path.insert(0, str(root))
    import redis.asyncio as redis
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from app.core.config import settings
    from app.core.kafka_security import kafka_client_kwargs
    from app.services.confidence import ConfidenceScorer
    from app.services.correlator import Correlator
    from app.services.deduplicator import Deduplicator
    from app.services.entity_risk import EntityRiskEngine
    from app.services.fusion_engine import FusionEngine
    from app.services.lake_writer import LakeWriter, _to_ip_obj, event_to_row
    from app.services.socai2_sink import Socai2AlertSink
    from app.workers.consumer import FusionWorker

    p, case = packet["plan"], packet["plan"]["case"]
    require(Path(sys.modules["app.core.config"].__file__).resolve().is_relative_to(root / "app"), "wrong_source")
    require([settings.kafka_topic_alerts_raw, settings.kafka_topic_raw_events, settings.kafka_topic_alerts_fused]
            == TOPICS and settings.kafka_consumer_group == GROUP, "child_topic_mismatch")
    require(urlsplit(settings.database_url).path == "/" + DB and settings.clickhouse_database == LAKE
            and settings.clickhouse_user == WRITER, "child_database_mismatch")
    require(not any((settings.ueba_fusion_enabled, settings.windowed_detection_enabled, settings.detection_engine_enabled,
                     settings.event_promotion_enabled, settings.attack_chain_grouping_enabled)), "unplanned_integration")
    rows = []
    for event in case["events"]:
        row = event_to_row(event)
        require(row and row["event_id"] == event["event_id"] and row["tenant_id"] == p["tenant_id"], "row_mismatch")
        row["source_ip"], row["dest_ip"] = _to_ip_obj(row["source_ip"]), _to_ip_obj(row["dest_ip"])
        rows.append(row)
    lake = LakeWriter(host=settings.clickhouse_host, port=settings.clickhouse_port, database=LAKE, user=WRITER,
                      password=settings.clickhouse_password, batch_size=1)
    require(lake._insert_sql.startswith("INSERT INTO " + LAKE + ".raw_events ("), "bad_writer_target")
    common = {"bootstrap_servers": settings.kafka_bootstrap_servers, **kafka_client_kwargs()}
    admin = AIOKafkaAdminClient(**common)
    await admin.start()
    try:
        require(set(TOPICS).isdisjoint(await admin.list_topics()), "topics_already_exist_no_replay")
        require(GROUP not in {g for g, _ in await admin.list_consumer_groups()}, "group_already_exists")
        if packet["preflight"]:
            import asyncpg
            from clickhouse_driver import Client
            conn = await asyncpg.connect(settings.database_url, timeout=10)
            try:
                require(await conn.fetchval("SELECT current_database()") == DB, "worker_db_unavailable")
            finally:
                await conn.close()
            async with redis.from_url(settings.redis_url) as rc:
                require(await rc.ping(), "worker_cache_unavailable")
            require(Client is not None, "lake_driver_missing")
            return {"passed": True, "preflight_only": True, "topics_absent": TOPICS, "group_absent": GROUP,
                    "projected_fields": [len(r) for r in rows]}
        await admin.create_topics([NewTopic(t, 1, 1) for t in TOPICS])
    finally:
        await admin.close()
    cache = redis.from_url(settings.redis_url)
    engine = FusionEngine(Deduplicator(cache), Correlator(cache), entity_risk=EntityRiskEngine(cache),
                          confidence_scorer=ConfidenceScorer(enabled=settings.confidence_enabled))
    sink = Socai2AlertSink(settings.database_url)
    worker = FusionWorker(engine, sink=sink, lake=lake)
    reader = AIOKafkaConsumer(TOPICS[2], **common, auto_offset_reset="earliest", group_id=None)
    producer = AIOKafkaProducer(**common)
    task = asyncio.create_task(worker.start())
    receipts, fused = [], []
    try:
        await producer.start()
        await reader.start()
        async with asyncio.timeout(35):
            while not worker.attached or {tp.topic for tp in worker._consumer.assignment()} != set(TOPICS[:2]):
                if task.done():
                    await task
                    raise RuntimeError("worker_failed_before_assignment")
                await asyncio.sleep(.1)
            assignment = worker._consumer.assignment()
            require(all(o == 0 for o in (await worker._consumer.end_offsets(assignment)).values()), "topics_not_empty")
            for partition in assignment:
                require(await worker._consumer.position(partition) == 0, "unexpected_start_offset")
            require(sink._pool is not None and lake._client is not None and not lake._disabled, "sinks_not_ready")
            await asyncio.to_thread(lake._client.execute, "SELECT 1")
        for topic, values in [(TOPICS[1], case["events"]), (TOPICS[0], case["alerts"])]:
            for value in values:
                body = json.dumps(value, ensure_ascii=False).encode()
                meta = await producer.send_and_wait(topic, body)
                receipts.append({"topic": meta.topic, "partition": meta.partition, "offset": meta.offset,
                                 "sha256": hashlib.sha256(body).hexdigest()})
        async with asyncio.timeout(100):
            while len(fused) < 2:
                if task.done():
                    await task
                    raise RuntimeError("worker_stopped")
                for msgs in (await reader.getmany(timeout_ms=500)).values():
                    for msg in msgs:
                        fused.append({"topic": msg.topic, "offset": msg.offset, "value": json.loads(msg.value)})
            committed = {}
            while sorted(committed.values()) != [2, 2]:
                committed = {tp.topic: (await worker._consumer.committed(tp) or 0) for tp in worker._consumer.assignment()}
                await asyncio.sleep(.1)
        await lake.flush()
        require(lake.rows_written == 2 and len(fused) == 2, "fusion_counts_incomplete")
        return {"passed": True, "receipts": receipts, "fused": fused, "planned_lake_rows": rows, "committed": committed,
                "metrics": worker.get_metrics(), "model_calls": 0}
    finally:
        await worker.stop()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await reader.stop()
        await producer.stop()
        await cache.aclose()


def verify(p, result):
    case, where = p["case"], event_filter(p)
    rows = [json.loads(line) for line in lake_query("SELECT * FROM " + LAKE + ".raw_events WHERE " + where
            + " ORDER BY event_id FORMAT JSONEachRow").splitlines()]
    require(len(rows) == 2, "validation_lake_incomplete")
    expected = {r["event_id"]: r for r in result["planned_lake_rows"]}
    require(set(expected) == {r["event_id"] for r in rows}, "lake_identity_mismatch")
    for row in rows:
        for field, value in expected[row["event_id"]].items():
            actual = row[field]
            if field == "event_time":
                actual, value = datetime.fromisoformat(actual), datetime.fromisoformat(value)
            elif field in {"source_ip", "dest_ip"}:
                actual, value = ipaddress.ip_address(actual), ipaddress.ip_address(value)
            require(actual == value, "lake_field_mismatch:" + field)
    require(lake_query("SELECT count() FROM aisoc.raw_events WHERE " + where) == "0", "old_lake_nonzero")
    by_source = {r["value"]["alert"]["source_alert_id"]: r["value"] for r in result["fused"]}
    members = [by_source[a["source_alert_id"]] for a in case["alerts"]]
    aids = [m["alert_row_id"] for m in members]
    incidents = {str(UUID(m["incident_id"])) for m in members}
    require(aids == p["canonical_alert_ids"] and len(incidents) == 1, "unexpected_correlation")
    iid = incidents.pop()
    sql = (f"SELECT alert_id FROM socai2.incident_alerts WHERE tenant_id='{UUID(p['tenant_id'])}' "
           f"AND incident_id='{iid}' ORDER BY alert_id")
    require(pg(sql).splitlines() == sorted(aids), "pg_members_mismatch")
    write("lake-readback", {"passed": True, "database": LAKE, "rows": rows, "old_lake_count": 0,
                           "plan_sha256": PLAN_SHA})
    write("ingest-subjects", {"passed": True, "alert_ids": aids, "incident_id": iid, "plan_sha256": PLAN_SHA})
    print(json.dumps({"passed": True, "alert_ids": aids, "incident_id": iid, "lake": len(rows), "old_lake": 0}))


def host(preflight):
    require(Path(__file__).resolve().parent == ROOT, "wrong_remote_directory")
    p = plan()
    cfg = json.loads((ROOT / "private/pilot-pg.json").read_text())
    require(cfg["DATABASE"] == DB and cfg["TENANT"] == p["tenant_id"] and cfg["FUSION_ROLE"] != cfg["API_ROLE"],
            "unexpected_new_pg")
    db_read = pg(f"SELECT current_database(); SELECT count(*) FROM socai2.alerts WHERE tenant_id='{UUID(p['tenant_id'])}'")
    require(db_read.splitlines() == [DB, "0"], "planned_pg_not_empty")
    pre = {db: lake_query(f"SELECT count() FROM {db}.raw_events WHERE " + event_filter(p)) for db in (LAKE, "aisoc")}
    require(pre == {LAKE: "0", "aisoc": "0"}, "event_already_exists")
    require(lake_query(f"SELECT count() FROM system.users WHERE name='{WRITER}'") == "0", "writer_already_exists")
    current_image = command(["docker", "inspect", "--format", "{{.Config.Image}}", API])
    require(current_image == IMAGE, "carrier_image_changed")
    fusion = env("socai2-fusion-1")
    app = env(API)
    redis = urlsplit(app["REDIS_URL"])
    pg_route = urlsplit(app["DATABASE_URL"])
    require((pg_route.hostname, pg_route.port) == ("192.168.1.21", 5432), "unknown_carrier_pg_route")
    dsn = "postgresql://" + cfg["FUSION_ROLE"] + ":" + quote(cfg["FUSION_DB_PASSWORD"], safe="") + \
          "@" + pg_route.hostname + ":" + str(pg_route.port) + "/" + DB
    password = secrets.token_hex(32)
    childenv = {k: v for k, v in fusion.items() if k.startswith("KAFKA_")}
    childenv.update({"KAFKA_TOPIC_ALERTS_RAW": TOPICS[0], "KAFKA_TOPIC_RAW_EVENTS": TOPICS[1],
                     "KAFKA_TOPIC_ALERTS_FUSED": TOPICS[2], "KAFKA_CONSUMER_GROUP": GROUP,
                     "KAFKA_SSL_CAFILE": "/run/certs/ca.crt", "DATABASE_URL": dsn,
                     "CLICKHOUSE_HOST": fusion["CLICKHOUSE_HOST"], "CLICKHOUSE_PORT": fusion["CLICKHOUSE_PORT"],
                     "CLICKHOUSE_DATABASE": LAKE, "CLICKHOUSE_USER": WRITER, "CLICKHOUSE_PASSWORD": password,
                     "REDIS_URL": urlunsplit(redis._replace(path="/13")), "ENVIRONMENT": "production",
                     "AISOC_ALERT_STORE_SCHEMA": "socai2", "AISOC_EVENT_PROMOTION_ENABLED": "false",
                     "AISOC_WINDOWED_DETECTION_ENABLED": "false", "AISOC_DETECTION_ENGINE_ENABLED": "false",
                     "AISOC_UEBA_FUSION_ENABLED": "false", "AISOC_ATTACK_CHAIN_GROUPING_ENABLED": "false",
                     "AISOC_FUSION_MEMORY_NUDGE": "false"})
    source = ROOT / "source/services/fusion"
    manifest = json.loads((ROOT / "source-manifest.json").read_bytes())
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    require(hashlib.sha256(canonical).hexdigest() == p["transferred_source_manifest_sha256"], "source_manifest_mismatch")
    expected_files = {k: v for k, v in manifest.items() if k.startswith("services/fusion/app/")}
    actual_files = {f.relative_to(ROOT / "source").as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                    for f in (source / "app").rglob("*") if f.is_file()}
    require(expected_files and actual_files == expected_files, "fusion_source_mismatch")
    files = {f.relative_to(source).as_posix(): f.read_bytes().hex() for f in (source / "app").rglob("*") if f.is_file()}
    packet = json.dumps({"plan": p, "environment": childenv, "preflight": preflight, "fusion_sources": files}).encode()
    cmd = ["docker", "run", "-i", "--rm", "--pull=never", "--network", "container:" + API,
           "--volumes-from", API + ":ro", "--read-only", "--tmpfs", "/tmp",
           "-v", str(Path(__file__).resolve()) + ":/pilot-runner.py:ro", "-w", "/tmp",
           "--entrypoint", "python", IMAGE, "-B", "/pilot-runner.py", "--child"]

    def launch():
        output = command(cmd, packet, timeout=210)
        lines = [line.removeprefix("PILOT_RESULT=") for line in output.splitlines() if line.startswith("PILOT_RESULT=")]
        require(len(lines) == 1, "missing_child_receipt")
        return json.loads(lines[0])

    if preflight:
        result = launch()
        print(json.dumps(result))
        require(result["passed"], "preflight_failed")
        return
    write("fusion-intent", {"at": datetime.now(timezone.utc).isoformat(), "plan_sha256": PLAN_SHA,
                            "database": DB, "topic": PREFIX, "group": GROUP, "lake_before": pre,
                            "model_calls": 0, "alerts": 2, "events": 2, "retries": 0})
    lake_query(f"CREATE USER {WRITER} IDENTIFIED WITH sha256_password BY '{password}'")
    try:
        lake_query(f"GRANT INSERT ON {LAKE}.raw_events TO {WRITER}")
        result = launch()
        write("fusion-result", result)
    finally:
        lake_query("DROP USER " + WRITER)
    if not result["passed"]:
        print(json.dumps(result))
        raise RuntimeError("fusion_failed_no_replay")
    verify(p, result)


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    cli.add_argument("--execute", action="store_true")
    cli.add_argument("--preflight", action="store_true")
    cli.add_argument("--verify-only", action="store_true")
    args = cli.parse_args()
    if args.child:
        try:
            receipt = asyncio.run(child(json.load(sys.stdin)))
        except Exception as exc:  # noqa: BLE001 -- retain sanitized frames, never service credentials
            receipt = failure(exc)
        print("PILOT_RESULT=" + json.dumps(receipt, default=str))
    elif args.verify_only:
        verify(plan(), json.loads((ROOT / "fusion-result.json").read_text()))
    elif args.execute or args.preflight:
        host(args.preflight)
    else:
        cli.error("select --execute for the single new card or --verify-only for existing rows")
