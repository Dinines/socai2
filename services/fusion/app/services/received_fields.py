"""Small projections of received values; no enrichment or inferred labels."""
from datetime import UTC, datetime

from app.services.raw_data import decode_raw_data


def nested(value, *path):
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def strings(value):
    return list(dict.fromkeys(v for v in value if isinstance(v, str) and v)) if isinstance(value, (list, tuple)) else []


def parse_received_time(value):
    """Same seconds/milliseconds convention as the existing parser, without host-local time."""
    try:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            dt = datetime.fromtimestamp(value / 1000 if value > 1e11 else value, UTC)
        elif isinstance(value, str) and value:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, OverflowError, OSError):
        return None


def received_time(message, ocsf):
    raw = decode_raw_data(ocsf) or {}
    for path, value in [("ocsf.time", ocsf.get("time")), ("event_time", message.get("event_time")),
                        ("raw_data.event_time", raw.get("event_time")), ("raw_data.timestamp", raw.get("timestamp"))]:
        dt = parse_received_time(value)
        if dt is not None:
            return dt, path
    return None, "unknown"


def activity_block(message):
    top = message.get("activity")
    body = nested(message, "ocsf_event", "activity")
    if isinstance(top, dict) and top and isinstance(body, dict) and body:
        def merge(lower, upper):
            return {**lower, **{k: merge(lower[k], v) if isinstance(v, dict) and isinstance(lower.get(k), dict) else v
                               for k, v in upper.items()}}
        return merge(body, top), "activity+ocsf_event.activity"
    if isinstance(top, dict) and top:
        return top, "activity"
    return (body, "ocsf_event.activity") if isinstance(body, dict) else ({}, "unknown")


def source_labels(ocsf):
    tactics, techniques = strings(ocsf.get("mitre_tactics")), strings(ocsf.get("mitre_techniques"))
    block = ocsf.get("mitre_attck")
    for entry in block if isinstance(block, list) else []:
        if isinstance(entry, dict):
            tactics.extend(strings(entry.get("tactic_names")))
            if isinstance(entry.get("technique_id"), str) and entry["technique_id"]:
                techniques.append(entry["technique_id"])
    return list(dict.fromkeys(tactics)), list(dict.fromkeys(techniques))


def received_projection(message, ocsf, *, rule_tactics=(), rule_techniques=()):
    raw = decode_raw_data(ocsf) or {}
    time, time_source = received_time(message, ocsf)
    source_tactics, source_techniques = source_labels(ocsf)
    candidates = {
        "src_ip": [("ocsf.src_endpoint.ip", nested(ocsf, "src_endpoint", "ip")), ("raw_data.src_ip", raw.get("src_ip"))],
        "dst_ip": [("ocsf.dst_endpoint.ip", nested(ocsf, "dst_endpoint", "ip")), ("raw_data.dst_ip", raw.get("dst_ip"))],
        "hostname": [("ocsf.device.name", nested(ocsf, "device", "name")), ("ocsf.src_endpoint.hostname", nested(ocsf, "src_endpoint", "hostname")), ("raw_data.hostname", raw.get("hostname")), ("raw_data.host", raw.get("host"))],
        "username": [("ocsf.actor.user.name", nested(ocsf, "actor", "user", "name")), ("raw_data.user", raw.get("user"))],
        "domain": [("ocsf.domain", ocsf.get("domain")), ("ocsf.dns.query.hostname", nested(ocsf, "dns", "query", "hostname")), ("raw_data.domain", raw.get("domain"))],
        "url": [("ocsf.url.url_string", nested(ocsf, "url", "url_string")), ("ocsf.url", ocsf.get("url")), ("raw_data.url", raw.get("url"))],
    }
    values, origins = {}, {}
    for field, options in candidates.items():
        for path, value in options:
            if isinstance(value, str) and value:
                values[field], origins[field] = value, path
                break
    return {**values, "event_time": time,
            "mitre_tactics": list(dict.fromkeys([*strings(rule_tactics), *source_tactics])),
            "mitre_techniques": list(dict.fromkeys([*strings(rule_techniques), *source_techniques])),
            "field_metadata": {"event_time_source": time_source, "entity_sources": origins,
                               "detection_labels": {"source": {"tactics": source_tactics, "techniques": source_techniques},
                                                    "rule": {"tactics": strings(rule_tactics), "techniques": strings(rule_techniques)}}}}


def received_rule(ocsf):
    rule = ocsf.get("rule") if isinstance(ocsf.get("rule"), dict) else {}
    finding = nested(ocsf, "finding", "rule")
    finding = finding if isinstance(finding, dict) else {}
    def first(*values):
        return next((v for v in values if isinstance(v, str) and v), None)
    return {"rule_id": first(ocsf.get("rule_id"), rule.get("uid"), rule.get("id"), finding.get("uid")),
            "rule_name": first(ocsf.get("rule_name"), rule.get("name"), finding.get("name"))}
