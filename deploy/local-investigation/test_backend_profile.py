"""Offline model-switching guards; no private env, network or database access."""
import asyncio
import hashlib
import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from backend_profile import DEEPSEEK_DEFAULTS, ModelProfileMismatch, freeze, validate
from config import DATABASE, LAKE, TOPIC
from flow_fixture import PILOT_CAMPAIGN, prepare
from validate_flow import ConfigurationStopped, Driver, FlowStopped

DEPLOYED = {"OPENAI_MODEL": "fixture-deployed-model", "OPENAI_BASE_URL": "http://deployed-model.invalid:8000/v1/",
    "SOCAI2_MODEL_PROTOCOL": "chat_completions", "SOCAI2_MODEL_SCHEMA_PROFILE": "vllm_grammar_v1"}


def plan(values=DEPLOYED, backend="deployed"):
    return {"case": {"backend": backend}, "model_profile": freeze(values, backend)}


@pytest.mark.parametrize("status,correct", [(401, False), (404, False), (None, False), (200, False), (200, True)])
def test_deployed_pilot_requires_running_api_model_identity(status, correct):
    driver = Driver.__new__(Driver)
    driver.plan = {**plan(), "campaign": PILOT_CAMPAIGN}
    driver.env, driver.values = DEPLOYED, {"OPENAI_API_KEY": "fixture-only"}
    actual = driver.plan["model_profile"] if correct else freeze(DEEPSEEK_DEFAULTS)
    driver.http = AsyncMock(return_value={"status": status, "body": actual})
    driver.verify_sources = Mock()
    driver.pg = AsyncMock(return_value=[{"database": DATABASE, "tables": 29, "freshness": True}])
    driver.budget = AsyncMock(return_value={"attempted_models": 63, "global_cap": 70})
    with patch("httpx.AsyncClient") as client:
        client.return_value.__aenter__.return_value.get.return_value = SimpleNamespace(status_code=200)
        if correct:
            result = asyncio.run(driver.preflight())
            assert result["runtime"]["running_api_profile_verified"] is True
            driver.budget.assert_awaited_once_with(7)
        else:
            with pytest.raises(ConfigurationStopped, match="running_api_model_profile_not_verified"):
                asyncio.run(driver.preflight())
            driver.pg.assert_not_awaited()
            driver.verify_sources.assert_not_called()
            client.assert_not_called()
    driver.http.assert_awaited_once_with("model-profile", "GET", "/api/v1/socai2/validation/model-profile",
                                         record=False, require_success=False)


def test_freeze_excludes_url_authentication_and_secret_fingerprints():
    secret = "explicit-fixture-secret-not-a-real-key"
    values = {**DEPLOYED, "OPENAI_API_KEY": secret}
    frozen = freeze(values, "deployed")
    text = json.dumps(frozen)
    assert secret not in text and hashlib.sha256(secret.encode()).hexdigest() not in text
    assert "deployed-model.invalid" not in text and "OPENAI_API_KEY" not in text
    assert frozen["base_url_sha256"] == hashlib.sha256(b"http://deployed-model.invalid:8000/v1").hexdigest()
    # Credentials may rotate without changing the frozen non-secret backend.
    assert validate(plan(), {**values, "OPENAI_API_KEY": "changed-fixture-key"})["backend"] == "deployed"


@pytest.mark.parametrize("key,value", [("OPENAI_MODEL", "different-model"),
    ("OPENAI_BASE_URL", "http://different.invalid:8000/v1"), ("SOCAI2_MODEL_SCHEMA_PROFILE", "standard"),
    ("SOCAI2_MODEL_PROTOCOL", "deepseek_responses")])
def test_frozen_configuration_drift_is_rejected_before_any_service_access(key, value):
    driver = Driver.__new__(Driver)
    driver.plan, driver.env = plan(), {**DEPLOYED, key: value}
    driver.values = {"OPENAI_API_KEY": "fixture-only"}
    driver.verify_sources = lambda: None
    driver.pg = AsyncMock(side_effect=AssertionError("database access is forbidden"))
    with patch("httpx.AsyncClient", side_effect=AssertionError("network access is forbidden")), \
            pytest.raises(FlowStopped, match="model_configuration_changed|deployed_backend_requires"):
        asyncio.run(driver.preflight())
    driver.pg.assert_not_called()


def test_legacy_plans_are_deepseek_only_and_validate_the_full_official_endpoint():
    legacy = {"case": {"backend": "deepseek"}}
    assert validate(legacy, DEEPSEEK_DEFAULTS)["compatibility"] == "legacy_deepseek_only"
    for changes in ({"OPENAI_BASE_URL": "https://api.deepseek.com/v1"},
                    {"OPENAI_BASE_URL": "https://api.deepseek.com.invalid"},
                    {"SOCAI2_MODEL_SCHEMA_PROFILE": "vllm_grammar_v1"}):
        with pytest.raises(ModelProfileMismatch, match="deepseek_backend_configuration_mismatch"):
            validate(legacy, {**DEEPSEEK_DEFAULTS, **changes})
    with pytest.raises(ModelProfileMismatch, match="legacy_plan_only_supports"):
        validate({"case": {"backend": "deployed"}}, DEPLOYED)


@pytest.mark.parametrize("url", ["https://user:password@fixture.invalid/v1",
    "https://fixture.invalid/v1?api_key=fixture", "https://fixture.invalid/v1#credential", "file:///tmp/socket"])
def test_endpoint_cannot_hide_credentials_in_the_frozen_url(url):
    with pytest.raises(ModelProfileMismatch, match="model_base_url_must_be_plain_http_endpoint") as exc:
        freeze({**DEPLOYED, "OPENAI_BASE_URL": url}, "deployed")
    assert url not in str(exc.value)


def test_prepare_requires_explicit_deployed_backend_and_preserves_local_data_routes():
    start = "2026-11-05T12:00:00+00:00"
    with pytest.raises(ModelProfileMismatch, match="deepseek_backend_configuration_mismatch"):
        prepare("local-profile-default", start, model_values=DEPLOYED)
    with pytest.raises(ModelProfileMismatch, match="requires_explicit_local_configuration"):
        prepare("local-profile-missing", start, backend="deployed")
    default, _ = prepare("local-profile-cloud", start)
    deployed, _ = prepare("local-profile-deployed", start, backend="deployed", model_values=DEPLOYED)
    assert default["case"]["backend"] == default["model_profile"]["backend"] == "deepseek"
    assert deployed["case"]["key"] == "deployed-maintenance"
    assert deployed["model_profile"] == freeze(DEPLOYED, "deployed")
    for result in (default, deployed):
        assert (result["database"], result["lake_database"], result["topic_prefix"]) == (DATABASE, LAKE, TOPIC)
        assert result["max_model_calls"] == 11 and result["global_local_model_call_cap"] == 50
        assert result["baseline_limits"] == {"max_tokens": 48000, "max_model_calls": 4, "max_tool_calls": 4, "seconds": 120}
    assert not set(default["canonical_alert_ids"]) & set(deployed["canonical_alert_ids"])


def test_frozen_case_backend_and_profile_must_agree():
    changed = plan()
    changed["case"]["backend"] = "deepseek"
    with pytest.raises(ModelProfileMismatch, match="case_backend_does_not_match"):
        validate(changed, DEPLOYED)


@pytest.mark.parametrize("source_drift", [False, True])
def test_configuration_rejection_does_not_trigger_failure_export(tmp_path, source_drift):
    from validate_flow import run
    driver = Driver.__new__(Driver)
    driver.root = tmp_path / "validation" / "local-profile-rejection"
    driver.root.mkdir(parents=True)
    driver.plan, driver.env = plan(), {**DEPLOYED, "OPENAI_MODEL": "changed-model"}
    driver.values = {"OPENAI_API_KEY": "fixture-only"}
    driver.verify_sources = Mock(side_effect=FlowStopped("source_changed_after_plan_freeze_new_batch_required") if source_drift else None)
    driver.pg = AsyncMock(side_effect=AssertionError("database access is forbidden"))
    export = AsyncMock(side_effect=AssertionError("failure export is forbidden"))
    args = SimpleNamespace(batch=driver.root.name, phase="preflight", execute=True)
    with patch("validate_flow.dispatch_lock", return_value=nullcontext()), \
            patch("validate_flow.STATE", tmp_path), patch("validate_flow.Driver", return_value=driver), \
            patch("validate_flow.read_private", return_value={}), patch("validate_flow.export", export), \
            patch("httpx.AsyncClient", side_effect=AssertionError("network access is forbidden")):
        result = asyncio.run(run(args))
    assert result["passed"] is False and result["export_skipped_reason"] == "model_configuration_not_verified"
    assert result["code"] == "model_configuration_changed_after_plan_freeze_new_batch_required"
    driver.verify_sources.assert_not_called()
    driver.pg.assert_not_called()
    export.assert_not_called()
