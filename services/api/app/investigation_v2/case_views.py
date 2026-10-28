"""Case investigation materials, recorded steps and saved Markdown delivery."""
import json

from fastapi import HTTPException
from sqlalchemy import select

from app.models.investigation import InvestigationArtifact, InvestigationEvent
from .case_analysis import LIMITS, case_context, get_case_run
from .case_analysis_tools import CaseTools


async def preview_analysis(db, tenant_id, case_id, request):
    context = await case_context(db, tenant_id, case_id, request)
    tools = await CaseTools.for_context(db, tenant_id, context, request.start, request.end)
    return {"context": context, "tools": tools.schemas(), "limits": LIMITS,
            "missing_member_ids": sorted(set(context["selected_member_ids"]) - set(context["read_member_ids"])),
            "notice": "本次为当前材料预览；启动调查时重新读取并固定范围，不执行模型或查询。"}


async def list_steps(db, tenant_id, case_id, run_id, *, after_seq=0, limit=20):
    await get_case_run(db, tenant_id, case_id, run_id)
    rows = list((await db.execute(select(InvestigationEvent).where(
        InvestigationEvent.tenant_id == tenant_id, InvestigationEvent.run_id == run_id,
        InvestigationEvent.seq > after_seq,
    ).order_by(InvestigationEvent.seq).limit(limit + 1))).scalars().all())
    base = f"/api/v2/investigation/cases/{case_id}/investigations/{run_id}"
    return {"items": [{"event_id": str(event.id), "seq": event.seq, "kind": event.kind,
                       "recorded_at": event.ts, "summary": event.summary,
                       "detail_url": f"{base}/steps/{event.seq}"} for event in rows[:limit]],
            "next_after_seq": rows[limit - 1].seq if len(rows) > limit else None}


async def read_step(db, tenant_id, case_id, run_id, seq):
    await get_case_run(db, tenant_id, case_id, run_id)
    event = (await db.execute(select(InvestigationEvent).where(
        InvestigationEvent.tenant_id == tenant_id, InvestigationEvent.run_id == run_id,
        InvestigationEvent.seq == seq,
    ))).scalar_one_or_none()
    if event is None:
        raise HTTPException(404, "case_analysis_step_not_found")
    artifact = (await db.execute(select(InvestigationArtifact).where(
        InvestigationArtifact.tenant_id == tenant_id, InvestigationArtifact.run_id == run_id,
        InvestigationArtifact.event_id == event.id, InvestigationArtifact.kind == "case_analysis_step",
    ))).scalar_one_or_none()
    return {"run_id": str(run_id), "case_id": str(case_id), "event_id": str(event.id),
            "seq": event.seq, "kind": event.kind, "recorded_at": event.ts, "summary": event.summary,
            "data": json.loads(artifact.content) if artifact else None}


async def saved_report(db, tenant_id, case_id, run_id):
    await get_case_run(db, tenant_id, case_id, run_id)
    artifact = (await db.execute(select(InvestigationArtifact).where(
        InvestigationArtifact.tenant_id == tenant_id, InvestigationArtifact.run_id == run_id,
        InvestigationArtifact.kind == "case_analysis_markdown",
    ))).scalar_one_or_none()
    if artifact is None:
        raise HTTPException(409, "case_report_not_ready")
    return artifact.content
