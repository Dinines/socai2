"""Business changes, separate from immutable source identities and execution metadata."""
import copy

from .baseline_store import encoded

VERSION = "socai2.case-update-input.v1"


def ordered(values):
    return sorted(values, key=encoded)


def scope(value):
    if not isinstance(value, dict):
        return value
    return {key: ordered(item) if key in {"alert_ids", "object_keys"} else copy.deepcopy(item)
            for key, item in value.items()}


def rows(values):
    """Only generated row labels/housekeeping are omitted; evidence references stay literal."""
    return ordered([{key: scope(value) if key == "scope" else copy.deepcopy(value)
                     for key, value in row.items()
                     if key not in {"id", "actor", "created_at", "updated_at", "source_ids"}}
                    for row in (values or [])])


def assessment(value):
    if value is None:
        return None
    return {**{key: value.get(key) for key in ("verdict", "rationale", "confidence", "score_state")},
            "recommendations": rows(value.get("recommendations"))}


def diagnosis(item):
    material = getattr(item, "analysis_material", None)
    if material:
        return copy.deepcopy(material["business_view"])
    if not item.diagnosis_usable or not item.diagnosis_scope:
        return None
    raw = item.diagnosis
    body = raw["diagnosis"]
    return {"summary": raw.get("summary"), "conclusion": body.get("conclusion"),
            "findings": rows(body.get("findings")), "open_questions": rows(raw.get("open_questions")),
            "source_refs": ordered(body.get("source_refs", [])),
            "limitations": ordered(body.get("limitations", [])),
            "analysis_coverage": {key: sorted(value) for key, value in
                (body.get("delivery_assessment", {}).get("member_coverage") or {}).items()},
            "case_member_ids": sorted(item.diagnosis_scope["case_covered_alert_ids"]),
            "member_ids": sorted(item.diagnosis_scope["input_selection"]["selected_alert_ids"])}


def business_view(context):
    return {"version": VERSION,
        "alerts": {aid: {"triage": assessment(item.triage) if item.triage_usable else None,
            "feedback": assessment(item.feedback) if item.feedback and
                item.feedback.get("input_material_id") == item.alert.get("latest_material_id") else None}
            for aid, item in sorted(context.alerts.items())},
        "incidents": {iid: diagnosis(item) for iid, item in sorted(context.incidents.items())},
        "human_feedback": {tid: {"result_text": item.revision["result_text"],
            "result_scope": scope(item.revision["result_scope"]),
            "source_refs": ordered(item.revision.get("source_refs", []))}
            for tid, item in sorted(context.tasks.items()) if item.usable_feedback}}


def trigger_view(value, incident_ids=None):
    # The same *current* receiver set filters both snapshots. Switching a pointer
    # is not itself input, and inactive I updates do not broadcast to old Cases.
    return {**value, "incidents": {iid: row for iid, row in value["incidents"].items()
            if row is not None and (incident_ids is None or iid in incident_ids)}}


def unchanged(old_context, current, incident_ids=None):
    old = (old_context.update_context or {}).get("business_view") or business_view(old_context)
    if incident_ids is not None:
        # A disappearing/stale diagnosis is not a new upstream conclusion.
        # Only currently terminal I materials can drive this automatic check;
        # alert changes reach Case through I, while effective H stays independent.
        applicable = {iid for iid in incident_ids if current["incidents"].get(iid) is not None}

        def automatic(value):
            return {"human_feedback": value["human_feedback"], "incidents": {
                iid: {key: field for key, field in row.items() if key != "case_member_ids"}
                for iid in applicable if (row := value["incidents"].get(iid)) is not None}}

        return automatic(old) == automatic(current)
    return trigger_view(old, incident_ids) == trigger_view(current, incident_ids)
