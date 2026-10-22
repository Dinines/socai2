#!/usr/bin/env python3
"""Local-only functional observation of original Case → four-agent workflow.

Uses already-provided local credentials and 21 PG/Neo4j/model infrastructure.
Starts no worker, runs no DDL/deployment, records at most four real model calls.
All secrets and raw observations stay in git-ignored .local; source fixture is
explicitly synthetic. Modes api/agents are separate local uvicorn processes.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import secrets
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".local/aisoc21/attack-context-20261021"
PRIVATE = ROOT / ".local/aisoc21/private"
API_URL = "http://127.0.0.1:24900"
AGENTS_URL = "http://127.0.0.1:24904"


def envfile(path: Path) -> dict[str, str]:
    from dotenv import dotenv_values
    return {k: v for k, v in dotenv_values(path).items() if v is not None}


def configure(mode: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    secret_file = OUT / "local-secrets.json"
    if not secret_file.exists():
        fd = os.open(secret_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({k: secrets.token_urlsafe(48) for k in ("jwt", "api_reader", "agents_peer")}, f)
    local = json.loads(secret_file.read_text())
    runtime = envfile(PRIVATE / "runtime.env")
    agents = envfile(PRIVATE / "agents-1g.env")
    os.environ.update({k: agents[k] for k in ("OPENAI_API_KEY", "LLM_GATEWAY_API_KEY", "LITELLM_MASTER_KEY") if agents.get(k)})
    os.environ.update({
        "DATABASE_URL": runtime["DATABASE_URL"],
        "PGSSLROOTCERT": str(ROOT / ".local/aisoc21/ueba-fusion-joint-20261021/ca.crt"),
        "SECRET_KEY": local["jwt"], "ENVIRONMENT": "test", "ENV": "test", "DEBUG": "false",
        "AISOC_API_SERVICE_TOKEN": local["api_reader"], "AISOC_AGENTS_SERVICE_TOKEN": local["agents_peer"],
        "AISOC_ATTACK_CONTEXT_ENABLED": "true", "AISOC_GRAPH_ENABLED": "true",
        "AISOC_INVESTIGATE_USE_ROUTER": "false", "AISOC_TRIAGE_WORKER_ENABLED": "false",
        "API_SERVICE_URL": API_URL, "AISOC_API_URL": API_URL, "AGENTS_SERVICE_URL": AGENTS_URL,
        "OPENAI_BASE_URL": "http://127.0.0.1:24800/v1", "LLM_GATEWAY_URL": "http://127.0.0.1:24800/v1",
        "ENRICHMENT_SERVICE_URL": "http://127.0.0.1:24802", "AISOC_UEBA_URL": "http://127.0.0.1:24803",
        "AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS": "2048", "AISOC_INVESTIGATION_MAX_SECONDS": "240",
        "AISOC_LLM_RESPONSE_CACHE": "0", "AISOC_DEV_AUTH_BYPASS": "false",
        "REALTIME_URL": "http://127.0.0.1:24999",
    })
    # This local process has its own seven-RO identity. Do not inherit a stale
    # tenant map or accidentally promote the read token to projection writer.
    for name in ("AISOC_INVESTIGATION_CONTEXT_KEYS_FILE", "AISOC_INVESTIGATION_PREPARE_KEYS_FILE", "AISOC_TRIAGE_IDENTITY_KEYS_FILE"):
        os.environ.pop(name, None)
    sys.path.insert(0, str(ROOT / "services" / ("agents" if mode == "agents" else "api")))


def api_app():
    from fastapi import FastAPI
    from neo4j import AsyncGraphDatabase
    from app.db import neo4j as graph_db
    from app.api.v1.endpoints import cases, graph, investigations, attack_chain
    config = json.loads((PRIVATE / "identity-graph-3a/config.json").read_text())

    @asynccontextmanager
    async def lifespan(app):
        # Original schema bootstrap deliberately not called against shared 21.
        graph_db._driver = AsyncGraphDatabase.driver(config["uri"], auth=(config["username"], config["password"]),
                                                     connection_timeout=5, max_transaction_retry_time=0)
        await graph_db._driver.verify_connectivity()
        yield
        await graph_db._driver.close()
    app = FastAPI(lifespan=lifespan)
    for router in (cases.router, graph.router, investigations.router, attack_chain.router, attack_chain.alert_router):
        app.include_router(router, prefix="/api/v1")
    return app


def agents_app():
    from fastapi import FastAPI
    spec = importlib.util.spec_from_file_location("observation_probe", ROOT / "deploy/aisoc21/probe_investigation_case.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    evidence = OUT / "observation"
    evidence.mkdir(exist_ok=True)
    observation = probe.Observation(evidence, max_calls=4)
    observation.observe_http()
    observation.observe_factory()
    from app.investigator import orchestrator
    for stage in ("recon", "forensic", "responder", "report_writer"):
        name = "run_" + stage
        setattr(orchestrator, name, observation.wrap_node(getattr(orchestrator, name), stage))
    from app.api import investigate
    from app.llm import contract
    contract._RESPONSE_CACHE_ENABLED = False
    contract._RESPONSE_CACHE.clear()
    from app.investigator import ledger

    @asynccontextmanager
    async def lifespan(app):
        yield
        (OUT / "model-observation-summary.json").write_text(json.dumps({"calls_started": observation.calls_started,
            "replies_received": observation.replies_received, "models": observation.model_records}, indent=2))
        await ledger.close_pool()
    app = FastAPI(lifespan=lifespan)
    app.include_router(investigate.router)
    return app


async def client(mode: str) -> None:
    import asyncpg
    import httpx
    from app.core.security import create_access_token
    draft = json.loads((OUT / "case-three-alerts.draft.json").read_text())
    tenant = draft["tenant_id"]
    actor = draft["actor_user_id"]
    token = create_access_token({"sub": actor, "tenant_id": tenant})
    headers = {"Authorization": "Bearer " + token}
    local = json.loads((OUT / "local-secrets.json").read_text())
    read_headers = {"Authorization": "Bearer " + local["api_reader"], "X-AiSOC-Tenant-ID": tenant}
    async with httpx.AsyncClient(base_url=API_URL, timeout=40) as http:
        async def request(method, path, name, **kwargs):
            response = await http.request(method, path, headers=kwargs.pop("headers", headers), **kwargs)
            try: data = response.json()
            except ValueError: data = response.text
            (OUT / name).write_text(json.dumps({"method": method, "path": path, "http_status": response.status_code, "body": data}, ensure_ascii=False, indent=2))
            print(name, response.status_code, flush=True)
            return response, data
        if mode == "seed":
            import uuid
            dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(dsn)
            try:
                user = await conn.fetchrow("SELECT id, tenant_id, role, is_active FROM users WHERE id=$1", uuid.UUID(actor))
                if not user or not user["is_active"] or str(user["tenant_id"]) != tenant:
                    raise RuntimeError("Fixture actor is not an active user of the expected tenant")
                async with conn.transaction():
                    await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", tenant)
                    for original in draft["alerts"]:
                        row = {**original, "case_id": None}
                        columns = list(row)
                        values = []
                        casts = []
                        for k,v in row.items():
                            if k in {"id", "tenant_id", "case_id"}: v = uuid.UUID(v) if v else None
                            if k in {"event_time", "first_seen", "last_seen"}: v = datetime.fromisoformat(v)
                            cast = "::jsonb" if isinstance(v,(list,dict)) else ""
                            values.append(json.dumps(v) if cast else v)
                            casts.append(f"${len(values)}{cast}")
                        await conn.execute(f"INSERT INTO alerts ({','.join(columns)}) VALUES ({','.join(casts)})", *values)
                print("seeded_new_synthetic_alerts", len(draft["alerts"]), flush=True)
            finally: await conn.close()
            response, body = await request("POST", "/api/v1/cases", "case-created.json", json=draft["case"])
            response.raise_for_status()
            cid = body["id"]
            (OUT / "active-case.json").write_text(json.dumps({"case_id": cid,"tenant_id":tenant,"alert_ids":draft["case"]["alert_ids"]}, indent=2))
        else:
            active = json.loads((OUT / "active-case.json").read_text()); cid = active["case_id"]
        aid = draft["alerts"][0]["id"]
        if mode == "checks":
            import uuid
            control_id = str(uuid.uuid4())
            row = draft["alerts"][0]
            dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(dsn)
            try:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", tenant)
                    await conn.execute("INSERT INTO alerts (id,tenant_id,title,severity,status,priority,event_time,first_seen,last_seen,affected_hosts,affected_users,affected_ips,affected_assets,entities,source_event_ids,mitre_techniques,mitre_tactics,raw_event,enrichment_data,tags) VALUES ($1,$2,$3,'low','new',10,$4,$4,$4,$5::jsonb,'[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'[]'::jsonb,'{}'::jsonb,'{}'::jsonb,'[\"synthetic\",\"attack-context-control\"]'::jsonb)",
                        uuid.UUID(control_id), uuid.UUID(tenant), "Synthetic unrelated alert control", datetime.fromisoformat(row["event_time"]), json.dumps(["LAB-UNRELATED-"+control_id]))
            finally: await conn.close()
            (OUT / "control-alert.json").write_text(json.dumps({"id":control_id,"synthetic":True}))
            await request("GET", "/api/v1/graph/investigation-context", "control-no-case-context.json", headers=read_headers, params={"alert_id":control_id})
            identities = json.loads((PRIVATE / "app-1f.json").read_text())["identities"]
            other = str(identities["b"]["tenant_id"])
            await request("GET", "/api/v1/graph/investigation-context", "other-tenant-context.json", headers={**read_headers,"X-AiSOC-Tenant-ID":other}, params={"case_id":cid})
        if mode in {"seed", "read"}:
            await request("POST", "/api/v1/graph/investigation-context", "projection-read-token-refused.json", headers=read_headers, json={"case_id":cid})
            await request("POST", "/api/v1/graph/investigation-context", "projection.json", json={"case_id":cid})
            await request("GET", "/api/v1/graph/investigation-context", "case-context.json", headers=read_headers, params={"case_id":cid})
            await request("GET", f"/api/v1/alerts/{aid}/attack-chain", "alert-chain.json")
            await request("GET", "/api/v1/graph/investigation-context", "alert-context.json", params={"alert_id":aid})
        if mode == "launch":
            if active.get("run_id"):
                raise ValueError("This observation already launched a Run; use fresh inputs and output directory, never replay it")
            response, body = await request("POST", f"/api/v1/cases/{cid}/investigate", "investigation-launched.json", json={"alert_summary":"Local synthetic functional case. Read-only investigation; shared entities imply candidates, not confirmed causality."})
            response.raise_for_status()
            active["run_id"] = body["run_id"]
            (OUT / "active-case.json").write_text(json.dumps(active,indent=2))
        if mode == "results":
            rid = active["run_id"]
            await request("GET", f"/api/v1/investigations/{rid}", "run-detail.json")
            await request("GET", f"/api/v1/investigations/{rid}/events", "run-events.json", params={"since":-1,"limit":200})
            _, body = await request("GET", f"/api/v1/investigations/{rid}/artifacts", "run-artifacts.json")
            rows = body if isinstance(body,list) else body.get("items",body.get("artifacts",[]))
            for row in rows:
                await request("GET", f"/api/v1/investigations/{rid}/artifacts/{row['id']}", f"artifact-{row['kind']}-{row['id']}.json")
            _, md = await request("GET", f"/api/v1/cases/{cid}/investigations/{rid}/report.md", "report-response.json")
            if isinstance(md,str): (OUT/"report.md").write_text(md)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["api","agents","seed","read","launch","results","checks"])
    parser.add_argument("--output-dir", type=Path, help="Fresh git-ignored output directory, one Case observation per directory")
    args=parser.parse_args()
    if args.output_dir:
        OUT = args.output_dir.resolve()
        if not OUT.is_relative_to(ROOT / ".local"):
            raise ValueError("Probe outputs and secrets must stay in git-ignored .local")
    configure(args.mode)
    if args.mode in {"api","agents"}:
        import uvicorn
        uvicorn.run(api_app() if args.mode=="api" else agents_app(), host="127.0.0.1", port=24900 if args.mode=="api" else 24904, log_level="warning")
    else:
        asyncio.run(client(args.mode))
