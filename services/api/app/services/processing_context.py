"""Bounded, tenant-scoped PG context reads and explicit scoring provenance.

This is a current read view, not a mutation of frozen alert or Fusion scores.
Each dimension uses a savepoint so a failed optional SELECT does not poison
the remaining reads on PostgreSQL. Missing material is distinct from failure.
"""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.services.alert_priority import AssetContext, IdentityContext, score_alert_priority

LIMIT = 20
ASSETS = """
SELECT a.id,a.name,a.fqdn,a.ip_addresses,a.criticality,a.owner_email,
       a.last_seen,a.updated_at,jsonb_build_object(
       'source',a.metadata->'source','source_ref',a.metadata->'source_ref',
       'observed_at',a.metadata->'observed_at','internet_facing',a.metadata->'internet_facing') AS metadata
FROM assets a WHERE a.tenant_id=CAST(:tenant_id AS uuid) AND (
 lower(a.name)=ANY(CAST(:hosts AS text[])) OR
 lower(a.fqdn)=ANY(CAST(:hosts AS text[])) OR
 a.ip_addresses && CAST(:ips AS text[]) OR a.id IN (
 SELECT asset_id FROM alert_asset_correlations
 WHERE tenant_id=CAST(:tenant_id AS uuid) AND alert_id=CAST(:alert_id AS uuid)))
ORDER BY a.id LIMIT 21
"""
IDENTITIES = """
SELECT id,principal,privilege_tier,is_service,is_break_glass,source,updated_at
FROM identity_privilege WHERE tenant_id=CAST(:tenant_id AS uuid)
 AND lower(principal)=ANY(CAST(:accounts AS text[])) ORDER BY id LIMIT 21
"""
VULNERABILITIES = """
SELECT id,asset_id,cve_id,title,severity,cvss_score,is_exploited,source,
       first_found,last_found,remediated_at,jsonb_build_object(
       'kev',metadata->'kev','source_ref',metadata->'source_ref',
       'observed_at',metadata->'observed_at') AS metadata
FROM asset_vulnerabilities WHERE tenant_id=CAST(:tenant_id AS uuid)
 AND asset_id=ANY(CAST(:asset_ids AS uuid[])) AND remediated_at IS NULL
ORDER BY id LIMIT 21
"""
HISTORY = """
SELECT id,title,severity,event_time,created_at,source_event_ids
FROM alerts WHERE tenant_id=CAST(:tenant_id AS uuid)
 AND id<>CAST(:alert_id AS uuid)
 AND COALESCE(event_time,created_at)<CAST(:event_time AS timestamptz)
 AND COALESCE(event_time,created_at)>=CAST(:event_time AS timestamptz)-interval '7 days'
 AND (affected_hosts ?| CAST(:hosts_original AS text[]) OR
      affected_users ?| CAST(:accounts_original AS text[]) OR
      affected_ips ?| CAST(:ips AS text[]))
ORDER BY COALESCE(event_time,created_at) DESC,id LIMIT 21
"""

def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({v.strip() for v in values if isinstance(v, str) and v.strip()})[:LIMIT]

async def _read(db: Any, query: str, params: dict, source: str) -> dict:
    try:
        async with db.begin_nested():
            await db.execute(text("SET LOCAL statement_timeout='3000ms'"))
            result = await db.execute(text(query), params)
            rows = [dict(row) for row in result.mappings().all()]
        return {"status": "matched" if rows else "no_match", "source": source,
                "rows": rows[:LIMIT], "truncated": len(rows) > LIMIT}
    except Exception as exc:
        # Never expose DSNs/SQL errors or describe a failed read as empty data.
        return {"status": "unavailable", "source": source, "rows": [],
                "truncated": False, "error_type": type(exc).__name__}

async def collect_processing_context(db: Any, alert: Any) -> dict:
    hosts = _strings(getattr(alert, "affected_hosts", None))
    accounts = _strings(getattr(alert, "affected_users", None))
    ips = _strings(getattr(alert, "affected_ips", None))
    reference = getattr(alert, "event_time", None) or alert.created_at
    params = {"tenant_id": str(alert.tenant_id), "alert_id": str(alert.id),
              "hosts": [s.lower() for s in hosts], "hosts_original": hosts,
              "accounts": [s.lower() for s in accounts], "accounts_original": accounts,
              "ips": ips, "event_time": reference}
    assets = await _read(db, ASSETS, params, "assets/alert_asset_correlations")
    identities = await _read(db, IDENTITIES, params, "identity_privilege") if accounts else {
        "status": "not_requested", "source": "identity_privilege", "rows": [], "truncated": False}
    if assets["status"] == "unavailable":
        vulnerabilities = {"status": "unavailable", "source": "asset_vulnerabilities",
                           "rows": [], "reason": "asset_lookup_failed", "truncated": False}
    elif assets["rows"]:
        vulnerabilities = await _read(db, VULNERABILITIES,
            {**params, "asset_ids": [str(a["id"]) for a in assets["rows"]]}, "asset_vulnerabilities")
    else:
        vulnerabilities = {"status": "not_requested", "source": "asset_vulnerabilities",
                           "rows": [], "reason": "no_matched_asset", "truncated": False}
    history = await _read(db, HISTORY, params, "alerts: prior7days, event_time or created_at") if hosts or accounts or ips else {
        "status": "not_requested", "source": "alerts", "rows": [], "truncated": False}
    dimensions = {"assets": assets, "identities": identities, "vulnerabilities": vulnerabilities, "alert_history": history}
    priority: dict[str, Any]
    # Truncated vulnerability sets must not yield an apparently complete score.
    required = [assets, identities, vulnerabilities]
    if any(d["status"] == "unavailable" for d in required):
        priority = {"status": "unavailable", "score": None, "rationale": []}
    elif any(d["truncated"] for d in required) or len(assets["rows"]) > 1 or len(identities["rows"]) > 1:
        priority = {"status": "ambiguous", "score": None, "rationale": []}
    else:
        a = assets["rows"][0] if assets["rows"] else None
        i = identities["rows"][0] if identities["rows"] else None
        vulns = vulnerabilities["rows"]
        result = score_alert_priority(severity=alert.severity,
            asset=AssetContext(asset_id=str(a["id"]),criticality=a["criticality"],
                has_kev_vulnerability=any((v.get("metadata") or {}).get("kev") is True for v in vulns),
                exploitable_vuln_count=sum(v.get("is_exploited") is True for v in vulns),
                internet_facing=(a.get("metadata") or {}).get("internet_facing") is True) if a else None,
            identity=IdentityContext(principal=i["principal"],privilege_tier=i["privilege_tier"],
                is_service=i["is_service"],is_break_glass=i["is_break_glass"]) if i else None)
        priority = {"status": "computed", **result.as_dict(),
                    "asset_id": str(a["id"]) if a else None, "identity_id": str(i["id"]) if i else None,
                    "material_complete": bool(a and i)}
    return {"schema_version": "processing-context-v1", "tenant_id": str(alert.tenant_id),
            "alert_id": str(alert.id), "queried_at": datetime.now(UTC),
            "query": {"hosts": hosts, "accounts": accounts, "ips": ips,
                      "history_before": reference, "history_days": 7, "limit_per_dimension": LIMIT},
            "dimensions": dimensions, "priority": priority,
            "scoring_source_sha256": hashlib.sha256(Path(__file__).with_name("alert_priority.py").read_bytes()).hexdigest(),
            "partial": any(d["status"] == "unavailable" for d in dimensions.values()),
            "external_event_history": {"status": "not_configured"},
            "ueba": {"status": "not_configured"}, "original_alert_modified": False}
