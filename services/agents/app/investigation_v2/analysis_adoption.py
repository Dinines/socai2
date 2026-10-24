"""M4.1b finite network-observation predicates, not a generic truth checker.

The model proposes temporary keys and explanations. Only the predicates below
have program-checked semantics; free prose stays model_assessed and is excluded
from the readable facts. No IO, completion decision, response action or retry.
"""
from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any

from .evidence_view import EvidenceView
from .execution_store import canonical_json, content_hash, scope_fingerprint
from .scope import ScopeContext

MODES = frozenset({"combined_analysis", "focused_analysis"})
QUESTIONS = ("Q1", "Q2", "Q5")
MAX_FINDINGS = 6
MAX_PROPOSALS = 2
_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
_CLAIMS = {"network_observed": "Q1", "outcome_unknown": "Q1", "source_versions_conflict": "Q1",
           "alert_linked": "Q2", "bounded_query": "Q5", "query_empty": "Q5", "source_unavailable": "Q5"}


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _strings(value: Any, *, minimum: int = 0, maximum: int = 6) -> bool:
    return (isinstance(value, list) and minimum <= len(value) <= maximum
            and all(isinstance(v, str) for v in value) and len(set(value)) == len(value))


def _prose(value: Any) -> bool:
    return isinstance(value, str) and len(value.encode("utf-8")) <= 1024


def checked_view(context: ScopeContext, view: EvidenceView) -> dict:
    _require(isinstance(context, ScopeContext) and isinstance(view, EvidenceView), "trusted_scope_and_view_required")
    document = json.loads(view.canonical_doc)
    reference = document["model_view"].pop("snapshot_ref")
    _require(reference == "ev:" + content_hash(canonical_json(document)), "view_integrity_mismatch")
    _require(view.scope_hash == scope_fingerprint(context), "view_scope_mismatch")
    _require(document["model_view"]["questions"] == list(QUESTIONS), "question_group_mismatch")
    return view.model_view


def _predicate(finding: dict, model_view: dict, index: dict) -> dict:
    claim, refs = finding["claim"], finding["refs"]
    _require(claim in _CLAIMS and finding["question"] == _CLAIMS[claim], "unsupported_claim_or_question")
    _require(_strings(refs, minimum=1, maximum=10) and all(ref in index for ref in refs), "missing_or_unknown_reference")
    events = {e["ref"]: e for e in model_view["events"]}
    cited = [events[r] for r in refs if r in events]
    query, alert = model_view["query"], model_view["alert"]
    if claim in {"network_observed", "outcome_unknown"}:
        _require(len(refs) == len(cited) == 1, "one_source_version_required")
        field, expected = ("action", "network_connection_observed") if claim == "network_observed" else ("outcome", "unknown")
        _require(cited[0]["fields"][field] == expected, "source_does_not_support_predicate")
        return {"predicate": claim, "source_identity": cited[0]["identity"], "source_version": cited[0]["version"],
                "fields": cited[0]["fields"], "conflict": cited[0]["conflict"]}
    if claim == "alert_linked":
        _require(len(refs) == 2 and len(cited) == 1 and alert["ref"] in refs, "alert_and_one_source_required")
        event_id = cited[0]["identity"].rsplit(":", 1)[1]
        _require(event_id in alert["source_event_ids"], "no_exact_source_id_association")
        return {"predicate": claim, "event_id": event_id, "association": "exact_declared_source_id_only"}
    if claim == "source_versions_conflict":
        _require(len(cited) == len(refs) and len({e["identity"] for e in cited}) == 1, "same_source_identity_required")
        _require(all(e["conflict"] for e in cited), "source_conflict_not_observed")
        all_visible = {e["ref"] for e in events.values() if e["identity"] == cited[0]["identity"]}
        _require(set(refs) == all_visible, "conflict_omits_visible_counterversion")
        return {"predicate": claim, "source_identity": cited[0]["identity"],
                "visible_versions": sorted(e["version"] for e in cited),
                "missing_version_hashes": sorted({v for e in cited for v in e["missing_version_hashes"]})}
    _require(refs == [query["ref"]], "query_receipt_reference_required")
    if claim == "bounded_query":
        _require(query["status"] == "ok" and query["executed"] is True, "successful_query_required")
    elif claim == "query_empty":
        _require(query["status"] == "empty" and query["executed"] is True and query["returned_count"] == 0,
                 "successful_empty_query_required")
    else:
        _require(query["status"] in {"unavailable", "error", "rejected"}, "source_failure_required")
    return {"predicate": claim, "status": query["status"], "executed": query["executed"],
            "execution_state": query["execution_state"], "returned_count": query["returned_count"],
            "truncated": query["truncated"], "coverage": query["coverage"]}


def adopt_candidate(context: ScopeContext, view: EvidenceView, candidate: Any, *, mode: str,
                    current_snapshot_ref: str) -> dict:
    """Adopt independently valid parts; the owner supplies the current snapshot.

    This does not publish a latest-result pointer or provide concurrent snapshot
    CAS. The later single-owner executor must supply its current snapshot here.
    A stale result remains a candidate and cannot overwrite current findings.
    """
    result = {"schema": "network_analysis_adoption.v1", "snapshot_ref": view.snapshot_ref,
              "mode": mode, "candidate_ref": None, "status": "rejected", "findings": [],
              "answers": [], "assessment": None, "rejections": [], "proposals": [],
              "scope_readiness": "not_evaluated", "nature": "unresolved", "authorization": "unknown",
              "retained_questions": [{"question": q.question_id, "critical": q.critical,
                                      "status": "unassessed", "capability_gaps": list(q.capability_gaps)}
                                     for q in context.questions]}
    try:
        visible = checked_view(context, view)
        _require(mode in MODES, "unsupported_analysis_mode")
        _require(current_snapshot_ref == view.snapshot_ref, "stale_input_snapshot")
        body = canonical_json(candidate, max_bytes=32 * 1024)
        result["candidate_ref"] = "candidate:" + content_hash(body)
        candidate = json.loads(body)
        _require(isinstance(candidate, dict) and set(candidate) ==
                 {"snapshot_ref", "mode", "findings", "answers", "assessment", "proposals"}, "candidate_shape")
        _require(candidate["snapshot_ref"] == view.snapshot_ref and candidate["mode"] == mode,
                 "candidate_task_version_mismatch")
        _require(isinstance(candidate["findings"], list) and len(candidate["findings"]) <= MAX_FINDINGS,
                 "finding_limit")
        _require(isinstance(candidate["answers"], list) and len(candidate["answers"]) <= len(QUESTIONS), "answer_limit")
        _require(isinstance(candidate["proposals"], list) and len(candidate["proposals"]) <= MAX_PROPOSALS,
                 "proposal_limit")
    except (ValueError, TypeError, KeyError) as exc:
        result["rejections"].append({"part": "candidate", "reason": str(exc)})
        return result

    counts = Counter(f.get("key") for f in candidate["findings"] if isinstance(f, dict) and isinstance(f.get("key"), str))
    adopted = {}
    index = view.index
    for number, finding in enumerate(candidate["findings"]):
        key = finding.get("key") if isinstance(finding, dict) else None
        try:
            _require(isinstance(finding, dict) and set(finding) == {"key", "question", "claim", "refs", "rationale"},
                     "finding_shape")
            _require(isinstance(key, str) and bool(_KEY.fullmatch(key)) and counts[key] == 1, "ambiguous_finding_key")
            _require(_prose(finding["rationale"]), "rationale_limit")
            fact = _predicate(finding, visible, index)
            accepted = {"id": "finding:" + content_hash(canonical_json([view.snapshot_ref, key, fact])),
                        "candidate_key": key, "question": finding["question"], "revision": view.revision,
                        "adoption": "admitted", "assurance": "rule_checked", "validity": "current", "kind": "source_observation",
                        "evidence_refs": finding["refs"], "fact": fact,
                        "model_assessed_rationale": finding["rationale"]}
            adopted[key] = accepted
            result["findings"].append(accepted)
        except (ValueError, TypeError, KeyError) as exc:
            result["rejections"].append({"part": "finding", "index": number,
                                          "candidate_key": key if isinstance(key, str) else None, "reason": str(exc)})

    answers = {}
    answer_counts = Counter(a.get("question") for a in candidate["answers"]
                            if isinstance(a, dict) and isinstance(a.get("question"), str))
    for number, answer in enumerate(candidate["answers"]):
        try:
            _require(isinstance(answer, dict) and set(answer) == {"question", "status", "finding_keys", "rationale"},
                     "answer_shape")
            question, status, keys = answer["question"], answer["status"], answer["finding_keys"]
            _require(isinstance(question, str) and question in QUESTIONS and answer_counts[question] == 1,
                     "ambiguous_or_unrequested_question")
            _require(_strings(keys) and all(k in adopted for k in keys), "answer_depends_on_rejected_finding")
            _require(_prose(answer["rationale"]), "rationale_limit")
            claims = {adopted[k]["fact"]["predicate"] for k in keys}
            has_conflict = any(e["conflict"] for e in visible["events"])
            if status == "supported":
                required = {"Q1": {"network_observed"}, "Q2": {"alert_linked"},
                            "Q5": {"bounded_query", "query_empty", "source_unavailable"}}[question]
                _require(bool(claims & required), "answer_not_supported_by_predicate")
                _require(question != "Q1" or not has_conflict, "answer_ignores_source_conflict")
            elif status == "conflicting":
                _require(question == "Q1" and "source_versions_conflict" in claims, "answer_conflict_not_supported")
            elif status in {"insufficient_evidence", "unassessed"}:
                # A cautious but unhelpful answer remains visible. The M4
                # useful-judgment gate, separately, must not count it as pass.
                pass
            else:
                raise ValueError("unsupported_answer_status")
            accepted = {"question": question, "status": status, "revision": view.revision,
                        "finding_ids": [adopted[k]["id"] for k in keys], "adoption": "admitted",
                        "model_assessed_rationale": answer["rationale"]}
            answers[question] = accepted
            result["answers"].append(accepted)
        except (ValueError, TypeError, KeyError) as exc:
            result["rejections"].append({"part": "answer", "index": number, "reason": str(exc)})
    for question in result["retained_questions"]:
        if question["question"] in answers:
            question["status"] = answers[question["question"]]["status"]

    assessment = candidate["assessment"]
    if assessment is not None:
        try:
            _require(mode == "combined_analysis", "focused_has_no_overall_assessment")
            _require(isinstance(assessment, dict) and set(assessment) ==
                     {"finding_keys", "nature", "authorization", "rationale"}, "assessment_shape")
            keys = assessment["finding_keys"]
            _require(_strings(keys, minimum=1) and all(k in adopted for k in keys), "assessment_depends_on_rejected_finding")
            _require(set(answers) == set(QUESTIONS), "assessment_missing_question_results")
            _require(any(adopted[k]["question"] == "Q5" for k in keys), "assessment_missing_coverage")
            _require(assessment["nature"] == "unresolved" and assessment["authorization"] == "unknown",
                     "assessment_exceeds_policy_axes")
            _require(_prose(assessment["rationale"]), "rationale_limit")
            result["assessment"] = {"id": "assessment:" + content_hash(canonical_json([view.snapshot_ref, assessment])),
                                    "revision": view.revision, "adoption": "admitted", "assurance": "model_assessed", "validity": "current",
                                    "nature": "unresolved", "authorization": "unknown",
                                    "finding_ids": [adopted[k]["id"] for k in keys],
                                    "model_assessed_rationale": assessment["rationale"]}
        except (ValueError, TypeError, KeyError) as exc:
            result["rejections"].append({"part": "assessment", "reason": str(exc)})
    elif mode == "combined_analysis":
        result["rejections"].append({"part": "assessment", "reason": "combined_assessment_missing"})
    for number, proposal in enumerate(candidate["proposals"]):
        if (isinstance(proposal, dict) and set(proposal) == {"question", "rationale"}
                and proposal["question"] in QUESTIONS and _prose(proposal["rationale"])):
            result["proposals"].append({**proposal, "adoption": "deferred", "executable": False})
        else:
            result["rejections"].append({"part": "proposal", "index": number, "reason": "proposal_shape_or_scope"})
    result["status"] = "partial" if result["rejections"] else "admitted"
    return result


def readable_facts(result: dict) -> dict:
    """A bounded review projection, not a report or completion manifest.

    Never promote free model prose to a program-verified fact. Model output and
    its rationale remain available in the candidate/adoption artifacts.
    """
    return {"snapshot_ref": result["snapshot_ref"],
            "facts": [f["fact"] for f in result["findings"]],
            "answers": [{k: a[k] for k in ("question", "status", "finding_ids")} for a in result["answers"]],
            "nature": "unresolved", "authorization": "unknown", "scope_readiness": "not_evaluated",
            "has_overall_candidate": result["assessment"] is not None}
