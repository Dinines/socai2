"""Explicit adoption of saved whole-case conclusions; no model or Run execution."""
from uuid import uuid4

from sqlalchemy import func, insert, select, update

from app.models import socai2 as m

from .baseline_store import RES, RESM, RM, C, R, StoreError, digest
from .case_adoption_contracts import (
    AdoptedAssessment,
    AssessmentHistory,
    ResultAdoptionPreview,
    ResultAdoptionReceipt,
)
from .case_contracts import ResultView, RunView, project

ASSESS, SOURCES, COVER = (m.CaseAssessments.__table__, m.CaseAssessmentSources.__table__,
                         m.CaseAssessmentMembers.__table__)
TASK, REVISION = m.Tasks.__table__, m.TaskRevisions.__table__
ACTION = "case_result_adopted"


async def rows(store, statement):
    return [dict(row) for row in (await store.db.execute(statement)).mappings()]


async def assessment_view(store, case_id, assessment):
    aid = assessment["id"]
    sources = await rows(store, select(SOURCES.c.result_id, SOURCES.c.task_revision_id,
        SOURCES.c.artifact_id).where(*store.where(SOURCES, SOURCES.c.case_id == case_id,
        SOURCES.c.assessment_id == aid)).order_by(SOURCES.c.id))
    members = await rows(store, select(COVER.c.alert_id, COVER.c.coverage_note).where(*store.where(
        COVER, COVER.c.case_id == case_id, COVER.c.assessment_id == aid)).order_by(COVER.c.alert_id))
    results = await rows(store, select(RES).where(*store.where(RES, RES.c.case_id == case_id,
        RES.c.id.in_([s["result_id"] for s in sources if s["result_id"]]))).order_by(RES.c.id))
    return AdoptedAssessment(**{k: assessment[k] for k in AdoptedAssessment.model_fields
        if k not in {"sources", "members", "results"}}, sources=sources, members=members,
        results=[project(ResultView, row) for row in results])


async def preview(store, case, result_id):
    cid = case["id"]
    result = await store.one(select(RES).where(*store.where(RES, RES.c.case_id == cid, RES.c.id == result_id)))
    if result is None:
        raise StoreError("case_result_not_found", 404)
    run = await store.one(select(R).where(*store.where(R, R.c.case_id == cid, R.c.id == result["source_run_id"])))
    if run is None:
        raise StoreError("result_run_link_invalid")
    current = None
    if case["current_assessment_id"]:
        assessment = await store.one(select(ASSESS).where(*store.where(ASSESS,
            ASSESS.c.case_id == cid, ASSESS.c.id == case["current_assessment_id"])))
        if assessment is None:
            raise StoreError("current_assessment_reference_invalid")
        current = await assessment_view(store, cid, assessment)
    members = await rows(store, select(RESM.c.alert_id, RESM.c.assessment_state,
        RESM.c.conclusion_covered, RESM.c.assessment, RESM.c.limitations).where(*store.where(
        RESM, RESM.c.case_id == cid, RESM.c.result_id == result_id)).order_by(RESM.c.alert_id))
    promised = set((await store.db.execute(select(RM.c.alert_id).where(*store.where(
        RM, RM.c.case_id == cid, RM.c.run_id == run["id"])))).scalars())
    actual = await store.members(cid)
    delivered = {row["alert_id"] for row in members}
    covered = {row["alert_id"] for row in members
               if row["conclusion_covered"] and row["assessment_state"] in {"analyzed", "unresolved"}}
    tasks = await rows(store, select(TASK.c.id.label("task_id"), REVISION.c.id.label("revision_id"),
        REVISION.c.title, REVISION.c.state).join(REVISION,
            (REVISION.c.tenant_id == TASK.c.tenant_id) & (REVISION.c.case_id == TASK.c.case_id)
            & (REVISION.c.task_id == TASK.c.id) & (REVISION.c.id == TASK.c.current_revision_id))
        .where(*store.where(TASK, TASK.c.case_id == cid),
               REVISION.c.state.in_(["not_started", "in_progress"])).order_by(TASK.c.id))
    runs = await rows(store, select(R.c.id.label("run_id"), R.c.kind, R.c.state, R.c.row_version)
        .where(*store.where(R, R.c.case_id == cid,
            R.c.state.in_(["pending_update", "running", "unknown"]))).order_by(R.c.id))
    freshness = (await store.input_freshness(run["id"]) if run["kind"] == "baseline"
                 else {"state": "unverified", "reasons": ["not_baseline_result"]})
    reasons = []
    if case["handling_status"] == "resolved":
        reasons.append("case_reopen_required")
    if result["kind"] != "baseline" or run["kind"] != "baseline" or run["scope_kind"] != "whole_case":
        reasons.append("result_not_whole_case_baseline")
    if run["state"] != "completed":
        reasons.append("result_run_not_completed")
    if (result["validation_state"] != "accepted" or result["conclusion_origin"] != "model"
            or result["conclusion_state"] == "unavailable" or not (result["conclusion"] or "").strip()):
        reasons.append("result_conclusion_not_eligible")
    if run["scope_revision"] != case["scope_revision"] or promised != actual:
        reasons.append("result_scope_not_current")
    if not actual or delivered != actual or covered != actual:
        reasons.append("result_member_coverage_incomplete")
    if freshness["state"] != "current":
        reasons.append("result_input_not_current")
    value = ResultAdoptionPreview(case_id=cid, case_row_version=case["row_version"],
        scope_revision=case["scope_revision"], handling_status=case["handling_status"],
        review_token="0" * 64, current_assessment=current, candidate=project(ResultView, result),
        source_run=project(RunView, run), current_alert_ids=sorted(actual), members=members,
        uncovered_alert_ids=sorted(actual - covered), outside_alert_ids=sorted(delivered - actual),
        input_freshness=freshness, unfinished_tasks=tasks, unfinished_runs=runs,
        requires_pending_work_acknowledgement=bool(tasks or runs), can_adopt=not reasons, refusal_reasons=reasons)
    return value.model_copy(update={"review_token": digest(value.model_dump(mode="json", exclude={"review_token"}))})


async def read_preview(service, tenant_id, case_id, result_id):
    async with service.transaction(tenant_id, readonly=True) as store:
        return await preview(store, await store.case(case_id, lock=False), result_id)


async def adopt(service, tenant_id, case_id, result_id, request, actor):
    intent = digest({"case_id": str(case_id), "result_id": str(result_id), "actor": str(actor.user_id),
                     "request": request.model_dump(mode="json")})
    async with service.transaction(tenant_id) as store:
        await service.actor(store, actor)
        case = await store.case(case_id)
        prior = await store.receipt(case_id, request.operation_key, ACTION)
        if prior:
            if prior["request_hash"] != intent:
                raise StoreError("operation_key_conflict")
            return ResultAdoptionReceipt.model_validate(prior["outcome"])
        checked = await preview(store, case, result_id)
        if checked.review_token != request.expected_review_token:
            raise StoreError("result_adoption_preview_changed")
        if not checked.can_adopt:
            raise StoreError(checked.refusal_reasons[0])
        if checked.requires_pending_work_acknowledgement and not request.acknowledge_pending_work:
            raise StoreError("result_adoption_pending_work_confirmation_required")
        revision = (await store.db.execute(select(func.coalesce(func.max(ASSESS.c.revision), 0)).where(
            *store.where(ASSESS, ASSESS.c.case_id == case_id)))).scalar_one() + 1
        aid, now = uuid4(), await store.now()
        await store.db.execute(insert(ASSESS).values(id=aid, tenant_id=tenant_id, case_id=case_id,
            revision=revision, conclusion=checked.candidate.conclusion, origin=checked.candidate.conclusion_origin,
            validity=checked.candidate.validation_state, scope_revision=case["scope_revision"],
            formed_at=checked.candidate.created_at, adopted_at=now, adopted_by=actor.user_id,
            actor=actor.snapshot(), reason=request.reason,
            operation_key=f"manual-adopt:{case_id}:{request.operation_key}"))
        await store.db.execute(insert(SOURCES).values(id=uuid4(), tenant_id=tenant_id,
            case_id=case_id, assessment_id=aid, result_id=result_id))
        for member in checked.members:
            await store.db.execute(insert(COVER).values(id=uuid4(), tenant_id=tenant_id, case_id=case_id,
                assessment_id=aid, alert_id=member["alert_id"], coverage_note=member["limitations"]))
        await store.db.execute(update(C).where(*store.where(C, C.c.id == case_id)).values(
            current_assessment_id=aid, row_version=C.c.row_version + 1, business_updated_at=now))
        out = ResultAdoptionReceipt(case_id=case_id, result_id=result_id, assessment_id=aid,
            previous_assessment_id=case["current_assessment_id"], assessment_revision=revision,
            case_row_version=case["row_version"] + 1)
        await store.event(case_id, request.operation_key, actor.snapshot(), ACTION,
            {"request_hash": intent, "outcome": out.model_dump(mode="json"), "reason": request.reason,
             "review_token": checked.review_token, "acknowledge_pending_work": request.acknowledge_pending_work,
             "unfinished_tasks": checked.model_dump(mode="json")["unfinished_tasks"],
             "unfinished_runs": checked.model_dump(mode="json")["unfinished_runs"]},
            [("case_id", case_id, {"current_assessment_id": str(case["current_assessment_id"])
                if case["current_assessment_id"] else None}, {"current_assessment_id": str(aid)}),
             ("result_id", result_id, None, {"adopted_assessment_id": str(aid)})])
        return out


async def read_history(service, tenant_id, case_id, *, limit=20, offset=0):
    if not 1 <= limit <= 100 or offset < 0:
        raise StoreError("invalid_assessment_history_page", 422)
    async with service.transaction(tenant_id, readonly=True) as store:
        await store.case(case_id, lock=False)
        where = store.where(ASSESS, ASSESS.c.case_id == case_id)
        count = (await store.db.execute(select(func.count()).select_from(ASSESS).where(*where))).scalar_one()
        selected = await rows(store, select(ASSESS).where(*where)
            .order_by(ASSESS.c.revision.desc()).offset(offset).limit(limit))
        return AssessmentHistory(items=[await assessment_view(store, case_id, row) for row in selected],
            total=count, next_offset=offset + limit if offset + limit < count else None)
