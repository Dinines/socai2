"""M6.1 pure post-query policy for one checked alert's limited observations.

No dispatch, durable admission, retries, models or publication. The owner must
supply the current checked view and any already-observed execution stop. Those
preconditions do not grant new work: every result stops and retains its gaps.
"""
from __future__ import annotations

from dataclasses import replace
import json

from .analysis_adoption import checked_view, _predicate
from .business_profile import BusinessProfileRequest
from .evidence_view import EvidenceView
from .execution_store import canonical_json, content_hash

EXECUTION_STOPS = frozenset({"budget_limit", "deadline", "unknown_attempt", "retention_gap", "cancelled"})
_BLOCKING_GAPS = frozenset({"query_rows_truncated", "source_body_truncated", "source_identity_conflict",
                            "undelivered_conflict_versions", "member_coverage_incomplete"})


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def evaluate_alert_recon(request: BusinessProfileRequest, evidence: EvidenceView | None, *,
                         current_snapshot_ref: str | None, execution_stop: str | None = None) -> dict:
    """Return detached finite facts and a stop handoff, never a Run completion.

    ``execution_stop`` only restricts this result; M6.2 must obtain the actual
    cause from the owned M3 runtime. It is not an independent budget/clock gate.
    """
    _require(isinstance(request, BusinessProfileRequest), "checked_business_request_required")
    request = replace(request)  # Recheck the fixed scope/target/profile binding.
    _require(request.profile == "alert_recon", "fixed_recon_requires_alert_profile")
    _require(execution_stop is None or isinstance(execution_stop, str) and execution_stop in EXECUTION_STOPS,
             "unsupported_execution_stop")
    context, binding = request.context, request.descriptor
    facts, held_refs, gaps, blockers = [], [], set(), set()
    statuses = {q.question_id: "unassessed" for q in context.questions}
    snapshot_ref = None
    revision = None
    if evidence is None:
        _require(current_snapshot_ref is None, "current_view_missing")
        gaps.add("committed_source_material_missing")
        blockers.add("committed_source_material_missing")
    else:
        visible = checked_view(context, evidence)
        _require(current_snapshot_ref == evidence.snapshot_ref, "stale_input_snapshot")
        document = json.loads(evidence.canonical_doc)
        _require(document["schema"] == "network_evidence_view.v1"
                 and document["material"]["retention"] == "committed", "committed_evidence_view_required")
        snapshot_ref, revision = evidence.snapshot_ref, evidence.revision
        _require(type(revision) is int and revision > 0, "positive_view_revision_required")
        events, query, alert, index = visible["events"], visible["query"], visible["alert"], evidence.index
        _require(len(events) <= context.query_scope.max_limit, "source_version_limit_exceeded")
        held_refs = sorted(index)
        gaps.update(query["coverage"]["gaps"])
        blockers.update(gaps & _BLOCKING_GAPS)
        blockers.update(gap for gap in gaps if gap.startswith("source_excerpt_"))

        def add(claim: str, question: str, refs: list[str]) -> None:
            fact = _predicate({"claim": claim, "question": question, "refs": refs}, visible, index)
            body = {"question": question, "fact": fact, "evidence_refs": refs,
                    "snapshot_ref": snapshot_ref, "binding_ref": binding["binding_ref"]}
            facts.append({**body, "id": "program-finding:" + content_hash(canonical_json(body)),
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
    ready = not blockers and all(statuses[q.question_id] == "supported"
                                 for q in context.questions if q.decision_dependency)
    result = {"schema": "fixed_alert_recon.v1", "profile": request.profile, "binding_ref": binding["binding_ref"],
              "tenant_id": str(context.tenant_id), "run_id": str(context.run_id),
              "delivery_target": binding["delivery_target"], "snapshot_ref": snapshot_ref, "revision": revision,
              "facts": facts, "questions": questions, "held_refs": held_refs, "coverage_gaps": sorted(gaps),
              "blocking_gaps": sorted(blockers), "scope_readiness": "ready" if ready else "partial",
              "completion_basis": "limited_source_observation_only", "nature": "unresolved", "authorization": "unknown",
              "status": "stopped", "execution_stop": execution_stop,
              "stop_reason": execution_stop or ("limited_objective_answered" if ready else "material_gap"),
              "handoff": {"review_required": not ready, "automatic_query": False, "automatic_model": False,
                          "case_action": "not_requested", "run_completion": "not_published"}}
    result["result_ref"] = "fixed-recon:" + content_hash(canonical_json(result))
    return json.loads(canonical_json(result))
