"""Direct C3 boundary/merge checks; no model substitute or generation calls."""
import copy
import json
from pathlib import Path

import pytest
import test_socai2_case_model_boundary as base
from app.socai2 import case_c3_completion as completion
from app.socai2 import case_c3_delivery as units
from app.socai2 import case_followup_input as followup
from app.socai2 import case_output_adapter as output
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from app.socai2.case_c3_sections import SECTIONS, read_sections
from app.socai2.citation_quality import new_review
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError

configured, sample = base.configured, base.sample
ROOT = Path(__file__).resolve().parents[3]


def test_saved_real_truncation_retains_six_sections_with_citation_issues():
    folder = ROOT / "docs/operations/evidence/c3-capacity-20261114-01"
    plan = json.loads((folder / "plan.json").read_text())
    text = (folder / "C02-4096/answer.txt").read_text()
    sections, review = read_sections(text), new_review()
    assert list(sections["retained"]) == list(SECTIONS[:-1]) and sections["missing"] == ["followups"]
    for key, (start, end) in sections["value_spans"].items():
        assert json.loads(text[start:end]) == sections["retained"][key]
    original = copy.deepcopy(sections["retained"])
    restored = completion.validate_sections(original, plan["prepared"], Context.model_validate(plan["context"]),
        plan["bindings"], restored=True, citation_review=review)
    assert original == sections["retained"] and "followups" not in restored and review["issues"]


@pytest.mark.parametrize("missing", [["followups"], ["questions", "domains"]])
def test_missing_fields_frozen_context_and_merge_preserve_originals(sample, missing):
    context, prepared = base.prepared_sample(sample)
    answer = base.answer_for(prepared, context)
    retained = {k: v for k, v in answer.items() if k not in missing}
    scanned = read_sections(json.dumps(retained, ensure_ascii=False))
    assert set(scanned["missing"]) == set(missing)
    completion.validate_sections(retained, prepared, context, {})
    fmt = completion.subset_format(output.output_format(prepared, context, {}), missing)
    schema = fmt["json_schema"]["schema"]
    assert set(schema["properties"]) == set(schema["required"]) == set(missing)
    assert schema["additionalProperties"] is False
    reply = {key: answer[key] for key in missing}
    Draft202012Validator(schema).validate(reply)
    with pytest.raises(SchemaError):
        Draft202012Validator(schema).validate({**reply, "summary": "Replacement"})
    accepted = completion.parse_reply(json.dumps(reply), missing, prepared, context, {})
    wire, merged = completion.merge(retained, accepted.model_dump(), prepared, context, {}, new_review())
    assert wire == answer and [wire[k] for k in retained] == list(retained.values())
    assert len(merged.questions) == 6
    request = {"body": {"messages": prepared["messages"]}, "case_boundary": prepared["case_boundary"],
        "source_map": prepared["source_map"], "binding_map": {}, "input_artifact_ids": ["frozen-view"]}
    request_before = copy.deepcopy(request)
    supplement = completion.prepare_completion(prepared, request, retained, missing, "first-response")
    assert request == request_before
    assert supplement["messages"][1:-1] == request["body"]["messages"][1:]
    assert supplement["source_map"] == request["source_map"] and supplement["case_boundary"] == request["case_boundary"]
    prior = json.loads(supplement["messages"][-1]["content"])
    assert prior["role"] == "prior_analysis" and set(prior["retained_sections"]) <= set(retained)
    assert all(prior["retained_sections"][k] == retained[k] for k in prior["retained_sections"])
    assert "一次返回summary" not in supplement["messages"][0]["content"]
    assert supplement["section_completion"]["attempt"] == 1


def test_complete_values_missing_only_outer_close_do_not_need_a_reply(sample):
    context, prepared = base.prepared_sample(sample)
    answer = base.answer_for(prepared, context)
    answer["summary"] = '保留转义："引号"、反斜杠\\、\n和括号{}[]。'
    text = json.dumps(answer, ensure_ascii=False)
    scanned = read_sections(text[:-1])
    assert scanned["closing_delimiter_only"] and scanned["missing"] == []
    wire, _ = completion.merge(scanned["retained"], {}, prepared, context, {}, new_review())
    assert wire == answer and wire["followups"] == wire["findings"] == wire["conflicts"] == []


@pytest.mark.parametrize("text", ['{"summary":"x","summary":', '{"summary":"x","members":[{"alert_id":"A1","alert_id":',
    '{"summary":"x","members":[true false', '{"summary":"x","members":"bad\\x', '{}'])
def test_ambiguous_or_invalid_prefix_is_not_a_completion_target(text):
    with pytest.raises(AnalysisRejected):
        read_sections(text)


@pytest.mark.parametrize("fault", ["unknown_member", "duplicate_member", "invalid_type"])
def test_invalid_retained_structure_is_not_treated_as_missing(sample, fault):
    context, prepared = base.prepared_sample(sample)
    answer = base.answer_for(prepared, context)
    answer.pop("followups")
    if fault == "unknown_member":
        answer["members"][0]["alert_id"] = "unknown"
    elif fault == "duplicate_member":
        answer["members"].append(copy.deepcopy(answer["members"][0]))
    else:
        answer["questions"] = None
    with pytest.raises(AnalysisRejected):
        completion.validate_sections(answer, prepared, context, {})


@pytest.mark.parametrize("reply", [{}, {"followups": [], "summary": "overwrite"}, {"followups": [{"question_id": "unknown"}]}])
def test_unqualified_supplement_cannot_replace_retained_fields(sample, reply):
    context, prepared = base.prepared_sample(sample)
    with pytest.raises(AnalysisRejected):
        completion.parse_reply(json.dumps(reply), ["followups"], prepared, context, {})


def test_incomplete_c3_sections_reach_c6_without_invented_missing_fields(sample):
    context, prepared = base.prepared_sample(sample)
    answer = base.answer_for(prepared, context)
    answer.pop("followups")
    received = units.receive(json.dumps(answer), prepared, context, {}, "00000000-0000-0000-0000-000000000078")
    restored = received["analysis"]
    previous = {"analysis": restored, "validation": "structure_scope_checked", "source_map": prepared["source_map"],
        "basis": {"stage_delivery": units.summary(received, "00000000-0000-0000-0000-000000000079"),
                  "citation_review": received["quality"]}}
    result = followup.build("C6", context, prepared, {}, previous=previous,
        prior_id="00000000-0000-0000-0000-000000000077", extra={"comparison": {"state": "initial", "result_id": None}})
    assert result["ready"]
    row = next(row for row in result["followup_boundary"]["records"] if row["block"] == "C3")
    assert row["ref"]["role"] == "prior_analysis" and row["value"]["summary"] == restored["summary"]
    assert row["value"]["missing_sections"] == ["followups"] and "followups" not in row["value"]
    assert "C3仅完成已列出的部分" in result["messages"][1]["content"]
