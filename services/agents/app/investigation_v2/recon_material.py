"""Pure retained-material preparation; no dispatch, saving or publication.

The owner must verify the CommittedMaterial claim before calling. A projection
block preserves checked references, but never adopts facts from a missing view.
"""
from __future__ import annotations

from dataclasses import replace
import json

from .business_profile import BusinessProfileRequest
from .evidence_view import CommittedMaterial, EvidenceProjectionBlocked, build_evidence_view
from .execution_store import canonical_json, content_hash
from .fixed_recon import COMPLETION_POLICY_REF, EXECUTION_STOPS, _window_coverage, evaluate_alert_recon


def prepare_alert_recon(request: BusinessProfileRequest, query_result: dict, material: CommittedMaterial,
                        revision: int, *, execution_stop: str | None = None) -> dict:
    if not isinstance(request, BusinessProfileRequest):
        raise ValueError("checked_business_request_required")
    request = replace(request)
    if request.profile != "alert_recon":
        raise ValueError("fixed_recon_requires_alert_profile")
    if execution_stop is not None and (not isinstance(execution_stop, str) or execution_stop not in EXECUTION_STOPS):
        raise ValueError("unsupported_execution_stop")
    blocked, document = None, None
    try:
        evidence = build_evidence_view(request.context, query_result, material, revision)
    except EvidenceProjectionBlocked as exc:
        # Only this builder invocation can supply the checked block receipt;
        # arbitrary ValueError/contract/retention failures are never downgraded.
        blocked = exc.receipt
        query = blocked["query"]
        gaps = set(query["coverage"]["gaps"]) | {"material_projection_blocked"}
        blockers = {"material_projection_blocked"}
        if execution_stop is not None:
            gaps.add("execution_" + execution_stop)
            blockers.add("execution_" + execution_stop)
        binding = request.descriptor
        result = {
            "schema": "blocked_alert_recon.v1", "profile": request.profile,
            "completion_policy_ref": COMPLETION_POLICY_REF, "binding_ref": binding["binding_ref"],
            "tenant_id": str(request.context.tenant_id), "run_id": str(request.context.run_id),
            "delivery_target": binding["delivery_target"], "snapshot_ref": None, "revision": revision,
            "facts": [], "questions": [
                {"question": q.question_id, "critical": q.critical, "decision_dependency": q.decision_dependency,
                 "status": "unassessed", "finding_ids": [], "capability_gaps": list(q.capability_gaps),
                 "material_gap": "material_projection_blocked", "policy_reason": q.policy_reason}
                for q in request.context.questions],
            "held_refs": sorted({*blocked["held_refs"], blocked["material"]["artifact_ref"]}),
            "coverage": _window_coverage(request.context, query),
            "coverage_gaps": sorted(gaps), "blocking_gaps": sorted(blockers),
            "source_state": query["status"], "source_available": query["status"] in {"ok", "empty"},
            "execution_state": query["execution_state"], "scope_readiness": "partial",
            "completion_basis": "limited_source_observation_only", "nature": "unresolved", "authorization": "unknown",
            "status": "stopped", "execution_stop": execution_stop,
            "stop_reason": execution_stop or "material_projection_blocked",
            "handoff": {"review_required": True, "automatic_query": False, "automatic_model": False,
                        "case_action": "not_requested", "run_completion": "not_published",
                        "delivery_status": "required", "next_step": "review_retained_material_projection"}}
        result["result_ref"] = "blocked-recon:" + content_hash(canonical_json(result))
    else:
        document = json.loads(evidence.canonical_doc)
        result = evaluate_alert_recon(request, evidence, current_snapshot_ref=evidence.snapshot_ref,
                                      execution_stop=execution_stop)
    preparation = {
        "schema": "alert_recon_preparation.v1", "material_state": "material_projection_blocked" if blocked else "view_ready",
        "completion_policy_ref": COMPLETION_POLICY_REF, "material": blocked["material"] if blocked else document["material"],
        "evidence_snapshot_ref": None if blocked else result["snapshot_ref"],
        "evidence_document": document, "projection_block": blocked, "result": result,
        "persistence_status": "not_attempted"}
    preparation["preparation_ref"] = "recon-preparation:" + content_hash(canonical_json(preparation))
    return json.loads(canonical_json(preparation))
