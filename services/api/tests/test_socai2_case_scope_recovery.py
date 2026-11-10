"""Saved failures and scope identities; no model calls or original-data writes."""
import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
import test_socai2_case_followup_boundary as followup
import test_socai2_case_model_boundary as base_tests
from app.socai2 import baseline_enrichment_sources as enrichment
from app.socai2 import (
    case_followup_input,
    case_followup_output,
    case_model_boundary,
    case_output_adapter,
)
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from app.socai2.case_source_scope import query_scope
from jsonschema import Draft202012Validator

configured, sample = base_tests.configured, base_tests.sample
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def recorded(configured):
    data = json.loads((ROOT / "docs/operations/evidence/case-current-flow-20261110-01/published/C02/database.json").read_text())
    artifact = next(a for a in data["artifacts"] if a["schema_version"] == "socai2.baseline-context.v1")
    raw = copy.deepcopy(artifact["content_json"])
    raw["case_input_profile"] = configured.case_io.identity
    context = Context.model_validate(raw)
    materials = {aid: next(m for m in data["alert_materials"] if m["id"] == member.material["id"])
                 for aid, member in context.alerts.items()}
    prepared = case_model_boundary.build(context, artifact["id"], [], [], materials)
    assert prepared["ready"], prepared["reason"]
    return context, prepared, artifact


def test_recorded_history_subject_survives_c3_deep_and_final(recorded):
    context, base, artifact = recorded
    a1, _, a3 = sorted(context.alerts)
    path = f"$.alerts.{a3}.queries.2.content_json.rows.0.record.triage"
    sid, source = next((sid, row) for sid, row in base["source_map"].items() if row["ref"]["source_path"] == path)
    assert source["ref"]["id"] == artifact["id"] and source["ref"]["role"] == "prior_analysis"
    assert source["alert_ids"] == source["record_alert_ids"] == [a1]
    assert source["query_alert_ids"] == [a3]
    # Dependencies to an older frozen C1 artifact must not restore its former
    # query-container ownership when the current base view lacks that ref.
    separate = copy.deepcopy(base)
    separate["input_ledger"]["records"] = [r for r in separate["input_ledger"]["records"] if r["ref"] != source["ref"]]
    registry = case_followup_input.Sources(context, separate, {artifact["id"]: artifact}, [])
    restored = registry.resolve({"ref": source["ref"], "alert_ids": [a3]})
    assert registry.by_ref[case_followup_input.encoded(source["ref"])]["alert_ids"] == [a1]
    assert restored and registry.rows[-1]["query_alert_ids"] == [a3]
    answer = base_tests.answer_for(base, context)
    answer["members"][0]["evidence_ids"].append(sid)
    parsed = case_output_adapter.parse(json.dumps(answer), base, context, {})
    previous = {"analysis": parsed.model_dump(mode="json"), "source_map": base["source_map"],
                "validation": "structure_scope_sources_checked"}
    for stage in ("Deep", "C6"):
        prepared = case_followup_input.build(stage, context, base, {}, previous=previous, prior_id=uuid4(),
                                             question_id=context.questions[0].id if stage == "Deep" else None)
        mapped = next(s for s in prepared["source_map"].values() if s["ref"] == source["ref"])
        assert mapped["alert_ids"] == mapped["record_alert_ids"] == [a1]
        assert mapped["query_alert_ids"] == [a3] and mapped["membership_basis"] == "history_record_identity"
        assert "查询范围=A3；返回记录主体=A1" in prepared["messages"][1]["content"]
    answer["members"][2]["evidence_ids"].append(sid)
    with pytest.raises(AnalysisRejected, match="source_member_mismatch"):
        case_output_adapter.parse(json.dumps(answer), base, context, {})


@pytest.mark.parametrize("kind", ["outside", "mismatch", "missing", "nonhistory", "child_mismatch"])
def test_history_identity_cannot_be_inferred_from_query_or_host(kind):
    origin, subject, external = map(str, (uuid4(), uuid4(), uuid4()))
    body = {"tool_name": "history", "rows": [{"record_id": subject, "record": {"id": subject,
            "title": "Identical title and host do not establish membership", "triage": {"alert_id": subject}}}]}
    if kind == "outside":
        body["rows"][0] = {"record_id": external, "record": {"id": external}}
    elif kind == "mismatch":
        body["rows"][0]["record_id"] = origin
    elif kind == "missing":
        body["rows"][0]["record"].pop("id")
    elif kind == "nonhistory":
        body["tool_name"] = "assets"
    else:
        body["rows"][0]["record"]["triage"]["alert_id"] = origin
    before = copy.deepcopy(body)
    result = query_scope(body, "$.rows.0", [origin], {origin, subject})
    assert result["query_alert_ids"] == [origin]
    assert result["alert_ids"] == ([origin] if kind == "nonhistory" else [])
    assert result["membership_basis"] != "history_record_identity" and body == before


def test_scope_and_local_finding_feedback_does_not_repair_answer(sample):
    context, prepared = base_tests.prepared_sample(sample)
    answer = base_tests.answer_for(prepared, context)
    answer["members"][0]["evidence_ids"] += answer["members"][1]["evidence_ids"]
    answer["domains"][0]["finding_ids"] = ["F3", "authorization"]
    original = json.dumps(answer)
    result = case_output_adapter.CaseReview(prepared, context, {}).feedback(original)
    assert {e.get("code") for e in result["errors"]} >= {"source_member_mismatch", "unknown_local_finding"}
    assert result["local_findings"] == [] and json.dumps(answer) == original
    assert all(a.startswith("A") for s in result["allowed_sources"] for a in s["alert_ids"])
    answer["members"][1]["alert_id"] = answer["members"][0]["alert_id"]
    assert case_output_adapter.CaseReview(prepared, context, {}).feedback(json.dumps(answer)) is None


def test_query_origin_outside_current_case_is_retained_without_adding_members():
    origin, subject = str(uuid4()), str(uuid4())
    body = {"tool_name": "history", "rows": [{"record_id": subject, "record": {"id": subject}}]}
    result = query_scope(body, "$.rows.0", [origin], {subject})
    assert result["alert_ids"] == [subject] and result["query_alert_ids"] == [origin]


def test_final_finding_feedback_uses_current_answer_not_previous_findings(sample):
    context, base, previous = followup.fixture(sample)
    prepared = case_followup_input.build("C6", context, base, {}, previous=previous, prior_id=uuid4())
    comparison = {"state": "initial", "result_id": None}
    answer = followup.final_answer(prepared, context, comparison)
    answer["analysis"]["domains"][0]["finding_ids"] = ["F1"]
    review = case_followup_output.FinalReview(prepared, context, comparison)
    result = review.feedback(json.dumps(answer))
    assert result["local_findings"] == []
    assert any(e["path"] == ["analysis", "domains", 0, "finding_ids"] and e["invalid_finding_ids"] == ["F1"]
               for e in result["errors"])
    with pytest.raises(AnalysisRejected):
        review.feedback('{"analysis":{}}')


def test_real_failed_impact_gets_precise_feedback_without_rewriting(configured):
    folder = ROOT / "docs/operations/evidence/case-scope-recovery-20261110-01/real-model-01"
    data = json.loads((folder / "export/database.json").read_text())
    stage = next(s for s in data["run_steps"] if s["stage_code"] == "C6" and s["kind"] == "model")
    prepared = next(a["content_json"]["payload"] for a in data["artifacts"] if a["id"] == stage["input_artifact_id"])
    prepared["coverage"] = {}
    context = Context.model_validate(next(a["content_json"] for a in data["artifacts"] if a["schema_version"] == "socai2.baseline-context.v1"))
    content = json.loads((folder / "calls/call-4-receipt.json").read_text())["raw"]["choices"][0]["message"]["content"]
    review = case_followup_output.FinalReview(prepared, context, {"state": "initial", "result_id": None})
    result = review.feedback(content)
    assert any(e["path"] == ["impact", "support_ids"] and e["uncovered_members"] == ["A2"]
               and not e["direct_evidence_required"] for e in result["errors"])
    assert json.loads(content)["impact"]["support_ids"] == ["N3_S14", "N3_S64"]
    # A source's declared coverage alone cannot substantiate a supported claim.
    answer = json.loads(content)
    answer["conclusion"].update(state="supported", support_ids=["N3_S97"])
    error = next(e for e in review.feedback(json.dumps(answer))["errors"] if e["path"] == ["conclusion", "support_ids"])
    assert error["uncovered_members"] == ["A1", "A2", "A3"] and error["direct_evidence_required"]


def test_deep_action_schema_and_receiver_agree_on_handoff_and_query(sample):
    context, base, previous = followup.fixture(sample)
    prepared = case_followup_input.build("Deep", context, base, {}, previous=previous, prior_id=uuid4(),
                                         question_id=context.questions[0].id)
    original = {"action": "handoff", "binding_id": None, "reason": "Need explicit confirmation.", "answer": None}
    validator = Draft202012Validator(case_followup_output.deep_format(prepared)["json_schema"]["schema"])
    for branch in validator.schema["anyOf"]:
        assert set(branch["required"]) == {"action", "binding_id", "reason", "answer"}
        assert branch["additionalProperties"] is False
        nested = branch["properties"]["answer"]
        for answer in nested.get("anyOf", [nested]):
            assert set(answer["required"]) == {"state", "text", "support_ids", "counter_ids", "alternatives", "limitations"}
            assert answer["additionalProperties"] is False
    assert list(validator.iter_errors(original))
    valid = {**original, "answer": {"state": "unresolved", "text": "Confirmation is missing.",
        "support_ids": [], "counter_ids": [], "alternatives": [], "limitations": ["No authorization record supplied."]}}
    validator.validate(valid)
    assert case_followup_output.parse_deep(json.dumps(valid), prepared).action == "handoff"
    for bad in ({**valid, "answer": {**valid["answer"], "state": "supported"}},
                {**valid, "answer": {**valid["answer"], "limitations": []}},
                {**original, "action": "query"}):
        assert list(validator.iter_errors(bad))
    prepared["binding_map"] = {"B1": {}}
    validator = Draft202012Validator(case_followup_output.deep_format(prepared)["json_schema"]["schema"])
    query = {**original, "action": "query", "binding_id": "B1"}
    validator.validate(query)
    assert case_followup_output.parse_deep(json.dumps(query), prepared).action == "query"
    assert list(validator.iter_errors({**query, "binding_id": None}))


def test_paired_receipts_lower_refresh_priority_and_leave_room_for_knowledge(recorded, monkeypatch):
    context, _, _ = recorded
    monkeypatch.setattr(enrichment, "connected", lambda source: source != "graph")
    plan = enrichment.selection_plan(context)
    assert plan[0]["source"] == "knowledge"
    assets = next(row for row in plan if row["source"] == "assets")
    assert assets["paired_query_members"] == assets["eligible_members"]
    assert assets["reason"] == "paired_background_available"
    assert enrichment.selection_config(context)["reserved_tool_calls"] == 2
    missing = context.model_copy(update={"alerts": {aid: alert.model_copy(update={"queries": []})
                                                   for aid, alert in context.alerts.items()}})
    assert enrichment.selection_plan(missing)[0]["source"] == "assets"


@pytest.mark.parametrize("field,value", [("reserved_tool_calls", -1), ("reserved_tool_calls", True),
    ("paired_source_penalty", "100"), ("priorities", {"assets": 1})])
def test_invalid_enrichment_profile_is_rejected(configured, monkeypatch, field, value):
    from app.socai2.runtime_policy import load_case_profile
    data = configured.case_io.config
    data["enrichment"][field] = value
    original = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda p: json.dumps(data).encode() if p.name == "case-input-v1.json" else original(p))
    with pytest.raises(ValueError, match="case_profile_enrichment_or_citation_invalid"):
        load_case_profile({"profile": "case-input-v1.json"})
