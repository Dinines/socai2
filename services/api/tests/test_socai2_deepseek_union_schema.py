"""The m3 fix changes representation only, and is applied before persistence."""
from copy import deepcopy
from types import SimpleNamespace

import jsonschema
import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import baseline_deep_contract as deep
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.model_protocol import (
    DEEPSEEK_PROTOCOL,
    deepseek_schema,
    prepare_request,
)
from app.socai2.structured_output import response_format


class DeepSeekWireGateway:
    """Real protocol-shaped request/response, explicitly substituted model."""
    provider, model, schema_profile = DEEPSEEK_PROTOCOL, "deepseek-flash", "standard"

    def __init__(self, delegate):
        self.delegate, self.requests, self.responses = delegate, [], []

    async def configure(self, *args):
        return await self.delegate.configure(*args)

    async def measure(self, body, stage):
        from socai2_test_model_view import synthetic_measure
        return await synthetic_measure(body, stage)

    async def complete(self, body, timeout):
        self.requests.append(deepcopy(body))
        assert "messages" not in body and body["text"]["format"]["strict"] is True
        fmt = {k: v for k, v in body["text"]["format"].items() if k != "type"}
        chat = {"model": body["model"], "messages": body["input"], "max_tokens": body["max_output_tokens"],
            "temperature": body["temperature"], "response_format": {"type": "json_schema", "json_schema": fmt}}
        result = await self.delegate.complete(chat, timeout)
        usage = result["usage"]
        response = {"object": "response", "id": result["id"], "status": "completed", "error": None,
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": result["choices"][0]["message"]["content"]}]}],
            "usage": {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"]}}
        self.responses.append(deepcopy(response))
        return response


def branches(value):
    if isinstance(value, dict):
        yield from value.get("anyOf", [])
        for child in value.values():
            yield from branches(child)
    elif isinstance(value, list):
        for child in value:
            yield from branches(child)


@pytest.mark.parametrize("model", [alert.Answer, incident.Answer, analysis.Analysis, analysis.ExecutionAnalysis, deep.Decision, delivery.Delivery])
def test_each_contract_exposes_union_types_without_changing_definitions_or_inputs(model):
    schema = response_format(model, ["N1_S1"], members=["00000000-0000-0000-0000-000000000001"],
        questions=["Q1"], objects=["host:synthetic"], bindings=["B1"])["json_schema"]["schema"]
    before = deepcopy(schema)
    output = deepseek_schema(schema)
    assert schema == before
    jsonschema.Draft202012Validator.check_schema(output)
    assert all(isinstance(b.get("type"), str) and "$ref" not in b for b in branches(output))
    assert output["$defs"]["SourceId"] == schema["$defs"]["SourceId"]
    assert output["required"] == schema["required"] and output["additionalProperties"] is False


def test_m3_alert_object_and_null_keep_identical_acceptance_boundaries():
    schema = response_format(alert.Answer, ["N1_S1"])["json_schema"]["schema"]
    output = deepseek_schema(schema)
    left, right = [jsonschema.Draft202012Validator({**s["properties"]["decision_basis"], "$defs": s["$defs"]})
                   for s in (schema, output)]
    valid = {"kind": "authorized_or_expected_behavior", "claim": "Schema test only", "source_ids": ["N1_S1"]}
    cases = [None, valid, False, "null", [], {}, {**valid, "extra": 1}, {**valid, "source_ids": ["N1_S2"]},
        {**valid, "source_ids": []}, {**valid, "claim": "x" * 4001}, {**valid, "kind": "unknown"}]
    cases += [{k: v for k, v in valid.items() if k != missing} for missing in valid]
    assert all(left.is_valid(v) == right.is_valid(v) for v in cases)
    assert output["properties"]["decision_basis"]["anyOf"][0] == schema["$defs"]["DecisionBasis"]
    assert output["properties"]["decision_basis"]["anyOf"][1] == {"type": "null"}


@pytest.mark.parametrize("ref,definitions,sibling,reason", [
    ("https://example.invalid/schema", {}, False, "not_local"),
    ("#/$defs/Missing", {}, False, "missing"),
    ("#/$defs/Loop", {"Loop": {"anyOf": [{"$ref": "#/$defs/Loop"}, {"type": "null"}]}}, False, "cycle"),
    ("#/$defs/Defined", {"Defined": {"type": "string"}}, True, "siblings_unsupported")])
def test_unresolvable_union_references_fail_without_silently_dropping_constraints(ref, definitions, sibling, reason):
    branch = {"$ref": ref, **({"maxLength": 5} if sibling else {})}
    with pytest.raises(ValueError, match=reason):
        deepseek_schema({"$defs": definitions, "anyOf": [branch, {"type": "null"}]})


def test_only_deepseek_wire_changes_and_ordinary_refs_stay_compact():
    body = {"model": "synthetic", "messages": [{"role": "user", "content": "schema test"}],
        "max_tokens": 512, "temperature": 0, "response_format": response_format(alert.Answer, ["N1_S1"])}
    before = deepcopy(body)
    assert prepare_request(SimpleNamespace(provider="chat_completions"), body) is body
    wire = prepare_request(SimpleNamespace(provider=DEEPSEEK_PROTOCOL), body)
    schema = wire["text"]["format"]["schema"]
    assert body == before and wire["input"] == body["messages"]
    assert schema["properties"]["rationale"] == body["response_format"]["json_schema"]["schema"]["properties"]["rationale"]
    assert "$ref" in schema["properties"]["rationale"]
