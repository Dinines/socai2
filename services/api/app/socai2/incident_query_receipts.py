"""Validate frozen A query receipts, without fetching newer data or querying tools."""
from .baseline_enrichment import citation_roles
from .baseline_store import StoreError, digest, encoded
from .stage_inputs import QUERY_RECEIPTS_VERSION
from .stage_result_contracts import ALERT_EXECUTOR_VERSION


def receipts(source):
    if "query_receipts_version" not in source:
        return []
    if source["query_receipts_version"] != QUERY_RECEIPTS_VERSION:
        raise StoreError("incident_query_version_unsupported", 422)
    members = {m["alert"]["id"]: m for m in source["members"]}
    found, seen = [], set()
    for aid, rows in source["triage_queries"].items():
        member = members.get(aid)
        valid = source["triage_validation"].get(aid, {})
        triage = member.get("triage") if member else None
        if (not triage or not valid.get("usable") or valid.get("triage_id") != triage["id"]
                or valid.get("source_run_id") != triage["source_run_id"]):
            raise StoreError("incident_query_pairing_invalid", 422)
        for row in rows:
            body = row["content_json"]
            if (row["id"] in seen or row["alert_id"] != aid or row["tenant_id"] != member["alert"]["tenant_id"]
                    or row["run_id"] != triage["source_run_id"] or row["kind"] != "tool_response"
                    or row["schema_version"] != ALERT_EXECUTOR_VERSION or row["material_state"] != "complete"
                    or row.get("blob_ref") is not None or not isinstance(body, dict)
                    or digest(body) != row["sha256"] or len(encoded(body)) != row["size_bytes"]):
                raise StoreError("incident_query_receipt_invalid", 422)
            if body.get("actual_args", {}).get("scope", {}).get("alert_ids") != [aid]:
                raise StoreError("incident_query_scope_invalid", 422)
            count, values = body.get("returned_rows"), body.get("rows")
            if (not isinstance(body.get("tool_name"), str) or not isinstance(body.get("state"), str)
                    or count is not None and (type(count) is not int or count < 0)
                    or values is not None and not isinstance(values, list)
                    or body.get("state") == "completed" and (type(count) is not int or count != len(values or []))):
                raise StoreError("incident_query_payload_invalid", 422)
            try:
                citation_roles(body)
            except (KeyError, TypeError, AttributeError) as exc:
                raise StoreError("incident_query_payload_invalid", 422) from exc
            seen.add(row["id"])
            found.append((aid, row))
    return found


def reference_roles(source):
    return {str(row["id"]): {None: "execution_receipt", **citation_roles(row["content_json"])}
            for _, row in receipts(source)}
