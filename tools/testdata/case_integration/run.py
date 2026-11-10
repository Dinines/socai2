"""Local PG boundary checks and scoped readback. Never dispatch a real model."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


async def export(engine, config, output, sample, index):
    from app.socai2.case_data import export_page_data
    from app.socai2.case_service import CaseService
    from flow_export import TABLES, query_for
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    folder = output / f"case-{index}"
    data = {}
    async with engine.begin() as conn:
        await conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        await conn.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": config["tenant_id"]})
        params = {"p1": config["tenant_id"], "p2": list(map(str, sample["alert_ids"])),
            "p3": str(sample["incident_id"]), "p4": str(sample["case_id"]),
            "p5": list(map(str, sample["stage_run_ids"]))}
        for table in TABLES:
            sql = query_for(table)
            for n in range(1, 6):
                sql = sql.replace(f"${n}::uuid[]", f"CAST(:p{n} AS uuid[])").replace(f"${n}::uuid", f"CAST(:p{n} AS uuid)")
            data[table] = (await conn.execute(text(sql), params)).scalar_one()
    pages = await export_page_data(data)
    from uuid import UUID
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    cid, rid, tenant = sample["case_id"], sample["run_id"], UUID(config["tenant_id"])
    # Same service methods as authenticated original GET handlers.
    from app.socai2.baseline_store import StoreError
    reads = {}
    for name, method, arguments in (("case", service.read_case, (tenant, cid)),
            ("run", service.read_run, (tenant, cid, rid)), ("history", service.read_history, (tenant, cid))):
        try:
            reads[name] = await method(*arguments)
        except StoreError as exc:
            reads[name] = {"read_error": exc.code, "status": exc.status}
    reads = {k: v.model_dump(mode="json") if hasattr(v, "model_dump") else v for k, v in reads.items()}
    assert all(row["description"] == "Original collected description." for row in data["alerts"])
    assert all(row["raw_json"]["custom"] == {"id": "business-id", "authorized": False, "size": 0}
               for row in data["alert_materials"])
    sources = []
    for name, value in (("database.json", data), ("case-page-data.json", pages), ("service-reads.json", reads)):
        path = folder / name
        save(path, value)
        sources.append({"file": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    save(folder / "manifest.json", {"schema_version": "socai2.page-export.v1",
        "batch_id": config["batch"] + "-" + output.name + f"-{index}", "exported_at": datetime.now(UTC).isoformat(),
        "source_environment": "isolated_local_pg_models_and_tools_substituted", "database": config["expected_database"],
        "tenant_id": config["tenant_id"], "case_id": str(cid), "input_kind": "synthetic", "sources": sources,
        "table_counts": {k: len(v) for k, v in data.items()}, "real_model_calls": 0})
    return {"case_id": str(cid), "run_id": str(rid), "folder": str(folder.relative_to(ROOT)),
        "service_reads": sum(not isinstance(v, dict) or "read_error" not in v for v in reads.values()),
        "read_errors": {k: v for k, v in reads.items() if isinstance(v, dict) and "read_error" in v},
        "original_materials_unchanged": True,
        "states": {r["id"]: r["state"] for r in data["runs"]}}


async def main(config, output, only):
    from sqlalchemy import text
    from test_socai2_case_boundary_pg import run_checks

    from tools.testdata.incident_integration.run import connect

    records, fixtures = [], []
    def record(name, passed, detail):
        if name == "fixture_registered":
            fixtures.append(detail)
            save(output / "fixtures.json", fixtures)
        else:
            records.append({"name": name, "passed": passed, "detail": detail})
            save(output / "checks.json", records)
            print(json.dumps({"name": name, "passed": passed}), flush=True)
    engine = await connect(config)
    try:
        async with engine.connect() as conn:
            catalog = (await conn.execute(text("SELECT table_name,column_name,data_type,is_nullable,column_default "
                "FROM information_schema.columns WHERE table_schema='socai2' ORDER BY table_name,ordinal_position"))).all()
            save(output / "schema-before.json", [list(r) for r in catalog])
        await run_checks(engine, record, only=only)
        exports = []
        for index, sample in enumerate(fixtures, 1):
            exports.append(await export(engine, config, output, sample, index))
        async with engine.connect() as conn:
            after = (await conn.execute(text("SELECT table_name,column_name,data_type,is_nullable,column_default "
                "FROM information_schema.columns WHERE table_schema='socai2' ORDER BY table_name,ordinal_position"))).all()
        assert catalog == after
        save(output / "summary.json", {"checks": records, "exports": exports, "real_model_calls": 0,
            "schema_unchanged": True, "tables": len({r[0] for r in catalog}), "columns": len(catalog),
            "scope": config.get("scope", "Local synthetic C1/C2/C3 integration, not full Case quality acceptance")})
    finally:
        await engine.dispose()
    return 0 if records and all(r["passed"] for r in records) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    assert cfg["real_model_calls"] == 0 and cfg["deployment"] is False
    assert Path(args.attempt).name == args.attempt
    os.environ.update(json.loads((ROOT / cfg["environment_file"]).read_text()))
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / cfg["policy"])
    sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests"), str(ROOT / "deploy/local-investigation"), str(ROOT)]
    folder = ROOT / cfg["output"] / args.attempt
    folder.mkdir(parents=True, exist_ok=False)
    raise SystemExit(asyncio.run(main(cfg, folder, args.only)))
