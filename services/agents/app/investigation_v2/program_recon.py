"""Pure finite structured-source facts under explicit new program policies.

Only the trusted owner supplies current material and observed execution stops.
No auth/retention proof, dispatch, model call, storage, Run completion or old
runtime selection occurs here. The complete Alert prose remains unassessed.
"""
from __future__ import annotations

from dataclasses import replace
import json

from .analysis_adoption import _predicate
from .business_profile import BusinessProfileRequest
from .evidence_view import CommittedMaterial
from .execution_store import canonical_json, content_hash, scope_snapshot
from .fixed_recon import EXECUTION_STOPS, _BLOCKING_GAPS, _window_coverage
from .program_material import (ProgramMaterial, build_program_material, checked_program_material,
    MATERIAL_SCHEMA, MATERIAL_POLICY_REF, MODEL_PROJECTION, FREE_TEXT_SEMANTICS)

FACT_POLICY_REF = "finite_network_program_fields.v1"
COMPLETION_POLICY_REF = "bounded_full_window_program_fields.v1"
RESULT_SCHEMA = "program_alert_recon.v1"
PREPARATION_SCHEMA = "program_alert_recon_preparation.v1"
_TARGET_OUTSIDE_GAPS = frozenset({"alert_free_text_not_semantically_assessed", "model_projection_not_requested"})


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def evaluate_program_alert_recon(request: BusinessProfileRequest, material: ProgramMaterial | None, *,
                                 current_snapshot_ref: str | None, execution_stop: str | None = None) -> dict:
    """Stop with finite facts; ready refers only to structured source fields."""
    _require(isinstance(request, BusinessProfileRequest), "checked_business_request_required")
    request = replace(request)  # Recheck the fixed scope/target/profile binding.
    _require(request.profile == "alert_recon", "fixed_recon_requires_alert_profile")
    _require(execution_stop is None or isinstance(execution_stop, str) and execution_stop in EXECUTION_STOPS,
             "unsupported_execution_stop")
    context, binding = request.context, request.descriptor
    _, frozen_sources = scope_snapshot(context)
    source_refs = sorted(frozen_sources)
    facts, held_refs, gaps, blockers = [], list(source_refs), set(_TARGET_OUTSIDE_GAPS), set()
    statuses = {q.question_id: "unassessed" for q in context.questions}
    snapshot_ref = None
    revision = None
    query = None
    if material is None:
        _require(current_snapshot_ref is None, "current_program_material_missing")
        gaps.add("committed_source_material_missing")
        blockers.add("committed_source_material_missing")
    else:
        document = checked_program_material(context, material, current_snapshot_ref=current_snapshot_ref)
        _require(document["schema"] == MATERIAL_SCHEMA and document["material_policy_ref"] == MATERIAL_POLICY_REF
                 and document["material"]["retention"] == "committed", "committed_program_material_required")
        # Internal predicate input is structured source data, not an EvidenceView
        # or a model input document. No model eligibility follows from it.
        fields_input = {"events": document["records"], "query": document["query"], "alert": document["alert"]}
        snapshot_ref, revision = material.snapshot_ref, material.revision
        _require(type(revision) is int and revision > 0, "positive_view_revision_required")
        events, query, alert, index = fields_input["events"], fields_input["query"], fields_input["alert"], material.index
        _require(len(events) <= context.query_scope.max_limit, "source_version_limit_exceeded")
        held_refs = sorted({*index, *source_refs, document["material"]["artifact_ref"]})
        gaps.update(query["coverage"]["gaps"])
        blockers.update(gaps & _BLOCKING_GAPS)
        blockers.update(gap for gap in gaps if gap.startswith("source_excerpt_"))

        def add(claim: str, question: str, refs: list[str]) -> None:
            fact = _predicate({"claim": claim, "question": question, "refs": refs}, fields_input, index)
            body = {"fact_policy_ref": FACT_POLICY_REF, "material_schema": MATERIAL_SCHEMA,
                    "question": question, "fact": fact, "evidence_refs": refs,
                    "snapshot_ref": snapshot_ref, "binding_ref": binding["binding_ref"]}
            facts.append({**body, "id": "program-field-finding:" + content_hash(canonical_json(body)),
                          "revision": revision, "origin": "program", "assurance": "rule_checked",
                          "validity": "current", "dependency_refs": [snapshot_ref, *refs]})

        for event in events:
            if event["fields"]["action"] == "network_connection_observed":
                add("network_observed", "Q1", [event["ref"]])
            else:
                gaps.add("unsupported_source_action")
                blockers.add("unsupported_source_action")
            if event["fields"]["outcome"] == "unknown":
                add("outcome_unknown", "Q1", [event["ref"]])
            if event["identity"].rsplit(":", 1)[1] in alert["source_event_ids"]:
                add("alert_linked", "Q2", [alert["ref"], event["ref"]])

        conflicts = sorted({event["identity"] for event in events if event["conflict"]})
        for identity in conflicts:
            add("source_versions_conflict", "Q1", [e["ref"] for e in events if e["identity"] == identity])
        if query["status"] in {"ok", "empty"}:
            add("query_empty" if query["status"] == "empty" else "bounded_query", "Q5", [query["ref"]])
        else:
            add("source_unavailable", "Q5", [query["ref"]])
        _require(len(facts) <= 4 * context.query_scope.max_limit + 1, "program_fact_limit_exceeded")
        claims = {fact["fact"]["predicate"] for fact in facts}
        statuses["Q1"] = ("conflicting" if conflicts else
                          "supported" if "network_observed" in claims else "insufficient_evidence")
        statuses["Q2"] = "supported" if "alert_linked" in claims else "insufficient_evidence"
        statuses["Q5"] = "supported"  # Supports the coverage statement, including a failed/empty query.
        if statuses["Q1"] != "supported":
            blockers.add("source_observation_not_resolved")
        if statuses["Q2"] != "supported":
            gaps.add("no_exact_alert_source_link")
        if query["status"] not in {"ok", "empty"}:
            blockers.add("source_not_available")
    coverage = _window_coverage(context, query)
    if coverage["covered_window"] is not None and not coverage["full_window_queried"]:
        gaps.add("query_window_coverage_incomplete")
        blockers.add("query_window_coverage_incomplete")
    if execution_stop is not None:
        gaps.add("execution_" + execution_stop)
        blockers.add("execution_" + execution_stop)
    questions = []
    for question in context.questions:
        questions.append({"question": question.question_id, "critical": question.critical,
                          "decision_dependency": question.decision_dependency,
                          "status": statuses[question.question_id],
                          "finding_ids": [fact["id"] for fact in facts if fact["question"] == question.question_id],
                          "capability_gaps": list(question.capability_gaps), "policy_reason": question.policy_reason})
    ready = not blockers and coverage["full_window_queried"] and all(statuses[q.question_id] == "supported"
                                 for q in context.questions if q.decision_dependency)
    result = {"schema": RESULT_SCHEMA, "profile": request.profile, "binding_ref": binding["binding_ref"],
              "tenant_id": str(context.tenant_id), "run_id": str(context.run_id),
              "delivery_target": binding["delivery_target"], "snapshot_ref": snapshot_ref, "revision": revision,
              "material_schema": MATERIAL_SCHEMA, "material_policy_ref": MATERIAL_POLICY_REF, "fact_policy_ref": FACT_POLICY_REF,
              "program_material_state": "missing" if material is None else "program_material_validated",
              "model_projection": dict(MODEL_PROJECTION), "free_text_semantics": FREE_TEXT_SEMANTICS,
              "source_state": query["status"] if query is not None else "not_confirmed",
              "source_available": query["status"] in {"ok", "empty"} if query is not None else None,
              "execution_state": query["execution_state"] if query is not None else "unknown",
              "facts": facts, "questions": questions, "held_refs": held_refs, "coverage_gaps": sorted(gaps),
              "blocking_gaps": sorted(blockers), "scope_readiness": "ready" if ready else "partial",
              "completion_policy_ref": COMPLETION_POLICY_REF, "coverage": coverage,
              "completion_basis": "bounded_structured_source_fields_only", "nature": "unresolved", "authorization": "unknown",
              "status": "stopped", "execution_stop": execution_stop,
              "stop_reason": execution_stop or ("limited_objective_answered" if ready else "material_gap"),
              "handoff": {"review_required": not ready, "automatic_query": False, "automatic_model": False,
                          "case_action": "not_requested", "run_completion": "not_published"}}
    result["result_ref"] = "program-recon:" + content_hash(canonical_json(result))
    return json.loads(canonical_json(result))


def prepare_program_alert_recon(request: BusinessProfileRequest, query_result: dict, tool_material: CommittedMaterial,
                                revision: int, *, execution_stop: str | None = None) -> dict:
    """Caller owns frozen begin/tool material; this result is not persisted."""
    _require(isinstance(request, BusinessProfileRequest), "checked_business_request_required")
    request = replace(request)
    _require(request.profile == "alert_recon", "fixed_recon_requires_alert_profile")
    _require(execution_stop is None or isinstance(execution_stop, str) and execution_stop in EXECUTION_STOPS,
             "unsupported_execution_stop")
    material = build_program_material(request.context, query_result, tool_material, revision)
    result = evaluate_program_alert_recon(request, material, current_snapshot_ref=material.snapshot_ref,
                                         execution_stop=execution_stop)
    doc = json.loads(material.canonical_doc)
    preparation = {"schema": PREPARATION_SCHEMA, "material_state": "program_material_validated", "material": doc["material"],
        "material_policy_ref": MATERIAL_POLICY_REF, "fact_policy_ref": FACT_POLICY_REF, "completion_policy_ref": COMPLETION_POLICY_REF,
        "program_material_document": doc, "program_material_snapshot_ref": material.snapshot_ref,
        "model_projection": dict(MODEL_PROJECTION), "result": result, "persistence_status": "not_attempted"}
    preparation["preparation_ref"] = "program-recon-preparation:" + content_hash(canonical_json(preparation))
    return json.loads(canonical_json(preparation))
