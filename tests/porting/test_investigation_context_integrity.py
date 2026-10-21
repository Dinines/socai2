"""B2: actual bundle/tool modules with bounded HTTP doubles; no infrastructure/model."""
from __future__ import annotations

from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest

from app.context import bundle as module
from app.investigator import bundle_prompt
from app.tools import enrichment, graph


A = "11111111-1111-1111-1111-111111111111"
B = "22222222-2222-2222-2222-222222222222"
ALERT_A = "33333333-3333-3333-3333-333333333333"
ALERT_B = "44444444-4444-4444-4444-444444444444"
CASE = "55555555-5555-5555-5555-555555555555"
FETCH_BASELINES = module.ContextBundleBuilder._fetch_baselines
FETCH_THREAT_INTEL = module.ContextBundleBuilder._fetch_threat_intel


def payload(tenant=A, alert=ALERT_A, **extra):
    return {"tenant_id": tenant, "alert_id": alert, "identities": [], "assets": [],
            "cloud": [], "business": [], "threat": [], "narrative": [],
            "partial": False, "errors": [], **extra}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for key in ("DATABASE_URL", "DATABASE_DSN", "AISOC_INVESTIGATION_CONTEXT_KEYS_FILE", "AISOC_TRIAGE_IDENTITY_KEYS_FILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(graph, "_GRAPH_ENABLED", True)
    monkeypatch.setattr(module.ContextBundleBuilder, "_fetch_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(module.ContextBundleBuilder, "_fetch_baselines", AsyncMock(return_value={}))
    monkeypatch.setattr(module.ContextBundleBuilder, "_fetch_threat_intel", AsyncMock(return_value={}))


def transport(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


def mapping(monkeypatch, tmp_path, rows, env="AISOC_TRIAGE_IDENTITY_KEYS_FILE"):
    path = tmp_path / (env + ".json")
    path.write_text(json.dumps(rows))
    path.chmod(0o600)
    monkeypatch.setenv(env, str(path))


@pytest.mark.asyncio
async def test_real_prefetch_uses_each_tenants_graph_reader_and_case_alert_ids(monkeypatch, tmp_path):
    mapping(monkeypatch, tmp_path, {A: "synthetic-reader-a", B: "synthetic-reader-b"})
    calls = []

    def reply(request):
        tenant = request.headers["X-Tenant-ID"]
        assert request.headers["Authorization"] == "Bearer synthetic-reader-" + ("a" if tenant == A else "b")
        calls.append((tenant, request.url.path))
        if "incident-context" in request.url.path:
            return httpx.Response(200, json=payload(tenant, request.url.path.rsplit("/", 1)[-1],
                assets=[{"name": "asset-" + tenant[0]}], narrative=["Scoped asset is an investigation fact."]))
        if "neighbors" in request.url.path:
            return httpx.Response(200, json={"neighbors": [{"id": "related-" + tenant[0]}]})
        return httpx.Response(200, json={"blast_radius_score": 0.4})

    transport(monkeypatch, reply)
    for tenant, alert in ((A, ALERT_A), (B, ALERT_B)):
        result = await bundle_prompt.prefetch_context_bundle_dict(
            case_id=CASE, tenant_id=tenant, alert_summary="Case investigation",
            raw_alert={"alerts": [{"id": alert, "affected_hosts": ["host-" + tenant[0]],
                                   "affected_users": ["analyst"], "affected_ips": ["192.0.2.7"]}]},
        )
        assert result["incident_context"]["source_alert_ids"] == [alert]
        assert result["incident_context"]["assets"] == [{"name": "asset-" + tenant[0]}]
        assert "host:host-" + tenant[0] in result["entity_neighborhoods"]
        text = bundle_prompt.format_bundle_prompt_append(result)
        assert "Scoped asset" in text and alert in text
        assert result["errors"] == [] and len(result["sources_called"]) == 5
    assert len(calls) == 10
    assert all(CASE not in path for _, path in calls)


@pytest.mark.asyncio
async def test_missing_tenant_mapping_never_uses_shared_or_other_tenant_credential(monkeypatch, tmp_path):
    mapping(monkeypatch, tmp_path, {A: "synthetic-reader-a"})
    monkeypatch.setenv("AISOC_AGENTS_API_KEY", "synthetic-shared-must-not-be-used")
    transport(monkeypatch, lambda request: pytest.fail("No credential should be sent"))
    result = await bundle_prompt.prefetch_context_bundle_dict(
        case_id=CASE, tenant_id=B, alert_summary="Case",
        raw_alert={"alerts": [{"id": ALERT_B, "affected_hosts": ["host-b"]}]})
    assert result["entity_neighborhoods"] == {}
    text = bundle_prompt.format_bundle_prompt_append(result)
    assert "unknown" in text and "unavailable" in text
    assert "0 nodes" not in text and "0 neighbors" not in text


@pytest.mark.asyncio
async def test_explicit_investigation_mapping_miss_does_not_fall_back(monkeypatch, tmp_path):
    mapping(monkeypatch, tmp_path, {A: "synthetic-old-reader"})
    mapping(monkeypatch, tmp_path, {B: "synthetic-reader-b"}, "AISOC_INVESTIGATION_CONTEXT_KEYS_FILE")
    transport(monkeypatch, lambda request: pytest.fail("Explicit mapping miss must not fall back"))
    result = await bundle_prompt.prefetch_context_bundle_dict(
        case_id=CASE, tenant_id=A, alert_summary="Case", raw_alert={"id": ALERT_A, "hostname": "host-a"})
    assert result["errors"] and not result["entity_neighborhoods"]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [{"available": False}, {"error": "graph down"}, {"neighbors": "wrong schema"}])
async def test_unavailable_graph_is_never_rendered_as_a_successful_empty_query(monkeypatch, failure):
    async def neighbors(*args, **kwargs):
        return deepcopy(failure)
    monkeypatch.setattr(graph, "get_entity_neighbors", neighbors)
    monkeypatch.setattr(graph, "get_blast_radius", AsyncMock(return_value={"blast_radius_score": 0.0}))
    state = SimpleNamespace(incident_id=UUID(CASE), tenant_id=A, alert_summary="Case", raw_alert={"hostname": "host-a"})
    result = await module.ContextBundleBuilder(api_token="synthetic-reader").build(state)
    assert not result.entity_neighborhoods and result.errors and not result.is_complete
    text = "\n".join(result.prompt_context_lines())
    assert "unknown" in text and "0 nodes" not in text


@pytest.mark.asyncio
async def test_legal_empty_and_zero_remain_successful_graph_results(monkeypatch):
    monkeypatch.setattr(graph, "get_entity_neighbors", AsyncMock(return_value={"neighbors": []}))
    monkeypatch.setattr(graph, "get_blast_radius", AsyncMock(return_value={"blast_radius_score": 0.0}))
    state = SimpleNamespace(incident_id=UUID(CASE), tenant_id=A, alert_summary="Case", raw_alert={"hostname": "host-a"})
    result = await module.ContextBundleBuilder(api_token="synthetic-reader").build(state)
    assert result.entity_neighborhoods["host:host-a"].blast_radius_score == 0.0
    assert result.errors == [] and result.is_complete
    assert "0 nodes" in "\n".join(result.prompt_context_lines())


@pytest.mark.asyncio
async def test_blast_failure_preserves_good_neighbors_without_inventing_zero_score(monkeypatch):
    monkeypatch.setattr(graph, "get_entity_neighbors", AsyncMock(return_value={"neighbors": [{"id": "host-b"}]}))
    monkeypatch.setattr(graph, "get_blast_radius", AsyncMock(return_value={"error": "failed", "blast_radius_score": 0.0}))
    state = SimpleNamespace(incident_id=UUID(CASE), tenant_id=A, alert_summary="Case", raw_alert={"hostname": "host-a"})
    result = await module.ContextBundleBuilder(api_token="synthetic-reader").build(state)
    assert result.entity_neighborhoods["host:host-a"].node_count == 1
    assert result.entity_neighborhoods["host:host-a"].blast_radius_score is None
    assert result.errors and "blast_radius=0.00" not in "\n".join(result.prompt_context_lines())


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong", [{"tenant_id": B}, {"alert_id": ALERT_B}, {"assets": "invalid"}])
async def test_incident_context_rejects_wrong_identity_or_schema(monkeypatch, wrong):
    transport(monkeypatch, lambda request: httpx.Response(200, json=payload(**wrong)))
    result = await module.ContextBundleBuilder(api_token="synthetic-reader")._fetch_incident_context(A, {"id": ALERT_A})
    assert result.partial and result.errors and not result.has_content and not result.source_alert_ids


@pytest.mark.asyncio
async def test_case_context_preserves_partial_success_and_source_linkage(monkeypatch):
    def reply(request):
        alert = request.url.path.rsplit("/", 1)[-1]
        if alert == ALERT_B:
            return httpx.Response(503)
        return httpx.Response(200, json=payload(assets=[{"name": "host-a"}], narrative=["Observed asset."]))
    transport(monkeypatch, reply)
    result = await module.ContextBundleBuilder(api_token="synthetic-reader")._fetch_incident_context(
        A, {"alerts": [{"id": ALERT_A}, {"id": ALERT_B}]})
    assert result.source_alert_ids == [ALERT_A] and result.assets == [{"name": "host-a"}]
    assert result.partial and ALERT_B in result.errors[0]


@pytest.mark.asyncio
async def test_partial_without_server_error_details_remains_incomplete(monkeypatch):
    transport(monkeypatch, lambda request: httpx.Response(200, json=payload(partial=True)))
    state = SimpleNamespace(incident_id=UUID(CASE), tenant_id=A, alert_summary="Case", raw_alert={"id": ALERT_A})
    result = await module.ContextBundleBuilder(api_token="synthetic-reader").build(state)
    assert result.incident_context.partial and not result.is_complete
    assert "unknown" in "\n".join(result.prompt_context_lines())


@pytest.mark.asyncio
@pytest.mark.parametrize("status, body, failed", [(503, [], True), (200, {}, True), (200, [], False)])
async def test_ueba_failure_and_valid_empty_remain_distinct(monkeypatch, status, body, failed):
    transport(monkeypatch, lambda request: httpx.Response(status, json=body))
    errors = []
    result = await FETCH_BASELINES(module.ContextBundleBuilder(), A,
        [module.EntityRef(type="host", value="host-a")], errors=errors)
    assert result == {} and bool(errors) is failed


@pytest.mark.asyncio
@pytest.mark.parametrize("specific,common,expected", [("ueba-token", "common-token", "ueba-token"), ("", "common-token", "common-token")])
async def test_ueba_uses_native_port_and_tenant_service_headers(monkeypatch, specific, common, expected):
    monkeypatch.delenv("AISOC_UEBA_URL", raising=False)
    monkeypatch.setenv("AISOC_UEBA_SERVICE_TOKEN", specific)
    monkeypatch.setenv("AISOC_SERVICE_TOKEN", common)
    calls = []

    def reply(request):
        calls.append(request)
        assert str(request.url).startswith("http://ueba:8004/api/v1/ueba/baselines?")
        assert request.headers["Authorization"] == "Bearer " + expected
        assert request.headers["X-AiSOC-Tenant-ID"] == request.url.params["tenant_id"] == A
        return httpx.Response(200, json=[])

    transport(monkeypatch, reply)
    assert await FETCH_BASELINES(module.ContextBundleBuilder(), A, [module.EntityRef(type="user", value="test-user")]) == {}
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_ueba_native_feature_stats_and_window_are_preserved_without_inventing_deviation(monkeypatch):
    stats = {"login_count": {"mean": 12.0, "M2": 2.0, "count": 3, "std": 1.0}}
    transport(monkeypatch, lambda request: httpx.Response(200, json=[{
        "tenant_id": A, "entity_id": "test-user", "entity_type": "user", "feature_stats": stats,
        "window_start": "2026-10-16T00:00:00Z", "window_end": "2026-10-21T00:00:00Z",
    }]))
    result = await FETCH_BASELINES(module.ContextBundleBuilder(), A, [module.EntityRef(type="user", value="test-user")])
    baseline = result["user:test-user"]
    assert baseline.baseline == stats and baseline.activity_window_days == 5
    assert baseline.deviation_score is None
    bundle = module.ContextBundle(incident_id=UUID(CASE), peer_baselines=result)
    assert bundle.summary_for_llm()["ueba_max_deviation"] is None
    assert "deviation=unknown" in "\n".join(bundle.prompt_context_lines())


@pytest.mark.asyncio
async def test_ueba_native_entity_names_preserve_context_join_keys(monkeypatch):
    calls = []

    def reply(request):
        entity_type = request.url.params["entity_type"]
        calls.append(entity_type)
        entity_id = {"device": "host-a", "user": "alice@example.com"}[entity_type]
        return httpx.Response(200, json=[{"entity_id": entity_id, "feature_stats": {"count": {"mean": 1.0}}}])

    transport(monkeypatch, reply)
    result = await FETCH_BASELINES(module.ContextBundleBuilder(), A, [
        module.EntityRef(type="host", value="host-a"), module.EntityRef(type="email", value="alice@example.com")])
    assert sorted(calls) == ["device", "user"]
    assert set(result) == {"host:host-a", "email:alice@example.com"}
    assert all(value.baseline == {"count": {"mean": 1.0}} for value in result.values())


@pytest.mark.asyncio
async def test_bulk_enrichment_failure_is_not_a_valid_empty_result(monkeypatch):
    transport(monkeypatch, lambda request: httpx.Response(503))
    assert await enrichment.bulk_enrich_iocs([]) == []  # Existing caller contract.
    with pytest.raises(httpx.HTTPStatusError):
        await enrichment.bulk_enrich_iocs([], raise_on_error=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("status, body, failed", [(503, {}, True), (200, {"results": []}, False)])
async def test_builder_sees_enrichment_failure_separately_from_empty(monkeypatch, status, body, failed):
    transport(monkeypatch, lambda request: httpx.Response(status, json=body))
    call = FETCH_THREAT_INTEL(module.ContextBundleBuilder(), [module.EntityRef(type="ip", value="192.0.2.1")])
    if failed:
        with pytest.raises(httpx.HTTPStatusError):
            await call
    else:
        assert await call == {}


@pytest.mark.asyncio
async def test_case_context_reads_only_bounded_head_and_marks_partial(monkeypatch):
    calls = []
    def reply(request):
        alert = request.url.path.rsplit("/", 1)[-1]
        calls.append(alert)
        return httpx.Response(200, json=payload(alert=alert))
    transport(monkeypatch, reply)
    result = await module.ContextBundleBuilder(api_token="synthetic-reader")._fetch_incident_context(
        A, {"alerts": [{"id": str(index)} for index in range(4)]})
    assert calls == ["0", "1", "2"] and result.partial and result.errors


def test_case_entity_extraction_reads_existing_affected_entity_arrays():
    rows = module.extract_entities({"alerts": [{"id": ALERT_A, "affected_hosts": ["host-a"],
        "affected_users": ["analyst@example.com"], "affected_ips": ["192.0.2.1"]}]})
    assert {item.key for item in rows} >= {"host:host-a", "email:analyst@example.com", "ip:192.0.2.1"}


def test_existing_entity_arrays_are_not_silently_truncated():
    rows = module.extract_entities({"affected_hosts": [f"host-{index}" for index in range(26)]})
    assert len(rows) == 26
