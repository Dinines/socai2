"""Execute real model-step code against an explicit in-memory ledger substitute.

This checks dispatch/persistence/budget behavior, not PostgreSQL transactions or
model judgment quality. Inputs are the frozen two-member full-wire packets.
"""
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.baseline_capacity import final_reservation
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import FULL_EXECUTOR_VERSION, Limits
from app.socai2.baseline_reasoning import ModelSteps
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format


@pytest.mark.parametrize("protocol", ["chat_completions", "deepseek_responses"])
def test_shared_call_path_dispatches_two_deep_and_final_exact_wire_with_reserved_time(protocol):
    from diagnose_socai2_kafka_inputs_20261105 import DIRECTORY, one
    db = json.loads(max(DIRECTORY.glob("database-*.json")).read_text())
    run = next(r for r in db["runs"] if r["stop_reason"] == "required_model_input_unavailable"
        and any(s["run_id"] == r["id"] and s["stage_code"] == "C4.deep" for s in db["run_steps"]))
    rows = [a for a in db["artifacts"] if a["run_id"] == run["id"] and isinstance(a["content_json"], dict)]
    context = Context.model_validate(next(a["content_json"] for a in rows if a["schema_version"] == "socai2.baseline-context.v1"))
    stage_ids = {s["id"] for s in db["run_steps"] if s["run_id"] == run["id"] and s["stage_code"] == "C4.deep"}
    original = next(a["content_json"]["payload"] for a in rows if a["kind"] == "model_request" and a["step_id"] in stage_ids)
    frozen = original["body"]
    fmt = frozen["text"]["format"]
    deep_format = {"type": "json_schema", "json_schema": {k: v for k, v in fmt.items() if k != "type"}}
    deep_prepared = {"ready": True, "messages": frozen["input"], "source_map": original["source_map"],
        "input_artifact_ids": original["input_artifact_ids"], "omissions": []}
    final_prepared = asyncio.run(one(db, run))["prepared"]
    final_prepared["input_artifact_ids"] = [str(uuid4())]
    final_format = response_format(delivery.Delivery, final_prepared["source_map"], members=context.alerts,
        questions=[q.id for q in context.questions], objects=context.scope.object_keys)

    class Ledger:
        tenant_id = UUID(run["tenant_id"])
        owner = None
        def __init__(self):
            self.db = self
            self.requests, self.responses = [], []
            self.steps = [{"id": uuid4(), "kind": "model", "state": "completed", "stage_code": "C3",
                "usage": {"usage_state": "reported", "total_tokens": 1000}}]
        def where(self, _table, *conditions):
            return conditions
        async def now(self):
            return context.captured_at
        async def one(self, query):
            return self.plan if query.get_final_froms()[0].name == "artifacts" else self.owner
        async def execute(self, query):
            if query.is_select:
                return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: copy.deepcopy(self.steps)))
            params = query.compile().params
            if query.is_insert:
                self.steps.append({**params, "usage": None})
            elif query.is_update:
                target = next(s for s in self.steps if s["id"] == params["id_1"])
                target.update({k: v for k, v in params.items() if k != "id_1"})
            return SimpleNamespace()

    ledger = Ledger()
    class Gateway:
        provider, model, schema_profile = protocol, "deepseek-flash", "standard"
        async def configure(self, *_):
            return True
        async def complete(self, body, timeout):
            assert body == ledger.requests[-1]["payload"]["body"]
            assert 0 < timeout <= (120 if ledger.owner["stage_code"] == "C6" else 90)
            if protocol == "deepseek_responses":
                return {"object": "response", "id": "substitute", "status": "completed", "error": None,
                    "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": '{"synthetic":true}'}]}],
                    "usage": {"input_tokens": 500, "output_tokens": 500, "total_tokens": 1000}}
            return {"choices": [{"finish_reason": "stop", "message": {"content": '{"synthetic":true}'}}],
                "usage": {"prompt_tokens": 500, "completion_tokens": 500, "total_tokens": 1000}}
    gateway = Gateway()
    reserve = final_reservation(gateway, context)
    plan_id = uuid4()
    ledger.plan = {"content_json": {"final_reservation": reserve}}
    ledger.plan["sha256"] = digest(ledger.plan["content_json"])
    ledger.steps.insert(0, {"id": uuid4(), "kind": "stage", "state": "completed", "stage_code": "C1.executor", "output_artifact_id": plan_id})
    limits = Limits(max_model_calls=4, max_tokens=48000, max_tool_calls=4, max_rows_per_query=50,
        deadline_at=context.captured_at + timedelta(seconds=120), policy_version="local-v2-ledger-substitute")
    current = {**run, "id": UUID(run["id"]), "case_id": UUID(run["case_id"]), "state": "running",
        "executor_version": FULL_EXECUTOR_VERSION, "limits": limits.model_dump(mode="json")}
    @asynccontextmanager
    async def transaction(_):
        yield ledger
    class Calls(ModelSteps):
        async def locked(self, *_):
            return current
        async def idle(self, *_):
            return None
        async def seq(self, *_):
            return len(ledger.steps) + 1
        async def save(self, _store, _run, _step, payload, kind, refs=()):
            (ledger.requests if kind == "model_request" else ledger.responses).append(copy.deepcopy(payload))
            return uuid4()
    caller = Calls(SimpleNamespace(transaction=transaction), "synthetic-model-step-test")
    async def execute():
        for stage, prepared, output in [("C4.deep", deep_prepared, deep_format),
                ("C4.deep", deep_prepared, deep_format), ("C6", final_prepared, final_format)]:
            ledger.owner = {"id": uuid4(), "stage_code": stage, "question_id": "execution_fixture"}
            parsed, reason, _, _ = await caller.call(ledger.tenant_id, current["case_id"], current["id"],
                ledger.owner["id"], stage, copy.deepcopy(prepared), gateway, json.loads, output_format=output)
            assert parsed == {"synthetic": True} and reason is None
        attempts = [s for s in ledger.steps if s["kind"] == "model"]
        assert len(attempts) == 4 and sum(s["usage"]["total_tokens"] for s in attempts) == 4000
    asyncio.run(execute())
    expected_final = prepare_request(gateway, {"model": gateway.model, "messages": final_prepared["messages"],
        "max_tokens": 3000, "temperature": 0, "response_format": final_format})
    assert ledger.requests[-1]["payload"]["body"] == expected_final
    assert all(r["payload"]["reserved_token_upper_bound"] == len(encoded(r["payload"]["body"])) + 3256 for r in ledger.requests)
    assert [r["usage"]["total_tokens"] for r in ledger.responses] == [1000, 1000, 1000]
