"""Read Case membership and Runs whose fixed selection covers source alerts."""
from sqlalchemy import Text, and_, cast, func, select, tuple_
from sqlalchemy.dialects.postgresql import JSONB, array
from uuid import UUID

from app.models.case import Case
from app.models.investigation import InvestigationArtifact, InvestigationRun
from .case_analysis import PROFILE, analysis_urls
from .case_baseline import history_time
from .pagination import decode_cursor, encode_cursor


async def read_related(db, tenant_id, member_ids, *, subject, limit=20, cursor=None):
    ids = sorted(set(map(str, member_ids)))
    scope = f"related-investigations:{tenant_id}:{subject}"
    after = decode_cursor(cursor, scope)
    cases = (await db.execute(select(Case.id, Case.title, Case.status, Case.alert_ids).where(
        Case.tenant_id == tenant_id, Case.alert_ids.overlap(member_ids),
    ).order_by(Case.updated_at.desc(), Case.id.desc()).limit(51))).all()
    run, artifact = InvestigationRun, InvestigationArtifact
    selected = run.raw_alert["scope"]["selected_member_ids"]
    filters = (run.tenant_id == tenant_id, run.raw_alert["analysis_profile"].astext == PROFILE,
               selected.has_any(array(ids, type_=Text)))
    content = cast(artifact.content, JSONB)
    query = select(run.id.label("run_id"), run.case_id, run.status, run.started_at, run.completed_at,
        history_time().label("history_at"), run.created_at.label("requested_at"),
        run.investigation_kind, run.scope_revision, run.scope_updated_at,
        run.raw_alert["baseline"].label("baseline"),
        run.raw_alert["scope"].label("scope"), run.raw_alert["previous_run_id"].astext.label("previous_run_id"),
        run.raw_alert["source_incident_ids"].label("source_incident_ids"),
        artifact.id.is_not(None).label("result_available"),
        content["stop_reason"].astext.label("stop_reason"), content["completion"].astext.label("completion"),
        func.left(content["report"]["summary"].astext, 800).label("summary"),
        (func.length(content["report"]["summary"].astext) > 800).label("summary_truncated"),
    ).outerjoin(artifact, and_(artifact.run_id == run.id, artifact.tenant_id == tenant_id,
                              artifact.kind == "case_analysis_result")).where(*filters)
    if after:
        query = query.where(tuple_(history_time(), run.id) < after)
    rows = (await db.execute(query.order_by(history_time().desc(), run.id.desc()).limit(limit + 1))).mappings().all()
    # Coverage is across matching Runs, not just the displayed history page.
    selected_rows = select(func.jsonb_array_elements_text(selected).label("member_id")).where(*filters).subquery()
    covered = set((await db.execute(select(selected_rows.c.member_id).where(
        selected_rows.c.member_id.in_(ids)).distinct())).scalars().all())
    return {
        "cases": [{"case_id": str(case.id), "title": case.title, "status": case.status,
                   "member_ids": sorted(set(map(str, case.alert_ids or [])) & set(ids)),
                   "case_url": f"/api/v1/cases/{case.id}",
                   "investigations_url": f"/api/v2/investigation/cases/{case.id}/investigations"}
                  for case in cases[:50]],
        "cases_truncated": len(cases) > 50,
        "items": [{**row, "run_id": str(row["run_id"]),
                   "matched_member_ids": sorted(set(row["scope"]["selected_member_ids"]) & set(ids)),
                   "matched_read_member_ids": sorted(set(row["scope"].get("read_member_ids", [])) & set(ids)),
                   **analysis_urls(row["case_id"], row["run_id"])} for row in rows[:limit]],
        "next_cursor": encode_cursor(rows[limit - 1].get("history_at") or rows[limit - 1]["started_at"], rows[limit - 1]["run_id"], scope)
                       if len(rows) > limit else None,
        "member_ids_with_runs": sorted(covered), "member_ids_without_runs": sorted(set(ids) - covered),
        "coverage_notice": "有Run表示已有调查执行或待更新记录；待更新不表示已经分析，须查看实际开始、结束和结果。",
    }


async def attach_related(db, overview):
    related = await read_related(db, overview.tenant_id, [member.alert_id for member in overview.members],
                                 subject=f"incident:{overview.incident_id}")
    updated = [value for item in related["items"] for value in (item["started_at"], item["completed_at"]) if value]
    if overview.source_updated_at is not None:
        updated.append(overview.source_updated_at)
    return overview.model_copy(update={"investigations": related,
                                       "members": [member.model_copy(update={"case_ids": [UUID(item["case_id"]) for item in related["cases"]
                                           if str(member.alert_id) in item["member_ids"]], "case_ids_truncated": related["cases_truncated"]}) for member in overview.members],
                                       "source_updated_at": max(updated) if updated else None})
