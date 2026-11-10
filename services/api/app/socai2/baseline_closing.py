"""Every investigation leaves an explicit, source-labelled closing statement."""
from typing import Literal
from uuid import uuid4, uuid5

from sqlalchemy import func, insert, select, update

from app.models import socai2 as models

from .baseline_contracts import Publication


class InterruptedReport(Publication):
    """Artifact-only closing; never supplied to Result publication."""
    terminal_state: None
    run_state: Literal["unknown"]
    delivery_state: Literal["none"]
    closing_state: Literal["saved"]
    closing_delivery_state: Literal["partial"]
    closing_reason: Literal["investigation_execution_uncertain"]


def statement(member_count):
    # Business conclusion only. Technical causes belong to Run.stop_reason,
    # RunSteps.error and the immutable execution receipts, never this field.
    return (f"案件性质待核实。本案涉及 {member_count} 条告警，"
        "当前调查尚不足以确认行为性质和影响范围，需继续核查。")


async def record_case_closing(store, run, source_id, conclusion, *, source_kind="result"):
    """Fill an otherwise empty Case, never replace a model/human assessment.

    A system closing is explicitly system_only and asserts no analyzed-member
    coverage. The same scope/freshness protections as adoption still apply.
    """
    case = await store.case(run["case_id"])
    assessments, sources = models.CaseAssessments.__table__, models.CaseAssessmentSources.__table__
    if source_kind not in {"result", "artifact"}:
        raise ValueError("invalid closing source")
    key = "baseline-closing:" + str(source_id)
    prior = await store.one(select(assessments).where(*store.where(assessments, assessments.c.operation_key == key)))
    if prior:
        return {"state": "system_closing_saved", "assessment_id": str(prior["id"])}
    current = await store.one(select(assessments).where(*store.where(assessments,
        assessments.c.id == case["current_assessment_id"]))) if case["current_assessment_id"] else None
    if current and (current["origin"] != "system" or current["validity"] != "system_only"):
        return {"state": "existing_judgment_preserved", "assessment_id": str(current["id"])}
    if case["scope_revision"] != run["scope_revision"]:
        return {"state": "stale_scope"}
    freshness = await store.input_freshness(run["id"])
    if freshness["state"] != "current":
        return {"state": "stale_input", "input_freshness": freshness}
    if current and current["adopted_at"] >= run["started_at"]:
        return {"state": "newer_assessment"}
    revision = (await store.db.execute(select(func.coalesce(func.max(assessments.c.revision), 0) + 1)
        .where(*store.where(assessments, assessments.c.case_id == run["case_id"])))).scalar_one()
    identity, now = uuid4(), await store.now()
    actor = {"type": "service", "user_id": None, "name_snapshot": "调查系统收尾",
        "service_name": "socai2.baseline-closing", "service_version": "v1"}
    await store.db.execute(insert(assessments).values(id=identity, tenant_id=store.tenant_id,
        case_id=run["case_id"], revision=revision, conclusion=conclusion, origin="system", validity="system_only",
        scope_revision=run["scope_revision"], formed_at=now, adopted_at=now, actor=actor, operation_key=key,
        reason="执行收尾，非有效模型安全定性；不声明成员已分析覆盖"))
    await store.db.execute(insert(sources).values(id=uuid4(), tenant_id=store.tenant_id,
        case_id=run["case_id"], assessment_id=identity, **{source_kind + "_id": source_id}, source_note="C6 system closing"))
    cases = models.Cases.__table__
    await store.db.execute(update(cases).where(*store.where(cases, cases.c.id == run["case_id"])).values(
        current_assessment_id=identity, row_version=cases.c.row_version + 1, business_updated_at=now))
    await store.event(run["case_id"], uuid5(source_id, "case-closing"), actor, "baseline_system_closing_saved",
        {source_kind + "_id": str(source_id), "assessment_id": str(identity), "validity": "system_only"},
        [("case_id", run["case_id"], {"current_assessment_id": str(case["current_assessment_id"]) if case["current_assessment_id"] else None},
            {"current_assessment_id": str(identity)})])
    return {"state": "system_closing_saved", "assessment_id": str(identity)}


def interrupted_report(publication, run):
    """An artifact is not a terminal Result; retain the actual unsettled Run."""
    if run["state"] != "unknown" or run["ended_at"] is not None:
        raise ValueError("interrupted_report_requires_unsettled_run")
    return InterruptedReport.model_validate({**publication.model_dump(mode="json"), "terminal_state": None,
        "run_state": run["state"], "delivery_state": run["delivery_state"],
        "stop_reason": run["stop_reason"], "closing_state": "saved",
        "closing_delivery_state": "partial", "closing_reason": "investigation_execution_uncertain"}).model_dump(mode="json")


async def interrupted(service, tenant_id, case_id, run_id):
    """Persist C6 system closure without pretending an uncertain call finished."""
    from .baseline_context import reference
    from .baseline_delivery import BaselineDelivery
    from .baseline_delivery_contract import SCHEMA
    from .baseline_delivery_projection import make_publication, markdown
    from .baseline_store import RES, RM

    executor, steps_table = BaselineDelivery(service), models.RunSteps.__table__
    async with service.transaction(tenant_id) as store:
        await store.case(case_id)
        run = await store.run(case_id, run_id)
        if run["state"] not in {"running", "unknown"} or await store.one(select(RES.c.id)
                .where(*store.where(RES, RES.c.source_run_id == run_id)).limit(1)):
            return
        await store.mark_unknown(case_id, run_id)
        run = await store.run(case_id, run_id)
        context, now = await store.read_context(case_id, run_id), await store.now()
        c6 = await store.one(select(steps_table).where(*store.where(steps_table,
            steps_table.c.run_id == run_id, steps_table.c.stage_code == "C6", steps_table.c.kind == "stage")))
        if c6 and c6["state"] == "completed":
            return
        stage_id = c6["id"] if c6 else uuid4()
        if not c6:
            await store.db.execute(insert(steps_table).values(id=stage_id, tenant_id=tenant_id, run_id=run_id,
                seq=await executor.seq(store, run_id), kind="stage", stage_code="C6", name="system_closing",
                state="running", implementation_version=SCHEMA, started_at=now, input_artifact_id=run["input_artifact_id"]))
        members = (await store.db.execute(select(RM).where(*store.where(RM, RM.c.run_id == run_id)))).mappings().all()
        comparison = {"state": "not_comparable" if run["comparison_result_id"] else "initial",
            "result_id": str(run["comparison_result_id"]) if run["comparison_result_id"] else None,
            "added_alert_ids": [], "removed_alert_ids": [], "shared_alert_ids": []}
        prepared = {"input_artifact_ids": [str(run["input_artifact_id"])], "source_map": {}}
        graph = {"delivery_state": "partial", "graph_artifact_id": None}
        reason = "investigation_execution_uncertain"
        publication, limitations = make_publication(None, context, {m["alert_id"]: m for m in members},
            prepared, comparison, graph, uuid5(run_id, "socai2-C6-interrupted-closing-v1"), reason)
        report_id, summary_id = uuid4(), uuid4()
        publication = publication.model_copy(update={"report_artifact_id": report_id})
        report_data = interrupted_report(publication, run)
        steps = (await store.db.execute(select(steps_table).where(*store.where(steps_table,
            steps_table.c.run_id == run_id)).order_by(steps_table.c.seq))).mappings().all()
        report = {"schema_version": SCHEMA, "type": "delivery_report", "run_id": str(run_id),
            "result_id": None, "result": report_data, "delivery": None,
            "scope": context.scope.model_dump(mode="json"), "source_map": {}, "comparison": comparison,
            "input_artifact_ids": prepared["input_artifact_ids"], "domain_artifact_ids": {},
            "execution": {"run_state": run["state"], "delivery_state": run["delivery_state"],
                "model_calls": sum(s["kind"] == "model" and s["state"] not in {"planned", "skipped"} for s in steps),
                "tool_calls": sum(s["kind"] == "tool" and s["state"] not in {"planned", "skipped"} for s in steps),
                "total_tokens": None, "usage_state": "unknown", "followup_dispatch": None,
                "steps": [{"id": str(s["id"]), "kind": s["kind"], "stage_code": s["stage_code"],
                    "state": "completed" if s["id"] == stage_id else s["state"]} for s in steps]},
            "limitations": limitations + ["unsettled_calls_remain_unknown_no_automatic_retry"], "captured_at": now.isoformat()}
        refs = [reference("artifact", run["input_artifact_id"], "execution_receipt")]
        detail_id = await executor.save(store, run, stage_id, report, "source_snapshot", refs)
        await store.save_input_artifact(case_id, run_id, report_id, report_data,
            kind="report_json", schema=SCHEMA, captured_at=now, refs=refs, actor_id=run["requested_by"], step_id=stage_id)
        text_id = await executor.save_markdown(store, run, stage_id, markdown(report), report_id, detail_id)
        await store.db.execute(update(steps_table).where(*store.where(steps_table, steps_table.c.id == stage_id))
            .values(state="completed", ended_at=now, output_artifact_id=summary_id,
                error={"code": reason, "message": reason, "retryable": False, "occurred_at": now.isoformat()}))
        # A Result requires a terminal Run in the existing database contract.
        # An unresolved call remains unknown; retain its closing as an artifact
        # and link the Case directly to that artifact without inventing a Result.
        adoption = await record_case_closing(store, run, report_id, publication.conclusion, source_kind="artifact")
        outcome = {"run_id": str(run_id), "result_id": None, "adoption": adoption}
        summary = {"schema_version": SCHEMA, "type": "delivery_receipt", "run_id": str(run_id),
            "state": "completed", "reason": reason, "delivery_state": run["delivery_state"], "outcome": outcome,
            "run_state": run["state"], "closing_state": "saved", "closing_delivery_state": "partial",
            "report_artifact_id": str(report_id), "detail_artifact_id": str(detail_id),
            "markdown_artifact_id": str(text_id), "domain_artifact_ids": {}, "captured_at": now.isoformat()}
        await store.save_input_artifact(case_id, run_id, summary_id, summary, kind="source_snapshot", schema=SCHEMA,
            captured_at=now, refs=refs, actor_id=run["requested_by"], step_id=stage_id)
