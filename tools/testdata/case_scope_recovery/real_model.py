"""One isolated Case, original materials, real gateway and normal C1-C6 executor."""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


def initialize(path):
    config = read(path)
    os.environ.update(read(ROOT / config["environment_file"]))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "deploy/local-investigation")]
    config["transport"] = {**read(ROOT / config["transport_config"])["transport"],
                           "remote_evidence_dir": config["remote_evidence_dir"]}
    return config, ROOT / config["output"]


def prepare(config, path, folder):
    from app.socai2.runtime_policy import active_policy
    policy = active_policy()
    snapshot = read(ROOT / config["snapshot"])
    samples = []
    for row in snapshot["alerts"]:
        material = next(m for m in snapshot["alert_materials"] if m["id"] == row["latest_material_id"])
        samples.append({"source_alert_id": row["id"], "alert_id": identity(config["batch"], row["id"]),
            "material_id": identity(config["batch"], material["id"]),
            "alert": {k: row[k] for k in ("title", "description", "event_time", "event_time_source", "severity", "original_vendor")},
            "material": {k: material[k] for k in ("raw_json", "raw_text", "ocsf_json", "detection", "enrichment", "source_scope", "retention", "material_state")},
            "objects": [{k: obj[k] for k in ("object_type", "object_role", "object_key", "namespace", "raw_value", "normalized_value", "source_path", "attributes")}
                        for obj in snapshot["alert_objects"] if obj["alert_id"] == row["id"]]})
    files = [path, ROOT / config["snapshot"], ROOT / config["policy"], Path(__file__)]
    files += [p for p in (ROOT / "services/api/app/socai2").glob("*") if p.suffix in {".py", ".json"}]
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / "plan.json", {"config": config, "members": samples,
        "operation_key": identity(config["batch"], "create"), "max_model_calls": policy.case.max_model_calls,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files}})
    print(json.dumps({"state": "prepared", "members": len(samples), "max_model_calls": policy.case.max_model_calls}), flush=True)


def plan_for(config, folder):
    plan = read(folder / "plan.json")
    assert plan["config"] == config
    assert all(sha(ROOT / p) == value for p, value in plan["source_sha256"].items()), "prepared_source_changed"
    return plan


class Gateway:
    def __init__(self, config, folder):
        from app.socai2.runtime_policy import active_policy
        from app.socai2.token_budget import BackendTokenMeter

        from tools.testdata.incident_integration.gateway import TokenizerTransport
        self.config, self.folder, self.calls, self.unknown = config, folder, 0, False
        policy = active_policy().model
        self.provider, self.model, self.schema_profile = policy.protocol, policy.alias, policy.schema_profile
        self.meter = BackendTokenMeter(policy, transport=TokenizerTransport(config, folder))

    async def configure(self, *_):
        return self.config["preflight"]["state"] == "ready" and not self.unknown

    async def measure(self, body, stage):
        return await self.meter.measure(body, stage)

    async def complete(self, body, timeout):
        import httpx
        from app.socai2.model_errors import ModelCallError, provider_error
        from app.socai2.runtime_policy import active_policy

        from tools.testdata.case_io_eval.model_eval import remote
        assert not self.unknown and timeout > 0 and self.calls < active_policy().case.max_model_calls
        self.calls += 1
        key = f"call-{self.calls}"
        save(self.folder / f"{key}-intent.json", {"body": body, "attempt": 1})
        print(key + " dispatch", flush=True)
        value = await asyncio.to_thread(remote, self.config, {"phase": "call", "cell": key, "body": body,
            "timeout_seconds": min(timeout, active_policy().single_model_timeout_seconds)})
        save(self.folder / f"{key}-receipt.json", value)
        print(json.dumps({"call": self.calls, "state": value["state"], "usage": value.get("raw", {}).get("usage")}), flush=True)
        if value["state"] != "response_received":
            self.unknown = "unknown" in value["state"]
            if value.get("error_body") and value.get("http_status"):
                response = httpx.Response(value["http_status"], content=value["error_body"], request=httpx.Request("POST", "https://gateway.invalid"))
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ModelCallError(provider_error(exc, "")) from None
            raise ModelCallError({"http_status": value.get("http_status"), "fields": {}, "body_state": "unavailable", "exception_type": "RemoteTransportUncertain"})
        return value["raw"]


async def execute(config, folder):
    from app.models import socai2 as m
    from app.socai2.baseline_contracts import Actor, Start
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.runtime_policy import active_policy
    from sqlalchemy import insert, update
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tools.testdata.case_io_eval.model_eval import check_route, remote
    plan = plan_for(config, folder)
    preflight = await asyncio.to_thread(remote, config, {"phase": "preflight", "timeout_seconds": config["preflight_timeout_seconds"]})
    save(folder / "preflight.json", preflight)
    check_route(config, preflight)
    save(folder / "execute-intent.json", {"plan_sha256": sha(folder / "plan.json"), "retries": 0})
    engine = await connect(config)
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    tenant = UUID(config["tenant_id"])
    actor = Actor(user_id=UUID(config["actor_id"]), name=config["actor_name"])
    gateway = Gateway({**config, "preflight": preflight}, folder / "calls")
    try:
        async with service.transaction(tenant) as store:
            for member in plan["members"]:
                aid, mid = UUID(member["alert_id"]), UUID(member["material_id"])
                alert = dict(member["alert"])
                if alert["event_time"]:
                    alert["event_time"] = datetime.fromisoformat(alert["event_time"])
                await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant,
                    source_namespace=config["batch"], source_identity_key=str(aid), **alert))
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1, **member["material"]))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                for index, obj in enumerate(member["objects"]):
                    await store.db.execute(insert(m.AlertObjects).values(id=UUID(identity(config["batch"], f"{aid}:object:{index}")),
                        tenant_id=tenant, alert_id=aid, material_id=mid, **obj))
        created = await service.create_case(tenant, CaseCreate(operation_key=UUID(plan["operation_key"]), title=config["title"],
            alert_ids=[UUID(m["alert_id"]) for m in plan["members"]], description="\n".join(config["limitations"])), actor=actor)
        save(folder / "created.json", created.model_dump(mode="json"))
        async with service.transaction(tenant, readonly=True) as store:
            now = await store.now()
        limits = active_policy().case.limits(now, "case-scope-recovery.local-real.v1")
        times = [datetime.fromisoformat(m["alert"]["event_time"]) for m in plan["members"] if m["alert"]["event_time"]]
        pad = timedelta(seconds=config["window_padding_seconds"])
        try:
            outcome = await service.start_full(tenant, created.case_id, created.pending_run_id, Start(
                expected_scope_revision=created.scope_revision, operation_key=UUID(identity(config["batch"], "start")),
                window_start=min(times)-pad, window_end=max(times)+pad), actor=actor, limits=limits, gateway=gateway)
            outcome = outcome.model_dump(mode="json") if hasattr(outcome, "model_dump") else outcome
        except Exception as exc:  # noqa: BLE001 -- avoid logging private driver details
            outcome = {"state": "execution_exception", "error_type": type(exc).__name__, "code": getattr(exc, "code", None)}
        save(folder / "execution.json", {"outcome": outcome, "model_calls": gateway.calls, "unknown": gateway.unknown})
        print(json.dumps({"outcome": outcome, "model_calls": gateway.calls}, default=str), flush=True)
    finally:
        await engine.dispose()


async def export(config, folder):
    from app.api.v1.endpoints import socai2_cases as api
    from app.socai2.case_data import export_page_data
    from app.socai2.case_service import CaseService
    from fastapi import FastAPI
    from flow_export import TABLES, query_for
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker
    plan = plan_for(config, folder)
    created = read(folder / "created.json")
    engine = await connect(config)
    cid, rid = created["case_id"], created["pending_run_id"]
    try:
        data = {}
        async with engine.begin() as conn:
            await conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await conn.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": config["tenant_id"]})
            params = {"p1": config["tenant_id"], "p2": [m["alert_id"] for m in plan["members"]], "p3": None, "p4": cid, "p5": []}
            for table in TABLES:
                sql = query_for(table)
                for i in range(1, 6):
                    sql = sql.replace(f"${i}::uuid[]", f"CAST(:p{i} AS uuid[])").replace(f"${i}::uuid", f"CAST(:p{i} AS uuid)")
                data[table] = (await conn.execute(text(sql), params)).scalar_one()
        for member in plan["members"]:
            alert = next(a for a in data["alerts"] if a["id"] == member["alert_id"])
            material = next(m for m in data["alert_materials"] if m["id"] == member["material_id"])
            assert all(material[k] == v for k, v in member["material"].items()), "original_material_changed"
            assert alert["description"] == member["alert"]["description"] and alert["latest_triage_id"] is None
        save(folder / "export/database.json", data)
        save(folder / "export/page-data.json", await export_page_data(data))
        service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
        app = FastAPI()
        app.include_router(api.router)
        app.dependency_overrides[api.ReadUser.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=UUID(config["tenant_id"]))
        app.dependency_overrides[api.get_service] = lambda: service
        paths = [f"/socai2/cases/{cid}", f"/socai2/cases/{cid}/history", f"/socai2/cases/{cid}/page-data", f"/socai2/cases/{cid}/runs/{rid}"]
        paths += [f"/socai2/cases/{cid}/results/{row['id']}" for row in data["results"]]
        paths += [f"/socai2/cases/{cid}/runs/{rid}/artifacts/{row['id']}" for row in data["artifacts"] if row["run_id"] == rid]
        observations = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://local.validation") as client:
            for path in paths:
                response = await client.get(path)
                observations.append({"path": path, "status": response.status_code, "body": response.json()})
        save(folder / "export/api-responses.json", observations)
        summary = {"case_id": cid, "run_id": rid, "table_counts": {k: len(v) for k, v in data.items()},
            "original_materials_unchanged": True, "real_model_calls": read(folder / "execution.json")["model_calls"],
            "http_reads": len(observations), "http_errors": [v["path"] for v in observations if v["status"] != 200],
            "state": data["runs"][0]["state"], "delivery_state": data["runs"][0]["delivery_state"],
            "current_assessment_id": data["cases"][0]["current_assessment_id"], "limitations": config["limitations"]}
        save(folder / "export/manifest.json", summary)
        print(json.dumps(summary), flush=True)
        assert not summary["http_errors"]
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "run", "export"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    cfg, output = initialize(config_path)
    if args.phase == "prepare":
        prepare(cfg, config_path, output)
    else:
        asyncio.run((execute if args.phase == "run" else export)(cfg, output))
