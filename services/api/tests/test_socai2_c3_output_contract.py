"""C3's frozen count policy controls one complete reply, without changing C6."""
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import test_socai2_case_model_boundary as base
from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as final
from app.socai2 import case_model_boundary as boundary
from app.socai2 import case_output_adapter as c3
from app.socai2 import runtime_policy
from app.socai2.baseline_analysis_contract import Analysis, AnalysisRejected
from app.socai2.citation_quality import new_review
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError
from test_socai2_case_followup_boundary import final_answer

configured, sample = base.configured, base.sample
SECTIONS = {"summary", "members", "findings", "questions", "domains", "conflicts", "followups"}


def with_findings(prepared, context, count):
    answer = base.answer_for(prepared, context)
    for i in range(count):
        member = answer["members"][i % len(answer["members"])]
        answer["findings"].append({"id": f"F{i + 1}", "state": "inferred",
            "statement": f"  合成核心发现{i + 1}：原文保留，未作真实质量判定。\n",
            "alert_ids": [member["alert_id"]], "support_ids": member["evidence_ids"],
            "counter_ids": [], "alternatives": [], "limitations": ["Synthetic only."]})
    return answer


@pytest.mark.parametrize("count", [0, 5])
def test_seven_sections_zero_or_five_findings_and_program_coverage(sample, count):
    context, prepared = base.prepared_sample(sample)
    answer = with_findings(prepared, context, count)
    schema = c3.output_format(prepared, context, {})["json_schema"]["schema"]
    assert set(schema["required"]) == SECTIONS == set(answer)
    assert schema["properties"]["findings"]["maxItems"] == 5
    Draft202012Validator(schema).validate(answer)
    content = json.dumps(answer, ensure_ascii=False)
    result = c3.parse(content, prepared, context, {}, citation_review=new_review())
    assert len(result.findings) == count and len(result.members) == len(context.alerts)
    assert len(answer["questions"]) == 5 and len(result.questions) == 6
    assert result.questions[-1].id == "coverage"
    assert len(result.domains) == 4 and result.followups == []
    assert [f.statement for f in result.findings] == [f["statement"] for f in answer["findings"]]
    prompt = prepared["messages"][0]["content"]
    assert "最多5个核心findings" in prompt and "一次返回summary、members、findings、questions、domains、conflicts、followups七部分" in prompt
    assert "1800" not in prompt and "最多3个" not in prompt


def test_six_findings_are_a_structural_error_and_cannot_be_trimmed_by_partial(sample):
    context, prepared = base.prepared_sample(sample)
    answer = with_findings(prepared, context, 6)
    original = copy.deepcopy(answer)
    content, review = json.dumps(answer), new_review()
    with pytest.raises(SchemaError):
        Draft202012Validator(c3.output_format(prepared, context, {})["json_schema"]["schema"]).validate(answer)
    with pytest.raises(AnalysisRejected, match="^case_finding_limit_exceeded$"):
        c3.parse(content, prepared, context, {}, citation_review=review)
    with pytest.raises(AnalysisRejected, match="^case_finding_limit_exceeded$"):
        c3.CaseReview(prepared, context, {}).partial(content)
    assert answer == original and review["issues"] == []


def test_one_config_value_drives_prompt_schema_and_frozen_receive(sample, configured, monkeypatch):
    data = configured.case_io.config
    data["c3_output"]["max_findings"] = 4
    raw = json.dumps(data, ensure_ascii=False).encode()
    profile = replace(configured.case_io, raw=raw, sha256=hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(boundary, "active_policy", lambda: replace(configured, case_io=profile))
    sample["context"]["case_input_profile"] = profile.identity
    context, prepared = base.prepared_sample(sample)
    assert prepared["case_boundary"]["c3_output"]["max_findings"] == 4
    assert "最多4个核心findings" in prepared["messages"][0]["content"]
    assert c3.output_format(prepared, context, {})["json_schema"]["schema"]["properties"]["findings"]["maxItems"] == 4
    assert len(c3.parse(json.dumps(with_findings(prepared, context, 4)), prepared, context, {}).findings) == 4
    with pytest.raises(AnalysisRejected, match="case_finding_limit_exceeded"):
        c3.parse(json.dumps(with_findings(prepared, context, 5)), prepared, context, {})


def test_historical_frozen_boundary_and_c6_keep_their_shared_capacity(sample):
    context, prepared = base.prepared_sample(sample)
    legacy = copy.deepcopy(prepared)
    legacy["case_boundary"].pop("c3_output")
    answer = with_findings(legacy, context, 6)
    Draft202012Validator(c3.output_format(legacy, context, {})["json_schema"]["schema"]).validate(answer)
    assert len(c3.parse(json.dumps(answer), legacy, context, {}).findings) == 6
    assert Analysis.model_json_schema()["properties"]["findings"]["maxItems"] == 24
    comparison = {"state": "initial", "result_id": None}
    prepared = inputs.build("C6", context, prepared, {}, extra={"comparison": comparison})
    answer = final_answer(prepared, context, comparison)
    answer["analysis"] = with_findings(prepared, context, 6)
    Draft202012Validator(final.final_format(prepared, context, comparison)["json_schema"]["schema"]).validate(answer)
    assert len(final.parse_final(json.dumps(answer), prepared, context, comparison).analysis.findings) == 6


@pytest.mark.parametrize("policy", [{"version": "unknown", "max_findings": 5},
    {"version": "socai2.c3-output.v1"}, {"version": "socai2.c3-output.v1", "max_findings": True}])
def test_invalid_new_frozen_policy_does_not_fall_back(sample, policy):
    context, prepared = base.prepared_sample(sample)
    prepared["case_boundary"]["c3_output"] = policy
    with pytest.raises(AnalysisRejected, match="case_finding_limit_unavailable"):
        c3.output_format(prepared, context, {})
    with pytest.raises(AnalysisRejected, match="case_finding_limit_unavailable"):
        c3.parse(json.dumps(with_findings(prepared, context, 0)), prepared, context, {})


@pytest.mark.parametrize("fault", ["boolean_count", "missing_placeholder"])
def test_invalid_source_configuration_fails_loading(configured, monkeypatch, fault):
    data = configured.case_io.config
    if fault == "boolean_count":
        data["c3_output"]["max_findings"] = True
    else:
        data["c3_output"]["instruction"] = data["c3_output"]["instruction"].replace("{max_findings}", "5")
    original = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda path: json.dumps(data).encode()
        if path.name == "case-input-v1.json" else original(path))
    with pytest.raises(ValueError, match="case_c3_output_policy_invalid"):
        runtime_policy.load_case_profile({"profile": "case-input-v1.json"})


def test_expanded_case_budget_preserves_call_and_tool_limits(configured):
    prior = runtime_policy.load_policy(base.ROOT / "deploy/local-investigation/investigation-policy-ai-v1.toml")
    assert configured.model.output_tokens["C3"] == 16384
    for name in ("case", "alert_basic", "incident_diagnosis"):
        current, old = getattr(configured, name), getattr(prior, name)
        assert current.max_model_calls == old.max_model_calls
        assert current.max_tool_calls == old.max_tool_calls
        assert current.max_rows_per_query == old.max_rows_per_query
        assert current.deadline_seconds == old.deadline_seconds
        assert current.max_total_tokens > old.max_total_tokens
    assert configured.model.final_reserved_calls == prior.model.final_reserved_calls
    assert configured.model.final_reserved_input_tokens > prior.model.final_reserved_input_tokens
