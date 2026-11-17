"""One new fixed Run using unchanged H/AI, with knowledge forwarding held open."""
import argparse
import asyncio
import importlib.util
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import Gateway, initialize
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


def prior_driver(config):
    spec = importlib.util.spec_from_file_location("fixed08_export", ROOT / config["export_driver"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(config, folder):
    from app.socai2.runtime_policy import active_policy

    prior = read(ROOT / config["prior_plan"])
    db = read(ROOT / config["snapshot"])
    case = next(c for c in db["cases"] if c["id"] == config["case_id"])
    human = next(t for t in db["task_revisions"] if t["id"] == config["human_revision_id"])
    comparison = next(r for r in db["results"] if r["id"] == config["comparison_result_id"])
    assert human["state"] == "completed" and comparison["validation_state"] == "accepted" and comparison["conclusion"]
    files = [HERE / "config.json", HERE / "run.py", ROOT / config["export_driver"], ROOT / config["prior_plan"],
        ROOT / config["snapshot"], ROOT / config["policy"], ROOT / config["knowledge_profile"],
        ROOT / config["local_services"], ROOT / "tools/testdata/case_scope_recovery/real_model.py",
        ROOT / "tools/testdata/incident_integration/run.py", ROOT / "tools/testdata/incident_integration/gateway.py",
        ROOT / "tools/testdata/case_io_eval/model_eval.py", ROOT / "tools/testdata/case_io_eval/model_worker.py"]
    files.extend(p for p in (ROOT / "services/api/app/socai2").glob("*") if p.suffix in {".py", ".json"})
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / "plan.json", {"config": config, "members": prior["members"], "scope": prior["scope"],
        "incident_id": prior["incident_id"], "prior_stage_run_ids": prior["prior_stage_run_ids"],
        "expected_alert_pointers": prior["expected_alert_pointers"],
        "expected_incident_pointers": prior["expected_incident_pointers"], "case": case,
        "human_revision": human, "comparison_result": comparison,
        "old_run_ids": sorted(r["id"] for r in db["runs"] if r["case_id"] == config["case_id"]),
        "operations": {key: identity(config["batch"], key) for key in ("prepare", "start")},
        "max_model_calls": active_policy().case.max_model_calls,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "original_files_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
            (ROOT / config["original_flow"]).rglob("*") if p.is_file() and "__pycache__" not in p.parts},
        "checks": config["checks"], "new_runs": 1, "new_AI_runs": 0, "new_H_revisions": 0})
    print("Prepared one new Run; no network or database calls.", flush=True)


@contextmanager
def knowledge_forward(config, out):
    import httpx

    cfg = read(ROOT / config["local_services"])
    port = cfg["embedding_host_port"]
    profile = read(ROOT / config["knowledge_profile"])
    assert profile["embedding"]["url"] == f"http://127.0.0.1:{port}/api/embed"
    with socket.socket() as sock:
        assert sock.connect_ex(("127.0.0.1", port)) != 0, "unowned_listener_already_present"
    argv = ["ssh", "-N", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
        "-o", f"ConnectTimeout={config['ssh_connect_timeout_seconds']}",
        "-o", f"ServerAliveInterval={config['ssh_keepalive_seconds']}",
        "-L", f"127.0.0.1:{port}:{cfg['embedding_target']}", cfg["ssh_host"]]
    save(out / "transport-intent.json", {"argv": argv, "started_at": datetime.now(UTC),
        "scope": "owned_local_forward_held_through_new_fixed_run", "remote_restart": False})
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    receipt = {"pid": proc.pid, "ready": False}
    try:
        deadline = time.monotonic() + config["tunnel_ready_timeout_seconds"]
        while time.monotonic() < deadline:
            assert proc.poll() is None, "forward_exited"
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("forward_not_ready")
        url = profile["embedding"]["url"].rsplit("/", 1)[0] + "/version"
        version = httpx.get(url, timeout=config["preflight_timeout_seconds"])
        version.raise_for_status()
        receipt.update(ready=True, version=version.json(), http_status=version.status_code)
        yield
    finally:
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=config["ssh_connect_timeout_seconds"])
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate()
        save(out / "transport-result.json", {**receipt, "owned_forward_closed": True,
            "returncode": proc.returncode, "stderr": stderr, "finished_at": datetime.now(UTC)})


async def run(config, folder):
    from app.db import database
    from app.models import socai2 as m
    from app.socai2.baseline_contracts import Actor, Start
    from app.socai2.case_contracts import PrepareBaseline
    from app.socai2.case_service import CaseService
    from app.socai2.runtime_policy import active_policy
    from fastapi.encoders import jsonable_encoder
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tools.testdata.case_io_eval.model_eval import check_route, remote

    plan = prior_driver(config).plan_for(config, folder)
    out = folder / config["scenario"]
    assert not (out / "execute-intent.json").exists(), "recorded_run_not_redispatched"
    route = await asyncio.to_thread(remote, config, {"phase": "preflight",
        "timeout_seconds": config["preflight_timeout_seconds"]})
    save(out / "model-route.json", route)
    check_route(config, route)
    gateway = Gateway({**config, "preflight": route}, out / "calls")
    engine = await connect(config)
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    tenant, cid = UUID(config["tenant_id"]), UUID(config["case_id"])
    actor = Actor(user_id=UUID(config["actor_id"]), name=config["actor_name"])
    outcome, rid, phase = {}, None, "verify_unchanged_sources"
    try:
        async with service.transaction(tenant, readonly=True) as store:
            case = await store.one(select(m.Cases.__table__).where(m.Cases.id == cid, m.Cases.tenant_id == tenant))
            assert jsonable_encoder(case) == plan["case"], "case_changed_since_frozen_H01"
            current_runs = (await store.db.execute(select(m.Runs.id).where(m.Runs.case_id == cid,
                m.Runs.tenant_id == tenant))).scalars().all()
            assert sorted(map(str, current_runs)) == plan["old_run_ids"], "case_has_new_runs"
            for member in plan["members"]:
                alert = await store.one(select(m.Alerts.__table__).where(m.Alerts.id == UUID(member["alert_id"]),
                    m.Alerts.tenant_id == tenant))
                assert {k: str(alert[k]) if alert[k] else None for k in plan["expected_alert_pointers"][member["alert_id"]]} == plan["expected_alert_pointers"][member["alert_id"]]
                material = await store.one(select(m.AlertMaterials.__table__).where(m.AlertMaterials.id == UUID(member["material_id"]),
                    m.AlertMaterials.tenant_id == tenant))
                assert {k: material[k] for k in member["material"]} == member["material"]
            for iid, diagnosis in plan["expected_incident_pointers"].items():
                actual = (await store.db.execute(select(m.Incidents.latest_diagnosis_id).where(
                    m.Incidents.id == UUID(iid), m.Incidents.tenant_id == tenant))).scalar_one()
                assert str(actual) == diagnosis
            task = await store.one(select(m.Tasks.__table__).where(m.Tasks.id == UUID(plan["human_revision"]["task_id"]),
                m.Tasks.tenant_id == tenant))
            assert str(task["current_revision_id"]) == config["human_revision_id"]
            human = await store.one(select(m.TaskRevisions.__table__).where(m.TaskRevisions.id == UUID(config["human_revision_id"]),
                m.TaskRevisions.tenant_id == tenant))
            assert jsonable_encoder(human) == plan["human_revision"], "human_revision_changed"
            comparison = await store.one(select(m.Results.__table__).where(m.Results.id == UUID(config["comparison_result_id"]),
                m.Results.tenant_id == tenant))
            assert jsonable_encoder(comparison) == plan["comparison_result"], "comparison_changed"
        save(out / "execute-intent.json", {"scenario": config["scenario"], "attempt": 1,
            "plan_sha256": sha(folder / "plan.json"), "new_runs": 1, "new_AI_runs": 0, "new_H_revisions": 0})
        phase = "prepare_new_run"
        prepared = await service.prepare_baseline(tenant, cid, PrepareBaseline(
            operation_key=plan["operations"]["prepare"], expected_scope_revision=plan["case"]["scope_revision"]), actor=actor)
        save(out / "prepared.json", jsonable_encoder(prepared))
        rid = prepared.pending_run_id
        request = Start(operation_key=plan["operations"]["start"], expected_scope_revision=plan["case"]["scope_revision"],
            window_start=plan["scope"]["window_start"], window_end=plan["scope"]["window_end"],
            comparison_result_id=config["comparison_result_id"])
        save(out / "start-request.json", {"case_id": cid, "run_id": rid, "body": request.model_dump(mode="json")})
        async with service.transaction(tenant, readonly=True) as store:
            now = await store.now()
        policy = active_policy()
        limits = policy.case.limits(now, policy.identity)
        save(out / "limits.json", limits.model_dump(mode="json"))
        phase = "fixed_C1_C6"
        await service.start_full(tenant, cid, rid, request, actor=actor, limits=limits, gateway=gateway)
        phase = "read_run"
        actual = jsonable_encoder(await service.read_run(tenant, cid, rid))
        save(out / "run-readback.json", actual)
        outcome = {"run_state": actual["run"]["state"], "result_ids": actual["result_ids"]}
    except Exception as exc:  # noqa: BLE001 -- do not expose connection credentials
        outcome = {"state": "execution_exception", "phase": phase, "error_type": type(exc).__name__,
                   "code": getattr(exc, "code", None)}
    finally:
        save(out / "execution.json", {**outcome, "case_id": cid, "run_id": rid,
            "model_calls": gateway.calls, "unknown": gateway.unknown})
        await database.engine.dispose()
        await engine.dispose()
    print(outcome, "model_calls", gateway.calls, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "run", "export"))
    args = parser.parse_args()
    config, folder = initialize(HERE / "config.json")
    if args.phase == "prepare":
        prepare(config, folder)
    elif args.phase == "export":
        asyncio.run(prior_driver(config).export(config, folder, config["scenario"]))
    else:
        with knowledge_forward(config, folder / config["scenario"]):
            asyncio.run(run(config, folder))
