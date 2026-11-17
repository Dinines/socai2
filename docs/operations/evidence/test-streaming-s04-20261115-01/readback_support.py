"""Existing S01 ordinary-reader snapshot helpers, reused for the S04 delta."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg
from clickhouse_driver import Client

TABLES = ("alerts", "alert_materials", "alert_source_refs", "alert_objects", "alert_assessments", "incidents", "incident_alerts", "incident_diagnoses", "cases", "case_alerts", "case_incidents", "case_assessments", "case_assessment_sources", "case_assessment_members", "analysis_tasks", "analysis_attempts", "runs", "run_steps", "run_members", "results", "result_members", "artifacts")

def check(value, label):
    if not value:
        raise AssertionError(label)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")

def normalized(value):
    return json.loads(json.dumps(value, default=str))

async def pg_snapshot(cfg, tenant, connector):
    private = json.loads(Path(cfg["postgres"]["private_runtime"]).read_text())
    dsn = private["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn, timeout=cfg["timeout_seconds"],
                                 command_timeout=cfg["postgres"]["statement_timeout_seconds"])
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", tenant)
            identity = dict(await conn.fetchrow("""SELECT current_database() AS database,
                current_user AS role, current_setting('transaction_read_only') AS readonly,
                ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"""))
            check(identity["database"] == cfg["postgres"]["database"], "wrong_pg_database")
            check(identity["role"] == cfg["postgres"]["reader"], "wrong_pg_reader")
            check(identity["readonly"] == "on" and identity["ssl"], "pg_not_readonly_tls")
            rows = {}
            for table in TABLES:
                values = await conn.fetch("SELECT row_to_json(t) AS row FROM socai2." + table
                                          + " t WHERE tenant_id=$1 ORDER BY id", UUID(tenant))
                rows[table] = [json.loads(row["row"]) for row in values]
            found = await conn.fetch("SELECT id,tenant_id FROM public.connectors WHERE tenant_id=$1 AND id=$2",
                                     UUID(tenant), UUID(connector))
            return {"identity": identity, "counts": {key: len(value) for key, value in rows.items()},
                    "connector": [dict(row) for row in found], "rows": rows}
    finally:
        await conn.close()

def lake_snapshot(cfg, tenant, query):
    lake = cfg["clickhouse"]
    private = json.loads(Path(lake["private_runtime"]).read_text())["reader"]
    client = Client(host=lake["host"], port=lake["native_port"], database=lake["database"],
                    user=private["user"], password=private["password"],
                    connect_timeout=cfg["timeout_seconds"], send_receive_timeout=cfg["timeout_seconds"],
                    settings={"readonly": 1, "max_execution_time": cfg["timeout_seconds"]})
    try:
        who = client.execute("SELECT currentDatabase(),currentUser()")[0]
        check(who == (lake["database"], lake["reader"]), "wrong_lake_identity")
        values, columns = client.execute("SELECT *,toUnixTimestamp64Milli(event_time) AS event_time_ms FROM "
            + lake["table"] + " WHERE tenant_id=%(tenant)s ORDER BY event_id", {"tenant": tenant}, with_column_types=True)
        rows = [dict(zip([col[0] for col in columns], value, strict=True)) for value in values]
        hits = {}
        for name, kind in (("authentication_activity", 3002), ("process_activity", 1007), ("network_connections", 4001)):
            result = client.execute("SELECT event_id FROM " + lake["table"] + " WHERE tenant_id=%(tenant)s "
                "AND src_hostname=%(host)s AND class_uid=%(kind)s "
                "AND event_time>=toDateTime64(%(start)s,3,'UTC') AND event_time<toDateTime64(%(end)s,3,'UTC') "
                "ORDER BY event_id", {"tenant": tenant, "host": query["hostname"], "kind": kind,
                    "start": datetime.fromisoformat(query["window_start"]).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "end": datetime.fromisoformat(query["window_end"]).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")})
            hits[name] = [str(row[0]) for row in result]
        return {"identity": {"database": who[0], "role": who[1]}, "rows": rows,
                "query": query, "hits": hits}
    finally:
        client.disconnect()
