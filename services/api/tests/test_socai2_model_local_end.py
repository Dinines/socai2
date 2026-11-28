"""S3 direct call-boundary checks using the existing ledger; no provider/database."""
import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from app.models import socai2 as models
from app.services.llm_safety import LLMInputContract
from app.socai2 import alert_basic_executor as alert
from app.socai2 import incident_diagnosis_executor as incident
from app.socai2.analysis_dispatch_types import (
    ExecutionFailure,
    classify_failure,
    model_dispatch_fact,
)
from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_failure import accounted_steps
from app.socai2.baseline_reasoning import ModelSteps
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_errors import (
    DEADLINE_BEFORE_DISPATCH,
    ModelCallError,
    provider_error,
)
from app.socai2.model_protocol import DEEPSEEK_PROTOCOL
from app.socai2.run_records import RunRecordLimits, RunRecordService
from app.socai2.stage_delivery import VERSION, validate_sources
from investigation_http.adapters.run_records import RunRecordBackend
from test_socai2_model_input_guard import FORMAT, Ledger, gateway, setup

__all__ = ["setup"]


@pytest.mark.parametrize("protocol", ["chat_completions", DEEPSEEK_PROTOCOL])
def test_exact_gateway_deadline_is_known_unsent(setup, protocol):
    with pytest.raises(ExecutionFailure) as caught:
        asyncio.run(gateway(protocol).complete({}, 0))
    failure = caught.value
    outcome = classify_failure(failure, stage="execute")
    assert failure.not_executed and not failure.temporary
    assert outcome.outcome == "failed" and outcome.error_code == DEADLINE_BEFORE_DISPATCH
    assert not outcome.retryable
    setup[1].assert_not_awaited()
    assert setup[2].calls == 0


def ai_call(monkeypatch, stage):
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

    async def call(value):
        executor = cls(ledger, gateway=value)
        if stage == "A":
            monkeypatch.setattr(executor, "background", AsyncMock(return_value={}))
        return await executor.execute(ledger.tenant_id, uuid4(), uuid4())

    return ledger, call


async def saved_local(ledger, state, dispatched, code):
    rows = ledger.tables[models.Artifacts.__tablename__]
    originals = {str(row["id"]): row["content_json"] for row in rows}
    receipt_row = next(row for row in rows if row["schema_version"] == VERSION)
    saved = validate_sources(receipt_row["content_json"], originals)
    assert saved.execution.call_state == state and saved.execution.request_dispatched is dispatched
    assert saved.execution.local_state == "ended" and saved.execution.local_ended_at
    assert not saved.execution.retry_allowed and saved.execution.error.code == code
    assert saved.parse.state == "no_response" and saved.delivery.state == "none"
    assert not saved.retained_units and not saved.use.conclusion_available and not saved.use.adoption_eligible
    assert not ledger.tables.get(models.Results.__tablename__)
    assert "s3-private-error-text" not in str(rows)
    model = next(row for row in ledger.tables[models.RunSteps.__tablename__] if row["kind"] == "model")
    assert model["state"] == state and bool(model["ended_at"]) is (state == "failed")
    assert model["error"]["request_dispatched"] is dispatched and model["error"]["code"] == code
    assert model["usage"]["total_tokens"] is None
    assert {o.artifact_id for o in saved.originals} == {model["input_artifact_id"], model["output_artifact_id"]}
    if ledger.run["kind"] != "case":
        assert saved.step_id == model["parent_step_id"]
        assert ledger.run["state"] == state and bool(ledger.run.get("ended_at")) is (state == "failed")
    response = originals[str(model["output_artifact_id"])]
    assert response.get("payload", response)["raw"] is None
    assert not any(row["content_json"].get(key) == "model_original_response"
        for row in rows for key in ("type", "artifact_role"))
    for row in rows:
        assert row["sha256"] == digest(row["content_json"]) and row["size_bytes"] == len(encoded(row["content_json"]))
    reader = RunRecordService(None, limits=RunRecordLimits(10, 20))
    reader.transaction = ledger.transaction
    backend = RunRecordBackend.__new__(RunRecordBackend)
    backend.reader = reader
    read = await backend.step(ledger.tenant_id, ledger.run["id"], model["id"])
    assert read["error"]["request_dispatched"] is dispatched and read["error"]["code"] == code
    assert {str(ref["artifact_id"]) for ref in read["artifact_refs"]} == {
        str(model["input_artifact_id"]), str(model["output_artifact_id"])}
    return model


@pytest.mark.parametrize("stage,error_type,state,code,dispatched,retryable", [
    ("A", httpx.ConnectTimeout, "failed", "service_unavailable", False, True),
    ("I", httpx.ReadTimeout, "unknown", "call_timeout", None, False),
    ("I", RuntimeError, "unknown", "execution_failed", None, False),
    ("A", TimeoutError, "unknown", "call_timeout", None, False),
])
def test_ai_call_failure_is_saved_read_and_propagated(setup, monkeypatch, caplog,
        stage, error_type, state, code, dispatched, retryable):
    monkeypatch.setattr(LLMInputContract, "validate", lambda messages: messages)
    post = AsyncMock(side_effect=error_type("s3-private-error-text"))
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    ledger, call = ai_call(monkeypatch, stage)

    async def check():
        with pytest.raises(ModelCallError if issubclass(error_type, httpx.HTTPError) else error_type) as caught:
            await call(gateway())
        outcome = classify_failure(caught.value, stage="execute")
        assert outcome.outcome == state and outcome.error_code == code and outcome.retryable is retryable
        await saved_local(ledger, state, dispatched, code)

    asyncio.run(check())
    assert post.await_count == 1 and "s3-private-error-text" not in caplog.text


def test_ai_zero_deadline_is_failed_without_post(setup, monkeypatch):
    setup[0].single_model_timeout_seconds = 0
    ledger, call = ai_call(monkeypatch, "I")

    async def check():
        result = await call(gateway())
        assert result["state"] == "failed" and result["stop_reason"] == DEADLINE_BEFORE_DISPATCH
        await saved_local(ledger, "failed", False, DEADLINE_BEFORE_DISPATCH)

    asyncio.run(check())
    setup[1].assert_not_awaited()


@pytest.mark.parametrize("stage", ["A", "case"])
def test_actual_task_cancellation_saves_local_end_then_propagates(setup, monkeypatch, stage, caplog):
    monkeypatch.setattr(LLMInputContract, "validate", lambda messages: messages)
    ledger, call = case_call(monkeypatch) if stage == "case" else ai_call(monkeypatch, stage)

    async def check():
        entered = asyncio.Event()

        async def suspended(*_args, **_kwargs):
            entered.set()
            await asyncio.Future()

        post = AsyncMock(side_effect=suspended)
        monkeypatch.setattr(httpx.AsyncClient, "post", post)
        task = asyncio.create_task(call(gateway()))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel("s3-private-error-text")
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled() and post.await_count == 1
        await saved_local(ledger, "unknown", None, "execution_unknown")
        if stage == "case":
            await assert_case_budget(ledger, not_executed=False)

    asyncio.run(check())
    assert "s3-private-error-text" not in caplog.text


async def assert_case_budget(ledger, *, not_executed):
    accounted = await accounted_steps(ledger, ledger.run["id"], ledger.tables[models.RunSteps.__tablename__])
    model = next(row for row in accounted if row["kind"] == "model")
    assert bool(model.get("not_executed")) is not_executed and model["reserved_tokens"] == 64
    assert model["usage"]["total_tokens"] is None
    limits = Limits.model_validate(ledger.run["limits"]).model_copy(update={"max_tokens": 64})
    reason = budget_reason(accounted, limits, 1, ledger.clock,
        measurement={"context_fits": True, "reserved_total_tokens": 64})
    assert reason == (None if not_executed else "model_token_budget_insufficient")


@pytest.mark.parametrize("error_type,code", [(RuntimeError, "execution_failed"), (httpx.ReadTimeout, "call_timeout")])
def test_case_unknown_call_keeps_local_receipt_and_reservation(setup, monkeypatch, caplog, error_type, code):
    monkeypatch.setattr(LLMInputContract, "validate", lambda messages: messages)
    post = AsyncMock(side_effect=error_type("s3-private-error-text"))
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    ledger, call = case_call(monkeypatch)

    async def check():
        if error_type is RuntimeError:
            with pytest.raises(RuntimeError):
                await call(gateway())
        else:
            result = await call(gateway())
            assert result[0] is None and result[1] == code
        await saved_local(ledger, "unknown", None, code)
        await assert_case_budget(ledger, not_executed=False)

    asyncio.run(check())
    assert post.await_count == 1 and "s3-private-error-text" not in caplog.text


@pytest.mark.parametrize("stage", ["A", "case"])
def test_schema_rejection_records_http_sent_and_keeps_existing_budget_treatment(setup, monkeypatch, stage):
    monkeypatch.setattr(LLMInputContract, "validate", lambda messages: messages)
    response = httpx.Response(400, json={"error": {"code": "invalid_schema"}},
        request=httpx.Request("POST", "https://model.invalid/"))
    post = AsyncMock(return_value=response)
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    ledger, call = case_call(monkeypatch) if stage == "case" else ai_call(monkeypatch, stage)

    async def check():
        result = await call(gateway())
        if stage == "case":
            assert result[0] is None and result[1] == "model_schema_rejected"
        else:
            assert result["state"] == "failed" and result["stop_reason"] == "model_schema_rejected"
        await saved_local(ledger, "failed", True, "model_schema_rejected")
        if stage == "case":
            await assert_case_budget(ledger, not_executed=True)

    asyncio.run(check())
    assert post.await_count == 1


@pytest.mark.parametrize("stage", ["I", "case"])
def test_failure_before_model_creation_does_not_fabricate_call_receipts(setup, monkeypatch, stage):
    ledger, call = case_call(monkeypatch) if stage == "case" else ai_call(monkeypatch, stage)
    value = gateway()
    value.configure = AsyncMock(side_effect=RuntimeError("s3-private-error-text"))
    with pytest.raises(RuntimeError):
        asyncio.run(call(value))
    assert not any(row["kind"] == "model" for row in ledger.tables[models.RunSteps.__tablename__])
    rows = ledger.tables[models.Artifacts.__tablename__]
    assert not any(row["kind"] in {"model_request", "model_response"} or row["schema_version"] == VERSION for row in rows)
    setup[1].assert_not_awaited()


def test_known_failure_without_dispatch_evidence_is_not_reported_as_sent():
    failure = ExecutionFailure("test_known_failure", stage="execute", known_failed=True, status_code=400)
    assert classify_failure(failure, stage="execute").outcome == "failed"
    assert model_dispatch_fact(failure) is None
    assert model_dispatch_fact(ValueError("s3-private-error-text")) is None
    response = httpx.Response(503, request=httpx.Request("POST", "https://model.invalid/"))
    failure = ModelCallError(provider_error(httpx.HTTPStatusError("s3-private-error-text",
        request=response.request, response=response), ""))
    assert model_dispatch_fact(failure) is True
    assert classify_failure(failure, stage="execute").outcome == "unknown"


def case_call(monkeypatch):
    ledger = Ledger("case", "local-end-test")
    owner = ledger.put(models.RunSteps.__table__, {"id": uuid4(), "run_id": ledger.run["id"], "kind": "stage",
        "stage_code": "C3", "state": "running", "seq": 1, "question_id": None})
    caller = ModelSteps(ledger, "local-end-test")
    monkeypatch.setattr(ModelSteps, "locked", AsyncMock(return_value=ledger.run))
    prepared = {"ready": True, "messages": [{"role": "user", "content": "{}"}], "source_map": {},
        "binding_map": {}, "input_artifact_ids": [str(ledger.run["input_artifact_id"])], "omissions": []}

    async def call(value):
        return await caller.call(ledger.tenant_id, ledger.run["case_id"], ledger.run["id"], owner["id"], "C3",
            prepared, value, lambda _: pytest.fail("no response to parse"), output_format=FORMAT)

    return ledger, call


def test_case_zero_deadline_saves_receipt_without_unknown_token_charge(setup, monkeypatch):
    ledger, call = case_call(monkeypatch)
    setup[0].single_model_timeout_seconds = 0

    async def check():
        outcome = await call(gateway())
        assert outcome[0] is None and outcome[1] == DEADLINE_BEFORE_DISPATCH
        rows = ledger.tables[models.Artifacts.__tablename__]
        originals = {str(row["id"]): row["content_json"] for row in rows}
        receipt = next(row["content_json"] for row in rows if row["schema_version"] == VERSION)
        saved = validate_sources(receipt, originals)
        assert saved.execution.call_state == "failed" and saved.execution.request_dispatched is False
        assert saved.execution.local_state == "ended" and not saved.execution.retry_allowed
        assert saved.parse.state == "no_response" and saved.delivery.state == "none"
        steps = ledger.tables[models.RunSteps.__tablename__]
        accounted = await accounted_steps(ledger, ledger.run["id"], steps)
        model = next(row for row in accounted if row["kind"] == "model")
        assert model["not_executed"] and model["reserved_tokens"] == 64
        assert model["usage"]["total_tokens"] is None
        limits = Limits.model_validate(ledger.run["limits"]).model_copy(update={"max_tokens": 64})
        assert budget_reason(accounted, limits, 1, ledger.clock,
            measurement={"context_fits": True, "reserved_total_tokens": 64}) is None
        assert not ledger.tables.get(models.Results.__tablename__)

    asyncio.run(check())
    setup[1].assert_not_awaited()
