"""Direct history GET checks against the isolated synthetic Story fixture."""
from datetime import timedelta
from uuid import uuid4

from app.models import socai2 as m
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import digest, encoded
from app.socai2.stage_inputs import VERSION as STAGE_INPUT_VERSION
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.case_investigations import CaseInvestigationBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.dependencies import case_investigation_history_service
from investigation_http.main import app
from sqlalchemy import insert, select, update
from test_socai2_case_story_related_pg import add, seed_story


async def history_records(fixture):
    case_id, at, end = fixture.case_id, fixture.at, fixture.end
    async with BaselineService(fixture.sessions).transaction(fixture.tenant) as store:
        async def snapshot(run_id, identity, payload, **owner):
            await add(store, m.Artifacts, id=identity, run_id=run_id, kind="input_snapshot", **owner,
                      schema_version=payload.get("version", payload.get("schema_version")), content_json=payload,
                      sha256=digest(payload), size_bytes=len(encoded(payload)), captured_at=at,
                      mime_type="application/json", material_state="complete", source_refs=[], retention={})

        other_case = await add(store, m.Cases, title="Other fixture", scope_revision=1)
        saved_table = m.Results.__table__
        saved = dict(await store.one(select(saved_table).where(*store.where(
            saved_table, saved_table.c.id == fixture.saved_result,
        ))))
        saved.pop("id")
        saved.pop("tenant_id")
        later = saved["saved_at"] + timedelta(seconds=1)
        archived_new = await add(store, m.Results, **{
            **saved, "closing_note": "  System disclosure.  ", "supersedes_result_id": fixture.saved_result,
            "operation_key": str(uuid4()), "saved_at": later,
        })
        input_id = await store.db.scalar(select(m.Runs.input_artifact_id).where(m.Runs.id == fixture.frozen))
        baseline = {
            **saved, "kind": "baseline", "source_run_id": fixture.frozen, "source_answer_id": None,
            "input_artifact_id": input_id, "conclusion": "  Original conclusion.  ",
            "conclusion_state": "supported",
        }
        primary = await add(store, m.Results, **{**baseline, "operation_key": str(uuid4())})
        revision = await add(store, m.Results, **{
            **baseline, "conclusion": "Later revision.", "supersedes_result_id": primary,
            "operation_key": str(uuid4()), "saved_at": later,
        })
        empty, empty_input, failed, failed_input, fallback_input = (uuid4() for _ in range(5))
        await add(store, m.Runs, id=empty, case_id=case_id, kind="ai_question", state="completed",
                  title="History fixture", purpose="Verify saved history", trigger="question", scope_revision=1,
                  scope_kind="selected_alerts", requested_at=at, started_at=at, ended_at=at,
                  input_artifact_id=empty_input, executor_version="fixture", operation_key=str(uuid4()),
                  request_hash=digest({"run": str(empty)}))
        await snapshot(empty, empty_input, {
            "schema_version": "socai2.page-model.v1", "run_kind": "ai_question", "scope": {"alert_ids": []},
        }, case_id=case_id)
        await add(store, m.Runs, id=failed, incident_id=fixture.historical_incident, kind="incident_diagnosis",
                  state="failed", title="History fixture", purpose="Verify failed history", trigger="manual",
                  requested_at=at, started_at=at, ended_at=end, input_artifact_id=failed_input,
                  executor_version="fixture", operation_key=str(uuid4()), request_hash=digest({"run": str(failed)}))
        await snapshot(failed, failed_input, {
            "version": STAGE_INPUT_VERSION, "kind": "incident_diagnosis",
            "parent": {"id": str(fixture.historical_incident)}, "members": [{"alert": {"id": str(fixture.first)}}],
        }, incident_id=fixture.historical_incident)
        revision_number = await store.db.scalar(select(m.Cases.scope_revision).where(m.Cases.id == case_id))
        members = (await store.db.execute(select(m.CaseAlerts.alert_id).where(m.CaseAlerts.case_id == case_id))).scalars()
        member_ids = list(members)
        fallback_run = fixture.pending
        for member in set(member_ids) - {fixture.first}:
            await add(store, m.RunMembers, case_id=case_id, run_id=fallback_run, alert_id=member)
        await snapshot(fallback_run, fallback_input, {
            "schema_version": "socai2.page-model.v1", "run_kind": "baseline",
            "scope": {"kind": "whole_case", "alert_ids": list(map(str, member_ids))},
        }, case_id=case_id)
        await store.db.execute(update(m.Runs).where(m.Runs.id == fallback_run).values(
            state="running", scope_revision=revision_number, started_at=at,
            input_artifact_id=fallback_input, executor_version="fixture",
            operation_key=str(uuid4()), request_hash=digest({"run": str(fallback_run)}),
        ))
        await store.db.execute(update(m.Runs).where(m.Runs.id == fallback_run).values(state="completed", ended_at=end))
        pending = await add(store, m.Runs, case_id=case_id, kind="baseline", state="pending_update",
                            title="History fixture", purpose="Verify planned members", trigger="manual",
                            scope_revision=revision_number, scope_kind="whole_case", requested_at=at)
        await add(store, m.RunMembers, case_id=case_id, run_id=pending, alert_id=fixture.first)
        fallback_id, earlier_id = sorted((uuid4(), uuid4()), reverse=True)
        for identity, supersedes in ((earlier_id, revision), (fallback_id, earlier_id)):
            await add(store, m.Results, id=identity, **{
                **baseline, "source_run_id": fallback_run, "input_artifact_id": fallback_input,
                "supersedes_result_id": supersedes, "operation_key": str(uuid4()), "saved_at": later,
            })

        conversation = await add(store, m.Conversations, case_id=case_id, created_by=fixture.actor, title="Fixture")
        answer = await add(store, m.Messages, case_id=case_id, conversation_id=conversation, sequence=1,
                           role="assistant", content="Saved answer.", state="completed", source_run_id=empty,
                           input_artifact_id=empty_input, answered_at=end, source_refs=[],
                           client_request_key=str(uuid4()))
        await add(store, m.Results, **{
            **saved, "source_run_id": empty, "source_answer_id": answer, "input_artifact_id": empty_input,
            "operation_key": str(uuid4()), "saved_at": later,
        })
        triage = await add(store, m.AlertAssessments, alert_id=fixture.first, kind="triage",
                           source_run_id=fixture.triage, rationale="Saved triage.", producer="fixture",
                           actor={}, assessed_at=end, operation_key=str(uuid4()))
        diagnosis = await add(store, m.IncidentDiagnoses, incident_id=fixture.historical_incident,
                              source_run_id=fixture.diagnosis, revision=1, state="completed",
                              summary="Saved diagnosis.", diagnosis={"validation_state": "accepted"},
                              input_artifact_id=fixture.stage_inputs[fixture.diagnosis],
                              source_fingerprint=digest({"run": str(fixture.diagnosis)}),
                              producer="fixture", requested_at=at, generated_at=end)

        def step(seq, kind, state, **fields):
            return {"id": uuid4(), "tenant_id": fixture.tenant, "run_id": fixture.frozen, "seq": seq,
                    "stage_code": "C2", "name": "Fixture step", "kind": kind, "state": state, **fields}

        await store.db.execute(insert(m.RunSteps), [
            step(1, "tool", "planned"), step(2, "tool", "skipped"), step(3, "tool", "completed"),
            *[step(seq, "stage", "completed") for seq in range(4, 1002)],
        ])
        await store.db.execute(insert(m.RunSteps), [
            step(1002, "model", "completed", usage={"usage_state": "reported", "total_tokens": 17}),
            step(1003, "model", "failed", usage={"usage_state": "unavailable"}),
            step(1004, "model", "skipped", usage={"usage_state": "reported", "total_tokens": 31}),
            step(1005, "model", "planned", usage={"usage_state": "reported", "total_tokens": 37}),
        ])
    return other_case, primary, revision, archived_new, empty, failed, pending, fallback_id, triage, diagnosis


async def run_checks(engine, record):
    fixture = await seed_story(engine)
    other_case, primary, revision, archived_new, empty, failed, pending, fallback_id, triage, diagnosis = (
        await history_records(fixture)
    )
    ids = (fixture.frozen, fixture.pending, fixture.cancelled, fixture.triage, fixture.diagnosis, fixture.legacy,
           fixture.archived, empty, failed, pending)
    expected = sorted(map(str, ids), reverse=True)
    prefix = "/api/v1/socai2"
    directory = f"{prefix}/cases/{fixture.case_id}/investigations"
    other = f"{prefix}/cases/{other_case}/investigations"
    overrides = dict(app.dependency_overrides)
    previous = getattr(app.state, "business_context", None)
    app.state.business_context = BusinessContext(
        tenant_id=fixture.tenant, user_id=fixture.actor, email="Fixture reader",
    )
    app.dependency_overrides[case_investigation_history_service] = lambda: CaseInvestigationBackend(fixture.sessions)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, *, params=None, status=200):
                response = await client.get(path, params=params)
                assert response.status_code == status
                return response.json()

            first = await get(directory, params={"limit": 1})
            second = await get(directory, params={"cursor": first["next_cursor"]})
            assert first["total"] == second["total"] == len(expected)
            assert second["next_cursor"] is None
            items = first["items"] + second["items"]
            assert [item["run_id"] for item in items] == expected
            assert (await get(f"{directory}/{expected[-1]}"))["item"] == items[-1]
            assert (await get(f"{other}/{expected[-1]}", status=404))["detail"]["code"] == "run_not_found"
            assert (await get(f"{directory}/{fixture.unknown}", status=404))["detail"]["code"] == "run_not_found"
            assert (await get(other, params={"cursor": first["next_cursor"]}, status=422))["detail"]["code"] == "invalid_cursor"
            assert (await get(other))["items"] == []

            cards = {item["run_id"]: item for item in items}
            card = cards[str(fixture.frozen)]
            assert card["input_member_count"] == 1 and card["duration_seconds"] == 60
            assert card["tool_record_count"] == 3
            assert card["usage"] == {"model_calls": 2, "total_tokens": None, "known_total_tokens": 17,
                                     "unknown_token_calls": 1}
            assert card["preview"] == {
                "result_id": str(primary), "result_type": "case_result", "kind": "baseline",
                "source_field": "conclusion", "text": "  Original conclusion.  ",
            }
            assert {ref["id"] for ref in card["result_refs"]} == {str(primary), str(revision)}
            archived = cards[str(fixture.archived)]
            assert archived["input_member_count"] is None
            assert archived["preview"] == {
                "result_id": str(archived_new), "result_type": "case_result", "kind": "ai_saved",
                "source_field": "closing_note", "text": "  System disclosure.  ",
            }
            assert cards[str(empty)]["input_member_count"] == 0 and cards[str(empty)]["duration_seconds"] == 0
            fallback = cards[str(fixture.pending)]
            assert fallback["run_kind"] == "baseline" and fallback["preview"]["kind"] == "baseline"
            assert fallback["preview"]["result_id"] == str(fallback_id)
            assert cards[str(pending)]["duration_seconds"] is None
            assert cards[str(pending)]["input_member_count"] is None
            assert cards[str(failed)]["state"] == "failed" and cards[str(failed)]["preview"] is None
            assert cards[str(failed)]["result_refs"] == []
            assert "frozen_input_membership_unverified" in first["limitations"]

            for run_id, subject, source_field, result_id in (
                (fixture.triage, "alert", "rationale", triage),
                (fixture.diagnosis, "incident", "summary", diagnosis),
            ):
                stage = cards[str(run_id)]
                preview = stage["preview"]
                assert stage["subject_type"] == subject and stage["input_member_count"] == 1
                assert preview["result_id"] == str(result_id) and preview["source_field"] == source_field
                assert stage["result_refs"][0]["url"] == stage["detail_url"]
                assert set(stage["relations"][0]) == {"kind", "source_type", "source_id", "source_url"}
            assert len(cards[str(fixture.triage)]["relations"]) >= 2
    finally:
        app.state.business_context = previous
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
    record("case_investigation_history_http", {
        "state": "passed",
        "checks": ["case_scope_keyset_exact", "same_run_previews_and_refs", "all_saved_steps_and_usage",
                   "verified_frozen_scope_and_times"],
    })
