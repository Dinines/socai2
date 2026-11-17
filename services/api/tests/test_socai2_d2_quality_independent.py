"""D2 independent checks: current policy, offline receivers and report rendering.

The recorded r3 response is read-only input to a new parser check; its historical
Run/result is never rewritten. These checks do not call a model or a database.
"""
import copy
import hashlib
import json
import os
import socket
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import test_socai2_case_citation_quality as existing
import test_socai2_case_model_boundary as fixtures
from app.socai2 import (
    case_followup_input,
    case_followup_output,
    case_output_adapter,
    runtime_policy,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_delivery_projection import make_publication, markdown
from app.socai2.case_citation_quality import LIMITATION_NOTE, VALIDATION
from app.socai2.citation_quality import NOTE, new_review
from test_socai2_case_followup_boundary import final_answer

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml"
SNAPSHOT = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-01/final-pg.json"
sample = fixtures.sample
# Reuse the existing assertions under this module's explicitly selected policy.
test_existing_c3 = existing.test_c3_keeps_prose_states_and_records_independent_source_problems
test_existing_followups = existing.test_deep_and_c6_receive_retained_prior_with_warning_and_keep_final
test_existing_receipt_roles = existing.test_deep_missing_sources_and_receipt_role_do_not_change_supported_state
test_existing_identity_and_execution = existing.test_structural_and_execution_guards_remain_strict


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("D2 independent receiver checks must remain offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert policy.model.output_tokens["C3"] == 16384
    assert policy.model.output_tokens["C6"] == 16384
    yield policy
    runtime_policy.active_policy.cache_clear()


def record(name, value):
    if directory := os.environ.get("SOCAI2_D2_EVIDENCE_DIR"):
        path = Path(directory) / (name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@pytest.mark.parametrize("quality", ["explanation", "citation", "mixed"])
def test_next_inputs_describe_only_the_actual_quality_problem(sample, quality):
    context, prepared = fixtures.prepared_sample(sample)
    raw = fixtures.answer_for(prepared, context)
    raw["summary"] = "  原结论保留；不因质量提示重写。\n"
    question = next(item for item in raw["questions"] if item["id"] == context.questions[0].id)
    question["answer"] = "  当前问题原答保留。\n"
    if quality in {"explanation", "mixed"}:
        raw["members"][0]["limitations"] = []
    if quality in {"citation", "mixed"}:
        raw["members"][0]["evidence_ids"] = ["missing-reference"]
    before, review = copy.deepcopy(raw), new_review()
    value = case_output_adapter.parse(json.dumps(raw, ensure_ascii=False), prepared, context, {},
                                     citation_review=review)
    previous = {"analysis": value.model_dump(mode="json"), "source_map": prepared["source_map"],
                "validation": VALIDATION, "basis": {"citation_review": review}}
    previous_before = copy.deepcopy(previous)
    checks = {}
    for stage in ("Deep", "C6"):
        options = {"question_id": context.questions[0].id} if stage == "Deep" else {
            "extra": {"comparison": {"state": "initial", "result_id": None}}}
        followup = case_followup_input.build(stage, context, prepared, {}, previous=previous,
                                            prior_id=uuid4(), **options)
        assert followup["ready"], followup["reason"]
        text = followup["messages"][1]["content"]
        assert (NOTE in text) == (quality in {"citation", "mixed"})
        assert (LIMITATION_NOTE in text) == (quality in {"explanation", "mixed"})
        expected_text = "当前问题原答保留。" if stage == "Deep" else "原结论保留；不因质量提示重写。"
        assert expected_text in text
        checks[stage] = {"ready": True, "citation_note": NOTE in text,
                         "explanation_note": LIMITATION_NOTE in text}
    assert raw == before and previous == previous_before
    assert value.summary == raw["summary"] and review["prose_quality"] == "not_checked"
    record("followup-" + quality, {"checks": checks, "citation_review": review,
                                  "original_unchanged": True})


def test_report_distinguishes_missing_explanation_from_no_restrictions(sample):
    context, base = fixtures.prepared_sample(sample)
    comparison = {"state": "initial", "result_id": None, "added_alert_ids": [], "removed_alert_ids": []}
    prepared = case_followup_input.build("C6", context, base, {}, extra={"comparison": comparison})
    assert prepared["ready"], prepared["reason"]
    raw = final_answer(prepared, context, comparison)
    raw["conclusion"].update(text="原结论仍需核实。", limitations=[])
    raw["analysis"]["domains"][0].update(applicability="not_applicable", limitations=[])
    review = new_review()
    value = case_followup_output.parse_final(json.dumps(raw, ensure_ascii=False), prepared, context,
                                            comparison, citation_review=review)
    publication, limitations = make_publication(value, context,
        {UUID(a): {"read_state": "read"} for a in context.alerts}, prepared, comparison,
        {"delivery_state": "complete", "graph_artifact_id": uuid4()}, uuid4(), None)
    report = {"result": publication.model_dump(mode="json"), "delivery": value.model_dump(mode="json"),
              "comparison": comparison, "citation_review": review, "source_map": prepared["source_map"],
              "execution": {"model_calls": 0, "tool_calls": 0, "total_tokens": None},
              "limitations": limitations}
    # Exercise the valid nullable read-model field, without inventing an explanation.
    report["result"]["members"][0]["limitations"] = None
    before = copy.deepcopy(report)
    rendered = markdown(report)
    assert report == before
    assert "原结论仍需核实。" in rendered and "未记录限制说明" in rendered
    assert "无额外限制" not in rendered
    assert "分析与引用质量记录" in rendered and "采用不代表质量通过" in rendered
    assert "unapplied\\_domain\\_needs\\_limitations" in rendered
    assert report["delivery"]["conclusion"]["limitations"] == []
    assert report["delivery"]["analysis"]["domains"][0]["limitations"] == []
    record("report", {"markdown": rendered, "citation_review": review, "report_unchanged": True})


def test_recorded_r3_c6_quality_rejection_is_retained_by_current_receiver():
    frozen = SNAPSHOT.read_bytes()
    original_hash = hashlib.sha256(frozen).hexdigest()
    rows = json.loads(frozen)["rows"]
    artifacts = {row["id"]: row["content_json"] for row in rows["artifacts"]}
    context = Context.model_validate(artifacts["8a8af2e1-9d8d-45b0-a81f-5e35462980e9"])
    prepared = copy.deepcopy(artifacts["24300b26-a508-4c1a-9bf8-5d9730d56cd0"]["payload"])
    original_report = artifacts["cf756795-1629-4739-b470-54686255c3e8"]
    comparison = original_report["comparison"]
    # The stored wire has the actual C6 source map. Reconstruct only the receiver's
    # coverage counts by the same public rule, never the prompt or source aliases.
    prepared["coverage"] = copy.deepcopy(artifacts["aa16ff46-14c0-4a92-abbc-8be7f31eec80"]["coverage"])
    for aid, entry in prepared["coverage"].items():
        entry["included"] = sum(aid in row["alert_ids"] for row in prepared["source_map"].values())
    content = artifacts["93b2483c-3864-464e-9281-1ae5a31541cc"]["raw"]["choices"][0]["message"]["content"]
    raw, review = json.loads(content), new_review()
    value = case_followup_output.parse_final(content, prepared, context, comparison, citation_review=review)
    observation = next(item for item in value.analysis.findings if item.id == "F1")
    original_observation = next(item for item in raw["analysis"]["findings"] if item["id"] == "F1")
    assert observation.state == original_observation["state"] == "observed"
    assert observation.support_ids == original_observation["support_ids"]
    # Independently reconstructed from all frozen fields before the fix; never
    # computed by the production formatter as the expected result of this test.
    assert len(observation.statement) == 1218
    assert hashlib.sha256(observation.statement.encode()).hexdigest() == (
        "1f3da21c4be5ec0c04c1736db3744ab3d8d440a429a172432c5a093e54a28d85")
    assert value.conclusion.text == raw["conclusion"]["text"]
    assert value.conclusion.state == raw["conclusion"]["state"]
    assert [str(a) for a in value.conclusion.alert_ids] == [
        {alias: aid for aid, alias in prepared["case_boundary"]["member_aliases"].items()}[a]
        for a in raw["conclusion"]["alert_ids"]]
    assert any(i["code"] == "unapplied_domain_needs_limitations" and
               i.get("category") == "explanation_completeness" for i in review["issues"])
    for original, retained in zip(raw["analysis"]["domains"], value.analysis.domains, strict=True):
        assert (retained.applicability, retained.reason, retained.limitations) == (
            original["applicability"], original["reason"], original["limitations"])
    assert original_report["result"]["validation_state"] == "rejected"
    assert original_report["result"]["conclusion_state"] == "unavailable"
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == original_hash
    assert review["prose_quality"] == "not_checked"
    record("r3-c6-receiver-replay", {"snapshot_sha256": original_hash,
        "raw_content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "historical_result": "rejected/unavailable (unchanged)",
        "new_offline_receiver": "accepted with quality issues; not a new business Run",
        "restored_observation_characters": len(observation.statement),
        "all_32_original_field_references_and_statement_preserved": True,
        "original_text_state_scope_preserved": True, "citation_review": review})
