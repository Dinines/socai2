"""Received Fusion values -> new-schema fields, without inventing source facts."""
import hashlib
import json
from uuid import uuid5

from app.services.received_fields import activity_block, nested, parse_received_time

VERSION = "socai2.fusion-material.v1"
STORE_NAMESPACE = "fusion.v1"
MAX_REFS = 200


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def input_value(alert):
    # id and created_at may be generated again on replay. Preserve the first
    # received values in the material, but do not use arrival clocks as identity.
    return alert.model_dump(mode="json", exclude={"id", "created_at"})


def namespace(alert):
    return "connector:" + str(alert.connector_id) if alert.connector_id else "source:" + alert.source


def retained(value):
    size, sha = len(encoded(value).encode("utf-8")), digest(value)
    return {"original_size_bytes": size, "retained_size_bytes": size, "original_sha256": sha,
        "retained_sha256": sha, "truncated": False, "reason": None, "omitted_paths": []}


def original_vendor(raw):
    ocsf = raw.get("ocsf_event") if isinstance(raw.get("ocsf_event"), dict) else raw
    raw_data = ocsf.get("raw_data")
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except (TypeError, ValueError):
            raw_data = None
    for item in (raw, ocsf, raw_data):
        if isinstance(item, dict):
            for key in ("original_vendor", "deviceVendor"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    return value
    return None


def source_scope(alert):
    ids = list(dict.fromkeys(v for v in alert.source_event_ids if v.strip()))
    window = alert.field_metadata.get("source_window") or {}
    kind = "explicit_sources" if ids else "unknown"
    relation = "source_event"
    if window:
        sequence = window.get("scope") == "matched_stage_candidates" or "sequence" in str(window.get("coverage", ""))
        kind, relation = ("sequence_candidates", "sequence_candidate") if sequence else ("bounded_observed_references", "threshold_candidate")
    truncated = len(ids) > MAX_REFS or bool(window.get("truncated"))
    complete = False if truncated else window.get("complete", False) if window else True if ids else None
    def time(key):
        value = parse_received_time(window.get(key, window.get("candidate_start" if key == "window_start" else "candidate_end")))
        return value.isoformat() if value else None
    scope = {"kind": kind, "received_count": len(ids), "retained_count": min(len(ids), MAX_REFS),
        "complete": complete, "truncated": truncated, "window_start": time("window_start"), "window_end": time("window_end"),
        "omission_reason": "source_reference_limit" if truncated else "window_candidates_not_complete_activity" if window else None}
    return scope, [{"source_namespace": namespace(alert), "source_event_id": identity, "relation_kind": relation,
        "observed_at": None, "source_path": f"$.raw_json.source_event_ids[{alert.source_event_ids.index(identity)}]"}
        for identity in ids[:MAX_REFS]]


def project(fused, alert, snapshot_id):
    same_input = input_value(alert) == input_value(fused.alert)
    status = {"computed": "available", "unknown": "not_computed", "disabled": "disabled", "failed": "failed"}[
        fused.confidence_status] if same_input else "not_computed"
    available = status == "available"
    raw = alert.raw_event
    ocsf = raw.get("ocsf_event") if isinstance(raw.get("ocsf_event"), dict) else None
    if ocsf is None and isinstance(raw.get("class_uid"), int):
        ocsf = raw
    if ocsf and ocsf is not raw and isinstance(raw.get("activity"), dict):
        # Preserve the envelope and OCSF values separately. C4 already knows
        # this marker and reports conflicts instead of silently choosing one.
        ocsf = {**ocsf, "_socai2_storage": {**(ocsf.get("_socai2_storage") or {}),
            "activity_source": activity_block(raw)[1], "envelope_activity": raw["activity"]}}
    scope, refs = source_scope(alert)
    body = {"schema_version": VERSION, "items": [
        {"kind": "first_fusion_result_reference", "source": "fusion", "collected_at": None,
            "source_path": "$.fused", "value": {"artifact_id": str(snapshot_id), "same_material_input": same_input}},
    ]}
    if same_input:
        body["items"].append({"kind": "fusion_session", "source": "fusion", "collected_at": None,
            "source_path": "$.fused", "value": {"session_id": str(fused.session_id) if fused.session_id else None,
                "session_key_kind": fused.session_key_kind, "originating_human": fused.originating_human}})
    detection = {"rule_id": alert.rule_id, "rule_name": alert.rule_name, "tactics": alert.mitre_tactics,
        "techniques": alert.mitre_techniques, "labels_provided": bool(alert.mitre_tactics or alert.mitre_techniques),
        "confidence_state": status, "confidence_value": fused.confidence_score * 100 if available else None,
        "confidence_label": fused.confidence_label.value if available else None,
        "confidence_rationale": [encoded(f.model_dump(mode="json")) for f in fused.confidence_rationale] if available else None,
        "score_source": "fusion" if same_input else None, "ocsf_class_uid": alert.ocsf_class_uid}
    value = {"raw_text": ocsf.get("raw_data") if ocsf and isinstance(ocsf.get("raw_data"), str) else None,
        "raw_json": alert.model_dump(mode="json"), "ocsf_json": ocsf, "detection": detection, "enrichment": body, "source_scope": scope}
    # Preserve received payloads in full. The existing one-MiB delivery limit
    # is enforced by the sink; over-limit inputs fail, never slice invalid JSON.
    value.update(sha256=digest(value), retention=retained(value), material_state="complete")
    objects = []
    for field, typ, role in (("hostname", "host", "entity"), ("username", "user", "entity"),
            ("src_ip", "ip", "both"), ("dst_ip", "ip", "both"), ("domain", "domain", "ioc"),
            ("url", "url", "ioc"), ("file_hash", "hash", "ioc")):
        raw_value = getattr(alert, field)
        if not raw_value or not raw_value.strip():
            continue
        attrs = {"received_field": field, "original_path": nested(alert.field_metadata, "entity_sources", field)}
        # No hash algorithm is guessed from length or used as SHA256 implicitly.
        if typ == "hash" and ocsf:
            hashes = nested(ocsf, "file", "hashes")
            for item in hashes if isinstance(hashes, list) else []:
                if isinstance(item, dict) and item.get("value") == raw_value and item.get("algorithm"):
                    attrs["algorithm"] = item["algorithm"]
                    break
        objects.append({"object_key": encoded([typ, raw_value]), "object_type": typ, "object_role": role,
            "namespace": namespace(alert), "raw_value": raw_value, "normalized_value": raw_value,
            "source_type": alert.source, "source_path": "$.raw_json." + field, "attributes": attrs})
    # Index additional explicit OCSF endpoints without collapsing them to the
    # single hostname/IP slots in RawAlert. The unmodified envelope stays above.
    seen = {(o["object_type"], o["raw_value"]) for o in objects}
    for path, typ, role in (("device.name", "host", "entity"), ("src_endpoint.hostname", "host", "entity"),
            ("dst_endpoint.hostname", "host", "entity"), ("src_endpoint.ip", "ip", "both"),
            ("dst_endpoint.ip", "ip", "both"), ("actor.user.name", "user", "entity")):
        value_at = nested(ocsf, *path.split("."))
        if not isinstance(value_at, str) or not value_at.strip() or (typ, value_at) in seen:
            continue
        seen.add((typ, value_at))
        objects.append({"object_key": encoded([typ, value_at]), "object_type": typ, "object_role": role,
            "namespace": namespace(alert), "raw_value": value_at, "normalized_value": value_at,
            "source_type": alert.source, "source_path": "$.ocsf_json." + path, "attributes": {"original_path": path}})
    event_time = parse_received_time(alert.event_time)
    fields = {"source_alert_id": str(alert.source_alert_id) if alert.source_alert_id else None,
        "vendor_alert_id": alert.external_id, "connector_id": alert.connector_id, "connector_type": alert.connector_type,
        "original_vendor": original_vendor(raw), "title": alert.title, "description": alert.description or None,
        "severity": alert.severity.value, "severity_raw": alert.severity.value, "tags": alert.tags,
        "event_time": event_time, "event_time_source": "source" if event_time else "unknown"}
    return fields, value, refs, objects


def correlation(fused, snapshot_id):
    basis = fused.correlation_basis
    key = encoded([basis.entity_type, basis.entity_value]) if basis and basis.entity_type and basis.entity_value else None
    return {"method": basis.policy_version if basis else "fusion_basis_not_recorded", "rule_id": None,
        "object_keys": [key] if key else [], "window_start": None, "window_end": None,
        "reason": basis.reason if basis else None, "relation_strength": "shared_object" if key else "legacy_unverified",
        "source_refs": [{"type": "artifact", "id": str(snapshot_id), "external": None,
            "source_path": "$.fused.correlation_basis", "row_keys": [], "role": "execution_receipt"}] if basis else []}


def snapshot_id(alert_id):
    return uuid5(alert_id, "socai2.fusion.first-result.v1")
