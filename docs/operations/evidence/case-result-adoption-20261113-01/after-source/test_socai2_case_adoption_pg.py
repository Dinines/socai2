"""One fixed-result adoption path on explicit local PG; no model executor."""
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.baseline_context import reference
from app.socai2.baseline_contracts import (
    FULL_EXECUTOR_VERSION,
    Publication,
    Scope,
    Start,
)
from app.socai2.baseline_store import RES, A, StoreError
from app.socai2.case_adoption_contracts import (
    ResultAdoptionPreview,
    ResultAdoptionRequest,
)
from app.socai2.case_contracts import CaseCreate, PrepareBaseline
from app.socai2.human_task_contracts import TaskCreate, TaskEdit
from app.socai2.human_task_service import task_view
from app.socai2.runtime_policy import active_policy
from sqlalchemy import insert, select, update


async def exercise(service, tenant, actor, record, *, continuation=None):
    if continuation is None:
        aids, materials = [uuid4(), uuid4()], [uuid4(), uuid4()]
        async with service.transaction(tenant) as store:
            for aid, mid in zip(aids, materials, strict=True):
                await store.db.execute(insert(A).values(id=aid, tenant_id=tenant,
                    source_namespace="synthetic.result-adoption", source_identity_key=str(aid),
                    title="Synthetic fixed-adoption alert", event_time=await store.now(), event_time_source="source"))
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid,
                    revision=1, raw_text="Synthetic observation; authorization not established.",
                    raw_json={"synthetic": True}, detection={}, source_scope={}, retention={}, material_state="complete"))
                await store.db.execute(update(A).where(*store.where(A, A.c.id == aid)).values(latest_material_id=mid))
        created = await service.create_case(tenant, CaseCreate(operation_key=uuid4(),
            title="Synthetic fixed-result adoption", alert_ids=aids), actor=actor)
        cid = created.case_id
        record("fixture", {"case_id": cid, "alert_ids": aids, "material_ids": materials,
                           "run_id": created.pending_run_id, "synthetic_program_results": True})
    else:
        fixture = continuation["fixture"]
        aids = list(map(UUID, fixture["alert_ids"]))
        materials = list(map(UUID, fixture["material_ids"]))
        cid = UUID(fixture["case_id"])
        record("fixture", fixture)
    scope = Scope(kind="whole_case", alert_ids=aids, object_keys=[], window_start=None, window_end=None, limitations=[])

    async def start(rid):
        async with service.transaction(tenant, readonly=True) as store:
            limits = active_policy().case.limits(await store.now(), "synthetic.result-adoption.v1")

        async def idle(_):
            pass  # C1 persistence only; no C2-C6 model or tool execution.

        await service.start(tenant, cid, rid, Start(operation_key=uuid4(), expected_scope_revision=1),
            actor=actor, executor=idle, executor_version=FULL_EXECUTOR_VERSION, limits=limits)

    async def prepare():
        return (await service.prepare_baseline(tenant, cid,
            PrepareBaseline(operation_key=uuid4(), expected_scope_revision=1), actor=actor)).pending_run_id

    async def publish(rid, *, failed_partial=False):
        payload = Publication(operation_key=uuid4(), terminal_state="failed" if failed_partial else "completed",
            stop_reason="synthetic_result_adoption_fixture", title="Synthetic result; not a model quality test",
            conclusion="Synthetic uncertainty: authorization still needs human confirmation.",
            conclusion_state="uncertain", conclusion_origin="model", validation_state="accepted",
            closing_note="Program-supplied test result; no model was called.", findings=[],
            questions=[{"id": "authorization", "text": "Is the activity authorized?", "scope": scope,
                "evidence_requirements": ["Human confirmation"], "state": "unresolved", "answer": None,
                "evidence_refs": [], "limitations": ["Authorization has not been established."]}],
            recommendations=[], change_kind="initial", change_summary=None,
            case_impact={"summary": None, "supported_changes": [], "cannot_generalize": ["Synthetic only."],
                         "affected_scope": scope, "next_steps": []}, delivery_state="partial",
            members=[{"alert_id": aid, "read_state": "read",
                "assessment_state": "not_analyzed" if failed_partial and index else "unresolved",
                "conclusion_covered": not (failed_partial and index), "assessment": None,
                "limitations": "Still needs human confirmation.",
                "evidence_refs": [reference("alert_material", mid, "observation")]}
                for index, (aid, mid) in enumerate(zip(aids, materials, strict=True))])
        out = await service.publish(tenant, cid, rid, payload)
        record("publication-" + str(rid), {"input": payload, "outcome": out})
        return UUID(out["result_id"]), out

    async def refused(code, result_id, request):
        before = await service.read_case(tenant, cid)
        try:
            await service.adopt_result(tenant, cid, result_id, request, actor=actor)
        except StoreError as exc:
            assert exc.code == code, exc.code
        else:
            raise AssertionError("adoption should refuse: " + code)
        assert await service.read_case(tenant, cid) == before
        record(code, {"request": request, "code": code, "case_unchanged": True})

    if continuation is None:
        await start(created.pending_run_id)
        first, published = await publish(created.pending_run_id)
        assert published["adoption"]["state"] == "adopted"
        original_result = await service.read_result(tenant, cid, first)
        initial = await service.preview_result_adoption(tenant, cid, first)
        assert initial.can_adopt and not initial.uncovered_alert_ids
        assert initial.candidate.conclusion_state == "uncertain" and initial.candidate.delivery_state == "partial"
        record("initial-preview", initial)

        failed_run = await prepare()
        await start(failed_run)
        failed_result, _ = await publish(failed_run, failed_partial=True)
        rejected = await service.preview_result_adoption(tenant, cid, failed_result)
        assert {"result_run_not_completed", "result_member_coverage_incomplete"} <= set(rejected.refusal_reasons)
        assert rejected.uncovered_alert_ids == [aids[1]]
        record("failed-partial-preview", rejected)
        await refused("result_run_not_completed", failed_result, ResultAdoptionRequest(
            operation_key=uuid4(), expected_review_token=rejected.review_token, reason="Attempt incomplete result"))

        active_run = await prepare()
        await start(active_run)
        pending_run = await prepare()
        old_preview = await service.preview_result_adoption(tenant, cid, first)
        task = (await service.write(tenant, cid, TaskCreate(operation_key=uuid4(), expected_scope_revision=1,
            title="Confirm the synthetic maintenance authorization"), actor=actor)).task
        await refused("result_adoption_preview_changed", first, ResultAdoptionRequest(
            operation_key=uuid4(), expected_review_token=old_preview.review_token,
            acknowledge_pending_work=True, reason="Previously reviewed before task creation"))

        ready = await service.preview_result_adoption(tenant, cid, first)
        assert ready.can_adopt and len(ready.unfinished_tasks) == 1
        assert {row["state"] for row in ready.unfinished_runs} == {"running", "pending_update"}
        request = ResultAdoptionRequest(operation_key=uuid4(), expected_review_token=ready.review_token,
            reason="Retain the uncertain conclusion while the human task remains open.")
        await refused("result_adoption_pending_work_confirmation_required", first, request)
        request = request.model_copy(update={"acknowledge_pending_work": True})
        record("adoption-preview", ready)
        record("adoption-request", request)
    else:
        # Resume only assertions after the saved, successful adoption. No old
        # Run is restarted and the operation receipt is recovered idempotently.
        ready = ResultAdoptionPreview.model_validate(continuation["adoption-preview"])
        request = ResultAdoptionRequest.model_validate(continuation["adoption-request"])
        first = ready.candidate.id
        original_result = await service.read_result(tenant, cid, first)
        assert original_result["result"] == ready.candidate
        saved = continuation["database"]
        task_row = saved["tasks"][0]
        revision_row = next(row for row in saved["task_revisions"]
                            if row["id"] == task_row["current_revision_id"])
        task = task_view(task_row, revision_row)
        active_run = UUID(next(row["run_id"] for row in ready.unfinished_runs if row["state"] == "running"))
        pending_run = UUID(next(row["run_id"] for row in ready.unfinished_runs if row["state"] == "pending_update"))
        record("continuation", {"source": "pg-02", "already_adopted": True, "no_run_restarted": True})
    adopted = await service.adopt_result(tenant, cid, first, request, actor=actor)
    assert await service.adopt_result(tenant, cid, first, request, actor=actor) == adopted
    await refused("operation_key_conflict", first, request.model_copy(update={"reason": "Different intent"}))
    after = await service.read_case(tenant, cid)
    assert after["case"].handling_status == ready.handling_status
    assert after["case"].current_assessment_id == adopted.assessment_id
    assert after["current_assessment"]["input_freshness"]["state"] == "current"
    assert await service.read(tenant, cid, task.id) == task
    assert await service.read_result(tenant, cid, first) == original_result
    assert {row["run"].id: row["run"].state for row in after["baseline_records"]} == {
        active_run: "running", pending_run: "pending_update"}
    history = await service.read_assessment_history(tenant, cid)
    assert history.total == 2 and [row.id for row in history.items] == [adopted.assessment_id, adopted.previous_assessment_id]
    assert history.items[0].reason == request.reason and history.items[0].adopted_by == actor.user_id
    assert history.items[0].origin == "model" and history.items[0].results[0].id == first
    assert {row["alert_id"] for row in history.items[0].members} == set(aids)
    record("adoption-receipt", adopted)
    record("case-after-adoption", after)
    record("history-after-adoption", history)
    record("result-readback", original_result)
    record("activities-after-adoption", await service.read_activities(tenant, cid))

    _, old_outcome = await publish(active_run)
    assert old_outcome["adoption"]["state"] == "newer_assessment"
    assert (await service.read_case(tenant, cid))["case"].current_assessment_id == adopted.assessment_id
    await start(pending_run)
    newest, new_outcome = await publish(pending_run)
    assert new_outcome["adoption"]["state"] == "adopted"
    assert (await service.read_assessment_history(tenant, cid)).total == 3
    record("automatic-order", {"earlier_run": old_outcome, "later_explicit_run": new_outcome})

    latest_preview = await service.preview_result_adoption(tenant, cid, newest)
    completed = await service.write(tenant, cid, TaskEdit(operation_key=uuid4(), expected_scope_revision=1,
        expected_row_version=task.row_version, title=task.current.title, state="completed",
        result_text="Synthetic operator confirms the authorized test window.", result_scope=scope),
        actor=actor, task_id=task.id)
    stale = await service.preview_result_adoption(tenant, cid, newest)
    assert not stale.can_adopt and "result_input_not_current" in stale.refusal_reasons
    assert "human_feedback_changed" in stale.input_freshness["reasons"]
    await refused("result_adoption_preview_changed", newest, ResultAdoptionRequest(operation_key=uuid4(),
        expected_review_token=latest_preview.review_token, reason="Based on the old feedback version"))
    await refused("result_input_not_current", newest, ResultAdoptionRequest(operation_key=uuid4(),
        expected_review_token=stale.review_token, reason="Attempt stale result"))
    final_case = await service.read_case(tenant, cid)
    assert final_case["current_assessment"]["input_freshness"]["state"] == "stale"
    assert not final_case["baseline_records"]  # Feedback did not schedule another Run.
    assert final_case["case"].current_assessment_id == UUID(new_outcome["adoption"]["assessment_id"])
    assert await service.adopt_result(tenant, cid, first, request, actor=actor) == adopted
    assert await service.read_case(tenant, cid) == final_case  # Old retry cannot restore an older assessment.
    record("human-feedback", completed)
    record("stale-preview", stale)
    record("final-case", final_case)
    async with service.transaction(tenant, readonly=True) as store:
        assert (await store.db.execute(select(RES.c.id).where(*store.where(RES, RES.c.case_id == cid)))).scalars().all()
    return cid
