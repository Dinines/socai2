"""C2 read-only sources. All selectors originate in frozen C1 objects.

These are current inventory / recorded history / internal intelligence reads,
not forensic proof or an external intelligence lookup. No agent service imports.
"""
import json
from datetime import datetime

from sqlalchemy import text

from . import baseline_optional_sources as optional

VERSION = "socai2.c2-db.v1"
SOURCES = ("assets", "history", "threat_intel", "ueba", "knowledge", "graph")
CONNECTED = frozenset(SOURCES[:3])


def connected(source):
    return source in CONNECTED or source in {"ueba", "knowledge", "graph"} and optional.enabled(source)


def selectors(context, source):
    found = {}
    for aid, alert in context.alerts.items():
        if source == "knowledge":
            term = alert.alert.get("title")
            if isinstance(term, str) and term.strip():
                found[(aid,)] = {"object_key": "detection:"+aid, "namespace": alert.alert["source_namespace"],
                    "object_type": "detection", "value": term[:256], "ioc_type": None, "alert_ids": [aid],
                    "source_paths": [{"alert_id": aid, "source_path": "$.alert.title",
                        "original_characters": len(term), "query_text_truncated": len(term) > 256,
                        "transform": "prefix_256_characters"}]}
            continue
        for obj in alert.objects:
            typ, value = obj["object_type"], obj["normalized_value"]
            ioc_type = typ
            if typ == "hash":
                ioc_type = obj.get("attributes", {}).get("algorithm")
                ioc_type = ioc_type.lower().replace("-", "") if isinstance(ioc_type, str) else None
            eligible = (source == "history" or
                source in {"ueba", "graph"} and typ == "user" and bool(obj["namespace"]) or
                source == "assets" and typ in {"host", "ip"} or
                source == "threat_intel" and obj["object_role"] in {"ioc", "both"}
                and ioc_type in {"ip", "domain", "url", "email", "md5", "sha1", "sha256"})
            if not eligible:
                continue
            key = (obj["object_key"], obj["namespace"], typ, value, ioc_type)
            item = found.setdefault(key, {"object_key": key[0], "namespace": key[1],
                "object_type": typ, "value": value, "ioc_type": ioc_type,
                "alert_ids": [], "source_paths": []})
            if aid not in item["alert_ids"]:
                item["alert_ids"].append(aid)
            item["source_paths"].append({"alert_id": aid, "material_id": obj["material_id"],
                "object_id": obj["id"], "source_path": obj["source_path"]})
    return sorted(found.values(), key=lambda item: (item["object_key"], item["namespace"], item["value"]))


def selection_config(context):
    if not getattr(context, "case_input_profile", None):
        return None
    from .case_model_boundary import selected_profile
    return selected_profile(context).config["enrichment"]


def selection_plan(context, knowledge_keys=None):
    """Rank frozen object relevance, without an LLM call or inferred verdict."""
    keys = {source: selectors(context, source) for source in SOURCES}
    if knowledge_keys is not None:
        keys["knowledge"] = knowledge_keys
    has_host = any(k["object_type"] == "host" for k in keys["assets"])
    has_specific = bool(keys["threat_intel"] or keys["ueba"] or has_host)
    ranking = {
        "threat_intel": (100, "explicit_typed_ioc_reputation"),
        "ueba": (90, "namespaced_user_behavior_context"),
        "assets": (80 if has_host else 50, "host_inventory" if has_host else "ip_inventory"),
        "knowledge": (40 if has_specific else 100, "detection_guidance"),
        "history": (60, "same_object_history"),
        "graph": (30, "user_identity_relationships"),
    }
    config = selection_config(context)
    paired = {}
    if config:
        from .case_query_snapshot import source as query_source
        from .incident_query_receipts import receipts
        for aid, receipt in receipts(query_source(context.model_dump(mode="json"))):
            body = receipt["content_json"]
            if body["state"] == "completed":
                paired.setdefault(body["tool_name"], set()).add(aid)
    plan = [{"source": source, "priority": ranking[source][0] if keys[source] and connected(source) else 0,
        "reason": ranking[source][1], "selector_count": len(keys[source]), "connected": connected(source)}
        for source in SOURCES]
    if config:
        for item in plan:
            source = item["source"]
            eligible = {aid for key in keys[source] for aid in key["alert_ids"]}
            covered = eligible & paired.get(source, set())
            repeated = bool(eligible) and eligible <= covered
            priority = config["priorities"][source] - (config["paired_source_penalty"] if repeated else 0)
            item.update(priority=priority if eligible and item["connected"] else -1 - config["paired_source_penalty"],
                        reason="paired_background_available" if repeated else "missing_paired_background",
                        paired_query_members=sorted(covered), eligible_members=sorted(eligible),
                        selection_policy=config["version"])
    return sorted(plan, key=lambda p: (-p["priority"], SOURCES.index(p["source"])))


KEYS = """WITH keys AS (
 SELECT * FROM jsonb_to_recordset(CAST(:keys AS jsonb))
 AS k(object_key text, namespace text, object_type text, value text, ioc_type text)
)
"""
QUERIES = {
    "assets": KEYS + """
SELECT jsonb_build_object('object_key',k.object_key,'namespace',k.namespace,
 'record_id',a.id,'match_basis',CASE WHEN k.object_type='ip' THEN 'exact_ip'
 WHEN lower(a.name)=lower(k.value) THEN 'exact_name_casefold' ELSE 'exact_fqdn_casefold' END,
 'record',jsonb_build_object('id',a.id,'name',a.name,'fqdn',a.fqdn,
 'asset_type',a.asset_type,'ip_addresses',a.ip_addresses,'criticality',a.criticality,
 'tags',a.tags,'owner_email',a.owner_email,'os',a.os,'os_version',a.os_version,
 'first_seen',a.first_seen,'last_seen',a.last_seen,'updated_at',a.updated_at)) AS row
FROM keys k JOIN public.assets a ON a.tenant_id=:tenant AND (
 (k.object_type='host' AND (lower(a.name)=lower(k.value) OR lower(a.fqdn)=lower(k.value)))
 OR (k.object_type='ip' AND k.value=ANY(a.ip_addresses)))
ORDER BY k.object_key,k.namespace,a.id LIMIT :fetch_limit
""",
    "history": KEYS + """
SELECT DISTINCT jsonb_build_object('object_key',k.object_key,'namespace',k.namespace,
 'record_id',a.id,'match_basis','exact_typed_namespaced_object',
 'record',jsonb_build_object('id',a.id,'title',a.title,'event_time',a.event_time,
 'material_id',a.latest_material_id,'severity',a.severity,'original_vendor',a.original_vendor,
 'triage',to_jsonb(t),'feedback',to_jsonb(f))) AS row
FROM keys k JOIN socai2.alert_objects o ON o.tenant_id=:tenant
 AND o.object_key=k.object_key AND o.namespace=k.namespace
 AND o.object_type=k.object_type AND o.normalized_value=k.value
JOIN socai2.alerts a ON a.tenant_id=o.tenant_id AND a.id=o.alert_id
 AND a.latest_material_id=o.material_id
LEFT JOIN socai2.alert_assessments t ON t.tenant_id=a.tenant_id AND t.alert_id=a.id
 AND t.id=a.latest_triage_id AND t.kind='triage'
LEFT JOIN socai2.alert_assessments f ON f.tenant_id=a.tenant_id AND f.alert_id=a.id
 AND f.id=a.latest_feedback_id AND f.kind='human_feedback'
WHERE a.event_time>=CAST(:window_start AS timestamptz) AND a.event_time<=CAST(:window_end AS timestamptz)
 AND NOT (a.id=ANY(CAST(:exclude AS uuid[])))
ORDER BY row LIMIT :fetch_limit
""",
    "threat_intel": KEYS + """
SELECT jsonb_build_object('object_key',k.object_key,'namespace',k.namespace,
 'record_id',i.id,'match_basis','exact_typed_ioc',
 'record',jsonb_build_object('id',i.id,'ioc_type',i.ioc_type,'value',i.value,
 'confidence',i.confidence,'confidence_provenance','stored_score_calculation_unverified',
 'severity',i.severity,'tags',i.tags,'source',i.source,'source_ref',i.source_ref,
 'first_seen',i.first_seen,'last_seen',i.last_seen,'expires_at',i.expires_at,'updated_at',i.updated_at)) AS row
FROM keys k JOIN public.threat_intel_iocs i ON i.tenant_id=:tenant
 AND i.ioc_type=k.ioc_type AND i.value=k.value
WHERE i.is_active AND NOT i.false_positive AND (i.expires_at IS NULL OR i.expires_at>:observed_at)
ORDER BY k.object_key,k.namespace,i.id LIMIT :fetch_limit
""",
}

LIMITATIONS = {
    "assets": ["current_inventory_not_event_time_state", "exact_name_or_ip_match_not_identity_proof",
               "inventory_has_no_object_namespace_all_matches_retained"],
    "history": ["recorded_alerts_only_not_complete_activity_history", "same_object_not_causality",
                "prior_triage_and_human_feedback_are_not_independent_observations", "legacy_public_alerts_not_queried"],
    "threat_intel": ["tenant_internal_intelligence_only", "no_hit_does_not_mean_safe",
                     "stored_score_not_case_confidence_or_proof_of_malice"],
}


LIMITATIONS.update(optional.LIMITATIONS)


async def query(service, tenant_id, source, args):
    """One bounded SELECT per call, with explicit tenant filters even without RLS."""
    if source == "graph":
        return await optional.graph_query({**args, "tenant_id": str(tenant_id)})
    if source == "knowledge":
        from .knowledge_config import configured
        if configured():
            from .knowledge_source import query as knowledge_query
            return await knowledge_query(service, tenant_id, args)
    async with service.transaction(tenant_id, readonly=True) as store:
        observed = await store.now()
        params = {"tenant": tenant_id, "keys": json.dumps(args["parameters"]["selectors"]),
            "fetch_limit": args["limit"] + 1, "observed_at": observed,
            "exclude": args["scope"]["alert_ids"],
            "window_start": datetime.fromisoformat(args["scope"]["window_start"]) if args["scope"]["window_start"] else None,
            "window_end": datetime.fromisoformat(args["scope"]["window_end"]) if args["scope"]["window_end"] else None}
        rows = (await store.db.execute(text((QUERIES | optional.QUERIES)[source]), params)).scalars().all()
        return list(rows), observed
