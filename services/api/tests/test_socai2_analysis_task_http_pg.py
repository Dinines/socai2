"""Task HTTP contracts over actual isolated PG lifecycle records; no model calls."""
import hashlib
import json
import os
import traceback
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_store import digest, encoded
from app.socai2.stage_reader import StageReadService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.services import CaseBackend
from investigation_http.analysis_task_contracts import (
    AnalysisTaskDetail,
    AnalysisTaskPage,
)
from investigation_http.dependencies import (
    analysis_service,
    analysis_task_service,
    case_service,
)
from investigation_http.main import app
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT = UUID(int=1)


async def run_checks(engine, record, only=None):
    if only and "analysis_task_http" not in only:
        return
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    path = Path(__file__).resolve().parents[3] / "deploy/local-investigation/analysis-tasks.json"
    policy = replace(AnalysisTaskPolicy(**json.loads(path.read_text())), default_limit=2, max_limit=3)
    service = AnalysisTaskService(sessions, policy)
    immediate = AnalysisTaskService(sessions, replace(policy, retry_delay_seconds=0))
    backend = AnalysisTaskBackend(sessions, policy=policy)
    subjects = {kind: uuid4() for kind in ("alert", "incident", "case")}
    ids, submitted, runs, results, calls = set(subjects.values()), {}, {}, {}, []
    overrides = dict(app.dependency_overrides)
    old_context = getattr(app.state, "business_context", None)
    old_policy = os.environ.get("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE")

    async def add(store, model, **values):
        identity = values.pop("id", uuid4())
        ids.add(identity)
        await store.db.execute(insert(model).values(tenant_id=TENANT, id=identity, **values))
        return identity

    async def accept(kind, intent, key, selected=service):
        value = await selected.submit(TENANT, kind={"alert": "alert_triage", "incident": "incident_diagnosis",
            "case": "case_investigation"}[kind], subject_id=subjects[kind], intent=intent, source="user",
            operation_key=uuid4(), submitted_by=UUID(int=3))
        submitted[key] = value["task_id"]
        ids.add(value["task_id"])
        return value["task_id"]

    async def attempt(task_id, selected=service):
        async with selected.transaction(TENANT) as store:
            value = await store.start_attempt(task_id)
            ids.add(value["id"])
            return value

    async def saved_run(attempt, outcome, selected=service, *, result=False, retryable=False):
        kind, identity = attempt["subject_type"], attempt["subject_id"]
        rid, fid = uuid4(), uuid4()
        async with selected.transaction(TENANT) as store:
            now = await store.now()
            run_kind = {"alert": "alert_basic", "incident": "incident_diagnosis", "case": "baseline"}[kind]
            payload = {"version": "socai2.stage-result.v1", "kind": run_kind,
                       "members": [{"alert": {"id": str(subjects['alert'])}}]}
            values = {"id": rid, kind + "_id": identity, "kind": run_kind, "title": "Task HTTP fixture",
                      "purpose": "Synthetic persistence/read test", "trigger": "manual"}
            frozen = {"state": "running", "started_at": now, "input_artifact_id": fid,
                      "operation_key": str(uuid4()), "request_hash": digest(payload), "executor_version": "synthetic.v1"}
            if kind == "case":
                scope = (await store.case(identity))["scope_revision"]
                values.update(state="pending_update", scope_revision=scope, scope_kind="whole_case")
            else:
                values.update(frozen)
            await add(store, m.Runs, **values)
            await add(store, m.Artifacts, id=fid, **{kind + "_id": identity}, run_id=rid, kind="input_snapshot",
                      schema_version=payload["version"], content_json=payload, sha256=digest(payload),
                      size_bytes=len(encoded(payload)), captured_at=now, mime_type="application/json",
                      material_state="complete", source_refs=[], retention={})
            if kind == "case":
                await add(store, m.RunMembers, case_id=identity, run_id=rid, alert_id=subjects["alert"])
                await store.db.execute(update(m.Runs).where(m.Runs.id == rid).values(**frozen))
            await store.bind_run(attempt["id"], rid, input_digest=digest(payload))
            if outcome != "unknown":
                await store.db.execute(update(m.Runs).where(m.Runs.id == rid).values(state=outcome, ended_at=await store.now()))
            if result:
                if kind == "alert":
                    result_id = await add(store, m.AlertAssessments, alert_id=identity, kind="triage", source_run_id=rid,
                        verdict="needs_review", producer="synthetic.v1", actor={}, assessed_at=now, operation_key=str(uuid4()))
                elif kind == "incident":
                    result_id = await add(store, m.IncidentDiagnoses, incident_id=identity, source_run_id=rid,
                        revision=1, state="completed", input_artifact_id=fid, source_fingerprint="0" * 64,
                        producer="synthetic.v1", requested_at=now, generated_at=now, summary="Synthetic diagnosis")
                else:
                    result_id = await add(store, m.Results, case_id=identity, kind="baseline", source_run_id=rid,
                        title="Saved synthetic result", purpose="HTTP reference verification", conclusion_state="unavailable",
                        conclusion_origin="system", validation_state="system_only", closing_note="synthetic",
                        findings=[], questions=[], recommendations=[], change_kind="initial", input_artifact_id=fid,
                        delivery_state="partial", created_at=now, operation_key=str(uuid4()), case_impact={"summary": None,
                            "supported_changes": [], "cannot_generalize": [], "next_steps": [], "affected_scope": {
                                "kind": "whole_case", "alert_ids": [str(subjects['alert'])], "object_keys": [],
                                "window_start": None, "window_end": None, "limitations": []}})
                results[kind] = result_id
            await store.finish_attempt(attempt["id"], outcome=outcome, retryable=retryable,
                error_code=None if outcome == "completed" else "executor_interrupted" if outcome == "unknown" else "execution_failed")
        runs.setdefault(kind, []).append(rid)
        return rid

    async def fixtures():
        async with service.transaction(TENANT) as store:
            await add(store, m.Alerts, id=subjects["alert"], title="Task HTTP alert", source_namespace="analysis-task-http-20261114",
                      source_identity_key=str(subjects["alert"]))
            await add(store, m.Incidents, id=subjects["incident"], title="Task HTTP incident", source_namespace="analysis-task-http-20261114",
                      source_incident_id=str(subjects["incident"]))
            await add(store, m.Cases, id=subjects["case"], title="Task HTTP case")
            await add(store, m.IncidentAlerts, incident_id=subjects["incident"], alert_id=subjects["alert"], membership_source="manual",
                      correlation_basis={}, basis_version="synthetic.v1", source_operation_id=uuid4())
            await add(store, m.CaseAlerts, case_id=subjects["case"], alert_id=subjects["alert"], membership_source="manual", source_operation_id=uuid4())
        for kind in subjects:
            root = await accept(kind, "initial", kind + "_completed")
            if kind == "case":
                merged = await accept(kind, "check", "case_merged")
                # Saved merge relationship only; no Redis/merger implementation claimed.
                async with service.transaction(TENANT) as store:
                    await store.db.execute(update(m.AnalysisTasks).where(m.AnalysisTasks.id == merged).values(
                        state="merged", merged_into_task_id=root, ended_at=await store.now()))
            await saved_run(await attempt(root), "completed", result=True)
        await accept("alert", "check", "alert_accepted")
        await attempt(await accept("alert", "rerun", "alert_preparing"))
        skipped = await accept("case", "check", "case_skipped")
        async with service.transaction(TENANT) as store:
            await store.skip(skipped, "no_changes")
        retry = await accept("incident", "rerun", "incident_failed", selected=immediate)
        await saved_run(await attempt(retry, immediate), "failed", immediate, retryable=True)
        await saved_run(await attempt(retry, immediate), "unknown", immediate)
        waiting = await accept("incident", "check", "incident_waiting")
        pending = await attempt(waiting)
        async with service.transaction(TENANT) as store:
            await store.finish_attempt(pending["id"], outcome="failed", error_code="connection_refused", retryable=True)

    async def snapshot():
        values = {}
        async with service.transaction(TENANT, readonly=True) as store:
            for model in (m.Alerts, m.Incidents, m.Cases, m.CaseAlerts, m.IncidentAlerts, m.Runs, m.RunMembers,
                          m.Artifacts, m.AlertAssessments, m.IncidentDiagnoses, m.Results,
                          m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState):
                table = model.__table__
                identity = table.c.subject_id if model is m.AnalysisSubjectState else table.c.id
                rows = (await store.db.execute(select(table).where(*store.where(table, identity.in_(ids)))
                    .order_by(identity))).mappings().all()
                values[table.name] = {"count": len(rows), "sha256": hashlib.sha256(
                    json.dumps([dict(row) for row in rows], sort_keys=True, default=str).encode()).hexdigest()}
        return values

    try:
        await fixtures()
        before = await snapshot()
        app.state.business_context = BusinessContext(TENANT, UUID(int=3), "Synthetic task reader")
        app.dependency_overrides[analysis_task_service] = lambda: backend
        app.dependency_overrides[analysis_service] = lambda: StageReadService(sessions)
        app.dependency_overrides[case_service] = lambda: CaseBackend(sessions)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            async def get(url, params=None, status=200):
                response = await client.get(url, params=params)
                assert response.status_code == status, (url, response.status_code, response.text[:1500])
                body = response.json()
                calls.append({"url": str(response.request.url), "status": status, "body": body})
                return body

            found, cursors = {}, {}
            for kind, identity in subjects.items():
                url = f"/api/v1/socai2/{kind}s/{identity}/analysis-tasks"
                page = await get(url)
                AnalysisTaskPage.model_validate(page)
                assert page["total"] == 3 and len(page["items"]) == 2
                cursors[kind] = page["next_cursor"]
                second = await get(url, {"cursor": page["next_cursor"], "limit": 1})
                assert second["total"] == 3 and len(second["items"]) == 1 and second["next_cursor"] is None
                items = page["items"] + second["items"]
                assert len({row['task_id'] for row in items}) == 3
                assert [(row['submitted_at'], row['task_id']) for row in items] == sorted(
                    [(row['submitted_at'], row['task_id']) for row in items], reverse=True)
                for row in items:
                    detail = await get(row["status_url"])
                    AnalysisTaskDetail.model_validate(detail)
                    assert row == detail
                    found[UUID(row["task_id"])] = row
                    assert not {"request_payload", "merged_into_task_id", "effective_request_id"} & row.keys()
                    assert all("id" not in a and "task_id" not in a for a in row["attempts"])
                    for execution in row["attempts"]:
                        if execution["run_url"]:
                            data = await get(execution["run_url"])
                            assert data["run"]["id"] == execution["run_id"]
                    for result in row["results"]:
                        data = await get(result["url"])
                        assert data["result"]["id"] == result["id"]
                        assert data["result"]["source_run_id"] == result["source_run_id"]
                        assert result["kind"] == {"alert": "triage", "incident": "incident_diagnosis", "case": "baseline"}[kind]
                assert page["update_state"]["ineligible_reason"] == {
                    "alert": "not_periodic", "incident": "executor_interrupted", "case": None}[kind]
            by_key = {key: found[value] for key, value in submitted.items()}
            assert by_key['alert_accepted']['status'] == 'accepted' and by_key['alert_accepted']['attempts'] == []
            assert by_key['alert_preparing']['status'] == 'running' and by_key['alert_preparing']['latest_run_id'] is None
            assert by_key['case_skipped']['status'] == 'skipped' and by_key['case_skipped']['reason_code'] == 'no_changes'
            assert by_key['case_merged']['task_id'] != by_key['case_completed']['task_id']
            assert by_key['case_merged']['attempts'] == by_key['case_completed']['attempts']
            assert by_key['case_merged']['results'] == by_key['case_completed']['results']
            failed = by_key['incident_failed']
            assert failed['status'] == 'failed' and failed['retry_count'] == 1 and len(failed['attempts']) == 2
            assert failed['attempts'][-1]['outcome'] == 'unknown' and failed['attempts'][-1]['local_ended_at']
            waiting = by_key['incident_waiting']
            assert waiting['status'] == 'accepted' and waiting['next_retry_at'] and waiting['retry_count'] == 0
            assert waiting['latest_run_id'] is None and waiting['attempts'][0]['run_url'] is None
            case_url = f"/api/v1/socai2/cases/{subjects['case']}/analysis-tasks"
            for bad in ({'limit': 0}, {'limit': 4}, {'cursor': 'broken'}, {'extra': 'yes'},
                        [('limit', '1'), ('limit', '2')], {'cursor': cursors['alert']}):
                await get(case_url, bad, 422)
            await get(case_url + '/' + str(submitted['alert_accepted']), status=404)
            await get(case_url + '/' + str(uuid4()), status=404)
            await get(case_url + '/invalid', status=422)
            await get(case_url + '/' + str(submitted['case_completed']), {'extra': 'yes'}, 422)
            await get(f'/api/v1/socai2/cases/{uuid4()}/analysis-tasks', status=404)
            app.state.business_context = BusinessContext(UUID(int=2), UUID(int=3), 'Other synthetic tenant')
            await get(case_url, status=404)
            app.state.business_context = BusinessContext(TENANT, UUID(int=3), 'Synthetic task reader')
            # Use actual dependency/config loading, not a fake database error.
            app.dependency_overrides.pop(analysis_task_service)
            os.environ.pop('SOCAI2_ANALYSIS_TASKS_CONFIG_FILE', None)
            assert (await get(case_url, status=503))['detail']['code'] == 'service_unavailable'
        after = await snapshot()
        assert before == after
        record('analysis_task_http', True, {'real_pg': True, 'subjects': subjects, 'tasks': submitted,
            'runs': runs, 'results': results, 'http_reads': calls, 'database_before': before, 'database_after': after,
            'merged_relationship': 'explicit synthetic saved merge; no scheduler executed', 'model_calls': 0, 'tool_calls': 0})
    except Exception:  # noqa: BLE001 -- retain exact failed batch instead of rewriting it
        record('analysis_task_http', False, {'trace': traceback.format_exc(), 'http_reads': calls})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = old_context
        if old_policy is None:
            os.environ.pop('SOCAI2_ANALYSIS_TASKS_CONFIG_FILE', None)
        else:
            os.environ['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE'] = old_policy
