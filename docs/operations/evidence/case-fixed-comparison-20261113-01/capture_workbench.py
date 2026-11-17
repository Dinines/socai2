"""Export only actual Case membership; the fixture's unlinked I stays in pg-01."""
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "docs/operations")]
from capture_processing_case import SCOPE, TABLES, check_credentials, scoped_table_query
from sqlalchemy import text

from tools.testdata.incident_integration.run import connect, read, save, sha


async def main():
    # Reuse the explicit connection configuration from the real 07 batch.
    config = read(HERE.parent / "fixed-investigation-20261113-07/config.json")
    old = read(HERE / "pg-01/database.json")
    manifest = read(HERE / "pg-01/manifest.json")
    output = HERE / "workbench-export"
    engine = await connect(config)
    try:
        async with engine.connect() as db, db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": config["tenant_id"]})
            sql = SCOPE.replace(":true", r"\:true").replace("$1", ":tenant").replace("$2", ":cid")
            scope = (await db.execute(text(sql),
                {"tenant": UUID(config["tenant_id"]), "cid": UUID(manifest["case_id"])})).mappings().one()
            params = {"tenant": config["tenant_id"], "aids": list(map(str, scope["alerts"])),
                "incident": list(map(str, scope["incidents"])), "stages": list(map(str, scope["stages"])),
                "cid": manifest["case_id"]}
            cte = ("WITH scope AS (SELECT CAST(:tenant AS uuid) tenant, CAST(:aids AS uuid[]) aids, "
                   "CAST(:incident AS uuid[]) incident, CAST(:cid AS uuid) cid, CAST(:stages AS uuid[]) stages) ")
            data = {table: (await db.execute(text(cte + scoped_table_query(table)), params)).scalar_one() for table in TABLES}
        check_credentials(json.dumps(data, default=str).encode())
        for table in ("cases", "results", "case_assessments"):
            assert {r["id"]: r for r in data[table]} == {r["id"]: r for r in old[table]}
        output.mkdir(exist_ok=False)
        save(output / "database.json", data)
        manifest.update(exported_at=scope["captured_at"], sources=[{"file": "database.json", "sha256": sha(output / "database.json")}],
            table_counts={k: len(v) for k, v in data.items()},
            limitations=["Case is linked by alerts; the fixture's independent I is not a Case incident."])
        save(output / "manifest.json", manifest)
        save(HERE / "snapshot-scope.json", {"scope": params, "original_snapshot_sha256": sha(HERE / "pg-01/database.json"),
            "new_snapshot_sha256": sha(output / "database.json"), "old_snapshot_retained": True,
            "Case_Result_current_assessment_unchanged": True, "model_calls": 0, "database_writes": 0})
        print("Captured actual Case membership; original complete fixture snapshot retained.")
    finally:
        await engine.dispose()


asyncio.run(main())
