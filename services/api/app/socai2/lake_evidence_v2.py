"""C4 v2 bindings use the shared lake query scope and explicit object roles."""
from .baseline_store import digest
from .lake_queries import (
    LIMITATIONS,
    MAPPING,
    LakeQueries,
    active_profile,
    search_sql,
    selector_value,
    validate_search_rows,
)
from .lake_query_contracts import LakeReadError, LakeSearch, LakeSelector

VERSION = "socai2.c4-lake.v2"


def subject(binding):
    return {"selector": binding["selector"]} if binding.get("contract_version") == VERSION else {"hostname": binding["hostname"]}


def catalog(context, tenant_id, *, profile=None):
    from .baseline_evidence_tools import TOOLS
    from .case_execution_input import binding_scope
    profile = profile or active_profile()
    scopes = [s for s in profile.scopes if s["tenant_id"] == str(tenant_id)]
    grouped, omissions, bindings = {}, [], {}
    for aid, alert in sorted(context.alerts.items()):
        for obj in alert.objects:
            kind = {"host": "hostname", "ip": "ip"}.get(obj["object_type"])
            if kind is None:
                continue
            try:
                value = selector_value(LakeSelector(role="source", kind=kind, value=obj["normalized_value"]))
            except (ValueError, LakeReadError):
                omissions.append({"alert_id": aid, "object_id": obj["id"], "reason": "unsupported_lake_selector"})
                continue
            entry = grouped.setdefault((kind, value), {"alert_ids": set(), "objects": []})
            entry["alert_ids"].add(aid)
            entry["objects"].append({"alert_id": aid, "object_id": obj["id"], "object_key": obj["object_key"], "namespace": obj["namespace"]})
    for (kind, value), entry in sorted(grouped.items()):
        for scope in scopes:
            legacy = not scope["mapping_version"]
            roles = (("legacy_host", "destination") if kind == "hostname" else ("source", "destination")) if legacy else ("device", "source", "destination")
            for role in roles:
                for tool in TOOLS:
                    binding = {"tool_name": tool, "contract_version": VERSION, "tenant_id": str(tenant_id),
                        "case_id": str(context.case_id), "scope": binding_scope(context, entry["alert_ids"]),
                        "selector": {"role": role, "kind": kind, "value": value},
                        "alert_ids": sorted(entry["alert_ids"]), "objects": entry["objects"],
                        "source_database": profile.database, "source_namespace": scope["source_namespace"],
                        "mapping_version": scope["mapping_version"], "query_profile_digest": profile.digest,
                        "max_rows_per_query": profile.max_page_size,
                        "time_basis": "legacy_event" if legacy else "event", "limitations": list(LIMITATIONS),
                        "window_semantics": "start_inclusive_end_exclusive"}
                    if legacy:
                        binding["limitations"].append("legacy_source_host_role_and_event_time_unverified")
                    bindings[digest(binding)] = binding
    return {"bindings": bindings, "omissions": omissions,
            "unsupported": ["unconfigured_lake_sources_not_offered", "non_frozen_objects_not_offered"]}


def request(args, *, profile=None):
    from .baseline_evidence_tools import TOOLS
    profile = profile or active_profile()
    params = args["parameters"]
    if (not params.get("selector") or args["contract_version"] != VERSION or args["tool_name"] not in TOOLS
            or params["source_database"] != profile.database or params["query_profile_digest"] != profile.digest):
        raise LakeReadError("frozen_lake_query_profile_changed", "unavailable", 503)
    limit, ceiling = args["limit"], args["row_limit"]
    if type(limit) is not int or type(ceiling) is not int or not 1 <= limit <= min(ceiling, profile.max_page_size):
        raise LakeReadError("invalid_frozen_lake_limit", status=422)
    query = LakeSearch(source_namespace=params["source_namespace"], mapping_version=params["mapping_version"],
        selector=params["selector"], time_basis=params["time_basis"], start=args["scope"]["window_start"],
        end=args["scope"]["window_end"], class_uids=[TOOLS[args["tool_name"]]], limit=limit)
    return profile, params["tenant_id"], query


def query_sql(args):
    profile, tenant, query = request(args)
    sql, params, *_ = search_sql(profile, tenant, query, full=True)
    return sql, params


def validate_rows(rows, args):
    profile, tenant, query = request(args)
    validate_search_rows(rows, profile, tenant, query, full=True)


async def query(args, query_id, timeout):
    profile, tenant, request_body = request(args)
    return await LakeQueries(profile).evidence(tenant, request_body, query_id=query_id, timeout=timeout)


def parameters(binding):
    return {name: binding[name] for name in ("selector", "source_database", "source_namespace", "mapping_version", "query_profile_digest", "time_basis")}


def project_roles(value, row):
    """Refine only new lake rows; old frozen semantics/alert projections stay intact."""
    from .baseline_semantics import same_scalar, scalar_reason
    for field in value["fields"]:
        if field["name"] == "device_name" and field["source_path"].endswith(".device.hostname"):
            field["name"] = "device_hostname"
        if row["mapping_version"] == MAPPING and field["source_path"] in {
            "$.ocsf_json.device.name", "$.ocsf_json.device.hostname",
        } and field["name"] in {"device_name", "device_hostname"}:
            # The legacy projector compares these two different attributes.
            # Their values may differ legitimately. A mismatch with the stored
            # hostname column is still detected below for the same attribute.
            field["conflict"] = False
    if row["event_time_source"] != "ocsf_time_ms":
        value["fields"] = [f for f in value["fields"] if not (f["name"] == "event_time" and f["source_path"] == "$.event_time")]
        value["limitations"].append("projected_event_time_not_reliable_occurrence_time")
    for name in ("device_hostname", "device_ip"):
        original = row[name]
        if original in (None, "", "::", "::ffff:0.0.0.0", "0.0.0.0") or scalar_reason(name, original):
            continue
        existing = [f for f in value["fields"] if f["name"] == name]
        conflict = any(not same_scalar(name, f["value"], original) for f in existing)
        for field in existing:
            field["conflict"] = field["conflict"] or conflict
        if not existing or conflict:
            value["fields"].append({"name": name, "value": original, "source_path": "$."+name, "transform": "identity", "conflict": conflict})
    return value


def rank_binding(bid, binding, members):
    from .baseline_evidence_tools import TOOLS
    from .baseline_semantics import EVENT_KINDS
    selector, matched = LakeSelector(**binding["selector"]), []
    path = {"device": "device", "source": "src_endpoint", "destination": "dst_endpoint"}.get(selector.role)
    suffix = f".{path}.{selector.kind}" if path else None
    for aid in binding["alert_ids"]:
        fields = members.get(aid, {}).get("fields", [])
        for field in fields:
            if not suffix or field.get("conflict") is not False or not (field.get("source_path") or "").endswith(suffix):
                continue
            try:
                value = selector_value(selector.model_copy(update={"value": field["value"]}))
            except (ValueError, TypeError, LakeReadError):
                continue
            if value == selector_value(selector):
                matched.append(next((f["value"] for f in fields if f.get("name") == "event_kind" and f.get("conflict") is False), None))
                break
    tool = binding["tool_name"]
    return (-len(matched), -matched.count(EVENT_KINDS.get(TOOLS.get(tool))), -len(binding["alert_ids"]), selector.value, tool, bid)
