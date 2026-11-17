"""One existing observed-finding correction and storage path, isolated PostgreSQL only."""
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
plan = json.loads(Path(__file__).with_name("config.json").read_text())
assert cfg["host"] == plan["database_host"] and cfg["processing_database"] == plan["database"]
os.environ.update(json.loads(args.environment_file.read_text()))
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / plan["policy"])
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
    paths = [ROOT / plan["policy"], Path(__file__), Path(__file__).with_name("config.json")]
    paths += [ROOT / "services/api/tests" / name for name in (
        "test_socai2_case_boundary_pg.py", "test_socai2_case_followup_pg.py")]
    paths += [ROOT / "services/api/app/socai2" / name for name in (
        "case-input-v1.json", "case_context_input.py", "case_model_boundary.py", "case_input_text.py",
        "case_c3_input_selection.py", "case_followup_input.py", "baseline_delivery_projection.py",
        "case_program_output.py", "case_citation_feedback.py", "case_followup_output.py", "runtime_policy.py")]
    save("source-sha256.json", {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    url = URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"],
        port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, connect_args={"sslmode": plan["database_sslmode"],
        "options": "-c role=" + cfg["processor"]})
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("select current_database(),current_user"))).one() == (
                cfg["processing_database"], cfg["processor"])
        await run_checks(engine, record, only={plan["scenario"]})
        fixture = next(c["detail"] for c in reversed(checks) if c["name"] == "fixture_registered")
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
            "batch_id": Path(__file__).parent.name + "-" + args.output.name,
            "exported_at": now, "source_environment": "isolated_local_pg_models_and_tools_substituted",
            "database": cfg["processing_database"], "tenant_id": T, "case_id": fixture["case_id"],
            "input_kind": "synthetic", "real_model_calls": 0, "database_snapshot": "single_readonly_repeatable_read",
            "sources": [{"file": "database.json", "sha256": checksum}],
            "table_counts": {k: len(v) for k, v in data.items()}})
        assert all(c["passed"] for c in checks), "See retained checks and snapshot; do not reuse this batch."
    finally:
        await engine.dispose()


asyncio.run(main())
