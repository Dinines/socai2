"""Zero-dependency integrity probes; never import or execute service startup.

Production functions are extracted verbatim from their ASTs. Their dependencies
are explicit in-memory doubles: no SDK, network, PostgreSQL, Kafka or model.
This verifies branch/composition behavior, not a deployed failure or acceptance.
"""
from __future__ import annotations

import ast
import asyncio
import copy
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import time
from types import SimpleNamespace
from uuid import UUID


ROOT = Path(__file__).resolve().parents[4]
SOURCES: dict[str, dict] = {}


def extract(relative: str, names: list[str], namespace: dict) -> dict:
    path = ROOT / relative
    raw = path.read_bytes()
    tree = ast.parse(raw.decode())
    found = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in names
    }
    assert set(found) == set(names)
    SOURCES[relative] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "functions": {
            name: {"start_line": found[name].lineno, "end_line": found[name].end_lineno}
            for name in names
        },
    }
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *[found[name] for name in names],
    ], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    return namespace


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *_):
        return False


class NullLogger:
    def __getattr__(self, _):
        return lambda *args, **kwargs: None


class PersistError(Exception):
    pass


class Status(Enum):
    RUNNING = "running"
    COMPLETED = "completed"


async def noop(*args, **kwargs):
    return None


async def probe() -> dict:
    state = SimpleNamespace(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
        status=Status.RUNNING,
    )
    state.model_copy = lambda **kwargs: state
    calls = {"persist": 0, "escalate": 0, "lookup": 0}

    async def record(*args, **kwargs):
        calls["persist"] += 1

    async def escalate(*args, **kwargs):
        calls["escalate"] += 1

    projection = {"verdict": "true_positive", "confidence": .9, "tier": "llm"}
    worker_ns = extract("services/agents/app/workers/fused_alert_consumer.py",
                        ["triage", "_save_pending"], {
        "deepcopy": copy.deepcopy,
        "build_state": lambda _: state,
        "ledger_module": SimpleNamespace(LedgerPersistError=PersistError),
    })
    key = (str(state.run_id), str(state.tenant_id))
    pending = {key: SimpleNamespace(
        state=state, tier="llm", verdict="true_positive", confidence=.9,
        tokens=18, cost={}, writer=SimpleNamespace(escalation_allowed=True),
        projection=projection, saving=False,
    )}
    worker = SimpleNamespace(
        _uses_delivery_guard=lambda: True,
        _review_only=lambda: False,
        _pending=lambda: pending,
        _record=record,
        _maybe_escalate=escalate,
    )
    worker._save_pending = lambda saved_key: worker_ns["_save_pending"](worker, saved_key)
    assert await worker_ns["triage"](worker, {}) == projection
    assert calls["persist"] == 1 and calls["escalate"] == 0 and not pending
    warm = {"persist_calls": 1, "escalation_calls": 0, "returned_first_triage": True}

    async def lookup(**kwargs):
        calls["lookup"] += 1
        return copy.deepcopy(projection)

    worker_ns["triage_delivery"] = SimpleNamespace(lookup=lookup)
    worker._delivery_fields = lambda _: {}
    worker._review_prior = lambda result, *args, **kwargs: result
    assert await worker_ns["triage"](worker, {}) == projection
    assert calls["lookup"] == 1 and calls["escalate"] == 0
    cold = {"lookup_calls": 1, "escalation_calls": 0, "returned_first_triage": True}

    run = {
        "model_used": "kafka:auto_triage:llm", "total_tokens": 18,
        "measured_call_count": 0, "estimated_call_count": 0,
        "unpriced_call_count": 1, "total_cost_usd": 0, "estimated_cost_usd": 0,
    }

    class Connection:
        async def execute(self, sql, *args):
            assert "UPDATE investigation_runs" in sql
            run.update(total_tokens=args[4], measured_call_count=args[6],
                       estimated_call_count=args[8], unpriced_call_count=args[9])

    pool = SimpleNamespace(acquire=lambda: AsyncContext(Connection()))

    async def get_pool():
        return pool

    ledger_ns = extract("services/agents/app/investigator/ledger.py", ["complete_run"], {
        "get_pool": get_pool, "_set_rls_context": noop, "logger": NullLogger(),
    })

    class Model:
        @staticmethod
        def model_validate(_):
            return state

    state.incident_id = "33333333-3333-3333-3333-333333333333"
    state.alert_summary, state.raw_alert = "probe", {}
    state.error, state.iteration_count = None, 3
    state.to_dict = lambda: {}

    async def resolve(*args):
        return state.tenant_id

    runner_ns = extract("services/agents/app/graph/runner.py", ["_run"], {
        "asyncio": asyncio, "time": time,
        "ledger_module": SimpleNamespace(resolve_tenant=resolve, start_run=noop,
                                          complete_run=ledger_ns["complete_run"]),
        "InvestigationState": Model, "logger": NullLogger(),
    })

    class NoopGraph:
        async def astream(self, _):
            if False:
                yield {}

    await runner_ns["_run"](NoopGraph(), state,
                            budget=SimpleNamespace(max_seconds=5), persist=True, seq_start=1)
    assert run["total_tokens"] == 0 and run["unpriced_call_count"] == 0
    recovery = {
        "schema_version": 1, "workflow_version": "auto-triage-v1",
        "run_id": str(state.run_id), "tenant_id": str(state.tenant_id),
        "alert_id": state.incident_id, "incident_id": state.incident_id,
        "shadow": False, "tier": "llm", "verdict": "true_positive", "confidence": .9,
        "findings": [], "proposed_actions": [], "confidence_basis": [],
        "business_context_rules": [], "business_context_policy": {},
        "cost": {"measured_calls": 0, "estimated_calls": 0, "unpriced_calls": 1,
                 "tokens": 18, "measured_usd": None, "estimated_usd": None,
                 "resolved_models": ["probe"]},
    }
    payload = {"verdict": "true_positive", "confidence": .9,
               "findings": [], "proposed_actions": [], "recovery": recovery}
    delivery_ns = extract("services/agents/app/workers/triage_delivery.py",
                          ["_fail", "_object", "_number", "_projection"], {
        "LedgerPersistError": PersistError, "deepcopy": copy.deepcopy, "math": math,
    })
    try:
        delivery_ns["_projection"](
            payload, run, run_id=state.run_id, tenant_id=state.tenant_id,
            alert_id=state.incident_id, workflow_version="auto-triage-v1",
        )
    except PersistError as exc:
        reason = str(exc)
        assert "recovery usage differs from completed run" in reason
    else:
        raise AssertionError("Expected completed-graph usage to invalidate triage recovery")

    return {
        "probe_passed": True,
        "classification": "composition defects reproduced with explicit doubles",
        "warm_first_result": warm,
        "cold_first_result": cold,
        "graph_completion": {"tokens_before": 18, "tokens_after": run["total_tokens"],
                             "unpriced_calls_before": 1,
                             "unpriced_calls_after": run["unpriced_call_count"]},
        "triage_recovery_after_graph": {"rejected": True, "reason": reason},
        "method": "verbatim AST-extracted current production functions; in-memory dependencies",
        "doubles": ["state/model", "live admission and pending/lookup stores", "writer",
                    "PostgreSQL pool/connection", "tenant resolver", "no-op graph"],
        "network_calls": 0, "sdk_calls": 0, "model_calls": 0, "business_writes": 0,
        "deployed_failure_claimed": False,
        "limitations": [
            "No production dependency imports, real graph node/model, Kafka or PostgreSQL execution",
            "Warm/cold branches prove early return before escalation, not a deployed outage",
            "Graph was disabled in the latest accepted deployment; these probes do not change flags",
        ],
        "prior_probe_attempt": {
            "result": "harness NameError after warm/cold checks",
            "cause": "time was not injected into the extracted graph._run namespace",
            "correction": "time injected; complete corrected probe passed",
            "product_failure": False,
        },
        "sources": SOURCES,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(probe()), ensure_ascii=False, indent=2))
