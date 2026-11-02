"""Stored alert fields shared by page and Case readers; no inferred facts."""
import json
from copy import deepcopy
from sqlalchemy import select
from app.models.tenant import User


async def assignee_names(db, tenant_id, alerts):
    ids = {getattr(alert, "assigned_to_id", None) for alert in alerts} - {None}
    if not ids:
        return {}
    rows = (await db.execute(select(User.id, User.username).where(User.tenant_id == tenant_id, User.id.in_(ids)))).all()
    return dict(rows)


def strings(values):
    return sorted({v for v in values if isinstance(v, str) and v}) if isinstance(values, list) else []


def fusion_metadata(alert):
    data = getattr(alert, "enrichment_data", None)
    fusion = data.get("socai2_fusion") if isinstance(data, dict) else None
    return fusion if isinstance(fusion, dict) else {}


def alert_objects(alert):
    pairs = set()
    for kind, column in (("host", "affected_hosts"), ("user", "affected_users"), ("ip", "affected_ips")):
        pairs.update((kind, value) for value in strings(getattr(alert, column, None)))
    for column in ("entities", "iocs"):
        for item in getattr(alert, column, None) or []:
            if isinstance(item, dict):
                kind, value = item.get("type"), item.get("value")
                if isinstance(kind, str) and kind and isinstance(value, str) and value:
                    pairs.add((kind, value))
    return [{"type": kind, "value": value} for kind, value in sorted(pairs)]


def alert_source(alert):
    identity = fusion_metadata(alert).get("identity")
    identity = identity if isinstance(identity, dict) else {}
    raw = getattr(alert, "raw_event", None)
    raw = raw if isinstance(raw, dict) else {}
    inner = raw.get("raw_data")
    if isinstance(inner, str):
        try:
            inner = json.loads(inner)
        except ValueError:
            inner = None
    vendor, path = None, None
    # Explicit original producer fields only. metadata.product may describe
    # an intermediate SIEM; connector_type and identity.source are not fallbacks.
    for prefix, record in (("raw_event", raw), ("raw_event.raw_data", inner)):
        if isinstance(record, dict):
            for key in ("original_vendor", "deviceVendor"):
                value = record.get(key)
                if isinstance(value, str) and value.strip():
                    vendor, path = value.strip(), f"{prefix}.{key}"
                    break
        if vendor:
            break
    return {"detection_source": vendor, "detection_source_path": path,
            "source_alert_id": identity.get("source_alert_id"),
            "external_id": getattr(alert, "external_id", None),
            "connector_id": str(alert.connector_id) if getattr(alert, "connector_id", None) else None,
            "connector_type": getattr(alert, "connector_type", None)}


def detection_fields(alert):
    fusion = fusion_metadata(alert)
    state = fusion.get("confidence_status")
    state = state if state in {"computed", "unknown", "disabled", "failed"} else "legacy_unverified"
    # Old stored scores remain readable but their calculation state is unknown.
    show_score = state in {"computed", "legacy_unverified"}
    return deepcopy({"rule_id": getattr(alert, "rule_id", None), "rule_name": getattr(alert, "rule_name", None),
            "mitre_tactics": strings(getattr(alert, "mitre_tactics", None)),
            "mitre_techniques": strings(getattr(alert, "mitre_techniques", None)),
            "label_meaning": "source_detection_labels",
            "confidence": {"source": "fusion", "status": state, "meaning": "stored_score_not_independent_evidence",
                           "score": getattr(alert, "confidence", None) if show_score else None,
                           "label": getattr(alert, "confidence_label", None) if show_score else None,
                           "rationale": (getattr(alert, "confidence_rationale", None) or []) if show_score else []},
            "event_time_source": fusion.get("event_time_source"),
            "event_time_fallback": fusion.get("event_time_fallback"),
            "source_event_ids_truncated": fusion.get("source_event_ids_truncated"),
            "field_metadata": fusion.get("field_metadata") or {}})


def triage_fields(event):
    payload = event.payload if isinstance(event.payload, dict) else {}
    return deepcopy({"event_id": str(event.id), "run_id": str(event.run_id), "recorded_at": event.ts,
            "meaning": "saved_analysis_judgment", "score_source": "triage_event.payload.confidence",
            "score_meaning": "confidence_in_paired_verdict_not_risk",
            **{key: payload.get(key) for key in ("verdict", "rationale", "auto_closed", "confidence")},
            "findings": payload.get("findings") or [], "proposed_actions": payload.get("proposed_actions") or []})
