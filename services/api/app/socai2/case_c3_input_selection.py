"""Case field selection after original guards; no prose summarization."""
import copy
import json

from .baseline_store import digest, encoded
from .case_context_input import human_refs
from .case_input_hierarchy import project
from .knowledge_content import project_content

UNMAPPED_REASON = "configured_case_unmapped_material"
MISSING = object()


def material_path(value, path):
    """Read only the existing material reference syntax; never guess dotted keys."""
    if path == "$":
        return value
    for key in path.removeprefix("$.").split("."):
        if isinstance(value, dict):
            value = value.get(key, MISSING)
        elif isinstance(value, list) and key.isdecimal() and int(key) < len(value):
            value = value[int(key)]
        else:
            return MISSING
    return value


def within(path, root):
    return path == root or path.startswith(root + ".")


def unmapped_value(value, path, policy):
    """Exclude declared containers even when a dotted business key retains a parent."""
    roots = policy.get("material_unmapped_paths", [])
    if any(within(path, root) for root in roots):
        return MISSING
    selected = copy.deepcopy(value)
    for root in roots:
        if not within(root, path):
            continue
        relative = root[len(path) + 1:].split(".")
        parent = selected
        for key in relative[:-1]:
            parent = parent.get(key, MISSING) if isinstance(parent, dict) else MISSING
        if isinstance(parent, dict):
            parent.pop(relative[-1], None)
    return selected


def unmapped_material(material, policy, omissions):
    """Project fixed OCSF roots and proven same-material JSON wrappers only."""
    roots = policy.get("material_unmapped_paths", [])
    selected = unmapped_value(material, "$", policy)

    def replace(path, value):
        parent_path, key = path.rsplit(".", 1)
        parent = material_path(selected, parent_path)
        if isinstance(parent, dict):
            if value is MISSING:
                parent.pop(key, None)
            else:
                parent[key] = value

    # Only these configured string fields are decoded. Parsing failure or a
    # different structure is not evidence of equivalence or successful filtering.
    parsed = {}
    for path in policy.get("material_unmapped_serialized_paths", []):
        value = material_path(material, path)
        if isinstance(value, str):
            try:
                decoded = json.loads(value, object_pairs_hook=unique_object)
                encoded(decoded)
                if isinstance(decoded, (dict, list)):
                    parsed[path] = decoded
            except (ValueError, TypeError, RecursionError):
                pass
    # Remove exact copies of an excluded container before projecting full OCSF
    # mirrors, so an outer mirror cannot retain its raw_data copy.
    for path, value in parsed.items():
        if any(same_json_value(value, material_path(material, root)) for root in roots):
            replace(path, MISSING)
    objects = [root.removesuffix(".unmapped") for root in roots]
    for path in sorted(parsed, key=lambda p: not p.endswith(".raw_data")):
        if material_path(selected, path) is MISSING:
            continue
        root = next((root for root in objects if isinstance(material_path(material, root), dict)
                     and same_json_value(parsed[path], material_path(material, root))), None)
        if root and not same_json_value(material_path(selected, root), material_path(material, root)):
            replace(path, encoded(material_path(selected, root)).decode())
    for path in dict.fromkeys([*roots, *parsed]):
        original, visible = material_path(material, path), material_path(selected, path)
        if original is not MISSING and (visible is MISSING or not same_json_value(original, visible)):
            omissions.append({"material_id": material["id"], "path": path, "reason": UNMAPPED_REASON,
                              "value_sha256": digest(original)})
    return selected


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
        if row.get("context_kind") == "human_feedback":
            for _, refs in human_refs(value):
                result.extend(refs)
        if row["block"] == "triage":
            for item in [value, *value.get("recommendations", [])]:
                result.extend(item.get("source_refs", []))
        elif row["block"] in {"finding", "question"}:
            for key in ("support", "counterevidence", "evidence_refs"):
                result.extend(value.get(key, []))
        elif row["block"] == "incident":
            result.extend(row.get("incident_source_refs", []))
    return result


def unique_object(pairs):
    result = {}
    for key, child in pairs:
        if key in result:
            raise ValueError("duplicate_source_key")
        result[key] = child
    return result


def same_json_value(left, right):
    """JSON equality includes scalar types, object keys and array positions."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            isinstance(key, str) and same_json_value(child, right[key]) for key, child in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(same_json_value(a, b) for a, b in zip(left, right, strict=True))
    return type(left) in {str, int, float, bool, type(None)} and left == right


def serialized_mirror_path(value, material, path, policy):
    """Compare the complete originals before metadata/field selection loses keys."""
    rule = next((r for r in policy.get("material_mirrors", []) if r["source_path"] == path), None)
    if rule is None or not isinstance(value, str):
        return None
    original = material
    for key in rule["object_path"][2:].split("."):
        if not isinstance(original, dict) or key not in original:
            return None
        original = original[key]
    if not isinstance(original, dict):
        return None
    try:
        parsed = json.loads(value, object_pairs_hook=unique_object)
        encoded(parsed)  # Reject non-finite numbers and invalid JSON strings.
        return rule["object_path"] if same_json_value(parsed, original) else None
    except (ValueError, TypeError, RecursionError):
        return None


def mirror_referenced(ref, refs):
    """A whole material or ancestor attachment also depends on the original text."""
    path = ref.get("source_path") or "$"
    for other in refs:
        if other.get("type") != ref["type"] or other.get("id") != ref["id"]:
            continue
        required = other.get("source_path") or "$"
        if required == path or path.startswith(required + ".") or required.startswith(path + "."):
            return True
    return False


def serialized_fields(value, available):
    if not isinstance(value, str):
        return value
    try:
        parsed = json.loads(value, object_pairs_hook=unique_object)
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
    available_paths = {(r["ref"]["type"], r["ref"]["id"], r["ref"]["role"], r["ref"].get("source_path") or "") for r in rows}
    tools = {r["ref"]["id"]: r["value"].get("tool_name") for r in rows
             if r["ref"]["role"] == "execution_receipt" and isinstance(r["value"], dict)}
    material_values = {}
    incident_overviews = {(r["ref"]["type"], r["ref"]["id"],
                           r["ref"]["source_path"].removesuffix(".diagnosis.conclusion") + ".summary")
                          for r in rows if r["block"] == "incident" and isinstance(r["value"], str)
                          and r["value"].strip() and (r["ref"].get("source_path") or "").endswith(".diagnosis.conclusion")}
    for row in rows:
        field = semantic(row, business, config)
        if row["block"] == "material" and field:
            material_values.setdefault(row["ref"]["id"], set()).add((field, digest(row["value"])))

    def required(row):
        ref = row["ref"]
        path = ref.get("source_path") or ""
        return any(r.get("type") == ref["type"] and r.get("id") == ref["id"]
                   and ((r.get("source_path") or "") == path
                        or ((r.get("source_path") or "").startswith(path + ".")
                            and (r.get("type"), r.get("id"), r.get("role"), r.get("source_path") or "") not in available_paths))
                   for r in refs)

    def omit(row, reason):
        omissions.append({"source_id": row["id"], "ref": copy.deepcopy(row["ref"]),
                          "alert_ids": row["alert_ids"], "reason": reason,
                          "value_sha256": digest(row["value"])})

    kept = []
    for row in rows:
        ref, value = row["ref"], copy.deepcopy(row["value"])
        path, kind = ref.get("source_path") or "", row["block"]
        if kind == "material":
            projected = unmapped_value(value, path, policy)
            if projected is MISSING:
                omit(row, UNMAPPED_REASON)
                continue  # Explicit references cannot restore excluded material.
            if not same_json_value(projected, value):
                omit(row, UNMAPPED_REASON)
                value = projected
                row["visible_observation_value"] = copy.deepcopy(projected)
        if (kind == "material" and row.get("typed_raw_alert_envelope") and row.get("serialized_mirror_of")
                and not mirror_referenced(ref, refs)):
            omit(row, "same_material_serialized_mirror")
            omissions[-1]["equivalent_ref"] = copy.deepcopy(row["serialized_mirror_of"])
            continue
        historical = tools.get(ref["id"]) == "history" and path.startswith("$.rows.")
        if row.get("knowledge") or historical:
            kind = "prior_analysis" if ref["role"] == "prior_analysis" else (
                "human_statement" if ref["role"] == "human_statement" else "knowledge" if row.get("knowledge") else "history")
        elif kind == "material":
            kind = path[2:] if path in {"$.source_scope", "$.detection"} else "material"
        elif (kind in {"query", "background_query"} and path.startswith("$.rows.")
              and path.removeprefix("$.rows.").isdigit()):
            query_kind = f"query_{tools.get(ref['id'])}"
            if query_kind in policy["hierarchy"]:
                kind = query_kind
        value = project(value, kind, policy, omissions, row["id"])
        program_limits = policy.get("incident_program_limitations", [])
        if program_limits and row["block"] in {"incident", "finding", "question"}:
            limits = value if path.endswith(".diagnosis.limitations") else (
                value.get("limitations") if isinstance(value, dict) else None)
            if isinstance(limits, list):
                known = [*program_limits, *(f"triage_not_used:{aid}:{member.get('triage_freshness')}"
                                           for aid, member in context["alerts"].items())]
                selected_limits = [item for item in limits if item not in known]
                if selected_limits != limits:
                    omit(row, "incident_program_markers_not_business_limits")
                    if isinstance(value, list):
                        value = selected_limits
                    else:
                        value["limitations"] = selected_limits
        if kind == "knowledge" and isinstance(value, dict):
            value = project_content(value, config, omissions, row["id"])
            record = value.get("record", {})
            if record.get("history", {}).get("schema_version") == policy["historical_card_schema"]:
                value["record"] = project(record, "historical_card", policy, omissions, row["id"])
        reason = None
        if row["block"] == "incident" and path.endswith(".diagnosis.limitations") and value == []:
            reason = "incident_no_business_limitations"
        if (policy.get("omit_unusable_prior_results") and row.get("context_kind") == "prior_result"
                and isinstance(value, dict) and not value.get("conclusion")):
            reason = "no_historical_judgment_for_c3"
        if (policy.get("prefer_incident_conclusion") and row["block"] == "incident"
                and (ref["type"], ref["id"], path) in incident_overviews):
            reason = "incident_conclusion_and_findings_used_instead_of_overview"
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
            if row.get("typed_raw_alert_envelope"):
                backend = next((root for root in policy["material_backend_paths"]
                                if path == root or path.startswith(root + ".")), None)
                # Opt in only the new subtree; existing exact-reference
                # behavior for other backend fields remains below in required().
                protected = backend in policy.get("material_backend_reference_paths", []) and mirror_referenced(ref, refs)
                if backend is not None and not protected:
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
        if historical:
            # Select each projected part independently. A useful judgment or
            # human statement does not make its catalog wrapper evidence.
            useful = value not in (None, "", {}) if ref["role"] in {"prior_analysis", "human_statement"} else False
            if ref["role"] not in {"prior_analysis", "human_statement"} and isinstance(value, dict):
                useful = any(k not in policy["history_catalog_fields"] and v is not None and v != ""
                             for k, v in value.get("record", {}).items())
                useful |= any(k != "record" and v is not None and v != "" for k, v in value.items())
            if not useful:
                reason = "history_catalog_only"
        if reason and not required(row):
            omit(row, reason)
            continue
        row["value"] = value
        if "visible_observation_value" in row:
            row["visible_observation_value"] = copy.deepcopy(value)
        kept.append(row)
    return kept


def describe(row, alias):
    """Only the returned subject matters here; receipt details stay backstage."""
    basis = row.get("membership_basis")
    if basis == "history_record_outside_case":
        return "案件外历史参考｜原主体=" + "、".join(alias(a) for a in row["record_alert_ids"]) + "；不证明本案成员事实。"
    if basis == "history_record_identity":
        return "历史记录主体=" + "、".join(alias(a) for a in row["record_alert_ids"]) + "。"
    if basis == "history_record_identity_unverified":
        return "历史记录主体未核实。"
    if basis == "query_binding_only" and not row.get("knowledge"):
        return "返回行未确认成员归属。"
    return ""
