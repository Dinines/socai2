"""Direct C3 admission and Deep/C6 material-boundary checks; no network or DB."""
import asyncio
import copy
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import test_socai2_case_followup_boundary as followup
import test_socai2_case_model_boundary as base
from app.socai2 import baseline_analysis_contract as contract
from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as outputs
from app.socai2 import case_output_adapter as adapter
from app.socai2.baseline_dispatch import dispatch_followups, offered_bindings
from app.socai2.baseline_evidence_tools import catalog
from app.socai2.case_input_text import field_hint
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError

configured, sample = base.configured, base.sample


def request(sample, configured):
    context, prepared = base.prepared_sample(sample)
    now = datetime.now(UTC)
    _, bindings, _ = offered_bindings(catalog(context, "00000000-0000-0000-0000-000000000001"),
        configured.case.limits(now, "case-grounding.test"), now, [], SimpleNamespace(configured=lambda: True))
    assert len(bindings) >= 3
    aliases = prepared["case_boundary"]
    answer = base.answer_for(prepared, context)
    answer["followups"] = [{"question_id": q.id, "mode": "query", "binding_id": key,
        "alert_ids": [aliases["member_aliases"][a] for a in binding["alert_ids"]],
        "object_keys": [aliases["object_aliases"][o["object_key"]] for o in binding["objects"]],
        "priority": "decision_critical", "objective": "Synthetic distinct query.",
        "required_evidence": "Synthetic observations.", "source_ids": []}
        for q, (key, binding) in zip(context.questions, list(bindings.items())[:3])]
    return context, prepared, bindings, answer


@pytest.mark.parametrize("count", [2, 3])
def test_c3_limit_gates_schema_parser_partial_and_dispatch(sample, configured, count):
    context, prepared, bindings, answer = request(sample, configured)
    answer["followups"] = answer["followups"][:count]
    raw = json.dumps(answer)
    validator = Draft202012Validator(adapter.output_format(prepared, context, bindings)["json_schema"]["schema"])
    calls = []

    class Service:
        async def query_evidence(self, *args, **kwargs):
            calls.append(args[3])
            return {"reused": False, "result": {"state": "completed"}, "projection": {"reason": None},
                    "artifact_id": "synthetic", "projection_id": "synthetic"}

    async def receive_then_dispatch(receiver):
        parsed = receiver(raw)
        return await dispatch_followups(Service(), "t", "c", "r",
            [f.model_dump(mode="json") for f in parsed.followups], bindings, gateway=None, lake=None)

    review = adapter.CaseReview(prepared, context, bindings)
    def receive(content):
        return adapter.parse(content, prepared, context, bindings)
    if count == 2:
        validator.validate(answer)
        assert len(asyncio.run(receive_then_dispatch(receive))) == len(calls) == 2
        assert len(review.partial(raw).followups) == 2
    else:
        with pytest.raises(SchemaError):
            validator.validate(answer)
        for receiver in (receive, review.partial):
            with pytest.raises(contract.AnalysisRejected, match="case_followup_limit_exceeded"):
                asyncio.run(receive_then_dispatch(receiver))
        with pytest.raises(contract.AnalysisRejected, match="case_followup_limit_exceeded"):
            review.feedback(raw)
        assert calls == []
    assert json.loads(raw) == answer


def test_historical_three_followups_and_c6_suggestions_remain_readable(sample, configured):
    context, prepared, bindings, answer = request(sample, configured)
    old_boundary = {k: v for k, v in prepared["case_boundary"].items() if k != "max_followups"}
    restored = adapter.restore(json.dumps(answer), old_boundary)
    historical = contract.parse(restored, prepared["source_map"], context, prepared["coverage"], bindings=bindings)
    assert len(historical.followups) == 3
    comparison = {"state": "initial", "result_id": None}
    final = inputs.build("C6", context, prepared, {}, extra={"comparison": comparison})
    result = followup.final_answer(final, context, comparison)
    result["analysis"]["followups"] = [{k: v for k, v in row.items() if k not in {"priority", "binding_id"}}
        for row in answer["followups"]]
    Draft202012Validator(outputs.final_format(final, context, comparison)["json_schema"]["schema"]).validate(result)
    assert len(outputs.parse_final(json.dumps(result), final, context, comparison).analysis.followups) == 3


@pytest.mark.parametrize("stage", ["Deep", "C6"])
def test_case_registration_is_excluded_without_rewriting_or_dependency_reentry(sample, stage):
    context, prepared, prior = followup.fixture(sample)
    before = copy.deepcopy((context.model_dump(), prepared, prior))
    result = inputs.build(stage, context, prepared, {}, previous=prior, prior_id=uuid4(),
                          question_id="impact" if stage == "Deep" else None)
    assert result["ready"], result["reason"]
    records = [r for r in result["followup_boundary"]["records"] if r["ref"]["source_path"] == "$.case"]
    assert not records
    assert not any(r["ref"]["source_path"] == "$.case" for r in prepared["input_ledger"]["records"])
    assert {r.get("path") for r in prepared["omissions"]} >= {"$.case.title", "$.case.description"}
    context_id = str(sample["context_id"])
    artifacts = {context_id: {"schema_version": "socai2.baseline-context.v1", "content_json": context.model_dump(mode="json")}}
    registry = inputs.Sources(context, prepared, artifacts, [])
    source = {"ref": {"type": "artifact", "id": context_id, "role": context.citation_roles["$.case"],
        "source_path": "$.case", "external": None, "row_keys": []}, "alert_ids": list(context.alerts)}
    resolved = registry.resolve(source)
    if resolved:
        value = next(r["value"] for r in registry.rows if r["id"] == resolved)
        assert "title" not in value and "description" not in value
    cfg = inputs.selected_profile(context).config
    for view, rows in ((prepared, prepared["input_ledger"]["records"]), (result, result["followup_boundary"]["records"])):
        shown = "\n".join(m["content"] for m in view["messages"])
        assert "[impact 的回答边界]" in shown
        meanings = [field_hint(r["ref"], cfg) for r in rows if field_hint(r["ref"], cfg)]
        assert meanings and all(meaning in shown for meaning in meanings)
    assert (context.model_dump(), prepared, prior) == before


@pytest.mark.parametrize("stage", ["Deep", "C6"])
def test_background_summary_uses_receipts_even_when_prior_text_disagrees(sample, stage):
    context, prepared, prior = followup.fixture(sample)
    prior["analysis"]["summary"] = "Synthetic wrong prior: assets skipped; history returned zero."
    receipts = [{"tool_name": "assets", "state": "completed", "outcome": "empty", "returned_rows": 0, "truncated": False},
                {"tool_name": "history", "state": "skipped", "outcome": "not_queried", "returned_rows": None, "truncated": False}]
    for i, value in enumerate(receipts):
        prepared["input_ledger"]["records"].append({"id": f"receipt-{i}", "block": "background_query",
            "value": value, "alert_ids": list(context.alerts),
            "ref": {"type": "artifact", "id": str(uuid4()), "role": "execution_receipt",
                    "source_path": None, "external": None, "row_keys": []}})
    before = copy.deepcopy((prepared, prior))
    result = inputs.build(stage, context, prepared, {}, previous=prior, prior_id=uuid4(),
                          question_id=context.questions[0].id if stage == "Deep" else None)
    assert result["ready"], result["reason"]
    status = result["followup_boundary"]["background_status"]
    assert [{k: v for k, v in row.items() if k != "source_id"} for row in status] == receipts
    for row in status:
        assert result["source_map"][row["source_id"]]["ref"]["role"] == "execution_receipt"
    text = result["messages"][1]["content"]
    assert text.index("本轮背景查询的程序摘要") > text.index("前序C3判断原文")
    assert "返回行数=0" in text and "not_queried" in text
    assert (prepared, prior) == before


@pytest.mark.parametrize("stage", ["C3", "C6"])
def test_conflict_requires_each_findings_original_support_including_partial(sample, stage):
    context, prepared = base.prepared_sample(sample)
    comparison = {"state": "initial", "result_id": None}
    if stage == "C6":
        prepared = inputs.build(stage, context, prepared, {}, extra={"comparison": comparison})
    analysis = base.answer_for(prepared, context)
    findings = [{"id": f"F{i}", "state": "inferred", "statement": "Synthetic claim; this test checks sources only.",
        "alert_ids": [row["alert_id"]], "support_ids": row["evidence_ids"], "counter_ids": [],
        "alternatives": [], "limitations": []} for i, row in enumerate(analysis["members"][:2], 1)]
    analysis.update(findings=findings, conflicts=[{"id": "C1", "finding_ids": [f["id"] for f in findings],
        "state": "unresolved", "explanation": "Synthetic candidate; semantic contradiction is not verified here.",
        "evidence_ids": [f["support_ids"][0] for f in findings]}])
    if stage == "C3":
        answer, fmt = analysis, adapter.output_format(prepared, context, {})
        receive = lambda text: adapter.parse(text, prepared, context, {})
        review = adapter.CaseReview(prepared, context, {})
    else:
        answer = followup.final_answer(prepared, context, comparison)
        answer["analysis"] = analysis
        fmt = outputs.final_format(prepared, context, comparison)
        receive = lambda text: outputs.parse_final(text, prepared, context, comparison)
        review = outputs.FinalReview(prepared, context, comparison)
    validator = Draft202012Validator(fmt["json_schema"]["schema"])
    validator.validate(answer)
    receive(json.dumps(answer))  # Inferred findings with actual support stay eligible.
    # Borrowing an unrelated observation in conflict.evidence_ids cannot cover
    # a finding that has no original observation support of its own.
    findings[1].update(state="unresolved", support_ids=[], limitations=["Missing original evidence."])
    raw = json.dumps(answer)
    validator.validate(answer)  # Cross-finding dependencies are checked on receipt.
    with pytest.raises(contract.AnalysisRejected, match="conflict_original_support_missing"):
        receive(raw)
    diagnostic = review.feedback(raw)
    assert any(e["code"] == "conflict_original_support_missing" and e["finding_id"] == "F2" for e in diagnostic["errors"])
    partial = review.partial(raw)
    retained = partial.model_dump(mode="json") if stage == "C3" else review.details["retained_analysis"]
    assert retained["conflicts"] == [] and len(retained["findings"]) == 2
    assert any(d["code"] == "conflict_original_support_missing" for d in review.details["diagnostics"])
    assert review.details["conclusion_adoptable"] is False
    assert json.loads(raw) == answer
    # An output source with only a label or query membership is not a direct
    # observation, even when its ID appears among an otherwise valid pair.
    findings[1].update(state="inferred", support_ids=[analysis["members"][1]["evidence_ids"][0]])
    sid = findings[1]["support_ids"][0]
    for change in ({"ref": {**prepared["source_map"][sid]["ref"], "role": "source_label"}},
                   {"membership_basis": "query_binding_only"}):
        changed = copy.deepcopy(prepared)
        changed["source_map"][sid].update(change)
        changed_fmt = (adapter.output_format(changed, context, {}) if stage == "C3"
                       else outputs.final_format(changed, context, comparison))
        with pytest.raises(SchemaError):
            Draft202012Validator(changed_fmt["json_schema"]["schema"]).validate(answer)
