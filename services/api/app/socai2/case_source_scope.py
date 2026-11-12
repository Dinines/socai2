"""Case-only query provenance; a query binding is not a returned row's subject."""
from uuid import UUID

FIELDS = ("query_alert_ids", "record_alert_ids", "membership_basis")


def metadata(source):
    return {key: source[key] for key in FIELDS if key in source}


def identity(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def query_scope(body, path, query_members, case_members):
    query_members = sorted(set(query_members))
    result = {"alert_ids": sorted(set(query_members) & set(case_members)), "query_alert_ids": query_members,
              "record_alert_ids": [], "membership_basis": "query_execution_scope"}
    parts = (path or "").split(".")
    if len(parts) < 3 or parts[:2] != ["$", "rows"]:
        return result
    result["membership_basis"] = "query_binding_only"
    historical_knowledge = body.get("tool_name") == "knowledge"
    if body.get("tool_name") != "history" and not historical_knowledge:
        return result
    # Only the server's history record contract supplies an alert identity.
    # Names, host matches, and arbitrary IDs in other tools do not establish it.
    result.update(alert_ids=[], membership_basis="history_record_identity_unverified")
    try:
        row = body["rows"][int(parts[2])]
        record = row["record"]
    except (KeyError, IndexError, ValueError, TypeError):
        return result
    if not isinstance(record, dict):
        return result
    if historical_knowledge:
        if row.get("purpose") != "historical_case_reference":
            result.update(alert_ids=sorted(set(query_members) & set(case_members)), membership_basis="query_binding_only")
            return result
        aid = identity(record.get("history", {}).get("source", {}).get("alert_id"))
    else:
        aid = identity(record.get("id"))
    if aid is None or (not historical_knowledge and identity(row.get("record_id")) != aid):
        return result
    for key in ("triage", "feedback"):
        child = record.get(key)
        if child is not None and (not isinstance(child, dict) or identity(child.get("alert_id")) != aid):
            return result
    result.update(record_alert_ids=[aid], alert_ids=[aid] if aid in case_members else [],
                  membership_basis="history_record_identity" if aid in case_members else "history_record_outside_case")
    return result


def describe(source, alias):
    if "query_alert_ids" not in source:
        return ""
    query = "、".join(alias(a) for a in source["query_alert_ids"]) or "共同背景"
    basis = source["membership_basis"]
    if basis in {"history_record_identity", "history_record_outside_case"}:
        subject = "、".join(alias(a) for a in source["record_alert_ids"])
        return f"查询范围={query}；返回记录主体={subject}；查询出处不改变记录主体。"
    if basis == "history_record_identity_unverified":
        return f"查询范围={query}；返回记录主体未核实，不能绑定为本案成员事实。"
    if basis == "query_binding_only":
        return f"查询范围={query}；仅查询绑定，非逐行成员归属。"
    return f"查询范围={query}；仅说明执行状态。"


def frozen_query_scope(context, path, case_members):
    parts = (path or "").split(".")
    if len(parts) < 6 or parts[:2] != ["$", "alerts"] or parts[3] != "queries" or parts[5] != "content_json":
        return None
    try:
        body = context["alerts"][parts[2]]["queries"][int(parts[4])]["content_json"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return query_scope(body, ".".join(["$", *parts[6:]]), [parts[2]], case_members)
