"""D3b independent checks with current profiles and explicitly derived old material.

Controllers use in-memory persistence and controlled replies. No real model,
database or HTTP request is made; historical D2 evidence is never rewritten.
"""
import asyncio
import copy
import hashlib
import json
import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from app.socai2 import case_c3_completion_flow as flow
from app.socai2 import case_c3_delivery as units
from app.socai2 import (
    case_followup_input,
    case_model_boundary,
    case_output_adapter,
    runtime_policy,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_dispatch import dispatch_followups
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.case_citation_quality import VALIDATION
from app.socai2.citation_quality import new_review
from app.socai2.stage_delivery import validate_sources

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/test-c3-continuation-d3-20261116-01"
POLICY = ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml"


def identity(name):
    return str(uuid5(NAMESPACE_URL, "socai2-independent-d3b/" + name))


def record(name, body):
    if directory := os.environ.get("SOCAI2_D3B_EVIDENCE_DIR"):
        path = Path(directory) / (name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2, default=str) + "\n")


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Independent D3b checks must remain offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert policy.model.output_tokens["C3"] == policy.model.output_tokens["C6"] == 16384
    yield policy
    runtime_policy.active_policy.cache_clear()


@pytest.fixture
def derived(configured):
    manifest = json.loads((EVIDENCE / "fixtures-01/manifest.json").read_text())
    path = ROOT / manifest["source_batch"] / "database.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["source_hashes"]["database.json"]
    rows = json.loads(path.read_text())
    artifacts = {row["id"]: row["content_json"] or {} for row in rows["artifacts"]}
    frozen_context = artifacts["3136a3cf-bde9-4d4d-83ef-96be9b852315"]
    raw = copy.deepcopy(frozen_context)
    raw["case_input_profile"] = configured.case_io.identity
    context = Context.model_validate(raw)
    prepared = case_model_boundary.build(context, identity("derived-context"), [], [],
        {r["alert_id"]: r for r in rows["alert_materials"]},
        execution_time=rows["runs"][0]["started_at"], run_id=identity("derived-run"))
    assert prepared["ready"], prepared["reason"]
    # This scenario offers no tools. It uses real frozen observations, not old
    # runtime configuration or old C3 request messages.
    messages, _ = case_model_boundary.messages(prepared, context, [])
    prepared.update(messages=messages, binding_map={}, input_view_id=identity("derived-view"),
        input_artifact_ids=[identity("derived-view")], citation_review=new_review())
    original = (EVIDENCE / "fixtures-01/f1-closed-f2-partial.txt").read_text()
    mother = json.loads((EVIDENCE / "fixtures-01/mother.txt").read_text())
    old_sources = artifacts["dce9cfcc-f454-47b8-b3bd-167ca41bbd38"]["source_map"]
    for finding in mother["findings"][:2]:
        for sid in finding["support_ids"]:
            old, new = old_sources[sid], prepared["source_map"][sid]
            assert old["ref"]["source_path"] == new["ref"]["source_path"]
            assert old["ref"]["role"] == new["ref"]["role"] and old["alert_ids"] == new["alert_ids"]
    record("derived-fixture", {"kind": "offline_current_profile_derivative", "source": str(path.relative_to(ROOT)),
        "source_sha256": manifest["source_hashes"]["database.json"],
        "historical_profile": frozen_context["case_input_profile"], "current_profile": configured.case_io.identity,
        "derived_context_id": identity("derived-context"), "derived_run_id": identity("derived-run"),
        "input_view_id": prepared["input_view_id"], "prepared": prepared,
        "changes": ["new context/view/run fixture identities", "current profile and regenerated C3 input",
                    "no optional enrichment or offered tools", "unchanged original F1/F2 values and source paths"],
        "real_model_calls": 0, "database_calls": 0})
    yield original, mother, prepared, context
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["source_hashes"]["database.json"]


@pytest.mark.parametrize("mode", ["disabled", "budget_skip", "blank", "invalid", "partial_conflict", "filled_findings"])
def test_current_controller_preserves_sources_and_feeds_actual_c6(derived, monkeypatch, mode):
    initial_text, mother, prepared, context = derived
    run_id, stage_id, model_id, request_id, original_id = [UUID(identity(mode + "/" + k))
        for k in ("run", "stage", "model", "request", "original")]
    prepared.update(received_finish_reason="length")
    prepared["citation_review"]["original_response_artifact_id"] = str(original_id)
    units.parser(prepared, context, {})(initial_text)
    first_units = copy.deepcopy(prepared["unit_delivery"]["retained_units"])
    assert len(first_units) == 6
    if mode == "disabled":
        prepared["case_boundary"]["c3_completion"]["max_attempts"] = 0
    request = copy.deepcopy(prepared)
    request["body"] = {"messages": prepared["messages"]}
    originals = {str(request_id): {"payload": request}, str(original_id): {
        "type": "model_original_response", "request_artifact_id": str(request_id),
        "raw": {"choices": [{"message": {"content": initial_text}}]}}}
    supplement = " " if mode == "blank" else '{"findings":[false]}'
    if mode == "partial_conflict":
        supplement = json.dumps({"findings": mother["findings"][:2]}, ensure_ascii=False)[:-2] + ',{"id":"F3"'
    elif mode == "filled_findings":
        supplement = json.dumps({"findings": mother["findings"][1:]}, ensure_ascii=False)
    saved, calls, extra_originals = {}, [], {}

    class Store:
        async def now(self):
            return datetime(2026, 11, 16, 12, tzinfo=timezone.utc)

        async def save_input_artifact(self, case, run, artifact, payload, **kwargs):
            saved[str(artifact)] = {"payload": copy.deepcopy(payload), "run_id": str(run), **kwargs}

    class Service:
        @asynccontextmanager
        async def transaction(self, _tenant):
            yield Store()

    class Steps:
        def __init__(self, *_args):
            pass

        async def locked(self, *_args):
            return {"requested_by": identity("actor")}

        async def save(self, store, run, step, payload, kind, refs=()):
            artifact = identity(mode + "/saved/" + str(len(saved)))
            saved[artifact] = {"payload": copy.deepcopy(payload), "kind": kind}
            return artifact

        async def call(self, tenant, case, run, stage, code, extra, gateway, parser, **kwargs):
            calls.append(copy.deepcopy(extra))
            assert code == "C3" and run == run_id and stage == stage_id
            assert kwargs["allow_correction"] is False
            if mode == "budget_skip":
                return None, "final_model_call_reserved", None, None
            rid, oid = identity(mode + "/supplement-request"), identity(mode + "/supplement-original")
            extra["citation_review"]["original_response_artifact_id"] = oid
            extra["received_finish_reason"] = "length" if mode == "partial_conflict" else "stop"
            extra_originals.update({rid: {"payload": copy.deepcopy(extra)}, oid: {
                "type": "model_original_response", "request_artifact_id": rid,
                "raw": {"choices": [{"message": {"content": supplement}}]}}})
            return parser(supplement), None, UUID(identity(mode + "/supplement-model")), identity(mode + "/response")

    async def read_originals(service, steps, tenant, case, run, mid, response):
        if mid == model_id:
            return {"state": "completed", "input_artifact_id": request_id}, originals, request
        return None, extra_originals, None

    monkeypatch.setattr(flow, "ModelSteps", Steps)
    monkeypatch.setattr(flow, "originals_for", read_originals)
    result = asyncio.run(flow.complete_sections(Service(), identity("tenant"), identity("case"), run_id, stage_id,
        prepared, context, {}, case_output_adapter.output_format(prepared, context, {}), None,
        (None, None, model_id, identity(mode + "/initial-response")), schema="socai2.baseline-analysis.v3"))
    receipt_row = saved[str(result[3])]
    receipt = receipt_row["payload"]
    assert receipt_row["step_id"] == stage_id and receipt_row["run_id"] == str(run_id)
    validate_sources(receipt, {**originals, **extra_originals})
    assert receipt["retained_units"][:6] == first_units
    assert receipt["delivery"]["state"] == "partial"
    assert len(calls) == (0 if mode == "disabled" else 1)
    attempts = prepared["section_completion_result"]["attempts"]
    assert attempts == (0 if mode in {"disabled", "budget_skip"} else 1)
    analysis = result[0].model_dump()
    expected_findings = ["F1", "F2"] if mode == "partial_conflict" else (
        ["F1", "F2", "F3", "F4", "F5"] if mode == "filled_findings" else ["F1"])
    assert [f["id"] for f in analysis["findings"]] == expected_findings
    assert "questions" not in analysis and "followups" not in analysis
    if mode == "partial_conflict":
        assert {"path": "$.supplement.findings[0]", "reason_code": "supplement_retained_unit_conflict"} in receipt["invalid_units"]
        assert receipt["retained_units"][-1]["path"] == "$.supplement.findings[1]"
    for unit in receipt["retained_units"]:
        text = initial_text if unit["original_artifact_id"] == str(original_id) else supplement
        start, end = unit["value_span"]
        assert json.loads(text[start:end]) == unit["value"]
        assert hashlib.sha256(text[start:end].encode()).hexdigest() == unit["value_sha256"]
    previous = {"analysis": analysis, "source_map": prepared["source_map"], "validation": VALIDATION,
        "basis": {"stage_delivery": prepared["stage_delivery_result"], "citation_review": prepared["citation_review"]}}
    before = copy.deepcopy(previous)
    c6 = case_followup_input.build("C6", context, prepared, {}, previous=previous, prior_id=identity(mode + "/prior"),
        extra={"comparison": {"state": "initial", "result_id": None}})
    assert c6["ready"] and previous == before
    row = next(r for r in c6["followup_boundary"]["records"] if r["block"] == "C3")
    assert row["ref"]["role"] == "prior_analysis" and row["ref"]["source_path"] == "$.analysis"
    assert [f["id"] for f in row["value"]["findings"]] == expected_findings
    assert row["value"]["findings"][0]["statement"] == analysis["findings"][0]["statement"]
    text = json.dumps(c6["messages"], ensure_ascii=False)
    assert "C3仅完成已列出的部分" in text
    assert not any(s in text for s in ("value_span", "value_sha256", "original_artifact_id", str(result[3])))
    assert receipt["quality"]["prose_quality"] == "not_checked"
    record(mode, {"stage_delivery": receipt, "completion": prepared["section_completion_result"],
        "analysis": analysis, "c6": c6, "controlled_supplement": supplement if attempts else None,
        "controller_calls": len(calls), "supplement_attempts": attempts, "real_model_calls": 0,
        "database_calls": 0, "source_checks": len(receipt["retained_units"])})


def test_empty_findings_keep_all_four_undetermined_domains(derived):
    _, mother, prepared, context = derived
    raw = copy.deepcopy(mother)
    raw.update(findings=[], conflicts=[])
    raw.pop("followups")
    raw["domains"] = [{"name": d["name"], "applicability": "undetermined", "reason": "待核实",
        "alert_ids": [], "finding_ids": [], "limitations": ["暂无发现"]} for d in raw["domains"]]
    received = units.receive(json.dumps(raw, ensure_ascii=False), prepared, context, {}, identity("empty-findings"))
    assert received["analysis"]["findings"] == []
    assert received["analysis"]["domains"] == raw["domains"] and len(raw["domains"]) == 4
    assert not received["invalid_units"]
    assert units.completion_fields(received) == ["followups"]
    assert any(u["path"] == "$.findings" and u["kind"] == "empty_array" for u in received["retained_units"])
    record("empty-findings-domains", received)


def test_c4_keeps_missing_dependency_and_later_plan_indices(derived):
    _, mother, prepared, context = derived
    raw = copy.deepcopy(mother)
    first, second = raw["followups"]
    assert first["question_id"] != second["question_id"]
    raw["questions"] = [q for q in raw["questions"] if q["id"] != first["question_id"]]
    for plan in raw["followups"]:
        plan.update(mode="human", binding_id=None)
    received = units.receive(json.dumps(raw, ensure_ascii=False), prepared, context, {}, identity("plans"))
    assert len(received["analysis"]["followups"]) == 2
    summary = units.summary(received, identity("plans-receipt"))
    assert summary["followup_unit_paths"] == ["$.followups[0]", "$.followups[1]"]
    assert summary["dispatch_paths"] == ["$.followups[1]"]
    allowed = {i for i, p in enumerate(summary["followup_unit_paths"]) if p in summary["dispatch_paths"]}
    plans = received["analysis"]["followups"]
    routes = asyncio.run(dispatch_followups(SimpleNamespace(), None, None, None, plans, {},
        gateway=None, lake=None, allowed_indices=allowed))
    by_index = {r["followup_index"]: r for r in routes}
    assert by_index[0]["state"] == "skipped" and by_index[0]["reason"] == "c3_followup_dependency_unavailable"
    assert by_index[1]["state"] == "handoff"
    _, selected = delivery_followups({"initial_analysis_artifact_id": identity("plans-analysis"), "routes": routes},
        {"analysis": {"followups": plans}})
    assert sorted(p["entry"]["value"]["execution_plan_index"] for p in selected) == [0, 1]
    record("c4-indices", {"summary": summary, "routes": routes, "projection": selected, "tool_calls": 0})
