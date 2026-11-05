"""C6 reads verified query projections, not a second lossy C4 model view."""
from collections import Counter

from .baseline_context import reference
from .baseline_evidence import citation_roles
from .baseline_store import StoreError, digest, encoded

# A real behavior/attribute is required before a nonempty query can reach C6.
# Actor process and source endpoint fields deliberately are not substitutes.
PRIMARY = {
    "process_activity": ("process_command_line", "process_name", "process_path"),
    "network_connections": ("dest_ip", "dst_hostname"),
    "authentication_activity": ("user_name", "user_uid"),
    "product_host_details": ("product_platform", "product_os_version", "product_agent_version",
        "product_containment_status", "product_local_ip", "product_external_ip"),
}


def query_candidates(queries, bases):
    """Keep original fields/roles/paths; only one row's minimum is mandatory.

    All other fields, including conflicting alternatives, remain candidates and
    get normal omission receipts. Counts describe retained projection fields,
    not full raw results or model understanding.
    """
    projections = {str(row["id"]): row for row in bases
        if row["content_json"].get("type") == "query_projection"}
    result, missing = [], []
    for qi, query in enumerate(queries, 1):
        row = projections.get(query["artifact_id"])
        if not row or digest(row["content_json"]) != row["sha256"]:
            raise StoreError("evidence_receipt_invalid")
        value, candidates = row["content_json"], []
        for path, role in citation_roles(value).items():
            bits = path.split(".")
            field = value["rows"][int(bits[2])]["semantics"]["fields"][int(bits[-1])]
            record_key = f"Q{qi}R{bits[2]}"
            visible = {"record_key": record_key, **field}
            candidates.append({"original": visible, "entry": {"role": role,
                "alert_ids": value["alert_ids"], "membership_basis": "query_binding_only", "value": visible},
                "source": {"ref": reference("artifact", row["id"], role, path), "record_key": record_key,
                    "related_alert_ids": value["alert_ids"], "alert_ids": value["alert_ids"],
                    "membership_basis": "query_binding_only"}})
        # Choose a row with the strongest available primary field. Never replace
        # or merge conflicting same-name values: the first original remains a
        # field, its alternatives remain separate optional fields and receipts.
        primary = next((c for name in PRIMARY.get(query["tool_name"], ()) for c in candidates
            if c["entry"]["value"]["name"] == name), None)
        if primary:
            primary["required"] = True
            companion = {"network_connections": "dst_port", "authentication_activity": "action"}.get(query["tool_name"])
            secondary = next((c for c in candidates if companion
                and c["source"]["record_key"] == primary["source"]["record_key"]
                and c["entry"]["value"]["name"] == companion), None)
            if secondary:
                secondary["required"] = True
        elif value["rows"] or query["observed_rows_in_bounded_fetch"]:
            missing.append({"ref": reference("artifact", row["id"], "execution_receipt", "$.rows"),
                "reason": "required_query_evidence_unavailable"})
        query.update(projected_fields=len(candidates), visible_fields=0, view_state="partial")
        result.extend(candidates)
    return result, missing


def share_query_context(data):
    """Hoist only keys present and equal in every query; missing is not null."""
    queries = data.get("queries", [])
    if len(queries) < 2:
        return
    keys = set.intersection(*(set(query) for query in queries)) - {
        "artifact_id", "tool_name", "question_id", "projected_fields", "visible_fields", "view_state"}
    shared = {key: queries[0][key] for key in sorted(keys)
        if all(encoded(query[key]) == encoded(queries[0][key]) for query in queries)}
    if shared:
        data["query_context"] = {"applies_to": "queries", **shared}
        data["queries"] = [{key: value for key, value in query.items() if key not in shared} for query in queries]


def update_query_visibility(data, source_map):
    visible = Counter(str(source["ref"]["id"]) for source in source_map.values()
        if source.get("membership_basis") == "query_binding_only")
    for query in data.get("queries", []):
        if "projected_fields" in query:
            query["visible_fields"] = visible[query["artifact_id"]]
            query["view_state"] = "partial" if query["visible_fields"] < query["projected_fields"] else "all_projected_fields"
