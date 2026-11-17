"""A/I retention policy: source quality never rewrites a business judgment."""
import copy
import json

import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_store import StoreError, digest
from app.socai2.citation_quality import new_review, seal
from test_socai2_stage_partial_review import packet


@pytest.mark.parametrize("verdict,ids", [
    ("true_positive", ["missing"]), ("benign", []),
    ("false_positive", ["N1_S1", "N1_S1"]), ("needs_review", []),
])
def test_alert_retains_judgment_advice_and_prose(verdict, ids):
    sources, data, raw, _ = packet()
    kinds = {"true_positive": "malicious_behavior", "benign": "authorized_or_expected_behavior",
             "false_positive": "refuted_detection"}
    raw.update(verdict=verdict, evidence_ids=ids, rationale="  原判定与原说明。\n",
        decision_basis=None if verdict == "needs_review" else {
            "kind": kinds[verdict], "claim": "原主张。", "source_ids": ids})
    sources["N1_S1"]["ref"]["role"] = "source_label"
    content = json.dumps(raw, ensure_ascii=False)
    diagnostics, review = [], new_review()
    result = alert.parse(content, sources, data, diagnostics=diagnostics, citation_review=review)
    assert result.verdict == verdict and result.rationale == raw["rationale"]
    assert result.confidence == raw["confidence"] and result.explanation == raw["explanation"]
    assert [v.reason for v in result.recommendations] == [v["reason"] for v in raw["recommendations"]]
    assert not result.recommendations[1].source_refs
    assert json.loads(content) == raw and review["state"] == "issues_recorded"
    assert all(d["severity"] != "error" for d in diagnostics)
    seal(review, content, result.model_dump(mode="json"))
    assert review["original_sha256"] == digest(content) and review["conclusion_modified"] is False
    if len(ids) == 2:
        assert review["processing"][0] == {"path": "$.evidence_ids", "action": "deduplicate_source_list",
                                           "before": ids, "after": ["N1_S1"]}


def test_incident_keeps_scope_and_all_business_units_with_reference_issues():
    sources, data, _, raw = packet()
    raw["summary"] = "  原事件摘要。\n"
    raw["members"][1]["assessment"] = "  原成员分析。\n"
    raw["evidence_ids"] = ["not-an-alias"]
    raw["members"][1]["source_ids"] = ["N1_S1", "N1_S1"]
    raw["findings"][0]["source_ids"] = []
    raw["open_questions"][0]["source_ids"] = ["N9_S9"]
    before = copy.deepcopy(raw)
    review = new_review()
    result, members = incident.parse(json.dumps(raw), sources, data, citation_review=review)
    assert raw == before
    assert (result.summary, result.conclusion) == (raw["summary"], raw["conclusion"])
    assert [m["state"] for m in members] == [m["state"] for m in raw["members"]]
    assert result.findings[1].statement == raw["members"][1]["assessment"]
    assert str(result.findings[1].scope.alert_ids[0]) == raw["members"][1]["alert_id"]
    assert str(result.findings[1].support[0].id) == sources["N1_S1"]["ref"]["id"]
    assert result.findings[2].statement == raw["findings"][0]["statement"]
    assert not result.findings[2].support and result.findings[2].state == "unresolved"
    assert result.open_questions[0].text == raw["open_questions"][0]["text"]
    assert not result.source_refs and not result.open_questions[0].evidence_refs
    detail = next(r for r in review["references"] if r["path"] == "$.members.1.source_ids")
    assert detail["declared_members"] == [raw["members"][1]["alert_id"]]
    assert detail["resolved"][0]["alert_ids"] == [raw["members"][0]["alert_id"]]


def test_combined_references_cover_multiple_members_without_false_scope_issue():
    sources, data, _, raw = packet()
    raw["findings"][0].update(alert_ids=[m["alert_id"] for m in raw["members"]], source_ids=list(sources))
    review = new_review()
    incident.parse(json.dumps(raw), sources, data, citation_review=review)
    assert review["state"] == "checked" and not review["issues"]


@pytest.mark.parametrize("failure", ["malformed", "unknown_member", "duplicate_member", "duplicate_finding"])
def test_structural_identity_errors_still_reject(failure):
    sources, data, _, raw = packet()
    if failure == "unknown_member":
        raw["members"][0]["alert_id"] = "00000000-0000-0000-0000-000000000099"
    elif failure == "duplicate_member":
        raw["members"][1]["alert_id"] = raw["members"][0]["alert_id"]
    elif failure == "duplicate_finding":
        raw["findings"].append(copy.deepcopy(raw["findings"][0]))
    review = new_review()
    with pytest.raises(StoreError):
        incident.parse("{broken" if failure == "malformed" else json.dumps(raw), sources, data, citation_review=review)
    if failure == "malformed":
        assert review["state"] == "not_checked"
