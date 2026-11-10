"""Directory of registered frozen sources; no judgment from model prose.

One immutable material is one entry. Observation leaves are references, not
separate counts. Query receipts remain separately readable Run artifacts.
"""
from uuid import UUID, uuid5

from pydantic import ValidationError
from sqlalchemy import update

from .baseline_store import C, StoreError, digest
from .case_data import OCSF_OBSERVATION_PATHS, Lookup, pointer, save_index
from .case_data_contracts import KIND, SCHEMA, EvidenceIndex


def saved_ref(kind, identity, path, role):
    return {"type": kind, "id": str(identity), "external": None,
        "source_path": path, "row_keys": [], "role": role}


def material_entry(aid, material):
    if material["material_state"] != "complete":
        return None
    root = ["ocsf_json"]
    if not isinstance(material.get("ocsf_json"), dict):
        raw = material.get("raw_json") or {}
        root = ["raw_json", "ocsf_event"] if isinstance(raw, dict) and isinstance(raw.get("ocsf_event"), dict) else ["raw_json", "raw_event"]
    refs = []
    for path in sorted(OCSF_OBSERVATION_PATHS):
        source_path = "/" + "/".join([*root, *path])
        try:
            value = pointer(material, source_path)
        except StoreError:
            continue
        if type(value) in {str, int, float} and (not isinstance(value, str) or value.strip()):
            refs.append(saved_ref("alert_material", material["id"], source_path, "observation"))
    if not refs:
        return None
    return {"evidence_id": "material:" + str(material["id"]), "title": "告警原始材料 · " + aid,
        "type": "alert_material", "alert_ids": [aid], "object_keys": [], "source_refs": refs,
        "verdict": "unknown", "verdict_sources": [], "threat": None, "remediation": None, "state": "active"}


async def publish_directory(store, run, context, step_id):
    """Inside C6's locked publication transaction, before adopting its result."""
    cas = await store.case(run["case_id"])
    current = cas["current_evidence_artifact_id"]
    if (cas["scope_revision"] != context.case["scope_revision"]
            or str(current) != str(context.case.get("current_evidence_artifact_id"))):
        return {"state": "skipped", "reason": "case_evidence_or_scope_changed", "artifact_id": None}
    if current:
        previous = await Lookup(store)("artifact", current)
        if (previous is None or previous["case_id"] != run["case_id"]
                or previous["kind"] != KIND or previous["schema_version"] != SCHEMA
                or digest(previous["content_json"]) != previous["sha256"]):
            return {"state": "skipped", "reason": "existing_evidence_directory_invalid", "artifact_id": None}
        try:
            prior = EvidenceIndex.model_validate(previous["content_json"])
        except ValidationError:
            return {"state": "skipped", "reason": "existing_evidence_directory_invalid", "artifact_id": None}
        curated = previous["run_id"] is None or any(e.state == "withdrawn" or e.verdict != "unknown"
            or e.threat is not None or e.remediation is not None for e in prior.entries)
        if curated:
            return {"state": "skipped", "reason": "existing_curated_evidence_directory",
                "artifact_id": str(current)}
    fresh = await store.input_freshness(run["id"])
    if fresh["state"] != "current":
        return {"state": "skipped", "reason": "stale_input", "artifact_id": None}
    entries, omissions = [], []
    for aid, item in sorted(context.alerts.items()):
        if not item.material:
            omissions.append("frozen_material_missing")
            continue
        material = await store.read_material(run["case_id"], run["id"], UUID(item.material["id"]))
        if material["material_state"] != "complete":
            omissions.append("frozen_material_not_complete")
        entry = material_entry(aid, material)
        if entry:
            entries.append(entry)
    revisions = {str(t.revision["id"]): t.revision for t in context.tasks.values() if t.usable_feedback}
    revisions.update({identity: revision for identity, revision in context.adopted_task_revisions.items()
        if context.citation_roles.get(f"$.adopted_task_revisions.{identity}") == "human_statement"})
    for identity, revision in sorted(revisions.items()):
        entries.append({"evidence_id": "human:" + identity, "title": "人工反馈 · " + identity,
            "type": "human_statement", "alert_ids": revision["result_scope"]["alert_ids"], "object_keys": [],
            "source_refs": [saved_ref("task_revision", identity, "/result_text", "human_statement")],
            "verdict": "unknown", "verdict_sources": [], "threat": None, "remediation": None, "state": "active"})
    if len(entries) > 500:
        entries = entries[:500]
        omissions.append("registered_directory_entry_limit")
    limitations = ["registered_material_observations_and_frozen_human_feedback_only",
        "query_receipts_remain_in_run_artifacts_not_counted_as_independent_entries",
        "no_evidence_specific_verdict_or_threat_assignment_available", *sorted(set(omissions))]
    index = EvidenceIndex(schema_version=SCHEMA, scope_revision=cas["scope_revision"],
        alert_ids=sorted(context.alerts), supersedes_artifact_id=current,
        availability_state="partial" if omissions else "available", limitations=limitations, entries=entries)
    now = await store.now()
    try:
        identity = await save_index(store, cas, index, actor_id=run["requested_by"], now=now,
            run_id=run["id"], step_id=step_id)
    except StoreError as exc:
        # Distinguish failed generation from a successfully empty directory.
        index = index.model_copy(update={"availability_state": "unavailable", "entries": [],
            "limitations": ["evidence_directory_validation_failed", exc.code]})
        identity = await save_index(store, cas, index, actor_id=run["requested_by"], now=now,
            run_id=run["id"], step_id=step_id)
    await store.db.execute(update(C).where(*store.where(C, C.c.id == run["case_id"])).values(
        current_evidence_artifact_id=identity, row_version=C.c.row_version + 1, business_updated_at=now))
    receipt = {"state": index.availability_state, "artifact_id": str(identity),
        "entries": len(index.entries), "source_run_id": str(run["id"]), "limitations": index.limitations}
    await store.event(run["case_id"], uuid5(run["id"], "socai2-evidence-directory-v1"),
        {"type": "service", "user_id": None, "name_snapshot": None,
         "service_name": "socai2.baseline", "service_version": run["executor_version"]},
        "case_evidence_published", receipt, [("case_id", run["case_id"],
            {"current_evidence_artifact_id": str(current) if current else None},
            {"current_evidence_artifact_id": str(identity)})])
    return receipt
