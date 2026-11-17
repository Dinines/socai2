"""Step 5 HTTP admission against handed-over PG fixtures; no executor or model."""
import hashlib
import json
import os
import traceback
from pathlib import Path
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_service import BaselineService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import analysis_task_service, case_service
from investigation_http.main import app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

TABLES = (m.Alerts, m.Incidents, m.IncidentAlerts, m.Cases, m.CaseAlerts, m.CaseIncidents,
          m.CaseAlertExclusions, m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState,
          m.Runs, m.Activities, m.ActivityTargets)


async def run_checks(engine, record, only=None):
    if only == {"case_replace_added_only_http"}:
        return await run_added_only_check(engine, record)
    phase = "case_allocation_http_writes"
    assert only == {phase}
    sample = json.loads(Path(os.environ["SOCAI2_CASE_ALLOCATION_HTTP_SAMPLE_FILE"]).read_text())
    tenant, actor, event = (UUID(sample[k]) for k in ("tenant_id", "actor_id", "incident_id"))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    core = BaselineService(sessions)
    backend = CaseBackend(sessions)
    originals = dict(app.dependency_overrides)
    context = getattr(app.state, "business_context", None)
    env = {key: os.environ.get(key) for key in ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE")}
    calls, receipts, before, after = [], {}, None, None

    async def snapshot():
        rows, hashes = {}, {}
        async with core.transaction(tenant, readonly=True) as store:
            for model in TABLES:
                table = model.__table__
                data = [dict(row) for row in (await store.db.execute(
                    select(table).where(table.c.tenant_id == tenant))).mappings()]
                rows[table.name] = data
                hashes[table.name] = {json.dumps({key.name: row[key.name] for key in table.primary_key}, sort_keys=True, default=str):
                    hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest() for row in data}
        return rows, hashes

    async def verify_allocation(value):
        saved, _ = await snapshot()
        for item in value["allocations"]:
            row = next(row for row in saved["cases"] if str(row["id"]) == item["case_id"])
            assert row["scope_revision"] == item["scope_revision"]
            actual = {str(row["alert_id"]) for row in saved["case_alerts"] if str(row["case_id"]) == item["case_id"]}
            assert set(item["added_alert_ids"]) | set(item["existing_alert_ids"]) <= actual
            assert item["case_url"] == f"/api/v1/socai2/cases/{item['case_id']}"
            task = item["initial_task"]
            if task:
                stored = next(row for row in saved["analysis_tasks"] if str(row["id"]) == task["task_id"])
                assert str(stored["subject_id"]) == item["case_id"] == task["subject_id"]
                assert stored["state"] == task["status"] == "accepted" and stored["intent"] == "initial"
                assert str(stored["submitted_by"]) == str(actor)
                assert task["status_url"] == item["case_url"] + "/analysis-tasks/" + task["task_id"]
            assert (task is not None) == item["created"]
        return saved

    try:
        os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = sample["allocation_policy_file"]
        os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = sample["task_policy_file"]
        policy = AnalysisTaskPolicy.load()
        app.state.business_context = BusinessContext(tenant, actor, "Case allocation HTTP fixture")
        app.dependency_overrides.update({case_service: lambda: backend,
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy)})
        saved, before = await snapshot()
        alerts = sorted(str(row["id"]) for row in saved["alerts"])
        assert len(alerts) >= 320
        event_members = {str(row["alert_id"]) for row in saved["incident_alerts"] if row["incident_id"] == event}
        assert len(event_members) > 200
        root = "/api/v1/socai2"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def request(method, path, status=200, **kwargs):
                call = {"method": method, "path": path, "request": kwargs}
                calls.append(call)
                response = await client.request(method, path, **kwargs)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == status, call
                return call["body"]

            async def detail(cid):
                return await request("GET", root + "/cases/" + cid)

            create = {"operation_key": str(uuid4()), "title": "HTTP 99 plus 5", "alert_ids": alerts[:99]}
            first = await request("POST", root + "/cases", 201, json=create)
            receipts["create"] = first
            await verify_allocation(first)
            cid = first["primary_case_id"]
            view = await detail(cid)
            assert view["member_count"] == 99
            associate = {"operation_key": str(uuid4()), "expected_scope_revision": view["case"]["scope_revision"],
                         "alert_ids": alerts[99:104]}
            associated = await request("POST", root + f"/cases/{cid}/associations", json=associate)
            receipts["associate"] = associated
            await verify_allocation(associated)
            views = [await detail(item["case_id"]) for item in associated["allocations"]]
            assert [view["member_count"] for view in views] == [100, 4]
            kept = sorted(row["alert_id"] for row in views[0]["members"])[:98]
            replaced = await request("PUT", root + f"/cases/{cid}/members", json={"operation_key": str(uuid4()),
                "expected_scope_revision": views[0]["case"]["scope_revision"], "alert_ids": kept + [alerts[-1]]})
            receipts["replace"] = replaced
            await verify_allocation(replaced["allocation"])
            assert len(replaced["source"]["removed_alert_ids"]) == 2
            assert (await detail(cid))["member_count"] == 98
            assert next(i for i in replaced["allocation"]["allocations"] if i["case_id"] == associated["receiving_case_id"])["added_alert_ids"] == [alerts[-1]]

            source = await request("POST", root + "/cases", 201, json={"operation_key": str(uuid4()),
                "title": "HTTP move source", "alert_ids": alerts[300:302]})
            await verify_allocation(source)
            sid = source["primary_case_id"]
            sv, tv = await detail(sid), await detail(cid)
            moved = await request("POST", root + f"/cases/{sid}/members/move", json={"operation_key": str(uuid4()),
                "target_case_id": cid, "expected_source_scope_revision": sv["case"]["scope_revision"],
                "expected_target_scope_revision": tv["case"]["scope_revision"], "alert_ids": [alerts[300]]})
            receipts["move"] = moved
            await verify_allocation(moved["allocation"])
            assert moved["source"]["removed_alert_ids"] == moved["moved_alert_ids"] == [alerts[300]]
            sv = await detail(sid)
            assert sv["member_count"] == 1
            cleared = await request("PUT", root + f"/cases/{sid}/members", json={"operation_key": str(uuid4()),
                "expected_scope_revision": sv["case"]["scope_revision"], "alert_ids": []})
            receipts["clear"] = cleared
            assert (await detail(sid))["member_count"] == 0
            assert not any(i["initial_task"] for i in cleared["allocation"]["allocations"])

            current = await detail(cid)
            later = await request("POST", root + f"/cases/{cid}/associations", json={"operation_key": str(uuid4()),
                "expected_scope_revision": current["case"]["scope_revision"], "alert_ids": alerts[104:204]})
            await verify_allocation(later)
            assert later["receiving_case_id"] != associated["receiving_case_id"]
            _, replay_before = await snapshot()
            assert await request("POST", root + "/cases", 201, json=create) == first
            assert await request("POST", root + f"/cases/{cid}/associations", json=associate) == associated
            conflict = await request("POST", root + "/cases", 409, json={**create, "title": "different"})
            assert conflict["detail"]["code"] == "operation_conflict"
            stale = await request("POST", root + f"/cases/{cid}/associations", 409, json={"operation_key": str(uuid4()),
                "expected_scope_revision": 0, "alert_ids": [alerts[204]]})
            assert stale["detail"]["code"] == "scope_conflict"
            missing = await request("POST", root + "/cases", 404, json={"operation_key": str(uuid4()),
                "title": "Missing member must not leave a case", "alert_ids": [str(uuid4())]})
            assert missing["detail"]["code"] == "member_alert_not_found"
            assert replay_before == (await snapshot())[1]

            full = await request("POST", root + "/cases", 201, json={"operation_key": str(uuid4()),
                "title": "HTTP whole event", "incident_ids": [str(event)]})
            receipts["whole_event"] = full
            await verify_allocation(full)
            assert {aid for item in full["allocations"] for aid in item["added_alert_ids"]} == event_members
            assert len(full["allocations"]) == (len(event_members) + 99) // 100
            full_views = [await detail(item["case_id"]) for item in full["allocations"]]
            assert sum(view["member_count"] for view in full_views) == len(event_members)
            assert all(0 < view["member_count"] <= 100 for view in full_views)
            eroot = full["primary_case_id"]
            ids = sorted(row["alert_id"] for row in full_views[0]["members"])
            exclusion = await request("PUT", root + f"/cases/{eroot}/members", json={"operation_key": str(uuid4()),
                "expected_scope_revision": full_views[0]["case"]["scope_revision"], "alert_ids": ids[1:]})
            ex_view = await detail(eroot)
            honored = await request("POST", root + f"/cases/{eroot}/associations", json={"operation_key": str(uuid4()),
                "expected_scope_revision": ex_view["case"]["scope_revision"], "incident_ids": [str(event)]})
            receipts["exclude"], receipts["exclusion_honored"] = exclusion, honored
            await verify_allocation(honored)
            assert honored["excluded_alert_ids"] == ids[:1]
            assert ids[0] not in {a for i in honored["allocations"] for a in i["added_alert_ids"] + i["existing_alert_ids"]}
            saved, after = await snapshot()
            new_cases = {str(row["id"]) for row in saved["cases"] if str(row["created_by"]) == str(actor)}
            initial_ids = {i["initial_task"]["task_id"] for receipt in (first, associated, source, later, full)
                           for i in receipt["allocations"] if i["initial_task"]}
            for task_id in initial_ids:
                task_row = next(r for r in saved["analysis_tasks"] if str(r["id"]) == task_id)
                assert str(task_row["subject_id"]) in new_cases
                task = await request("GET", root + f"/cases/{task_row['subject_id']}/analysis-tasks/{task_id}")
                assert task["status"] == "accepted" and task["latest_run_id"] is None
                assert task["attempts"] == [] and task["results"] == []
            assert after == (await snapshot())[1], "Task GET must remain read-only"
            for table in ("alerts", "incident_alerts", "runs", "analysis_attempts"):
                assert before[table] == after[table], table
            assert all(after["cases"][key] == value for key, value in before["cases"].items())
        record(phase, True, {"sample": sample, "calls": calls, "receipts": receipts, "before": before,
            "after": after, "initial_task_count": len(initial_ids), "whole_event_member_count": len(event_members),
            "model_calls": 0, "redis_calls": 0, "case_execution_calls": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve original partial batch; do not claim acceptance
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"sample": sample, "calls": calls, "receipts": receipts, "before": before,
            "after": after, "error": str(exc), "error_type": type(exc).__name__,
            "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(originals)
        app.state.business_context = context
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def run_added_only_check(engine, record):
    """Narrow follow-up for source.changed and management CaseView projection."""
    sample = json.loads(Path(os.environ["SOCAI2_CASE_ALLOCATION_HTTP_SAMPLE_FILE"]).read_text())
    tenant, actor = UUID(sample["tenant_id"]), UUID(sample["actor_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    core, backend = BaselineService(sessions), CaseBackend(sessions)
    original, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    env = {k: os.environ.get(k) for k in ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE")}
    calls = []
    try:
        os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = sample["allocation_policy_file"]
        os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = sample["task_policy_file"]
        app.state.business_context = BusinessContext(tenant, actor, "Case added-only HTTP fixture")
        app.dependency_overrides[case_service] = lambda: backend
        async with core.transaction(tenant, readonly=True) as store:
            aids = [str(a) for a in (await store.db.execute(select(m.Alerts.id).where(
                m.Alerts.tenant_id == tenant).order_by(m.Alerts.id).limit(2))).scalars()]
        prefix = "/api/v1/socai2/cases"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def request(method, path, status=200, **kwargs):
                call = {"method": method, "path": path, "request": kwargs}
                calls.append(call)
                response = await client.request(method, path, **kwargs)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == status, call
                return call["body"]
            created = await request("POST", prefix, 201, json={"operation_key": str(uuid4()),
                "title": "HTTP replacement added-only", "alert_ids": aids[:1]})
            cid = created["primary_case_id"]
            body = {"operation_key": str(uuid4()), "expected_scope_revision": created["allocations"][0]["scope_revision"], "alert_ids": aids}
            replaced = await request("PUT", prefix + f"/{cid}/members", json=body)
            assert replaced["source"]["changed"] is True and replaced["source"]["removed_alert_ids"] == []
            assert replaced["allocation"]["allocations"][0]["added_alert_ids"] == aids[1:]
            assert replaced["allocation"]["allocations"][0]["initial_task"] is None
            detail = await request("GET", prefix + f"/{cid}")
            assert detail["member_count"] == 2 and {r["alert_id"] for r in detail["members"]} == set(aids)
            management = await request("GET", prefix + f"/{cid}/management")
            changed = await request("PATCH", prefix + f"/{cid}/management", json={"operation_key": str(uuid4()),
                "expected_row_version": management["case"]["row_version"], "title": "HTTP replacement saved"})
            latest = await request("GET", prefix + f"/{cid}")
            assert changed["case"]["continuation"] == latest["case"]["continuation"] == detail["case"]["continuation"]
            assert latest["case"]["title"] == "HTTP replacement saved"
            assert await request("PUT", prefix + f"/{cid}/members", json=body) == replaced
        async with core.transaction(tenant, readonly=True) as store:
            row = await store.case(UUID(cid), lock=False)
            assert set(await store.members(UUID(cid))) == set(map(UUID, aids))
            assert row["scope_revision"] == replaced["source"]["scope_revision"]
            tasks = [dict(r) for r in (await store.db.execute(select(m.AnalysisTasks.__table__).where(
                m.AnalysisTasks.tenant_id == tenant, m.AnalysisTasks.subject_id == UUID(cid)))).mappings()]
            assert len(tasks) == 1 and tasks[0]["state"] == "accepted" and tasks[0]["intent"] == "initial"
            runs = (await store.db.execute(select(m.Runs.id).where(m.Runs.tenant_id == tenant,
                m.Runs.case_id == UUID(cid)))).scalars().all()
            assert runs == []
        record("case_replace_added_only_http", True, {"sample": sample, "calls": calls,
            "case": dict(row), "tasks": tasks, "model_calls": 0, "case_execution_calls": 0})
    except Exception as exc:  # noqa: BLE001 -- keep the targeted follow-up evidence
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record("case_replace_added_only_http", False, {"sample": sample, "calls": calls,
            "error_type": type(exc).__name__, "error": str(exc),
            "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
        app.state.business_context = context
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
