"""Pilot route checks using the real gateway configuration path, without provider I/O."""
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints.socai2_cases import get_service
from app.socai2 import baseline_analysis_model
from backend_profile import freeze
from config import TENANT
from fastapi.testclient import TestClient
from pilot_api import PROFILE_PATH, app, investigation_api, probe

DEPLOYED = {"OPENAI_MODEL": "fixture-9b", "OPENAI_BASE_URL": "http://fixture-21.invalid/v1",
            "SOCAI2_MODEL_PROTOCOL": "chat_completions", "SOCAI2_MODEL_SCHEMA_PROFILE": "vllm_grammar_v1"}


@pytest.fixture
def runtime(monkeypatch):
    user = CurrentUser(UUID(int=1), UUID(TENANT), "analyst", "fixture", scopes=["cases:read"])
    db = object()

    @asynccontextmanager
    async def transaction(tenant_id):
        assert tenant_id == UUID(TENANT)
        yield SimpleNamespace(db=db)

    config = SimpleNamespace(allowed=True, base_url=DEPLOYED["OPENAI_BASE_URL"],
                             model=DEPLOYED["OPENAI_MODEL"], api_key="never-exported-key")
    resolver = AsyncMock(return_value=config)
    monkeypatch.setattr(baseline_analysis_model, "resolve_llm_config", resolver)
    monkeypatch.setattr(baseline_analysis_model.TenantChatGateway, "complete",
                        AsyncMock(side_effect=AssertionError("a preflight cannot infer")))
    monkeypatch.setenv("OPENAI_MODEL", "different-environment-model")
    monkeypatch.setenv("SOCAI2_MODEL_PROTOCOL", DEPLOYED["SOCAI2_MODEL_PROTOCOL"])
    monkeypatch.setenv("SOCAI2_MODEL_SCHEMA_PROFILE", DEPLOYED["SOCAI2_MODEL_SCHEMA_PROFILE"])
    monkeypatch.setitem(probe.dependency_overrides, get_current_user, lambda: user)
    monkeypatch.setitem(probe.dependency_overrides, get_service, lambda: SimpleNamespace(transaction=transaction))
    yield SimpleNamespace(client=TestClient(app), db=db, resolver=resolver, config=config, user=user)
    baseline_analysis_model.TenantChatGateway.complete.assert_not_awaited()


def test_pilot_returns_actual_tenant_profile_with_only_public_fields(runtime):
    response = runtime.client.get(PROFILE_PATH)
    assert response.status_code == 200
    assert response.json() == freeze(DEPLOYED, backend="deployed")
    runtime.resolver.assert_awaited_once_with(runtime.db, UUID(TENANT))


def test_pilot_rejects_deepseek_process(runtime, monkeypatch):
    runtime.config.base_url = baseline_analysis_model.DEEPSEEK_BASE
    runtime.config.model = "deepseek-flash"
    monkeypatch.setenv("SOCAI2_MODEL_PROTOCOL", "deepseek_responses")
    monkeypatch.setenv("SOCAI2_MODEL_SCHEMA_PROFILE", "standard")
    response = runtime.client.get(PROFILE_PATH)
    assert response.status_code == 409
    assert response.json() == {"detail": "pilot_deployed_model_profile_mismatch"}


@pytest.mark.parametrize("reason", ["disabled", "error"])
def test_unavailable_gateway_returns_safe_failure(runtime, reason):
    runtime.config.allowed = False
    if reason == "error":
        runtime.resolver.side_effect = RuntimeError("internal secret")
    response = runtime.client.get(PROFILE_PATH)
    assert response.status_code == 503
    assert response.json() == {"detail": "pilot_model_configuration_unavailable"}


@pytest.mark.parametrize("invalid", ["scope", "tenant"])
def test_pilot_requires_case_read_permission_and_fixed_tenant(runtime, invalid):
    if invalid == "scope":
        runtime.user.scopes = ["alerts:read"]
    else:
        runtime.user.tenant_id = UUID(int=2)
    assert runtime.client.get(PROFILE_PATH).status_code == 403
    runtime.resolver.assert_not_awaited()


def test_probe_requires_auth_and_leaves_normal_api_untouched():
    assert TestClient(app).get(PROFILE_PATH).status_code == 401
    assert TestClient(investigation_api).get(PROFILE_PATH).status_code == 404
    assert PROFILE_PATH not in investigation_api.openapi()["paths"]
    assert TestClient(app).get("/livez").json() == TestClient(investigation_api).get("/livez").json()
