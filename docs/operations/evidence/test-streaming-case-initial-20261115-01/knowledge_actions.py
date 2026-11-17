"""Explicit normal KB maintenance and retrieval, without Case or model generation."""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from app.api.v1.deps import CurrentUser
from app.api.v1.endpoints.knowledge_base import IngestRequest, ingest
from app.db.rls import set_rls_context
from app.socai2.analysis_dispatch_runtime import load_profile
from app.socai2.baseline_service import BaselineService
from app.socai2.knowledge_config import content_hash, load, selectors
from app.socai2.knowledge_source import DOCUMENTS, index, query
from app.socai2.knowledge_vectors import Vectors
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def read(path):
    return json.loads(path.read_text())


async def main():
    folder, action = Path(sys.argv[1]), sys.argv[2]
    cfg, corpus, expected = (read(folder / name) for name in ("runtime.json", "knowledge-documents.json", "expected.json"))
    profile, fingerprint = load()
    assert fingerprint == cfg["knowledge_profile_sha256"]
    assert profile.vector.collection == cfg["knowledge_collection"] and not profile.history.sync_after_adopted_triage
    dispatch = load_profile(cfg["dispatcher_profile"])
    dsn = Path(dispatch["database_url_file"]).read_text().strip()
    role = cfg["writer"]
    if action == "readback":
        dsn = make_url(read(Path(cfg["reader_private_path"]))["DATABASE_URL"])
        assert dsn.query.get("sslmode") == "require" and dispatch["database_connect_args"]["ssl"] == "require"
        dsn = dsn.difference_update_query(["sslmode", "channel_binding"])
        role = cfg["reader"]
    engine = create_async_engine(dsn, connect_args=dispatch["database_connect_args"], hide_parameters=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service, tenant = BaselineService(sessions), UUID(cfg["tenant_id"])
    try:
        async with service.transaction(tenant, readonly=True) as store:
            who = dict((await store.db.execute(text("""SELECT current_database() AS database,current_user AS role,
                current_setting('transaction_read_only') AS readonly,ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"""))).mappings().one())
            assert who["database"] == cfg["database"] and who["role"] == role and who["ssl"] and who["readonly"] == "on"
        result = {"state": "passed", "action": action, "identity": who, "generation_calls": 0,
                  "profile_sha256": fingerprint, "batch_id": cfg["batch_id"]}
        if action in {"ingest_K1", "ingest_K2"}:
            doc = next(d for d in corpus["documents"] if d["logical_id"] == action.removeprefix("ingest_"))
            async with sessions() as db:
                await set_rls_context(db, tenant)
                actor = (await db.execute(text("SELECT id,tenant_id,email,role FROM public.users WHERE tenant_id=:tenant AND id=:id"),
                                         {"tenant": tenant, "id": UUID(cfg["actor_id"])})).mappings().one()
                count = (await db.execute(text("SELECT count(*) FROM public.aisoc_kb_documents WHERE tenant_id=:tenant AND (title=:title OR source_url=:url)"),
                                         {"tenant": tenant, "title": doc["request"]["title"], "url": doc["request"]["source_url"]})).scalar_one()
                assert count == 0, "fixture_already_present_do_not_reimport"
                user = CurrentUser(user_id=actor["id"], tenant_id=actor["tenant_id"], role=actor["role"], email=actor["email"])
                imported = await ingest(IngestRequest(**doc["request"]), db, user)
                result.update(logical_id=doc["logical_id"], documents=[d.model_dump(mode="json") for d in imported])
                assert len(imported) == doc["expected_chunks"]
        else:
            imported = [read(folder / ("knowledge-ingest_" + key + "-01.json")) for key in ("K1", "K2")]
            assert all(v["status"] == "passed" for v in imported)
            ids = [d["id"] for v in imported for d in v["result"]["documents"]]
            if action == "index":
                vectors = Vectors(profile)
                try:
                    async with sessions() as db:
                        await set_rls_context(db, tenant)
                        result["index"] = await index(db, tenant, [UUID(v) for v in ids], vectors=vectors,
                                                      expected_profile_sha256=fingerprint)
                except Exception as exc:  # noqa: BLE001 -- preserve network outcome without credentials
                    result.update(state="failed_inspect_before_retry", error_type=type(exc).__name__, calls=vectors.calls)
            elif action == "readback":
                async with service.transaction(tenant, readonly=True) as store:
                    docs = list((await store.db.execute(text(DOCUMENTS), {"tenant": tenant, "ids": ids})).mappings())
                assert {str(v["id"]) for v in docs} == set(ids)
                saved = []
                for item, receipt in zip(corpus["documents"], imported, strict=True):
                    doc = next(d for d in docs if str(d["id"]) == receipt["result"]["documents"][0]["id"])
                    assert all(doc[k] == item["request"][k] for k in ("title", "doc_kind", "source_url", "content", "tags"))
                    assert doc["chunk_index"] == 0 and doc["chunk_total"] == 1
                    saved.append({"logical_id": item["logical_id"], "content_sha256": content_hash(doc), "row": dict(doc)})
                result["documents"] = saved
            elif action == "retrieve":
                indexed = read(folder / "knowledge-index-01.json")
                assert indexed["status"] == "passed"
                result["cases"] = {}
                all_ids = expected["cases"]["event_case"]["member_ids"]
                async with service.transaction(tenant, readonly=True) as store:
                    original = list((await store.db.execute(text("""SELECT to_jsonb(a) AS alert,to_jsonb(m) AS material
                        FROM socai2.alerts a JOIN socai2.alert_materials m ON m.tenant_id=a.tenant_id AND m.id=a.latest_material_id
                        WHERE a.tenant_id=:tenant AND a.id=ANY(CAST(:ids AS uuid[]))"""), {"tenant": tenant, "ids": all_ids})).mappings())
                # One full-member source probe includes A01; actual Case runs
                # will separately freeze their own selectors and exclusions.
                for name in ("event_case",):
                    case = expected["cases"][name]
                    selected = [r for r in original if str(r["alert"]["id"]) in case["member_ids"]]
                    assert len(selected) == len(case["member_ids"])
                    context = SimpleNamespace(alerts={str(r["alert"]["id"]): SimpleNamespace(alert=r["alert"]) for r in selected},
                                              scope=SimpleNamespace(window_start=datetime.fromisoformat(case["window"]["start"])))
                    keys = selectors(context, {str(r["alert"]["id"]): r["material"] for r in selected}, profile)
                    for key in keys:
                        key["profile_sha256"] = fingerprint
                    args = {"parameters": {"selectors": keys}}
                    vectors = Vectors(profile)
                    try:
                        rows, captured, metadata = await query(service, tenant, args, vectors=vectors)
                        positive = {r["purpose"] for r in rows}
                        assert {r["record_id"] for r in rows} <= set(ids)
                        assert not any(r["purpose"] == "historical_case_reference" for r in rows)
                        result["cases"][name] = {"args": args, "rows": rows, "captured_at": captured.isoformat(),
                                                 "metadata": metadata, "positive_purposes": sorted(positive),
                                                 "required_nonempty_coverage": {"technical_explanation", "investigation_guidance"} <= positive}
                    except Exception as exc:  # noqa: BLE001 -- no fallback or automatic repeat
                        result["cases"][name] = {"state": "failed", "error_type": type(exc).__name__, "calls": vectors.calls}
                        result["state"] = "failed"
                if result["state"] == "passed" and not all(v["required_nonempty_coverage"] for v in result["cases"].values()):
                    result["state"] = "source_coverage_incomplete"
            else:
                raise ValueError("unsupported action")
        print(json.dumps(result, ensure_ascii=False, default=str))
        return result["state"] == "passed"
    finally:
        await engine.dispose()


raise SystemExit(0 if asyncio.run(main()) else 1)
