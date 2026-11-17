"""One repeatable-read snapshot for the two known S01 batches; no execution."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from uuid import UUID

import asyncpg


async def main():
    folder = Path(sys.argv[1])
    cfg = json.loads((folder / "capture-config.json").read_text())
    runtime = json.loads((folder / "source-runtime.json").read_text())
    private = json.loads(Path(runtime["private_http_source"]).read_text())
    output = folder / "analysis-pg-01.json"
    if output.exists():
        raise SystemExit("snapshot already exists; no repeated database capture")
    dsn = private["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn, timeout=runtime["probe_timeout_seconds"],
                                command_timeout=runtime["probe_timeout_seconds"])
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            tenant = UUID(cfg["tenant_id"])
            alerts = [UUID(v) for v in cfg["alert_ids"]]
            incidents = [UUID(v) for v in cfg["incident_ids"]]
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            who = dict(await conn.fetchrow("""SELECT current_database() AS database,current_user AS role,
                current_setting('transaction_read_only') AS readonly,ssl,version,
                statement_timestamp() AS captured_at FROM pg_stat_ssl WHERE pid=pg_backend_pid()"""))
            assert who["database"] == cfg["database"] and who["role"] == cfg["reader"]
            assert who["readonly"] == "on" and who["ssl"]
            rows = {}

            async def fetch(table, clause, values, order="id"):
                records = await conn.fetch("SELECT row_to_json(t) AS row FROM socai2." + table
                                           + " t WHERE tenant_id=$1 AND (" + clause + ") ORDER BY " + order,
                                           tenant, *values)
                rows[table] = [json.loads(row["row"]) for row in records]

            await fetch("alerts", "id=ANY($2::uuid[])", [alerts])
            for table in ("alert_materials", "alert_source_refs", "alert_objects", "alert_assessments"):
                await fetch(table, "alert_id=ANY($2::uuid[])", [alerts])
            await fetch("incidents", "id=ANY($2::uuid[])", [incidents])
            for table in ("incident_alerts", "incident_diagnoses"):
                await fetch(table, "incident_id=ANY($2::uuid[])", [incidents])
            subjects = alerts + incidents
            await fetch("analysis_tasks", "subject_id=ANY($2::uuid[])", [subjects])
            tasks = [UUID(t["id"]) for t in rows["analysis_tasks"]]
            await fetch("analysis_attempts", "task_id=ANY($2::uuid[])", [tasks])
            await fetch("runs", "alert_id=ANY($2::uuid[]) OR incident_id=ANY($3::uuid[])", [alerts, incidents])
            runs = [UUID(r["id"]) for r in rows["runs"]]
            for table in ("run_steps", "run_members", "results"):
                await fetch(table, "run_id=ANY($2::uuid[])", [runs])
            await fetch("artifacts", "alert_id=ANY($2::uuid[]) OR incident_id=ANY($3::uuid[]) OR run_id=ANY($4::uuid[])",
                        [alerts, incidents, runs])
            await fetch("analysis_subject_state", "subject_id=ANY($2::uuid[])", [subjects], "subject_type,subject_id")
            cases = await conn.fetchval("SELECT count(*) FROM socai2.cases WHERE tenant_id=$1", tenant)
            result = {"source": "real_postgres_readonly_snapshot", "identity": who, "batch_id": cfg["batch_id"],
                      "capture_config_sha256": hashlib.sha256((folder / "capture-config.json").read_bytes()).hexdigest(),
                      "tenant_case_count": cases, "counts": {k: len(v) for k, v in rows.items()}, "rows": rows}
            with output.open("x") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2, default=str)
                stream.write("\n")
            print(json.dumps({"status": "captured_not_yet_validated", "counts": result["counts"],
                              "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
    finally:
        await conn.close()


asyncio.run(main())
