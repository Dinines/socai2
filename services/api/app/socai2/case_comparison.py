"""Select once before execution; all Case projections read the saved decision."""
from uuid import UUID

from sqlalchemy import exists, or_, select

from .analysis_task_store import A
from .baseline_contracts import Scope
from .baseline_model_view import blocked, field_limit
from .baseline_store import RES, F, R, digest, encoded


async def select_previous(store, case_id, member_ids):
    ended_attempt = exists(select(A.c.id).where(*store.where(A,
        A.c.run_id == R.c.id, A.c.local_state.in_(["ended", "interrupted"]))))
    prior = await store.one(select(R).where(*store.where(R, R.c.case_id == case_id,
        R.c.kind == "baseline", R.c.scope_kind == "whole_case", R.c.started_at.is_not(None),
        R.c.input_artifact_id.is_not(None), or_(R.c.state.in_(["completed", "failed"]),
            (R.c.state == "unknown") & ended_attempt)))
        .order_by(R.c.started_at.desc(), R.c.id.desc()).limit(1))
    meta = {"previous_run_id": str(prior["id"]) if prior else None,
            "comparison_result_id": None, "state": "initial" if prior is None else "unavailable", "reason_code": None}
    if prior is None:
        return meta
    result = await store.one(select(RES).where(*store.where(RES, RES.c.case_id == case_id,
        RES.c.source_run_id == prior["id"], RES.c.kind == "baseline"))
        .order_by(RES.c.saved_at.desc(), RES.c.id.desc()).limit(1))
    if result is None:
        return {**meta, "reason_code": "previous_result_unavailable"}
    value = {key: result[key] for key in ("conclusion", "conclusion_state", "conclusion_origin", "validation_state", "delivery_state")}
    if (result["validation_state"] != "accepted" or result["conclusion_state"] == "unavailable"
            or not result["conclusion"] or blocked(value) or len(encoded(value)) > field_limit()):
        return {**meta, "reason_code": "previous_conclusion_unusable"}
    original = await store.one(select(F).where(*store.where(F, F.c.case_id == case_id,
        F.c.run_id == prior["id"], F.c.id == result["input_artifact_id"])))
    if not original or not original["content_json"] or digest(original["content_json"]) != original["sha256"]:
        return {**meta, "reason_code": "previous_input_unavailable"}
    try:
        original_scope = Scope.model_validate(original["content_json"]["scope"])
    except (KeyError, TypeError, ValueError):
        return {**meta, "reason_code": "previous_scope_unavailable"}
    if not set(map(str, original_scope.alert_ids)) & set(map(str, member_ids)):
        return {**meta, "reason_code": "previous_scope_not_overlapping"}
    return {**meta, "comparison_result_id": str(result["id"]), "state": "eligible"}


async def frozen(store, input_artifact_id):
    if input_artifact_id is None:
        return None
    value = await store.one(select(F.c.content_json["comparison_context"].label("comparison_context"))
        .where(*store.where(F, F.c.id == input_artifact_id, F.c.kind == "input_snapshot")))
    return value["comparison_context"] if value else None


async def project_comparison(store, model, row):
    from .case_contracts import CaseComparison, project
    value = await frozen(store, row["input_artifact_id"])
    if value is not None:
        parsed = CaseComparison.model_validate(value)
        if parsed.comparison_result_id != (UUID(str(row["comparison_result_id"])) if row["comparison_result_id"] else None):
            from .baseline_store import StoreError
            raise StoreError("case_comparison_reference_mismatch")
        return project(model, row).model_copy(update={"comparison_context": parsed})
    return project(model, row)
