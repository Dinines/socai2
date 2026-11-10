"""Structural projection only. Never summarize, correct or extract prose claims."""
import copy
import json

from .incident_input_text import matches


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
    facts = []

    def clean(value, path):
        if isinstance(value, dict):
            result = {}
            rules = [rule for pattern, rule in cfg["container_rules"].items() if matches(pattern, path)]
            for key, item in value.items():
                child = path + "." + key
                if any(key in rule["omit"] for rule in rules):
                    omissions.append({"path": child, "reason": "program_metadata", "original": item})
                    continue
                if any(key in rule["empty_optional"] for rule in rules) and (empty(item) or item in ([], {})):
                    omissions.append({"path": child, "reason": "empty_optional", "original": item})
                    continue
                item = clean(item, child)
                if not empty(item):
                    result[key] = item
            return result
        if isinstance(value, list):
            return [clean(v, f"{path}.{i}") for i, v in enumerate(value)]
        if isinstance(value, str) and value:
            preserved_texts.append({"path": path, "value": value})
        return value

    items = rows(data)
    history = {}
    for item in items:
        value = item["value"]
        if (item["origin"] == "history" and item["role"] == "source_label"
                and isinstance(value, dict) and value.get("record_id") and isinstance(value.get("record"), dict)):
            ref = source_map[item["id"]]["ref"]
            key = (ref["id"], value["record_id"], encoded(value["record"]))
            history.setdefault(key, []).append(item)
    history_by_id = {item["id"]: group for group in history.values() for item in group}

    for item in items:
        sid, path, value = item["id"], item["field"], item["value"]
        ref = source_map[sid]["ref"]
        if sid in history_by_id:
            group = history_by_id[sid]
            if sid != group[0]["id"]:
                continue
            matching = [{k: v for k, v in row["value"].items() if k not in {"record", "record_id"}} for row in group]
            merged = clean({"record": value["record"], "matched_by": matching}, path)
            for row in group:
                visible[row["id"]] = copy.deepcopy(source_map[row["id"]])
            fragments.append(f"[{','.join(row['id'] for row in group)}｜关联历史记录] {encoded(merged)}")
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
        if empty(value):
            omissions.append({"path": path, "reason": "empty_optional", "original": value})
            continue
        ep = event_path(path)
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
        visible[sid] = copy.deepcopy(source_map[sid])
        if ep and not isinstance(value, (dict, list)):
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
            if isinstance(selected, str):
                preserved_texts.append({"path": path, "value": selected})
                text = selected
            else:
                text = encoded(selected)
            fragments.append(f"[{sid}｜{role}｜{item['origin']}] {path}：{text}")
            if item["role"] == "observation":
                facts.append((text, ref))

    queries = []
    for state in data.get("program_facts", {}).get("query_statuses", []):
        name = cfg["queries"].get(state["source"], state["source"])
        status = cfg["query_outcomes"].get(state["outcome"], state["outcome"])
        details = {k: state[k] for k in ("returned_rows", "reason", "truncated") if not empty(state.get(k))}
        queries.append(f"{name}：{status}；{encoded(details)}。")
    # Program facts that matter beyond duplicated identifiers/time are retained.
    other_facts = []
    for member in data.get("program_facts", {}).get("members", []):
        selected = {k: member[k] for k in ("activity_time_state", "log_severity", "unavailable_fields") if not empty(member.get(k))}
        labels = member.get("detection_labels", {}).get("entries")
        if labels:
            selected["detection_labels"] = labels
        if selected:
            other_facts.append(encoded(selected))
    user = "\n".join([cfg["task"], *fragments, "[本次查询｜程序事实]", *queries,
                      *other_facts, cfg["query_rule"],
                      "材料状态=" + str(data.get("stored_material_state", "unknown"))])
    # JSON string quoting is reversible; source strings themselves are not rewritten.
    assert all(t["value"] in user or encoded(t["value"]) in user for t in preserved_texts)
    return {"user": user, "source_map": visible, "data": copy.deepcopy(data),
            "omissions": omissions, "preserved_texts": preserved_texts,
            "fact_text": "；".join(t for t, _ in facts), "fact_refs": [ref for _, ref in facts]}
