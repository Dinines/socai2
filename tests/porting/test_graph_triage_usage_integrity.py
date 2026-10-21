"""Normal graph usage and immutable triage recovery against disposable PG.

Graph nodes substitute model responses. Runner, tracker, SQL, atomic usage
receipt and first-result lookup are production code; no broker/model is used.
"""
from copy import deepcopy
from decimal import Decimal
import json
import os
from unittest.mock import AsyncMock
from uuid import uuid4, uuid5

import asyncpg
import pytest
import pytest_asyncio

from app.core.cost_telemetry import CostTracker, current_cost_tracker
from app.graph import runner
from app.investigator import ledger
from app.models.state import InvestigationState
from app.workers import triage_delivery


@pytest_asyncio.fixture
async def database(monkeypatch):
    dsn = os.getenv("SOCAI2_INTEGRITY_TEST_DSN")
    if not dsn:
        pytest.skip("explicit disposable PostgreSQL DSN required")
    conn = await asyncpg.connect(dsn)
    await conn.execute("""
        CREATE TEMP TABLE investigation_runs (
            id uuid PRIMARY KEY, tenant_id uuid NOT NULL, case_id varchar(200),
            alert_summary text, raw_alert jsonb, model_used varchar(100), status text,
            error text, iterations integer NOT NULL DEFAULT 0,
            total_tokens integer NOT NULL DEFAULT 0,
            total_cost_usd numeric(10,4) NOT NULL DEFAULT 0,
            measured_call_count integer NOT NULL DEFAULT 0,
            estimated_cost_usd numeric(10,4) NOT NULL DEFAULT 0,
            estimated_call_count integer NOT NULL DEFAULT 0,
            unpriced_call_count integer NOT NULL DEFAULT 0,
            started_at timestamptz, completed_at timestamptz, created_at timestamptz
        );
        CREATE TEMP TABLE investigation_events (
            id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES investigation_runs(id),
            tenant_id uuid NOT NULL, seq integer NOT NULL, ts timestamptz,
            kind varchar(40), agent varchar(80), summary text, payload jsonb,
            input_hash varchar(64), output_hash varchar(64), duration_ms integer,
            created_at timestamptz, UNIQUE (run_id, seq)
        );
        CREATE TEMP TABLE investigation_artifacts (
            id uuid, run_id uuid, tenant_id uuid, event_id uuid, kind text,
            content text, sha256 text, size_bytes integer, created_at timestamptz
        )
    """)

    class Acquire:
        async def __aenter__(self):
            return conn
        async def __aexit__(self, *_):
            return False

    class Pool:
        def acquire(self):
            return Acquire()

    monkeypatch.setattr(ledger, "get_pool", AsyncMock(return_value=Pool()))
    try:
        yield conn
    finally:
        await conn.close()


def first_result(run, tenant, alert, measured=None):
    cost = {"tokens": 37, "measured_calls": int(measured is not None), "estimated_calls": 0,
            "unpriced_calls": 1, "measured_usd": measured,
            "estimated_usd": None, "resolved_models": ["unit:first"]}
    recovery = {"schema_version": 1, "workflow_version": "unit-v1",
                "run_id": str(run), "tenant_id": str(tenant),
                "alert_id": str(alert), "incident_id": str(uuid4()),
                "verdict": "needs_review", "confidence": .6,
                "tier": "llm", "findings": ["first triage finding"],
                "proposed_actions": [], "shadow": False, "cost": cost,
                "confidence_basis": [], "business_context_rules": [],
                "business_context_policy": {}}
    return {"verdict": "needs_review", "confidence": .6, "rationale": "First bounded evidence",
            "findings": ["first triage finding"], "proposed_actions": [],
            "auto_closed": False, "recovery": recovery}


async def seed(conn, measured=None):
    tenant, alert = uuid4(), uuid4()
    run = uuid5(triage_delivery._NAMESPACE, f"{alert}:unit-v1")
    first = first_result(run, tenant, alert, measured)
    await conn.execute("""
        INSERT INTO investigation_runs
            (id, tenant_id, case_id, raw_alert, model_used, status, total_tokens,
             total_cost_usd, measured_call_count, unpriced_call_count)
        VALUES ($1,$2,$3,$4::jsonb,'kafka:auto_triage:llm','completed',37,$5,$6,1)
    """, run, tenant, str(alert), json.dumps({"id": str(alert)}),
        measured if measured is not None else Decimal(0), int(measured is not None))
    await conn.execute("""
        INSERT INTO investigation_events (id,run_id,tenant_id,seq,kind,agent,payload)
        VALUES ($1,$2,$3,1,'triage_verdict','auto_triage:llm',$4::jsonb)
    """, uuid4(), run, tenant, json.dumps(first))
    return run, tenant, alert, first


def delta_kwargs(amount=None):
    return dict(total_tokens=8, total_cost_usd=amount, measured_call_count=int(amount is not None),
                estimated_cost_usd=None, estimated_call_count=0,
                unpriced_call_count=int(amount is None), resolved_models=[],
                add_usage=True, graph_usage_seq=2)


@pytest.mark.asyncio
async def test_omitted_usage_preserves_prior_phase_and_tenant_binding(database):
    run, tenant, _, _ = await seed(database)
    await ledger.complete_run(run_id=run, tenant_id=tenant, status="failed",
                              iterations=3, error="bounded completion")
    row = await database.fetchrow("SELECT * FROM investigation_runs WHERE id=$1", run)
    assert row["total_tokens"] == 37 and row["unpriced_call_count"] == 1
    assert row["measured_call_count"] == 0
    assert row["status"] == "failed" and row["iterations"] == 3
    assert row["error"] == "bounded completion" and row["completed_at"] is not None
    await ledger.complete_run(run_id=run, tenant_id=uuid4(), status="completed",
                              total_tokens=0, unpriced_call_count=0)
    row = await database.fetchrow("SELECT * FROM investigation_runs WHERE id=$1", run)
    assert row["status"] == "failed" and row["total_tokens"] == 37


@pytest.mark.asyncio
async def test_runner_records_exact_graph_delta_and_keeps_first_result_readable(database):
    run, tenant, alert, first = await seed(database)
    state = InvestigationState(run_id=run, incident_id=uuid4(), tenant_id=tenant, alert_summary="unit")

    class Graph:
        async def astream(self, _):
            current_cost_tracker().record(model="aisoc-unit-investigation",
                                          prompt_tokens=11, completion_tokens=7, latency_ms=1)
            yield {"investigation": {"status": "completed"}}

    async with CostTracker(run_id=str(run), tenant_id=str(tenant), persist=False) as tracker:
        # An outer tracker may already contain the sealed triage phase.
        tracker.record(model="aisoc-unit-triage", prompt_tokens=37, completion_tokens=0, latency_ms=1)
        await runner._run(Graph(), state, budget=runner.InvestigationBudget(max_seconds=5),
                          persist=True, seq_start=1)
    row = dict(await database.fetchrow("SELECT * FROM investigation_runs WHERE id=$1", run))
    assert row["total_tokens"] == 55 and row["unpriced_call_count"] == 2
    assert row["measured_call_count"] == 0
    usage_event = await database.fetchrow("SELECT * FROM investigation_events WHERE run_id=$1 AND kind='graph_usage'", run)
    usage = json.loads(usage_event["payload"])["usage"]
    assert usage["tokens"] == 18 and usage["unpriced_calls"] == 1
    assert usage["measured_usd"] is None and usage["estimated_usd"] is None
    fields = dict(run_id=run, tenant_id=tenant, alert_id=str(alert), workflow_version="unit-v1")
    before = deepcopy(first)
    result = await triage_delivery.lookup(**fields)
    assert first == before and result["cost"]["tokens"] == 37
    assert result["cost"]["unpriced_calls"] == 1 and result["cost"]["measured_usd"] is None
    assert result["findings"] == ["first triage finding"] and result["reused_persisted"] is True
    stored_first = await database.fetchval("SELECT payload FROM investigation_events WHERE run_id=$1 AND seq=1", run)
    assert json.loads(stored_first) == before

    # Reconfirming the same accounting result must not increment the Run again.
    repeated = {**delta_kwargs(), "total_tokens": 18, "graph_usage_seq": usage_event["seq"]}
    await ledger.complete_run(run_id=run, tenant_id=tenant, status="completed", **repeated)
    assert await database.fetchval("SELECT total_tokens FROM investigation_runs WHERE id=$1", run) == 55
    with pytest.raises(ledger.LedgerPersistError, match="conflicts"):
        await ledger.complete_run(run_id=run, tenant_id=tenant, status="completed",
                                  **{**repeated, "total_tokens": 19})
    # A larger total without an accompanying immutable source must still hold.
    await database.execute("UPDATE investigation_runs SET total_tokens=56 WHERE id=$1", run)
    with pytest.raises(ledger.LedgerPersistError, match="usage differs"):
        await triage_delivery.lookup(**fields)


@pytest.mark.asyncio
@pytest.mark.parametrize("prior,additional,expected", [(None, None, None), (None, 0.0, 0.0),
                                                       (None, .05, .05), (.1, .05, .15),
                                                       (.00015, None, .0001)])
async def test_graph_cost_addition_keeps_measured_provenance(database, prior, additional, expected):
    run, tenant, alert, first = await seed(database, measured=prior)
    fields = dict(run_id=run, tenant_id=tenant, alert_id=str(alert), workflow_version="unit-v1")
    initial = await triage_delivery.lookup(**fields)
    assert initial["cost"] == first["recovery"]["cost"]
    await ledger.complete_run(run_id=run, tenant_id=tenant, status="completed", **delta_kwargs(additional))
    row = await database.fetchrow("SELECT * FROM investigation_runs WHERE id=$1", run)
    assert row["total_tokens"] == 45
    assert row["measured_call_count"] == int(prior is not None) + int(additional is not None)
    result = await triage_delivery.lookup(**fields)
    assert result["cost"] == first["recovery"]["cost"]
    event = await database.fetchrow("SELECT payload FROM investigation_events WHERE run_id=$1 AND kind='graph_usage'", run)
    assert json.loads(event["payload"])["usage"]["measured_usd"] == additional
    if expected is None:
        assert row["measured_call_count"] == 0
    else:
        assert float(row["total_cost_usd"]) == pytest.approx(expected)


@pytest.mark.asyncio
async def test_usage_event_and_aggregate_rollback_together(database):
    run, tenant, _, _ = await seed(database)
    await database.execute("""
        CREATE FUNCTION pg_temp.reject_usage_update() RETURNS trigger LANGUAGE plpgsql AS
        $$ BEGIN RAISE EXCEPTION 'isolated graph usage update failure'; END $$;
        CREATE TRIGGER reject_usage_update BEFORE UPDATE ON investigation_runs
        FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_usage_update()
    """)
    with pytest.raises(ledger.LedgerPersistError, match="transaction failed"):
        await ledger.complete_run(run_id=run, tenant_id=tenant, status="completed", **delta_kwargs())
    assert await database.fetchval("SELECT total_tokens FROM investigation_runs WHERE id=$1", run) == 37
    assert await database.fetchval("SELECT count(*) FROM investigation_events WHERE kind='graph_usage'") == 0
    with pytest.raises(ledger.LedgerPersistError, match="ownership"):
        await ledger.complete_run(run_id=run, tenant_id=uuid4(), status="completed", **delta_kwargs())
    assert await database.fetchval("SELECT count(*) FROM investigation_events WHERE kind='graph_usage'") == 0


@pytest.mark.parametrize("tokens", [36, 38])
def test_first_result_rejects_any_unaccounted_run_usage(tokens):
    run, tenant, alert = uuid4(), uuid4(), uuid4()
    row = {"model_used": "kafka:auto_triage:llm", "total_tokens": tokens,
           "measured_call_count": 0, "estimated_call_count": 0, "unpriced_call_count": 1}
    with pytest.raises(ledger.LedgerPersistError, match="usage differs"):
        triage_delivery._projection(first_result(run, tenant, alert), row, run_id=run,
            tenant_id=tenant, alert_id=str(alert), workflow_version="unit-v1")
