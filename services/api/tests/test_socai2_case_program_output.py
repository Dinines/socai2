"""Fixed facts are assembled without accepting model-authored replacements."""
import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import test_socai2_case_followup_boundary as followup
import test_socai2_case_model_boundary as base
from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as final
from app.socai2 import case_output_adapter as initial
from app.socai2 import case_program_output as program
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_evidence import SCHEMA
from app.socai2.baseline_store import BaselineStore, StoreError, digest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError

configured, sample = base.configured, base.sample


@pytest.mark.parametrize("stage", ["C3", "C6"])
def test_observed_statement_is_original_fields_and_model_cannot_supply_it(sample, stage):
    context, prepared = base.prepared_sample(sample)
    comparison = {"state": "initial", "result_id": None}
    if stage == "C6":
        prepared = inputs.build(stage, context, prepared, {}, extra={"comparison": comparison})
    analysis = base.answer_for(prepared, context)
    member = analysis["members"][0]
    finding = {"id": "F1", "state": "observed", "alert_ids": [member["alert_id"]],
        "support_ids": member["evidence_ids"], "counter_ids": [], "alternatives": [], "limitations": []}
    analysis["findings"] = [finding]
    answer = analysis if stage == "C3" else {**followup.final_answer(prepared, context, comparison), "analysis": analysis}
    fmt = initial.output_format(prepared, context, {}) if stage == "C3" else final.final_format(prepared, context, comparison)

    def receive(value):
        result = initial.parse(json.dumps(value), prepared, context, {}) if stage == "C3" else final.parse_final(json.dumps(value), prepared, context, comparison)
        return result if stage == "C3" else result.analysis

    before = copy.deepcopy(answer)
    Draft202012Validator(fmt["json_schema"]["schema"]).validate(answer)
    parsed = receive(answer)
    sid = member["evidence_ids"][0]
    literal = prepared["case_boundary"]["observation_literals"][sid]
    assert literal["path"] in parsed.findings[0].statement
    assert json.dumps(literal["value"], ensure_ascii=False, separators=(",", ":")) in parsed.findings[0].statement
    assert answer == before
    finding["statement"] = "Unsupported model-authored direction must not be replaced and accepted."
    with pytest.raises(SchemaError):
        Draft202012Validator(fmt["json_schema"]["schema"]).validate(answer)
    with pytest.raises(AnalysisRejected, match="observed_statement_is_program_owned"):
        receive(answer)


def test_overlong_original_is_rejected_and_partial_retains_independent_units(sample):
    context, prepared = base.prepared_sample(sample)
    answer = base.answer_for(prepared, context)
    member = answer["members"][0]
    sid = member["evidence_ids"][0]
    prepared["case_boundary"]["observation_literals"][sid]["value"] = "x" * 1300
    answer["findings"] = [{"id": "F1", "state": "observed", "alert_ids": [member["alert_id"]],
        "support_ids": [sid], "counter_ids": [], "alternatives": [], "limitations": []}]
    raw = json.dumps(answer)
    with pytest.raises(AnalysisRejected, match="observed_original_fields_exceed_statement_contract"):
        initial.parse(raw, prepared, context, {})
    review = initial.CaseReview(prepared, context, {})
    assert any(e["code"] == "observed_original_fields_exceed_statement_contract" for e in review.feedback(raw)["errors"])
    partial = review.partial(raw)
    assert partial.findings == [] and len(partial.members) == len(context.alerts)
    assert any(e["code"] == "observed_original_fields_exceed_statement_contract" for e in review.details["diagnostics"])
    assert json.loads(raw) == answer


def test_program_coverage_keeps_zero_unqueried_and_actual_retained_states(sample):
    context, base_input = base.prepared_sample(sample)
    for i, (tool, state, count) in enumerate([("assets", "completed", 0), ("history", "skipped", None)]):
        base_input["input_ledger"]["records"].append({"id": f"receipt-{i}", "block": "background_query",
            "value": {"tool_name": tool, "state": state, "outcome": "empty" if count == 0 else "not_queried",
                      "returned_rows": count, "truncated": False}, "alert_ids": list(context.alerts),
            "ref": {"type": "artifact", "id": str(uuid4()), "role": "execution_receipt",
                    "source_path": None, "external": None, "row_keys": []}})
    comparison = {"state": "initial", "result_id": None}
    prepared = inputs.build("C6", context, base_input, {}, extra={"comparison": comparison,
        "followup_execution": {"routes": [{"state": "handoff", "question_id": "authorization"}]}})
    answer = followup.final_answer(prepared, context, comparison)
    assert len(answer["analysis"]["questions"]) == 5
    parsed = final.parse_final(json.dumps(answer), prepared, context, comparison)
    assert len(parsed.analysis.questions) == 6
    coverage = next(q for q in parsed.analysis.questions if q.id == "coverage")
    assert 'state="completed"' in coverage.answer and "returned_rows=0" in coverage.answer
    assert 'state="skipped"' in coverage.answer and "returned_rows=null" in coverage.answer
    assert "handoff" in coverage.answer and len(coverage.evidence_ids) == 2
    invalid = copy.deepcopy(answer)
    invalid["analysis"]["questions"].append(coverage.model_dump(mode="json"))
    with pytest.raises(AnalysisRejected, match="coverage_question_is_program_owned"):
        final.parse_final(json.dumps(invalid), prepared, context, comparison)
    answer["analysis"]["members"][0]["evidence_ids"] = ["not-present"]
    review = final.FinalReview(prepared, context, comparison)
    assert review.partial(json.dumps(answer)) is None
    retained = review.details["retained_analysis"]
    assert "not_analyzed=1" in next(q["answer"] for q in retained["questions"] if q["id"] == "coverage")
    assert review.details["conclusion_adoptable"] is False


def test_historical_boundary_keeps_authored_observation_and_six_questions(sample):
    context, prepared = base.prepared_sample(sample)
    prepared["case_boundary"].pop("program_output")
    answer = base.answer_for(prepared, context)
    member = answer["members"][0]
    answer["findings"] = [{"id": "F1", "state": "observed", "statement": "Historical prose retained verbatim.",
        "alert_ids": [member["alert_id"]], "support_ids": member["evidence_ids"],
        "counter_ids": [], "alternatives": [], "limitations": []}]
    parsed = initial.parse(json.dumps(answer), prepared, context, {})
    assert parsed.findings[0].statement == "Historical prose retained verbatim." and len(parsed.questions) == 6


def test_c4_receipts_preserve_material_read_states_and_pass_actual_save_gate(sample):
    context, base_input = base.prepared_sample(sample)
    aids = list(context.alerts)
    material = {"type": "materials", "members": {
        aids[0]: {"state": "available", "material_state": "partial", "limitations": ["selected fields only"], "omissions": []},
        aids[1]: {"state": "unavailable", "limitations": ["not retained"], "omissions": [{"reason": "missing"}]}},
        "catalog": {"bindings": {"B": {"tool_name": "network_connections", "hostname": "synthetic-host",
            "scope": {"window_start": None, "window_end": None}}}}}
    payload = {"type": "query_projection", "binding_id": "B", "state": "completed", "reason": None,
        "question_id": "impact", "alert_ids": aids, "observed_rows_in_bounded_fetch": 0, "truncated": False,
        "limitations": [], "rows": []}
    rows = [{"id": uuid4(), "schema_version": SCHEMA, "content_json": p, "sha256": digest(p)} for p in (material, payload)]
    artifacts = {str(r["id"]): r for r in rows}
    comparison = {"state": "initial", "result_id": None}
    prepared = inputs.build("C6", context, base_input, artifacts, material=material, projections=[rows[1]],
                            extra={"comparison": comparison})
    before = copy.deepcopy((material, payload))
    answer = followup.final_answer(prepared, context, comparison)
    parsed = final.parse_final(json.dumps(answer), prepared, context, comparison)
    coverage = next(q for q in parsed.analysis.questions if q.id == "coverage")
    aliases = prepared["case_boundary"]["member_aliases"]
    assert "available=1" in coverage.answer and "unavailable=1" in coverage.answer and "unrecorded=1" in coverage.answer
    assert "observed_rows_in_bounded_fetch=0" in coverage.answer and "truncated=false" in coverage.answer
    facts = prepared["case_boundary"]["coverage_facts"]
    assert facts["material_reads"][aliases[aids[0]]] == material["members"][aids[0]]
    assert facts["material_reads"][aliases[aids[1]]]["omissions"] == [{"reason": "missing"}]
    # Resolve through a fresh registry: no cached row may mask mismatched projection.
    registry = inputs.Sources(context, base_input, artifacts, [])
    refs = []
    for sid in coverage.evidence_ids:
        source = prepared["source_map"][sid]
        ref = source["ref"]
        assert ref["source_path"] is None and ref["role"] == "execution_receipt"
        resolved = registry.resolve(source)
        original = next(r for r in prepared["followup_boundary"]["records"] if r["id"] == sid)
        assert next(r for r in registry.rows if r["id"] == resolved)["value"] == original["value"]
        refs.append(ref)
    assert len(refs) == 2 and (material, payload) == before

    # Only SQL results are substituted. This calls the production publication
    # scope/path/role gate, including its real C4 role mapping, without a database.
    async def check_save_gate():
        allowed = SimpleNamespace(scalars=lambda: [r["id"] for r in rows])
        mappings = lambda values: SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: values))
        store = BaselineStore(SimpleNamespace(execute=AsyncMock(side_effect=[allowed, mappings([]), mappings(rows)] * 2)), uuid4())
        store.one = AsyncMock(return_value={"content_json": {"prior_results": [], "task_revisions": [], "source_materials": []}})
        run = {"input_artifact_id": uuid4(), "case_id": uuid4(), "id": uuid4()}
        publication = SimpleNamespace(model_dump=lambda **_: {"evidence": refs}, graph_artifact_id=None, report_artifact_id=None)
        await store.validate_result_refs(run, [], publication)
        bad = {**refs[0], "source_path": "$.state"}
        publication.model_dump = lambda **_: {"evidence": [bad]}
        with pytest.raises(StoreError, match="context_citation_path_or_role_invalid"):
            await store.validate_result_refs(run, [], publication)
    asyncio.run(check_save_gate())


def test_material_coverage_summary_fits_valid_larger_case_without_losing_receipts():
    reads = {f"A{i}": {"state": "available", "omissions": [], "limitations": ["selected fields only"]} for i in range(40)}
    facts = {"visible_members": 40, "total_members": 40, "omission_count": 0, "material_reads": reads,
        "material_source_ids": ["M"], "execution_states": {}, "queries": [
            {"tool_name": tool, "state": "skipped", "outcome": "not_queried", "returned_rows": None,
             "truncated": False, "source_ids": [tool]} for tool in ("assets", "history", "knowledge", "ueba", "threat_intel", "graph")]}
    root = {"members": [{"state": "unresolved"}] * 40, "questions": [], "conflicts": [], "followups": []}
    before = copy.deepcopy(facts)
    answer = program.coverage_question(root, {"coverage_facts": facts})
    assert "available=40" in answer["answer"] and len(answer["answer"]) <= 1200
    assert answer["evidence_ids"] == ["M", "assets", "history", "knowledge", "ueba", "threat_intel", "graph"]
    assert facts == before
