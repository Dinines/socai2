"""List only Case-owned analysis Runs, without loading full reports."""
from sqlalchemy import and_, cast, select, tuple_
from sqlalchemy.dialects.postgresql import JSONB
from fastapi import HTTPException

from app.models.case import Case
from app.models.investigation import InvestigationArtifact, InvestigationRun
from .case_analysis import PROFILE, analysis_urls
from .case_baseline import history_time
from .pagination import decode_cursor, encode_cursor


async def list_analyses(db, tenant_id, case_id, *, limit=20, cursor=None):
    scope = f"case-history:{tenant_id}:{case_id}"
    after = decode_cursor(cursor, scope)
    exists = (await db.execute(select(Case.id).where(Case.tenant_id == tenant_id, Case.id == case_id))).scalar_one_or_none()
    if exists is None:
        raise HTTPException(404, "case_not_found")
    run, artifact = InvestigationRun, InvestigationArtifact
    content = cast(artifact.content, JSONB)
    query = select(run.id.label("run_id"), run.started_at, run.completed_at, run.status,
        run.created_at.label("requested_at"), history_time().label("history_at"),
        run.investigation_kind, run.scope_revision, run.scope_updated_at,
        run.raw_alert["baseline"].label("baseline"),
        run.raw_alert["scope"].label("scope"), run.raw_alert["previous_run_id"].astext.label("previous_run_id"),
        content["stop_reason"].astext.label("stop_reason"),
        content["completion"].astext.label("completion")).outerjoin(artifact, and_(
            artifact.run_id == run.id, artifact.tenant_id == tenant_id, artifact.kind == "case_analysis_result"))
    query = query.where(run.tenant_id == tenant_id, run.case_id == str(case_id),
                        run.raw_alert["analysis_profile"].astext == PROFILE)
    if after:
        query = query.where(tuple_(history_time(), run.id) < after)
    rows = (await db.execute(query.order_by(history_time().desc(), run.id.desc()).limit(limit + 1))).mappings().all()
    return {"items": [{**row, "case_id": str(case_id), **analysis_urls(case_id, row["run_id"])}
             for row in rows[:limit]],
            "executions_url": f"/api/v2/investigation/executions?case_id={case_id}",
            "next_cursor": encode_cursor(rows[limit - 1].get("history_at") or rows[limit - 1]["started_at"], rows[limit - 1]["run_id"], scope)
            if len(rows) > limit else None}
