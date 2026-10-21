"""Tenant-owned graph/WS entry and existing durable report delivery; no models."""
from contextlib import asynccontextmanager
import hashlib
import json
import os
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket
from fastapi.testclient import TestClient

from app.api import investigate, investigation_access, router as graph_api
from app.core.cost_telemetry import CostTracker, current_cost_tracker
from app.core.scoped_baseline import apply_scope
from app.models.state import AgentStatus, InvestigationState
from app.security.tenant_scope import TenantPrincipal


def principal(tenant):
    return TenantPrincipal(tenant_ids=frozenset({tenant}), subject="delivery-unit")


@pytest_asyncio.fixture
async def db(monkeypatch):
    dsn = os.getenv("SOCAI2_INTEGRITY_TEST_DSN")
    if not dsn:
        pytest.skip("explicit disposable PostgreSQL DSN required")
    conn = await asyncpg.connect(dsn)
    await conn.execute("""
      CREATE TEMP TABLE aisoc_cases (id uuid PRIMARY KEY,tenant_id uuid NOT NULL);
      CREATE TEMP TABLE alerts (id uuid PRIMARY KEY,tenant_id uuid NOT NULL,enrichment_data jsonb);
      CREATE TEMP TABLE investigation_runs (
        id uuid PRIMARY KEY,tenant_id uuid NOT NULL,case_id text,status text,error text,
        started_at timestamptz DEFAULT now(),completed_at timestamptz,iterations int DEFAULT 0,
        total_tokens int DEFAULT 37,total_cost_usd numeric(10,4) DEFAULT 0,
        measured_call_count int DEFAULT 0,estimated_cost_usd numeric(10,4) DEFAULT 0,
        estimated_call_count int DEFAULT 0,unpriced_call_count int DEFAULT 1);
      CREATE TEMP TABLE investigation_events (
        id uuid PRIMARY KEY,run_id uuid,tenant_id uuid,seq int,kind text,agent text,
        summary text,payload jsonb,ts timestamptz DEFAULT now());
      CREATE TEMP TABLE investigation_artifacts (
        id uuid PRIMARY KEY,run_id uuid,tenant_id uuid,kind text,content text,
        sha256 text,size_bytes int,created_at timestamptz DEFAULT now());
    """)

    class Pool:
        @asynccontextmanager
        async def acquire(self):
            yield conn

    monkeypatch.setattr(investigation_access.ledger, "get_pool", AsyncMock(return_value=Pool()))
    monkeypatch.setattr(investigate, "_runs", {})
    monkeypatch.setattr(graph_api, "_runs", {})
    try:
        yield conn
    finally:
        await conn.close()


async def seed_run(db, *, report=True):
    tenant, run, case = uuid4(), uuid4(), uuid4()
    await db.execute("INSERT INTO aisoc_cases VALUES ($1,$2)", case, tenant)
    await db.execute("INSERT INTO investigation_runs(id,tenant_id,case_id,status) VALUES ($1,$2,$3,'completed')",
                     run, tenant, str(case))
    await db.execute("INSERT INTO investigation_events(id,run_id,tenant_id,seq,kind,agent,summary,payload) "
                     "VALUES ($1,$2,$3,1,'triage_verdict','auto_triage','first verdict',$4::jsonb)",
                     uuid4(), run, tenant, json.dumps({"verdict": "needs_review"}))
    if report:
        await artifact(db, run, tenant, "report_md", "# Marked report\n<script>private()</script>")
    return tenant, run, case


async def artifact(db, run, tenant, kind, content):
    await db.execute("INSERT INTO investigation_artifacts(id,run_id,tenant_id,kind,content,sha256,size_bytes) "
                     "VALUES($1,$2,$3,$4,$5,$6,$7)", uuid4(), run, tenant, kind, content,
                     hashlib.sha256(content.encode()).hexdigest(), len(content.encode()))


@pytest.mark.asyncio
async def test_owned_graph_launch_binds_cost_and_keeps_owner_at_completion(db, monkeypatch):
    tenant, case = uuid4(), uuid4()
    await db.execute("INSERT INTO aisoc_cases VALUES($1,$2)", case, tenant)
    tasks = BackgroundTasks()
    out = await graph_api.start_investigation(graph_api.InvestigationRequest(
        incident_id=case, tenant_id=tenant, alert_summary="marked"), tasks, principal(tenant))
    run_id = str(out.run_id)
    observed = []

    async def graph(state):
        tracker = current_cost_tracker()
        observed.append((tracker.run_id, tracker.tenant_id))
        state.status = AgentStatus.COMPLETED
        return state

    monkeypatch.setattr(graph_api, "run_full_investigation", graph)
    await tasks()
    result = await graph_api.get_investigation(run_id, principal(tenant))
    assert observed == [(run_id, str(tenant))]
    assert result["status"] == "completed" and result["tenant_id"] == str(tenant)
    with pytest.raises(HTTPException) as err:
        await graph_api.get_investigation(run_id, principal(uuid4()))
    assert err.value.status_code == 404


@pytest.mark.asyncio
async def test_graph_reuses_matching_outer_tracker_without_rebinding(db, monkeypatch):
    tenant, run_id = uuid4(), str(uuid4())
    state = InvestigationState(run_id=run_id, tenant_id=tenant, incident_id=uuid4())
    graph_api._runs[run_id] = {"tenant_id": str(tenant), "status": "running"}
    async with CostTracker(run_id=run_id, tenant_id=str(tenant), persist=False) as outer:
        async def graph(state):
            assert current_cost_tracker() is outer
            return state
        monkeypatch.setattr(graph_api, "run_full_investigation", graph)
        await graph_api._run_investigation(run_id, state)
        assert current_cost_tracker() is outer
    assert graph_api._runs[run_id]["tenant_id"] == str(tenant)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [AgentStatus.FAILED, AgentStatus.CANCELLED])
async def test_graph_terminal_without_error_is_failed_in_hot_and_cold_reads(db, monkeypatch, status):
    tenant, run, case = await seed_run(db)
    run_id = str(run)
    state = InvestigationState(run_id=run, tenant_id=tenant, incident_id=case, status=status)
    graph_api._runs[run_id] = {"tenant_id": str(tenant), "status": "running"}
    monkeypatch.setattr(graph_api, "run_full_investigation", AsyncMock(return_value=state))
    await graph_api._run_investigation(run_id, state)
    hot = await graph_api.get_investigation(run_id, principal(tenant))
    assert hot["status"] == "failed" and status.value in hot["error"]
    assert hot["investigation_completion"] == "partial"
    # The graph's own durable contract records a standalone partial Run as
    # failed and retains its actual terminal state in the graph_result blob.
    await db.execute("UPDATE investigation_runs SET status='failed',error=NULL WHERE id=$1", run)
    await artifact(db, run, tenant, "graph_result", json.dumps(state.to_dict()))
    await db.execute("INSERT INTO investigation_events(id,run_id,tenant_id,seq,kind,payload) "
                     "VALUES($1,$2,$3,2,'graph_result',$4::jsonb)", uuid4(), run, tenant,
                     json.dumps({"completion": "partial"}))
    graph_api._runs.pop(run_id)
    cold = await graph_api.get_investigation(run_id, principal(tenant))
    assert cold["status"] == hot["status"] and cold["error"] == hot["error"]
    assert cold["investigation_completion"] == hot["investigation_completion"]


@pytest.mark.asyncio
async def test_foreign_graph_target_and_body_tenant_queue_nothing(db):
    tenant_a, tenant_b, case = uuid4(), uuid4(), uuid4()
    await db.execute("INSERT INTO aisoc_cases VALUES($1,$2)", case, tenant_b)
    tasks = BackgroundTasks()
    request = graph_api.InvestigationRequest(incident_id=case, tenant_id=tenant_a, alert_summary="foreign")
    with pytest.raises(HTTPException) as err:
        await graph_api.start_investigation(request, tasks, principal(tenant_a))
    assert err.value.status_code == 404
    request.tenant_id = tenant_b
    with pytest.raises(HTTPException) as err:
        await graph_api.start_investigation(request, tasks, principal(tenant_a))
    assert err.value.status_code == 403
    assert not tasks.tasks and not graph_api._runs


@pytest.mark.asyncio
@pytest.mark.parametrize("use_fusion_incident", [False, True])
async def test_graph_target_accepts_own_alert_or_persisted_fusion_incident(db, use_fusion_incident):
    tenant, alert, incident = uuid4(), uuid4(), uuid4()
    await db.execute("INSERT INTO alerts VALUES($1,$2,$3::jsonb)", alert, tenant,
                     json.dumps({"socai2_fusion": {"incident_id": str(incident)}}))
    target = incident if use_fusion_incident else alert
    assert await investigation_access.require_owned_target(target, tenant) == target
    with pytest.raises(HTTPException) as err:
        await investigation_access.require_owned_target(target, uuid4())
    assert err.value.status_code == 404


@pytest.mark.asyncio
async def test_cold_reports_and_both_status_routes_use_owned_persisted_material(db):
    tenant, run, case = await seed_run(db)
    for read in (investigate.get_investigation, graph_api.get_investigation):
        data = await read(str(run), principal(tenant))
        assert data["case_id"] == str(case) and data["total_tokens"] == 37
        assert data["total_cost_usd"] is None and data["unpriced_call_count"] == 1
        with pytest.raises(HTTPException) as err:
            await read(str(run), principal(uuid4()))
        assert err.value.status_code == 404
    assert "Marked report" in await investigate.get_report_md(str(run), principal(tenant))
    html = await investigate.get_report_html(str(run), principal(tenant))
    assert "&lt;script&gt;private()&lt;/script&gt;" in html and "<script>" not in html
    for read in (investigate.get_report_md, investigate.get_report_html, investigate.get_report_pdf):
        with pytest.raises(HTTPException) as err:
            await read(str(run), principal(uuid4()))
        assert err.value.status_code == 404
    assert not investigate._runs and not graph_api._runs  # Reads never create work.


@pytest.mark.asyncio
async def test_absent_report_is_not_a_successful_empty_document(db):
    tenant, run, _ = await seed_run(db, report=False)
    with pytest.raises(HTTPException) as err:
        await investigate.get_report_md(str(run), principal(tenant))
    assert err.value.status_code == 404


@pytest.mark.asyncio
async def test_done_propagates_failed_report_state_and_delivers_labeled_fallback(db, monkeypatch):
    tenant, run, case = await seed_run(db)
    run_id = str(run)
    investigate._runs[run_id] = {"run_id": run_id, "tenant_id": str(tenant),
                                 "case_id": str(case), "status": "running"}
    error = "Report generation truncated (finish_reason=length); complete fallback supplied; no model retry."
    async def stream(**_):
        yield {"type": "done", "state": {"status": "failed", "error": error,
               "report_md": "# Complete fallback\nOriginal model report truncated.",
               "report_html": "<body><p>Complete fallback</p></body>"}}
    emitted = AsyncMock()
    monkeypatch.setattr(investigate, "_investigate_stream", stream)
    monkeypatch.setattr(investigate, "_emit_event", emitted)
    await investigate._run_and_store(run_id, str(case), investigate.InvestigateRequest(
        tenant_id=str(tenant), alert_summary="marked"))
    status = await investigate.get_investigation(run_id, principal(tenant))
    assert status["status"] == "failed" and status["error"] == error
    assert emitted.await_args.args[2]["kind"] == "error"
    assert emitted.await_args.args[2]["data"] == {"status": "failed", "error": error}
    md = await investigate.get_report_md(run_id, principal(tenant))
    assert md.headers["X-Investigation-Status"] == "failed"
    assert md.headers["X-Investigation-Report-State"] == "partial"
    assert b"Complete fallback" in md.body and b"status: failed" in md.body
    html = await investigate.get_report_html(run_id, principal(tenant))
    assert b"status: failed" in html.body and error.encode() in html.body


@pytest.mark.asyncio
async def test_failed_persisted_fallback_remains_readable_with_explicit_status(db):
    tenant, run, _ = await seed_run(db)
    await db.execute("UPDATE investigation_runs SET status='failed',error='Report generation truncated'")
    result = await investigate.get_investigation(str(run), principal(tenant))
    assert result["status"] == "failed" and "truncated" in result["error"]
    md = await investigate.get_report_md(str(run), principal(tenant))
    html = await investigate.get_report_html(str(run), principal(tenant))
    assert md.headers["X-Investigation-Status"] == "failed" and b"Marked report" in md.body
    assert html.headers["X-Investigation-Report-State"] == "partial"
    assert b"&lt;script&gt;" in html.body and b"<script>" not in html.body


@pytest.mark.asyncio
async def test_cold_graph_result_is_separate_from_first_triage_and_run_total(db):
    tenant, run, _ = await seed_run(db)
    state = {"run_id": str(run), "tenant_id": str(tenant), "verdict": "true_positive"}
    await artifact(db, run, tenant, "graph_result", json.dumps(state))
    await db.execute("INSERT INTO investigation_events(id,run_id,tenant_id,seq,kind,payload) "
                     "VALUES($1,$2,$3,2,'graph_result',$4::jsonb)", uuid4(), run, tenant,
                     json.dumps({"completion": "partial"}))
    data = await investigation_access.read_persisted_run(str(run), principal(tenant))
    assert data["result"] == state and data["investigation_completion"] == "partial"
    assert data["total_tokens"] == 37 and data["audit_log"][0]["payload"]["verdict"] == "needs_review"


@pytest.mark.asyncio
async def test_completed_shared_run_with_partial_graph_labels_all_report_formats(db, monkeypatch):
    tenant, run, _ = await seed_run(db)
    await db.execute("INSERT INTO investigation_events(id,run_id,tenant_id,seq,kind,payload) "
                     "VALUES($1,$2,$3,2,'graph_result',$4::jsonb)", uuid4(), run, tenant,
                     json.dumps({"completion": "partial"}))
    renderer = MagicMock()
    renderer.HTML.return_value.write_pdf.return_value = b"%PDF-partial"
    monkeypatch.setitem(__import__("sys").modules, "weasyprint", renderer)
    for read in (investigate.get_report_md, investigate.get_report_html, investigate.get_report_pdf):
        response = await read(str(run), principal(tenant))
        assert response.headers["X-Investigation-Status"] == "completed"
        assert response.headers["X-Investigation-Report-State"] == "partial"
        if read != investigate.get_report_pdf:
            assert b"Investigation result: partial" in response.body
            assert b"Run status: completed" in response.body
    assert "Investigation result: partial" in renderer.HTML.call_args.kwargs["string"]


@pytest.mark.asyncio
async def test_changed_persisted_artifact_is_not_delivered(db):
    tenant, run, _ = await seed_run(db)
    await db.execute("UPDATE investigation_artifacts SET content='different'")
    with pytest.raises(HTTPException) as err:
        await investigate.get_report_md(str(run), principal(tenant))
    assert err.value.status_code == 503


class Socket:
    def __init__(self, params=None):
        self.query_params = params or {}
        self.accepted = False
        self.closed = None
        self.messages = []
    async def accept(self): self.accepted = True
    async def close(self, code, reason=""): self.closed = code
    async def send_text(self, value): self.messages.append(json.loads(value))


@pytest.mark.asyncio
@pytest.mark.parametrize("cached", [True, False])
async def test_ws_owned_tail_and_foreign_rejection(db, monkeypatch, cached):
    tenant, run, case = await seed_run(db)
    if cached:
        investigate._runs[str(run)] = {"tenant_id": str(tenant), "case_id": str(case),
                                       "status": "completed", "audit_log": [{"summary": "marked"}]}
    monkeypatch.setattr(investigate, "_ws_principal", AsyncMock(return_value=principal(tenant)))
    ws = Socket()
    await investigate.stream_investigation(ws, str(run))
    assert ws.accepted and ws.messages[-1]["type"] == "done"
    assert ws.messages[-1]["case_id"] == str(case)
    monkeypatch.setattr(investigate, "_ws_principal", AsyncMock(return_value=principal(uuid4())))
    foreign = Socket()
    await investigate.stream_investigation(foreign, str(run))
    assert not foreign.accepted and foreign.closed == 1008 and not foreign.messages


@pytest.mark.asyncio
async def test_ws_fresh_case_reuses_launch_and_server_issued_run(db, monkeypatch):
    tenant, case = uuid4(), uuid4()
    await db.execute("INSERT INTO aisoc_cases VALUES($1,$2)", case, tenant)
    monkeypatch.setattr(investigate, "_ws_principal", AsyncMock(return_value=principal(tenant)))
    observed = []
    async def run(run_id, case_id, request):
        observed.append((run_id, case_id, request.tenant_id))
        investigate._runs[run_id].update(status="completed", audit_log=[])
    monkeypatch.setattr(investigate, "_run_and_store", run)
    requested_id = str(uuid4())
    ws = Socket({"case_id": str(case), "alert_summary": "marked"})
    await investigate.stream_investigation(ws, requested_id)
    started = ws.messages[0]
    assert started["type"] == "started" and started["run_id"] != requested_id
    assert observed == [(started["run_id"], str(case), str(tenant))]
    assert ws.messages[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_ws_foreign_case_cannot_start_new_work(db, monkeypatch):
    tenant, case = uuid4(), uuid4()
    await db.execute("INSERT INTO aisoc_cases VALUES($1,$2)", case, uuid4())
    monkeypatch.setattr(investigate, "_ws_principal", AsyncMock(return_value=principal(tenant)))
    launch = AsyncMock()
    monkeypatch.setattr(investigate, "_run_and_store", launch)
    ws = Socket({"case_id": str(case), "alert_summary": "foreign"})
    await investigate.stream_investigation(ws, str(uuid4()))
    assert not ws.accepted and ws.closed == 1008 and not investigate._runs
    launch.assert_not_awaited()


def test_baseline_restores_only_owned_investigation_routes(monkeypatch):
    monkeypatch.setenv("AISOC_SCOPED_BASELINE", "1")
    app = FastAPI()
    @app.post("/api/v1/agent-runs")
    def launch(): return {"type": "owned graph"}
    @app.post("/api/v1/triage")
    def triage(): raise AssertionError("Direct triage remains outside this change")
    @app.websocket("/api/v1/investigations/{run_id}/stream")
    async def stream(ws: WebSocket, run_id: str):
        await ws.accept()
        await ws.send_json({"run_id": run_id})
        await ws.close()
    apply_scope(app, "agents")
    with TestClient(app) as client:
        assert client.post("/api/v1/agent-runs").status_code == 200
        assert client.post("/api/v1/triage").status_code == 404
        with client.websocket_connect("/api/v1/investigations/marked/stream") as ws:
            assert ws.receive_json() == {"run_id": "marked"}
