"""Direct attack-context handoff contracts; HTTP is intercepted by respx."""

import json
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import respx

from app.context import attack_context
from app.context.bundle import ContextBundle, ContextBundleBuilder, IncidentContextDimensions
from app.investigator import bundle_prompt
from app.investigator.deep_investigation import _summarise_alert
from app.tools.graph import _headers

URL = "https://attack-context.example.invalid/api/v1/graph/investigation-context"


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("AISOC_ATTACK_CONTEXT_ENABLED", "true")
    monkeypatch.setenv("API_SERVICE_URL", "https://attack-context.example.invalid")
    monkeypatch.setenv("AISOC_API_SERVICE_TOKEN", "existing-read-only")
    for name in ("AISOC_INVESTIGATION_CONTEXT_KEYS_FILE", "AISOC_TRIAGE_IDENTITY_KEYS_FILE", "AISOC_INVESTIGATION_PREPARE_KEYS_FILE"):
        monkeypatch.delenv(name, raising=False)


def _payload(tenant, *, case=None, alert="seed-alert"):
    return {
        "tenant_id": tenant, "case_id": case, "alert_id": alert,
        "scope": "case" if case else "alert", "queried_at": "2026-10-21T10:00:00Z",
        "attack_chain": {"status": "success", "source": "postgres_alert_entity_bfs", "query": {"window": "24h"}, "error": None,
                         "data": {"seed_alert_id": alert, "window": "24h", "generated_at": "2026-10-21T10:00:00Z", "chain": [
                             {"alert_id": "candidate-2", "event_time": "2026-10-21T09:00:00Z", "score": 0.6,
                              "shared_entities": [{"kind": "Endpoint", "value": "HOST-SHARED"}]}]}},
        "attack_path": {"status": "success" if case else "not_linked", "source": "neo4j" if case else "none", "error": None,
                        "data": {"nodes": [{"id": "internal-node-123", "label": "IOC", "properties": {"value": "internal-value", "indicator_value": "observable.example"}}], "edges": []} if case else None},
        "alert_graph": {"status": "not_applicable" if case else "success", "source": "neo4j", "error": None,
                        "data": None if case else {"neighbors": {"neighbors": []}, "blast_radius": {"total_affected": 0, "blast_radius_score": 0.0}}},
    }


@pytest.mark.asyncio
async def test_disabled_keeps_context_empty(configured, monkeypatch):
    monkeypatch.setenv("AISOC_ATTACK_CONTEXT_ENABLED", "false")
    with respx.mock(assert_all_called=False) as router:
        assert await attack_context.fetch_attack_context("tenant-a", case_id="case-a") == {}
        assert not router.calls


@pytest.mark.asyncio
async def test_case_get_uses_read_identity_and_saves_actual_summary(configured):
    with respx.mock(assert_all_called=True) as router:
        route = router.get(URL, params={"case_id": "case-a"}).respond(200, json=_payload("tenant-a", case="case-a"))
        result = await attack_context.fetch_attack_context("tenant-a", case_id="case-a")
        assert len(router.calls) == 1  # Case preparation is owned by its API POST.
        assert route.calls[0].request.headers["Authorization"] == "Bearer existing-read-only"
        assert route.calls[0].request.headers["X-AiSOC-Tenant-ID"] == "tenant-a"
    summary = result["model_summary"]
    assert all(value in summary for value in ("candidate-2", "HOST-SHARED", "2026-10-21T09:00:00Z", "postgres_alert_entity_bfs", "observable.example"))
    assert "indicator_value=observable.example" in summary
    assert "indicator_value=internal-value" not in summary
    assert "not confirmed attack causality" in summary
    artifacts = attack_context.attack_context_artifacts({"attack_context": result})
    assert {kind for kind, _ in artifacts} == {"attack_chain", "attack_path", "alert_graph"}
    assert all(json.loads(content)["model_summary"] == summary for _, content in artifacts)


@pytest.mark.asyncio
async def test_explicit_reader_miss_never_falls_back_to_service_token(configured, monkeypatch, tmp_path):
    mapping = tmp_path / "reader.json"
    mapping.write_text(json.dumps({"other-tenant": "other-reader"}))
    mapping.chmod(0o600)
    monkeypatch.setenv("AISOC_INVESTIGATION_CONTEXT_KEYS_FILE", str(mapping))
    with respx.mock(assert_all_called=False) as router:
        result = await attack_context.fetch_attack_context("tenant-a", alert_id="alert-a")
        assert not router.calls
    assert result["attack_chain"]["status"] == "unavailable"
    assert result["attack_chain"]["error"] == "tenant_reader_not_configured"


@pytest.mark.asyncio
async def test_alert_without_writer_only_reads(configured):
    with respx.mock(assert_all_called=True) as router:
        router.get(URL, params={"alert_id": "alert-a"}).respond(200, json=_payload("tenant-a", alert="alert-a"))
        result = await attack_context.fetch_attack_context("tenant-a", alert_id="alert-a")
        assert [call.request.method for call in router.calls] == ["GET"]
    assert result["prepare"]["status"] == "not_provided"
    assert result["attack_path"]["status"] == "not_linked"


@pytest.mark.asyncio
async def test_alert_context_read_never_prepares_even_with_writer(configured, monkeypatch, tmp_path):
    mapping = tmp_path / "writer.json"
    mapping.write_text(json.dumps({"tenant-a": "separate-projection-writer"}))
    mapping.chmod(0o600)
    monkeypatch.setenv("AISOC_INVESTIGATION_PREPARE_KEYS_FILE", str(mapping))
    with respx.mock(assert_all_called=True) as router:
        get = router.get(URL, params={"alert_id": "alert-a"}).respond(200, json=_payload("tenant-a", alert="alert-a"))
        result = await attack_context.fetch_attack_context("tenant-a", alert_id="alert-a")
        assert [call.request.method for call in router.calls] == ["GET"]
        assert get.calls[0].request.headers["Authorization"] == "Bearer existing-read-only"
    assert result["prepare"]["status"] == "not_provided"
    assert result["attack_chain"]["status"] == "success"  # GET remains the query source.


@pytest.mark.asyncio
async def test_read_identity_in_writer_file_never_posts(configured, monkeypatch, tmp_path):
    mapping = tmp_path / "wrong-writer.json"
    mapping.write_text(json.dumps({"tenant-a": "existing-read-only"}))
    mapping.chmod(0o600)
    monkeypatch.setenv("AISOC_INVESTIGATION_PREPARE_KEYS_FILE", str(mapping))
    with respx.mock(assert_all_called=False) as router:
        result = await attack_context.prepare_alert_graph("tenant-a", "alert-a")
        assert not router.calls
    assert result["reason"] == "projection_writer_is_read_identity"


@pytest.mark.asyncio
@pytest.mark.parametrize("http_status,body", [(403, {}), (200, _payload("foreign-tenant", case="case-a"))])
async def test_failed_or_foreign_read_is_unknown_not_empty(configured, http_status, body):
    with respx.mock(assert_all_called=True) as router:
        router.get(URL).respond(http_status, json=body)
        result = await attack_context.fetch_attack_context("tenant-a", case_id="case-a")
    assert result["attack_path"]["status"] == "unavailable"
    assert "remains unknown" in result["model_summary"]


def test_bundle_summary_reaches_manual_append_and_deep_user_without_extra_call():
    context = _payload("tenant-a", case="case-a")
    context["model_summary"] = attack_context.model_summary(context)
    bundle = ContextBundle(incident_id=uuid4(), tenant_id="tenant-a", attack_context=context)
    assert bundle.has_any_context
    assert bundle.summary_for_llm()["attack_context_summary"] == context["model_summary"]
    encoded = bundle.model_dump(mode="json")
    assert context["model_summary"] in bundle_prompt.format_bundle_prompt_append(encoded)
    state = SimpleNamespace(raw_alert={"title": "generic alert"}, alert_summary="generic alert", mitre_mappings=[], context_bundle=encoded)
    assert context["model_summary"] in _summarise_alert(state)


@pytest.mark.asyncio
async def test_builder_adopts_one_explicit_target_fetch(configured, monkeypatch):
    builder = ContextBundleBuilder()
    captured = []

    async def empty_dict(*_args, **_kwargs):
        return {}

    async def empty_list(*_args, **_kwargs):
        return []

    async def empty_dimensions(*_args, **_kwargs):
        return IncidentContextDimensions()

    async def fetch(tenant_id, **kwargs):
        captured.append((tenant_id, kwargs))
        result = _payload(tenant_id, case=kwargs["case_id"])
        result["model_summary"] = attack_context.model_summary(result)
        return result

    for method in ("_fetch_neighborhoods", "_fetch_baselines", "_fetch_threat_intel"):
        monkeypatch.setattr(builder, method, empty_dict)
    monkeypatch.setattr(builder, "_fetch_history", empty_list)
    monkeypatch.setattr(builder, "_fetch_incident_context", empty_dimensions)
    monkeypatch.setattr(attack_context, "fetch_attack_context", fetch)
    state = SimpleNamespace(incident_id=uuid4(), tenant_id="tenant-a", case_id="case-a", alert_id=None, alert_summary="generic", raw_alert={})
    bundle = await builder.build(state)
    assert captured == [("tenant-a", {"case_id": "case-a", "alert_id": None})]
    assert bundle.attack_context["case_id"] == "case-a"
    assert "candidate-2" in "\n".join(bundle.prompt_context_lines())


@pytest.mark.asyncio
async def test_builder_preserves_case_api_projection_receipt_without_post(configured, monkeypatch):
    from unittest.mock import AsyncMock

    builder = ContextBundleBuilder()
    for method in ("_fetch_neighborhoods", "_fetch_baselines", "_fetch_threat_intel"):
        monkeypatch.setattr(builder, method, AsyncMock(return_value={}))
    monkeypatch.setattr(builder, "_fetch_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(builder, "_fetch_incident_context", AsyncMock(return_value=IncidentContextDimensions()))
    receipt = {"tenant_id": "tenant-a", "case_id": "case-a", "status": "unavailable",
               "source": "postgres_alert_projection", "source_alert_ids": ["seed-alert"],
               "error": "GraphUnavailable", "reason": "GraphUnavailable"}
    state = SimpleNamespace(incident_id=uuid4(), tenant_id="tenant-a", case_id="case-a", alert_id=None,
                            alert_summary="generic", raw_alert={"attack_context_preparation": receipt})
    with respx.mock(assert_all_called=True) as router:
        router.get(URL, params={"case_id": "case-a"}).respond(200, json=_payload("tenant-a", case="case-a"))
        bundle = await builder.build(state)
        assert [call.request.method for call in router.calls] == ["GET"]
    assert bundle.attack_context["prepare"] == {**receipt, "owner": "case_api"}
    assert bundle.attack_context["attack_path"]["status"] == "success"  # Preparation is not the GET result.
    assert "GraphUnavailable" in bundle.attack_context["model_summary"]
    assert "owner=case_api" in bundle.attack_context["model_summary"]
    receipt["source_alert_ids"].clear()
    for _kind, content in attack_context.attack_context_artifacts(bundle.model_dump(mode="json")):
        assert json.loads(content)["prepare"]["source_alert_ids"] == ["seed-alert"]


@pytest.mark.asyncio
async def test_builder_preserves_broker_alert_receipt_with_resolved_case(configured, monkeypatch):
    from unittest.mock import AsyncMock

    builder = ContextBundleBuilder()
    for method in ("_fetch_neighborhoods", "_fetch_baselines", "_fetch_threat_intel"):
        monkeypatch.setattr(builder, method, AsyncMock(return_value={}))
    monkeypatch.setattr(builder, "_fetch_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(builder, "_fetch_incident_context", AsyncMock(return_value=IncidentContextDimensions()))
    receipt = {"tenant_id": "tenant-a", "case_id": "case-a", "alert_id": "alert-a", "scope": "alert",
               "owner": "kafka_consumer", "status": "success", "source_alert_ids": ["alert-a"]}
    state = SimpleNamespace(incident_id=uuid4(), tenant_id="tenant-a", case_id=None, alert_id="alert-a",
                            alert_summary="generic", raw_alert={"attack_context_preparation": receipt})
    body = _payload("tenant-a", case="case-a", alert="alert-a")
    body["scope"] = "alert"
    with respx.mock(assert_all_called=True) as router:
        router.get(URL, params={"alert_id": "alert-a"}).respond(200, json=body)
        bundle = await builder.build(state)
        assert [call.request.method for call in router.calls] == ["GET"]
    for _kind, content in attack_context.attack_context_artifacts(bundle.model_dump(mode="json")):
        saved = json.loads(content)
        assert saved["prepare"] == receipt
        assert "owner=kafka_consumer" in saved["model_summary"]
    receipt["source_alert_ids"].clear()
    assert bundle.attack_context["prepare"]["source_alert_ids"] == ["alert-a"]


@pytest.mark.asyncio
async def test_attack_context_completes_without_extending_existing_source_cutoff(configured, monkeypatch):
    from unittest.mock import AsyncMock

    builder = ContextBundleBuilder(per_source_timeout=0.01)
    for method in ("_fetch_neighborhoods", "_fetch_baselines", "_fetch_threat_intel"):
        monkeypatch.setattr(builder, method, AsyncMock(return_value={}))
    monkeypatch.setattr(builder, "_fetch_incident_context", AsyncMock(return_value=IncidentContextDimensions()))

    async def slow_existing_history(*_args, **_kwargs):
        await asyncio.sleep(0.1)
        return []

    async def delayed_attack_context(*_args, **_kwargs):
        await asyncio.sleep(0.03)
        result = _payload("tenant-a", case="case-a")
        result["model_summary"] = attack_context.model_summary(result)
        return result

    monkeypatch.setattr(builder, "_fetch_history", slow_existing_history)
    monkeypatch.setattr(attack_context, "fetch_attack_context", delayed_attack_context)
    state = SimpleNamespace(incident_id=uuid4(), tenant_id="tenant-a", case_id="case-a", alert_id=None,
                            alert_summary="generic", raw_alert={})
    bundle = await builder.build(state)
    assert "memory:timeout" in bundle.errors
    assert "attack_context:timeout" not in bundle.errors
    assert bundle.attack_context["attack_chain"]["status"] == "success"
    assert "candidate-2" in bundle.summary_for_llm()["attack_context_summary"]


@pytest.mark.asyncio
@pytest.mark.parametrize("case_id,alert_id", [("case-a", None), (None, "alert-a")])
async def test_prefetch_retains_explicit_case_or_alert_target(monkeypatch, case_id, alert_id):
    captured = []

    class Builder:
        def __init__(self, **_kwargs):
            pass

        async def build(self, state):
            captured.append(state)
            return ContextBundle(incident_id=state.incident_id, tenant_id=state.tenant_id)

    monkeypatch.setattr(bundle_prompt, "ContextBundleBuilder", Builder)
    result = await bundle_prompt.prefetch_context_bundle_dict(case_id=case_id, alert_id=alert_id, tenant_id="tenant-a", alert_summary="test", raw_alert={})
    assert result
    assert captured[0].case_id == case_id
    assert captured[0].alert_id == alert_id


def test_legacy_graph_helper_uses_service_tenant_header():
    assert _headers("read-only", "tenant-a") == {"Authorization": "Bearer read-only", "X-AiSOC-Tenant-ID": "tenant-a"}
