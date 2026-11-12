"""Citation failures retain independent units, never invent a valid judgment."""
import copy
import json
from uuid import UUID

import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_store import StoreError
from app.socai2.stage_answer_review import (
    citation_feedback,
    review_alert,
    review_incident,
)


def packet(n=2):
    aids = [str(UUID(int=i + 1)) for i in range(n)]
    sources = {f"N1_S{i+1}": {"alert_ids": [aid], "ref": {"type": "alert_material",
        "id": str(UUID(int=1000 + i)), "external": None, "role": "observation",
        "source_path": "$.ocsf_json.process.pid", "row_keys": []}} for i, aid in enumerate(aids)}
    data = {"citations": "structured_v3", "stored_material_state": "complete", "omissions": {},
        "source_statuses": [], "items": [], "members": [{"alert_id": aid, "included": 1,
            "triage_eligible": False, "triage_freshness": "unavailable"} for aid in aids]}
    a = {"verdict": "needs_review", "confidence": .2, "rationale": "已记录行为，授权待核。",
         "explanation": "现有证据不足以定性。", "evidence_ids": ["N1_S1"],
         "decision_basis": None, "limitations": [], "recommendations": [
             {"reason": "核对来源。", "source_ids": ["N1_S1"]},
             {"reason": "该建议引用错误。", "source_ids": ["N1_S999"]}]}
    i = {"summary": "原始摘要依赖范围未知。", "conclusion": "原始总体判断。",
        "evidence_ids": ["N1_S1"], "limitations": [],
        "members": [{"alert_id": aid, "state": "summarized", "assessment": "成员记录已阅读。",
            "source_ids": [sid], "limitations": []} for aid, sid in zip(aids, sources)],
        "findings": [{"id": "F1", "statement": "第一条记录待核。", "state": "unresolved",
            "alert_ids": [aids[0]], "source_ids": ["N1_S1"], "limitations": []}],
        "open_questions": [{"text": "核对授权。", "alert_ids": [aids[0]],
            "source_ids": ["N1_S1"], "evidence_requirements": ["人工确认"]}]}
    return sources, data, a, i


def test_citation_feedback_uses_wire_paths_and_preserves_original():
    sources, data, answer, _ = packet()
    answer.update(recommendations=[], evidence_ids=["N1_S1", "N1_S1"])
    content, diagnostics = json.dumps(answer), []
    with pytest.raises(StoreError, match="alert_answer_source_invalid"):
        alert.parse(content, sources, data, diagnostics=diagnostics)
    feedback = citation_feedback("A", content, sources, diagnostics, {"source_map": sources})
    assert feedback["errors"] == [{"path": "$.evidence_ids", "code": "alert_answer_source_invalid"}]
    assert json.loads(content)["evidence_ids"] == ["N1_S1", "N1_S1"]
    assert citation_feedback("A", content, sources, diagnostics, None) is None
    diagnostics.append({"path": "$", "code": "model_usage_unknown_or_inconsistent", "severity": "error"})
    assert citation_feedback("A", content, sources, diagnostics, {"source_map": sources}) is None


def test_only_bad_advice_dropped_original_assessment_preserved():
    sources, data, raw, _ = packet()
    before = copy.deepcopy(raw)
    with pytest.raises(StoreError):
        alert.parse(json.dumps(raw), sources, data)
    result, review = review_alert(json.dumps(raw), sources, data)
    assert raw == before and result.verdict == raw["verdict"]
    assert result.confidence == raw["confidence"] and result.rationale == raw["rationale"]
    assert [r.id for r in result.recommendations] == ["R1"]
    assert review["conclusion_adoptable"] is True
    assert review["diagnostics"][0]["path"] == ["recommendations", 1]


def test_bad_global_evidence_preserves_valid_advice_without_replacement_judgment():
    sources, data, raw, _ = packet()
    raw.update(verdict="benign", evidence_ids=["N1_S999"], decision_basis={
        "kind": "authorized_or_expected_behavior", "claim": "无据授权主张。", "source_ids": ["N1_S999"]})
    result, review = review_alert(json.dumps(raw), sources, data)
    assert result is None and review["conclusion_adoptable"] is False
    assert review["retained_analysis"]["assessment"] is None
    assert len(review["retained_analysis"]["recommendations"]) == 1
    assert "无据授权主张" not in json.dumps(review, ensure_ascii=False)


def test_wrong_member_reference_keeps_other_member_finding_and_question():
    sources, data, _, raw = packet()
    raw["members"][1]["source_ids"] = ["N1_S1"]
    review = review_incident(json.dumps(raw), sources, data)
    kept = review["retained_analysis"]
    assert [m["alert_id"] for m in kept["members"]] == [data["members"][0]["alert_id"]]
    assert len(kept["findings"]) == 2 and len(kept["open_questions"]) == 1
    assert kept["summary"] is None and kept["conclusion"] is None
    assert not review["conclusion_adoptable"]
    assert review["diagnostics"][0]["path"] == ["members", 1]


def test_diagnostic_truncation_cannot_make_invalid_later_member_valid():
    sources, data, _, raw = packet(72)
    # Valid inline references create many presentation warnings. The invalid
    # final member is still revalidated even if the original log stops at 64.
    for member, sid in zip(raw["members"], sources):
        member["assessment"] += f" ({sid})"
    raw["members"][-1]["source_ids"] = ["N1_S1"]
    diagnostics = []
    with pytest.raises(StoreError):
        incident.parse(json.dumps(raw), sources, data, diagnostics=diagnostics)
    assert len(diagnostics) == 64 and all(d["severity"] == "warning" for d in diagnostics)
    kept = review_incident(json.dumps(raw), sources, data)["retained_analysis"]
    assert len(kept["members"]) == 71
    assert data["members"][-1]["alert_id"] not in {m["alert_id"] for m in kept["members"]}


@pytest.mark.parametrize("failure", ["shape", "duplicate", "identity", "ambiguous_finding"])
def test_global_invalid_incident_is_not_salvaged(failure):
    sources, data, _, raw = packet()
    if failure == "shape":
        raw["members"] = None
    elif failure == "identity":
        raw["members"][1]["alert_id"] = raw["members"][0]["alert_id"]
    elif failure == "ambiguous_finding":
        raw["findings"].append(copy.deepcopy(raw["findings"][0]))
    content = json.dumps(raw)
    if failure == "duplicate":
        content = content[:-1] + ', "members": []}'
    assert review_incident(content, sources, data) is None
