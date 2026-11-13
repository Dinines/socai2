"""One real HTTP adoption path on a new local synthetic Case; no model calls."""
import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument("--profile", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
cfg = json.loads(args.profile.read_text())
db_cfg = json.loads((ROOT / cfg["database_config"]).read_text())
assert (db_cfg["host"], db_cfg["port"], db_cfg["processing_database"], db_cfg["processor"]) == (
    cfg["host"], cfg["port"], cfg["database"], cfg["role"])
os.environ.update(json.loads((ROOT / cfg["environment"]).read_text()))
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / cfg["policy"])
sys.path[:0] = [str(ROOT / p) for p in (".", "services/api", "docs/operations")]

from app.models import socai2 as m
from app.socai2.baseline_context import reference
from app.socai2.baseline_contracts import (
    FULL_EXECUTOR_VERSION,
    Actor,
    Publication,
    Scope,
    Start,
)
from app.socai2.baseline_store import A
from app.socai2.case_service import CaseService
from app.socai2.runtime_policy import active_policy
from capture_processing_case import TABLES, check_credentials, scoped_table_query
from httpx import AsyncClient
from sqlalchemy import URL, insert, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

args.output.mkdir(parents=True, exist_ok=False)
receipts = []
fixture = {}
tenant = UUID(cfg["tenant_id"])


def value(item):
    return item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item)


def save(name, data):
    body = json.dumps(data, ensure_ascii=False, indent=2, default=value) + "\n"
    check_credentials(body.encode())
    (args.output / (name + ".json")).write_text(body)
    return hashlib.sha256(body.encode()).hexdigest()


async def snapshot(service, name):
    async with service.transaction(tenant, readonly=True) as store:
        params = {"tenant": tenant, "aids": [UUID(fixture["alert_id"])], "incident": [],
                  "cid": UUID(fixture["case_id"]), "stages": []}
        prefix = ("WITH scope AS (SELECT CAST(:tenant AS uuid) tenant, CAST(:aids AS uuid[]) aids, "
                  "CAST(:incident AS uuid[]) incident, CAST(:cid AS uuid) cid, CAST(:stages AS uuid[]) stages) ")
        data = {table: (await store.db.execute(text(prefix + scoped_table_query(table)), params)).scalar_one()
                for table in TABLES}
        now = await store.now()
    checksum = save(name, data)
    return data, now, checksum


async def main():
    url = URL.create("postgresql+psycopg", username=db_cfg["admin"],
        password=Path(db_cfg["password_file"]).read_text().strip(), host=db_cfg["host"],
        port=db_cfg["port"], database=db_cfg["processing_database"])
    engine = create_async_engine(url, connect_args={"sslmode": cfg["sslmode"], "options": "-c role=" + cfg["role"]})
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    secret = json.loads((ROOT / cfg["credential_file"]).read_text())
    passed = False
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("select current_database(),current_user"))).one() == (cfg["database"], cfg["role"])
        async with AsyncClient(base_url=cfg["base_url"], timeout=cfg["timeout_seconds"],
            headers={"Authorization": "Bearer " + secret["api_key"]}) as client:

            async def request(method, path, body=None, expected=200):
                intent = {"method": method, "path": path, "input": copy.deepcopy(body)}
                save(f"{len(receipts) + 1:02}-intent", intent)
                response = await client.request(method, path, json=intent["input"])
                try:
                    data = response.json()
                except ValueError:
                    data = {"non_json_response": response.text}
                shown = data
                if path == "/openapi.json" and response.status_code == 200:
                    save("openapi", data)
                    shown = {"saved_as": "openapi.json", "release": data["info"]["version"]}
                receipts.append({**intent, "status": response.status_code, "body": copy.deepcopy(shown)})
                save("responses", receipts)
                assert response.status_code == expected, (path, response.status_code, data)
                return data

            contract = await request("GET", "/openapi.json")
            assert contract["info"]["version"] == cfg["release"]
            assert sum(len(v) for p, v in contract["paths"].items() if p.startswith("/api/v1/socai2")) == cfg["expected_operations"]
            aid, mid = uuid4(), uuid4()
            async with service.transaction(tenant) as store:
                await store.db.execute(insert(A).values(id=aid, tenant_id=tenant,
                    source_namespace="synthetic.result-adoption-http", source_identity_key=str(aid),
                    title=cfg["title"], event_time=await store.now(), event_time_source="source"))
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid,
                    revision=1, raw_text="Synthetic observation; authorization still unknown.", raw_json={"synthetic": True},
                    detection={}, source_scope={}, retention={}, material_state="complete"))
                await store.db.execute(update(A).where(*store.where(A, A.c.id == aid)).values(latest_material_id=mid))
            created = await request("POST", "/api/v1/socai2/cases", {"operation_key": str(uuid4()),
                "title": cfg["title"], "alert_ids": [str(aid)]})
            cid, rid = UUID(created["case_id"]), UUID(created["pending_run_id"])
            fixture.update(case_id=str(cid), alert_id=str(aid), material_id=str(mid), run_id=str(rid))
            save("fixture", fixture)
            async with service.transaction(tenant, readonly=True) as store:
                case = await store.case(cid, lock=False)
                actor = Actor(user_id=case["created_by"], name="Synthetic HTTP fixture preparer")
                limits = active_policy().case.limits(await store.now(), "synthetic.adoption-http.v1")

            async def idle(_):
                pass  # C1 only; Result below is a program fixture, not a model reply.

            await service.start(tenant, cid, rid, Start(operation_key=uuid4(), expected_scope_revision=1),
                actor=actor, executor=idle, executor_version=FULL_EXECUTOR_VERSION, limits=limits)
            scope = Scope(kind="whole_case", alert_ids=[aid], object_keys=[], window_start=None, window_end=None, limitations=[])
            publication = Publication(operation_key=uuid4(), terminal_state="completed",
                stop_reason="synthetic_http_adoption_fixture", title=cfg["title"],
                conclusion="Synthetic review-needed conclusion; authorization remains unconfirmed.",
                conclusion_state="uncertain", conclusion_origin="model", validation_state="accepted",
                closing_note="Program-provided Result for HTTP persistence verification; no model call.",
                findings=[], recommendations=[], questions=[{"id": "authorization", "text": "Confirm authorization",
                    "scope": scope, "evidence_requirements": ["Human confirmation"], "state": "unresolved",
                    "answer": None, "evidence_refs": [], "limitations": ["Not yet confirmed."]}],
                change_kind="initial", change_summary=None, delivery_state="partial",
                case_impact={"summary": None, "supported_changes": [], "cannot_generalize": ["Synthetic fixture only."],
                    "affected_scope": scope, "next_steps": []}, members=[{"alert_id": aid, "read_state": "read",
                    "assessment_state": "unresolved", "conclusion_covered": True, "assessment": None,
                    "limitations": "Authorization unconfirmed.", "evidence_refs": [reference("alert_material", mid, "observation")]}])
            save("program-publication-input", publication)
            published = await service.publish(tenant, cid, rid, publication)
            save("program-publication-output", published)
            assert published["adoption"]["state"] == "adopted"
            fixture["result_id"] = published["result_id"]
            path = "/api/v1/socai2/cases/" + str(cid)
            result_path = path + "/results/" + published["result_id"]
            preview = await request("GET", result_path + "/adoption-preview")
            assert preview["can_adopt"] and not preview["uncovered_alert_ids"]
            task = (await request("POST", path + "/tasks", {"operation_key": str(uuid4()),
                "expected_scope_revision": 1, "title": "采用结论后仍待人工核实"}))["task"]
            pending = await request("POST", path + "/baseline/prepare", {"operation_key": str(uuid4()), "expected_scope_revision": 1})
            body = {"operation_key": str(uuid4()), "expected_review_token": preview["review_token"],
                    "reason": "采用待复核判断，保留人工核实事项。", "acknowledge_pending_work": True}
            assert (await request("POST", result_path + "/adopt", body, 409))["detail"] == "result_adoption_preview_changed"
            ready = await request("GET", result_path + "/adoption-preview")
            save("adoption-preview", ready)
            assert ready["requires_pending_work_acknowledgement"]
            body["expected_review_token"] = ready["review_token"]
            assert (await request("POST", result_path + "/adopt", {**body, "acknowledge_pending_work": False}, 409))["detail"] == "result_adoption_pending_work_confirmation_required"
            before, _, _ = await snapshot(service, "sql-before-adoption")
            adoption = await request("POST", result_path + "/adopt", body)
            assert await request("POST", result_path + "/adopt", body) == adoption
            assert (await request("POST", result_path + "/adopt", {**body, "reason": "Different intent"}, 409))["detail"] == "operation_key_conflict"
            current = await request("GET", path)
            result = await request("GET", result_path)
            history = await request("GET", path + "/assessments?limit=1")
            older = await request("GET", path + "/assessments?limit=1&offset=1")
            assert current["case"]["current_assessment_id"] == adoption["assessment_id"]
            assert current["current_assessment"]["input_freshness"]["state"] == "current"
            assert result["result"] == ready["candidate"]
            assert history["total"] == 2 and history["next_offset"] == 1 and older["next_offset"] is None
            assert history["items"][0]["reason"] == body["reason"] and history["items"][0]["adopted_by"] == str(actor.user_id)
            assert history["items"][0]["origin"] == "model" and history["items"][0]["results"] == [result["result"]]
            assert older["items"] == [ready["current_assessment"]]
            assert await request("GET", path + "/tasks/" + task["id"]) == task
            assert (await request("GET", path + "/runs/" + pending["pending_run_id"]))["run"]["state"] == "pending_update"
            activities = await request("GET", path + "/activities")
            adopted_activities = [row for row in activities["items"] if row["action"] == "case_result_adopted"]
            assert len(adopted_activities) == 1
            await request("POST", result_path + "/adopt", {"operation_key": str(uuid4()), "expected_scope_revision": 1}, 422)
            await request("GET", path + "/results/" + str(uuid4()) + "/adoption-preview", expected=404)
            after, now, checksum = await snapshot(service, "database")
            for table in ("results", "result_members", "tasks", "task_revisions", "runs", "run_members", "artifacts"):
                assert after[table] == before[table], table
            assert len(after["case_assessments"]) == 2
            manual = next(row for row in after["case_assessments"] if row["id"] == adoption["assessment_id"])
            assert manual["reason"] == body["reason"] and manual["adopted_by"] == str(actor.user_id)
            assert manual["conclusion"] == publication.conclusion
            assert after["cases"][0]["current_assessment_id"] == manual["id"]
            assert after["cases"][0]["handling_status"] == before["cases"][0]["handling_status"]
            save("manifest", {"schema_version": "socai2.page-export.v1", "batch_id": args.output.parent.name + "-" + args.output.name,
                "exported_at": now, "source_environment": "local_tcp_real_pg_program_result_no_model",
                "database": cfg["database"], "tenant_id": tenant, "case_id": cid, "input_kind": "synthetic",
                "real_model_calls": 0, "database_snapshot": "single_readonly_repeatable_read",
                "sources": [{"file": "database.json", "sha256": checksum}],
                "table_counts": {table: len(rows) for table, rows in after.items()}})
            fixture.update(pending_run_id=pending["pending_run_id"], task_id=task["id"], adoption=adoption)
            save("fixture", fixture)
            passed = True
    except Exception:
        save("failure", {"traceback": traceback.format_exc()})
        if fixture.get("case_id"):
            await snapshot(service, "failure-database")
        raise
    finally:
        save("verification", {"passed": passed, "http_requests": len(receipts), "models": 0,
            "database": cfg["database"], "fixture": fixture, "production_changed": False})
        await engine.dispose()
    print(json.dumps({"passed": passed, "http_requests": len(receipts), "case_id": fixture["case_id"]}))


asyncio.run(main())
