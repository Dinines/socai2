"""Audit regressions: frozen packets and pure projections, never model calls."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.socai2 import baseline_delivery_contract as contract
from app.socai2 import baseline_enrichment_sources as sources
from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_evidence_tools import row_projection
from app.socai2.baseline_reasoning import fit_final_request
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_errors import ModelCallError
from app.socai2.model_input_view import items
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("run_index", range(3))
def test_c6_frozen_packets_keep_facts_human_and_plans_in_original_budgets(run_index):
    from diagnose_socai2_kafka_inputs_20261105 import DIRECTORY, one
    db = json.loads(max(DIRECTORY.glob("database-*.json")).read_text("utf-8"))
    run = [r for r in db["runs"] if r["stop_reason"] == "required_model_input_unavailable"][run_index]
    result = asyncio.run(one(db, run))
    prepared, captured = result["prepared"], result["captured"]
    assert prepared["ready"], prepared["reason"]
    assert prepared["bytes"] <= 8192 and len(encoded(prepared["messages"])) <= 12288
    required = [c for c in captured["candidates"] if c.get("required")]
    context = Context.model_validate(next(a["content_json"] for a in db["artifacts"]
        if a["run_id"] == run["id"] and a["schema_version"] == "socai2.baseline-context.v1"))
    canonical = {"model": "deepseek-flash", "messages": prepared["messages"], "max_tokens": 3000, "temperature": 0,
        "response_format": response_format(contract.Delivery, prepared["source_map"],
            members=context.alerts, questions=[q.id for q in context.questions], objects=context.scope.object_keys)}
    body = prepare_request(SimpleNamespace(provider="deepseek_responses", schema_profile="standard"), canonical)
    previous = [s for s in db["run_steps"] if s["run_id"] == run["id"] and s["kind"] == "model"]
    assert all(s["usage"]["usage_state"] == "reported" for s in previous)
    used = sum(s["usage"]["total_tokens"] for s in previous)
    allowance = 24000 - used - 3000 - 256
    fit_final_request(body, prepared, allowance)
    # The original C3 calls already spent 7k+ tokens; a replay cannot erase
    # those costs. Verify preparation and the remaining-budget stop separately.
    assert len(encoded(body)) + 3000 + 256 <= 24000
    limits = Limits.model_validate(run["limits"])
    reason = budget_reason(previous, limits, len(encoded(body)), context.captured_at)
    assert reason == ("model_token_budget_insufficient" if len(encoded(body)) > allowance else None)
    visible = {i["id"]: i for i in items(json.loads(body["input"][1]["content"]))}
    selected = {encoded(s["ref"]): visible[sid]["value"] for sid, s in prepared["source_map"].items()}
    for candidate in required:
        value = selected[encoded(candidate["source"]["ref"])]
        assert value == candidate["entry"]["value"]
    for candidate in captured["candidates"]:
        ref = encoded(candidate["source"]["ref"])
        if ref in selected:
            assert digest(selected[ref]) == digest(candidate["entry"]["value"])
        else:
            assert any(encoded(o["ref"]) == ref for o in prepared["omissions"])


@pytest.mark.parametrize("field", ["hashes", "fingerprints"])
def test_hash_keeps_explicit_algorithm_source_and_conflicts(field):
    value = "a" * 64
    output = row_projection({"hash_sha256": value.upper(), "ocsf_json": {"class_uid": 1007,
        "file": {field: [{"algorithm": "SHA-256", "value": value}]}}})
    hashes = [f for f in output["fields"] if f["name"] == "hash_sha256"]
    assert len(hashes) == 1 and hashes[0]["value"] == value and not hashes[0]["conflict"]
    output = row_projection({"hash_sha256": "b" * 64, "ocsf_json": {"class_uid": 1007,
        "file": {field: [{"algorithm": "SHA256", "value": value}]}}})
    hashes = [f for f in output["fields"] if f["name"] == "hash_sha256"]
    assert len(hashes) == 2 and all(f["conflict"] for f in hashes)
    assert {f["source_path"] for f in hashes} == {"$.hash_sha256", f"$.ocsf_json.file.{field}[0].value"}


def test_flat_hash_and_invalid_or_unspecified_algorithms():
    value = "0" * 64
    assert any(f["value"] == value for f in row_projection({"hash_sha256": value})["fields"])
    out = row_projection({"hash_sha256": "bad", "ocsf_json": {"file": {"hashes": [
        {"value": value}, {"algorithm": "MD5", "value": value}, {"algorithm": "SHA256", "value": "bad"}]}}})
    assert not any(f["name"] == "hash_sha256" for f in out["fields"])
    assert {o["reason"] for o in out["omissions"]} >= {"invalid_sha256", "sha256_algorithm_not_explicit"}


@pytest.mark.parametrize("status,message,expected", [(400, 'Grammar error: Unimplemented keys: ["uniqueItems"]', True),
    (422, "invalid schema for response_format", True), (408, "invalid schema", False),
    (500, "invalid schema", False), (400, "upstream error", False), (None, "timeout", False)])
def test_schema_rejection_is_narrow_and_usage_not_invented(status, message, expected):
    exc = ModelCallError({"http_status": status, "fields": {"message": message}})
    assert bool(exc.rejection_code) == expected
    assert exc.payload()["raw"] is None


@pytest.mark.parametrize("types,expected", [([("host", "entity")], ["assets", "history"]),
    ([("hash", "ioc"), ("user", "entity")], ["threat_intel", "ueba"]),
    ([], ["knowledge"])])
def test_c2_choices_change_with_frozen_objects(types, expected):
    context = SimpleNamespace(alerts={"a": SimpleNamespace(alert={"title": "detection", "source_namespace": "test"},
        objects=[{"object_type": t, "object_role": role, "normalized_value": "synthetic", "object_key": t,
            "namespace": "test", "attributes": {"algorithm": "SHA256"}, "material_id": "m", "id": t,
            "source_path": "$.objects"} for t, role in types])})
    with patch.object(sources.optional, "enabled", return_value=True):
        plan = sources.selection_plan(context)
    assert [p["source"] for p in plan if p["priority"]][:len(expected)] == expected
