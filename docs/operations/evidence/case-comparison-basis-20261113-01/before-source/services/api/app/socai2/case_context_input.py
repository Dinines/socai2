"""Business views of frozen H revisions and historical judgments, never prose edits."""
import copy

from .baseline_store import digest


def kind(ref):
    path = (ref.get("source_path") or "").split(".")
    if ref["type"] == "result":
        return "prior_result"
    if ref["type"] != "artifact":
        return None
    if len(path) == 4 and path[1] == "tasks" and path[3] == "revision":
        return "human_feedback"
    if len(path) == 3 and path[1] == "adopted_task_revisions":
        return "human_feedback"
    if len(path) == 3 and path[1] == "prior_results":
        return "prior_result"
    return "current_assessment" if path == ["$", "current_assessment"] else None


def select(ref, value, config, omissions):
    category = kind(ref)
    if category is None or not isinstance(value, dict):
        return value
    rule = config["context_input_selection"][category]
    result = copy.deepcopy(value)

    def remove(key, reason):
        if key in result:
            omissions.append({"ref": ref, "field": key, "reason": reason, "value_sha256": digest(result.pop(key))})

    for key in rule["omit"]:
        remove(key, "context_field_not_needed_for_model_task")
    for key in rule["empty"]:
        if result.get(key) is None or result.get(key) == "":
            remove(key, "empty_context_optional")
    if category == "prior_result" and (value.get("validation_state", "accepted") != "accepted"
            or value.get("conclusion_state") == "unavailable" or not value.get("conclusion")):
        remove("conclusion", "no_accepted_historical_conclusion")
        result["conclusion_state"] = "unavailable"
    return result


def metadata(ref, original, config):
    category = kind(ref)
    if category is None or not isinstance(original, dict):
        return {}
    path = ref.get("source_path") or ""
    use = ("adopted_feedback" if path.startswith("$.adopted_task_revisions.") else
           "selected_comparison" if ref["type"] == "result" else category)
    result = {"context_kind": category, "context_label": config["context_input_selection"]["labels"][use]}
    identity = original.get("id") or (ref["id"] if ref["type"] == "result" else None)
    if identity:
        result["context_identity"] = str(identity)
    if category == "human_feedback" and isinstance(original.get("result_scope"), dict):
        result["original_scope"] = copy.deepcopy(original["result_scope"])
    if category == "prior_result" and original.get("member_deliveries"):
        # Only original membership is available here. Do not invent the old
        # time/object scope; C6 receives that separately from frozen comparison.
        result["original_scope"] = {"alert_ids": sorted({str(m["alert_id"]) for m in original["member_deliveries"]})}
    return result


def scope_key(row):
    return "result_scope" if row.get("context_kind") == "human_feedback" else "declared_scope"


def group_key(row):
    if not row.get("context_identity"):
        return None
    return ("frozen_context", row["context_kind"], row["context_identity"], row["ref"]["role"],
            tuple(row["alert_ids"]), digest(row.get("original_scope")), digest(row["value"]))


def human_refs(value):
    return [(key, value[key]) for key in ("source_refs", "result_source_refs") if key in value]
