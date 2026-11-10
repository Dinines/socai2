"""Configured, loss-accounted presentation of nested C3 data ."""
import copy
import json

from .baseline_store import digest

_DROP = object()


def text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def pointer(parts):
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def matches(pattern, parts):
    tokens = [] if pattern == "" else pattern.removeprefix("/").split("/")
    return len(tokens) == len(parts) and all(a == "*" or a == str(b).replace("~", "~0").replace("/", "~1")
                                           for a, b in zip(tokens, parts, strict=True))


def empty(value):
    # Deliberately not `if not value`: 0 and False are business values.
    return value is None or isinstance(value, (str, list, dict)) and len(value) == 0


def record_omission(ledger, origin, path, value, reason, **extra):
    ledger.append({"origin": origin, "pointer": pointer(path), "value_sha256": digest(value),
                   "reason": reason, **extra})


def project(value, kind, config, ledger, origin):
    """Exact container + JSON Pointer rules; unknown keys survive at any depth."""
    rules = config["hierarchy"].get(kind, [])

    def walk(item, path):
        applicable = [r for r in rules if matches(r["path"], path)]
        for rule in applicable:
            if rule["action"] == "omit" or rule["action"] == "constant" and digest(item) == digest(rule["value"]):
                record_omission(ledger, origin, path, item, rule["reason"])
                return _DROP
        if isinstance(item, dict):
            result = {}
            for key, child in item.items():
                visible = walk(child, (*path, key))
                if visible is not _DROP:
                    result[key] = visible
        elif isinstance(item, list):
            result = []
            for index, child in enumerate(item):
                visible = walk(child, (*path, index))
                if visible is not _DROP:
                    result.append(visible)
        else:
            result = item
        for rule in applicable:
            if rule["action"] == "empty" and empty(result):
                record_omission(ledger, origin, path, item, rule["reason"])
                return _DROP
        return result

    result = walk(value, ())
    return None if result is _DROP else result


def enrichment(value, config, ledger, origin):
    """Discard only recognized pointer-only or empty session envelopes."""
    value = copy.deepcopy(value)
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        return value
    kept = []
    for index, item in enumerate(value["items"]):
        rule = config["empty_enrichment_kinds"].get(item.get("kind")) if isinstance(item, dict) else None
        payload = item.get("value") if isinstance(item, dict) else None
        if (rule and isinstance(payload, dict) and set(item) <= set(rule["wrapper_keys"])
                and set(payload) <= set(rule["payload_keys"])
                and (rule["payload_mode"] == "backend_only" or all(empty(v) for v in payload.values()))):
            record_omission(ledger, origin, ("items", index), item, rule["reason"])
            continue
        kept.append(item)
    value["items"] = kept
    return value


def translate(value, kind, config, ledger, origin):
    """Map only reviewed path/type/value triples, never arbitrary prose."""
    rules = config.get("semantic_rules", {}).get(kind, [])

    def walk(item, path):
        for rule in rules:
            if matches(rule["path"], path) and type(item).__name__ == rule["type"] and str(item) in rule["values"]:
                mapped = rule["values"][str(item)]
                ledger.append({"origin": origin, "pointer": pointer(path), "reason": "configured_business_meaning",
                               "original_value": item, "rendered_value": mapped})
                return mapped
        if isinstance(item, dict):
            return {k: walk(v, (*path, k)) for k, v in item.items()}
        if isinstance(item, list):
            return [walk(v, (*path, i)) for i, v in enumerate(item)]
        return item

    return walk(value, ())


def render(value, config, *, key=None, map_value=False):
    """Render structure; all prose values are copied literally, not summarized."""
    labels = config["presentation"]["labels"]
    if key is not None and key not in labels and not map_value:
        return text(value)
    if isinstance(value, dict) and value:
        # Equal sibling values share a label, never merge sources or roles.
        groups, seen = [], {}
        for name, child in value.items():
            group = next((g for g in config["presentation"]["equal_fields"] if name in g), None)
            signature = (tuple(group), digest(child)) if group else None
            if signature is not None and signature in seen:
                seen[signature][0].append(name)
            else:
                pair = ([name], child)
                groups.append(pair)
                if signature is not None:
                    seen[signature] = pair
        dynamic = key in config["presentation"].get("map_containers", [])
        return "；".join("/".join(labels.get(k, k) for k in names) + "=" +
                        ("(" + render(child, config, key=names[0], map_value=dynamic) + ")" if isinstance(child, dict) and child
                         else render(child, config, key=names[0], map_value=dynamic)) for names, child in groups)
    if isinstance(value, list) and value:
        return "[" + " | ".join(render(v, config, key=key) for v in value) + "]"
    return text(value)


def shared_fields(items, keys, ledger):
    """Factor exact repeated fields, with every applicable source named."""
    groups = {}
    for identifier, value in items:
        if not isinstance(value, dict):
            continue
        for key in keys:
            if key in value and not empty(value[key]):
                groups.setdefault((key, digest(value[key])), []).append((identifier, value[key]))
    shared, omitted = [], {}
    for (key, _), matches_ in groups.items():
        if len(matches_) < 2:
            continue
        owners = [i for i, _ in matches_]
        shared.append({"field": key, "applies_to": owners, "value": matches_[0][1]})
        for identifier in owners:
            omitted.setdefault(identifier, set()).add(key)
        ledger.append({"reason": "shared_exact_value", "field": key, "applies_to": owners,
                       "value_sha256": digest(matches_[0][1])})
    return shared, omitted


def repeated_prose(rows, config, ledger):
    """Reuse literal prior prose, without merging source identity or scope."""
    seen, references = {}, {}
    for row in rows:
        if row["ref"]["role"] != "prior_analysis" or not isinstance(row["value"], dict):
            continue
        for key in config["presentation"]["repeatable_prior_prose"]:
            value = row["value"].get(key)
            if not isinstance(value, str) or not value:
                continue
            signature = (key, value)
            if signature in seen:
                original_id = seen[signature]
                references.setdefault(row["id"], {})[key] = original_id
                ledger.append({"reason": "same_prose_not_independent_evidence", "source_id": row["id"],
                               "field": key, "text_at_source_id": original_id, "value_sha256": digest(value)})
            else:
                seen[signature] = row["id"]
    return references


def fact_projection(facts, rows, aliases, incident_aliases, config, ledger):
    """Only deduplicate facts against exact visible source/path/value pairs."""
    facts = copy.deepcopy(facts)
    by_ref = {digest(r["ref"]): r for r in rows}

    def same(ref, value, field=None):
        row = by_ref.get(digest(ref))
        visible = row["value"] if row else None
        if field is not None:
            visible = visible.get(field, _DROP) if isinstance(visible, dict) else _DROP
        if row and visible is not _DROP and digest(visible) == digest(value):
            return row["id"]
        return None

    for index, member in enumerate(facts.get("members", [])):
        aid = member["alert"]["id"]
        if aid not in aliases:
            raise ValueError("program_fact_member_unknown")
        origin = f"program_facts.members.{index}"
        member["member"] = aliases[aid]
        alert_ref = member.get("alert_source")
        for key, value in list(member["alert"].items()):
            sid = same(alert_ref, value, key)
            if sid:
                del member["alert"][key]
                record_omission(ledger, origin, ("alert", key), value, "same_fact_already_visible", source_id=sid)
        times = []
        for i, item in enumerate(member.get("activity_times", [])):
            # Only the known ISO activity-time projection has implicit units
            # in its original field. Numeric units and unknown additions remain.
            sid = same(item.get("source"), item.get("value"))
            if (sid and item.get("kind") == "activity_time" and item.get("unit") == "iso8601_with_offset"
                    and isinstance(item.get("value"), str)
                    and set(item) <= {"kind", "source", "unit", "value"}
                    and item.get("source", {}).get("source_path") in config["activity_time_paths"]):
                record_omission(ledger, origin, ("activity_times", i), item, "same_fact_already_visible", source_id=sid)
            else:
                times.append(item)
        if "activity_times" in member:
            member["activity_times"] = times
        if member.get("activity_time_state") == "available" and member.get("activity_times") == [] and any(
                r.get("origin") == origin and r.get("reason") == "same_fact_already_visible"
                and r.get("pointer", "").startswith("/activity_times/") for r in ledger):
            record_omission(ledger, origin, ("activity_time_state",), member.pop("activity_time_state"), "derived_state_already_visible")
    levels = {}
    for iid, value in facts.get("incident_severities", {}).items():
        if iid not in incident_aliases:
            raise ValueError("program_fact_incident_unknown")
        members = {}
        for aid, level in value.get("member_severities", {}).items():
            alias = aliases.get(aid)
            # Preserve unknown scope rather than silently treating it as local.
            if alias is None:
                raise ValueError("program_fact_severity_member_unknown")
            row = next((r for r in rows if r["block"] == "alert" and r["alert_ids"] == [aid]), None)
            if row and digest(row["value"].get("severity")) == digest(level) and "severity" in row["value"]:
                record_omission(ledger, "program_facts.incident_severities." + iid,
                                ("member_severities", aid), level, "same_fact_already_visible", source_id=row["id"])
            else:
                members[alias] = level
        value["member_severities"] = members
        if "missing_member_ids" in value:
            value["missing_member_ids"] = [aliases[a] for a in value["missing_member_ids"]]
        levels[incident_aliases[iid]] = value
    if "incident_severities" in facts:
        facts["incident_severities"] = levels
    facts = project(facts, "program_facts", config, ledger, "program_facts")
    remaining = []
    for i, member in enumerate(facts.get("members", [])):
        if set(member) == {"member"}:
            record_omission(ledger, "program_facts", ("members", i), member, "no_additional_member_fact")
        else:
            remaining.append(member)
    if remaining:
        facts["members"] = remaining
    elif "members" in facts:
        del facts["members"]
    return facts


def render_tools(catalog, config):
    """Keep selection semantics; retain optional technical detail in the ledger."""
    catalog = copy.deepcopy(catalog)
    ledger = []
    capabilities = catalog.pop("capabilities", [])
    shown_capabilities = copy.deepcopy(capabilities)
    detail_policy = config["presentation"].get("tool_field_detail")
    for capability in shown_capabilities:
        fields = capability.get("returned_fields")
        if (detail_policy and isinstance(fields, list) and fields
                and all(isinstance(f, str) and f in detail_policy["known_fields"] for f in fields)
                and all(isinstance(capability.get(k), str) and capability[k].strip()
                        for k in detail_policy["required_business_fields"])):
            capability.pop("returned_fields")
            ledger.append({"tool_name": capability["tool_name"], "reason": "technical_fields_retained_in_backend",
                           "returned_fields": fields,
                           "business_description_sha256": digest({k: capability[k] for k in detail_policy["required_business_fields"]})})
    shared, omitted = shared_fields([(c["tool_name"], c) for c in shown_capabilities],
                                     config["presentation"]["tool_shared_fields"], ledger)
    lines = ["[可用调查工具｜程序提供]", render(catalog, config)]
    for item in shared:
        shown = translate({item["field"]: item["value"]}, "tool", config, ledger, item["applies_to"])[item["field"]]
        lines.append("共同" + config["presentation"]["labels"].get(item["field"], item["field"]) +
                     "（适用于 " + "、".join(item["applies_to"]) + "）：" + render(shown, config))
    for capability in shown_capabilities:
        name = capability["tool_name"]
        value = {k: capability[k] for k in dict.fromkeys([*config["presentation"]["tool_field_order"], *capability])
                 if k in capability and k not in omitted.get(name, set())}
        value = translate(value, "tool", config, ledger, name)
        lines.append(render(value, config))
    return {"text": "\n".join(lines), "ledger": ledger, "catalog": catalog, "capabilities": capabilities}
