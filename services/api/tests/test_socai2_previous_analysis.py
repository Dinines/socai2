"""Previous admitted units are history, not an older successful comparison."""
import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from app.socai2 import case_previous_analysis as previous
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_update_inputs import business_view
from test_socai2_c6_units import (
    mother as mother,  # noqa: PLC0414 - pytest fixture re-export
)

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/c6-unit-continuation-d5b-20261118-01"


@pytest.fixture
def saved():
    return json.loads((EVIDENCE / "analysis-only-01/snapshot.json").read_text())


def project(saved, members=None):
    run = saved["runs"][0]
    return previous.project(saved["artifacts"], run["tenant_id"], run["case_id"], run["id"],
                            members or [m["alert_id"] for m in saved["run_members"]])


def artifact(saved, predicate):
    return next(r for r in saved["artifacts"] if predicate(r.get("content_json") or {}))


def reseal(row):
    row.update(sha256=digest(row["content_json"]), size_bytes=len(encoded(row["content_json"])))


def admitted_observation_snapshot(saved, mother, stage):
    from app.socai2 import case_c3_delivery, case_c6_delivery
    from app.socai2.stage_delivery import VERSION, validate_sources

    if stage == "C3":
        context = Context.model_validate(artifact(saved, lambda body:
            body.get("schema_version") == "socai2.baseline-context.v1")["content_json"])
        summary = artifact(saved, lambda body: body.get("stage") == "C3_initial")["content_json"]
        rows = {row["id"]: row for row in saved["artifacts"]}
        prior = rows[summary["basis"]["stage_delivery"]["artifact_id"]]["content_json"]
        prepared = rows[prior["input_artifact_id"]]["content_json"]
        prepared = copy.deepcopy(prepared.get("payload", prepared))
        finding = copy.deepcopy(next(unit["value"] for unit in prior["retained_units"]
            if isinstance(unit["value"], dict) and unit["value"].get("state") == "observed" and "statement" not in unit["value"]
            and "support_ids" in unit["value"]))
        raw = {"findings": [finding]}
    else:
        text, prepared, context, comparison = copy.deepcopy(mother)
        raw = json.loads(text)
        finding = next(item for item in raw["analysis"]["findings"]
            if item["state"] == "observed" and "statement" not in item)
        if stage == "C6.partial":
            raw = {"analysis": {"findings": [finding]}}
    first = finding["support_ids"][0]
    finding["support_ids"] = [first, first, *finding["support_ids"][1:]]
    original_raw, original_prepared = copy.deepcopy(raw), copy.deepcopy(prepared)
    content = json.dumps(raw, ensure_ascii=False)
    original_id, input_id, receipt_id = map(str, (uuid4(), uuid4(), uuid4()))
    if stage == "C3":
        received = case_c3_delivery.receive(content, prepared, context, {}, original_id)
        analysis = received["analysis"]
        summary = {"stage": "C3_initial", "analysis": analysis,
                   "basis": {"stage_delivery": {"artifact_id": receipt_id}, "citation_review": received["quality"]}}
    else:
        received = case_c6_delivery.receive(content, prepared, context, comparison, original_id)
        assert received["delivery"]["state"] == ("complete" if stage == "C6.complete" else "partial")
        analysis = received["retained_output"]["fields"]["analysis"]
        summary = {"type": "delivery_report", "retained_output": received["retained_output"],
                   "stage_delivery": {"artifact_id": receipt_id}, "citation_review": received["quality"]}
    published = next(item for item in analysis["findings"] if item["id"] == finding["id"])
    assert published["support_ids"] == list(dict.fromkeys(finding["support_ids"]))
    assert received["quality"]["processing"]
    assert raw == original_raw and prepared == original_prepared
    run = {"id": str(uuid4()), "tenant_id": str(uuid4()), "case_id": str(context.case_id)}
    original = {"raw": {"choices": [{"message": {"content": content}}]}}
    execution = copy.deepcopy(artifact(saved, lambda body: body.get("type") == "stage_delivery")["content_json"]["execution"])
    receipt = {"schema_version": VERSION, "type": "stage_delivery", "run_id": run["id"],
        "step_id": str(uuid4()), "stage": "C3.initial" if stage == "C3" else "C6",
        "input_artifact_id": input_id, "originals": [{"artifact_id": original_id,
            "kind": "response", "sha256": digest(original)}], "execution": execution,
        **{key: received[key] for key in ("parse", "delivery", "retained_units", "missing_units", "invalid_units", "quality", "use")}}
    receipt = validate_sources(receipt, {original_id: original}).model_dump(mode="json")
    records = []
    for identity, body in ((str(uuid4()), context.model_dump(mode="json")), (input_id, {"payload": prepared}),
                           (original_id, original), (receipt_id, receipt), (str(uuid4()), summary)):
        body = json.loads(json.dumps(body, default=str))
        record = {"id": identity, "tenant_id": run["tenant_id"], "case_id": run["case_id"], "run_id": run["id"],
            "kind": "source_snapshot", "schema_version": body.get("schema_version", "test.native-admission.v1"),
            "material_state": "complete", "blob_ref": None, "content_json": body}
        reseal(record)
        records.append(record)
    return {"runs": [run], "run_members": [{"alert_id": aid} for aid in context.alerts],
            "artifacts": records}, finding["id"], published["statement"]


@pytest.mark.parametrize("stage", ["C3", "C6.partial", "C6.complete"])
def test_program_observation_replays_native_admission_after_save_read(saved, mother, tmp_path, stage):
    snapshot, identity, expected = admitted_observation_snapshot(saved, mother, stage)
    path = tmp_path / "native-admission.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False))
    loaded = json.loads(path.read_text())
    before = copy.deepcopy(loaded)
    result = project(loaded)
    unit = next(item for item in result["units"] if item["kind"] == "findings" and item["identity"] == identity)
    assert unit["value"]["statement"] == expected
    assert loaded == before
    summary = artifact(loaded, lambda body: body.get("stage") == "C3_initial" or body.get("type") == "delivery_report")
    fields = summary["content_json"].get("analysis") or summary["content_json"]["retained_output"]["fields"]["analysis"]
    finding = next(item for item in fields["findings"] if item["id"] == identity)
    finding["statement"] += "\nchanged"
    reseal(summary)
    with pytest.raises(ValueError, match="previous_analysis_program_observation_mismatch"):
        project(loaded)


def test_failed_final_keeps_only_admitted_business_content(saved):
    value = project(saved)
    assert len(value["units"]) == 11
    assert {u["source_stage"] for u in value["units"]} == {"C6"}
    assert all(u["kind"] not in {"conclusion", "domains", "followups"} for u in value["units"])
    report = artifact(saved, lambda c: c.get("type") == "delivery_report")["content_json"]
    finding = next(u for u in value["units"] if u["kind"] == "findings")
    original = report["retained_output"]["fields"]["analysis"]["findings"][0]
    assert all(finding["value"][k] == original[k] for k in previous.FIELDS["findings"])
    assert "support_ids" not in finding["value"] and "receipt_artifact_id" not in finding["value"]


def test_cross_member_scope_never_shrinks_prose(saved):
    aid = saved["run_members"][0]["alert_id"]
    value = project(saved, [aid])
    finding = next(u for u in value["units"] if u["kind"] == "findings")
    assert len(finding["declared_scope"]["alert_ids"]) == 4
    assert finding["applicable_alert_ids"] == [aid]
    assert finding["value"] == next(u for u in project(saved)["units"] if u["kind"] == "findings")["value"]


@pytest.mark.parametrize("damage", ["tenant", "case", "run", "hash", "span", "prose", "summary", "member", "scope", "observed"])
def test_corrupt_or_foreign_sources_cannot_be_frozen(saved, damage):
    report = artifact(saved, lambda c: c.get("type") == "delivery_report")
    if damage in {"tenant", "case", "run"}:
        report[damage + "_id"] = str(uuid4())
    elif damage == "hash":
        report["sha256"] = "0" * 64
    elif damage == "span":
        receipt = artifact(saved, lambda c: c.get("type") == "stage_delivery" and c["stage"] == "C6")
        receipt["content_json"]["retained_units"][0]["value_span"][1] += 1
        reseal(receipt)
    elif damage == "prose":
        report["content_json"]["retained_output"]["fields"]["analysis"]["members"][0]["summary"] = "altered prose"
        reseal(report)
    else:
        fields = report["content_json"]["retained_output"]["fields"]["analysis"]
        if damage == "summary":
            fields["summary"] = "unrelated summary"
        elif damage == "member":
            fields["members"][0]["alert_id"] = fields["members"][1]["alert_id"]
        elif damage == "scope":
            fields["findings"][0]["alert_ids"] = fields["findings"][0]["alert_ids"][:1]
        else:
            fields["findings"][0]["statement"] = "altered observation"
        reseal(report)
    with pytest.raises(ValueError):
        project(saved)


def test_missing_receipt_uses_c3_without_reparsing_c6(saved):
    report = artifact(saved, lambda c: c.get("type") == "delivery_report")
    report["content_json"].pop("stage_delivery")
    reseal(report)
    value = project(saved)
    assert {u["source_stage"] for u in value["units"]} == {"C3"}
    assert value["omissions"] == ["C6_admission_receipt_unavailable"]


def test_deep_answer_is_fallback_only_for_missing_business_question(saved):
    for row in saved["artifacts"]:
        body = row.get("content_json") or {}
        if body.get("type") == "delivery_report":
            body.pop("stage_delivery")
            reseal(row)
        if body.get("stage") == "C3_initial":
            body["basis"].pop("stage_delivery")
            reseal(row)
    value = project(saved)
    assert len(value["units"]) == 1 and value["units"][0]["source_stage"] == "Deep"
    answer = artifact(saved, lambda c: c.get("type") == "deep_summary")["content_json"]["answer"]
    assert all(value["units"][0]["value"][k] == answer[k] for k in previous.FIELDS["answer"])


def test_copy_is_not_new_business_input_for_scheduling(saved):
    context = Context.model_validate(artifact(saved, lambda c: c.get("schema_version") == "socai2.baseline-context.v1")["content_json"])
    changed = context.model_copy(update={"update_context": {"previous_analysis_material": project(saved)}})
    assert business_view(changed) == business_view(context)
    assert previous.unit(changed, previous.PREFIX + "5.value")["kind"] == "findings"
    assert previous.unit(changed, previous.PREFIX + "5.original_artifact_id") is None


def test_c3_actual_view_has_history_and_aliases_without_backend(saved, monkeypatch):
    import test_socai2_case_model_boundary as base
    from app.socai2.case_model_boundary import build
    from app.socai2.runtime_policy import active_policy
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(base.POLICY))
    active_policy.cache_clear()
    source = artifact(saved, lambda c: c.get("schema_version") == "socai2.baseline-context.v1")
    context = Context.model_validate(source["content_json"])
    material = project(saved)
    context = context.model_copy(update={"update_context": {"previous_analysis_material": material},
        "citation_roles": {**context.citation_roles, **{previous.PREFIX + str(i) + ".value": "prior_analysis"
                                                      for i in range(len(material["units"]))}}})
    materials = {r["alert_id"]: r for r in saved["alert_materials"]}
    result = build(context, source["id"], [], {}, materials)
    rows = [r for r in result["input_ledger"]["records"] if r.get("context_kind") == "previous_analysis"]
    assert len(rows) == 11
    assert all(r["ref"]["role"] == "prior_analysis" for r in rows)
    messages = json.dumps(result["messages"], ensure_ascii=False)
    assert "上一轮有效分析片段" in messages
    assert material["source_run_id"] not in messages
    assert all(u["receipt_artifact_id"] not in messages for u in material["units"])
    finding = next(u for u in material["units"] if u["kind"] == "findings")
    assert finding["value"]["statement"] in "\n".join(m["content"] for m in result["messages"])
    assert all(a.startswith("A") for r in rows for a in r["value"]["declared_scope"]["alert_ids"])
    active_policy.cache_clear()
