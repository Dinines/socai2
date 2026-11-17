"""Freeze the selected diagnosis's own input and coverage, never today's members."""
import copy

from .incident_inputs import SELECTION_VERSION, coverage
from .stage_inputs import VERSION

# Part of the same C1 statement that selects the diagnosis pointer. The full
# artifact is transient for integrity checks; C1 only retains its scope/identity.
SOURCE_SQL = """(SELECT jsonb_build_object(
 'source_run_id',r.id,'run_state',r.state,'input_artifact_id',f.id,
 'material_state',f.material_state,'blob_ref',f.blob_ref,
 'sha256',f.sha256,'size_bytes',f.size_bytes,'content_json',f.content_json)
 FROM socai2.incident_diagnoses d
 JOIN socai2.runs r ON r.tenant_id=d.tenant_id AND r.id=d.source_run_id
   AND r.kind='incident_diagnosis' AND r.incident_id=d.incident_id
 JOIN socai2.artifacts f ON f.tenant_id=d.tenant_id AND f.id=d.input_artifact_id
   AND f.id=r.input_artifact_id AND f.run_id=r.id AND f.incident_id=d.incident_id
   AND f.kind='input_snapshot'
 WHERE d.tenant_id=:tenant AND d.incident_id=i.id AND d.id=i.latest_diagnosis_id)"""


def freeze(incident_id, diagnosis, source, case_members):
    """An unavailable upstream scope excludes that judgment, not the whole Case."""
    from .baseline_store import digest, encoded

    if not diagnosis:
        return None, []
    if not source:
        return None, ["diagnosis_scope_unavailable"]
    body = source.get("content_json")
    if (not isinstance(body, dict) or source.get("run_state") != "completed"
            or source.get("material_state") != "complete" or source.get("blob_ref") is not None
            or source.get("source_run_id") != diagnosis.get("source_run_id")
            or source.get("input_artifact_id") != diagnosis.get("input_artifact_id")
            or source.get("sha256") != diagnosis.get("source_fingerprint")
            or digest(body) != source.get("sha256") or len(encoded(body)) != source.get("size_bytes")):
        return None, ["diagnosis_scope_source_invalid"]
    selection = body.get("input_selection")
    if (body.get("version") != VERSION or body.get("kind") != "incident_diagnosis"
            or (body.get("parent") or {}).get("id") != str(incident_id)
            or body.get("selection_version") != SELECTION_VERSION or not isinstance(selection, dict)):
        return None, ["diagnosis_scope_unavailable"]
    try:
        selected = selection["selected_alert_ids"]
        frozen = [row["alert"]["id"] for row in body["members"]]
        if (not isinstance(selected, list) or not all(isinstance(aid, str) for aid in selected)
                or len(set(selected)) != len(selected) or sorted(selected) != sorted(frozen)
                or any(type(selection[key]) is not int for key in
                       ("limit", "total_member_count", "selected_count", "omitted_count"))
                or selection["selected_count"] != len(selected)
                or not 0 < len(selected) <= selection["limit"]
                or selection["omitted_count"] < 0
                or selection["total_member_count"] != len(selected) + selection["omitted_count"]):
            return None, ["diagnosis_scope_selection_invalid"]
        actual = coverage(body, diagnosis.get("diagnosis"))
    except (KeyError, TypeError, ValueError):
        return None, ["diagnosis_scope_selection_invalid"]
    if not actual or actual["state"] == "unknown":
        return None, ["diagnosis_analysis_coverage_unavailable"]
    members = set(map(str, case_members))
    result = {"source_run_id": source["source_run_id"], "input_artifact_id": source["input_artifact_id"],
              "source_fingerprint": source["sha256"], "input_selection": copy.deepcopy(selection),
              "analysis_coverage": actual,
              "case_selected_alert_ids": sorted(set(selected) & members),
              "case_covered_alert_ids": sorted(set(actual["covered_alert_ids"]) & members)}
    reasons = [] if result["case_covered_alert_ids"] else ["diagnosis_no_analyzed_member_overlap"]
    if set(selected) - members:
        reasons.append("diagnosis_scope_extends_beyond_case")
    return result, reasons


def source_members(item, path, case_members):
    """Association for a diagnosis field; individual statements keep their scope."""
    frozen = item.diagnosis_scope
    if not item.diagnosis_usable or not frozen:
        return []
    parts = path.split(".")
    if "findings" in parts or "open_questions" in parts:
        value = item.diagnosis
        for part in parts[4:]:  # $.incidents.<id>.diagnosis
            value = value[int(part)] if isinstance(value, list) else value[part]
        selected = set(frozen["input_selection"]["selected_alert_ids"])
        return sorted(set((value.get("scope") or {}).get("alert_ids", [])) & selected & set(case_members))
    return list(frozen["case_covered_alert_ids"])
