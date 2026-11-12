"""Structural projection only. Never summarize, correct or extract prose claims."""
import copy
import json

from .baseline_store import digest
from .incident_input_text import matches
from .program_facts import query_result_text


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def empty(value):
    return value is None or value == ""


def rows(data):
    if "items" in data:
        return data["items"]
    return [{**{k: v for k, v in g.items() if k != "items"}, **item}
            for g in data["source_groups"] for item in g["items"]]


def event_path(path):
    for root in ("$.raw_json.raw_event.ocsf_event.", "$.ocsf_json."):
        if path.startswith(root):
            return path[len(root):]
    return None


def prepare(data, source_map, config):
    cfg = config["render"]
    omissions, preserved_texts, fragments, visible, dedup = [], [], [], {}, {}
    facts, selected_values = [], {}

    def semantic(path):
        return event_path(path) or (cfg["raw_field_aliases"].get(path) if data.get("raw_alert_envelope") else None)

    items = rows(data)
    material_values = {}
    for item in items:
        ref = source_map[item["id"]]["ref"]
        field = semantic(item["field"])
        if field and ref["type"] == "alert_material":
            material_values.setdefault(ref["id"], set()).add((field, encoded(item["value"])))
    observed = {(semantic(i["field"]), encoded(i["value"])) for i in items if i["role"] == "observation"}
    classes = {encoded(i["value"]) for i in items if semantic(i["field"]) == "class_uid"}
    alerts = [i["value"] for i in items if matches("$.members.*.alert", i["field"])]

    def redundant_object(value):
        if not isinstance(value, dict) or not set(value) <= set(cfg["object_index_keys"]):
            return False
        raw = value.get("raw_value")
        return (raw is not None and encoded(value.get("normalized_value", raw)) == encoded(raw)
                and any((path, encoded(raw)) in observed for path in cfg["object_paths"].get(value.get("object_type"), [])))

    def clean(value, path):
        if isinstance(value, dict):
            if path == "$.enrichment" and value.get("schema_version") == cfg["enrichment_schema"]:
                kept = []
                for index, item in enumerate(value.get("items", [])):
                    fields = cfg["backend_enrichment_items"].get(item.get("kind")) if isinstance(item, dict) else None
                    if (fields is not None and set(item) <= {"kind", "source", "collected_at", "source_path", "value"}
                            and isinstance(item.get("value"), dict) and set(item["value"]) <= set(fields)):
                        omissions.append({"path": f"{path}.items.{index}", "reason": "program_metadata", "original": item})
                    else:
                        kept.append(item)
                value = {**value, "items": kept}
            result = {}
            rules = [rule for pattern, rule in cfg["container_rules"].items() if matches(pattern, path)]
            for key, item in value.items():
                child = path + "." + key
                if ((path == "$.detection" and key == "ocsf_class_uid" and encoded(item) in classes)
                        or (matches("$.members.*.alert", path) and key == "event_time"
                            and any(row["field"] == child and row["value"] == item for row in items))):
                    omissions.append({"path": child, "reason": "same_business_field_already_present", "original": item})
                    continue
                if any(key in rule["omit"] for rule in rules):
                    omissions.append({"path": child, "reason": "program_metadata", "original": item})
                    continue
                if any(key in rule["empty_optional"] for rule in rules) and (empty(item) or item in ([], {})):
                    omissions.append({"path": child, "reason": "empty_optional", "original": item})
                    continue
                item = clean(item, child)
                if any(key in rule["empty_optional"] for rule in rules) and item in (None, "", [], {}):
                    omissions.append({"path": child, "reason": "empty_optional_after_projection"})
                    continue
                if not empty(item):
                    result[key] = item
            return result
        if isinstance(value, list):
            result = []
            for index, child in enumerate(value):
                selected = clean(child, f"{path}.{index}")
                if matches("$.members.*.objects", path) and redundant_object(selected):
                    omissions.append({"path": f"{path}.{index}", "reason": "object_already_in_observation", "original": child})
                else:
                    result.append(selected)
            return result
        return value

    def serialized_fields(value, ref):
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
            encoded(parsed)  # Nonfinite values cannot become structured fields.
        except (ValueError, TypeError):
            return value
        if not isinstance(parsed, (dict, list)):
            return value
        from .incident_model_boundary import fields
        selected = {path.removeprefix("$."): child for path, child in fields(parsed, "$")
                    if (path.removeprefix("$."), encoded(child)) not in material_values.get(ref["id"], set())}
        omissions.append({"path": ref["source_path"], "reason": "serialized_material_business_fields",
                          "original": value, "selected_fields": list(selected)})
        return selected

    def remember(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                remember(child, path + "." + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                remember(child, path + f".{index}")
        elif isinstance(value, str) and value:
            preserved_texts.append({"path": path, "value": value})

    def show(sid, value):
        visible[sid] = {**copy.deepcopy(source_map[sid]), "visible_value_sha256": digest(value)}
        selected_values[sid] = copy.deepcopy(value)

    children = {}
    for item in items:
        if item["origin"] == "history" and item["role"] in {"prior_analysis", "human_statement"}:
            key = source_map[item["id"]]["ref"]["id"], ".".join(item["field"].split(".")[:3])
            children.setdefault(key, []).append(item)
    history = {}
    for item in items:
        value = item["value"]
        if (item["origin"] == "history" and item["role"] == "source_label"
                and isinstance(value, dict) and value.get("record_id") and isinstance(value.get("record"), dict)):
            ref = source_map[item["id"]]["ref"]
            linked = children.get((ref["id"], item["field"]), [])
            key = (ref["id"], value["record_id"], encoded(value["record"]),
                   tuple((child["role"], encoded(child["value"])) for child in linked))
            history.setdefault(key, []).append(item)
    history_by_id = {item["id"]: group for group in history.values() for item in group}

    for item in items:
        sid, path, value = item["id"], item["field"], item["value"]
        ref = source_map[sid]["ref"]
        if sid in history_by_id:
            group = history_by_id[sid]
            if sid != group[0]["id"]:
                continue
            merged = clean({"record": value["record"]}, path)
            linked = children.get((ref["id"], path), [])
            judgment = any(clean(child["value"], child["field"]) for child in linked)
            business = any(key not in cfg["history_catalog_fields"] and not empty(child)
                           for key, child in merged["record"].items())
            if not judgment and not business:
                omissions.extend({"path": row["field"], "source_id": row["id"], "reason": "history_catalog_only"} for row in group)
                continue
            for row in group:
                show(row["id"], merged)
            remember(merged, path)
            fragments.append(f"[{','.join(row['id'] for row in group)}｜关联历史记录] {encoded(merged['record'])}")
            omissions.extend({"path": row["field"], "source_id": row["id"], "reason": "history_matching_kept_in_backend"} for row in group)
            if len(group) > 1:
                omissions.append({"path": path, "reason": "same_history_record_match_relations_combined",
                                  "source_paths": [row["field"] for row in group]})
            continue
        if path in cfg["known_metadata_paths"]:
            omissions.append({"path": path, "reason": "program_metadata", "original": value})
            continue
        if data.get("raw_alert_envelope") and path.startswith("$.raw_json."):
            tail = path.removeprefix("$.raw_json.")
            if any(tail == key or tail.startswith(key + ".") for key in cfg["raw_alert_envelope"]["backend_fields"]):
                omissions.append({"path": path, "reason": "program_metadata", "original": value})
                continue
            if tail in cfg["raw_alert_envelope"]["empty_optional"] and value in (None, "", [], {}):
                omissions.append({"path": path, "reason": "empty_optional", "original": value})
                continue
            mirror = cfg["raw_alert_mirrors"].get(path)
            if mirror and any(alert.get(mirror) == value for alert in alerts):
                omissions.append({"path": path, "reason": "same_frozen_alert_field", "original": value})
                continue
        if empty(value):
            omissions.append({"path": path, "reason": "empty_optional", "original": value})
            continue
        ep = semantic(path)
        # Only same-material, same-field, same-role and identical values fold.
        identity = (ref["type"], ref["id"], item["role"], ep, encoded(value)) if ep else None
        if item["role"] in {"prior_analysis", "human_statement"} and isinstance(value, dict) and value.get("id"):
            identity = (ref["type"], ref["id"], item["role"], value["id"], encoded(value))
        if identity is not None and identity in dedup:
            omissions.append({"path": path, "reason": "same_source_same_value", "alias_of": dedup[identity], "original": value})
            continue
        if identity is not None:
            dedup[identity] = sid
        role = cfg["roles"][item["role"]]
        if ep and not isinstance(value, (dict, list)):
            if path in cfg["serialized_material_paths"]:
                selected = serialized_fields(value, ref)
                if selected != value:
                    if selected:
                        show(sid, selected)
                        remember(selected, path)
                        fragments.append(f"[{sid}｜{role}] 原记录补充字段：{encoded(selected)}")
                    continue
            show(sid, value)
            label = cfg["field_labels"].get(ep, ep)
            shown = encoded(value)
            if ep == "activity.action" and value in cfg["actions"]:
                shown = cfg["actions"][value] + "（" + value + "）"
            if ep == "activity.outcome" and value in cfg["outcomes"]:
                shown = cfg["outcomes"][value] + "（" + value + "）"
            part = f"{label}={shown}"
            fragments.append(f"[{sid}｜{role}] {part}")
            if item["role"] == "observation":
                facts.append((part, ref))
            if isinstance(value, str):
                preserved_texts.append({"path": path, "value": value})
        else:
            # Free strings are inserted verbatim. Only known structured
            # containers lose explicit program-only keys.
            structured_container = path.startswith(("$.members.", "$.rows.")) or path in {"$.detection", "$.source_scope", "$.enrichment"}
            selected = clean(value, path) if structured_container else value
            if path in cfg["serialized_material_paths"]:
                selected = serialized_fields(selected, ref)
            if (structured_container or path in cfg["serialized_material_paths"]) and selected in ({}, []):
                omissions.append({"path": path, "reason": "no_additional_business_content", "original": value})
                continue
            show(sid, selected)
            remember(selected, path)
            if isinstance(selected, str):
                preserved_texts.append({"path": path, "value": selected})
                text = selected
            else:
                text = encoded(selected)
            label = next((label for pattern, label in cfg["block_labels"].items() if matches(pattern, path)), path)
            fragments.append(f"[{sid}｜{role}] {label}：{text}")
            if item["role"] == "observation":
                facts.append((text, ref))

    queries = [query_result_text(state, cfg["queries"])
               for state in data.get("program_facts", {}).get("query_statuses", [])]
    # Program facts that matter beyond duplicated identifiers/time are retained.
    other_facts = []
    for member in data.get("program_facts", {}).get("members", []):
        selected = {}
        if member.get("activity_time_state") not in (None, "available"):
            selected["活动时间"] = "未提供"
        labels = member.get("detection_labels", {}).get("entries")
        if labels:
            selected["detection_labels"] = labels
        if selected:
            other_facts.append(encoded(selected))
    user = "\n".join([cfg["task"], *fragments, "[查询结果]", *queries,
                      *other_facts,
                      *([] if data.get("stored_material_state") == "complete" else ["原材料不可用"])])
    # JSON string quoting is reversible; source strings themselves are not rewritten.
    assert all(t["value"] in user or encoded(t["value"]) in user for t in preserved_texts)
    return {"user": user, "source_map": visible, "data": copy.deepcopy(data),
            "omissions": omissions, "preserved_texts": preserved_texts,
            "selected_values": selected_values,
            "fact_text": "；".join(t for t, _ in facts), "fact_refs": [ref for _, ref in facts]}
