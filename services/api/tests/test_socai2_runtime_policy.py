"""Configured time limits apply at admission, reservation and actual dispatch."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.socai2 import baseline_analysis_model as model
from app.socai2 import runtime_policy as policy

FILE = Path(__file__).resolve().parents[3] / "deploy/local-investigation/investigation-policy.toml"


def test_selected_policy_is_fingerprinted_and_has_independent_stage_deadlines():
    settings = policy.load_policy(FILE)
    now = datetime.now(UTC)
    case = settings.case.limits(now, settings.identity)
    assert case.deadline_at - now == timedelta(seconds=1500)
    assert settings.final_reserve_seconds == settings.single_model_timeout_seconds == 300
    assert settings.alert_basic.limits(now, settings.identity).deadline_at - now == timedelta(seconds=300)
    assert settings.incident_diagnosis.limits(now, settings.identity).deadline_at - now == timedelta(seconds=300)
    assert settings.case.allows(case, now)
    assert not settings.case.allows(case.model_copy(update={"deadline_at": case.deadline_at + timedelta(seconds=1)}), now)
    assert not settings.case.allows(case.model_copy(update={"max_model_calls": settings.case.max_model_calls + 1}), now)
    assert settings.sha256[:12] in case.policy_version


@pytest.mark.parametrize("before,after", [("deadline_seconds = 1500", "deadline_seconds = 300"),
    ("final_reserve_seconds = 300", "final_reserve_seconds = 30"),
    ("max_model_calls = 6", "max_model_calls = true")])
def test_missing_or_inconsistent_capacity_is_not_silently_defaulted(tmp_path, before, after):
    target = tmp_path / "policy.toml"
    target.write_text(FILE.read_text().replace(before, after))
    with pytest.raises(ValueError):
        policy.load_policy(target)


def test_actual_provider_request_uses_single_call_cap_and_remaining_time(monkeypatch):
    settings = policy.load_policy(FILE)
    monkeypatch.setattr(policy, "active_policy", lambda: settings)
    calls = []
    async def request(**kwargs):
        calls.append(kwargs["timeout"])
        return {"synthetic": True}
    monkeypatch.setattr(model, "safe_chat_completions_request", request)
    monkeypatch.setattr(model, "enforce_airgap_for_url", lambda url: None)
    gateway = model.TenantChatGateway()
    gateway.config = SimpleNamespace(base_url="http://synthetic.invalid", api_key="synthetic")
    body = {"model": "synthetic", "messages": [], "max_tokens": 1, "response_format": {}}
    asyncio.run(gateway.complete(body, 1400))
    asyncio.run(gateway.complete(body, 17))
    assert calls == [300, 17]
    with pytest.raises(TimeoutError):
        asyncio.run(gateway.complete(body, 0))
    assert calls == [300, 17]


def test_no_selected_policy_cannot_reuse_an_implicit_environment(monkeypatch):
    from app.socai2.baseline_store import StoreError
    policy.active_policy.cache_clear()
    monkeypatch.delenv("SOCAI2_INVESTIGATION_POLICY", raising=False)
    with pytest.raises(StoreError, match="investigation_policy_file_required"):
        policy.active_policy()
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(FILE))
    assert policy.active_policy().case.deadline_seconds == 1500
    policy.active_policy.cache_clear()
