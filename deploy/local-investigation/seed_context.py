"""Import synthetic inventory/SOP through real local storage; never call a model."""
import argparse
import ast
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from config import (
    DATABASE,
    LAKE,
    PORTS,
    PRIVATE,
    ROOT,
    STATE,
    TENANT,
    USER,
    minimal_process_environment,
    read_private,
    runtime_environment,
)
from initialize import safe_error


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def read_plan(path):
    path = path.resolve()
    path.relative_to((STATE / "validation").resolve())
    assert path.name == "plan.json" and path.parent.name.startswith("local-")
    plan = json.loads(path.read_text())
    assert plan["tenant_id"] == TENANT and plan["database"] == DATABASE and plan["lake_database"] == LAKE
    assert plan["batch_id"] == path.parent.name
    assert plan["case"]["host"] == plan["batch_id"] + "-host"
    assert len(plan["case"]["alerts"]) == len(plan["canonical_alert_ids"]) == 2
    return path, plan


def context_input(plan):
    tree = ast.parse((ROOT / "services/fusion/app/services/socai2_projection.py").read_text())
    namespace = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "STORE_NAMESPACE" for t in node.targets))
    titles = list(dict.fromkeys(a["title"] for a in plan["case"]["alerts"]))
    assert all(isinstance(t, str) and 2 <= len(t) <= 256 for t in titles)
    terms = "Retrieval terms: " + "; ".join(titles) + ". "
    content = terms + (
        "This general investigation procedure lists checks to perform, not findings about a particular activity. "
        "Preserve event identifiers, raw source records, account and host names, commands, parent processes and exact timestamps. "
        "Distinguish a process start from a completed command. An event reporting success only describes the action reported by that event. "
        "Look for command completion, exit status and follow-on activity before describing execution outcomes. "
        "Resolve missing telemetry and conflicting clocks explicitly.\n\n"
    ) + terms + (
        "For a network connection, retain endpoint addresses, ports, protocol, process attribution and observed time range. "
        "A connection alone does not establish data contents, an external transfer or successful exfiltration. "
        "Obtain relevant byte counters and transfer records when the question requires them. "
        "For authorization, seek a change record or accountable human confirmation that identifies the exact account, host, action and window. "
        "An inventory entry, an account role or a familiar hostname is not evidence that an activity was authorized. "
        "Do not extend a statement about one event to other events without a documented matching scope. "
        "Record unavailable evidence and unresolved questions; this SOP supplies no case verdict or authorization decision."
    )
    return {"batch_id": plan["batch_id"], "tenant_id": TENANT, "input_kind": "synthetic_context",
        "source_namespace": namespace,
        "case_truth_included": False, "human_result_included": False,
        "asset": {"id": str(uuid5(NAMESPACE_URL, "local-context:" + plan["batch_id"] + ":asset")),
                  "name": plan["case"]["host"], "asset_type": "host", "criticality": "medium",
                  "inventory_only_not_authorization": True},
        "document": {"title": "General process and network investigation SOP",
            "content": content, "doc_kind": "sop", "source_url": "urn:socai2:local-context:" + plan["batch_id"], "tags": []},
        "retrieval_titles": titles,
        "write_path": "direct knowledge_base.ingest with synthetic CurrentUser and admin AsyncSession",
        "http_auth_chain_verified": False, "model_calls": 0}


async def work(plan, payload, values, *, verify_only):
    # Import the real API function in its normal module context, without any
    # model credential or inherited old environment. There is no HTTP request.
    env = {**minimal_process_environment(), **runtime_environment("api", values)}
    env["OPENAI_API_KEY"] = ""
    os.environ.clear()
    os.environ.update(env)
    os.chdir(PRIVATE)
    sys.path.insert(0, str(ROOT / "services/api"))
    from app.api.v1.deps import CurrentUser
    from app.api.v1.endpoints.knowledge_base import IngestRequest, ingest
    from app.db.database import engine as api_engine
    from app.services.kb_chunking import chunk_text
    from app.socai2.baseline_enrichment_sources import QUERIES as CONTEXT_QUERIES
    from app.socai2.baseline_optional_sources import QUERIES
    from sqlalchemy import text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    expected_chunks = chunk_text(payload["document"]["content"])
    admin_engine = create_async_engine(URL.create("postgresql+asyncpg", username="postgres",
        password=values["PG_ADMIN_PASSWORD"], host="127.0.0.1", port=PORTS["postgres"], database=DATABASE),
        connect_args={"ssl": False, "timeout": 10, "command_timeout": 30}, echo=False)
    try:
        async with async_sessionmaker(admin_engine)() as db:
            assert (await db.execute(text("SELECT current_database()"))).scalar_one() == DATABASE
            if not verify_only:
                existing = (await db.execute(text("SELECT count(*) FROM public.aisoc_kb_documents WHERE tenant_id=:tenant AND source_url=:url"),
                    {"tenant": UUID(TENANT), "url": payload["document"]["source_url"]})).scalar_one()
                assert existing == 0, "context already seeded; use verify-only"
                now = datetime.now(UTC)
                await db.execute(text("""INSERT INTO public.assets
                    (id,tenant_id,asset_type,name,criticality,tags,last_seen,first_seen,metadata,created_at,updated_at)
                    VALUES(:id,:tenant,'host',:name,'medium','{}',:now,:now,
                           CAST(:metadata AS jsonb),:now,:now)"""),
                    {"id": UUID(payload["asset"]["id"]), "tenant": UUID(TENANT), "name": payload["asset"]["name"], "now": now,
                     "metadata": json.dumps({"source": "local_synthetic_inventory", "authorization": None})})
                # ingest commits its transaction, including the bounded asset insert.
                user = CurrentUser(user_id=UUID(USER), tenant_id=UUID(TENANT), role="soc_admin",
                                   email="context-import@local.invalid", scopes=["settings:write"])
                docs = await ingest(IngestRequest(**payload["document"]), db, user)
                assert len(docs) == len(expected_chunks)
        # Read and retrieve through the actual restricted API role and C2 SQL.
        async with async_sessionmaker(api_engine)() as db:
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": TENANT})
            rows = (await db.execute(text("SELECT * FROM public.aisoc_kb_documents WHERE tenant_id=:tenant AND source_url=:url ORDER BY chunk_index,id"),
                {"tenant": UUID(TENANT), "url": payload["document"]["source_url"]})).mappings().all()
            assert len(rows) == len(expected_chunks) and [r["content"] for r in rows] == expected_chunks
            assert [r["chunk_index"] for r in rows] == list(range(len(expected_chunks)))
            assert all(r["chunk_total"] == len(expected_chunks) for r in rows)
            ids = {str(row["id"]) for row in rows}
            probes = []
            for index, alert in enumerate(plan["case"]["alerts"]):
                keys = [{"object_key": "detection:" + plan["canonical_alert_ids"][index],
                    "namespace": payload["source_namespace"], "object_type": "detection", "value": alert["title"][:256], "ioc_type": None}]
                result = (await db.execute(text(QUERIES["knowledge"]),
                    {"keys": json.dumps(keys), "tenant": UUID(TENANT), "fetch_limit": 20})).scalars().all()
                result = [json.loads(row) if isinstance(row, str) else row for row in result]
                matched = [row for row in result if str(row["record_id"]) in ids]
                assert matched and all(row["record"]["content"] in expected_chunks for row in matched)
                probes.append({"alert_id": plan["canonical_alert_ids"][index], "title": alert["title"], "rows": matched})
            keys = [{"object_key": "host:" + payload["asset"]["name"], "namespace": payload["source_namespace"],
                     "object_type": "host", "value": payload["asset"]["name"], "ioc_type": "host"}]
            assets = (await db.execute(text(CONTEXT_QUERIES["assets"]),
                {"keys": json.dumps(keys), "tenant": UUID(TENANT), "fetch_limit": 20})).scalars().all()
            assets = [json.loads(row) if isinstance(row, str) else row for row in assets]
            assert any(str(row["record_id"]) == payload["asset"]["id"] for row in assets)
            return {"asset_rows": assets, "kb_rows": [dict(row) for row in rows], "title_fts_probes": probes,
                "chunk_count": len(rows), "runtime_role": "local_socai2_api", "actual_c2_run_consumption_verified": False,
                "function_ingest_verified": True, "http_auth_chain_verified": False, "model_calls": 0}
    finally:
        await admin_engine.dispose()
        await api_engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Allow the explicit local write/read phase")
    args = parser.parse_args()
    path, plan = read_plan(ROOT / args.plan)
    payload = context_input(plan)
    input_path = path.parent / "context-input.json"
    if input_path.exists():
        assert json.loads(input_path.read_text()) == payload, "context input changed"
    else:
        save(input_path, payload)
    if args.prepare_only:
        print(json.dumps({"prepared": True, "path": str(input_path), "model_calls": 0}))
        return
    assert args.execute, "--execute required for local context database access"
    relative = str((ROOT / "deploy/local-investigation/seed_context.py").relative_to(ROOT))
    assert plan["source_sha256"][relative] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), "script differs from fixed plan"
    if not args.verify_only:
        save(path.parent / "context-seed-intent.json", {"at": datetime.now(UTC), "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
             "writes": ["public.assets", "public.aisoc_kb_documents"], "retries": 0, "model_calls": 0})
    values = read_private()
    receipt = {"batch_id": plan["batch_id"], "started_at": datetime.now(UTC), "mode": "verify" if args.verify_only else "seed", "model_calls": 0}
    try:
        receipt.update(status="passed", results=asyncio.run(work(plan, payload, values, verify_only=args.verify_only)))
    except Exception as exc:  # noqa: BLE001 -- retain a sanitized partial-attempt record
        receipt.update(status="failed", error_type=type(exc).__name__, message=safe_error(exc, values))
    receipt["ended_at"] = datetime.now(UTC)
    receipt_path = path.parent / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-context-" + receipt["mode"] + ".json")
    save(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path), "model_calls": 0,
                      **({"error_type": receipt["error_type"], "message": receipt["message"]} if receipt["status"] == "failed" else {})}))
    raise SystemExit(0 if receipt["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
