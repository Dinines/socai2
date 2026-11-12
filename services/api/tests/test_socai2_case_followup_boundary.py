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
from app.socai2.baseline_store import StoreError, digest, encoded
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
    evidence = next(r for r in base["input_ledger"]["records"] if r["ref"]["role"] == "observation")
    triage = next(r for r in base["input_ledger"]["records"] if r["block"] == "triage")
    triage["value"]["source_refs"] = [evidence["id"]]
    triage["original_value"]["source_refs"] = [evidence["ref"]]
    incident = next(r for r in base["input_ledger"]["records"] if r["block"] == "incident")
    incident["prior_reference_resolution"] = {"visible": [evidence["id"]], "not_visible": []}
    incident["incident_source_refs"] = [evidence["ref"]]
    before = copy.deepcopy((base, prior))
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    assert prepared["ready"], prepared["reason"]
    rows = prepared["followup_boundary"]["records"]
    previous = next(r for r in rows if r["block"] == "C3")
    assert set(previous["value"]) == set(prior["analysis"])
    assert previous["value"]["summary"] == prior["analysis"]["summary"]
    assert [q["id"] for q in previous["value"]["questions"]] == [q["id"] for q in prior["analysis"]["questions"] if q["id"] != "coverage"]
    finding = previous["value"]["findings"][0]
    assert finding["alert_ids"] == ["A1", "A2"]
    assert finding["support_ids"] and finding["counter_ids"]
    assert all(d["visible_id"] in prepared["source_map"] for d in prepared["followup_boundary"]["dependencies"])
    assert not set(base["source_map"]) & set(prepared["source_map"])
    assert (base, prior) == before
    assert len({r["ref"]["source_path"] for r in rows if ".diagnosis.findings." in (r["ref"]["source_path"] or "")}) == 8
    assert len({r["ref"]["source_path"].split(".content_json")[0] for r in rows if ".queries." in (r["ref"]["source_path"] or "")}) == 9
    current_triage = next(r for r in rows if r["ref"] == triage["ref"])
    current_incident = next(r for r in rows if r["ref"] == incident["ref"])
    for sid in [*current_triage["value"]["source_refs"], *current_incident["prior_reference_resolution"]["visible"]]:
        assert prepared["source_map"][sid]["ref"] == evidence["ref"]
    for old in base["input_ledger"]["records"]:
        if "original_scope" in old:
            current = next(r for r in rows if r["ref"] == old["ref"])
            assert prepared["source_map"][current["id"]]["original_scope"] == old["original_scope"]
    assert "[材料限制]" not in prepared["messages"][1]["content"]


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


@pytest.mark.parametrize("has_observation", [True, False])
def test_deep_wire_and_receive_agree_on_execution_receipt_evidence(has_observation):
    sources = {"S1": {"ref": {"role": "execution_receipt"}}}
    if has_observation:
        sources["S2"] = {"ref": {"role": "observation"}}
    prepared = {"source_map": sources, "binding_map": {}, "case_boundary": {"question_id": "coverage"}}
    original = copy.deepcopy(prepared)
    schema = outputs.deep_format(prepared)["json_schema"]["schema"]
    validator = Draft202012Validator(schema)
    answer = {"action": "handoff", "binding_id": None, "reason": "Source coverage still unknown.",
        "answer": {"state": "unresolved", "text": "No substantive conclusion.", "support_ids": [],
                   "counter_ids": [], "alternatives": [], "limitations": ["Query status alone is not evidence."]}}
    validator.validate(answer)
    outputs.parse_deep(json.dumps(answer), prepared)
    for field in ("support_ids", "counter_ids"):
        invalid = copy.deepcopy(answer)
        invalid["answer"][field] = ["S1"]
        assert list(validator.iter_errors(invalid))
        with pytest.raises(AnalysisRejected, match="execution_receipt_is_not_evidence"):
            outputs.parse_deep(json.dumps(invalid), prepared)
    if has_observation:
        answer["answer"]["support_ids"] = ["S2"]
        validator.validate(answer)
        outputs.parse_deep(json.dumps(answer), prepared)
    assert prepared == original  # keep receipt input and its original role


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
    empty_recommendation = copy.deepcopy(answer)
    empty_recommendation["recommendations"][0]["source_ids"] = []
    assert list(Draft202012Validator(schema).iter_errors(empty_recommendation))
    with pytest.raises(AnalysisRejected, match="recommendation_needs_sources"):
        outputs.parse_final(json.dumps(empty_recommendation), prepared, context, comparison)
    review = outputs.FinalReview(prepared, context, comparison)
    feedback = review.feedback(json.dumps(empty_recommendation))
    assert any(e["path"] == ["recommendations", 0, "source_ids"]
               and e["code"] == "recommendation_needs_sources" for e in feedback["errors"])
    assert review.partial(json.dumps(empty_recommendation)) is None
    assert review.details["conclusion_adoptable"] is False
    assert len(review.details["retained_analysis"]["members"]) == len(context.alerts)
    from app.socai2.baseline_delivery_contract import delivery_format
    legacy = Draft202012Validator(delivery_format(prepared["source_map"], context, comparison)["json_schema"]["schema"])
    legacy.validate(json.loads(outputs.restore_final(json.dumps(answer), prepared, comparison)))
    assert list(legacy.iter_errors(json.loads(outputs.restore_final(json.dumps(empty_recommendation), prepared, comparison))))
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
    answer["analysis"]["members"][0]["state"] = "unresolved"
    feedback = review.feedback(json.dumps(answer))
    assert any(e["path"] == ["analysis", "members", 0, "evidence_ids"]
               and e["code"] == "member_source_coverage_missing" for e in feedback["errors"])
    answer["analysis"]["members"][0]["evidence_ids"] = ["invalid-source"]
    assert review.partial(json.dumps(answer)) is None
    assert review.details["conclusion_adoptable"] is False
    assert review.details["retained_analysis"]["members"][1]["state"] == "unresolved"


def test_final_evidence_slots_exclude_receipts_without_narrowing_analysis(sample):
    context, base, prior = fixture(sample)
    comparison = {"state": "not_selected", "result_id": None}
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    answer = final_answer(prepared, context, comparison)
    receipt = next(sid for sid, source in prepared["source_map"].items()
                   if source["ref"]["role"] == "execution_receipt")
    schema = outputs.final_format(prepared, context, comparison)["json_schema"]["schema"]
    validator = Draft202012Validator(schema)
    validator.validate(answer)
    outputs.parse_final(json.dumps(answer), prepared, context, comparison)
    for name in ("conclusion", "comparison", "impact", "recommendations"):
        invalid = copy.deepcopy(answer)
        if name == "recommendations":
            invalid[name][0]["source_ids"] = [receipt]
        else:
            invalid[name]["support_ids"] = [receipt]
        assert list(validator.iter_errors(invalid))
        with pytest.raises(AnalysisRejected, match="execution_receipt_not_conclusion_evidence"):
            outputs.parse_final(json.dumps(invalid), prepared, context, comparison)
    answer["analysis"]["questions"][0].update(state="unresolved", evidence_ids=[receipt],
        limitations=["Execution coverage alone leaves the business question unresolved."])
    validator.validate(answer)
    outputs.parse_final(json.dumps(answer), prepared, context, comparison)


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
    context, base, prior = fixture(sample)
    aid, identity = next(iter(context.alerts)), str(uuid4())
    fields = [{"name": name, "value": value, "source_path": "$.raw." + name, "transform": "identity", "conflict": False}
              for name, value in [("dest_ip", "198.51.100.20"), ("dst_port", 443), ("is_approved", False), ("bytes_out", 0)]]
    payload = {"type": "query_projection", "binding_id": "bound", "question_id": context.questions[0].id,
        "state": "completed", "reason": None, "alert_ids": [aid], "observed_rows_in_bounded_fetch": 1,
        "truncated": False, "limitations": [], "rows": [{"semantics": {"fields": fields}}]}
    material = {"catalog": {"bindings": {"bound": {"tool_name": "network_connections", "hostname": "host",
        "scope": {"window_start": None, "window_end": None}}}}}
    def build(stage="C6", previous=None, extra=()):
        projection = {"id": identity, "schema_version": inputs.EVIDENCE_SCHEMA,
                      "content_json": payload, "sha256": inputs.digest(payload)}
        projections = [projection, *extra]
        return inputs.build(stage, context, base, {p["id"]: p for p in projections}, material=material,
                            projections=projections, previous=previous, prior_id=uuid4(),
                            question_id=context.questions[0].id if stage == "Deep" else None)
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
    fields[0]["value"] = "198.51.100.20"
    fields.extend({"name": name, "value": value, "source_path": "$.raw." + name,
                   "transform": "identity", "conflict": False} for name, value in [
        ("event_id", "internal-event-0"), ("event_time", "2026-11-12T01:00:00Z"),
        ("process_command_line", "synthetic repeated command with original arguments"), ("custom_matches", [])])
    # Keep rows independent, with distinct time/identity and an explicit conflict.
    payload["rows"] = [copy.deepcopy(payload["rows"][0]) for _ in range(3)]
    for i, record in enumerate(payload["rows"]):
        record["semantics"]["fields"][4]["value"] = f"internal-event-{i}"
        record["semantics"]["fields"][5]["value"] = f"2026-11-12T01:00:0{i}Z"
    payload["rows"][2]["semantics"]["fields"][0].update(value="203.0.113.55", conflict=True)
    payload["observed_rows_in_bounded_fetch"] = 3
    original = copy.deepcopy(payload)
    ref = inputs.reference("artifact", identity, "observation", "$.rows.0.semantics.fields.4")
    prior["source_map"]["cited-query-identity"] = {"ref": ref, "alert_ids": [aid]}
    prior["analysis"]["questions"][0]["evidence_ids"].append("cited-query-identity")
    other = {"id": str(uuid4()), "schema_version": inputs.EVIDENCE_SCHEMA, "content_json": copy.deepcopy(payload)}
    other["content_json"].update(rows=[copy.deepcopy(payload["rows"][0])], observed_rows_in_bounded_fetch=1)
    other["sha256"] = inputs.digest(other["content_json"])
    for stage in ("Deep", "C6"):
        compact = build(stage, prior, [other])
        assert compact["ready"], compact["reason"]
        text = compact["messages"][1]["content"]
        query = {r["id"]: r for r in compact["followup_boundary"]["records"] if r["block"] == "query"}
        shared = [g for g in compact["followup_boundary"]["presentation"]["groups"]
                  if len(g) == 3 and all(s in query for s in g)]
        command = next(g for g in shared if query[g[0]]["value"]["name"] == "process_command_line")
        assert {query[s]["record_key"] for s in command} == {"Q1R0", "Q1R1", "Q1R2"}
        assert text.count("synthetic repeated command with original arguments") == 2  # Queries remain separate.
        assert "internal-event-0" in text and "internal-event-1" not in text and "internal-event-2" not in text
        assert "203.0.113.55" in text and all(f"2026-11-12T01:00:0{i}Z" in text for i in range(3))
        assert "custom_matches=[]" in text and "bytes_out=0" in text and "is_approved=false" in text
        assert all(f"[{s}] {query[s]['record_key']}" in text for s in command)
        for sid, row in query.items():
            source = compact["source_map"][sid]
            stored = payload if source["ref"]["id"] == identity else other["content_json"]
            assert inputs.path_value(stored, source["ref"]["source_path"])["value"] == row["value"]["value"]
            assert source["record_key"] == row["record_key"]
        assert all(d["visible_id"] for d in compact["followup_boundary"]["dependencies"])
    assert payload == original
    # A dependency restored without its query list must also retain a record key.
    registry = inputs.Sources(context, base, {other["id"]: other}, {}, field_selection=True)
    sid = registry.resolve({"ref": inputs.reference("artifact", other["id"], "observation", "$.rows.0.semantics.fields.4"),
                            "alert_ids": [aid]})
    assert registry.rows[0]["id"] == sid and registry.rows[0]["record_key"] == "Q1R0"


def test_deep_narrow_scope_restores_required_cross_member_source_without_relabeling(sample):
    context, base, prior = fixture(sample)
    aid, other = list(context.alerts)[:2]
    question = context.questions[0]
    question = question.model_copy(update={"scope": question.scope.model_copy(update={"alert_ids": [UUID(aid)]})})
    context = context.model_copy(update={"questions": [question, *context.questions[1:]]})
    source = next(sid for sid, row in base["source_map"].items() if row["alert_ids"] == [other] and row["ref"]["role"] == "observation")
    prior["analysis"]["questions"][0]["evidence_ids"] = [source]
    prior["analysis"]["questions"][1]["answer"] = "Unrelated question answer stays backstage."
    prepared = inputs.build("Deep", context, base, {}, previous=prior, prior_id=uuid4(), question_id=question.id)
    row = next(r for r in prepared["followup_boundary"]["records"] if r["block"] == "C3")
    sid = row["value"]["question"]["evidence_ids"][0]
    assert prepared["source_map"][sid]["alert_ids"] == [other]
    assert prepared["source_map"][sid]["ref"] == base["source_map"][source]["ref"]
    finding = row["value"]["findings"][0]
    assert finding["statement"] == prior["analysis"]["findings"][0]["statement"]
    assert finding["alert_ids"] == ["A1", "A2"] and finding["counter_ids"]
    assert "Unrelated question answer stays backstage." not in prepared["messages"][1]["content"]
    assert prepared["messages"][2]["content"] == "[可用调查工具]\n无可用查询候选。"
    assert all(aid in r["alert_ids"] or not r["alert_ids"] for r in prepared["followup_boundary"]["records"]
               if r["block"] == "base")


def test_knowledge_deduplication_task_selection_and_prior_dependency(sample):
    from app.socai2.baseline_context import Context
    from app.socai2.case_model_boundary import build
    from app.socai2.knowledge_model_input import choose

    context = Context.model_validate(sample["context"])
    aid, other = list(context.alerts)[:2]
    ident = str(uuid4())
    content = json.dumps({"name": "Example analytic", "description": "Original optional reference.",
        "x_mitre_platforms": ["Example platform"], "x_mitre_log_source_references": [
            {"x_mitre_data_component_ref": "internal-reference", "name": "Process events", "channel": "Creation"}],
        "x_mitre_mutable_elements": [{"field": "CommandLine", "description": "Compare parent process and output."}],
        "conditions": {"count": 0, "enabled": False, "exceptions": []}})
    row = {"record_id": "doc", "object_key": "knowledge:test", "namespace": "test", "content_sha256": "version1", "purpose": "technical_explanation",
           "purpose_label": "技术解释", "use": "解释而非证据", "query_alert_ids": [other],
           "record": {"id": "doc", "content": content}}
    body = {"tool_name": "knowledge", "state": "completed", "rows": [row, copy.deepcopy(row)],
            "returned_rows": 2, "truncated": False, "actual_args": {"scope": {"alert_ids": [aid, other]},
                "parameters": {"selectors": [{"object_key": "knowledge:test", "namespace": "test", "alert_ids": [other]}]}}}
    base = build(context, sample["context_id"], [(ident, body, None)], [], sample["materials"])
    knowledge = [r for r in base["input_ledger"]["records"] if r.get("knowledge")]
    assert len(knowledge) == 1
    assert len(knowledge[0]["knowledge"]["origins"]) == 2
    assert body["rows"][0] == row  # saved retrieval is unchanged
    selected_text = knowledge[0]["value"]["record"]["content"]
    assert "Original optional reference." in selected_text and "Compare parent process and output." in selected_text
    assert "internal-reference" not in selected_text
    assert '"count":0' in selected_text and '"enabled":false' in selected_text and '"exceptions":[]' in selected_text
    final = inputs.build("C6", context, base, {})
    assert final["ready"], final["reason"]
    final_knowledge = [r for r in final["followup_boundary"]["records"] if r.get("knowledge")]
    assert final_knowledge[0]["value"]["record"]["content"] == selected_text
    assert any(o["reason"] == "duplicate_knowledge_version" for o in base["omissions"])
    question = next(q for q in context.questions if q.id != "coverage")
    question = question.model_copy(update={"scope": question.scope.model_copy(update={"alert_ids": [UUID(aid)]})})
    context = context.model_copy(update={"questions": [question if q.id == question.id else q for q in context.questions]})
    excluded = inputs.build("Deep", context, base, {}, question_id=question.id)
    assert not any(r.get("knowledge") for r in excluded["followup_boundary"]["records"])
    answer = answer_for(base, context)
    answer["questions"][0]["evidence_ids"] = [knowledge[0]["id"]]
    prior = {"analysis": json.loads(case_output_adapter.restore(json.dumps(answer), base["case_boundary"])),
             "source_map": base["source_map"], "validation": "structure_scope_sources_checked"}
    restored = inputs.build("Deep", context, base, {}, previous=prior, prior_id=uuid4(), question_id=question.id)
    refs = [r for r in restored["followup_boundary"]["records"] if r.get("knowledge")]
    assert len(refs) == 1 and refs[0]["block"] == "dependency"
    assert refs[0]["ref"] == knowledge[0]["ref"]
    assert refs[0]["value"] == knowledge[0]["value"]
    # An unprojected complete JSON card can also be restored repeatedly by a
    # follow-up dependency without changing its identity or conflicting values.
    registry = inputs.Sources(context, base, {}, {})
    unprojected = copy.deepcopy(knowledge[0]["value"])
    unprojected["record"]["content"] = content
    original = knowledge[0]
    from app.socai2.case_source_scope import metadata
    sid = registry.add(original["ref"], unprojected, original["alert_ids"], "dependency",
                       original=original["original_value"], **metadata(original))
    assert registry.add(original["ref"], unprojected, original["alert_ids"], "dependency",
                        original=original["original_value"], **metadata(original)) == sid
    assert registry.rows[0]["value"] == original["value"]
    from app.socai2.knowledge_content import project_content
    unrepresentable = {"record": {"content": content[:-1] + ',"number":1e400}'}}
    assert project_content(unrepresentable, base_tests.runtime_policy.active_policy().case_io.config,
                           [], "unrepresentable") == unrepresentable
    policy = {"stage_max_characters": {"C3": 1, "Deep": 10000},
              "stage_purposes": {"C3": ["technical_explanation"], "Deep": ["investigation_guidance", "historical_case_reference"]}}
    selected, omissions = choose(knowledge, "C3", [other], policy)
    assert not selected and omissions[0]["reason"] == "knowledge_optional_budget"
    selected, omissions = choose(knowledge, "Deep", [other], policy)
    assert not selected and omissions[0]["reason"] == "knowledge_purpose_not_for_stage"
    mixed = copy.deepcopy(knowledge)
    mixed[0]["knowledge"]["origins"][1].update(purpose="investigation_guidance", query_alert_ids=[aid])
    selected, omissions = choose(mixed, "Deep", [other], policy)
    assert not selected and omissions[0]["reason"] == "knowledge_outside_task_scope"
    selected, omissions = choose(mixed, "Deep", [aid], policy)
    assert selected == mixed and not omissions


def test_knowledge_context_survives_c3_c6_but_cannot_cover_current_members(sample):
    from app.socai2.baseline_context import Context
    from app.socai2.case_model_boundary import build

    context = Context.model_validate(sample["context"])
    aid, other = list(context.alerts)[:2]
    historical = str(uuid4())
    row = {"record_id": "history-card", "object_key": "knowledge:history", "namespace": "test",
           "content_sha256": "version1", "purpose": "historical_case_reference", "query_alert_ids": [aid],
           "record": {"history": {"source": {"alert_id": historical}}, "content": "Historical comparison only.",
                      "triage": {"alert_id": historical, "summary": "Historical judgment only."},
                      "feedback": {"alert_id": historical, "summary": "Historical statement only."}}}
    body = {"tool_name": "knowledge", "state": "completed", "rows": [row], "returned_rows": 1,
            "truncated": False, "actual_args": {"scope": {"alert_ids": [aid]}, "parameters": {"selectors": [
                {"object_key": "knowledge:history", "namespace": "test", "alert_ids": [aid]}]}}}
    base = build(context, sample["context_id"], [(str(uuid4()), body, None)], [], sample["materials"])
    knowledge = [sid for sid, source in base["source_map"].items() if source.get("knowledge")]
    assert {base["source_map"][sid]["ref"]["role"] for sid in knowledge} == {
        "source_label", "prior_analysis", "human_statement"}
    assert all(base["source_map"][sid]["alert_ids"] == [] for sid in knowledge)
    assert all(base["source_map"][sid]["record_alert_ids"] == [historical] for sid in knowledge)
    answer = answer_for(base, context)
    answer["members"][0]["evidence_ids"].extend(knowledge)
    raw = json.dumps(answer)
    accepted = case_output_adapter.parse(raw, base, context, {})
    review = case_output_adapter.CaseReview(base, context, {})
    assert review.feedback(raw) is None
    assert review.partial(raw).members[0].evidence_ids == accepted.members[0].evidence_ids

    wrong_member = copy.deepcopy(answer)
    wrong_member["members"][1]["evidence_ids"].append(knowledge[0])
    with pytest.raises(AnalysisRejected, match="source_member_mismatch"):
        case_output_adapter.parse(json.dumps(wrong_member), base, context, {})
    assert any(e["code"] == "source_member_mismatch" for e in review.feedback(json.dumps(wrong_member))["errors"])
    assert other != aid
    for sid in knowledge:
        only_knowledge = copy.deepcopy(answer)
        only_knowledge["members"][0]["evidence_ids"] = [sid]
        with pytest.raises(AnalysisRejected, match="member_source_coverage_missing"):
            case_output_adapter.parse(json.dumps(only_knowledge), base, context, {})
        assert any(e["code"] == "member_source_coverage_missing"
                   for e in review.feedback(json.dumps(only_knowledge))["errors"])

    previous = {"analysis": accepted.model_dump(mode="json"), "source_map": base["source_map"],
                "validation": "structure_scope_sources_checked"}
    prepared = inputs.build("C6", context, base, {}, previous=previous, prior_id=uuid4())
    refs = [sid for sid, source in prepared["source_map"].items() if source.get("knowledge")]
    assert len(refs) == len(knowledge)
    comparison = {"state": "initial", "result_id": None}
    final = final_answer(prepared, context, comparison)
    final["analysis"]["members"][0]["evidence_ids"].extend(refs)
    final["conclusion"]["support_ids"].extend(refs)
    outputs.parse_final(json.dumps(final), prepared, context, comparison)
    assert outputs.FinalReview(prepared, context, comparison).feedback(json.dumps(final)) is None
    wrong_final = copy.deepcopy(final)
    wrong_final["conclusion"].update(alert_ids=[prepared["case_boundary"]["member_aliases"][other]],
        support_ids=wrong_final["analysis"]["members"][1]["evidence_ids"] + refs)
    with pytest.raises(AnalysisRejected, match="source_member_mismatch"):
        outputs.parse_final(json.dumps(wrong_final), prepared, context, comparison)
    errors = outputs.FinalReview(prepared, context, comparison).feedback(json.dumps(wrong_final))["errors"]
    assert any(e["path"] == ["conclusion", "support_ids"] and e["code"] == "source_member_mismatch" for e in errors)
    # Even query-bound knowledge cannot satisfy final coverage (including an uncertain conclusion).
    for sid in refs:
        prepared["source_map"][sid]["alert_ids"] = [aid]
    final["conclusion"].update(alert_ids=[prepared["case_boundary"]["member_aliases"][aid]], support_ids=refs)
    with pytest.raises(AnalysisRejected, match="delivery_source_coverage_missing"):
        outputs.parse_final(json.dumps(final), prepared, context, comparison)
    errors = outputs.FinalReview(prepared, context, comparison).feedback(json.dumps(final))["errors"]
    assert any(e["path"] == ["conclusion", "support_ids"] and e["uncovered_members"] == ["A1"] for e in errors)


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


def test_history_duplicate_presentation_preserves_c3_and_final_dependencies(sample):
    row = next(row for alert in sample["context"]["alerts"].values() for row in alert["queries"]
               if row["content_json"]["tool_name"] == "history" and row["content_json"].get("rows"))
    body = row["content_json"]
    original = copy.deepcopy(body["rows"][0])
    duplicate = copy.deepcopy(original)
    duplicate["object_key"] = "same-record-another-object"
    body.update(rows=[original, duplicate], returned_rows=2)
    row.update(sha256=digest(body), size_bytes=len(encoded(body)))
    sample["context"]["citation_roles"].update(base_tests.queries.roles(sample["context"]))
    context, base = prepared_sample(sample)
    selected = [r for r in base["input_ledger"]["records"] if r.get("original_reference", {}).get("id") == row["id"]
                and (r["original_reference"]["source_path"] or "").count(".") == 2]
    assert len(selected) == 2 and selected[0]["id"] != selected[1]["id"]
    assert "[" + ",".join(r["id"] for r in selected) + "]" in base["messages"][1]["content"]
    final = inputs.build("C6", context, base, {})
    assert final["ready"]
    refs = [r["ref"] for r in selected]
    finals = [r for r in final["followup_boundary"]["records"] if r["ref"] in refs]
    assert len(finals) == 2
    assert "[" + ",".join(r["id"] for r in finals) + "]" in final["messages"][1]["content"]
    assert all(r["id"] in final["source_map"] for r in finals)
    assert body["returned_rows"] == 2 and body["rows"] == [original, duplicate]


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


def test_case_message_guard_checks_actual_text_and_all_windows():
    from app.socai2.baseline_model_view import blocked, blocked_message
    text = '"ordinary business text"\n' * 2300
    assert len(text) < 60000 < len(encoded(text).decode())
    assert blocked(text) and not blocked_message(text)
    assert blocked_message('a' * 60001)
    assert blocked_message('a' * 4500 + ' password="synthetic_not_a_real_password"')


def test_final_shared_display_keeps_sources_and_query_limits_in_backend(sample):
    context, base, prior = fixture(sample)
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    records = {r["id"]: r for r in prepared["followup_boundary"]["records"]}
    presentation = prepared["followup_boundary"]["presentation"]
    ids = [sid for group in presentation["groups"] for sid in group]
    assert len(ids) == len(set(ids)) and set(ids) == set(prepared["source_map"])
    assert any(len(group) > 1 and records[group[0]]["ref"]["type"] == "alert_material" for group in presentation["groups"])
    assert all(records[sid]["block"] == "graph" for item in presentation["shared_fields"] for sid in item["applies_to"])
    lines = prepared["messages"][1]["content"].splitlines()
    for sid, row in records.items():
        if row["ref"]["role"] != "execution_receipt":
            continue
        line = next(line for line in lines if line.startswith(f"[{sid}] "))
        assert not any(word in line for word in ("查询范围", "限制", "返回上限", "截断", "原因"))
        if row["value"].get("state") == "skipped":
            assert line == f"[{sid}] 威胁情报：未查询"
            assert row["value"]["reason"] == "no_supported_frozen_objects"
    for item in presentation["shared_fields"]:
        assert all(records[sid]["value"][item["field"]] == item["value"] for sid in item["applies_to"])
        assert all(text in prepared["messages"][1]["content"] for text in item["value"])


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
