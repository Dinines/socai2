"""Read only the admitted single-part subjects from the existing 21 service."""
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main(config):
    profile = json.loads(Path(config["dispatcher_profile"]).read_text())
    assert profile["tenant_id"] == config["tenant_id"]
    engine = create_async_engine(Path(profile["database_url_file"]).read_text().strip(),
        connect_args=profile["database_connect_args"], hide_parameters=True)
    try:
        async with engine.connect() as db, db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"),
                             {"tenant": config["tenant_id"]})
            actual = (await db.execute(text("SELECT current_database() AS database, current_user AS role, "
                "current_setting('transaction_read_only') AS readonly, now() AS captured_at"))).mappings().one()
            assert actual["database"] == config["expected_database"] and actual["role"] == config["expected_role"]
            assert actual["readonly"] == "on"

            async def rows(table, column, ids):
                if not ids:
                    return []
                # table/column names only originate from the fixed list below.
                return (await db.execute(text(f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') "
                    f"FROM socai2.{table} t WHERE tenant_id=:tenant AND {column}=ANY(CAST(:ids AS uuid[]))"),
                    {"tenant": UUID(config["tenant_id"]), "ids": [UUID(x) for x in ids]})).scalar_one()

            aids, cids = config["alert_ids"], config["case_ids"]
            values = {"alerts": await rows("alerts", "id", aids)}
            for name in ("alert_materials", "alert_objects", "alert_source_refs", "alert_assessments", "incident_alerts"):
                values[name] = await rows(name, "alert_id", aids)
            iids = sorted({x["incident_id"] for x in values["incident_alerts"]})
            values["incidents"] = await rows("incidents", "id", iids)
            values["incident_alerts"] = await rows("incident_alerts", "incident_id", iids)
            values["incident_diagnoses"] = await rows("incident_diagnoses", "incident_id", iids)
            values["cases"] = await rows("cases", "id", cids)
            for name in ("case_alerts", "case_incidents", "case_alert_exclusions", "results", "case_assessments"):
                values[name] = await rows(name, "case_id", cids)
            subjects = aids + iids + cids
            for name in ("analysis_tasks", "analysis_attempts", "analysis_subject_state"):
                values[name] = await rows(name, "subject_id", subjects)
            rids = sorted({x["run_id"] for x in values["analysis_attempts"] if x["run_id"]})
            values["runs"] = await rows("runs", "id", rids)
            for name in ("run_steps", "run_members", "artifacts"):
                values[name] = await rows(name, "run_id", rids)
            assert not values["results"] and not values["case_assessments"]
            values["activities"] = await rows("activities", "subject_case_id", cids)
            values["activity_targets"] = await rows("activity_targets", "activity_id", [r["id"] for r in values["activities"]])
            assert {x["alert_id"] for x in values["incident_alerts"]} == set(aids)
            assert all(x["state"] in {"completed", "failed", "skipped"} for x in values["analysis_tasks"])
            return {"source": dict(actual), "rows": values}
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main(json.load(sys.stdin))), ensure_ascii=False, default=str))
