"""Frozen same-material handoff and program-field restoration, no network."""
import copy
import json
from uuid import UUID, uuid4

import pytest
import test_socai2_case_model_boundary as base_tests
from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as outputs
from app.socai2 import case_output_adapter
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_store import StoreError
from jsonschema import Draft202012Validator

answer_for, prepared_sample = base_tests.answer_for, base_tests.prepared_sample
configured, sample = base_tests.configured, base_tests.sample


def fixture(sample):
    context, base = prepared_sample(sample)
    answer = answer_for(base, context)
    own = answer["members"][0]["evidence_ids"][0]
    second = answer["members"][1]["evidence_ids"][0]
    answer["questions"][0]["evidence_ids"] = [own]
    answer["summary"] = "Historical N1_S1 prose must remain verbatim."
    answer["findings"] = [{"id": "F1", "state": "unresolved", "statement": "Synthetic cross-member issue.",
        "alert_ids": [m["alert_id"] for m in answer["members"][:2]], "support_ids": [own],
        "counter_ids": [second], "alternatives": ["Synthetic alternative."], "limitations": ["Synthetic only."]}]
    original = json.loads(case_output_adapter.restore(json.dumps(answer), base["case_boundary"]))
    previous = {"analysis": original, "source_map": base["source_map"], "validation": "structure_scope_sources_checked"}
    return context, base, previous


def final_answer(prepared, context, comparison):
    answer = answer_for(prepared, context)
    result = {"analysis": answer, "conclusion": {"text": "Synthetic uncertain conclusion.", "state": "uncertain",
        "alert_ids": [prepared["case_boundary"]["member_aliases"][aid] for aid in context.alerts],
        "support_ids": [m["evidence_ids"][0] for m in answer["members"]], "limitations": ["Synthetic only."]},
        "closing_note": "Synthetic round.", "impact": {"summary": "No confirmed impact.", "alert_ids": [],
            "support_ids": [], "supported_changes": [], "cannot_generalize": ["Synthetic only."], "next_steps": []},
        "recommendations": [{"action_type": "investigate", "object_keys": [], "reason": "Synthetic review.",
            "source_ids": [answer["members"][0]["evidence_ids"][0]], "limitations": []}]}
    if not outputs.fixed_comparison(comparison):
        result["comparison"] = {"kind": "not_comparable", "summary": "No selected comparison.", "support_ids": []}
    return result


def test_final_preserves_complete_prior_and_support_counter_dependencies(sample):
    context, base, prior = fixture(sample)
    before = copy.deepcopy((base, prior))
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    assert prepared["ready"], prepared["reason"]
    rows = prepared["followup_boundary"]["records"]
    previous = next(r for r in rows if r["block"] == "C3")
    assert set(previous["value"]) == set(prior["analysis"])
    assert previous["value"]["summary"] == prior["analysis"]["summary"]
    assert len(previous["value"]["questions"]) == 6
    finding = previous["value"]["findings"][0]
    assert finding["alert_ids"] == ["A1", "A2"]
    assert finding["support_ids"] and finding["counter_ids"]
    assert all(d["visible_id"] in prepared["source_map"] for d in prepared["followup_boundary"]["dependencies"])
    assert not set(base["source_map"]) & set(prepared["source_map"])
    assert (base, prior) == before
    assert len({r["ref"]["source_path"] for r in rows if ".diagnosis.findings." in (r["ref"]["source_path"] or "")}) == 8
    assert len({r["ref"]["source_path"].split(".content_json")[0] for r in rows if ".queries." in (r["ref"]["source_path"] or "")}) == 9


def test_missing_prior_source_is_explicit_not_relabelled_or_invented(sample):
    context, base, prior = fixture(sample)
    prior["analysis"]["questions"][0]["evidence_ids"] = ["not-visible"]
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    previous = next(r for r in prepared["followup_boundary"]["records"] if r["block"] == "C3")
    assert previous["value"]["unavailable_prior_reference_count"] == 1
    assert previous["value"]["questions"][0]["evidence_ids"] == []
    assert previous["value"]["questions"][0]["state"] == prior["analysis"]["questions"][0]["state"]
    assert any(d["visible_id"] is None for d in prepared["followup_boundary"]["dependencies"])


def test_deep_answer_references_are_handed_to_final_with_original_role(sample):
    context, base, prior = fixture(sample)
    sid = prior["analysis"]["members"][0]["evidence_ids"][0]
    identity = str(uuid4())
    answer = {"state": "unresolved", "text": "Original Deep N2_E7 prose.", "support_ids": [sid],
              "counter_ids": [], "alternatives": [], "limitations": ["Not resolved."]}
    artifact = {identity: {"content_json": {"type": "deep_summary", "answer": answer,
        "question_id": context.questions[0].id, "source_map": prior["source_map"]}}}
    prepared = inputs.build("C6", context, base, artifact, previous=prior, prior_id=uuid4())
    row = next(r for r in prepared["followup_boundary"]["records"] if r["block"] == "Deep")
    assert row["ref"]["role"] == "prior_analysis"
    assert row["value"]["text"] == answer["text"]
    assert prepared["source_map"][row["value"]["support_ids"][0]]["ref"] == prior["source_map"][sid]["ref"]


def test_deep_omits_question_output_and_restores_only_bound_identity(sample):
    context, base, prior = fixture(sample)
    qid = context.questions[0].id
    prepared = inputs.build("Deep", context, base, {}, previous=prior, prior_id=uuid4(), question_id=qid)
    assert prepared["ready"], prepared["reason"]
    fmt = outputs.deep_format(prepared)["json_schema"]["schema"]
    answer = {"action": "handoff", "binding_id": None, "reason": "Human evidence required.",
        "answer": {"state": "unresolved", "text": "Needs evidence.", "support_ids": [], "counter_ids": [],
                   "alternatives": [], "limitations": ["No authorization records."]}}
    assert set(fmt["properties"]) == {"action", "binding_id", "reason", "answer"}
    Draft202012Validator(fmt).validate(answer)
    assert outputs.parse_deep(json.dumps(answer), prepared).question_id == qid
    with pytest.raises(AnalysisRejected):
        outputs.parse_deep(json.dumps({**answer, "question_id": "another-question"}), prepared)


@pytest.mark.parametrize("state", ["initial", "not_selected"])
def test_final_restores_original_contract_without_model_owned_known_fields(sample, state):
    context, base, prior = fixture(sample)
    comparison = {"state": state, "result_id": None}
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4(), extra={"comparison": comparison})
    answer = final_answer(prepared, context, comparison)
    schema = outputs.final_format(prepared, context, comparison)["json_schema"]["schema"]
    assert "id" not in schema["$defs"]["Recommendation"]["properties"]
    assert ("comparison" in schema["properties"]) == (state != "initial")
    Draft202012Validator(schema).validate(answer)
    value = outputs.parse_final(json.dumps(answer), prepared, context, comparison)
    assert value.recommendations[0].id == "R1"
    assert {str(m.alert_id) for m in value.analysis.members} == set(context.alerts)
    assert value.comparison.kind == ("initial" if state == "initial" else "not_comparable")


def test_final_feedback_and_partial_review_still_use_model_aliases(sample):
    context, base, prior = fixture(sample)
    comparison = {"state": "initial", "result_id": None}
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    answer = final_answer(prepared, context, comparison)
    answer["analysis"]["members"][0].update(state="analyzed", evidence_ids=[])
    review = outputs.FinalReview(prepared, context, comparison)
    feedback = review.feedback(json.dumps(answer))
    assert feedback["errors"][0]["subject_id"] == "A1"
    answer["analysis"]["members"][0]["evidence_ids"] = ["invalid-source"]
    assert review.partial(json.dumps(answer)) is None
    assert review.details["conclusion_adoptable"] is False
    assert review.details["retained_analysis"]["members"][1]["state"] == "unresolved"


def test_no_accepted_c3_remains_explicit_and_profile_mismatch_rejected(sample):
    context, base, _ = fixture(sample)
    prepared = inputs.build("C6", context, base, {})
    assert "没有可用的C3判断" in prepared["messages"][1]["content"]
    base["case_boundary"]["profile"]["sha256"] = "changed"
    with pytest.raises(StoreError, match="case_input_profile_changed"):
        inputs.build("C6", context, base, {})


@pytest.mark.parametrize("state,rows", [("completed", 0), ("failed", None), ("unknown", None), ("skipped", None)])
def test_actual_query_states_and_empty_result_are_not_conflated(sample, state, rows):
    context, base, _ = fixture(sample)
    aid, identity = next(iter(context.alerts)), str(uuid4())
    payload = {"type": "query_projection", "binding_id": "bound", "question_id": context.questions[0].id,
        "state": state, "reason": None, "alert_ids": [aid], "observed_rows_in_bounded_fetch": rows,
        "truncated": False, "limitations": [], "rows": []}
    material = {"catalog": {"bindings": {"bound": {"tool_name": "authentication_activity", "hostname": "host",
        "scope": {"window_start": None, "window_end": None}}}}}
    projection = {"id": identity, "content_json": payload, "sha256": inputs.digest(payload)}
    prepared = inputs.build("C6", context, base, {}, material=material, projections=[projection])
    assert prepared["ready"]
    fact = prepared["followup_boundary"]["query_facts"][0]
    assert fact["state"] == state and fact["observed_rows_in_bounded_fetch"] == rows
    assert not any(r["block"] == "query" for r in prepared["followup_boundary"]["records"])


def test_c6_query_rows_preserve_grouping_typed_values_and_required_behavior_guard(sample):
    context, base, _ = fixture(sample)
    aid, identity = next(iter(context.alerts)), str(uuid4())
    fields = [{"name": name, "value": value, "source_path": "$.raw." + name, "transform": "identity", "conflict": False}
              for name, value in [("dest_ip", "198.51.100.20"), ("dst_port", 443), ("is_approved", False), ("bytes_out", 0)]]
    payload = {"type": "query_projection", "binding_id": "bound", "question_id": context.questions[0].id,
        "state": "completed", "reason": None, "alert_ids": [aid], "observed_rows_in_bounded_fetch": 1,
        "truncated": False, "limitations": [], "rows": [{"semantics": {"fields": fields}}]}
    material = {"catalog": {"bindings": {"bound": {"tool_name": "network_connections", "hostname": "host",
        "scope": {"window_start": None, "window_end": None}}}}}
    def build():
        projection = {"id": identity, "content_json": payload, "sha256": inputs.digest(payload)}
        return inputs.build("C6", context, base, {}, material=material, projections=[projection])
    prepared = build()
    assert prepared["ready"]
    rows = [r for r in prepared["followup_boundary"]["records"] if r["block"] == "query"]
    assert {r["value"]["record_key"] for r in rows} == {"Q1R0"}
    assert rows[2]["value"]["value"] is False and type(rows[3]["value"]["value"]) is int
    assert all(r["membership_basis"] == "query_binding_only" for r in rows)
    fields[0]["value"] = 'password="synthetic_not_a_real_password"'
    blocked = build()
    assert not blocked["ready"] and blocked["reason"] == "required_query_evidence_unavailable"
    assert blocked["followup_boundary"]["query_facts"][0]["visible_fields"] == 3


def test_deep_narrow_scope_restores_required_cross_member_source_without_relabeling(sample):
    context, base, prior = fixture(sample)
    aid, other = list(context.alerts)[:2]
    question = context.questions[0]
    question = question.model_copy(update={"scope": question.scope.model_copy(update={"alert_ids": [UUID(aid)]})})
    context = context.model_copy(update={"questions": [question, *context.questions[1:]]})
    source = next(sid for sid, row in base["source_map"].items() if row["alert_ids"] == [other] and row["ref"]["role"] == "observation")
    prior["analysis"]["questions"][0]["evidence_ids"] = [source]
    prepared = inputs.build("Deep", context, base, {}, previous=prior, prior_id=uuid4(), question_id=question.id)
    row = next(r for r in prepared["followup_boundary"]["records"] if r["block"] == "C3")
    sid = row["value"]["question"]["evidence_ids"][0]
    assert prepared["source_map"][sid]["alert_ids"] == [other]
    assert prepared["source_map"][sid]["ref"] == base["source_map"][source]["ref"]


def test_frozen_material_identity_projection_deduplicates_but_changed_value_does_not(sample):
    context, base, prior = fixture(sample)
    field = next(r for r in base["input_ledger"]["records"] if r["ref"]["type"] == "alert_material" and r["ref"]["source_path"].endswith(".outcome"))
    aid, identity = field["alert_ids"][0], str(uuid4())
    value = {"name": "outcome", "value": field["value"], "source_path": field["ref"]["source_path"],
             "transform": "identity", "conflict": False}
    payload = {"type": "materials", "members": {aid: {"material_id": field["ref"]["id"], "fields": [value]}}}
    ref = inputs.reference("artifact", identity, "observation", f"$.members.{aid}.fields.0")
    prior["source_map"]["old-field"] = {"ref": ref, "alert_ids": [aid]}
    prior["analysis"]["questions"][0]["evidence_ids"] = ["old-field"]
    artifacts = {identity: {"content_json": payload, "schema_version": inputs.EVIDENCE_SCHEMA}}
    def target():
        result = inputs.build("C6", context, base, artifacts, previous=prior, prior_id=uuid4())
        c3 = next(r for r in result["followup_boundary"]["records"] if r["block"] == "C3")
        return result["source_map"][c3["value"]["questions"][0]["evidence_ids"][0]]["ref"]
    assert target() == field["ref"]
    value["value"] = "different original observation"
    assert target() == ref


def test_stale_graph_and_guarded_c3_cannot_appear_available(sample, monkeypatch):
    from app.socai2.case_followup_loader import graph_candidates
    context, base, prior = fixture(sample)
    prior["analysis"]["summary"] = 'password="synthetic_not_a_real_password"'
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    assert prepared["ready"]
    assert "没有可用的C3判断" in prepared["messages"][1]["content"]
    assert not any(r["block"] == "C3" for r in prepared["followup_boundary"]["records"])
    assert graph_candidates([], {}) == ("not_built", [])
    bases = [{"id": "new-query", "content_json": {"type": "query_projection"}},
             {"id": "snapshot", "content_json": {"type": "graph_snapshot", "captured_at": "2026-11-10", "input_artifact_ids": []}}]
    assert graph_candidates(bases, {}) == ("stale", [])


def test_historical_comparison_keeps_old_scope_without_offering_historical_targets(sample):
    context, base, prior = fixture(sample)
    aid, removed, rid = next(iter(context.alerts)), str(uuid4()), str(uuid4())
    comparison = {"state": "eligible", "result_id": rid, "added_alert_ids": [], "removed_alert_ids": [removed],
        "shared_alert_ids": [aid], "prior_scope": {"kind": "whole_case", "alert_ids": [aid, removed],
            "object_keys": ["host:previous-only"], "window_start": "2026-10-01T00:00:00Z", "window_end": "2026-10-01T01:00:00Z"}}
    value = {"comparison_result_id": rid, "validation_state": "accepted", "delivery_state": "complete",
             "conclusion_state": "uncertain", "conclusion_origin": "model", "conclusion": "Old judgment unchanged."}
    lead = [{"original": value, "required": True, "entry": {"value": value},
             "source": {"ref": inputs.reference("result", rid, "prior_analysis"), "alert_ids": [aid]}}]
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4(), extra={"comparison": comparison}, lead=lead)
    assert prepared["ready"]
    text = prepared["messages"][1]["content"]
    assert rid not in text and removed not in text
    assert "2026-10-01T00:00:00Z" in text and "H1=host:previous-only" in text
    row = next(r for r in prepared["followup_boundary"]["records"] if r["block"] == "comparison")
    assert row["value"]["conclusion"] == value["conclusion"]
    assert "comparison_result_id" not in row["value"]
    schema = outputs.final_format(prepared, context, comparison)["json_schema"]["schema"]
    assert "X1" not in schema["$defs"]["AlertId"]["enum"]
    assert "H1" not in schema["$defs"]["ObjectKey"]["enum"]
