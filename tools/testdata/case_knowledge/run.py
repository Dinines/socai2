"""One real local KB import/index -> C2/C3/remaining Case -> saved readback."""
import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_human_http.run import seed
from tools.testdata.case_scope_recovery.real_model import (
    Gateway,
    initialize,
    plan_for,
    prepare,
)
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


def application(config):
    from app.api.v1.deps import CurrentUser, get_current_user
    from app.api.v1.endpoints import knowledge_base, socai2_cases
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(knowledge_base.router, prefix="/api/v1")
    app.include_router(socai2_cases.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=UUID(config["actor_id"]), tenant_id=UUID(config["tenant_id"]), role="admin",
        email=config["actor_name"], scopes=["settings:write", "knowledge_base:read", "cases:read", "cases:write"])
    return app


async def execute(config, folder):
    from app.db import database
    from app.db.case_database import close_case_database
    from app.socai2 import baseline_executor
    from httpx import ASGITransport, AsyncClient

    from tools.testdata.case_io_eval.model_eval import remote
    plan = plan_for(config, folder)
    preflight = await asyncio.to_thread(remote, config, {"phase": "preflight", "timeout_seconds": config["preflight_timeout_seconds"]})
    save(folder / "model-preflight.json", preflight)
    assert preflight["state"] == "ready"
    save(folder / "execute-intent.json", {"attempts": 1, "plan_sha256": sha(folder / "plan.json")})
    gateway = Gateway({**config, "preflight": preflight}, folder / "calls")
    original = baseline_executor.TenantChatGateway
    baseline_executor.TenantChatGateway = lambda: gateway
    requests, outcome = [], {"state": "not_completed"}
    try:
        await seed(config, plan)
        async with AsyncClient(transport=ASGITransport(app=application(config)),
                               base_url=config["http_base_url"], timeout=config["http_timeout_seconds"]) as client:
            async def request(label, method, path, body=None):
                response = await client.request(method, path, json=body)
                receipt = {"label": label, "method": method, "path": path, "request": body,
                           "status": response.status_code, "body": response.json()}
                save(folder / "http" / f"{len(requests)+1:02d}-{label}.json", receipt)
                requests.append(receipt)
                print(json.dumps({"label": label, "status": response.status_code}), flush=True)
                assert response.is_success, label + ":HTTP" + str(response.status_code)
                return receipt["body"]

            imported = []
            for i, doc in enumerate(read(ROOT / config["corpus"])):
                rows = await request(f"ingest-{i+1}", "POST", "/api/v1/kb/ingest", doc["request"])
                imported.extend(r["id"] for r in rows)
            await request("index", "POST", "/api/v1/kb/index", {"document_ids": imported})
            created = await request("create", "POST", "/api/v1/socai2/cases", {
                "operation_key": plan["operation_key"], "title": config["title"],
                "description": "\n".join(config["limitations"]), "alert_ids": [m["alert_id"] for m in plan["members"]]})
            save(folder / "created.json", created)
            base = "/api/v1/socai2/cases/" + created["case_id"]
            times = [datetime.fromisoformat(m["alert"]["event_time"]) for m in plan["members"]]
            pad = timedelta(seconds=config["window_padding_seconds"])
            rid = created["pending_run_id"]
            await request("start", "POST", base + f"/runs/{rid}/start", {
                "expected_scope_revision": created["scope_revision"], "operation_key": identity(config["batch"], "start"),
                "window_start": (min(times)-pad).isoformat(), "window_end": (max(times)+pad).isoformat()})
            run = await request("run", "GET", base + f"/runs/{rid}")
            for result_id in run["result_ids"]:
                await request("result-" + result_id, "GET", base + "/results/" + result_id)
            await request("case-final", "GET", base)
            assert run["run"]["state"] == "completed" and run["result_ids"]
            outcome = {"state": "completed", "case_id": created["case_id"], "run_id": rid, "document_ids": imported}
    except Exception as exc:  # noqa: BLE001 -- keep private connections out of public evidence
        outcome = {"state": "execution_exception", "error_type": type(exc).__name__, "code": getattr(exc, "code", None)}
        print(json.dumps(outcome), flush=True)
    finally:
        baseline_executor.TenantChatGateway = original
        save(folder / "api-responses.json", requests)
        save(folder / "execution.json", {**outcome, "model_calls": gateway.calls, "unknown": gateway.unknown})
        await close_case_database()
        await database.engine.dispose()
    return outcome["state"] == "completed"


async def export(config, folder):
    from app.socai2.case_data import export_page_data
    from flow_export import TABLES, query_for
    from sqlalchemy import text
    plan = plan_for(config, folder)
    created, execution = read(folder / "created.json"), read(folder / "execution.json")
    engine = await connect(config)
    try:
        data = {}
        async with engine.begin() as conn:
            await conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await conn.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": config["tenant_id"]})
            params = {"p1": config["tenant_id"], "p2": [m["alert_id"] for m in plan["members"]],
                      "p3": None, "p4": created["case_id"], "p5": []}
            for table in TABLES:
                sql = query_for(table)
                for i in range(1, 6):
                    sql = sql.replace(f"${i}::uuid[]", f"CAST(:p{i} AS uuid[])").replace(f"${i}::uuid", f"CAST(:p{i} AS uuid)")
                data[table] = (await conn.execute(text(sql), params)).scalar_one()
        output = folder / "export"
        save(output / "database.json", data)
        save(output / "case-page-data.json", await export_page_data(data))
        observations = read(folder / "api-responses.json")
        save(output / "api-responses.json", observations)
        save(output / "manifest.json", {"schema_version": "socai2.page-export.v1", "batch_id": config["batch"],
            "exported_at": datetime.now(UTC).isoformat(), "source_environment": "local_pg_qdrant_real_embedding_and_model",
            "database": config["expected_database"], "tenant_id": config["tenant_id"], "case_id": created["case_id"],
            "sources": [{"file": name, "sha256": sha(output / name)} for name in
                        ("database.json", "case-page-data.json", "api-responses.json")],
            "table_counts": {key: len(value) for key, value in data.items()}, "limitations": config["limitations"]})
        receipts = [r for r in data["artifacts"] if r["kind"] == "tool_response" and r["content_json"].get("tool_name") == "knowledge"]
        assert receipts and receipts[0]["content_json"]["state"] == "completed" and receipts[0]["content_json"]["rows"]
        knowledge = receipts[0]
        model_inputs = [r for r in data["artifacts"] if r["kind"] == "model_request"]
        inputs = []
        for r in model_inputs:
            payload = r["content_json"]["payload"]
            sources = {sid: s for sid, s in payload["source_map"].items() if s["ref"]["id"] == knowledge["id"]
                       and (s["ref"]["source_path"] or "").startswith("$.rows.")}
            inputs.append({"request_id": r["id"], "step_id": r["step_id"], "knowledge_sources": sources})
        assert any(r["knowledge_sources"] for r in inputs), "knowledge_not_model_visible"
        fields = ("conclusion", "conclusion_state", "validation_state", "findings", "questions", "recommendations")
        for observation in observations:
            if observation["label"].startswith("result-"):
                result = observation["body"]["result"]
                row = next(r for r in data["results"] if r["id"] == result["id"])
                assert all(result[k] == row[k] for k in fields)
        for member in plan["members"]:
            material = next(r for r in data["alert_materials"] if r["id"] == member["material_id"])
            assert all(material[k] == v for k, v in member["material"].items())
        save(output / "verification.json", {**execution, "knowledge_artifact_id": knowledge["id"],
            "rows": knowledge["content_json"]["returned_rows"], "model_inputs": inputs,
            "http_requests": len(observations), "result_fields_match": list(fields), "original_materials_unchanged": True,
            "model_quality": "NOT_PASSED; inspect actual use separately; known M01 remains deferred"})
        print(json.dumps({"export": str(output), "knowledge_rows": knowledge["content_json"]["returned_rows"],
                          "model_requests": len(model_inputs)}), flush=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "run", "export"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    path = args.config.resolve()
    cfg, output = initialize(path)
    if args.phase == "prepare":
        prepare(cfg, path, output)
        sources = [Path(__file__), ROOT / cfg["corpus"], ROOT / cfg["knowledge_profile"],
                   ROOT / "services/api/app/api/v1/endpoints/knowledge_base.py"]
        save(output / "knowledge-source-sha256.json", {str(p.relative_to(ROOT)): sha(p) for p in sources})
    elif args.phase == "run":
        assert all(sha(ROOT / p) == v for p, v in read(output / "knowledge-source-sha256.json").items())
        sys.exit(0 if asyncio.run(execute(cfg, output)) else 1)
    else:
        asyncio.run(export(cfg, output))
