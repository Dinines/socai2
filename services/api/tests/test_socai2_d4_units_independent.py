"""Current A/I receivers against independently frozen real-mother expectations.

All responses are controlled variants. No network, database or real model call.
Current builders process frozen material; referenced aliases must still resolve
to the exact original field, role and owners before the old text can be reused.
"""
import copy
import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import NAMESPACE_URL, uuid5

import pytest
from app.socai2 import (
    ai_delivery_store,
    alert_model_boundary,
    incident_model_boundary,
    runtime_policy,
    stage_delivery,
)
from app.socai2.baseline_analysis_model import usage
from app.socai2.baseline_store import digest, encoded

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/test-ai-continuation-d4-20261116-01"
POLICY = ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml"
FIXTURES = sorted([*(EVIDENCE / "fixtures-02").glob("*/*.expected.json"),
                   *(EVIDENCE / "boundaries-02").glob("*.expected.json")])


def identity(name):
    return str(uuid5(NAMESPACE_URL, "socai2-independent-d4a/" + name))


def read(path):
    return json.loads(path.read_text())


def record(name, value):
    if directory := os.environ.get("SOCAI2_D4_EVIDENCE_DIR"):
        path = Path(directory) / (name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@pytest.fixture(autouse=True)
def current_policy(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("D4 independent checks must remain offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert policy.model.output_tokens["A"] == policy.model.output_tokens["I"] == 8192
    yield policy
    runtime_policy.active_policy.cache_clear()


@pytest.fixture
def current_prepared(current_policy):
    cfg = read(EVIDENCE / "fixture-config.json")
    snapshot = ROOT / cfg["source_snapshot"]
    original_bytes = snapshot.read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == cfg["source_snapshot_sha256"]
    rows = json.loads(original_bytes)["rows"]
    fixtures = {}
    for stage in ("A", "I"):
        frozen = read(EVIDENCE / "fixtures-02" / stage / "frozen-source.json")
        run = frozen["run"]
        source = copy.deepcopy(frozen["input_snapshot"]["content_json"])
        before = copy.deepcopy(source)
        if stage == "A":
            queries = [(r["id"], copy.deepcopy(r["content_json"])) for r in rows["artifacts"]
                       if r["run_id"] == run["id"] and r["kind"] == "tool_response"]
            messages, mapping, _, prepared = alert_model_boundary.build(source, run["input_artifact_id"], queries,
                current_policy.alert_io, execution_time=run["started_at"])
        else:
            messages, mapping, _, prepared = incident_model_boundary.build(source, run["input_artifact_id"],
                current_policy.incident_io, execution_time=run["started_at"])
        assert source == before
        old = frozen["request"]["content_json"]["source_map"]
        # Current metadata filtering can remove unused sources. Every source
        # actually named by the real mother must retain its precise binding.
        used = set()

        def source_ids(value, collected):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"evidence_ids", "source_ids"}:
                        collected.update(child)
                    else:
                        source_ids(child, collected)
            elif isinstance(value, list):
                for child in value:
                    source_ids(child, collected)

        source_ids(json.loads((EVIDENCE / "fixtures-02" / stage / "mother.txt").read_text()), used)
        assert all(mapping[sid] == old[sid] for sid in used)
        if stage == "I":
            assert prepared["member_aliases"] == frozen["request"]["content_json"]["incident_boundary"]["member_aliases"]
        request = {"body": {"messages": messages, "max_tokens": current_policy.model.output_tokens[stage]},
            "source_map": mapping, "boundary": prepared["boundary"],
            "reserved_token_upper_bound": frozen["request"]["content_json"]["reserved_token_upper_bound"]}
        fixtures[stage] = prepared, request, frozen
        record(stage + "-current-preparation", {"kind": "offline_current_builder_over_frozen_original_material",
            "request": request, "source_snapshot_sha256": cfg["source_snapshot_sha256"],
            "frozen_run_id": run["id"], "referenced_sources_verified": sorted(used),
            "historical_source_count": len(old), "current_source_count": len(mapping),
            "reservation_note": "frozen original request bound used for controlled protocol validation, not new usage"})
    yield fixtures
    assert snapshot.read_bytes() == original_bytes


@pytest.mark.parametrize("fixture", FIXTURES, ids=[p.parent.name + "/" + p.stem for p in FIXTURES])
@pytest.mark.asyncio
async def test_current_ai_receive_preserves_frozen_units_scope_and_core_dependencies(current_prepared, fixture):
    expected = read(fixture)
    stage, name = expected["stage"], expected["name"]
    prepared, request, frozen = current_prepared[stage]
    fragment = fixture.with_name(name + ".txt").read_text()
    assert hashlib.sha256(fragment.encode()).hexdigest() == expected["fragment_sha256"]
    original_id, request_id = identity(stage + "/" + name + "/original"), identity(stage + "/" + name + "/request")
    payload = copy.deepcopy(frozen["original"]["content_json"]["raw"])
    payload["choices"][0]["message"]["content"] = fragment
    payload["choices"][0]["finish_reason"] = expected["finish_reason"]
    before = copy.deepcopy(prepared)
    received = ai_delivery_store.receive_payload(stage, payload, prepared, original_id, usage(payload), request)
    assert prepared == before
    actual = {u["path"]: u for u in received["retained_units"]}
    invalid = {u["path"] for u in received["invalid_units"]}
    oracle = {u["path"]: u for u in expected.get("complete_candidate_units", expected.get("complete_value_catalog", []))}
    if "complete_candidate_units" in expected:
        assert set(actual) == set(oracle)
        assert not invalid
    assert set(expected.get("must_retain_paths", [])) <= set(actual)
    assert set(expected.get("must_reject_paths", [])) <= invalid
    assert not set(expected.get("must_reject_paths", [])) & set(actual)
    assert received["delivery"]["state"] == expected["expected_delivery"]
    assert (received["result"] is not None) == expected["expected_usable_result"]
    assert received["use"]["conclusion_available"] == expected["expected_usable_result"]
    assert received["use"]["dispatch_paths"] == []
    assert not received["use"]["adoption_eligible"] and not received["use"]["comparison_eligible"]
    assert received["quality"]["prose_quality"] == "not_checked"
    for field in expected.get("must_not_create_fields", []):
        assert field not in received["analysis"]
    for path, unit in actual.items():
        start, end = unit["value_span"]
        assert json.loads(fragment[start:end]) == unit["value"]
        assert hashlib.sha256(fragment[start:end].encode()).hexdigest() == unit["value_sha256"]
        if path in oracle:
            assert (unit["value"], unit["value_span"], unit["value_sha256"]) == (
                oracle[path]["value"], oracle[path]["value_span"], oracle[path]["value_sha256"])
        assert unit["original_artifact_id"] == original_id
        for ref in unit["resolved_refs"]:
            source = prepared["source_map"][ref["source_id"]]
            assert ref["ref"] == source["ref"] and ref["alert_ids"] == source.get("alert_ids", [])
        if isinstance(unit["value"], dict) and "alert_refs" in unit["value"]:
            assert unit["declared_scope"] == {"alert_refs": unit["value"]["alert_refs"]}
    if stage == "I":
        aliases = prepared["member_aliases"]
        admitted = [aliases[m["alert_id"]] for m in received["validated_members"]]
        if "expected_original_member_aliases" in expected:
            assert admitted == expected["expected_original_member_aliases"]
        if "expected_question_ids" in expected:
            assert [q.id for q in received["result"].open_questions] == expected["expected_question_ids"]
    if received["result"] is not None:
        if stage == "A":
            assert received["result"].rationale == received["analysis"]["rationale"]
        else:
            assert received["result"].conclusion == received["analysis"]["diagnosis"]["conclusion"]
        if received["delivery"]["state"] == "partial":
            assert "stage_output_incomplete_see_stage_delivery" in received["result"].limitations
    originals = {request_id: request, original_id: {"raw": payload}}
    run = {**frozen["run"], "id": identity(stage + "/" + name + "/run")}
    step_id = identity(stage + "/" + name + "/step")
    store = AsyncMock()
    store.tenant_id = run["tenant_id"]
    store.where = lambda table, *conditions: conditions
    store.now.return_value = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    store.one.side_effect = [{"content_json": body, "material_state": "complete", "sha256": digest(body),
                              "size_bytes": len(encoded(body))} for body in originals.values()]
    _, receipt = await ai_delivery_store.save(store, run, step_id, request_id, original_id, received)
    stage_delivery.validate_sources(receipt, originals)
    inserted = store.db.execute.call_args_list[0].args[0].compile().params
    subject_key = "alert_id" if stage == "A" else "incident_id"
    assert inserted[subject_key] == run[subject_key] and inserted["run_id"] == run["id"]
    assert inserted["step_id"] == step_id and inserted["content_json"] == receipt
    assert "path_mapping" not in receipt["quality"]
    record(stage + "-" + name, {"kind": "controlled_real_mother_variant_offline", "stage_delivery": receipt,
        "analysis": received["analysis"], "validated_members": received["validated_members"],
        "result": received["result"].model_dump(mode="json") if received["result"] else None,
        "model_calls": 0, "database_calls": 0, "network_calls": 0})
