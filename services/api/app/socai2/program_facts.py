"""Facts from the frozen input, separately from the model's business claims."""
from datetime import datetime

from .baseline_context import reference
from .runtime_policy import active_policy

VERSION = "socai2.program-facts.v1.2"
RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def incident_level(parent, alerts, member_ids):
    expected = set(map(str, member_ids))
    known = {aid: alerts[aid].get("severity") for aid in sorted(expected & set(alerts))}
    missing = sorted(expected - set(known))
    values = [v for v in known.values() if v in RANK]
    auto = max(values, key=RANK.get) if values and not missing else None
    override = parent.get("severity_override")
    return {"severity_auto": auto, "severity_override": override,
        "severity_effective": override if override in RANK else auto,
        "severity_source": "manual_override" if override in RANK else "member_max" if auto else None,
        "member_severities": known, "missing_member_ids": missing,
        "unknown_severity_count": sum(v not in RANK for v in known.values()) + len(missing),
        "state": "partial_member_scope" if missing else "complete_member_scope"}


def labels(detection):
    policy = active_policy()
    output = []
    for category in ("tactics", "techniques"):
        for value in detection.get(category, []) if isinstance(detection.get(category), list) else []:
            spec = policy.labels["entries"].get(value) if isinstance(value, str) else None
            output.append({"category": category, "received": value,
                "mapping_state": "mapped" if spec else "unknown", **(dict(spec) if spec else {"name": None})})
    return {"dictionary_version": policy.labels["version"], "policy_sha256": policy.sha256,
            "entries": output, "role": "source_label", "does_not_establish_observed_attack": True}


def member_facts(member, source_id, path):
    from .baseline_model_view import blocked, compact_objects
    from .baseline_semantics import TIME_PATHS, material_projection
    alert, material = member["alert"], member.get("material")
    # No model output is accepted by this function. Unknown/blocked fields are
    # explicit and never filled with an unrelated clock, name or vendor label.
    values, unavailable = {}, []
    for key in ("id", "title", "original_vendor", "source_alert_id", "event_time", "event_time_source",
                "ingested_at", "severity"):
        value = alert.get(key)
        if blocked(value):
            unavailable.append(key)
            value = None
        values[key] = value
    result = {"alert": values, "alert_source": reference("artifact", source_id, "source_label", path + ".alert"),
        "unavailable_fields": unavailable, "activity_times": [], "log_severity": [],
        "objects": compact_objects(member.get("objects") or [])}
    if blocked(result["objects"]):
        result.update(objects=[], unavailable_fields=[*unavailable, "objects"])
    result["objects_source"] = reference("artifact", source_id, "source_label", path + ".objects")
    result["material_id"] = str(material["id"]) if material else None
    received = material.get("received_at") if material else None
    result["material_received_at"] = received.isoformat() if isinstance(received, datetime) else received
    result["material_source"] = (reference("alert_material", material["id"], "source_label") if material else None)
    if material and material.get("material_state") == "complete":
        for field in material_projection({**material, "alert_id": alert["id"]})["fields"]:
            if field["name"] in TIME_PATHS:
                result["activity_times"].append({"kind": field["name"], "value": field["value"],
                    "unit": field["unit"], "source": reference("alert_material", material["id"], "observation", field["source_path"])})
        raw = material.get("ocsf_json")
        root = "$.ocsf_json"
        if raw is None:
            raw, root = material.get("raw_json"), "$.raw_json"
            for key in ("raw_event", "ocsf_event"):
                if isinstance(raw, dict) and isinstance(raw.get(key), dict):
                    raw, root = raw[key], root + "." + key
        if isinstance(raw, dict):
            for key in ("severity_id", "severity"):
                value = raw.get(key)
                if type(value) in {str, int} and not blocked(value):
                    result["log_severity"].append({"value": value,
                        "source": reference("alert_material", material["id"], "source_label", root + "." + key)})
    detection = material.get("detection", {}) if material else {}
    result["detection_labels"] = labels(detection if isinstance(detection, dict) and not blocked(detection) else {})
    result["activity_time_state"] = ("available" if result["activity_times"] else "not_loaded_or_unavailable"
        if not material or not any(k in material for k in ("ocsf_json", "raw_json"))
        or material.get("material_state") != "complete" else "not_provided_or_invalid")
    return result


def query_outcome(payload):
    """Derive the result from recorded state, never from the explanatory prose."""
    state = payload.get("state")
    count = payload.get("returned_rows", payload.get("observed_rows_in_bounded_fetch"))
    if state == "skipped":
        return "not_queried"
    if state in {"failed", "timeout"}:
        return "failed"
    if state == "completed" and type(count) is int:
        if count > 0:
            return "data"
        if count == 0 and not payload.get("truncated"):
            return "empty"
    return "unknown"


def query_result_text(payload, names, *, tool_name=None):
    """The model needs a query result, not its execution ledger."""
    name = tool_name or payload.get("tool_name") or payload.get("source") or "查询"
    result = {"not_queried": "未查询", "failed": "查询失败", "unknown": "结果未知",
              "empty": "无结果", "data": "有结果"}[query_outcome(payload)]
    return names.get(name, name) + "：" + result


def query_statuses(queries):
    """Describe actual receipts; absence or truncation is never a zero-hit result."""
    facts = []
    for identity, payload in queries:
        state, count = payload.get("state"), payload.get("returned_rows")
        outcome = query_outcome(payload)
        text = {"not_queried": "本次未执行查询，不能称为无命中或无记录。",
            "failed": "查询失败或超时，未获得确定的查询结果。",
            "data": f"本次查询保留{count}行；仅适用于回执中的对象、时间和来源范围。",
            "empty": "本次查询成功，在该查询范围内返回0行；不能据此证明行为安全或检测错误。",
            "unknown": "回执不足或返回被截断，不能推定查空。"}[outcome]
        facts.append({"source": payload["tool_name"], "state": state, "outcome": outcome,
            "reason": payload.get("reason"), "returned_rows": count,
            "truncated": bool(payload.get("truncated")), "statement": text,
            "receipt": reference("artifact", identity, "execution_receipt")})
    return facts


def stage_facts(source, source_id, execution_time=None, *, queries=None):
    if queries is None and "query_receipts_version" in source:
        from .incident_query_receipts import receipts
        queries = [(row["id"], row["content_json"]) for _, row in receipts(source)]
    members = [member_facts(m, source_id, f"$.members.{index}") for index, m in enumerate(source["members"])]
    output = {"schema_version": VERSION, "members": members, "execution_started_at": execution_time,
              "time_rule": "activity_time != alert.event_time != ingested_at != execution_started_at"}
    if queries is not None:
        output["query_statuses"] = query_statuses(queries)
    if source.get("parent"):
        alerts = {m["alert"]["id"]: m["alert"] for m in source["members"]}
        output["incident_severity"] = incident_level(source["parent"], alerts, alerts)
        output["incident_source"] = reference("artifact", source_id, "source_label", "$.parent")
    return output


def case_facts(context, context_id, materials=None, *, execution_time=None, run_id=None):
    members = []
    for aid, item in sorted(context.alerts.items()):
        member = item.model_dump(mode="json")
        member["material"] = (materials or {}).get(aid, item.material)
        members.append(member_facts(member, context_id, f"$.alerts.{aid}"))
    alerts = {aid: item.alert for aid, item in context.alerts.items()}
    return {"schema_version": VERSION, "members": members,
        "snapshot_captured_at": context.captured_at.isoformat(),
        "execution_started_at": execution_time.isoformat() if isinstance(execution_time, datetime) else execution_time,
        "execution_time_source": {"table": "socai2.runs", "id": str(run_id), "field": "started_at"} if run_id else None,
        "case_severity": context.case.get("severity"),
        "case_source": reference("artifact", context_id, "source_label", "$.case"),
        "incident_severities": {iid: {**incident_level(item.incident, alerts, item.member_ids),
            "source": reference("artifact", context_id, "source_label", f"$.incidents.{iid}")}
            for iid, item in context.incidents.items()},
        "limitations": ["frozen_metadata_not_new_observations", "model_prose_not_rewritten",
            "missing_activity_time_never_replaced_by_alert_or_execution_time"]}
