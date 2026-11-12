"""Full frozen I input -> configured text -> unchanged stored result contract."""
import copy
from collections import Counter

from .alert_basic_contract import raw_field_role, retain_omission_details
from .baseline_context import reference
from .baseline_enrichment import citation_roles
from .baseline_model_view import blocked, draft_limit
from .baseline_store import StoreError, digest, encoded
from .incident_input_text import prepare
from .incident_query_receipts import receipts
from .model_input_view import LIMITATIONS, source_prefix
from .program_facts import query_statuses, stage_facts


def fields(value, path):
    """Keep unknown values, including 0/false/empty containers, addressable.

    A key containing a dot cannot use our deliberately small reference syntax.
    Keep its enclosing object intact instead of dropping the field or inventing
    an address. Role classification then uses that enclosing object's path.
    """
    if isinstance(value, dict) and value:
        if any(not isinstance(k, str) or not k or "." in k for k in value):
            yield path, value
        else:
            for key, child in value.items():
                yield from fields(child, path + "." + key)
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from fields(child, path + "." + str(index))
    elif value is not None and value != "":
        yield path, value


def query_items(aid, row, cfg):
    body = row["content_json"]
    fact = query_statuses([(row["id"], body)])[0]
    args = body.get("actual_args") or {}
    projection = {k: copy.deepcopy(body[k]) for k in cfg["query_receipt_fields"] if k in body}
    projection.update(outcome=fact["outcome"], statement=fact["statement"])
    projection["scope"] = {k: v for k, v in args.get("scope", {}).items() if k not in cfg["query_scope_backend_fields"]}
    parameters = args.get("parameters") or {}
    projection["selectors"] = [{k: v for k, v in selector.items() if k not in cfg["query_selector_backend_fields"]}
                               for selector in parameters.get("selectors", [])]
    if "source_scope" in parameters:
        projection["source_scope"] = parameters["source_scope"]
    if "limit" in args:
        projection["limit"] = args["limit"]
    projection["other_parameters"] = {k: v for k, v in parameters.items() if k not in {"selectors", "source_scope"}}
    yield reference("artifact", row["id"], "execution_receipt"), projection, projection, [aid]
    for path, role in citation_roles(body).items():
        cursor = body
        for part in path[2:].split("."):
            cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
        projected = copy.deepcopy(cursor)
        if path.count(".") == 2 and isinstance(projected, dict):
            # Only strip known query envelope/record fields. Unknown nested
            # business objects and their identifiers retain their own meaning.
            for key in cfg["query_envelope_backend_fields"]:
                projected.pop(key, None)
            record = projected.get("record")
            if isinstance(record, dict):
                for key in cfg["query_record_backend_fields"]:
                    record.pop(key, None)
                historical_knowledge = body["tool_name"] == "knowledge" and projected.get("purpose") == "historical_case_reference"
                if body["tool_name"] == "history" or historical_knowledge:
                    record.pop("triage", None)
                    record.pop("feedback", None)
                if historical_knowledge:
                    # The structured card is the model view; keep serialized
                    # content only in the saved original, not duplicated as prose.
                    record.pop("content", None)
        elif path.endswith(".record.triage"):
            for key in cfg["container_rules"]["$.members.*.triage"]["omit"]:
                projected.pop(key, None)
        elif path.endswith(".record.feedback"):
            for key in cfg["container_rules"]["$.members.*.feedback"]["omit"]:
                projected.pop(key, None)
        yield reference("artifact", row["id"], role, path), cursor, projected, [aid]


def query_record_identity(body, path):
    """Display identity only: one exact history version in one frozen receipt."""
    parts = (path or "").split(".")
    if body.get("tool_name") != "history" or len(parts) < 3 or parts[:2] != ["$", "rows"]:
        return None
    row = body["rows"][int(parts[2])]
    record = row.get("record")
    if not isinstance(record, dict) or not row.get("record_id") or record.get("id") != row["record_id"]:
        return None
    return str(row["record_id"]), digest(record), ".".join(parts[3:])


def build(source, input_id, profile, *, execution_time=None):
    if len(source["members"]) > 200:
        raise StoreError("incident_member_directory_too_large", 422)
    validation = source.get("triage_validation")
    if validation is None:
        raise StoreError("incident_triage_validation_missing", 422)
    verified = receipts(source)
    query_bodies = {row["id"]: row["content_json"] for _, row in verified}
    cfg = profile.config
    candidates = [(reference("artifact", input_id, "source_label", "$.parent"),
                   source["parent"], source["parent"], [])]
    coverage = {}
    for index, member in enumerate(source["members"]):
        aid, material, triage = member["alert"]["id"], member["material"], member["triage"]
        validity = validation.get(aid, {})
        usable = bool(validity.get("usable") and triage and validity.get("triage_id") == triage["id"]
                      and validity.get("source_run_id") == triage["source_run_id"])
        coverage[aid] = {"alert_id": aid, "stored_material_state": material["material_state"] if material else "unavailable",
            "triage_freshness": validity.get("freshness", "unverified"), "triage_eligible": usable,
            "triage_visibility": "omitted" if usable else "unavailable", "included": 0, "omitted": 0,
            "view_coverage": "complete_required" if material and material["material_state"] == "complete" else "partial",
            "queries_available": any(owner == aid for owner, _ in verified)}
        for key, role in (("alert", "source_label"), ("objects", "source_label"),
                          ("feedback", "human_statement"), ("triage", "prior_analysis")):
            value = member.get(key)
            if value and (key != "triage" or usable):
                candidates.append((reference("artifact", input_id, role, f"$.members.{index}.{key}"), value, value, [aid]))
        if not material or material["material_state"] != "complete":
            continue
        for key in ("raw_text", "ocsf_json", "raw_json", "detection", "enrichment", "source_scope"):
            value, path = material.get(key), "$." + key
            # raw_json has a typed envelope; keep all branches, not just the
            # raw_event branch, because other connectors may populate siblings.
            entries = [(path, value)] if key in {"detection", "enrichment", "source_scope"} else fields(value, path)
            for field, original in entries:
                if original is not None and original != "":
                    candidates.append((reference("alert_material", material["id"], raw_field_role(field), field),
                                       original, original, [aid]))
    for aid, row in verified:
        candidates.extend(query_items(aid, row, cfg["render"]))
    data = {"incident_id": source["parent"]["id"], "members": list(coverage.values()), "items": [],
        "omissions": {}, "view_limitations": LIMITATIONS, "citations": "structured_v3",
        "prose_alias_format": cfg.get("output_validation", {}).get("prose_alias_format", "legacy_v1"),
        "program_facts": stage_facts(source, input_id, execution_time)}
    envelope = cfg["render"]["raw_alert_envelope"]
    data["raw_alert_envelopes"] = [m["alert"]["id"] for m in source["members"]
        if isinstance((m.get("material") or {}).get("raw_json"), dict)
        and all(type(m["material"]["raw_json"].get(k)).__name__ == typ for k, typ in envelope["required_fields"].items())]
    # Preserve explicitly cited history even when it is only catalog context.
    # Old source numbers inside prose are not resolvable evidence references.
    data["required_history_rows"] = []
    paired_queries = {(aid, row["id"]) for aid, row in verified}
    for member in source["members"]:
        aid, triage = member["alert"]["id"], member.get("triage")
        if not coverage[aid]["triage_eligible"]:
            continue
        for item in [triage, *(triage.get("recommendations") or [])]:
            for ref in item.get("source_refs", []):
                path = ref.get("source_path") or ""
                if ref.get("type") == "artifact" and (aid, ref.get("id")) in paired_queries and path.startswith("$.rows."):
                    data["required_history_rows"].append([ref["id"], ".".join(path.split(".")[:3])])
    source_map, omissions, counts = {}, [], Counter()
    prefix = source_prefix(source)
    for ref, original, value, owners in candidates:
        if blocked({ref["source_path"] or "query_receipt": original}):
            omissions.append({"source": ref, "alert_ids": owners, "reason": "input_guard"})
            counts["input_guard"] += 1
            for aid in owners:
                coverage[aid]["omitted"] += 1
            continue
        sid = f"{prefix}S{len(source_map) + 1}"
        source_map[sid] = {"ref": ref, "alert_ids": owners, "visible_value_sha256": digest(value)}
        if ref["role"] == "prior_analysis" and isinstance(original, dict) and original.get("id"):
            source_map[sid]["analysis_identity"] = [str(original["id"]), digest(original)]
        if ref["id"] in query_bodies:
            identity = query_record_identity(query_bodies[ref["id"]], ref["source_path"])
            if identity:
                source_map[sid]["query_record_identity"] = identity
        data["items"].append({"id": sid, "alert_ids": owners, "role": ref["role"], "field": ref["source_path"], "value": value})
    data["omissions"] = dict(counts)
    for aid, member in coverage.items():
        member["queries_available"] = any(item["alert_ids"] == [aid] and item["role"] == "execution_receipt"
                                           for item in data["items"])
    prepared = prepare(data, source_map, cfg)
    for item in prepared["source_map"].values():
        for aid in item["alert_ids"]:
            coverage[aid]["included"] += 1
            path = item["ref"]["source_path"] or ""
            if item["ref"]["role"] == "prior_analysis" and path.startswith("$.members.") and path.endswith(".triage"):
                coverage[aid]["triage_visibility"] = "included"
    data["items"] = [{"id": sid, "alert_ids": prepared["source_map"][sid]["alert_ids"],
        "role": record["header"][1], "field": prepared["source_map"][sid]["ref"]["source_path"], "value": record["value"]}
        for record in prepared["records"] for sid in record["source_ids"]]
    # Retain original snapshot separately; the model request stores an audit of
    # structural omissions without duplicating raw values or administrative IDs.
    structural = [{k: v for k, v in item.items() if k != "original"} | {"value_sha256": digest(item["original"])}
                  for item in prepared["omissions"]]
    retain_omission_details(data, omissions)
    prepared["data"] = data
    prepared["boundary"] = {"version": profile.version, "profile_sha256": profile.sha256,
        "output_validation": {"prose_alias_format": data["prose_alias_format"]},
        "render_revision": cfg["render"]["revision"], "member_aliases": prepared["member_aliases"],
        "structural_omissions": structural, "full_source": reference("artifact", input_id, "execution_receipt")}
    messages = [{"role": "system", "content": cfg["system_prompt"]}, {"role": "user", "content": prepared["user"]}]
    if not prepared["source_map"] or blocked(messages):
        raise StoreError("incident_model_view_unavailable", 422)
    if len(encoded(messages)) > draft_limit():
        raise StoreError("incident_required_input_view_size", 422)
    return messages, prepared["source_map"], data, prepared
