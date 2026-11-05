"""Provider schemas enforce shape; local parsers still enforce ownership/truth boundaries."""
import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import jsonschema
import pytest
from app.services.llm_resolver import LlmConfig
from app.socai2 import alert_basic_contract as a
from app.socai2 import baseline_analysis_contract as c
from app.socai2 import baseline_deep_contract as d
from app.socai2 import baseline_delivery_contract as f
from app.socai2 import incident_diagnosis_contract as i
from app.socai2.baseline_analysis_model import TenantChatGateway
from app.socai2.baseline_reasoning import fit_final_request
from app.socai2.baseline_store import encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format


@pytest.mark.parametrize("model", [a.Answer, i.Answer, c.Analysis, d.Decision, f.Delivery])
def test_contract_schemas_valid_and_do_not_mutate_contract(model):
    before = deepcopy(model.model_json_schema())
    fmt = response_format(model, ["S1", "S2"], members=[uuid4(), uuid4()],
        questions=["detection_facts"], objects=["host:x"], bindings=["B1"])
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    jsonschema.Draft202012Validator.check_schema(fmt["json_schema"]["schema"])
    assert before == model.model_json_schema()


def test_a_provider_rejects_unknown_source_and_wrong_arrays_but_not_truth():
    schema = response_format(a.Answer, ["S1"])["json_schema"]["schema"]
    value = {"verdict": "needs_review", "confidence": None, "rationale": "Unknown", "explanation": "Pending",
        "evidence_ids": ["S1"], "recommendations": [], "limitations": [], "decision_basis": None}
    jsonschema.validate(value, schema)
    for change in ({"evidence_ids": ["G1"]}, {"limitations": None}, {"limitations": "unknown"}, {"verdict": "closed"}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**value, **change}, schema)
    # This would still need semantic review. Schema success is not truth proof.
    jsonschema.validate({**value, "verdict": "benign", "rationale": "A label claims safety"}, schema)


def test_prose_alias_constraint_matches_parser_and_preserves_literal_received_values():
    data = {"items": [{"role": "observation", "field": "$.ocsf_json.device.hostname", "value": "S1"},
        {"role": "prior_analysis", "value": "Earlier analysis cited S20"}]}
    sources = ["S1", "S2", "S20"]
    forbidden = [sid for sid in sources if a.source_alias_in_prose([sid], [sid], data)]
    fmt = response_format(a.Answer, sources, forbidden_prose=forbidden)
    value = {"verdict": "needs_review", "confidence": None, "rationale": "Host S1 needs review",
        "explanation": "TCP port 443 does not establish HTTPS", "evidence_ids": ["S2"],
        "recommendations": [{"reason": "Check host", "source_ids": ["S20"]}], "limitations": [], "decision_basis": None}
    jsonschema.validate(value, fmt["json_schema"]["schema"])
    for text in ("S2", "见S2记录", "(S2-S20)", "line\nS20", "S20。"):
        assert a.source_alias_in_prose([text], sources, data)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**value, "rationale": text}, fmt["json_schema"]["schema"])
    jsonschema.validate({**value, "rationale": "XS2 or S20_host are literal strings"}, fmt["json_schema"]["schema"])


def test_conflict_requires_two_distinct_existing_findings_in_output_schema():
    schema = response_format(c.Analysis, ["S1"])["json_schema"]["schema"]
    conflict = {"id": "C1", "finding_ids": ["F1", "F2"], "state": "unresolved",
        "explanation": "Conflicting observations", "evidence_ids": ["S1"]}
    validator = jsonschema.Draft202012Validator({"$ref": "#/$defs/Conflict", "$defs": schema["$defs"]})
    validator.validate(conflict)
    for ids in ([], ["F1"], ["F1", "F1"]):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({**conflict, "finding_ids": ids})


def test_c_required_members_questions_and_direct_ids_are_constrained():
    aids = [str(uuid4()), str(uuid4())]
    schema = response_format(c.Analysis, ["S1"], members=aids,
        questions=["detection_facts"])["json_schema"]["schema"]
    assert schema["properties"]["members"]["minItems"] == 2
    assert schema["properties"]["members"]["maxItems"] == 2
    assert schema["properties"]["questions"]["minItems"] == 6
    assert schema["properties"]["domains"]["minItems"] == 4
    assert schema["$defs"]["AlertId"]["enum"] == sorted(aids)
    assert schema["$defs"]["Answer"]["properties"]["id"] == {"$ref": "#/$defs/QuestionId"}


def test_deep_only_offered_query_and_question_with_no_empty_enum():
    value = {"question_id": "authorization", "action": "query", "binding_id": "B1", "reason": "Check", "answer": None}
    schema = response_format(d.Decision, [], questions=["authorization"], bindings=["B1"])["json_schema"]["schema"]
    jsonschema.validate(value, schema)
    for change in ({"binding_id": "B2"}, {"question_id": "other"}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**value, **change}, schema)
    empty = response_format(d.Decision, [], questions=["authorization"])["json_schema"]["schema"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, empty)


def test_gateway_transmits_recorded_schema_and_sampling_without_fallback():
    body = {"model": "synthetic", "messages": [{"role": "user", "content": "synthetic"}],
        "max_tokens": 3000, "temperature": 0, "response_format": response_format(a.Answer, ["S1"])}
    original, seen = deepcopy(body), []
    async def rejecting_provider(**kwargs):
        seen.append(kwargs)
        raise ValueError("synthetic provider rejected schema")
    gateway = TenantChatGateway()
    gateway.config = LlmConfig(True, "https://model.invalid/v1", "synthetic", "fixture-not-a-key", "tenant", "")
    with patch("app.socai2.baseline_analysis_model.safe_chat_completions_request", rejecting_provider), \
            pytest.raises(ValueError, match="synthetic provider rejected schema"):
        asyncio.run(gateway.complete(body, 5))
    assert len(seen) == 1
    assert {key: seen[0][key] for key in body} == original
    assert body == original


@pytest.mark.parametrize("protocol", ["chat_completions", "deepseek_responses"])
def test_final_budget_trims_optional_values_and_updates_exact_sources(protocol):
    items = [{"id": f"S{x}", "value": "retained source " * 50} for x in range(1, 9)]
    frozen = {"scope": {"alert_ids": ["a"]}, "members": {"a": {"included": 8}},
        "questions": ["keep all questions"], "source_states": [{"outcome": "empty"}], "items": items}
    prepared = {"source_map": {item["id"]: {"ref": {"id": item["id"]}, "alert_ids": ["a"]} for item in items},
        "omissions": [], "messages": [{"role": "system", "content": "rules"},
            {"role": "user", "content": encoded(frozen).decode()}]}
    body = {"model": "synthetic", "messages": prepared["messages"], "max_tokens": 3000,
        "temperature": 0, "response_format": response_format(a.Answer, prepared["source_map"])}
    body = prepare_request(SimpleNamespace(provider=protocol), body)
    limit = len(encoded(body)) - 1700
    fit_final_request(body, prepared, limit)
    assert len(encoded(body)) <= limit and body.get("max_tokens", body.get("max_output_tokens")) == 3000
    wire_messages = body.get("messages", body.get("input"))
    schema = body["text"]["format"]["schema"] if "text" in body else body["response_format"]["json_schema"]["schema"]
    data = json.loads(wire_messages[1]["content"])
    for key in ("scope", "questions", "source_states"):
        assert data[key] == frozen[key]
    ids = {item["id"] for item in data["items"]}
    assert ids == set(prepared["source_map"]) == set(schema["$defs"]["SourceId"]["enum"])
    assert prepared["coverage"]["a"]["included"] == len(ids)
    assert len(prepared["omissions"]) == data["omission_counts"]["remaining_final_token_budget"] == 8-len(ids)
    assert len(frozen["items"]) == 8
