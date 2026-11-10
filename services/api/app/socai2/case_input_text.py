"""Configured C3 input: structural projection, no interpretation or external calls."""
import copy
import json
from collections import Counter

from .alert_basic_contract import raw_field_role
from .baseline_context import reference
from .baseline_model_view import blocked
from .baseline_store import digest, encoded
from .case_input_hierarchy import (
    enrichment,
    fact_projection,
    project,
    render,
    repeated_prose,
    shared_fields,
    translate,
)
from .incident_model_boundary import fields, query_items
from .incident_query_receipts import receipts
from .model_input_view import frozen_items, source_prefix


def text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def select(value, rule, omissions, path):
    result = copy.deepcopy(value)
    if not isinstance(result, dict):
        return result
    for key in rule["omit"]:
        if key in result:
            old = result.pop(key)
            omissions.append({"path": path + "." + key, "reason": "configured_backend_field", "value_sha256": digest(old)})
    for key in rule["empty"]:
        if key in result and (result[key] is None or result[key] == ""):
            old = result.pop(key)
            omissions.append({"path": path + "." + key, "reason": "empty_optional", "value_sha256": digest(old)})
    return result


def material_entries(aid, material, config, omissions, candidate=None):
    """Use received structure, including unknown branches; never sample names."""
    if material.get("material_state") != "complete":
        return []
    cfg = config["render"]
    envelope = cfg["raw_alert_envelope"]
    raw = material.get("raw_json")
    known_envelope = isinstance(raw, dict) and all(type(raw.get(k)).__name__ == typ
                                                  for k, typ in envelope["required_fields"].items())
    result = []
    for name in ("raw_text", "ocsf_json", "raw_json", "detection", "enrichment", "source_scope"):
        value = material.get(name)
        rows = [("$." + name, value)] if name in {"detection", "enrichment", "source_scope"} else fields(value, "$." + name)
        for path, original in rows:
            if original is None or original == "":
                continue
            administrative = path in cfg["metadata_paths"] or known_envelope and any(
                path == "$.raw_json." + key or path.startswith("$.raw_json." + key + ".")
                for key in envelope["backend_fields"])
            if administrative:
                omissions.append({"material_id": material["id"], "path": path,
                                  "reason": "configured_backend_field", "value_sha256": digest(original)})
                continue
            projected = original
            if candidate and known_envelope and (path in candidate["material_backend_paths"] or
                    path in candidate["material_optional_paths"] and original in ([], {})):
                omissions.append({"material_id": material["id"], "path": path,
                                  "reason": "configured_material_wrapper", "value_sha256": digest(original)})
                continue
            if path == "$.detection":
                rule = cfg["container_rules"]["$.detection"]
                projected = select(original, {"omit": rule["omit"], "empty": rule["empty_optional"]}, omissions, path)
            if candidate and path in {"$.enrichment", "$.source_scope", "$.detection"}:
                kind = path[2:]
                origin = {"material_id": material["id"], "path": path}
                if kind == "enrichment":
                    projected = enrichment(projected, candidate, omissions, origin)
                projected = project(projected, kind, candidate, omissions, origin)
                if projected is None:
                    continue
            if projected == {} and path == "$.detection":
                continue
            result.append({"ref": reference("alert_material", material["id"], raw_field_role(path), path),
                "alert_ids": [aid], "value": projected, "original_value": original, "block": "material",
                "typed_raw_alert_envelope": known_envelope})
    return result


def prepare(sample, config, business):
    context, cid = sample["context"], sample["context_id"]
    paired = copy.deepcopy(sample["query_source"])
    paired["members"] = [{"alert": row["alert"], "triage": row["triage"]} for row in context["alerts"].values()]
    paired["triage_validation"] = {aid: {"usable": row.get("triage_usable") is True and row.get("triage_freshness") == "current",
        "triage_id": row["triage"]["id"], "source_run_id": row["triage"]["source_run_id"]}
        for aid, row in context["alerts"].items() if row.get("triage")}
    verified_queries = receipts(paired)
    aliases = {aid: config["member_prefix"] + str(i) for i, aid in enumerate(sorted(context["alerts"]), 1)}
    incident_aliases = {iid: config["incident_prefix"] + str(i) for i, iid in enumerate(sorted(context["incidents"]), 1)}
    object_aliases = {key: config["object_prefix"] + str(i) for i, key in enumerate(context["scope"]["object_keys"], 1)}
    external = {}
    rules, cfg = config["rules"], business["render"]
    omissions, entries, notices, presentation = [], [], [], []

    def owner_alias(aid):
        if aid in aliases:
            return aliases[aid]
        if aid not in external:
            external[aid] = config["external_member_prefix"] + str(len(external) + 1)
        return external[aid]

    def alias_scope(value):
        result = copy.deepcopy(value)
        if "alert_ids" in result:
            result["alert_ids"] = [owner_alias(aid) for aid in result["alert_ids"]]
        if "object_keys" in result:
            result["object_keys"] = [object_aliases.get(key, key) for key in result["object_keys"]]
        return result

    def add(path, original, owners, role, block, value=None, scope=None):
        entry = {"ref": reference("artifact", cid, role, path), "alert_ids": sorted(set(owners) & set(aliases)),
                 "value": copy.deepcopy(original if value is None else value),
                 "original_value": copy.deepcopy(original), "block": block}
        if scope is not None:
            entry["original_scope"] = copy.deepcopy(scope)
            entry["value"]["declared_scope"] = alias_scope(scope)
            entry["value"]["outside_case_members"] = [owner_alias(a) for a in scope.get("alert_ids", []) if a not in aliases]
        entries.append(entry)

    # Preserve original visible background/human sources, replacing only known
    # member/incident blocks with full, frozen business projections below.
    for item in frozen_items(sample["data"]):
        ref, path = item["source"], item["source"].get("source_path") or ""
        if ref["type"] == "alert_material":
            continue
        if ref["id"] == cid and (path.startswith("$.alerts.") and path.rsplit(".", 1)[-1] in {"alert", "triage", "material"}
                                  or path.startswith("$.incidents.") and path.endswith(".diagnosis")):
            continue
        source = next(v for v in sample["request"]["source_map"].values() if v["ref"] == ref)
        entries.append({"ref": copy.deepcopy(ref), "alert_ids": source["alert_ids"], "value": item["value"],
                        "original_value": item["value"], "block": "background"})

    for aid, row in sorted(context["alerts"].items()):
        material = sample["materials"].get(aid)
        if material:
            entries.extend(material_entries(aid, material, business, omissions, config))
        if not material or material.get("material_state") != "complete":
            notices.append(aliases[aid] + "：完整原材料不可用。")
        path = f"$.alerts.{aid}.alert"
        add(path, row["alert"], [aid], "source_label", "alert", select(row["alert"], rules["alert"], omissions, path))
        if row.get("triage") and row.get("triage_usable") is True and row.get("triage_freshness") == "current":
            path = f"$.alerts.{aid}.triage"
            add(path, row["triage"], [aid], "prior_analysis", "triage", select(row["triage"], rules["triage"], omissions, path))
        else:
            notices.append(aliases[aid] + "：没有经确认可用的当前分诊，不能沿用旧判断。")

    for iid, row in sorted(context["incidents"].items()):
        if not row["diagnosis_usable"]:
            notices.append("相关事件诊断不可作为当前有效判断使用。")
            continue
        base, diagnosis = f"$.incidents.{iid}.diagnosis", row["diagnosis"]
        original_scope = {"alert_ids": row["member_ids"]}
        add(base + ".summary", diagnosis["summary"], row["case_member_ids"], "prior_analysis", "incident")
        for key in ("conclusion", "limitations"):
            if key in diagnosis["diagnosis"]:
                value = diagnosis["diagnosis"][key]
                add(base + ".diagnosis." + key, value, row["case_member_ids"], "prior_analysis", "incident")
        notices.append(incident_aliases[iid] + " 事件背景原范围：" + render(alias_scope(original_scope), config))
        for kind, values, path in (("finding", diagnosis["diagnosis"].get("findings", []), base + ".diagnosis.findings"),
                                   ("question", diagnosis.get("open_questions", []), base + ".open_questions")):
            for index, value in enumerate(values):
                scope = value.get("scope")
                if not isinstance(scope, dict) or not isinstance(scope.get("alert_ids"), list):
                    raise TypeError("incident_item_scope_missing")
                selected = select(value, rules[kind], omissions, path + f".{index}")
                add(path + f".{index}", value, scope["alert_ids"], "prior_analysis", kind, selected, scope)

    for aid, row in verified_queries:
        for ref, original, projected, owners in query_items(aid, row, cfg):
            entries.append({"ref": ref, "alert_ids": owners, "value": projected,
                            "original_value": original, "block": "query"})
    entries.extend(copy.deepcopy(sample.get("additional_queries", [])))
    available_queries = {aid for aid, _ in verified_queries}
    for aid, alias in aliases.items():
        if aid not in available_queries:
            notices.append(alias + "：未提供同次分诊的可核对查询回执；不能推断查询结果。")

    prefix = source_prefix([context, sample["request"], sample["materials"], sample["query_source"], entries])
    source_map, rows, index_by_ref = {}, [], {}
    for entry in entries:
        if blocked(entry["original_value"]):
            omissions.append({"ref": entry["ref"], "alert_ids": entry["alert_ids"],
                              "reason": "input_guard", "value_sha256": digest(entry["original_value"])})
            notices.append("有原始字段被输入检查排除，不能视作完整材料。")
            continue
        key = encoded(entry["ref"]).decode()
        if key in index_by_ref:
            if digest(rows[index_by_ref[key]]["original_value"]) != digest(entry["original_value"]):
                raise ValueError("same_reference_has_conflicting_value")
            continue
        sid = f"{prefix}S{len(source_map) + 1}"
        entry = copy.deepcopy(entry)
        entry["id"] = sid
        index_by_ref[key] = len(rows)
        rows.append(entry)
        source_map[sid] = {"ref": entry["ref"], "alert_ids": entry["alert_ids"],
                           "visible_value_sha256": digest(entry["value"])}
        if "original_scope" in entry:
            source_map[sid]["original_scope"] = entry["original_scope"]

    # Resolve only actually displayed direct references. Unavailable prior
    # support remains explicitly unavailable; the prior statement is unchanged.
    def resolve_prior_refs(refs):
        visible, missing = [], []
        for ref in refs:
            ix = index_by_ref.get(encoded(ref).decode())
            if ix is None:
                missing.append(copy.deepcopy(ref))
            else:
                visible.append(rows[ix]["id"])
        return visible, missing

    for row in rows:
        if row["block"] == "triage":
            resolutions = []
            for original, visible in zip(row["original_value"].get("recommendations", []),
                                         row["value"].get("recommendations", []), strict=True):
                if "source_refs" in original:
                    refs, missing = resolve_prior_refs(original["source_refs"])
                    visible["source_refs"] = refs
                    if missing:
                        visible["unavailable_prior_reference_count"] = len(missing)
                    resolutions.append({"visible": refs, "not_visible": missing})
            row["prior_recommendation_reference_resolution"] = resolutions
            source_map[row["id"]]["visible_value_sha256"] = digest(row["value"])
        if row["block"] not in {"finding", "question"}:
            continue
        resolved, missing = {}, {}
        for key in ("support", "counterevidence", "evidence_refs"):
            if key not in row["original_value"]:
                continue
            resolved[key], missing[key] = resolve_prior_refs(row["original_value"][key])
        row["prior_reference_resolution"] = {"visible": resolved, "not_visible": missing}
        row["value"]["visible_prior_references"] = resolved
        row["value"]["unavailable_prior_reference_counts"] = {k: len(v) for k, v in missing.items() if v}
        source_map[row["id"]]["visible_value_sha256"] = digest(row["value"])

    for row in rows:
        kind = "receipt" if row["block"] in {"query", "background_query"} and row["ref"]["role"] == "execution_receipt" else row["block"]
        row["value"] = project(row["value"], kind, config, omissions, row["id"])
        source_map[row["id"]]["visible_value_sha256"] = digest(row["value"])

    def field(row):
        path = row["ref"]["source_path"] or ""
        semantic = next((path[len(root):] for root in cfg["event_roots"] if path.startswith(root)), None)
        if semantic is None and row.get("typed_raw_alert_envelope"):
            semantic = config["material_field_aliases"].get(path)
        return semantic

    def label(row):
        path = row["ref"]["source_path"] or ""
        semantic = field(row)
        fallback = path.removeprefix("$.raw_json.raw_event.").removeprefix("$.raw_json.").removeprefix("$.")
        if row["block"] != "material":
            fallback = config["block_labels"][row["block"]]
        return config["material_labels"].get(semantic, cfg["field_labels"].get(semantic, semantic or fallback or row["block"]))

    def heading(row):
        members = (row["value"]["declared_scope"]["alert_ids"] if row["block"] in {"finding", "question"}
                   else [aliases[a] for a in row["alert_ids"]])
        return row["block"], tuple(members), row["ref"]["role"]

    # Aggregate duplicate representations ONLY within one material and one
    # semantic field/value/role, retaining every resolvable source ID.
    groups, seen = [], {}
    for row in rows:
        ref = row["ref"]
        semantic = field(row)
        key = (ref["id"], ref["role"], semantic, digest(row["value"])) if ref["type"] == "alert_material" and semantic else None
        if key is not None and key in seen:
            seen[key]["ids"].append(row["id"])
            continue
        group = {"ids": [row["id"]], "row": row}
        groups.append(group)
        if key is not None:
            seen[key] = group
    heading_order = {h: i for i, h in enumerate(dict.fromkeys(heading(g["row"]) for g in groups))}
    groups.sort(key=lambda g: heading_order[heading(g["row"])])
    presentation.append({"reason": "grouped_by_member_and_role", "groups": [g["ids"] for g in groups]})
    scope = project(alias_scope(context["scope"]), "scope", config, omissions, "context.scope")
    blocks = [config["task"], "调查范围：" + render(scope, config), "[本轮要回答的问题]"]
    blocks += [q["id"] + "：" + q["text"] + "；依据要求：" + "；".join(q["evidence_requirements"]) for q in context["questions"]]
    if object_aliases:
        objects = {key: [] for key in object_aliases}
        for aid, member in context["alerts"].items():
            for obj in member.get("objects", []):
                if obj["object_key"] in objects:
                    detail = {"type": obj["object_type"], "value": obj.get("raw_value"), "role": obj.get("object_role")}
                    for key in ("namespace", "attributes", "asset_ref"):
                        if obj.get(key) is not None and obj[key] != "" and obj[key] != {}:
                            detail[key] = obj[key]
                    detail = project(detail, "object", config, omissions,
                                     {"object_key": obj["object_key"], "member": aliases[aid]})
                    matching = next((r for r in objects[obj["object_key"]] if r["detail"] == detail), None)
                    if matching:
                        matching["alert_ids"].append(aliases[aid])
                    else:
                        objects[obj["object_key"]].append({"alert_ids": [aliases[aid]], "detail": detail})
        blocks.append("[可选对象｜同对象不证明因果]")
        for key, items in objects.items():
            for item in items:
                blocks.append(object_aliases[key] + "：" + render({**item["detail"], "alert_ids": item["alert_ids"]}, config))
    if notices:
        blocks += ["[实际材料限制与范围｜程序提供]", *dict.fromkeys(notices)]
    shared, shared_omits = shared_fields(
        [(r["id"], r["value"]) for r in rows if r["block"] in {"query", "background_query"} and r["ref"]["role"] == "execution_receipt"],
        config["presentation"]["receipt_shared_fields"], omissions)
    if shared:
        blocks.append("[查询回执共同限制｜仅适用于所列回执]")
        for item in shared:
            value = translate({item["field"]: item["value"]}, "receipt", config, presentation, item["applies_to"])
            blocks.append("、".join(item["applies_to"]) + "：" + render(value[item["field"]], config))
    shared_scopes, scope_omits = shared_fields(
        [(r["id"], {"scope_limitations": r["value"]["declared_scope"].get("limitations", [])})
         for r in rows if r["block"] in {"finding", "question"}], ["scope_limitations"], presentation)
    if shared_scopes:
        blocks.append("[已有发现及问题的共同范围限制｜仅适用于所列来源]")
        for item in shared_scopes:
            value = translate({"limitations": item["value"]}, "scope", config, presentation, item["applies_to"])
            blocks.append("、".join(item["applies_to"]) + "：" + render(value["limitations"], config))
    prose_references = repeated_prose(rows, config, omissions)
    receipts_by_artifact = {r["ref"]["id"]: r["id"] for r in rows
                            if r["block"] in {"query", "background_query"} and r["ref"]["role"] == "execution_receipt"}
    rows_by_ref = {(r["ref"]["id"], r["ref"]["source_path"]): r["id"] for r in rows}
    last = None
    for group in groups:
        row = group["row"]
        current_heading = heading(row)
        if current_heading != last:
            owners = "、".join(current_heading[1]) or "案件背景"
            if row["block"] in {"finding", "question"}:
                owners = "原范围=" + owners
            blocks.append(f"[{config['block_labels'][row['block']]}｜{owners}｜{cfg['roles'][row['ref']['role']]}]")
            last = current_heading
        if row["ref"]["role"] == "execution_receipt" and row["block"] in {"query", "background_query"}:
            value = {k: v for k, v in row["value"].items() if k not in shared_omits.get(row["id"], set())}
            value = translate(value, "receipt", config, presentation, row["id"])
            shown = render(value, config)
        else:
            value = copy.deepcopy(row["value"])
            if row["block"] == "material":
                dictionary = cfg["field_values"].get(field(row), {})
                if type(value).__name__ == dictionary.get("type") and str(value) in dictionary.get("values", {}):
                    value = dictionary["values"][str(value)]
                    presentation.append({"source_id": row["id"], "reason": "existing_field_dictionary",
                                         "field": field(row), "original_value": row["value"], "rendered_value": value})
                if row["ref"]["source_path"] == "$.detection":
                    value = translate(value, "detection", config, presentation, row["id"])
            if row["block"] in {"finding", "question"}:
                scope = value["declared_scope"]
                scope.pop("alert_ids")
                if scope.get("kind") == config["presentation"]["member_scope_kind"]:
                    scope.pop("kind")
                if "scope_limitations" in scope_omits.get(row["id"], set()):
                    scope.pop("limitations")
                value["declared_scope"] = translate(scope, "scope", config, presentation, row["id"])
                if not value["declared_scope"]:
                    value.pop("declared_scope")
                presentation.append({"source_id": row["id"], "reason": "scope_members_in_heading",
                                     "original_scope": row["original_scope"], "heading_members": list(current_heading[1]),
                                     "remaining_scope": scope})
            for key, original_id in prose_references.get(row["id"], {}).items():
                value[key] = f"与 {original_id} 对应字段逐字相同，见该原文；同文不等于独立佐证"
            caption = label(row)
            if row["block"] in {"query", "background_query"}:
                path = row["ref"]["source_path"] or ""
                parts = path.split(".")
                if len(parts) >= 3 and parts[0:2] == ["$", "rows"]:
                    receipt_id = receipts_by_artifact[row["ref"]["id"]]
                    parent = rows_by_ref.get((row["ref"]["id"], ".".join(parts[:3])))
                    caption = (f"回执 {receipt_id} 的第 {int(parts[2]) + 1} 条返回" if len(parts) == 3
                               else f"返回记录 {parent or receipt_id} 的 {'.'.join(parts[3:])}")
            shown = caption + "：" + render(value, config)
        blocks.append("[" + ",".join(group["ids"]) + "] " + shown)
    facts = fact_projection(sample["data"].get("program_facts", {}), rows, aliases, incident_aliases, config, omissions)
    if facts:
        blocks.append("[补充业务事实｜程序提供]\n" + render(translate(facts, "program_facts", config, presentation, "program_facts"), config))
    coverage = {aid: {"included": sum(aid in src["alert_ids"] for src in source_map.values()),
                      "omitted": sum(aid in entry.get("alert_ids", []) for entry in omissions)} for aid in aliases}
    return {"user": "\n".join(blocks), "source_map": source_map, "records": rows, "omissions": omissions,
            "member_aliases": aliases, "incident_aliases": incident_aliases,
            "external_member_aliases": external, "object_aliases": object_aliases,
            "coverage": coverage, "query_supplement": sample["query_source"], "program_facts": sample["data"].get("program_facts"),
            "presented_program_facts": facts, "shared_receipt_fields": shared,
            "prior_prose_references": prose_references,
            "presentation_ledger": presentation,
            "record_counts": dict(Counter(r["block"] for r in rows)), "group_count": len(groups),
            "query_supplement_was_in_original_c1": False}
