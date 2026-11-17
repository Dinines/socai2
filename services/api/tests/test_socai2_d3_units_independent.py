"""D3a independent frozen expectations; offline receive and receipt checks only."""
import copy
import hashlib
import json
import os
import socket
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from app.socai2 import case_c3_delivery, runtime_policy, stage_delivery
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import digest

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/test-c3-continuation-d3-20261116-01"
POLICY = ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml"
FIXTURES = sorted(p for folder in ("fixtures-01", "boundaries-01", "structure-01", "order-01")
                  for p in (EVIDENCE / folder).glob("*.expected.json"))


def read(path):
    return json.loads(path.read_text())


def identity(name):
    return str(uuid5(NAMESPACE_URL, "socai2-independent-d3a/" + name))


@pytest.fixture(autouse=True)
def selected_policy(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("D3a independent tests must not access a network service")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert policy.model.output_tokens["C3"] == 16384
    yield policy
    runtime_policy.active_policy.cache_clear()


@pytest.fixture
def frozen():
    manifest = read(EVIDENCE / "fixtures-01/manifest.json")
    source = ROOT / manifest["source_batch"] / "database.json"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["source_hashes"]["database.json"]
    rows = read(source)
    artifacts = {a["id"]: a["content_json"] or {} for a in rows["artifacts"]}
    prepared = copy.deepcopy(artifacts[manifest["request_artifact_id"]]["payload"])
    context = Context.model_validate(artifacts["3136a3cf-bde9-4d4d-83ef-96be9b852315"])
    view = artifacts["dce9cfcc-f454-47b8-b3bd-167ca41bbd38"]
    prepared["coverage"] = copy.deepcopy(view["coverage"])
    for aid, entry in prepared["coverage"].items():
        entry["included"] = sum(aid in r["alert_ids"] for r in prepared["source_map"].values())
    assert prepared["case_boundary"]["c3_output"]["max_findings"] == 5
    return prepared, context


def receive(text, expected, frozen):
    prepared, context = frozen
    original_id = identity(expected["name"] + "/original")
    before = copy.deepcopy(prepared)
    result = case_c3_delivery.receive(text, prepared, context, prepared["binding_map"], original_id,
                                     finish_reason=expected["finish_reason"])
    assert prepared == before
    original = {"raw": {"choices": [{"message": {"content": text}, "finish_reason": expected["finish_reason"]}]}}
    receipt = {"schema_version": stage_delivery.VERSION, "type": "stage_delivery",
        "run_id": identity("run"), "step_id": identity("step"), "stage": "C3", "input_artifact_id": identity("input"),
        "originals": [{"artifact_id": original_id, "kind": "received_fragment", "sha256": digest(original)}],
        "execution": {"kind": "model", "call_state": "completed", "local_state": "ended",
            "local_ended_at": "2026-11-16T12:00:00Z", "request_dispatched": True,
            "finish_reason": expected["finish_reason"], "error": None, "retry_allowed": False,
            "retry_reason": "offline_received_fragment_fixture_no_real_request"},
        **{k: result[k] for k in ("parse", "delivery", "retained_units", "missing_units", "invalid_units", "quality", "use")}}
    originals = {original_id: original}
    stage_delivery.validate_sources(receipt, originals)
    return result, receipt, originals


@pytest.mark.parametrize("fixture", FIXTURES, ids=[p.name.removesuffix(".expected.json") for p in FIXTURES])
def test_independent_frozen_units_and_business_boundaries(frozen, fixture):
    expected = read(fixture)
    text = fixture.with_name(expected["name"] + ".txt").read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == expected["fragment_sha256"]
    result, receipt, _ = receive(text, expected, frozen)
    actual = {unit["path"]: unit for unit in result["retained_units"]}
    assert len(actual) == len(result["retained_units"])
    lexical = expected.get("lexically_complete_original_units", expected.get("lexical_units"))
    if lexical is not None:
        known = {unit["path"]: unit for unit in lexical}
        assert set(actual) <= set(known)
        for path, unit in actual.items():
            oracle = known[path]
            assert (unit["value"], unit["value_span"], unit["value_sha256"]) == (
                oracle["value"], oracle["value_span"], oracle["value_sha256"])
    if "lexically_complete_original_units" in expected:
        assert set(actual) == {u["path"] for u in lexical}
        assert not result["invalid_units"]
    assert set(expected.get("must_retain_business_paths", [])) <= set(actual)
    assert not (set(expected.get("must_not_retain_paths", [])) & set(actual))
    for section in expected.get("forbidden_sections", []):
        assert section not in result["analysis"]
        assert not any(path == "$." + section or path.startswith("$." + section + "[") for path in actual)
    if expected.get("dispatch_paths") is not None:
        assert result["use"]["dispatch_paths"] == expected["dispatch_paths"]
    if "expected_delivery" in expected:
        assert result["delivery"]["state"] == expected["expected_delivery"]
    if expected.get("expected_invalid_reason"):
        assert any(gap["reason_code"] == expected["expected_invalid_reason"] and
                   gap["path"] in expected["must_not_retain_paths"] for gap in result["invalid_units"])
    if "maximum_accepted_findings" in expected:
        assert len(result["analysis"].get("findings", [])) <= expected["maximum_accepted_findings"]
    if expected["name"] in {"unknown-member", "duplicate-member-key", "duplicate-members-section", "duplicate-finding-id"}:
        assert result["invalid_units"] and result["delivery"]["state"] == "partial"
    if expected["name"] == "explicit-empty-followups":
        assert result["analysis"]["followups"] == [] and actual["$.followups"]["kind"] == "empty_array"
    if expected["name"] == "f1-closed-f2-partial":
        assert [f["id"] for f in result["analysis"]["findings"]] == ["F1"]
        assert "statement" not in actual["$.findings[0]"]["value"]
        assert result["analysis"]["findings"][0]["statement"]
        assert set(result["analysis"]) == {"summary", "members", "findings"}
    if expected["name"] in {"complete-stop", "complete-length", "root-close-missing"}:
        assert result["delivery"]["state"] == "complete"
    if expected["name"] == "complete-length":
        assert result["parse"]["state"] == "complete_json" and result["parse"]["truncated"]
    if expected.get("semantic_equal_to"):
        baseline_text = (EVIDENCE / expected["semantic_equal_to"]).read_text()
        baseline, _, _ = receive(baseline_text, {"name": "comparison", "finish_reason": "stop"}, frozen)
        assert result["analysis"] == baseline["analysis"]
        assert result["quality"] == baseline["quality"] and result["invalid_units"] == baseline["invalid_units"]

    prepared, _ = frozen
    for path, unit in actual.items():
        start, end = unit["value_span"]
        original_slice = text[start:end]
        assert json.loads(original_slice) == unit["value"]
        assert hashlib.sha256(original_slice.encode()).hexdigest() == unit["value_sha256"]
        assert unit["original_artifact_id"] == identity(expected["name"] + "/original")
        assert unit["original_content_path"] == "$.raw.choices[0].message.content"
        for ref in unit["resolved_refs"]:
            source = prepared["source_map"][ref["source_id"]]
            assert ref["ref"] == source["ref"] and ref["alert_ids"] == source.get("alert_ids", [])
    assert set(result["use"]["dispatch_paths"]) <= set(result["use"]["material_paths"]) <= set(actual)
    assert not any(result["use"][key] for key in ("conclusion_available", "adoption_eligible", "comparison_eligible"))
    assert result["quality"]["prose_quality"] == "not_checked"
    if out := os.environ.get("SOCAI2_D3_EVIDENCE_DIR"):
        folder = Path(out)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (expected["name"] + ".json")).write_text(json.dumps({
            "fixture": str(fixture.relative_to(ROOT)), "content_sha256": expected["fragment_sha256"],
            "checked_raw_units": len(actual), "stage_delivery": receipt, "derived_analysis": result["analysis"],
            "network_calls": 0, "database_calls": 0, "model_calls": 0}, ensure_ascii=False, indent=2) + "\n")


@pytest.mark.parametrize("fault", ["foreign_original", "wrong_content_path", "out_of_range_span", "changed_original", "unretained_dispatch"])
def test_receipt_cannot_claim_unavailable_or_changed_originals(frozen, fault):
    text = (EVIDENCE / "fixtures-01/complete-stop.txt").read_text()
    _, receipt, originals = receive(text, {"name": "receipt-protection", "finish_reason": "stop"}, frozen)
    first = receipt["retained_units"][0]
    if fault == "foreign_original":
        first["original_artifact_id"] = identity("foreign-original")
    elif fault == "wrong_content_path":
        first["original_content_path"] = "$.raw.choices[1].message.content"
    elif fault == "out_of_range_span":
        first["value_span"][1] = len(text) + 1
    elif fault == "changed_original":
        next(iter(originals.values()))["raw"]["choices"][0]["message"]["content"] += " "
    else:
        receipt["use"]["dispatch_paths"].append("$.not_retained[0]")
    with pytest.raises((ValueError, KeyError, IndexError)):
        stage_delivery.validate_sources(receipt, originals)
