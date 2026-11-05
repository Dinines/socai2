"""Typed projection of retained event fields, never a raw-log model shortcut.

Each selected original scalar is guarded before any size reduction. Source paths,
omissions and conflicting alternatives are retained. No value is inferred from
titles, raw text, a storage preview, or an unrelated sibling object.
"""
import ipaddress
import json
import re

from .baseline_model_view import MAX_FIELD_BYTES, blocked
from .baseline_store import digest, encoded

VERSION = "socai2.event-semantics.v1"
EVENT_KINDS = {1007: "process_activity", 4001: "network_activity", 3002: "authentication_activity"}
# OCSF process and actor.process describe different actors. Keep them distinct.
PATHS = {
    "process_name": ("process.name",), "process_pid": ("process.pid",),
    "process_uid": ("process.uid",), "process_command_line": ("process.cmd_line",),
    "process_path": ("process.file.path",), "parent_pid": ("process.parent_process.pid",),
    "parent_uid": ("process.parent_process.uid",), "parent_name": ("process.parent_process.name",),
    "parent_path": ("process.parent_process.file.path",),
    "parent_command_line": ("process.parent_process.cmd_line",),
    "actor_process_pid": ("actor.process.pid",), "actor_process_name": ("actor.process.name",),
    "actor_process_command_line": ("actor.process.cmd_line",),
    "actor_process_parent_pid": ("actor.process.parent_process.pid",),
    "user_name": ("actor.user.name", "user.name"), "user_uid": ("actor.user.uid", "user.uid"),
    "device_name": ("device.name", "device.hostname"), "src_hostname": ("src_endpoint.hostname",),
    "dst_hostname": ("dst_endpoint.hostname",), "source_ip": ("src_endpoint.ip",),
    "dest_ip": ("dst_endpoint.ip",), "src_port": ("src_endpoint.port",),
    "dst_port": ("dst_endpoint.port",),
    "protocol": ("protocol", "connection_info.protocol_name", "network.protocol_name"), "file_path": ("file.path",),
    "process_session_uid": ("process.session.uid",), "process_session_uid_alt": ("process.session_uid",),
    "actor_session_uid": ("actor.session.uid",), "actor_session_uid_alt": ("actor.session_uid",),
    "action": ("activity.action",), "outcome": ("activity.outcome",),
    "session_id": ("activity.session.id",), "session_key": ("activity.session.key",),
    "session_key_kind": ("activity.session.key_kind",),
    "session_originating_human": ("activity.session.originating_human",),
}
ACTIVITY_FIELDS = {name for name, paths in PATHS.items() if paths[0].startswith("activity.")}
# Optional OCSF traffic counters. Do not add six missing-field entries to every
# process/authentication observation or infer zero from an absent counter.
TRAFFIC_PATHS = {"network_" + name: ("traffic." + name,) for name in
    ("bytes", "bytes_in", "bytes_out", "packets", "packets_in", "packets_out")}
LIMITATIONS = ["selected_source_fields_only_not_full_raw_review",
    "source_reports_are_not_independent_corroboration", "parent_or_session_fields_do_not_prove_causality"]


def at(value, path):
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def parse_object(value):
    if isinstance(value, dict):
        return value, None
    if isinstance(value, str):
        def unique(pairs):
            obj = {}
            for k, v in pairs:
                if k in obj:
                    raise ValueError("duplicate_key")
                obj[k] = v
            return obj
        try:
            obj = json.loads(value, object_pairs_hook=unique,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        except (ValueError, RecursionError):
            return None, "invalid_structured_material"
        if isinstance(obj, dict):
            return obj, None
    return None, "structured_material_missing"


def scalar_reason(name, value):
    if type(value) not in {str, int}:
        return "unsupported_field_type"
    if blocked(value):
        return "source_guard_blocked"
    if len(encoded(value)) > MAX_FIELD_BYTES:
        return "whole_field_exceeds_budget"
    if type(value) is str and not value.strip():
        return "empty_source_value"
    if name in TRAFFIC_PATHS:
        if type(value) is not int or not 0 <= value <= 2**63 - 1:
            return "invalid_traffic_counter"
    elif name == "hash_sha256":
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            return "invalid_sha256"
    elif name.endswith("_pid"):
        if type(value) is not int or value < 0:
            return "invalid_pid"
    elif name in {"src_port", "dst_port"}:
        if type(value) is not int or not 0 <= value <= 65535:
            return "invalid_port"
    elif name in {"source_ip", "dest_ip"}:
        if not isinstance(value, str):
            return "invalid_ip"
        try:
            ipaddress.ip_address(value)
        except ValueError:
            return "invalid_ip"
    elif type(value) is not str:
        return "unsupported_field_type"
    return None


def same_scalar(name, left, right):
    """Compare typed values without rewriting their retained source representation."""
    if name in {"source_ip", "dest_ip"}:
        def address(value):
            parsed = ipaddress.ip_address(value)
            return parsed.ipv4_mapped or parsed if isinstance(parsed, ipaddress.IPv6Address) else parsed
        return address(left) == address(right)
    if name == "hash_sha256":
        return left.lower() == right.lower()
    return left == right


def project(value, *, root="$.ocsf_json"):
    obj, reason = parse_object(value)
    result = {"schema_version": VERSION, "fields": [], "omissions": [],
        "limitations": list(LIMITATIONS), "source_sha256": digest(value), "state": "available"}
    if reason:
        result.update(state="unavailable", omissions=[{"source_path": root, "reason": reason}])
        return result
    storage = obj.get("_socai2_storage")
    if isinstance(storage, dict) and storage.get("truncated") is True:
        result.update(state="unavailable", omissions=[{"source_path": root, "reason": "stored_preview_not_original"}])
        return result
    raw_kind = obj.get("class_uid")
    if type(raw_kind) is int and raw_kind in EVENT_KINDS:
        result["fields"].append({"name": "event_kind", "value": EVENT_KINDS[raw_kind],
            "source_path": root + ".class_uid", "transform": "explicit_class_mapping", "conflict": False})
    else:
        result["omissions"].append({"source_path": root + ".class_uid", "reason": "event_kind_unknown"})
    selected_paths = {**PATHS, **{name: paths for name, paths in TRAFFIC_PATHS.items()
        if any(at(obj, path) is not None for path in paths)}}
    if any(name in TRAFFIC_PATHS for name in selected_paths):
        result["limitations"].append(
            "traffic_in_is_destination_to_source_out_is_source_to_destination_bytes_are_not_payload_content")
    for name, paths in selected_paths.items():
        # Fusion retains envelope activity separately, with precedence recorded.
        # Keep both values when they disagree; do not create a hybrid session.
        paths = list(paths)
        if name in ACTIVITY_FIELDS and isinstance(storage, dict) and str(storage.get("activity_source", "")).startswith("activity"):
            paths.insert(0, "_socai2_storage.envelope_activity." + paths[0][len("activity."):])
        seen = [(p, at(obj, p)) for p in paths if at(obj, p) is not None]
        if not seen:
            result["omissions"].append({"source_path": root + "." + paths[0], "reason": "not_provided"})
        conflict = len({digest(v) for _, v in seen}) > 1
        for path, original in seen:
            why = scalar_reason(name, original)
            if why:
                result["omissions"].append({"source_path": root + "." + path, "reason": why})
            else:
                result["fields"].append({"name": name, "value": original, "source_path": root + "." + path,
                    "transform": "identity", "conflict": conflict})
    hashes = []
    if "hash_sha256" in obj:
        hashes.append(("hash_sha256", obj["hash_sha256"]))
    for path in ("file.hashes", "file.fingerprints"):
        entries = at(obj, path)
        if entries is None:
            continue
        if not isinstance(entries, list):
            result["omissions"].append({"source_path": root + "." + path, "reason": "unsupported_hash_container"})
            continue
        for index, entry in enumerate(entries):
            source = f"{path}[{index}]"
            if (not isinstance(entry, dict) or not isinstance(entry.get("algorithm"), str)
                    or entry["algorithm"].upper().replace("-", "") != "SHA256"):
                result["omissions"].append({"source_path": root + "." + source, "reason": "sha256_algorithm_not_explicit"})
                continue
            hashes.append((source + ".value", entry.get("value")))
    valid = []
    for path, original in hashes:
        why = scalar_reason("hash_sha256", original)
        if why:
            result["omissions"].append({"source_path": root + "." + path, "reason": why})
        else:
            valid.append((path, original))
    conflict = len({v.lower() for _, v in valid}) > 1
    result["fields"].extend({"name": "hash_sha256", "value": original, "source_path": root + "." + path,
        "transform": "identity", "conflict": conflict} for path, original in valid)
    return result


def material_projection(material):
    value, root = material.get("ocsf_json"), "$.ocsf_json"
    if value is None and isinstance(material.get("raw_json"), dict):
        value, root = material["raw_json"], "$.raw_json"
        if isinstance(value.get("raw_event"), dict):
            value, root = value["raw_event"], root + ".raw_event"
        if isinstance(value.get("ocsf_event"), dict):
            value, root = value["ocsf_event"], root + ".ocsf_event"
    output = project(value, root=root)
    output.update(material_id=str(material["id"]), alert_id=str(material["alert_id"]),
        material_state=material["material_state"], material_sha256=material.get("sha256"))
    if material["material_state"] != "complete":
        output["limitations"].append("retained_material_" + material["material_state"])
    return output
