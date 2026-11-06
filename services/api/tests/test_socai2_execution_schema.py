"""C3 binding-aware wire constraints; no model, DB, or response repair calls."""
import copy
import json
from types import SimpleNamespace

import pytest
from app.socai2 import baseline_analysis_contract as contract
from app.socai2.baseline_context import Context
from app.socai2.baseline_execution_schema import (
    compact_definitions,
    compact_execution_wire,
    execution_format,
)
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format
from jsonschema import Draft202012Validator
from test_socai2_followup_scope import frozen


def fixture():
    packet, value = frozen()
    context = Context.model_validate(packet["context"])
    ids = list(context.alerts)
    host = next(k for k in context.scope.object_keys if json.loads(k)[0] == "host")
    extra = next(k for k in context.scope.object_keys if json.loads(k)[0] != "host")
    bindings = {name: {"alert_ids": ids, "objects": [{"object_key": host}]} for name in ("B1", "B2")}
    bindings["B3"] = {"alert_ids": ids[:1], "objects": []}
    for item in value["followups"]:
        item.update(mode="human", binding_id=None, priority="supporting")
    query = value["followups"][0]
    query.update(mode="query", binding_id="B1", alert_ids=ids, object_keys=[host], source_ids=[])
    fmt = response_format(contract.ExecutionAnalysis, packet["source_map"], members=context.alerts,
        questions=[q.id for q in context.questions], objects=context.scope.object_keys, bindings=bindings)
    return packet, context, value, bindings, fmt, host, extra


def expanded(schema):
    def visit(node):
        if isinstance(node, dict):
            if "$ref" in node:
                assert set(node) == {"$ref"}
                return visit(schema["$defs"][node["$ref"].removeprefix("#/$defs/")])
            return {k: visit(v) for k, v in node.items() if k != "$defs"}
        return [visit(v) for v in node] if isinstance(node, list) else node
    return visit(schema)


@pytest.mark.parametrize("protocol", ["chat_completions", "deepseek_responses"])
@pytest.mark.parametrize("profile", ["standard", "vllm_grammar_v1"])
def test_dynamic_scope_matrix_and_equivalent_provider_aliases(protocol, profile):
    packet, context, value, bindings, fmt, host, extra = fixture()
    before = copy.deepcopy(fmt)
    dynamic = execution_format(fmt, bindings)
    assert fmt == before and len(dynamic["json_schema"]["schema"]["$defs"]["ExecutionFollowup"]["anyOf"]) == 3
    body = {"model": "fixture", "messages": [{"role": "user", "content": "unmodified case facts"}],
        "max_tokens": 3000, "temperature": 0, "response_format": dynamic}
    wire = prepare_request(SimpleNamespace(provider=protocol, schema_profile=profile), body)
    original = copy.deepcopy(wire)
    compact = compact_execution_wire(wire)
    old_schema = (wire["text"]["format"] if "text" in wire else wire["response_format"]["json_schema"])["schema"]
    schema = (compact["text"]["format"] if "text" in compact else compact["response_format"]["json_schema"])["schema"]
    assert wire == original and expanded(old_schema) == expanded(schema)
    assert len(json.dumps(schema)) < len(json.dumps(old_schema))
    assert {k: v for k, v in compact.items() if k not in {"text", "response_format"}} == {
        k: v for k, v in wire.items() if k not in {"text", "response_format"}}
    validator = Draft202012Validator(schema)
    validator.check_schema(schema)
    validator.validate(value)
    contract.parse(json.dumps(value), packet["source_map"], context, packet["coverage"], bindings=bindings)
    for alias in ("B1", "B2"):
        positive = copy.deepcopy(value)
        positive["followups"][0].update(binding_id=alias, object_keys=[])
        validator.validate(positive)
    nongroup = copy.deepcopy(value)
    nongroup["followups"][0].update(binding_id="B3", alert_ids=list(context.alerts)[:1], object_keys=[])
    validator.validate(nongroup)
    human = copy.deepcopy(value)
    human["followups"][0].update(mode="human", binding_id=None, object_keys=[extra])
    validator.validate(human)
    contract.parse(json.dumps(human), packet["source_map"], context, packet["coverage"], bindings=bindings)
    changes = [{"object_keys": [host, extra]}, {"binding_id": "unoffered"}, {"binding_id": None},
        {"mode": "human"}, {"alert_ids": list(context.alerts)[:1]}, {"binding_id": "B3"},
        {"priority": "invented"}, {"objective": "x" * 1201}]
    for change in changes:
        negative = copy.deepcopy(value)
        negative["followups"][0].update(change)
        assert not validator.is_valid(negative), change
        with pytest.raises(contract.AnalysisRejected):
            contract.parse(json.dumps(negative), packet["source_map"], context, packet["coverage"], bindings=bindings)
    duplicate = copy.deepcopy(value)
    duplicate["followups"][0]["alert_ids"] = [next(iter(context.alerts))] * len(context.alerts)
    assert validator.is_valid(duplicate) is (profile == "vllm_grammar_v1")
    # Grammar compatibility still relies on the unchanged local duplicate gate.
    with pytest.raises(contract.AnalysisRejected):
        contract.parse(json.dumps(duplicate), packet["source_map"], context, packet["coverage"], bindings=bindings)


def test_no_bindings_removes_query_only_and_preserves_nonquery_objects():
    _, _, value, _, fmt, _, extra = fixture()
    schema = execution_format(fmt, {})["json_schema"]["schema"]
    assert "anyOf" not in schema["$defs"]["ExecutionFollowup"]
    validator = Draft202012Validator(schema)
    assert not validator.is_valid(value)
    value["followups"][0].update(mode="human", binding_id=None, object_keys=[extra])
    validator.validate(value)


@pytest.mark.parametrize("kind", ["external", "missing", "cycle", "nested", "subpath"])
def test_aliases_reject_external_missing_recursive_or_ambiguous_refs(kind):
    schema = {"$defs": {"a": {"type": "string"}}, "$ref": "#/$defs/a"}
    if kind == "external":
        schema["$ref"] = "https://invalid.example/schema.json#/$defs/a"
    elif kind == "missing":
        schema["$ref"] = "#/$defs/missing"
    elif kind == "cycle":
        schema["$defs"]["a"] = {"$ref": "#/$defs/a"}
    elif kind == "nested":
        schema["$defs"]["a"]["$defs"] = {}
    else:
        schema["$ref"] = "#/$defs/a/properties/x"
    original = copy.deepcopy(schema)
    with pytest.raises(ValueError, match="execution_schema_"):
        compact_definitions(schema)
    assert schema == original


def test_aliases_preserve_field_names_literal_refs_and_handle_name_collisions():
    schema = {"$defs": {"a": {"type": "string", "enum": ["#/$defs/z", "a"]},
        "z": {"type": "integer", "minimum": 4}}, "type": "object",
        "properties": {"a": {"$ref": "#/$defs/z"}, "z": {"$ref": "#/$defs/a"}},
        "required": ["a", "z"], "additionalProperties": False}
    output = compact_definitions(schema)
    assert expanded(output) == expanded(schema) and output["properties"].keys() == schema["properties"].keys()
    validator = Draft202012Validator(output)
    validator.validate({"a": 4, "z": "#/$defs/z"})
    assert not validator.is_valid({"a": 3, "z": "a"})


def test_single_use_chain_is_inlined_without_copying_shared_refs_or_losing_sibling_constraints():
    schema = {"$defs": {"Parent": {"type": "array", "items": {"$ref": "#/$defs/Item"}},
        "Item": {"type": "string", "enum": ["x", "y"]}, "Shared": {"type": "boolean"},
        "Positive": {"type": "integer", "minimum": 1}}, "type": "object", "properties": {
            "items": {"$ref": "#/$defs/Parent"}, "a": {"$ref": "#/$defs/Shared"},
            "b": {"$ref": "#/$defs/Shared"}, "bounded": {"$ref": "#/$defs/Positive", "maximum": 4}}}
    output = compact_definitions(schema)
    props = output["properties"]
    assert props["items"] == {"type": "array", "items": schema["$defs"]["Item"]}
    assert props["a"] == props["b"] and "$ref" in props["a"]
    assert props["bounded"]["maximum"] == 4 and "$ref" in props["bounded"]
    assert len(output["$defs"]) == 2
    for row in ({"items": ["x"], "bounded": 3}, {"items": ["z"]}, {"bounded": 0}, {"bounded": 5}):
        assert Draft202012Validator(output).is_valid(row) == Draft202012Validator(schema).is_valid(row)
