"""C6 contract gates remain strict after prompt-only clarification."""
import copy
import json

import pytest
from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.baseline_context import Context
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
