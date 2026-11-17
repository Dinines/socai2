"""D2: explanatory gaps preserve model judgments and downstream use."""
import copy
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import test_socai2_case_model_boundary as base_tests
from app.socai2 import (
    case_followup_input,
    case_followup_output,
    case_output_adapter,
    runtime_policy,
)
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_delivery_projection import make_publication
from app.socai2.case_citation_quality import VALIDATION
from app.socai2.citation_quality import new_review
from test_socai2_case_followup_boundary import final_answer
from test_socai2_case_model_boundary import answer_for, prepared_sample

sample = base_tests.sample


@pytest.fixture
def configured(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(root /
        "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml"))
    runtime_policy.active_policy.cache_clear()
    yield runtime_policy.active_policy()
    runtime_policy.active_policy.cache_clear()


@pytest.mark.parametrize("section,code", [
    ("members", "member_limitations_required"),
    ("questions", "question_limitations_required"),
    ("findings", "finding_limitations_required"),
    ("domains", "unapplied_domain_needs_limitations"),
])
def test_c3_explanatory_gap_survives_and_enters_final_input(sample, section, code):
    context, prepared = prepared_sample(sample)
    raw = answer_for(prepared, context)
    if section == "findings":
        raw[section] = [{"id": "F1", "state": "unresolved", "statement": "原发现仍需核实。",
            "alert_ids": [raw["members"][0]["alert_id"]], "support_ids": [], "counter_ids": [],
            "alternatives": [], "limitations": []}]
    else:
        raw[section][0]["limitations"] = []
    original = copy.deepcopy(raw)
    review = new_review()
    parsed = case_output_adapter.parse(json.dumps(raw, ensure_ascii=False), prepared, context, {},
                                       citation_review=review)
    assert raw == original
    assert getattr(parsed, section)[0].limitations == []
    assert parsed.summary == raw["summary"]
    entry = next(item for item in review["issues"] if item["code"] == code)
    assert entry["category"] == "explanation_completeness"
    assert entry["action"] == "retain_judgment"
    assert review["prose_quality"] == "not_checked"
    previous = {"analysis": parsed.model_dump(mode="json"), "source_map": prepared["source_map"],
                "validation": VALIDATION, "basis": {"citation_review": review}}
    final = case_followup_input.build("C6", context, prepared, {}, previous=previous, prior_id=uuid4(),
                                      extra={"comparison": {"state": "initial", "result_id": None}})
    assert final["ready"], final["reason"]
    assert "限制说明" in final["messages"][1]["content"]
    assert "Synthetic unresolved analysis." in final["messages"][1]["content"]


def test_deep_unresolved_answer_retains_empty_limitations_and_text(sample):
    context, prepared = prepared_sample(sample)
    deep = case_followup_input.build("Deep", context, prepared, {}, question_id=context.questions[0].id)
    assert deep["ready"], deep["reason"]
    raw = {"action": "handoff", "binding_id": None, "reason": "仍需额外核查。",
           "answer": {"state": "unresolved", "text": "  原分析结论，保留空白。\n", "support_ids": [],
                      "counter_ids": [], "alternatives": [], "limitations": []}}
    before, review = copy.deepcopy(raw), new_review()
    value = case_followup_output.parse_deep(json.dumps(raw, ensure_ascii=False), deep, citation_review=review)
    assert raw == before and value.action == "handoff"
    assert value.answer.text == raw["answer"]["text"]
    assert value.answer.state == "unresolved" and value.answer.limitations == []
    assert any(i["code"] == "unresolved_answer_needs_limitations" for i in review["issues"])


def test_c6_keeps_conclusion_with_missing_limits_and_citation_issues(sample):
    context, base = prepared_sample(sample)
    comparison = {"state": "initial", "result_id": None}
    prepared = case_followup_input.build("C6", context, base, {}, extra={"comparison": comparison})
    assert prepared["ready"], prepared["reason"]
    raw = final_answer(prepared, context, comparison)
    raw["conclusion"].update(text="  当前行为性质仍需核实。\n", state="uncertain", limitations=[],
                             support_ids=["missing-reference", "missing-reference"])
    raw["analysis"]["domains"][0].update(applicability="not_applicable", limitations=[])
    original, review = copy.deepcopy(raw), new_review()
    value = case_followup_output.parse_final(json.dumps(raw, ensure_ascii=False), prepared, context,
                                            comparison, citation_review=review)
    assert raw == original
    assert value.conclusion.text == raw["conclusion"]["text"]
    assert value.conclusion.state == "uncertain" and value.conclusion.limitations == []
    codes = {item["code"] for item in review["issues"]}
    assert {"unapplied_domain_needs_limitations", "uncertain_conclusion_needs_limits", "duplicate_source"} <= codes
    pub, _ = make_publication(value, context, {UUID(a): {"read_state": "read"} for a in context.alerts},
        prepared, comparison, {"delivery_state": "complete", "graph_artifact_id": uuid4()}, uuid4(), None)
    assert pub.terminal_state == "completed" and pub.validation_state == "accepted"
    assert pub.conclusion == raw["conclusion"]["text"] and pub.conclusion_state == "uncertain"
    assert all(m.conclusion_covered for m in pub.members)
    assert review["prose_quality"] == "not_checked"


def test_program_observation_keeps_full_fields_but_rejects_authored_statement(sample):
    from app.socai2.case_program_output import observed_text, validate_program

    context, prepared = prepared_sample(sample)
    raw = answer_for(prepared, context)
    source = raw["members"][0]["evidence_ids"][0]
    boundary = prepared["case_boundary"]
    literal = "完整原字段" * 300
    boundary["observation_literals"][source]["value"] = literal
    raw["findings"] = [{"id": "F1", "state": "observed", "alert_ids": [raw["members"][0]["alert_id"]],
        "support_ids": [source], "counter_ids": [], "alternatives": [], "limitations": []}]
    expected = observed_text(raw["findings"][0], boundary)
    parsed = case_output_adapter.parse(json.dumps(raw, ensure_ascii=False), prepared, context, {},
                                       citation_review=new_review())
    assert len(expected) > 1200 and parsed.findings[0].statement == expected and literal in expected
    changed = parsed.model_dump(mode="json")
    changed["findings"][0]["statement"] = "篡改原字段"
    with pytest.raises(AnalysisRejected, match="observed_program_text_mismatch"):
        validate_program(changed, boundary, citation_review=new_review())
    raw["findings"][0]["statement"] = expected
    with pytest.raises(AnalysisRejected, match="observed_statement_is_program_owned"):
        case_output_adapter.parse(json.dumps(raw, ensure_ascii=False), prepared, context, {}, citation_review=new_review())


@pytest.mark.parametrize("state", ["inferred", "unresolved"])
def test_generated_finding_keeps_original_text_limit(sample, state):
    context, prepared = prepared_sample(sample)
    raw = answer_for(prepared, context)
    raw["findings"] = [{"id": "F1", "state": state, "statement": "长" * 1201,
        "alert_ids": [raw["members"][0]["alert_id"]], "support_ids": [], "counter_ids": [],
        "alternatives": [], "limitations": ["仍需核实"]}]
    with pytest.raises(AnalysisRejected, match="case_output_shape_or_alias_invalid"):
        case_output_adapter.parse(json.dumps(raw, ensure_ascii=False), prepared, context, {}, citation_review=new_review())
