"""Retain Case judgments; diagnose citations without widening execution scope."""
import copy
import json
from uuid import UUID, uuid4

import pytest
import test_socai2_case_model_boundary as base_tests
from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as outputs
from app.socai2 import case_output_adapter as c3
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_delivery_projection import make_publication
from app.socai2.case_citation_quality import VALIDATION, links
from app.socai2.case_program_output import UNBOUND_OBSERVATION
from app.socai2.citation_quality import NOTE, new_review
from test_socai2_case_followup_boundary import final_answer
from test_socai2_case_model_boundary import answer_for, prepared_sample

configured, sample = base_tests.configured, base_tests.sample


def faulty_analysis(answer, prepared):
    """Provider substitute deliberately violates citation generation constraints."""
    own = answer["members"][0]["evidence_ids"][0]
    alias = answer["members"][0]["alert_id"]
    label = next(s for s, row in prepared["source_map"].items() if row["ref"]["role"] == "source_label")
    answer["summary"] = "  原主分析摘要：保持原判断。\n"
    answer["members"][0].update(state="analyzed", evidence_ids=[], summary="原成员分析：已分析。")
    answer["members"][1].update(state="analyzed", evidence_ids=[own, own])
    answer["questions"][0].update(state="answered", answer="原问题回答。", evidence_ids=["missing-reference"])
    answer["findings"] = [{"id": "F1", "state": "inferred", "statement": "  原推断正文。\n",
        "alert_ids": [alias], "support_ids": ["missing-reference", "missing-reference"],
        "counter_ids": [own], "alternatives": ["原替代解释。"], "limitations": ["原限制。"]},
        {"id": "F2", "state": "observed", "alert_ids": [alias], "support_ids": [label],
         "counter_ids": [], "alternatives": [], "limitations": []}]
    answer["domains"][0].update(applicability="applicable", reason="原领域分析。", alert_ids=[alias],
                                finding_ids=["F1", "F1", "missing-finding"])
    answer["conflicts"] = [{"id": "X1", "finding_ids": ["F1", "F1"], "state": "resolved",
                            "explanation": "原矛盾判定。", "evidence_ids": []}]
    return answer


def retained(sample):
    context, base = prepared_sample(sample)
    raw = faulty_analysis(answer_for(base, context), base)
    before, review = copy.deepcopy(raw), new_review()
    value = c3.parse(json.dumps(raw), base, context, {}, citation_review=review)
    assert raw == before
    previous = {"analysis": value.model_dump(mode="json"), "source_map": base["source_map"],
                "validation": VALIDATION, "basis": {"citation_review": review}}
    return context, base, raw, value, review, previous


def test_c3_keeps_prose_states_and_records_independent_source_problems(sample):
    context, base, raw, value, review, _ = retained(sample)
    assert value.summary == raw["summary"]
    assert [(m.state, m.summary) for m in value.members] == [(m["state"], m["summary"]) for m in raw["members"]]
    assert value.questions[0].answer == raw["questions"][0]["answer"] and value.questions[0].state == "answered"
    assert value.findings[0].statement == raw["findings"][0]["statement"]
    assert value.findings[1].state == "observed" and value.findings[1].statement == UNBOUND_OBSERVATION
    assert value.domains[0].reason == raw["domains"][0]["reason"] and value.domains[0].applicability == "applicable"
    assert value.conflicts[0].state == "resolved" and value.conflicts[0].explanation == raw["conflicts"][0]["explanation"]
    assert value.conflicts[0].finding_ids == ["F1"] and value.domains[0].finding_ids == ["F1", "missing-finding"]
    codes = {e["code"] for e in review["issues"]}
    assert {"empty_sources", "duplicate_source", "source_not_in_model_input", "source_member_mismatch",
            "non_observation_promoted_to_observed", "unknown_domain_finding", "invalid_conflict_findings"} <= codes
    assert links(value.findings[1].support_ids, base["source_map"], observed=True) == []
    cross = next(r for r in review["references"] if r["path"] == "$.members.1.evidence_ids")
    assert cross["declared_members"] != cross["resolved"][0]["alert_ids"]
    assert review["prose_quality"] == "not_checked"
    with pytest.raises(AnalysisRejected):  # Historical strict receive policy remains available.
        c3.parse(json.dumps(raw), base, context, {})


def test_deep_and_c6_receive_retained_prior_with_warning_and_keep_final(sample):
    context, base, _, _, _, previous = retained(sample)
    qid = context.questions[0].id
    deep = inputs.build("Deep", context, base, {}, previous=previous, prior_id=uuid4(), question_id=qid)
    assert deep["ready"], deep["reason"]
    assert NOTE in deep["messages"][1]["content"] and "原问题回答" in deep["messages"][1]["content"]
    raw_deep = {"action": "answer", "binding_id": None, "reason": "原 Deep 完成理由。",
        "answer": {"state": "supported", "text": "  原 Deep 回答。\n", "support_ids": ["missing-reference"] * 2,
                   "counter_ids": [], "alternatives": ["原替代解释。"], "limitations": []}}
    deep_review = new_review()
    decision = outputs.parse_deep(json.dumps(raw_deep), deep, citation_review=deep_review)
    assert decision.answer.state == "supported" and decision.answer.text == raw_deep["answer"]["text"]
    deep_payload = {"type": "deep_summary", "question_id": qid, "answer": decision.answer.model_dump(mode="json"),
                    "source_map": deep["source_map"], "citation_review": deep_review}
    comparison = {"state": "initial", "result_id": None}
    final = inputs.build("C6", context, base, {str(uuid4()): {"content_json": deep_payload}},
        previous=previous, prior_id=uuid4(), extra={"comparison": comparison})
    assert final["ready"], final["reason"]
    assert NOTE in final["messages"][1]["content"] and "原 Deep 回答" in final["messages"][1]["content"]
    raw = final_answer(final, context, comparison)
    faulty_analysis(raw["analysis"], final)
    raw["conclusion"].update(text="  原最终结论。\n", state="supported", support_ids=[])
    raw["impact"].update(summary="原影响分析。", alert_ids=raw["conclusion"]["alert_ids"],
                         supported_changes=["原影响判定。"], support_ids=[])
    raw["recommendations"][0].update(reason="原建议。", source_ids=[])
    review = new_review()
    value = outputs.parse_final(json.dumps(raw), final, context, comparison, citation_review=review)
    assert value.conclusion.text == raw["conclusion"]["text"] and value.conclusion.state == "supported"
    assert value.impact.summary == raw["impact"]["summary"] and value.impact.supported_changes == raw["impact"]["supported_changes"]
    assert value.recommendations[0].reason == raw["recommendations"][0]["reason"]
    pub, _ = make_publication(value, context, {UUID(a): {"read_state": "read"} for a in context.alerts},
        final, comparison, {"delivery_state": "complete", "graph_artifact_id": uuid4()}, uuid4(), None)
    assert pub.validation_state == "accepted" and pub.conclusion == raw["conclusion"]["text"]
    assert all(m.conclusion_covered for m in pub.members)
    assert pub.members[0].evidence_refs == [] and pub.members[0].assessment_state == "analyzed"
    assert pub.findings[1].state == "observed" and pub.findings[1].support == []
    # Citation tolerance never authorizes missing analysis or a foreign identity.
    raw["analysis"]["members"][0]["state"] = "not_analyzed"
    with pytest.raises(AnalysisRejected, match="unanalysed_member_in_conclusion"):
        outputs.parse_final(json.dumps(raw), final, context, comparison, citation_review=new_review())


@pytest.mark.parametrize("fault", ["unknown_member", "duplicate_definition", "missing_question", "unknown_binding"])
def test_structural_and_execution_guards_remain_strict(sample, fault):
    context, base = prepared_sample(sample)
    raw = faulty_analysis(answer_for(base, context), base)
    if fault == "unknown_member":
        raw["members"][0]["alert_id"] = "foreign-member"
    elif fault == "duplicate_definition":
        raw["findings"][1]["id"] = "F1"
    elif fault == "missing_question":
        raw["questions"].pop()
    else:
        raw["followups"] = [{"question_id": context.questions[0].id, "alert_ids": [raw["members"][0]["alert_id"]],
            "mode": "query", "objective": "原查询理由。", "required_evidence": "原待查证据。", "source_ids": [],
            "object_keys": [], "binding_id": "unoffered", "priority": "decision_critical"}]
    with pytest.raises(AnalysisRejected):
        c3.parse(json.dumps(raw), base, context, {}, citation_review=new_review())


def test_deep_missing_sources_and_receipt_role_do_not_change_supported_state():
    from app.socai2.baseline_deep_contract import parse
    source = {"ref": {"type": "artifact", "id": str(uuid4()), "role": "execution_receipt"}, "alert_ids": []}
    for ids in ([], ["receipt"], ["unknown"]):
        raw = {"question_id": "q", "action": "answer", "binding_id": None, "reason": "原理由。",
            "answer": {"state": "supported", "text": "原回答。", "support_ids": ids, "counter_ids": [],
                       "alternatives": [], "limitations": []}}
        review = new_review()
        value = parse(json.dumps(raw), {"receipt": source}, {}, "q", citation_review=review)
        assert value.answer.state == "supported" and value.answer.text == raw["answer"]["text"]
        assert review["state"] == "issues_recorded" and links(ids, {"receipt": source}, evidence_only=True) == []
    raw["action"], raw["binding_id"], raw["answer"] = "query", "unoffered", None
    with pytest.raises(AnalysisRejected, match="unoffered_query"):
        parse(json.dumps(raw), {}, {}, "q", citation_review=new_review())
