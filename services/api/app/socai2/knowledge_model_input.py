"""Deduplicate frozen knowledge and select whole optional cards for each task."""
import copy

from .baseline_store import digest, encoded


def metadata(body, ref):
    parts = (ref.get("source_path") or "").split(".")
    if body.get("tool_name") != "knowledge" or len(parts) < 3 or parts[:2] != ["$", "rows"]:
        return {}
    row = body["rows"][int(parts[2])]
    history = row.get("record", {}).get("history")
    identity = {"document_id": row["record_id"], "content_sha256": row["content_sha256"]}
    if history:
        identity["historical_source"] = history["source"]
    return {"knowledge": {"identity": digest(identity), "part": ".".join(parts[3:]) or "card",
        "origins": [{"ref": copy.deepcopy(ref), "purpose": row["purpose"],
            "purpose_label": row.get("purpose_label"), "use": row.get("use"),
            "query_alert_ids": row.get("query_alert_ids", body.get("actual_args", {}).get("scope", {}).get("alert_ids", [])),
            "source_paths": row.get("query_source_paths", [])}]}}


def coalesce(entries):
    result, seen, omissions = [], {}, []
    for entry in entries:
        item = entry.get("knowledge")
        if not item:
            result.append(entry)
            continue
        key = item["identity"], item["part"], entry["ref"]["role"]
        if key not in seen:
            seen[key] = entry
            result.append(entry)
        else:
            canonical = seen[key]
            canonical["knowledge"]["origins"].extend(item["origins"])
            for field in ("alert_ids", "query_alert_ids"):
                canonical[field] = sorted(set(canonical.get(field, [])) | set(entry.get(field, [])))
            omissions.append({"ref": entry["ref"], "reason": "duplicate_knowledge_version",
                              "canonical_ref": canonical["ref"], "knowledge_identity": item["identity"]})
    for entry in seen.values():
        if entry["knowledge"]["part"] == "card":
            value = entry["value"]
            value["purposes"] = list({origin["purpose"]: {k: origin.get(k) for k in
                ("purpose", "purpose_label", "use")} for origin in entry["knowledge"]["origins"]}.values())
            for key in ("purpose", "purpose_label", "use", "query_alert_ids", "query_source_paths", "similarity", "content_sha256"):
                value.pop(key, None)
    return result, omissions


def choose(entries, stage, allowed, policy, *, dependencies=(), excluded=()):
    groups, retained, omissions = {}, [], []
    for entry in entries:
        item = entry.get("knowledge")
        if not item:
            retained.append(entry)
        else:
            groups.setdefault(item["identity"], []).append(entry)
    budget = policy["stage_max_characters"][stage]
    used = sum(len(encoded(r["value"]).decode()) for r in entries
               if r.get("knowledge", {}).get("identity") in dependencies)
    for identity, rows in groups.items():
        if identity in dependencies:
            retained.extend(rows)
            continue
        origins = [o for r in rows for o in r["knowledge"]["origins"]]
        purpose_allowed = any(o["purpose"] in policy["stage_purposes"][stage] for o in origins)
        related = any(set(o["query_alert_ids"]) & set(allowed) for o in origins)
        size = sum(len(encoded(r["value"]).decode()) for r in rows)
        reason = ("knowledge_input_capacity" if identity in excluded else
                  "knowledge_purpose_not_for_stage" if not purpose_allowed else
                  "knowledge_outside_task_scope" if not related else
                  "knowledge_optional_budget" if used + size > budget else None)
        if reason:
            omissions.extend({"ref": r["ref"], "reason": reason, "knowledge_identity": identity} for r in rows)
        else:
            used += size
            retained.extend(rows)
    return retained, omissions
