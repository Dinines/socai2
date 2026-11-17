"""Current execution rejects incomplete contracts before storage, queues or models."""
import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.socai2 import analysis_case_executor, runtime_policy
from app.socai2.alert_basic_executor import AlertBasicExecutor
from app.socai2.analysis_dispatch_runtime import validate_executors
from app.socai2.baseline_context import capture
from app.socai2.baseline_deep import BaselineDeep
from app.socai2.baseline_executor import BaselineExecutor
from app.socai2.baseline_reanalysis import BaselineReanalysis
from app.socai2.baseline_store import StoreError
from app.socai2.case_allocation_policy import CaseAllocationPolicy
from app.socai2.incident_diagnosis_executor import IncidentDiagnosisExecutor

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "deploy/local-investigation/investigation-policy-case-v1.toml"


@pytest.fixture
def current(monkeypatch):
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    selected = runtime_policy.active_policy
    selected.cache_clear()
    yield selected()
    selected.cache_clear()


def config(path=POLICY):
    value = json.loads((ROOT / "deploy/local-investigation/analysis-aic-executors.example.json").read_text())
    return {**value, "investigation_policy_file": str(path)}


@pytest.mark.parametrize("missing", ["alert_io", "incident_io", "case_io"])
def test_factory_rejects_missing_contract_before_constructing_handlers(current, missing, monkeypatch):
    monkeypatch.setattr(analysis_case_executor, "active_policy", lambda: replace(current, **{missing: None}))
    def forbidden(*args):
        pytest.fail("partial handlers must not be constructed")
    monkeypatch.setattr(analysis_case_executor, "ai_executors", forbidden)
    with pytest.raises(ValueError, match="execution_profile_required:" + missing):
        analysis_case_executor.executors(config(), SimpleNamespace(sessions=None))


def test_complete_factory_and_configured_budget_remain_valid(current, tmp_path, monkeypatch):
    target = tmp_path / "policy.toml"
    source = POLICY.read_text()
    configured_budget = f"C3 = {current.model.output_tokens['C3']}"
    assert source.count(configured_budget) == 1
    target.write_text(source.replace(configured_budget, "C3 = 4096", 1))
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(target))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert policy.model.output_tokens["C3"] == 4096
    monkeypatch.setattr(CaseAllocationPolicy, "load", lambda: CaseAllocationPolicy(100, 100, 20, 100))
    handlers = analysis_case_executor.executors(config(target), SimpleNamespace(sessions=None))
    assert set(handlers) == {"alert_triage", "incident_diagnosis", "case_investigation"}
    validate_executors(handlers)
    with pytest.raises(ValueError, match="differs from selected runtime policy"):
        analysis_case_executor.executors(config(), SimpleNamespace(sessions=None))


@pytest.mark.parametrize("name", ["incident_io", "case_io"])
def test_old_nested_contract_is_readable_but_not_executable(current, name):
    profile = getattr(current, name)
    value = profile.config
    if name == "incident_io":
        value.pop("output_validation")
    else:
        value["program_output"]["version"] = "socai2.case-program-output.v1"
    raw = json.dumps(value).encode()
    policy = replace(current, **{name: replace(profile, raw=raw, sha256=hashlib.sha256(raw).hexdigest())})
    assert policy.snapshot()["profiles"][name]["json_text"] == raw.decode()
    with pytest.raises(ValueError, match="execution_profile_not_current:" + name):
        policy.require_execution_profiles()


@pytest.mark.parametrize("missing", ["alert_triage", "incident_diagnosis", "case_investigation"])
def test_partial_dispatcher_registration_is_rejected(missing):
    handler = SimpleNamespace(load=AsyncMock(), execute=AsyncMock())
    handlers = dict.fromkeys({"alert_triage", "incident_diagnosis", "case_investigation"} - {missing}, handler)
    with pytest.raises(ValueError, match="requires current A/I/Case"):
        validate_executors(handlers)
    handler.load.assert_not_awaited()
    handler.execute.assert_not_awaited()


@pytest.mark.parametrize("kind,executor", [("alert_io", AlertBasicExecutor), ("incident_io", IncidentDiagnosisExecutor)])
def test_actual_stage_entry_rejects_missing_contract_before_claim(current, kind, executor, monkeypatch):
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: replace(current, **{kind: None}))
    service = SimpleNamespace(begin=AsyncMock())
    gateway = SimpleNamespace(configure=AsyncMock(), complete=AsyncMock())
    with pytest.raises(StoreError, match="investigation_execution_contract_required"):
        asyncio.run(executor(service, gateway=gateway).execute(uuid4(), uuid4(), uuid4()))
    service.begin.assert_not_awaited()
    gateway.configure.assert_not_awaited()
    gateway.complete.assert_not_awaited()


def test_case_capture_rejects_old_policy_before_database_read(current, monkeypatch):
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: replace(current, case_io=None))
    db = SimpleNamespace(execute=AsyncMock())
    with pytest.raises(StoreError, match="investigation_execution_contract_required"):
        asyncio.run(capture(db, uuid4(), uuid4(), None))
    db.execute.assert_not_awaited()


@pytest.mark.parametrize("profile", [None, {"version": "old", "sha256": "old", "business_sha256": "old"}])
def test_case_and_followup_entries_cannot_fall_back_to_old_frozen_input(current, profile):
    context = SimpleNamespace(case_input_profile=profile)
    store = SimpleNamespace(read_context=AsyncMock(return_value=context))
    @asynccontextmanager
    async def transaction(*args, **kwargs):
        yield store
    service = SimpleNamespace(transaction=transaction)
    gateway = SimpleNamespace(configure=AsyncMock(), complete=AsyncMock())
    tenant, case, run = uuid4(), uuid4(), uuid4()
    calls = [
        BaselineExecutor(service, tenant, gateway=gateway, lake=object()).execute(SimpleNamespace(case_id=case, run_id=run)),
        BaselineDeep(service).input(tenant, case, run, "q", {}, uuid4(), None),
        BaselineReanalysis(service).input(tenant, case, run, context, {}, uuid4(), [], extra_data={"round": "final_delivery"}),
    ]
    for call in calls:
        with pytest.raises(StoreError, match="case_input_profile_changed"):
            asyncio.run(call)
    gateway.configure.assert_not_awaited()
    gateway.complete.assert_not_awaited()


def test_older_policy_snapshots_remain_loadable_without_becoming_execution_defaults():
    policy = runtime_policy.load_policy(POLICY.with_name("investigation-policy.toml"))
    assert policy.snapshot()["toml_text"] and not policy.snapshot()["profiles"]
    with pytest.raises(ValueError, match="execution_profile_required"):
        policy.require_execution_profiles()
