"""One explicit synthetic historical source -> real KB/C2/model/storage flow."""
import argparse
import asyncio
import copy
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_human_http.run import seed
from tools.testdata.case_knowledge.run import application, export
from tools.testdata.case_scope_recovery.real_model import (
    Gateway,
    initialize,
    plan_for,
    prepare,
)
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


async def seed_history(config, plan):
    from app.models import socai2 as m
    from app.socai2.baseline_store import digest, encoded
    from sqlalchemy import insert, text, update
    fixture = read(ROOT / config["history_fixture"])
    aid, mid = [identity(config["batch"], key) for key in ("history-alert", "history-material")]
    material = copy.deepcopy(plan["members"][0]["material"])
    material.update(raw_text=json.dumps(fixture["ocsf_json"], ensure_ascii=False), raw_json={"synthetic_fixture": True},
                    ocsf_json=fixture["ocsf_json"], enrichment={})
    material["source_scope"].update(received_count=1, retained_count=1)
    material["detection"].update(ocsf_class_uid=1007)
    raw = {k: material[k] for k in ("raw_text", "raw_json", "ocsf_json")}
    material["sha256"] = digest(raw)
    material["retention"].update(original_sha256=digest(raw), retained_sha256=digest(raw),
                                 original_size_bytes=len(encoded(raw)), retained_size_bytes=len(encoded(raw)))
    await seed(config, {"members": [{"alert_id": aid, "material_id": mid, "alert": fixture["alert"],
                                    "material": material, "objects": []}]})
    engine = await connect(config)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": config["tenant_id"]})
            for kind, key, pointer in (("triage", "triage", "latest_triage_id"), ("human_feedback", "feedback", "latest_feedback_id")):
                ident = UUID(identity(config["batch"], key))
                await conn.execute(insert(m.AlertAssessments).values(id=ident, tenant_id=UUID(config["tenant_id"]),
                    alert_id=UUID(aid), input_material_id=UUID(mid), kind=kind, **fixture[key],
                    actor={"type": "service", "service_name": "historical-knowledge-validation-fixture",
                           "service_version": "fixture.v1", "user_id": None, "name_snapshot": None},
                    producer="synthetic_fixture_not_actual_human_or_model", assessed_at=datetime(2026, 11, 1, 7, tzinfo=UTC),
                    operation_key=identity(config["batch"], "assessment:" + key)))
                await conn.execute(update(m.Alerts).where(m.Alerts.id == UUID(aid)).values(**{pointer: ident}))
        return aid
    finally:
        await engine.dispose()


async def knowledge(config, folder):
    from app.db import database
    from httpx import ASGITransport, AsyncClient
    plan = plan_for(config, folder)
    assert not (folder / "knowledge-intent.json").exists(), "inspect_completed_writes_before_retry"
    save(folder / "knowledge-intent.json", {"fixture": config["history_fixture"], "fixture_sha256": sha(ROOT / config["history_fixture"])})
    aid = await seed_history(config, plan)
    try:
        async with AsyncClient(transport=ASGITransport(app=application(config)), base_url=config["http_base_url"],
                               timeout=config["http_timeout_seconds"]) as client:
            receipts = []
            async def request(label, method, path, body=None):
                response = await client.request(method, path, json=body)
                data = response.json()
                receipts.append({"label": label, "method": method, "path": path, "request": body,
                                 "status": response.status_code, "body": data})
                save(folder / "knowledge-http" / f"{len(receipts):02d}-{label}.json", receipts[-1])
                print(json.dumps({"label": label, "status": response.status_code}), flush=True)
                assert response.is_success, label
                return data
            imported = await request("import", "POST", "/api/v1/kb/alert-experiences", {"alert_ids": [aid]})
            assert imported["cards"][0]["state"] == "stored", imported
            duplicate = await request("same-source", "POST", "/api/v1/kb/alert-experiences", {"alert_ids": [aid]})
            assert imported == duplicate
            ids = [r["document_id"] for r in imported["cards"]]
            await request("index", "POST", "/api/v1/kb/index", {"document_ids": ids})
            card = await request("card", "GET", "/api/v1/kb/alert-experiences/" + ids[0])
            fixture = read(ROOT / config["history_fixture"])
            assert all(card["card"][key]["rationale"] == fixture[key]["rationale"] for key in ("triage", "feedback"))
            assert card["card"]["source"]["alert_id"] == aid
            save(folder / "knowledge-http.json", receipts)
            save(folder / "knowledge-ready.json", {"historical_alert_id": aid, "document_ids": ids,
                                                  "original_text_verified": True, "actual_business_history": False})
    finally:
        await database.engine.dispose()


async def run(config, folder):
    from app.db import database
    from app.db.case_database import close_case_database
    from app.socai2 import baseline_executor
    from httpx import ASGITransport, AsyncClient

    from tools.testdata.case_io_eval.model_eval import check_route, remote
    plan = plan_for(config, folder)
    ready = read(folder / "knowledge-ready.json")
    assert not (folder / "execute-intent.json").exists(), "batch_already_attempted"
    preflight = await asyncio.to_thread(remote, config, {"phase": "preflight", "timeout_seconds": config["preflight_timeout_seconds"]})
    save(folder / "model-preflight.json", preflight)
    check_route(config, preflight)
    save(folder / "execute-intent.json", {"attempts": 1, "plan_sha256": sha(folder / "plan.json")})
    gateway = Gateway({**config, "preflight": preflight}, folder / "calls")
    original = baseline_executor.TenantChatGateway
    baseline_executor.TenantChatGateway = lambda: gateway
    requests, outcome = [], {"state": "not_completed"}
    try:
        await seed(config, plan)
        async with AsyncClient(transport=ASGITransport(app=application(config)), base_url=config["http_base_url"],
                               timeout=config["http_timeout_seconds"]) as client:
            async def request(label, method, path, body=None):
                response = await client.request(method, path, json=body)
                receipt = {"label": label, "method": method, "path": path, "request": body,
                           "status": response.status_code, "body": response.json()}
                save(folder / "http" / f"{len(requests)+1:02d}-{label}.json", receipt)
                requests.append(receipt)
                print(json.dumps({"label": label, "status": response.status_code}), flush=True)
                assert response.is_success, label
                return receipt["body"]
            created = await request("create", "POST", "/api/v1/socai2/cases", {"operation_key": plan["operation_key"],
                "title": config["title"], "description": "\n".join(config["limitations"]),
                "alert_ids": [m["alert_id"] for m in plan["members"]]})
            save(folder / "created.json", created)
            base, rid = "/api/v1/socai2/cases/" + created["case_id"], created["pending_run_id"]
            times = [datetime.fromisoformat(m["alert"]["event_time"]) for m in plan["members"]]
            pad = timedelta(seconds=config["window_padding_seconds"])
            await request("start", "POST", base + f"/runs/{rid}/start", {
                "expected_scope_revision": created["scope_revision"], "operation_key": identity(config["batch"], "start"),
                "window_start": (min(times)-pad).isoformat(), "window_end": (max(times)+pad).isoformat()})
            result = await request("run", "GET", base + f"/runs/{rid}")
            for ident in result["result_ids"]:
                await request("result-" + ident, "GET", base + "/results/" + ident)
            await request("case-final", "GET", base)
            assert result["run"]["state"] == "completed" and result["result_ids"]
            outcome = {"state": "completed", "case_id": created["case_id"], "run_id": rid, **ready}
    except Exception as exc:  # noqa: BLE001 -- public evidence omits private connections
        outcome = {"state": "execution_exception", "error_type": type(exc).__name__, "code": getattr(exc, "code", None)}
        print(json.dumps(outcome), flush=True)
    finally:
        baseline_executor.TenantChatGateway = original
        save(folder / "api-responses.json", requests)
        save(folder / "execution.json", {**outcome, "model_calls": gateway.calls, "unknown": gateway.unknown})
        await close_case_database()
        await database.engine.dispose()
    return outcome["state"] == "completed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "knowledge", "run", "export"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    path = args.config.resolve()
    config, folder = initialize(path)
    if args.phase == "prepare":
        prepare(config, path, folder)
        files = [Path(__file__), ROOT / config["history_fixture"], ROOT / config["knowledge_profile"],
                 ROOT / "services/api/app/api/v1/endpoints/knowledge_base.py"]
        save(folder / "knowledge-source-sha256.json", {str(p.relative_to(ROOT)): sha(p) for p in files})
    else:
        assert all(sha(ROOT / p) == value for p, value in read(folder / "knowledge-source-sha256.json").items())
        if args.phase == "knowledge":
            asyncio.run(knowledge(config, folder))
        elif args.phase == "run":
            sys.exit(0 if asyncio.run(run(config, folder)) else 1)
        else:
            asyncio.run(export(config, folder))
