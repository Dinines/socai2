"""Related story and focused readback on a dedicated synthetic PostgreSQL database."""
import base64
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.models import socai2 as m
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_data_contracts import KIND as EVIDENCE_INDEX_KIND
from app.socai2.case_data_contracts import SCHEMA as EVIDENCE_INDEX_SCHEMA
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.case_story import CaseStoryBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.dependencies import story_service
from investigation_http.main import app
from sqlalchemy import insert, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker


async def add(store, model, *, id=None, **values):
    identity = id or uuid4()
    await store.db.execute(insert(model).values(id=identity, tenant_id=store.tenant_id, **values))
    return identity


async def seed_story(engine, *, first_detection=None, peer_detection=None):
    assert engine.url.host == "127.0.0.1" and engine.url.database.startswith("socai2_story_check")
    tenant, actor, case_id, incident, historical_incident, task, old_revision, new_revision = (uuid4() for _ in range(8))
    first, peer, lacking, outsider = (uuid4() for _ in range(4))
    frozen, pending, cancelled, triage, diagnosis, legacy, unknown = (uuid4() for _ in range(7))
    archived, archived_input, saved_result = (uuid4() for _ in range(3))
    at = datetime(2026, 1, 1, tzinfo=UTC)
    end = at + timedelta(minutes=1)
    stage_inputs = {}
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)

    async def input_artifact(store, run_id, owner, payload, *, artifact_id=None):
        version = payload.get("version", payload.get("schema_version"))
        return await add(store, m.Artifacts, id=artifact_id, run_id=run_id, **owner, kind="input_snapshot",
                         schema_version=version, content_json=payload, sha256=digest(payload),
                         size_bytes=len(encoded(payload)), captured_at=at, mime_type="application/json",
                         material_state="complete", source_refs=[], retention={})

    def frozen_scope(alert):
        return {"kind": "selected_alerts", "alert_ids": [str(alert)], "object_keys": [],
                "window_start": None, "window_end": None, "limitations": []}

    async with service.transaction(tenant) as store:
        await store.db.execute(text(
            "INSERT INTO public.tenants (id,name,slug,plan,is_active,settings,limits,created_at,updated_at) "
            "VALUES (:id,'Story fixture',:slug,'test',true,'{}','{}',now(),now())"
        ), {"id": tenant, "slug": str(tenant)})
        await store.db.execute(text(
            "INSERT INTO public.users (id,tenant_id,email,username,hashed_password,role,is_active,is_verified,"
            "preferences,created_at,updated_at) "
            "VALUES (:id,:tenant,:email,'Fixture','disabled','viewer',false,false,'{}',now(),now())"
        ), {"id": actor, "tenant": tenant, "email": f"{actor}@test.invalid"})
        await add(store, m.Cases, id=case_id, title="Story fixture", scope_revision=1)
        for identity in (incident, historical_incident):
            await add(store, m.Incidents, id=identity, title="Stage fixture", source_namespace="lyc-story",
                      source_incident_id=str(identity))
        await add(store, m.CaseIncidents, case_id=case_id, incident_id=incident, source_operation_id=uuid4())
        for alert, title, severity, when, detection in (
            (first, "searchable marker", "high", at, first_detection),
            (peer, "Peer fact", "low", end, peer_detection),
            (lacking, "Unknown time", "low", None, None), (outsider, "Outside the Case", "high", at, None),
        ):
            await add(store, m.Alerts, id=alert, title=title, severity=severity, source_namespace="lyc-story",
                      source_identity_key=str(alert), event_time=when, event_time_source="source" if when else "unknown")
            if alert == outsider:
                continue
            if alert == first:
                await add(store, m.CaseAlerts, case_id=case_id, alert_id=alert,
                          membership_source="manual", source_operation_id=uuid4())
            if alert == lacking:
                continue
            material = await add(store, m.AlertMaterials, alert_id=alert, revision=1, detection=detection or {},
                                 source_scope={}, material_state="complete", retention={})
            await store.db.execute(update(m.Alerts).where(m.Alerts.id == alert).values(latest_material_id=material))
            for kind, namespace, key, source in (
                ("host", "net", "shared-one", "/object/1"), ("user", "accounts", "shared-two", "/object/2"),
                ("host", "net" if alert == first else "other", "shared-one", "/object/3"),
            ):
                await add(store, m.AlertObjects, alert_id=alert, material_id=material, object_type=kind,
                          object_role="entity", namespace=namespace, object_key=key, raw_value=key,
                          normalized_value=key, source_path=source, attributes={})

        for run_id, final_state in ((frozen, "completed"), (cancelled, "cancelled"), (pending, "pending_update")):
            await add(store, m.Runs, id=run_id, case_id=case_id, kind="baseline", title="Case Run",
                      purpose="Review evidence", trigger="manual", scope_revision=1, scope_kind="whole_case",
                      requested_at=at, state="pending_update")
            await add(store, m.RunMembers, case_id=case_id, run_id=run_id, alert_id=first)
            if final_state == "pending_update":
                continue
            if final_state == "completed":
                artifact = await input_artifact(store, run_id, {"case_id": case_id}, {
                    "schema_version": "socai2.page-model.v1", "run_kind": "baseline",
                    "scope": {**frozen_scope(first), "kind": "whole_case"},
                })
                await store.db.execute(update(m.Runs).where(m.Runs.id == run_id).values(
                    state="running", started_at=at, input_artifact_id=artifact, executor_version="fixture.v1",
                    operation_key=str(uuid4()), request_hash=digest({"run": str(run_id)}),
                ))
            await store.db.execute(update(m.Runs).where(m.Runs.id == run_id).values(state=final_state, ended_at=end))

        for alert in (peer, lacking):
            await add(store, m.CaseAlerts, case_id=case_id, alert_id=alert,
                      membership_source="manual", source_operation_id=uuid4())

        await add(store, m.Runs, id=archived, case_id=case_id, kind="ai_question", title="Archived work",
                  purpose="Saved history", trigger="question", scope_revision=1, scope_kind="selected_alerts",
                  requested_at=at, started_at=at, ended_at=end, state="completed", input_artifact_id=archived_input,
                  executor_version="fixture.v1", operation_key=str(uuid4()), request_hash=digest({"run": str(archived)}))
        await input_artifact(store, archived, {"case_id": case_id},
                             {"schema_version": "fixture.archive.v1"}, artifact_id=archived_input)
        conversation = await add(store, m.Conversations, case_id=case_id, created_by=actor, title="Archived work")
        answer = await add(store, m.Messages, case_id=case_id, conversation_id=conversation, sequence=1,
                           role="assistant", content="Saved response", state="completed", source_run_id=archived,
                           input_artifact_id=archived_input, answered_at=end, source_refs=[], client_request_key=str(uuid4()))
        await add(store, m.Results, id=saved_result, case_id=case_id, kind="ai_saved", source_run_id=archived,
                  source_answer_id=answer, title="Archived result", purpose="Saved history",
                  conclusion_state="unavailable", conclusion_origin="system", validation_state="system_only",
                  closing_note="Stored", findings=[], questions=[], recommendations=[], change_kind="initial",
                  case_impact={"summary": None, "supported_changes": [], "cannot_generalize": [], "next_steps": [],
                               "affected_scope": frozen_scope(first)},
                  input_artifact_id=archived_input, delivery_state="partial", created_at=end, operation_key=str(uuid4()))

        for run_id, kind, owner, frozen_alerts, selection in (
            (triage, "alert_basic", {"alert_id": first}, [first], None),
            (diagnosis, "incident_diagnosis", {"incident_id": historical_incident}, [outsider], "socai2.incident-selection.v1"),
            (legacy, "incident_diagnosis", {"incident_id": incident}, [peer], None),
            (unknown, "incident_diagnosis", {"incident_id": incident}, [first], "unknown-selection"),
        ):
            payload = {"version": "socai2.stage-result.v1", "kind": kind,
                       "parent": {"id": str(owner["incident_id"])} if "incident_id" in owner else None,
                       "members": [{"alert": {"id": str(alert)}} for alert in frozen_alerts]}
            if selection is not None:
                payload.update(selection_version=selection, input_selection={"selected_alert_ids": [str(first)]})
            artifact = uuid4()
            await add(store, m.Runs, id=run_id, **owner, kind=kind, title="Stage Run", purpose="Review evidence",
                      trigger="manual", requested_at=at, state="completed", started_at=at, ended_at=end,
                      input_artifact_id=artifact, executor_version="fixture.v1", operation_key=str(uuid4()),
                      request_hash=digest({"run": str(run_id)}))
            stage_inputs[run_id] = await input_artifact(store, run_id, owner, payload, artifact_id=artifact)

        await add(store, m.Tasks, id=task, case_id=case_id, current_revision_id=new_revision)
        await add(store, m.TaskRevisions, id=old_revision, task_id=task, case_id=case_id, revision=1,
                  title="Completed review", state="completed", changed_by=actor, completed_by=actor,
                  completed_at=end, result_text="Recorded", result_scope=frozen_scope(first), source_refs=[{
                      "type": "artifact", "id": str(stage_inputs[triage]), "external": None,
                      "source_path": None, "row_keys": [], "role": "execution_receipt",
                  }])
        await add(store, m.TaskRevisions, id=new_revision, task_id=task, case_id=case_id, revision=2,
                  title="Later text", state="not_started", changed_by=actor)
        index = {
            "schema_version": EVIDENCE_INDEX_SCHEMA, "scope_revision": 1,
            "alert_ids": list(map(str, (first, peer, lacking))), "supersedes_artifact_id": None,
            "availability_state": "available", "limitations": [], "entries": [{
                "evidence_id": "fixture:invalid-path", "title": "Stored index", "type": "observation",
                "alert_ids": [str(first)], "object_keys": [], "verdict": "unknown", "verdict_sources": [],
                "threat": None, "remediation": None, "state": "active", "source_refs": [{
                    "type": "artifact", "id": str(stage_inputs[unknown]), "external": None,
                    "source_path": "/content_json/nonexistent", "row_keys": [], "role": "execution_receipt",
                }],
            }],
        }
        evidence = await add(store, m.Artifacts, case_id=case_id, kind=EVIDENCE_INDEX_KIND,
                             schema_version=EVIDENCE_INDEX_SCHEMA, content_json=index, sha256=digest(index),
                             size_bytes=len(encoded(index)), captured_at=end, mime_type="application/json",
                             material_state="complete", source_refs=[], retention={})
        await store.db.execute(update(m.Cases).where(m.Cases.id == case_id).values(current_evidence_artifact_id=evidence))

    return SimpleNamespace(
        sessions=sessions, tenant=tenant, actor=actor, case_id=case_id, historical_incident=historical_incident,
        task=task, old_revision=old_revision, first=first, peer=peer, outsider=outsider, at=at, end=end,
        frozen=frozen, pending=pending, cancelled=cancelled, triage=triage, diagnosis=diagnosis, legacy=legacy,
        unknown=unknown, archived=archived, saved_result=saved_result, stage_inputs=stage_inputs,
    )


async def run_checks(engine, record):
    fixture = await seed_story(engine)
    sessions, tenant, actor, case_id = fixture.sessions, fixture.tenant, fixture.actor, fixture.case_id
    first, peer, outsider = fixture.first, fixture.peer, fixture.outsider
    frozen, pending, cancelled = fixture.frozen, fixture.pending, fixture.cancelled
    triage, diagnosis, legacy = fixture.triage, fixture.diagnosis, fixture.legacy
    archived, saved_result = fixture.archived, fixture.saved_result
    historical_incident, task, old_revision = fixture.historical_incident, fixture.task, fixture.old_revision
    at, end = fixture.at, fixture.end
    checks = []
    overrides = dict(app.dependency_overrides)
    prior = getattr(app.state, "business_context", None)
    app.state.business_context = BusinessContext(tenant, actor, "Isolated story checks")
    app.dependency_overrides[story_service] = lambda: CaseStoryBackend(sessions)
    base = f"/api/v1/socai2/cases/{case_id}"

    def run_ids(items):
        return {item["investigation_ref"]["run_id"] for item in items if item["investigation_ref"]}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, code=200, **params):
                response = await client.get(base + path, params=params)
                assert response.status_code == code
                return response.json()

            old = await get("/story", limit=1, severity="high")
            assert set(old) == {"items", "total", "next_cursor", "observed_at"}
            anchor = old["items"][0]
            encoded_old = base64.urlsafe_b64encode(encoded({
                "fingerprint": digest({"tenant": str(tenant), "case": str(case_id), "q": None, "severity": "high"}),
                "at": anchor["occurred_at"], "key": anchor["id"],
            })).decode()
            old_next = await get("/story", limit=1, severity="high", cursor=encoded_old)
            assert old_next["items"][0]["id"] != anchor["id"]
            await get("/story", 422, kind="all")
            checks.append("legacy_envelope_and_cursor")

            all_rows = await get("/story", view="related", focus_alert_id=str(first))
            stats = all_rows["summary"]
            assert (stats["member_alert_count"], stats["member_object_count"], stats["matched_alert_count"]) == (3, 3, 3)
            assert stats["members_without_current_material_count"] == 1 and stats["focus_alert_id"] == str(first)
            assert datetime.fromisoformat(stats["activity_time_from"]) == at
            assert datetime.fromisoformat(stats["activity_time_to"]) == end
            assert run_ids(all_rows["items"]) == set(map(str, (frozen, pending, cancelled, triage, diagnosis, legacy, archived)))
            archive = next(item for item in all_rows["items"] if item["run"] and item["run"]["id"] == str(archived))
            assert [result["id"] for result in archive["results"]] == [str(saved_result)]
            assert archive["investigation_ref"]["result_refs"][0]["url"].endswith(f"/results/{saved_result}")
            assert "frozen_input_membership_unverified" in all_rows["limitations"]
            checks.append("full_case_summary_and_versioned_sources")

            q = await get("/story", view="related", q="searchable marker")
            result = await get("/story", view="related", q="searchable marker", severity="high")
            assert run_ids(q["items"]) == run_ids(result["items"]) == set(map(str, (frozen, triage, diagnosis)))
            [human] = [item for item in result["items"] if item["kind"] == "human_result"]
            assert human["task_revision"]["id"] == str(old_revision) and not human["is_current_task_revision"]
            first_page = await get("/story", view="related", limit=1, severity="high")
            next_page = await get("/story", view="related", limit=1, severity="high", cursor=first_page["next_cursor"])
            assert first_page["total"] == next_page["total"] and first_page["summary"] == next_page["summary"]
            await get("/story", 422, view="related", cursor=encoded_old)
            checks.append("matching_scope_real_members_and_pagination")

            path = f"/members/{first}/relations"
            relations = await get(path, objects_limit=1, runs_limit=1)
            objects, runs = relations["shared_objects"], relations["investigations"]
            assert objects["total"] == 2 and objects["items"][0]["other_alert_count"] == 1
            assert runs["total"] == 3 and runs["next_cursor"]
            continued = await get(path, objects_limit=1, objects_cursor=objects["next_cursor"], runs_limit=1,
                                  runs_cursor=runs["next_cursor"])
            assert continued["shared_objects"]["items"][0]["focus_object_id"] != objects["items"][0]["focus_object_id"]
            assert continued["investigations"]["items"][0]["run_id"] != runs["items"][0]["run_id"]
            peer_rows = await get(f"/members/{peer}/relations")
            assert {item["run_id"] for item in peer_rows["investigations"]["items"]} == {str(legacy)}
            await get(f"/members/{peer}/relations", 422, objects_cursor=objects["next_cursor"])
            await get(f"/members/{outsider}/relations", 404)
            actual = await get(path)
            by_id = {item["run_id"]: item for item in actual["investigations"]["items"]}
            assert set(by_id) == set(map(str, (frozen, triage, diagnosis)))
            assert by_id[str(diagnosis)]["detail_url"].endswith(f"/incidents/{historical_incident}/analysis/runs/{diagnosis}")
            triage_links = by_id[str(triage)]["relations"]
            assert {link["kind"] for link in triage_links} == {"explicit_reference", "frozen_member_overlap"}
            assert any(link["source_url"].endswith(f"/tasks/{task}/revisions/{old_revision}") for link in triage_links)
            checks.append("focused_relations_and_immutable_provenance")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = prior
    record("case_story_related_http", {"state": "passed", "checks": checks})
