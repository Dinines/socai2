"""Project known I structures into business text; keep the full backend ledger."""
import copy
import hashlib
import json
import re


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def rows(data):
    if "items" in data:
        return data["items"]
    return [{**{k: v for k, v in group.items() if k != "items"}, **item}
            for group in data["source_groups"] for item in group["items"]]


def matches(pattern, path):
    # The wildcard addresses array positions, never arbitrary business keys.
    return re.fullmatch(re.escape(pattern).replace(r"\*", r"[0-9]+"), path) is not None


def empty(value):
    return value is None or value == "" or isinstance(value, (dict, list)) and not value


def prepare(data, source_map, config):
    cfg, items = config["render"], rows(data)
    aids = [m["alert_id"] for m in data["members"]]
    if len(aids) != len(set(aids)):
        raise ValueError("duplicate_input_member")
    aliases = {aid: cfg["member_prefix"] + str(i) for i, aid in enumerate(aids, 1)}
    omissions, visible, records, grouped = [], {}, [], {}
    query_names = {source_map[item["id"]]["ref"]["id"]: cfg["query_names"].get(item["value"].get("tool_name"), item["value"].get("tool_name"))
                   for item in items if item["role"] == "execution_receipt" and item["id"] in source_map}

    def omit(path, value, reason):
        omissions.append({"path": path, "original": copy.deepcopy(value), "reason": reason})

    def semantic(path):
        if path == "$.raw_text":
            return "raw_text"
        if path is None:
            return None
        return next((path[len(root):] for root in cfg["event_roots"] if path.startswith(root)), None)

    seen, observed, classes, materials = set(), set(), set(), {}
    for item in items:
        sid, path, owners = item["id"], item["field"], item.get("alert_ids", [])
        if sid in seen or sid not in source_map:
            raise ValueError("duplicate_or_unknown_source")
        seen.add(sid)
        source = source_map[sid]
        if (owners != source.get("alert_ids", []) or any(aid not in aliases for aid in owners)
                or item["role"] != source["ref"]["role"] or path != source["ref"]["source_path"]):
            raise ValueError("source_ownership_or_path_mismatch")
        ep = semantic(path)
        if ep and source["ref"]["type"] == "alert_material":
            for aid in owners:
                materials.setdefault(aid, set()).add(source["ref"]["id"])
                if item["role"] == "observation":
                    observed.add((aid, ep, encoded(item["value"])))
                if ep == "class_uid":
                    classes.add((aid, encoded(item["value"])))

    def redundant_object(value, owners):
        if (not isinstance(value, dict) or not set(value) <= set(cfg["object_index_keys"])
                or not owners or any(len(materials.get(aid, ())) != 1 for aid in owners)):
            return False
        raw = value.get("raw_value")
        if raw is None or encoded(value.get("normalized_value", raw)) != encoded(raw):
            return False
        paths = cfg["object_paths"].get(value.get("object_type"), [])
        return all(any((aid, path, encoded(raw)) in observed for path in paths) for aid in owners)

    def select(value, path, owners):
        if isinstance(value, list):
            selected = []
            for i, item in enumerate(value):
                child = select(item, path + f".{i}", owners)
                if matches("$.members.*.objects", path) and redundant_object(child, owners):
                    omit(path + f".{i}", item, "object_index_repeats_visible_observation")
                else:
                    selected.append(child)
            return selected
        if not isinstance(value, dict):
            return value
        selected = copy.deepcopy(value)
        if path == "$.enrichment" and selected.get("schema_version") == cfg["enrichment_schema"]:
            kept = []
            for index, item in enumerate(selected.get("items", [])):
                fields = cfg["backend_enrichment_items"].get(item.get("kind")) if isinstance(item, dict) else None
                if (fields is not None and set(item) <= {"kind", "source", "collected_at", "source_path", "value"}
                        and isinstance(item.get("value"), dict) and set(item["value"]) <= set(fields)):
                    omit(path + f".items.{index}", item, "backend_enrichment_reference")
                else:
                    kept.append(item)
            selected["items"] = kept
        for pattern, rule in cfg["container_rules"].items():
            if matches(pattern, path):
                for key in rule["omit"]:
                    if key in selected:
                        omit(path + "." + key, selected.pop(key), "backend_field")
                for key in rule["empty_optional"]:
                    if key in selected and empty(selected[key]):
                        omit(path + "." + key, selected.pop(key), "empty_optional")
        if path == "$.detection" and "ocsf_class_uid" in selected and owners:
            value = selected["ocsf_class_uid"]
            if all((aid, encoded(value)) in classes for aid in owners):
                omit(path + ".ocsf_class_uid", selected.pop("ocsf_class_uid"), "type_already_present")
        if (matches("$.members.*.alert", path) and "event_time" in selected
                and any(item["field"] == path + ".event_time" and item.get("alert_ids") == owners
                        and item["value"] == selected["event_time"] for item in items)):
            omit(path + ".event_time", selected.pop("event_time"), "same_alert_time_already_present")
        selected = {key: select(child, path + "." + key, owners) for key, child in selected.items()}
        for pattern, rule in cfg["container_rules"].items():
            if matches(pattern, path):
                for key in rule["empty_optional"]:
                    if key in selected and empty(selected[key]):
                        omit(path + "." + key, selected.pop(key), "empty_after_projection")
        return selected

    for item in items:
        sid, path, original = item["id"], item["field"], item["value"]
        source, owners = source_map[sid], item.get("alert_ids", [])
        envelope = cfg["raw_alert_envelope"]
        if path and owners and all(aid in data.get("raw_alert_envelopes", []) for aid in owners):
            removed = any(path == "$.raw_json." + key or path.startswith("$.raw_json." + key + ".")
                          for key in envelope["backend_fields"])
            absent = path in ["$.raw_json." + key for key in envelope["empty_optional"]] and empty(original)
            if removed or absent:
                omit(path, original, "raw_alert_backend_field" if removed else "empty_optional")
                omissions[-1]["source_id"] = sid
                continue
        if path is not None and (path in cfg["metadata_paths"] or any(matches(p, path) for p in cfg["out_of_task_paths"])):
            omit(path, original, "out_of_task" if path not in cfg["metadata_paths"] else "program_metadata")
            omissions[-1]["source_id"] = sid
            continue
        value = select(original, path, owners) if path is not None else original
        known = path is not None and (any(matches(p, path) for p in cfg["container_rules"]) or matches("$.members.*.objects", path))
        if known and empty(value):
            omit(path, original, "no_additional_business_content")
            omissions[-1]["source_id"] = sid
            continue
        ep = semantic(path)
        header = (tuple(aliases[aid] for aid in owners), item["role"])
        identity = (header, source["ref"]["type"], source["ref"]["id"], ep, encoded(value)) if ep and not isinstance(value, (dict, list)) else None
        record = grouped.get(identity) if identity else None
        if record is None:
            field = cfg["field_labels"].get(ep, ep or path)
            if path and path.endswith(".alert.event_time"):
                field = cfg["text_field_labels"]["event_time"]
            if item["role"] == "execution_receipt":
                field = cfg["query_names"].get(value.get("tool_name"), value.get("tool_name", "查询")) + "执行情况"
            if path and path.startswith("$.rows.") and source["ref"]["id"] in query_names:
                field = query_names[source["ref"]["id"]] + cfg["query_row_labels"][item["role"]]
            record = {"source_ids": [], "header": header, "field": field, "semantic_field": ep,
                      "container_known": known, "value": value, "source_paths": []}
            records.append(record)
            if identity:
                grouped[identity] = record
        record["source_ids"].append(sid)
        record["source_paths"].append(path)
        visible[sid] = {**copy.deepcopy(source), "visible_value_sha256": digest(value)}

    def atom(value, key=None):
        mapping = cfg["field_values"].get(key, {})
        if type(value).__name__ == mapping.get("type") and str(value) in mapping.get("values", {}):
            return mapping["values"][str(value)]
        return value if isinstance(value, str) else encoded(value)

    def container(value):
        if isinstance(value, dict):
            priority = cfg["text_field_order"]
            keys = sorted(value, key=lambda key: priority.index(key) if key in priority else len(priority))
            return "；".join(cfg["text_field_labels"].get(key, key) + "：" + atom(value[key], key) for key in keys)
        return encoded(value)

    notices, context = {}, []

    def notice(aid, key, **values):
        text = cfg["notices"][key].format(**values)
        owners = notices.setdefault(text, [])
        if aliases[aid] not in owners:
            owners.append(aliases[aid])

    for index, member in enumerate(data["members"]):
        aid = member["alert_id"]
        omit(f"$.members.{index}", member, "backend_input_coverage")
        if member["stored_material_state"] != "complete":
            notice(aid, "material_unavailable")
        prior = any(aid in v["alert_ids"] and v["ref"]["role"] == "prior_analysis"
                    and v["ref"]["source_path"] == f"$.members.{index}.triage" for v in visible.values())
        if not prior:
            notice(aid, "triage_unavailable")
        elif not member.get("triage_eligible") or member.get("triage_freshness") != "current":
            notice(aid, "triage_stale")
        if member.get("omitted", 0) or member.get("view_coverage") == "partial":
            notice(aid, "input_omitted")
        if not member.get("queries_available"):
            notice(aid, "queries_unavailable")

    facts = copy.deepcopy(data.get("program_facts", {}))
    omit("$.program_facts", facts, "full_program_facts_retained_in_backend")
    for fact in facts.get("members", []):
        aid = fact.get("alert", {}).get("id")
        if aid not in aliases:
            raise ValueError("program_fact_member_unknown")
        alias, index = aliases[aid], aids.index(aid)
        if fact.get("activity_time_state") not in (None, "available"):
            notice(aid, "activity_time_unavailable")
        if fact.get("unavailable_fields"):
            notice(aid, "fields_unavailable", fields="、".join(fact["unavailable_fields"]))
        labels = fact.get("detection_labels", {}).get("entries", [])
        if labels:
            context.append(f"{alias} 检测标签释义（仅背景）：" + encoded(labels))
        # Preserve business facts that were available ONLY in program_facts.
        # Do not turn their backend references into independent new evidence.
        for entry in fact.get("activity_times", []):
            if not any(v["ref"] == entry.get("source") and any(sid in r["source_ids"] and r["value"] == entry.get("value")
                       for r in records) for sid, v in visible.items()):
                context.append(f"{alias} 活动时间：" + encoded({k: v for k, v in entry.items() if k != "source"}))
        for key in ("title", "description", "event_time"):
            value = fact.get("alert", {}).get(key)
            if empty(value):
                continue
            present = any(alias in r["header"][0] and (
                isinstance(r["value"], dict) and r["value"].get(key) == value and f"$.members.{index}.alert" in r["source_paths"]
                or r["value"] == value and f"$.members.{index}.alert.{key}" in r["source_paths"]) for r in records)
            if not present:
                context.append(alias + " " + cfg["text_field_labels"][key] + "：" + atom(value))
        objects = select(fact.get("objects", []), f"$.members.{index}.objects", [aid])
        if objects and not any(alias in r["header"][0] and r["value"] == objects and
                               f"$.members.{index}.objects" in r["source_paths"] for r in records):
            context.append(f"{alias} 其他对象背景：" + encoded(objects))
        extra = {k: v for k, v in fact.items() if k not in cfg["member_fact_backend_keys"] and not empty(v)}
        if extra:
            context.append(f"{alias} 其他已提供资料：" + encoded(extra))
    extra = {k: v for k, v in facts.items() if k not in cfg["program_backend_keys"] and not empty(v)}
    if extra:
        context.append("其他已提供资料：" + encoded(extra))

    order = {alias: i for i, alias in enumerate(aliases.values())}
    records.sort(key=lambda r: (tuple(order[a] for a in r["header"][0]) or (-1,),
                               cfg["role_order"].index(r["header"][1])))
    blocks = [cfg["task"], "本轮成员：" + "、".join(aliases.values()) + "。"]
    if notices:
        blocks.append("[实际材料限制｜程序提供]")
        blocks.extend("、".join(owners) + "：" + text for text, owners in notices.items())
    last = None
    for record in records:
        owners, role = record["header"]
        if record["header"] != last:
            blocks.append("[" + ("、".join(owners) or "事件背景") + "｜" + cfg["roles"][role] + "]")
            last = record["header"]
        label = "[" + ",".join(record["source_ids"]) + "] "
        if role == "execution_receipt":
            value = record["value"]
            parts = [record["field"] + "：" + value["statement"]]
            for key in cfg["query_text_fields"]:
                if key in value and not empty(value[key]):
                    parts.append(cfg["query_text_fields"][key] + "：" + atom(value[key]))
            text = "；".join(parts)
        elif isinstance(record["value"], dict) and record["container_known"]:
            text = container(record["value"])
        else:
            text = record["field"] + "：" + atom(record["value"], record["semantic_field"])
        record["rendered_text"] = text
        blocks.append(label + text)
    if context:
        blocks += ["[补充业务背景｜程序提供]", *context]
    return {"user": "\n".join(blocks), "data": copy.deepcopy(data), "source_map": visible,
            "member_aliases": aliases, "records": records, "omissions": omissions,
            "material_notices": notices, "program_context": context,
            "program_facts": facts, "original_source_map": copy.deepcopy(source_map)}
