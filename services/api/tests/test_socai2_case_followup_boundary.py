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
    original = json.loads(case_output_adapter.restore_current(json.dumps(answer), base["case_boundary"]))
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
    if outputs.restored_comparison(prepared, comparison) is None:
        result["comparison"] = {"kind": "not_comparable", "summary": "No selected comparison.", "support_ids": []}
    return result


def background_query_example(context):
    """Synthetic nonempty rows matching the four current background contracts."""
    from app.socai2.baseline_enrichment import citation_roles

    stamp = "2026-11-13T01:00:00+00:00"
    records = {
        "assets": {"name": "example-host", "criticality": "high", "ip_addresses": ["192.0.2.10"],
                   "first_seen": stamp, "last_seen": stamp},
        "threat_intel": {"ioc_type": "ip", "value": "192.0.2.20", "severity": "medium",
                        "source": "Synthetic intelligence", "source_ref": "example-ioc-1", "last_seen": stamp,
                        "confidence_provenance": "stored_score_calculation_unverified"},
        "ueba": {"profile_id": "internal-profile", "external_user_ref": "example-user", "risk_score": 0,
                 "risk_tier": "low", "failed_auth_24h": 0, "last_evaluated_at": stamp,
                 "score_provenance": "stored_prior_analysis_calculation_unverified"},
        "graph": {"account": "example-user", "provider": "example-provider", "employee": "Example Analyst",
                  "department": "Operations", "is_active": False, "employee_linked": True, "start_date": "2026-01-01",
                  "relationship_source": {"employee_identity": "AUTHENTICATES_AS"},
                  "imported_at": stamp, "imported_at_status": "native", "imported_at_raw_sha256": "internal-hash"},
    }
    result = []
    for index, (tool, record) in enumerate(records.items(), 1):
        # Same names at other business paths must not be scrubbed recursively.
        record["extension"] = {"match_basis": "Original business statement.", "profile_id": "business-profile",
                               "imported_at": "Business import event.", "count": 0, "enabled": False, "items": []}
        selector = {"object_key": "synthetic:" + tool, "namespace": "synthetic-example",
                    "alert_ids": sorted(context.alerts)}
        body = {"tool_name": tool, "state": "completed", "returned_rows": 1, "truncated": False,
                "actual_args": {"scope": context.scope.model_dump(mode="json"), "parameters": {"selectors": [selector]}},
                "rows": [{"object_key": selector["object_key"], "namespace": selector["namespace"],
                          "record_id": str(UUID(int=index)), "match_basis": "exact_match", "record": record}]}
        if tool == "threat_intel":
            other = copy.deepcopy(body["rows"][0])
            other["record"]["confidence_provenance"] = "Original source-specific qualification."
            body["rows"].append(other)
            body["returned_rows"] = 2
        result.append((str(UUID(int=1000 + index)), body, citation_roles(body)))
    return result


def test_background_query_business_rows_keep_values_and_refs_across_stages(sample):
    from app.socai2.baseline_context import Context

    context = Context.model_validate(sample["context"])
    enrichment = background_query_example(context)
    original = copy.deepcopy(enrichment)
    base = base_tests.boundary.build(context, sample["context_id"], enrichment, [], sample["materials"])
    assert base["ready"], base["reason"]
    identities = {identity for identity, _, _ in enrichment}
    query_rows = [r for r in base["input_ledger"]["records"] if r["ref"]["id"] in identities
                  and r["ref"]["source_path"]]
    assert len(query_rows) == 5
    answer = answer_for(base, context)
    answer["questions"][0]["evidence_ids"] = [r["id"] for r in query_rows]
    prior = {"analysis": json.loads(case_output_adapter.restore_current(json.dumps(answer), base["case_boundary"])),
             "source_map": base["source_map"], "validation": "structure_scope_sources_checked"}
    stages = [(base, "input_ledger")]
    for stage in ("Deep", "C6"):
        prepared = inputs.build(stage, context, base, {}, previous=prior, prior_id=UUID(int=2000),
                                question_id=context.questions[0].id if stage == "Deep" else None)
        assert prepared["ready"], prepared["reason"]
        stages.append((prepared, "followup_boundary"))
    for prepared, ledger in stages:
        for row in query_rows:
            current = next(r for r in prepared[ledger]["records"] if r["ref"] == row["ref"])
            body = next(body for identity, body, _ in enrichment if identity == row["ref"]["id"])
            raw = body["rows"][int(row["ref"]["source_path"].rsplit(".", 1)[-1])]
            value = current["value"]
            assert "match_basis" not in value and row["original_value"] == raw
            record = value["record"]
            assert record["extension"] == raw["record"]["extension"]
            assert "[" + current["id"] + "]" in prepared["messages"][1]["content"]
            assert prepared["source_map"][current["id"]]["ref"] == row["ref"]
            assert current["alert_ids"] == row["alert_ids"]
            if body["tool_name"] == "ueba":
                assert "profile_id" not in record and "score_provenance" not in record
                assert record["risk_score"] == record["failed_auth_24h"] == 0
                assert record["last_evaluated_at"] == raw["record"]["last_evaluated_at"]
                assert current["ref"]["role"] == "prior_analysis"
            elif body["tool_name"] == "graph":
                assert not set(record) & {"imported_at", "imported_at_status", "imported_at_raw_sha256"}
                assert record["is_active"] is False and record["employee_linked"] is True
                assert record["start_date"] == raw["record"]["start_date"]
            elif body["tool_name"] == "threat_intel":
                assert record["source_ref"] == raw["record"]["source_ref"]
                assert record.get("confidence_provenance") == (None if row["ref"]["source_path"].endswith(".0")
                    else "Original source-specific qualification.")
            else:
                assert record == raw["record"]
    assert enrichment == original


def test_final_selects_prior_and_preserves_support_counter_dependencies(sample):
    context, base, prior = fixture(sample)
    evidence = next(r for r in base["input_ledger"]["records"] if r["ref"]["role"] == "observation")
    triage = next(r for r in base["input_ledger"]["records"] if r["block"] == "triage")
    triage["value"]["source_refs"] = [evidence["id"]]
    triage["original_value"]["source_refs"] = [evidence["ref"]]
    incident = next(r for r in base["input_ledger"]["records"] if r["block"] == "incident")
    incident["prior_reference_resolution"] = {"visible": [evidence["id"]], "not_visible": []}
    incident["incident_source_refs"] = [evidence["ref"]]
    old_finding = next(r for r in base["input_ledger"]["records"] if r["block"] == "finding")
    prior["analysis"]["questions"][0]["evidence_ids"] += [triage["id"], incident["id"], old_finding["id"]]
    history_values = [{"text": "Independent human denial of authorization."},
                      {"record": {"approved": False, "attempts": 0, "exceptions": []}}]
    for i, (role, value) in enumerate(zip(("human_statement", "source_label"), history_values, strict=True)):
        sid = f"history_{i}"
        row = {"id": sid, "ref": inputs.reference("artifact", uuid4(), role, "$.rows.0"),
               "value": value, "original_value": copy.deepcopy(value), "alert_ids": [], "block": "query",
               "membership_basis": "history_record_outside_case", "record_alert_ids": [str(uuid4())]}
        base["input_ledger"]["records"].append(row)
        base["source_map"][sid] = {"ref": row["ref"], "alert_ids": []}
    before = copy.deepcopy((base, prior))
    graph_id = str(uuid4())
    graphs = [{"source": {"ref": inputs.reference("artifact", graph_id, "prior_analysis", f"$.edges.{i}"),
                          "alert_ids": evidence["alert_ids"]}, "entry": {"value": {"relation": relation}},
               "original": {"relation": relation}} for i, relation in enumerate(("source_reports_object", "reported_network_activity"))]
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4(), graphs=graphs)
    assert prepared["ready"], prepared["reason"]
    rows = prepared["followup_boundary"]["records"]
    previous = next(r for r in rows if r["block"] == "C3")
    assert set(previous["value"]) == set(prior["analysis"]) - {"members", "domains"}
    assert previous["value"]["summary"] == prior["analysis"]["summary"]
    assert [q["id"] for q in previous["value"]["questions"]] == [q["id"] for q in prior["analysis"]["questions"] if q["id"] != "coverage"]
    finding = previous["value"]["findings"][0]
    assert finding["alert_ids"] == ["A1", "A2"]
    assert finding["support_ids"] and finding["counter_ids"]
    assert all(d["visible_id"] in prepared["source_map"] for d in prepared["followup_boundary"]["dependencies"])
    assert not set(base["source_map"]) & set(prepared["source_map"])
    assert (base, prior) == before
    assert len({r["ref"]["source_path"] for r in rows if ".diagnosis.findings." in (r["ref"]["source_path"] or "")}) == 1
    assert len({r["ref"]["source_path"].split(".content_json")[0] for r in rows if ".queries." in (r["ref"]["source_path"] or "")}) == 9
    current_triage = next(r for r in rows if r["ref"] == triage["ref"])
    current_incident = next(r for r in rows if r["ref"] == incident["ref"])
    for sid in [*current_triage["value"]["source_refs"], *current_incident["prior_reference_resolution"]["visible"]]:
        assert prepared["source_map"][sid]["ref"] == evidence["ref"]
    for current in rows:
        if "original_scope" in current:
            old = next(r for r in base["input_ledger"]["records"] if r["ref"] == current["ref"])
            assert prepared["source_map"][current["id"]]["original_scope"] == old["original_scope"]
    assert [r["value"]["relation"] for r in rows if r["block"] == "graph"] == ["reported_network_activity"]
    assert len([r for r in rows if r["ref"] == triage["ref"]]) == 1
    assert any(o["reason"] == "c6_prior_context_dependency_only" for o in prepared["omissions"])
    assert all(any(r["value"] == value for r in rows) for value in history_values)
    # The selected request remains a serializable frozen artifact; its sources
    # also support the unchanged final-result restoration contract.
    frozen = json.loads(json.dumps(prepared))
    comparison = {"state": "initial", "result_id": None}
    outputs.parse_final(json.dumps(final_answer(frozen, context, comparison)), frozen, context, comparison)
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


@pytest.mark.parametrize("state", ["initial", "not_selected", "unavailable"])
def test_final_restores_original_contract_without_model_owned_known_fields(sample, state):
    context, base, prior = fixture(sample)
    comparison = {"state": state, "result_id": str(uuid4()) if state == "unavailable" else None}
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4(), extra={"comparison": comparison})
    answer = final_answer(prepared, context, comparison)
    schema = outputs.final_format(prepared, context, comparison)["json_schema"]["schema"]
    assert "id" not in schema["$defs"]["Recommendation"]["properties"]
    assert "comparison" not in schema["properties"] and "comparison" not in schema["required"]
    assert prepared["case_boundary"]["fixed_comparison"]["selection"] == comparison
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
    assert value.comparison.model_dump() == prepared["case_boundary"]["fixed_comparison"]["value"]
    forged = copy.deepcopy(answer)
    forged["comparison"] = {"kind": "unchanged", "summary": "Invented comparison.", "support_ids": []}
    assert list(Draft202012Validator(schema).iter_errors(forged))
    with pytest.raises(AnalysisRejected, match="final_boundary_shape_or_alias_invalid"):
        outputs.parse_final(json.dumps(forged), prepared, context, comparison)
    if state != "initial":
        old_prepared = copy.deepcopy(prepared)
        old_prepared["case_boundary"].pop("fixed_comparison")
        old_answer = final_answer(old_prepared, context, comparison)
        old_schema = outputs.final_format(old_prepared, context, comparison)["json_schema"]["schema"]
        outputs.parse_final(json.dumps(old_answer), old_prepared, context, comparison)
        for field, invalid_value in (("kind", "unchanged"), ("summary", None)):
            invalid = copy.deepcopy(old_answer)
            invalid["comparison"][field] = invalid_value
            original = json.dumps(invalid)
            assert list(Draft202012Validator(old_schema).iter_errors(invalid))
            with pytest.raises(AnalysisRejected, match="comparison_not_available"):
                outputs.parse_final(original, old_prepared, context, comparison)
            review = outputs.FinalReview(old_prepared, context, comparison)
            diagnostic = review.feedback(original)
            assert len(diagnostic["errors"]) == 1
            error = diagnostic["errors"][0]
            assert error["path"] == ["comparison", field]
            assert error["code"] == "comparison_not_available" and error["comparison_state"] == state
            assert error["current_values"] == invalid_value
            assert diagnostic["allowed_sources"] == diagnostic["local_findings"] == []
            assert review.partial(original) is None and review.details["conclusion_adoptable"] is False
            assert original == json.dumps(invalid)


def test_final_feedback_and_partial_review_still_use_model_aliases(sample):
    context, base, prior = fixture(sample)
    comparison = {"state": "initial", "result_id": None}
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4())
    answer = final_answer(prepared, context, comparison)
    duplicate = copy.deepcopy(answer)
    refs = duplicate["recommendations"][0]["source_ids"]
    refs.append(refs[0])
    original = json.dumps(duplicate)
    review = outputs.FinalReview(prepared, context, comparison)
    feedback = review.feedback(original)
    assert feedback["errors"] == [{"path": ["recommendations", 0, "source_ids"], "code": "duplicate_source",
        "subject_id": None, "duplicate_ids": [refs[0]], "current_values": refs}]
    assert feedback["allowed_sources"] == feedback["local_findings"] == feedback["observed_support_ids"] == []
    assert json.dumps(duplicate) == original
    with pytest.raises(AnalysisRejected, match="delivery_source_not_visible_or_duplicate"):
        outputs.parse_final(original, prepared, context, comparison)
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

    # Final coverage errors get only the missing members' eligible candidates.
    final = final_answer(prepared, context, comparison)
    final["impact"].update(alert_ids=list(prepared["case_boundary"]["member_aliases"].values()), support_ids=[])
    original = json.dumps(final)
    with pytest.raises(AnalysisRejected, match="delivery_source_coverage_missing"):
        outputs.parse_final(original, prepared, context, comparison)
    diagnostic = outputs.FinalReview(prepared, context, comparison).feedback(original)
    assert diagnostic["allowed_sources"] == diagnostic["local_findings"] == []
    error = diagnostic["errors"][0]
    assert error["path"] == ["impact", "support_ids"] and error["current_values"] == []
    assert error["declared_members"] == error["uncovered_members"] == final["impact"]["alert_ids"]
    assert error["claim"] == final["impact"]["summary"]
    for alias, roles in error["candidate_source_ids_by_member_role"].items():
        aid = next(a for a, name in prepared["case_boundary"]["member_aliases"].items() if name == alias)
        for role, ids in roles.items():
            assert role != "execution_receipt"
            assert all(aid in prepared["source_map"][sid]["alert_ids"] and not prepared["source_map"][sid].get("knowledge")
                       and prepared["source_map"][sid]["ref"]["role"] == role for sid in ids)
    assert json.dumps(final) == original
    final["analysis"]["members"][0].update(state="analyzed", evidence_ids=[])
    mixed = outputs.FinalReview(prepared, context, comparison).feedback(json.dumps(final))
    assert mixed["allowed_sources"] and len(mixed["errors"]) > 1


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
    visible = {encoded(r["ref"]) for r in prepared["followup_boundary"]["records"]}
    assert all(encoded(r["ref"]) in visible for r in base["input_ledger"]["records"]
               if r["block"] in {"triage", "incident", "finding", "question"})
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
    fields[1]["transform"] = "numeric_conversion"
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
    assert rows[1]["value"]["value"] == 443 and all("transform" not in r["value"] for r in rows)
    assert payload["rows"][0]["semantics"]["fields"][1]["transform"] == "numeric_conversion"
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
    prior = {"analysis": json.loads(case_output_adapter.restore_current(json.dumps(answer), base["case_boundary"])),
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
    # The same-member guide is optional for authorization, but a selected
    # prior citation still carries its exact source into that question.
    guided = copy.deepcopy(body)
    guided["rows"][1].update(purpose="investigation_guidance", purpose_label="取证指导")
    guided_base = build(context, sample["context_id"], [(ident, guided, None)], [], sample["materials"])
    card = next(r for r in guided_base["input_ledger"]["records"] if r.get("knowledge"))
    authorization = inputs.build("Deep", context, guided_base, {}, question_id="authorization")
    assert authorization["ready"], authorization["reason"]
    assert not any(r.get("knowledge") for r in authorization["followup_boundary"]["records"])
    assert any(o["reason"] == "knowledge_purpose_not_for_question" for o in authorization["omissions"])
    nature = inputs.build("Deep", context, guided_base, {}, question_id="behavior_nature")
    assert any(r.get("knowledge") for r in nature["followup_boundary"]["records"])
    answer = answer_for(guided_base, context)
    next(q for q in answer["questions"] if q["id"] == "authorization")["evidence_ids"] = [card["id"]]
    prior = {"analysis": json.loads(case_output_adapter.restore_current(json.dumps(answer), guided_base["case_boundary"])),
             "source_map": guided_base["source_map"], "validation": "structure_scope_sources_checked"}
    required = inputs.build("Deep", context, guided_base, {}, previous=prior, prior_id=uuid4(), question_id="authorization")
    actual = next(r for r in required["followup_boundary"]["records"] if r.get("knowledge"))
    assert actual["block"] == "dependency" and actual["ref"] == card["ref"]
    assert actual["value"] == card["value"] and actual["alert_ids"] == card["alert_ids"]
    assert not any(o["reason"] == "knowledge_purpose_not_for_question" for o in required["omissions"])
    # Final synthesis must match purpose and members on the same open question.
    final_answer = answer_for(guided_base, context)
    for item in final_answer["questions"]:
        item["state"] = "unresolved" if item["id"] == "authorization" else "not_applicable"

    def final_for(selected_context):
        previous = {"analysis": json.loads(case_output_adapter.restore_current(json.dumps(final_answer), guided_base["case_boundary"])),
                    "source_map": guided_base["source_map"], "validation": "structure_scope_sources_checked"}
        prepared = inputs.build("C6", selected_context, guided_base, {}, previous=previous, prior_id=uuid4())
        assert prepared["ready"], prepared["reason"]
        return [r for r in prepared["followup_boundary"]["records"] if r.get("knowledge")]

    assert final_for(context) == []  # Matching authorization members alone are insufficient.
    nature_question = next(q for q in final_answer["questions"] if q["id"] == "behavior_nature")
    nature_question["state"] = "unresolved"
    assert final_for(context)[0]["value"] == card["value"]
    narrow = context.model_copy(update={"questions": [
        q.model_copy(update={"scope": q.scope.model_copy(update={"alert_ids": [UUID(aid)]})})
        if q.id == "behavior_nature" else q for q in context.questions]})
    assert final_for(narrow) == []  # Do not borrow the other member from authorization.
    nature_question["state"] = "not_applicable"
    next(q for q in final_answer["questions"] if q["id"] == "authorization")["evidence_ids"] = [card["id"]]
    required_card = final_for(context)[0]
    assert required_card["block"] == "dependency" and required_card["ref"] == card["ref"]
    assert required_card["value"] == card["value"] and required_card["alert_ids"] == card["alert_ids"]
    legacy = copy.deepcopy(base_tests.runtime_policy.active_policy().case_io.config["knowledge_selection"])
    legacy.pop("final_question_purposes")
    selected, omissions = choose([card], "C6", [other], legacy, question_scopes={"authorization": [other]})
    assert selected == [card] and not omissions


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
    aid = next(iter(context.alerts))
    graph_value = {"relation": "reported_parent_process", "from": "parent", "to": "child", "strength": "observed",
                   "limitations": ["external_topology_not_queried", "derived_view_not_independent_evidence"]}
    graphs = [{"original": graph_value, "entry": {"value": graph_value}, "source": {
        "ref": inputs.reference("artifact", uuid4(), "prior_analysis", "$.edges.0"), "alert_ids": [aid]}}]
    prepared = inputs.build("C6", context, base, {}, previous=prior, prior_id=uuid4(), graphs=graphs)
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
    graph = next(r for r in records.values() if r["block"] == "graph")
    assert graph["value"] == {k: v for k, v in graph_value.items() if k != "limitations"}
    assert graph["ref"]["role"] == "prior_analysis" and graph["alert_ids"] == [aid]
    assert graph_value["limitations"] == ["external_topology_not_queried", "derived_view_not_independent_evidence"]
    assert "execution_receipt" not in prepared["messages"][1]["content"]
    assert "completed/empty/0" not in prepared["messages"][0]["content"]
    options = [{"binding_id": "B1", "tool_name": "process_activity", "hostname": "synthetic-host",
                "alert_ids": [aid], "object_keys": []}]
    c3_base = copy.deepcopy(base)
    c3_messages, _ = base_tests.boundary.messages(c3_base, context, options)
    deep = inputs.build("Deep", context, base, {}, previous=prior, prior_id=uuid4(),
                        question_id="detection_facts", options=options)
    assert deep["ready"]
    for messages, tool_view in ((c3_messages, c3_base["tool_presentation"]), (deep["messages"], deep["tool_presentation"])):
        menu = messages[2]["content"]
        assert all(text in menu for text in ("绑定=B1", "synthetic-host", "process_activity", "不能回答="))
        assert not any(text in menu for text in ("共同限制", "schema_version", "选择原则", "可用=true", "使用范围=", "返回字段="))
        assert all(cap["inputs"] and cap["limitations"] and cap["returned_fields"] for cap in tool_view["capabilities"])
        assert any(row.get("reason") == "tool_execution_limits_kept_in_backend" for row in tool_view["ledger"])


def test_historical_comparison_keeps_old_scope_without_offering_historical_targets(sample):
    aid, removed, rid = next(iter(sample["context"]["alerts"])), str(uuid4()), str(uuid4())
    comparison = {"state": "eligible", "result_id": rid, "added_alert_ids": [], "removed_alert_ids": [removed],
        "shared_alert_ids": [aid], "prior_scope": {"kind": "whole_case", "alert_ids": [aid, removed],
            "object_keys": ["host:previous-only"], "window_start": "2026-10-01T00:00:00Z", "window_end": "2026-10-01T01:00:00Z"}}
    value = {"comparison_result_id": rid, "validation_state": "accepted", "delivery_state": "complete",
             "conclusion_state": "uncertain", "conclusion_origin": "model", "conclusion": "Old judgment unchanged."}
    historical_ref = inputs.reference("artifact", uuid4(), "observation")
    old = {**value, "id": rid, "member_deliveries": [{"alert_id": aid}, {"alert_id": removed}],
           "findings": [{"id": "historical-internal-finding", "state": "inferred",
               "statement": "Old N1_S1 suggested a shared session, without direct proof.",
               "scope": comparison["prior_scope"], "support": [historical_ref], "counterevidence": [],
               "limitations": ["Different sessions remain possible."], "business_extension": {"count": 0, "confirmed": False}}],
           "questions": [
               {"id": "authorization", "state": "unresolved", "answer": "No authorization was confirmed.",
                "scope": comparison["prior_scope"], "limitations": ["Absence of approval is not proof of malice."],
                "evidence_refs": [historical_ref]},
               {"id": "coverage", "state": "unresolved", "answer": "Old execution statistics are not a business question."},
               {"id": "detection_facts", "state": "answered", "answer": "Resolved old answer need not repeat the findings."}],
           "case_impact": {"summary": "Transfer was not established.", "supported_changes": [],
               "cannot_generalize": ["A connection does not establish a data transfer."],
               "affected_scope": comparison["prior_scope"], "next_steps": ["Old action must not become current advice."]},
           "operation_key": "internal-result-operation", "business_extension": {"count": 0, "approved": False, "exceptions": []}}
    sample["context"]["prior_results"][rid] = old
    sample["context"]["citation_roles"][f"$.prior_results.{rid}"] = "prior_analysis"
    context, base, prior = fixture(sample)
    base_row = next(r for r in base["input_ledger"]["records"] if r.get("context_identity") == rid)
    assert "comparison_basis" not in base_row["value"]
    assert old["findings"][0]["statement"] not in base["messages"][1]["content"]
    prior["analysis"]["questions"][0]["evidence_ids"].append(base_row["id"])
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
    assert "fixed_comparison" not in prepared["case_boundary"] and "comparison" in schema["properties"]
    assert "X1" not in schema["$defs"]["AlertId"]["enum"]
    assert "H1" not in schema["$defs"]["ObjectKey"]["enum"]
    assert "unchanged" in schema["$defs"]["Comparison"]["properties"]["kind"]["enum"]
    duplicates = [r for r in prepared["followup_boundary"]["records"] if r.get("context_identity") == rid]
    assert len(duplicates) == 2 and {r["ref"]["type"] for r in duplicates} == {"artifact", "result"}
    assert duplicates[0]["value"] == duplicates[1]["value"]
    assert text.count(value["conclusion"]) == 1
    assert "internal-result-operation" not in text
    assert text.count(old["findings"][0]["statement"]) == 1
    basis = row["value"]["comparison_basis"]
    assert basis["findings"][0]["scope"]["alert_ids"] == [prepared["case_boundary"]["member_aliases"][aid], "X1"]
    assert basis["findings"][0]["limitations"] == old["findings"][0]["limitations"]
    assert basis["findings"][0]["business_extension"] == {"count": 0, "confirmed": False}
    assert [q["id"] for q in basis["questions"]] == ["authorization"]
    assert basis["questions"][0]["answer"] == old["questions"][0]["answer"]
    assert basis["case_impact"]["supported_changes"] == []
    assert basis["case_impact"]["cannot_generalize"] == old["case_impact"]["cannot_generalize"]
    assert all(excluded not in text for excluded in (historical_ref["id"], "historical-internal-finding",
        old["questions"][1]["answer"], old["questions"][2]["answer"], old["case_impact"]["next_steps"][0]))
    assert context.prior_results[rid] == old
    assert row["value"]["business_extension"] == old["business_extension"]
    assert row["original_scope"]["alert_ids"] == sorted([aid, removed])
    background = next(r for r in duplicates if r["ref"]["type"] == "artifact")
    assert "指定比较基线引用=[" + row["id"] + "]" in text
    assert "[" + row["id"] + "]（同文历史背景引用：[" + background["id"] + "]）" in text
    assert "[" + ",".join(r["id"] for r in duplicates) + "]" not in text
    # The display distinguishes citation duties; it does not weaken acceptance.
    final = final_answer(prepared, context, comparison)
    current = final["analysis"]["members"][0]["evidence_ids"][0]
    final["comparison"] = {"kind": "unchanged", "summary": "Synthetic comparison.",
                           "support_ids": [background["id"], current]}
    original = json.dumps(final)
    with pytest.raises(AnalysisRejected, match="comparison_needs_selected_baseline_and_current_sources"):
        outputs.parse_final(original, prepared, context, comparison)
    final["recommendations"][0]["source_ids"] *= 2
    errors = outputs.FinalReview(prepared, context, comparison).feedback(json.dumps(final))["errors"]
    assert {e["code"] for e in errors} == {"duplicate_source", "comparison_needs_selected_baseline_and_current_sources"}
    error = next(e for e in errors if e["path"] == ["comparison", "support_ids"])
    assert error["selected_baseline_ids"] == [row["id"]] and error["selected_baseline_missing"]
    final["recommendations"][0]["source_ids"] = [current]
    final["comparison"]["support_ids"] = [row["id"]]
    error = outputs.FinalReview(prepared, context, comparison).feedback(json.dumps(final))["errors"][0]
    assert error["current_source_required"] and error["current_source_missing"] and not error["selected_baseline_missing"]
    final["comparison"]["support_ids"].append(current)
    assert outputs.parse_final(json.dumps(final), prepared, context, comparison).comparison.kind == "unchanged"
    assert outputs.FinalReview(prepared, context, comparison).feedback(json.dumps(final)) is None
    sample["context"]["prior_results"][rid]["validation_state"] = "rejected"
    _, rejected = prepared_sample(sample)
    assert not any(r.get("context_identity") == rid for r in rejected["input_ledger"]["records"])
    assert value["conclusion"] not in rejected["messages"][1]["content"]


def test_fixed_h_feedback_keeps_revision_scope_and_real_refs_in_c3_c6(sample):
    _, initial = prepared_sample(sample)
    evidence = next(r for r in initial["input_ledger"]["records"] if r["ref"]["type"] == "alert_material"
                    and r["ref"]["role"] == "observation")
    aid, tid, vid, older_id = evidence["alert_ids"][0], str(uuid4()), str(uuid4()), str(uuid4())
    raw = sample["context"]
    revision = {"id": vid, "task_id": tid, "revision": 2, "state": "completed",
        "title": "核对本次操作授权", "description": "保留业务反证，不作事实推断。",
        "result_text": "本次操作未得到业务授权；请核对审批记录。", "completed_by": "internal-user-id",
        "result_scope": {**raw["scope"], "alert_ids": [aid]},
        "source_refs": [evidence["ref"], inputs.reference("artifact", uuid4(), "observation")],
        "business_extension": {"count": 0, "authorized": False, "exceptions": []}}
    older = {**copy.deepcopy(revision), "id": older_id, "revision": 1, "result_text": "旧版本曾认为操作已获授权。"}
    raw["tasks"][tid] = {"task_id": tid, "revision": revision, "usable_feedback": True, "limitations": []}
    raw["adopted_task_revisions"].update({vid: copy.deepcopy(revision), older_id: older})
    raw["current_assessment"] = {"id": str(uuid4()), "conclusion": "当前采用判断仍需结合新反馈复核。",
        "origin": "human", "validity": "accepted", "reason": "复核原始材料",
        "formed_at": "2026-11-01T00:00:00Z", "adopted_by": "internal-adopter",
        "actor": {"user_id": "internal-actor"}, "operation_key": "internal-adoption-operation"}
    removed = str(uuid4())
    raw["assessment_members"] = [{"alert_id": aid}, {"alert_id": removed}]
    raw["citation_roles"]["$.current_assessment"] = "prior_analysis"
    raw["citation_roles"].update({f"$.tasks.{tid}.revision": "human_statement",
        f"$.adopted_task_revisions.{vid}": "human_statement", f"$.adopted_task_revisions.{older_id}": "human_statement"})
    before = copy.deepcopy(raw)
    context, base = prepared_sample(sample)
    analysis = json.loads(case_output_adapter.restore_current(json.dumps(answer_for(base, context)), base["case_boundary"]))
    final = inputs.build("C6", context, base, {}, previous={"analysis": analysis,
        "source_map": base["source_map"], "validation": "structure_scope_sources_checked"}, prior_id=uuid4())
    deep = inputs.build("Deep", context, base, {}, previous={"analysis": analysis,
        "source_map": base["source_map"], "validation": "structure_scope_sources_checked"},
        prior_id=uuid4(), question_id="authorization")
    for prepared, rows in ((base, base["input_ledger"]["records"]), (deep, deep["followup_boundary"]["records"]),
                           (final, final["followup_boundary"]["records"])):
        assert prepared["ready"]
        text = prepared["messages"][1]["content"]
        assert text.count(revision["result_text"]) == text.count(older["result_text"]) == 1
        assert "internal-user-id" not in text
        assessment = next(r for r in rows if r.get("context_kind") == "current_assessment")
        assert set(assessment["value"]) == {"conclusion", "origin", "validity", "reason", "declared_scope"}
        assert assessment["alert_ids"] == [aid] and assessment["ref"]["role"] == "prior_analysis"
        assert assessment["original_scope"] == {"alert_ids": sorted([aid, removed])}
        aliases = {**prepared["case_boundary"]["member_aliases"],
                   **prepared.get("input_ledger", {}).get("external_member_aliases", {})}
        assert aliases[removed].startswith("X")
        assert assessment["value"]["declared_scope"] == {"alert_ids": [aliases[a] for a in sorted([aid, removed])]}
        assert prepared["source_map"][assessment["id"]]["original_scope"] == assessment["original_scope"]
        assert assessment["value"]["conclusion"] == raw["current_assessment"]["conclusion"]
        assert removed not in context.alerts
        if prepared is not base:
            heading = text[:text.index("[" + assessment["id"] + "]")].splitlines()[-1]
            assert "原范围=" + "、".join(aliases[a] for a in sorted([aid, removed])) in heading
        current = [r for r in rows if r.get("context_identity") == vid]
        assert len(current) == 2 and current[0]["ref"] != current[1]["ref"]
        for row in current:
            assert row["ref"]["role"] == "human_statement" and row["alert_ids"] == [aid]
            assert row["original_scope"] == revision["result_scope"]
            assert row["value"]["business_extension"] == revision["business_extension"]
            assert row["value"]["revision"] == 2 and row["value"]["unavailable_prior_reference_count"] == 1
            assert prepared["source_map"][row["value"]["source_refs"][0]]["ref"] == evidence["ref"]
    assert raw == before
