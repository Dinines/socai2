"""Regression for the saved whitespace failure; no new model calls."""
import copy
import json
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.socai2.alert_output_adapter import Answer as AlertAnswer
from app.socai2.incident_output_adapter import BoundaryAnswer, decode
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import ModelPolicy
from jsonschema import Draft202012Validator
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/model-output-compatibility-20261116-01"
GATEWAY = SimpleNamespace(provider="chat_completions", schema_profile="vllm_grammar_v1")


def read(name):
    return json.loads((EVIDENCE / name).read_text())


def test_recorded_incident_request_matches_successful_real_replay_without_input_changes():
    original = read("original-request.json")
    before = copy.deepcopy(original)
    actual = prepare_request(GATEWAY, original)
    assert actual == read("candidate-request.json")
    assert original == before
    assert prepare_request(SimpleNamespace(provider="chat_completions"), original) is original
    assert {k: v for k, v in actual.items() if k != "response_format"} == {
        k: v for k, v in original.items() if k != "response_format"}
    raw = read("out/response.json")
    text = (EVIDENCE / "out/output.txt").read_text()
    assert raw["choices"][0]["message"]["content"] == text
    assert raw["choices"][0]["finish_reason"] == "stop" and text == text.rstrip()
    answer = decode(text)
    Draft202012Validator(original["response_format"]["json_schema"]["schema"]).validate(answer)
    BoundaryAnswer.model_validate(answer, strict=True)
    assert len(answer["diagnosis"]["summary"]) > 1 and len(answer["members"][0]["assessment"]) > 1


def test_incident_layout_limit_is_encoded_without_changing_schema_or_budget():
    body = {
        "model": "synthetic",
        "messages": [{"role": "user", "content": "合成材料"}],
        "max_tokens": 8192,
        "temperature": 0,
        "response_format": {"type": "json_schema", "json_schema": {"schema": {
            "type": "object", "properties": {"source": {"enum": ["S1"]},
                                             "analysis": {"type": "string", "pattern": r"\S"}},
            "required": ["source", "analysis"], "additionalProperties": False}}},
    }
    before = copy.deepcopy(body)
    expected = prepare_request(GATEWAY, body)
    actual = prepare_request(GATEWAY, body, max_structure_whitespace=8)
    assert actual == {**expected, "response_format": {"type": "structural_tag", "format": {
        "type": "json_schema", "json_schema": expected["response_format"]["json_schema"]["schema"],
        "max_whitespace_cnt": 8}}}
    assert body == before
    with pytest.raises(ValueError, match="model_structure_whitespace_not_supported"):
        prepare_request(SimpleNamespace(provider="chat_completions"), body, max_structure_whitespace=8)


def test_layout_limit_policy_accepts_legacy_profiles_and_validates_explicit_setting():
    config = ROOT / "deploy/local-investigation/investigation-policy-case-v1.toml"
    values = tomllib.loads(config.read_text())["model"]
    policy = ModelPolicy.parse(values)
    assert policy.incident_max_structure_whitespace == 8 and policy.output_tokens["I"] == 8192
    legacy = {key: value for key, value in values.items() if key != "incident_max_structure_whitespace"}
    assert ModelPolicy.parse(legacy).incident_max_structure_whitespace is None
    assert ModelPolicy.parse({**values, "incident_max_structure_whitespace": 0}).incident_max_structure_whitespace == 0
    for changes in ({"incident_max_structure_whitespace": -1}, {"incident_max_structure_whitespace": True},
                    {"schema_profile": "standard"}):
        with pytest.raises(ValueError, match="model_policy_incident_whitespace_invalid"):
            ModelPolicy.parse({**values, **changes})


@pytest.mark.parametrize("stage,model,limit", [("alert", AlertAnswer, 4000), ("incident", BoundaryAnswer, 3000)])
def test_nonblank_and_length_contract_still_rejects_invalid_prose(stage, model, limit):
    if stage == "incident":
        answer = decode((EVIDENCE / "out/output.txt").read_text())
        target, field = answer["diagnosis"], "summary"
    else:
        answer = {"verdict": "needs_review", "confidence": None, "rationale": "说明待核原因",
                  "evidence_ids": ["N1_S1"], "recommendations": []}
        target, field = answer, "rationale"
    for text in ('记录含有"引号"\n下一行仍是正常正文。', "说明待核原因"):
        target[field] = text
        model.model_validate(answer, strict=True)
    for text in ("", " \t\n", "字" * (limit + 1)):
        target[field] = text
        with pytest.raises(ValidationError):
            model.model_validate(answer, strict=True)


def test_only_schema_positions_change_and_scope_enums_patterns_and_literals_stay():
    text = {"type": "string", "minLength": 1, "maxLength": 30, "pattern": r"\S"}
    literal = {"type": "string", "minLength": 3, "maxLength": 9, "pattern": r"\S", "uniqueItems": True}
    schema = {"type": "object", "$defs": {"pattern": copy.deepcopy(text)},
        "properties": {"pattern": copy.deepcopy(text), "minLength": {"$ref": "#/$defs/pattern"},
            "maxLength": {"anyOf": [copy.deepcopy(text), {"type": "null"}]},
            "uniqueItems": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 30},
                "minItems": 1, "maxItems": 3, "uniqueItems": True},
            "member": {"type": "string", "enum": ["A1"], "minLength": 2},
            "id": {"type": "string", "pattern": "^F[1-9][0-9]*$", "maxLength": 20},
            "constant": {"const": literal}, "enumerated": {"enum": [literal]}},
        "required": ["pattern", "minLength", "maxLength", "uniqueItems", "member", "id"],
        "additionalProperties": False, "default": literal, "examples": [literal]}
    body = {"response_format": {"json_schema": {"schema": schema}}, "messages": []}
    before = copy.deepcopy(body)
    result = prepare_request(GATEWAY, body)["response_format"]["json_schema"]["schema"]
    assert body == before and result["properties"].keys() == schema["properties"].keys()
    assert result["$defs"]["pattern"] == result["properties"]["pattern"] == {"type": "string"}
    assert result["properties"]["minLength"] == {"$ref": "#/$defs/pattern"}
    assert result["properties"]["maxLength"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert result["properties"]["uniqueItems"] == {
        "type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3}
    for key in ("member", "id", "constant", "enumerated"):
        assert result["properties"][key] == schema["properties"][key]
    for key in ("required", "additionalProperties", "default", "examples"):
        assert result[key] == schema[key]

