#!/usr/bin/env python3
"""One isolated real Kafka delivery → local API → PG/Neo4j observation.

The original worker starts only on a fresh test topic/group. Its triage entry
is an observation seam which raises BudgetHold, so no outcome is fabricated,
no offset is committed and no model/Run/closure is attempted. Credentials
remain in the ignored output directory. Never import the older model probes.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / ".local/aisoc21/private"
API_URL = "http://127.0.0.1:24920"


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    path.chmod(0o600)


def envfile(name: str) -> dict[str, str]:
    from dotenv import dotenv_values
    return {k: v for k, v in dotenv_values(PRIVATE / name).items() if v is not None}


def configure(out: Path, mode: str) -> dict:
    config = json.loads((out / "private.json").read_text())
    # Only transport/PG configuration is copied; no model or vendor credentials.
    fusion = envfile("fusion-1f.env")
    runtime = envfile("runtime.env")
    for name in list(os.environ):
        if name.startswith(("OPENAI_", "LLM_", "LITELLM_", "ANTHROPIC_")):
            os.environ.pop(name, None)
    os.environ.update({k: v for k, v in fusion.items() if k.startswith("KAFKA_")})
    os.environ.update({
        "DATABASE_URL": runtime["DATABASE_URL"],
        "PGSSLROOTCERT": str(ROOT / ".local/aisoc21/ueba-fusion-joint-20261021/ca.crt"),
        "PGSSLMODE": "verify-full",
        "KAFKA_SSL_CAFILE": str(ROOT / ".local/aisoc21/ueba-fusion-joint-20261021/ca.crt"),
        "SECRET_KEY": config["jwt_secret"], "ENVIRONMENT": "test", "ENV": "test", "DEBUG": "false",
        "AISOC_API_SERVICE_TOKEN": config["reader"], "AISOC_DEV_AUTH_BYPASS": "false",
        "API_SERVICE_URL": API_URL, "AISOC_API_URL": API_URL,
        "AISOC_ATTACK_CONTEXT_ENABLED": "true", "AISOC_GRAPH_ENABLED": "true",
        "AISOC_TRIAGE_WORKER_ENABLED": "false", "AISOC_TRIAGE_ADMISSION_PROFILE": "legacy",
        "AISOC_DETERMINISTIC": "1", "AISOC_AGENT_ESCALATE_TO_GRAPH": "0",
        "AISOC_AGENT_RAISE_APPROVALS": "0", "AISOC_AGENT_MEMORY_SUPPRESSION": "0",
        "AISOC_AGENT_MEMORY_WRITEBACK": "0", "AISOC_PLAYBOOK_EXECUTION_ENABLED": "false",
        "AISOC_INVESTIGATION_PREPARE_KEYS_FILE": str(out / "writers.json"),
        "AISOC_INVESTIGATION_CONTEXT_KEYS_FILE": str(out / "readers.json"),
    })
    os.environ.pop("AISOC_TRIAGE_IDENTITY_KEYS_FILE", None)
    sys.path.insert(0, str(ROOT / "services" / ("api" if mode == "api" else "agents")))
    return config


async def graph_rows(driver, tenant: str, aid: str) -> dict:
    async with driver.session() as session:
        result = await session.run(
            "MATCH (a:Alert {id:$aid,tenant_id:$tenant}) "
            "OPTIONAL MATCH (a)-[r]->(n) "
            "RETURN properties(a) AS alert, type(r) AS relation, properties(r) AS provenance, "
            "labels(n) AS labels, properties(n) AS node ORDER BY relation",
            aid=aid, tenant=tenant)
        rows = await result.data()
        cases = await (await session.run(
            "MATCH (c:Case)-[:CONTAINS_ALERT]->(a:Alert {id:$aid,tenant_id:$tenant}) RETURN count(c) AS count",
            aid=aid, tenant=tenant)).single()
    return {"rows": rows, "case_memberships": cases["count"]}


def api_app(out: Path):
    from fastapi import FastAPI, Request
    from neo4j import AsyncGraphDatabase
    from app.db import neo4j as graph_db
    from app.db.database import engine
    from app.api.v1.endpoints import graph
    graph_config = json.loads((PRIVATE / "identity-graph-3a/config.json").read_text())

    @asynccontextmanager
    async def lifespan(app):
        graph_db._driver = AsyncGraphDatabase.driver(graph_config["uri"],
            auth=(graph_config["username"], graph_config["password"]),
            connection_timeout=5, max_transaction_retry_time=0)
        try:
            await graph_db._driver.verify_connectivity()
            yield
        finally:
            await graph_db._driver.close()
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.include_router(graph.router, prefix="/api/v1")

    @app.get("/probe-ready")
    async def ready():
        return {"ready": True}

    @app.middleware("http")
    async def record(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/"):
            # Never persist Authorization or other header values.
            with (out / "api-requests.jsonl").open("a") as stream:
                stream.write(json.dumps({"method": request.method, "path": request.url.path,
                    "status": response.status_code}) + "\n")
        return response
    return app


async def observe(out: Path, config: dict) -> None:
    from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state
    from app.workers import triage_budget
    from app.investigator import ledger
    from neo4j import AsyncGraphDatabase
    worker = FusedAlertTriageWorker(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        topic=config["topic"], group_id=config["group"], max_attempts=1, entity_concurrency=1)
    graph_config = json.loads((PRIVATE / "identity-graph-3a/config.json").read_text())
    driver = AsyncGraphDatabase.driver(graph_config["uri"],
        auth=(graph_config["username"], graph_config["password"]),
        connection_timeout=5, max_transaction_retry_time=0)
    observation = {"triage_entry_calls": 0, "business_triage_executed": False,
        "model_calls": 0, "run_created_by_probe": False, "expected_hold": False}

    async def triage_entry(message):
        observation["triage_entry_calls"] += 1
        state = build_state(message)
        if state is None:
            raise triage_budget.BudgetHold("Observation input invalid")
        observation["preparation"] = state.raw_alert.get("attack_context_preparation")
        observation["received_message"] = message
        observation["graph_at_triage_entry"] = await graph_rows(driver, config["tenant_id"], config["alert_id"])
        save(out / "observation.json", observation)
        # Deliberately retain the message: no triage result exists to acknowledge.
        raise triage_budget.BudgetHold("Bounded graph observation completed before business triage")

    worker.triage = triage_entry
    task = asyncio.create_task(worker.start())
    try:
        async with asyncio.timeout(30):
            while not worker._attached or not worker._consumer.assignment():
                if task.done():
                    await task
                await asyncio.sleep(0.1)
            partitions = worker._consumer.assignment()
            positions = [await worker._consumer.position(tp) for tp in partitions]
            assert positions == [0], "Fresh isolated topic must start empty"
            save(out / "consumer-ready.json", {"topic": config["topic"], "group": config["group"], "positions": positions})
        try:
            async with asyncio.timeout(45):
                await task
        except ledger.LedgerPersistError:
            observation["expected_hold"] = observation["triage_entry_calls"] == 1
        save(out / "observation.json", observation)
        assert observation["expected_hold"], "Original loop must exit without a durable triage outcome"
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await worker.stop()
        await driver.close()
        await ledger.close_pool()


async def run(out: Path, config: dict) -> None:
    import asyncpg
    import httpx
    import jwt
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from aiokafka.structs import TopicPartition
    from neo4j import AsyncGraphDatabase
    from app.core.kafka_security import kafka_client_kwargs
    tenant, aid = config["tenant_id"], config["alert_id"]
    receipt = {k: v for k, v in config.items() if k not in {"jwt_secret", "reader"}}
    receipt.update(status="started", model_calls=0, deployment=False, resident_worker_enabled=False,
        scope="real isolated Kafka intake and graph preparation; triage entry is observation seam",
        fusion_executed=False, production_topics_used=False)
    processes = []
    conn = None
    producer = admin = inspector = driver = None

    def phase(value):
        receipt["phase"] = value
        save(out / "receipt.json", receipt)
        print(json.dumps({"run_id": config["run_id"], "phase": value}), flush=True)

    def child(mode):
        log = (out / (mode + ".log")).open("w")
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), mode, "--out", str(out)],
            cwd=ROOT, stdout=log, stderr=log)
        processes.append((process, log))
        return process

    try:
        phase("read-only connection preflight")
        conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"), timeout=10)
        actor = await conn.fetchrow("SELECT tenant_id,is_active FROM users WHERE id=$1", uuid.UUID(config["actor_user_id"]))
        assert actor and actor["is_active"] and str(actor["tenant_id"]) == tenant
        shadow = await conn.fetchval("SELECT bool_or(enabled) FROM aisoc_shadow_mode WHERE tenant_id=$1 AND alert_class=ANY($2::text[])",
            uuid.UUID(tenant), ["identity", "*"])
        assert not shadow, "Do not bypass an existing shadow policy"
        receipt["shadow_policy_read"] = "disabled_for_fixture_class_and_wildcard"
        graph_config = json.loads((PRIVATE / "identity-graph-3a/config.json").read_text())
        driver = AsyncGraphDatabase.driver(graph_config["uri"], auth=(graph_config["username"], graph_config["password"]),
            connection_timeout=5, max_transaction_retry_time=0)
        await driver.verify_connectivity()
        before = await graph_rows(driver, tenant, aid)
        assert not before["rows"]
        receipt["graph_before"] = before
        admin = AIOKafkaAdminClient(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"], **kafka_client_kwargs())
        await admin.start()
        now = datetime.now(UTC)
        token = jwt.encode({"sub": config["actor_user_id"], "type": "access", "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 300}, config["jwt_secret"], algorithm="HS256")
        save(out / "writers.json", {tenant: token})
        save(out / "readers.json", {tenant: config["reader"]})
        api_process = child("api")
        async with httpx.AsyncClient(base_url=API_URL, timeout=25) as http:
            async with asyncio.timeout(25):
                while True:
                    assert api_process.poll() is None, "Local API exited; private log retained"
                    try:
                        if (await http.get("/probe-ready")).status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(0.2)
            # Seed exactly one new already-persisted fused Alert fixture, not a Fusion run.
            row = json.loads((out / "fixture.json").read_text())
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", tenant)
                await conn.execute("INSERT INTO alerts (id,tenant_id,title,severity,status,priority,event_time,first_seen,last_seen,affected_hosts,affected_users,affected_ips,affected_assets,entities,source_event_ids,mitre_techniques,mitre_tactics,raw_event,enrichment_data,tags) VALUES ($1,$2,$3,'medium','new',50,$4,$4,$4,$5::jsonb,$6::jsonb,'[]'::jsonb,'[]'::jsonb,$7::jsonb,'[]'::jsonb,$8::jsonb,'[]'::jsonb,'{}'::jsonb,'{}'::jsonb,$9::jsonb)",
                    uuid.UUID(aid), uuid.UUID(tenant), row["alert"]["title"], now,
                    json.dumps([row["alert"]["hostname"]]), json.dumps([row["alert"]["user"]]),
                    json.dumps([{"type": "domain", "value": config["ioc"]}]), json.dumps(["T1078"]),
                    json.dumps(["synthetic", "kafka-graph-intake", config["run_id"]]))
            receipt["seeded_alerts"] = 1
            # The local seven-RO identity remains unable to project this real row.
            reader_headers = {"Authorization": "Bearer " + config["reader"], "X-AiSOC-Tenant-ID": tenant}
            refusal = await http.post("/api/v1/graph/investigation-context", headers=reader_headers, json={"alert_id": aid})
            receipt["reader_post_status"] = refusal.status_code
            assert refusal.status_code == 403
            await admin.create_topics([NewTopic(config["topic"], 1, 1, topic_configs={"retention.ms": "86400000"})])
            observer_process = child("observe")
            async with asyncio.timeout(30):
                while not (out / "consumer-ready.json").exists():
                    assert observer_process.poll() is None, "Observer exited before assignment; private log retained"
                    await asyncio.sleep(0.2)
            phase("real consumer assigned; publishing one synthetic fused envelope")
            producer = AIOKafkaProducer(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"], **kafka_client_kwargs())
            await producer.start()
            metadata = await producer.send_and_wait(config["topic"], json.dumps(row).encode())
            receipt["published"] = {"topic": metadata.topic, "partition": metadata.partition, "offset": metadata.offset}
            async with asyncio.timeout(55):
                while observer_process.poll() is None:
                    await asyncio.sleep(0.2)
            assert observer_process.returncode == 0, "Observation failed; private log retained"
            observed = json.loads((out / "observation.json").read_text())
            prep = observed["preparation"]
            assert prep["status"] == "success" and prep["owner"] == "kafka_consumer"
            assert prep["tenant_id"] == tenant and prep["alert_id"] == aid
            graph = observed["graph_at_triage_entry"]
            expected = {"OBSERVED_ON": "Host", "INVOLVES_USER": "User", "CONTAINS_IOC": "IOC", "MAPS_TO": "Technique"}
            assert len(graph["rows"]) == 4 and graph["case_memberships"] == 0
            assert {r["relation"]: r["labels"][0] for r in graph["rows"]} == expected
            assert all(r["provenance"]["source_alert_id"] == aid for r in graph["rows"])
            assert all(r["node"].get("tenant_id") == tenant for r in graph["rows"] if "Technique" not in r["labels"])
            assert any(r["node"].get("indicator_value") == config["ioc"] for r in graph["rows"])
            response = await http.get("/api/v1/graph/investigation-context", headers=reader_headers, params={"alert_id": aid})
            response.raise_for_status()
            save(out / "context-read.json", response.json())
            assert response.json()["attack_path"]["status"] == "not_linked"
            inspector = AIOKafkaConsumer(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
                group_id=config["group"], enable_auto_commit=False, **kafka_client_kwargs())
            await inspector.start()
            receipt["committed_offset_after"] = await inspector.committed(TopicPartition(config["topic"], 0))
            assert receipt["committed_offset_after"] is None
            alert = await conn.fetchrow("SELECT status,case_id FROM alerts WHERE id=$1 AND tenant_id=$2", uuid.UUID(aid), uuid.UUID(tenant))
            assert alert["status"] == "new" and alert["case_id"] is None
            # Use the actual build_state identity, which remains only in memory.
            from app.workers.fused_alert_consumer import build_state
            run_id = str(build_state(row).run_id)
            receipt["new_run_count"] = await conn.fetchval("SELECT count(*) FROM investigation_runs WHERE id=$1 AND tenant_id=$2", uuid.UUID(run_id), uuid.UUID(tenant))
            assert receipt["new_run_count"] == 0
            receipt.update(status="passed", observation=observed, graph_node_count=5, graph_edge_count=4,
                alert_status=alert["status"], case_id=None, business_triage_executed=False)
            phase("bounded joint verification passed")
    except BaseException as exc:
        receipt.update(status="failed", error_type=type(exc).__name__)
        phase("stopped; evidence retained")
        raise
    finally:
        for process, log in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, 10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    await asyncio.to_thread(process.wait, 5)
            log.close()
        for client in (inspector, producer, admin):
            if client is not None:
                try:
                    await client.close() if client is admin else await client.stop()
                except Exception:
                    pass
        if driver is not None:
            await driver.close()
        if conn is not None:
            await conn.close()
        receipt["local_processes_stopped"] = all(process.poll() is not None for process, _ in processes)
        save(out / "receipt.json", receipt)


def initialize(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    run_id = uuid.uuid4().hex[:12]
    # Existing synthetic actor: do not alter its permissions or tenant.
    actor = json.loads((ROOT / ".local/aisoc21/attack-context-20261021/case-three-alerts.draft.json").read_text())
    config = {"run_id": run_id, "tenant_id": actor["tenant_id"], "actor_user_id": actor["actor_user_id"],
        "alert_id": str(uuid.uuid4()), "topic": f"socai2.graphintake.{run_id}.fused",
        "group": f"socai2.graphintake.{run_id}.agents", "ioc": f"graph-{run_id}.example.invalid",
        "jwt_secret": secrets.token_urlsafe(48), "reader": secrets.token_urlsafe(48)}
    save(out / "private.json", config)
    save(out / "fixture.json", {"tenant_id": config["tenant_id"], "id": config["alert_id"],
        "alert_row_id": config["alert_id"], "incident_id": str(uuid.uuid4()), "alert": {
            "id": "synthetic-upstream-" + run_id, "tenant_id": config["tenant_id"],
            "title": "Synthetic Kafka graph intake " + run_id, "category": "identity", "severity": "medium",
            "hostname": "LAB-GRAPH-" + run_id, "user": "synthetic-graph-" + run_id,
            "domain": config["ioc"], "mitre_techniques": ["T1078"]}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "api", "observe"])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "run":
            initialize(args.out)
        configuration = configure(args.out, args.mode)
        if args.mode == "api":
            import uvicorn
            uvicorn.run(api_app(args.out), host="127.0.0.1", port=24920, log_level="warning")
        else:
            asyncio.run(run(args.out, configuration) if args.mode == "run" else observe(args.out, configuration))
    except Exception as exc:
        # A traceback may contain connection strings; keep terminal output safe.
        print(json.dumps({"status": "stopped", "error_type": type(exc).__name__}), flush=True)
        sys.exit(1)
