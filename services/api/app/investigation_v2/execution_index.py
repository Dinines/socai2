"""Shared execution discovery; legacy rows retain their original ledger reader."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, and_, cast, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import JSONB, array

from app.api.v1.deps import CurrentUser, require_permission
from app.db.rls import TenantDBSession
from app.models.alert import Alert
from app.models.case import Case
from app.models.investigation import InvestigationArtifact, InvestigationRun
from .case_analysis import PROFILE
from .case_navigation import analysis_urls
from .pagination import decode_cursor, encode_cursor
from .result_api import _explicit_bearer

router = APIRouter(prefix="/api/v2/investigation/executions", tags=["investigation-executions"])


def _query(tenant_id):
    run, artifact = InvestigationRun, InvestigationArtifact
    content = cast(artifact.content, JSONB)
    return select(run.id.label("run_id"), run.case_id.label("recorded_case_reference"), run.status,
        run.started_at, run.completed_at, run.raw_alert["analysis_profile"].astext.label("profile"),
        run.raw_alert["id"].astext.label("source_alert_id"), run.raw_alert["scope"].label("scope"),
        run.raw_alert["previous_run_id"].astext.label("previous_run_id"),
        artifact.id.is_not(None).label("result_available"), content["completion"].astext.label("completion"),
        content["stop_reason"].astext.label("stop_reason"),
        func.left(content["report"]["summary"].astext, 800).label("summary"),
        (func.length(content["report"]["summary"].astext) > 800).label("summary_truncated"),
    ).outerjoin(artifact, and_(artifact.tenant_id == tenant_id, artifact.run_id == run.id,
                              artifact.kind == "case_analysis_result")).where(run.tenant_id == tenant_id)


def _entry(row, member_ids=None):
    current = row["profile"] == PROFILE
    run_id, case_id = str(row["run_id"]), row["recorded_case_reference"] if current else None
    members = (row["scope"] or {}).get("selected_member_ids", []) if current else [row["source_alert_id"]]
    urls = analysis_urls(case_id, run_id) if current else {
        "result_url": f"/api/v1/investigations/{run_id}", "steps_url": f"/api/v1/investigations/{run_id}/events",
        "artifacts_url": f"/api/v1/investigations/{run_id}/artifacts", "report_url": None, "evidence_url": None,
        "execution_url": f"/api/v2/investigation/executions/{run_id}"}
    return {"run_id": run_id, "case_id": case_id, "run_type": "case_analysis" if current else "legacy_or_other",
            "profile": row["profile"], "native_reader": "case_analysis" if current else "legacy_ledger",
            "status": row["status"], "started_at": row["started_at"], "completed_at": row["completed_at"],
            "scope": row["scope"] if current else None, "source_alert_id": row["source_alert_id"],
            "previous_run_id": row["previous_run_id"] if current else None,
            "previous_result_url": analysis_urls(case_id, row["previous_run_id"])["result_url"]
                                   if current and row["previous_run_id"] else None,
            "matched_member_ids": sorted(set(members) & set(member_ids)) if member_ids is not None else None,
            **{key: row[key] if current else None for key in
               ("result_available", "completion", "stop_reason", "summary", "summary_truncated")}, **urls,
            "notice": None if current else "沿用原账本读取；旧case_id不推定为真实Case归属，结果完整度及细分类型未知。"}


async def list_executions(db, tenant_id, *, alert_id=None, incident_id=None, case_id=None, limit=20, cursor=None):
    chosen = [(kind, identity) for kind, identity in (("alert", alert_id), ("incident", incident_id), ("case", case_id))
              if identity is not None]
    if len(chosen) != 1:
        raise HTTPException(422, "exactly_one_execution_filter_required")
    kind, identity = chosen[0]
    scope = f"execution-index:{tenant_id}:{kind}:{identity}"
    after = decode_cursor(cursor, scope)
    if kind == "case":
        case = (await db.execute(select(Case).where(Case.tenant_id == tenant_id, Case.id == identity))).scalar_one_or_none()
        if case is None:
            raise HTTPException(404, "case_not_found")
        members = list(map(str, case.alert_ids or []))
    else:
        condition = (Alert.id == identity if kind == "alert" else
                     Alert.enrichment_data["socai2_fusion"]["incident_id"].astext == str(identity))
        members = list(map(str, (await db.execute(select(Alert.id).where(Alert.tenant_id == tenant_id, condition))).scalars().all()))
        if not members:
            raise HTTPException(404, f"{kind}_not_found")
    run = InvestigationRun
    profile = run.raw_alert["analysis_profile"].astext
    current_scope = run.case_id == str(case_id) if kind == "case" else run.raw_alert["scope"]["selected_member_ids"].has_any(array(members, type_=Text))
    query = _query(tenant_id).where(or_(and_(profile == PROFILE, current_scope),
        and_(or_(profile.is_(None), profile != PROFILE), run.raw_alert["id"].astext.in_(members))))
    if after:
        query = query.where(tuple_(run.started_at, run.id) < after)
    rows = (await db.execute(query.order_by(run.started_at.desc(), run.id.desc()).limit(limit + 1))).mappings().all()
    return {"source": {"type": kind, "id": str(identity), "current_member_ids": sorted(set(members))},
            "items": [_entry(row, members) for row in rows[:limit]],
            "next_cursor": encode_cursor(rows[limit - 1]["started_at"], rows[limit - 1]["run_id"], scope) if len(rows) > limit else None,
            "notice": "Case筛选按新版Run的Case归属；旧记录只按当前成员的明确来源告警关联，不表示其历史Case归属。"}


@router.get("")
async def executions(db: TenantDBSession,
                     _credential: Annotated[None, Depends(_explicit_bearer)],
                     user: Annotated[CurrentUser, Depends(require_permission("cases:read"))],
                     alert_id: UUID | None = None, incident_id: UUID | None = None, case_id: UUID | None = None,
                     limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None):
    user.require_permission("alerts:read")
    return await list_executions(db, user.tenant_id, alert_id=alert_id, incident_id=incident_id, case_id=case_id,
                                 limit=limit, cursor=cursor)


@router.get("/{run_id}")
async def execution(run_id: UUID, db: TenantDBSession,
                    _credential: Annotated[None, Depends(_explicit_bearer)],
                    user: Annotated[CurrentUser, Depends(require_permission("cases:read"))]):
    user.require_permission("alerts:read")
    row = (await db.execute(_query(user.tenant_id).where(InvestigationRun.id == run_id))).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "investigation_execution_not_found")
    return _entry(row)
