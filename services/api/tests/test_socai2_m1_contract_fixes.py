"""Fixed m1 evidence plus negative cases; no model, database or history writes."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jsonschema
import pytest
from app.socai2 import alert_basic_contract as alert
from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.answer_validation import Checks
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import StoreError
from app.socai2.model_input_view import items, source_prefix
from app.socai2.model_protocol import prepare_request
from test_socai2_stage_quality import answer, source

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m1"


def frozen():
    plan = json.loads((EVIDENCE / "plan-and-packets.json").read_text("utf-8"))
    parsed = json.loads((EVIDENCE / "parsed-results.json").read_text("utf-8"))
    return {p["id"]: p for p in plan["packets"]}, {p["cell"]: p for p in parsed["cells"]}


def test_unsupported_keyword_removed_before_dispatch_only_for_explicit_profile():
    packets, _ = frozen()
    packet = packets["C3-current"]
    body = {"model": "test", "messages": packet["messages"], "response_format": packet["response_format"], "temperature": 0, "max_tokens": 3000}
    original = copy.deepcopy(body)
    wire = prepare_request(SimpleNamespace(provider="chat_completions", schema_profile="vllm_grammar_v1"), body)
    assert '"uniqueItems"' not in json.dumps(wire)
    assert body == original and '"uniqueItems"' in json.dumps(body)
    assert wire["messages"] == body["messages"] and wire["max_tokens"] == 3000
    schema = wire["response_format"]["json_schema"]["schema"]
    jsonschema.Draft202012Validator.check_schema(schema)
    assert prepare_request(SimpleNamespace(provider="chat_completions"), body) is body
    with pytest.raises(ValueError, match="unknown_model_schema_profile"):
        prepare_request(SimpleNamespace(schema_profile="guess"), body)


def test_m1_time_context_and_domain_links_accepted_without_changing_answer():
    packets, results = frozen()
    packet, raw = packets["C3-current"], results["C3-current-deepseek"]["answer"]
    before = copy.deepcopy(raw)
    result = analysis.parse(json.dumps(raw), packet["source_map"], Context.model_validate(packet["context"]), packet["coverage"])
    assert result.domains[0].applicability == "undetermined" and result.domains[0].finding_ids == ["F1"]
    from app.socai2.baseline_analysis import domain_block
    block = domain_block(result.domains[0], result, packet["source_map"], Context.model_validate(packet["context"]))
    assert block["applicability"] == "undetermined" and block["findings"][0]["id"] == "F1"
    contracts = json.loads((ROOT / "services/api/app/socai2/contracts.schema.json").read_text("utf-8"))
    jsonschema.Draft202012Validator({"$ref": "#/$defs/analysis_block", "$defs": contracts["$defs"]}).validate(block)
    assert raw == before


def test_domain_focus_can_reference_shared_finding_without_changing_either_scope():
    from app.socai2 import baseline_delivery_contract as delivery
    from app.socai2.baseline_analysis import domain_block

    packets, results = frozen()
    packet = packets["C3-current"]
    raw = copy.deepcopy(results["C3-current-deepseek"]["answer"])
    members = [m["alert_id"] for m in raw["members"]]
    refs = list(dict.fromkeys(s for m in raw["members"] for s in m["evidence_ids"]))
    finding = raw["findings"][0]
    finding.update(state="inferred", statement="synthetic cross-member relationship, purpose uncertain",
                   alert_ids=members, support_ids=refs, counter_ids=[])
    domain = raw["domains"][0]
    domain.update(alert_ids=[members[-1]], finding_ids=[finding["id"]])
    before = copy.deepcopy(raw)
    context = Context.model_validate(packet["context"])
    parsed = analysis.parse(json.dumps(raw), packet["source_map"], context, packet["coverage"])
    block = domain_block(parsed.domains[0], parsed, packet["source_map"], context)
    assert block["focus_scope"]["alert_ids"] == [members[-1]]
    assert block["findings"][0]["scope"]["alert_ids"] == members
    schema = json.loads((ROOT / "services/api/app/socai2/contracts.schema.json").read_text())
    validator = jsonschema.Draft202012Validator({"$ref": "#/$defs/analysis_block", "$defs": schema["$defs"]})
    validator.validate(block)
    # Historical blocks remain readable without inventing a focus scope.
    legacy = {k: v for k, v in block.items() if k != "focus_scope"}
    validator.validate(legacy)
    final = {"analysis": raw, "conclusion": {"text": "synthetic unresolved judgment", "state": "uncertain",
        "alert_ids": members, "support_ids": refs, "limitations": ["synthetic test"]},
        "closing_note": "synthetic closing note", "comparison": {"kind": "initial", "summary": None, "support_ids": []},
        "impact": {"summary": "unknown", "alert_ids": [], "support_ids": [], "supported_changes": [],
            "cannot_generalize": ["synthetic incomplete observations"], "next_steps": []}, "recommendations": []}
    delivered = delivery.parse(json.dumps(final), packet["source_map"], context, packet["coverage"],
                               {"state": "initial", "result_id": None})
    assert list(map(str, delivered.analysis.findings[0].alert_ids)) == members
    assert raw == before


@pytest.mark.parametrize("change,expected", [("time_only", "observed_requires_activity_source"),
    ("title", "non_observation_promoted_to_observed"), ("wrong_member_time", "source_member_mismatch"),
    ("duplicate_conflict", "duplicate_conflict_finding"), ("wrong_domain_scope", "domain_finding_scope_mismatch")])
def test_context_exception_cannot_promote_labels_or_bypass_scope(change, expected):
    packets, results = frozen()
    packet, raw = packets["C3-current"], copy.deepcopy(results["C3-current-deepseek"]["answer"])
    if change == "time_only":
        raw["findings"][0]["support_ids"] = ["S22"]
    elif change == "title":
        raw["findings"][0]["support_ids"].append("S24")
    elif change == "wrong_member_time":
        raw["findings"][0]["support_ids"].append("S23")
    elif change == "duplicate_conflict":
        raw["conflicts"] = [{"id": "X1", "finding_ids": ["F1", "F1"], "state": "unresolved", "explanation": "test", "evidence_ids": []}]
    else:
        raw["domains"][0]["alert_ids"] = [raw["members"][1]["alert_id"]]
    with pytest.raises(analysis.AnalysisRejected, match=expected):
        analysis.parse(json.dumps(raw), packet["source_map"], Context.model_validate(packet["context"]), packet["coverage"])


def test_history_namespace_preserves_literal_text_and_avoids_all_received_prefixes():
    original = source()
    member = original["members"][0]
    member["triage"] = {"id": str(uuid4()), "source_run_id": str(uuid4()), "verdict": "needs_review",
        "rationale": "Source S14 says TCP. Prior N1_S2 is uncertain. Account S1 is literal.", "confidence": .4,
        "score_state": "available", "assessed_at": "2026-11-04T00:00:00Z"}
    original["triage_validation"][member["alert"]["id"]] = {"usable": True, "freshness": "current",
        "triage_id": member["triage"]["id"], "source_run_id": member["triage"]["source_run_id"]}
    before = copy.deepcopy(original)
    messages, mapping, data = incident.build(original, uuid4())
    assert all(sid.startswith("N2_S") for sid in mapping)
    prior = next(i for i in items(data) if i["role"] == "prior_analysis")
    assert prior["value"]["rationale"] == member["triage"]["rationale"]
    assert original == before and len(messages[1]["content"].encode()) <= 8192
    assert source_prefix(["N1_", "N2_", "N3_", (uuid4(), {"value": "N4_S1"})]) == "N5_"


def test_historical_prose_no_longer_exempts_an_unbound_current_id():
    packets, _ = frozen()
    packet = packets["I-current"]
    checks = Checks()
    checks.prose("Source S1", "$", [], packet["source_map"], packet["data"], "incident_answer")
    assert checks.first_error == "incident_answer_prose_source_unbound"


def test_single_structured_reference_is_not_repaired_from_known_inline_reference():
    _, mapping, data = alert.build(source(), uuid4(), [])
    value = answer(data)
    sid = next(s for s in mapping if s not in value["evidence_ids"])
    value["explanation"] = f"Visible record {sid}; purpose still unknown."
    diagnostics = []
    output = alert.parse(json.dumps(value), mapping, data, diagnostics=diagnostics)
    assert len(output.source_refs) == 1
    assert any(d["code"] == "inline_source_not_structured_evidence" and d["severity"] == "warning" for d in diagnostics)
    value["explanation"] = "N999_S1 says authorized."
    with pytest.raises(StoreError, match="prose_source_unbound"):
        alert.parse(json.dumps(value), mapping, data)


def test_inline_member_reference_still_checks_ownership():
    mapping = {"N1_S1": {"ref": {"role": "observation"}, "alert_ids": ["other"]}}
    checks = Checks()
    checks.prose("N1_S1", "$", [], mapping, {"items": [], "citations": "structured_v3"}, "incident_answer", owned=["own"])
    assert checks.first_error == "incident_answer_prose_source_wrong_member"


def test_positive_judgment_requires_separate_direct_basis_not_mixed_label_evidence():
    _, mapping, data = alert.build(source(), uuid4(), [])
    value = answer(data)
    obs = value["evidence_ids"][0]
    label = next(i["id"] for i in items(data) if i["role"] == "source_label")
    value.update(verdict="benign", evidence_ids=[obs, label])
    with pytest.raises(StoreError, match="alert_decision_basis_required"):
        alert.parse(json.dumps(value), mapping, data)
    value["decision_basis"] = {"kind": "authorized_or_expected_behavior", "claim": "The label asserts normal activity", "source_ids": [label]}
    with pytest.raises(StoreError, match="alert_decision_basis_not_direct"):
        alert.parse(json.dumps(value), mapping, data)
    value["decision_basis"]["source_ids"] = [obs, label]
    with pytest.raises(StoreError, match="alert_decision_basis_not_direct"):
        alert.parse(json.dumps(value), mapping, data)
    value["verdict"] = "true_positive"
    with pytest.raises(StoreError, match="alert_decision_basis_mismatch"):
        alert.parse(json.dumps(value), mapping, data)


def test_explicit_human_basis_retains_references_and_is_not_a_truth_guarantee():
    frozen_source = source()
    frozen_source["members"][0]["feedback"] = {"conclusion": "benign", "comment": "I authorized this exact process during this window."}
    _, mapping, data = alert.build(frozen_source, uuid4(), [])
    human = next(i["id"] for i in items(data) if i["role"] == "human_statement")
    value = answer(data)
    value.update(verdict="benign", rationale="Human authorization for the scoped activity", evidence_ids=[human],
        decision_basis={"kind": "authorized_or_expected_behavior", "claim": "Explicit authorization for the scoped activity", "source_ids": [human]})
    result = alert.parse(json.dumps(value), mapping, data)
    assert result.verdict == "benign" and result.source_refs[0].role == "human_statement"
    assert "structure_sources_checked_not_truth_proven" in result.limitations
