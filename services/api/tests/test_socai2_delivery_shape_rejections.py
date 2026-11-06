"""C6 provider shape constraints and the independent local receipt gates."""
import copy
import json
from types import SimpleNamespace

import pytest
from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.baseline_capacity import final_reservation, final_wire_reason
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import encoded
from app.socai2.model_protocol import DEEPSEEK_PROTOCOL, prepare_request
from app.socai2.structured_output import response_format
from jsonschema import Draft202012Validator
from test_socai2_followup_scope import frozen


def candidate():
    packet, answer = frozen()
    context = Context.model_validate(packet["context"])
    sources = list(dict.fromkeys(next(sid for sid, source in packet["source_map"].items()
        if aid in source["alert_ids"] and source["ref"]["role"] != "execution_receipt") for aid in context.alerts))
    value = {"analysis": answer,
        "conclusion": {"text": "Authorization remains unresolved", "state": "uncertain",
            "alert_ids": list(context.alerts), "support_ids": sources, "limitations": ["No approval supplied"]},
        "closing_note": "Review the scoped evidence",
        "comparison": {"kind": "initial", "summary": None, "support_ids": []},
        "impact": {"summary": "Impact not established", "alert_ids": [], "support_ids": [],
            "supported_changes": [], "cannot_generalize": ["No observed impact"], "next_steps": []},
        "recommendations": []}
    return packet, context, value


def parse(packet, context, value):
    return delivery.parse(json.dumps(value), packet["source_map"], context, packet["coverage"],
        {"state": "initial", "result_id": None})


def test_missing_final_followups_is_rejected_without_default_or_response_repair():
    packet, context, value = candidate()
    value["analysis"]["followups"] = []
    parse(packet, context, value)
    del value["analysis"]["followups"]
    original = copy.deepcopy(value)
    errors = list(Draft202012Validator(delivery.Delivery.model_json_schema()).iter_errors(value))
    assert len(errors) == 1 and list(errors[0].absolute_path) == ["analysis"]
    assert errors[0].validator == "required" and "followups" in errors[0].message
    with pytest.raises(analysis.AnalysisRejected, match="^delivery_shape_invalid$"):
        parse(packet, context, value)
    assert value == original and "followups" not in value["analysis"]


def test_final_domain_cannot_omit_member_of_linked_finding():
    packet, context, value = candidate()
    parse(packet, context, value)
    domain = next(d for d in value["analysis"]["domains"] if d["finding_ids"])
    finding = next(f for f in value["analysis"]["findings"] if f["id"] == domain["finding_ids"][0])
    omitted = finding["alert_ids"][0]
    domain["alert_ids"] = [a for a in context.alerts if a != omitted]
    original = copy.deepcopy(value)
    # Cross-field scope is a semantic gate, even when the wire shape is valid.
    Draft202012Validator(delivery.Delivery.model_json_schema()).validate(value)
    with pytest.raises(analysis.AnalysisRejected, match="^domain_finding_scope_mismatch$"):
        parse(packet, context, value)
    assert value == original


def test_narrow_domain_can_leave_a_cross_member_finding_in_the_case_only():
    packet, context, value = candidate()
    case_analysis = value["analysis"]
    finding = next(f for f in case_analysis["findings"] if len(f["alert_ids"]) > 1)
    domain = case_analysis["domains"][0]
    domain["alert_ids"] = finding["alert_ids"][:1]
    domain["finding_ids"] = [finding["id"]]
    with pytest.raises(analysis.AnalysisRejected, match="^domain_finding_scope_mismatch$"):
        parse(packet, context, value)

    domain["finding_ids"] = []
    accepted = parse(packet, context, value).analysis.model_dump(mode="json")
    assert accepted == case_analysis


def test_first_delivery_wire_requires_the_same_empty_comparison_as_the_parser():
    packet, context, value = candidate()
    sources = packet["source_map"]
    initial = {"state": "initial", "result_id": None}
    schema = delivery.delivery_format(sources, context, initial)["json_schema"]["schema"]
    validator = Draft202012Validator(schema)
    validator.validate(value)
    parse(packet, context, value)
    for field, invalid in (("summary", "没有基线"), ("support_ids", [next(iter(sources))]), ("kind", "expanded")):
        wrong = copy.deepcopy(value)
        wrong["comparison"][field] = invalid
        assert not validator.is_valid(wrong)
        with pytest.raises(analysis.AnalysisRejected, match="^initial_delivery_must_not_invent_comparison$"):
            parse(packet, context, wrong)
    with pytest.raises(analysis.AnalysisRejected, match="^delivery_shape_invalid$"):
        delivery.parse(json.dumps(value)[:-1], sources, context, packet["coverage"], initial)


@pytest.mark.parametrize("provider,profile", [("chat_completions", "standard"),
    ("chat_completions", "vllm_grammar_v1"), (DEEPSEEK_PROTOCOL, "standard")])
def test_initial_schema_fits_existing_reservation_and_other_rounds_keep_their_schema(provider, profile):
    packet, context, value = candidate()
    sources = packet["source_map"]
    gateway = SimpleNamespace(model="synthetic", provider=provider, schema_profile=profile)
    generic = response_format(delivery.Delivery, sources, members=context.alerts,
        questions=[q.id for q in context.questions], objects=context.scope.object_keys)
    for state, rid in (("eligible", "prior"), ("unavailable", "prior"), ("not_selected", None)):
        assert delivery.delivery_format(sources, context, {"state": state, "result_id": rid}) == generic
    envelope = {"model": gateway.model, "messages": [], "temperature": 0, "max_tokens": 3000}
    base = prepare_request(gateway, {**envelope, "response_format": generic})
    first = prepare_request(gateway, {**envelope, "response_format": delivery.delivery_format(
        sources, context, {"state": "initial", "result_id": None})})
    wire_schema = (first["text"]["format"]["schema"] if provider == DEEPSEEK_PROTOCOL
                   else first["response_format"]["json_schema"]["schema"])
    Draft202012Validator(wire_schema).validate(value)
    assert len(encoded(first)) <= len(encoded(base))
    assert final_wire_reason(first, final_reservation(gateway, context)) is None
