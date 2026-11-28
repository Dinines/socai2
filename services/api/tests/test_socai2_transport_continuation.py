"""Direct transport ownership, immutable receipt and budget continuation checks."""
import asyncio
import copy
import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.db import clickhouse_owned as owned
from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_failure import accounted_steps, local_receipt, locally_ended
from app.socai2.baseline_store import StoreError, digest, encoded


@pytest.mark.parametrize("mode,expected", [
    ("reserved", None), ("missing", "prior_model_usage_unknown"),
    ("over_budget", "model_token_budget_insufficient"), ("unsent", None),
    ("inconsistent", "prior_model_usage_invalid"), ("parse_and_usage", "prior_model_usage_invalid"), ("reported", None)])
def test_unknown_usage_is_reserved_not_fabricated(mode, expected):
    now = datetime.now(UTC)
    step = {"kind": "model", "state": "unknown", "usage": {"usage_state": "unavailable"},
        "reserved_tokens": 60, "error": None}
    if mode == "missing":
        step.pop("reserved_tokens")
    if mode == "over_budget":
        step["reserved_tokens"] = 90
    if mode == "unsent":
        step.update(not_executed=True, reserved_tokens=1000)
    if mode == "inconsistent":
        step["error"] = {"code": "provider_usage_inconsistent"}
    if mode == "parse_and_usage":
        step["error"] = {"code": "model_response_not_complete", "usage_issue": "provider_usage_inconsistent"}
    if mode == "reported":
        step["usage"] = {"usage_state": "reported", "total_tokens": 10}
        step["reserved_tokens"] = 1000
    original = copy.deepcopy(step)
    limits = Limits(max_model_calls=4, max_tool_calls=2, max_tokens=100, max_rows_per_query=10,
        deadline_at=now + timedelta(seconds=100), policy_version="direct")
    assert budget_reason([step], limits, 0, now,
        measurement={"context_fits": True, "reserved_total_tokens": 20}) == expected
    assert step == original


@pytest.mark.parametrize("tamper", [None, "hash", "meter_body", "bound"])
def test_unknown_budget_uses_verified_persisted_request(tamper):
    step = {"id": uuid4(), "kind": "model", "state": "unknown", "input_artifact_id": uuid4(), "error": None}
    payload = {"body": {"messages": []}, "reserved_token_upper_bound": 70,
        "token_measurement": {"reserved_total_tokens": 70, "body_sha256": digest({"messages": []})}}
    if tamper == "meter_body":
        payload["body"] = {"messages": ["changed"]}
    if tamper == "bound":
        payload["reserved_token_upper_bound"] = True
    content = {"payload": payload}
    row = {"content_json": content, "sha256": "0" * 64 if tamper == "hash" else digest(content)}
    store = SimpleNamespace(one=AsyncMock(return_value=row), where=lambda table, *terms: terms)
    if tamper == "hash":
        with pytest.raises(StoreError, match="model_budget_request_invalid"):
            asyncio.run(accounted_steps(store, uuid4(), [step]))
    else:
        result = asyncio.run(accounted_steps(store, uuid4(), [step]))[0]
        assert result.get("reserved_tokens") == (70 if tamper is None else None)


def receipt_fixture():
    run = {"id": uuid4(), "case_id": uuid4(), "requested_by": uuid4()}
    request_id, response_id, step_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    step = {"id": step_id, "kind": "tool", "stage_code": "C4.query", "state": "unknown",
        "started_at": now - timedelta(seconds=1), "input_artifact_id": request_id, "output_artifact_id": response_id}
    request = {"scope": {"hostname": "host-a"}}
    rows = [{"observation": "完整业务行", "value": 0}]
    response = {"rows": rows, "received_rows_json": encoded(rows).decode()}
    store = SimpleNamespace(now=AsyncMock(return_value=now), save_input_artifact=AsyncMock())
    asyncio.run(local_receipt(store, run, step, (request_id, request), (response_id, response),
        code="query_transport_interrupted", dispatched=True, rows=rows))
    value = store.save_input_artifact.call_args.args[3]
    originals = {str(request_id): request, str(response_id): response}
    return run, step, value, originals


@pytest.mark.parametrize("tamper", [None, "old_unknown", "step", "source", "time", "span", "missing_request", "wrong_kind"])
def test_unknown_is_idle_only_with_its_actual_end_and_sources(tamper):
    run, step, value, originals = receipt_fixture()
    if tamper == "step":
        value["step_id"] = str(uuid4())
    if tamper == "time":
        value["execution"]["local_ended_at"] = (step["started_at"] - timedelta(seconds=1)).isoformat()
    if tamper == "span":
        value["retained_units"][0]["value_span"][1] -= 1
    if tamper == "missing_request":
        value["originals"] = [o for o in value["originals"] if o["kind"] != "request"]
    rows = [] if tamper == "old_unknown" else [{"content_json": value, "sha256": digest(value)}]
    async def one(statement):
        identity = next(v for k,v in statement.compile().params.items() if k.startswith("id_"))
        body = originals[str(identity)]
        return {"id": identity, "content_json": body, "sha256": "0" * 64 if tamper == "source" else digest(body),
            "kind": "model_response" if tamper == "wrong_kind" else
                "tool_request" if identity == step["input_artifact_id"] else "tool_response"}
    store = SimpleNamespace(db=SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(
        mappings=lambda: SimpleNamespace(all=lambda: rows)))), one=one, where=lambda table,*terms: terms)
    if tamper in {"step", "source", "time", "span", "missing_request", "wrong_kind"}:
        with pytest.raises(StoreError, match="local_end_"):
            asyncio.run(locally_ended(store, run["id"], step))
    else:
        assert asyncio.run(locally_ended(store, run["id"], step)) == (tamper is None)
        assert step["state"] == "unknown"


POLICY = {"query_timeout_seconds": 1, "connect_timeout_seconds": 1,
    "send_receive_timeout_seconds": 1, "close_timeout_seconds": 0.02}


@pytest.mark.parametrize("mode", ["normal", "disconnect", "timeout", "cancel"])
def test_owned_query_waits_for_actual_worker_exit(monkeypatch, mode):
    began, unblock, finished, close_called = (threading.Event() for _ in range(4))
    class Driver:
        def execute_iter(self, *args, **kwargs):
            try:
                yield [("observation", "String")]
                yield ("kept row",)
                began.set()
                if mode == "disconnect":
                    raise ConnectionResetError("controlled disconnect")
                if mode in {"timeout", "cancel"}:
                    unblock.wait(5)
            finally:
                finished.set()
        def disconnect(self):
            close_called.set()
    monkeypatch.setattr(owned, "owned_client", lambda p: Driver())
    async def run():
        task = asyncio.create_task(owned.execute_owned("SELECT explicit", policy=POLICY,
            timeout_seconds=2, extra_settings=None, params={}, query_id="controlled"))
        if mode in {"timeout", "cancel"}:
            assert await asyncio.to_thread(began.wait, 2)
            if mode == "cancel":
                task.cancel()
            assert await asyncio.to_thread(close_called.wait, 2)
            await asyncio.sleep(0.04)
            assert not task.done() and not finished.is_set()
            unblock.set()
        if mode in {"disconnect", "timeout"}:
            with pytest.raises(owned.LakeQueryInterrupted) as caught:
                await task
            assert caught.value.rows == [["kept row"]] and caught.value.columns == ["observation"]
        elif mode == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            result = await task
            assert result.rows == [["kept row"]]
        assert finished.is_set() and close_called.is_set()
    asyncio.run(run())
