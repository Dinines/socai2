"""Incident selection and actual coverage must survive the Case model boundary."""
import copy
import json
from uuid import uuid4

import pytest
import test_socai2_case_model_boundary as base
from app.socai2.case_incident_scope import freeze
from socai2_test_incident_scope import attach

configured, sample = base.configured, base.sample


def test_diagnosis_of_one_member_is_not_associated_with_all_three(sample):
    iid, item = next(iter(sample["context"]["incidents"].items()))
    selected = [item["member_ids"][0]]
    attach(item, sample["context"]["alerts"], selected=selected)
    # This is a controlled input variation, never a rewrite of the saved source.
    original = copy.deepcopy(sample)
    context, prepared = base.prepared_sample(sample)
    conclusion = next(row for row in prepared["source_map"].values()
                      if row["ref"]["source_path"] == f"$.incidents.{iid}.diagnosis.diagnosis.conclusion")
    assert len(context.alerts) == 3
    assert conclusion["alert_ids"] == selected
    assert conclusion["original_scope"]["alert_ids"] == selected
    assert sample == original


def test_unresolved_counts_as_covered_but_not_reviewed_does_not(sample):
    iid, item = next(iter(sample["context"]["incidents"].items()))
    selected = item["member_ids"][:2]
    attach(item, sample["context"]["alerts"], selected=selected, covered=selected[:1])
    context, prepared = base.prepared_sample(sample)
    actual = context.incidents[iid].diagnosis_scope["analysis_coverage"]
    assert (actual["analyzed_count"], actual["unresolved_count"], actual["not_analyzed_count"]) == (0, 1, 1)
    conclusion = next(row for row in prepared["source_map"].values()
                      if row["ref"]["source_path"] == f"$.incidents.{iid}.diagnosis.diagnosis.conclusion")
    assert conclusion["alert_ids"] == selected[:1]
    assert conclusion["original_scope"]["alert_ids"] == selected


@pytest.mark.parametrize("missing", ["source", "selection", "coverage", "fingerprint", "overlap"])
def test_unavailable_scope_keeps_case_material_without_inventing_coverage(sample, missing):
    iid, item = next(iter(sample["context"]["incidents"].items()))
    members = sample["context"]["alerts"]
    source = attach(item, members)
    if missing == "source":
        source = None
    elif missing == "selection":
        source["content_json"].pop("input_selection")
        from app.socai2.baseline_store import digest, encoded
        source["sha256"] = item["diagnosis"]["source_fingerprint"] = digest(source["content_json"])
        source["size_bytes"] = len(encoded(source["content_json"]))
    elif missing == "coverage":
        item["diagnosis"]["diagnosis"].pop("delivery_assessment")
    elif missing == "fingerprint":
        item["diagnosis"]["source_fingerprint"] = "wrong"
    else:
        source = attach(item, [], selected=[str(uuid4())])
    item["diagnosis_scope"], reasons = freeze(iid, item["diagnosis"], source, members)
    item["diagnosis_usable"] = bool(item["diagnosis_scope"] and item["diagnosis_scope"]["case_covered_alert_ids"])
    assert reasons
    context, prepared = base.prepared_sample(sample)
    assert len(context.alerts) == 3 and prepared["ready"]
    assert not any(row["ref"]["source_path"].startswith(f"$.incidents.{iid}.diagnosis")
                   for row in prepared["source_map"].values())


def test_cross_case_finding_scope_survives_c3_and_followup(sample):
    from app.socai2 import case_followup_input as inputs
    from app.socai2.model_input_view import source_members

    iid, item = next(iter(sample["context"]["incidents"].items()))
    own, outside = item["member_ids"][0], str(uuid4())
    selected = [own, outside]
    item["member_ids"].append(outside)
    item["diagnosis"]["diagnosis"]["findings"][0]["scope"]["alert_ids"] = selected
    attach(item, sample["context"]["alerts"], selected=selected)
    context, prepared = base.prepared_sample(sample)
    levels = prepared["input_ledger"]["presented_program_facts"]["incident_severities"]
    assert any(value.get("outside_case_missing_member_count") == 1 for value in levels.values())
    path = f"$.incidents.{iid}.diagnosis.diagnosis.findings.0"
    row = next(row for row in prepared["input_ledger"]["records"] if row["ref"]["source_path"] == path)
    assert row["alert_ids"] == [own]
    assert row["original_scope"]["alert_ids"] == selected
    assert source_members(context, row["ref"], {}) == [own]
    assert inputs.scope_metadata(row)["original_scope"]["alert_ids"] == selected
    from app.socai2.case_output_adapter import restore_current
    answer = base.answer_for(prepared, context)
    answer["questions"][0]["evidence_ids"] = [row["id"]]
    previous = {"analysis": json.loads(restore_current(json.dumps(answer), prepared["case_boundary"])),
                "source_map": prepared["source_map"], "validation": "structure_scope_sources_checked"}
    for stage in ("Deep", "C6"):
        followup = inputs.build(stage, context, prepared, {}, previous=previous, prior_id=uuid4(),
                                question_id=context.questions[0].id if stage == "Deep" else None)
        assert followup["ready"]
        inherited = next(r for r in followup["followup_boundary"]["records"] if r["ref"] == row["ref"])
        assert inherited["alert_ids"] == [own]
        assert inherited["original_scope"]["alert_ids"] == selected
