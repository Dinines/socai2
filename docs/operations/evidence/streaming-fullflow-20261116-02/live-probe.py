"""Read only the new batch through ordinary PG and lake accounts."""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.socai2.analysis_dispatch_runtime import load_profile
from app.socai2.stage_results import StageResultService
from clickhouse_driver import Client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

p = json.loads(sys.stdin.read())
phase = sys.argv[1]


async def main():
    config = load_profile(p["dispatcher_profile"])
    assert config["tenant_id"] == p["tenant_id"]
    engine = create_async_engine(
        Path(config["database_url_file"]).read_text().strip(),
        connect_args=config["database_connect_args"],
        hide_parameters=True,
    )
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    out = {"batch_id": p["batch_id"], "phase": phase}
    params = {"alerts": [UUID(x) for x in p["alert_ids"]]}
    try:
        async with service.transaction(UUID(p["tenant_id"]), readonly=True) as store:

            async def fetch(table, clause, keys=None):
                rows = list(
                    (
                        await store.db.execute(
                            text(
                                "SELECT row_to_json(t) FROM socai2."
                                + table
                                + " t WHERE "
                                + clause
                                + " ORDER BY id"
                            ),
                            params,
                        )
                    ).scalars()
                )
                return (
                    [{k: r[k] for k in keys if k in r} for r in rows] if keys else rows
                )

            out["alerts"] = await fetch(
                "alerts",
                "id=ANY(CAST(:alerts AS uuid[]))",
                ["id", "title", "latest_material_id", "latest_triage_id", "event_time"],
            )
            inc = list(
                (
                    await store.db.execute(
                        text(
                            "SELECT DISTINCT incident_id FROM socai2.incident_alerts WHERE alert_id=ANY(CAST(:alerts AS uuid[]))"
                        ),
                        params,
                    )
                ).scalars()
            )
            cases = list(
                (
                    await store.db.execute(
                        text(
                            "SELECT DISTINCT case_id FROM socai2.case_alerts WHERE alert_id=ANY(CAST(:alerts AS uuid[]))"
                        ),
                        params,
                    )
                ).scalars()
            )
            params.update(
                incidents=inc, cases=cases, subjects=params["alerts"] + inc + cases
            )
            out["incidents"] = await fetch(
                "incidents",
                "id=ANY(CAST(:incidents AS uuid[]))",
                ["id", "title", "latest_diagnosis_id", "active_case_id"],
            )
            out["cases"] = await fetch(
                "cases",
                "id=ANY(CAST(:cases AS uuid[]))",
                ["id", "title", "state", "scope_revision", "current_assessment_id"],
            )
            out["tasks"] = await fetch(
                "analysis_tasks",
                "subject_id=ANY(CAST(:subjects AS uuid[]))",
                [
                    "id",
                    "subject_type",
                    "subject_id",
                    "state",
                    "intent",
                    "source",
                    "reason_code",
                    "retry_count",
                    "next_retry_at",
                    "source_run_id",
                    "source_result_id",
                    "submitted_at",
                    "ended_at",
                ],
            )
            out["runs"] = await fetch(
                "runs",
                "alert_id=ANY(CAST(:alerts AS uuid[])) OR incident_id=ANY(CAST(:incidents AS uuid[])) OR case_id=ANY(CAST(:cases AS uuid[]))",
                [
                    "id",
                    "kind",
                    "state",
                    "alert_id",
                    "incident_id",
                    "case_id",
                    "started_at",
                    "ended_at",
                    "stop_reason",
                ],
            )
            out["results"] = await fetch(
                "results",
                "case_id=ANY(CAST(:cases AS uuid[]))",
                [
                    "id",
                    "case_id",
                    "source_run_id",
                    "validation_state",
                    "conclusion_state",
                    "delivery_state",
                    "created_at",
                ],
            )
            params["case_runs"] = [UUID(r["id"]) for r in out["runs"] if r["case_id"]]
            out["case_steps"] = await fetch(
                "run_steps",
                "run_id=ANY(CAST(:case_runs AS uuid[]))",
                [
                    "id",
                    "run_id",
                    "stage_code",
                    "seq",
                    "state",
                    "error",
                    "usage",
                    "started_at",
                    "ended_at",
                ],
            )
            out["global_running_tasks"] = await store.db.scalar(
                text("SELECT count(*) FROM socai2.analysis_tasks WHERE state='running'")
            )
            out["new_batch_alert_count"] = len(out["alerts"])
    finally:
        await engine.dispose()
    if phase == "preflight" or phase.endswith("context-readback"):
        lake = Client(
            host=os.environ["CLICKHOUSE_HOST"],
            port=int(os.environ["CLICKHOUSE_PORT"]),
            database=os.environ["CLICKHOUSE_DATABASE"],
            user=os.environ["CLICKHOUSE_USER"],
            password=os.environ["CLICKHOUSE_PASSWORD"],
            connect_timeout=p["timeouts"]["lake_connect_seconds"],
            send_receive_timeout=p["timeouts"]["lake_read_seconds"],
            settings={
                "readonly": 1,
                "max_execution_time": p["timeouts"]["lake_query_seconds"],
            },
        )
        try:
            ids = (
                p["event_ids"]
                if phase == "preflight"
                else [x["event_id"] for x in p["readback_events"]]
            )
            rows, columns = lake.execute(
                "SELECT *,toUnixTimestamp64Milli(event_time) AS event_time_ms FROM raw_events WHERE tenant_id=%(tenant)s AND event_id IN %(ids)s",
                {"tenant": p["tenant_id"], "ids": tuple(ids)},
                with_column_types=True,
            )
            saved = [dict(zip([c[0] for c in columns], r)) for r in rows]
            out["new_batch_context_count"] = len(saved)
            if phase == "preflight":
                assert (
                    not saved and not out["alerts"] and out["global_running_tasks"] == 0
                )
            else:
                by = {str(r["event_id"]): r for r in saved}
                assert set(by) == set(ids)
                for event in p["readback_events"]:
                    row = by[event["event_id"]]
                    ocsf = event["ocsf_event"]
                    stored = json.loads(row["ocsf_json"])
                    assert (
                        str(row["tenant_id"]) == p["tenant_id"]
                        and row["src_hostname"] == ocsf["device"]["name"]
                    )
                    assert row["class_uid"] == ocsf["class_uid"] and row[
                        "event_time_ms"
                    ] == round(datetime.fromisoformat(ocsf["time"]).timestamp() * 1000)
                    assert row["raw_payload"] == ocsf["raw_data"] and all(
                        stored.get(k) == v for k, v in ocsf.items()
                    )
                    assert (
                        not stored["_socai2_storage"]["raw_payload"]["truncated"]
                        and not stored["_socai2_storage"]["event_time_fallback"]
                    )
                out.update(
                    source="real_lake_readback", event_ids=sorted(by), lake_rows=saved
                )
        finally:
            lake.disconnect()
    out["status"] = "passed"
    print(json.dumps(out, ensure_ascii=False, default=str))


asyncio.run(main())
