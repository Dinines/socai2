"""Tenant-owned investigation targets and reads of the existing ledger."""
from __future__ import annotations

import hashlib
import html
import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.investigator import ledger
from app.security.tenant_scope import TenantPrincipal


async def require_owned_target(target_id: str | UUID, tenant_id: UUID, *, case_only: bool = False) -> UUID:
    """Validate a Case, or a persisted Alert/Fusion incident, before starting work."""
    try:
        target = UUID(str(target_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Investigation target must be a UUID") from exc
    pool = await ledger.get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Investigation ledger unavailable")
    async with pool.acquire() as conn:
        owned = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM aisoc_cases WHERE id=$1 AND tenant_id=$2)", target, tenant_id,
        )
        if not owned and not case_only:
            owned = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM alerts WHERE tenant_id=$2 AND "
                "(id=$1 OR enrichment_data->'socai2_fusion'->>'incident_id'=$3))",
                target, tenant_id, str(target),
            )
    if not owned:
        raise HTTPException(status_code=404, detail="Case not found" if case_only else "Investigation target not found")
    return target


def _json(value: Any) -> Any:
    try:
        return json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Persisted investigation material invalid") from exc


def _scalar(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


async def read_persisted_run(run_id: str, principal: TenantPrincipal) -> dict[str, Any]:
    """Read only rows explicitly owned by the credential; never relaunch work.

    Graph results stay separate from the original triage event and Run totals.
    Legacy pipelines persisted Markdown only; an escaped literal HTML view of
    that same document keeps cold report reads safe without another model call.
    """
    try:
        run_uuid = UUID(run_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Investigation run not found") from exc
    tenants = sorted(principal.tenant_ids, key=str)
    if not tenants:
        raise HTTPException(status_code=404, detail="Investigation run not found")
    pool = await ledger.get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Investigation ledger unavailable")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id,tenant_id,case_id,status,error,started_at,completed_at,iterations,total_tokens,"
            "total_cost_usd,measured_call_count,estimated_cost_usd,estimated_call_count,unpriced_call_count "
            "FROM investigation_runs WHERE id=$1 AND tenant_id=ANY($2::uuid[])", run_uuid, tenants,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Investigation run not found")
        tenant_id = row["tenant_id"]
        events = await conn.fetch(
            "SELECT seq,kind,agent,summary,payload,ts FROM investigation_events "
            "WHERE run_id=$1 AND tenant_id=$2 ORDER BY seq", run_uuid, tenant_id,
        )
        artifacts = await conn.fetch(
            "SELECT DISTINCT ON (kind) kind,content,sha256,size_bytes FROM investigation_artifacts "
            "WHERE run_id=$1 AND tenant_id=$2 AND kind=ANY($3::text[]) "
            "ORDER BY kind,created_at DESC,id DESC", run_uuid, tenant_id,
            ["report_md", "report_html", "graph_result"],
        )
    result = {k: _scalar(v) for k, v in dict(row).items()}
    result["run_id"] = result.pop("id")
    # NUMERIC zero with no priced calls is absence of a measured dollar value.
    for field, counter in [("total_cost_usd", "measured_call_count"), ("estimated_cost_usd", "estimated_call_count")]:
        result[field] = float(row[field]) if row[counter] else None
    result["audit_log"] = [{k: _scalar(_json(v) if k == "payload" else v) for k, v in dict(e).items()} for e in events]
    for artifact in artifacts:
        content = artifact["content"]
        if not isinstance(content, str):
            raise HTTPException(status_code=503, detail="Persisted investigation material unavailable")
        encoded = content.encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != artifact["sha256"] or len(encoded) != artifact["size_bytes"]:
            raise HTTPException(status_code=503, detail="Persisted investigation material differs")
        if artifact["kind"] == "graph_result":
            state = _json(content)
            if not isinstance(state, dict) or state.get("run_id") != str(run_uuid) or state.get("tenant_id") != str(tenant_id):
                raise HTTPException(status_code=503, detail="Persisted graph identity differs")
            result["result"] = state
        else:
            result[artifact["kind"]] = content
    graph_events = [_json(e["payload"]) for e in events if e["kind"] == "graph_result"]
    if graph_events:
        if not isinstance(graph_events[-1], dict):
            raise HTTPException(status_code=503, detail="Persisted graph result invalid")
        result["investigation_completion"] = graph_events[-1].get("completion")
    if result["status"] == "failed" and not result.get("error"):
        state = result.get("result", {})
        status = state.get("status", "failed")
        result["error"] = state.get("error") or state.get("budget_exhausted_reason") or (
            f"Investigation returned {status}; partial result."
        )
    if result.get("report_md") and not result.get("report_html"):
        result["report_html"] = (
            '<!doctype html><html><head><meta charset="utf-8"><title>Investigation report</title></head>'
            '<body><pre style="white-space:pre-wrap">' + html.escape(result["report_md"]) + '</pre></body></html>'
        )
        result["report_html_source"] = "escaped_persisted_markdown"
    result["source"] = "investigation_ledger"
    return result
