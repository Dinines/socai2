"""R1 HTTP reads on isolated PG with real task acceptance and retained fixtures."""
import base64
import hashlib
import json
import traceback
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_store import StoreError, digest, encoded
from app.socai2.run_directory import R, RunDirectoryService
from app.socai2.run_directory_contracts import RunDirectoryQuery
from app.socai2.run_records import RunRecordLimits
from app.socai2.stage_reader import StageReadService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.run_directory import RunDirectoryBackend
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import (
    analysis_service,
    case_service,
    run_directory_service,
)
from investigation_http.main import app
from investigation_http.run_directory_contracts import RunDirectoryPage
from pydantic import ValidationError
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT = UUID(int=1)


async def run_checks(engine, record, only=None):
    if only and "run_directory_http" not in only:
        return
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    reader = RunDirectoryService(sessions, limits=RunRecordLimits(2, 3))
    backend = RunDirectoryBackend(sessions, limits=RunRecordLimits(2, 3))
    policy = AnalysisTaskPolicy(**json.loads((Path(__file__).resolve().parents[3] /
        "deploy/local-investigation/analysis-tasks.json").read_text()))
    lifecycle = AnalysisTaskService(sessions, replace(policy, retry_delay_seconds=0))
    task_subject = uuid4()
    linked_runs, tasks = [], []
    alerts, incidents, cases = ([uuid4() for _ in range(n)] for n in (3, 2, 3))
    run_ids = [uuid4() for _ in range(8)]
    artifact_ids = [uuid4() for _ in range(6)]
    result_ids = [uuid4() for _ in range(4)]
    # An isolated, synthetic time range; every seeded Run has a fresh identity.
    at = datetime(2020, 1, 1, tzinfo=UTC) + timedelta(seconds=uuid4().int % 100000000)
    end = at + timedelta(seconds=1)
    query = RunDirectoryQuery(time_from=at, time_to=end)
    ids = set(alerts + incidents + cases + run_ids + artifact_ids + result_ids)
    calls = []
    http_reads = []
    overrides = dict(app.dependency_overrides)
    old_context = getattr(app.state, "business_context", None)

    async def add(store, model, **values):
        identity = values.pop("id", uuid4())
        ids.add(identity)
        await store.db.execute(insert(model).values(id=identity, tenant_id=TENANT, **values))

    async def fixture():
        async with reader.transaction(TENANT) as store:
            for aid in alerts:
                await add(store, m.Alerts, id=aid, title="Directory fixture alert", source_namespace="run-directory-20261114",
                          source_identity_key=str(aid))
            for iid in incidents:
                await add(store, m.Incidents, id=iid, title="Directory fixture incident", source_namespace="run-directory-20261114",
                          source_incident_id=str(iid))
            for cid in cases:
                await add(store, m.Cases, id=cid, title="Directory fixture case")
            for cid, aid in ((cases[0], alerts[0]), (cases[1], alerts[0]), (cases[1], alerts[1])):
                await add(store, m.CaseAlerts, case_id=cid, alert_id=aid, membership_source="manual", source_operation_id=uuid4())
            for aid in alerts[:2]:
                await add(store, m.IncidentAlerts, incident_id=incidents[0], alert_id=aid, membership_source="manual",
                          correlation_basis={}, basis_version="synthetic.v1", source_operation_id=uuid4())
            for cid in (cases[0], cases[2]):
                await add(store, m.CaseIncidents, case_id=cid, incident_id=incidents[0], source_operation_id=uuid4())
            states = ["completed", "unknown", "failed", "completed", "unknown", "pending_update"]
            deliveries = ["complete", "unknown", "none", "partial", "unknown", "complete"]
            parents = [("alert", aid) for aid in alerts] + [("incident", iid) for iid in incidents] + [("case", cases[0])]
            for n, (kind, identity) in enumerate(parents):
                values = {"kind": {"alert": "alert_basic", "incident": "incident_diagnosis", "case": "baseline"}[kind],
                          kind + "_id": identity, "title": "Directory fixture Run", "purpose": "saved records test",
                          "trigger": "manual", "requested_at": at, "state": states[n], "delivery_state": deliveries[n]}
                if kind == "case":
                    scope = (await store.db.execute(select(m.Cases.scope_revision).where(m.Cases.id == identity))).scalar_one()
                    values.update(scope_revision=scope, scope_kind="whole_case")
                else:
                    values.update(started_at=at, input_artifact_id=artifact_ids[n], executor_version="synthetic.v1",
                                  operation_key=str(uuid4()), request_hash=digest({"run": str(run_ids[n])}))
                    if states[n] in {"completed", "failed"}:
                        values["ended_at"] = end
                await add(store, R, id=run_ids[n], **values)
                members = [{"alert": {"id": str(alerts[n] if n < 3 else alerts[0])}}] if n != 4 else []
                payload = {"version": "socai2.stage-result.v1", "kind": values["kind"], "members": members}
                if n == 2:
                    payload = {"fixture": "no recorded membership"}
                await add(store, m.Artifacts, id=artifact_ids[n], **{kind + "_id": identity}, run_id=run_ids[n],
                          kind="input_snapshot", schema_version="socai2.stage-result.v1", content_json=payload,
                          sha256=digest(payload), size_bytes=len(encoded(payload)), captured_at=at,
                          mime_type="application/json", material_state="complete", source_refs=[], retention={})
                if kind == "case":
                    await add(store, m.RunMembers, case_id=identity, run_id=run_ids[n], alert_id=alerts[0])
                    await store.db.execute(update(R).where(R.c.id == run_ids[n]).values(state="running", started_at=at,
                        input_artifact_id=artifact_ids[n], executor_version="synthetic.v1", operation_key=str(uuid4()), request_hash=digest({"fixture": True})))
                    await store.db.execute(update(R).where(R.c.id == run_ids[n]).values(state="completed", ended_at=end))
            # Current membership changes after freezing; the reader must still return one input.
            await add(store, m.CaseAlerts, case_id=cases[0], alert_id=alerts[1], membership_source="manual", source_operation_id=uuid4())
            await add(store, R, id=run_ids[6], case_id=cases[2], kind="baseline", title="No frozen input", purpose="empty run",
                      trigger="manual", state="pending_update", scope_revision=1, scope_kind="whole_case", requested_at=at)
            await add(store, R, id=run_ids[7], alert_id=alerts[0], kind="alert_basic", title="Time boundary", purpose="half open range",
                      trigger="manual", state="cancelled", ended_at=end, requested_at=end)
            await add(store, m.AlertAssessments, id=result_ids[0], alert_id=alerts[0], kind="triage", source_run_id=run_ids[0],
                      verdict="needs_review", producer="synthetic.v1", actor={}, assessed_at=end, operation_key=str(uuid4()))
            await add(store, m.IncidentDiagnoses, id=result_ids[1], incident_id=incidents[0], source_run_id=run_ids[3],
                      revision=1, state="completed", input_artifact_id=artifact_ids[3], source_fingerprint="0" * 64,
                      producer="synthetic.v1", requested_at=at, generated_at=end, summary="Synthetic diagnosis")
            for n, rid in enumerate(result_ids[2:]):
                await add(store, m.Results, id=rid, case_id=cases[0], kind="baseline", source_run_id=run_ids[5],
                          title="Synthetic saved result", purpose="directory references", conclusion_state="unavailable",
                          conclusion_origin="system", validation_state="system_only", closing_note="synthetic",
                          findings=[], questions=[], recommendations=[], change_kind="initial", case_impact={
                              "summary": None, "supported_changes": [], "cannot_generalize": [], "next_steps": [],
                              "affected_scope": {"kind": "whole_case", "alert_ids": [str(alerts[0])], "object_keys": [],
                                                 "window_start": None, "window_end": None, "limitations": []}},
                          input_artifact_id=artifact_ids[5], delivery_state="partial", created_at=end, operation_key=str(uuid4()),
                          **({"supersedes_result_id": result_ids[2]} if n else {}))

    async def task_fixture():
        async with lifecycle.transaction(TENANT) as store:
            await add(store, m.Alerts, id=task_subject, title="Real task association fixture",
                      source_namespace="run-directory-http-20261114", source_identity_key=str(task_subject))
        for intent, outcomes in (("initial", ("failed", "unknown")), ("rerun", ("completed",)), ("check", ())):
            task = await lifecycle.submit(TENANT, kind="alert_triage", subject_id=task_subject, intent=intent,
                                          source="user", operation_key=uuid4(), submitted_by=UUID(int=3))
            tasks.append(task["task_id"])
            ids.add(task["task_id"])
            for outcome in outcomes:
                async with lifecycle.transaction(TENANT) as store:
                    attempt = await store.start_attempt(task["task_id"])
                    ids.add(attempt["id"])
                async with lifecycle.transaction(TENANT) as store:
                    rid, fid, now = uuid4(), uuid4(), await store.now()
                    payload = {"version": "socai2.stage-result.v1", "kind": "alert_basic",
                               "members": [{"alert": {"id": str(task_subject)}}]}
                    await add(store, R, id=rid, alert_id=task_subject, kind="alert_basic", title="Task-linked Run",
                              purpose="association read validation", trigger="manual", state="running", started_at=now,
                              input_artifact_id=fid, executor_version="synthetic.v1", operation_key=str(uuid4()),
                              request_hash=digest(payload))
                    await add(store, m.Artifacts, id=fid, alert_id=task_subject, run_id=rid, kind="input_snapshot",
                              schema_version=payload["version"], content_json=payload, sha256=digest(payload),
                              size_bytes=len(encoded(payload)), captured_at=now, mime_type="application/json",
                              material_state="complete", source_refs=[], retention={})
                    await store.bind_run(attempt["id"], rid, input_digest=digest(payload))
                    if outcome != "unknown":
                        await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                            state=outcome, ended_at=await store.now()))
                    await store.finish_attempt(attempt["id"], outcome=outcome,
                        error_code=None if outcome == "completed" else "execution_failed" if outcome == "failed" else "executor_interrupted",
                        retryable=outcome == "failed")
                    linked_runs.append(rid)

    async def snapshot():
        values = {}
        async with reader.transaction(TENANT, readonly=True) as store:
            for model in (m.Alerts, m.Incidents, m.Cases, m.CaseAlerts, m.CaseIncidents, m.IncidentAlerts,
                          m.Runs, m.RunMembers, m.Artifacts, m.AlertAssessments, m.IncidentDiagnoses, m.Results,
                          m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState):
                table = model.__table__
                identity = table.c.subject_id if model is m.AnalysisSubjectState else table.c.id
                rows = (await store.db.execute(select(table).where(*store.where(table, identity.in_(ids)))
                    .order_by(identity))).mappings().all()
                values[table.name] = {"count": len(rows), "sha256": hashlib.sha256(
                    json.dumps([dict(row) for row in rows], sort_keys=True, default=str).encode()).hexdigest()}
        return values

    async def read(**changes):
        selected = RunDirectoryQuery(**{**query.model_dump(), **changes})
        page = await backend.read(TENANT, selected)
        calls.append({"query": selected.model_dump(mode="json", exclude={"cursor"}), "total": page["total"],
                      "run_ids": [str(row["run_id"]) for row in page["items"]], "statistics": page["statistics"]})
        return page

    async def rejected(code, **changes):
        try:
            await read(**changes)
        except StoreError as exc:
            assert exc.code == code
        else:
            raise AssertionError("invalid query accepted")

    try:
        await fixture()
        await task_fixture()
        before = await snapshot()
        page = await read()
        expected = {"total_runs": 7, "by_state": {"pending_update": 1, "running": 0, "unknown": 2,
                    "completed": 3, "failed": 1, "cancelled": 0},
                    "by_delivery_state": {"none": 2, "partial": 1, "complete": 2, "unknown": 2},
                    "without_related_case_count": 2, "related_case_count": 3}
        assert page["total"] == 7 and len(page["items"]) == 2 and page["statistics"] == expected, page
        cursor = page["next_cursor"]
        all_items = page["items"][:]
        while page["next_cursor"]:
            page = await read(cursor=page["next_cursor"], limit=3)
            assert page["statistics"] == expected
            all_items += page["items"]
        assert [row["run_id"] for row in all_items] == sorted(run_ids[:7], reverse=True)
        rows = {row["run_id"]: row for row in all_items}
        assert [rows[rid]["input_member_count"] for rid in run_ids[:7]] == [1, 1, None, 1, 0, 1, None]
        assert len(rows[run_ids[5]]["results"]) == 2
        assert rows[run_ids[0]]["results"][0]["result_type"] == "alert_assessment"
        assert rows[run_ids[3]]["results"][0]["kind"] == "incident_diagnosis"
        assert not rows[run_ids[2]]["results"] and rows[run_ids[2]]["state"] == "failed"
        assert all(row["task_id"] is None and row["intent"] is None for row in all_items)
        for rid, row in rows.items():
            assert str(rid) in row["detail_url"] and str(row["subject_id"]) in row["detail_url"]
            for result in row["results"]:
                assert result["source_run_id"] == rid
                assert str(result["id"] if result["result_type"] == "case_result" else rid) in result["url"]
        app.state.business_context = BusinessContext(TENANT, UUID(int=3), "Synthetic directory reader")
        app.dependency_overrides[analysis_service] = lambda: StageReadService(sessions)
        app.dependency_overrides[case_service] = lambda: CaseBackend(sessions)
        app.dependency_overrides[run_directory_service] = lambda: backend
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            url = "/api/v1/socai2/analysis-runs"

            async def http_get(params, expected_status=200):
                response = await client.get(url, params=params)
                assert response.status_code == expected_status, (params, response.status_code, response.text[:1000])
                body = response.json()
                http_reads.append({"url": str(response.request.url), "status": response.status_code, "body": body})
                if expected_status == 200:
                    RunDirectoryPage.model_validate(body)
                return body

            params = {"time_from": at.isoformat(), "time_to": end.isoformat()}
            collected = []
            while True:
                body = await http_get(params)
                assert body["statistics"] == expected
                collected += [UUID(row["run_id"]) for row in body["items"]]
                if body["next_cursor"] is None:
                    break
                params["cursor"] = body["next_cursor"]
            assert collected == sorted(run_ids[:7], reverse=True)
            params = {"subject_type": "alert", "subject_id": str(task_subject)}
            body = await http_get(params)
            assert body["total"] == 3 and body["statistics"]["without_related_case_count"] == 3
            task_cursor = body["next_cursor"]
            linked = body["items"] + (await http_get({**params, "cursor": task_cursor}))["items"]
            assert [UUID(row["run_id"]) for row in linked] == list(reversed(linked_runs))
            assert [UUID(row["task_id"]) for row in linked] == [tasks[1], tasks[0], tasks[0]]
            assert [row["intent"] for row in linked] == ["rerun", "initial", "initial"]
            assert [row["state"] for row in linked] == ["completed", "unknown", "failed"]
            assert linked[1]["ended_at"] is None
            assert all(row["input_member_count"] == 1 for row in linked)
            initial = await http_get({**params, "intent": "initial", "limit": 1})
            assert initial["total"] == 2 and initial["statistics"]["by_state"]["unknown"] == 1
            second = await http_get({**params, "intent": "initial", "cursor": initial["next_cursor"]})
            assert second["statistics"] == initial["statistics"] and len(second["items"]) == 1
            assert (await http_get({**params, "intent": "check"}))["total"] == 0  # accepted, no Run
            assert (await http_get({**params, "intent": "rerun", "state": "completed"}))["total"] == 1
            assert (await http_get({"time_from": at.isoformat(), "time_to": end.isoformat(), "intent": "initial"}))["total"] == 0
            for invalid in ({"subject_id": str(task_subject)}, {"time_from": "2026-11-14T12:00:00"},
                            {"time_from": end.isoformat(), "time_to": at.isoformat()}, {"intent": "other"},
                            {"limit": 0}, {"limit": 4}, {"cursor": "malformed"}, {"extra": "true"},
                            [("limit", "1"), ("limit", "2")], {**params, "intent": "initial", "cursor": task_cursor}):
                await http_get(invalid, 422)
            assert (await http_get({"subject_type": "case", "subject_id": str(uuid4())}))["items"] == []
            def unavailable():
                from investigation_http.errors import record_error
                raise record_error("service_unavailable", 503)
            app.dependency_overrides[run_directory_service] = unavailable
            assert (await http_get({}, 503))["detail"]["code"] == "service_unavailable"
            app.dependency_overrides[run_directory_service] = lambda: backend
            for row in all_items:
                response = await client.get(row["detail_url"])
                assert response.status_code == 200, (response.status_code, response.text[:1000])
                body = response.json()
                assert body["run"]["id"] == str(row["run_id"])
                http_reads.append({"url": row["detail_url"], "run_id": row["run_id"], "status": response.status_code})
                for result in row["results"]:
                    if result["result_type"] == "case_result":
                        response = await client.get(result["url"])
                        assert response.status_code == 200, (response.status_code, response.text[:1000])
                        item = response.json()["result"]
                        http_reads.append({"url": result["url"], "result_id": result["id"], "status": response.status_code})
                    else:
                        item = body["result"]
                    assert item["id"] == str(result["id"]) and item["source_run_id"] == str(row["run_id"])
        incident = await read(subject_type="incident", subject_id=incidents[0])
        assert incident["total"] == 1 and incident["statistics"]["related_case_count"] == 3
        assert incident["statistics"]["without_related_case_count"] == 0
        alert = await read(subject_type="alert", subject_id=alerts[0])
        assert alert["total"] == 1 and alert["statistics"]["related_case_count"] == 2
        assert (await read(state="unknown"))["total"] == 2
        assert (await read(run_kind="baseline"))["total"] == 2
        empty = await read(subject_type="case", subject_id=uuid4())
        assert empty["total"] == 0 and empty["items"] == [] and empty["next_cursor"] is None
        assert all(n == 0 for n in empty["statistics"]["by_state"].values())
        boundary = await read(time_from=end, time_to=end + timedelta(seconds=1))
        assert [row["run_id"] for row in boundary["items"]] == [run_ids[7]]
        await rejected("invalid_cursor", cursor=cursor, state="failed")
        await rejected("invalid_cursor", cursor="malformed")
        await rejected("invalid_cursor", cursor=base64.urlsafe_b64encode(b'[]').decode())
        await rejected("invalid_input", limit=4)
        assert (await read(intent="check"))["total"] == 0
        for invalid in ({"subject_id": uuid4()}, {"time_from": "2026-11-14T12:00:00"},
                        {"time_from": end, "time_to": at}, {"subject_type": "other"}, {"extra": True}):
            try:
                RunDirectoryQuery(**invalid)
            except ValidationError:
                pass
            else:
                raise AssertionError("invalid input accepted")
        RunDirectoryPage.model_validate({**page, "items": all_items})
        other = await reader.read(UUID(int=2), query)
        assert other["total"] == 0
        assert "/api/v1/socai2/analysis-runs" in app.openapi()["paths"]
        after = await snapshot()
        assert before == after
        record("run_directory_http", True, {"real_pg": True, "http_endpoint_mounted": True,
               "task_dependency": "real core accept/start/bind/finish; no task-table substitution", "runs": run_ids,
               "linked_runs": linked_runs, "tasks": tasks, "results": result_ids,
               "items": all_items, "queries": calls, "existing_http_reads": http_reads, "database_before": before, "database_after": after,
               "model_calls": 0, "tool_calls": 0, "schema_migrations": 0})
    except Exception:  # noqa: BLE001 -- retain exact failed fixture/verification evidence
        record("run_directory_http", False, {"trace": traceback.format_exc(), "queries": calls, "existing_http_reads": http_reads})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = old_context
