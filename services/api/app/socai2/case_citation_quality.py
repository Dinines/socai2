"""Case citation diagnostics; structural identity and execution guards stay strict."""
from .citation_quality import FIELDS, NOTE, issue, normalize

VALIDATION = "structure_scope_checked"
SOURCE_FIELDS = FIELDS | {"finding_ids"}
LIMITATION_CODES = {
    "member_limitations_required", "question_limitations_required", "finding_limitations_required",
    "unapplied_domain_needs_limitations", "unresolved_answer_needs_limitations", "uncertain_conclusion_needs_limits",
}
LIMITATION_NOTE = "前序模型分析保留原判断；部分限制说明缺失，已记录质量问题，不代表正文已核实。"
QUALITY_CODES = {
    "duplicate_source", "source_not_in_model_input", "source_member_mismatch",
    "member_source_coverage_missing", "unseen_member_marked_analyzed", "answered_question_needs_sources",
    "same_source_as_support_and_counterevidence", "non_observation_promoted_to_observed",
    "observed_requires_activity_source", "direct_alert_membership_not_proven",
    "duplicate_domain_finding", "unknown_domain_finding", "domain_finding_scope_mismatch",
    "duplicate_conflict_finding", "invalid_conflict_findings", "resolved_conflict_needs_sources",
    "source_not_in_model_input_or_duplicate", "execution_receipt_is_not_evidence", "supported_answer_needs_sources",
    "delivery_source_not_visible_or_duplicate", "execution_receipt_not_conclusion_evidence",
    "delivery_source_coverage_missing", "comparison_needs_selected_baseline_and_current_sources",
    "recommendation_needs_sources",
} | LIMITATION_CODES


def reject_or_record(review, code, path="$", **details):
    if review is None or code not in QUALITY_CODES:
        from .baseline_analysis_contract import AnalysisRejected
        raise AnalysisRejected(code)
    if code in LIMITATION_CODES:
        details["category"] = "explanation_completeness"
    issue(review, code, path, **details)


def normalized(value, review, path="$"):
    return normalize(value, review, path, fields=SOURCE_FIELDS) if review is not None else value


def links(ids, sources, *, evidence_only=False, observed=False):
    return [sources[sid]["ref"] for sid in dict.fromkeys(ids) if sid in sources
            and (not evidence_only or sources[sid]["ref"]["role"] != "execution_receipt")
            and (not observed or sources[sid]["ref"]["role"] == "observation"
                 and sources[sid].get("membership_basis") != "query_binding_only" and not sources[sid].get("knowledge"))]


def accepted(payload):
    return payload.get("validation") in {"structure_scope_sources_checked", VALIDATION}


def with_note(value, payload):
    review = payload.get("citation_review") or (payload.get("basis") or {}).get("citation_review") or {}
    if review.get("state") != "issues_recorded":
        return value
    codes = {item["code"] for item in review["issues"]}
    notes = ([NOTE] if codes - LIMITATION_CODES else []) + ([LIMITATION_NOTE] if codes & LIMITATION_CODES else [])
    return {**value, "citation_quality_note": " ".join(notes)}
