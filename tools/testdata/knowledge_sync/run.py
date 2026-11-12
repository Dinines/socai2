"""One new synthetic A publication -> real history sync -> readback, with no analysis model."""
import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_human_http.run import seed
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


def initialize(path):
    config = read(path)
    os.environ.update(read(ROOT / config["environment_file"]))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    os.environ["SOCAI2_KNOWLEDGE_PROFILE"] = str(ROOT / config["knowledge_profile"])
    sys.path.insert(0, str(ROOT / "services/api"))
    return config, ROOT / config["output"]


def prepare(config, path, folder):
    snapshot = read(ROOT / config["snapshot"])
    alert = next(a for a in snapshot["alerts"] if a["id"] == config["source_alert_id"])
    material = next(m for m in snapshot["alert_materials"] if m["id"] == alert["latest_material_id"])
    member = {"source_alert_id": alert["id"], "alert_id": identity(config["batch"], alert["id"]),
        "material_id": identity(config["batch"], material["id"]),
        "alert": {k: alert[k] for k in ("title", "description", "event_time", "event_time_source", "severity", "original_vendor")},
        "material": {k: material[k] for k in ("raw_json", "raw_text", "ocsf_json", "detection", "enrichment", "source_scope", "retention", "material_state")},
        "objects": [{k: obj[k] for k in ("object_type", "object_role", "object_key", "namespace", "raw_value", "normalized_value", "source_path", "attributes")}
                    for obj in snapshot["alert_objects"] if obj["alert_id"] == alert["id"]]}
    output = {"verdict": "needs_review", "rationale": "同步接线验证用模板判断；记录进程启动，业务合理性尚未核实。",
        "confidence": None, "score_state": "not_computed", "explanation": "明确的合成存储输入；没有执行分析模型，不代表独立真值。",
        "generation_method": "template", "recommendations": [], "limitations": config["limitations"],
        "source_refs": [{"type": "alert_material", "id": member["material_id"], "external": None,
            "source_path": "$.ocsf_json.process.name", "row_keys": [], "role": "observation"}]}
    paths = [path, Path(__file__), ROOT / config["snapshot"], ROOT / config["policy"], ROOT / config["knowledge_profile"]]
    paths += sorted((ROOT / "services/api/app/socai2").glob("*.py"))
    save(folder / "plan.json", {"batch": config["batch"], "config": config, "members": [member],
        "cases": [{"key": "A01", "title": "新分诊保存后同步历史知识（合成判断，无分析模型）", "alert_ids": [member["alert_id"]]}],
        "output": output, "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in paths}})
    print(json.dumps({"state": "prepared", "alerts": 1, "analysis_model_calls": 0}), flush=True)


async def execute(config, folder):
    from app.db import database
    from app.models import socai2 as m
    from app.socai2.baseline_contracts import Limits
    from app.socai2.knowledge_config import load, selectors
    from app.socai2.knowledge_source import query
    from app.socai2.knowledge_sync import VERSION
    from app.socai2.stage_result_contracts import AlertOutput
    from app.socai2.stage_results import StageResultService
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    plan = read(folder / "plan.json")
    assert plan["config"] == config
    assert all(sha(ROOT / p) == digest for p, digest in plan["source_sha256"].items()), "prepared_source_changed"
    save(folder / "execute-intent.json", {"attempts": 1, "analysis_model_calls": 0})
    await seed(config, plan)
    engine = await connect(config)
    service, tenant = StageResultService(async_sessionmaker(engine, expire_on_commit=False)), UUID(config["tenant_id"])
    member = plan["members"][0]
    aid = UUID(member["alert_id"])
    try:
        claim = await service.begin(tenant, "alert_basic", aid, UUID(identity(config["batch"], "triage")),
            producer="knowledge-sync-validation-fixture.v1", limits=Limits(max_model_calls=0, max_tokens=0,
                max_tool_calls=0, max_rows_per_query=0, deadline_at=None, policy_version="synthetic.storage-only"))
        save(folder / "claim.json", claim)
        judgment = AlertOutput.model_validate(plan["output"])
        outcome = await service.finish(tenant, claim["run_id"], judgment, alert_delivery_state="complete")
        save(folder / "publication.json", outcome)
        replay = await service.finish(tenant, claim["run_id"], judgment, alert_delivery_state="complete")
        assert replay == outcome and outcome["adopted"]
        async with service.transaction(tenant, readonly=True) as store:
            data = {}
            for table in m.Socai2Base.metadata.sorted_tables:
                if table.schema != "socai2":
                    continue
                data[table.name] = []
                predicate = table.c.id == aid if table.name == "alerts" else table.c.alert_id == aid if "alert_id" in table.c else None
                if predicate is not None:
                    data[table.name] = [dict(row) for row in (await store.db.execute(select(table).where(
                        table.c.tenant_id == tenant, predicate))).mappings()]
            connection = dict((await store.db.execute(text("SELECT current_database() AS database,current_user AS role"))).mappings().one())
        data = json.loads(json.dumps(data, default=str))
        receipts = [a for a in data["artifacts"] if a["schema_version"] == VERSION]
        assert len(receipts) == 2
        result = next(a["content_json"] for a in receipts if a["content_json"]["phase"] == "result")
        save(folder / "sync-result.json", result)
        assert result["state"] == "completed" and result["source_current"] is True
        assert data["runs"][0]["state"] == "completed"
        assert data["alert_assessments"][0]["rationale"] == judgment.rationale
        assert data["alerts"][0]["latest_triage_id"] == outcome["result_id"]
        assert result["triage_id"] == outcome["result_id"]
        save(folder / "readback/A01/database.json", data)

        # A read-only historical query using the original recorded C02 material.
        # No additional Case/Run or forged tool receipt is created.
        profile, fingerprint = load()
        context = SimpleNamespace(alerts={member["source_alert_id"]: SimpleNamespace(alert={
            **member["alert"], "source_namespace": config["batch"]})},
            scope=SimpleNamespace(window_start=config["query_window_start"]))
        keys = [k for k in selectors(context, {member["source_alert_id"]: member["material"]}, profile)
                if k["purpose"] == "historical_case_reference"]
        assert len(keys) == 1
        keys[0]["profile_sha256"] = fingerprint
        save(folder / "query-input.json", keys)
        rows, queried_at, metadata = await query(service, tenant, {"parameters": {"selectors": keys}})
        save(folder / "query.json", {"rows": rows, "queried_at": queried_at, "metadata": metadata})
        assert [r["record_id"] for r in rows] == [result["document_id"]]
        assert rows[0]["record"]["history"]["source_version_state"] == "current"
        gets = await read_http(config, folder, claim, aid, result, receipts)
        save(folder / "summary.json", {"state": "completed", "connection": connection,
            "alert_id": str(aid), "run_id": str(claim["run_id"]), "result_id": outcome["result_id"],
            "document_id": result["document_id"], "publication_replay_unchanged": replay == outcome,
            "sync_artifacts": len(receipts), "http_gets": gets, "query_rows": len(rows), "analysis_model_calls": 0,
            "synthetic_judgment": True, "model_quality": "NOT_EVALUATED", "profile_sha256": fingerprint,
            "completed_at": datetime.now(UTC).isoformat()})
        print(json.dumps({"state": "completed", "query_rows": len(rows), "http_gets": gets, "analysis_model_calls": 0}), flush=True)
    finally:
        await engine.dispose()
        await database.engine.dispose()


async def read_http(config, folder, claim, aid, result, receipts):
    from app.api.v1.deps import CurrentUser, get_current_user
    from app.api.v1.endpoints import knowledge_base, socai2_pages
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    app = FastAPI()
    for router in (knowledge_base.router, socai2_pages.router):
        app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id=UUID(config["actor_id"]),
        tenant_id=UUID(config["tenant_id"]), role="admin", email=config["actor_name"],
        scopes=["alerts:read", "knowledge_base:read"])
    base = f"/api/v1/socai2/alerts/{aid}/analysis/runs/{claim['run_id']}"
    paths = {"trace": base + "/trace", "card": "/api/v1/kb/alert-experiences/" + result["document_id"],
        "publication": base + "/artifacts/" + str(uuid5(claim["run_id"], "publication"))}
    paths.update({a["content_json"]["phase"]: base + "/artifacts/" + a["id"] for a in receipts})
    async with AsyncClient(transport=ASGITransport(app=app), base_url=config["http_base_url"],
            timeout=config["http_timeout_seconds"]) as client:
        for name, path in paths.items():
            response = await client.get(path)
            save(folder / "http" / (name + ".json"), {"path": path, "status": response.status_code, "body": response.json()})
            assert response.is_success, f"{name}:HTTP{response.status_code}"
    return len(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config, folder = initialize(args.config)
    if args.phase == "prepare":
        prepare(config, args.config.resolve(), folder)
    else:
        asyncio.run(execute(config, folder))
