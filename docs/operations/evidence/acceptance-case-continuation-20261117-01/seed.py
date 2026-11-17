"""Copy original business rows into the new empty database, retaining failed tasks."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from support import TABLES, engine, environment, same, save, snapshot


async def main(config):
    from sqlalchemy import text
    out = Path(__file__).parent
    source = json.loads(Path(config["source_snapshot_file"]).read_text())
    tenant, actor = UUID(config["tenant_id"]), UUID(config["actor_id"])
    db_engine = engine(config, admin=True)
    try:
        async with db_engine.begin() as db:
            assert (await db.execute(text("SELECT count(*) FROM socai2.cases"))).scalar_one() == 0
            assert (await db.execute(text("SELECT count(*) FROM public.tenants"))).scalar_one() == 0
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": str(tenant)})
            await db.execute(text("INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at) "
                "VALUES(:id,'Operations','operations','enterprise',true,'{}','{}',now(),now())"), {"id": tenant})
            await db.execute(text("INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at) "
                "VALUES(:id,:tenant,'analyst@example.invalid','Operations analyst','!','soc_analyst',true,false,'{}',now(),now())"),
                {"id": actor, "tenant": tenant})
            for alert in source["alerts"]:
                await db.execute(text("INSERT INTO public.connectors(id,tenant_id,name,connector_type,category,is_enabled,auth_config,connector_config,health_status,"
                    "events_ingested,events_dropped,error_count,oauth_provisioned,oauth_refresh_failures,tags,created_at,updated_at) "
                    "VALUES(:id,:tenant,:name,:name,'telemetry',true,'{}','{}','unknown',0,0,0,false,0,'[]',now(),now()) ON CONFLICT DO NOTHING"),
                    {"id": UUID(alert["connector_id"]), "tenant": tenant, "name": alert["connector_type"]})
            await db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            order = ("alerts", "alert_materials", "alert_objects", "alert_source_refs", "incidents", "incident_alerts",
                "cases", "case_alerts", "case_incidents", "case_alert_exclusions", "artifacts", "runs", "run_steps",
                "run_members", "alert_assessments", "incident_diagnoses", "analysis_tasks", "analysis_attempts",
                "analysis_subject_state", "activities", "activity_targets")
            with_attempts = {a["task_id"] for a in source["analysis_attempts"]}
            for table in order:
                assert table in TABLES
                for original in source[table]:
                    row = dict(original)
                    # Honor the INSERT attempt guard inside this single import transaction;
                    # restore all original task fields before committing, no trigger bypass.
                    if table == "analysis_tasks" and row["id"] in with_attempts:
                        row.update(state="running", ended_at=None, next_retry_at=None)
                    await db.execute(text(f"INSERT INTO socai2.{table} SELECT * FROM "
                        f"jsonb_populate_record(NULL::socai2.{table},CAST(:row AS jsonb))"), {"row": json.dumps(row)})
                if table == "analysis_attempts":
                    for row in source["analysis_tasks"]:
                        if row["id"] in with_attempts:
                            await db.execute(text("UPDATE socai2.analysis_tasks SET state=:state,ended_at=CAST(:ended AS timestamptz),"
                                "next_retry_at=CAST(:retry AS timestamptz) WHERE tenant_id=:tenant AND id=:id"),
                                {"state": row["state"], "ended": row["ended_at"], "retry": row["next_retry_at"],
                                 "tenant": tenant, "id": UUID(row["id"])})
            await db.execute(text("INSERT INTO socai2.incidents(id,tenant_id,source_namespace,source_incident_id,title) "
                "VALUES(:id,:tenant,'telemetry-channel-03',:source,'Independent service observation')"),
                {"id": UUID(config["control_incident_id"]), "tenant": tenant, "source": config["control_incident_id"]})
        actual, hashes = await snapshot(db_engine, str(tenant))
        for table, expected in source.items():
            observed = [r for r in actual[table] if table != "incidents" or r["id"] != config["control_incident_id"]]
            assert same(expected, observed), table
        save(out / "seed-snapshot.json", actual)
        save(out / "seed-validation.json", {"status": "passed", "counts_hashes": hashes,
            "original_row_values_preserved": True, "retained_failed_task_ids": [t["id"] for t in source["analysis_tasks"] if t["state"] == "failed"],
            "control_incident_id": config["control_incident_id"], "business_uuid_remapping": False,
            "public_identity_seeds": "same referenced IDs; neutral names, no source credentials", "kafka_sends": 0, "new_model_calls": 0})
        print("Saved dependencies imported and read back unchanged; original failed task retained, two incidents coexist.")
    finally:
        await db_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    environment(cfg)
    asyncio.run(main(cfg))
