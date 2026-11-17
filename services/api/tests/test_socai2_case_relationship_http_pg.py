"""Real PG relation/receiver HTTP reads, with explicitly labelled state fixtures."""
import hashlib
import json
import os
import traceback
from pathlib import Path
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_service import BaselineService
from app.socai2.page_reader import PageReadService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import case_service, page_service
from investigation_http.main import app
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker

TABLES = (m.Alerts, m.Incidents, m.IncidentAlerts, m.Cases, m.CaseAlerts, m.CaseIncidents,
          m.CaseAlertExclusions, m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState,
          m.Runs, m.Activities, m.ActivityTargets)


async def run_checks(engine, record, only=None):
    if only == {"alert_incident_records_contract"}:
        return await check_alert_incident_records(engine, record)
    phase = "case_relationship_http_reads"
    assert only == {phase}
    sample = json.loads(Path(os.environ["SOCAI2_CASE_ALLOCATION_HTTP_SAMPLE_FILE"]).read_text())
    tenant, actor, event = (UUID(sample[k]) for k in ("tenant_id", "actor_id", "incident_id"))
    write = json.loads(Path(sample["write_evidence"]).read_text())["checks"][0]
    assert write["passed"]
    root_id = UUID(write["detail"]["receipts"]["whole_event"]["primary_case_id"])
    source_sample = json.loads(Path(sample["source_evidence"]).read_text())["http_sample"]
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    core, backend = BaselineService(sessions), CaseBackend(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    env = {k: os.environ.get(k) for k in ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE")}
    calls, before, after, fixtures = [], None, None, {}

    async def snapshot():
        rows, hashes = {}, {}
        async with core.transaction(tenant, readonly=True) as store:
            for model in TABLES:
                table = model.__table__
                data = [dict(row) for row in (await store.db.execute(select(table).where(table.c.tenant_id == tenant))).mappings()]
                rows[table.name] = data
                hashes[table.name] = hashlib.sha256(json.dumps(sorted(data, key=lambda row: json.dumps(row, sort_keys=True, default=str)),
                    sort_keys=True, default=str).encode()).hexdigest()
        return rows, hashes

    def expected_relations(saved):
        cases = {r["id"]: r for r in saved["cases"]}
        by_alert, sources = {}, {}
        for row in saved["incident_alerts"]:
            by_alert.setdefault(row["alert_id"], set()).add(row["incident_id"])
        for row in saved["case_incidents"]:
            sources.setdefault(row["case_id"], {}).setdefault(row["incident_id"], set()).add("explicit")
        for row in saved["case_alerts"]:
            for iid in by_alert.get(row["alert_id"], set()):
                sources.setdefault(row["case_id"], {}).setdefault(iid, set()).add("member_alert")
        ours = sources.get(root_id, {})
        expected = []
        for cid, case in cases.items():
            if cid == root_id:
                continue
            same = case["continuation_root_case_id"] == cases[root_id]["continuation_root_case_id"]
            common = set(ours) & set(sources.get(cid, {}))
            if same or common:
                expected.append((case, same, common))
        expected.sort(key=lambda item: (not item[1], item[0]["created_at"], str(item[0]["id"])))
        return cases, sources, expected

    try:
        os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = sample["allocation_policy_file"]
        os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = sample["task_policy_file"]
        AnalysisTaskPolicy.load()
        app.state.business_context = BusinessContext(tenant, actor, "Case relationship HTTP fixture")
        app.dependency_overrides.update({case_service: lambda: backend, page_service: lambda: PageReadService(sessions)})
        # Only synthetic receiving-state fixtures are inserted here. They are not
        # successful user associations to a closed Case and do not run analysis.
        async with core.transaction(tenant) as store:
            for label, cid in (("closed", UUID(source_sample["closed_case"])),
                               ("auto_window_expired", UUID(source_sample["active_receiver"])), ("no_target", None)):
                iid = uuid4()
                await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant,
                    source_namespace="case-allocation-fixture", source_incident_id=str(iid),
                    title="Synthetic HTTP receiving state: " + label, active_case_id=cid))
                if cid:
                    await store.db.execute(insert(m.CaseIncidents).values(id=uuid4(), tenant_id=tenant,
                        case_id=cid, incident_id=iid, linked_by=actor, source_operation_id=uuid4()))
                fixtures[label] = {"incident_id": str(iid), "active_case_id": str(cid) if cid else None}
        saved, before = await snapshot()
        cases, sources, expected = expected_relations(saved)
        assert expected and any(same and common for _, same, common in expected)
        assert any(not same and common for _, same, common in expected)
        prefix = "/api/v1/socai2"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def request(method, path, status=200, **kwargs):
                call = {"method": method, "path": path, "request": kwargs}
                calls.append(call)
                response = await client.request(method, path, **kwargs)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == status, call
                return call["body"]

            url = prefix + f"/cases/{root_id}/related-cases"
            rows, cursor, revision, first_cursor = [], None, None, None
            while True:
                page = await request("GET", url, params={"limit": 2, **({"cursor": cursor} if cursor else {})})
                assert page["total"] == len(expected) and page["case_id"] == str(root_id)
                revision = revision or page["relation_revision"]
                assert page["relation_revision"] == revision
                rows.extend(page["items"])
                cursor = page["next_cursor"]
                first_cursor = first_cursor or cursor
                if cursor is None:
                    break
                assert len(rows) < page["total"]
            assert [r["case_id"] for r in rows] == [str(r[0]["id"]) for r in expected]
            for item, (case, same, common) in zip(rows, expected, strict=True):
                assert item["relation_types"] == (["continuation"] if same else []) + (["shared_incident"] if common else [])
                assert item["primary_relation"] == item["relation_types"][0]
                assert item["case_url"] == prefix + "/cases/" + str(case["id"])
                for field in ("title", "handling_status", "severity"):
                    assert item[field] == case[field]
                if same:
                    assert item["continuation"] == {"root_case_id": str(case["continuation_root_case_id"]),
                        "previous_case_id": str(case["previous_case_id"]) if case["previous_case_id"] else None,
                        "receiving_case_id": str(cases[case["continuation_root_case_id"]]["receiving_case_id"])}
                else:
                    assert item["continuation"] is None
                assert [s["incident_id"] for s in item["shared_incidents"]] == sorted(str(iid) for iid in common)
                for shared in item["shared_incidents"]:
                    iid = UUID(shared["incident_id"])
                    assert shared["current_case_sources"] == sorted(sources[root_id][iid])
                    assert shared["related_case_sources"] == sorted(sources[case["id"]][iid])

            root_view = await request("GET", prefix + f"/cases/{root_id}")
            assert root_view["case"]["continuation"]["receiving_case_id"] == str(cases[root_id]["receiving_case_id"])
            queue = await request("GET", prefix + "/cases", params={"q": root_view["case"]["title"], "limit": 50})
            queue_item = next(item for item in queue["items"] if item["case"]["id"] == str(root_id))
            management = await request("GET", prefix + f"/cases/{root_id}/management")
            assert queue_item["case"]["continuation"] == management["case"]["continuation"] == root_view["case"]["continuation"]
            current = await request("GET", prefix + f"/incidents/{event}")
            active = str(next(i for i in saved["incidents"] if i["id"] == event)["active_case_id"])
            assert current["case_receiving"] == {"active_case_id": active, "can_receive_automatically": True, "reason_code": None}
            items, offset = [], 0
            while True:
                page = await request("GET", prefix + f"/incidents/{event}/records/cases", params={"limit": 3, "offset": offset})
                items.extend(page["items"])
                if page["next_offset"] is None:
                    break
                offset = page["next_offset"]
            assert len(items) == page["total"] and len({i["id"] for i in items}) == len(items)
            assert [i["id"] for i in items if i["is_active_receiver"]] == [active]
            for label, fixture in fixtures.items():
                view = await request("GET", prefix + "/incidents/" + fixture["incident_id"])
                assert view["case_receiving"] == {"active_case_id": fixture["active_case_id"],
                    "can_receive_automatically": False, "reason_code": label}
            aid = str(saved["alerts"][0]["id"])
            alert = await request("GET", prefix + f"/alerts/{aid}")
            assert "case_receiving" not in alert
            alert_cases = await request("GET", prefix + f"/alerts/{aid}/records/cases")
            assert all("is_active_receiver" not in item for item in alert_cases["items"])
            empty = await request("GET", prefix + f"/cases/{source_sample['closed_case']}/related-cases")
            assert empty["items"] == [] and empty["total"] == 0 and empty["next_cursor"] is None
            missing = await request("GET", prefix + f"/cases/{uuid4()}/related-cases", 404)
            assert missing["detail"]["code"] == "case_not_found"
            for params, code in (({"cursor": "invalid"}, "invalid_cursor"), ({"limit": 101}, "invalid_input"), ({"extra": "x"}, "invalid_input")):
                value = await request("GET", url, 422, params=params)
                assert value["detail"]["code"] == code
            _, after = await snapshot()
            assert before == after, "All relationship GETs must be read-only"
            assert first_cursor
            member = next(row["alert_id"] for row in saved["incident_alerts"] if row["incident_id"] == event)
            changed = await request("POST", prefix + "/cases", 201, json={"operation_key": str(uuid4()),
                "title": "HTTP relation cursor change", "alert_ids": [str(member)]})
            _, changed_before = await snapshot()
            stale = await request("GET", url, 409, params={"limit": 2, "cursor": first_cursor})
            assert stale["detail"]["code"] == "cursor_stale"
            refreshed = await request("GET", url)
            assert refreshed["total"] == len(expected) + 1 and refreshed["relation_revision"] != revision
            assert any(i["case_id"] == changed["primary_case_id"] for i in refreshed["items"])
            assert changed_before == (await snapshot())[1]
        record(phase, True, {"sample": sample, "calls": calls, "fixtures": fixtures,
            "before": before, "after": after, "after_relation_change": changed_before,
            "related_count": len(expected), "model_calls": 0, "redis_calls": 0, "case_execution_calls": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve the failed batch without replacing its fixtures
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"sample": sample, "calls": calls, "fixtures": fixtures, "before": before, "after": after,
            "error_type": type(exc).__name__, "error": str(exc), "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def check_alert_incident_records(engine, record):
    """One GET protects the existing alert contract from the new routing column."""
    sample = json.loads(Path(os.environ["SOCAI2_CASE_ALLOCATION_HTTP_SAMPLE_FILE"]).read_text())
    tenant, actor = UUID(sample["tenant_id"]), UUID(sample["actor_id"])
    source = json.loads(Path(sample["source_evidence"]).read_text())["http_sample"]
    aid = UUID(source["alert_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    core = BaselineService(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    calls, before, after = [], None, None

    async def hashes():
        result = {}
        async with core.transaction(tenant, readonly=True) as store:
            for model in TABLES:
                table = model.__table__
                values = [dict(r) for r in (await store.db.execute(select(table).where(table.c.tenant_id == tenant))).mappings()]
                result[table.name] = hashlib.sha256(json.dumps(sorted(values, key=lambda r: json.dumps(r, sort_keys=True, default=str)),
                    sort_keys=True, default=str).encode()).hexdigest()
        return result

    try:
        before = await hashes()
        async with core.transaction(tenant, readonly=True) as store:
            expected_ids = {str(i) for i in (await store.db.execute(select(m.IncidentAlerts.incident_id).where(
                m.IncidentAlerts.tenant_id == tenant, m.IncidentAlerts.alert_id == aid))).scalars()}
        assert 0 < len(expected_ids) <= 200
        app.state.business_context = BusinessContext(tenant, actor, "Alert incident contract readback")
        app.dependency_overrides[page_service] = lambda: PageReadService(sessions)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            response = await client.get(f"/api/v1/socai2/alerts/{aid}/records/incidents", params={"limit": 200})
            body = response.json()
            calls.append({"method": "GET", "path": str(response.request.url), "status": response.status_code, "body": body})
            assert "authorization" not in response.request.headers
            assert response.status_code == 200
            assert {row["id"] for row in body["items"]} == expected_ids
            assert body["total"] == len(expected_ids) and body["next_offset"] is None
            assert all("active_case_id" not in row and "case_receiving" not in row for row in body["items"])
            assert all({"linked_at", "membership_source", "correlation_basis", "basis_version", "source_incident_id", "latest_diagnosis_id"} <= set(row) for row in body["items"])
        after = await hashes()
        assert before == after
        record("alert_incident_records_contract", True, {"sample": sample, "calls": calls,
            "before": before, "after": after, "model_calls": 0, "database_writes": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve read-only failure evidence
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record("alert_incident_records_contract", False, {"sample": sample, "calls": calls, "before": before,
            "after": after, "error_type": type(exc).__name__, "error": str(exc),
            "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
