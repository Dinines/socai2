"""D4b independent checks against saved D4a originals and current profiles.

Offline only. SQL row selection and real allocation remain owner PG checks;
the in-memory capture/dispatch boundaries are explicitly controlled dependencies.
"""
import copy
import hashlib
import json
import os
import socket
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from app.socai2 import (
    baseline_context,
    case_incident_material,
    case_model_boundary,
    case_update_inputs,
    case_update_scanner,
    runtime_policy,
)
from app.socai2.baseline_contracts import Start
from app.socai2.baseline_store import digest, encoded

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/test-incident-signal-d4b-20261116-01"
PREP = EVIDENCE / "preparation-01"
RUNTIME = ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis"
RUNS = {"complete": "75255ae9-8159-5fa4-ae53-af5927e26523",
        "partial": "7ef7bceb-7c93-5894-bd0c-b0343334050b", "none": "3d8b5a17-512d-563d-b34e-6250c3f1bf35"}


def identity(label):
    return str(uuid5(NAMESPACE_URL, "socai2-d4b-independent/" + label))


def record(label, value):
    if target := os.environ.get("SOCAI2_D4B_EVIDENCE_DIR"):
        path = Path(target) / "cases" / (label + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


@pytest.fixture(autouse=True)
def current_policy(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("D4b independent direct checks must remain offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr("app.socai2.ai_stage_delivery.receive", forbidden)
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(RUNTIME / "investigation-policy.toml"))
    runtime_policy.active_policy.cache_clear()
    yield runtime_policy.active_policy()
    runtime_policy.active_policy.cache_clear()


@pytest.fixture
def source():
    manifest = json.loads((PREP / "manifest.json").read_text())
    row = manifest["sources"][0]
    raw = (ROOT / row["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    return json.loads(raw)


def candidate(source, state="partial"):
    rid = RUNS[state]
    artifacts = {row["id"]: row for row in source["artifacts"] if row["run_id"] == rid}
    attempt = next(row for row in source["analysis_attempts"] if row["run_id"] == rid)
    receipt = next(row for row in artifacts.values() if (row.get("content_json") or {}).get("type") == "stage_delivery")
    return copy.deepcopy({
        "run": next(row for row in source["runs"] if row["id"] == rid), "attempt": attempt,
        "task": next(row for row in source["analysis_tasks"] if row["id"] == attempt["task_id"]),
        "input": artifacts[attempt["input_artifact_id"]], "receipt": receipt,
        "response": next(row for row in artifacts.values() if row["kind"] == "model_response"),
        "originals": [artifacts[o["artifact_id"]] for o in receipt["content_json"]["originals"]],
        "diagnosis": next(row for row in source["incident_diagnoses"] if row["source_run_id"] == rid),
    })


def frozen(row, members=None):
    members = members if members is not None else row["input"]["content_json"]["input_selection"]["selected_alert_ids"]
    return case_incident_material.freeze(row["run"]["incident_id"], row, members)


def rehash(artifact):
    artifact["sha256"] = digest(artifact["content_json"])
    artifact["size_bytes"] = len(encoded(artifact["content_json"]))


def execution_copy(row):
    ids = {row[key]["id"] for key in ("run", "task", "attempt", "input", "response", "receipt")}
    ids.update(item["id"] for item in row["originals"])
    mapping = {old: identity("execution-copy/" + old) for old in ids}
    # UUID replacement only; original model text contains aliases, not these IDs.
    raw = json.dumps(row)
    for old, new in mapping.items():
        raw = raw.replace(old, new)
    result = json.loads(raw)
    result["task"]["reason_code"] = "controlled_execution_noise"
    result["attempt"]["error_code"] = "controlled_execution_noise"
    result["attempt"]["local_ended_at"] = "2026-11-16T16:00:00+00:00"
    result["task"]["ended_at"] = "2026-11-16T16:00:00+00:00"
    for artifact in (result["input"], result["response"], *result["originals"]):
        rehash(artifact)
    for original in result["receipt"]["content_json"]["originals"]:
        original["sha256"] = next(a["sha256"] for a in result["originals"] if a["id"] == original["artifact_id"])
    rehash(result["receipt"])
    return result


def context_for_compare(material):
    return SimpleNamespace(update_context=None, alerts={}, tasks={}, incidents={"i": SimpleNamespace(
        analysis_material=material, diagnosis_usable=False, diagnosis_scope=None)})


def projection_args(row):
    request = next(a for a in row["originals"] if a["kind"] == "model_request")
    return (copy.deepcopy(row["input"]["content_json"]), row["input"]["id"], copy.deepcopy(request["content_json"]["source_map"]))


@pytest.mark.parametrize("state,expected_paths", [
    ("complete", ["$.members[0]", "$.members[1]", "$.members[2]", "$.members[3]", "$.findings[0]",
                  "$.open_questions[0]", "$.open_questions[1]", "$.diagnosis.summary", "$.diagnosis.conclusion", "$.diagnosis.limitations"]),
    ("partial", ["$.members[0]"]), ("none", []),
])
def test_B03_saved_terminal_material_keeps_actual_units(source, state, expected_paths):
    row = candidate(source, state)
    original = copy.deepcopy(row)
    material, reasons = frozen(row)
    assert material, reasons
    assert [unit["path"] for unit in material["units"]] == expected_paths
    assert material["receipt"] == row["receipt"]["content_json"]
    assert material["input"]["sha256"] == row["input"]["sha256"]
    assert material["business_view"]["conclusion_available"] is (state == "complete")
    assert len(material["input_selection"]["selected_alert_ids"]) == 4
    if state == "partial":
        assert material["units"][0]["value"]["assessment"] == row["receipt"]["content_json"]["retained_units"][0]["value"]["assessment"]
        assert material["units"][0]["scope"]["alert_ids"] == [row["response"]["content_json"]["received_analysis"]["members"][0]["alert_id"]]
    assert row == original
    record("B03-" + state, {"material": material, "reasons": reasons, "source_unchanged": True})


@pytest.mark.parametrize("variation", ["running", "retry_wait", "missing_receipt", "original_digest", "wrong_source_run"])
def test_B01_B04_unfinished_or_invalid_candidate_cannot_signal(source, variation):
    row = candidate(source)
    if variation == "running":
        row["attempt"].update(local_state="running", local_ended_at=None)
    elif variation == "retry_wait":
        row["task"].update(state="waiting", next_retry_at="2026-11-16T16:00:00+00:00")
    elif variation == "missing_receipt":
        row["receipt"] = None
    elif variation == "original_digest":
        row["originals"][-1]["sha256"] = "0" * 64
    else:
        row["response"]["run_id"] = identity("wrong-run")
    result, reasons = frozen(row)
    assert result is None and reasons == ["incident_terminal_material_invalid"]
    record("B01-B04-" + variation, {"result": result, "reasons": reasons, "SQL_selection": "not_tested_here"})


@pytest.mark.parametrize("state", RUNS)
def test_B05_B06_execution_identity_and_error_noise_deduplicate(source, state):
    row = candidate(source, state)
    first, _ = frozen(row)
    second, reasons = frozen(execution_copy(row))
    assert second, reasons
    assert second["source_run_id"] != first["source_run_id"]
    assert second["input"]["id"] != first["input"]["id"]
    assert second["business_view"] == first["business_view"]
    assert case_update_inputs.unchanged(context_for_compare(first),
        case_update_inputs.business_view(context_for_compare(second)), {"i"})
    record("B05-" + state, {"first": first["business_view"], "second": second["business_view"], "same_business": True})


def test_B05_structured_aliases_and_nested_execution_support_do_not_trigger(source):
    row = candidate(source, "complete")
    receipt, analysis = copy.deepcopy(row["receipt"]["content_json"]), copy.deepcopy(row["response"]["content_json"]["received_analysis"])
    args = projection_args(row)
    _, before = case_incident_material.project(receipt, analysis, *args)
    for unit in receipt["retained_units"]:
        for ref in unit["resolved_refs"]:
            ref["source_id"] = "RENAMED_" + ref["source_id"]
    args[2].update({"RENAMED_" + key: value for key, value in list(args[2].items())})
    for members in (analysis["members"], analysis["findings"], analysis["open_questions"], [analysis["diagnosis"]]):
        for member in members:
            member["source_ids"] = ["RENAMED_" + sid for sid in member.get("source_ids", [])]
    _, after = case_incident_material.project(receipt, analysis, *args)
    assert after == before
    material, _ = frozen(row)
    updated = copy.deepcopy(row)
    legacy = updated["diagnosis"]["diagnosis"]
    changed_refs = []
    for ref in [*legacy.get("source_refs", []), *(r for f in legacy.get("findings", []) for r in f.get("support", []))]:
        changed_refs.append(ref["id"])
        ref["id"] = identity("legacy-support/" + ref["id"])
    assert changed_refs
    after_material, reasons = frozen(updated)
    assert after_material, reasons
    assert after_material["business_view"] == material["business_view"]
    record("B05-alias-support", {"scope": "projection alias mapping plus legacy diagnosis support identity noise",
                                 "same_business": True, "legacy_refs_changed": len(changed_refs)})


def test_B06_new_business_input_none_changes_signal(source):
    row = candidate(source, "none")
    before, _ = frozen(row)
    # Input business view mutation, not a new Run ID used as a proxy.
    changed = copy.deepcopy(row)
    view = changed["input"]["content_json"]["change_view"]
    member = next(member for member in view["members"] if member["triage"])
    member["triage"]["rationale"] += " 控制对照：新增业务授权材料待核。"
    selected = next(m for m in changed["input"]["content_json"]["members"] if m["alert"]["id"] == member["alert_id"])
    selected["triage"]["rationale"] = member["triage"]["rationale"]
    changed["attempt"]["input_digest"] = digest(view)
    rehash(changed["input"])
    after, reasons = frozen(changed)
    assert after, reasons
    assert not after["business_view"]["conclusion_available"]
    assert not case_update_inputs.unchanged(context_for_compare(before),
        case_update_inputs.business_view(context_for_compare(after)), {"i"})
    record("B06-new-input-none", {"before": before["business_view"], "after": after["business_view"],
                                 "scope": "controlled frozen input; SQL freshness checked by owner PG"})


@pytest.mark.parametrize("variation,expected_same", [("reference_identity", True), ("recommendation_reason", False)])
def test_B05_upstream_triage_recommendation_reference_noise_keeps_business(source, variation, expected_same):
    row = candidate(source, "complete")
    receipt = row["receipt"]["content_json"]
    analysis = row["response"]["content_json"]["received_analysis"]
    args = projection_args(row)
    _, before = case_incident_material.project(receipt, analysis, *args)
    triage = next(member["triage"] for member in args[0]["members"] if member["triage"])
    if variation == "reference_identity":
        references = [ref for recommendation in triage["recommendations"] for ref in recommendation["source_refs"]]
        assert references
        for ref in references:
            ref["id"] = identity("upstream-A-new-artifact/" + ref["id"])
    else:
        triage["recommendations"][0]["reason"] += " 新的业务核查理由。"
    _, after = case_incident_material.project(receipt, analysis, *args)
    assert (before == after) is expected_same
    record("B05-upstream-A-" + variation, {"same_business": expected_same, "before": before, "after": after})


@pytest.mark.parametrize("variation", ["content", "scope", "source_role", "source_business_value"])
def test_B08_actual_business_scope_or_role_changes_are_not_discarded(source, variation):
    row = candidate(source)
    receipt, analysis = copy.deepcopy(row["receipt"]["content_json"]), copy.deepcopy(row["response"]["content_json"]["received_analysis"])
    args = projection_args(row)
    _, before = case_incident_material.project(receipt, analysis, *args)
    if variation == "content":
        analysis["members"][0]["assessment"] += " 控制对照：新增业务说明。"
    elif variation == "scope":
        analysis["members"][0]["alert_id"] = args[0]["input_selection"]["selected_alert_ids"][1]
    elif variation == "source_role":
        receipt["retained_units"][0]["resolved_refs"][0]["ref"]["role"] = "human_statement"
    else:
        args[0]["members"][0]["alert"]["title"] += " 新业务观察。"
    _, after = case_incident_material.project(receipt, analysis, *args)
    assert after != before
    record("B08-" + variation, {"scope": "projection only; explicitly controlled variant", "before": before, "after": after})


async def captured(source, row, only_members=None):
    """Execute real capture on controlled SQL rows; no claim of SQL evaluation."""
    cid, iid, tid = identity("case"), row["run"]["incident_id"], row["run"]["tenant_id"]
    materials = {a["alert_id"]: copy.deepcopy(a) for a in source["alert_materials"]}
    alerts = {a["id"]: {"alert": copy.deepcopy(a), "membership": {"case_id": cid, "alert_id": a["id"]},
        "material": {**copy.deepcopy(materials[a["id"]]), "has_raw": True},
        "source_refs": [], "objects": [copy.deepcopy(o) for o in source["alert_objects"] if o["alert_id"] == a["id"]],
        "triage": None, "feedback": None, "triage_freshness": "unavailable", "triage_run_state": None, "queries": []}
        for a in source["alerts"] if only_members is None or a["id"] in only_members}
    raw = {"captured_at": "2026-11-16T17:00:00+00:00", "case": {"id": cid, "tenant_id": tid,
        "title": "Current terminal incident material", "description": "Controlled C1 assembly", "scope_revision": 1,
        "severity": "medium", "handling_status": "new"}, "alerts": alerts,
        "incidents": {iid: {"incident": copy.deepcopy(source["incidents"][0]), "linked_from_case": True,
            "member_ids": sorted(a["id"] for a in source["alerts"]), "member_links": copy.deepcopy(source["incident_alerts"]),
            "_terminal_material": copy.deepcopy(row)}},
        "tasks": {}, "current_assessment": None, "assessment_members": [], "assessment_sources": [],
        "prior_results": {}, "adopted_task_revisions": {}, "adopted_artifacts": {},
        "query_receipts_version": "socai2.case-queries.v1"}
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: copy.deepcopy(raw))))
    context = await baseline_context.capture(db, UUID(tid), UUID(cid),
        Start(expected_scope_revision=1, operation_key=UUID(identity("capture"))))
    assert db.execute.await_count == 1
    return context, materials


@pytest.mark.asyncio
@pytest.mark.parametrize("state", RUNS)
async def test_B10_capture_to_actual_C3_keeps_scope_role_and_excludes_ledger(source, state, current_policy):
    row = candidate(source, state)
    context, materials = await captured(source, row)
    iid = row["run"]["incident_id"]
    frozen_json = context.model_dump(mode="json")
    material = context.incidents[iid].analysis_material
    assert material["source_run_id"] == RUNS[state]
    assert context.case_input_profile == current_policy.case_io.identity
    refs = baseline_context.selected_refs(context)
    expected_ids = {r["id"] for r in [material["input"], material["response"], material["receipt_source"], *material["originals"]]}
    assert expected_ids <= {r["id"] for r in refs}
    prepared = case_model_boundary.build(context, identity("context"), [], [], materials,
        execution_time=datetime(2026, 11, 16, 17, tzinfo=UTC), run_id=identity("case-run"))
    assert prepared["ready"], prepared.get("reason")
    messages, mapping = case_model_boundary.messages(prepared, context, [])
    wire = "\n".join(m["content"] for m in messages)
    for index, unit in enumerate(material["units"]):
        path = f"$.incidents.{iid}.analysis_material.units.{index}.value"
        assert context.citation_roles[path] == "prior_analysis"
        sources = [item for item in mapping.values() if item["ref"].get("source_path") == path]
        assert sources and all(s["ref"]["role"] == "prior_analysis" for s in sources)
        assert all(sorted(s["alert_ids"]) == unit["scope"]["alert_ids"] for s in sources)
        text = unit["value"].get("assessment") if isinstance(unit["value"], dict) else None
        if text:
            assert text in wire
    forbidden = [material["attempt_id"], material["task_id"], material["source_run_id"],
                 material["receipt_source"]["sha256"], "retained_units", "local_ended_at", "controlled_execution_noise"]
    assert not any(value in wire for value in forbidden)
    row["receipt"]["content_json"]["delivery"]["state"] = "none"
    assert context.model_dump(mode="json") == frozen_json
    if state == "partial":
        assert not context.incidents[iid].diagnosis_usable and len(material["units"]) == 1
    record("B10-" + state, {"context": frozen_json, "messages": messages, "source_map": mapping,
                            "capture_dependency": "controlled SQL result; no database request"})


@pytest.mark.asyncio
async def test_B10_cross_member_finding_keeps_original_scope_for_one_member_case(source):
    row = candidate(source, "complete")
    owner = row["input"]["content_json"]["input_selection"]["selected_alert_ids"][0]
    context, materials = await captured(source, row, only_members={owner})
    iid = row["run"]["incident_id"]
    material = context.incidents[iid].analysis_material
    unit_index = next(n for n, unit in enumerate(material["units"]) if unit["path"] == "$.findings[0]")
    declared = material["units"][unit_index]["scope"]["alert_ids"]
    assert len(declared) == 4 and material["case_selected_alert_ids"] == [owner]
    prepared = case_model_boundary.build(context, identity("one-member-context"), [], [], materials,
        execution_time=datetime(2026, 11, 16, 17, tzinfo=UTC), run_id=identity("one-member-case-run"))
    assert prepared["ready"], prepared.get("reason")
    messages, mapping = case_model_boundary.messages(prepared, context, [])
    path = f"$.incidents.{iid}.analysis_material.units.{unit_index}.value"
    references = [v for v in mapping.values() if v["ref"].get("source_path") == path]
    assert references and all(v["alert_ids"] == [owner] for v in references)
    assert all(v["original_scope"]["alert_ids"] == declared for v in references)
    assert material["units"][unit_index]["value"]["statement"] in "\n".join(m["content"] for m in messages)
    record("B10-cross-case-scope", {"case_members": [owner], "original_scope": declared,
                                   "source_records": references, "messages": messages})


@pytest.mark.asyncio
@pytest.mark.parametrize("state,expected", [("partial", True), ("none", True), ("missing", False)])
async def test_B09_follow_current_uses_terminal_material_gate(source, monkeypatch, state, expected):
    row = candidate(source, "partial" if state == "missing" else state)
    context, _ = await captured(source, row)
    iid, cid = UUID(row["run"]["incident_id"]), context.case_id
    if state == "missing":
        context.incidents[str(iid)] = context.incidents[str(iid)].model_copy(update={"analysis_material": None})
    store = SimpleNamespace(case=AsyncMock(return_value={"continuation_root_case_id": cid, "scope_revision": 1}),
        where=lambda *args: [], db=SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: [iid]))))
    @asynccontextmanager
    async def transaction(*args, **kwargs):
        yield store
    follow = AsyncMock(return_value={"controlled_follow_receipt": True})
    monkeypatch.setattr(case_update_scanner, "capture", AsyncMock(return_value=context))
    monkeypatch.setattr(case_update_scanner.case_relations, "follow", follow)
    executor = SimpleNamespace(service=SimpleNamespace(transaction=transaction), allocation_policy=object(),
        task_service=SimpleNamespace(policy=object()))
    result = await case_update_scanner.follow_current(executor, UUID(row["run"]["tenant_id"]), cid, automatic=True)
    assert bool(result) is expected and follow.await_count == int(expected)
    if expected:
        assert follow.await_args.args[2] == iid
    record("B09-gate-" + state, {"follow_called": expected, "actual_allocation": "owner_PG_pending"})


def test_B11_late_single_alert_A_does_not_trigger_automatic_case(source):
    material, _ = frozen(candidate(source))
    before = context_for_compare(material)
    after = context_for_compare(copy.deepcopy(material))
    after.alerts["a"] = SimpleNamespace(triage_usable=True, triage={"verdict": "needs_review",
        "rationale": "首次分诊晚到", "confidence": None, "score_state": "unknown", "recommendations": []}, feedback=None)
    assert case_update_inputs.unchanged(before, case_update_inputs.business_view(after), {"i"})
    assert not case_update_inputs.unchanged(before, case_update_inputs.business_view(after))
    record("B11-late-A", {"automatic_unchanged": True, "manual_reads_new_A": True})
