"""Thin tenant-scoped adapter for existing attack-chain/graph context.

The API owns projection and the original algorithms. This module only reads
their results and renders bounded, explicitly associative model context.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import httpx

_PARTS = ("attack_chain", "attack_path", "alert_graph")
TENANT_HEADER = "X-AiSOC-Tenant-ID"


def enabled() -> bool:
    return os.getenv("AISOC_ATTACK_CONTEXT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def reader_token(tenant_id: str) -> str | None:
    """An explicit investigation mapping is authoritative, even on a miss."""
    from app.context.organisation_memory import _credential

    for env in ("AISOC_INVESTIGATION_CONTEXT_KEYS_FILE", "AISOC_TRIAGE_IDENTITY_KEYS_FILE"):
        if os.getenv(env, "").strip():
            return _credential(tenant_id, keys_file_env=env)
    # Existing seven-permission service identity is read-only. It is only a
    # reader fallback when no explicit tenant mapping was configured at all.
    return (os.getenv("AISOC_API_SERVICE_TOKEN", "").strip()
            or os.getenv("AISOC_SERVICE_TOKEN", "").strip() or None)


def _text(value: Any, limit: int = 160) -> str:
    from app.investigator.prompt_sanitizer import sanitize_text

    return sanitize_text(str(value), max_len=limit).replace("\n", " ")


def model_summary(context: dict[str, Any]) -> str:
    """Render source facts, not a new attack score or a model verdict."""
    from app.investigator.prompt_sanitizer import sanitize_text, wrap_untrusted

    lines = [
        "Attack correlation context: candidate relationships and graph reachability are not confirmed attack causality or chronology.",
        f"Scope={_text(context.get('scope'))}; case_id={_text(context.get('case_id'))}; alert_id={_text(context.get('alert_id'))}; queried_at={_text(context.get('queried_at'))}.",
        "Empty results apply only to the stated source/query scope. Missing, unavailable or unprojected data remains unknown, not proof of safety. This is a bounded summary; full results stay on this Run.",
    ]
    if context.get("query_scope"):
        lines.append("Query scope and coverage: " + _text(json.dumps(context["query_scope"], ensure_ascii=False), 360))
    prepare = context.get("prepare") or {}
    if prepare:
        lines.append(f"Projection preparation for this Run: {_text(prepare.get('status'))}; owner={_text(prepare.get('owner'))}; source={_text(prepare.get('source'))}; error={_text(prepare.get('error'))}; reason={_text(prepare.get('reason'))}. A missing preparation does not prove no graph exists.")
    # Availability and provenance for every part precede detail, so bounded
    # rendering cannot hide a later source failure behind a long chain.
    for name in _PARTS:
        part = context.get(name) or {}
        lines.append(f"{name}: status={_text(part.get('status'))}; source={_text(part.get('source'))}; error={_text(part.get('error'))}.")
    for name in _PARTS:
        part = context.get(name) or {}
        data = part.get("data") or {}
        query = part.get("query") or {}
        if not isinstance(data, dict):
            continue
        if name == "attack_chain":
            links = data.get("chain") if isinstance(data.get("chain"), list) else []
            lines.append(f"Chain seed={_text(data.get('seed_alert_id'))}; window={_text(query.get('window') or data.get('window'))}; anchor={_text(query.get('anchor') or 'unknown')}; generated_at={_text(data.get('generated_at'))}; candidates={len(links)}. Ranking scores express correlation, not maliciousness probability.")
            for link in links[:5]:
                if not isinstance(link, dict):
                    continue
                shared = link.get("shared_entities") or []
                lines.append(f"Candidate alert_id={_text(link.get('alert_id'))}; event_time={_text(link.get('event_time'))}; score={_text(link.get('score'))}; shared_entities={_text(json.dumps(shared[:4], ensure_ascii=False), 260)}.")
            if len(links) > 5:
                lines.append(f"Chain summary shows first 5 of {len(links)} ranked candidates; full result is retained on this Run.")
        elif name == "attack_path":
            nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else []
            edges = data.get("edges") if isinstance(data.get("edges"), list) else []
            lines.append(f"Case path: nodes={data.get('node_count', len(nodes))}; edges={data.get('edge_count', len(edges))}. Case membership and technique associations alone do not establish an observed attack progression.")
            for node in [row for row in nodes if isinstance(row, dict) and row.get("label") == "IOC"][:3]:
                if not isinstance(node, dict):
                    continue
                props = node.get("properties") or {}
                if node.get("label") == "IOC" and isinstance(props, dict):
                    value = props.get("indicator_value") or props.get("value")
                    lines.append(f"IOC graph node id={_text(node.get('id'), 110)}; indicator_value={_text(value)}. The node id is an internal identifier, not the indicator value.")
            for edge in edges[:5]:
                if isinstance(edge, dict):
                    lines.append(f"Graph association: {_text(edge.get('source') or edge.get('from'), 110)} --{_text(edge.get('type') or edge.get('kind'), 60)}--> {_text(edge.get('target') or edge.get('to'), 110)}.")
        else:
            neighbors = data.get("neighbors") or {}
            blast = data.get("blast_radius") or {}
            if isinstance(neighbors, dict):
                rows = neighbors.get("neighbors") or neighbors.get("nodes") or []
                lines.append(f"Alert neighborhood: returned_nodes={len(rows) if isinstance(rows, list) else 'unknown'}.")
            if isinstance(blast, dict):
                lines.append(f"Alert blast radius: reachable={_text(blast.get('total_affected'))}; score={_text(blast.get('blast_radius_score'))}. This is alert-associated graph scope, not a Case attack path.")
    return wrap_untrusted(sanitize_text("\n".join(lines), max_len=4200), label="attack_correlation_context")


def _unavailable(tenant_id: str, case_id: str | None, alert_id: str | None, reason: str) -> dict[str, Any]:
    result = {
        "tenant_id": tenant_id, "case_id": case_id, "alert_id": alert_id,
        "scope": "case" if case_id else "alert" if alert_id else "none",
        "queried_at": datetime.now(UTC).isoformat(),
        **{name: {"status": "unavailable", "source": "api.graph.investigation-context", "data": None, "error": reason} for name in _PARTS},
    }
    if not case_id:
        result["attack_path"].update(status="not_linked", error="No real Case was supplied; no Case was created.")
    result["model_summary"] = model_summary(result)
    return result


async def prepare_alert_graph(tenant_id: str, alert_id: str) -> dict[str, Any]:
    """Prepare one broker Alert using an independent writer, never a reader."""
    from app.context.organisation_memory import _credential

    receipt: dict[str, Any] = {"tenant_id": tenant_id, "alert_id": alert_id,
        "scope": "alert", "owner": "kafka_consumer", "status": "unavailable"}
    if not enabled():
        return {**receipt, "status": "disabled", "reason": "attack_context_disabled"}
    if not tenant_id or not alert_id:
        return {**receipt, "reason": "missing_explicit_target"}
    writer = _credential(tenant_id, keys_file_env="AISOC_INVESTIGATION_PREPARE_KEYS_FILE")
    if not writer:
        return {**receipt, "status": "not_configured", "reason": "tenant_projection_writer_not_configured"}
    read_identities = {reader_token(tenant_id), os.getenv("AISOC_API_SERVICE_TOKEN", "").strip(),
                       os.getenv("AISOC_SERVICE_TOKEN", "").strip()}
    if writer in read_identities:
        return {**receipt, "reason": "projection_writer_is_read_identity"}
    url = os.getenv("API_SERVICE_URL", "http://api:8000").rstrip("/") + "/api/v1/graph/investigation-context"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json={"alert_id": alert_id},
                headers={"Authorization": f"Bearer {writer}", TENANT_HEADER: tenant_id})
        receipt["http_status"] = response.status_code
        if not response.is_success:
            return {**receipt, "reason": "projection_request_refused"}
        body = response.json()
        projection = body.get("projection") if isinstance(body, dict) else None
        if (not isinstance(projection, dict) or str(body.get("tenant_id")) != tenant_id
                or str(body.get("alert_id")) != alert_id
                or str(projection.get("tenant_id")) != tenant_id
                or str(projection.get("alert_id")) != alert_id or projection.get("scope") != "alert"
                or projection.get("status") not in {"success", "partial", "unavailable", "error"}
                or (projection.get("status") == "success"
                    and (not isinstance(projection.get("source_alert_ids"), list)
                         or alert_id not in projection["source_alert_ids"]))):
            return {**receipt, "reason": "invalid_projection_response"}
        return {**receipt, **deepcopy(projection), "owner": "kafka_consumer"}
    except (ValueError, TypeError, httpx.HTTPError) as exc:
        return {**receipt, "reason": type(exc).__name__}


async def fetch_attack_context(
    tenant_id: str, *, case_id: str | None = None, alert_id: str | None = None,
) -> dict[str, Any]:
    """Read the explicit Case or Alert; preparation belongs to its entry point."""
    if not enabled():
        return {}
    case_id = str(case_id) if case_id else None
    alert_id = str(alert_id) if alert_id and not case_id else None
    if not tenant_id or not (case_id or alert_id):
        return _unavailable(tenant_id, case_id, alert_id, "missing_explicit_target")
    token = reader_token(tenant_id)
    if not token:
        return _unavailable(tenant_id, case_id, alert_id, "tenant_reader_not_configured")
    target = {"case_id": case_id} if case_id else {"alert_id": alert_id}
    url = os.getenv("API_SERVICE_URL", "http://api:8000").rstrip("/") + "/api/v1/graph/investigation-context"
    headers = {"Authorization": f"Bearer {token}", TENANT_HEADER: tenant_id}
    prepare: dict[str, Any] = {"status": "not_provided", "reason": "No entry preparation receipt supplied; this context GET did not write the graph."}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=target, headers=headers)
    except httpx.HTTPError as exc:
        result = _unavailable(tenant_id, case_id, alert_id, type(exc).__name__)
        result["prepare"] = prepare
        result["model_summary"] = model_summary(result)
        return result
    if response.status_code != 200:
        result = _unavailable(tenant_id, case_id, alert_id, f"read_http_{response.status_code}")
    else:
        try:
            result = response.json()
            if (not isinstance(result, dict) or str(result.get("tenant_id")) != tenant_id
                    or result.get("scope") != ("case" if case_id else "alert")
                    or (case_id and str(result.get("case_id")) != case_id)
                    or (alert_id and str(result.get("alert_id")) != alert_id)
                    or any(not isinstance(result.get(name), dict)
                           or result[name].get("status") not in {"success", "empty", "unavailable", "error", "not_linked", "not_applicable", "partial"}
                           or (result[name].get("data") is not None and not isinstance(result[name]["data"], dict))
                           for name in _PARTS)):
                raise ValueError("invalid attack context identity or shape")
            result = deepcopy(result)
        except (ValueError, TypeError):
            result = _unavailable(tenant_id, case_id, alert_id, "invalid_response")
    result["prepare"] = prepare
    result["model_summary"] = model_summary(result)
    return result


def attack_context_artifacts(bundle_dict: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Existing ledger artifact kinds, each carrying this Run's exact summary."""
    context = (bundle_dict or {}).get("attack_context")
    if not isinstance(context, dict) or not context:
        return []
    common = {key: deepcopy(context.get(key)) for key in ("tenant_id", "case_id", "alert_id", "scope", "queried_at", "prepare", "model_summary")}
    return [(name, json.dumps({**common, name: context.get(name)}, ensure_ascii=False, sort_keys=True))
            for name in _PARTS if isinstance(context.get(name), dict)]
