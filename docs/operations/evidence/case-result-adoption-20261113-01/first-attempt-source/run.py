"""Run one local core-adoption path and retain SQL/readback evidence."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
BATCH = Path(__file__).parent
parser = argparse.ArgumentParser()
parser.add_argument("--database-config", type=Path, required=True)
parser.add_argument("--environment-file", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
cfg, plan = json.loads(args.database_config.read_text()), json.loads((BATCH / "config.json").read_text())
assert (cfg["host"], cfg["port"], cfg["processing_database"], cfg["processor"]) == (
    plan["host"], plan["port"], plan["database"], plan["role"])
os.environ.update(json.loads(args.environment_file.read_text()))
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / plan["policy"])
sys.path[:0] = [str(ROOT / p) for p in (".", "services/api", "services/api/tests", "docs/operations")]

from app.socai2.baseline_contracts import Actor
from app.socai2.human_task_service import HumanTaskService
from capture_processing_case import TABLES, check_credentials, scoped_table_query
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_socai2_case_adoption_pg import exercise

args.output.mkdir(parents=True, exist_ok=False)
records = {}


def json_value(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else str(value)


def save(name, value):
    body = json.dumps(value, ensure_ascii=False, indent=2, default=json_value) + "\n"
    check_credentials(body.encode())
    (args.output / (name + ".json")).write_text(body)
    return hashlib.sha256(body.encode()).hexdigest()


def record(name, value):
    records[name] = value
    save(name, value)
    print(name, flush=True)


async def snapshot(engine, tenant):
    fixture = records.get("fixture")
    if not fixture:
        return
    async with engine.connect() as connection, connection.begin():
        await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        await connection.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": str(tenant)})
        now = (await connection.execute(text("SELECT transaction_timestamp()"))).scalar_one()
        params = {"tenant": tenant, "aids": fixture["alert_ids"], "incident": [], "cid": fixture["case_id"], "stages": []}
        scope = ("WITH scope AS (SELECT CAST(:tenant AS uuid) tenant, CAST(:aids AS uuid[]) aids, "
                 "CAST(:incident AS uuid[]) incident, CAST(:cid AS uuid) cid, CAST(:stages AS uuid[]) stages) ")
        data = {}
        for table in TABLES:
            data[table] = (await connection.execute(text(scope + scoped_table_query(table)), params)).scalar_one()
    checksum = save("database", data)
    save("manifest", {"schema_version": "socai2.page-export.v1", "batch_id": BATCH.name + "-" + args.output.name,
        "exported_at": now, "source_environment": "isolated_local_pg_program_supplied_results_no_model_execution",
        "database": plan["database"], "tenant_id": tenant, "case_id": fixture["case_id"],
        "input_kind": "synthetic", "real_model_calls": 0, "database_snapshot": "single_readonly_repeatable_read",
        "sources": [{"file": "database.json", "sha256": checksum}],
        "table_counts": {key: len(value) for key, value in data.items()}})


async def main():
    source_files = [Path(__file__), BATCH / "config.json", ROOT / plan["policy"],
        ROOT / "services/api/tests/test_socai2_case_adoption_pg.py"]
    source_files += [ROOT / "services/api/app/socai2" / name for name in (
        "case_adoption.py", "case_adoption_contracts.py", "case_service.py", "baseline_store.py",
        "case_reader.py", "case_query_snapshot.py", "human_task_service.py")]
    save("source-sha256", {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files})
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, connect_args={"sslmode": plan["sslmode"], "options": "-c role=" + cfg["processor"]})
    tenant, passed = UUID(plan["tenant_id"]), False
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("select current_database(),current_user"))).one() == (
                plan["database"], plan["role"])
        service = HumanTaskService(async_sessionmaker(engine, expire_on_commit=False))
        await exercise(service, tenant, Actor(user_id=UUID(plan["actor_id"]), name=plan["actor_name"]), record)
        passed = True
    except Exception:
        save("failure", {"traceback": traceback.format_exc()})
        raise
    finally:
        try:
            await snapshot(engine, tenant)
            save("verification", {"passed": passed, "single_direct_path": True, "real_model_calls": 0,
                "model_quality": "NOT_TESTED", "public_http": "NOT_CHANGED", "records": list(records)})
        finally:
            await engine.dispose()


asyncio.run(main())
