"""Project known I structures into business text; keep the full backend ledger."""
import copy
import hashlib
import json
import re

from .program_facts import query_result_text


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
    local = cfg["incident_only"]
    container_rules = copy.deepcopy(cfg["container_rules"])
    for pattern, names in local["container_omit"].items():
        container_rules[pattern]["omit"].extend(names)
    roles = {**cfg["roles"], **local["roles"]}
    aids = [m["alert_id"] for m in data["members"]]
    if len(aids) != len(set(aids)):
        raise ValueError("duplicate_input_member")
    aliases = {aid: cfg["member_prefix"] + str(i) for i, aid in enumerate(aids, 1)}
    omissions, visible, records, grouped = [], {}, [], {}
    query_tools = {source_map[item["id"]]["ref"]["id"]: item["value"].get("tool_name")
                   for item in items if item["role"] == "execution_receipt" and item["id"] in source_map}
    query_names = {identity: cfg["query_names"].get(tool, tool) for identity, tool in query_tools.items()}

    def omit(path, value, reason):
        omissions.append({"path": path, "original": copy.deepcopy(value), "reason": reason})

    def semantic(path, owners):
        if path == "$.raw_text":
            return "raw_text"
        if path is None:
            return None
        field = next((path[len(root):] for root in cfg["event_roots"] if path.startswith(root)), None)
        if not field and owners and all(aid in data.get("raw_alert_envelopes", []) for aid in owners):
            field = cfg["raw_field_aliases"].get(path)
        return field

    seen, observed, classes, materials, material_values = set(), set(), set(), {}, {}
    for item in items:
        sid, path, owners = item["id"], item["field"], item.get("alert_ids", [])
        if sid in seen or sid not in source_map:
            raise ValueError("duplicate_or_unknown_source")
        seen.add(sid)
        source = source_map[sid]
        if (owners != source.get("alert_ids", []) or any(aid not in aliases for aid in owners)
                or item["role"] != source["ref"]["role"] or path != source["ref"]["source_path"]):
            raise ValueError("source_ownership_or_path_mismatch")
        ep = semantic(path, owners)
        if ep and source["ref"]["type"] == "alert_material":
            material_values.setdefault(source["ref"]["id"], set()).add((ep, encoded(item["value"])))
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
        for pattern, rule in container_rules.items():
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
        for pattern, rule in container_rules.items():
            if matches(pattern, path):
                for key in rule["empty_optional"]:
                    if key in selected and empty(selected[key]):
                        omit(path + "." + key, selected.pop(key), "empty_after_projection")
        return selected

    def serialized_fields(value, source):
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
        selected = {path.removeprefix("$."): child for path, child in fields(parsed, "$")
                    if (path.removeprefix("$."), encoded(child)) not in material_values.get(source["ref"]["id"], set())}
        omit(source["ref"]["source_path"], value, "serialized_material_business_fields")
        return selected

    # Decide history selection per original row, including its separately typed
    # judgment and feedback. A full record digest prevents merging versions.
    history_rows, history_values, history_keys = {}, {}, {}
    for item in items:
        src = source_map[item["id"]]
        path = item["field"] or ""
        if query_tools.get(src["ref"]["id"]) != "history" or not path.startswith("$.rows."):
            continue
        row = (src["ref"]["id"], ".".join(path.split(".")[:3]))
        history_rows.setdefault(row, []).append(item)
        history_values[item["id"]] = select(item["value"], path, item.get("alert_ids", []))
        identity = src.get("query_record_identity")
        history_keys[row] = tuple(identity[:2]) if identity else row
    required = {tuple(row) for row in data.get("required_history_rows", [])}
    useful_history = set()
    for row, entries in history_rows.items():
        useful = row in required
        for item in entries:
            value = history_values[item["id"]]
            if item["role"] in {"prior_analysis", "human_statement"}:
                useful |= not empty(value)
            elif isinstance(value, dict):
                record = value.get("record", {})
                useful |= any(key not in cfg["history_catalog_fields"] and child is not None and child != ""
                              for key, child in record.items())
                useful |= any(key != "record" and child is not None and child != "" for key, child in value.items())
        if useful:
            useful_history.add(history_keys[row])
    history_labels = {}
    alert_values = {tuple(item.get("alert_ids", [])): item["value"] for item in items
                    if item["field"] and matches("$.members.*.alert", item["field"])}
    prior_targets = {}
    for item in items:
        identity = source_map[item["id"]].get("analysis_identity")
        if identity and item["field"] and matches("$.members.*.triage", item["field"]):
            value = select(item["value"], item["field"], item["alert_ids"])
            prior_targets[(tuple(identity), encoded(value))] = [aliases[aid] for aid in item["alert_ids"]]

    for item in items:
        sid, path, original = item["id"], item["field"], item["value"]
        source, owners = source_map[sid], item.get("alert_ids", [])
        history_label = None
        if sid in history_values:
            key = history_keys[(source["ref"]["id"], ".".join(path.split(".")[:3]))]
            if key not in useful_history:
                omit(path, original, "history_catalog_only")
                omissions[-1]["source_id"] = sid
                continue
            history_label = history_labels.setdefault(key, cfg["history_prefix"] + str(len(history_labels) + 1))
        envelope = cfg["raw_alert_envelope"]
        if path and owners and all(aid in data.get("raw_alert_envelopes", []) for aid in owners):
            removed = any(path == "$.raw_json." + key or path.startswith("$.raw_json." + key + ".")
                          for key in [*envelope["backend_fields"], *local["raw_alert_backend_fields"]])
            absent = path in ["$.raw_json." + key for key in envelope["empty_optional"]] and empty(original)
            if removed or absent:
                omit(path, original, "raw_alert_backend_field" if removed else "empty_optional")
                omissions[-1]["source_id"] = sid
                continue
            mirror = cfg["raw_alert_mirrors"].get(path)
            if mirror and alert_values.get(tuple(owners), {}).get(mirror) == original:
                omit(path, original, "same_frozen_alert_field")
                omissions[-1]["source_id"] = sid
                continue
        if path is not None and (path in cfg["metadata_paths"] or any(matches(p, path) for p in cfg["out_of_task_paths"])):
            omit(path, original, "out_of_task" if path not in cfg["metadata_paths"] else "program_metadata")
            omissions[-1]["source_id"] = sid
            continue
        value = history_values[sid] if sid in history_values else select(original, path, owners) if path is not None else original
        known = path is not None and (any(matches(p, path) for p in container_rules) or matches("$.members.*.objects", path))
        if path in cfg["serialized_material_paths"]:
            value = serialized_fields(value, source)
            known |= isinstance(value, (dict, list))
        if known and empty(value):
            omit(path, original, "no_additional_business_content")
            omissions[-1]["source_id"] = sid
            continue
        ep = semantic(path, owners)
        header = (tuple(aliases[aid] for aid in owners), item["role"])
        identity = (header, source["ref"]["type"], source["ref"]["id"], ep, encoded(value)) if ep and not isinstance(value, (dict, list)) else None
        if source.get("query_record_identity"):
            identity = (item["role"], tuple(source["query_record_identity"]), encoded(value))
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
                      "container_known": known, "value": value, "source_paths": [], "history": history_label}
            if history_label and source.get("analysis_identity"):
                record["shared_analysis"] = prior_targets.get((tuple(source["analysis_identity"]), encoded(value)))
            records.append(record)
            if identity:
                grouped[identity] = record
        elif history_label:
            # Share text only. Each visible source keeps its original owners.
            record["header"] = (tuple(alias for alias in aliases.values() if alias in {*record["header"][0], *header[0]}), item["role"])
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
    records.sort(key=lambda r: (int(bool(r["history"])), int(r["history"][len(cfg["history_prefix"]):]) if r["history"] else 0,
                               tuple(order[a] for a in r["header"][0]) or (-1,),
                               cfg["role_order"].index(r["header"][1])))
    blocks = [cfg["task"], "本轮成员：" + "、".join(aliases.values()) + "。"]
    if notices:
        blocks.append("[实际材料限制｜程序提供]")
        blocks.extend("、".join(owners) + "：" + text for text, owners in notices.items())
    last = None
    for record in records:
        owners, role = record["header"]
        section = (record["history"], record["header"])
        if section != last:
            heading = record["history"] + " 历史参考；用于 " + "、".join(owners) if record["history"] else "、".join(owners) or "事件背景"
            blocks.append("[" + heading + "｜" + roles[role] + "]")
            last = section
        if record["history"] and len(owners) > 1:
            label = "[" + "；".join(alias + ":" + ",".join(sid for sid in record["source_ids"]
                if any(aliases[aid] == alias for aid in visible[sid]["alert_ids"])) for alias in owners) + "] "
        else:
            label = "[" + ",".join(record["source_ids"]) + "] "
        if role == "execution_receipt":
            text = query_result_text(record["value"], cfg["query_names"])
        elif record.get("shared_analysis"):
            text = "同一份已有判定及理由：见 " + "、".join(record["shared_analysis"]) + " 的 A 分诊原文。"
        elif record["history"] and isinstance(record["value"], dict):
            text = container(record["value"]["record"] if set(record["value"]) == {"record"} else record["value"])
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
