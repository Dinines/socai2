"""Read saved evidence and the exact recorded tool exchange, without re-querying."""
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.models.investigation import InvestigationArtifact, InvestigationEvent
from .case_analysis import get_case_run
from .case_navigation import analysis_urls, evidence_index, evidence_url


async def saved_evidence(db, tenant_id, case_id, run_id):
    await get_case_run(db, tenant_id, case_id, run_id)
    artifact = (await db.execute(select(InvestigationArtifact).where(
        InvestigationArtifact.tenant_id == tenant_id, InvestigationArtifact.run_id == run_id,
        InvestigationArtifact.kind == "case_analysis_result",
    ))).scalar_one_or_none()
    if artifact is None:
        raise HTTPException(409, "case_evidence_not_ready")
    return json.loads(artifact.content)


async def list_evidence(db, tenant_id, case_id, run_id):
    result = await saved_evidence(db, tenant_id, case_id, run_id)
    return {"case_id": str(case_id), "run_id": str(run_id),
            "items": evidence_index(case_id, run_id, result), **analysis_urls(case_id, run_id)}


def _find(result, evidence_id):
    item = next((item for item in result.get("evidence", []) if item["evidence_id"] == evidence_id), None)
    if item is None:
        raise HTTPException(404, "case_evidence_not_found")
    return item


async def _tool_trace(db, tenant_id, case_id, run_id, evidence_id):
    # The current loop has at most four Tool calls. These are saved exchanges, not source queries.
    event, artifact = InvestigationEvent, InvestigationArtifact
    rows = (await db.execute(select(event.seq, artifact.content).join(artifact, artifact.event_id == event.id).where(
        event.tenant_id == tenant_id, event.run_id == run_id, event.kind == "case_analysis_tool",
        artifact.tenant_id == tenant_id, artifact.run_id == run_id, artifact.kind == "case_analysis_step",
    ).order_by(event.seq))).mappings().all()
    pending = {}
    base = analysis_urls(case_id, run_id)["steps_url"]
    for row in rows:
        data = json.loads(row["content"])
        call_id = data.get("call_id")
        if call_id and "tool" in data:
            pending[call_id] = row["seq"]
        if data.get("evidence", {}).get("evidence_id") == evidence_id:
            return {"call_id": call_id,
                    "request_step_url": f"{base}/{pending[call_id]}" if call_id in pending else None,
                    "response_step_url": f"{base}/{row['seq']}"}
    return None


async def read_evidence(db, tenant_id, case_id, run_id, evidence_id):
    item = _find(await saved_evidence(db, tenant_id, case_id, run_id), evidence_id)
    links, trace = {}, None
    if item["kind"] == "alert":
        links["source_alert_url"] = f"/api/v1/alerts/{item['data']['alert_id']}"
    elif item["kind"] == "triage" and item.get("event_id"):
        event = (await db.execute(select(InvestigationEvent).where(
            InvestigationEvent.tenant_id == tenant_id, InvestigationEvent.id == UUID(item["event_id"]),
        ))).scalar_one_or_none()
        if event is not None:
            links.update(source_run_url=f"/api/v1/investigations/{event.run_id}",
                         source_events_url=f"/api/v1/investigations/{event.run_id}/events",
                         source_event_id=str(event.id))
    elif item["kind"] == "prior_analysis":
        links["previous_result_url"] = analysis_urls(case_id, item["data"]["run_id"])["result_url"]
    elif item["kind"] == "tool":
        trace = await _tool_trace(db, tenant_id, case_id, run_id, evidence_id)
        if item.get("reused_from"):
            origin = item["reused_from"]
            links["reused_evidence_url"] = evidence_url(case_id, origin["run_id"], origin["evidence_id"])
        source_alert = item.get("source", {}).get("source_alert_id")
        if source_alert:
            links["source_alert_url"] = f"/api/v1/alerts/{source_alert}"
    return {"case_id": str(case_id), "run_id": str(run_id), "evidence": item,
            "detail_url": evidence_url(case_id, run_id, evidence_id), "source_links": links, "tool_trace": trace,
            "query_execution": ("reused" if item.get("reused_from") else "recorded_attempt") if item["kind"] == "tool" else None,
            "rows": [{"index": index, "source_record_id": row.get("event_id") or row.get("device_id"),
                      "url": evidence_url(case_id, run_id, evidence_id, index)} for index, row in enumerate(item.get("rows", []))],
            "notice": "证据正文为该Run已保存材料；来源对象链接读取当前对象，GET不重新执行查询。"}


async def read_evidence_row(db, tenant_id, case_id, run_id, evidence_id, row_index):
    item = _find(await saved_evidence(db, tenant_id, case_id, run_id), evidence_id)
    rows = item.get("rows", [])
    if item["kind"] != "tool" or row_index < 0 or row_index >= len(rows):
        raise HTTPException(404, "case_evidence_row_not_found")
    row = rows[row_index]
    return {"case_id": str(case_id), "run_id": str(run_id), "evidence_id": evidence_id, "row_index": row_index,
            "row": row, "source_record_id": row.get("event_id") or row.get("device_id"),
            "evidence_url": evidence_url(case_id, run_id, evidence_id),
            "provenance": {key: item[key] for key in ("tool", "arguments", "query_id", "query_scope", "source",
                "upstream_request_id", "observed_at", "reused_from", "limitation") if key in item}}
