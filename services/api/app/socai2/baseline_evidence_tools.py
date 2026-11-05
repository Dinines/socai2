"""Fixed read-only C4 lake contracts. No model SQL or caller-supplied filters."""
import json
import re
from datetime import UTC, datetime
from uuid import UUID

from . import baseline_optional_sources as optional
from .baseline_semantics import project, scalar_reason
from .baseline_store import digest

VERSION = "socai2.c4-lake.v1"
TOOLS = {"process_activity": 1007, "network_connections": 4001, "authentication_activity": 3002}
PRODUCT_FIELDS = ("device_id", "hostname", "platform", "os_version", "agent_version", "local_ip", "external_ip",
    "last_seen", "first_seen", "containment_status", "tags", "source_connector_id", "upstream_request_id", "observed_at")
PRODUCT_LIMITATIONS = ["current_product_snapshot_not_case_window_history", "source_host_match_not_identity_proof",
    "not_a_process_tree_or_authorization_record", "empty_product_lookup_is_not_counterevidence"]
FIELDS = ("event_id", "event_time", "class_uid", "src_hostname", "dst_hostname", "process_name",
    "source_ip", "dest_ip", "src_port", "dst_port", "protocol", "file_path", "hash_sha256", "user_name",
    "action", "outcome", "session_id", "session_key", "session_key_kind", "session_originating_human", "ocsf_json")
LIMITATIONS = ["host_time_match_is_not_causality_or_alert_membership",
    "lake_has_no_source_namespace_filter_may_include_multiple_connectors",
    "source_id_match_is_not_independent_corroboration", "empty_query_is_not_counterevidence",
    "coverage_and_collection_completeness_unknown"]


def catalog(context, tenant_id):
    grouped, omissions = {}, []
    for aid, alert in sorted(context.alerts.items()):
        for obj in alert.objects:
            if obj["object_type"] != "host":
                continue
            host = obj["normalized_value"]
            if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,253}", host):
                omissions.append({"alert_id": aid, "object_id": obj["id"], "reason": "unsupported_hostname"})
                continue
            entry = grouped.setdefault(host, {"alert_ids": set(), "objects": []})
            entry["alert_ids"].add(aid)
            entry["objects"].append({"alert_id": aid, "object_id": obj["id"],
                "object_key": obj["object_key"], "namespace": obj["namespace"]})
    bindings = {}
    for host, entry in sorted(grouped.items()):
        for tool in TOOLS:
            binding = {"tool_name": tool, "contract_version": VERSION, "tenant_id": str(tenant_id),
                "case_id": str(context.case_id), "scope": context.scope.model_dump(mode="json"),
                "hostname": host, "alert_ids": sorted(entry["alert_ids"]), "objects": entry["objects"],
                "source_database": optional.lake_database(),
                "limitations": list(LIMITATIONS), "window_semantics": "start_inclusive_end_exclusive"}
            bindings[digest(binding)] = binding
        for aid in sorted(entry["alert_ids"]):
            alert = context.alerts[aid].alert
            if not alert.get("connector_id") or alert.get("connector_type") != "crowdstrike":
                continue
            binding = {"tool_name": "product_host_details", "contract_version": VERSION,
                "tenant_id": str(tenant_id), "case_id": str(context.case_id),
                "scope": context.scope.model_dump(mode="json"), "hostname": host, "alert_ids": [aid],
                "source_alert_id": aid, "connector_id": str(alert["connector_id"]),
                "objects": [o for o in entry["objects"] if o["alert_id"] == aid],
                "limitations": list(PRODUCT_LIMITATIONS), "window_semantics": "current_snapshot"}
            bindings[digest(binding)] = binding
    return {"bindings": bindings, "omissions": omissions,
        "unsupported": ["product_host_details_requires_explicit_crowdstrike_connector",
                        "authentication_requires_frozen_source_hostname"]}


def query_sql(args):
    name, params = args["tool_name"], args["parameters"]
    if name not in TOOLS or args["contract_version"] != VERSION:
        raise ValueError("unsupported_tool_contract")
    scope = args["scope"]
    start, end = (datetime.fromisoformat(scope[k]) for k in ("window_start", "window_end"))
    if start.tzinfo is None or end.tzinfo is None or start >= end or not 1 <= args["limit"] <= 50:
        raise ValueError("invalid_frozen_query_scope")
    fields = ", ".join(FIELDS)
    database = optional.lake_database()
    if params.get("source_database", database) != database:
        raise ValueError("frozen_lake_database_changed")
    sql = f"""SELECT {fields} FROM (
 SELECT {fields}, row_number() OVER (
 PARTITION BY tenant_id,event_time,class_uid,event_id ORDER BY ingest_time DESC) AS source_rank
 FROM {database}.raw_events WHERE tenant_id=%(tenant_id)s AND src_hostname=%(hostname)s
 AND event_time>=toDateTime64(%(start)s,6,'UTC') AND event_time<toDateTime64(%(end)s,6,'UTC')
 AND class_uid=%(class_uid)s
) WHERE source_rank=1 ORDER BY event_time,event_id LIMIT %(fetch_limit)s"""
    bound = {"tenant_id": str(UUID(params["tenant_id"])), "hostname": params["hostname"],
        "start": start.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "end": end.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "class_uid": TOOLS[name], "fetch_limit": args["limit"] + 1}
    return sql, bound


def normalize_rows(rows):
    # Ledger is lossless for JSON-compatible driver values; byte limits are
    # applied later to whole rows, with explicit omissions.
    return json.loads(json.dumps(rows, default=lambda v: v.isoformat() if isinstance(v, datetime) else str(v),
                                ensure_ascii=False, allow_nan=False))


def validate_rows(rows, args):
    if len(rows) > args["limit"] + 1:
        raise ValueError("query_returned_beyond_sentinel_limit")
    if args["tool_name"] == "product_host_details":
        if len(rows) > 1:
            raise ValueError("ambiguous_product_host_response")
        for row in rows:
            if (set(row) != set(PRODUCT_FIELDS) or not row["device_id"] or not row["upstream_request_id"]
                    or row["source_connector_id"] != args["parameters"]["connector_id"]
                    or not isinstance(row["hostname"], str)
                    or row["hostname"].casefold() != args["parameters"]["hostname"].casefold()):
                raise ValueError("product_host_response_outside_binding")
        return
    start, end = (datetime.fromisoformat(args["scope"][k]) for k in ("window_start", "window_end"))
    seen = set()
    for row in rows:
        if set(row) != set(FIELDS):
            raise ValueError("query_column_contract_mismatch")
        event_time = datetime.fromisoformat(row["event_time"])
        # CH DateTime64 is declared UTC; driver may return a naive datetime.
        event_time = event_time.replace(tzinfo=UTC) if event_time.tzinfo is None else event_time
        key = (str(UUID(row["event_id"])), event_time, row["class_uid"])
        if (row["src_hostname"] != args["parameters"]["hostname"] or row["class_uid"] != TOOLS[args["tool_name"]]
                or not start <= event_time < end or key in seen):
            raise ValueError("query_row_outside_bound_scope_or_duplicate")
        seen.add(key)


def row_projection(row):
    if "source_connector_id" in row:
        fields, omissions = [], []
        for name in PRODUCT_FIELDS:
            reason = scalar_reason(name, row[name])
            if reason:
                omissions.append({"source_path": "$."+name, "reason": reason})
            else:
                fields.append({"name": "product_"+name, "value": row[name], "source_path": "$."+name,
                    "transform": "identity", "conflict": False})
        return {"state": "complete", "fields": fields, "omissions": omissions, "limitations": list(PRODUCT_LIMITATIONS)}
    value = project(row.get("ocsf_json"), root="$.ocsf_json")
    for name in ("event_id", "event_time"):
        if not scalar_reason(name, row.get(name)):
            value["fields"].append({"name": name, "value": row[name], "source_path": "$." + name,
                "transform": "identity", "conflict": False})
    # Nonempty source columns remain useful when retained OCSF is unavailable.
    # Ingestion sentinel defaults never establish an observation on their own.
    names = ("src_hostname", "dst_hostname", "process_name", "source_ip", "dest_ip", "src_port", "dst_port",
             "protocol", "file_path", "user_name", "action", "outcome", "session_id", "session_key",
             "session_key_kind", "session_originating_human", "hash_sha256")
    for name in names:
        original = row.get(name)
        why = scalar_reason(name, original)
        if original in (None, "", 0, "::", "::ffff:0.0.0.0", "0.0.0.0"):
            why = "flattened_empty_or_default"
        if why:
            value["omissions"].append({"source_path": "$." + name, "reason": why})
            continue
        existing = [f for f in value["fields"] if f["name"] == name]
        conflict = any((f["value"].lower() != original.lower()) if name == "hash_sha256"
            else f["value"] != original for f in existing)
        for field in existing:
            field["conflict"] = field["conflict"] or conflict
        if not existing or conflict:
            value["fields"].append({"name": name, "value": original, "source_path": "$." + name,
                "transform": "identity", "conflict": conflict})
    value["limitations"].append("flattened_defaults_not_promoted_to_observations")
    return value


class LakeGateway:
    def __init__(self, service=None):
        self.service = service

    def configured(self):
        from app.core.config import settings
        return bool(settings.CLICKHOUSE_HOST and not settings.AISOC_DISABLE_CLICKHOUSE) or optional.enabled("product_host")

    def unavailable_reason(self, binding):
        if binding["tool_name"] == "product_host_details":
            return None if optional.enabled("product_host") else "product_source_not_enabled"
        from app.core.config import settings
        if not settings.CLICKHOUSE_HOST or settings.AISOC_DISABLE_CLICKHOUSE:
            return "lake_not_configured"
        if binding.get("source_database", "aisoc") != optional.lake_database():
            return "frozen_lake_database_changed"
        return None

    async def query(self, args, query_id, timeout):
        if args["tool_name"] == "product_host_details":
            if not optional.enabled("product_host") or self.service is None:
                raise optional.SourceUnavailable("product_source_not_enabled")
            return await optional.product_query(self.service, args, timeout)
        from app.db.clickhouse import execute_lake_query
        if timeout < 1:
            # execute_lake_query floors seconds; zero would disable its server cap.
            raise ValueError("insufficient_query_time")
        sql, params = query_sql(args)
        result = await execute_lake_query(sql, params=params, query_id=query_id,
            timeout_seconds=min(timeout, 20), extra_settings={"max_result_rows": args["limit"] + 1})
        names = [c["name"] if isinstance(c, dict) else c for c in result.columns]
        return normalize_rows([dict(zip(names, row, strict=True)) for row in result.rows])
