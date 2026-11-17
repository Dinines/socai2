"""D3a: real-response mother, closed units and exact saved-source receipts."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from app.socai2 import case_c3_delivery as receiver
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import digest
from app.socai2.case_c3_sections import read_units
from app.socai2.runtime_policy import validate_c3_completion
from app.socai2.stage_delivery import VERSION, validate_sources
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "docs/operations/evidence/test-c3-continuation-d3-20261116-01/fixtures-01"


@pytest.fixture
def mother():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    database = json.loads((ROOT / manifest["source_batch"] / "database.json").read_text())
    artifacts = {a["id"]: a["content_json"] or {} for a in database["artifacts"]}
    prepared = copy.deepcopy(artifacts[manifest["request_artifact_id"]]["payload"])
    context = Context.model_validate(next(v for v in artifacts.values() if "case_input_profile" in v))
    model_view = next(v for v in artifacts.values() if "coverage" in v and "case_boundary" in v)
    prepared["coverage"] = copy.deepcopy(model_view["coverage"])
    for aid, coverage in prepared["coverage"].items():
        coverage["included"] = sum(aid in r["alert_ids"] for r in prepared["source_map"].values())
    text = (FIXTURES / "mother.txt").read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == manifest["mother_sha256"]
    return text, prepared, context


def receive(text, prepared, context, **kwargs):
    return receiver.receive(text, prepared, context, prepared["binding_map"], uuid4(), **kwargs)


@pytest.mark.parametrize("name", ["complete-stop", "complete-length", "f1-closed-f2-partial",
    "root-close-missing", "empty", "random-1", "random-2", "random-3"])
def test_closed_units_match_independently_frozen_spans(mother, name):
    _, prepared, context = mother
    text = (FIXTURES / (name + ".txt")).read_text()
    expected = json.loads((FIXTURES / (name + ".expected.json")).read_text())
    scanned = read_units(text)
    actual = receive(text, prepared, context, finish_reason=expected["finish_reason"])
    want = expected["lexically_complete_original_units"]
    assert [(u["path"], u["value_span"], u["value"]) for u in scanned["units"]] == [
        (u["path"], u["value_span"], u["value"]) for u in want]
    assert [(u["path"], u["value_sha256"], u["value"]) for u in actual["retained_units"]] == [
        (u["path"], u["value_sha256"], u["value"]) for u in want]
    assert actual["invalid_units"] == []
    if name in {"complete-stop", "complete-length", "root-close-missing"}:
        assert actual["delivery"]["state"] == "complete"
        assert len(actual["analysis"]["questions"]) == 6  # Separate program-owned coverage.
    else:
        assert actual["delivery"]["state"] == ("none" if not want else "partial")
        assert "followups" not in actual["analysis"] and actual["use"]["dispatch_paths"] == []
    if name == "f1-closed-f2-partial":
        assert [f["id"] for f in actual["analysis"]["findings"]] == ["F1"]
        assert "questions" not in actual["analysis"] and "domains" not in actual["analysis"]
        assert actual["analysis"]["findings"][0]["statement"]  # Restored field, not authored text.
        assert "statement" not in actual["retained_units"][-1]["value"]
    if name == "complete-length":
        assert actual["parse"]["state"] == "complete_json" and actual["parse"]["truncated"]


def test_json_property_order_does_not_change_dependency_diagnostics(mother):
    text, prepared, context = mother
    raw = json.loads(text)
    reordered = {k: raw[k] for k in ("domains", "conflicts", "summary", "members", "questions", "findings", "followups")}
    initial = receive(text, prepared, context)
    changed = receive(json.dumps(reordered, ensure_ascii=False), prepared, context)
    assert changed["analysis"] == initial["analysis"]
    assert changed["quality"] == initial["quality"] and changed["invalid_units"] == []


def test_duplicate_definitions_and_over_limit_are_explicit_partial_delivery(mother):
    text, prepared, context = mother
    raw = json.loads(text)
    raw["findings"][1]["id"] = raw["findings"][0]["id"]
    result = receive(json.dumps(raw), prepared, context)
    assert [u["path"] for u in result["invalid_units"]] == ["$.findings[0]", "$.findings[1]"]
    assert all(f["id"] != "F1" for f in result["analysis"]["findings"])
    raw = json.loads(text)
    raw["findings"].append({**copy.deepcopy(raw["findings"][-1]), "id": "F6"})
    original = copy.deepcopy(raw)
    result = receive(json.dumps(raw), prepared, context)
    assert result["invalid_units"] == [{"path": "$.findings[5]", "reason_code": "section_item_limit_exceeded"}]
    assert len(result["analysis"]["findings"]) == 5 and raw == original
    assert result["delivery"]["state"] == "partial"


def test_missing_question_retains_plan_but_does_not_dispatch(mother):
    text, prepared, context = mother
    raw = json.loads(text)
    qid = raw["followups"][0]["question_id"]
    raw["questions"] = [q for q in raw["questions"] if q["id"] != qid]
    result = receive(json.dumps(raw), prepared, context)
    assert result["analysis"]["followups"]
    assert "$.followups[0]" in result["use"]["material_paths"]
    assert "$.followups[0]" not in result["use"]["dispatch_paths"]


@pytest.mark.parametrize("text,paths", [
    ('{"summary":"保留\\n\\\"原文\\u0030","findings":[1e', ["$.summary"]),
    ('{"summary":"原文","findings":[true', ["$.summary"]),
    ('{"summary":"原文","findings":[false ', ["$.summary"]),
    ('{"summary":"first","summary":"second"}', []),
    ('{"summary":"原文","findings":[{"id":"F1","id":"F2"}]}', ["$.summary"]),
    ('{"summary":"原文","findings":[],"followups":', ["$.summary", "$.findings"]),
])
def test_ambiguous_units_are_not_repaired(text, paths):
    assert [u["path"] for u in read_units(text)["units"]] == paths


def test_strict_receipt_checks_saved_original_and_each_unit_span(mother):
    text, prepared, context = mother
    original_id, input_id, run_id, step_id = [uuid4() for _ in range(4)]
    original = {"raw": {"choices": [{"message": {"content": text}}]}}
    result = receiver.receive(text, prepared, context, prepared["binding_map"], original_id)
    receipt = {"schema_version": VERSION, "type": "stage_delivery", "run_id": str(run_id),
        "step_id": str(step_id), "stage": "C3", "input_artifact_id": str(input_id),
        "originals": [{"artifact_id": str(original_id), "kind": "response", "sha256": digest(original)}],
        "execution": {"kind": "model", "call_state": "completed", "local_state": "ended",
            "local_ended_at": datetime.now(timezone.utc).isoformat(), "request_dispatched": True,
            "finish_reason": "stop", "error": None, "retry_allowed": False, "retry_reason": "no_retry_needed"},
        **{key: result[key] for key in ("parse", "delivery", "retained_units", "missing_units", "invalid_units", "quality", "use")}}
    originals = {str(original_id): original}
    assert validate_sources(receipt, originals).delivery.state == "complete"
    for field, value in (("value", "changed"), ("value_sha256", "0" * 64), ("value_span", [0, 1])):
        changed = copy.deepcopy(receipt)
        changed["retained_units"][0][field] = value
        with pytest.raises(ValueError):
            validate_sources(changed, originals)
    changed = copy.deepcopy(receipt)
    changed["use"]["dispatch_paths"].append("$.missing[0]")
    with pytest.raises(ValidationError):
        validate_sources(changed, originals)
    changed = copy.deepcopy(receipt)
    changed["unknown_field"] = True
    with pytest.raises(ValidationError):
        validate_sources(changed, originals)


def test_existing_response_protocol_locates_the_actual_raw_text(mother):
    from app.socai2.model_protocol import response_choices, response_content_path
    from app.socai2.stage_delivery import original_value
    text, prepared, context = mother
    payload = {"object": "response", "status": "completed", "output": [
        {"type": "reasoning"}, {"type": "message", "role": "assistant", "status": "completed",
         "content": [{"type": "output_text", "text": text}]}]}
    location = response_content_path(payload)
    assert original_value({"raw": payload}, location) == response_choices(payload)[0]["message"]["content"] == text
    result = receiver.receive(text, prepared, context, prepared["binding_map"], uuid4(), original_content_path=location)
    assert result["delivery"]["state"] == "complete"
    assert all(u["original_content_path"] == "$.raw.output[1].content[0].text" for u in result["retained_units"])


@pytest.mark.parametrize("count", [0, 1, 2, True])
def test_completion_policy_is_zero_or_one(mother, count):
    _, prepared, _ = mother
    policy = copy.deepcopy(prepared["case_boundary"]["c3_completion"])
    policy["max_attempts"] = count
    if type(count) is int and count in (0, 1):
        validate_c3_completion(policy, frozen=True)
    else:
        with pytest.raises(ValueError):
            validate_c3_completion(policy, frozen=True)
