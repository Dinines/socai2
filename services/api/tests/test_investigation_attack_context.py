"""Direct contracts for owned, explicit preparation and read-only consumption."""
from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.v1.deps import CurrentUser, SERVICE_PRINCIPAL_PERMISSIONS, get_current_user
from app.api.v1.endpoints import graph, attack_chain
from app.db.database import get_db
from app.services import graph_service
from app.services import investigation_attack_context as ctx

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER = uuid.UUID("22222222-2222-2222-2222-222222222222")
CASE = uuid.UUID("33333333-3333-3333-3333-333333333333")
ALERT = uuid.UUID("44444444-4444-4444-4444-444444444444")
LATER = uuid.UUID("55555555-5555-5555-5555-555555555555")


class DB:
    def __init__(self, *, case=True, ambiguous=False):
        self.calls = []
        self.case = case
        self.ambiguous = ambiguous
        self.alert = {"id": ALERT, "tenant_id": TENANT, "title": "source alert", "severity": "high",
                      "case_id": None, "affected_hosts": ["host-a", "host-b"],
                      "affected_users": ["alice", "bob"], "affected_ips": ["192.0.2.1"],
                      "entities": [{"type": "domain", "value": "source.example"}], "mitre_techniques": ["T1059.001"]}

    async def execute(self, query, params):
        sql = str(query)
        self.calls.append((sql, params))
        rows = []
        if params.get("tenant") == str(TENANT):
            if "FROM aisoc_cases" in sql and self.case:
                rows = [{"id": CASE, "tenant_id": TENANT, "title": "case", "severity": "high", "alert_ids": [ALERT]}]
                if self.ambiguous and "LIMIT 2" in sql:
                    rows += [{**rows[0], "id": LATER}]
            elif "FROM alerts" in sql:
                rows = [self.alert]
        result = MagicMock()
        result.mappings.return_value.all.return_value = rows
        return result


@pytest.mark.asyncio
async def test_projection_uses_all_reported_entities_then_alert_then_case(monkeypatch):
    writes = []
    for name in ("upsert_host", "upsert_user", "upsert_alert_node", "upsert_case_node"):
        async def record(*args, _name=name, **kwargs):
            writes.append((_name, args, kwargs))
        monkeypatch.setattr(graph_service, name, record)
    result = await ctx.prepare_investigation_graph(DB(), TENANT, case_id=CASE)
    assert result["status"] == "success" and result["source_alert_ids"] == [str(ALERT)]
    assert [w[0] for w in writes] == ["upsert_host", "upsert_host", "upsert_user", "upsert_user", "upsert_alert_node", "upsert_case_node"]
    args = writes[4][2]
    assert len(args["host_ids"]) == len(args["user_ids"]) == 2
    assert args["source_alert_id"] == str(ALERT) and args["tenant_scoped_iocs"]
    assert args["ioc_values"] == ["192.0.2.1", "source.example"]
    assert ctx._entity_id(str(TENANT), "host", "host-a") != ctx._entity_id(str(OTHER), "host", "host-a")


@pytest.mark.asyncio
async def test_foreign_anchor_never_writes(monkeypatch):
    write = AsyncMock()
    monkeypatch.setattr(graph_service, "upsert_alert_node", write)
    with pytest.raises(HTTPException) as caught:
        await ctx.prepare_investigation_graph(DB(), OTHER, alert_id=ALERT)
    assert caught.value.status_code == 404
    write.assert_not_awaited()


@pytest.mark.asyncio
async def test_alert_projection_keeps_current_alert_beyond_case_first_fifty(monkeypatch):
    current = DB().alert
    earlier = [{**current, "id": uuid.uuid4(), "affected_hosts": [f"earlier-{i}"]} for i in range(51)]
    case = {"id": CASE, "tenant_id": TENANT, "title": "large case", "severity": "high",
            "alert_ids": [a["id"] for a in earlier] + [ALERT]}

    async def rows(_db, sql, **params):
        assert params["tenant"] == str(TENANT)
        if "FROM aisoc_cases" in sql:
            return [case]
        return earlier if "ORDER BY CASE" in sql else [current]

    monkeypatch.setattr(ctx, "_rows", rows)
    writes = {name: AsyncMock() for name in ("upsert_host", "upsert_user", "upsert_alert_node", "upsert_case_node")}
    for name, write in writes.items():
        monkeypatch.setattr(graph_service, name, write)
    result = await ctx.prepare_investigation_graph(object(), TENANT, alert_id=ALERT)
    assert result["status"] == "success" and result["source_alert_ids"] == [str(ALERT)]
    assert result["case_id"] == str(CASE) and not result["truncated"]
    writes["upsert_alert_node"].assert_awaited_once()
    assert writes["upsert_alert_node"].await_args.args[0] == str(ALERT)
    writes["upsert_case_node"].assert_awaited_once_with(str(CASE), str(TENANT), "large case", "high", [str(ALERT)])
    assert [call.args[1] for call in writes["upsert_host"].await_args_list] == ["host-a", "host-b"]


@pytest.mark.asyncio
async def test_alert_without_case_and_ambiguous_case_stay_not_linked(monkeypatch):
    monkeypatch.setattr(ctx, "compute_attack_chain", AsyncMock(return_value=SimpleNamespace(to_dict=lambda: {"chain": []})))
    monkeypatch.setattr(graph_service, "get_entity_neighbors", AsyncMock(return_value={"source": None, "neighbors": []}))
    monkeypatch.setattr(graph_service, "get_blast_radius", AsyncMock(return_value={"total_affected": 0}))
    for db in (DB(case=False), DB(ambiguous=True)):
        result = await ctx.read_investigation_attack_context(db, TENANT, alert_id=ALERT)
        assert result["case_id"] is None and result["attack_path"]["status"] == "not_linked"
        assert result["attack_chain"]["status"] == "empty"
        assert all(sql.lstrip().startswith("SELECT") for sql, _ in db.calls)


@pytest.mark.asyncio
async def test_case_seed_remains_earliest_explicit_link_not_latest_payload(monkeypatch):
    db = DB()
    chain = AsyncMock(return_value=SimpleNamespace(to_dict=lambda: {"chain": [{"id": "candidate"}]}))
    monkeypatch.setattr(ctx, "compute_attack_chain", chain)
    result = await ctx.read_attack_chain(db, TENANT, case_id=CASE, window="6h")
    assert chain.await_args.kwargs["seed_alert_id"] == ALERT
    assert chain.await_args.kwargs["window"] == ctx.WINDOWS["6h"]
    assert result["case_id"] == str(CASE)
    assert not any("INSERT" in sql or "UPDATE" in sql for sql, _ in db.calls)


@pytest.mark.asyncio
async def test_projection_failure_is_explicit_not_success_empty(monkeypatch):
    monkeypatch.setattr(graph_service, "upsert_host", AsyncMock(side_effect=RuntimeError("private connection detail")))
    result = await ctx.prepare_investigation_graph(DB(), TENANT, case_id=CASE)
    assert result["status"] == "unavailable" and result["error"] == "RuntimeError"
    assert "private connection detail" not in str(result)


def test_context_get_does_not_prepare_and_seven_read_permissions_cannot_post(monkeypatch):
    monkeypatch.setenv("AISOC_ATTACK_CONTEXT_ENABLED", "1")
    read, write = AsyncMock(return_value={"scope": "alert"}), AsyncMock()
    monkeypatch.setattr(ctx, "read_investigation_attack_context", read)
    monkeypatch.setattr(ctx, "prepare_investigation_graph", write)
    user = CurrentUser(user_id=ALERT, tenant_id=TENANT, role="api_service", email="service@test", resolved_permissions=SERVICE_PRINCIPAL_PERMISSIONS)
    app = FastAPI()
    app.include_router(graph.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: user
    async def db():
        yield object()
    app.dependency_overrides[get_db] = db
    with TestClient(app) as client:
        assert client.get(f"/api/v1/graph/investigation-context?alert_id={ALERT}").status_code == 200
        assert client.post("/api/v1/graph/investigation-context", json={"alert_id": str(ALERT)}).status_code == 403
    assert read.await_count == 1
    write.assert_not_awaited()


@pytest.mark.asyncio
async def test_graph_projection_iocs_are_tenant_id_nodes_and_edges_have_source(monkeypatch):
    session = SimpleNamespace(run=AsyncMock())
    @asynccontextmanager
    async def get_session():
        yield session
    monkeypatch.setattr(graph_service, "get_session", get_session)
    await graph_service.upsert_alert_node(str(ALERT), str(TENANT), "source", "high", host_ids=["h1", "h2"],
        user_ids=["u1", "u2"], ioc_values=["192.0.2.1"], source_alert_id=str(ALERT), tenant_scoped_iocs=True)
    calls = session.run.await_args_list
    ioc = next(c for c in calls if "indicator_value" in c.args[0])
    assert "i:IOC {id:" in ioc.args[0] and "i.value" not in ioc.args[0]
    assert ioc.kwargs["ioc_val"] == "192.0.2.1"
    assert all(c.kwargs.get("tenant_id") == str(TENANT) for c in calls)
    assert sum("OBSERVED_ON" in c.args[0] for c in calls) == 2


@pytest.mark.asyncio
async def test_attack_path_edge_ids_match_ioc_technique_and_scope(monkeypatch):
    session = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(single=AsyncMock(return_value={"nodes": [], "edges": []}))))
    @asynccontextmanager
    async def get_session():
        yield session
    monkeypatch.setattr(graph_service, "get_session", get_session)
    await graph_service.get_attack_path(str(CASE), str(TENANT))
    sql = session.run.await_args.args[0]
    assert "coalesce(endNode(r).id, endNode(r).value, endNode(r).technique_id)" in sql
    assert "startNode(r) IN nodes AND endNode(r) IN nodes" in sql


def test_feature_is_opt_in(monkeypatch):
    monkeypatch.delenv("AISOC_ATTACK_CONTEXT_ENABLED", raising=False)
    assert not ctx.enabled()


@pytest.mark.asyncio
async def test_case_path_reports_backend_and_fallback(monkeypatch):
    monkeypatch.setattr(ctx, "compute_attack_chain", AsyncMock(return_value=SimpleNamespace(to_dict=lambda: {"chain": []})))
    monkeypatch.setattr(graph_service, "get_entity_neighbors", AsyncMock(return_value={"source": None}))
    monkeypatch.setattr(graph_service, "get_blast_radius", AsyncMock(return_value={}))
    path = {"nodes": [{"id": str(CASE), "label": "Case"}, {"id": str(ALERT), "label": "Alert"}],
            "edges": [{"source": str(CASE), "target": str(ALERT)}]}
    monkeypatch.setattr(graph_service, "get_attack_path", AsyncMock(return_value=path))
    actual = await ctx.read_investigation_attack_context(DB(), TENANT, case_id=CASE)
    assert actual["attack_path"]["source"] == "neo4j" and not actual["attack_path"]["fallback"]
    monkeypatch.setattr(graph_service, "get_attack_path", AsyncMock(side_effect=RuntimeError("offline")))
    fallback = {"nodes": [{"id": f"case:{CASE}", "label": "Case"}, {"id": f"alert:{ALERT}", "label": "Alert"}],
                "edges": [{"source": f"case:{CASE}", "target": f"alert:{ALERT}"}]}
    monkeypatch.setattr(graph, "_attack_path_from_relational", AsyncMock(return_value=fallback))
    actual = await ctx.read_investigation_attack_context(DB(), TENANT, case_id=CASE)
    assert actual["attack_path"]["source"] == "postgres_fallback" and actual["attack_path"]["fallback"]
    assert actual["attack_path"]["error"] == "RuntimeError"


@pytest.mark.asyncio
@pytest.mark.parametrize(("kind", "property_name"), [("host", "hostname"), ("user", "username"), ("ioc", "indicator_value")])
async def test_original_bundle_names_resolve_new_entity_ids(monkeypatch, kind, property_name):
    result = SimpleNamespace(single=AsyncMock(return_value=None))
    session = SimpleNamespace(run=AsyncMock(return_value=result))
    @asynccontextmanager
    async def get_session():
        yield session
    monkeypatch.setattr(graph_service, "get_session", get_session)
    await graph_service.get_entity_neighbors("original-name", kind, str(TENANT))
    await graph_service.get_blast_radius("original-name", kind, str(TENANT))
    await graph_service._blast_radius_fallback("original-name", kind, str(TENANT), 2)
    for call in session.run.await_args_list:
        assert f".{property_name} = $entity_id" in call.args[0]
        assert call.kwargs["tenant_id"] == str(TENANT)
