"""C3-only field selection after original guards; no prose summarization."""
import copy
import json

from .baseline_store import digest, encoded
from .case_input_hierarchy import project
from .knowledge_content import project_content


def semantic(row, business, config):
    path = row["ref"].get("source_path") or ""
    field = next((path[len(root):] for root in business["event_roots"] if path.startswith(root)), None)
    if field is None and row.get("typed_raw_alert_envelope"):
        field = {**config["material_field_aliases"], **config["c3_input_selection"]["material_field_aliases"]}.get(path)
    return field


def prior_refs(rows):
    result = []
    for row in rows:
        value = row["original_value"]
        if row["block"] == "triage":
            for item in [value, *value.get("recommendations", [])]:
                result.extend(item.get("source_refs", []))
        elif row["block"] in {"finding", "question"}:
            for key in ("support", "counterevidence", "evidence_refs"):
                result.extend(value.get(key, []))
        elif row["block"] == "incident":
            result.extend(row.get("incident_source_refs", []))
    return result


def serialized_fields(value, available):
    if not isinstance(value, str):
        return value

    def unique(pairs):
        result = {}
        for key, child in pairs:
            if key in result:
                raise ValueError("duplicate_source_key")
            result[key] = child
        return result

    try:
        parsed = json.loads(value, object_pairs_hook=unique)
        encoded(parsed)
    except (ValueError, TypeError):
        return value
    if not isinstance(parsed, (dict, list)):
        return value
    from .incident_model_boundary import fields
    return {path.removeprefix("$."): child for path, child in fields(parsed, "$")
            if (path.removeprefix("$."), digest(child)) not in available}


def select_rows(rows, context, config, business, omissions, *, required_refs=()):
    """Keep each retained ref/subject/scope unchanged, including shared history."""
    policy = config["c3_input_selection"]
    refs = [*prior_refs(rows), *required_refs]
    tools = {r["ref"]["id"]: r["value"].get("tool_name") for r in rows
             if r["ref"]["role"] == "execution_receipt" and isinstance(r["value"], dict)}
    material_values = {}
    for row in rows:
        field = semantic(row, business, config)
        if row["block"] == "material" and field:
            material_values.setdefault(row["ref"]["id"], set()).add((field, digest(row["value"])))

    def required(row):
        ref = row["ref"]
        path = ref.get("source_path") or ""
        return any(r.get("type") == ref["type"] and r.get("id") == ref["id"]
                   and ((r.get("source_path") or "") == path
                        or (r.get("source_path") or "").startswith(path + ".")) for r in refs)

    def omit(row, reason):
        omissions.append({"source_id": row["id"], "ref": copy.deepcopy(row["ref"]),
                          "alert_ids": row["alert_ids"], "reason": reason,
                          "value_sha256": digest(row["value"])})

    histories, kept = {}, []
    for row in rows:
        ref, value = row["ref"], copy.deepcopy(row["value"])
        path, kind = ref.get("source_path") or "", row["block"]
        historical = tools.get(ref["id"]) == "history" and path.startswith("$.rows.")
        if row.get("knowledge") or historical:
            kind = "prior_analysis" if ref["role"] == "prior_analysis" else (
                "human_statement" if ref["role"] == "human_statement" else "knowledge" if row.get("knowledge") else "history")
        elif kind == "material":
            kind = path[2:] if path in {"$.source_scope", "$.detection"} else "material"
        value = project(value, kind, policy, omissions, row["id"])
        if kind == "knowledge" and isinstance(value, dict):
            value = project_content(value, config, omissions, row["id"])
            record = value.get("record", {})
            if record.get("history", {}).get("schema_version") == policy["historical_card_schema"]:
                value["record"] = project(record, "historical_card", policy, omissions, row["id"])
        reason = None
        if row["block"] == "background" and len(row["alert_ids"]) == 1:
            aid = row["alert_ids"][0]
            member = context["alerts"][aid]
            if path == f"$.alerts.{aid}.alert.event_time" and value == {"alert_time": member["alert"].get("event_time")}:
                reason = "same_alert_time_already_visible"
            if path == f"$.alerts.{aid}.objects" and isinstance(value, list) and all(
                    isinstance(obj, dict) and set(obj) <= set(policy["object_index_fields"])
                    and any(all(digest(obj[k]) == digest(full.get(k)) for k in obj)
                            and full["object_key"] in context["scope"]["object_keys"]
                            for full in member.get("objects", [])) for obj in value):
                reason = "object_index_already_in_directory"
        if row["block"] == "material":
            if row.get("typed_raw_alert_envelope") and path in policy["material_backend_paths"]:
                reason = "configured_c3_material_backend_field"
            if path == "$.raw_json.title" and row.get("typed_raw_alert_envelope") and all(
                    context["alerts"][a]["alert"].get("title") == value for a in row["alert_ids"]):
                reason = "same_alert_title_already_visible"
            if kind == "detection" and isinstance(value, dict) and (
                    "class_uid", digest(value.get("ocsf_class_uid"))) in material_values.get(ref["id"], set()):
                value.pop("ocsf_class_uid", None)
            if path == "$.raw_text" or semantic(row, business, config) == "raw_data":
                selected = serialized_fields(value, material_values.get(ref["id"], set()))
                if selected != value:
                    omit(row, "serialized_material_business_fields")
                value = selected
            if value is None or value == {} and (kind in {"source_scope", "detection"} or path == "$.raw_text"
                                                or semantic(row, business, config) == "raw_data"):
                reason = "empty_after_c3_selection"
        if reason and not required(row):
            omit(row, reason)
            continue
        row["value"] = value
        kept.append(row)
        if historical:
            # Full record digest distinguishes versions, not just equal prose.
            identity = row.get("query_record_identity")
            key = tuple(identity[:2]) if identity else (ref["id"], ".".join(path.split(".")[:3]))
            histories.setdefault(key, []).append(row)

    dropped = set()
    for entries in histories.values():
        useful = any(required(r) for r in entries)
        for row in entries:
            value = row["value"]
            if row["ref"]["role"] in {"prior_analysis", "human_statement"}:
                useful |= value not in (None, "", {})
            elif isinstance(value, dict):
                useful |= any(k not in policy["history_catalog_fields"] and v is not None and v != ""
                              for k, v in value.get("record", {}).items())
                useful |= any(k != "record" and v is not None and v != "" for k, v in value.items())
        if not useful:
            for row in entries:
                omit(row, "history_catalog_only")
                dropped.add(row["id"])
    return [r for r in kept if r["id"] not in dropped]


def describe(row, alias):
    """Only the returned subject matters here; receipt details stay backstage."""
    basis = row.get("membership_basis")
    if basis in {"history_record_identity", "history_record_outside_case"}:
        return "历史记录主体=" + "、".join(alias(a) for a in row["record_alert_ids"]) + "。"
    if basis == "history_record_identity_unverified":
        return "历史记录主体未核实。"
    if basis == "query_binding_only" and not row.get("knowledge"):
        return "返回行未确认成员归属。"
    return ""
