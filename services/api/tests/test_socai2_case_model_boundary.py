"""C3 structural projection and restoration; immutable recorded inputs, no network."""
import copy
import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from app.socai2 import baseline_analysis_contract as contract
from app.socai2 import case_model_boundary as boundary
from app.socai2 import case_output_adapter as adapter
from app.socai2 import case_query_snapshot as queries
from app.socai2 import runtime_policy
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import StoreError
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError

from tools.testdata.case_io_eval.fixtures import load

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "deploy/local-investigation/investigation-policy-case-v1.toml"


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    runtime_policy.active_policy.cache_clear()
    yield runtime_policy.active_policy()
    runtime_policy.active_policy.cache_clear()


@pytest.fixture
def sample(configured):
    config = json.loads((ROOT / "tools/testdata/case_io_eval/config.json").read_text())
    sample = load(ROOT, config)
    raw = sample["context"]
    raw["query_receipts_version"] = queries.VERSION
    raw["case_input_profile"] = configured.case_io.identity
    for aid, item in raw["alerts"].items():
        item["triage_run_state"] = "completed"
        item["queries"] = copy.deepcopy(sample["query_source"]["triage_queries"].get(aid, []))
        for row in item["queries"]:
            row.update(output_artifact_id=row["id"], step_kind="tool",
                       step_state=row["content_json"]["state"], source_run_state="completed")
    for iid, item in raw["incidents"].items():
        if not item["diagnosis_usable"]:
            continue
        diagnosis, base = item["diagnosis"], f"$.incidents.{iid}.diagnosis"
        paths = [base + ".summary"]
        paths += [base + ".diagnosis." + key for key in ("conclusion", "limitations") if key in diagnosis["diagnosis"]]
        paths += [base + f".diagnosis.findings.{i}" for i in range(len(diagnosis["diagnosis"].get("findings", [])))]
        paths += [base + f".open_questions.{i}" for i in range(len(diagnosis.get("open_questions", [])))]
        raw["citation_roles"].update(dict.fromkeys(paths, "prior_analysis"))
    raw["citation_roles"].update(queries.roles(raw))
    return sample


def prepared_sample(sample):
    context = Context.model_validate(sample["context"])
    value = boundary.build(context, sample["context_id"], [], [], sample["materials"],
                           execution_time=sample["run"]["started_at"], run_id=sample["run"]["id"])
    assert value["ready"], value["reason"]
    return context, value


def answer_for(prepared, context):
    aliases = prepared["case_boundary"]["member_aliases"]
    own = {aid: next(sid for sid, item in prepared["source_map"].items()
                    if item["alert_ids"] == [aid] and item["ref"]["role"] == "observation") for aid in aliases}
    return {"summary": "Synthetic unresolved analysis.",
        "members": [{"alert_id": alias, "state": "unresolved", "summary": "Synthetic observation needs context.",
                     "evidence_ids": [own[aid]], "limitations": ["Synthetic only."]} for aid, alias in aliases.items()],
        "questions": [{"id": q.id, "state": "unresolved", "answer": "Needs evidence.",
                       "evidence_ids": [], "limitations": ["Synthetic only."]} for q in context.questions
                      if not (prepared["case_boundary"].get("program_output")
                              and prepared["case_boundary"].get("stage") == "C6" and q.id == "coverage")],
        "findings": [], "domains": [{"name": name, "applicability": "undetermined", "reason": "Needs evidence.",
                                     "alert_ids": [], "finding_ids": [], "limitations": ["Synthetic only."]}
                                    for name in contract.DOMAINS], "conflicts": [], "followups": []}


def test_c1_copy_references_resolve_exact_roles_without_mutating_sources(sample):
    original = copy.deepcopy(sample)
    context, prepared = prepared_sample(sample)
    assert sample == original
    copied = [r for r in prepared["input_ledger"]["records"] if "original_reference" in r]
    assert len({r["original_reference"]["id"] for r in copied}) == 9
    for row in copied:
        ref = row["ref"]
        assert ref["id"] == sample["context_id"]
        value = sample["context"]
        for part in ref["source_path"][2:].split("."):
            value = value[int(part)] if isinstance(value, list) else value[part]
        if ref["source_path"].endswith(".content_json"):
            assert all(value[k] == row["original_value"][k] for k in ("tool_name", "state", "returned_rows"))
        else:
            assert value == row["original_value"]
        assert context.citation_roles[ref["source_path"]] == ref["role"]
    assert prepared["input_ledger"]["record_counts"]["finding"] == 8
    assert prepared["input_ledger"]["record_counts"]["question"] == 2
    assert prepared["input_ledger"]["query_supplement_was_in_original_c1"] is True


@pytest.mark.parametrize("field,value", [("output_artifact_id", "wrong"), ("source_run_state", "failed"),
    ("step_kind", "model"), ("step_state", "running"), ("run_id", "wrong"), ("sha256", "wrong")])
def test_query_receipt_identity_step_and_digest_are_required(sample, field, value):
    row = next(a for a in sample["context"]["alerts"].values() if a["queries"])["queries"][0]
    row[field] = value
    with pytest.raises(StoreError):
        queries.source(sample["context"])


def test_old_snapshot_does_not_fetch_or_invent_receipts(sample):
    raw = sample["context"]
    raw.pop("query_receipts_version")
    with pytest.raises(StoreError, match="case_queries_without_version"):
        queries.source(raw)
    for row in raw["alerts"].values():
        row.pop("queries")
    assert queries.source(raw) == {}
    raw["query_receipts_version"] = "future-version"
    with pytest.raises(StoreError, match="case_query_version_unsupported"):
        queries.source(raw)


def test_profile_drift_does_not_silently_rebuild_frozen_input(sample):
    sample["context"]["case_input_profile"]["sha256"] = "changed"
    with pytest.raises(StoreError, match="case_input_profile_changed"):
        prepared_sample(sample)


def test_database_material_types_have_same_business_view(sample):
    _, expected = prepared_sample(sample)
    for material in sample["materials"].values():
        for key in ("id", "tenant_id", "alert_id"):
            material[key] = UUID(material[key])
        material["received_at"] = datetime.fromisoformat(material["received_at"])
    _, actual = prepared_sample(sample)
    assert actual["messages"] == expected["messages"]
    assert actual["source_map"] == expected["source_map"]


def test_aliases_restore_only_structural_fields_and_partial_review_is_retained(sample):
    context, prepared = prepared_sample(sample)
    answer = answer_for(prepared, context)
    answer["summary"] = "Original text A1 stays as authored."
    fmt = adapter.output_format(prepared, context, {})
    Draft202012Validator(fmt["json_schema"]["schema"]).validate(answer)
    parsed = adapter.parse(json.dumps(answer), prepared, context, {})
    assert {str(m.alert_id) for m in parsed.members} == set(context.alerts)
    assert parsed.summary == answer["summary"]
    answer["members"][0]["evidence_ids"] = ["nonexistent-source"]
    with pytest.raises(contract.AnalysisRejected, match="source_not_in_model_input"):
        adapter.parse(json.dumps(answer), prepared, context, {})
    review = adapter.CaseReview(prepared, context, {})
    partial = review.partial(json.dumps(answer))
    assert partial.members[0].state == "not_analyzed"
    assert all(m.state == "unresolved" for m in partial.members[1:])
    assert len(review.details["diagnostics"]) == 1


def test_correction_feedback_and_conditional_tool_schema_use_same_short_namespace(sample):
    context, prepared = prepared_sample(sample)
    messages, sources = boundary.messages(prepared, context, [])
    assert messages[-1]["content"].startswith("[可用调查工具｜程序提供]")
    assert sources == prepared["source_map"]
    assert prepared["tool_presentation"]["text"] == messages[-1]["content"]
    answer = answer_for(prepared, context)
    answer["members"][0].update(state="analyzed", evidence_ids=[])
    feedback = adapter.CaseReview(prepared, context, {}).feedback(json.dumps(answer))
    assert feedback["errors"][0]["subject_id"] == "A1"
    assert all(a.startswith("A") for s in feedback["allowed_sources"] for a in s["alert_ids"])
    bindings = sample["request"]["binding_map"]
    assert bindings
    key, binding = next(iter(bindings.items()))
    aliases = prepared["case_boundary"]["member_aliases"]
    answer["followups"] = [{"question_id": context.questions[0].id,
        "alert_ids": [aliases[a] for a in binding["alert_ids"]], "mode": "query", "binding_id": key,
        "priority": "decision_critical", "objective": "Synthetic check.", "required_evidence": "Synthetic evidence.",
        "source_ids": [], "object_keys": []}]
    validator = Draft202012Validator(adapter.output_format(prepared, context, bindings)["json_schema"]["schema"])
    validator.validate(answer)
    answer["followups"][0]["binding_id"] = None
    with pytest.raises(SchemaError):
        validator.validate(answer)
