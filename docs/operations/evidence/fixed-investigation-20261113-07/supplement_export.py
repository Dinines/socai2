"""Read the historical A/I Runs referenced by the scoped snapshot for 4177."""
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "docs/operations")]
from capture_processing_case import TABLES, check_credentials, scoped_table_query
from sqlalchemy import text

from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import connect, read, save, sha


async def main():
    config, folder = initialize(HERE / "config.json")
    plan = read(folder / "plan.json")
    original = folder / config["scenario"] / "export"
    output = original.parent / "workbench-export"
    old = read(original / "database.json")
    referenced = {row["source_run_id"] for name in ("incident_diagnoses", "alert_assessments")
                  for row in old[name] if row.get("source_run_id")}
    missing = referenced - {r["id"] for r in old["runs"]}
    assert missing, "no_missing_historical_source_runs"
    engine = await connect(config)
    try:
        async with engine.connect() as db, db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": config["tenant_id"]})
            scope = ("WITH scope AS (SELECT CAST(:tenant AS uuid) tenant, CAST(:aids AS uuid[]) aids, "
                     "CAST(:incident AS uuid[]) incident, CAST(:cid AS uuid) cid, CAST(:stages AS uuid[]) stages) ")
            params = {"tenant": config["tenant_id"], "aids": [m["alert_id"] for m in plan["members"]],
                "incident": [plan["incident_id"]], "cid": config["case_id"],
                "stages": sorted(set(plan["prior_stage_run_ids"]) | referenced)}
            data = {table: (await db.execute(text(scope + scoped_table_query(table)), params)).scalar_one()
                    for table in TABLES}
        check_credentials(json.dumps(data, default=str).encode())
        for table in ("cases", "results", "task_revisions", "case_assessments", "incident_diagnoses"):
            assert {r["id"]: r for r in data[table]} == {r["id"]: r for r in old[table]}, table
        assert referenced <= {r["id"] for r in data["runs"]}
        output.mkdir(exist_ok=False)
        save(output / "database.json", data)
        manifest = read(original / "manifest.json")
        manifest.update(exported_at=datetime.now(UTC), sources=[{"file": "database.json", "sha256": sha(output / "database.json")}],
            table_counts={k: len(v) for k, v in data.items()})
        save(output / "manifest.json", manifest)
        save(HERE / "snapshot-supplement.json", {"reason": "initial scoped export omitted historical I source Runs",
            "missing_source_run_ids": sorted(missing), "original_snapshot_sha256": sha(original / "database.json"),
            "new_snapshot_sha256": sha(output / "database.json"), "business_results_and_H_unchanged": True,
            "model_calls": 0, "database_writes": 0, "original_snapshot_preserved": True})
        print("Read-only 4177 snapshot includes", len(missing), "previously omitted historical Runs.")
    finally:
        await engine.dispose()


asyncio.run(main())
