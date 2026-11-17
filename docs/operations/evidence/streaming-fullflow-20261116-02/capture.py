"""One ordinary HTTP reader snapshot for the actual new A/I/Case identities."""

import asyncio
import json
import sys
from uuid import UUID

from app.db.database import engine
from sqlalchemy import text

CFG = json.loads(sys.stdin.read())


async def main():
    rows = {}
    params = {
        "tenant": UUID(CFG["tenant_id"]),
        "alerts": [UUID(x) for x in CFG["alert_ids"]],
        "incidents": [UUID(x) for x in CFG["incident_ids"]],
        "cases": [UUID(x) for x in CFG["case_ids"]],
    }
    async with engine.connect() as conn:
        await conn.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        )
        await conn.execute(
            text("SELECT set_config('app.current_tenant_id',:tenant,true)"),
            {"tenant": CFG["tenant_id"]},
        )
        who = dict(
            (
                await conn.execute(
                    text(
                        "SELECT current_database() AS database,current_user AS role,current_setting('transaction_read_only') AS readonly,ssl,version,statement_timestamp() AS captured_at FROM pg_stat_ssl WHERE pid=pg_backend_pid()"
                    )
                )
            )
            .mappings()
            .one()
        )
        assert (
            who["database"] == CFG["database"]["name"]
            and who["role"] == CFG["database"]["reader_role"]
            and who["readonly"] == "on"
            and who["ssl"]
        )

        async def fetch(table, clause, order="id"):
            values = await conn.execute(
                text(
                    "SELECT row_to_json(t) FROM socai2."
                    + table
                    + " t WHERE tenant_id=:tenant AND ("
                    + clause
                    + ") ORDER BY "
                    + order
                ),
                params,
            )
            rows[table] = list(values.scalars())

        for table, key in [
            ("alerts", "alerts"),
            ("incidents", "incidents"),
            ("cases", "cases"),
        ]:
            await fetch(table, "id=ANY(CAST(:" + key + " AS uuid[]))")
        assert all(len(rows[t]) == len(params[t]) for t in ("alerts", "incidents"))
        assert len(rows["cases"]) == len(params["cases"])
        for table in [
            "alert_materials",
            "alert_source_refs",
            "alert_objects",
            "alert_assessments",
        ]:
            await fetch(table, "alert_id=ANY(CAST(:alerts AS uuid[]))")
        for table in ["incident_alerts", "incident_diagnoses"]:
            await fetch(table, "incident_id=ANY(CAST(:incidents AS uuid[]))")
        for table in [
            "case_alerts",
            "case_incidents",
            "case_assessments",
            "case_assessment_sources",
            "case_assessment_members",
        ]:
            await fetch(table, "case_id=ANY(CAST(:cases AS uuid[]))")
        params["subjects"] = params["alerts"] + params["incidents"] + params["cases"]
        await fetch("analysis_tasks", "subject_id=ANY(CAST(:subjects AS uuid[]))")
        params["tasks"] = [UUID(r["id"]) for r in rows["analysis_tasks"]]
        await fetch("analysis_attempts", "task_id=ANY(CAST(:tasks AS uuid[]))")
        assert all(
            r["state"] in {"completed", "failed", "skipped"}
            for r in rows["analysis_tasks"]
        )
        await fetch(
            "runs",
            "alert_id=ANY(CAST(:alerts AS uuid[])) OR incident_id=ANY(CAST(:incidents AS uuid[])) OR case_id=ANY(CAST(:cases AS uuid[]))",
        )
        params["runs"] = [UUID(r["id"]) for r in rows["runs"]]
        for table in ["run_steps", "run_members"]:
            await fetch(table, "run_id=ANY(CAST(:runs AS uuid[]))")
        await fetch("results", "source_run_id=ANY(CAST(:runs AS uuid[]))")
        params["results"] = [UUID(r["id"]) for r in rows["results"]]
        await fetch("result_members", "result_id=ANY(CAST(:results AS uuid[]))")
        await fetch(
            "artifacts",
            "alert_id=ANY(CAST(:alerts AS uuid[])) OR incident_id=ANY(CAST(:incidents AS uuid[])) OR case_id=ANY(CAST(:cases AS uuid[])) OR run_id=ANY(CAST(:runs AS uuid[]))",
        )
        await fetch(
            "analysis_subject_state",
            "subject_id=ANY(CAST(:subjects AS uuid[]))",
            "subject_type,subject_id",
        )
        await conn.rollback()
    await engine.dispose()
    # Avoid exporting credentials or hidden reasoning if a new raw shape appears.
    sensitive = []

    def walk(value, path="$"):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {
                    "api_key",
                    "authorization",
                    "password",
                    "secret_key",
                    "reasoning_content",
                    "thinking_content",
                } and item not in (None, "", [], {}):
                    sensitive.append(path + "." + key)
                walk(item, path + "." + key)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, path + "[" + str(i) + "]")

    walk(rows)
    assert not sensitive, "export_sensitive_paths:" + ",".join(sensitive)
    print(
        json.dumps(
            {
                "source": "real_postgres_readonly_snapshot",
                "batch_id": CFG["batch_id"],
                "identity": who,
                "counts": {k: len(v) for k, v in rows.items()},
                "rows": rows,
                "export_sensitive_paths": sensitive,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


asyncio.run(main())
