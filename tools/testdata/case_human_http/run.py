"""One local HTTP Case -> Run -> revised H -> next Run, using real DB/model.

Only authentication and internal model transport are adapted. Route dependencies,
Case/H services, executor, storage and GET responses are the application originals.
"""
import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import (
    Gateway,
    initialize,
    plan_for,
    prepare,
)
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


async def seed(config, plan):
    from app.models import socai2 as m
    from app.socai2.case_service import CaseService
    from sqlalchemy import insert, update
    from sqlalchemy.ext.asyncio import async_sessionmaker
    engine = await connect(config)
    try:
        service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
        async with service.transaction(UUID(config["tenant_id"])) as store:
            for member in plan["members"]:
                aid, mid = UUID(member["alert_id"]), UUID(member["material_id"])
                alert = dict(member["alert"])
                if alert["event_time"]:
                    alert["event_time"] = datetime.fromisoformat(alert["event_time"])
                await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=store.tenant_id,
                    source_namespace=config["batch"], source_identity_key=str(aid), **alert))
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=store.tenant_id,
                    alert_id=aid, revision=1, **member["material"]))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                for index, obj in enumerate(member["objects"]):
                    await store.db.execute(insert(m.AlertObjects).values(
                        id=UUID(identity(config["batch"], f"{aid}:object:{index}")), tenant_id=store.tenant_id,
                        alert_id=aid, material_id=mid, **obj))
    finally:
        await engine.dispose()


def http_app(config):
    from app.api.v1.deps import CurrentUser, get_current_user
    from app.api.v1.endpoints import socai2_cases, socai2_tasks
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(socai2_cases.router, prefix="/api/v1")
    app.include_router(socai2_tasks.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=UUID(config["actor_id"]), tenant_id=UUID(config["tenant_id"]), role="analyst",
        email=config["actor_name"], scopes=["cases:read", "cases:write"])
    return app


async def execute(config, folder):
    from app.db import database
    from app.db.case_database import close_case_database, get_case_write_sessions
    from app.socai2 import baseline_executor
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text

    from tools.testdata.case_io_eval.model_eval import check_route, remote
    plan = plan_for(config, folder)
    hashes = read(folder / "http-source-sha256.json")
    assert all(sha(ROOT / name) == value for name, value in hashes.items()), "http_source_changed"
    assert not (folder / "execute-intent.json").exists(), "batch_already_attempted"
    preflight = await asyncio.to_thread(remote, config, {"phase": "preflight",
        "timeout_seconds": config["preflight_timeout_seconds"]})
    save(folder / "preflight.json", preflight)
    check_route(config, preflight)
    connections = {}
    for name, sessions in (("reader", database.AsyncSessionLocal), ("writer", get_case_write_sessions())):
        async with sessions() as session:
            row = (await session.execute(text("SELECT current_database(), current_user"))).one()
            connections[name] = {"database": row[0], "role": row[1]}
    db = read(ROOT / config["database_profile"])
    assert connections == {k: {"database": config["expected_database"], "role": db[v]}
                           for k, v in (("reader", "reader"), ("writer", "processor"))}
    save(folder / "connections.json", connections)
    save(folder / "execute-intent.json", {"plan_sha256": sha(folder / "plan.json"), "attempts": 1})
    gateways = []

    def gateway_factory():
        index = len(gateways) + 1
        transport = {**config["transport"], "remote_evidence_dir": config["remote_evidence_dir"] + f"/round-{index}"}
        value = Gateway({**config, "transport": transport, "preflight": preflight}, folder / f"round-{index}/calls")
        gateways.append(value)
        return value

    original_gateway = baseline_executor.TenantChatGateway
    baseline_executor.TenantChatGateway = gateway_factory
    requests = []
    outcome = {"state": "not_completed"}
    try:
        await seed(config, plan)
        async with AsyncClient(transport=ASGITransport(app=http_app(config)),
                               base_url=config["http_base_url"], timeout=config["http_timeout_seconds"]) as client:
            async def request(label, method, path, body=None):
                response = await client.request(method, path, json=body)
                receipt = {"label": label, "method": method, "path": path, "request": body,
                           "status": response.status_code, "body": response.json()}
                save(folder / "http" / f"{len(requests)+1:02d}-{label}.json", receipt)
                requests.append(receipt)
                print(json.dumps({"label": label, "status": response.status_code}), flush=True)
                assert response.is_success, f"{label}:HTTP{response.status_code}"
                return receipt["body"]

            created = await request("create", "POST", "/api/v1/socai2/cases", {
                "operation_key": plan["operation_key"], "title": config["title"],
                "description": "\n".join(config["limitations"]), "alert_ids": [m["alert_id"] for m in plan["members"]]})
            save(folder / "created.json", created)
            base = "/api/v1/socai2/cases/" + created["case_id"]
            times = [datetime.fromisoformat(m["alert"]["event_time"]) for m in plan["members"]]
            pad = timedelta(seconds=config["window_padding_seconds"])
            start = {"expected_scope_revision": created["scope_revision"],
                     "window_start": (min(times)-pad).isoformat(), "window_end": (max(times)+pad).isoformat()}

            async def run_round(index, rid):
                await request(f"start-{index}", "POST", base + f"/runs/{rid}/start", {
                    **start, "operation_key": identity(config["batch"], f"start-{index}")})
                run = await request(f"run-{index}", "GET", base + f"/runs/{rid}")
                assert run["run"]["state"] == "completed" and run["result_ids"], "no_saved_delivery"
                for result_id in run["result_ids"]:
                    await request(f"result-{index}-{result_id}", "GET", base + f"/results/{result_id}")
                return run

            first = await run_round(1, created["pending_run_id"])
            scope = {"kind": "whole_case", "alert_ids": [m["alert_id"] for m in plan["members"]],
                     "object_keys": [], "window_start": start["window_start"], "window_end": start["window_end"],
                     "limitations": ["材料完整性核查，不是业务授权或安全结论。"]}
            fields = {"title": config["human_title"], "expected_scope_revision": created["scope_revision"],
                      "state": "completed", "result_scope": scope,
                      "source_refs": [{"type": "alert_material", "id": m["material_id"]} for m in plan["members"]]}
            initial = await request("human-create", "POST", base + "/tasks", {**fields,
                "operation_key": identity(config["batch"], "human-create"), "result_text": config["human_initial"]})
            task = initial["task"]
            revised = await request("human-revise", "PUT", base + "/tasks/" + task["id"], {**fields,
                "operation_key": identity(config["batch"], "human-revise"), "expected_row_version": task["row_version"],
                "result_text": config["human_revised"]})
            await request("human-current", "GET", base + "/tasks/" + task["id"])
            await request("human-revisions", "GET", base + "/tasks/" + task["id"] + "/revisions")
            pending = await request("prepare-next", "POST", base + "/baseline/prepare", {
                "operation_key": identity(config["batch"], "prepare-next"),
                "expected_scope_revision": created["scope_revision"]})
            second = await run_round(2, pending["pending_run_id"])
            await request("case-final", "GET", base)
            outcome = {"state": "completed", "first_run_id": first["run"]["id"],
                "second_run_id": second["run"]["id"], "task_id": task["id"],
                "initial_revision_id": task["current_revision_id"],
                "selected_revision_id": revised["task"]["current_revision_id"]}
    except Exception as exc:  # noqa: BLE001 -- private URLs must not enter evidence
        outcome = {"state": "execution_exception", "error_type": type(exc).__name__, "code": getattr(exc, "code", None)}
    finally:
        baseline_executor.TenantChatGateway = original_gateway
        save(folder / "api-responses.json", requests)
        save(folder / "execution.json", {**outcome, "rounds": [
            {"model_calls": g.calls, "unknown": g.unknown} for g in gateways]})
        await close_case_database()
        await database.engine.dispose()
    print(json.dumps(outcome), flush=True)
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
            "exported_at": datetime.now(UTC).isoformat(), "source_environment": "local_http_real_pg_real_model_auth_transport_adapters",
            "database": config["expected_database"], "tenant_id": config["tenant_id"], "case_id": created["case_id"],
            "sources": [{"file": name, "sha256": sha(output / name)} for name in
                        ("database.json", "case-page-data.json", "api-responses.json")],
            "table_counts": {key: len(value) for key, value in data.items()}, "limitations": config["limitations"]})
        assert execution["state"] == "completed", "http_chain_incomplete_snapshot_saved"
        selected = execution["selected_revision_id"]
        revision = next(r for r in data["task_revisions"] if r["id"] == selected)
        assert revision["result_text"] == config["human_revised"] and revision["revision"] == 2
        prior = next(r for r in data["task_revisions"] if r["id"] == execution["initial_revision_id"])
        assert prior["result_text"] == config["human_initial"] and prior["revision"] == 1
        first = next(r for r in data["runs"] if r["id"] == execution["first_run_id"])
        second = next(r for r in data["runs"] if r["id"] == execution["second_run_id"])
        artifacts = {r["id"]: r for r in data["artifacts"]}
        frozen = artifacts[second["input_artifact_id"]]["content_json"]
        assert frozen["task_revisions"] == [selected]
        assert artifacts[first["input_artifact_id"]]["content_json"]["task_revisions"] == []
        assert any(r["id"] == selected and r["role"] == "human_statement" for r in frozen["source_materials"])
        model_inputs = [r for r in data["artifacts"] if r["run_id"] == second["id"] and r["kind"] == "model_request"]
        assert model_inputs and all(config["human_revised"] in json.dumps(r["content_json"], ensure_ascii=False) for r in model_inputs)
        fields = ("conclusion", "conclusion_state", "validation_state", "findings", "questions", "recommendations")
        for observation in observations:
            if observation["label"].startswith("result-"):
                result = observation["body"]["result"]
                row = next(r for r in data["results"] if r["id"] == result["id"])
                assert all(result[k] == row[k] for k in fields), "result_readback_differs"
        for member in plan["members"]:
            material = next(r for r in data["alert_materials"] if r["id"] == member["material_id"])
            assert all(material[k] == v for k, v in member["material"].items()), "original_material_changed"
        summary = {**execution, "case_id": created["case_id"], "http_requests": len(observations),
            "saved_revision_matches": True, "prior_revision_preserved": True, "frozen_selected_revision_matches": True,
            "human_statement_role": True, "feedback_in_next_model_requests": len(model_inputs),
            "result_fields_match": list(fields), "original_materials_unchanged": True,
            "runs": [{k: r[k] for k in ("id", "state", "delivery_state")} for r in data["runs"]],
            "model_quality": "NOT_PASSED; existing M01 issues remain deferred; no repeat sampling"}
        save(output / "verification.json", summary)
        print(json.dumps(summary), flush=True)
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
        sources = [Path(__file__), ROOT / "services/api/app/db/case_database.py",
                   ROOT / "services/api/app/db/database.py", ROOT / "services/api/app/core/config.py"]
        sources += [ROOT / f"services/api/app/api/v1/endpoints/{name}.py" for name in ("socai2_cases", "socai2_tasks")]
        save(output / "http-source-sha256.json", {str(p.relative_to(ROOT)): sha(p) for p in sources})
    elif args.phase == "run":
        sys.exit(0 if asyncio.run(execute(cfg, output)) else 1)
    else:
        asyncio.run(export(cfg, output))
