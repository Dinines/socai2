"""I delivery completeness from saved, validated units; never infer verdicts from prose."""
from typing import Literal

from .baseline_contracts import Contract
from .baseline_store import StoreError

VERSION = "socai2.incident-delivery.v1"


class MemberCoverage(Contract):
    expected_ids: list[str]
    analyzed_ids: list[str]
    not_reviewed_ids: list[str]
    missing_ids: list[str]


class ReviewItems(Contract):
    state: Literal["required", "none_listed", "unknown"]
    unresolved_member_ids: list[str]
    unresolved_finding_ids: list[str]
    open_question_ids: list[str]


class IncidentDelivery(Contract):
    schema_version: Literal["socai2.incident-delivery.v1"]
    state: Literal["complete", "partial", "none"]
    reasons: list[str]
    member_coverage: MemberCoverage
    review_items: ReviewItems


def assess(source, *, output=None, members=None, partial_review=None):
    """Only the executor supplies parsed members; a missing directory is partial.

    Source availability, needs_review, unanswered questions, freshness and
    adoption are separate facts. An explicit not_reviewed member is unfinished
    analysis, unlike an analyzed member with unresolved business questions.
    """
    expected = [m["alert"]["id"] for m in source["members"]]
    if output is not None and partial_review is not None:
        raise StoreError("incident_delivery_inputs_conflict", 422)
    if partial_review is not None:
        kept = partial_review["retained_analysis"]
        members = kept["members"]
        findings, questions = kept["findings"], kept["open_questions"]
    else:
        findings, questions = (output or {}).get("findings", []), (output or {}).get("open_questions", [])
    members = members or []
    ids = [m["alert_id"] for m in members]
    if (len(ids) != len(set(ids)) or not set(ids) <= set(expected)
            or any(m["state"] not in {"summarized", "unresolved", "not_reviewed"} for m in members)):
        raise StoreError("incident_delivery_member_scope_invalid", 422)
    analyzed = [m["alert_id"] for m in members if m["state"] != "not_reviewed"]
    unread = [m["alert_id"] for m in members if m["state"] == "not_reviewed"]
    missing = [aid for aid in expected if aid not in ids]
    # Each parsed member also produces a member:<UUID> finding. It is not an
    # additional event finding, nor does not_reviewed become analyzed this way.
    event_findings = [f for f in findings if not f["id"].startswith("member:")]
    usable = bool(output is not None or analyzed or event_findings or questions)
    reasons = []
    if partial_review is not None:
        reasons.append("invalid_response_units_excluded")
    if missing:
        reasons.append("member_analysis_missing")
    if unread:
        reasons.append("member_analysis_not_completed")
    state = "complete" if output is not None and not reasons else "partial" if usable else "none"
    if state == "none":
        reasons.append("no_valid_analysis_content")
    unresolved = [m["alert_id"] for m in members if m["state"] == "unresolved"]
    unresolved_findings = [f["id"] for f in event_findings if f["state"] == "unresolved"]
    open_questions = [q["id"] for q in questions if q["state"] in {"open", "unresolved", "not_attempted"}]
    review = "required" if unresolved or unresolved_findings or open_questions else "none_listed" if state == "complete" else "unknown"
    return IncidentDelivery(schema_version=VERSION, state=state, reasons=reasons,
        member_coverage=MemberCoverage(expected_ids=expected, analyzed_ids=analyzed,
            not_reviewed_ids=unread, missing_ids=missing),
        review_items=ReviewItems(state=review, unresolved_member_ids=unresolved,
            unresolved_finding_ids=unresolved_findings, open_question_ids=open_questions)).model_dump(mode="json")
