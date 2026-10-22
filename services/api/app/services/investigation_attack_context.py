"""Bounded, tenant-owned alert/Case context for an investigation.

Preparation is an explicit write. Reading recomputes the original PG chain
without its HTTP endpoint's cache write, and never creates graph nodes.
Graph edges describe what the source alert reported, not verified causality.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text

from app.services import graph_service
from app.services.attack_chain import PostgresAttackChainLoader, compute_attack_chain

WINDOWS = {"1h": timedelta(hours=1), "6h": timedelta(hours=6), "24h": timedelta(hours=24),
           "72h": timedelta(hours=72), "7d": timedelta(days=7), "30d": timedelta(days=30)}
ALERT_LIMIT = 50
ENTITY_LIMIT = 20


def enabled() -> bool:
    import os
    return os.getenv("AISOC_ATTACK_CONTEXT_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


async def _rows(db: Any, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (await db.execute(text(sql), params)).mappings().all()]


async def _anchor(db: Any, tenant_id: Any, case_id: Any = None, alert_id: Any = None) -> dict[str, Any]:
    tenant = str(uuid.UUID(str(tenant_id)))
    cid = str(uuid.UUID(str(case_id))) if case_id else None
    aid = str(uuid.UUID(str(alert_id))) if alert_id else None
    if not cid and not aid:
        raise HTTPException(422, "case_id or alert_id is required")
    alert = None
    if aid:
        rows = await _rows(db, "SELECT * FROM alerts WHERE id = CAST(:id AS UUID) AND tenant_id = CAST(:tenant AS UUID)", id=aid, tenant=tenant)
        if not rows:
            raise HTTPException(404, "alert_not_found")
        alert = rows[0]
    ambiguous = False
    if aid and not cid:
        cases = await _rows(db, "SELECT * FROM aisoc_cases WHERE tenant_id = CAST(:tenant AS UUID) "
                            "AND (CAST(:id AS UUID) = ANY(alert_ids) OR id = CAST(:linked AS UUID)) ORDER BY id LIMIT 2",
                            tenant=tenant, id=aid, linked=str(alert["case_id"]) if alert.get("case_id") else None)
        if len(cases) == 1:
            cid = str(cases[0]["id"])
        ambiguous = len(cases) > 1
    case = None
    alerts = [alert] if alert else []
    if cid:
        cases = await _rows(db, "SELECT * FROM aisoc_cases WHERE id = CAST(:id AS UUID) AND tenant_id = CAST(:tenant AS UUID)", id=cid, tenant=tenant)
        if not cases:
            raise HTTPException(404, "case_not_found")
        case = cases[0]
        ids = [str(x) for x in case.get("alert_ids") or []]
        if aid and aid not in ids and str(alert.get("case_id")) != cid:
            raise HTTPException(404, "alert_not_linked_to_case")
        alerts = await _rows(db, "SELECT * FROM alerts WHERE tenant_id = CAST(:tenant AS UUID) "
                             "AND (id = ANY(CAST(:ids AS UUID[])) OR case_id = CAST(:case AS UUID)) "
                             "ORDER BY CASE WHEN id = ANY(CAST(:ids AS UUID[])) THEN 0 ELSE 1 END, event_time ASC, id ASC LIMIT :limit", tenant=tenant, ids=ids, case=cid, limit=ALERT_LIMIT + 1)
    # Keep the original Case seed rule: earliest explicitly linked alert,
    # then alerts.case_id only when none of those explicit IDs resolve.
    explicit = {str(x) for x in (case or {}).get("alert_ids") or []}
    seed = next((str(a["id"]) for a in alerts if str(a["id"]) in explicit), None)
    if aid and not case_id:
        seed = aid  # The Alert entry never changes its seed to an older Case alert.
    seed = seed or (str(alerts[0]["id"]) if alerts else None)
    return {"tenant_id": tenant, "case_id": cid, "alert_id": aid, "case": case, "requested_alert": alert,
            "alerts": alerts[:ALERT_LIMIT], "seed_alert_id": seed,
            "scope": "case" if case_id else "alert", "case_ambiguous": ambiguous,
            "truncated": len(alerts) > ALERT_LIMIT}


def _values(alert: dict[str, Any], column: str, kinds: set[str]) -> list[str]:
    values = [x for x in alert.get(column) or [] if isinstance(x, str) and x.strip()]
    entities = alert.get("entities") or []
    if isinstance(entities, list):
        values += [e.get("value") for e in entities if isinstance(e, dict)
                   and e.get("type") in kinds and isinstance(e.get("value"), str)]
    return list(dict.fromkeys(x.strip()[:500] for x in values if x.strip()))


def _entity_id(tenant: str, kind: str, value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"aisoc:reported:{tenant}:{kind}:{value}"))


async def prepare_investigation_graph(db: Any, tenant_id: Any, case_id: Any = None, alert_id: Any = None) -> dict[str, Any]:
    anchor = await _anchor(db, tenant_id, case_id, alert_id)
    receipt: dict[str, Any] = {"status": "success", "source": "postgres_alert_projection", "error": None,
        "tenant_id": anchor["tenant_id"], "case_id": anchor["case_id"], "alert_id": anchor["alert_id"],
        "scope": anchor["scope"], "source_alert_ids": [], "truncated": anchor["truncated"],
        "evidence_semantics": "source_alert_reported_association; not independently verified attack causality"}
    tenant = anchor["tenant_id"]
    projection_alerts = ([anchor["requested_alert"]] if alert_id and not case_id else anchor["alerts"])
    if alert_id and not case_id:
        receipt["truncated"] = False  # This projection covers only the verified requested Alert.
    try:
        for alert in projection_alerts:
            aid = str(alert["id"])
            hosts = _values(alert, "affected_hosts", {"host", "hostname", "device"})
            users = _values(alert, "affected_users", {"user", "username", "email"})
            iocs = _values(alert, "affected_ips", {"ip", "domain", "hash", "url"})
            if max(len(hosts), len(users), len(iocs)) > ENTITY_LIMIT:
                receipt["truncated"] = True
            host_ids, user_ids = [], []
            for host in hosts[:ENTITY_LIMIT]:
                hid = _entity_id(tenant, "host", host)
                await graph_service.upsert_host(hid, host, tenant)
                host_ids.append(hid)
            for user in users[:ENTITY_LIMIT]:
                uid = _entity_id(tenant, "user", user)
                await graph_service.upsert_user(uid, user, tenant)
                user_ids.append(uid)
            techniques = [x if isinstance(x, str) else x.get("technique_id") or x.get("id")
                          for x in alert.get("mitre_techniques") or [] if isinstance(x, (str, dict))]
            await graph_service.upsert_alert_node(
                aid, tenant, alert.get("title") or "", alert.get("severity") or "unknown",
                mitre_techniques=[x for x in techniques if x][:ENTITY_LIMIT],
                host_ids=host_ids, user_ids=user_ids, ioc_values=iocs[:ENTITY_LIMIT],
                source_alert_id=aid, tenant_scoped_iocs=True,
            )
            receipt["source_alert_ids"].append(aid)
        if anchor["case"]:
            case = anchor["case"]
            await graph_service.upsert_case_node(anchor["case_id"], tenant, case.get("title") or "",
                                                 case.get("severity") or "unknown", receipt["source_alert_ids"])
    except Exception as exc:
        receipt.update(status="unavailable", error=type(exc).__name__)
    receipt["reason"] = receipt["error"] or ("bounded_projection" if receipt["truncated"] else "source_alerts_projected")
    return receipt


async def read_attack_chain(db: Any, tenant_id: Any, *, case_id: Any = None, alert_id: Any = None,
                            window: str = "24h", anchor: dict[str, Any] | None = None) -> dict[str, Any]:
    if window not in WINDOWS:
        raise HTTPException(422, "unsupported window")
    anchor = anchor or await _anchor(db, tenant_id, case_id, alert_id)
    seed = anchor["seed_alert_id"]
    if seed:
        chain = await compute_attack_chain(seed_alert_id=uuid.UUID(seed), tenant_id=uuid.UUID(anchor["tenant_id"]),
                                          loader=PostgresAttackChainLoader(db), window=WINDOWS[window], window_label=window)
        if chain is None:
            raise HTTPException(404, "seed_alert_not_found")
        data = chain.to_dict()
    else:
        data = {"tenant_id": anchor["tenant_id"], "window": window, "seed_alert_id": None,
                "chain": [], "entity_graph": {"nodes": [], "edges": []}, "chain_signature": None,
                "confidence": 0.0, "reason": "case_has_no_linked_alerts"}
    data["case_id"] = anchor["case_id"]
    return data


def _part(status: str, source: str | None, data: Any = None, error: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"status": status, "source": source, "data": data, "error": error, **extra}


async def read_investigation_attack_context(db: Any, tenant_id: Any, case_id: Any = None,
                                           alert_id: Any = None, window: str = "24h") -> dict[str, Any]:
    anchor = await _anchor(db, tenant_id, case_id, alert_id)
    result = {k: anchor[k] for k in ("tenant_id", "case_id", "alert_id", "scope")}
    result.update(queried_at=datetime.now(UTC).isoformat(),
                  query_scope={"projection_alert_limit": ALERT_LIMIT, "truncated": anchor["truncated"],
                               "case_ambiguous": anchor["case_ambiguous"], "seed_alert_id": anchor["seed_alert_id"],
                               "semantics": "candidate association, not verified causal attack chain"})
    try:
        data = await read_attack_chain(db, tenant_id, window=window, anchor=anchor)
        result["attack_chain"] = _part("success" if data["chain"] else "empty", "postgres", data,
                                       query={"window": window, "anchor": "seed_event_time_plus_minus_window"})
    except HTTPException:
        raise
    except Exception as exc:
        result["attack_chain"] = _part("unavailable", "postgres", error=type(exc).__name__, query={"window": window})
    result["attack_path"] = _part("not_linked", None, error="ambiguous_case" if anchor["case_ambiguous"] else "no_linked_case")
    if anchor["case_id"]:
        source, failure, data = "neo4j", None, None
        try:
            data = await graph_service.get_attack_path(anchor["case_id"], anchor["tenant_id"])
        except Exception as exc:
            failure = type(exc).__name__
        if not data or not data.get("nodes"):
            # Reuse the existing PG fallback; only verified owned Alert IDs are supplied.
            from app.api.v1.endpoints.graph import _attack_path_from_relational
            try:
                data = await _attack_path_from_relational(db, anchor["case_id"], anchor["tenant_id"])
            except Exception as exc:
                result["attack_path"] = _part("unavailable", "postgres_fallback", error=type(exc).__name__, fallback=True)
                data = None
                source = None
            if data:
                allowed = {f"alert:{a['id']}" for a in anchor["alerts"]}
                data["nodes"] = [n for n in data["nodes"] if n["label"] != "Alert" or n["id"] in allowed]
                ids = {n["id"] for n in data["nodes"]}
                data["edges"] = [e for e in data["edges"] if e["source"] in ids and e["target"] in ids]
                data.update(node_count=len(data["nodes"]), edge_count=len(data["edges"]))
            if source is not None:
                source = "postgres_fallback"
        if source is not None:
            result["attack_path"] = _part("success" if data and data.get("edges") else "empty", source, data,
                                          failure, fallback=source == "postgres_fallback")
    aid = anchor["alert_id"] or anchor["seed_alert_id"]
    result["alert_graph"] = _part("empty", "neo4j", {"neighbors": None, "blast_radius": None})
    if aid:
        try:
            neighbors = await graph_service.get_entity_neighbors(aid, "alert", anchor["tenant_id"])
            blast = await graph_service.get_blast_radius(aid, "alert", anchor["tenant_id"])
            result["alert_graph"] = _part("success" if neighbors.get("source") else "empty", "neo4j",
                                          {"neighbors": neighbors, "blast_radius": blast})
        except Exception as exc:
            result["alert_graph"] = _part("unavailable", "neo4j", error=type(exc).__name__)
    return result
