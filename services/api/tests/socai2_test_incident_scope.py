"""Explicit synthetic selection added to copies of old, immutable Case fixtures."""
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_incident_scope import freeze
from app.socai2.incident_inputs import SELECTION_VERSION
from app.socai2.stage_inputs import VERSION


def attach(item, case_members, *, selected=None, covered=None, unresolved=None):
    selected = list(selected if selected is not None else item["member_ids"])
    covered = list(covered if covered is not None else selected)
    unresolved = list(unresolved if unresolved is not None else covered)
    diagnosis = item["diagnosis"]
    diagnosis["diagnosis"]["delivery_assessment"] = {
        "member_coverage": {"expected_ids": selected, "analyzed_ids": covered,
                            "not_reviewed_ids": sorted(set(selected) - set(covered)), "missing_ids": []},
        "review_items": {"unresolved_member_ids": unresolved}, "reasons": [],
    }
    body = {"version": VERSION, "kind": "incident_diagnosis", "parent": {"id": diagnosis["incident_id"]},
            "members": [{"alert": {"id": aid}} for aid in selected], "selection_version": SELECTION_VERSION,
            "input_selection": {"selected_alert_ids": selected, "limit": len(selected),
                "policy": "recently_linked", "order": "linked_at_desc_alert_id_asc",
                "captured_at": "2026-11-15T00:00:00+00:00", "total_member_count": len(item["member_ids"]),
                "selected_count": len(selected), "omitted_count": len(item["member_ids"]) - len(selected)}}
    diagnosis["source_fingerprint"] = digest(body)
    source = {"source_run_id": diagnosis["source_run_id"], "run_state": "completed",
              "input_artifact_id": diagnosis["input_artifact_id"], "material_state": "complete", "blob_ref": None,
              "sha256": digest(body), "size_bytes": len(encoded(body)), "content_json": body}
    item["diagnosis_scope"], reasons = freeze(diagnosis["incident_id"], diagnosis, source, case_members)
    item["diagnosis_usable"] = bool(item["diagnosis_scope"] and item["diagnosis_scope"]["case_covered_alert_ids"])
    item["limitations"].extend(reasons)
    return source
