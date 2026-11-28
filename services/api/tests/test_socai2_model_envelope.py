"""S2 response-envelope checks; reuse S1's local ledger, never call a provider/database."""
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from app.models import socai2 as models
from app.services.llm_safety import LLMInputContract, safe_chat_completions_request
from app.socai2 import alert_basic_executor as alert
from app.socai2 import case_c3_completion_flow as completion
from app.socai2 import incident_diagnosis_executor as incident
from app.socai2.analysis_dispatch_types import classify_failure
from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_failure import accounted_steps
from app.socai2.baseline_reasoning import ModelSteps
from app.socai2.baseline_store import digest, encoded
from app.socai2.citation_quality import new_review
from app.socai2.model_errors import (
    RESPONSE_ENVELOPE_INVALID,
    ModelCallError,
    decode_response,
)
from app.socai2.model_protocol import DEEPSEEK_PROTOCOL, prepare_request
from app.socai2.run_records import RunRecordLimits, RunRecordService
from app.socai2.stage_delivery import VERSION, validate_sources
from investigation_http.adapters.run_records import RunRecordBackend
from test_socai2_model_input_guard import (
    FORMAT,
    Ledger,
    gateway,
    setup,
)

__all__ = ["setup"]  # Re-export the existing pytest fixture for this module.


def response_substitute(monkeypatch, body=b'{"s2-body-must-not-leak":', status=200):
    monkeypatch.setattr(LLMInputContract, "validate", lambda messages: messages)
    response = httpx.Response(status, content=body, request=httpx.Request("POST", "https://model.invalid/"))
    post = AsyncMock(return_value=response)
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    return post, body


@pytest.mark.parametrize("protocol", ["chat_completions", DEEPSEEK_PROTOCOL])
@pytest.mark.parametrize("body", [b'{"s2-body-must-not-leak":', b'[["s2-body-must-not-leak", 1]]'])
def test_received_envelope_is_typed_at_decode_and_never_retried(setup, monkeypatch, protocol, body, caplog):
    post, _ = response_substitute(monkeypatch, body)
    value = gateway(protocol)
    request = prepare_request(value, {"model": value.model, "messages": [], "max_tokens": 32,
                                     "temperature": 0, "response_format": FORMAT})
    with pytest.raises(ModelCallError) as failed:
        asyncio.run(value.complete(request, 30))
    failure = failed.value
    assert failure.envelope_code == RESPONSE_ENVELOPE_INVALID and not failure.rejection_code
    assert failure.details["response_received"] is True and failure.details["http_status"] == 200
    assert failure.details["response_bytes"] == len(body)
    assert failure.details["response_sha256"] == hashlib.sha256(body).hexdigest()
    assert failure.details["body_state"] in {"non_json_omitted", "unsupported_shape_omitted"}
    assert not failure.details["fields"]
    assert failure.payload()["raw"] is None and "s2-body-must-not-leak" not in str(failure.payload())
    assert "s2-body-must-not-leak" not in caplog.text
    outcome = classify_failure(failure, stage="execute")
    assert outcome.outcome == "failed" and not outcome.retryable and outcome.error_code == RESPONSE_ENVELOPE_INVALID
    assert post.await_count == 1 and "response_decoder" not in post.await_args.kwargs["json"]


def test_scalar_body_is_omitted_and_successful_object_is_unchanged():
    response = httpx.Response(200, content=b'"s2-body-must-not-leak"')
    with pytest.raises(ModelCallError) as failed:
        decode_response(response, "")
    assert failed.value.details["body_state"] == "unsupported_shape_omitted"
    assert not failed.value.details["fields"] and "s2-body-must-not-leak" not in str(failed.value.payload())
    assert decode_response(httpx.Response(200, json={"choices": [], "usage": None}), "") == {"choices": [], "usage": None}


def test_decoder_recursion_failure_is_still_a_received_envelope(monkeypatch):
    response = httpx.Response(200, content=b"{}")
    monkeypatch.setattr(response, "json", lambda: (_ for _ in ()).throw(RecursionError()))
    with pytest.raises(ModelCallError) as failed:
        decode_response(response, "")
    assert failed.value.envelope_code == RESPONSE_ENVELOPE_INVALID
    assert failed.value.details["exception_type"] == "RecursionError"


def test_shared_default_decoder_and_http_failure_behavior_are_unchanged(setup, monkeypatch):
    post, _ = response_substitute(monkeypatch, b'[["existing_default_shape", true]]')
    received = asyncio.run(safe_chat_completions_request(api_key="", model="test", messages=[], url="https://model.invalid/"))
    assert received == {"existing_default_shape": True} and post.await_count == 1
    post, _ = response_substitute(monkeypatch, status=400)
    value = gateway()
    with pytest.raises(ModelCallError) as failed:
        asyncio.run(value.complete({"model": value.model, "messages": [], "max_tokens": 32, "response_format": FORMAT}, 30))
    assert failed.value.envelope_code is None and classify_failure(failed.value, stage="execute").error_code == "invalid_input"
    assert post.await_count == 1


def saved_failures(ledger):
    rows = ledger.tables[models.Artifacts.__tablename__]
    originals = {str(row["id"]): row["content_json"] for row in rows}
    receipts = [row for row in rows if row["schema_version"] == VERSION]
    assert receipts
    for row in receipts:
        value = validate_sources(row["content_json"], originals)
        assert value.execution.call_state == "failed" and value.execution.request_dispatched is True
        assert value.execution.local_state == "ended" and not value.execution.retry_allowed
        assert value.parse.state == "unusable" and value.delivery.state == "none"
        assert not value.retained_units and not value.use.conclusion_available
        assert row["sha256"] == digest(row["content_json"]) and row["size_bytes"] == len(encoded(row["content_json"]))
    assert not ledger.tables.get(models.Results.__tablename__)
    assert "s2-body-must-not-leak" not in str(rows)
    responses = [row for row in rows if row["kind"] == "model_response"]
    assert len(responses) == 1
    value = responses[0]["content_json"]
    local = value.get("payload", value)
    assert local["raw"] is None and local["validation_error"] == RESPONSE_ENVELOPE_INVALID
    assert local["transport_error"]["response_received"] is True
    assert not any(row["content_json"].get("type") == "model_original_response" for row in rows)
    return receipts


@pytest.mark.parametrize("stage", ["A", "I"])
def test_actual_ai_received_failure_saves_and_reads_without_result(setup, monkeypatch, stage):
    post, _ = response_substitute(monkeypatch)
    module, cls, kind = (alert, alert.AlertBasicExecutor, "alert_basic") if stage == "A" else (
        incident, incident.IncidentDiagnosisExecutor, "incident_diagnosis")
    ledger = Ledger(kind, module.VERSION)
    data = {"members": [], "omissions": [], "view_limitations": [], "view_coverage": {},
        "omission_details": [], "omission_detail_count": 0, "omission_details_truncated": False}
    prepared = {"boundary": {}, "severity_opinion_version": "test", "business_verdict_version": "test"}
    build = lambda *_args, **_kwargs: ([{"role": "user", "content": "{}"}], {}, data, prepared)
    if stage == "A":
        monkeypatch.setattr(module, "build", build)
        monkeypatch.setattr(module, "schema", lambda *_: FORMAT)
    else:
        monkeypatch.setattr(module.incident_model_boundary, "build", build)
        monkeypatch.setattr(module.incident_output_adapter, "candidate_schema", lambda *_: FORMAT["json_schema"]["schema"])
    executor = cls(ledger, gateway=gateway())
    if stage == "A":
        monkeypatch.setattr(executor, "background", AsyncMock(return_value={}))

    async def check():
        result = await executor.execute(ledger.tenant_id, uuid4(), uuid4())
        assert result["state"] == "failed" and result["stop_reason"] == RESPONSE_ENVELOPE_INVALID
        receipts = saved_failures(ledger)
        model = next(row for row in ledger.tables[models.RunSteps.__tablename__] if row["kind"] == "model")
        assert model["state"] == "failed" and model["ended_at"] and model["usage"]["total_tokens"] is None
        assert str(model["parent_step_id"]) == receipts[0]["content_json"]["step_id"]
        refs = {r["artifact_id"] for r in receipts[0]["content_json"]["originals"]}
        assert refs == {str(model["input_artifact_id"]), str(model["output_artifact_id"])}
        reader = RunRecordService(None, limits=RunRecordLimits(10, 20))
        reader.transaction = ledger.transaction
        backend = RunRecordBackend.__new__(RunRecordBackend)
        backend.reader = reader
        read = await backend.step(ledger.tenant_id, ledger.run["id"], model["id"])
        assert read["error"]["request_dispatched"] is True and read["error"]["code"] == RESPONSE_ENVELOPE_INVALID
        assert {str(ref["artifact_id"]) for ref in read["artifact_refs"]} == refs
        before = len(ledger.tables[models.Artifacts.__tablename__])
        await executor.execute(ledger.tenant_id, uuid4(), uuid4())
        assert len(ledger.tables[models.Artifacts.__tablename__]) == before

    asyncio.run(check())
    assert post.await_count == 1


@pytest.mark.parametrize("stage", ["C3", "C4.deep", "C6"])
def test_case_received_failure_preserves_budget_and_c3_unusable(setup, monkeypatch, stage):
    post, _ = response_substitute(monkeypatch)
    ledger = Ledger("case", "envelope-test")
    owner = ledger.put(models.RunSteps.__table__, {"id": uuid4(), "run_id": ledger.run["id"], "kind": "stage",
        "stage_code": stage, "state": "running", "seq": 1, "question_id": None})
    caller = ModelSteps(ledger, "envelope-test")
    monkeypatch.setattr(ModelSteps, "locked", AsyncMock(return_value=ledger.run))
    prepared = {"ready": True, "messages": [{"role": "user", "content": "{}"}], "source_map": {},
        "binding_map": {}, "input_artifact_ids": [str(ledger.run["input_artifact_id"])], "omissions": []}

    async def check():
        outcome = await caller.call(ledger.tenant_id, ledger.run["case_id"], ledger.run["id"], owner["id"], stage,
            prepared, gateway(), lambda _: pytest.fail("invalid envelope must not reach content parsing"), output_format=FORMAT)
        assert outcome[0] is None and outcome[1] == RESPONSE_ENVELOPE_INVALID and ledger.run["state"] == "running"
        saved_failures(ledger)
        steps = ledger.tables[models.RunSteps.__tablename__]
        accounted = await accounted_steps(ledger, ledger.run["id"], steps)
        model = next(row for row in accounted if row["kind"] == "model")
        assert not model.get("not_executed") and model["reserved_tokens"] == 64 and model["usage"]["total_tokens"] is None
        limits = Limits.model_validate(ledger.run["limits"]).model_copy(update={"max_tokens": 64})
        assert budget_reason(accounted, limits, 1, ledger.clock,
            measurement={"context_fits": True, "reserved_total_tokens": 64}) == "model_token_budget_insufficient"
        if stage == "C3":
            policy = json.loads((Path(__file__).parents[1] / "app/socai2/case-input-v1.json").read_text())["c3_completion"]
            policy["system"] = "test"
            prepared.update(citation_review=new_review(), input_view_id=str(ledger.run["input_artifact_id"]),
                            case_boundary={"c3_completion": policy})
            monkeypatch.setattr(completion.units, "receive", lambda *_: {"analysis": {}, "closed_sections": [],
                "delivery": {"state": "none", "reasons": [RESPONSE_ENVELOPE_INVALID]},
                "parse": {"state": "no_response", "truncated": False, "reasons": []},
                "retained_units": [], "missing_units": [], "invalid_units": [], "quality": new_review(),
                "use": {"material_paths": [], "dispatch_paths": [], "conclusion_available": False,
                        "adoption_eligible": False, "comparison_eligible": False, "reasons": []}})
            await completion.complete_sections(ledger, ledger.tenant_id, ledger.run["case_id"], ledger.run["id"],
                owner["id"], prepared, SimpleNamespace(), {}, FORMAT, gateway(), outcome, schema=caller.schema)
            assert prepared["section_completion_result"]["attempts"] == 0
            assert prepared["section_completion_result"]["state"] == "skipped"
            saved_failures(ledger)

    asyncio.run(check())
    assert post.await_count == 1
