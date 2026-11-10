"""Role-aware generation and diagnostics, including actual preserved failures."""
import copy
import json
from pathlib import Path

import pytest
import test_socai2_case_followup_boundary as followup
import test_socai2_case_model_boundary as base
from app.socai2 import case_followup_input, case_followup_output, case_output_adapter
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from jsonschema import Draft202012Validator

configured, sample = base.configured, base.sample
ROOT = Path(__file__).resolve().parents[3]


def model_case(sample, stage):
    context, prepared = base.prepared_sample(sample)
    if stage == "C3":
        answer = base.answer_for(prepared, context)
        return context, prepared, answer, answer, (
            lambda: case_output_adapter.output_format(prepared, context, {})), (
            lambda content: case_output_adapter.parse(content, prepared, context, {})), (
            lambda: case_output_adapter.CaseReview(prepared, context, {}))
    comparison = {"state": "initial", "result_id": None}
    prepared = case_followup_input.build("C6", context, prepared, {})
    answer = followup.final_answer(prepared, context, comparison)
    return context, prepared, answer, answer["analysis"], (
        lambda: case_followup_output.final_format(prepared, context, comparison)), (
        lambda content: case_followup_output.parse_final(content, prepared, context, comparison)), (
        lambda: case_followup_output.FinalReview(prepared, context, comparison))


def finding(prepared):
    aid, alias = next(iter(prepared["case_boundary"]["member_aliases"].items()))
    sid = next(sid for sid, s in prepared["source_map"].items()
               if s["ref"]["role"] == "observation" and aid in s["alert_ids"])
    row = {"id": "F1", "state": "observed", "statement": "Synthetic observation.",
           "alert_ids": [alias], "support_ids": [sid], "counter_ids": [],
           "alternatives": [], "limitations": []}
    return aid, sid, row


@pytest.mark.parametrize("stage", ["C3", "C6"])
@pytest.mark.parametrize("role", ["source_label", "prior_analysis", "human_statement", "execution_receipt"])
def test_mixed_observation_roles_are_constrained_and_precisely_diagnosed(sample, stage, role):
    _, prepared, answer, analysis, format_, parse, review = model_case(sample, stage)
    aid, sid, row = finding(prepared)
    contextual = copy.deepcopy(prepared["source_map"][sid])
    contextual["ref"].update(role=role, source_path="$.synthetic_context")
    prepared["source_map"]["ContextSource"] = contextual
    analysis["findings"] = [row]
    validator = Draft202012Validator(format_()["json_schema"]["schema"])
    validator.validate(answer)
    parse(json.dumps(answer))
    row["support_ids"].append("ContextSource")
    original = copy.deepcopy(answer)
    assert not validator.is_valid(answer)
    with pytest.raises(AnalysisRejected, match="non_observation_promoted_to_observed"):
        parse(json.dumps(answer))
    feedback = review().feedback(json.dumps(answer))
    errors = [e for e in feedback["errors"] if e.get("code") == "non_observation_promoted_to_observed"]
    assert len(errors) == 1
    assert errors[0]["path"] == (["analysis"] if stage == "C6" else []) + ["findings", 0, "support_ids", 1]
    assert errors[0]["actual_role"] == role and errors[0]["source_id"] == "ContextSource"
    assert sid in feedback["observed_support_ids"] and "ContextSource" not in feedback["observed_support_ids"]
    assert answer == original and contextual["alert_ids"] == [aid]
    # Inference/unresolved are explicit choices, not an automatic repair.
    row["state"] = "inferred"
    validator.validate(answer)
    parse(json.dumps(answer))
    row.update(state="unresolved", support_ids=[], limitations=["Synthetic missing evidence."])
    validator.validate(answer)
    parse(json.dumps(answer))
    row["limitations"] = []
    assert not validator.is_valid(answer)


@pytest.mark.parametrize("stage", ["C3", "C6"])
def test_missing_observation_and_query_binding_do_not_offer_observed(sample, stage):
    _, prepared, _, _, format_, _, _ = model_case(sample, stage)
    _, sid, row = finding(prepared)
    source = prepared["source_map"][sid]
    source["membership_basis"] = "query_binding_only"
    prepared["source_map"] = {sid: source}
    schema = format_()["json_schema"]["schema"]
    validator = Draft202012Validator({"$ref": "#/$defs/Finding", "$defs": schema["$defs"]})
    assert not validator.is_valid(row)
    row["state"] = "inferred"
    validator.validate(row)
    row["support_ids"] = []
    assert not validator.is_valid(row)
    prepared["source_map"] = {}
    schema = format_()["json_schema"]["schema"]
    validator = Draft202012Validator({"$ref": "#/$defs/Finding", "$defs": schema["$defs"]})
    assert not validator.is_valid(row)
    row.update(state="unresolved", limitations=["No available evidence."])
    validator.validate(row)


@pytest.mark.parametrize("stage", ["C3", "C6"])
def test_time_context_compatibility_and_member_observation_coverage(sample, stage):
    context, prepared, answer, analysis, _, parse, review = model_case(sample, stage)
    aid, sid, row = finding(prepared)
    temporal = copy.deepcopy(prepared["source_map"][sid])
    temporal["ref"].update(type="artifact", role="source_label", source_path=f"$.alerts.{aid}.alert.event_time")
    prepared["source_map"]["EventTime"] = temporal
    row["support_ids"].append("EventTime")
    analysis["findings"] = [row]
    parse(json.dumps(answer))
    assert review().feedback(json.dumps(answer)) is None
    other = next(a for a in context.alerts if a != aid)
    temporal.update(alert_ids=[other])
    temporal["ref"]["source_path"] = f"$.alerts.{other}.alert.event_time"
    row["alert_ids"].append(prepared["case_boundary"]["member_aliases"][other])
    with pytest.raises(AnalysisRejected, match="member_source_coverage_missing"):
        parse(json.dumps(answer))
    errors = review().feedback(json.dumps(answer))["errors"]
    assert any(e.get("code") == "observed_member_source_coverage_missing"
               and e["uncovered_members"] == [row["alert_ids"][1]] for e in errors)
    assert not any(e.get("code") == "non_observation_promoted_to_observed" for e in errors)


@pytest.mark.parametrize("stage", ["C3", "C6"])
def test_query_only_and_overlapping_support_receive_no_automatic_rewrite(sample, stage):
    _, prepared, answer, analysis, _, parse, review = model_case(sample, stage)
    _, sid, row = finding(prepared)
    analysis["findings"] = [row]
    prepared["source_map"][sid]["membership_basis"] = "query_binding_only"
    with pytest.raises(AnalysisRejected, match="direct_alert_membership_not_proven"):
        parse(json.dumps(answer))
    assert any(e.get("code") == "direct_alert_membership_not_proven"
               for e in review().feedback(json.dumps(answer))["errors"])
    prepared["source_map"][sid].pop("membership_basis")
    row["counter_ids"] = [sid]
    original = copy.deepcopy(answer)
    with pytest.raises(AnalysisRejected, match="same_source_as_support_and_counterevidence"):
        parse(json.dumps(answer))
    assert any(e.get("code") == "same_source_as_support_and_counterevidence"
               for e in review().feedback(json.dumps(answer))["errors"])
    assert answer == original


@pytest.mark.parametrize("seq", [11, 19, 20])
def test_actual_failed_reply_keeps_receiver_rejection_and_gains_role_feedback(configured, seq):
    data = json.loads((ROOT / "docs/operations/evidence/case-scope-recovery-20261110-01/real-model-03/export/database.json").read_text())
    artifacts = {a["id"]: a for a in data["artifacts"]}
    step = next(s for s in data["run_steps"] if s["seq"] == seq)
    prepared = copy.deepcopy(artifacts[step["input_artifact_id"]]["content_json"]["payload"])
    prepared["coverage"] = next(a["content_json"]["coverage"] for a in artifacts.values()
        if a["schema_version"] == "socai2.case-model-input.v1")
    context = Context.model_validate(next(a["content_json"] for a in artifacts.values()
        if a["schema_version"] == "socai2.baseline-context.v1"))
    content = next(a["content_json"]["payload"]["raw"]["choices"][0]["message"]["content"] for a in artifacts.values()
        if a["step_id"] == step["id"] and a["kind"] == "model_response")
    before = copy.deepcopy(prepared)
    if step["stage_code"] == "C3":
        fmt = case_output_adapter.output_format(prepared, context, prepared["binding_map"])
        review = case_output_adapter.CaseReview(prepared, context, prepared["binding_map"])
        parse = lambda: case_output_adapter.parse(content, prepared, context, prepared["binding_map"])
    else:
        comparison = {"state": "initial", "result_id": None}
        fmt = case_followup_output.final_format(prepared, context, comparison)
        review = case_followup_output.FinalReview(prepared, context, comparison)
        parse = lambda: case_followup_output.parse_final(content, prepared, context, comparison)
    assert not Draft202012Validator(fmt["json_schema"]["schema"]).is_valid(json.loads(content))
    with pytest.raises(AnalysisRejected, match="non_observation_promoted_to_observed"):
        parse()
    feedback = review.feedback(content)
    assert any(e.get("code") == "non_observation_promoted_to_observed" for e in feedback["errors"])
    assert prepared == before
