"""One existing normal flow in the explicitly configured local test database.

All model and lake calls are substitutes. Existing rows are never reset.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument("--database-config", type=Path, required=True)
parser.add_argument("--environment-file", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
cfg = json.loads(args.database_config.read_text())
assert cfg["host"] == "127.0.0.1" and cfg["processing_database"] == "v12_upgrade_dev"
os.environ.update(json.loads(args.environment_file.read_text()))
sys.path[:0] = [str(ROOT / p) for p in (".", "services/api", "services/api/tests", "docs/operations")]

from capture_processing_case import TABLES, check_credentials, scoped_table_query
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine
from test_socai2_case_boundary_pg import T, run_checks

args.output.mkdir(parents=True, exist_ok=False)
checks = []


def save(name, value):
    body = json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
    check_credentials(body.encode())
    (args.output / name).write_text(body)
    return hashlib.sha256(body.encode()).hexdigest()


def record(name, passed, detail=None):
    checks.append({"name": name, "passed": passed, "detail": detail})
    save("checks.json", checks)
    print(name, passed, flush=True)


async def main():
    url = URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"],
        port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, connect_args={"sslmode": "disable", "options": "-c role=" + cfg["processor"]})
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("select current_database(),current_user"))).one() == (
                cfg["processing_database"], cfg["processor"])
        await run_checks(engine, record, only={"test_case_boundary_followups_final_storage"})
        fixture = next(c["detail"] for c in checks if c["name"] == "fixture_registered")
        data = {}
        async with engine.connect() as connection, connection.begin():
            await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            await connection.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": str(T)})
            now = (await connection.execute(text("SELECT transaction_timestamp()"))).scalar_one()
            params = {"tenant": T, "aids": fixture["alert_ids"], "incident": [fixture["incident_id"]],
                      "cid": fixture["case_id"], "stages": fixture["stage_run_ids"]}
            scope = ("WITH scope AS (SELECT CAST(:tenant AS uuid) tenant, CAST(:aids AS uuid[]) aids, "
                     "CAST(:incident AS uuid[]) incident, CAST(:cid AS uuid) cid, CAST(:stages AS uuid[]) stages) ")
            for table in TABLES:
                data[table] = (await connection.execute(text(scope + scoped_table_query(table)), params)).scalar_one()
        checksum = save("database.json", data)
        save("manifest.json", {"schema_version": "socai2.page-export.v1",
            "batch_id": "model-input-selection-20261112-07-" + args.output.name,
            "exported_at": now, "source_environment": "isolated_local_pg_models_and_tools_substituted",
            "database": cfg["processing_database"], "tenant_id": T, "case_id": fixture["case_id"],
            "input_kind": "synthetic", "real_model_calls": 0, "database_snapshot": "single_readonly_repeatable_read",
            "sources": [{"file": "database.json", "sha256": checksum}],
            "table_counts": {k: len(v) for k, v in data.items()}})
        assert all(c["passed"] for c in checks), "See retained checks and snapshot; do not reuse this batch."
    finally:
        await engine.dispose()


asyncio.run(main())
