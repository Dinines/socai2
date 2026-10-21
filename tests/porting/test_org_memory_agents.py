"""3A-04: typed organisation-memory reads, current material, and frozen replay."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.agents.auto_triage_agent import _build_alert_context
from app.context import organisation_memory as om
from app.models.state import InvestigationState
from app.replay.shadow import ContextSnapshot, FrozenTriageContextReader
from app.workers.triage_persistence import CONTEXT_FREEZE_KINDS, LiveTriageContextReader, TriageContextReader

TENANT = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)


@pytest.fixture
def context(monkeypatch, tmp_path):
    keys = tmp_path / "org-memory-keys.json"
    keys.write_text(json.dumps({TENANT: "tenant-a-key", OTHER: "tenant-b-key"}))
    keys.chmod(0o600)
    monkeypatch.setenv("AISOC_ORG_MEMORY_KEYS_FILE", str(keys))
    monkeypatch.setenv("AISOC_ORG_MEMORY_ENABLED", "1")
    monkeypatch.setenv("AISOC_AGENTS_SERVICE_TOKEN", "must-never-be-used")
    monkeypatch.setattr(om, "_now", lambda: NOW)
    om.clear_cache()
    calls = []
    reply = SimpleNamespace(status=200, body={"tenant_id": TENANT, "statements": []}, error=None)

    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if reply.error:
                raise reply.error
            return om.httpx.Response(reply.status, json=reply.body)

    monkeypatch.setattr(om.httpx, "AsyncClient", lambda **kwargs: Client())
    yield keys, calls, reply
    om.clear_cache()


@pytest.mark.asyncio
async def test_bearer_identity_tenant_and_empty_meaning(context):
    _, calls, _ = context
    result = await LiveTriageContextReader().fetch_organisation_memory(TENANT)
    assert result["status"] == "no_match"
    assert result["statement_scope"] == "tenant_active_statements"
    assert result["http_status"] == 200
    assert calls[0][1] == {"params": {"tenant_id": TENANT}, "headers": {"Authorization": "Bearer tenant-a-key"}}
    assert "not a search" in om.render_read_status(result)
    assert "must-never" not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,reason", [("absent", "not_configured"), ("bad_json", "not_configured"), ("permissions", "not_configured"), ("unmapped", "not_configured")])
async def test_missing_or_unsafe_mapping_never_falls_back(context, monkeypatch, mode, reason):
    keys, calls, _ = context
    if mode == "absent":
        monkeypatch.delenv("AISOC_ORG_MEMORY_KEYS_FILE")
    elif mode == "bad_json":
        keys.write_text("{")
    elif mode == "permissions":
        keys.chmod(0o644)
    else:
        keys.write_text(json.dumps({OTHER: "tenant-b-key"}))
    result = await om.fetch_organisation_memory(TENANT)
    assert result["status"] == "unavailable" and result["reason"] == reason
    assert result["statements"] == [] and calls == []


@pytest.mark.asyncio
async def test_disabled_is_distinct_and_does_not_contact_api(context, monkeypatch):
    _, calls, _ = context
    monkeypatch.setenv("AISOC_ORG_MEMORY_ENABLED", "0")
    result = await om.fetch_organisation_memory(TENANT)
    assert result["status"] == "disabled" and calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status,reason", [(401, "auth_failed"), (403, "auth_failed"), (500, "http_error"), (302, "http_error")])
async def test_http_failure_is_not_an_empty_success(context, status, reason):
    _, _, reply = context
    reply.status = status
    result = await om.fetch_organisation_memory(TENANT)
    assert result["status"] == "unavailable" and result["reason"] == reason
    assert result["http_status"] == status and result["statements"] == []
    assert "does not establish" in om.render_read_status(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"tenant_id": OTHER, "statements": []}, {"tenant_id": TENANT}, {"tenant_id": TENANT, "statements": ["oops"]}, {"tenant_id": TENANT, "statements": [{"observations": 1}]}, {"tenant_id": TENANT, "statements": [{"statement": "bad expiry", "expires_at": "invalid"}]}, {"tenant_id": TENANT, "statements": [{"statement": "   "}]}])
async def test_malformed_or_wrong_tenant_response_cannot_poison_cache(context, body):
    _, _, reply = context
    reply.body = body
    result = await om.fetch_organisation_memory(TENANT)
    assert result["status"] == "unavailable" and result["reason"] == "invalid_response"
    assert om._cache == {} and result["statements"] == []


@pytest.mark.asyncio
async def test_expiry_is_rechecked_on_fresh_cache_hit(context, monkeypatch):
    _, calls, reply = context
    reply.body["statements"] = [{"statement": "Short-lived change window", "observations": 2, "expires_at": (NOW + timedelta(seconds=1)).isoformat()}]
    first = await om.fetch_organisation_memory(TENANT)
    assert first["status"] == "success" and first["adopted_count"] == 1
    monkeypatch.setattr(om, "_now", lambda: NOW + timedelta(seconds=2))
    second = await om.fetch_organisation_memory(TENANT)
    assert second["status"] == "no_match" and second["adopted_count"] == 0
    assert second["expired_count"] == 1 and len(calls) == 1
    assert second["cache"]["source"] == "memory"


@pytest.mark.asyncio
async def test_failed_refresh_does_not_adopt_stale_and_recovers(context, monkeypatch):
    _, calls, reply = context
    monkeypatch.setattr(om, "_CACHE_TTL_S", 0)
    reply.body["statements"] = [{"statement": "Still valid but stale", "observations": 2, "expires_at": None}]
    assert (await om.fetch_organisation_memory(TENANT))["status"] == "success"
    reply.error = om.httpx.ConnectError("unavailable")
    failed = await om.fetch_organisation_memory(TENANT)
    assert failed["status"] == "unavailable" and failed["reason"] == "transport_error"
    assert failed["statements"] == [] and failed["cache"]["freshness"] == "expired"
    reply.error = None
    assert (await om.fetch_organisation_memory(TENANT))["status"] == "success"
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_identity_rotation_and_mapping_removal_do_not_reuse_cache(context):
    keys, calls, reply = context
    reply.body["statements"] = [{"statement": "Tenant A convention", "observations": 2}]
    await om.fetch_organisation_memory(TENANT)
    keys.write_text(json.dumps({TENANT: "rotated-tenant-a-key"}))
    await om.fetch_organisation_memory(TENANT)
    assert len(calls) == 2 and calls[-1][1]["headers"]["Authorization"] == "Bearer rotated-tenant-a-key"
    keys.write_text("{}")
    missing = await om.fetch_organisation_memory(TENANT)
    assert missing["reason"] == "not_configured" and missing["statements"] == []


@pytest.mark.asyncio
async def test_live_tenant_cache_is_isolated(context):
    _, calls, reply = context
    reply.body["statements"] = [{"statement": "Tenant A only", "observations": 2}]
    await om.fetch_organisation_memory(TENANT)
    reply.body = {"tenant_id": OTHER, "statements": [{"statement": "Tenant B only", "observations": 3}]}
    other = await om.fetch_organisation_memory(OTHER)
    assert other["statements"][0]["statement"] == "Tenant B only"
    assert calls[-1][1]["headers"]["Authorization"] == "Bearer tenant-b-key"
    first = await om.fetch_organisation_memory(TENANT)
    assert first["statements"][0]["statement"] == "Tenant A only" and len(calls) == 2


def test_actual_adopted_subset_and_entire_prompt_block_are_accounted_for():
    rows = [{"statement": f"Statement {i}: " + "a" * 400, "observations": i} for i in range(20)]
    result = om.make_read(TENANT, rows=rows)
    assert result["received_count"] == 20 and result["adopted_count"] == 12
    assert result["statements"][0]["observations"] == 19
    assert all(len(row["statement"]) == 300 for row in result["statements"])
    stable = json.dumps(result["statements"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert result["statements_sha256"] == hashlib.sha256(stable.encode()).hexdigest()
    state = InvestigationState(tenant_id=UUID(TENANT), incident_id=UUID(OTHER), organisation_memory=result["statements"], organisation_memory_read=result)
    prompt = _build_alert_context(state, nonce="test")
    assert result["prompt_block"] in prompt and len(result["prompt_block"]) > 2000
    assert "status=success" in prompt and "never overrides direct evidence of compromise" in prompt
    assert result["prompt_sha256"] == hashlib.sha256(result["prompt_block"].encode()).hexdigest()


@pytest.mark.asyncio
async def test_frozen_read_uses_split_and_never_todays_expiry_clock(context, monkeypatch):
    _, calls, _ = context
    split = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot = ContextSnapshot(split_at=split, statements=({"statement": "Valid at historical split", "observations": 2, "expires_at": "2026-02-01T00:00:00Z"},))
    frozen = FrozenTriageContextReader(snapshot)
    assert isinstance(frozen, TriageContextReader)
    result = await frozen.fetch_organisation_memory(TENANT)
    assert result["status"] == "success" and result["source"] == "replay.snapshot"
    assert result["read_at"] == split.isoformat() and result["cache"]["freshness"] == "frozen"
    assert result["statements"][0]["statement"] == "Valid at historical split" and calls == []
    result["statements"][0]["statement"] = "edited"
    assert (await frozen.fetch_organisation_memory(TENANT))["statements"][0]["statement"] == "Valid at historical split"
    assert CONTEXT_FREEZE_KINDS["fetch_organisation_memory"] == "snapshot"


def test_no_read_is_explicit_without_inventing_prompt_material():
    state = InvestigationState(tenant_id=UUID(TENANT), incident_id=UUID(OTHER))
    assert state.organisation_memory_read == {"status": "not_requested"}
    assert "Organisation memory" not in _build_alert_context(state, nonce="test")
