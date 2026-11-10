"""Compare saved real-case GETs and a subsequent scoped read-only DB snapshot."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from real_model import ROOT, initialize

sys.path.insert(0, str(ROOT / "docs/operations"))


async def verify(config, folder):
    from flow_export import TABLES, query_for
    from sqlalchemy import text
    from verify_database_handoff import FK_SQL, audit

    from tools.testdata.incident_integration.run import connect, read, save

    before = read(folder / "export/database.json")
    case = before["cases"][0]["id"]
    engine = await connect(config)
    try:
        after = {}
        async with engine.begin() as conn:
            await conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await conn.execute(text("SELECT set_config('app.current_tenant_id',:t,true)"), {"t": config["tenant_id"]})
            keys = (await conn.execute(text(FK_SQL))).scalar_one()
            params = {"p1": config["tenant_id"], "p2": [r["id"] for r in before["alerts"]],
                      "p3": None, "p4": case, "p5": []}
            for table in TABLES:
                sql = query_for(table)
                for i in range(1, 6):
                    sql = sql.replace(f"${i}::uuid[]", f"CAST(:p{i} AS uuid[])").replace(f"${i}::uuid", f"CAST(:p{i} AS uuid)")
                after[table] = (await conn.execute(text(sql), params)).scalar_one()
        responses = read(folder / "export/api-responses.json")
        for response in responses:
            suffix = response["path"].split("/cases/", 1)[1].split("/")[1:]
            kind = "case" if not suffix else {"history": "history", "page-data": "page_data",
                "results": "result", "runs": "artifact" if len(suffix) > 2 else "run"}[suffix[0]]
            response.update(kind=kind, expected_status=200)
            if kind in {"result", "run", "artifact"}:
                response["id"] = suffix[-1]
        checks = audit(after, before, keys, responses)
        save(folder / "export/database-after-reads.json", after)
        save(folder / "export/field-checks.json", checks)
        summary = {"checks": len(checks), "passed": sum(c["passed"] for c in checks),
                   "failed": [c for c in checks if not c["passed"]], "http_reads": len(responses),
                   "database_unchanged": after == before, "case_id": case}
        save(folder / "export/field-summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        assert not summary["failed"] and summary["database_unchanged"]
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg, output = initialize(args.config.resolve())
    asyncio.run(verify(cfg, output))
